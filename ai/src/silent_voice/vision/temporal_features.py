from dataclasses import dataclass

from silent_voice.vision.landmarks import MouthLandmarksFrame
from silent_voice.vision.normalization import normalize_mouth_points


MOUTH_COORDINATE_COUNT = 80
VISUAL_FEATURE_COUNT = 160

VisualFeatureValues = tuple[float, ...]


@dataclass(frozen=True, slots=True)
class VisualTemporalFeatureFrame:
    frame_index: int
    timestamp_ms: float
    values: VisualFeatureValues


def flatten_mouth_points(
    points: tuple[tuple[float, float], ...],
) -> VisualFeatureValues:
    values = []

    for x, y in points:
        values.extend((x, y))

    return tuple(values)


def extract_temporal_features(
    frames: tuple[MouthLandmarksFrame, ...],
) -> tuple[VisualTemporalFeatureFrame, ...]:
    if not frames:
        return ()

    feature_frames = []
    previous_shape: VisualFeatureValues | None = None

    for frame in frames:
        normalized_points = normalize_mouth_points(frame.points)
        current_shape = flatten_mouth_points(normalized_points)

        if previous_shape is None:
            velocity = (0.0,) * MOUTH_COORDINATE_COUNT
        else:
            velocity = tuple(
                current_value - previous_value
                for current_value, previous_value in zip(
                    current_shape,
                    previous_shape,
                )
            )

        values = current_shape + velocity

        feature_frames.append(
            VisualTemporalFeatureFrame(
                frame_index=frame.frame_index,
                timestamp_ms=frame.timestamp_ms,
                values=values,
            )
        )

        previous_shape = current_shape

    return tuple(feature_frames)
