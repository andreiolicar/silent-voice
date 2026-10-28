"""Métricas de decisão open-set derivadas de contagens de amostras."""

from collections import Counter

from silent_voice.rejection.rejection_protocol import NEGATIVE_CATEGORIES


def calculate_rejection_metrics(
    observations: tuple[dict, ...], accepted: tuple[bool, ...]
) -> dict:
    if not observations or len(observations) != len(accepted):
        raise ValueError("Observações e decisões devem ser não vazias e pareadas.")
    if any(type(decision) is not bool for decision in accepted):
        raise ValueError("Cada decisão deve ser booleana.")

    counts = Counter()
    negative_counts = Counter()
    negative_rejects = Counter()
    fallback_unknown = Counter()
    closed_set_correct = 0
    fallback_known = 0
    for observation, is_accepted in zip(observations, accepted, strict=True):
        kind = observation["sample_kind"]
        if kind == "KNOWN":
            counts["known_count"] += 1
            correct = observation["predicted_label"] == observation["expected_label"]
            closed_set_correct += int(correct)
            fallback_known += int(observation.get("segmentation_fallback", False))
            if not is_accepted:
                counts["KNOWN_REJECT"] += 1
            elif correct:
                counts["KNOWN_CORRECT_ACCEPT"] += 1
            else:
                counts["KNOWN_WRONG_ACCEPT"] += 1
        elif kind == "UNKNOWN":
            category = observation["negative_category"]
            if category not in NEGATIVE_CATEGORIES:
                raise ValueError(f"Categoria negativa desconhecida: {category}")
            counts["unknown_count"] += 1
            negative_counts[category] += 1
            fallback_unknown[category] += int(
                observation.get("segmentation_fallback", False)
            )
            if is_accepted:
                counts["UNKNOWN_FALSE_ACCEPT"] += 1
            else:
                counts["UNKNOWN_REJECT"] += 1
                negative_rejects[category] += 1
        else:
            raise ValueError(f"sample_kind inválido: {kind}")

    known_count = counts["known_count"]
    unknown_count = counts["unknown_count"]
    known_accept_count = counts["KNOWN_CORRECT_ACCEPT"] + counts["KNOWN_WRONG_ACCEPT"]
    kcar = counts["KNOWN_CORRECT_ACCEPT"] / known_count if known_count else 0.0
    urr = counts["UNKNOWN_REJECT"] / unknown_count if unknown_count else 0.0
    balanced = 2 * kcar * urr / (kcar + urr) if kcar > 0 and urr > 0 else 0.0
    return {
        "known_count": known_count,
        "unknown_count": unknown_count,
        "KNOWN_CORRECT_ACCEPT": counts["KNOWN_CORRECT_ACCEPT"],
        "KNOWN_WRONG_ACCEPT": counts["KNOWN_WRONG_ACCEPT"],
        "KNOWN_REJECT": counts["KNOWN_REJECT"],
        "UNKNOWN_REJECT": counts["UNKNOWN_REJECT"],
        "UNKNOWN_FALSE_ACCEPT": counts["UNKNOWN_FALSE_ACCEPT"],
        "known_correct_accept_rate": kcar,
        "known_wrong_accept_rate": (
            counts["KNOWN_WRONG_ACCEPT"] / known_count if known_count else 0.0
        ),
        "known_reject_rate": (
            counts["KNOWN_REJECT"] / known_count if known_count else 0.0
        ),
        "known_coverage": known_accept_count / known_count if known_count else 0.0,
        "accepted_known_accuracy": (
            counts["KNOWN_CORRECT_ACCEPT"] / known_accept_count
            if known_accept_count
            else 0.0
        ),
        "known_closed_set_accuracy": (
            closed_set_correct / known_count if known_count else 0.0
        ),
        "unknown_rejection_rate": urr,
        "unknown_false_accept_rate": (
            counts["UNKNOWN_FALSE_ACCEPT"] / unknown_count if unknown_count else 0.0
        ),
        "rejection_balanced_score": balanced,
        "unknown_count_by_category": {
            category: negative_counts[category] for category in NEGATIVE_CATEGORIES
        },
        "unknown_rejection_rate_by_category": {
            category: (
                negative_rejects[category] / negative_counts[category]
                if negative_counts[category]
                else 0.0
            )
            for category in NEGATIVE_CATEGORIES
        },
        "segmentation_fallback_known_count": fallback_known,
        "segmentation_fallback_unknown_count": sum(fallback_unknown.values()),
        "segmentation_fallback_unknown_by_category": {
            category: fallback_unknown[category] for category in NEGATIVE_CATEGORIES
        },
    }
