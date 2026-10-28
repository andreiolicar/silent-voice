"""Seleção nested R3.3 somente em desenvolvimento, sob protocolo R3.1.1."""

import json
import math
import subprocess
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import Sequence

import numpy as np

from silent_voice.rejection.hybrid_rejection_nested_loso import (
    _fit_positive,
    build_nested_session_plan,
    preflight_real_nested_loso,
)
from silent_voice.rejection.rejection_3_diagnostics import (
    FORBIDDEN_SOURCES,
    R2_REFERENCE_PATH,
    R2_REFERENCE_SHA256,
    _guard_development_paths,
    _predict_query,
    build_class_references,
    build_development_diagnostics,
    build_query_record,
    diagnostic_fold_definitions,
)
from silent_voice.rejection.rejection_3_scores import (
    CANDIDATE_IDS,
    candidate_accepts,
    threshold_candidates,
)
from silent_voice.rejection.rejection_protocol import (
    NEGATIVE_CATEGORIES,
    NEGATIVE_DEVELOPMENT_SESSIONS,
)
from silent_voice.vision.hybrid_features import raw_current_dtw_distance
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


PROTOCOL_PATH = Path("docs/cycles/rejection_3_protocol.json")
PROTOCOL_SHA256 = "1a7d178c5ea9fd5e8376622db260828561efaf3cfa3afb0734d58d076c35ebf7"
DIAGNOSTICS_PATH = Path(
    "data/processed/evaluation/rejection_3_development_score_diagnostics.json"
)
DIAGNOSTICS_SHA256 = "c9e100ad4a1f9f34f2f100ba89b71a54c757aa6f3bf502da8600adb7c897344b"
OUTPUT_PATH = Path(
    "data/processed/evaluation/rejection_3_nested_candidate_evaluation.json"
)
SCORE_FIELDS = {
    CANDIDATE_IDS[0]: ("cos_pred",),
    CANDIDATE_IDS[1]: ("robust_z_cosine",),
    CANDIDATE_IDS[2]: ("cosine_gap",),
    CANDIDATE_IDS[3]: ("cosine_gap", "logit_margin"),
    CANDIDATE_IDS[4]: ("robust_z_cosine", "cosine_gap", "logit_margin"),
}
THRESHOLD_CRITERIA = [
    "larger balanced harmonic score",
    "smaller KWA count",
    "larger KCA count",
    "smaller UFA count",
    "larger min(KCAR, URR)",
    "stricter thresholds; E: higher z, then gap, then margin",
]
GLOBAL_CRITERIA = [
    "larger global pooled balanced score",
    "smaller global KWA",
    "larger global KCA",
    "smaller global UFA",
    "larger worst-fold balanced score",
    "smaller fold-to-fold balanced range",
    "simplicity order",
]
STRICTNESS_ORDER = {
    CANDIDATE_IDS[3]: ["gap_threshold", "margin_threshold"],
    CANDIDATE_IDS[4]: ["z_threshold", "gap_threshold", "margin_threshold"],
}


def validate_protocol_contract(protocol: dict) -> None:
    """Falha se a revisão normativa ou alguma ordem congelada divergir."""
    if (
        protocol.get("protocol_version") != "R3.1.1"
        or tuple(item["id"] for item in protocol["candidates"]) != CANDIDATE_IDS
        or protocol.get("simplicity_order") != list(CANDIDATE_IDS)
        or protocol.get("threshold_strictness_order") != STRICTNESS_ORDER
        or protocol.get("threshold_tie_break") != THRESHOLD_CRITERIA
        or protocol.get("global_candidate_tie_break") != GLOBAL_CRITERIA
        or protocol.get("threshold_candidates", {}).get("one_dimensional")
        != ["-inf", "each unique observed INNER calibration score", "+inf"]
        or len(protocol.get("outer_folds", ())) != 3
    ):
        raise ValueError("Protocolo R3.1.1, candidatos ou strictness divergentes.")


