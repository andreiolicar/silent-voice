"""Contratos sintéticos da interface GLOBAL, sem câmera ou modelo."""

from dataclasses import replace
import importlib
from pathlib import Path

import pytest

from silent_voice.inference import global_live_visual_tester as global_ui
from silent_voice.inference.live_visual_tester import TemporalCaptureError


def _trial(decision="ACCEPT"):
    return {
        "sample_id": "synthetic_001",
        "predicted_label": "ÁGUA",
        "score": 0.72,
        "threshold": 0.56,
        "decision": decision,
        "emitted_label": "ÁGUA" if decision == "ACCEPT" else None,
        "segmentation_status": "DETECTED",
        "segmentation_fallback": False,
        "source_frame_count": 121,
        "end_to_end_latency_ms": 42.0,
        "capture_timing": {
            "technical_decision": "PASS",
            "source_fps_effective": 30.0,
        },
    }


def test_display_transitions_preserve_r4_decision_and_never_emit_rejected_word():
    state = global_ui.initial_state(camera_index=1)
    assert state.phase == "AGUARDANDO"
    assert state.decision is None and state.word is None
    state = global_ui.capture_state(replace(state, camera_status="ATIVA"))
    assert state.phase == "CAPTURANDO" and state.decision is None
    state = global_ui.processing_state(state)
    assert state.phase == "PROCESSANDO" and state.word is None
    accepted = global_ui.result_state(state, _trial())
    assert accepted.phase == "ACCEPT" and accepted.word == "ÁGUA"
    assert accepted.score_label == "Score do modelo R4"
    rejected = global_ui.result_state(state, _trial("REJECT"))
    assert rejected.phase == "REJECT" and rejected.word is None
    assert rejected.predicted_label == "ÁGUA"
    assert "ÁGUA" not in rejected.headline


def test_technical_error_clears_previous_result_and_allows_manual_retry():
    ready = replace(global_ui.initial_state(1), camera_status="ATIVA")
    accepted = global_ui.result_state(ready, _trial())
    failed = global_ui.error_state(accepted, "source_fps_below_minimum")
    assert failed.phase == "ERRO TÉCNICO"
    assert failed.decision is None and failed.word is None
    assert failed.can_capture is True
    assert "source_fps_below_minimum" in failed.detail
    assert global_ui.capture_state(failed).phase == "CAPTURANDO"


def test_camera_unavailable_and_close_are_distinct_states():
    state = global_ui.initial_state(1)
    unavailable = global_ui.error_state(state, "Câmera indisponível", camera=False)
    assert unavailable.camera_status == "INDISPONÍVEL"
    assert unavailable.can_capture is False
    assert global_ui.closed_state(unavailable).phase == "ENCERRADA"


def test_dashboard_renders_unicode_and_long_errors_without_overflow():
    state = global_ui.error_state(
        global_ui.initial_state(1), "Falha técnica de aquisição " * 25
    )
    image = global_ui.render_dashboard(state, size=(1280, 720))
    assert image.size == (1280, 720)
    assert image.mode == "RGB"
    assert image.getpixel((0, 0)) == (11, 17, 32)
    assert image.getbbox() is not None


def test_preview_mode_does_not_open_camera_or_load_models(monkeypatch):
    calls = []
    monkeypatch.setattr(
        global_ui.legacy, "open_camera", lambda *a: calls.append("camera")
    )
    monkeypatch.setattr(
        global_ui.legacy, "load_live_pipeline", lambda *a: calls.append("model")
    )
    state = global_ui.initial_state(1, visual_preview=True)
    image = global_ui.render_dashboard(state, size=(1280, 720))
    assert image.size == (1280, 720)
    assert state.session_status == "PRÉVIA SINTÉTICA"
    assert calls == []


class FakeBackend:
    def __init__(self, *, temporal_failure=False):
        self.events = []
        self.temporal_failure = temporal_failure

    @staticmethod
    def clip_path(root, session_id, number, *, keep):
        folder = "clips" if keep else "tmp"
        return root / "data" / "processed" / "live_tester" / folder / "test.mp4"

    def record_clip(self, camera, path, **kwargs):
        self.events.append("record")
        if self.temporal_failure:
            raise TemporalCaptureError("source_fps_below_minimum")
        path.write_bytes(b"synthetic video")
        return {
            "technical_decision": "PASS",
            "output_frame_count": 121,
            "source_fps_effective": 30.0,
        }

    def infer_clip(self, pipeline, path, sample_id, session_id, *, root):
        self.events.append("infer")
        return _trial()

    def build_log_record(self, trial, **kwargs):
        self.events.append("log")
        return {
            "decision": trial["decision"],
            "capture_timing": trial["capture_timing"],
        }

    def append_log(self, path, record):
        self.events.append("append")

    def cleanup_temporary_clip(self, root, path):
        self.events.append("cleanup")
        path.unlink(missing_ok=True)


