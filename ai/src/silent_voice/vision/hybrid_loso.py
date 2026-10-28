"""LOSO dos dois híbridos pré-registrados com referências congeladas."""

import json
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import numpy as np

from silent_voice.vision.dtw_tcn_comparison import calculate_paired_metrics
from silent_voice.vision.dtw_tcn_error_analysis import analyze_paired_errors
from silent_voice.vision.dtw_tcn_predictions import PairedPredictions, SamplePrediction
from silent_voice.vision.hybrid_features import (
    HYBRID_EPSILON,
    HybridSample,
    class_minimum_dtw_distances,
    equal_energy_fusion,
    landmark_stats,
    load_authorized_clip_embeddings,
    load_authorized_visual_samples,
    normalized_reciprocal_evidence,
    raw_current_dtw_distance,
    select_authorized_embedding_paths,
)
from silent_voice.vision.hybrid_linear_probe import (
    predict_hybrid_linear,
    train_hybrid_linear,
)
from silent_voice.vision.legacy_weighted_dtw_loso import (
    CURRENT_DTW_SHA256,
    DATASET_RELATIVE_PATH,
    SWINLIP_RELATIVE_PATH,
    SWINLIP_SHA256,
    _load_references,
    analyze_triple,
    segment_development_samples,
)
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.swinlip_embedding_dataset import (
    OUTPUT_MANIFEST_RELATIVE_PATH,
)
from silent_voice.vision.swinlip_frozen_loso import EMBEDDING_MANIFEST_SHA256
from silent_voice.vision.swinlip_frozen_probe import (
    LINEAR_EPOCHS,
    LINEAR_GRADIENT_CLIP_NORM,
    LINEAR_LEARNING_RATE,
    LINEAR_SEED,
    LINEAR_WEIGHT_DECAY,
)
from silent_voice.vision.visual_cross_validation import (
    build_leave_one_session_out_folds,
)
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

A_NAME = "HYBRID_CLIP_DTW_EVIDENCE_LINEAR"
B_NAME = "HYBRID_CLIP_LANDMARK_STATS_LINEAR"
VISUAL_ONLY_NAME = "SWINLIP_LINEAR_PROBE"
OUTPUT_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_silent_voice_hybrid_loso.json"
)
LEGACY_RESULT_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_legacy_weighted_dtw_loso.json"
)
LEGACY_RESULT_SHA256 = (
    "edea6f7acb7ada1910886c29b1fba1f118a5165b3a3f6568ecc1d4c4ccc8ff88"
)


def _validate_hybrid_samples(samples: tuple[HybridSample, ...]) -> None:
    if len(samples) != 54 or len({item.sample_id for item in samples}) != 54:
        raise ValueError("Híbrido exige 54 sample_id únicos.")
    if Counter(item.session_id for item in samples) != Counter(
        {session: 18 for session in SESSION_IDS}
    ):
        raise ValueError("Híbrido aceita apenas três sessões de desenvolvimento.")
    if Counter((item.session_id, item.label_index) for item in samples) != Counter(
        {(session, index): 3 for session in SESSION_IDS for index in range(6)}
    ):
        raise ValueError("Híbrido exige três amostras por classe e sessão.")
    for item in samples:
        if (
            item.label_index not in range(6)
            or item.label != DEFAULT_VISUAL_LABELS[item.label_index]
            or item.clip_embedding.shape != (1664,)
            or item.clip_embedding.dtype != np.float32
            or not np.isfinite(item.clip_embedding).all()
            or item.features.ndim != 2
            or item.features.shape[1] != 160
            or not np.isfinite(item.features).all()
        ):
            raise ValueError("Shape, label ou feature do híbrido inválido.")


def _prediction(sample: HybridSample, predicted_index: int) -> SamplePrediction:
    return SamplePrediction(
        sample_id=sample.sample_id,
        validation_session_id=sample.session_id,
        expected_label=sample.label,
        expected_label_index=sample.label_index,
        predicted_label=DEFAULT_VISUAL_LABELS[predicted_index],
        predicted_label_index=predicted_index,
        correct=predicted_index == sample.label_index,
    )


