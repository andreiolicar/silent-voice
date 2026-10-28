"""Calibração e inferência congelada do rejection 2.0 FP32."""

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from silent_voice.rejection.hybrid_rejection_nested_loso import (
    OUTPUT_RELATIVE_PATH as NESTED_RESULT_PATH,
    NegativeSample,
    preflight_real_nested_loso,
    validate_development_pairs,
)
from silent_voice.rejection.hybrid_rejection_scores import (
    acceptance_decision,
    calculate_detailed_metrics,
    select_calibrated_threshold,
)
from silent_voice.rejection.rejection_protocol import NEGATIVE_CATEGORIES
from silent_voice.vision.hybrid_features import HybridSample
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.positive_classifier_final import (
    CHECKPOINT_RELATIVE_PATH,
    CLASSIFIER_ID,
    CONFIG_RELATIVE_PATH,
    SWINLIP_CHECKPOINT_SHA256,
    SWINLIP_COMMIT,
    SWINLIP_SOURCE,
    clip_embedding_sha256,
    load_frozen_positive_classifier,
    segmented_feature_sha256,
)
from silent_voice.vision.swinlip_frozen_probe import l2_normalize
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

POLICY = "CLIP_CLASS_COSINE"
STATE = "REJECTION_2_FROZEN_BEFORE_HELDOUT"
NESTED_RESULT_SHA256 = (
    "54f487336f1ca1ef452576b883312af867f18c6f44fabcd61aeaa396083d0d3e"
)
CENTROID_RELATIVE_PATH = Path(
    "data/processed/models/cycle_06_rejection_2_clip_centroids.npz"
)
CONFIG_FINAL_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_rejection_2_final_config.json"
)
CALIBRATION_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_rejection_2_final_calibration.json"
)
SOURCE_HASHES = {
    "positive_classifier_checkpoint": (
        "33a0d1f1f564dc75f83ebc08fc2dca255840da60ca40a9c41fdd36d4ad0cc6a2"
    ),
    "positive_classifier_config": (
        "29b7df189ac8f3b5b01ce2b5b5b03870dd37b678ccb6f6f536e8ac9debaa7a1e"
    ),
    "positive_embedding_manifest": (
        "13a45412538e9a67756884dbafcdb3d22bbfd0126892dcf2e0f4e8f52db49b17"
    ),
    "negative_capture_snapshot": (
        "86427fb09df7981f997ef61c1c2a4ccd7142105bad3bcfea0f606f28c72abe82"
    ),
    "negative_roi_manifest": (
        "cacab11fb0d4890558bc292c9b68087d8e5a5f42a9fdd8db0a6877185d08c0c4"
    ),
    "negative_embedding_manifest": (
        "8b59f0c07a9947a06416eea2359a0acc86921d3c16a51c4349edca0689909d46"
    ),
    "nested_loso_result": NESTED_RESULT_SHA256,
}
SOURCE_PATHS = {
    "positive_classifier_checkpoint": CHECKPOINT_RELATIVE_PATH,
    "positive_classifier_config": CONFIG_RELATIVE_PATH,
    "positive_embedding_manifest": Path(
        "data/processed/evaluation/cycle_06_swinlip_embedding_manifest.json"
    ),
    "negative_capture_snapshot": Path(
        "data/processed/evaluation/rejection_dev_capture_snapshot.json"
    ),
    "negative_roi_manifest": Path(
        "data/processed/evaluation/cycle_06_rejection_dev_mouth_roi_manifest.json"
    ),
    "negative_embedding_manifest": Path(
        "data/processed/evaluation/"
        "cycle_06_rejection_dev_swinlip_embedding_manifest.json"
    ),
    "nested_loso_result": NESTED_RESULT_PATH,
}


def _unit_clip(clip: np.ndarray) -> np.ndarray:
    values = np.asarray(clip)
    if (
        values.shape != (1664,)
        or values.dtype != np.float32
        or not np.isfinite(values).all()
        or np.linalg.norm(values) <= 1e-12
    ):
        raise ValueError("Clip precisa ser float32 finito e não nulo de 1664-D.")
    return l2_normalize(values)


def _class_clips(positives: tuple, index: int) -> tuple:
    if index not in range(6):
        raise ValueError("Índice de classe fora do vocabulário congelado.")
    rows = tuple(row for row in positives if row.label_index == index)
    if len(rows) != 9 or any(row.label != DEFAULT_VISUAL_LABELS[index] for row in rows):
        raise ValueError("Cada centroide exige nove clips da classe correta.")
    return rows


