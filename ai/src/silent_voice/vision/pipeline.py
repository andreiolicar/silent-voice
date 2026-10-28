from typing import Any

from silent_voice.vision.temporal_features import (
    VisualTemporalFeatureFrame,
    extract_temporal_features,
)
from silent_voice.vision.video_sequence import extract_video_sequence


def extract_visual_feature_sequence(
    capture: Any,
    detector: Any,
) -> tuple[VisualTemporalFeatureFrame, ...]:
    landmark_sequence = extract_video_sequence(
        capture=capture,
        detector=detector,
    )

    return extract_temporal_features(landmark_sequence)
