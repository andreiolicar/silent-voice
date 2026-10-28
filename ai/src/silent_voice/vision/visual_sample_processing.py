from typing import Any

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)
from silent_voice.vision.feature_sample_builder import (
    build_visual_feature_sample,
)
from silent_voice.vision.pipeline import (
    extract_visual_feature_sequence,
)


def process_visual_sample(
    sample_id: str,
    label: str,
    capture: Any,
    detector: Any,
    session_id: str | None = None,
) -> VisualFeatureSample:
    feature_frames = extract_visual_feature_sequence(
        capture=capture,
        detector=detector,
    )

    return build_visual_feature_sample(
        sample_id=sample_id,
        label=label,
        frames=feature_frames,
        session_id=session_id,
    )