def _centroid(rows: tuple) -> np.ndarray:
    unit_clips = np.stack([_unit_clip(row.clip_embedding) for row in rows])
    mean = unit_clips.mean(axis=0).astype(np.float32)
    return _unit_clip(mean)


def build_final_clip_centroids(positives: tuple) -> np.ndarray:
    """Nove clips por classe, média de vetores unitários e L2 final."""
    if len(positives) != 54 or len({row.sample_id for row in positives}) != 54:
        raise ValueError("Centroides finais exigem 54 positivos únicos.")
    centroids = np.stack(
        [_centroid(_class_clips(positives, index)) for index in range(6)]
    ).astype(np.float32)
    if centroids.shape != (6, 1664) or not np.allclose(
        np.linalg.norm(centroids, axis=1), 1.0, atol=1e-5
    ):
        raise ValueError("Centroides finais inválidos.")
    return centroids


def score_known_clip(query: HybridSample, predicted_index: int, positives: tuple):
    """Remove o próprio clip apenas se ele integra a classe prevista."""
    rows = _class_clips(positives, predicted_index)
    matching = [row for row in rows if row.sample_id == query.sample_id]
    excluded = bool(matching)
    if excluded:
        if len(matching) != 1 or query.label_index != predicted_index:
            raise ValueError("Self exclusion não corresponde à classe prevista.")
        rows = tuple(row for row in rows if row.sample_id != query.sample_id)
    score = float(np.dot(_unit_clip(query.clip_embedding), _centroid(rows)))
    return score, excluded


def score_unknown_clip(clip: np.ndarray, predicted_index: int, centroids: np.ndarray):
    """Query externa usa o centroide final completo da classe prevista."""
    _validate_centroids(centroids)
    if predicted_index not in range(6):
        raise ValueError("Índice previsto inválido.")
    return float(np.dot(_unit_clip(clip), centroids[predicted_index]))


def _validate_centroids(centroids: np.ndarray) -> None:
    if (
        centroids.shape != (6, 1664)
        or centroids.dtype != np.float32
        or not np.isfinite(centroids).all()
        or not np.allclose(np.linalg.norm(centroids, axis=1), 1.0, atol=1e-5)
    ):
        raise ValueError("Artefato de centroides inválido.")


def calibration_observation(
    query: HybridSample | NegativeSample,
    predicted_index: int,
    positives: tuple,
    centroids: np.ndarray,
) -> dict:
    """Produz um score com o protocolo específico de KNOWN ou UNKNOWN."""
    if predicted_index not in range(6):
        raise ValueError("Classe prevista inválida.")
    common = {
        "sample_id": query.sample_id,
        "session_id": query.session_id,
        "predicted_label": DEFAULT_VISUAL_LABELS[predicted_index],
        "predicted_label_index": predicted_index,
    }
    if isinstance(query, NegativeSample) or hasattr(query, "negative_category"):
        score = score_unknown_clip(query.clip_embedding, predicted_index, centroids)
        return {
            **common,
            "sample_kind": "UNKNOWN",
            "negative_category": query.negative_category,
            "oov_prompt": query.oov_prompt,
            "segmentation_fallback": query.segmentation_fallback,
            "clip_class_cosine": score,
            "self_excluded_from_centroid": False,
        }
    score, excluded = score_known_clip(query, predicted_index, positives)
    return {
        **common,
        "sample_kind": "KNOWN",
        "expected_label": query.label,
        "expected_label_index": query.label_index,
        "classification_correct_before_rejection": predicted_index == query.label_index,
        "segmentation_fallback": False,
        "clip_class_cosine": score,
        "self_excluded_from_centroid": excluded,
    }


@dataclass(frozen=True, slots=True)
class FrozenClipRejection:
    centroids: np.ndarray
    threshold: float
    config: dict

    def decide(self, clip: np.ndarray, predicted_label: str, predicted_index: int):
        """Executa somente a decisão de rejection após classificação externa."""
        if (
            predicted_index not in range(6)
            or predicted_label != DEFAULT_VISUAL_LABELS[predicted_index]
        ):
            raise ValueError("Label previsto inconsistente com índice.")
        score = score_unknown_clip(clip, predicted_index, self.centroids)
        accepted = score >= self.threshold
        return {
            "predicted_label": predicted_label,
            "predicted_label_index": predicted_index,
            "clip_class_cosine": score,
            "threshold": self.threshold,
            "decision": "ACCEPT" if accepted else "REJECT",
            "accepted_label": predicted_label if accepted else None,
        }


