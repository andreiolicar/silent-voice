"""ROI e embeddings SwinLip dos 54 UNKNOWN de desenvolvimento, sem scores."""

import json
import math
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch

from silent_voice.rejection.rejection_capture_snapshot import (
    validate_rejection_capture_snapshot,
)
from silent_voice.rejection.rejection_dataset import (
    NegativeCapturePlanItem,
    build_rejection_session_plan,
    negative_sample_path,
    validate_rejection_sample,
)
from silent_voice.rejection.rejection_protocol import (
    NEGATIVE_CATEGORIES,
    NEGATIVE_DEVELOPMENT_SESSIONS,
)
from silent_voice.vision.detector import MediaPipeMouthDetector
from silent_voice.vision.feature_sample import VisualFeatureSample
from silent_voice.vision.mouth_roi_dataset import (
    MouthRoiConfig,
    _crop_frame,
    _decode_and_detect,
    _interpolate_and_smooth,
    _max_missing_run,
    sha256_file,
)
from silent_voice.vision.swinlip_embedding_dataset import (
    CHECKPOINT_RELATIVE_PATH,
    SOURCE_RELATIVE_ROOT,
)
from silent_voice.vision.swinlip_frozen_encoder import (
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
    extract_embeddings,
    load_official_model,
    prepare_input,
    select_source_frame_indices,
)
from silent_voice.vision.visual_experiment_defaults import (
    build_default_segmentation_config,
)
from silent_voice.vision.visual_sample_segmentation import segment_visual_feature_sample

SNAPSHOT_RELATIVE_PATH = Path(
    "data/processed/evaluation/rejection_dev_capture_snapshot.json"
)
SNAPSHOT_SHA256 = "86427fb09df7981f997ef61c1c2a4ccd7142105bad3bcfea0f606f28c72abe82"
PROCESSED_SOURCE_ROOT = Path("data/processed/rejection")
RAW_SOURCE_ROOT = Path("data/raw/rejection")
CAPTURE_MANIFEST_PATH = Path("data/processed/evaluation/rejection_protocol.json")
ROI_ROOT = Path("data/processed/rejection_visual_mouth_roi")
ROI_MANIFEST_PATH = Path(
    "data/processed/evaluation/cycle_06_rejection_dev_mouth_roi_manifest.json"
)
EMBEDDING_ROOT = Path("data/processed/rejection_visual_swinlip_embeddings")
EMBEDDING_MANIFEST_PATH = Path(
    "data/processed/evaluation/cycle_06_rejection_dev_swinlip_embedding_manifest.json"
)
SWINLIP_CHECKPOINT_SHA256 = (
    "32f77c3ac7ff6cc4e970bf8dd53b1dade84d1905dd7b30d95ca105380b6cd6f5"
)
FORBIDDEN_SESSIONS = ("sessao_04", "rejeicao_heldout_01")
FORMAT_VERSION = 1


def negative_plan() -> tuple[NegativeCapturePlanItem, ...]:
    return tuple(
        item
        for session in NEGATIVE_DEVELOPMENT_SESSIONS
        for item in build_rejection_session_plan(session)
    )


def _video_path(raw_root: Path, item: NegativeCapturePlanItem) -> Path:
    return (
        Path(raw_root)
        / item.session_id
        / item.negative_category
        / f"{item.sample_id}.mp4"
    )


