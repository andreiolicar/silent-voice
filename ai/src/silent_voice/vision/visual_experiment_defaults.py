from silent_voice.vision.visual_activity_segmentation import (
    VisualActivitySegmentationConfig,
)


SESSION_IDS = (
    "sessao_01",
    "sessao_02",
    "sessao_03",
)


def build_default_segmentation_config() -> VisualActivitySegmentationConfig:
    return VisualActivitySegmentationConfig(
        velocity_start_index=80,
        smoothing_window=5,
        threshold_ratio=0.25,
        padding_frames=6,
        minimum_segment_frames=18,
        minimum_activity_range=1e-6,
    )