def load_frozen_clip_rejection(config_path: Path, repository_root: Path):
    """Valida config, checkpoint e centroide sem rodar encoder/classificador."""
    root = Path(repository_root).resolve()
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if (
        config.get("format_version") != 1
        or config.get("state") != STATE
        or config.get("policy") != POLICY
        or config.get("labels") != list(DEFAULT_VISUAL_LABELS)
        or config.get("heldouts_used") is not False
        or config.get("policy_selected_before_final_calibration") is not True
        or config.get("threshold_frozen_before_new_heldout") is not True
        or config.get("calibration_not_generalization") is not True
        or not isinstance(config.get("threshold"), (int, float))
        or math.isnan(config["threshold"])
    ):
        raise ValueError("Config final de rejection inválido.")
    classifier = config.get("positive_classifier", {})
    centroid = config.get("centroids", {})
    if (
        classifier.get("checkpoint_path") != CHECKPOINT_RELATIVE_PATH.as_posix()
        or classifier.get("config_path") != CONFIG_RELATIVE_PATH.as_posix()
        or classifier.get("model_id") != CLASSIFIER_ID
        or classifier.get("input_dim") != 1670
        or classifier.get("output_dim") != 6
    ):
        raise ValueError("Metadados do classificador divergentes.")
    if sha256_file(root / classifier["checkpoint_path"]) != classifier.get(
        "checkpoint_sha256"
    ):
        raise ValueError("SHA do checkpoint divergente.")
    if sha256_file(root / classifier["config_path"]) != classifier.get("config_sha256"):
        raise ValueError("SHA do config positivo divergente.")
    if centroid.get("artifact_path") != CENTROID_RELATIVE_PATH.as_posix():
        raise ValueError("Path do centroide divergente.")
    centroid_path = root / centroid["artifact_path"]
    if sha256_file(centroid_path) != centroid.get("artifact_sha256"):
        raise ValueError("SHA do centroide divergente.")
    if (
        centroid.get("shape") != [6, 1664]
        or centroid.get("dtype") != "float32"
        or centroid.get("labels") != list(DEFAULT_VISUAL_LABELS)
    ):
        raise ValueError("Metadados de centroide inválidos.")
    with np.load(centroid_path, allow_pickle=False) as data:
        if set(data.files) != {"centroids", "labels", "format_version"}:
            raise ValueError("Campos do centroide inválidos.")
        values = np.asarray(data["centroids"]).copy()
        labels = np.asarray(data["labels"]).tolist()
        version = int(data["format_version"])
    if version != 1 or labels != list(DEFAULT_VISUAL_LABELS):
        raise ValueError("Ordem de labels do centroide inválida.")
    _validate_centroids(values)
    return FrozenClipRejection(values, float(config["threshold"]), config)


def preflight_final_calibration(repository_root: Path) -> dict:
    """Valida sete hashes e paths autorizados antes de qualquer score real."""
    root = Path(repository_root).resolve()
    for relative in (
        CENTROID_RELATIVE_PATH,
        CONFIG_FINAL_RELATIVE_PATH,
        CALIBRATION_RELATIVE_PATH,
    ):
        if (root / relative).exists():
            raise FileExistsError(f"Calibração final já existe: {relative}")
    for name, relative in SOURCE_PATHS.items():
        if sha256_file(root / relative) != SOURCE_HASHES[name]:
            raise ValueError(f"SHA-256 congelado divergiu: {name}")
    nested = json.loads((root / NESTED_RESULT_PATH).read_text(encoding="utf-8"))
    if (
        nested.get("development_preferred_rejection_policy") != POLICY
        or nested.get("state") != "REJECTION_2_DEVELOPMENT_SELECTED"
        or nested.get("heldouts_used") is not False
    ):
        raise ValueError("Seleção 6.8B não autoriza esta policy.")
    prepared = preflight_real_nested_loso(root)
    positives = prepared["positives"]
    negatives = prepared["negatives"]
    validate_development_pairs(positives, negatives)
    classifier = load_frozen_positive_classifier(
        root / CHECKPOINT_RELATIVE_PATH, root / CONFIG_RELATIVE_PATH
    )
    records = classifier.config["template_bank"]["templates"]
    actual = {item.sample_id: item for item in positives}
    if {item["sample_id"] for item in records} != set(actual):
        raise ValueError("Template bank e development não pareiam.")
    for record in records:
        sample = actual[record["sample_id"]]
        if record["clip_embedding_sha256"] != clip_embedding_sha256(
            sample.clip_embedding
        ) or record["segmented_feature_sha256"] != segmented_feature_sha256(
            sample.features
        ):
            raise ValueError("Template positivo divergiu dos 54 inputs.")
    snapshot = json.loads(
        (root / SOURCE_PATHS["negative_capture_snapshot"]).read_text(encoding="utf-8")
    )
    if set(snapshot["npz_sha256"]) != {row.sample_id for row in negatives}:
        raise ValueError("Snapshot negativo não cobre as 54 amostras.")
    return {
        **prepared,
        "classifier": classifier,
        "nested": nested,
        "negative_npz_hashes": snapshot["npz_sha256"],
    }