def test_temporal_failure_stops_before_inference_and_creates_no_video(tmp_path):
    backend = FakeBackend(temporal_failure=True)
    with pytest.raises(TemporalCaptureError, match="source_fps_below_minimum"):
        global_ui.perform_capture(
            tmp_path,
            object(),
            object(),
            {},
            camera_index=1,
            session_id="synthetic",
            number=1,
            backend=backend,
        )
    assert backend.events == ["record"]
    assert not list(tmp_path.rglob("*.mp4"))


def test_valid_capture_reuses_r4_pipeline_and_cleans_temporary_clip(tmp_path):
    backend = FakeBackend()
    trial = global_ui.perform_capture(
        tmp_path,
        object(),
        object(),
        {},
        camera_index=1,
        session_id="synthetic",
        number=1,
        backend=backend,
    )
    assert trial["decision"] == "ACCEPT"
    assert trial["capture_timing"]["technical_decision"] == "PASS"
    assert backend.events == ["record", "infer", "log", "append", "cleanup"]
    assert not list(tmp_path.rglob("*.mp4"))


def test_capture_validates_log_destination_before_recording(tmp_path, monkeypatch):
    backend = FakeBackend()

    def blocked(*args):
        raise ValueError("Área diagnóstica redirecionada")

    monkeypatch.setattr(global_ui.legacy, "ensure_diagnostic_path", blocked)
    with pytest.raises(ValueError, match="redirecionada"):
        global_ui.perform_capture(
            tmp_path,
            object(),
            object(),
            {},
            camera_index=1,
            session_id="synthetic",
            number=1,
            backend=backend,
        )
    assert backend.events == []


def test_profile_mode_requires_ready_head_and_preserves_global_state():
    state = global_ui.initial_state(1, visual_preview=True)
    assert state.mode == "GLOBAL"
    with pytest.raises(ValueError, match="perfil"):
        global_ui.select_mode(state, "PERSONALIZED")
    ready = global_ui.profile_state(
        state,
        progress=(2,) * 6,
        status="PRONTO",
        message="Perfil criado.",
    )
    personalized = global_ui.select_mode(ready, "PERSONALIZED")
    assert personalized.mode == "PERSONALIZED"
    assert global_ui.select_mode(personalized, "GLOBAL").mode == "GLOBAL"


def test_profile_panel_has_twelve_clickable_slots_in_synthetic_preview():
    state = global_ui.profile_state(
        global_ui.initial_state(1, visual_preview=True),
        progress=(0, 1, 2, 0, 0, 0),
        status="INCOMPLETO",
        message="Prévia sintética.",
        open_panel=True,
    )
    image = global_ui.render_dashboard(state)
    assert image.size == (1280, 720)
    bounds = global_ui.profile_action_bounds((1280, 720))
    assert len([name for name in bounds if name.startswith("slot_")]) == 12
    assert all(
        right > left and bottom > top for left, top, right, bottom in bounds.values()
    )
    left, top, _, _ = bounds["build"]
    assert image.getpixel((left + 20, top + 5)) != (56, 189, 248)


def test_personal_pipeline_dispatch_keeps_r4_capture_gate(tmp_path):
    class Pipeline:
        def infer_clip(self, video, sample_id, session_id):
            assert sample_id and session_id
            return FakeBackend().infer_clip(
                None, video, sample_id, session_id, root=tmp_path
            )

    backend = FakeBackend()
    trial = global_ui.perform_capture(
        tmp_path,
        object(),
        Pipeline(),
        {},
        camera_index=1,
        session_id="synthetic",
        number=1,
        backend=backend,
    )
    assert trial["decision"] == "ACCEPT"
    assert "infer" not in backend.events


def test_preview_cli_routes_to_visual_only_mode(monkeypatch):
    cli = importlib.import_module("scripts.demo.global_live_visual_tester")
    observed = []
    monkeypatch.setattr(
        cli, "launch_global_tester", lambda *a, **kw: observed.append(kw)
    )
    cli.main(["--visual-preview", "--camera-index", "2"])
    assert observed == [
        {"camera_index": 2, "visual_preview": True, "keep_clips": False}
    ]