def select_authorized_negative_paths(
    processed_root: Path, raw_root: Path
) -> tuple[tuple[NegativeCapturePlanItem, Path, Path], ...]:
    """Filtra sessões por caminho e valida 54 pares antes de abrir bytes."""
    processed_root, raw_root = Path(processed_root), Path(raw_root)
    plan = negative_plan()
    expected_npz = {negative_sample_path(processed_root, item) for item in plan}
    expected_mp4 = {_video_path(raw_root, item) for item in plan}

    def selected(root: Path, suffix: str) -> set[Path]:
        candidates = root.rglob(f"*{suffix}")
        allowed = set()
        for path in candidates:
            parts = path.relative_to(root).parts
            if not parts or parts[0] not in NEGATIVE_DEVELOPMENT_SESSIONS:
                continue
            if any(forbidden in parts for forbidden in FORBIDDEN_SESSIONS):
                raise ValueError("Caminho proibido sob sessão autorizada.")
            allowed.add(path)
        return allowed

    observed_npz = selected(processed_root, ".npz")
    observed_mp4 = selected(raw_root, ".mp4")
    if len(plan) != 54 or observed_npz != expected_npz or observed_mp4 != expected_mp4:
        raise ValueError("Exigidos 54 pares NPZ/MP4 UNKNOWN autorizados.")
    return tuple(
        (item, negative_sample_path(processed_root, item), _video_path(raw_root, item))
        for item in plan
    )


def load_authorized_negative_records(
    processed_root: Path,
    raw_root: Path,
    reader: Callable[
        [Path, NegativeCapturePlanItem], object
    ] = validate_rejection_sample,
) -> tuple[object, ...]:
    """Só chama reader depois da validação completa de caminhos."""
    selected = select_authorized_negative_paths(processed_root, raw_root)
    return tuple(reader(npz_path, item) for item, npz_path, _ in selected)


def _load_unknown_source(
    path: Path, item: NegativeCapturePlanItem
) -> VisualFeatureSample:
    validate_rejection_sample(path, item)
    with np.load(path, allow_pickle=False) as data:
        features = np.asarray(data["features"]).copy()
        timestamps = np.asarray(data["timestamps_ms"]).copy()
    return VisualFeatureSample(
        item.sample_id, "UNKNOWN", features, timestamps, item.session_id
    )


def preflight_unknown_sources(repository_root: Path) -> dict:
    """Verifica snapshot, 54 fontes e hashes antes de vídeo/NPZ derivado."""
    root = Path(repository_root).resolve()
    processed = root / PROCESSED_SOURCE_ROOT
    raw = root / RAW_SOURCE_ROOT
    selected = select_authorized_negative_paths(processed, raw)
    snapshot_path = root / SNAPSHOT_RELATIVE_PATH
    if sha256_file(snapshot_path) != SNAPSHOT_SHA256:
        raise ValueError("SHA-256 do snapshot negativo divergiu.")
    snapshot = validate_rejection_capture_snapshot(
        snapshot_path, processed, raw, verify_videos=True
    )
    if (
        snapshot["total_sample_count"] != 54
        or len(snapshot["npz_sha256"]) != 54
        or len(snapshot["mp4_sha256"]) != 54
        or snapshot["per_session_counts"]
        != {session: 18 for session in NEGATIVE_DEVELOPMENT_SESSIONS}
        or snapshot["per_category_counts"]
        != {category: 9 for category in NEGATIVE_CATEGORIES}
    ):
        raise ValueError("Snapshot negativo não possui 54/18/9 amostras.")
    if (root / ROI_ROOT).exists() or (root / ROI_MANIFEST_PATH).exists():
        raise FileExistsError("ROI UNKNOWN derivado já existe.")
    return {"selected": selected, "snapshot": snapshot, "sample_count": 54}


@dataclass(frozen=True, slots=True)
class UnknownRoi:
    sample_id: str
    session_id: str
    negative_category: str
    oov_prompt: str
    source_video_sha256: str
    source_npz_sha256: str
    frame_count: int
    fps: float
    frame_indices: np.ndarray
    timestamps_ms: np.ndarray
    mouth_rois: np.ndarray
    detection_valid_mask: np.ndarray
    crop_centers_xy: np.ndarray
    crop_angles_deg: np.ndarray
    crop_side_px: float
    decoded_frame_count: int
    detected_landmark_frame_count: int
    missing_detection_count: int
    missing_detection_rate: float
    max_consecutive_missing: int


