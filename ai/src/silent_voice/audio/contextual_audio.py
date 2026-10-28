"""Captura contextual mono e transcrição Whisper local sob comando explícito."""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from math import gcd, isfinite
from pathlib import Path
from threading import Lock
import hashlib
import time

import numpy as np
from scipy.signal import resample_poly


WHISPER_SAMPLE_RATE = 16_000


class TranscriptionStatus(str, Enum):
    AVAILABLE = "TRANSCRIPTION_AVAILABLE"
    NO_SPEECH = "NO_SPEECH"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"


@dataclass(frozen=True, slots=True)
class AudioTranscriptionResult:
    text: str | None
    start_ns: int | None
    end_ns: int | None
    status: TranscriptionStatus
    model_id: str
    language: str
    error: str | None = None
    source_sample_rate: float | None = None
    chunk_timestamps_ns: tuple[int, ...] = ()

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "status": self.status.value,
            "model_id": self.model_id,
            "language": self.language,
            "error": self.error,
            "source_sample_rate": self.source_sample_rate,
            "chunk_timestamps_ns": list(self.chunk_timestamps_ns),
        }


class AudioCaptureError(RuntimeError):
    def __init__(self, result: AudioTranscriptionResult):
        self.result = result
        super().__init__(result.error or "Falha de captura de áudio.")


def prepare_whisper_audio(samples: np.ndarray, sample_rate: float) -> np.ndarray:
    """Converte uma sequência mono da taxa efetiva para float32/16 kHz."""
    audio = np.asarray(samples, dtype=np.float32)
    if audio.ndim != 1:
        raise ValueError("O áudio para Whisper deve ser mono e unidimensional.")
    if not isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("A taxa de amostragem deve ser positiva e finita.")
    rounded_rate = round(sample_rate)
    if abs(sample_rate - rounded_rate) > 0.01:
        raise ValueError("A taxa real do dispositivo deve ser um número inteiro de Hz.")
    if not np.all(np.isfinite(audio)):
        raise ValueError("O áudio contém valores não finitos.")
    if rounded_rate == WHISPER_SAMPLE_RATE:
        return np.ascontiguousarray(audio)
    divisor = gcd(rounded_rate, WHISPER_SAMPLE_RATE)
    converted = resample_poly(
        audio, WHISPER_SAMPLE_RATE // divisor, rounded_rate // divisor
    )
    return np.ascontiguousarray(converted, dtype=np.float32)


