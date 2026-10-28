"""Avaliação única do novo held-out visual com pipeline Edge congelado."""

import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.dataset.capture_cycle_06_heldout_raw import load_capture_plan
from scripts.dataset.qc_cycle_06_new_heldout import (
    dataset_fingerprint,
    validate_inventory,
)
from silent_voice.edge.preheldout_freeze import (
    load_frozen_edge_pipeline,
    validate_edge_config,
    validate_freeze_manifest,
)
from silent_voice.rejection.rejection_metrics import calculate_rejection_metrics
from silent_voice.vision.detector import MediaPipeMouthDetector
from silent_voice.vision.feature_sample_builder import build_visual_feature_sample
from silent_voice.vision.hybrid_features import HybridSample
from silent_voice.vision.mouth_roi_dataset import (
    MouthRoiConfig,
    _crop_frame,
    _decode_and_detect,
    _interpolate_and_smooth,
    _max_missing_run,
    sha256_file,
)
from silent_voice.vision.positive_classifier_final import (
    CHECKPOINT_RELATIVE_PATH,
    CONFIG_RELATIVE_PATH,
    load_frozen_positive_classifier,
)
from silent_voice.vision.swinlip_frozen_encoder import (
    prepare_input,
    select_source_frame_indices,
)
from silent_voice.vision.temporal_features import extract_temporal_features
from silent_voice.vision.visual_experiment_defaults import (
    build_default_segmentation_config,
)
from silent_voice.vision.visual_sample_segmentation import segment_visual_feature_sample
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


LABELS = tuple(DEFAULT_VISUAL_LABELS)
SESSIONS = ("cycle_06_heldout_session_01", "cycle_06_heldout_session_02")
CATEGORIES = (
    "BOCA_PARADA",
    "SORRISO",
    "ABRE_FECHA",
    "MOV_CABECA",
    "MOV_BOCA_ALEATORIO",
    "FALA_FORA_VOCAB",
)
THRESHOLD = 0.6401554942131042
PLAN = Path("docs/cycles/cycle_06_new_heldout_capture_plan.json")
DATASET_MANIFEST = Path(
    "data/processed/evaluation/cycle_06_new_heldout_dataset_manifest.json"
)
EDGE_CONFIG = Path(
    "data/processed/evaluation/cycle_06_edge_preheldout_final_config.json"
)
FREEZE_MANIFEST = Path(
    "data/processed/evaluation/cycle_06_preheldout_freeze_manifest.json"
)
OUTPUT = Path("data/processed/evaluation/cycle_06_final_heldout_evaluation.json")
ATTEMPT = Path("data/processed/evaluation/cycle_06_final_heldout_attempt.json")
ENCODER_FILE = Path(
    "data/processed/models/edge/cycle_06_swinlip_clip_encoder_fp16.onnx"
)
CLASSIFIER_FILE = Path("data/processed/models/edge/cycle_06_positive_head_fp32.onnx")
CENTROIDS_FILE = Path(
    "data/processed/models/edge/cycle_06_onnx_fp16_rejection_clip_centroids.npz"
)
EXPECTED_HASHES = {
    "capture_plan": "cd0d54815acd4b1a67d3b0bb483bc80a4165c990656783be0fa99aeff3889cd7",
    "dataset_manifest": (
        "79c4bb1e9ed66ff44a321f467963577ccc922c2735a3f66612b540fbc3f542e4"
    ),
    "edge_config": "a761de851e7dc22ed8974dbd3dc98e23963d384057488bdfe9aae0ef406eb4d4",
    "freeze_manifest": (
        "41cf1f308a1c153bfc0f533c70676309139d63531cce9ce31363c74643e611bd"
    ),
    "encoder": "ff81172639263a6a74975e7147d63e62af944b947e48f53fba6980af732c91a7",
    "classifier": "eb299d65e4f2b9a15108f79b8044355068911d2180161d46806a9c0269fa9261",
    "centroids": "d7cece625425d09cb313830e0491121b42d116f409bd400bf9c18f7ea53e0a61",
}
DATASET_FINGERPRINT = "22134fce454ac873f36ca3b5c46659621d48c9663c17612f606d345d5b78f39c"
PIPELINE_FINGERPRINT = (
    "e8394f470520f61d096bc0f1a4f5997f5ae5692af412707c4905519ae602c48b"
)
IMPLEMENTATION_FILES = {
    "runtime_implementation_sha256": "src/silent_voice/edge/preheldout_freeze.py",
    "roi_implementation_sha256": "src/silent_voice/vision/mouth_roi_dataset.py",
    "segmentation_implementation_sha256": (
        "src/silent_voice/vision/visual_sample_segmentation.py"
    ),
    "preprocessing_implementation_sha256": (
        "src/silent_voice/vision/swinlip_frozen_encoder.py"
    ),
    "distance_implementation_sha256": (
        "src/silent_voice/vision/strong_dtw_distance.py"
    ),
    "evidence_implementation_sha256": "src/silent_voice/vision/hybrid_features.py",
    "centroid_and_score_implementation_sha256": (
        "src/silent_voice/rejection/hybrid_rejection_final.py"
    ),
    "threshold_selection_implementation_sha256": (
        "src/silent_voice/rejection/hybrid_rejection_scores.py"
    ),
}