def validate_unknown_roi(roi: UnknownRoi, item: NegativeCapturePlanItem) -> None:
    count = roi.frame_count
    if (
        roi.sample_id != item.sample_id
        or roi.session_id != item.session_id
        or roi.negative_category != item.negative_category
        or roi.oov_prompt != item.oov_prompt
        or count <= 0
        or roi.decoded_frame_count != count
        or roi.mouth_rois.shape != (count, 96, 96)
        or roi.mouth_rois.dtype != np.uint8
        or not np.array_equal(roi.frame_indices, np.arange(count))
        or roi.timestamps_ms.shape != (count,)
        or not np.isfinite(roi.timestamps_ms).all()
        or (count > 1 and not np.all(np.diff(roi.timestamps_ms) > 0))
        or roi.detection_valid_mask.shape != (count,)
        or roi.detection_valid_mask.dtype != np.bool_
        or roi.crop_centers_xy.shape != (count, 2)
        or roi.crop_angles_deg.shape != (count,)
        or not np.isfinite(roi.crop_centers_xy).all()
        or not np.isfinite(roi.crop_angles_deg).all()
        or not math.isfinite(roi.crop_side_px)
        or roi.crop_side_px <= 0
        or not math.isfinite(roi.fps)
        or roi.fps <= 0
        or roi.detected_landmark_frame_count != int(roi.detection_valid_mask.sum())
        or roi.missing_detection_count != count - roi.detected_landmark_frame_count
        or not math.isclose(
            roi.missing_detection_rate, roi.missing_detection_count / count
        )
        or roi.missing_detection_rate > MouthRoiConfig().max_missing_rate
        or roi.max_consecutive_missing > MouthRoiConfig().max_consecutive_missing
        or roi.max_consecutive_missing != _max_missing_run(roi.detection_valid_mask)
        or len(roi.source_video_sha256) != 64
        or len(roi.source_npz_sha256) != 64
    ):
        raise ValueError(f"Contrato ROI UNKNOWN inválido: {item.sample_id}")


def derive_unknown_roi(
    item: NegativeCapturePlanItem,
    source: VisualFeatureSample,
    video_path: Path,
    video_sha256: str,
    npz_sha256: str,
    detector: object,
) -> UnknownRoi:
    """Reusa crop e política espacial congelados, sem known label."""
    if (
        source.sample_id != item.sample_id
        or source.session_id != item.session_id
        or source.label != "UNKNOWN"
    ):
        raise ValueError("NPZ UNKNOWN não corresponde ao plano.")
    config = MouthRoiConfig()
    frames, fps, geometry, mask, timestamps = _decode_and_detect(video_path, detector)
    count = len(frames)
    if source.frame_count != count:
        raise ValueError(f"Vídeo e NPZ divergem: {item.sample_id}")
    if not np.allclose(source.timestamps_ms, timestamps, rtol=0, atol=1.0):
        raise ValueError("Timestamps ROI/NPZ divergem.")
    missing = count - int(mask.sum())
    missing_rate = missing / count
    max_gap = _max_missing_run(mask)
    if (
        not np.any(mask)
        or missing_rate > config.max_missing_rate
        or max_gap > config.max_consecutive_missing
    ):
        raise ValueError(f"Detecção facial insuficiente: {item.sample_id}")
    detected = np.flatnonzero(mask)
    angles = geometry[:, 2].copy()
    angles[detected] = np.unwrap(angles[detected])
    centers = np.column_stack(
        [
            _interpolate_and_smooth(
                geometry[:, axis], detected, count, config.smoothing_window
            )
            for axis in (0, 1)
        ]
    )
    smoothed_angles = _interpolate_and_smooth(
        angles, detected, count, config.smoothing_window
    )
    crop_side = config.crop_scale * float(np.median(geometry[mask, 3]))
    rois = np.stack(
        [
            _crop_frame(
                frame,
                float(centers[index, 0]),
                float(centers[index, 1]),
                math.degrees(float(smoothed_angles[index])),
                crop_side,
            )
            for index, frame in enumerate(frames)
        ]
    )
    roi = UnknownRoi(
        item.sample_id,
        item.session_id,
        item.negative_category,
        item.oov_prompt,
        video_sha256,
        npz_sha256,
        count,
        fps,
        np.arange(count, dtype=np.int32),
        timestamps,
        rois,
        mask,
        centers,
        np.degrees(smoothed_angles),
        crop_side,
        count,
        count - missing,
        missing,
        missing_rate,
        max_gap,
    )
    validate_unknown_roi(roi, item)
    return roi


