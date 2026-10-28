"""Nested LOSO pareado do rejection 2.0, somente development."""

import json
import math
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from silent_voice.rejection.hybrid_rejection_scores import (
    POLICY_NAMES,
    acceptance_decision,
    calculate_detailed_metrics,
    class_centroids,
    raw_rejection_scores,
    select_calibrated_threshold,
    select_development_policy,
)
from silent_voice.rejection.rejection_protocol import (
    NEGATIVE_CATEGORIES,
    NEGATIVE_DEVELOPMENT_SESSIONS,
)
from silent_voice.vision.hybrid_features import (
    HybridSample,
    class_minimum_dtw_distances,
    equal_energy_fusion,
    normalized_reciprocal_evidence,
    raw_current_dtw_distance,
)
from silent_voice.vision.hybrid_linear_probe import (
    predict_hybrid_linear,
    train_hybrid_linear,
)
from silent_voice.vision.hybrid_loso import (
    A_NAME,
    OUTPUT_RELATIVE_PATH as HYBRID_REFERENCE_PATH,
    preflight_hybrid_loso,
)
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.rejection_visual_features import (
    EMBEDDING_MANIFEST_PATH,
    EMBEDDING_ROOT,
    PROCESSED_SOURCE_ROOT,
    RAW_SOURCE_ROOT,
    ROI_MANIFEST_PATH,
    SNAPSHOT_RELATIVE_PATH,
    _load_unknown_source,
    select_authorized_negative_paths,
    validate_unknown_embedding_dataset,
)
from silent_voice.vision.swinlip_frozen_encoder import select_source_frame_indices
from silent_voice.vision.visual_experiment_defaults import (
    SESSION_IDS,
    build_default_segmentation_config,
)
from silent_voice.vision.visual_sample_segmentation import segment_visual_feature_sample
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

OUTPUT_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_rejection_2_nested_loso.json"
)
POSITIVE_CLASSIFIER_CHECKPOINT = Path(
    "data/processed/models/cycle_06_hybrid_positive_classifier.pt"
)
POSITIVE_CLASSIFIER_CONFIG = Path(
    "data/processed/evaluation/cycle_06_positive_classifier_final_config.json"
)
SOURCE_HASHES = {
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
    "final_positive_classifier_checkpoint_not_used": (
        "33a0d1f1f564dc75f83ebc08fc2dca255840da60ca40a9c41fdd36d4ad0cc6a2"
    ),
    "final_positive_classifier_config_not_used": (
        "29b7df189ac8f3b5b01ce2b5b5b03870dd37b678ccb6f6f536e8ac9debaa7a1e"
    ),
}


@dataclass(frozen=True, slots=True)
class NegativeSample:
    sample_id: str
    session_id: str
    negative_category: str
    oov_prompt: str
    clip_embedding: np.ndarray
    features: np.ndarray
    segmentation_fallback: bool


@dataclass(frozen=True, slots=True)
class InnerPass:
    train_session_id: str
    calibration_session_id: str
    known_train: tuple
    known_calibration: tuple
    unknown_calibration: tuple


@dataclass(frozen=True, slots=True)
class NestedFold:
    validation_session_id: str
    negative_validation_session_id: str
    known_train: tuple
    known_validation: tuple
    unknown_validation: tuple
    inner_passes: tuple[InnerPass, InnerPass]


def validate_development_pairs(positives: tuple, negatives: tuple) -> None:
    """Exige 54+54 amostras balanceadas e IDs disjuntos."""
    if (
        len(positives) != 54
        or len(negatives) != 54
        or len({row.sample_id for row in (*positives, *negatives)}) != 108
        or Counter(row.session_id for row in positives)
        != Counter({session: 18 for session in SESSION_IDS})
        or Counter(row.session_id for row in negatives)
        != Counter({session: 18 for session in NEGATIVE_DEVELOPMENT_SESSIONS})
        or Counter((row.session_id, row.label_index) for row in positives)
        != Counter(
            {(session, index): 3 for session in SESSION_IDS for index in range(6)}
        )
        or Counter((row.session_id, row.negative_category) for row in negatives)
        != Counter(
            {
                (session, category): 3
                for session in NEGATIVE_DEVELOPMENT_SESSIONS
                for category in NEGATIVE_CATEGORIES
            }
        )
    ):
        raise ValueError(
            "Development exige 54 KNOWN e 54 UNKNOWN únicos e balanceados."
        )
    if any(row.label != DEFAULT_VISUAL_LABELS[row.label_index] for row in positives):
        raise ValueError("Classe positiva fora do vocabulário congelado.")


