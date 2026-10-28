"""Primitivas puras pré-registradas para o protocolo Rejection 3.0."""

import json
import math
import operator
from pathlib import Path
from statistics import median
from typing import Mapping, Sequence


ROBUST_SCALE_EPS = 1e-6
CANDIDATE_IDS = (
    "R2_GLOBAL_CLIP_COSINE",
    "R3_ROBUST_CLASS_Z_COSINE",
    "R3_COSINE_GAP",
    "R3_COSINE_GAP_AND_LOGIT_MARGIN",
    "R3_ROBUST_Z_OR_GAP_AND_MARGIN",
)
_SCORE_NAMES = ("cos_pred", "robust_z", "gap", "margin")
_THRESHOLD_COUNTS = dict(zip(CANDIDATE_IDS, (1, 1, 1, 2, 3)))
_POSITIVE_SESSIONS = frozenset(("sessao_01", "sessao_02", "sessao_03"))
_NEGATIVE_SESSIONS = frozenset(
    ("rejeicao_dev_01", "rejeicao_dev_02", "rejeicao_dev_03")
)
_CONSUMED_HELDOUTS = (
    "sessao_04",
    "rejeicao_heldout_01",
    "cycle_06_heldout_session_01",
    "cycle_06_heldout_session_02",
    "cycle_06_final_heldout_evaluation.json",
    "rejection_3_heldout",
    "r3_heldout_session_",
)


def _finite_values(values: Sequence[float], expected_count: int | None = None) -> tuple:
    try:
        converted = tuple(float(value) for value in values)
    except (TypeError, ValueError) as error:
        raise ValueError("Scores devem ser números finitos.") from error
    if expected_count is not None and len(converted) != expected_count:
        raise ValueError(f"São necessários exatamente {expected_count} scores.")
    if not converted or not all(math.isfinite(value) for value in converted):
        raise ValueError("Scores devem ser números finitos e não vazios.")
    return converted


def cosine_gap(cosines: Sequence[float], predicted_label_index: int) -> float:
    """Cosseno da classe prevista menos o maior cosseno de outra classe."""
    values = _finite_values(cosines, expected_count=6)
    try:
        index = operator.index(predicted_label_index)
    except TypeError as error:
        raise ValueError("Índice da classe prevista fora do vocabulário.") from error
    if not 0 <= index < 6:
        raise ValueError("Índice da classe prevista fora do vocabulário.")
    competitor = max(value for other, value in enumerate(values) if other != index)
    return values[index] - competitor


def logit_margin(logits: Sequence[float]) -> float:
    """Diferença entre os dois maiores logits da cabeça positiva."""
    values = sorted(_finite_values(logits, expected_count=6), reverse=True)
    return values[0] - values[1]


def robust_class_statistics(own_class_cosines: Sequence[float]) -> tuple[float, float]:
    """Mediana e 1,4826 × MAD de referências positivas só de treino."""
    values = _finite_values(own_class_cosines)
    center = float(median(values))
    mad = float(median(abs(value - center) for value in values))
    return center, 1.4826 * mad


def robust_z_cosine(cos_pred: float, class_median: float, class_scale: float) -> float:
    """Normaliza sem alterar o MAD bruto; o piso vale só no denominador."""
    score, center, scale = _finite_values((cos_pred, class_median, class_scale), 3)
    if scale < 0:
        raise ValueError("A escala robusta não pode ser negativa.")
    return (score - center) / max(scale, ROBUST_SCALE_EPS)


def threshold_candidates(inner_scores: Sequence[float]) -> tuple[float, ...]:
    """Limiares exatos da calibração interna, sem pontos médios."""
    values = _finite_values(inner_scores)
    return (-math.inf, *sorted(set(values)), math.inf)


def candidate_accepts(
    candidate_id: str, scores: Mapping[str, float], thresholds: Sequence[float]
) -> bool:
    """Aplica uma das cinco fórmulas; igualdade ao limiar aceita."""
    if candidate_id not in _THRESHOLD_COUNTS:
        raise ValueError("Candidato fora do protocolo Rejection 3.0.")
    if set(scores) != set(_SCORE_NAMES):
        raise ValueError("São exigidos os quatro scores pré-registrados.")
    values = dict(
        zip(
            _SCORE_NAMES,
            _finite_values(tuple(scores[name] for name in _SCORE_NAMES), 4),
        )
    )
    try:
        gates = tuple(float(value) for value in thresholds)
    except (TypeError, ValueError) as error:
        raise ValueError("Limiares inválidos.") from error
    if len(gates) != _THRESHOLD_COUNTS[candidate_id] or any(
        math.isnan(value) for value in gates
    ):
        raise ValueError("Quantidade de limiares inválida ou NaN.")
    if candidate_id == "R2_GLOBAL_CLIP_COSINE":
        return values["cos_pred"] >= gates[0]
    if candidate_id == "R3_ROBUST_CLASS_Z_COSINE":
        return values["robust_z"] >= gates[0]
    if candidate_id == "R3_COSINE_GAP":
        return values["gap"] >= gates[0]
    if candidate_id == "R3_COSINE_GAP_AND_LOGIT_MARGIN":
        return values["gap"] >= gates[0] and values["margin"] >= gates[1]
    return values["robust_z"] >= gates[0] or (
        values["gap"] >= gates[1] and values["margin"] >= gates[2]
    )


def assert_development_source_path(path: str | Path, sample_kind: str) -> None:
    """Bloqueia held-outs consumidos e exige sessão de desenvolvimento antes de I/O."""
    normalized = str(path).replace("\\", "/").casefold()
    parts = tuple(part for part in normalized.split("/") if part)
    if any(forbidden in normalized for forbidden in _CONSUMED_HELDOUTS):
        raise ValueError("Held-out consumido é proibido no Rejection 3.0.")
    if sample_kind == "KNOWN":
        allowed = _POSITIVE_SESSIONS
    elif sample_kind == "UNKNOWN":
        allowed = _NEGATIVE_SESSIONS
    else:
        raise ValueError("Tipo de amostra fora do protocolo.")
    filename = parts[-1] if parts else ""
    if not any(session in parts or f"_{session}_" in filename for session in allowed):
        raise ValueError("Fonte fora das sessões de desenvolvimento autorizadas.")


def canonical_protocol_bytes(protocol: dict) -> bytes:
    """Serializa o protocolo de forma estável para SHA-256 do arquivo."""
    return (
        json.dumps(
            protocol,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