def validate_fold_plan(folds: tuple, protocol: dict) -> list[dict]:
    """Confere sessões, contagens e separação dos dois passes internos."""
    validate_protocol_contract(protocol)
    definitions = diagnostic_fold_definitions(folds)
    for fold, definition, expected in zip(
        folds, definitions, protocol["outer_folds"], strict=True
    ):
        if (
            fold.validation_session_id != expected["validation_positive"]
            or fold.negative_validation_session_id != expected["validation_negative"]
            or sorted(expected["train_positive"]) != definition["reference_sessions"]
            or len(fold.inner_passes) != 2
        ):
            raise ValueError("Plano outer/inner divergiu do protocolo R3.1.1.")
        outer_ids = set(definition["validation_sample_ids"])
        inner_definitions = []
        for inner in fold.inner_passes:
            train_ids = {row.sample_id for row in inner.known_train}
            calibration_ids = {
                row.sample_id
                for row in (*inner.known_calibration, *inner.unknown_calibration)
            }
            negative_session = NEGATIVE_DEVELOPMENT_SESSIONS[
                SESSION_IDS.index(inner.calibration_session_id)
            ]
            if (
                inner.train_session_id not in expected["train_positive"]
                or inner.calibration_session_id not in expected["train_positive"]
                or inner.train_session_id == inner.calibration_session_id
                or len(inner.known_train) != 18
                or len(inner.known_calibration) != 18
                or len(inner.unknown_calibration) != 18
                or any(
                    row.session_id != inner.train_session_id
                    for row in inner.known_train
                )
                or any(
                    row.session_id != inner.calibration_session_id
                    for row in inner.known_calibration
                )
                or any(
                    row.session_id != negative_session
                    for row in inner.unknown_calibration
                )
                or len(train_ids | calibration_ids) != 54
                or outer_ids & (train_ids | calibration_ids)
            ):
                raise ValueError(
                    "Calibração inner contém vazamento ou sessão inválida."
                )
            inner_definitions.append(
                {
                    "fit_session": inner.train_session_id,
                    "calibration_session": inner.calibration_session_id,
                    "negative_calibration_session": negative_session,
                    "fit_sample_ids": sorted(train_ids),
                    "calibration_sample_ids": sorted(calibration_ids),
                }
            )
        if {row["fit_session"] for row in inner_definitions} != set(
            expected["train_positive"]
        ):
            raise ValueError("Os dois passes internos devem trocar as sessões.")
        definition.update(
            {
                "outer_known_count": 18,
                "outer_unknown_count": 18,
                "inner_known_count": 36,
                "inner_unknown_count": 36,
                "inner_passes": inner_definitions,
            }
        )
    return definitions


def verify_outer_diagnostics(
    current: Sequence[dict], previous: Sequence[dict], reference: dict[str, int]
) -> dict:
    """Exige 51/54 previsões e os mesmos 108 scores externos da R3.2."""
    current_by_id = {row["sample_id"]: row for row in current}
    previous_by_id = {row["sample_id"]: row for row in previous}
    known = [row for row in current if row["sample_kind"] == "KNOWN"]
    if (
        len(current) != 108
        or len(previous) != 108
        or len(current_by_id) != 108
        or len(previous_by_id) != 108
        or current_by_id.keys() != previous_by_id.keys()
        or len(known) != 54
        or {row["sample_id"]: row["predicted_label_index"] for row in known}
        != reference
        or sum(row["positive_prediction_correct"] for row in known) != 51
    ):
        raise ValueError(
            "Predições positivas externas não reproduzem 51/54 por amostra."
        )
    stable_fields = (
        "session_id",
        "outer_fold",
        "sample_kind",
        "expected_label",
        "expected_label_index",
        "negative_category",
        "predicted_label",
        "predicted_label_index",
        "positive_prediction_correct",
    )
    score_fields = (
        "cos_pred",
        "cos_other_max",
        "cosine_gap",
        "logit_margin",
        "robust_z_cosine",
    )
    for sample_id, row in current_by_id.items():
        earlier = previous_by_id[sample_id]
        if any(row.get(field) != earlier.get(field) for field in stable_fields):
            raise ValueError("Predições externas divergiram da R3.2 por amostra.")
        if any(
            not math.isclose(row[field], earlier[field], rel_tol=0, abs_tol=1e-6)
            for field in score_fields
        ):
            raise ValueError("Scores externos divergiram da R3.2 por amostra.")
    return {"correct": 51, "total": 54, "sample_predictions_identical": True}


