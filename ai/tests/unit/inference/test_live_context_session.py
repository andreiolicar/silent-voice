"""C4.2: contratos C1/C2/C3 com áudio e rede substituídos por fontes sintéticas."""

from concurrent.futures import Future
from dataclasses import replace
from threading import Event
import json

import pytest

from silent_voice.audio.contextual_audio import (
    AudioTranscriptionResult,
    TranscriptionStatus,
)
from silent_voice.audio.context_interpreter import ContextStatus
from silent_voice.audio.context_interpreter import GroqContextProvider
from silent_voice.inference.live_context_session import LiveContextSession


def _audio(status=TranscriptionStatus.AVAILABLE):
    return AudioTranscriptionResult(
        text="Você quer água?" if status is TranscriptionStatus.AVAILABLE else None,
        start_ns=100,
        end_ns=200,
        status=status,
        model_id="whisper-local:synthetic",
        language="pt",
    )


def _visual(decision="ACCEPT", label="ÁGUA"):
    return {
        "predicted_label": label,
        "emitted_label": label if decision == "ACCEPT" else None,
        "score": 0.7,
        "threshold": 0.5666271450980487,
        "decision": decision,
    }


class SyntheticAudioSession:
    def __init__(self, result, events):
        self.result = result
        self.events = events

    def start(self, *, device, requested_samplerate):
        self.events.append(("start", device, requested_samplerate))

    def stop_async(self):
        self.events.append("stop")
        future = Future()
        future.set_result(self.result)
        return future

    def close(self):
        self.events.append("close")


class SyntheticProvider:
    name = "synthetic"
    model_id = "synthetic-context"
    configured = True

    def __init__(self, events, response=None):
        self.events = events
        self.response = response or (
            '{"topic":"bebida","relevant_known_words":["ÁGUA"]}'
        )

    def generate(self, text):
        self.events.append(("send", text))
        return self.response


def _session(tmp_path, *, result=None, provider=None, max_age=150, events=None):
    events = [] if events is None else events
    checkpoint = tmp_path / "small.pt"
    checkpoint.write_bytes(b"synthetic checkpoint marker")
    audio = SyntheticAudioSession(result or _audio(), events)
    context_provider = provider or SyntheticProvider(events)
    session = LiveContextSession(
        checkpoint,
        device=1,
        sample_rate=44100,
        max_context_age_ns=max_age,
        audio_factory=lambda *args, **kwargs: audio,
        provider_factory=lambda **kwargs: context_provider,
        beep=lambda: events.append("beep"),
        wait_for_capture=lambda cancel, seconds: events.append(("wait", seconds)),
        clock_ns=lambda: 250,
    )
    return session, events


def test_defaults_never_open_microphone_or_send_text(tmp_path):
    session, events = _session(tmp_path)
    assert session.audio_enabled is False
    assert session.ai_enabled is False
    assert session.capture_context() is None
    assert session.annotate(_visual(), None, visual_decision_ns=300)[
        "relationship"
    ] == ("NO_CONTEXT")
    assert events == []
    session.close()


def test_one_opted_in_capture_reuses_c1_c2_and_c3_without_changing_accept(tmp_path):
    session, events = _session(tmp_path)
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    attempt = session.capture_context()
    advisory = session.annotate(_visual(), attempt, visual_decision_ns=300)
    assert events[:3] == [("start", 1, 44100), "beep", ("wait", 5.0)]
    assert events[3:] == ["stop", ("send", "Você quer água?")]
    assert attempt.audio.status is TranscriptionStatus.AVAILABLE
    assert attempt.context.status is ContextStatus.AVAILABLE
    assert advisory["relationship"] == "SUPPORTED"
    assert advisory["decision"] == "ACCEPT" and advisory["word"] == "ÁGUA"
    session.close()


def test_reject_stays_reject_in_both_visual_modes(tmp_path):
    session, _ = _session(tmp_path)
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    attempt = session.capture_context()
    for mode in ("GLOBAL", "PERSONALIZED"):
        visual = {**_visual("REJECT"), "mode": mode}
        advisory = session.annotate(visual, attempt, visual_decision_ns=300)
        assert advisory["visual"]["mode"] == mode
        assert advisory["decision"] == "REJECT"
        assert advisory["word"] is None
        assert advisory["relationship"] == "NOT_APPLICABLE"
    session.close()


def test_silence_never_reaches_provider_and_keeps_visual_decision(tmp_path):
    session, events = _session(tmp_path, result=_audio(TranscriptionStatus.NO_SPEECH))
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    attempt = session.capture_context()
    advisory = session.annotate(_visual(), attempt, visual_decision_ns=300)
    assert attempt.context.status is ContextStatus.NO_SPEECH
    assert not any(isinstance(item, tuple) and item[0] == "send" for item in events)
    assert advisory["relationship"] == "NO_CONTEXT"
    assert advisory["decision"] == "ACCEPT"
    session.close()