def _default_stream_factory(callback, device, requested_samplerate):
    import sounddevice as sd

    samplerate = requested_samplerate
    if samplerate is None:
        samplerate = sd.query_devices(device, "input")["default_samplerate"]
    return sd.InputStream(
        samplerate=samplerate,
        device=device,
        channels=1,
        dtype="float32",
        callback=callback,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ContextualAudioSession:
    """O microfone só abre em ``start``; ``stop_async`` devolve um Future."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        stream_factory=None,
        model_loader=None,
        clock_ns=None,
    ) -> None:
        self.model_path = Path(model_path)
        self._stream_factory = stream_factory or _default_stream_factory
        self._model_loader = model_loader
        self._clock_ns = clock_ns or time.perf_counter_ns
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")
        self._lock = Lock()
        self._model_lock = Lock()
        self._model = None
        self._model_id = f"whisper-local:{self.model_path.name}"
        self._stream = None
        self._recording = False
        self._closed = False
        self._started_ns = None
        self._sample_rate = None
        self._chunks = []
        self._capture_issue = None
        self._pending = None

    def _result(
        self,
        status: TranscriptionStatus,
        *,
        text: str | None = None,
        end_ns: int | None = None,
        error: str | None = None,
        timestamps: tuple[int, ...] = (),
    ) -> AudioTranscriptionResult:
        return AudioTranscriptionResult(
            text=text,
            start_ns=self._started_ns,
            end_ns=end_ns,
            status=status,
            model_id=self._model_id,
            language="pt",
            error=error,
            source_sample_rate=self._sample_rate,
            chunk_timestamps_ns=timestamps,
        )

    def _on_audio(self, indata, frames, _time_info, status) -> None:
        received_ns = self._clock_ns()
        with self._lock:
            if not self._recording:
                return
            if status:
                self._capture_issue = str(status)
            chunk = np.asarray(indata, dtype=np.float32)
            if chunk.shape != (frames, 1) or not np.all(np.isfinite(chunk)):
                self._capture_issue = "Bloco de áudio mono inválido."
                return
            self._chunks.append((received_ns, chunk[:, 0].copy()))

    def start(self, *, device=None, requested_samplerate=None) -> None:
        """Abre uma captura mono somente após chamada explícita do operador."""
        with self._lock:
            if self._closed or self._recording:
                raise RuntimeError("Sessão de áudio fechada ou já em captura.")
            if self._pending is not None and not self._pending.done():
                raise RuntimeError("A transcrição anterior ainda está em andamento.")
            self._started_ns = None
            self._sample_rate = None
            self._chunks = []
            self._capture_issue = None
            self._recording = True
        stream = None
        try:
            stream = self._stream_factory(self._on_audio, device, requested_samplerate)
            sample_rate = float(stream.samplerate)
            if not isfinite(sample_rate) or sample_rate <= 0:
                raise ValueError("Taxa real do dispositivo inválida.")
            self._started_ns = self._clock_ns()
            stream.start()
            with self._lock:
                self._sample_rate = sample_rate
                self._stream = stream
        except Exception as error:
            with self._lock:
                self._recording = False
            if stream is not None:
                stream.close()
            raise AudioCaptureError(
                self._result(
                    TranscriptionStatus.CAPTURE_FAILED,
                    end_ns=self._clock_ns(),
                    error=f"Não foi possível iniciar o microfone: {error}",
                )
            ) from error

    def _load_model_once(self):
        with self._model_lock:
            if self._model is not None:
                return self._model
            if self._model_loader is not None:
                model = self._model_loader(self.model_path)
            else:
                path = self.model_path.resolve(strict=True)
                if not path.is_file():
                    raise ValueError("O checkpoint Whisper local não é um arquivo.")
                import whisper

                model = whisper.load_model(str(path))
                self._model_id = f"whisper-local:sha256:{_sha256(path)}"
            self._model = model
            return model

    def _transcribe(
        self, audio: np.ndarray, end_ns: int, timestamps: tuple[int, ...]
    ) -> AudioTranscriptionResult:
        try:
            prepared = prepare_whisper_audio(audio, self._sample_rate)
            model = self._load_model_once()
            raw = model.transcribe(
                prepared, language="pt", fp16=False, task="transcribe"
            )
            text = raw["text"].strip()
            if not text:
                return self._result(
                    TranscriptionStatus.NO_SPEECH,
                    end_ns=end_ns,
                    timestamps=timestamps,
                )
            return self._result(
                TranscriptionStatus.AVAILABLE,
                text=text,
                end_ns=end_ns,
                timestamps=timestamps,
            )
        except Exception as error:
            return self._result(
                TranscriptionStatus.TRANSCRIPTION_FAILED,
                end_ns=end_ns,
                error=f"Falha na transcrição local: {error}",
                timestamps=timestamps,
            )

    @staticmethod
    def _completed(result: AudioTranscriptionResult) -> Future:
        future = Future()
        future.set_result(result)
        return future

    def stop_async(self) -> Future:
        """Libera o microfone antes de iniciar a transcrição em outra thread."""
        with self._lock:
            if not self._recording or self._stream is None:
                raise RuntimeError("Não há captura de áudio ativa.")
            self._recording = False
            stream = self._stream
            self._stream = None
        release_error = None
        try:
            stream.stop()
        except Exception as error:
            release_error = str(error)
        finally:
            try:
                stream.close()
            except Exception as error:
                release_error = str(error)
        end_ns = self._clock_ns()
        with self._lock:
            chunks = tuple(self._chunks)
            issue = self._capture_issue
        timestamps = tuple(timestamp for timestamp, _ in chunks)
        if release_error or issue:
            return self._completed(
                self._result(
                    TranscriptionStatus.CAPTURE_FAILED,
                    end_ns=end_ns,
                    error=release_error or issue,
                    timestamps=timestamps,
                )
            )
        if not chunks:
            return self._completed(
                self._result(TranscriptionStatus.NO_SPEECH, end_ns=end_ns)
            )
        audio = np.concatenate([chunk for _, chunk in chunks])
        if not np.any(audio):
            return self._completed(
                self._result(
                    TranscriptionStatus.NO_SPEECH,
                    end_ns=end_ns,
                    timestamps=timestamps,
                )
            )
        self._pending = self._executor.submit(
            self._transcribe, audio, end_ns, timestamps
        )
        return self._pending

    def close(self) -> None:
        """Interrompe a captura ativa e libera os recursos da sessão."""
        with self._lock:
            stream = self._stream
            self._stream = None
            self._recording = False
            self._closed = True
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
        self._executor.shutdown(wait=False, cancel_futures=False)

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.close()