def build_nested_session_plan(
    positives: tuple, negatives: tuple
) -> tuple[NestedFold, ...]:
    """Constrói os três outer folds e dois passes internos por fold."""
    validate_development_pairs(positives, negatives)
    folds = []
    for positive_validation, negative_validation in zip(
        SESSION_IDS, NEGATIVE_DEVELOPMENT_SESSIONS, strict=True
    ):
        train_sessions = tuple(
            session for session in SESSION_IDS if session != positive_validation
        )
        inner = []
        for train_session in train_sessions:
            calibration_session = next(
                session for session in train_sessions if session != train_session
            )
            negative_calibration_session = NEGATIVE_DEVELOPMENT_SESSIONS[
                SESSION_IDS.index(calibration_session)
            ]
            inner.append(
                InnerPass(
                    train_session,
                    calibration_session,
                    tuple(row for row in positives if row.session_id == train_session),
                    tuple(
                        row
                        for row in positives
                        if row.session_id == calibration_session
                    ),
                    tuple(
                        row
                        for row in negatives
                        if row.session_id == negative_calibration_session
                    ),
                )
            )
        folds.append(
            NestedFold(
                positive_validation,
                negative_validation,
                tuple(row for row in positives if row.session_id in train_sessions),
                tuple(
                    row for row in positives if row.session_id == positive_validation
                ),
                tuple(
                    row for row in negatives if row.session_id == negative_validation
                ),
                tuple(inner),
            )
        )
    return tuple(folds)


def _fit_positive(train: tuple[HybridSample, ...], distance_fn: Callable) -> tuple:
    """Treina uma cabeça nova; self exclusion afeta somente features de treino."""
    if (
        len(train) not in (18, 36)
        or len({row.session_id for row in train}) != len(train) // 18
    ):
        raise ValueError("Fit positivo deve usar uma ou duas sessões inteiras.")
    train_features = {}
    for row in train:
        distances = class_minimum_dtw_distances(row, train, distance_fn)
        train_features[row.sample_id] = equal_energy_fusion(
            row.clip_embedding, normalized_reciprocal_evidence(distances), 1670
        )
    matrix = np.stack([train_features[row.sample_id] for row in train])
    labels = np.asarray([row.label_index for row in train], dtype=np.int64)
    model, diagnostics = train_hybrid_linear(matrix, labels)
    clips, hybrids = class_centroids(train, train_features)
    return model, clips, hybrids, diagnostics


def _score_query(
    query: object, train: tuple, fitted: tuple, distance_fn: Callable
) -> dict:
    model, clip_centroids, hybrid_centroids, _ = fitted
    if query.sample_id in {row.sample_id for row in train}:
        raise ValueError("Query de calibração/validação pertence ao treino.")
    evidence = normalized_reciprocal_evidence(
        class_minimum_dtw_distances(query, train, distance_fn)
    )
    feature = equal_energy_fusion(query.clip_embedding, evidence, 1670)
    predicted_index, logits = predict_hybrid_linear(model, feature)
    raw = raw_rejection_scores(
        np.asarray(logits),
        query.clip_embedding,
        feature,
        predicted_index,
        clip_centroids,
        hybrid_centroids,
    )
    observation = {
        "sample_id": query.sample_id,
        "session_id": query.session_id,
        "sample_kind": "UNKNOWN" if isinstance(query, NegativeSample) else "KNOWN",
        "predicted_label": DEFAULT_VISUAL_LABELS[predicted_index],
        "predicted_label_index": predicted_index,
        "logits": list(logits),
        **raw,
    }
    if isinstance(query, NegativeSample):
        observation.update(
            {
                "negative_category": query.negative_category,
                "oov_prompt": query.oov_prompt,
                "segmentation_fallback": query.segmentation_fallback,
            }
        )
    else:
        observation.update(
            {
                "expected_label": query.label,
                "expected_label_index": query.label_index,
                "classification_correct_before_rejection": predicted_index
                == query.label_index,
                "segmentation_fallback": False,
            }
        )
    return observation


def _reference_predictions(reference_rows: list[dict]) -> dict[str, int]:
    expected = {
        row["sample_id"]: row["predicted_label_index"] for row in reference_rows
    }
    if len(expected) != 54:
        raise ValueError("Referência 6.6 não contém 54 previsões únicas.")
    return expected


