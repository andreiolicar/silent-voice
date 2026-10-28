from dataclasses import dataclass

from silent_voice.vision.dtw_tcn_predictions import (
    PairedPredictions,
    SamplePrediction,
)
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


@dataclass(frozen=True, slots=True)
class FoldMetrics:
    validation_session_id: str
    sample_count: int
    correct_count: int
    accuracy: float | None


@dataclass(frozen=True, slots=True)
class ClassMetrics:
    label: str
    label_index: int
    sample_count: int
    correct_count: int
    accuracy: float | None


@dataclass(frozen=True, slots=True)
class ModelMetrics:
    total_sample_count: int
    correct_count: int
    error_count: int
    accuracy: float
    folds: tuple[FoldMetrics, ...]
    classes: tuple[ClassMetrics, ...]
    confusion_matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class PairedComparisonMetrics:
    labels: tuple[str, ...]
    dtw: ModelMetrics
    tcn: ModelMetrics


def _validate_predictions(
    predictions: tuple[SamplePrediction, ...],
    model_name: str,
    session_ids: tuple[str, ...],
) -> dict[str, SamplePrediction]:
    if not predictions:
        raise ValueError(f"O conjunto de previsões {model_name} está vazio.")

    label_to_index = {label: index for index, label in enumerate(DEFAULT_VISUAL_LABELS)}
    by_sample_id = {}

    for item in predictions:
        if item.sample_id in by_sample_id:
            raise ValueError(f"sample_id duplicado nas previsões {model_name}.")
        if not item.sample_id.strip():
            raise ValueError(f"sample_id vazio nas previsões {model_name}.")
        if item.validation_session_id not in session_ids:
            raise ValueError(
                "validation_session_id fora dos folds congelados: "
                f"{item.validation_session_id}."
            )
        if item.expected_label not in label_to_index:
            raise ValueError(f"expected_label inválido: {item.expected_label}.")
        if item.predicted_label not in label_to_index:
            raise ValueError(f"predicted_label inválido: {item.predicted_label}.")
        if (
            type(item.expected_label_index) is not int
            or item.expected_label_index != label_to_index[item.expected_label]
        ):
            raise ValueError(f"expected_label_index inconsistente: {item.sample_id}.")
        if (
            type(item.predicted_label_index) is not int
            or item.predicted_label_index != label_to_index[item.predicted_label]
        ):
            raise ValueError(f"predicted_label_index inconsistente: {item.sample_id}.")
        if type(item.correct) is not bool or item.correct != (
            item.expected_label == item.predicted_label
        ):
            raise ValueError(f"correct inconsistente: {item.sample_id}.")
        by_sample_id[item.sample_id] = item

    return by_sample_id


def _calculate_accuracy(correct_count: int, sample_count: int) -> float | None:
    if sample_count == 0:
        return None
    return correct_count / sample_count


def _calculate_model_metrics(
    predictions: tuple[SamplePrediction, ...],
    session_ids: tuple[str, ...],
) -> ModelMetrics:
    sample_count = len(predictions)
    correct_count = sum(item.correct for item in predictions)

    folds = tuple(
        FoldMetrics(
            validation_session_id=session_id,
            sample_count=sum(
                item.validation_session_id == session_id for item in predictions
            ),
            correct_count=sum(
                item.correct and item.validation_session_id == session_id
                for item in predictions
            ),
            accuracy=_calculate_accuracy(
                sum(
                    item.correct and item.validation_session_id == session_id
                    for item in predictions
                ),
                sum(item.validation_session_id == session_id for item in predictions),
            ),
        )
        for session_id in session_ids
    )

    classes = tuple(
        ClassMetrics(
            label=label,
            label_index=label_index,
            sample_count=sum(
                item.expected_label_index == label_index for item in predictions
            ),
            correct_count=sum(
                item.correct and item.expected_label_index == label_index
                for item in predictions
            ),
            accuracy=_calculate_accuracy(
                sum(
                    item.correct and item.expected_label_index == label_index
                    for item in predictions
                ),
                sum(item.expected_label_index == label_index for item in predictions),
            ),
        )
        for label_index, label in enumerate(DEFAULT_VISUAL_LABELS)
    )

    matrix = [[0 for _ in DEFAULT_VISUAL_LABELS] for _ in DEFAULT_VISUAL_LABELS]
    for item in predictions:
        matrix[item.expected_label_index][item.predicted_label_index] += 1

    return ModelMetrics(
        total_sample_count=sample_count,
        correct_count=correct_count,
        error_count=sample_count - correct_count,
        accuracy=correct_count / sample_count,
        folds=folds,
        classes=classes,
        confusion_matrix=tuple(tuple(row) for row in matrix),
    )


def calculate_paired_metrics(
    paired: PairedPredictions, session_ids: tuple[str, ...] = SESSION_IDS
) -> PairedComparisonMetrics:
    if paired.labels != DEFAULT_VISUAL_LABELS:
        raise ValueError("A ordem de labels deve seguir o vocabulário congelado.")
    if not session_ids or len(session_ids) != len(set(session_ids)):
        raise ValueError("session_ids inválidos para cálculo de métricas.")
    if any(item not in SESSION_IDS + ("sessao_04",) for item in session_ids):
        raise ValueError("session_ids fora do protocolo congelado.")

    dtw_by_id = _validate_predictions(paired.dtw_predictions, "DTW", session_ids)
    tcn_by_id = _validate_predictions(paired.tcn_predictions, "TCN", session_ids)

    if dtw_by_id.keys() != tcn_by_id.keys():
        raise ValueError("O pareamento de sample_id entre DTW e TCN é incompleto.")
    for sample_id, dtw in dtw_by_id.items():
        tcn = tcn_by_id[sample_id]
        if (
            dtw.validation_session_id != tcn.validation_session_id
            or dtw.expected_label != tcn.expected_label
            or dtw.expected_label_index != tcn.expected_label_index
        ):
            raise ValueError(f"O pareamento diverge para sample_id {sample_id}.")

    return PairedComparisonMetrics(
        labels=DEFAULT_VISUAL_LABELS,
        dtw=_calculate_model_metrics(paired.dtw_predictions, session_ids),
        tcn=_calculate_model_metrics(paired.tcn_predictions, session_ids),
    )