def _paired(
    first: tuple[SamplePrediction, ...], second: tuple[SamplePrediction, ...]
) -> PairedPredictions:
    return PairedPredictions(DEFAULT_VISUAL_LABELS, first, second)


def _ranking(metrics: dict) -> tuple[float, float, float]:
    return (
        metrics["accuracy"],
        min(row["accuracy"] for row in metrics["folds"]),
        min(row["accuracy"] for row in metrics["classes"]),
    )


def select_preferred_hybrid(a_metrics: dict, b_metrics: dict) -> str:
    """Global, pior fold, pior classe; empate final favorece A."""
    return B_NAME if _ranking(b_metrics) > _ranking(a_metrics) else A_NAME


def select_positive_classifier(
    visual_metrics: dict, hybrid_metrics: dict, hybrid_name: str
) -> str:
    """Empate completo favorece o probe visual pela simplicidade."""
    if hybrid_name not in (A_NAME, B_NAME):
        raise ValueError("Nome de híbrido inválido.")
    return (
        hybrid_name
        if _ranking(hybrid_metrics) > _ranking(visual_metrics)
        else VISUAL_ONLY_NAME
    )


def classify_incremental_signal(hybrid_correct: int, hybrid_only_correct: int) -> str:
    if hybrid_correct > 50:
        return "POSITIVE_INCREMENTAL_SIGNAL"
    if hybrid_correct == 50 and hybrid_only_correct >= 1:
        return "NEUTRAL_COMPLEMENTARY_SIGNAL"
    if hybrid_correct < 50 and hybrid_only_correct >= 1:
        return "COMPLEMENTARY_BUT_LOWER_GLOBAL_ACCURACY"
    return "NO_INCREMENTAL_SIGNAL"


def analyze_hybrid_pair(
    first: tuple[SamplePrediction, ...],
    second: tuple[SamplePrediction, ...],
    first_name: str,
    second_name: str,
) -> dict:
    analysis = analyze_paired_errors(_paired(first, second))
    return {
        "first_model": first_name,
        "second_model": second_name,
        "total_sample_count": analysis.total_sample_count,
        "both_correct_count": analysis.both_correct_count,
        "first_only_correct_count": analysis.dtw_only_correct_count,
        "second_only_correct_count": analysis.tcn_only_correct_count,
        "both_wrong_count": analysis.both_wrong_count,
        "agreement_count": analysis.agreement_count,
        "disagreement_count": analysis.disagreement_count,
        "disagreement_samples": [
            {
                "sample_id": item.sample_id,
                "session_id": item.validation_session_id,
                "expected_label": item.expected_label,
                "first_predicted_label": item.dtw_predicted_label,
                "second_predicted_label": item.tcn_predicted_label,
                "first_correct": item.dtw_correct,
                "second_correct": item.tcn_correct,
            }
            for item in analysis.paired_samples
            if not item.prediction_agreement
        ],
    }


def analyze_hybrid_triple(
    current: tuple[SamplePrediction, ...],
    swinlip: tuple[SamplePrediction, ...],
    hybrid: tuple[SamplePrediction, ...],
) -> dict:
    """Reusa as contagens triplas da 6.5 sem criar preditor oráculo."""
    base = analyze_triple(current, hybrid, swinlip)
    return {key: value for key, value in base.items() if key != "samples"} | {
        "samples": [
            {
                "sample_id": row["sample_id"],
                "session_id": row["session_id"],
                "expected_label": row["expected_label"],
                "current_dtw_correct": row["current_dtw_correct"],
                "swinlip_linear_correct": row["swinlip_linear_correct"],
                "hybrid_correct": row["legacy_dtw_correct"],
            }
            for row in base["samples"]
        ]
    }