def build_nested_report(
    positives: tuple[HybridSample, ...],
    negatives: tuple[NegativeSample, ...],
    reference_predictions: dict[str, int],
    distance_fn: Callable = raw_current_dtw_distance,
) -> dict:
    """Reproduz o closed-set antes de calibrar e avaliar rejection."""
    folds = build_nested_session_plan(positives, negatives)
    cache = {}

    def cached_distance(first: object, second: object) -> float:
        key = tuple(sorted((first.sample_id, second.sample_id)))
        if key not in cache:
            cache[key] = float(distance_fn(first, second))
        return cache[key]

    outer = []
    observed_predictions = {}
    for fold in folds:
        fitted = _fit_positive(fold.known_train, cached_distance)
        queries = tuple(
            _score_query(row, fold.known_train, fitted, cached_distance)
            for row in (*fold.known_validation, *fold.unknown_validation)
        )
        observed_predictions.update(
            (row["sample_id"], row["predicted_label_index"])
            for row in queries
            if row["sample_kind"] == "KNOWN"
        )
        outer.append((fold, fitted[3], queries))
    if (
        observed_predictions != reference_predictions
        or sum(
            row.label_index == observed_predictions[row.sample_id] for row in positives
        )
        != 51
    ):
        raise ValueError(
            "Closed-set positivo não reproduziu 51/54 e previsões da Task 6.6."
        )

    fold_records = []
    policy_folds = {name: [] for name in POLICY_NAMES}
    for fold, outer_diagnostics, queries in outer:
        calibration = []
        inner_records = []
        for inner in fold.inner_passes:
            fitted = _fit_positive(inner.known_train, cached_distance)
            rows = tuple(
                _score_query(row, inner.known_train, fitted, cached_distance)
                for row in (*inner.known_calibration, *inner.unknown_calibration)
            )
            calibration.extend(rows)
            inner_records.append(
                {
                    "train_session_id": inner.train_session_id,
                    "calibration_session_id": inner.calibration_session_id,
                    "negative_calibration_session_id": NEGATIVE_DEVELOPMENT_SESSIONS[
                        SESSION_IDS.index(inner.calibration_session_id)
                    ],
                    "training_sample_ids": [row.sample_id for row in inner.known_train],
                    "template_sample_ids": [row.sample_id for row in inner.known_train],
                    "calibration_sample_ids": [row["sample_id"] for row in rows],
                    "training_diagnostics": fitted[3],
                    "raw_scores": list(rows),
                }
            )
        if (
            len(calibration) != 72
            or len({row["sample_id"] for row in calibration}) != 72
        ):
            raise ValueError("Pool interno exige 36 KNOWN e 36 UNKNOWN únicos.")
        if set(row["sample_id"] for row in calibration) & set(
            row["sample_id"] for row in queries
        ):
            raise ValueError("Outer validation vazou para calibração.")
        thresholds_by_policy = {}
        for name in POLICY_NAMES:
            selected = select_calibrated_threshold(name, tuple(calibration))
            thresholds = tuple(selected["thresholds"])
            decisions = tuple(
                acceptance_decision(name, row, thresholds) for row in queries
            )
            metrics = calculate_detailed_metrics(queries, decisions)
            policy_folds[name].append(
                {
                    "validation_session_id": fold.validation_session_id,
                    "thresholds": list(thresholds),
                    "calibration_metrics": selected["metrics"],
                    "candidate_count": selected["candidate_count"],
                    "metrics": metrics,
                    "decisions": [
                        {"sample_id": row["sample_id"], "accepted": decision}
                        for row, decision in zip(queries, decisions, strict=True)
                    ],
                }
            )
            thresholds_by_policy[name] = selected
        fold_records.append(
            {
                "validation_session_id": fold.validation_session_id,
                "negative_validation_session_id": fold.negative_validation_session_id,
                "outer_training_sample_ids": [
                    row.sample_id for row in fold.known_train
                ],
                "outer_template_sample_ids": [
                    row.sample_id for row in fold.known_train
                ],
                "outer_training_diagnostics": outer_diagnostics,
                "inner_passes": inner_records,
                "calibration_count": len(calibration),
                "thresholds_by_policy": thresholds_by_policy,
                "outer_validation_raw_scores": list(queries),
            }
        )
    policies = {}
    all_queries = tuple(row for _, _, queries in outer for row in queries)
    for name in POLICY_NAMES:
        accepted_by_id = {
            decision["sample_id"]: decision["accepted"]
            for fold in policy_folds[name]
            for decision in fold["decisions"]
        }
        accepted = tuple(accepted_by_id[row["sample_id"]] for row in all_queries)
        policies[name] = {
            "folds": policy_folds[name],
            "global_metrics": calculate_detailed_metrics(all_queries, accepted),
        }
    preferred = select_development_policy(policies)
    preferred_decisions = {
        decision["sample_id"]: decision["accepted"]
        for fold in policies[preferred]["folds"]
        for decision in fold["decisions"]
    }
    known = [row for row in all_queries if row["sample_kind"] == "KNOWN"]
    unknown = [row for row in all_queries if row["sample_kind"] == "UNKNOWN"]
    return {
        "format_version": 1,
        "state": "REJECTION_2_DEVELOPMENT_SELECTED",
        "positive_classifier": A_NAME,
        "positive_closed_set_correct_count": 51,
        "positive_closed_set_count": 54,
        "positive_reference_predictions_identical": True,
        "outer_fold_count": 3,
        "folds": fold_records,
        "policies": policies,
        "development_preferred_rejection_policy": preferred,
        "preferred_false_accepts": [
            {**row, "decision": "ACCEPT"}
            for row in unknown
            if preferred_decisions[row["sample_id"]]
        ],
        "preferred_known_rejects": [
            {**row, "decision": "REJECT"}
            for row in known
            if not preferred_decisions[row["sample_id"]]
        ],
        "comparison_without_rejection": {
            "positive_closed_set_correct": 51,
            "correct_positives_rejected": sum(
                row["classification_correct_before_rejection"]
                and not preferred_decisions[row["sample_id"]]
                for row in known
            ),
            "wrong_positives_correctly_rejected": sum(
                not row["classification_correct_before_rejection"]
                and not preferred_decisions[row["sample_id"]]
                for row in known
            ),
            "unknown_false_accepts_avoided": sum(
                not preferred_decisions[row["sample_id"]] for row in unknown
            ),
        },
        "cycle_5_historical_reference": {
            "policy": "CLASS_SCALED_PATH_DISTANCE_AND_MARGIN",
            "KNOWN_CORRECT_ACCEPT": 34,
            "KNOWN_WRONG_ACCEPT": 8,
            "KNOWN_REJECT": 12,
            "UNKNOWN_REJECT": 51,
            "UNKNOWN_FALSE_ACCEPT": 3,
            "rejection_balanced_score": 0.7556,
            "comparison_kind": "descriptive_only_different_positive_classifiers",
        },
        "dtw_unique_pair_count": len(cache),
        "heldouts_used": False,
        "final_threshold_selected": False,
    }