def test_cli_forwards_explicit_camera_backend_without_changing_default(
    monkeypatch, tmp_path
):
    cli = importlib.import_module("scripts.demo.global_live_visual_tester")
    observed = []
    monkeypatch.setattr(
        cli, "launch_global_tester", lambda *a, **kw: observed.append(kw)
    )
    cli.main(
        [
            "--artifact-root",
            str(tmp_path),
            "--camera-index",
            "1",
            "--camera-backend",
            "MSMF",
        ]
    )
    assert observed == [
        {
            "camera_index": 1,
            "visual_preview": False,
            "keep_clips": False,
            "camera_backend": "MSMF",
        }
    ]


def test_cli_selects_valid_profile_and_rejects_path_traversal(monkeypatch):
    cli = importlib.import_module("scripts.demo.global_live_visual_tester")
    observed = []
    monkeypatch.setattr(
        cli, "launch_global_tester", lambda *a, **kw: observed.append(kw)
    )
    cli.main(["--visual-preview", "--profile-id", "synthetic_profile"])
    assert observed[0]["profile_id"] == "synthetic_profile"
    with pytest.raises(SystemExit):
        cli.parse_arguments(["--profile-id", "../local_default"])
    assert len(observed) == 1


def test_selected_profile_is_visible_and_isolated_in_window(tmp_path, monkeypatch):
    from silent_voice.inference import global_live_visual_tester_window as window

    app = window.GlobalTesterWindow(
        tmp_path, visual_preview=True, profile_id="synthetic_profile"
    )
    assert app._profile_store.profile_id == "synthetic_profile"
    assert app._profile_store.folder.name == "synthetic_profile"
    assert app.state.profile_id == "synthetic_profile"
    assert app._profile_store.folder != (
        tmp_path / "data/processed/live_tester/profiles/local_default"
    )
    drawn = []
    original = global_ui.ImageDraw.ImageDraw.text

    def observed(draw, xy, text, *args, **kwargs):
        drawn.append(str(text))
        return original(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(global_ui.ImageDraw.ImageDraw, "text", observed)
    global_ui.render_dashboard(app.state)
    assert any("synthetic_profile" in item for item in drawn)


def test_personalized_capture_log_identifies_selected_profile(tmp_path):
    backend = FakeBackend()
    observed = []
    backend.append_log = lambda path, record: observed.append(record)
    global_ui.perform_capture(
        tmp_path,
        object(),
        object(),
        {},
        camera_index=1,
        session_id="synthetic",
        number=1,
        backend=backend,
        profile_id="synthetic_profile",
        profile_version=1,
    )
    assert observed[0]["profile_id"] == "synthetic_profile"
    assert observed[0]["profile_version"] == 1


def test_window_uses_explicit_camera_backend_only_when_selected(tmp_path, monkeypatch):
    from silent_voice.inference import global_live_visual_tester_window as window

    calls = []
    monkeypatch.setattr(window.legacy, "verify_frozen_sources", lambda root: {})
    monkeypatch.setattr(window.legacy, "load_live_pipeline", lambda root: object())
    monkeypatch.setattr(
        window.legacy,
        "open_camera",
        lambda index, *, backend: calls.append((index, backend)) or object(),
    )
    app = window.GlobalTesterWindow(tmp_path, camera_backend="MSMF")
    monkeypatch.setattr(app._profile_store, "load", lambda sources: None)
    app._initialize()
    assert calls == [(1, "MSMF")]
    assert app._events.get_nowait()[0] == "model_ready"
    assert app._events.get_nowait()[0] == "ready"


def test_cli_configures_context_age_and_audio_without_enabling_capture(monkeypatch):
    cli = importlib.import_module("scripts.demo.global_live_visual_tester")
    observed = []
    monkeypatch.setattr(
        cli, "launch_global_tester", lambda *a, **kw: observed.append(kw)
    )
    cli.main(
        [
            "--visual-preview",
            "--whisper-model-path",
            "local-small.pt",
            "--audio-device",
            "1",
            "--audio-sample-rate",
            "44100",
            "--context-max-age-seconds",
            "120",
        ]
    )
    assert observed == [
        {
            "camera_index": 1,
            "visual_preview": True,
            "keep_clips": False,
            "whisper_model_path": Path("local-small.pt"),
            "audio_device": 1,
            "audio_sample_rate": 44100,
            "max_context_age_ns": 120_000_000_000,
        }
    ]


def test_visual_preview_window_runs_without_tcl_camera_or_model(tmp_path, monkeypatch):
    from silent_voice.inference import global_live_visual_tester_window as window

    observed = []

    def forbidden(*args, **kwargs):
        pytest.fail("Prévia sintética abriu câmera ou modelo.")

    monkeypatch.setattr(global_ui.legacy, "open_camera", forbidden)
    monkeypatch.setattr(global_ui.legacy, "load_live_pipeline", forbidden)
    monkeypatch.setattr(global_ui.legacy, "verify_frozen_sources", forbidden)
    monkeypatch.setattr(window.cv2, "namedWindow", lambda *args: None)
    monkeypatch.setattr(window.cv2, "resizeWindow", lambda *args: None)
    monkeypatch.setattr(window.cv2, "setMouseCallback", lambda *args: None)
    monkeypatch.setattr(window.cv2, "getWindowProperty", lambda *args: 1)
    monkeypatch.setattr(
        window.cv2, "getWindowImageRect", lambda *args: (0, 0, 1280, 720)
    )
    monkeypatch.setattr(window.cv2, "imshow", lambda *args: observed.append("frame"))
    monkeypatch.setattr(window.cv2, "waitKey", lambda *args: ord("q"))
    monkeypatch.setattr(
        window.cv2, "destroyWindow", lambda *args: observed.append("closed")
    )
    window.GlobalTesterWindow(tmp_path, visual_preview=True).run()
    assert observed == ["frame", "closed"]


def test_closed_native_window_is_not_recreated_before_exit(tmp_path, monkeypatch):
    from silent_voice.inference import global_live_visual_tester_window as window
    import numpy as np

    visible = True
    frames = 0
    close_reported = False
    destroyed = 0

    def show_frame(*_args):
        nonlocal visible, frames
        visible = True
        frames += 1

    def window_visible(*_args):
        nonlocal visible, close_reported
        if frames == 1 and not close_reported:
            close_reported = True
            visible = False
            return 1
        return int(visible)

    def destroy_window(*_args):
        nonlocal destroyed
        destroyed += 1

    monkeypatch.setattr(window.cv2, "namedWindow", lambda *_args: None)
    monkeypatch.setattr(window.cv2, "resizeWindow", lambda *_args: None)
    monkeypatch.setattr(window.cv2, "setMouseCallback", lambda *_args: None)
    monkeypatch.setattr(
        window.cv2, "getWindowImageRect", lambda *_args: (0, 0, 1280, 720)
    )
    monkeypatch.setattr(window.cv2, "getWindowProperty", window_visible)
    monkeypatch.setattr(window.cv2, "imshow", show_frame)
    monkeypatch.setattr(window.cv2, "cvtColor", lambda frame, _code: frame)
    monkeypatch.setattr(
        window.cv2, "waitKey", lambda *_args: ord("q") if frames >= 4 else -1
    )
    monkeypatch.setattr(window.cv2, "destroyWindow", destroy_window)
    monkeypatch.setattr(
        window,
        "render_dashboard",
        lambda *_args, **_kwargs: np.zeros((1, 1, 3), dtype=np.uint8),
    )

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True)
    app.run()

    assert frames == 1
    assert destroyed == 1
    assert app.state.phase == "ENCERRADA"


