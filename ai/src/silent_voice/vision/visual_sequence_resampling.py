import numpy as np

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)


def _build_resampling_positions(
    source_frame_count: int,
    target_frame_count: int,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:
    source_positions = np.linspace(
        0.0,
        float(source_frame_count - 1),
        num=source_frame_count,
        dtype=np.float64,
    )

    target_positions = np.linspace(
        0.0,
        float(source_frame_count - 1),
        num=target_frame_count,
        dtype=np.float64,
    )

    return (
        source_positions,
        target_positions,
    )


def _resample_features(
    features: np.ndarray,
    target_frame_count: int,
) -> np.ndarray:
    source_frame_count = features.shape[0]

    if source_frame_count == 1:
        return np.repeat(
            features,
            repeats=target_frame_count,
            axis=0,
        ).copy()

    (
        source_positions,
        target_positions,
    ) = _build_resampling_positions(
        source_frame_count=source_frame_count,
        target_frame_count=target_frame_count,
    )

    resampled = np.empty(
        (
            target_frame_count,
            features.shape[1],
        ),
        dtype=np.float64,
    )

    for feature_index in range(features.shape[1]):
        resampled[
            :,
            feature_index,
        ] = np.interp(
            target_positions,
            source_positions,
            features[
                :,
                feature_index,
            ],
        )

    return resampled.astype(
        features.dtype,
        copy=False,
    )


def _resample_timestamps(
    timestamps_ms: np.ndarray,
    target_frame_count: int,
) -> np.ndarray:
    source_frame_count = timestamps_ms.shape[0]

    if source_frame_count == 1:
        return np.full(
            target_frame_count,
            timestamps_ms[0],
            dtype=np.float64,
        )

    (
        source_positions,
        target_positions,
    ) = _build_resampling_positions(
        source_frame_count=source_frame_count,
        target_frame_count=target_frame_count,
    )

    return np.interp(
        target_positions,
        source_positions,
        timestamps_ms,
    ).astype(
        np.float64,
        copy=False,
    )


def resample_visual_feature_sample(
    sample: VisualFeatureSample,
    target_frame_count: int,
) -> VisualFeatureSample:
    if (
        not isinstance(
            target_frame_count,
            int,
        )
        or isinstance(
            target_frame_count,
            bool,
        )
        or target_frame_count <= 0
    ):
        raise ValueError("O número alvo de frames deve ser " "um inteiro positivo.")

    resampled_features = _resample_features(
        features=sample.features,
        target_frame_count=target_frame_count,
    )

    resampled_timestamps = _resample_timestamps(
        timestamps_ms=sample.timestamps_ms,
        target_frame_count=target_frame_count,
    )

    return VisualFeatureSample(
        sample_id=sample.sample_id,
        label=sample.label,
        features=(resampled_features.copy()),
        timestamps_ms=(resampled_timestamps.copy()),
        session_id=sample.session_id,
    )