def _save_unknown_roi(roi: UnknownRoi, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"ROI UNKNOWN já existe: {path}")
    record = asdict(roi)
    record["preprocessing_config_json"] = json.dumps(asdict(MouthRoiConfig()))
    np.savez_compressed(
        path, **{key: np.asarray(value) for key, value in record.items()}
    )


def _load_unknown_roi(path: Path, item: NegativeCapturePlanItem) -> UnknownRoi:
    with np.load(path, allow_pickle=False) as data:
        values = {
            key: np.asarray(data[key]).copy() for key in UnknownRoi.__dataclass_fields__
        }
        for key in (
            "sample_id",
            "session_id",
            "negative_category",
            "oov_prompt",
            "source_video_sha256",
            "source_npz_sha256",
        ):
            values[key] = str(values[key].item())
        for key in (
            "frame_count",
            "decoded_frame_count",
            "detected_landmark_frame_count",
            "missing_detection_count",
            "max_consecutive_missing",
        ):
            values[key] = int(values[key].item())
        for key in ("fps", "crop_side_px", "missing_detection_rate"):
            values[key] = float(values[key].item())
        config = json.loads(str(data["preprocessing_config_json"].item()))
    if config != asdict(MouthRoiConfig()):
        raise ValueError("Configuração ROI UNKNOWN divergiu da congelada.")
    roi = UnknownRoi(**values)
    validate_unknown_roi(roi, item)
    return roi


def extract_unknown_rois(
    repository_root: Path,
    detector_factory: Callable[[], object] = MediaPipeMouthDetector,
) -> dict:
    """Deriva uma vez 54 ROIs UNKNOWN, sem executar classificador."""
    root = Path(repository_root).resolve()
    prepared = preflight_unknown_sources(root)
    snapshot = prepared["snapshot"]
    rois = []
    for item, npz_path, video_path in prepared["selected"]:
        source = _load_unknown_source(npz_path, item)
        detector = detector_factory()
        try:
            rois.append(
                derive_unknown_roi(
                    item,
                    source,
                    video_path,
                    snapshot["mp4_sha256"][item.sample_id],
                    snapshot["npz_sha256"][item.sample_id],
                    detector,
                )
            )
        finally:
            mesh = getattr(detector, "mesh", None)
            if mesh is not None and hasattr(mesh, "close"):
                mesh.close()
    entries = []
    for roi in rois:
        path = root / ROI_ROOT / f"{roi.sample_id}.npz"
        _save_unknown_roi(roi, path)
        entries.append(
            {
                "sample_id": roi.sample_id,
                "session_id": roi.session_id,
                "negative_category": roi.negative_category,
                "oov_prompt": roi.oov_prompt,
                "source_video_sha256": roi.source_video_sha256,
                "source_npz_sha256": roi.source_npz_sha256,
                "derived_roi_path": path.relative_to(root).as_posix(),
                "derived_roi_sha256": sha256_file(path),
                "frame_count": roi.frame_count,
                "decoded_frame_count": roi.decoded_frame_count,
                "detected_landmark_frame_count": roi.detected_landmark_frame_count,
                "missing_detection_count": roi.missing_detection_count,
                "missing_detection_rate": roi.missing_detection_rate,
                "max_consecutive_missing": roi.max_consecutive_missing,
                "crop_side_px": roi.crop_side_px,
            }
        )
    manifest = {
        "format_version": FORMAT_VERSION,
        "sample_count": 54,
        "session_ids": list(NEGATIVE_DEVELOPMENT_SESSIONS),
        "category_order": list(NEGATIVE_CATEGORIES),
        "per_session_counts": snapshot["per_session_counts"],
        "per_category_counts": snapshot["per_category_counts"],
        "source_snapshot_sha256": SNAPSHOT_SHA256,
        "recapture_audits": snapshot["recapture_audits"],
        "preprocessing_config": asdict(MouthRoiConfig()),
        "crop_method": "median_mouth_width_fixed_per_sample",
        "stabilization": "linear_gap_geometry_then_center_angle_moving_average",
        "missing_detection_handling": "interpolate_spatial_transform_only",
        "temporal_preservation": "all_decoded_real_frames",
        "roi_shape": [96, 96],
        "dtype": "uint8",
        "heldouts_used": False,
        "positive_classifier_executed": False,
        "rejection_scores_computed": False,
        "samples": entries,
    }
    path = root / ROI_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return validate_unknown_roi_dataset(root)