def test_close_waits_for_pending_worker_without_redrawing(tmp_path, monkeypatch):
    from threading import Thread
    import time

    from silent_voice.inference import global_live_visual_tester_window as window
    import numpy as np

    frames = []
    keys = [ord("q")]
    monkeypatch.setattr(window.cv2, "namedWindow", lambda *_args: None)
    monkeypatch.setattr(window.cv2, "resizeWindow", lambda *_args: None)
    monkeypatch.setattr(window.cv2, "setMouseCallback", lambda *_args: None)
    monkeypatch.setattr(
        window.cv2, "getWindowImageRect", lambda *_args: (0, 0, 1280, 720)
    )
    monkeypatch.setattr(window.cv2, "getWindowProperty", lambda *_args: 1)
    monkeypatch.setattr(window.cv2, "imshow", lambda *_args: frames.append(1))
    monkeypatch.setattr(window.cv2, "cvtColor", lambda frame, _code: frame)
    monkeypatch.setattr(
        window.cv2, "waitKey", lambda *_args: keys.pop(0) if keys else -1
    )
    monkeypatch.setattr(window.cv2, "destroyWindow", lambda *_args: None)
    monkeypatch.setattr(
        window,
        "render_dashboard",
        lambda *_args, **_kwargs: np.zeros((1, 1, 3), dtype=np.uint8),
    )

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True)

    def pending_task():
        if app._abort.wait(timeout=1):
            time.sleep(0.05)

    app._worker = Thread(target=pending_task, daemon=True)
    app._worker.start()
    app.run()

    assert frames == [1]
    assert not app._worker.is_alive()
    assert app.state.phase == "ENCERRADA"


