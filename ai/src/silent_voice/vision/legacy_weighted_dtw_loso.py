"""LOSO moderno do matcher legado, com referências de desenvolvimento congeladas."""

import json
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

from silent_voice.vision.dtw_tcn_comparison import calculate_paired_metrics
from silent_voice.vision.dtw_tcn_error_analysis import analyze_paired_errors
from silent_voice.vision.dtw_tcn_predictions import PairedPredictions, SamplePrediction
from silent_voice.vision.feature_sample import VisualFeatureSample
from silent_voice.vision.feature_sample_storage import load_visual_feature_sample
from silent_voice.vision.legacy_weighted_dtw import (
    LEGACY_K,
    LEGACY_MOVEMENT_WEIGHT,
    LEGACY_SHAPE_WEIGHT,
    predict_legacy_weighted_dtw,
)
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.visual_cross_validation import (
    build_leave_one_session_out_folds,
)
from silent_voice.vision.visual_experiment_defaults import (
    SESSION_IDS,
    build_default_segmentation_config,
)
from silent_voice.vision.visual_sample_segmentation import (
    segment_visual_feature_sample,
)
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

EXPERIMENT_NAME = "LEGACY_WEIGHTED_DTW_K3"
DATASET_RELATIVE_PATH = Path("data/processed/visual")
CURRENT_DTW_RELATIVE_PATH = Path("data/processed/evaluation/dtw_tcn_comparison.json")
SWINLIP_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_swinlip_frozen_probe_loso.json"
)
OUTPUT_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_legacy_weighted_dtw_loso.json"
)
CURRENT_DTW_SHA256 = "5948eca0e3f14de1dfa8be6c3daad66393060430d69b3fb6b7761593795048cf"
SWINLIP_SHA256 = "839bd866e6fe398df81b33c506e4fd0ce1405fce1c1e1390f4b5660bf69e1c9e"
LEGACY_SOURCE_REPOSITORY = "joaoxaviersilva/silent_voice"
LEGACY_SOURCE_BRANCH = "feature/pipeline-visao"
LEGACY_SOURCE_COMMIT = "865c86e328e924bdad9504f6f0ee9bcb78db67a3"


def validate_development_samples(samples: tuple[VisualFeatureSample, ...]) -> None:
    """Exige os 54 positivos modernos e exclui qualquer outra sessão."""
    if len(samples) != 54 or len({item.sample_id for item in samples}) != 54:
        raise ValueError("O LOSO exige exatamente 54 sample_id únicos.")
    if Counter(item.session_id for item in samples) != Counter(
        {session: 18 for session in SESSION_IDS}
    ):
        raise ValueError("Sessões fora do desenvolvimento ou contagens divergentes.")
    if Counter(item.label for item in samples) != Counter(
        {label: 9 for label in DEFAULT_VISUAL_LABELS}
    ):
        raise ValueError("Cada classe deve possuir nove amostras.")
    if Counter((item.session_id, item.label) for item in samples) != Counter(
        {
            (session, label): 3
            for session in SESSION_IDS
            for label in DEFAULT_VISUAL_LABELS
        }
    ):
        raise ValueError("Cada sessão deve possuir três amostras por classe.")


def _load_modern_development_samples(
    dataset_path: Path,
) -> tuple[tuple[VisualFeatureSample, ...], tuple[Path, ...]]:
    """Filtra paths por sessão antes de abrir qualquer NPZ."""
    path = Path(dataset_path)
    if not path.is_dir():
        raise FileNotFoundError(f"Diretório do dataset visual não encontrado: {path}")
    paths = tuple(
        sorted(
            item
            for item in path.rglob("*.npz")
            if any(f"_{session}_" in item.stem for session in SESSION_IDS)
        )
    )
    if not paths:
        raise ValueError("Dataset de desenvolvimento sem NPZ sessao_01–03.")
    samples = tuple(load_visual_feature_sample(item) for item in paths)
    if any(
        sample.sample_id != item.stem
        for sample, item in zip(samples, paths, strict=True)
    ):
        raise ValueError("sample_id do NPZ diverge do nome do arquivo.")
    return samples, paths