def _harmonic(kcar: float, urr: float) -> float:
    return 0.0 if kcar == 0.0 or urr == 0.0 else 2 * kcar * urr / (kcar + urr)


def calculate_metrics(rows: Sequence[dict], accepted: Sequence[bool]) -> dict:
    """Conta decisões KNOWN/UNKNOWN sem média de métricas por fold."""
    if len(rows) != len(accepted) or len({row["sample_id"] for row in rows}) != len(
        rows
    ):
        raise ValueError("Decisões devem parear queries únicas 1:1.")
    known = [
        (row, bool(decision))
        for row, decision in zip(rows, accepted, strict=True)
        if row["sample_kind"] == "KNOWN"
    ]
    unknown = [
        (row, bool(decision))
        for row, decision in zip(rows, accepted, strict=True)
        if row["sample_kind"] == "UNKNOWN"
    ]
    if len(known) + len(unknown) != len(rows) or not known or not unknown:
        raise ValueError("Métricas exigem KNOWN e UNKNOWN.")
    if any(row["positive_prediction_correct"] not in (True, False) for row, _ in known):
        raise ValueError("Correção closed-set KNOWN inválida.")
    closed_correct = sum(row["positive_prediction_correct"] for row, _ in known)
    kca = sum(
        row["positive_prediction_correct"] and decision for row, decision in known
    )
    kwa = sum(
        not row["positive_prediction_correct"] and decision for row, decision in known
    )
    kr = sum(not decision for _, decision in known)
    ur = sum(not decision for _, decision in unknown)
    ufa = sum(decision for _, decision in unknown)
    if kca + kwa + kr != len(known) or ur + ufa != len(unknown):
        raise ValueError("Identidades de métricas de rejection violadas.")
    kcar = kca / len(known)
    urr = ur / len(unknown)
    return {
        "known_count": len(known),
        "unknown_count": len(unknown),
        "closed_set_correct": closed_correct,
        "closed_set_wrong": len(known) - closed_correct,
        "KCA": kca,
        "KWA": kwa,
        "KR": kr,
        "KCAR": kcar,
        "coverage": (kca + kwa) / len(known),
        "accepted_known_accuracy": kca / (kca + kwa) if kca + kwa else None,
        "UR": ur,
        "UFA": ufa,
        "URR": urr,
        "balanced": _harmonic(kcar, urr),
    }


def threshold_rank(
    metrics: dict, thresholds: Sequence[float], candidate_id: str, protocol: dict
) -> tuple:
    """Aplica os seis critérios internos e a strictness explícita do JSON."""
    fields = SCORE_FIELDS[candidate_id]
    if len(thresholds) != len(fields):
        raise ValueError("Número de thresholds fora do candidato.")
    named = dict(zip(STRICTNESS_ORDER.get(candidate_id, ()), thresholds))
    strictness = (
        tuple(
            named[name] for name in protocol["threshold_strictness_order"][candidate_id]
        )
        if candidate_id in STRICTNESS_ORDER
        else tuple(thresholds)
    )
    return (
        metrics["balanced"],
        -metrics["KWA"],
        metrics["KCA"],
        -metrics["UFA"],
        min(metrics["KCAR"], metrics["URR"]),
        *strictness,
    )


def _score_values(row: dict) -> dict[str, float]:
    return {
        "cos_pred": row["cos_pred"],
        "robust_z": row["robust_z_cosine"],
        "gap": row["cosine_gap"],
        "margin": row["logit_margin"],
    }


