from pathlib import Path

import numpy as np
import pytest


def test_public_personalization_contract_is_local_and_fail_closed():
    from silent_voice.vision import personalization_development_protocol as protocol

    assert Path(protocol.__file__).resolve().is_relative_to(Path.cwd().resolve())
    result = protocol.safe_reject_output("synthetic", protocol.CONFIG_IDS[0])
    assert result["decision"] == "REJECT"
    assert result["inference_performed"] is False
    with pytest.raises(ValueError):
        protocol.safe_reject_output("synthetic", "not-a-valid-configuration")


def test_public_feature_contract_checks_shape_dtype_and_finiteness():
    from silent_voice.vision import visual_personalization_feature_build as features

    assert Path(features.__file__).resolve().is_relative_to(Path.cwd().resolve())
    clip = np.zeros((1, 1664), dtype=np.float32)
    temporal = np.zeros((1, 160), dtype=np.float32)
    features.validate_feature_arrays(clip, temporal)
    with pytest.raises(ValueError):
        features.validate_feature_arrays(clip.astype(np.float64), temporal)
    temporal[0, 0] = np.nan
    with pytest.raises(ValueError):
        features.validate_feature_arrays(clip, temporal)