def preflight_real_nested_loso(repository_root: Path) -> dict:
    """Valida hashes e filtra paths permitidos antes de ler NPZ/embeddings."""
    root = Path(repository_root).resolve()
    paths = {
        "positive_embedding_manifest": Path(
            "data/processed/evaluation/cycle_06_swinlip_embedding_manifest.json"
        ),
        "negative_capture_snapshot": SNAPSHOT_RELATIVE_PATH,
        "negative_roi_manifest": ROI_MANIFEST_PATH,
        "negative_embedding_manifest": EMBEDDING_MANIFEST_PATH,
        "final_positive_classifier_checkpoint_not_used": POSITIVE_CLASSIFIER_CHECKPOINT,
        "final_positive_classifier_config_not_used": POSITIVE_CLASSIFIER_CONFIG,
    }
    for name, relative in paths.items():
        if sha256_file(root / relative) != SOURCE_HASHES[name]:
            raise ValueError(f"SHA-256 congelado divergiu: {name}")
    selected = select_authorized_negative_paths(
        root / PROCESSED_SOURCE_ROOT, root / RAW_SOURCE_ROOT
    )
    negative_manifest = validate_unknown_embedding_dataset(root)
    positive = preflight_hybrid_loso(root)
    reference = json.loads((root / HYBRID_REFERENCE_PATH).read_text(encoding="utf-8"))
    if reference["candidates"][A_NAME]["metrics"]["correct_count"] != 51:
        raise ValueError("Referência closed-set 6.6 divergente.")
    reference_predictions = _reference_predictions(
        reference["candidates"][A_NAME]["predictions"]
    )
    embeddings_by_id = {
        entry["sample_id"]: entry for entry in negative_manifest["samples"]
    }
    segments_by_id = {
        entry["sample_id"]: entry for entry in negative_manifest["segments"]
    }
    if len(embeddings_by_id) != 54 or len(segments_by_id) != 54:
        raise ValueError("Embeddings/segmentos UNKNOWN incompletos.")
    negatives = []
    for item, npz_path, _ in selected:
        source = _load_unknown_source(npz_path, item)
        result = segment_visual_feature_sample(
            source, build_default_segmentation_config()
        )
        segment = segments_by_id[item.sample_id]
        if (
            segment["start_frame"] != result.segment.start_frame
            or segment["end_frame_exclusive"] != result.segment.end_frame_exclusive
            or segment["fallback"] != (not result.segment.detected)
        ):
            raise ValueError("Segmentação UNKNOWN divergiu da Task 6.8A.")
        embedding_path = root / EMBEDDING_ROOT / f"{item.sample_id}.npz"
        with np.load(embedding_path, allow_pickle=False) as data:
            clip = np.asarray(data["clip_embedding"]).copy()
            indices = np.asarray(data["selected_source_frame_indices"]).copy()
        if (
            sha256_file(embedding_path)
            != embeddings_by_id[item.sample_id]["embedding_sha256"]
            or clip.shape != (1664,)
            or clip.dtype != np.float32
            or not np.isfinite(clip).all()
            or not np.array_equal(
                indices,
                select_source_frame_indices(
                    result.segment.start_frame, result.segment.end_frame_exclusive
                ),
            )
        ):
            raise ValueError("Embedding UNKNOWN não pareia com NPZ segmentado.")
        negatives.append(
            NegativeSample(
                item.sample_id,
                item.session_id,
                item.negative_category,
                item.oov_prompt,
                clip,
                result.sample.features,
                not result.segment.detected,
            )
        )
    negatives = tuple(negatives)
    validate_development_pairs(positive["samples"], negatives)
    return {
        "positives": positive["samples"],
        "negatives": negatives,
        "reference_predictions": reference_predictions,
        "source_hashes": SOURCE_HASHES,
        "negative_embedding_hashes": {
            entry["sample_id"]: entry["embedding_sha256"]
            for entry in negative_manifest["samples"]
        },
        "positive_embedding_hashes": positive["embedding_hashes"],
        "positive_visual_npz_hashes": positive["visual_hashes"],
        "positive_segmentation": positive["segmentation"],
        "negative_fallback_count": sum(row.segmentation_fallback for row in negatives),
        "negative_fallback_by_category": {
            category: sum(
                row.segmentation_fallback and row.negative_category == category
                for row in negatives
            )
            for category in NEGATIVE_CATEGORIES
        },
    }