def _fold_class_counts(predictions: tuple[SamplePrediction, ...]) -> list[dict]:
    return [
        {
            "validation_session_id": session,
            "correct_counts": [
                sum(
                    row.correct
                    and row.validation_session_id == session
                    and row.expected_label_index == index
                    for row in predictions
                )
                for index in range(6)
            ],
        }
        for session in SESSION_IDS
    ]


def build_hybrid_loso_report(
    samples: tuple[HybridSample, ...],
    distance_fn: Callable[[object, object], float] = raw_current_dtw_distance,
) -> dict:
    """Treina seis cabeças independentes em três folds com features congeladas."""
    _validate_hybrid_samples(samples)
    folds = build_leave_one_session_out_folds(samples, SESSION_IDS)
    stats = {item.sample_id: landmark_stats(item.features) for item in samples}
    distance_cache: dict[tuple[str, str], float] = {}

    def cached_distance(first: HybridSample, second: HybridSample) -> float:
        key = tuple(sorted((first.sample_id, second.sample_id)))
        if key not in distance_cache:
            distance_cache[key] = float(distance_fn(first, second))
        return distance_cache[key]

    predictions_a = []
    predictions_b = []
    distance_by_id = {}
    evidence_by_id = {}
    diagnostics_a = []
    diagnostics_b = []
    fold_details = []
    for fold in folds:
        if len(fold.train) != 36 or len(fold.validation) != 18:
            raise ValueError("Fold híbrido deve possuir 36/18 amostras.")
        training_sessions = {item.session_id for item in fold.train}
        if fold.validation_session_id in training_sessions:
            raise ValueError("Vazamento de sessão no fold híbrido.")
        if Counter(item.label_index for item in fold.train) != Counter(
            {index: 6 for index in range(6)}
        ):
            raise ValueError("Fold híbrido exige seis amostras de treino por classe.")
        fold_details.append(
            {
                "validation_session_id": fold.validation_session_id,
                "training_session_ids": sorted(training_sessions),
                "training_count": 36,
                "validation_count": 18,
                "training_sample_ids": [item.sample_id for item in fold.train],
                "validation_sample_ids": [item.sample_id for item in fold.validation],
            }
        )

        def geometry_feature(sample: HybridSample) -> np.ndarray:
            distances = class_minimum_dtw_distances(sample, fold.train, cached_distance)
            evidence = normalized_reciprocal_evidence(distances)
            if sample.session_id == fold.validation_session_id:
                distance_by_id[sample.sample_id] = distances.tolist()
                evidence_by_id[sample.sample_id] = evidence.tolist()
            return equal_energy_fusion(sample.clip_embedding, evidence, 1670)

        def landmark_feature(sample: HybridSample) -> np.ndarray:
            return equal_energy_fusion(
                sample.clip_embedding, stats[sample.sample_id][0], 1984
            )

        train_a = np.stack([geometry_feature(item) for item in fold.train])
        train_b = np.stack([landmark_feature(item) for item in fold.train])
        targets = np.asarray([item.label_index for item in fold.train], dtype=np.int64)
        model_a, training_a = train_hybrid_linear(train_a, targets)
        model_b, training_b = train_hybrid_linear(train_b, targets)
        diagnostics_a.append(
            {"validation_session_id": fold.validation_session_id, **training_a}
        )
        diagnostics_b.append(
            {"validation_session_id": fold.validation_session_id, **training_b}
        )
        for item in fold.validation:
            predicted_a, _ = predict_hybrid_linear(model_a, geometry_feature(item))
            predicted_b, _ = predict_hybrid_linear(model_b, landmark_feature(item))
            predictions_a.append(_prediction(item, predicted_a))
            predictions_b.append(_prediction(item, predicted_b))
    a = tuple(predictions_a)
    b = tuple(predictions_b)
    metrics = calculate_paired_metrics(_paired(a, b))
    a_metrics = asdict(metrics.dtw)
    b_metrics = asdict(metrics.tcn)
    return {
        "sample_count": 54,
        "labels": list(DEFAULT_VISUAL_LABELS),
        "session_ids": list(SESSION_IDS),
        "folds": fold_details,
        "candidates": {
            A_NAME: {
                "metrics": a_metrics,
                "fold_class_correct_counts": _fold_class_counts(a),
                "training_diagnostics": diagnostics_a,
                "predictions": [
                    {
                        **asdict(row),
                        "session_id": row.validation_session_id,
                        "dtw_distances": distance_by_id[row.sample_id],
                        "evidence_values": evidence_by_id[row.sample_id],
                    }
                    for row in a
                ],
            },
            B_NAME: {
                "metrics": b_metrics,
                "fold_class_correct_counts": _fold_class_counts(b),
                "training_diagnostics": diagnostics_b,
                "predictions": [
                    {
                        **asdict(row),
                        "session_id": row.validation_session_id,
                        "landmark_summary_sha256": stats[row.sample_id][1],
                        "landmark_summary_norm": stats[row.sample_id][2],
                    }
                    for row in b
                ],
            },
        },
        "paired_candidates": analyze_hybrid_pair(a, b, A_NAME, B_NAME),
        "development_preferred_hybrid_candidate": select_preferred_hybrid(
            a_metrics, b_metrics
        ),
        "dtw_unique_pair_count": len(distance_cache),
    }


