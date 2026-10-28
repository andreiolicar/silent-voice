"""Scores e seleção pré-registrados para rejection do híbrido congelado."""

from itertools import product

import numpy as np

from silent_voice.rejection.rejection_metrics import calculate_rejection_metrics
from silent_voice.rejection.rejection_protocol import NEGATIVE_CATEGORIES
from silent_voice.vision.swinlip_frozen_probe import l2_normalize
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

POLICY_NAMES = (
    "MAX_SOFTMAX",
    "LOGIT_MARGIN",
    "CLIP_CLASS_COSINE",
    "HYBRID_CLASS_COSINE",
    "HYBRID_COSINE_AND_LOGIT_MARGIN",
)
SIMPLICITY_ORDER = (
    "LOGIT_MARGIN",
    "MAX_SOFTMAX",
    "CLIP_CLASS_COSINE",
    "HYBRID_CLASS_COSINE",
    "HYBRID_COSINE_AND_LOGIT_MARGIN",
)
SCORE_FIELD = {
    "MAX_SOFTMAX": "max_softmax",
    "LOGIT_MARGIN": "logit_margin",
    "CLIP_CLASS_COSINE": "clip_class_cosine",
    "HYBRID_CLASS_COSINE": "hybrid_class_cosine",
}


def class_centroids(
    train_samples: tuple, train_features: dict
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula centroides de clips/features somente do fit positivo recebido."""
    ids = {item.sample_id for item in train_samples}
    if (
        len(train_samples) not in (18, 36)
        or len(ids) != len(train_samples)
        or set(train_features) != ids
    ):
        raise ValueError("Centroides exigem apenas os positivos do fit.")
    clip_centroids = []
    hybrid_centroids = []
    for index, label in enumerate(DEFAULT_VISUAL_LABELS):
        rows = [
            item
            for item in train_samples
            if item.label_index == index and item.label == label
        ]
        if len(rows) != len(train_samples) // 6:
            raise ValueError("Classes de treino desbalanceadas para centroides.")
        clips = l2_normalize(np.stack([item.clip_embedding for item in rows]))
        hybrids = l2_normalize(
            np.stack([train_features[item.sample_id] for item in rows])
        )
        if clips.shape[1] != 1664 or hybrids.shape[1] != 1670:
            raise ValueError("Dimensões incompatíveis com o híbrido congelado.")
        clip_centroids.append(l2_normalize(clips.mean(axis=0)))
        hybrid_centroids.append(l2_normalize(hybrids.mean(axis=0)))
    return np.stack(clip_centroids), np.stack(hybrid_centroids)


def raw_rejection_scores(
    logits: np.ndarray,
    clip: np.ndarray,
    hybrid: np.ndarray,
    predicted_index: int,
    clip_centroids: np.ndarray,
    hybrid_centroids: np.ndarray,
) -> dict:
    """Calcula os quatro scores, sem calibrar ou decidir ACCEPT/REJECT."""
    values = np.asarray(logits, dtype=np.float64)
    if (
        values.shape != (6,)
        or not np.isfinite(values).all()
        or predicted_index not in range(6)
        or predicted_index != int(np.argmax(values))
        or clip_centroids.shape != (6, 1664)
        or hybrid_centroids.shape != (6, 1670)
    ):
        raise ValueError("Logits, índice ou centroides incompatíveis.")
    normalized_clip = l2_normalize(clip)
    normalized_hybrid = l2_normalize(hybrid)
    if normalized_clip.shape != (1664,) or normalized_hybrid.shape != (1670,):
        raise ValueError("Query com dimensão incompatível.")
    shifted = values - np.max(values)
    exp = np.exp(shifted)
    probabilities = exp / exp.sum()
    top = np.sort(values)[-2:]
    return {
        "softmax_probabilities": probabilities.tolist(),
        "max_softmax": float(probabilities.max()),
        "logit_margin": float(top[1] - top[0]),
        "clip_class_cosine": float(
            np.dot(normalized_clip, clip_centroids[predicted_index])
        ),
        "hybrid_class_cosine": float(
            np.dot(normalized_hybrid, hybrid_centroids[predicted_index])
        ),
    }


def threshold_candidates(
    observations: tuple[dict, ...], score_name: str
) -> tuple[float, ...]:
    score_name = SCORE_FIELD.get(score_name, score_name)
    if score_name not in SCORE_FIELD.values():
        raise ValueError("Score de threshold desconhecido.")
    if not observations:
        raise ValueError("Calibração vazia.")
    values = [float(row[score_name]) for row in observations]
    if not np.isfinite(values).all():
        raise ValueError("Scores de calibração não finitos.")
    return (-float("inf"), *sorted(set(values)), float("inf"))


def acceptance_decision(
    policy: str, observation: dict, thresholds: tuple[float, ...]
) -> bool:
    if policy == "HYBRID_COSINE_AND_LOGIT_MARGIN":
        if len(thresholds) != 2:
            raise ValueError("Política combinada exige dois thresholds.")
        return bool(
            observation["hybrid_class_cosine"] >= thresholds[0]
            and observation["logit_margin"] >= thresholds[1]
        )
    if policy not in SCORE_FIELD or len(thresholds) != 1:
        raise ValueError("Política ou threshold inválido.")
    return bool(observation[SCORE_FIELD[policy]] >= thresholds[0])


def calculate_detailed_metrics(
    observations: tuple[dict, ...], accepted: tuple[bool, ...]
) -> dict:
    """Reusa métricas do Cycle 5 e acrescenta classes/categorias explicitamente."""
    metrics = calculate_rejection_metrics(observations, accepted)
    known = []
    for label in DEFAULT_VISUAL_LABELS:
        rows = [
            (row, decision)
            for row, decision in zip(observations, accepted, strict=True)
            if row["sample_kind"] == "KNOWN" and row["expected_label"] == label
        ]
        known.append(
            {
                "label": label,
                "sample_count": len(rows),
                "correct_accept": sum(
                    decision and row["predicted_label"] == label
                    for row, decision in rows
                ),
                "wrong_accept": sum(
                    decision and row["predicted_label"] != label
                    for row, decision in rows
                ),
                "reject": sum(not decision for _, decision in rows),
                "closed_set_correct": sum(
                    row["predicted_label"] == label for row, _ in rows
                ),
            }
        )
    unknown = []
    for category in NEGATIVE_CATEGORIES:
        decisions = [
            decision
            for row, decision in zip(observations, accepted, strict=True)
            if row["sample_kind"] == "UNKNOWN" and row["negative_category"] == category
        ]
        rejected = sum(not decision for decision in decisions)
        unknown.append(
            {
                "category": category,
                "sample_count": len(decisions),
                "rejected": rejected,
                "false_accepted": sum(decisions),
                "rejection_rate": rejected / len(decisions) if decisions else 0.0,
            }
        )
    return {**metrics, "known_by_class": known, "unknown_by_category": unknown}


def select_calibrated_threshold(policy: str, observations: tuple[dict, ...]) -> dict:
    """Examina candidatos apenas do pool interno e aplica desempate estrito."""
    if policy not in POLICY_NAMES:
        raise ValueError("Política não pré-registrada.")
    if (
        not observations
        or not any(row["sample_kind"] == "KNOWN" for row in observations)
        or not any(row["sample_kind"] == "UNKNOWN" for row in observations)
    ):
        raise ValueError("Calibração exige KNOWN e UNKNOWN.")
    if policy == "HYBRID_COSINE_AND_LOGIT_MARGIN":
        candidates = product(
            threshold_candidates(observations, "hybrid_class_cosine"),
            threshold_candidates(observations, "logit_margin"),
        )
        candidate_count = len(
            threshold_candidates(observations, "hybrid_class_cosine")
        ) * len(threshold_candidates(observations, "logit_margin"))
    else:
        values = threshold_candidates(observations, SCORE_FIELD[policy])
        candidates = ((value,) for value in values)
        candidate_count = len(values)
    best = None
    best_key = None
    for thresholds in candidates:
        accepted = tuple(
            acceptance_decision(policy, row, thresholds) for row in observations
        )
        metrics = calculate_rejection_metrics(observations, accepted)
        key = (
            metrics["rejection_balanced_score"],
            -metrics["UNKNOWN_FALSE_ACCEPT"],
            -metrics["KNOWN_WRONG_ACCEPT"],
            metrics["KNOWN_CORRECT_ACCEPT"],
            *thresholds,
        )
        if best_key is None or key > best_key:
            best_key = key
            best = (thresholds, accepted)
    thresholds, accepted = best
    return {
        "thresholds": list(thresholds),
        "candidate_count": candidate_count,
        "metrics": calculate_detailed_metrics(observations, accepted),
    }


def select_development_policy(reports: dict) -> str:
    if set(reports) != set(POLICY_NAMES):
        raise ValueError("É obrigatório comparar as cinco políticas pré-registradas.")

    def rank(name: str) -> tuple:
        report = reports[name]
        metrics = report["global_metrics"]
        worst_fold = min(
            row["metrics"]["rejection_balanced_score"] for row in report["folds"]
        )
        return (
            metrics["rejection_balanced_score"],
            -metrics["UNKNOWN_FALSE_ACCEPT"],
            -metrics["KNOWN_WRONG_ACCEPT"],
            metrics["KNOWN_CORRECT_ACCEPT"],
            worst_fold,
            -SIMPLICITY_ORDER.index(name),
        )

    return max(POLICY_NAMES, key=rank)