def segment_development_samples(
    samples: tuple[VisualFeatureSample, ...],
) -> tuple[tuple[VisualFeatureSample, ...], dict]:
    """Aplica a segmentação congelada e exige 54 detecções sem fallback."""
    validate_development_samples(samples)
    config = build_default_segmentation_config()
    results = tuple(segment_visual_feature_sample(sample, config) for sample in samples)
    detected = sum(item.segment.detected for item in results)
    if detected != 54:
        raise ValueError("Segmentação divergiu: esperado 54/54 sem fallback.")
    segmented = tuple(item.sample for item in results)
    lengths = [item.frame_count for item in segmented]
    return segmented, {
        "config": asdict(config),
        "detected_count": detected,
        "fallback_count": len(results) - detected,
        "min_frames": min(lengths),
        "mean_frames": float(np.mean(lengths)),
        "max_frames": max(lengths),
    }


def _prediction(sample: VisualFeatureSample, predicted_index: int) -> SamplePrediction:
    expected_index = DEFAULT_VISUAL_LABELS.index(sample.label)
    return SamplePrediction(
        sample_id=sample.sample_id,
        validation_session_id=sample.session_id,
        expected_label=sample.label,
        expected_label_index=expected_index,
        predicted_label=DEFAULT_VISUAL_LABELS[predicted_index],
        predicted_label_index=predicted_index,
        correct=predicted_index == expected_index,
    )


def _paired(
    first: tuple[SamplePrediction, ...], second: tuple[SamplePrediction, ...]
) -> PairedPredictions:
    return PairedPredictions(DEFAULT_VISUAL_LABELS, first, second)


def _fold_class_correct_counts(predictions: tuple[SamplePrediction, ...]) -> list[dict]:
    return [
        {
            "validation_session_id": session,
            "correct_counts": [
                sum(
                    item.correct
                    and item.validation_session_id == session
                    and item.expected_label_index == index
                    for item in predictions
                )
                for index in range(6)
            ],
        }
        for session in SESSION_IDS
    ]


def build_legacy_loso_report(
    segmented_samples: tuple[VisualFeatureSample, ...],
) -> dict:
    """Avalia o matcher uma vez por sample com treino isolado por sessão."""
    validate_development_samples(segmented_samples)
    folds = build_leave_one_session_out_folds(segmented_samples, SESSION_IDS)
    predictions = []
    scores_by_id = {}
    fold_details = []
    for fold in folds:
        if len(fold.train) != 36 or len(fold.validation) != 18:
            raise ValueError("Fold LOSO deve possuir 36/18 amostras.")
        training_sessions = sorted({item.session_id for item in fold.train})
        if fold.validation_session_id in training_sessions:
            raise ValueError("Vazamento da sessão de validação nas templates.")
        training_counts = [
            sum(item.label == label for item in fold.train)
            for label in DEFAULT_VISUAL_LABELS
        ]
        validation_counts = [
            sum(item.label == label for item in fold.validation)
            for label in DEFAULT_VISUAL_LABELS
        ]
        if training_counts != [6] * 6 or validation_counts != [3] * 6:
            raise ValueError("Contagens por classe do fold LOSO divergentes.")
        templates = tuple(
            (item.sample_id, DEFAULT_VISUAL_LABELS.index(item.label), item.features)
            for item in fold.train
        )
        fold_details.append(
            {
                "validation_session_id": fold.validation_session_id,
                "training_session_ids": training_sessions,
                "training_count": 36,
                "validation_count": 18,
                "training_class_counts": training_counts,
                "validation_class_counts": validation_counts,
                "training_sample_ids": [item.sample_id for item in fold.train],
                "validation_sample_ids": [item.sample_id for item in fold.validation],
            }
        )
        for sample in fold.validation:
            predicted_index, scores = predict_legacy_weighted_dtw(
                sample.features, templates
            )
            predictions.append(_prediction(sample, predicted_index))
            scores_by_id[sample.sample_id] = scores
    result = tuple(predictions)
    metrics = asdict(calculate_paired_metrics(_paired(result, result)).dtw)
    return {
        "sample_count": 54,
        "labels": list(DEFAULT_VISUAL_LABELS),
        "session_ids": list(SESSION_IDS),
        "folds": fold_details,
        "metrics": metrics,
        "fold_class_correct_counts": _fold_class_correct_counts(result),
        "predictions": [
            {
                **asdict(item),
                "session_id": item.validation_session_id,
                "class_scores": list(scores_by_id[item.sample_id]),
            }
            for item in result
        ],
    }


