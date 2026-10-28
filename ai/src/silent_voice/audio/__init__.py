"""Áudio ambiental contextual local; sem decisão independente da intenção."""

from .contextual_audio import (
    AudioCaptureError,
    AudioTranscriptionResult,
    ContextualAudioSession,
    TranscriptionStatus,
    prepare_whisper_audio,
)

__all__ = [
    "AudioCaptureError",
    "AudioTranscriptionResult",
    "ContextualAudioSession",
    "TranscriptionStatus",
    "prepare_whisper_audio",
]