def select_inner_threshold(
    candidate_id: str, rows: Sequence[dict], protocol: dict
) -> dict:
    """Examina o produto cartesiano exato com máscaras de bits equivalentes."""
    validate_protocol_contract(protocol)
    if candidate_id not in CANDIDATE_IDS:
        raise ValueError("Candidato fora do protocolo.")
    base = calculate_metrics(rows, (False,) * len(rows))
    grids = tuple(
        threshold_candidates(tuple(row[field] for row in rows))
        for field in SCORE_FIELDS[candidate_id]
    )
    masks = tuple(
        tuple(
            sum(1 << index for index, row in enumerate(rows) if row[field] >= threshold)
            for threshold in grid
        )
        for field, grid in zip(SCORE_FIELDS[candidate_id], grids, strict=True)
    )
    known_correct = sum(
        1 << index
        for index, row in enumerate(rows)
        if row["sample_kind"] == "KNOWN" and row["positive_prediction_correct"]
    )
    known_wrong = sum(
        1 << index
        for index, row in enumerate(rows)
        if row["sample_kind"] == "KNOWN" and not row["positive_prediction_correct"]
    )
    unknown = sum(
        1 << index for index, row in enumerate(rows) if row["sample_kind"] == "UNKNOWN"
    )
    best_key = None
    best_thresholds = None
    for indices in product(*(range(len(grid)) for grid in grids)):
        selected_masks = tuple(
            mask[index] for mask, index in zip(masks, indices, strict=True)
        )
        if candidate_id == CANDIDATE_IDS[3]:
            accepted_mask = selected_masks[0] & selected_masks[1]
        elif candidate_id == CANDIDATE_IDS[4]:
            accepted_mask = selected_masks[0] | (selected_masks[1] & selected_masks[2])
        else:
            accepted_mask = selected_masks[0]
        kca = (accepted_mask & known_correct).bit_count()
        kwa = (accepted_mask & known_wrong).bit_count()
        ufa = (accepted_mask & unknown).bit_count()
        kcar = kca / base["known_count"]
        urr = (base["unknown_count"] - ufa) / base["unknown_count"]
        counts = {
            "balanced": _harmonic(kcar, urr),
            "KWA": kwa,
            "KCA": kca,
            "UFA": ufa,
            "KCAR": kcar,
            "URR": urr,
        }
        thresholds = tuple(
            grid[index] for grid, index in zip(grids, indices, strict=True)
        )
        key = threshold_rank(counts, thresholds, candidate_id, protocol)
        if best_key is None or key > best_key:
            best_key = key
            best_thresholds = thresholds
    accepted = tuple(
        candidate_accepts(candidate_id, _score_values(row), best_thresholds)
        for row in rows
    )
    return {
        "thresholds": list(best_thresholds),
        "candidate_count": math.prod(len(grid) for grid in grids),
        "metrics": calculate_metrics(rows, accepted),
    }


