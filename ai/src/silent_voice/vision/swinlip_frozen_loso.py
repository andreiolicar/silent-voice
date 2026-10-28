"""LOSO dos probes de clip SwinLip sobre três sessões de desenvolvimento."""

import json
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

from silent_voice.vision.dtw_tcn_comparison import calculate_paired_metrics
from silent_voice.vision.dtw_tcn_error_analysis import analyze_paired_errors
from silent_voice.vision.dtw_tcn_predictions import PairedPredictions, SamplePrediction
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.swinlip_embedding_dataset import (
    OUTPUT_MANIFEST_RELATIVE_PATH,
    validate_embedding_dataset,
)
from silent_voice.vision.swinlip_frozen_probe import (
    EMBEDDING_DIMENSION,
    EMBEDDING_NORMALIZATION_EPSILON,
    LINEAR_EPOCHS,
    LINEAR_GRADIENT_CLIP_NORM,
    LINEAR_LEARNING_RATE,
    LINEAR_SEED,
    LINEAR_WEIGHT_DECAY,
    ProbeSample,
    predict_centroid,
    predict_linear,
    train_centroids,
    train_linear_probe,
)
from silent_voice.vision.swinlip_frozen_encoder import CHECKPOINT_SHA256, SOURCE_COMMIT
from silent_voice.vision.visual_cross_validation import (
    build_leave_one_session_out_folds,
)
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

CENTROID_NAME = "COSINE_NEAREST_CENTROID"
LINEAR_NAME = "LINEAR_PROBE"
EMBEDDING_MANIFEST_SHA256 = (
    "13a45412538e9a67756884dbafcdb3d22bbfd0126892dcf2e0f4e8f52db49b17"
)
OUTPUT_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_swinlip_frozen_probe_loso.json"
)
HISTORICAL_DTW_RELATIVE_PATH = Path("data/processed/evaluation/dtw_tcn_comparison.json")


def validate_probe_samples(samples: tuple[ProbeSample, ...]) -> None:
    """Garante a partição fechada de 54 clips sem consultar held-outs."""
    if len(samples) != 54 or len({item.sample_id for item in samples}) != 54:
        raise ValueError("Os probes exigem 54 sample_id únicos.")
    if Counter(item.session_id for item in samples) != Counter(
        {session: 18 for session in SESSION_IDS}
    ):
        raise ValueError("Sessões fora do development ou contagens divergentes.")
    if Counter(item.label_index for item in samples) != Counter(
        {index: 9 for index in range(6)}
    ):
        raise ValueError("Cada classe deve ter nove amostras.")
    if Counter((item.session_id, item.label_index) for item in samples) != Counter(
        {(session, index): 3 for session in SESSION_IDS for index in range(6)}
    ):
        raise ValueError("Cada classe deve ter três amostras por sessão.")
    for item in samples:
        if (
            not item.sample_id
            or item.label_index not in range(6)
            or item.label != DEFAULT_VISUAL_LABELS[item.label_index]
            or not isinstance(item.clip_embedding, np.ndarray)
            or item.clip_embedding.shape != (EMBEDDING_DIMENSION,)
            or item.clip_embedding.dtype != np.float32
            or not np.isfinite(item.clip_embedding).all()
        ):
            raise ValueError("Contrato de clip embedding ou label inválido.")


def _prediction(sample: ProbeSample, predicted_index: int) -> SamplePrediction:
    return SamplePrediction(
        sample_id=sample.sample_id,
        validation_session_id=sample.session_id,
        expected_label=sample.label,
        expected_label_index=sample.label_index,
        predicted_label=DEFAULT_VISUAL_LABELS[predicted_index],
        predicted_label_index=predicted_index,
        correct=predicted_index == sample.label_index,
    )


def _pair_contract(
    first: tuple[SamplePrediction, ...], second: tuple[SamplePrediction, ...]
) -> PairedPredictions:
    return PairedPredictions(
        labels=DEFAULT_VISUAL_LABELS,
        dtw_predictions=first,
        tcn_predictions=second,
    )


