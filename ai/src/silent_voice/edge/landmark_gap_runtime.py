"""Runtime LGH distinto: geometria auditada antes do forward R4 congelado."""

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from silent_voice.edge.preheldout_freeze import validate_edge_embedding
from silent_voice.edge.rejection_4_final_heldout import LABELS, decision_for_score
from silent_voice.vision.detector import MediaPipeMouthDetector
from silent_voice.vision.feature_sample_builder import build_visual_feature_sample
from silent_voice.vision.hybrid_features import (
    HybridSample,
    class_minimum_dtw_distances,
    equal_energy_fusion,
    normalized_reciprocal_evidence,
)
from silent_voice.vision.landmark_gap import (
    POLICY_ID,
    POLICY_SHA256,
    SAFE_REJECT,
    analyze_and_reconstruct,
)
from silent_voice.vision.landmarks import MouthLandmarksFrame
from silent_voice.vision.mouth_roi_dataset import (
    MouthRoiConfig,
    _crop_frame,
    _interpolate_and_smooth,
    _max_missing_run,
)
from silent_voice.vision.positive_classifier_final import clip_embedding_sha256
from silent_voice.vision.swinlip_frozen_encoder import (
    prepare_input,
    select_source_frame_indices,
)
from silent_voice.vision.temporal_features import extract_temporal_features
from silent_voice.vision.visual_experiment_defaults import (
    build_default_segmentation_config,
)
from silent_voice.vision.visual_sample_segmentation import segment_visual_feature_sample

RUNTIME_ID = "VISUAL_RUNTIME_LANDMARK_GAP_HARDENED_V1"
REASON = "INSUFFICIENT_VISUAL_EVIDENCE"
DiagnosticSink = Callable[[dict], None]


@dataclass(frozen=True, slots=True)
class DecodedQuery:
    frames: tuple[np.ndarray, ...]
    coordinates: np.ndarray
    valid_mask: np.ndarray
    timestamps_ms: np.ndarray
    declared_frame_count: int


@dataclass(frozen=True, slots=True)
class PreparedQuery:
    query: HybridSample | None
    tensor: np.ndarray | None
    diagnostics: dict