def test_provider_error_is_unavailable_context_without_visual_override(tmp_path):
    provider = SyntheticProvider([], response="invalid JSON")
    session, _ = _session(tmp_path, provider=provider)
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    attempt = session.capture_context()
    advisory = session.annotate(_visual(), attempt, visual_decision_ns=300)
    assert attempt.context.status is ContextStatus.INVALID_RESPONSE
    assert advisory["relationship"] == "NO_CONTEXT"
    assert advisory["word"] == "ÁGUA"
    session.close()


def test_context_expiry_and_missing_policy_do_not_claim_support(tmp_path):
    session, _ = _session(tmp_path, max_age=99)
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    attempt = session.capture_context()
    assert (
        session.annotate(_visual(), attempt, visual_decision_ns=300)["relationship"]
        == "STALE_CONTEXT"
    )
    session.close()
    unknown, _ = _session(tmp_path, max_age=None)
    unknown.set_audio_enabled(True)
    unknown.set_ai_enabled(True)
    attempt = unknown.capture_context()
    assert (
        unknown.annotate(_visual(), attempt, visual_decision_ns=300)["relationship"]
        == "TEMPORAL_UNKNOWN"
    )
    unknown.close()


def test_revocation_blocks_new_sends_and_discards_old_context(tmp_path):
    session, events = _session(tmp_path)
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    attempt = session.capture_context()
    session.set_ai_enabled(False)
    assert (
        session.annotate(_visual(), attempt, visual_decision_ns=300)["relationship"]
        == "NO_CONTEXT"
    )
    second = session.capture_context()
    assert second.context.status is ContextStatus.DISABLED
    assert (
        len([item for item in events if isinstance(item, tuple) and item[0] == "send"])
        == 1
    )
    session.close()
    assert not session.ai_enabled
    with pytest.raises(RuntimeError, match="encerrada"):
        session.set_ai_enabled(True)


def test_disabling_during_capture_skips_provider(tmp_path):
    events = []
    session, events = _session(tmp_path, events=events)
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)

    def disable(cancel, seconds):
        session.set_ai_enabled(False)

    session._wait_for_capture = disable
    attempt = session.capture_context(cancel=Event())
    assert attempt.context.status is ContextStatus.DISABLED
    assert not any(isinstance(item, tuple) and item[0] == "send" for item in events)
    session.close()


def test_disabling_audio_interrupts_active_microphone_wait(tmp_path):
    session, _ = _session(tmp_path)
    session.set_audio_enabled(True)
    cancel = Event()
    observed = {}

    def disable(wait_event, seconds):
        observed["same_event"] = wait_event is cancel
        session.set_audio_enabled(False)
        observed["cancelled"] = wait_event.is_set()

    session._wait_for_capture = disable
    session.capture_context(cancel=cancel)
    assert observed == {"same_event": True, "cancelled": True}
    assert not session.audio_enabled
    session.close()


def test_capture_failure_does_not_beep_or_send(tmp_path):
    session, events = _session(tmp_path)
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    session._audio_factory = lambda *args, **kwargs: FailingAudio()
    attempt = session.capture_context()
    assert attempt.audio.status is TranscriptionStatus.CAPTURE_FAILED
    assert "beep" not in events
    assert attempt.context.status is ContextStatus.CAPTURE_FAILED
    session.close()


def test_revocation_during_model_get_blocks_following_post(tmp_path):
    events = []
    holder = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"data": [{"id": "openai/gpt-oss-20b", "active": True}]}
            ).encode("utf-8")

    def opener(request, *, timeout):
        events.append(request.get_method())
        if request.get_method() == "GET":
            holder["session"].set_ai_enabled(False)
        return Response()

    session, _ = _session(tmp_path, events=events)
    session._provider_factory = lambda *, opener: GroqContextProvider(
        model_id="openai/gpt-oss-20b", api_key="synthetic", opener=opener
    )
    session._network_opener = opener
    holder["session"] = session
    session.set_audio_enabled(True)
    session.set_ai_enabled(True)
    attempt = session.capture_context()
    assert events.count("GET") == 1
    assert "POST" not in events
    assert attempt.context.status is ContextStatus.PROVIDER_ERROR
    assert (
        session.annotate(_visual(), attempt, visual_decision_ns=300)["relationship"]
        == "NO_CONTEXT"
    )
    session.close()


class FailingAudio:
    def start(self, **kwargs):
        from silent_voice.audio.contextual_audio import AudioCaptureError

        raise AudioCaptureError(
            replace(_audio(), status=TranscriptionStatus.CAPTURE_FAILED, text=None)
        )

    def close(self):
        return None
