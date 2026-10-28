from dataclasses import dataclass

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)
from silent_voice.vision.visual_activity_segmentation import (
    VisualActivitySegmentationConfig,
    VisualActivitySegment,
    detect_visual_activity_segment,
)


@dataclass(frozen=True, slots=True)
class VisualSampleSegmentationResult:
    sample: VisualFeatureSample
    segment: VisualActivitySegment


def segment_visual_feature_sample(
    sample: VisualFeatureSample,
    config: VisualActivitySegmentationConfig,
) -> VisualSampleSegmentationResult:
    segment = detect_visual_activity_segment(
        features=sample.features,
        config=config,
    )

    start_frame = segment.start_frame

    end_frame_exclusive = segment.end_frame_exclusive

    segmented_features = sample.features[start_frame:end_frame_exclusive].copy()

    segmented_timestamps = sample.timestamps_ms[start_frame:end_frame_exclusive].copy()

    segmented_sample = VisualFeatureSample(
        sample_id=sample.sample_id,
        label=sample.label,
        features=segmented_features,
        timestamps_ms=segmented_timestamps,
        session_id=sample.session_id,
    )

    return VisualSampleSegmentationResult(
        sample=segmented_sample,
        segment=segment,
    )