def evaluate_candidates(fold_data: Sequence[dict], protocol: dict) -> dict:
    """Aplica thresholds internos aos respectivos outer folds, sem recalibrar."""
    validate_protocol_contract(protocol)
    if not fold_data:
        raise ValueError("Nenhum fold externo para avaliação.")
    reports = {}
    for candidate_id in CANDIDATE_IDS:
        folds = []
        all_rows = []
        all_decisions = []
        all_audit = []
        for item in fold_data:
            inner = tuple(item["inner"])
            outer = tuple(item["outer"])
            if {row["sample_id"] for row in inner} & {
                row["sample_id"] for row in outer
            }:
                raise ValueError("Outer validation vazou para a calibração inner.")
            selected = select_inner_threshold(candidate_id, inner, protocol)
            thresholds = tuple(selected["thresholds"])
            decisions = tuple(
                candidate_accepts(candidate_id, _score_values(row), thresholds)
                for row in outer
            )
            metrics = calculate_metrics(outer, decisions)
            audit = [
                {
                    "sample_id": row["sample_id"],
                    "outer_fold": item["outer_fold"],
                    "sample_kind": row["sample_kind"],
                    "session_id": row["session_id"],
                    "expected_label": row["expected_label"],
                    "negative_category": row["negative_category"],
                    "predicted_label": row["predicted_label"],
                    "positive_prediction_correct": row["positive_prediction_correct"],
                    "primitives": {
                        name: row[name]
                        for name in (
                            "cos_pred",
                            "robust_z_cosine",
                            "cosine_gap",
                            "logit_margin",
                        )
                    },
                    "selected_inner_thresholds": list(thresholds),
                    "decision": "ACCEPT" if decision else "REJECT",
                    "emitted_label": row["predicted_label"] if decision else None,
                }
                for row, decision in zip(outer, decisions, strict=True)
            ]
            folds.append(
                {
                    "outer_fold": item["outer_fold"],
                    "selected_inner_thresholds": list(thresholds),
                    "inner_candidate_count": selected["candidate_count"],
                    "inner_metrics": selected["metrics"],
                    "outer_metrics": metrics,
                    "per_query": audit,
                }
            )
            all_rows.extend(outer)
            all_decisions.extend(decisions)
            all_audit.extend(audit)
        balanced = [fold["outer_metrics"]["balanced"] for fold in folds]
        reports[candidate_id] = {
            "folds": folds,
            "global_metrics": calculate_metrics(all_rows, all_decisions),
            "worst_fold_balanced": min(balanced),
            "best_fold_balanced": max(balanced),
            "fold_balanced_range": max(balanced) - min(balanced),
            "per_query": all_audit,
        }
    return reports


def select_development_candidate(reports: dict, protocol: dict) -> dict:
    """Aplica o desempate global em contagens pooled; simplicidade por último."""
    validate_protocol_contract(protocol)
    if set(reports) != set(CANDIDATE_IDS):
        raise ValueError("São exigidos os cinco candidatos congelados.")

    def rank(candidate_id: str) -> tuple:
        report = reports[candidate_id]
        metrics = report["global_metrics"]
        return (
            metrics["balanced"],
            -metrics["KWA"],
            metrics["KCA"],
            -metrics["UFA"],
            report["worst_fold_balanced"],
            -report["fold_balanced_range"],
            -protocol["simplicity_order"].index(candidate_id),
        )

    ranking = sorted(CANDIDATE_IDS, key=rank, reverse=True)
    winner, runner_up = ranking[:2]
    decisive_index = next(
        index
        for index, (first, second) in enumerate(zip(rank(winner), rank(runner_up)))
        if first != second
    )
    return {
        "candidate_id": winner,
        "ranking": ranking,
        "criteria": list(protocol["global_candidate_tie_break"]),
        "decisive_criterion": protocol["global_candidate_tie_break"][decisive_index],
    }


def selected_breakdowns(report: dict) -> dict:
    """Expõe classes, categorias, sessões e erros sem alterar a seleção."""
    rows = report["per_query"]
    by_class = []
    for label in DEFAULT_VISUAL_LABELS:
        group = [
            row
            for row in rows
            if row["sample_kind"] == "KNOWN" and row["expected_label"] == label
        ]
        kca = sum(
            row["decision"] == "ACCEPT" and row["positive_prediction_correct"]
            for row in group
        )
        kwa = sum(
            row["decision"] == "ACCEPT" and not row["positive_prediction_correct"]
            for row in group
        )
        by_class.append(
            {
                "label": label,
                "total": len(group),
                "closed_set_correct": sum(
                    row["positive_prediction_correct"] for row in group
                ),
                "KCA": kca,
                "KWA": kwa,
                "KR": len(group) - kca - kwa,
                "correct_accept_rate": kca / len(group) if group else None,
            }
        )
    by_category = []
    for category in NEGATIVE_CATEGORIES:
        group = [
            row
            for row in rows
            if row["sample_kind"] == "UNKNOWN" and row["negative_category"] == category
        ]
        false_accepts = [row for row in group if row["decision"] == "ACCEPT"]
        by_category.append(
            {
                "category": category,
                "total": len(group),
                "rejected": len(group) - len(false_accepts),
                "false_accepted": len(false_accepts),
                "rejection_rate": (
                    (len(group) - len(false_accepts)) / len(group) if group else None
                ),
                "false_accept_predicted_labels": [
                    row["predicted_label"] for row in false_accepts
                ],
            }
        )
    return {
        "known_by_true_class": by_class,
        "unknown_by_category": by_category,
        "by_outer_session": [
            {"outer_fold": fold["outer_fold"], **fold["outer_metrics"]}
            for fold in report["folds"]
        ],
        "false_accepts": [
            row
            for row in rows
            if row["sample_kind"] == "UNKNOWN" and row["decision"] == "ACCEPT"
        ],
        "wrong_accepts": [
            row
            for row in rows
            if row["sample_kind"] == "KNOWN"
            and not row["positive_prediction_correct"]
            and row["decision"] == "ACCEPT"
        ],
        "correct_known_rejects": [
            row
            for row in rows
            if row["sample_kind"] == "KNOWN"
            and row["positive_prediction_correct"]
            and row["decision"] == "REJECT"
        ],
    }


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value):
            raise ValueError("Resultado contém NaN.")
        if math.isinf(value):
            return "+inf" if value > 0 else "-inf"
    return value