def test_external_window_close_exits_when_native_window_is_already_destroyed(
    tmp_path, monkeypatch
):
    from silent_voice.inference import global_live_visual_tester_window as window
    import numpy as np

    visible = True

    def close_native_window(*_args):
        nonlocal visible
        visible = False
        return -1

    def destroy_native_window(*_args):
        raise window.cv2.error("NULL window")

    monkeypatch.setattr(window.cv2, "namedWindow", lambda *_args: None)
    monkeypatch.setattr(window.cv2, "resizeWindow", lambda *_args: None)
    monkeypatch.setattr(window.cv2, "setMouseCallback", lambda *_args: None)
    monkeypatch.setattr(
        window.cv2, "getWindowImageRect", lambda *_args: (0, 0, 1280, 720)
    )
    monkeypatch.setattr(window.cv2, "getWindowProperty", lambda *_args: int(visible))
    monkeypatch.setattr(window.cv2, "imshow", lambda *_args: None)
    monkeypatch.setattr(window.cv2, "cvtColor", lambda frame, _code: frame)
    monkeypatch.setattr(window.cv2, "waitKey", close_native_window)
    monkeypatch.setattr(window.cv2, "destroyWindow", destroy_native_window)
    monkeypatch.setattr(
        window,
        "render_dashboard",
        lambda *_args, **_kwargs: np.zeros((1, 1, 3), dtype=np.uint8),
    )

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True)
    app.run()

    assert app.state.phase == "ENCERRADA"


def test_profile_panel_preview_opens_but_cannot_record(tmp_path):
    from silent_voice.inference import global_live_visual_tester_window as window

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True)
    left, top, _, _ = global_ui.action_bounds((1280, 720))["profile"]
    app._on_click(window.cv2.EVENT_LBUTTONDOWN, left + 5, top + 5, 0, None)
    assert app.state.profile_open
    left, top, _, _ = global_ui.profile_action_bounds((1280, 720))["slot_0_1"]
    app._on_click(window.cv2.EVENT_LBUTTONDOWN, left + 5, top + 5, 0, None)
    assert app.state.profile_progress == (0,) * 6
    assert app._worker is None


def test_escape_during_profile_recording_requests_cancellation(tmp_path):
    from silent_voice.inference import global_live_visual_tester_window as window

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True)
    app.state = replace(
        app.state, profile_open=True, phase="CAPTURANDO", active_slot=(0, 1)
    )
    app._on_key(27)
    assert app._capture_cancel.is_set()
    assert not app._closing


def test_context_controls_start_off_and_preview_cannot_enable_them(tmp_path):
    from silent_voice.inference import global_live_visual_tester_window as window

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True)
    assert not app.state.audio_enabled and not app.state.ai_enabled
    assert app.request_toggle_audio() is False
    assert app.request_toggle_ai() is False
    assert not app.state.audio_enabled and not app.state.ai_enabled
    bounds = global_ui.context_action_bounds((1280, 720))
    assert set(bounds) == {"audio", "ai"}
    assert global_ui.render_dashboard(app.state).size == (1280, 720)


def test_context_activation_is_session_scoped_and_never_opens_audio_on_toggle(
    tmp_path, monkeypatch
):
    from silent_voice.inference import global_live_visual_tester_window as window

    events = []

    class Context:
        audio_enabled = False
        ai_enabled = False

        def set_audio_enabled(self, enabled):
            events.append(("audio", enabled))
            self.audio_enabled = enabled
            if not enabled:
                self.ai_enabled = False

        def set_ai_enabled(self, enabled):
            events.append(("ai", enabled))
            self.ai_enabled = enabled

        def close(self):
            events.append("close")
            self.audio_enabled = self.ai_enabled = False

    monkeypatch.setattr(window, "LiveContextSession", lambda *a, **kw: Context())
    app = window.GlobalTesterWindow(tmp_path, whisper_model_path=tmp_path / "small.pt")
    assert app.request_toggle_audio() is True
    assert app.request_toggle_ai() is True
    assert events == [("audio", True), ("ai", True)]
    assert app.state.audio_enabled and app.state.ai_enabled
    assert app.request_toggle_ai() is False
    assert app.request_toggle_ai() is True
    assert app.request_toggle_audio() is False
    assert not app.state.ai_enabled
    app.close()
    assert events[-1] == "close"
    assert not app.state.ai_enabled


