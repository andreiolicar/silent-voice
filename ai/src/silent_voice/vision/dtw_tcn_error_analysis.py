from dataclasses import dataclass
from enum import Enum

from silent_voice.vision.dtw_tcn_comparison import calculate_paired_metrics
from silent_voice.vision.dtw_tcn_predictions import PairedPredictions
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


class OutcomeCategory(str, Enum):
    BOTH_CORRECT = "BOTH_CORRECT"
    DTW_ONLY_CORRECT = "DTW_ONLY_CORRECT"
    TCN_ONLY_CORRECT = "TCN_ONLY_CORRECT"
    BOTH_WRONG = "BOTH_WRONG"


@dataclass(frozen=True, slots=True)
class PairedSampleOutcome:
    sample_id: str
    validation_session_id: str
    expected_label: str
    expected_label_index: int
    dtw_predicted_label: str
    dtw_predicted_label_index: int
    dtw_correct: bool
    tcn_predicted_label: str
    tcn_predicted_label_index: int
    tcn_correct: bool
    prediction_agreement: bool
    outcome_category: OutcomeCategory


@dataclass(frozen=True, slots=True)
class FoldOutcomeCounts:
    validation_session_id: str
    sample_count: int
    both_correct_count: int
    dtw_only_correct_count: int
    tcn_only_correct_count: int
    both_wrong_count: int
    agreement_count: int
    disagreement_count: int


@dataclass(frozen=True, slots=True)
class ClassOutcomeCounts:
    label: str
    label_index: int
    sample_count: int
    both_correct_count: int
    dtw_only_correct_count: int
    tcn_only_correct_count: int
    both_wrong_count: int
    agreement_count: int
    disagreement_count: int


@dataclass(frozen=True, slots=True)
class PairedErrorAnalysis:
    labels: tuple[str, ...]
    total_sample_count: int
    both_correct_count: int
    dtw_only_correct_count: int
    tcn_only_correct_count: int
    both_wrong_count: int
    agreement_count: int
    disagreement_count: int
    both_wrong_same_prediction_count: int
    both_wrong_different_prediction_count: int
    paired_samples: tuple[PairedSampleOutcome, ...]
    folds: tuple[FoldOutcomeCounts, ...]
    classes: tuple[ClassOutcomeCounts, ...]
    dtw_only_correct_samples: tuple[PairedSampleOutcome, ...]
    tcn_only_correct_samples: tuple[PairedSampleOutcome, ...]
    both_wrong_samples: tuple[PairedSampleOutcome, ...]


def _counts(samples: tuple[PairedSampleOutcome, ...]) -> dict[str, int]:
    return {
        "sample_count": len(samples),
        "both_correct_count": sum(
            item.outcome_category == OutcomeCategory.BOTH_CORRECT for item in samples
        ),
        "dtw_only_correct_count": sum(
            item.outcome_category == OutcomeCategory.DTW_ONLY_CORRECT
            for item in samples
        ),
        "tcn_only_correct_count": sum(
            item.outcome_category == OutcomeCategory.TCN_ONLY_CORRECT
            for item in samples
        ),
        "both_wrong_count": sum(
            item.outcome_category == OutcomeCategory.BOTH_WRONG for item in samples
        ),
        "agreement_count": sum(item.prediction_agreement for item in samples),
        "disagreement_count": sum(not item.prediction_agreement for item in samples),
    }


def analyze_paired_errors(
    paired: PairedPredictions, session_ids: tuple[str, ...] = SESSION_IDS
) -> PairedErrorAnalysis:
    if len(paired.dtw_predictions) != len(paired.tcn_predictions):
        raise ValueError("Os conjuntos DTW e TCN têm quantidades diferentes.")
    calculate_paired_metrics(paired, session_ids=session_ids)

    tcn_by_id = {item.sample_id: item for item in paired.tcn_predictions}
    paired_samples = []
    for dtw in sorted(
        paired.dtw_predictions,
        key=lambda item: (
            session_ids.index(item.validation_session_id),
            item.sample_id,
        ),
    ):
        tcn = tcn_by_id[dtw.sample_id]
        if dtw.correct and tcn.correct:
            category = OutcomeCategory.BOTH_CORRECT
        elif dtw.correct:
            category = OutcomeCategory.DTW_ONLY_CORRECT
        elif tcn.correct:
            category = OutcomeCategory.TCN_ONLY_CORRECT
        else:
            category = OutcomeCategory.BOTH_WRONG

        paired_samples.append(
            PairedSampleOutcome(
                sample_id=dtw.sample_id,
                validation_session_id=dtw.validation_session_id,
                expected_label=dtw.expected_label,
                expected_label_index=dtw.expected_label_index,
                dtw_predicted_label=dtw.predicted_label,
                dtw_predicted_label_index=dtw.predicted_label_index,
                dtw_correct=dtw.correct,
                tcn_predicted_label=tcn.predicted_label,
                tcn_predicted_label_index=tcn.predicted_label_index,
                tcn_correct=tcn.correct,
                prediction_agreement=dtw.predicted_label_index
                == tcn.predicted_label_index,
                outcome_category=category,
            )
        )

    samples = tuple(paired_samples)
    counts = _counts(samples)
    dtw_only = tuple(
        item
        for item in samples
        if item.outcome_category == OutcomeCategory.DTW_ONLY_CORRECT
    )
    tcn_only = tuple(
        item
        for item in samples
        if item.outcome_category == OutcomeCategory.TCN_ONLY_CORRECT
    )
    both_wrong = tuple(
        item for item in samples if item.outcome_category == OutcomeCategory.BOTH_WRONG
    )

    folds = tuple(
        FoldOutcomeCounts(
            validation_session_id=session_id,
            **_counts(
                tuple(
                    item for item in samples if item.validation_session_id == session_id
                )
            ),
        )
        for session_id in session_ids
    )
    classes = tuple(
        ClassOutcomeCounts(
            label=label,
            label_index=label_index,
            **_counts(
                tuple(
                    item for item in samples if item.expected_label_index == label_index
                )
            ),
        )
        for label_index, label in enumerate(DEFAULT_VISUAL_LABELS)
    )

    return PairedErrorAnalysis(
        labels=DEFAULT_VISUAL_LABELS,
        total_sample_count=counts["sample_count"],
        both_correct_count=counts["both_correct_count"],
        dtw_only_correct_count=counts["dtw_only_correct_count"],
        tcn_only_correct_count=counts["tcn_only_correct_count"],
        both_wrong_count=counts["both_wrong_count"],
        agreement_count=counts["agreement_count"],
        disagreement_count=counts["disagreement_count"],
        both_wrong_same_prediction_count=sum(
            item.prediction_agreement for item in both_wrong
        ),
        both_wrong_different_prediction_count=sum(
            not item.prediction_agreement for item in both_wrong
        ),
        paired_samples=samples,
        folds=folds,
        classes=classes,
        dtw_only_correct_samples=dtw_only,
        tcn_only_correct_samples=tcn_only,
        both_wrong_samples=both_wrong,
    )