def analyze_probe_pair(
    centroid_predictions: tuple[SamplePrediction, ...],
    linear_predictions: tuple[SamplePrediction, ...],
) -> dict:
    """Reusa o contrato pareado da Task 4.8 com nomes dos probes atuais."""
    analysis = analyze_paired_errors(
        _pair_contract(centroid_predictions, linear_predictions)
    )
    category_names = {
        "BOTH_CORRECT": "BOTH_CORRECT",
        "DTW_ONLY_CORRECT": "CENTROID_ONLY_CORRECT",
        "TCN_ONLY_CORRECT": "LINEAR_ONLY_CORRECT",
        "BOTH_WRONG": "BOTH_WRONG",
    }
    return {
        "total_sample_count": analysis.total_sample_count,
        "both_correct_count": analysis.both_correct_count,
        "centroid_only_correct_count": analysis.dtw_only_correct_count,
        "linear_only_correct_count": analysis.tcn_only_correct_count,
        "both_wrong_count": analysis.both_wrong_count,
        "agreement_count": analysis.agreement_count,
        "disagreement_count": analysis.disagreement_count,
        "paired_samples": [
            {
                "sample_id": item.sample_id,
                "session_id": item.validation_session_id,
                "expected_label": item.expected_label,
                "expected_label_index": item.expected_label_index,
                "centroid_predicted_label": item.dtw_predicted_label,
                "centroid_predicted_label_index": item.dtw_predicted_label_index,
                "centroid_correct": item.dtw_correct,
                "linear_predicted_label": item.tcn_predicted_label,
                "linear_predicted_label_index": item.tcn_predicted_label_index,
                "linear_correct": item.tcn_correct,
                "prediction_agreement": item.prediction_agreement,
                "outcome_category": category_names[item.outcome_category.value],
            }
            for item in analysis.paired_samples
        ],
    }


def select_preferred_probe(centroid_metrics: dict, linear_metrics: dict) -> str:
    """Desempata por global, pior fold, pior classe e simplicidade."""

    def ranking(metrics: dict) -> tuple[float, float, float]:
        return (
            metrics["accuracy"],
            min(item["accuracy"] for item in metrics["folds"]),
            min(item["accuracy"] for item in metrics["classes"]),
        )

    if ranking(linear_metrics) > ranking(centroid_metrics):
        return LINEAR_NAME
    return CENTROID_NAME


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


def build_frozen_loso_report(samples: tuple[ProbeSample, ...]) -> dict:
    """Treina cada probe somente nos 36 exemplos dos outros dois folds."""
    validate_probe_samples(samples)
    folds = build_leave_one_session_out_folds(samples, SESSION_IDS)
    centroid_predictions = []
    linear_predictions = []
    centroid_scores = {}
    linear_scores = {}
    training_diagnostics = []
    for fold in folds:
        if len(fold.train) != 36 or len(fold.validation) != 18:
            raise ValueError("Fold LOSO não possui 36/18 amostras.")
        if set(item.session_id for item in fold.train) & set(
            item.session_id for item in fold.validation
        ):
            raise ValueError("Vazamento de sessão entre treino e validação.")
        centers = train_centroids(fold.train)
        linear_model, diagnostics = train_linear_probe(fold.train)
        training_diagnostics.append(
            {"validation_session_id": fold.validation_session_id, **diagnostics}
        )
        for sample in fold.validation:
            centroid_index, similarities = predict_centroid(centers, sample)
            linear_index, logits = predict_linear(linear_model, sample)
            centroid_predictions.append(_prediction(sample, centroid_index))
            linear_predictions.append(_prediction(sample, linear_index))
            centroid_scores[sample.sample_id] = similarities
            linear_scores[sample.sample_id] = logits
    centroid = tuple(centroid_predictions)
    linear = tuple(linear_predictions)
    paired = _pair_contract(centroid, linear)
    metrics = calculate_paired_metrics(paired)
    centroid_metrics = asdict(metrics.dtw)
    linear_metrics = asdict(metrics.tcn)
    return {
        "sample_count": len(samples),
        "labels": list(DEFAULT_VISUAL_LABELS),
        "session_ids": list(SESSION_IDS),
        "probes": {
            CENTROID_NAME: {
                "metrics": centroid_metrics,
                "fold_class_correct_counts": _fold_class_correct_counts(centroid),
                "predictions": [
                    {
                        **asdict(item),
                        "similarities": list(centroid_scores[item.sample_id]),
                    }
                    for item in centroid
                ],
            },
            LINEAR_NAME: {
                "metrics": linear_metrics,
                "fold_class_correct_counts": _fold_class_correct_counts(linear),
                "predictions": [
                    {**asdict(item), "logits": list(linear_scores[item.sample_id])}
                    for item in linear
                ],
            },
        },
        "paired_probes": analyze_probe_pair(centroid, linear),
        "linear_training_diagnostics": training_diagnostics,
        "development_preferred_frozen_probe": select_preferred_probe(
            centroid_metrics, linear_metrics
        ),
    }


