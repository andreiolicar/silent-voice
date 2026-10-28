"""Protocolo pré-captura congelado para rejeição visual no Cycle 5."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


PROTOCOL_STATUS = "REJECTION_PROTOCOL_DEFINED"
NEGATIVE_CATEGORIES = (
    "BOCA_PARADA",
    "SORRISO",
    "ABRE_FECHA",
    "MOV_CABECA",
    "MOV_BOCA_ALEATORIO",
    "FALA_FORA_VOCAB",
)
NEGATIVE_DEVELOPMENT_SESSIONS = (
    "rejeicao_dev_01",
    "rejeicao_dev_02",
    "rejeicao_dev_03",
)
CANDIDATE_POLICIES = (
    "PATH_DISTANCE",
    "CLASS_MARGIN",
    "PATH_DISTANCE_AND_MARGIN",
    "CLASS_SCALED_PATH_DISTANCE_AND_MARGIN",
)
DEVELOPMENT_OOV_PROMPTS = (
    ("rejeicao_dev_01", ("CASA", "COMIDA", "ESCOLA")),
    ("rejeicao_dev_02", ("TRABALHO", "HOJE", "FAMÍLIA")),
    ("rejeicao_dev_03", ("OBRIGADO", "LIVRO", "CARRO")),
)
HELDOUT_OOV_PROMPTS = ("TELEFONE", "JANELA", "SAPATO")
PROTOCOL_STATES = (
    "REJECTION_PROTOCOL_DEFINED",
    "REJECTION_DEV_CAPTURED",
    "REJECTION_CALIBRATED",
    "REJECTION_FROZEN_BEFORE_HELDOUT",
    "REJECTION_HELDOUT_CAPTURED_UNEVALUATED",
    "REJECTION_HELDOUT_EVALUATED",
)


@dataclass(frozen=True, slots=True)
class RejectionFold:
    validation_positive_session: str
    validation_negative_session: str
    training_positive_sessions: tuple[str, ...]
    training_negative_sessions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RejectionProtocol:
    format_version: int
    status: str
    primary_classifier: str
    known_labels: tuple[str, ...]
    negative_categories: tuple[str, ...]
    positive_development_sessions: tuple[str, ...]
    negative_development_sessions: tuple[str, ...]
    known_repetitions_per_label_per_session: int
    negative_repetitions_per_category_per_session: int
    positive_development_count: int
    negative_development_count: int
    total_development_count: int
    folds: tuple[RejectionFold, ...]
    development_oov_prompts: tuple[tuple[str, tuple[str, ...]], ...]
    candidate_policies: tuple[str, ...]
    heldout_session_id: str
    heldout_oov_prompts: tuple[str, ...]
    heldout_known_count: int
    heldout_unknown_count: int
    heldout_total_count: int
    negative_development_captured: bool


def build_rejection_protocol() -> RejectionProtocol:
    folds = tuple(
        RejectionFold(
            validation_positive_session=positive,
            validation_negative_session=negative,
            training_positive_sessions=tuple(
                item for item in SESSION_IDS if item != positive
            ),
            training_negative_sessions=tuple(
                item for item in NEGATIVE_DEVELOPMENT_SESSIONS if item != negative
            ),
        )
        for positive, negative in zip(
            SESSION_IDS, NEGATIVE_DEVELOPMENT_SESSIONS, strict=True
        )
    )
    return RejectionProtocol(
        format_version=1,
        status=PROTOCOL_STATUS,
        primary_classifier="DTW_LEGACY_RAW",
        known_labels=DEFAULT_VISUAL_LABELS,
        negative_categories=NEGATIVE_CATEGORIES,
        positive_development_sessions=SESSION_IDS,
        negative_development_sessions=NEGATIVE_DEVELOPMENT_SESSIONS,
        known_repetitions_per_label_per_session=3,
        negative_repetitions_per_category_per_session=3,
        positive_development_count=54,
        negative_development_count=54,
        total_development_count=108,
        folds=folds,
        development_oov_prompts=DEVELOPMENT_OOV_PROMPTS,
        candidate_policies=CANDIDATE_POLICIES,
        heldout_session_id="rejeicao_heldout_01",
        heldout_oov_prompts=HELDOUT_OOV_PROMPTS,
        heldout_known_count=18,
        heldout_unknown_count=18,
        heldout_total_count=36,
        negative_development_captured=False,
    )


def validate_rejection_protocol(protocol: RejectionProtocol) -> None:
    """Rejeita qualquer desvio do contrato pré-captura ou vazamento de sessão."""
    expected = build_rejection_protocol()
    if protocol.known_labels != DEFAULT_VISUAL_LABELS:
        raise ValueError("A ordem do vocabulário conhecido foi alterada.")
    if "sessao_04" in (
        protocol.positive_development_sessions + protocol.negative_development_sessions
    ):
        raise ValueError("sessao_04 é proibida como dado de tuning.")
    if protocol.positive_development_sessions != SESSION_IDS:
        raise ValueError("Sessões positivas de desenvolvimento inesperadas.")
    if protocol.negative_development_sessions != NEGATIVE_DEVELOPMENT_SESSIONS:
        raise ValueError("Sessões negativas de desenvolvimento inesperadas.")
    if protocol.negative_categories != NEGATIVE_CATEGORIES:
        raise ValueError("As categorias negativas devem seguir a lista congelada.")
    if protocol.candidate_policies != CANDIDATE_POLICIES:
        raise ValueError("As políticas candidatas devem seguir a lista congelada.")
    if protocol.negative_development_captured is not False:
        raise ValueError("A captura negativa ainda não ocorreu nesta task.")
    if (
        protocol.known_repetitions_per_label_per_session != 3
        or protocol.negative_repetitions_per_category_per_session != 3
        or protocol.positive_development_count != 54
        or protocol.negative_development_count != 54
        or protocol.total_development_count != 108
        or protocol.heldout_known_count != 18
        or protocol.heldout_unknown_count != 18
        or protocol.heldout_total_count != 36
    ):
        raise ValueError("A contagem planejada não corresponde ao protocolo.")
    if len(protocol.folds) != 3:
        raise ValueError("São necessários três folds LOSO pré-registrados.")
    for fold in protocol.folds:
        if (
            fold.validation_positive_session in fold.training_positive_sessions
            or fold.validation_negative_session in fold.training_negative_sessions
            or "sessao_04" in fold.training_positive_sessions
            or "sessao_04" in fold.training_negative_sessions
        ):
            raise ValueError("Vazamento de sessão no fold de rejection.")
    if protocol.folds != expected.folds:
        raise ValueError("O mapeamento dos folds LOSO foi alterado.")
    development_prompts = {
        prompt for _, prompts in protocol.development_oov_prompts for prompt in prompts
    }
    if development_prompts & set(protocol.heldout_oov_prompts):
        raise ValueError("OOV de desenvolvimento e held-out devem ser distintos.")
    if (
        protocol.development_oov_prompts != DEVELOPMENT_OOV_PROMPTS
        or protocol.heldout_oov_prompts != HELDOUT_OOV_PROMPTS
    ):
        raise ValueError("Os prompts OOV devem seguir a lista pré-registrada.")
    if protocol != expected:
        raise ValueError("O protocolo de rejection diverge do estado congelado.")


def build_rejection_protocol_manifest(protocol: RejectionProtocol) -> dict:
    """Representa somente decisões pré-captura; não contém scores medidos."""
    validate_rejection_protocol(protocol)
    return {
        "format_version": protocol.format_version,
        "protocol_status": protocol.status,
        "primary_classifier": protocol.primary_classifier,
        "classifier_contract": {
            "segmentation": "task_4_2_frozen",
            "features": "raw_shape_and_velocity",
            "distance": "classic_accumulated_dtw",
            "warping": "unrestricted",
            "neighbors": 1,
            "prediction_rule": "DTW_LEGACY_RAW_unchanged",
            "rejection_stage": "after_predicted_label",
            "accepted_output": "predicted_label",
            "rejected_output": None,
        },
        "known_labels": list(protocol.known_labels),
        "negative_categories": [
            {
                "name": name,
                "meaning": meaning,
                "system_label": "UNKNOWN",
            }
            for name, meaning in zip(
                protocol.negative_categories,
                (
                    "Rosto presente; boca em repouso; nenhuma palavra.",
                    "Sorriso natural e relaxamento; sem palavra.",
                    "Abre e fecha natural da boca; sem palavra conhecida.",
                    "Pequeno movimento natural da cabeça; rosto visível; sem palavra.",
                    "Movimentos arbitrários da boca; sem palavra conhecida.",
                    "Palavra real fora das seis palavras conhecidas.",
                ),
                strict=True,
            )
        ],
        "development_plan": {
            "positive_sessions": list(protocol.positive_development_sessions),
            "negative_sessions": list(protocol.negative_development_sessions),
            "known_repetitions_per_label_per_session": (
                protocol.known_repetitions_per_label_per_session
            ),
            "negative_repetitions_per_category_per_session": (
                protocol.negative_repetitions_per_category_per_session
            ),
            "positive_sample_count": protocol.positive_development_count,
            "negative_sample_count": protocol.negative_development_count,
            "total_sample_count": protocol.total_development_count,
        },
        "folds": [asdict(fold) for fold in protocol.folds],
        "development_oov_prompts": {
            session: list(prompts)
            for session, prompts in protocol.development_oov_prompts
        },
        "oov_prompt_metadata_rule": (
            "IDs internos usam ASCII; registrar o prompt original em metadados."
        ),
        "candidate_policies": [
            {
                "name": "PATH_DISTANCE",
                "signal": "best_match_total_cost / best_match_path_length",
                "acceptance_direction": "lower_is_more_similar",
            },
            {
                "name": "CLASS_MARGIN",
                "signal": "(d2 - d1) / max(d2, epsilon)",
                "acceptance_direction": "higher_is_more_separated",
            },
            {
                "name": "PATH_DISTANCE_AND_MARGIN",
                "signal": "path_distance_passes AND class_margin_passes",
                "acceptance_direction": "both_thresholds_required",
            },
            {
                "name": "CLASS_SCALED_PATH_DISTANCE_AND_MARGIN",
                "signal": "class_scaled_path_distance_passes AND class_margin_passes",
                "acceptance_direction": "both_thresholds_required",
                "class_scale": (
                    "median of same-class leave-one-out path distances "
                    "from positive training samples only"
                ),
            },
        ],
        "distance_diagnostics": {
            "class_distance_rule": "minimum accumulated DTW cost per class",
            "d1": "distance of the best class",
            "d2": "distance of the second-best class",
            "raw_accumulated_distance_policy_selectable": False,
            "segmentation_fallback": (
                "record as diagnostic; do not automatically reject"
            ),
        },
        "metrics": {
            "known_correct_accept_rate": {
                "formula": "KNOWN_CORRECT_ACCEPT / all_known"
            },
            "known_wrong_accept_rate": {"formula": "KNOWN_WRONG_ACCEPT / all_known"},
            "known_reject_rate": {"formula": "KNOWN_REJECT / all_known"},
            "known_coverage": {
                "formula": "(KNOWN_CORRECT_ACCEPT + KNOWN_WRONG_ACCEPT) / all_known"
            },
            "accepted_known_accuracy": {
                "formula": (
                    "KNOWN_CORRECT_ACCEPT / "
                    "(KNOWN_CORRECT_ACCEPT + KNOWN_WRONG_ACCEPT)"
                ),
                "zero_denominator": None,
            },
            "unknown_rejection_rate": {"formula": "UNKNOWN_REJECT / all_unknown"},
            "unknown_false_accept_rate": {
                "formula": "UNKNOWN_FALSE_ACCEPT / all_unknown"
            },
            "unknown_rejection_rate_by_category": {
                "formula": "UNKNOWN_REJECT_in_category / all_unknown_in_category"
            },
            "rejection_balanced_score": {
                "formula": (
                    "2 * KCAR * URR / (KCAR + URR) " "if KCAR > 0 and URR > 0 else 0"
                ),
                "is_conventional_accuracy": False,
            },
        },
        "selection": {
            "primary_metric": "rejection_balanced_score",
            "aggregation": "pooled validation counts across the three LOSO folds",
            "tie_breakers": [
                "unknown_false_accept_rate:ascending",
                "known_wrong_accept_rate:ascending",
                "known_correct_accept_rate:descending",
                "policy_simplicity:ascending",
            ],
            "policy_simplicity_order": list(protocol.candidate_policies),
            "threshold_calibration": (
                "training/calibration side of each fold only; never validation"
            ),
            "threshold_search_strategy": "deferred_to_later_task",
        },
        "heldout_plan": {
            "session_id": protocol.heldout_session_id,
            "known_labels": list(protocol.known_labels),
            "negative_categories": list(protocol.negative_categories),
            "repetitions_per_label": 3,
            "repetitions_per_negative_category": 3,
            "known_sample_count": protocol.heldout_known_count,
            "unknown_sample_count": protocol.heldout_unknown_count,
            "total_sample_count": protocol.heldout_total_count,
            "oov_prompts": list(protocol.heldout_oov_prompts),
            "one_shot": True,
            "capture_after_policy_threshold_pipeline_frozen": True,
        },
        "states": list(PROTOCOL_STATES),
        "forbidden_tuning_sessions": ["sessao_04"],
        "cycle_4_final_evaluation_forbidden_for_decisions": True,
        "negative_development_captured": protocol.negative_development_captured,
        "heldout_captured": False,
        "real_rejection_experiment_executed": False,
    }


def save_rejection_protocol_manifest(protocol: RejectionProtocol, path: Path) -> None:
    manifest = build_rejection_protocol_manifest(protocol)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
