from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class VisualActivitySegmentationConfig:
    velocity_start_index: int
    smoothing_window: int
    threshold_ratio: float
    padding_frames: int
    minimum_segment_frames: int
    minimum_activity_range: float


@dataclass(frozen=True, slots=True)
class VisualActivitySegment:
    detected: bool
    start_frame: int
    end_frame_exclusive: int
    baseline_activity: float
    peak_activity: float
    threshold: float

    @property
    def frame_count(self) -> int:
        return self.end_frame_exclusive - self.start_frame


def _validate_config(
    config: VisualActivitySegmentationConfig,
    feature_dimension: int,
) -> None:
    if (
        config.velocity_start_index < 0
        or config.velocity_start_index >= feature_dimension
    ):
        raise ValueError(
            "velocity_start_index deve apontar " "para uma posição válida das features."
        )

    if config.smoothing_window <= 0:
        raise ValueError("smoothing_window deve ser maior " "que zero.")

    if not 0.0 < config.threshold_ratio < 1.0:
        raise ValueError("threshold_ratio deve estar " "entre zero e um.")

    if config.padding_frames < 0:
        raise ValueError("padding_frames não pode ser negativo.")

    if config.minimum_segment_frames <= 0:
        raise ValueError("minimum_segment_frames deve ser " "maior que zero.")

    if config.minimum_activity_range < 0.0:
        raise ValueError("minimum_activity_range não pode " "ser negativo.")


def _calculate_frame_activity(
    features: np.ndarray,
    velocity_start_index: int,
) -> np.ndarray:
    velocity_features = np.asarray(
        features[
            :,
            velocity_start_index:,
        ],
        dtype=np.float64,
    )

    squared_velocity = np.square(velocity_features)

    return np.sqrt(
        np.mean(
            squared_velocity,
            axis=1,
        )
    )


def _smooth_activity(
    activity: np.ndarray,
    window_size: int,
) -> np.ndarray:
    if window_size == 1:
        return activity.copy()

    effective_window = min(
        window_size,
        len(activity),
    )

    kernel = np.ones(
        effective_window,
        dtype=np.float64,
    )

    kernel /= effective_window

    return np.convolve(
        activity,
        kernel,
        mode="same",
    )


def _build_full_sequence_segment(
    frame_count: int,
    baseline_activity: float,
    peak_activity: float,
    threshold: float,
) -> VisualActivitySegment:
    return VisualActivitySegment(
        detected=False,
        start_frame=0,
        end_frame_exclusive=frame_count,
        baseline_activity=baseline_activity,
        peak_activity=peak_activity,
        threshold=threshold,
    )


def _expand_to_minimum_length(
    start_frame: int,
    end_frame_exclusive: int,
    frame_count: int,
    minimum_segment_frames: int,
) -> tuple[int, int]:
    target_length = min(
        minimum_segment_frames,
        frame_count,
    )

    current_length = end_frame_exclusive - start_frame

    if current_length >= target_length:
        return (
            start_frame,
            end_frame_exclusive,
        )

    missing_frames = target_length - current_length

    left_expansion = missing_frames // 2

    right_expansion = missing_frames - left_expansion

    start_frame = max(
        0,
        start_frame - left_expansion,
    )

    end_frame_exclusive = min(
        frame_count,
        end_frame_exclusive + right_expansion,
    )

    current_length = end_frame_exclusive - start_frame

    if current_length < target_length:
        if start_frame == 0:
            end_frame_exclusive = min(
                frame_count,
                target_length,
            )
        elif end_frame_exclusive == frame_count:
            start_frame = max(
                0,
                frame_count - target_length,
            )

    return (
        start_frame,
        end_frame_exclusive,
    )


def detect_visual_activity_segment(
    features: np.ndarray,
    config: VisualActivitySegmentationConfig,
) -> VisualActivitySegment:
    feature_matrix = np.asarray(features)

    if feature_matrix.ndim != 2:
        raise ValueError("As features devem formar uma " "matriz bidimensional.")

    if feature_matrix.shape[0] == 0:
        raise ValueError("A sequência visual não pode ser vazia.")

    if feature_matrix.shape[1] == 0:
        raise ValueError("A dimensão de features não pode " "ser vazia.")

    if not np.all(np.isfinite(feature_matrix)):
        raise ValueError("As features devem conter apenas " "valores finitos.")

    _validate_config(
        config=config,
        feature_dimension=(feature_matrix.shape[1]),
    )

    frame_count = feature_matrix.shape[0]

    activity = _calculate_frame_activity(
        features=feature_matrix,
        velocity_start_index=(config.velocity_start_index),
    )

    smoothed_activity = _smooth_activity(
        activity=activity,
        window_size=(config.smoothing_window),
    )

    baseline_activity = float(
        np.percentile(
            smoothed_activity,
            20.0,
        )
    )

    peak_activity = float(np.max(smoothed_activity))

    activity_range = peak_activity - baseline_activity

    threshold = float(baseline_activity + (config.threshold_ratio * activity_range))

    if activity_range < config.minimum_activity_range:
        return _build_full_sequence_segment(
            frame_count=frame_count,
            baseline_activity=baseline_activity,
            peak_activity=peak_activity,
            threshold=threshold,
        )

    active_indices = np.flatnonzero(smoothed_activity > threshold)

    if len(active_indices) == 0:
        return _build_full_sequence_segment(
            frame_count=frame_count,
            baseline_activity=baseline_activity,
            peak_activity=peak_activity,
            threshold=threshold,
        )

    first_active_frame = int(active_indices[0])

    last_active_frame = int(active_indices[-1])

    start_frame = max(
        0,
        first_active_frame - config.padding_frames,
    )

    end_frame_exclusive = min(
        frame_count,
        last_active_frame + 1 + config.padding_frames,
    )

    (
        start_frame,
        end_frame_exclusive,
    ) = _expand_to_minimum_length(
        start_frame=start_frame,
        end_frame_exclusive=(end_frame_exclusive),
        frame_count=frame_count,
        minimum_segment_frames=(config.minimum_segment_frames),
    )

    return VisualActivitySegment(
        detected=True,
        start_frame=start_frame,
        end_frame_exclusive=(end_frame_exclusive),
        baseline_activity=baseline_activity,
        peak_activity=peak_activity,
        threshold=threshold,
    )