def _predictions_from_rows(rows: list[dict]) -> tuple[SamplePrediction, ...]:
    fields = SamplePrediction.__dataclass_fields__
    return tuple(SamplePrediction(**{key: row[key] for key in fields}) for row in rows)


def complete_hybrid_report(report: dict, preflight: dict) -> dict:
    preferred = report["development_preferred_hybrid_candidate"]
    hybrid = _predictions_from_rows(report["candidates"][preferred]["predictions"])
    swinlip = preflight["swinlip_predictions"]
    current = preflight["current_predictions"]
    vs_visual = analyze_hybrid_pair(hybrid, swinlip, preferred, VISUAL_ONLY_NAME)
    vs_current = analyze_hybrid_pair(hybrid, current, preferred, "CURRENT_DTW")
    report.update(
        {
            "preferred_hybrid_vs_visual_only": vs_visual,
            "preferred_hybrid_vs_current_dtw": vs_current,
            "triple_comparison": analyze_hybrid_triple(current, swinlip, hybrid),
            "development_preferred_positive_classifier": select_positive_classifier(
                preflight["swinlip_metrics"],
                report["candidates"][preferred]["metrics"],
                preferred,
            ),
            "incremental_signal_classification": classify_incremental_signal(
                report["candidates"][preferred]["metrics"]["correct_count"],
                vs_visual["first_only_correct_count"],
            ),
            "visual_only_reference_metrics": preflight["swinlip_metrics"],
            "current_dtw_reference_metrics": preflight["current_metrics"],
        }
    )
    return report