class JsonlDiagnosticSink:
    """Journal append-only, flush e fsync antes de permitir o próximo estágio."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def __call__(self, diagnostics: dict) -> None:
        payload = (
            json.dumps(
                diagnostics, ensure_ascii=False, sort_keys=True, allow_nan=False
            ).encode("utf-8")
            + b"\n"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())


def decode_query(path: Path) -> DecodedQuery:
    """Decodifica frames reais e detecta uma vez, mantendo ausências explícitas."""
    capture = cv2.VideoCapture(str(path))
    detector = None
    frames, coordinates, mask = [], [], []
    declared_count = None
    try:
        if not capture.isOpened():
            raise ValueError(f"Vídeo ilegível: {path}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        declared = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError(f"FPS inválido: {path}")
        if not math.isfinite(declared) or declared < 0 or not declared.is_integer():
            raise ValueError("Contagem declarada inválida.")
        declared_count = int(declared)
        detector = MediaPipeMouthDetector()
        while True:
            success, frame = capture.read()
            if not success:
                break
            index = len(frames)
            timestamp = index * 1000.0 / fps
            frames.append(frame)
            value = detector.extract(frame, index, timestamp)
            mask.append(value is not None)
            if value is None:
                coordinates.append(np.full((40, 2), np.nan, dtype=np.float64))
            else:
                if value.frame_index != index or value.timestamp_ms != timestamp:
                    raise ValueError("Índice/timestamp do detector desalinhado.")
                points = np.asarray(value.points, dtype=np.float64)
                if points.shape != (40, 2):
                    raise ValueError("Schema dos landmarks inválido.")
                coordinates.append(points)
        count = len(frames)
        return DecodedQuery(
            tuple(frames),
            np.asarray(coordinates, dtype=np.float64).reshape(count, 40, 2),
            np.asarray(mask, dtype=np.bool_),
            np.arange(count, dtype=np.float64) * 1000.0 / fps,
            int(declared),
        )
    except BaseException as error:
        context = {
            "decoded_frame_count": len(frames),
            "declared_frame_count": declared_count,
            "last_complete_detection_mask": list(mask),
            "last_complete_detection_count": sum(mask),
        }
        if len(mask) == len(frames):
            missing = [i for i, valid in enumerate(mask) if not valid]
            context.update(
                landmark_detected_count=sum(mask),
                landmark_missing_count=len(missing),
                landmark_missing_fraction=len(missing) / len(mask) if mask else None,
                landmark_max_consecutive_missing=_max_missing_run(
                    np.array(mask, dtype=np.bool_)
                ),
                landmark_missing_indices=missing,
                detection_valid_mask=list(mask),
            )
        error.landmark_gap_decode_context = context
        raise
    finally:
        capture.release()
        if detector is not None:
            detector.mesh.close()


def _diagnostic_identity(row, runtime_commit, models_loaded_process):
    return {
        **dict.fromkeys(
            (
                "decoded_frame_count",
                "declared_frame_count",
                "landmark_detected_count",
                "landmark_missing_count",
                "landmark_missing_fraction",
                "landmark_max_consecutive_missing",
                "landmark_missing_indices",
                "detection_valid_mask",
                "landmark_gap_action",
                "interpolation_count",
                "interpolation_indices",
            )
        ),
        "violated_conditions": [],
        "sample_id": row["sample_id"],
        "session_id": row["session_id"],
        "runtime_id": RUNTIME_ID,
        "runtime_commit": runtime_commit,
        "policy_id": POLICY_ID,
        "policy_sha256": POLICY_SHA256,
        "models_loaded_process": models_loaded_process,
        "model_inference_performed_for_query": False,
    }


def _technical_error(diagnostics: dict, stage: str, error: BaseException):
    return {
        **diagnostics,
        "preprocessing_status": "TECHNICAL_ERROR",
        "preprocessing_stage": stage,
        "technical_reason": f"{type(error).__name__}: {error}",
    }


def _safe_preparation(diagnostics: dict, condition: str, sink: DiagnosticSink):
    diagnostics.update(
        landmark_gap_action=SAFE_REJECT,
        preprocessing_status="SAFE_REJECTED",
        technical_reason=REASON,
        violated_conditions=[*diagnostics["violated_conditions"], condition],
    )
    sink(dict(diagnostics))
    return PreparedQuery(None, None, diagnostics)


def _array_evidence(values: np.ndarray) -> dict:
    data = np.ascontiguousarray(values)
    return {
        "shape": list(data.shape),
        "dtype": data.dtype.str,
        "sha256": hashlib.sha256(data.tobytes()).hexdigest(),
    }


def build_preprocessing_evidence(
    coordinates, geometry, rois, source, segmented_features, tensor, mask, indices
) -> dict:
    """Hashes exatos de dtype/shape/bytes, sem resultados ou métricas de modelo."""
    return {
        name: _array_evidence(value)
        for name, value in {
            "coordinates": coordinates,
            "geometry": geometry,
            "rois": rois,
            "features": source.features,
            "timestamps_ms": source.timestamps_ms,
            "segmented_features": segmented_features,
            "tensor": tensor,
            "detection_mask": mask,
            "sampled_indices": indices,
        }.items()
    }


def prepare_decoded_query(
    row: dict,
    decoded: DecodedQuery,
    *,
    diagnostic_sink: DiagnosticSink,
    runtime_commit: str,
    models_loaded_process: bool = False,
) -> PreparedQuery:
    """Aplica a policy antes de ROI/features e mantém o caminho numérico R4."""
    count = len(decoded.frames)
    diagnostics = {
        **_diagnostic_identity(row, runtime_commit, models_loaded_process),
        "decoded_frame_count": count,
        "declared_frame_count": decoded.declared_frame_count,
    }
    try:
        result = analyze_and_reconstruct(decoded.coordinates, decoded.valid_mask)
        diagnostics.update(result.diagnostics)
        diagnostics["preprocessing_stage"] = "LANDMARK_GAP_ANALYSIS"
        if any(
            not isinstance(frame, np.ndarray)
            or frame.dtype != np.uint8
            or frame.ndim != 3
            or frame.shape[2] != 3
            or frame.shape[0] <= 0
            or frame.shape[1] <= 0
            for frame in decoded.frames
        ):
            raise ValueError("Schema dos frames BGR uint8 inválido.")
        if (
            isinstance(decoded.declared_frame_count, bool)
            or not isinstance(decoded.declared_frame_count, int)
            or decoded.declared_frame_count < 0
            or (
                decoded.declared_frame_count > 0
                and decoded.declared_frame_count != count
            )
            or result.coordinates.shape[0] != count
            or not isinstance(decoded.timestamps_ms, np.ndarray)
            or decoded.timestamps_ms.shape != (count,)
            or decoded.timestamps_ms.dtype != np.float64
            or not np.isfinite(decoded.timestamps_ms).all()
            or (count and decoded.timestamps_ms[0] != 0)
            or (count > 1 and not np.all(np.diff(decoded.timestamps_ms) > 0))
        ):
            raise ValueError("Contagem/timestamps/schema decodificados inválidos.")
    except BaseException as error:
        mask = decoded.valid_mask
        if (
            diagnostics["detection_valid_mask"] is None
            and isinstance(mask, np.ndarray)
            and mask.dtype == np.bool_
            and mask.shape == (count,)
        ):
            missing = np.flatnonzero(~mask)
            diagnostics.update(
                landmark_detected_count=int(mask.sum()),
                landmark_missing_count=len(missing),
                landmark_missing_fraction=len(missing) / count if count else None,
                landmark_max_consecutive_missing=_max_missing_run(mask),
                landmark_missing_indices=missing.tolist(),
                detection_valid_mask=mask.tolist(),
            )
        diagnostic_sink(_technical_error(diagnostics, "LANDMARK_GAP_ANALYSIS", error))
        raise
    diagnostic_sink(dict(diagnostics))
    if result.action == SAFE_REJECT:
        return PreparedQuery(None, None, diagnostics)

    stage = "ROI_AND_FEATURES"
    diagnostics["preprocessing_stage"] = stage
    try:
        points, mask = result.coordinates, result.valid_mask
        geometry = np.full((count, 4), np.nan, dtype=np.float64)
        for index in np.flatnonzero(mask):
            left, right = points[index, 0], points[index, 10]
            delta = right - left
            center = (left + right) / 2.0
            geometry[index] = (
                center[0],
                center[1],
                math.atan2(delta[1], delta[0]),
                float(np.linalg.norm(delta)),
            )
        detected_indices = np.flatnonzero(mask)
        config = MouthRoiConfig()
        angles = geometry[:, 2].copy()
        angles[detected_indices] = np.unwrap(angles[detected_indices])
        centers = np.column_stack(
            [
                _interpolate_and_smooth(
                    geometry[:, axis], detected_indices, count, config.smoothing_window
                )
                for axis in (0, 1)
            ]
        )
        smoothed_angles = _interpolate_and_smooth(
            angles, detected_indices, count, config.smoothing_window
        )
        crop_side = config.crop_scale * float(np.median(geometry[mask, 3]))
        if (
            not np.isfinite(centers).all()
            or not np.isfinite(smoothed_angles).all()
            or not math.isfinite(crop_side)
            or crop_side <= 0
        ):
            return _safe_preparation(
                diagnostics, "INVALID_ROI_GEOMETRY", diagnostic_sink
            )
        rois = np.stack(
            [
                _crop_frame(
                    frame,
                    float(centers[index, 0]),
                    float(centers[index, 1]),
                    math.degrees(float(smoothed_angles[index])),
                    crop_side,
                )
                for index, frame in enumerate(decoded.frames)
            ]
        )
        landmarks = tuple(
            MouthLandmarksFrame(
                index,
                float(decoded.timestamps_ms[index]),
                tuple(map(tuple, coordinates)),
            )
            for index, coordinates in enumerate(points)
        )
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            source = build_visual_feature_sample(
                row["sample_id"],
                row["expected_label"],
                extract_temporal_features(landmarks),
                row["session_id"],
            )
        if not np.isfinite(source.features).all():
            return _safe_preparation(
                diagnostics, "NON_FINITE_FEATURES", diagnostic_sink
            )
        segmented = segment_visual_feature_sample(
            source, build_default_segmentation_config()
        )
        segment = segmented.segment
        indices = select_source_frame_indices(
            segment.start_frame, segment.end_frame_exclusive
        )
        tensor = prepare_input(rois, indices).numpy().copy()
        if tensor.shape != (1, 1, 29, 88, 88) or not np.isfinite(tensor).all():
            return _safe_preparation(diagnostics, "NON_FINITE_TENSOR", diagnostic_sink)
        query = HybridSample(
            row["sample_id"],
            row["session_id"],
            row["expected_label"],
            (
                LABELS.index(row["expected_label"])
                if row["sample_kind"] == "KNOWN"
                else -1
            ),
            np.zeros(1664, dtype=np.float32),
            segmented.sample.features,
        )
        diagnostics.update(
            {
                "segmentation_start_frame": segment.start_frame,
                "segmentation_end_frame_exclusive": segment.end_frame_exclusive,
                "segmentation_fallback": not segment.detected,
                "source_frame_count": count,
                "landmark_detection_count": int(mask.sum()),
                "sampled_frame_indices": indices.tolist(),
                "preprocessing_evidence": build_preprocessing_evidence(
                    points,
                    geometry,
                    rois,
                    source,
                    segmented.sample.features,
                    tensor,
                    mask,
                    indices,
                ),
                "preprocessing_status": "READY_FOR_INFERENCE",
                "preprocessing_stage": "READY_FOR_INFERENCE",
            }
        )
    except BaseException as error:
        diagnostic_sink(_technical_error(diagnostics, stage, error))
        raise
    diagnostic_sink(dict(diagnostics))
    return PreparedQuery(query, tensor, diagnostics)


def safe_reject_prediction(row: dict, diagnostics: dict) -> dict:
    if diagnostics["landmark_gap_action"] != SAFE_REJECT:
        raise ValueError("Abstention exige SAFE_REJECT explícito.")
    return {
        **diagnostics,
        "positive_predicted_label": None,
        "positive_predicted_label_index": None,
        "predicted_class_index": None,
        "rejection_score": None,
        "predicted_label": None,
        "predicted_label_index": None,
        "score": None,
        "positive_prediction_correct": None,
        "prediction_available": False,
        "decision": "REJECT",
        "emitted_label": None,
        "technical_reason": REASON,
        "model_inference_performed_for_query": False,
    }


def safe_reject_outcome(row: dict, prediction: dict) -> str:
    """Contrato futuro individual; não agrega ou calcula performance."""
    if (
        row["sample_kind"] not in ("KNOWN", "UNKNOWN")
        or prediction["decision"] != "REJECT"
        or prediction["prediction_available"] is not False
        or prediction["technical_reason"] != REASON
    ):
        raise ValueError("Contrato de abstention inválido.")
    return "KR" if row["sample_kind"] == "KNOWN" else "UR"


class HardenedRuntime:
    """Composição com sessões/templates R4; nenhum estado matemático é retunado."""

    def __init__(
        self, base_runtime, runtime_commit: str, diagnostic_sink: DiagnosticSink
    ):
        if not callable(diagnostic_sink):
            raise ValueError("Sink durável/emitido é obrigatório.")
        self.base = base_runtime
        self.runtime_commit = runtime_commit
        self.sink = diagnostic_sink

    def predict(self, row: dict, path: Path) -> dict:
        try:
            decoded = decode_query(path)
        except BaseException as error:
            diagnostics = {
                **_diagnostic_identity(row, self.runtime_commit, self.base is not None),
                **{
                    name: None
                    for name in (
                        "decoded_frame_count",
                        "declared_frame_count",
                        "landmark_detected_count",
                        "landmark_missing_count",
                        "landmark_missing_fraction",
                        "landmark_max_consecutive_missing",
                        "landmark_missing_indices",
                        "detection_valid_mask",
                        "landmark_gap_action",
                        "interpolation_count",
                    )
                },
                "violated_conditions": [],
                **getattr(error, "landmark_gap_decode_context", {}),
            }
            self.sink(_technical_error(diagnostics, "DECODE_AND_DETECT", error))
            raise
        prepared = prepare_decoded_query(
            row,
            decoded,
            diagnostic_sink=self.sink,
            runtime_commit=self.runtime_commit,
            models_loaded_process=self.base is not None,
        )
        if prepared.query is None:
            return safe_reject_prediction(row, prepared.diagnostics)
        diagnostics = {
            **prepared.diagnostics,
            "preprocessing_stage": "MODEL_INFERENCE",
            "model_inference_performed_for_query": True,
        }
        self.sink(dict(diagnostics))
        try:
            value = self._forward(row, prepared.query, prepared.tensor, diagnostics)
        except BaseException as error:
            self.sink(_technical_error(diagnostics, "MODEL_INFERENCE", error))
            raise
        self.sink({**diagnostics, "preprocessing_stage": "PREDICTION_READY"})
        return value

    def _forward(self, row, query, tensor, diagnostics):
        # Mesma ordem, dtypes e helpers de _R4Runtime.predict; fonte histórica intacta.
        output = self.base.encoder.run(None, {"roi_input": tensor})
        if len(output) != 1 or np.asarray(output[0]).shape != (1, 1664):
            raise ValueError("Saída do encoder ONNX inválida.")
        clip = validate_edge_embedding(np.asarray(output[0])[0])
        distances = class_minimum_dtw_distances(query, self.base.templates)
        feature = equal_energy_fusion(
            clip, normalized_reciprocal_evidence(distances), 1670
        )
        output = self.base.head.run(None, {"hybrid_features": feature[None, :]})
        if (
            len(output) != 1
            or np.asarray(output[0]).shape != (1, 6)
            or not np.isfinite(output[0]).all()
        ):
            raise ValueError("Logits ONNX inválidos.")
        index = int(np.argmax(output[0][0]))
        output = self.base.scorer.run(
            None,
            {
                "clip_embedding": clip[None, :],
                "predicted_label_index": np.array([index], dtype=np.int64),
            },
        )
        if len(output) != 1 or np.asarray(output[0]).shape != (1,):
            raise ValueError("Saída do scorer R4 ONNX inválida.")
        score = float(output[0][0])
        decision = decision_for_score(score)
        return {
            **diagnostics,
            "predicted_label": LABELS[index],
            "predicted_label_index": index,
            "score": score,
            "positive_predicted_label": LABELS[index],
            "positive_predicted_label_index": index,
            "predicted_class_index": index,
            "rejection_score": score,
            "decision": decision,
            "emitted_label": LABELS[index] if decision == "ACCEPT" else None,
            "positive_prediction_correct": (
                LABELS[index] == row["expected_label"]
                if row["sample_kind"] == "KNOWN"
                else None
            ),
            "prediction_available": True,
            "decode_status": "PASS",
            "roi_status": "PASS",
            "inference_status": "PASS",
            "segmentation_status": (
                "FALLBACK" if diagnostics["segmentation_fallback"] else "DETECTED"
            ),
            "dtw_distances": distances.tolist(),
            "clip_embedding_sha256": clip_embedding_sha256(clip),
        }
