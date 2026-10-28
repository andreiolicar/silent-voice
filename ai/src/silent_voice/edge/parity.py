"""Métricas pré-registradas de paridade e ordem de candidatos Edge."""

import math

import numpy as np

FROZEN_THRESHOLD = 0.6401790380477905
FP32_MIN_COSINE = 0.9999
FP32_MAX_ABS_ERROR = 1e-4


def embedding_parity(reference: np.ndarray, edge: np.ndarray) -> dict:
    """Compara dois clips 1664-D sem modificar embeddings ou tolerâncias."""
    left = np.asarray(reference)
    right = np.asarray(edge)
    if left.shape != (1664,) or right.shape != (1664,):
        raise ValueError("Paridade exige dois clip embeddings de 1664-D.")
    finite = bool(np.isfinite(left).all() and np.isfinite(right).all())
    if not finite:
        return {
            "finite": False,
            "reference_norm": None,
            "edge_norm": None,
            "max_abs_error": None,
            "mean_abs_error": None,
            "rmse": None,
            "cosine_similarity": None,
        }
    left = left.astype(np.float64)
    right = right.astype(np.float64)
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("Clip embedding de norma zero invalida paridade.")
    difference = np.abs(left - right)
    return {
        "finite": True,
        "reference_norm": left_norm,
        "edge_norm": right_norm,
        "max_abs_error": float(difference.max()),
        "mean_abs_error": float(difference.mean()),
        "rmse": float(np.sqrt(np.mean(np.square(difference)))),
        "cosine_similarity": float(np.dot(left, right) / left_norm / right_norm),
    }


def compare_downstream(
    reference_label: str,
    edge_label: str,
    reference_score: float,
    edge_score: float,
) -> dict:
    """Usa o mesmo threshold FP32 congelado apenas para teste de paridade."""
    if not all(math.isfinite(value) for value in (reference_score, edge_score)):
        raise ValueError("Scores de rejection não finitos.")
    reference_decision = "ACCEPT" if reference_score >= FROZEN_THRESHOLD else "REJECT"
    edge_decision = "ACCEPT" if edge_score >= FROZEN_THRESHOLD else "REJECT"
    return {
        "reference_predicted_label": reference_label,
        "edge_predicted_label": edge_label,
        "labels_equal": reference_label == edge_label,
        "reference_rejection_score": reference_score,
        "edge_rejection_score": edge_score,
        "rejection_score_abs_diff": abs(reference_score - edge_score),
        "reference_decision": reference_decision,
        "edge_decision": edge_decision,
        "decisions_equal": reference_decision == edge_decision,
    }


def candidate_status(candidate_id: str, rows: list[dict]) -> str:
    """Classifica FP32 estritamente e compressão apenas por decisões."""
    if len(rows) != 108:
        raise ValueError("A paridade exige exatamente 108 amostras development.")
    if candidate_id == "ONNX_FP32":
        equivalent = all(
            row["finite"]
            and row["cosine_similarity"] >= FP32_MIN_COSINE
            and row["max_abs_error"] <= FP32_MAX_ABS_ERROR
            and row["labels_equal"]
            and row["decisions_equal"]
            for row in rows
        )
        return (
            "FP32_EDGE_NUMERICALLY_EQUIVALENT"
            if equivalent
            else "FP32_EDGE_NUMERICALLY_DIFFERENT"
        )
    if candidate_id not in ("ONNX_FP16", "ONNX_DYNAMIC_INT8"):
        raise ValueError("Candidate de compressão desconhecido.")
    return (
        "DECISION_IDENTICAL"
        if all(
            row["finite"] and row["labels_equal"] and row["decisions_equal"]
            for row in rows
        )
        else "DECISION_CHANGED"
    )


def aggregate_candidate(candidate_id: str, rows: list[dict]) -> dict:
    """Resume as 108 observações sem descartar erros ou divergências."""
    status = candidate_status(candidate_id, rows)
    finite = [row for row in rows if row["finite"]]
    return {
        "status": status,
        "sample_count": len(rows),
        "finite_count": len(finite),
        "min_embedding_cosine": (
            min(row["cosine_similarity"] for row in finite) if finite else None
        ),
        "max_abs_embedding_error": (
            max(row["max_abs_error"] for row in finite) if finite else None
        ),
        "mean_abs_embedding_error": (
            float(np.mean([row["mean_abs_error"] for row in finite]))
            if finite
            else None
        ),
        "max_rmse": max(row["rmse"] for row in finite) if finite else None,
        "label_agreement_count": sum(row["labels_equal"] for row in rows),
        "decision_agreement_count": sum(row["decisions_equal"] for row in rows),
        "max_rejection_score_abs_diff": (
            max(
                row["rejection_score_abs_diff"]
                for row in rows
                if row["rejection_score_abs_diff"] is not None
            )
            if finite
            else None
        ),
    }


def leading_technical_candidate(candidates: list[dict]) -> str | None:
    """Aplica a ordem pré-registrada, sem escolher runtime de deployment."""
    eligible = [
        row
        for row in candidates
        if row["load_success"]
        and row["inference_success"]
        and row["finite_count"] == 108
    ]
    if not eligible:
        return None
    selected = max(
        eligible,
        key=lambda row: (
            row["label_agreement_count"] == 108,
            row["decision_agreement_count"] == 108,
            -row["size_bytes"],
            -row["host_p95_ms"],
        ),
    )
    return selected["id"]
