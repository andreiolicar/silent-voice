from dataclasses import dataclass

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)
from silent_voice.vision.strong_dtw_classifier import (
    StrongDtwVisualClassifier,
)
from silent_voice.vision.strong_dtw_distance import (
    StrongDtwDistanceConfig,
)
from silent_voice.vision.visual_activity_segmentation import (
    VisualActivitySegmentationConfig,
)
from silent_voice.vision.visual_cross_validation import (
    build_leave_one_session_out_folds,
)
from silent_voice.vision.visual_sample_segmentation import (
    segment_visual_feature_sample,
)


@dataclass(frozen=True, slots=True)
class StrongDtwCandidate:
    name: str
    config: StrongDtwDistanceConfig


@dataclass(frozen=True, slots=True)
class StrongDtwFoldEvaluation:
    validation_session_id: str
    correct_count: int
    sample_count: int
    accuracy: float


@dataclass(frozen=True, slots=True)
class StrongDtwCandidateEvaluation:
    candidate: StrongDtwCandidate
    folds: tuple[
        StrongDtwFoldEvaluation,
        ...,
    ]
    correct_count: int
    sample_count: int
    accuracy: float


@dataclass(frozen=True, slots=True)
class StrongDtwExperimentResult:
    evaluations: tuple[
        StrongDtwCandidateEvaluation,
        ...,
    ]
    selected: StrongDtwCandidateEvaluation


def build_frozen_strong_dtw_candidates() -> tuple[
    StrongDtwCandidate,
    ...,
]:
    return (
        StrongDtwCandidate(
            name="LEGACY_RAW",
            config=StrongDtwDistanceConfig(
                normalize_by_path_length=False,
                max_normalized_warping=None,
            ),
        ),
        StrongDtwCandidate(
            name="PATH_NORMALIZED",
            config=StrongDtwDistanceConfig(
                normalize_by_path_length=True,
                max_normalized_warping=None,
            ),
        ),
        StrongDtwCandidate(
            name="WARP_035",
            config=StrongDtwDistanceConfig(
                normalize_by_path_length=True,
                max_normalized_warping=0.35,
            ),
        ),
        StrongDtwCandidate(
            name="WARP_020",
            config=StrongDtwDistanceConfig(
                normalize_by_path_length=True,
                max_normalized_warping=0.20,
            ),
        ),
    )


def _segment_samples(
    samples: tuple[
        VisualFeatureSample,
        ...,
    ],
    config: VisualActivitySegmentationConfig,
) -> tuple[
    VisualFeatureSample,
    ...,
]:
    return tuple(
        segment_visual_feature_sample(
            sample=sample,
            config=config,
        ).sample
        for sample in samples
    )


def _evaluate_fold(
    training_samples: tuple[
        VisualFeatureSample,
        ...,
    ],
    validation_samples: tuple[
        VisualFeatureSample,
        ...,
    ],
    validation_session_id: str,
    config: StrongDtwDistanceConfig,
) -> StrongDtwFoldEvaluation:
    classifier = StrongDtwVisualClassifier(
        training_samples=training_samples,
        config=config,
    )

    correct_count = 0

    for sample in validation_samples:
        prediction = classifier.predict(sample)

        if prediction.label == sample.label:
            correct_count += 1

    sample_count = len(validation_samples)

    if sample_count == 0:
        raise ValueError(
            "Um fold Strong DTW não pode " "possuir zero amostras de validação."
        )

    return StrongDtwFoldEvaluation(
        validation_session_id=validation_session_id,
        correct_count=correct_count,
        sample_count=sample_count,
        accuracy=(correct_count / sample_count),
    )


def _evaluate_candidate(
    candidate: StrongDtwCandidate,
    folds,
) -> StrongDtwCandidateEvaluation:
    fold_evaluations = tuple(
        _evaluate_fold(
            training_samples=fold.train,
            validation_samples=fold.validation,
            validation_session_id=(fold.validation_session_id),
            config=candidate.config,
        )
        for fold in folds
    )

    correct_count = sum(fold.correct_count for fold in fold_evaluations)

    sample_count = sum(fold.sample_count for fold in fold_evaluations)

    if sample_count == 0:
        raise ValueError("O experimento Strong DTW não pode " "possuir zero amostras.")

    return StrongDtwCandidateEvaluation(
        candidate=candidate,
        folds=fold_evaluations,
        correct_count=correct_count,
        sample_count=sample_count,
        accuracy=(correct_count / sample_count),
    )


def _select_best_candidate(
    evaluations: tuple[
        StrongDtwCandidateEvaluation,
        ...,
    ],
) -> StrongDtwCandidateEvaluation:
    if not evaluations:
        raise ValueError(
            "O experimento Strong DTW não pode " "possuir zero candidatos."
        )

    selected = evaluations[0]

    for evaluation in evaluations[1:]:
        if evaluation.accuracy > selected.accuracy:
            selected = evaluation

    return selected


def evaluate_frozen_strong_dtw_candidates(
    samples: tuple[
        VisualFeatureSample,
        ...,
    ],
    session_ids: tuple[
        str,
        ...,
    ],
    segmentation_config: VisualActivitySegmentationConfig,
) -> StrongDtwExperimentResult:
    segmented_samples = _segment_samples(
        samples=samples,
        config=segmentation_config,
    )

    folds = build_leave_one_session_out_folds(
        samples=segmented_samples,
        session_ids=session_ids,
    )

    candidates = build_frozen_strong_dtw_candidates()

    evaluations = tuple(
        _evaluate_candidate(
            candidate=candidate,
            folds=folds,
        )
        for candidate in candidates
    )

    return StrongDtwExperimentResult(
        evaluations=evaluations,
        selected=_select_best_candidate(evaluations),
    )
