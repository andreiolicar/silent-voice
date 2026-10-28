from dataclasses import dataclass

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)
from silent_voice.vision.strong_dtw_distance import (
    StrongDtwDistanceConfig,
    calculate_strong_dtw_distance,
)


@dataclass(frozen=True, slots=True)
class StrongDtwVisualCandidate:
    label: str
    template_sample_id: str
    distance: float
    total_cost: float
    path_length: int


@dataclass(frozen=True, slots=True)
class StrongDtwVisualPrediction:
    label: str
    template_sample_id: str
    distance: float
    total_cost: float
    path_length: int


class StrongDtwVisualClassifier:
    def __init__(
        self,
        training_samples: tuple[
            VisualFeatureSample,
            ...,
        ],
        config: StrongDtwDistanceConfig,
    ) -> None:
        if not training_samples:
            raise ValueError(
                "O conjunto de treino do Strong DTW " "não pode ser vazio."
            )

        self._training_samples = tuple(training_samples)

        self._config = config

    @property
    def training_samples(
        self,
    ) -> tuple[
        VisualFeatureSample,
        ...,
    ]:
        return self._training_samples

    @property
    def config(
        self,
    ) -> StrongDtwDistanceConfig:
        return self._config

    def rank_templates(
        self,
        sample: VisualFeatureSample,
    ) -> tuple[
        StrongDtwVisualCandidate,
        ...,
    ]:
        candidates = []

        for template in self._training_samples:
            distance_result = calculate_strong_dtw_distance(
                sequence_a=sample.features,
                sequence_b=template.features,
                config=self._config,
            )

            candidates.append(
                StrongDtwVisualCandidate(
                    label=template.label,
                    template_sample_id=(template.sample_id),
                    distance=(distance_result.distance),
                    total_cost=(distance_result.total_cost),
                    path_length=(distance_result.path_length),
                )
            )

        return tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    candidate.distance,
                    candidate.template_sample_id,
                ),
            )
        )

    def predict(
        self,
        sample: VisualFeatureSample,
    ) -> StrongDtwVisualPrediction:
        ranking = self.rank_templates(sample)

        best = ranking[0]

        return StrongDtwVisualPrediction(
            label=best.label,
            template_sample_id=(best.template_sample_id),
            distance=best.distance,
            total_cost=best.total_cost,
            path_length=best.path_length,
        )