@pytest.mark.parametrize("decision", ["ACCEPT", "REJECT"])
@pytest.mark.parametrize("mode", ["GLOBAL", "PERSONALIZED"])
def test_context_advisory_is_associated_with_same_visual_attempt(
    tmp_path, monkeypatch, decision, mode
):
    from silent_voice.inference import global_live_visual_tester_window as window

    events = []
    trial = _trial()
    trial["decision"] = decision
    trial["emitted_label"] = trial["predicted_label"] if decision == "ACCEPT" else None

    class Context:
        audio_enabled = True
        ai_enabled = True

        def capture_context(self, **kwargs):
            events.append("audio")
            return "synthetic-context-attempt"

        def annotate(self, visual, attempt, *, visual_decision_ns):
            assert attempt == "synthetic-context-attempt"
            assert visual is trial
            assert visual_decision_ns > 0
            events.append("advisory")
            return {
                "decision": visual["decision"],
                "word": visual["emitted_label"],
                "relationship": (
                    "SUPPORTED" if decision == "ACCEPT" else "NOT_APPLICABLE"
                ),
                "temporal": {"status": "CURRENT"},
            }

    app = window.GlobalTesterWindow(tmp_path)
    app._context = Context()
    app._camera = object()
    app._pipeline = object()
    app._personal_pipeline = object()
    app._sources = {}
    app.state = replace(
        app.state, audio_enabled=True, ai_enabled=True, mode=mode, can_capture=True
    )
    monkeypatch.setattr(
        window,
        "perform_capture",
        lambda *a, **kw: (events.append("visual"), trial)[1],
    )
    app._capture()
    app._drain_events()
    assert events == ["audio", "visual", "advisory"]
    assert app.state.decision == decision
    assert app.state.word == trial["emitted_label"]
    assert app.state.relationship == (
        "SUPPORTED" if decision == "ACCEPT" else "NOT_APPLICABLE"
    )


def test_revoked_context_is_not_displayed_after_late_result(tmp_path):
    from silent_voice.audio.context_interpreter import ContextResult, ContextStatus
    from silent_voice.audio.contextual_audio import (
        AudioTranscriptionResult,
        TranscriptionStatus,
    )
    from silent_voice.inference import global_live_visual_tester_window as window
    from silent_voice.inference.live_context_session import ContextAttempt

    context = ContextResult(
        status=ContextStatus.AVAILABLE,
        topic="bebida",
        relevant_known_words=("ÁGUA",),
        capture_start_ns=100,
        capture_end_ns=200,
        transcription_received_ns=250,
        context_produced_ns=260,
        transcription_model_id="whisper-local:synthetic",
        provider="synthetic",
        context_model_id="synthetic",
    )
    attempt = ContextAttempt(
        audio=AudioTranscriptionResult(
            text="água",
            start_ns=100,
            end_ns=200,
            status=TranscriptionStatus.AVAILABLE,
            model_id="whisper-local:synthetic",
            language="pt",
        ),
        context=context,
        generation=1,
        capture_latency_ms=5,
        whisper_latency_ms=6,
        groq_latency_ms=7,
    )

    class Revoked:
        def annotate(self, visual, old_attempt, *, visual_decision_ns):
            assert old_attempt is attempt
            return {
                "context": None,
                "relationship": "NO_CONTEXT",
                "temporal": {"status": "NOT_CHECKED"},
            }

    app = window.GlobalTesterWindow(tmp_path)
    app._context = Revoked()
    app.state = replace(app.state, camera_status="ATIVA", ai_enabled=False)
    app._handle_event("result", (_trial(), attempt, 300))
    assert app.state.context_topic is None
    assert app.state.context_words == ()
    assert app.state.relationship == "NO_CONTEXT"
    assert app.state.groq_status == "DESATIVADO"


def test_camera_preview_does_not_read_while_visual_worker_owns_camera(
    tmp_path, monkeypatch
):
    from silent_voice.inference import global_live_visual_tester_window as window

    class Camera:
        def read(self):
            pytest.fail("Prévia competiu com o capturador pela câmera.")

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True)
    app._camera = Camera()
    app.state = replace(app.state, phase="ÁUDIO CONTEXTUAL")
    monkeypatch.setattr(window.cv2, "imshow", lambda *args: None)
    monkeypatch.setattr(
        window,
        "render_dashboard",
        lambda *args, **kwargs: global_ui.render_dashboard(app.state),
    )
    app._camera_owned_by_worker.set()
    app._tick()


def test_fps_diagnostic_mode_skips_redraw_but_drains_capture_events(
    tmp_path, monkeypatch
):
    import numpy as np

    from silent_voice.inference import global_live_visual_tester_window as window
    from silent_voice.inference.live_fps_diagnostic import FpsCaptureTrace

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True, fps_diagnostic=True)
    app.state = replace(app.state, camera_status="ATIVA", can_capture=True)
    app._on_key(ord("f"))
    assert app._fps_mode == "NO_REDRAW"
    app._fps_trace = FpsCaptureTrace(tmp_path, camera_index=1, mode=app._fps_mode)
    app.state = global_ui.capture_state(app.state)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    app._events.put(("capture_frame", (frame, 2.0)))
    monkeypatch.setattr(
        window, "render_dashboard", lambda *a, **kw: pytest.fail("redesenhou")
    )
    monkeypatch.setattr(
        window.cv2, "imshow", lambda *a, **kw: pytest.fail("exibiu frame")
    )
    app._tick()
    assert app._last_frame is frame
    assert app.state.remaining_seconds == 2.0
    app.state = replace(app.state, phase="AGUARDANDO", can_capture=True)
    app._on_key(ord("f"))
    assert app._fps_mode == "NORMAL"


