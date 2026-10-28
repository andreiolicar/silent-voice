"""Orquestra C1, C2 e C3 para uma tentativa casual do Live Tester."""

from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock
import time
from urllib.request import urlopen

from silent_voice.audio.contextual_audio import (
    AudioCaptureError,
    AudioTranscriptionResult,
    ContextualAudioSession,
    TranscriptionStatus,
    _default_stream_factory,
)
from silent_voice.audio.context_interpreter import (
    ContextInterpreter,
    ContextResult,
    GroqContextProvider,
)
from silent_voice.fusion.context_advisory import (
    TemporalReference,
    VisualTechnicalFailure,
    integrate_advisory,
)


def _beep_once() -> None:
    import winsound

    winsound.Beep(880, 150)


def _wait_for_capture(cancel: Event, seconds: float) -> None:
    cancel.wait(seconds)


@dataclass(frozen=True, slots=True)
class ContextAttempt:
    audio: AudioTranscriptionResult
    context: ContextResult
    generation: int
    capture_latency_ms: float
    whisper_latency_ms: float
    groq_latency_ms: float | None


class LiveContextSession:
    """Consentimento de sessão e recursos C1/C2 mantidos fora da UI gráfica."""

    def __init__(
        self,
        model_path: Path,
        *,
        device=None,
        sample_rate=None,
        max_context_age_ns: int | None = None,
        audio_factory=ContextualAudioSession,
        provider_factory=None,
        stream_factory=_default_stream_factory,
        network_opener=urlopen,
        beep=None,
        wait_for_capture=None,
        clock_ns=None,
    ) -> None:
        if max_context_age_ns is not None and (
            type(max_context_age_ns) is not int or max_context_age_ns <= 0
        ):
            raise ValueError("O prazo contextual configurado deve ser positivo.")
        self.model_path = Path(model_path)
        self.device = device
        self.sample_rate = sample_rate
        self.max_context_age_ns = max_context_age_ns
        self._audio_factory = audio_factory
        self._provider_factory = provider_factory or (
            lambda *, opener: GroqContextProvider(
                model_id="openai/gpt-oss-20b", opener=opener
            )
        )
        self._stream_factory_base = stream_factory
        self._network_opener = network_opener
        self._beep = beep or _beep_once
        self._wait_for_capture = wait_for_capture or _wait_for_capture
        self._clock_ns = clock_ns or time.perf_counter_ns
        self._lock = Lock()
        self._gate = Event()
        self._cancel = Event()
        self._generation = 0
        self._closed = False
        self._audio_enabled = False
        self._ai_enabled = False
        self._provider = None
        self._audio_session = None
        self._active_cancel = None

    @property
    def audio_enabled(self) -> bool:
        with self._lock:
            return self._audio_enabled

    @property
    def ai_enabled(self) -> bool:
        with self._lock:
            return self._ai_enabled

    def set_audio_enabled(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValueError("Estado de áudio inválido.")
        with self._lock:
            if self._closed:
                raise RuntimeError("Sessão contextual encerrada.")
            if enabled and not self.model_path.is_file():
                raise ValueError("Checkpoint Whisper local indisponível.")
            if self._audio_enabled == enabled:
                return
            self._generation += 1
            self._audio_enabled = enabled
            if not enabled:
                self._ai_enabled = False
                self._provider = None
                self._cancel.set()
                if self._active_cancel is not None:
                    self._active_cancel.set()
            else:
                self._cancel.clear()

    def _checked_open(self, generation: int, request, *, timeout):
        with self._lock:
            allowed = (
                not self._closed and self._ai_enabled and self._generation == generation
            )
        if not allowed:
            raise RuntimeError("Autorização contextual desta sessão revogada.")
        return self._network_opener(request, timeout=timeout)

    def set_ai_enabled(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValueError("Estado de contexto com IA inválido.")
        with self._lock:
            if self._closed:
                raise RuntimeError("Sessão contextual encerrada.")
            if enabled and not self._audio_enabled:
                raise ValueError("Ative primeiro o áudio contextual.")
            if self._ai_enabled == enabled:
                return
            self._generation += 1
            generation = self._generation
            self._ai_enabled = enabled
            self._provider = None
        if enabled:
            provider = self._provider_factory(
                opener=lambda request, *, timeout: self._checked_open(
                    generation, request, timeout=timeout
                )
            )
            if not provider.configured:
                with self._lock:
                    self._generation += 1
                    self._ai_enabled = False
                raise ValueError("Chave Groq local indisponível.")
            with self._lock:
                if self._generation == generation and self._ai_enabled:
                    self._provider = provider

    def _stream_factory(self, callback, device, requested_samplerate):
        def after_beep(indata, frames, time_info, status):
            if self._gate.is_set():
                callback(indata, frames, time_info, status)

        return self._stream_factory_base(after_beep, device, requested_samplerate)

    def _session(self):
        if self._audio_session is None:
            self._audio_session = self._audio_factory(
                self.model_path,
                stream_factory=self._stream_factory,
                clock_ns=self._clock_ns,
            )
        return self._audio_session

    def capture_context(self, *, cancel: Event | None = None, on_stage=None):
        """Captura 5 s após o bip, libera C1 e só então chama C2 se autorizado."""
        with self._lock:
            if self._closed or not self._audio_enabled:
                return None
            generation = self._generation
            provider = self._provider if self._ai_enabled else None
        cancel = cancel or self._cancel
        with self._lock:
            self._active_cancel = cancel
        session = self._session()
        self._gate.clear()
        started = self._clock_ns()
        if on_stage:
            on_stage("CAPTURANDO ÁUDIO")
        try:
            session.start(device=self.device, requested_samplerate=self.sample_rate)
        except AudioCaptureError as error:
            audio = error.result
            capture_ms = (self._clock_ns() - started) / 1e6
            whisper_ms = 0.0
        else:
            beep_error = None
            try:
                self._beep()
                self._gate.set()
                self._wait_for_capture(cancel, 5.0)
            except Exception as error:
                beep_error = str(error)
            finally:
                self._gate.clear()
                stopped = self._clock_ns()
                future = session.stop_async()
            if on_stage:
                on_stage("TRANSCRIBINDO")
            audio = future.result()
            capture_ms = (stopped - started) / 1e6
            whisper_ms = (self._clock_ns() - stopped) / 1e6
            if beep_error is not None:
                audio = AudioTranscriptionResult(
                    text=None,
                    start_ns=audio.start_ns,
                    end_ns=audio.end_ns,
                    status=TranscriptionStatus.CAPTURE_FAILED,
                    model_id=audio.model_id,
                    language=audio.language,
                    error=f"Sinal sonoro indisponível: {beep_error}",
                    source_sample_rate=audio.source_sample_rate,
                    chunk_timestamps_ns=audio.chunk_timestamps_ns,
                )
        with self._lock:
            allowed = (
                not self._closed
                and self._ai_enabled
                and self._generation == generation
                and provider is not None
                and not cancel.is_set()
                and not self._cancel.is_set()
            )
        if on_stage and allowed and audio.status is TranscriptionStatus.AVAILABLE:
            on_stage("CONSULTANDO GROQ")
        groq_start = self._clock_ns()
        context = ContextInterpreter(
            provider=provider if allowed else None,
            enabled=allowed,
            clock_ns=self._clock_ns,
        ).interpret(audio, external_consent=allowed)
        groq_ms = (
            (self._clock_ns() - groq_start) / 1e6
            if allowed and audio.status is TranscriptionStatus.AVAILABLE
            else None
        )
        result = ContextAttempt(
            audio=audio,
            context=context,
            generation=generation,
            capture_latency_ms=capture_ms,
            whisper_latency_ms=whisper_ms,
            groq_latency_ms=groq_ms,
        )
        with self._lock:
            if self._active_cancel is cancel:
                self._active_cancel = None
        return result

    def annotate(
        self,
        visual: dict | VisualTechnicalFailure,
        attempt: ContextAttempt | None,
        *,
        visual_decision_ns: int,
    ) -> dict:
        """O C3 observa a decisão visual e nunca a modifica."""
        with self._lock:
            usable = (
                attempt is not None
                and not self._closed
                and self._audio_enabled
                and attempt.generation == self._generation
            )
        context = attempt.context if usable else None
        reference = TemporalReference(
            visual_decision_ns=visual_decision_ns,
            max_context_age_ns=self.max_context_age_ns or 1,
            shared_monotonic_origin=self.max_context_age_ns is not None,
        )
        if (
            isinstance(visual, dict)
            and visual.get("score") is None
            and visual.get("technical_reason")
        ):
            visual = VisualTechnicalFailure(
                reason=visual["technical_reason"],
                capture_timing=visual.get("capture_timing"),
            )
        return integrate_advisory(visual, context, reference)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._generation += 1
            self._audio_enabled = False
            self._ai_enabled = False
            self._provider = None
            self._cancel.set()
            if self._active_cancel is not None:
                self._active_cancel.set()
        if self._audio_session is not None:
            self._audio_session.close()
