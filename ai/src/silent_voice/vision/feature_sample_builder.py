import numpy as np

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)
from silent_voice.vision.temporal_features import (
    VisualTemporalFeatureFrame,
)


def build_visual_feature_sample(
    sample_id: str,
    label: str,
    frames: tuple[VisualTemporalFeatureFrame, ...],
    session_id: str | None = None,
) -> VisualFeatureSample:
    if not frames:
        raise ValueError("A amostra deve possuir pelo menos um frame.")

    features = np.asarray(
        [frame.values for frame in frames],
        dtype=np.float32,
    )

    timestamps_ms = np.asarray(
        [frame.timestamp_ms for frame in frames],
        dtype=np.float64,
    )

    return VisualFeatureSample(
        sample_id=sample_id,
        label=label,
        features=features,
        timestamps_ms=timestamps_ms,
        session_id=session_id,
    )