def test_fps_diagnostic_cli_option_reaches_window(monkeypatch, tmp_path):
    from scripts.demo import global_live_visual_tester as cli

    options = []
    monkeypatch.setattr(
        cli, "launch_global_tester", lambda root, **kw: options.append(kw)
    )
    cli.main(
        ["--artifact-root", str(tmp_path), "--camera-index", "1", "--fps-diagnostic"]
    )
    assert options == [
        {
            "camera_index": 1,
            "visual_preview": False,
            "keep_clips": False,
            "fps_diagnostic": True,
        }
    ]


def test_auto_fps_diagnostic_cli_avoids_live_tester_and_models(monkeypatch, tmp_path):
    from scripts.demo import global_live_visual_tester as cli

    calls = []
    monkeypatch.setattr(
        cli, "launch_global_tester", lambda *a, **kw: pytest.fail("abriu tester")
    )
    monkeypatch.setattr(
        cli,
        "run_auto_fps_diagnostic",
        lambda root, *, camera_index: calls.append((root, camera_index)),
        raising=False,
    )
    cli.main(
        [
            "--artifact-root",
            str(tmp_path),
            "--camera-index",
            "1",
            "--fps-auto-diagnostic",
        ]
    )
    assert calls == [(tmp_path.resolve(), 1)]


def test_auto_fps_diagnostic_cli_forwards_backend(monkeypatch, tmp_path):
    from scripts.demo import global_live_visual_tester as cli

    calls = []
    monkeypatch.setattr(
        cli,
        "run_auto_fps_diagnostic",
        lambda root, *, camera_index, camera_backend: calls.append(
            (root, camera_index, camera_backend)
        ),
    )
    cli.main(
        [
            "--artifact-root",
            str(tmp_path),
            "--camera-index",
            "1",
            "--camera-backend",
            "MSMF",
            "--fps-auto-diagnostic",
        ]
    )
    assert calls == [(tmp_path.resolve(), 1, "MSMF")]


def test_auto_fps_diagnostic_collects_abab_without_media(tmp_path, monkeypatch):
    import numpy as np
    from PIL import Image

    from silent_voice.inference import live_fps_diagnostic as diagnostic

    class Camera:
        released = False

        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            self.released = True

        def get(self, _property):
            return 30.0

    camera = Camera()
    current_ns = 0

    def clock_ns():
        nonlocal current_ns
        current_ns += 33_333_334
        return current_ns

    monkeypatch.setattr(diagnostic.cv2, "namedWindow", lambda *a: None)
    monkeypatch.setattr(diagnostic.cv2, "resizeWindow", lambda *a: None)
    monkeypatch.setattr(diagnostic.cv2, "waitKey", lambda *a: -1)
    monkeypatch.setattr(diagnostic.cv2, "imshow", lambda *a: None)
    monkeypatch.setattr(diagnostic.cv2, "destroyWindow", lambda *a: None)
    monkeypatch.setattr(
        diagnostic, "render_dashboard", lambda *a, **kw: Image.new("RGB", (4, 4))
    )
    result = diagnostic.run_auto_fps_diagnostic(
        tmp_path,
        camera_index=1,
        camera_opener=lambda index: camera,
        clock_ns=clock_ns,
        warmup_frames=0,
    )
    assert camera.released is True
    assert [item["mode"] for item in result["attempts"]] == [
        "NORMAL",
        "NO_REDRAW",
        "NORMAL",
        "NO_REDRAW",
    ]
    assert all(item["gate"] == "PASS" for item in result["attempts"])
    assert all(item["source_frame_count"] == 121 for item in result["attempts"])
    assert list(tmp_path.rglob("*.mp4")) == []
    assert len(list(tmp_path.rglob("fps_diagnostic_*.json"))) == 4