def canonical_result_bytes(report: dict) -> bytes:
    """Serializa thresholds infinitos de modo estável e sem NaN."""
    return (
        json.dumps(
            _json_safe(report),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _build_inner_calibration(
    fold: object, distance_fn
) -> tuple[tuple[dict, ...], list[dict]]:
    rows = []
    passes = []
    outer_ids = {
        row.sample_id for row in (*fold.known_validation, *fold.unknown_validation)
    }
    for inner in fold.inner_passes:
        calibration = (*inner.known_calibration, *inner.unknown_calibration)
        calibration_ids = frozenset(row.sample_id for row in calibration)
        train_ids = {row.sample_id for row in inner.known_train}
        if train_ids & (calibration_ids | outer_ids) or calibration_ids & outer_ids:
            raise ValueError("Query de calibração/validação entrou no fit interno.")
        fitted = _fit_positive(inner.known_train, distance_fn)
        references = build_class_references(
            inner.known_train, calibration_ids | outer_ids
        )
        if not np.allclose(
            np.stack(
                [references[label]["centroid"] for label in DEFAULT_VISUAL_LABELS]
            ),
            fitted[1],
            rtol=0.0,
            atol=1e-7,
        ):
            raise ValueError("Centroides internos divergem do fit positivo congelado.")
        score_fold = SimpleNamespace(
            validation_session_id=inner.calibration_session_id,
            negative_validation_session_id=NEGATIVE_DEVELOPMENT_SESSIONS[
                SESSION_IDS.index(inner.calibration_session_id)
            ],
            known_train=inner.known_train,
        )
        pass_rows = []
        for query in calibration:
            index, logits = _predict_query(
                query, inner.known_train, fitted[0], distance_fn
            )
            kind = (
                "KNOWN"
                if query.session_id == inner.calibration_session_id
                else "UNKNOWN"
            )
            pass_rows.append(
                build_query_record(
                    query, kind, int(index), logits, references, score_fold
                )
            )
        rows.extend(pass_rows)
        passes.append(
            {
                "fit_session": inner.train_session_id,
                "calibration_session": inner.calibration_session_id,
                "reference_sample_ids": sorted(train_ids),
                "calibration_sample_ids": [row["sample_id"] for row in pass_rows],
                "raw_scores": pass_rows,
            }
        )
    if (
        len(rows) != 72
        or len({row["sample_id"] for row in rows}) != 72
        or sum(row["sample_kind"] == "KNOWN" for row in rows) != 36
    ):
        raise ValueError("Pool interno exige 36 KNOWN e 36 UNKNOWN únicos.")
    return tuple(rows), passes


def _assert_historical_score_parity(
    outer: Sequence[dict], inner: Sequence[dict], historical: dict
) -> None:
    """Descarta divergência de score A antes de qualquer seleção de candidato."""
    for fold in historical["folds"]:
        validation = fold["validation_session_id"]
        for row in fold["outer_validation_raw_scores"]:
            match = next(
                (item for item in outer if item["sample_id"] == row["sample_id"]), None
            )
            if (
                match is None
                or match["outer_fold"] != validation
                or not math.isclose(
                    match["cos_pred"], row["clip_class_cosine"], rel_tol=0, abs_tol=1e-6
                )
            ):
                raise ValueError("Score externo A divergiu da referência 6.8B.")
        inner_fold = next(item for item in inner if item["outer_fold"] == validation)
        inner_by_id = {row["sample_id"]: row for row in inner_fold["rows"]}
        for old_pass in fold["inner_passes"]:
            for row in old_pass["raw_scores"]:
                current = inner_by_id.get(row["sample_id"])
                if current is None or not math.isclose(
                    current["cos_pred"],
                    row["clip_class_cosine"],
                    rel_tol=0,
                    abs_tol=1e-6,
                ):
                    raise ValueError("Score interno A divergiu da referência 6.8B.")


def _historical_comparison(
    candidate_a: dict, outer_by_fold: Sequence[dict], historical: dict
) -> dict:
    """Classifica diferença histórica somente após validar replay da 6.8B."""
    r2_folds = historical["policies"]["CLIP_CLASS_COSINE"]["folds"]
    replay_rows = []
    replay_decisions = []
    thresholds_changed = False
    for item, old_fold, new_fold in zip(
        outer_by_fold, r2_folds, candidate_a["folds"], strict=True
    ):
        if item["outer_fold"] != old_fold["validation_session_id"]:
            raise ValueError("Folds históricos A fora da ordem de development.")
        threshold = old_fold["thresholds"][0]
        thresholds_changed |= new_fold["selected_inner_thresholds"][0] != threshold
        replay_rows.extend(item["outer"])
        replay_decisions.extend(
            candidate_accepts(CANDIDATE_IDS[0], _score_values(row), (threshold,))
            for row in item["outer"]
        )
    replay = calculate_metrics(replay_rows, replay_decisions)
    historical_counts = {"KCA": 49, "KWA": 1, "KR": 4, "UR": 46, "UFA": 8}
    if any(replay[key] != value for key, value in historical_counts.items()):
        raise ValueError(
            "Replay A da referência 6.8B divergiu: possível implementação."
        )
    actual = candidate_a["global_metrics"]
    same = all(actual[key] == value for key, value in historical_counts.items())
    if not same and not thresholds_changed:
        raise ValueError("A divergiu da 6.8B sem mudança de threshold: implementação.")
    return {
        "historical_task": "6.8B",
        "historical_counts": historical_counts,
        "historical_balanced": historical["policies"]["CLIP_CLASS_COSINE"][
            "global_metrics"
        ]["rejection_balanced_score"],
        "candidate_a_counts": {key: actual[key] for key in historical_counts},
        "candidate_a_balanced": actual["balanced"],
        "score_parity": True,
        "r2_threshold_replay_counts_identical": True,
        "thresholds_differ": thresholds_changed,
        "difference_classification": "NONE" if same else "PRE_REGISTERED_TIE_BREAK",
        "comparison_use": "DESCRIPTIVE_ONLY_NOT_FOR_SELECTION",
    }


def run_real_nested_selection(repository_root: Path) -> tuple[dict, str]:
    """Executa uma única comparação development após o commit pré-experimento."""
    root = Path(repository_root).resolve()
    output = root / OUTPUT_PATH
    if output.exists():
        raise FileExistsError("Resultado R3.3 já existe; reexecução proibida.")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError("Worktree versionável deve estar limpo antes da R3.3 real.")
    if sha256_file(root / PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise ValueError("SHA-256 do protocolo R3.1.1 divergiu.")
    if sha256_file(root / DIAGNOSTICS_PATH) != DIAGNOSTICS_SHA256:
        raise ValueError("SHA-256 do diagnóstico R3.2 divergiu.")
    protocol = json.loads((root / PROTOCOL_PATH).read_bytes())
    validate_protocol_contract(protocol)
    diagnostic = json.loads((root / DIAGNOSTICS_PATH).read_bytes())
    if diagnostic["state"] != "REJECTION_3_DEVELOPMENT_DIAGNOSTICS_COMPLETE":
        raise ValueError("Estado R3.2 não está concluído.")
    if sha256_file(root / R2_REFERENCE_PATH) != R2_REFERENCE_SHA256:
        raise ValueError("SHA-256 histórico 6.8B divergiu.")
    historical = json.loads((root / R2_REFERENCE_PATH).read_bytes())
    _guard_development_paths(root)
    preflight = preflight_real_nested_loso(root)
    folds = build_nested_session_plan(preflight["positives"], preflight["negatives"])
    definitions = validate_fold_plan(folds, protocol)
    outer_diagnostics = build_development_diagnostics(
        preflight["positives"],
        preflight["negatives"],
        preflight["reference_predictions"],
    )
    reproduction = verify_outer_diagnostics(
        outer_diagnostics["per_query"],
        diagnostic["per_query"],
        preflight["reference_predictions"],
    )
    cache = {}

    def cached_distance(first, second):
        key = tuple(sorted((first.sample_id, second.sample_id)))
        if key not in cache:
            cache[key] = float(raw_current_dtw_distance(first, second))
        return cache[key]

    inner_data = []
    fold_data = []
    for fold in folds:
        inner_rows, passes = _build_inner_calibration(fold, cached_distance)
        outer_rows = tuple(
            row
            for row in outer_diagnostics["per_query"]
            if row["outer_fold"] == fold.validation_session_id
        )
        if len(outer_rows) != 36:
            raise ValueError("Outer fold não possui 18 KNOWN + 18 UNKNOWN.")
        inner_data.append(
            {
                "outer_fold": fold.validation_session_id,
                "rows": inner_rows,
                "passes": passes,
            }
        )
        fold_data.append(
            {
                "outer_fold": fold.validation_session_id,
                "inner": inner_rows,
                "outer": outer_rows,
            }
        )
    _assert_historical_score_parity(
        outer_diagnostics["per_query"], inner_data, historical
    )
    reports = evaluate_candidates(fold_data, protocol)
    selection = select_development_candidate(reports, protocol)
    selected = selection["candidate_id"]
    historical_comparison = _historical_comparison(
        reports[CANDIDATE_IDS[0]], fold_data, historical
    )
    if any(len(report["per_query"]) != 108 for report in reports.values()):
        raise ValueError("Cada candidato deve ter 108 decisões externas.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    result = {
        "format_version": 1,
        "state": "REJECTION_3_DEVELOPMENT_SELECTED",
        "protocol_version": "R3.1.1",
        "protocol_sha256": PROTOCOL_SHA256,
        "diagnostics_sha256": DIAGNOSTICS_SHA256,
        "code_commit": commit,
        "worktree_clean_before_evaluation": True,
        "allowed_sources": protocol["allowed_data"],
        "forbidden_source_guards": list(FORBIDDEN_SOURCES),
        "outer_fold_definitions": definitions,
        "inner_calibration_by_fold": inner_data,
        "positive_reproduction": reproduction,
        "candidate_ids": list(CANDIDATE_IDS),
        "candidates": reports,
        "selection": selection,
        "development_preferred": selected,
        "selected_breakdowns": selected_breakdowns(reports[selected]),
        "r2_historical_comparison": historical_comparison,
        "source_hashes": preflight["source_hashes"],
        "final_threshold_calibrated": False,
        "heldouts_opened": False,
        "heldout_result_json_loaded": False,
        "comparison_run_count": 1,
    }
    if (
        sha256_file(root / PROTOCOL_PATH) != PROTOCOL_SHA256
        or sha256_file(root / DIAGNOSTICS_PATH) != DIAGNOSTICS_SHA256
    ):
        raise ValueError("Proveniência mudou durante a avaliação R3.3.")
    serialized = canonical_result_bytes(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(serialized)
    return result, sha256_file(output)
