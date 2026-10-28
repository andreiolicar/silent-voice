"""Diagnóstico leakage-safe de scores primitivos R3 somente em development."""

import json
import math
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Callable, Sequence

import numpy as np

from silent_voice.rejection.hybrid_rejection_nested_loso import (
    PROCESSED_SOURCE_ROOT,
    RAW_SOURCE_ROOT,
    _fit_positive,
    build_nested_session_plan,
    preflight_real_nested_loso,
)
from silent_voice.rejection.rejection_3_scores import (
    ROBUST_SCALE_EPS,
    assert_development_source_path,
    cosine_gap,
    logit_margin,
    robust_class_statistics,
    robust_z_cosine,
)
from silent_voice.rejection.rejection_protocol import (
    NEGATIVE_CATEGORIES,
    NEGATIVE_DEVELOPMENT_SESSIONS,
)
from silent_voice.vision.hybrid_features import (
    class_minimum_dtw_distances,
    equal_energy_fusion,
    normalized_reciprocal_evidence,
    raw_current_dtw_distance,
    select_authorized_visual_paths,
)
from silent_voice.vision.hybrid_linear_probe import predict_hybrid_linear
from silent_voice.vision.hybrid_loso import DATASET_RELATIVE_PATH
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.rejection_visual_features import (
    select_authorized_negative_paths,
)
from silent_voice.vision.swinlip_frozen_probe import l2_normalize
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


PROTOCOL_PATH = Path("docs/cycles/rejection_3_protocol.json")
PROTOCOL_SHA256 = "c2dfb35181e42a5209339ec6ec9c9f88caf3a049903b329a59e928387aa54dce"
OUTPUT_PATH = Path(
    "data/processed/evaluation/rejection_3_development_score_diagnostics.json"
)
R2_REFERENCE_PATH = Path(
    "data/processed/evaluation/cycle_06_rejection_2_nested_loso.json"
)
R2_REFERENCE_SHA256 = "54f487336f1ca1ef452576b883312af867f18c6f44fabcd61aeaa396083d0d3e"
SCORE_NAMES = ("cos_pred", "robust_z_cosine", "cosine_gap", "logit_margin")
FORBIDDEN_SOURCES = (
    "sessao_04",
    "rejeicao_heldout_01",
    "cycle_06_heldout_session_01",
    "cycle_06_heldout_session_02",
)


def diagnostic_fold_definitions(folds: tuple) -> list[dict]:
    """Registra o plano externo e impede qualquer sobreposição de IDs."""
    if len(folds) != 3:
        raise ValueError("São exigidos exatamente três folds externos.")
    definitions = []
    for index, fold in enumerate(folds):
        if (
            fold.validation_session_id != SESSION_IDS[index]
            or fold.negative_validation_session_id
            != NEGATIVE_DEVELOPMENT_SESSIONS[index]
            or len(fold.known_train) != 36
            or len(fold.known_validation) != 18
            or len(fold.unknown_validation) != 18
        ):
            raise ValueError("Fold externo fora do protocolo R3.1.")
        training_ids = [row.sample_id for row in fold.known_train]
        validation_ids = [
            row.sample_id for row in (*fold.known_validation, *fold.unknown_validation)
        ]
        if len(set(training_ids + validation_ids)) != 72:
            raise ValueError("IDs de treino e validação externa se sobrepõem.")
        reference_sessions = sorted({row.session_id for row in fold.known_train})
        if (
            len(reference_sessions) != 2
            or fold.validation_session_id in reference_sessions
        ):
            raise ValueError("Referências positivas contêm validação externa.")
        definitions.append(
            {
                "outer_fold": fold.validation_session_id,
                "validation_positive_session": fold.validation_session_id,
                "validation_negative_session": fold.negative_validation_session_id,
                "reference_sessions": reference_sessions,
                "reference_sample_ids": training_ids,
                "validation_sample_ids": validation_ids,
                "validation_known_count": 18,
                "validation_unknown_count": 18,
            }
        )
    return definitions