def read_probe_samples_from_manifest(
    root: Path, manifest: dict
) -> tuple[ProbeSample, ...]:
    """Lê exclusivamente clip_embedding; frame_embeddings nunca entra nos probes."""
    samples = []
    for entry in manifest["samples"]:
        path = Path(root) / entry["embedding_path"]
        with np.load(path, allow_pickle=False) as data:
            clip = np.asarray(data["clip_embedding"]).copy()
        samples.append(
            ProbeSample(
                sample_id=entry["sample_id"],
                session_id=entry["session_id"],
                label=entry["label"],
                label_index=entry["label_index"],
                clip_embedding=clip,
            )
        )
    result = tuple(samples)
    validate_probe_samples(result)
    return result


def preflight_frozen_probe_dataset(
    repository_root: Path,
) -> tuple[tuple[ProbeSample, ...], dict, str]:
    """Verifica hashes e contratos antes de calcular qualquer accuracy real."""
    root = Path(repository_root).resolve()
    manifest_path = root / OUTPUT_MANIFEST_RELATIVE_PATH
    if sha256_file(manifest_path) != EMBEDDING_MANIFEST_SHA256:
        raise ValueError("SHA-256 do manifesto de embeddings não é o congelado.")
    manifest = validate_embedding_dataset(root)
    if (
        manifest.get("source_commit") != SOURCE_COMMIT
        or manifest.get("checkpoint_sha256") != CHECKPOINT_SHA256
        or manifest.get("clip_embedding_shape") != [EMBEDDING_DIMENSION]
        or manifest.get("heldouts_used") is not False
    ):
        raise ValueError("Fonte, checkpoint, dimensão ou partição inconsistentes.")
    return (
        read_probe_samples_from_manifest(root, manifest),
        manifest,
        EMBEDDING_MANIFEST_SHA256,
    )


def load_historical_dtw_predictions(
    path: Path, samples: tuple[ProbeSample, ...]
) -> tuple[SamplePrediction, ...]:
    """Reusa somente o LOSO DTW de desenvolvimento já persistido na 4.8."""
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = report.get("paired_analysis", {}).get("paired_samples", [])
    metrics = report.get("dtw_metrics", {})
    if (
        report.get("labels") != list(DEFAULT_VISUAL_LABELS)
        or report.get("allowed_sessions") != list(SESSION_IDS)
        or report.get("dtw_baseline", {}).get("name") != "LEGACY_RAW"
        or metrics.get("total_sample_count") != 54
        or metrics.get("correct_count") != 43
        or len(rows) != 54
    ):
        raise ValueError("Relatório histórico DTW não corresponde ao baseline LOSO.")
    by_id = {row["sample_id"]: row for row in rows}
    if len(by_id) != 54 or set(by_id) != {item.sample_id for item in samples}:
        raise ValueError("IDs históricos DTW não pareiam com os embeddings.")
    predictions = []
    for sample in samples:
        row = by_id[sample.sample_id]
        if (
            row["validation_session_id"] != sample.session_id
            or row["expected_label"] != sample.label
            or row["expected_label_index"] != sample.label_index
        ):
            raise ValueError("Rótulo ou sessão histórica DTW diverge do embedding.")
        predictions.append(
            SamplePrediction(
                sample_id=sample.sample_id,
                validation_session_id=sample.session_id,
                expected_label=sample.label,
                expected_label_index=sample.label_index,
                predicted_label=row["dtw_predicted_label"],
                predicted_label_index=row["dtw_predicted_label_index"],
                correct=row["dtw_correct"],
            )
        )
    result = tuple(predictions)
    calculate_paired_metrics(_pair_contract(result, result))
    if sum(item.correct for item in result) != 43:
        raise ValueError("Contagem de acertos DTW histórica inconsistente.")
    return result


