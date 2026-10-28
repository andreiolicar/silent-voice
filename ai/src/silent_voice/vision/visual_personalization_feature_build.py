"""Public runtime feature validation, extracted from the frozen module."""

import numpy as np


def validate_feature_arrays(clip: np.ndarray, temporal: np.ndarray) -> None:
    if (
        not isinstance(clip, np.ndarray)
        or clip.shape != (1, 1664)
        or clip.dtype != np.float32
        or not np.isfinite(clip).all()
        or not isinstance(temporal, np.ndarray)
        or temporal.ndim != 2
        or temporal.shape[0] < 1
        or temporal.shape[1] != 160
        or temporal.dtype != np.float32
        or not np.isfinite(temporal).all()
    ):
        raise ValueError("Shape, dtype ou finitude das features incompatível.")
