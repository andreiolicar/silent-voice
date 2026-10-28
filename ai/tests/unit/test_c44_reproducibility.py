"""Public byte checks and optional private provenance integration."""

from hashlib import sha256
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = {
    "rejection_4_reference_bank_manifest.json": (
        "9d1ea4aa1ad869a6dc9076ecbbd9f81510b262c5c293600d54a84908a47456b5"
    ),
    "rejection_4_final_freeze.json": (
        "d2d37118ce0278192a7777951d30c7aefbfb4a3d1caa60858c1394f2fded19e1"
    ),
    "global_visual_v2_class_conditional_human_decision_resolution.json": (
        "ed13ca983c2814822fbc65ac16142ab365b1e281d0eff2b96d4efb1fc8d483bf"
    ),
}


def test_synthetic_line_endings_and_integrity(tmp_path):
    lf = b"synthetic\nfixture\n"
    crlf = lf.replace(b"\n", b"\r\n")
    path = tmp_path / "fixture.txt"
    path.write_bytes(crlf)
    assert path.read_bytes() == crlf
    assert sha256(path.read_bytes()).digest() != sha256(lf).digest()
    assert path.read_bytes().replace(b"\r\n", b"\n") == lf


def test_temporal_policy_has_original_hash():
    path = ROOT / "docs/cycles/multispeaker_visual_01_temporal_policy_v2.json"
    assert sha256(path.read_bytes()).hexdigest() == (
        "4680a3fb47866d470fb98223c8f8d654d19150905d4ba7289096e80d8a6f39a1"
    )


@pytest.mark.parametrize("name,expected", PRIVATE.items())
def test_private_document_integrity_when_available(name, expected):
    path = ROOT / "docs/cycles" / name
    if not path.is_file():
        pytest.skip("Documento privado não disponibilizado neste ambiente")
    payload = path.read_bytes()
    assert sha256(payload).hexdigest() == expected
    assert isinstance(json.loads(payload), dict)