def validate_unknown_roi_dataset(repository_root: Path) -> dict:
    """Confere 54 ROIs derivadas, fontes e metadados sem scores."""
    root = Path(repository_root).resolve()
    manifest = json.loads((root / ROI_MANIFEST_PATH).read_text(encoding="utf-8"))
    selected = select_authorized_negative_paths(
        root / PROCESSED_SOURCE_ROOT, root / RAW_SOURCE_ROOT
    )
    entries = manifest.get("samples")
    if (
        manifest.get("format_version") != FORMAT_VERSION
        or manifest.get("sample_count") != 54
        or manifest.get("session_ids") != list(NEGATIVE_DEVELOPMENT_SESSIONS)
        or manifest.get("category_order") != list(NEGATIVE_CATEGORIES)
        or manifest.get("source_snapshot_sha256") != SNAPSHOT_SHA256
        or manifest.get("preprocessing_config") != asdict(MouthRoiConfig())
        or manifest.get("heldouts_used") is not False
        or manifest.get("positive_classifier_executed") is not False
        or manifest.get("rejection_scores_computed") is not False
        or not isinstance(entries, list)
        or len(entries) != 54
    ):
        raise ValueError("Manifesto ROI UNKNOWN inválido.")
    by_id = {entry["sample_id"]: entry for entry in entries}
    if len(by_id) != 54 or set(by_id) != {item.sample_id for item, _, _ in selected}:
        raise ValueError("IDs ROI UNKNOWN divergentes.")
    expected_paths = {
        root / ROI_ROOT / f"{item.sample_id}.npz" for item, _, _ in selected
    }
    if set((root / ROI_ROOT).rglob("*.npz")) != expected_paths:
        raise ValueError("Arquivos ROI UNKNOWN ausentes ou inesperados.")
    for item, npz_path, video_path in selected:
        entry = by_id[item.sample_id]
        roi_path = root / ROI_ROOT / f"{item.sample_id}.npz"
        roi = _load_unknown_roi(roi_path, item)
        if (
            entry["session_id"] != item.session_id
            or entry["negative_category"] != item.negative_category
            or entry["oov_prompt"] != item.oov_prompt
            or entry["derived_roi_sha256"] != sha256_file(roi_path)
            or roi.source_npz_sha256 != sha256_file(npz_path)
            or roi.source_video_sha256 != sha256_file(video_path)
        ):
            raise ValueError("Proveniência ROI UNKNOWN divergente.")
    return manifest


def prepare_unknown_segment(
    roi: object, source: VisualFeatureSample
) -> tuple[np.ndarray, object]:
    """Reusa segmentação e 29 frames reais; fallback é diagnóstico."""
    if (
        roi.sample_id != source.sample_id
        or roi.session_id != source.session_id
        or source.session_id not in NEGATIVE_DEVELOPMENT_SESSIONS
        or source.label != "UNKNOWN"
        or source.frame_count != roi.frame_count
        or not np.array_equal(roi.frame_indices, np.arange(roi.frame_count))
        or not np.allclose(roi.timestamps_ms, source.timestamps_ms, rtol=0, atol=1.0)
    ):
        raise ValueError("ROI/landmarks UNKNOWN não pareiam.")
    segment = segment_visual_feature_sample(
        source, build_default_segmentation_config()
    ).segment
    indices = select_source_frame_indices(
        segment.start_frame, segment.end_frame_exclusive
    )
    return indices, segment


