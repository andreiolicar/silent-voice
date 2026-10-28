"""Falhas sintéticas de gravação e preservação de arquivos existentes."""

from pathlib import Path

import numpy as np
import pytest

from scripts.demo import msv_temporal_capture as temporal


def test_partial_video_is_removed_after_encoder_failure(tmp_path, monkeypatch):
    path = tmp_path / "attempt.mp4"

    class BrokenWriter:
        def __init__(self, filename, *_args):
            Path(filename).write_bytes(b"partial")

        def isOpened(self):
            return True

        def write(self, _frame):
            raise RuntimeError("synthetic encoder failure")

        def release(self):
            return None

    monkeypatch.setattr(temporal.cv2, "VideoWriter", BrokenWriter)
    policy = temporal.load_policy(version=2)
    frames = [np.zeros((480, 640, 3), dtype=np.uint8)] * 121
    timestamps = [round(i * 1_000_000_000 / 30) for i in range(121)]
    with pytest.raises(RuntimeError, match="synthetic encoder failure"):
        temporal.write_video_with_sidecar(
            path, frames, timestamps, policy, cleanup_on_error=True
        )
    assert not path.exists()
    assert not temporal.sidecar_path(path).exists()


@pytest.mark.parametrize("existing", ["video", "sidecar"])
def test_existing_attempt_is_preserved(tmp_path, existing):
    path = tmp_path / "attempt.mp4"
    target = path if existing == "video" else temporal.sidecar_path(path)
    target.write_bytes(b"existing data")
    policy = temporal.load_policy(version=2)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    with pytest.raises(FileExistsError):
        temporal.write_video_with_sidecar(
            path, [frame, frame], [0, 4_000_000_000], policy, cleanup_on_error=True
        )
    assert target.read_bytes() == b"existing data"


def test_requested_retention_preserves_partial_video(tmp_path, monkeypatch):
    path = tmp_path / "attempt.mp4"

    class BrokenWriter:
        def __init__(self, filename, *_args):
            Path(filename).write_bytes(b"partial")

        def isOpened(self):
            return False

        def release(self):
            return None

    monkeypatch.setattr(temporal.cv2, "VideoWriter", BrokenWriter)
    policy = temporal.load_policy(version=2)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    with pytest.raises(RuntimeError, match="codificação"):
        temporal.write_video_with_sidecar(
            path, [frame, frame], [0, 4_000_000_000], policy, cleanup_on_error=False
        )
    assert path.read_bytes() == b"partial"


def test_cleanup_preserves_an_attempt_not_created_by_this_process(tmp_path):
    from silent_voice.inference import live_visual_tester as tester

    path = tester.clip_path(tmp_path, "existing", 1, keep=False)
    path.parent.mkdir(parents=True)
    sidecar = temporal.sidecar_path(path)
    path.write_bytes(b"existing video")
    sidecar.write_bytes(b"existing sidecar")
    tester.cleanup_temporary_clip(tmp_path, path)
    assert path.read_bytes() == b"existing video"
    assert sidecar.read_bytes() == b"existing sidecar"


@pytest.mark.parametrize("cleanup", [True, False])
def test_sidecar_failure_respects_retention(tmp_path, monkeypatch, cleanup):
    path = tmp_path / "attempt.mp4"

    class Writer:
        def __init__(self, filename, *_args):
            self.path = Path(filename)

        def isOpened(self):
            return True

        def write(self, _frame):
            return None

        def release(self):
            self.path.write_bytes(b"video")

    monkeypatch.setattr(temporal.cv2, "VideoWriter", Writer)
    policy = temporal.load_policy(version=2)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    original = temporal.canonical_bytes

    def fail_report(value):
        if "video_sha256" in value:
            raise RuntimeError("synthetic sidecar failure")
        return original(value)

    monkeypatch.setattr(temporal, "canonical_bytes", fail_report)
    with pytest.raises(RuntimeError, match="synthetic sidecar failure"):
        temporal.write_video_with_sidecar(
            path, [frame, frame], [0, 4_000_000_000], policy, cleanup_on_error=cleanup
        )
    assert path.exists() is not cleanup
    assert temporal.sidecar_path(path).exists() is not cleanup


def test_cleanup_rejects_video_symlink_outside_diagnostics(tmp_path):
    from silent_voice.inference import live_visual_tester as tester

    target = tmp_path / "outside.mp4"
    target.write_bytes(b"private")
    link = tester.clip_path(tmp_path, "link", 1, keep=False)
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlink real indisponível neste ambiente")
    with pytest.raises(ValueError):
        tester.cleanup_temporary_clip(tmp_path, link)
    assert target.read_bytes() == b"private"
