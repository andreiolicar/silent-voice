from pathlib import Path
from typing import Any

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)
from silent_voice.vision.feature_sample_storage import (
    save_visual_feature_sample,
)
from silent_voice.vision.visual_sample_processing import (
    process_visual_sample,
)


def process_and_save_visual_sample(
    sample_id: str,
    label: str,
    capture: Any,
    detector: Any,
    output_path: str | Path,
    session_id: str | None = None,
) -> VisualFeatureSample:
    sample = process_visual_sample(
        sample_id=sample_id,
        label=label,
        capture=capture,
        detector=detector,
        session_id=session_id,
    )

    save_visual_feature_sample(
        sample=sample,
        output_path=output_path,
    )

    return sample
