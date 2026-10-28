"""Public runtime subset of the frozen personalization contract."""

LABELS = ("SIM", "NÃO", "AJUDA", "ÁGUA", "BANHEIRO", "PARAR")


FAMILIES = (
    "PERSONAL_REFERENCE_PROTOTYPES",
    "GLOBAL_PLUS_PERSONAL_RERANK",
    "PERSONAL_DTW_EVIDENCE",
    "LIGHTWEIGHT_PERSONAL_HEAD",
)


SHOT_REGIMES = (
    ("1SHOT", "ONE_SHOT_PER_CLASS", 1),
    ("2SHOT", "TWO_SHOT_PER_CLASS", 2),
    ("4SHOT", "FOUR_SHOT_PER_CLASS", 4),
)


GLOBAL_ID = "GLOBAL_UNPERSONALIZED_BASELINE"


CONFIG_IDS = (GLOBAL_ID,) + tuple(
    f"{family}__{shot}" for family in FAMILIES for shot, _, _ in SHOT_REGIMES
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_reject_output(opaque_query_id, config_id):
    _require(config_id in CONFIG_IDS, "Config ID")
    return {
        "query_id": opaque_query_id,
        "config_id": config_id,
        "decision": "REJECT",
        "predicted_label": None,
        "predicted_label_index": None,
        "score": None,
        "inference_performed": False,
        "reason": "INSUFFICIENT_VISUAL_EVIDENCE",
    }