def _predict_calibration_query(classifier, query) -> int:
    """Todos os 54 templates ficam no banco, inclusive para KNOWN."""
    if isinstance(query, HybridSample):
        query = HybridSample(
            query.sample_id + "__calibration_query",
            query.session_id,
            query.label,
            query.label_index,
            query.clip_embedding,
            query.features,
        )
    else:
        query = HybridSample(
            query.sample_id,
            query.session_id,
            "",
            -1,
            query.clip_embedding,
            query.features,
        )
    return classifier.predict_query(query)["predicted_label_index"]


def build_final_calibration_report(prepared: dict, code_commit: str) -> tuple:
    """Calcula um threshold único da policy já selecionada, sem persistência."""
    positives = prepared["positives"]
    negatives = prepared["negatives"]
    validate_development_pairs(positives, negatives)
    centroids = build_final_clip_centroids(positives)
    observations = tuple(
        calibration_observation(
            row,
            _predict_calibration_query(prepared["classifier"], row),
            positives,
            centroids,
        )
        for row in (*positives, *negatives)
    )
    if (
        len(observations) != 108
        or len({row["sample_id"] for row in observations}) != 108
    ):
        raise ValueError("Calibração deve conter 108 observações únicas.")
    selected = select_calibrated_threshold(POLICY, observations)
    threshold = selected["thresholds"][0]
    decisions = tuple(
        acceptance_decision(POLICY, row, (threshold,)) for row in observations
    )
    metrics = calculate_detailed_metrics(observations, decisions)
    rows = [
        {**row, "threshold": threshold, "decision": "ACCEPT" if accepted else "REJECT"}
        for row, accepted in zip(observations, decisions, strict=True)
    ]
    report = {
        "format_version": 1,
        "state": STATE,
        "policy": POLICY,
        "threshold": threshold,
        "candidate_count": selected["candidate_count"],
        "code_commit": code_commit,
        "calibration_kind": "FINAL_DEVELOPMENT_CALIBRATION_NOT_GENERALIZATION",
        "known_count": 54,
        "unknown_count": 54,
        "positive_classifier_fit_correct_count": sum(
            row["classification_correct_before_rejection"]
            for row in observations
            if row["sample_kind"] == "KNOWN"
        ),
        "metrics": metrics,
        "observations": rows,
        "unknown_false_accepts": [
            row
            for row in rows
            if row["sample_kind"] == "UNKNOWN" and row["decision"] == "ACCEPT"
        ],
        "known_correct_rejects": [
            row
            for row in rows
            if row["sample_kind"] == "KNOWN"
            and row["decision"] == "REJECT"
            and row["classification_correct_before_rejection"]
        ],
        "known_wrong_rejects": [
            row
            for row in rows
            if row["sample_kind"] == "KNOWN"
            and row["decision"] == "REJECT"
            and not row["classification_correct_before_rejection"]
        ],
        "source_hashes": SOURCE_HASHES,
        "heldouts_used": False,
        "final_calibration_count": 1,
    }
    return centroids, report


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and math.isinf(value):
        return "+inf" if value > 0 else "-inf"
    return value


def _write_json_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(
            _json_safe(payload), stream, ensure_ascii=False, indent=2, allow_nan=False
        )
        stream.write("\n")