def build_class_references(train: tuple, validation_ids: frozenset[str]) -> dict:
    """Centroides de treino e scores próprios com self-exclusion exata."""
    ids = [row.sample_id for row in train]
    if not ids or len(set(ids)) != len(ids) or set(ids) & validation_ids:
        raise ValueError("A validação não pode entrar em centroides ou estatísticas.")
    references = {}
    for label_index, label in enumerate(DEFAULT_VISUAL_LABELS):
        rows = [
            row
            for row in train
            if row.label == label and row.label_index == label_index
        ]
        if not rows:
            continue
        if len(rows) < 2:
            raise ValueError("Self-exclusion exige duas referências por classe.")
        normalized = l2_normalize(
            np.stack([np.asarray(row.clip_embedding) for row in rows])
        )
        centroid = l2_normalize(normalized.mean(axis=0))
        own_scores = []
        for index in range(len(rows)):
            others = np.delete(normalized, index, axis=0)
            excluded_centroid = l2_normalize(others.mean(axis=0))
            own_scores.append(float(np.dot(normalized[index], excluded_centroid)))
        center, raw_scale = robust_class_statistics(own_scores)
        mad = float(median(abs(score - center) for score in own_scores))
        if not math.isclose(raw_scale, 1.4826 * mad, abs_tol=1e-12):
            raise ValueError("MAD da referência não reproduz a escala robusta.")
        references[label] = {
            "centroid": centroid,
            "median": center,
            "mad": mad,
            "robust_scale": max(raw_scale, ROBUST_SCALE_EPS),
            "self_excluded_scores": tuple(own_scores),
            "reference_sample_ids": tuple(row.sample_id for row in rows),
        }
    if {row.label for row in train} != set(references):
        raise ValueError("Labels de treino fora da ordem congelada.")
    return references


def build_query_record(
    query: object,
    sample_kind: str,
    predicted_index: int,
    logits: Sequence[float],
    references: dict,
    fold: object,
) -> dict:
    """Calcula apenas os quatro scores pré-registrados, sem decisão."""
    if set(references) != set(DEFAULT_VISUAL_LABELS):
        raise ValueError("São exigidas seis referências de classe.")
    if sample_kind == "KNOWN":
        if query.session_id != fold.validation_session_id:
            raise ValueError("Query KNOWN fora da validação externa.")
        expected_label = query.label
        expected_index = query.label_index
        category = None
    elif sample_kind == "UNKNOWN":
        if query.session_id != fold.negative_validation_session_id:
            raise ValueError("Query UNKNOWN fora da validação externa.")
        expected_label = None
        expected_index = None
        category = query.negative_category
    else:
        raise ValueError("Tipo de query fora do protocolo.")
    reference_ids = {row.sample_id for row in fold.known_train}
    if query.sample_id in reference_ids:
        raise ValueError("Query de validação pertence ao treino.")
    values = np.asarray(logits, dtype=np.float64)
    if (
        values.shape != (6,)
        or not np.isfinite(values).all()
        or predicted_index not in range(6)
        or int(np.argmax(values)) != predicted_index
    ):
        raise ValueError("Logits ou classe prevista inválidos.")
    normalized_clip = l2_normalize(np.asarray(query.clip_embedding))
    cosines = tuple(
        float(np.dot(normalized_clip, references[label]["centroid"]))
        for label in DEFAULT_VISUAL_LABELS
    )
    gap = cosine_gap(cosines, predicted_index)
    cos_pred = cosines[predicted_index]
    cos_other_max = max(
        value for index, value in enumerate(cosines) if index != predicted_index
    )
    predicted_label = DEFAULT_VISUAL_LABELS[predicted_index]
    reference = references[predicted_label]
    return {
        "sample_id": query.sample_id,
        "session_id": query.session_id,
        "sample_kind": sample_kind,
        "expected_label": expected_label,
        "expected_label_index": expected_index,
        "negative_category": category,
        "predicted_label": predicted_label,
        "predicted_label_index": int(predicted_index),
        "positive_prediction_correct": (
            bool(predicted_index == expected_index) if sample_kind == "KNOWN" else None
        ),
        "logits": values.tolist(),
        "cos_pred": cos_pred,
        "cos_other_max": cos_other_max,
        "cosine_gap": gap,
        "logit_margin": logit_margin(values),
        "predicted_class_median": float(reference["median"]),
        "predicted_class_MAD": float(reference["mad"]),
        "predicted_class_robust_scale": float(reference["robust_scale"]),
        "robust_z_cosine": robust_z_cosine(
            cos_pred, reference["median"], reference["robust_scale"]
        ),
        "outer_fold": fold.validation_session_id,
        "reference_sessions": sorted({row.session_id for row in fold.known_train}),
    }