def check_hashes(records: dict[str, tuple[Path, str]]) -> dict[str, str]:
    """Confere os hashes esperados sem abrir caminhos derivados dos dados."""
    observed = {}
    for name, (path, expected) in records.items():
        digest = sha256_file(Path(path))
        if digest != expected:
            raise ValueError(f"SHA-256 divergente: {name}")
        observed[name] = digest
    return observed


def validate_dataset_manifest(plan: dict, manifest: dict) -> tuple[dict, ...]:
    """Exige os 72 registros exatos, na ordem congelada do plano."""
    expected = [row for session in plan["sessions"] for row in session["schedule"]]
    samples = manifest.get("samples", [])
    if (
        manifest.get("state") != "CYCLE_06_NEW_HELDOUT_DATASET_FROZEN"
        or manifest.get("heldout_technical_qc") != "PASS"
        or manifest.get("total_sample_count") != 72
        or len(samples) != 72
        or len(expected) != 72
    ):
        raise ValueError("Manifesto exige 72 amostras com QC PASS.")
    if len({item.get("sample_id") for item in samples}) != 72:
        raise ValueError("Sample ID duplicado no manifesto.")
    for source, item in zip(expected, samples, strict=True):
        if (
            item.get("sample_id") != source["sample_id"]
            or item.get("session_id") != source["session_id"]
            or item.get("sample_kind") != source["sample_kind"]
            or item.get("expected_label") != source["expected_label"]
            or item.get("negative_category") != source["negative_category"]
            or item.get("relative_path") != source["raw_video_path"]
            or item.get("technical_qc_decision") != "PASS"
            or not isinstance(item.get("byte_size"), int)
            or item["byte_size"] <= 0
            or not isinstance(item.get("file_sha256"), str)
            or len(item["file_sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in item["file_sha256"])
        ):
            raise ValueError("Manifesto não pareado ao plano ou path não autorizado.")
    if dataset_fingerprint(samples) != manifest.get(
        "heldout_dataset_fingerprint_sha256"
    ):
        raise ValueError("Fingerprint do dataset não corresponde às 72 amostras.")
    return tuple(samples)


def ensure_one_shot(output: Path, attempt: Path) -> None:
    """Qualquer resultado ou tentativa anterior impede execução automática."""
    if Path(output).exists() or Path(attempt).exists():
        raise FileExistsError("Avaliação ou tentativa held-out já existe.")


def wilson_interval(correct: int, total: int) -> list[float]:
    """Intervalo bilateral Wilson 95% para proporção binomial."""
    if not 0 <= correct <= total or total <= 0:
        raise ValueError("Contagem inválida para Wilson.")
    z = 1.959963984540054
    fraction = correct / total
    denominator = 1 + z * z / total
    center = (fraction + z * z / (2 * total)) / denominator
    radius = (
        z
        / denominator
        * math.sqrt(fraction * (1 - fraction) / total + z * z / (4 * total * total))
    )
    return [max(0.0, center - radius), min(1.0, center + radius)]


def _validate_predictions(rows: list[dict], plan: dict) -> None:
    expected = [item for session in plan["sessions"] for item in session["schedule"]]
    if len(rows) != 72 or len(expected) != 72:
        raise ValueError("Resultado deve conter as 72 amostras, sem exclusão.")
    if len({row.get("sample_id") for row in rows}) != 72:
        raise ValueError("Resultado não pareado: sample_id duplicado.")
    for row, source in zip(rows, expected, strict=True):
        if any(
            row.get(field) != source[field]
            for field in (
                "sample_id",
                "session_id",
                "sample_kind",
                "expected_label",
                "negative_category",
                "oov_prompt",
            )
        ):
            raise ValueError("Resultado não pareado com o plano congelado.")
        label = row.get("predicted_label")
        score = row.get("clip_class_cosine")
        logits = row.get("logits")
        if (
            label not in LABELS
            or row.get("predicted_label_index") != LABELS.index(label)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or row.get("threshold") != THRESHOLD
            or row.get("decision") != ("ACCEPT" if score >= THRESHOLD else "REJECT")
            or row.get("emitted_label") != (label if score >= THRESHOLD else None)
            or not isinstance(logits, list)
            or len(logits) != 6
            or not all(
                isinstance(value, (int, float)) and math.isfinite(value)
                for value in logits
            )
            or type(row.get("segmentation_fallback")) is not bool
            or row.get("inference_success") is not True
        ):
            raise ValueError("Resultado individual inválido ou decisão alterada.")


def _rejection_counts(rows: list[dict]) -> dict:
    accepted = tuple(row["decision"] == "ACCEPT" for row in rows)
    return calculate_rejection_metrics(tuple(rows), accepted)


def calculate_metrics(rows: list[dict], plan: dict) -> dict:
    """Calcula somente métricas pré-registradas, sem seleção de amostras."""
    _validate_predictions(rows, plan)
    counts = _rejection_counts(rows)
    kca = counts["KNOWN_CORRECT_ACCEPT"]
    kwa = counts["KNOWN_WRONG_ACCEPT"]
    kr = counts["KNOWN_REJECT"]
    ur = counts["UNKNOWN_REJECT"]
    ufa = counts["UNKNOWN_FALSE_ACCEPT"]
    if (kca + kwa + kr, ur + ufa) != (36, 36):
        raise ValueError("Identidades KNOWN/UNKNOWN inválidas.")
    known = [row for row in rows if row["sample_kind"] == "KNOWN"]
    unknown = [row for row in rows if row["sample_kind"] == "UNKNOWN"]
    closed = sum(row["predicted_label"] == row["expected_label"] for row in known)
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for row in known:
        matrix[LABELS.index(row["expected_label"])][row["predicted_label_index"]] += 1
    by_class = []
    for label in LABELS:
        group = [row for row in known if row["expected_label"] == label]
        correct = sum(row["predicted_label"] == label for row in group)
        correct_accept = sum(
            row["predicted_label"] == label and row["decision"] == "ACCEPT"
            for row in group
        )
        wrong_accept = sum(
            row["predicted_label"] != label and row["decision"] == "ACCEPT"
            for row in group
        )
        rejected = sum(row["decision"] == "REJECT" for row in group)
        if len(group) != 6 or correct_accept + wrong_accept + rejected != 6:
            raise ValueError("Classe KNOWN não possui seis decisões válidas.")
        by_class.append(
            {
                "label": label,
                "label_index": LABELS.index(label),
                "total": 6,
                "closed_set_correct": correct,
                "closed_set_wrong": 6 - correct,
                "correct_accept": correct_accept,
                "wrong_accept": wrong_accept,
                "rejected": rejected,
                "correct_accept_rate": correct_accept / 6,
            }
        )
    by_category = []
    for category in CATEGORIES:
        group = [row for row in unknown if row["negative_category"] == category]
        rejected = sum(row["decision"] == "REJECT" for row in group)
        false_accepts = [
            {"sample_id": row["sample_id"], "predicted_label": row["predicted_label"]}
            for row in group
            if row["decision"] == "ACCEPT"
        ]
        if len(group) != 6:
            raise ValueError("Categoria UNKNOWN não possui seis amostras.")
        by_category.append(
            {
                "category": category,
                "total": 6,
                "rejected": rejected,
                "false_accepted": len(false_accepts),
                "rejection_rate": rejected / 6,
                "false_accepts": false_accepts,
            }
        )
    oov = [
        {
            "sample_id": row["sample_id"],
            "session_id": row["session_id"],
            "prompt": row["oov_prompt"],
            "decision": row["decision"],
            "predicted_label": row["predicted_label"],
            "emitted_label": row["emitted_label"],
        }
        for row in unknown
        if row["negative_category"] == "FALA_FORA_VOCAB"
    ]
    if len(oov) != 6 or len({row["prompt"] for row in oov}) != 6:
        raise ValueError("Prompts OOV incompletos ou duplicados.")
    sessions = []
    for session_id in SESSIONS:
        group = [row for row in rows if row["session_id"] == session_id]
        detail = _rejection_counts(group)
        if len(group) != 36 or (detail["known_count"], detail["unknown_count"]) != (
            18,
            18,
        ):
            raise ValueError("Sessão held-out incompleta.")
        sessions.append(
            {
                "session_id": session_id,
                "known_closed_set_correct": sum(
                    row["predicted_label"] == row["expected_label"]
                    for row in group
                    if row["sample_kind"] == "KNOWN"
                ),
                "known_closed_set_accuracy": detail["known_closed_set_accuracy"],
                "known_correct_accept": detail["KNOWN_CORRECT_ACCEPT"],
                "known_wrong_accept": detail["KNOWN_WRONG_ACCEPT"],
                "known_reject": detail["KNOWN_REJECT"],
                "known_correct_accept_rate": detail["known_correct_accept_rate"],
                "unknown_reject": detail["UNKNOWN_REJECT"],
                "unknown_false_accept": detail["UNKNOWN_FALSE_ACCEPT"],
                "unknown_rejection_rate": detail["unknown_rejection_rate"],
                "balanced_score": detail["rejection_balanced_score"],
                "segmentation_fallback": sum(
                    row["segmentation_fallback"] for row in group
                ),
            }
        )
    safe = kca + ur
    return {
        "known": {
            "total": 36,
            "closed_set_correct": closed,
            "closed_set_wrong": 36 - closed,
            "closed_set_accuracy": closed / 36,
            "correct_accept": kca,
            "wrong_accept": kwa,
            "reject": kr,
            "correct_accept_rate": kca / 36,
            "coverage": (kca + kwa) / 36,
            "accepted_accuracy": kca / (kca + kwa) if kca + kwa else None,
        },
        "unknown": {
            "total": 36,
            "reject": ur,
            "false_accept": ufa,
            "rejection_rate": ur / 36,
            "false_accept_rate": ufa / 36,
        },
        "primary_balanced_score": counts["rejection_balanced_score"],
        "safe_decision": {"correct": safe, "total": 72, "accuracy": safe / 72},
        "wilson_95": {
            "known_closed_set_accuracy": wilson_interval(closed, 36),
            "known_correct_accept_rate": wilson_interval(kca, 36),
            "unknown_rejection_rate": wilson_interval(ur, 36),
            "safe_decision_accuracy": wilson_interval(safe, 72),
        },
        "labels": list(LABELS),
        "confusion_matrix": matrix,
        "known_by_class": by_class,
        "known_misclassified_or_rejected": [
            {
                "sample_id": row["sample_id"],
                "expected_label": row["expected_label"],
                "predicted_label": row["predicted_label"],
                "decision": row["decision"],
            }
            for row in known
            if row["predicted_label"] != row["expected_label"]
            or row["decision"] == "REJECT"
        ],
        "unknown_by_category": by_category,
        "oov_prompts": oov,
        "by_session": sessions,
        "segmentation_fallback": {
            "total": sum(row["segmentation_fallback"] for row in rows),
            "known": sum(row["segmentation_fallback"] for row in known),
            "unknown": sum(row["segmentation_fallback"] for row in unknown),
            "by_session": {
                session_id: sum(
                    row["segmentation_fallback"]
                    for row in rows
                    if row["session_id"] == session_id
                )
                for session_id in SESSIONS
            },
        },
    }


def serialize_result(payload: dict) -> bytes:
    return (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def _canonical_plan_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in raw:
        raise ValueError("Quebra de linha inesperada no plano congelado.")
    return hashlib.sha256(raw).hexdigest()


def _frozen_implementation_hashes(root: Path, config: dict) -> dict[str, str]:
    recorded = {
        "runtime_implementation_sha256": config["runtime_implementation_sha256"],
        "roi_implementation_sha256": config["preprocessing"]["roi_definition"][
            "implementation_sha256"
        ],
        "segmentation_implementation_sha256": config["preprocessing"][
            "segmentation_implementation_sha256"
        ],
        "preprocessing_implementation_sha256": config["preprocessing"][
            "preprocessing_implementation_sha256"
        ],
        "distance_implementation_sha256": config["dtw"][
            "distance_implementation_sha256"
        ],
        "evidence_implementation_sha256": config["dtw"][
            "evidence_implementation_sha256"
        ],
        "centroid_and_score_implementation_sha256": config["rejection"][
            "centroid_and_score_implementation_sha256"
        ],
        "threshold_selection_implementation_sha256": config["rejection"][
            "threshold_selection_implementation_sha256"
        ],
    }
    return check_hashes(
        {
            name: (root / IMPLEMENTATION_FILES[name], expected)
            for name, expected in recorded.items()
        }
    )


def preflight(root: Path, require_clean_worktree: bool = True) -> dict:
    """Valida artefatos, 72 hashes e worktree sem inferência semântica."""
    root = Path(root).resolve()
    ensure_one_shot(root / OUTPUT, root / ATTEMPT)
    if (root / (str(OUTPUT) + ".pending")).exists():
        raise FileExistsError("Resultado parcial da avaliação anterior existe.")
    if (
        require_clean_worktree
        and subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True
        ).strip()
    ):
        raise ValueError("Worktree versionável deve estar limpo antes do held-out.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    if _canonical_plan_sha256(root / PLAN) != EXPECTED_HASHES["capture_plan"]:
        raise ValueError("SHA-256 canônico do plano de captura divergiu.")
    hashes = check_hashes(
        {
            "dataset_manifest": (
                root / DATASET_MANIFEST,
                EXPECTED_HASHES["dataset_manifest"],
            ),
            "edge_config": (root / EDGE_CONFIG, EXPECTED_HASHES["edge_config"]),
            "freeze_manifest": (
                root / FREEZE_MANIFEST,
                EXPECTED_HASHES["freeze_manifest"],
            ),
            "encoder": (
                root / ENCODER_FILE,
                EXPECTED_HASHES["encoder"],
            ),
            "classifier": (
                root / CLASSIFIER_FILE,
                EXPECTED_HASHES["classifier"],
            ),
            "centroids": (
                root / CENTROIDS_FILE,
                EXPECTED_HASHES["centroids"],
            ),
        }
    )
    hashes["capture_plan"] = EXPECTED_HASHES["capture_plan"]
    plan = load_capture_plan(root / PLAN)
    manifest = json.loads((root / DATASET_MANIFEST).read_text(encoding="utf-8"))
    samples = validate_dataset_manifest(plan, manifest)
    if (
        manifest.get("capture_plan_sha256") != EXPECTED_HASHES["capture_plan"]
        or manifest["heldout_dataset_fingerprint_sha256"] != DATASET_FINGERPRINT
        or manifest.get("no_semantic_inference") is not True
        or manifest.get("models_loaded") is not False
        or manifest.get("old_heldouts_opened") is not False
    ):
        raise ValueError("Estado/fingerprint de captura congelada inválido.")
    config = json.loads((root / EDGE_CONFIG).read_text(encoding="utf-8"))
    freeze = json.loads((root / FREEZE_MANIFEST).read_text(encoding="utf-8"))
    if (
        config.get("pipeline_fingerprint_sha256") != PIPELINE_FINGERPRINT
        or config.get("cycle_06_heldout_evaluation_candidate") != "ONNX_FP16"
        or config.get("final_android_runtime") != "UNFROZEN"
        or config.get("rejection", {}).get("threshold") != THRESHOLD
    ):
        raise ValueError("Configuração Edge não corresponde ao freeze pré-held-out.")
    validate_edge_config(root, config)
    validate_freeze_manifest(root, freeze, config)
    implementation_hashes = _frozen_implementation_hashes(root, config)
    rows = tuple(row for session in plan["sessions"] for row in session["schedule"])
    paths = validate_inventory(rows, root)
    for item, path in zip(samples, paths, strict=True):
        if (
            path.stat().st_size != item["byte_size"]
            or sha256_file(path) != item["file_sha256"]
        ):
            raise ValueError(f"Hash/tamanho do held-out divergiu: {item['sample_id']}")
    hashes["heldout_dataset_fingerprint"] = DATASET_FINGERPRINT
    hashes["pipeline_fingerprint"] = PIPELINE_FINGERPRINT
    return {
        "root": root,
        "commit": commit,
        "plan": plan,
        "dataset_manifest": manifest,
        "config": config,
        "sample_paths": paths,
        "hashes": hashes,
        "implementation_hashes": implementation_hashes,
        "preflight_sample_count": len(samples),
        "semantic_predictions": 0,
        "old_heldouts_opened": False,
    }


class _RecordingDetector:
    """Reusa um único passe MediaPipe para ROI e features congeladas."""

    def __init__(self) -> None:
        self.detector = MediaPipeMouthDetector()
        self.landmarks = []

    def extract(self, frame: np.ndarray, index: int, timestamp_ms: float):
        value = self.detector.extract(frame, index, timestamp_ms)
        if value is not None:
            self.landmarks.append(value)
        return value

    def close(self) -> None:
        self.detector.mesh.close()


def prepare_query(row: dict, path: Path) -> tuple[HybridSample, np.ndarray, dict]:
    """Aplica ROI, features, segmentação e sampling congelados em memória."""
    detector = _RecordingDetector()
    try:
        frames, _, geometry, mask, _ = _decode_and_detect(path, detector)
    finally:
        detector.close()
    count = len(frames)
    config = MouthRoiConfig()
    missing = count - int(mask.sum())
    if count < 3 or missing or _max_missing_run(mask) > config.max_consecutive_missing:
        raise ValueError(f"Landmarks não pareiam todos os frames: {row['sample_id']}")
    detected_indices = np.flatnonzero(mask)
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
    source = build_visual_feature_sample(
        row["sample_id"],
        row["expected_label"],
        extract_temporal_features(tuple(detector.landmarks)),
        row["session_id"],
    )
    if source.frame_count != count:
        raise ValueError("Features e ROI não pareiam na contagem de frames.")
    segmented = segment_visual_feature_sample(
        source, build_default_segmentation_config()
    )
    segment = segmented.segment
    indices = select_source_frame_indices(
        segment.start_frame, segment.end_frame_exclusive
    )
    tensor = prepare_input(rois, indices).numpy().copy()
    if tensor.shape != (1, 1, 29, 88, 88) or not np.isfinite(tensor).all():
        raise ValueError("Tensor ONNX congelado inválido.")
    query = HybridSample(
        row["sample_id"],
        row["session_id"],
        row["expected_label"],
        LABELS.index(row["expected_label"]) if row["sample_kind"] == "KNOWN" else -1,
        np.zeros(1664, dtype=np.float32),
        segmented.sample.features,
    )
    diagnostics = {
        "segmentation_start_frame": segment.start_frame,
        "segmentation_end_frame_exclusive": segment.end_frame_exclusive,
        "segmentation_fallback": not segment.detected,
        "source_frame_count": count,
        "landmark_detection_count": count - missing,
        "sampled_frame_indices": indices.tolist(),
    }
    return query, tensor, diagnostics


def _write_attempt(path: Path, payload: dict) -> None:
    """Atualiza o registro de tentativa sem expor previsões no console."""
    data = serialize_result(payload)
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(data)
        return
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("xb") as stream:
        stream.write(data)
    os.replace(temporary, path)


def run_one_shot(prepared: dict) -> dict:
    """Executa uma vez, preservando auditoria parcial após qualquer falha."""
    root = prepared["root"]
    output = root / OUTPUT
    attempt_path = root / ATTEMPT
    ensure_one_shot(output, attempt_path)
    positive_config = root / CONFIG_RELATIVE_PATH
    positive_checkpoint = root / CHECKPOINT_RELATIVE_PATH
    check_hashes(
        {
            "positive_config": (
                positive_config,
                prepared["config"]["classifier"]["source_config_sha256"],
            ),
            "positive_checkpoint": (
                positive_checkpoint,
                prepared["config"]["classifier"]["source_checkpoint_sha256"],
            ),
        }
    )
    templates = load_frozen_positive_classifier(
        positive_checkpoint, positive_config
    ).templates
    pipeline = load_frozen_edge_pipeline(root, root / EDGE_CONFIG, templates)
    plan_rows = [
        row for session in prepared["plan"]["sessions"] for row in session["schedule"]
    ]
    attempt = {
        "state": "CYCLE_06_NEW_HELDOUT_CONSUMED",
        "phase": "SEMANTIC_PROCESSING_STARTED",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_commit": prepared["commit"],
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
        "heldout_dataset_fingerprint_sha256": DATASET_FINGERPRINT,
        "prediction_count": 0,
        "partial_results": [],
    }
    _write_attempt(attempt_path, attempt)
    predictions = []
    try:
        ready = [
            prepare_query(row, path)
            for row, path in zip(plan_rows, prepared["sample_paths"], strict=True)
        ]
        if len(ready) != 72:
            raise ValueError("Pré-processamento não produziu 72 queries.")
        attempt["phase"] = "INFERENCE_STARTED"
        _write_attempt(attempt_path, attempt)
        for row, (query, tensor, diagnostics) in zip(plan_rows, ready, strict=True):
            prediction = pipeline.predict(query, tensor)
            if prediction["pipeline_fingerprint_sha256"] != PIPELINE_FINGERPRINT:
                raise ValueError("Fingerprint divergiu durante inferência.")
            record = {
                "sample_id": row["sample_id"],
                "session_id": row["session_id"],
                "sample_kind": row["sample_kind"],
                "expected_label": row["expected_label"],
                "negative_category": row["negative_category"],
                "oov_prompt": row["oov_prompt"],
                **diagnostics,
                "clip_embedding_finite": True,
                "predicted_label": prediction["predicted_label"],
                "predicted_label_index": prediction["predicted_label_index"],
                "logits": prediction["logits"],
                "clip_class_cosine": prediction["clip_class_cosine"],
                "threshold": prediction["threshold"],
                "decision": prediction["decision"],
                "emitted_label": prediction["accepted_label"],
                "dtw_distances": prediction["dtw_distances"],
                "clip_embedding_sha256": prediction["clip_embedding_sha256"],
                "inference_success": True,
            }
            predictions.append(record)
            attempt["prediction_count"] = len(predictions)
            attempt["partial_results"] = predictions
            _write_attempt(attempt_path, attempt)
        metrics = calculate_metrics(predictions, prepared["plan"])
        result = {
            "format_version": 1,
            "state": "CYCLE_06_FINAL_HELDOUT_EVALUATED",
            "cycle_state": "CYCLE_06_CLOSED",
            "scientific_scope": "SAME_SPEAKER_NEW_SESSION",
            "evaluation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "evaluation_commit": prepared["commit"],
            "frozen_candidate": "ONNX_FP16",
            "final_android_runtime": "UNFROZEN",
            "rejection_policy": "CLIP_CLASS_COSINE",
            "threshold": THRESHOLD,
            "input_hashes": prepared["hashes"],
            "implementation_hashes": prepared["implementation_hashes"],
            "dataset_manifest_path": DATASET_MANIFEST.as_posix(),
            "heldout_dataset_fingerprint_sha256": DATASET_FINGERPRINT,
            "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
            "sample_count": len(predictions),
            "per_sample": predictions,
            "metrics": metrics,
            "development_references": {
                "positive_loso": {"correct": 51, "total": 54, "accuracy": 51 / 54},
                "rejection_nested_loso": {
                    "known_correct_accept": 49,
                    "known_wrong_accept": 1,
                    "known_reject": 4,
                    "unknown_reject": 46,
                    "unknown_false_accept": 8,
                    "balanced_score_reported": 0.8788,
                },
                "edge_development_calibration": {
                    "known_correct_accept": 47,
                    "known_wrong_accept": 0,
                    "known_reject": 7,
                    "unknown_reject": 53,
                    "unknown_false_accept": 1,
                    "balanced_score_reported": 0.9226,
                    "threshold": THRESHOLD,
                },
                "edge_calibration_is_generalization": False,
            },
            "post_heldout_tuning": False,
            "sample_exclusions": 0,
            "old_heldouts_opened": False,
            "heldout_consumed": True,
        }
        pending = root / (str(OUTPUT) + ".pending")
        with pending.open("xb") as stream:
            stream.write(serialize_result(result))
        os.rename(pending, output)
        attempt["phase"] = "COMPLETED"
        attempt["result_sha256"] = sha256_file(output)
        _write_attempt(attempt_path, attempt)
        return result
    except Exception as error:
        attempt["phase"] = "FAILED_AFTER_SEMANTIC_PROCESSING_STARTED"
        attempt["error_type"] = type(error).__name__
        attempt["error_message"] = str(error)
        attempt["prediction_count"] = len(predictions)
        attempt["partial_results"] = predictions
        _write_attempt(attempt_path, attempt)
        raise


def post_run_audit(root: Path) -> dict:
    """Reconfere integridade e contagem após o resultado, sem inferir novamente."""
    root = Path(root).resolve()
    output = root / OUTPUT
    if not output.is_file():
        raise FileNotFoundError("Resultado final da avaliação não existe.")
    plan = load_capture_plan(root / PLAN)
    result = json.loads(output.read_text(encoding="utf-8"))
    manifest = json.loads((root / DATASET_MANIFEST).read_text(encoding="utf-8"))
    samples = validate_dataset_manifest(plan, manifest)
    plan_rows = tuple(
        row for session in plan["sessions"] for row in session["schedule"]
    )
    validate_inventory(plan_rows, root)
    if result.get("sample_count") != 72 or result.get("heldout_consumed") is not True:
        raise ValueError("Resultado held-out incompleto.")
    recomputed = calculate_metrics(result["per_sample"], plan)
    if recomputed != result.get("metrics"):
        raise ValueError("Métricas persistidas divergem das 72 previsões.")
    attempt = json.loads((root / ATTEMPT).read_text(encoding="utf-8"))
    if (
        attempt.get("phase") != "COMPLETED"
        or attempt.get("prediction_count") != 72
        or attempt.get("result_sha256") != sha256_file(output)
    ):
        raise ValueError("Auditoria one-shot incompleta ou divergente.")
    if (
        result["heldout_dataset_fingerprint_sha256"] != DATASET_FINGERPRINT
        or result["pipeline_fingerprint_sha256"] != PIPELINE_FINGERPRINT
    ):
        raise ValueError("Fingerprint pós-avaliação divergiu.")
    hashes = check_hashes(
        {
            "dataset_manifest": (
                root / DATASET_MANIFEST,
                EXPECTED_HASHES["dataset_manifest"],
            ),
            "edge_config": (root / EDGE_CONFIG, EXPECTED_HASHES["edge_config"]),
            "freeze_manifest": (
                root / FREEZE_MANIFEST,
                EXPECTED_HASHES["freeze_manifest"],
            ),
            "encoder": (
                root / ENCODER_FILE,
                EXPECTED_HASHES["encoder"],
            ),
            "classifier": (
                root / CLASSIFIER_FILE,
                EXPECTED_HASHES["classifier"],
            ),
            "centroids": (
                root / CENTROIDS_FILE,
                EXPECTED_HASHES["centroids"],
            ),
        }
    )
    if _canonical_plan_sha256(root / PLAN) != EXPECTED_HASHES["capture_plan"]:
        raise ValueError("Plano de captura mudou após avaliação.")
    for item in samples:
        path = root / item["relative_path"]
        if sha256_file(path) != item["file_sha256"]:
            raise ValueError(f"Vídeo mudou após avaliação: {item['sample_id']}")
    hashes["capture_plan"] = EXPECTED_HASHES["capture_plan"]
    return {
        "sample_count": 72,
        "result_sha256": sha256_file(output),
        "hashes": hashes,
        "heldout_dataset_fingerprint_sha256": DATASET_FINGERPRINT,
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
    }