def run_real_final_calibration(repository_root: Path) -> dict:
    """Executa uma vez com código commitado e guarda três artefatos auditáveis."""
    root = Path(repository_root).resolve()
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError("Worktree versionável precisa estar limpo.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    prepared = preflight_final_calibration(root)
    centroids, report = build_final_calibration_report(prepared, commit)
    threshold = report["threshold"]
    if not math.isfinite(threshold):
        raise ValueError("Threshold final infinito não pode ser usado em produção.")
    centroid_path = root / CENTROID_RELATIVE_PATH
    centroid_path.parent.mkdir(parents=True, exist_ok=True)
    with centroid_path.open("xb") as stream:
        np.savez(
            stream,
            centroids=centroids,
            labels=np.asarray(DEFAULT_VISUAL_LABELS),
            format_version=np.asarray(1, dtype=np.int64),
        )
    centroid_sha = sha256_file(centroid_path)
    config = {
        "format_version": 1,
        "state": STATE,
        "policy": POLICY,
        "threshold": threshold,
        "acceptance_rule": "clip_class_cosine >= threshold",
        "labels": list(DEFAULT_VISUAL_LABELS),
        "code_commit": commit,
        "positive_classifier": {
            "model_id": CLASSIFIER_ID,
            "checkpoint_path": CHECKPOINT_RELATIVE_PATH.as_posix(),
            "checkpoint_sha256": SOURCE_HASHES["positive_classifier_checkpoint"],
            "config_path": CONFIG_RELATIVE_PATH.as_posix(),
            "config_sha256": SOURCE_HASHES["positive_classifier_config"],
            "input_dim": 1670,
            "output_dim": 6,
        },
        "swinlip": {
            "source_repository": SWINLIP_SOURCE,
            "source_commit": SWINLIP_COMMIT,
            "checkpoint_sha256": SWINLIP_CHECKPOINT_SHA256,
        },
        "source_hashes": SOURCE_HASHES,
        "centroids": {
            "artifact_path": CENTROID_RELATIVE_PATH.as_posix(),
            "artifact_sha256": centroid_sha,
            "shape": [6, 1664],
            "dtype": "float32",
            "labels": list(DEFAULT_VISUAL_LABELS),
            "class_counts": [9] * 6,
        },
        "calibration_dataset": {
            "positive_sample_ids": [row.sample_id for row in prepared["positives"]],
            "positive_embedding_hashes": prepared["positive_embedding_hashes"],
            "positive_visual_npz_hashes": prepared["positive_visual_npz_hashes"],
            "negative_sample_ids": [row.sample_id for row in prepared["negatives"]],
            "negative_npz_hashes": prepared["negative_npz_hashes"],
            "negative_embedding_hashes": prepared["negative_embedding_hashes"],
            "positive_sessions": ["sessao_01", "sessao_02", "sessao_03"],
            "negative_sessions": [
                "rejeicao_dev_01",
                "rejeicao_dev_02",
                "rejeicao_dev_03",
            ],
            "negative_categories": list(NEGATIVE_CATEGORIES),
        },
        "calibration_protocol": {
            "known_centroid": "predicted_class_leave_self_out_if_member",
            "unknown_centroid": "predicted_class_full_nine_positive_clips",
            "future_query_centroid": "predicted_class_full_nine_positive_clips",
            "candidates": "negative_infinity_unique_observed_scores_positive_infinity",
            "acceptance": "score_greater_than_or_equal_to_threshold",
            "selection": [
                "max_harmonic_KCAR_URR",
                "min_UNKNOWN_FALSE_ACCEPT",
                "min_KNOWN_WRONG_ACCEPT",
                "max_KNOWN_CORRECT_ACCEPT",
                "max_threshold",
            ],
            "candidate_count": report["candidate_count"],
        },
        "final_development_calibration_metrics": report["metrics"],
        "positive_classifier_fit_correct_count": report[
            "positive_classifier_fit_correct_count"
        ],
        "segmentation_diagnostics": {
            "positive_fallback_count": prepared["positive_segmentation"][
                "fallback_count"
            ],
            "negative_fallback_count": prepared["negative_fallback_count"],
            "negative_fallback_by_category": prepared["negative_fallback_by_category"],
        },
        "heldouts_used": False,
        "policy_selected_before_final_calibration": True,
        "policy_source": "Task 6.8B nested LOSO",
        "threshold_frozen_before_new_heldout": True,
        "calibration_not_generalization": True,
    }
    _write_json_exclusive(root / CONFIG_FINAL_RELATIVE_PATH, config)
    report["centroid_sha256"] = centroid_sha
    report["config_sha256"] = sha256_file(root / CONFIG_FINAL_RELATIVE_PATH)
    _write_json_exclusive(root / CALIBRATION_RELATIVE_PATH, report)
    return report
