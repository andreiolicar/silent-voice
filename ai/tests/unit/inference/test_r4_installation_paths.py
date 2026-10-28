"""Resolução de implementação congelada com dados inteiramente sintéticos."""

from hashlib import sha256
from pathlib import Path

import pytest

from silent_voice.edge import cycle_06_final_heldout as provenance
from silent_voice.inference import live_visual_tester as live
from scripts.demo import global_live_visual_tester as cli


def _synthetic_config(package):
    hashes = {}
    for name, recorded in provenance.IMPLEMENTATION_FILES.items():
        relative = Path(recorded).relative_to("src/silent_voice")
        target = package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = name.encode("ascii")
        target.write_bytes(payload)
        hashes[name] = sha256(payload).hexdigest()
    config = {
        "runtime_implementation_sha256": hashes["runtime_implementation_sha256"],
        "preprocessing": {
            "roi_definition": {
                "implementation_sha256": hashes["roi_implementation_sha256"]
            },
            "segmentation_implementation_sha256": hashes[
                "segmentation_implementation_sha256"
            ],
            "preprocessing_implementation_sha256": hashes[
                "preprocessing_implementation_sha256"
            ],
        },
        "dtw": {
            "distance_implementation_sha256": hashes["distance_implementation_sha256"],
            "evidence_implementation_sha256": hashes["evidence_implementation_sha256"],
        },
        "rejection": {
            "centroid_and_score_implementation_sha256": hashes[
                "centroid_and_score_implementation_sha256"
            ],
            "threshold_selection_implementation_sha256": hashes[
                "threshold_selection_implementation_sha256"
            ],
        },
    }
    return config, hashes


def test_implementation_hashes_use_installed_package_not_private_root(tmp_path):
    package = tmp_path / "installed" / "silent_voice"
    config, expected = _synthetic_config(package)
    private_root = tmp_path / "private"
    private_root.mkdir()
    assert (
        provenance._frozen_implementation_hashes(
            private_root, config, implementation_root=package
        )
        == expected
    )


def test_existing_source_tree_layout_still_works(tmp_path):
    config, expected = _synthetic_config(tmp_path / "src" / "silent_voice")
    assert provenance._frozen_implementation_hashes(tmp_path, config) == expected


@pytest.mark.parametrize("change", ["missing", "wrong_hash"])
def test_installed_implementation_missing_or_changed_fails(tmp_path, change):
    package = tmp_path / "installed" / "silent_voice"
    config, _ = _synthetic_config(package)
    recorded = next(iter(provenance.IMPLEMENTATION_FILES.values()))
    target = package / Path(recorded).relative_to("src/silent_voice")
    if change == "missing":
        target.unlink()
    else:
        target.write_bytes(b"different")
    with pytest.raises((FileNotFoundError, ValueError)):
        provenance._frozen_implementation_hashes(
            tmp_path / "private", config, implementation_root=package
        )


def test_implementation_path_outside_package_is_rejected(tmp_path, monkeypatch):
    package = tmp_path / "installed" / "silent_voice"
    config, _ = _synthetic_config(package)
    monkeypatch.setitem(
        provenance.IMPLEMENTATION_FILES, "runtime_implementation_sha256", "../other.py"
    )
    with pytest.raises(ValueError):
        provenance._frozen_implementation_hashes(
            tmp_path / "private", config, implementation_root=package
        )


def test_cli_uses_explicit_private_root(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli, "launch_global_tester", lambda root, **kw: calls.append(root)
    )
    cli.main(["--artifact-root", str(tmp_path)])
    assert calls == [tmp_path.resolve()]


def test_cli_does_not_guess_private_root():
    with pytest.raises(SystemExit, match="artifact-root"):
        cli.main([])


def test_missing_private_freeze_blocks_preflight(tmp_path):
    with pytest.raises(FileNotFoundError, match="ausente"):
        live.verify_frozen_sources(tmp_path)