def _validated_prediction_map(
    predictions: tuple[SamplePrediction, ...],
) -> dict[str, SamplePrediction]:
    calculate_paired_metrics(_paired(predictions, predictions))
    return {item.sample_id: item for item in predictions}


def analyze_legacy_pair(
    legacy: tuple[SamplePrediction, ...],
    other: tuple[SamplePrediction, ...],
    other_name: str,
) -> dict:
    """Reusa a análise pareada existente e lista todas as discordâncias."""
    if other_name not in ("CURRENT_DTW", "SWINLIP_LINEAR_PROBE"):
        raise ValueError("Nome da referência pareada inválido.")
    analysis = analyze_paired_errors(_paired(legacy, other))
    return {
        "other_model": other_name,
        "total_sample_count": analysis.total_sample_count,
        "both_correct_count": analysis.both_correct_count,
        "legacy_only_correct_count": analysis.dtw_only_correct_count,
        "other_only_correct_count": analysis.tcn_only_correct_count,
        "both_wrong_count": analysis.both_wrong_count,
        "agreement_count": analysis.agreement_count,
        "disagreement_count": analysis.disagreement_count,
        "disagreement_samples": [
            {
                "sample_id": item.sample_id,
                "session_id": item.validation_session_id,
                "expected_label": item.expected_label,
                "legacy_predicted_label": item.dtw_predicted_label,
                "other_predicted_label": item.tcn_predicted_label,
                "legacy_correct": item.dtw_correct,
                "other_correct": item.tcn_correct,
            }
            for item in analysis.paired_samples
            if not item.prediction_agreement
        ],
    }


def analyze_triple(
    current: tuple[SamplePrediction, ...],
    legacy: tuple[SamplePrediction, ...],
    swinlip: tuple[SamplePrediction, ...],
) -> dict:
    """Conta a união oráculo somente como limite descritivo, sem modelo novo."""
    current_by_id = _validated_prediction_map(current)
    legacy_by_id = _validated_prediction_map(legacy)
    swinlip_by_id = _validated_prediction_map(swinlip)
    if (
        current_by_id.keys() != legacy_by_id.keys()
        or current_by_id.keys() != swinlip_by_id.keys()
    ):
        raise ValueError("As três previsões devem possuir os mesmos sample_id.")
    rows = []
    for sample_id in sorted(current_by_id):
        items = (
            current_by_id[sample_id],
            legacy_by_id[sample_id],
            swinlip_by_id[sample_id],
        )
        if (
            len(
                {
                    (item.validation_session_id, item.expected_label_index)
                    for item in items
                }
            )
            != 1
        ):
            raise ValueError(f"Rótulo ou sessão divergente para {sample_id}.")
        rows.append(
            {
                "sample_id": sample_id,
                "session_id": items[0].validation_session_id,
                "expected_label": items[0].expected_label,
                "current_dtw_correct": items[0].correct,
                "legacy_dtw_correct": items[1].correct,
                "swinlip_linear_correct": items[2].correct,
            }
        )
    correct_per_row = [
        sum(
            (
                row["current_dtw_correct"],
                row["legacy_dtw_correct"],
                row["swinlip_linear_correct"],
            )
        )
        for row in rows
    ]
    return {
        "total_sample_count": len(rows),
        "all_three_correct_count": correct_per_row.count(3),
        "all_three_wrong_count": correct_per_row.count(0),
        "exactly_two_correct_count": correct_per_row.count(2),
        "exactly_one_correct_count": correct_per_row.count(1),
        "development_oracle_union_correct": sum(value > 0 for value in correct_per_row),
        "samples": rows,
    }