def validate_unknown_embedding(record: dict) -> None:
    """Valida representações, nunca classifica ou interpreta categoria."""
    indices = record.get("selected_source_frame_indices")
    frame = record.get("frame_embeddings")
    clip = record.get("clip_embedding")
    if (
        record.get("session_id") not in NEGATIVE_DEVELOPMENT_SESSIONS
        or record.get("negative_category") not in NEGATIVE_CATEGORIES
        or not isinstance(record.get("sample_id"), str)
        or not isinstance(record.get("oov_prompt"), str)
        or not isinstance(indices, np.ndarray)
        or indices.shape != (29,)
        or not np.issubdtype(indices.dtype, np.integer)
        or np.any(np.diff(indices) < 0)
        or not isinstance(frame, np.ndarray)
        or frame.shape != (29, 512)
        or frame.dtype != np.float32
        or not np.isfinite(frame).all()
        or not isinstance(clip, np.ndarray)
        or clip.shape != (1664,)
        or clip.dtype != np.float32
        or not np.isfinite(clip).all()
        or any(
            len(record.get(key, "")) != 64
            for key in ("source_roi_sha256", "source_npz_sha256", "checkpoint_sha256")
        )
        or any(key in record for key in ("label", "logits", "score", "prediction"))
    ):
        raise ValueError("Embedding UNKNOWN inválido ou contém resultado de modelo.")


def save_unknown_embedding(record: dict, path: Path) -> None:
    validate_unknown_embedding(record)
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Embedding UNKNOWN já existe: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path, **{key: np.asarray(value) for key, value in record.items()}
    )


def preflight_unknown_embeddings(repository_root: Path) -> dict:
    root = Path(repository_root).resolve()
    if (root / EMBEDDING_ROOT).exists() or (root / EMBEDDING_MANIFEST_PATH).exists():
        raise FileExistsError("Embeddings UNKNOWN já existem.")
    roi_manifest = validate_unknown_roi_dataset(root)
    if sha256_file(root / CHECKPOINT_RELATIVE_PATH) != SWINLIP_CHECKPOINT_SHA256:
        raise ValueError("Checkpoint SwinLip congelado divergiu.")
    return {
        "sample_count": 54,
        "roi_manifest_sha256": sha256_file(root / ROI_MANIFEST_PATH),
        "roi_manifest": roi_manifest,
        "checkpoint_sha256": SWINLIP_CHECKPOINT_SHA256,
    }


