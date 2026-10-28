from pathlib import Path

import numpy as np

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)


def save_visual_feature_sample(
    sample: VisualFeatureSample,
    output_path: str | Path,
) -> None:
    path = Path(output_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "sample_id": np.asarray(sample.sample_id),
        "label": np.asarray(sample.label),
        "features": sample.features,
        "timestamps_ms": sample.timestamps_ms,
    }

    if sample.session_id is not None:
        data["session_id"] = np.asarray(sample.session_id)

    np.savez_compressed(
        path,
        **data,
    )


def load_visual_feature_sample(
    sample_path: str | Path,
) -> VisualFeatureSample:
    path = Path(sample_path)

    if not path.is_file():
        raise FileNotFoundError(f"Arquivo da amostra visual não encontrado: {path}")

    with np.load(
        path,
        allow_pickle=False,
    ) as data:
        sample_id = str(data["sample_id"].item())

        label = str(data["label"].item())

        features = np.asarray(
            data["features"],
            dtype=np.float32,
        )

        timestamps_ms = np.asarray(
            data["timestamps_ms"],
            dtype=np.float64,
        )

        if "session_id" in data.files:
            session_id = str(data["session_id"].item())
        else:
            session_id = None

    return VisualFeatureSample(
        sample_id=sample_id,
        label=label,
        features=features,
        timestamps_ms=timestamps_ms,
        session_id=session_id,
    )