def test_fps_diagnostic_persists_distinct_attempts_without_media(tmp_path):
    from silent_voice.inference.live_fps_diagnostic import FpsCaptureTrace

    first = FpsCaptureTrace(tmp_path, camera_index=1, mode="NORMAL")
    second = FpsCaptureTrace(tmp_path, camera_index=1, mode="NO_REDRAW")
    first.record_capture(
        {
            "kind": "read",
            "frame_index": 0,
            "read_start_ns": 100,
            "read_end_ns": 120,
            "policy_timestamp_ns": 121,
            "copy_end_ns": 130,
            "ui_update_end_ns": 140,
        }
    )
    first.record_ui(150, 160)
    first.record_capture(
        {
            "kind": "gate",
            "source_frame_count": 1,
            "source_fps_effective": 0.0,
            "technical_decision": "BLOCKED",
            "technical_failures": ["source_fps_below_minimum"],
        }
    )
    first_path = first.finish(error="Gate temporal bloqueou")
    second_path = second.finish(error="Câmera indisponível")
    assert first_path != second_path
    assert first_path.parent == second_path.parent
    assert list(tmp_path.rglob("*.mp4")) == []
    import json

    payload = json.loads(first_path.read_text(encoding="utf-8"))
    assert payload["attempt_id"] == first.attempt_id
    assert payload["mode"] == "NORMAL"
    assert payload["reads"][0]["policy_timestamp_ns"] == 121
    assert payload["ui_updates"] == [{"start_ns": 150, "end_ns": 160}]
    assert payload["gate"]["source_fps_effective"] == 0.0
    assert payload["error"] == "Gate temporal bloqueou"


def test_failed_capture_saves_diagnostic_without_inference(tmp_path, monkeypatch):
    import json

    from silent_voice.inference import global_live_visual_tester_window as window
    from silent_voice.inference.live_fps_diagnostic import FpsCaptureTrace

    app = window.GlobalTesterWindow(tmp_path, visual_preview=True, fps_diagnostic=True)
    app._fps_trace = FpsCaptureTrace(tmp_path, camera_index=1, mode="NORMAL")
    app._camera = object()
    app._pipeline = object()
    app._sources = {}

    def blocked(*args, **kwargs):
        kwargs["diagnostic_callback"](
            {
                "kind": "gate",
                "technical_decision": "BLOCKED",
                "technical_failures": ["source_fps_below_minimum"],
                "source_frame_count": 106,
                "source_fps_effective": 25.95,
            }
        )
        raise TemporalCaptureError("source_fps_below_minimum")

    monkeypatch.setattr(window, "perform_capture", blocked)
    app._capture()
    files = list(tmp_path.rglob("fps_diagnostic_*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["gate"]["source_frame_count"] == 106
    assert payload["error"] == "source_fps_below_minimum"
    assert app._events.get_nowait()[0] == "visual_start"
    assert app._events.get_nowait()[0] == "capture_error"


def test_visual_gate_failure_keeps_context_status_without_accept_or_reject(
    tmp_path, monkeypatch
):
    from silent_voice.audio.context_interpreter import ContextResult, ContextStatus
    from silent_voice.audio.contextual_audio import (
        AudioTranscriptionResult,
        TranscriptionStatus,
    )
    from silent_voice.inference import global_live_visual_tester_window as window
    from silent_voice.inference.live_context_session import ContextAttempt

    attempt = ContextAttempt(
        audio=AudioTranscriptionResult(
            text="água",
            start_ns=100,
            end_ns=200,
            status=TranscriptionStatus.AVAILABLE,
            model_id="whisper-local:synthetic",
            language="pt",
        ),
        context=ContextResult(
            status=ContextStatus.AVAILABLE,
            topic="bebida",
            relevant_known_words=("ÁGUA",),
            capture_start_ns=100,
            capture_end_ns=200,
            transcription_received_ns=250,
            context_produced_ns=260,
            transcription_model_id="whisper-local:synthetic",
            provider="synthetic",
            context_model_id="synthetic",
        ),
        generation=1,
        capture_latency_ms=5,
        whisper_latency_ms=6,
        groq_latency_ms=7,
    )

    class Context:
        audio_enabled = True

        def capture_context(self, **kwargs):
            return attempt

        def annotate(self, visual, old_attempt, *, visual_decision_ns):
            assert old_attempt is attempt
            assert visual.reason == "source_fps_below_minimum"
            return {
                "context": attempt.context.to_dict(),
                "relationship": "NOT_APPLICABLE",
                "temporal": {"status": "NOT_CHECKED"},
            }

    app = window.GlobalTesterWindow(tmp_path)
    app._context = Context()
    app._camera = object()
    app._pipeline = object()
    app._sources = {}
    app.state = replace(app.state, audio_enabled=True, ai_enabled=True)

    def blocked(*args, **kwargs):
        raise TemporalCaptureError("source_fps_below_minimum")

    monkeypatch.setattr(window, "perform_capture", blocked)
    app._capture()
    app._drain_events()
    assert app.state.phase == "ERRO TÉCNICO"
    assert app.state.decision is None and app.state.word is None
    assert app.state.context_topic == "bebida"
    assert app.state.relationship == "NOT_APPLICABLE"