def extract_unknown_embeddings(repository_root: Path) -> dict:
    """Extrai embeddings congelados sem executar a cabeça positiva."""
    root = Path(repository_root).resolve()
    preflight = preflight_unknown_embeddings(root)
    selected = select_authorized_negative_paths(
        root / PROCESSED_SOURCE_ROOT, root / RAW_SOURCE_ROOT
    )
    prepared = []
    for item, npz_path, _ in selected:
        source = _load_unknown_source(npz_path, item)
        roi_path = root / ROI_ROOT / f"{item.sample_id}.npz"
        roi = _load_unknown_roi(roi_path, item)
        indices, segment = prepare_unknown_segment(roi, source)
        prepared.append((item, source, roi, roi_path, indices, segment))
    model, _ = load_official_model(
        root / SOURCE_RELATIVE_ROOT, root / CHECKPOINT_RELATIVE_PATH
    )
    if model.training or any(
        parameter.requires_grad for parameter in model.parameters()
    ):
        raise ValueError("SwinLip não está congelado.")
    records = []
    elapsed = []
    segments = []
    for item, source, roi, roi_path, indices, segment in prepared:
        tensor = prepare_input(roi.mouth_rois, indices)
        start = time.perf_counter()
        frame, clip = extract_embeddings(model, tensor)
        elapsed.append((time.perf_counter() - start) * 1000.0)
        record = {
            "sample_id": item.sample_id,
            "session_id": item.session_id,
            "negative_category": item.negative_category,
            "oov_prompt": item.oov_prompt,
            "source_roi_sha256": sha256_file(roi_path),
            "source_npz_sha256": roi.source_npz_sha256,
            "selected_source_frame_indices": indices,
            "frame_embeddings": frame,
            "clip_embedding": clip,
            "checkpoint_sha256": SWINLIP_CHECKPOINT_SHA256,
            "source_commit": SOURCE_COMMIT,
        }
        validate_unknown_embedding(record)
        records.append(record)
        segments.append(
            {
                "sample_id": item.sample_id,
                "start_frame": segment.start_frame,
                "end_frame_exclusive": segment.end_frame_exclusive,
                "length": segment.end_frame_exclusive - segment.start_frame,
                "fallback": not segment.detected,
            }
        )
    clips = np.stack([record["clip_embedding"] for record in records])
    norms = np.linalg.norm(clips.astype(np.float64), axis=1)
    if not np.isfinite(norms).all() or not np.any(np.var(clips, axis=0)):
        raise ValueError("Embeddings UNKNOWN não finitos ou todos idênticos.")
    entries = []
    for record in records:
        path = root / EMBEDDING_ROOT / f"{record['sample_id']}.npz"
        save_unknown_embedding(record, path)
        entries.append(
            {
                "sample_id": record["sample_id"],
                "session_id": record["session_id"],
                "negative_category": record["negative_category"],
                "oov_prompt": record["oov_prompt"],
                "source_roi_sha256": record["source_roi_sha256"],
                "source_npz_sha256": record["source_npz_sha256"],
                "embedding_path": path.relative_to(root).as_posix(),
                "embedding_sha256": sha256_file(path),
                "selected_source_frame_indices": record[
                    "selected_source_frame_indices"
                ].tolist(),
            }
        )
    manifest = {
        "format_version": FORMAT_VERSION,
        "sample_count": 54,
        "session_ids": list(NEGATIVE_DEVELOPMENT_SESSIONS),
        "category_order": list(NEGATIVE_CATEGORIES),
        "per_session_counts": {
            session: 18 for session in NEGATIVE_DEVELOPMENT_SESSIONS
        },
        "per_category_counts": {category: 9 for category in NEGATIVE_CATEGORIES},
        "source_snapshot_sha256": SNAPSHOT_SHA256,
        "roi_manifest_sha256": preflight["roi_manifest_sha256"],
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "checkpoint_sha256": SWINLIP_CHECKPOINT_SHA256,
        "source_config_sha256": sha256_file(
            root / SOURCE_RELATIVE_ROOT / "configs/swinlip.json"
        ),
        "preprocessing": {
            "source_size": [96, 96],
            "center_crop_size": [88, 88],
            "scale_divisor": 255.0,
            "mean": 0.421,
            "std": 0.165,
            "target_frame_count": 29,
            "temporal_sampling": "rint(linspace(start,end_inclusive,29))",
        },
        "segmentation_config": asdict(build_default_segmentation_config()),
        "frame_embedding_shape": [29, 512],
        "clip_embedding_shape": [1664],
        "dtype": "float32",
        "benchmark": {
            "device": "cpu",
            "threads": torch.get_num_threads(),
            "sample_count": len(elapsed),
            "p50_ms": statistics.median(elapsed),
            "p95_ms": float(np.percentile(elapsed, 95)),
            "min_ms": min(elapsed),
            "max_ms": max(elapsed),
        },
        "structural_diagnostics": {
            "segment_min_frames": min(item["length"] for item in segments),
            "segment_mean_frames": statistics.mean(item["length"] for item in segments),
            "segment_max_frames": max(item["length"] for item in segments),
            "segmentation_fallback_count": sum(item["fallback"] for item in segments),
            "clip_norm_min": float(norms.min()),
            "clip_norm_mean": float(norms.mean()),
            "clip_norm_max": float(norms.max()),
            "clip_global_variance_nonzero": True,
            "clips_all_distinct": len({clip.tobytes() for clip in clips}) == 54,
        },
        "segments": segments,
        "heldouts_used": False,
        "positive_classifier_executed": False,
        "rejection_scores_computed": False,
        "samples": entries,
    }
    path = root / EMBEDDING_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return validate_unknown_embedding_dataset(root)