def select_preferred_geometric_baseline(
    current_metrics: dict, legacy_metrics: dict
) -> str:
    """Global, pior fold, pior classe; empate final mantém CURRENT_DTW."""

    def rank(metrics: dict) -> tuple[float, float, float]:
        return (
            metrics["accuracy"],
            min(row["accuracy"] for row in metrics["folds"]),
            min(row["accuracy"] for row in metrics["classes"]),
        )

    if rank(legacy_metrics) > rank(current_metrics):
        return EXPERIMENT_NAME
    return "CURRENT_DTW"


def _parse_reference_rows(
    rows: list[dict],
    samples: tuple[VisualFeatureSample, ...],
    predicted_prefix: str,
) -> tuple[SamplePrediction, ...]:
    by_id = {row["sample_id"]: row for row in rows}
    if len(rows) != 54 or len(by_id) != 54:
        raise ValueError("Referência deve ter 54 sample_id únicos.")
    if set(by_id) != {item.sample_id for item in samples}:
        raise ValueError("Referência não pareia com os 54 NPZ modernos.")
    predictions = []
    for sample in samples:
        row = by_id[sample.sample_id]
        if (
            row["validation_session_id"] != sample.session_id
            or row["expected_label"] != sample.label
            or row["expected_label_index"] != DEFAULT_VISUAL_LABELS.index(sample.label)
        ):
            raise ValueError("Rótulo ou sessão da referência diverge do NPZ.")
        predictions.append(
            SamplePrediction(
                sample_id=sample.sample_id,
                validation_session_id=sample.session_id,
                expected_label=sample.label,
                expected_label_index=row["expected_label_index"],
                predicted_label=row[f"{predicted_prefix}predicted_label"],
                predicted_label_index=row[f"{predicted_prefix}predicted_label_index"],
                correct=row[f"{predicted_prefix}correct"],
            )
        )
    result = tuple(predictions)
    _validated_prediction_map(result)
    return result


def _load_references(
    root: Path, samples: tuple[VisualFeatureSample, ...]
) -> tuple[tuple[SamplePrediction, ...], dict, tuple[SamplePrediction, ...]]:
    current_path = root / CURRENT_DTW_RELATIVE_PATH
    swinlip_path = root / SWINLIP_RELATIVE_PATH
    if sha256_file(current_path) != CURRENT_DTW_SHA256:
        raise ValueError("SHA-256 do CURRENT_DTW histórico divergiu.")
    if sha256_file(swinlip_path) != SWINLIP_SHA256:
        raise ValueError("SHA-256 do SwinLip frozen probe divergiu.")
    current_report = json.loads(current_path.read_text(encoding="utf-8"))
    swinlip_report = json.loads(swinlip_path.read_text(encoding="utf-8"))
    current_metrics = current_report["dtw_metrics"]
    if (
        current_report["dtw_baseline"]["name"] != "LEGACY_RAW"
        or current_report["labels"] != list(DEFAULT_VISUAL_LABELS)
        or current_report["allowed_sessions"] != list(SESSION_IDS)
        or current_metrics["correct_count"] != 43
        or current_metrics["total_sample_count"] != 54
    ):
        raise ValueError("Contrato CURRENT_DTW histórico inválido.")
    if (
        swinlip_report["development_preferred_frozen_probe"] != "LINEAR_PROBE"
        or swinlip_report["labels"] != list(DEFAULT_VISUAL_LABELS)
        or swinlip_report["session_ids"] != list(SESSION_IDS)
        or swinlip_report["sample_count"] != 54
        or swinlip_report["heldouts_used"] is not False
        or swinlip_report["probes"]["LINEAR_PROBE"]["metrics"]["correct_count"] != 50
    ):
        raise ValueError("Contrato SwinLip frozen probe inválido.")
    current = _parse_reference_rows(
        current_report["paired_analysis"]["paired_samples"], samples, "dtw_"
    )
    swinlip = _parse_reference_rows(
        swinlip_report["probes"]["LINEAR_PROBE"]["predictions"], samples, ""
    )
    if (
        sum(item.correct for item in current) != 43
        or sum(item.correct for item in swinlip) != 50
    ):
        raise ValueError("Acertos históricos divergentes dos artefatos.")
    return current, current_metrics, swinlip