def compare_to_historical_dtw(
    dtw_predictions: tuple[SamplePrediction, ...],
    swinlip_predictions: tuple[SamplePrediction, ...],
) -> dict:
    analysis = analyze_paired_errors(
        _pair_contract(dtw_predictions, swinlip_predictions)
    )

    def listed(items: tuple) -> list[dict]:
        return [
            {
                "sample_id": item.sample_id,
                "session_id": item.validation_session_id,
                "expected_label": item.expected_label,
                "dtw_predicted_label": item.dtw_predicted_label,
                "swinlip_predicted_label": item.tcn_predicted_label,
            }
            for item in items
        ]

    return {
        "total_sample_count": analysis.total_sample_count,
        "both_correct_count": analysis.both_correct_count,
        "dtw_only_correct_count": analysis.dtw_only_correct_count,
        "swinlip_only_correct_count": analysis.tcn_only_correct_count,
        "both_wrong_count": analysis.both_wrong_count,
        "agreement_count": analysis.agreement_count,
        "disagreement_count": analysis.disagreement_count,
        "dtw_only_correct_samples": listed(analysis.dtw_only_correct_samples),
        "swinlip_only_correct_samples": listed(analysis.tcn_only_correct_samples),
        "both_wrong_samples": listed(analysis.both_wrong_samples),
    }


def classify_transfer_signal(accuracy: float, dtw_comparison: dict | None) -> str:
    if accuracy > 43 / 54:
        return "STRONG_TRANSFER_SIGNAL"
    if accuracy >= 0.70:
        return "PROMISING_TRANSFER_SIGNAL"
    if dtw_comparison is not None:
        exclusive = dtw_comparison["swinlip_only_correct_samples"]
        if len(exclusive) >= 5 and len({x["expected_label"] for x in exclusive}) >= 2:
            return "PROMISING_TRANSFER_SIGNAL"
    return "WEAK_TRANSFER_SIGNAL"


def run_real_frozen_probe_loso(repository_root: Path) -> dict:
    """Executa uma vez com código versionado e persiste o relatório auditável."""
    root = Path(repository_root).resolve()
    output_path = root / OUTPUT_RELATIVE_PATH
    if output_path.exists():
        raise FileExistsError("Resultado LOSO SwinLip já existe; não reexecutar.")
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip()
    if status:
        raise ValueError("O worktree versionável precisa estar limpo antes do LOSO.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    samples, manifest, manifest_sha = preflight_frozen_probe_dataset(root)
    report = build_frozen_loso_report(samples)
    preferred = report["development_preferred_frozen_probe"]
    preferred_predictions = tuple(
        SamplePrediction(**item)
        for item in (
            (
                {key: value for key, value in row.items() if key != "similarities"}
                if preferred == CENTROID_NAME
                else {key: value for key, value in row.items() if key != "logits"}
            )
            for row in report["probes"][preferred]["predictions"]
        )
    )
    historical_path = root / HISTORICAL_DTW_RELATIVE_PATH
    dtw_comparison = None
    historical_sha = None
    if historical_path.is_file():
        historical_predictions = load_historical_dtw_predictions(
            historical_path, samples
        )
        dtw_comparison = compare_to_historical_dtw(
            historical_predictions, preferred_predictions
        )
        historical_sha = sha256_file(historical_path)
    report.update(
        {
            "format_version": 1,
            "evaluation_count": 1,
            "code_commit": commit,
            "worktree_clean_before_evaluation": True,
            "heldouts_used": False,
            "source_embedding_manifest_path": OUTPUT_MANIFEST_RELATIVE_PATH.as_posix(),
            "source_embedding_manifest_sha256": manifest_sha,
            "source_checkpoint_sha256": manifest["checkpoint_sha256"],
            "source_commit": manifest["source_commit"],
            "source_embedding_hashes": {
                item["sample_id"]: item["embedding_sha256"]
                for item in manifest["samples"]
            },
            "protocol": {
                "embedding": "clip_embedding",
                "embedding_dimension": EMBEDDING_DIMENSION,
                "normalization": "individual_l2",
                "normalization_epsilon": EMBEDDING_NORMALIZATION_EPSILON,
                "folds": list(SESSION_IDS),
                "centroid": "mean_of_six_normalized_then_l2_cosine_argmax_first_index",
                "linear": {
                    "architecture": "Linear(1664,6,bias=True)",
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
            "historical_dtw_sha256": historical_sha,
            "dtw_complementarity": dtw_comparison,
            "transfer_signal_classification": classify_transfer_signal(
                report["probes"][preferred]["metrics"]["accuracy"], dtw_comparison
            ),
        }
    )
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    return report
