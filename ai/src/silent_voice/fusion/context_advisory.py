"""Anotação contextual C3 sem alterar a decisão visual R4."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
import math

from silent_voice.audio.context_interpreter import ContextResult, ContextStatus
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


@dataclass(frozen=True, slots=True)
class TemporalReference:
    """Comparação autorizada apenas com origem monotônica comum explícita."""

    visual_decision_ns: int | None
    max_context_age_ns: int
    shared_monotonic_origin: bool = False


@dataclass(frozen=True, slots=True)
class VisualTechnicalFailure:
    """Falha anterior ao resultado R4; não representa REJECT."""

    reason: str
    provenance: dict[str, Any] | None = None
    capture_timing: dict[str, Any] | None = None


def _valid_ns(value: object) -> bool:
    return type(value) is int and value >= 0


def _temporal_state(context: ContextResult, reference: TemporalReference) -> dict:
    decision = reference.visual_decision_ns
    start = context.capture_start_ns
    end = context.capture_end_ns
    received = context.transcription_received_ns
    produced = context.context_produced_ns
    if not reference.shared_monotonic_origin:
        return {"status": "UNKNOWN", "reason": "monotonic_origin_not_shared"}
    if not all(
        _valid_ns(value) for value in (decision, start, end, received, produced)
    ):
        return {"status": "UNKNOWN", "reason": "timestamp_missing_or_invalid"}
    if not start <= end <= received <= produced:
        return {"status": "UNKNOWN", "reason": "timestamp_order_invalid"}
    if produced > decision:
        return {"status": "UNKNOWN", "reason": "context_after_visual_decision"}
    capture_age = decision - end
    production_age = decision - produced
    status = "STALE" if capture_age > reference.max_context_age_ns else "CURRENT"
    return {
        "status": status,
        "reason": "capture_age_exceeded" if status == "STALE" else None,
        "capture_age_ns": capture_age,
        "production_age_ns": production_age,
        "max_context_age_ns": reference.max_context_age_ns,
    }


def _validate_visual(visual: dict) -> None:
    if not isinstance(visual, dict):
        raise ValueError("Resultado visual R4 inválido.")
    decision = visual.get("decision")
    label = visual.get("predicted_label")
    emitted = visual.get("emitted_label")
    if (
        decision not in ("ACCEPT", "REJECT")
        or label not in DEFAULT_VISUAL_LABELS
        or emitted != (label if decision == "ACCEPT" else None)
        or type(visual.get("score")) not in (int, float)
        or type(visual.get("threshold")) not in (int, float)
        or not math.isfinite(visual["score"])
        or not math.isfinite(visual["threshold"])
    ):
        raise ValueError("Resultado visual diverge do contrato R4.")


def _validate_context(context: ContextResult | None) -> None:
    if context is None:
        return
    if not isinstance(context, ContextResult) or not isinstance(
        context.status, ContextStatus
    ):
        raise ValueError("Resultado contextual C2 inválido.")
    words = context.relevant_known_words
    if (
        not isinstance(words, tuple)
        or len(words) != len(set(words))
        or any(word not in DEFAULT_VISUAL_LABELS for word in words)
    ):
        raise ValueError("Palavras fora do vocabulário fechado C2.")
    if context.status is not ContextStatus.AVAILABLE and words:
        raise ValueError("Estado contextual indisponível não pode sugerir palavras.")


def integrate_advisory(
    visual: dict | VisualTechnicalFailure,
    context: ContextResult | None,
    reference: TemporalReference,
) -> dict:
    """Combina contratos existentes sem executar modelo, rede ou E/S."""
    if (
        not isinstance(reference, TemporalReference)
        or type(reference.max_context_age_ns) is not int
        or reference.max_context_age_ns <= 0
        or type(reference.shared_monotonic_origin) is not bool
    ):
        raise ValueError("Referência temporal C3 inválida.")
    _validate_context(context)
    context_payload = deepcopy(context.to_dict()) if context is not None else None
    if isinstance(visual, VisualTechnicalFailure):
        if not isinstance(visual.reason, str) or not visual.reason.strip():
            raise ValueError("Falha técnica visual sem motivo.")
        visual_payload = {
            "reason": visual.reason,
            "provenance": deepcopy(visual.provenance),
            "capture_timing": deepcopy(visual.capture_timing),
        }
        return {
            "policy": "ADVISORY_ONLY",
            "visual_status": "TECHNICAL_FAILURE",
            "visual": visual_payload,
            "context": context_payload,
            "temporal": {"status": "NOT_CHECKED", "reason": "visual_technical_failure"},
            "relationship": "NOT_APPLICABLE",
            "decision": None,
            "word": None,
        }
    _validate_visual(visual)
    relationship = "NOT_APPLICABLE"
    temporal = {"status": "NOT_CHECKED", "reason": "no_usable_context"}
    if visual["decision"] == "ACCEPT":
        if context is None or context.status is not ContextStatus.AVAILABLE:
            relationship = "NO_CONTEXT"
        else:
            temporal = _temporal_state(context, reference)
            if temporal["status"] == "UNKNOWN":
                relationship = "TEMPORAL_UNKNOWN"
            elif temporal["status"] == "STALE":
                relationship = "STALE_CONTEXT"
            elif visual["emitted_label"] in context.relevant_known_words:
                relationship = "SUPPORTED"
            else:
                relationship = "NOT_SUGGESTED"
    return {
        "policy": "ADVISORY_ONLY",
        "visual_status": "PASS",
        "visual": deepcopy(visual),
        "context": context_payload,
        "temporal": temporal,
        "relationship": relationship,
        "decision": visual["decision"],
        "word": visual["emitted_label"],
    }