def preflight_legacy_loso(repository_root: Path) -> dict:
    """Valida dataset, segmentação e referências antes de medir o matcher."""
    root = Path(repository_root).resolve()
    dataset_path = root / DATASET_RELATIVE_PATH
    samples, sample_paths = _load_modern_development_samples(dataset_path)
    validate_development_samples(samples)
    segmented, segmentation = segment_development_samples(samples)
    current, current_metrics, swinlip = _load_references(root, samples)
    hashes = {
        path.relative_to(root).as_posix(): sha256_file(path) for path in sample_paths
    }
    return {
        "segmented_samples": segmented,
        "segmentation": segmentation,
        "current_predictions": current,
        "current_metrics": current_metrics,
        "swinlip_predictions": swinlip,
        "dataset_hashes": hashes,
    }


def run_real_legacy_loso(repository_root: Path) -> dict:
    """Executa o experimento uma vez, com commit limpo, e persiste ao final."""
    root = Path(repository_root).resolve()
    output_path = root / OUTPUT_RELATIVE_PATH
    if output_path.exists():
        raise FileExistsError("Resultado LOSO legado já existe; não reexecutar.")
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip()
    if status:
        raise ValueError("O worktree versionável precisa estar limpo antes do LOSO.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    preflight = preflight_legacy_loso(root)
    report = build_legacy_loso_report(preflight["segmented_samples"])
    legacy_predictions = tuple(
        SamplePrediction(
            **{
                key: value
                for key, value in row.items()
                if key not in ("session_id", "class_scores")
            }
        )
        for row in report["predictions"]
    )
    current = preflight["current_predictions"]
    swinlip = preflight["swinlip_predictions"]
    report.update(
        {
            "format_version": 1,
            "evaluation_count": 1,
            "experiment_name": EXPERIMENT_NAME,
            "code_commit": commit,
            "worktree_clean_before_evaluation": True,
            "heldouts_used": False,
            "source_provenance": {
                "repository": LEGACY_SOURCE_REPOSITORY,
                "branch": LEGACY_SOURCE_BRANCH,
                "commit": LEGACY_SOURCE_COMMIT,
                "historical_evaluation": "leave-one-sample-out, three classes",
            },
            "protocol": {
                "dataset": DATASET_RELATIVE_PATH.as_posix(),
                "segmentation": preflight["segmentation"],
                "shape_weight": LEGACY_SHAPE_WEIGHT,
                "movement_weight": LEGACY_MOVEMENT_WEIGHT,
                "k": LEGACY_K,
                "frame_distance": "sqrt(weighted_shape_mse_plus_movement_mse)",
                "dtw": "unrestricted_accumulated_cost_divided_by_length_sum",
                "class_score": "mean_of_three_smallest_distances",
            },
            "source_dataset_sha256": preflight["dataset_hashes"],
            "current_dtw_reference_sha256": CURRENT_DTW_SHA256,
            "swinlip_reference_sha256": SWINLIP_SHA256,
            "current_dtw_reference_correct_count": 43,
            "swinlip_linear_reference_correct_count": 50,
            "legacy_vs_current_dtw": analyze_legacy_pair(
                legacy_predictions, current, "CURRENT_DTW"
            ),
            "legacy_vs_swinlip_linear": analyze_legacy_pair(
                legacy_predictions, swinlip, "SWINLIP_LINEAR_PROBE"
            ),
            "triple_comparison": analyze_triple(current, legacy_predictions, swinlip),
            "development_preferred_geometric_baseline": (
                select_preferred_geometric_baseline(
                    preflight["current_metrics"], report["metrics"]
                )
            ),
        }
    )
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    return report