def validate_unknown_embedding_dataset(repository_root: Path) -> dict:
    root = Path(repository_root).resolve()
    roi_manifest = validate_unknown_roi_dataset(root)
    manifest_path = root / EMBEDDING_MANIFEST_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("samples")
    if (
        manifest.get("format_version") != FORMAT_VERSION
        or manifest.get("sample_count") != 54
        or manifest.get("session_ids") != list(NEGATIVE_DEVELOPMENT_SESSIONS)
        or manifest.get("category_order") != list(NEGATIVE_CATEGORIES)
        or manifest.get("source_snapshot_sha256") != SNAPSHOT_SHA256
        or manifest.get("roi_manifest_sha256") != sha256_file(root / ROI_MANIFEST_PATH)
        or manifest.get("checkpoint_sha256") != SWINLIP_CHECKPOINT_SHA256
        or manifest.get("heldouts_used") is not False
        or manifest.get("positive_classifier_executed") is not False
        or manifest.get("rejection_scores_computed") is not False
        or manifest.get("frame_embedding_shape") != [29, 512]
        or manifest.get("clip_embedding_shape") != [1664]
        or manifest.get("dtype") != "float32"
        or not isinstance(entries, list)
        or len(entries) != 54
    ):
        raise ValueError("Manifesto de embedding UNKNOWN inválido.")
    by_id = {entry["sample_id"]: entry for entry in entries}
    roi_by_id = {entry["sample_id"]: entry for entry in roi_manifest["samples"]}
    if len(by_id) != 54 or set(by_id) != set(roi_by_id):
        raise ValueError("ROI e embeddings UNKNOWN não pareiam 1:1.")
    expected = {root / EMBEDDING_ROOT / f"{sample_id}.npz" for sample_id in by_id}
    if set((root / EMBEDDING_ROOT).rglob("*.npz")) != expected:
        raise ValueError("Arquivos de embedding UNKNOWN ausentes ou inesperados.")
    for sample_id, entry in by_id.items():
        path = root / EMBEDDING_ROOT / f"{sample_id}.npz"
        roi = roi_by_id[sample_id]
        if (
            entry["negative_category"] != roi["negative_category"]
            or entry["oov_prompt"] != roi["oov_prompt"]
            or entry["source_roi_sha256"]
            != sha256_file(root / ROI_ROOT / f"{sample_id}.npz")
            or entry["embedding_sha256"] != sha256_file(path)
        ):
            raise ValueError("Proveniência de embedding UNKNOWN divergente.")
        with np.load(path, allow_pickle=False) as data:
            record = {key: np.asarray(data[key]).copy() for key in data.files}
            for key in (
                "sample_id",
                "session_id",
                "negative_category",
                "oov_prompt",
                "source_roi_sha256",
                "source_npz_sha256",
                "checkpoint_sha256",
                "source_commit",
            ):
                record[key] = str(record[key].item())
        validate_unknown_embedding(record)
        if (
            record["sample_id"] != sample_id
            or record["source_roi_sha256"] != entry["source_roi_sha256"]
        ):
            raise ValueError("Embedding UNKNOWN não corresponde ao manifesto.")
    return manifest


def run_unknown_visual_pipeline(repository_root: Path) -> dict:
    """Executa ROI e embeddings uma vez após commit limpo."""
    root = Path(repository_root).resolve()
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError("Worktree versionável deve estar limpo antes da extração.")
    preflight_unknown_sources(root)
    roi = extract_unknown_rois(root)
    embeddings = extract_unknown_embeddings(root)
    return {"roi": roi, "embeddings": embeddings}
