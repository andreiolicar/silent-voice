from dataclasses import dataclass

import numpy as np

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)
from silent_voice.vision.visual_sequence_resampling import (
    resample_visual_feature_sample,
)


VISUAL_TRAINING_FRAME_COUNT = 64

DEFAULT_VISUAL_LABELS = (
    "SIM",
    "NÃO",
    "AJUDA",
    "ÁGUA",
    "BANHEIRO",
    "PARAR",
)


@dataclass(frozen=True, slots=True)
class VisualTrainingSample:
    sample_id: str
    label: str
    label_index: int
    session_id: str
    features: np.ndarray

    def __post_init__(self) -> None:
        expected_shape = (
            VISUAL_TRAINING_FRAME_COUNT,
            160,
        )

        if self.features.shape != expected_shape:
            raise ValueError(
                "As features de treinamento visual " "devem possuir formato (64, 160)."
            )

        if not np.all(np.isfinite(self.features)):
            raise ValueError(
                "As features de treinamento visual "
                "devem conter apenas valores finitos."
            )


@dataclass(frozen=True, slots=True)
class VisualTrainingDataset:
    samples: tuple[
        VisualTrainingSample,
        ...,
    ]
    labels: tuple[
        str,
        ...,
    ]

    @property
    def sample_count(
        self,
    ) -> int:
        return len(self.samples)

    @property
    def class_count(
        self,
    ) -> int:
        return len(self.labels)


def _validate_samples(
    samples: tuple[
        VisualFeatureSample,
        ...,
    ],
) -> None:
    if not samples:
        raise ValueError("O dataset visual de treinamento " "não pode ser vazio.")

    observed_sample_ids = set()

    for sample in samples:
        if sample.sample_id in observed_sample_ids:
            raise ValueError(
                "O dataset visual de treinamento "
                "possui sample_id duplicado: "
                f"{sample.sample_id}."
            )

        observed_sample_ids.add(sample.sample_id)

        if sample.label not in DEFAULT_VISUAL_LABELS:
            raise ValueError(
                "A amostra possui um label fora do "
                "vocabulário visual congelado: "
                f"{sample.label}."
            )

        if sample.session_id is None:
            raise ValueError(
                "Toda amostra de treinamento visual "
                "deve possuir identificador de sessão."
            )

        if not sample.session_id.strip():
            raise ValueError(
                "O identificador de sessão da amostra "
                "de treinamento não pode ser vazio."
            )


def _build_label_index_by_label() -> dict[
    str,
    int,
]:
    return {label: index for index, label in enumerate(DEFAULT_VISUAL_LABELS)}


def build_visual_training_dataset(
    samples: tuple[
        VisualFeatureSample,
        ...,
    ],
) -> VisualTrainingDataset:
    _validate_samples(samples)

    label_index_by_label = _build_label_index_by_label()

    training_samples = []

    for sample in samples:
        resampled_sample = resample_visual_feature_sample(
            sample=sample,
            target_frame_count=(VISUAL_TRAINING_FRAME_COUNT),
        )

        training_samples.append(
            VisualTrainingSample(
                sample_id=(resampled_sample.sample_id),
                label=resampled_sample.label,
                label_index=(label_index_by_label[resampled_sample.label]),
                session_id=(resampled_sample.session_id),
                features=(resampled_sample.features.copy()),
            )
        )

    return VisualTrainingDataset(
        samples=tuple(training_samples),
        labels=DEFAULT_VISUAL_LABELS,
    )
