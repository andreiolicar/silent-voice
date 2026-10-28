from dataclasses import dataclass

import numpy as np

from silent_voice.vision.temporal_features import (
    VISUAL_FEATURE_COUNT,
)


@dataclass(frozen=True, slots=True)
class VisualFeatureSample:
    sample_id: str
    label: str
    features: np.ndarray
    timestamps_ms: np.ndarray
    session_id: str | None = None

    def __post_init__(self) -> None:
        if not self.sample_id.strip():
            raise ValueError("O identificador da amostra não pode estar vazio.")

        if not self.label.strip():
            raise ValueError("O rótulo da amostra não pode estar vazio.")

        if self.session_id is not None and not self.session_id.strip():
            raise ValueError("O identificador da sessão não pode estar vazio.")

        if self.features.ndim != 2:
            raise ValueError("As features devem possuir duas dimensões.")

        if self.features.shape[0] == 0:
            raise ValueError("A amostra deve possuir pelo menos um frame.")

        if self.features.shape[1] != VISUAL_FEATURE_COUNT:
            raise ValueError(
                "Cada frame deve possuir exatamente "
                f"{VISUAL_FEATURE_COUNT} features."
            )

        if self.timestamps_ms.ndim != 1:
            raise ValueError("Os timestamps devem possuir uma dimensão.")

        if len(self.timestamps_ms) != self.features.shape[0]:
            raise ValueError(
                "A quantidade de timestamps deve corresponder "
                "à quantidade de frames."
            )

    @property
    def frame_count(self) -> int:
        return int(self.features.shape[0])

    @property
    def feature_dimension(self) -> int:
        return int(self.features.shape[1])