def _json_finite(value: object) -> object:
    if isinstance(value, dict):
        return {key: _json_finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_finite(item) for item in value]
    if isinstance(value, float) and math.isinf(value):
        return "+inf" if value > 0 else "-inf"
    return value


def run_real_nested_loso(repository_root: Path) -> dict:
    """Executa uma vez com código commitado e salva JSON somente após consistência."""
    root = Path(repository_root).resolve()
    output = root / OUTPUT_RELATIVE_PATH
    if output.exists():
        raise FileExistsError("Resultado nested LOSO já existe; não reexecutar.")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError(
            "Worktree versionável precisa estar limpo antes do experimento."
        )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    preflight = preflight_real_nested_loso(root)
    report = build_nested_report(
        preflight["positives"],
        preflight["negatives"],
        preflight["reference_predictions"],
    )
    report.update(
        {
            "code_commit": commit,
            "evaluation_count": 1,
            "worktree_clean_before_evaluation": True,
            "source_hashes": preflight["source_hashes"],
            "positive_embedding_hashes": preflight["positive_embedding_hashes"],
            "positive_visual_npz_hashes": preflight["positive_visual_npz_hashes"],
            "negative_embedding_hashes": preflight["negative_embedding_hashes"],
            "segmentation_diagnostics": {
                "positive_fallback_count": preflight["positive_segmentation"][
                    "fallback_count"
                ],
                "negative_fallback_count": preflight["negative_fallback_count"],
                "negative_fallback_by_category": preflight[
                    "negative_fallback_by_category"
                ],
            },
            "protocol": {
                "outer_folds": 3,
                "inner_passes_per_fold": 2,
                "inner_calibration_known_count": 36,
                "inner_calibration_unknown_count": 36,
                "outer_validation_known_count": 18,
                "outer_validation_unknown_count": 18,
                "policies": list(POLICY_NAMES),
                "positive_training": (
                    "Linear(1670,6), seed2026, CPU, AdamW, 500 epochs, "
                    "full batch, gradient clip1.0"
                ),
                "positive_training_source": (
                    "Task 6.6 protocol; final 54-positive checkpoint not loaded"
                ),
                "final_threshold_not_selected": True,
            },
        }
    )
    serialized = (
        json.dumps(_json_finite(report), ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    return report