def preflight_hybrid_loso(repository_root: Path) -> dict:
    """Restringe ambos os conjuntos de paths antes de abrir qualquer NPZ."""
    root = Path(repository_root).resolve()
    manifest_path = root / OUTPUT_MANIFEST_RELATIVE_PATH
    if sha256_file(manifest_path) != EMBEDDING_MANIFEST_SHA256:
        raise ValueError("SHA-256 do manifesto SwinLip não é o congelado.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    select_authorized_embedding_paths(root, manifest)
    visual_samples, visual_paths = load_authorized_visual_samples(
        root / DATASET_RELATIVE_PATH
    )
    segmented, segmentation = segment_development_samples(visual_samples)
    clips, embedding_hashes = load_authorized_clip_embeddings(root, manifest)
    if set(clips) != {item.sample_id for item in segmented}:
        raise ValueError("IDs de embeddings e landmarks não pareiam 1:1.")
    current, current_metrics, swinlip = _load_references(root, visual_samples)
    legacy_path = root / LEGACY_RESULT_RELATIVE_PATH
    if sha256_file(legacy_path) != LEGACY_RESULT_SHA256:
        raise ValueError("SHA-256 do snapshot de NPZ da Task 6.5 divergiu.")
    legacy_report = json.loads(legacy_path.read_text(encoding="utf-8"))
    visual_hashes = {
        path.relative_to(root).as_posix(): sha256_file(path) for path in visual_paths
    }
    if visual_hashes != legacy_report["source_dataset_sha256"]:
        raise ValueError("Hashes dos 54 NPZ modernos divergiram da Task 6.5.")
    swinlip_report = json.loads(
        (root / SWINLIP_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    swinlip_metrics = swinlip_report["probes"]["LINEAR_PROBE"]["metrics"]
    samples = tuple(
        HybridSample(
            sample_id=item.sample_id,
            session_id=item.session_id,
            label=item.label,
            label_index=DEFAULT_VISUAL_LABELS.index(item.label),
            clip_embedding=clips[item.sample_id],
            features=item.features,
        )
        for item in segmented
    )
    _validate_hybrid_samples(samples)
    return {
        "samples": samples,
        "segmentation": segmentation,
        "embedding_manifest_sha256": EMBEDDING_MANIFEST_SHA256,
        "embedding_hashes": embedding_hashes,
        "visual_hashes": visual_hashes,
        "current_predictions": current,
        "current_metrics": current_metrics,
        "swinlip_predictions": swinlip,
        "swinlip_metrics": swinlip_metrics,
    }


def run_real_hybrid_loso(repository_root: Path) -> dict:
    """Avalia uma vez com código versionado e persiste só após consistência total."""
    root = Path(repository_root).resolve()
    output_path = root / OUTPUT_RELATIVE_PATH
    if output_path.exists():
        raise FileExistsError("Resultado LOSO híbrido já existe; não reexecutar.")
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip()
    if status:
        raise ValueError("O worktree versionável precisa estar limpo antes do LOSO.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    preflight = preflight_hybrid_loso(root)
    report = complete_hybrid_report(
        build_hybrid_loso_report(preflight["samples"]), preflight
    )
    report.update(
        {
            "format_version": 1,
            "evaluation_count": 1,
            "code_commit": commit,
            "worktree_clean_before_evaluation": True,
            "heldouts_used": False,
            "embedding_manifest_sha256": preflight["embedding_manifest_sha256"],
            "embedding_hashes": preflight["embedding_hashes"],
            "visual_npz_hashes": preflight["visual_hashes"],
            "reference_sha256": {
                "CURRENT_DTW": CURRENT_DTW_SHA256,
                VISUAL_ONLY_NAME: SWINLIP_SHA256,
                "cycle_06_legacy_result": LEGACY_RESULT_SHA256,
            },
            "protocol": {
                "clip_embedding_dimension": 1664,
                "normalization_epsilon": HYBRID_EPSILON,
                "segmentation": preflight["segmentation"],
                "A": "clip_l2_and_reciprocal_class_minimum_current_dtw_equal_energy",
                "A_input_dimension": 1670,
                "B": "clip_l2_and_landmark_mean_std_ddof0_equal_energy",
                "B_input_dimension": 1984,
                "linear_training": {
                    "seed": LINEAR_SEED,
                    "device": "cpu",
                    "epochs": LINEAR_EPOCHS,
                    "batch_size": 36,
                    "optimizer": "AdamW",
                    "learning_rate": LINEAR_LEARNING_RATE,
                    "weight_decay": LINEAR_WEIGHT_DECAY,
                    "loss": "CrossEntropyLoss",
                    "gradient_clip_norm": LINEAR_GRADIENT_CLIP_NORM,
                    "checkpoint_rule": "epoch_500_only",
                },
            },
        }
    )
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    return report