def score_summary(values: Sequence[float]) -> dict:
    """Resumo determinístico com quantis lineares, inclusive grupo vazio."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or not np.isfinite(array).all():
        raise ValueError("Resumo exige scores finitos em vetor 1D.")
    if array.size == 0:
        return {
            key: 0 if key == "n" else None
            for key in ("n", "min", "p25", "median", "mean", "p75", "max")
        }
    p25, center, p75 = np.quantile(array, (0.25, 0.5, 0.75), method="linear")
    return {
        "n": int(array.size),
        "min": float(array.min()),
        "p25": float(p25),
        "median": float(center),
        "mean": float(array.mean()),
        "p75": float(p75),
        "max": float(array.max()),
    }


def _score_summaries(rows: Sequence[dict]) -> dict:
    return {name: score_summary([row[name] for row in rows]) for name in SCORE_NAMES}


def summarize_diagnostics(records: Sequence[dict]) -> dict:
    """Agrega sem converter scores em thresholds ou decisões."""
    rows = tuple(records)
    if len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("sample_id duplicado no diagnóstico.")
    known = tuple(row for row in rows if row["sample_kind"] == "KNOWN")
    unknown = tuple(row for row in rows if row["sample_kind"] == "UNKNOWN")
    correct = tuple(row for row in known if row["positive_prediction_correct"])
    wrong = tuple(row for row in known if not row["positive_prediction_correct"])
    global_groups = {
        "known": known,
        "known_correct": correct,
        "known_wrong": wrong,
        "unknown": unknown,
    }
    by_true = {
        label: tuple(row for row in known if row["expected_label"] == label)
        for label in DEFAULT_VISUAL_LABELS
    }
    by_predicted = {
        label: tuple(row for row in known if row["predicted_label"] == label)
        for label in DEFAULT_VISUAL_LABELS
    }
    by_session = {
        **{
            session: tuple(row for row in known if row["session_id"] == session)
            for session in SESSION_IDS
        },
        **{
            session: tuple(row for row in unknown if row["session_id"] == session)
            for session in NEGATIVE_DEVELOPMENT_SESSIONS
        },
    }
    by_category = {
        category: tuple(row for row in unknown if row["negative_category"] == category)
        for category in NEGATIVE_CATEGORIES
    }
    session_shift = {}
    class_shift = {}
    for name in SCORE_NAMES:
        per_session = {
            session: score_summary(
                [row[name] for row in correct if row["session_id"] == session]
            )
            for session in SESSION_IDS
        }
        per_class = {
            label: score_summary(
                [row[name] for row in correct if row["expected_label"] == label]
            )
            for label in DEFAULT_VISUAL_LABELS
        }
        session_medians = [item["median"] for item in per_session.values()]
        class_medians = [item["median"] for item in per_class.values()]
        if any(value is None for value in (*session_medians, *class_medians)):
            raise ValueError(
                "Diagnóstico de variação exige KNOWN corretos em cada grupo."
            )
        session_shift[name] = {
            "per_session": {
                key: {metric: values[metric] for metric in ("p25", "median", "p75")}
                for key, values in per_session.items()
            },
            "range": float(max(session_medians) - min(session_medians)),
        }
        class_shift[name] = {
            "per_class": {key: values["median"] for key, values in per_class.items()},
            "range": float(max(class_medians) - min(class_medians)),
        }
    return {
        "global": {
            name: _score_summaries(group) for name, group in global_groups.items()
        },
        "known_by_true_class": {
            name: _score_summaries(group) for name, group in by_true.items()
        },
        "known_by_predicted_class": {
            name: _score_summaries(group) for name, group in by_predicted.items()
        },
        "by_session": {
            name: _score_summaries(group) for name, group in by_session.items()
        },
        "unknown_by_category": {
            name: _score_summaries(group) for name, group in by_category.items()
        },
        "session_median_ranges": session_shift,
        "class_median_ranges": class_shift,
    }


def verify_positive_reproduction(
    known_records: Sequence[dict], reference_predictions: dict[str, int]
) -> dict:
    """Exige 51/54 e previsão exata por amostra antes dos scores R3."""
    rows = tuple(known_records)
    observed = {row["sample_id"]: row["predicted_label_index"] for row in rows}
    correct = sum(
        row["expected_label_index"] == row["predicted_label_index"] for row in rows
    )
    if (
        len(rows) != 54
        or len(observed) != 54
        or observed != reference_predictions
        or correct != 51
    ):
        raise ValueError("Reconhecedor positivo não reproduziu 51/54 por amostra.")
    return {"correct": 51, "total": 54, "sample_predictions_identical": True}


def canonical_diagnostic_bytes(report: dict) -> bytes:
    """Serialização UTF-8/LF estável, sem NaN ou infinito."""
    return (
        json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _predict_query(query: object, train: tuple, model: object, distance_fn: Callable):
    if query.sample_id in {row.sample_id for row in train}:
        raise ValueError("Query de validação pertence ao fit positivo.")
    distances = class_minimum_dtw_distances(query, train, distance_fn)
    feature = equal_energy_fusion(
        query.clip_embedding,
        normalized_reciprocal_evidence(distances),
        1670,
    )
    return predict_hybrid_linear(model, feature)


def build_development_diagnostics(
    positives: tuple,
    negatives: tuple,
    reference_predictions: dict[str, int],
    distance_fn: Callable = raw_current_dtw_distance,
) -> dict:
    """Reproduz primeiro o positivo; só depois calcula primitives R3."""
    folds = build_nested_session_plan(positives, negatives)
    definitions = diagnostic_fold_definitions(folds)
    cache = {}

    def cached_distance(first: object, second: object) -> float:
        key = tuple(sorted((first.sample_id, second.sample_id)))
        if key not in cache:
            cache[key] = float(distance_fn(first, second))
        return cache[key]

    fitted_folds = []
    positive_predictions = []
    for fold in folds:
        fitted = _fit_positive(fold.known_train, cached_distance)
        predictions = {}
        for query in fold.known_validation:
            index, logits = _predict_query(
                query, fold.known_train, fitted[0], cached_distance
            )
            predictions[query.sample_id] = (int(index), tuple(logits))
            positive_predictions.append(
                {
                    "sample_id": query.sample_id,
                    "expected_label_index": query.label_index,
                    "predicted_label_index": int(index),
                }
            )
        fitted_folds.append((fold, fitted, predictions))
    reproduction = verify_positive_reproduction(
        positive_predictions, reference_predictions
    )

    records = []
    fold_references = []
    for fold, fitted, predictions in fitted_folds:
        validation_ids = frozenset(
            row.sample_id for row in (*fold.known_validation, *fold.unknown_validation)
        )
        references = build_class_references(fold.known_train, validation_ids)
        if not np.allclose(
            np.stack(
                [references[label]["centroid"] for label in DEFAULT_VISUAL_LABELS]
            ),
            fitted[1],
            rtol=0.0,
            atol=1e-7,
        ):
            raise ValueError("Centroides R3 divergem do fit positivo congelado.")
        fold_references.append(
            {
                "outer_fold": fold.validation_session_id,
                "class_statistics": {
                    label: {
                        "median": float(reference["median"]),
                        "mad": float(reference["mad"]),
                        "robust_scale": float(reference["robust_scale"]),
                        "reference_sample_ids": list(reference["reference_sample_ids"]),
                        "self_excluded_scores": list(reference["self_excluded_scores"]),
                    }
                    for label, reference in references.items()
                },
            }
        )
        for query in fold.known_validation:
            index, logits = predictions[query.sample_id]
            records.append(
                build_query_record(query, "KNOWN", index, logits, references, fold)
            )
        for query in fold.unknown_validation:
            index, logits = _predict_query(
                query, fold.known_train, fitted[0], cached_distance
            )
            records.append(
                build_query_record(
                    query, "UNKNOWN", int(index), logits, references, fold
                )
            )
    if (
        len(records) != 108
        or len({row["sample_id"] for row in records}) != 108
        or Counter(row["sample_kind"] for row in records)
        != Counter({"KNOWN": 54, "UNKNOWN": 54})
    ):
        raise ValueError("Diagnóstico exige 108 queries externas únicas.")
    summaries = summarize_diagnostics(records)
    return {
        "format_version": 1,
        "state": "REJECTION_3_DEVELOPMENT_DIAGNOSTICS_COMPLETE",
        "protocol_sha256": PROTOCOL_SHA256,
        "allowed_sources": {
            "positives": list(SESSION_IDS),
            "negatives": list(NEGATIVE_DEVELOPMENT_SESSIONS),
        },
        "forbidden_sources": list(FORBIDDEN_SOURCES),
        "outer_folds": definitions,
        "class_references_by_fold": fold_references,
        "positive_reproduction": reproduction,
        "per_query": records,
        "summaries": summaries,
        "quantile_method": "linear",
        "query_count": 108,
        "no_threshold_selection": True,
        "no_candidate_selection": True,
        "threshold_selected": False,
        "candidate_selected": False,
        "heldouts_opened": False,
        "heldout_result_json_loaded": False,
        "dtw_unique_pair_count": len(cache),
    }


def _guard_development_paths(root: Path) -> None:
    """Filtra metadados de caminhos antes de abrir qualquer fonte de dados."""
    visual_root = root / DATASET_RELATIVE_PATH
    selected_positive = select_authorized_visual_paths(
        tuple(visual_root.rglob("*.npz"))
    )
    selected_negative = select_authorized_negative_paths(
        root / PROCESSED_SOURCE_ROOT, root / RAW_SOURCE_ROOT
    )
    for path in selected_positive:
        assert_development_source_path(path, "KNOWN")
    for _, npz_path, mp4_path in selected_negative:
        assert_development_source_path(npz_path, "UNKNOWN")
        assert_development_source_path(mp4_path, "UNKNOWN")


def _reference_from_rejection_2(root: Path) -> dict[str, int]:
    path = root / R2_REFERENCE_PATH
    if sha256_file(path) != R2_REFERENCE_SHA256:
        raise ValueError("SHA-256 da referência development 6.8B divergiu.")
    report = json.loads(path.read_text(encoding="utf-8"))
    known_rows = [
        row
        for fold in report["folds"]
        for row in fold["outer_validation_raw_scores"]
        if row["sample_kind"] == "KNOWN"
    ]
    reference = {row["sample_id"]: row["predicted_label_index"] for row in known_rows}
    if len(known_rows) != 54 or len(reference) != 54:
        raise ValueError("Referência development 6.8B incompleta.")
    return reference


def run_real_development_diagnostics(repository_root: Path) -> tuple[dict, str]:
    """Executa somente development e persiste resultado canônico uma vez."""
    root = Path(repository_root).resolve()
    protocol = root / PROTOCOL_PATH
    if sha256_file(protocol) != PROTOCOL_SHA256:
        raise ValueError("SHA-256 do protocolo R3.1 divergiu; execução interrompida.")
    output = root / OUTPUT_PATH
    if output.exists():
        raise FileExistsError("Diagnóstico R3.2 já existe; não sobrescrever.")
    _guard_development_paths(root)
    reference_r2 = _reference_from_rejection_2(root)
    preflight = preflight_real_nested_loso(root)
    if reference_r2 != preflight["reference_predictions"]:
        raise ValueError("Referências positivas 6.6 e 6.8B divergem por amostra.")
    report = build_development_diagnostics(
        preflight["positives"], preflight["negatives"], reference_r2
    )
    report["source_hashes"] = preflight["source_hashes"]
    report["reference_rejection_2_sha256"] = R2_REFERENCE_SHA256
    report["positive_embedding_hashes"] = preflight["positive_embedding_hashes"]
    report["negative_embedding_hashes"] = preflight["negative_embedding_hashes"]
    if sha256_file(protocol) != PROTOCOL_SHA256:
        raise ValueError("Protocolo R3.1 mudou durante o diagnóstico.")
    serialized = canonical_diagnostic_bytes(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(serialized)
    return report, sha256_file(output)
