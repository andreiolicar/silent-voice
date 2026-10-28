"""Calibração cross-fitted e congelamento da política de referência R3.4."""

import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np

from silent_voice.rejection.hybrid_rejection_final import (
    CENTROID_RELATIVE_PATH,
    CONFIG_FINAL_RELATIVE_PATH,
    build_final_clip_centroids,
    load_frozen_clip_rejection,
)
from silent_voice.rejection.rejection_3_diagnostics import FORBIDDEN_SOURCES
from silent_voice.rejection.rejection_3_nested_selection import (
    DIAGNOSTICS_PATH,
    DIAGNOSTICS_SHA256,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    calculate_metrics,
    canonical_result_bytes,
    selected_breakdowns,
    threshold_rank,
    validate_protocol_contract,
)
from silent_voice.rejection.rejection_3_scores import (
    CANDIDATE_IDS,
    threshold_candidates,
)
from silent_voice.rejection.rejection_protocol import NEGATIVE_CATEGORIES
from silent_voice.vision.hybrid_loso import preflight_hybrid_loso
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.positive_classifier_final import (
    CHECKPOINT_RELATIVE_PATH,
    CONFIG_RELATIVE_PATH,
    ROI_MANIFEST_RELATIVE_PATH,
    ROI_MANIFEST_SHA256,
    SWINLIP_CHECKPOINT_SHA256,
)
from silent_voice.vision.swinlip_embedding_dataset import (
    CHECKPOINT_RELATIVE_PATH as SWINLIP_CHECKPOINT_PATH,
    OUTPUT_MANIFEST_RELATIVE_PATH as EMBEDDING_MANIFEST_PATH,
)
from silent_voice.vision.swinlip_frozen_loso import EMBEDDING_MANIFEST_SHA256
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

R3_3_PATH = Path(
    "data/processed/evaluation/rejection_3_nested_candidate_evaluation.json"
)
R3_3_SHA256 = "4bbc13e495ac82ed9ea03f21943cdb1f0770efaf06f8523a0de08a5135d193bf"
CALIBRATION_PATH = Path(
    "data/processed/evaluation/rejection_3_final_development_calibration.json"
)
FREEZE_PATH = Path("docs/cycles/rejection_3_reference_freeze.json")
REFERENCE_CONFIG_SHA256 = (
    "c13b81c22a3c04972a15ce4ca3382eb9c30ef6156e32af1a7acb4fd4a524dff1"
)
CENTROID_SHA256 = "3fd4b54a7f092ce9b09f064b8076c76e71b1833e3eab3786b4295f07e023a87e"
POSITIVE_CHECKPOINT_SHA256 = (
    "33a0d1f1f564dc75f83ebc08fc2dca255840da60ca40a9c41fdd36d4ad0cc6a2"
)
POSITIVE_CONFIG_SHA256 = (
    "29b7df189ac8f3b5b01ce2b5b5b03870dd37b678ccb6f6f536e8ac9debaa7a1e"
)
CANDIDATE_ID = CANDIDATE_IDS[0]
METHOD = "POOLED_OUTER_CROSSFITTED_DEVELOPMENT"
FORBIDDEN_PATH_TOKENS = (
    *FORBIDDEN_SOURCES,
    "cycle_06_final_heldout_evaluation.json",
    "rejection_3_heldout",
    "r3_heldout_session_",
)


def guard_repository_path(repository_root: Path, relative_path: str | Path) -> Path:
    """Rejeita fontes proibidas e escapes antes de qualquer leitura."""
    root = Path(repository_root).resolve()
    relative = Path(relative_path)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or any(token in str(relative).lower() for token in FORBIDDEN_PATH_TOKENS)
    ):
        raise ValueError("Caminho fora das fontes development autorizadas.")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Caminho fora das fontes development autorizadas.")
    return resolved


def validate_cross_fitted_source(report: dict, protocol: dict) -> list[dict]:
    """Extrai somente os scores externos de A e prova a separação por sessão."""
    validate_protocol_contract(protocol)
    reproduction = report.get("positive_reproduction", {})
    if (
        report.get("state") != "REJECTION_3_DEVELOPMENT_SELECTED"
        or report.get("protocol_version") != "R3.1.1"
        or report.get("development_preferred") != CANDIDATE_ID
        or report.get("candidate_ids") != list(CANDIDATE_IDS)
        or reproduction
        != {"correct": 51, "total": 54, "sample_predictions_identical": True}
        or report.get("heldouts_opened") is not False
        or report.get("heldout_result_json_loaded") is not False
        or report.get("final_threshold_calibrated") is not False
    ):
        raise ValueError("R3.3 não autoriza a calibração final do candidato A.")
    candidate = report["candidates"][CANDIDATE_ID]
    reference = candidate["global_metrics"]
    if tuple(reference.get(name) for name in ("KCA", "KWA", "KR", "UR", "UFA")) != (
        49,
        1,
        4,
        46,
        8,
    ) or not math.isclose(reference["balanced"], 0.8787524366471735, abs_tol=1e-12):
        raise ValueError("Estimativa nested R3.3 divergente da seleção congelada.")
    source_rows = candidate["per_query"]
    if len(source_rows) != 108 or len({row["sample_id"] for row in source_rows}) != 108:
        raise ValueError("São exigidas 108 queries externas únicas.")
    definitions = report.get("outer_fold_definitions", ())
    if len(definitions) != 3:
        raise ValueError("Faltam definições dos três folds externos.")
    rows = []
    for index, session in enumerate(SESSION_IDS):
        negative_session = f"rejeicao_dev_0{index + 1}"
        definition = definitions[index]
        expected_references = sorted(set(SESSION_IDS) - {session})
        fold_rows = [row for row in source_rows if row.get("outer_fold") == session]
        known = [row for row in fold_rows if row.get("sample_kind") == "KNOWN"]
        unknown = [row for row in fold_rows if row.get("sample_kind") == "UNKNOWN"]
        validation_ids = [row["sample_id"] for row in fold_rows]
        reference_ids = definition.get("reference_sample_ids", ())
        expected_reference_ids = {
            row["sample_id"]
            for row in source_rows
            if row.get("sample_kind") == "KNOWN"
            and row.get("session_id") in expected_references
        }
        if (
            definition.get("validation_positive_session") != session
            or definition.get("validation_negative_session") != negative_session
            or definition.get("reference_sessions") != expected_references
            or len(known) != 18
            or len(unknown) != 18
            or len(reference_ids) != 36
            or set(reference_ids) != expected_reference_ids
            or set(reference_ids) & set(validation_ids)
            or len(definition.get("validation_sample_ids", ())) != 36
            or set(definition["validation_sample_ids"]) != set(validation_ids)
        ):
            raise ValueError("Proveniência cross-fitted do outer fold divergente.")
        for row in fold_rows:
            sample_id = row["sample_id"]
            if any(token in sample_id.lower() for token in FORBIDDEN_PATH_TOKENS):
                raise ValueError("Query de held-out proibida na R3.4.")
            kind = row["sample_kind"]
            predicted = row.get("predicted_label")
            score = row.get("primitives", {}).get("cos_pred")
            if (
                predicted not in DEFAULT_VISUAL_LABELS
                or not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not math.isfinite(score)
            ):
                raise ValueError("Rótulo ou cos_pred inválido na query externa.")
            if kind == "KNOWN":
                valid = (
                    row.get("session_id") == session
                    and row.get("expected_label") in DEFAULT_VISUAL_LABELS
                    and row.get("negative_category") is None
                    and type(row.get("positive_prediction_correct")) is bool
                    and row["positive_prediction_correct"]
                    == (predicted == row["expected_label"])
                )
            else:
                valid = (
                    kind == "UNKNOWN"
                    and row.get("session_id") == negative_session
                    and row.get("expected_label") is None
                    and row.get("negative_category") in NEGATIVE_CATEGORIES
                    and row.get("positive_prediction_correct") is None
                )
            if not valid:
                raise ValueError("Query fora do contrato de classe/sessão.")
            rows.append(
                {
                    "sample_id": sample_id,
                    "outer_fold": session,
                    "session_id": row["session_id"],
                    "sample_kind": kind,
                    "expected_label": row["expected_label"],
                    "negative_category": row["negative_category"],
                    "predicted_label": predicted,
                    "positive_prediction_correct": row["positive_prediction_correct"],
                    "cos_pred": score,
                }
            )
    if len(rows) != 108 or sum(row["sample_kind"] == "KNOWN" for row in rows) != 54:
        raise ValueError("Folds externos não cobrem 54 KNOWN e 54 UNKNOWN.")
    if (
        sum(
            row["positive_prediction_correct"]
            for row in rows
            if row["sample_kind"] == "KNOWN"
        )
        != 51
    ):
        raise ValueError("Reprodução positiva externa deixou de ser 51/54.")
    if Counter(
        row["expected_label"] for row in rows if row["sample_kind"] == "KNOWN"
    ) != Counter({label: 9 for label in DEFAULT_VISUAL_LABELS}) or Counter(
        row["negative_category"] for row in rows if row["sample_kind"] == "UNKNOWN"
    ) != Counter(
        {category: 9 for category in NEGATIVE_CATEGORIES}
    ):
        raise ValueError("Distribuição de classes ou categorias divergente.")
    return rows


def choose_final_threshold(rows: list[dict], protocol: dict) -> dict:
    """Busca o grid escalar exato de A e audita cada etapa do desempate."""
    validate_protocol_contract(protocol)
    candidates = threshold_candidates(tuple(row["cos_pred"] for row in rows))
    ranked = []
    for threshold in candidates:
        metrics = calculate_metrics(
            rows, tuple(row["cos_pred"] >= threshold for row in rows)
        )
        ranked.append(
            (
                threshold,
                metrics,
                threshold_rank(metrics, (threshold,), CANDIDATE_ID, protocol),
            )
        )
    surviving = ranked
    counts = []
    decisive = None
    for index, criterion in enumerate(protocol["threshold_tie_break"]):
        best_value = max(rank[index] for _, _, rank in surviving)
        surviving = [item for item in surviving if item[2][index] == best_value]
        counts.append(len(surviving))
        if decisive is None and len(surviving) == 1:
            decisive = criterion
    if len(surviving) != 1:
        raise ValueError("Desempate escalar divergiu da busca R3.1.1.")
    selected_metrics = surviving[0][1]
    return {
        "selected_threshold": surviving[0][0],
        "threshold_candidates_count": len(candidates),
        "metrics": {
            **selected_metrics,
            "min_KCAR_URR": min(selected_metrics["KCAR"], selected_metrics["URR"]),
        },
        "selection_trace": {
            "criteria": protocol["threshold_tie_break"],
            "survivors_after_criterion": counts,
            "decisive_criterion": decisive,
        },
    }


def build_calibration_report(
    rows: list[dict], protocol: dict, source: dict, code_commit: str, artifacts: dict
) -> dict:
    """Registra ajuste em development sem tratá-lo como generalização."""
    selected = choose_final_threshold(rows, protocol)
    threshold = selected["selected_threshold"]
    audited = []
    for row in rows:
        accepted = row["cos_pred"] >= threshold
        audited.append(
            {
                **row,
                "selected_threshold": threshold,
                "decision": "ACCEPT" if accepted else "REJECT",
                "emitted_label": row["predicted_label"] if accepted else None,
            }
        )
    folds = []
    for session in SESSION_IDS:
        group = [row for row in audited if row["outer_fold"] == session]
        folds.append(
            {
                "outer_fold": session,
                "outer_metrics": calculate_metrics(
                    group, tuple(row["decision"] == "ACCEPT" for row in group)
                ),
            }
        )
    breakdown = selected_breakdowns({"per_query": audited, "folds": folds})
    for item in breakdown["known_by_true_class"]:
        item["coverage"] = (item["KCA"] + item["KWA"]) / item["total"]
    return {
        "state": "REJECTION_3_REFERENCE_POLICY_FROZEN",
        "format_version": 1,
        "code_commit": code_commit,
        "protocol_version": "R3.1.1",
        "protocol_sha256": PROTOCOL_SHA256,
        "r3_2_diagnostics_sha256": DIAGNOSTICS_SHA256,
        "r3_3_nested_evaluation_sha256": R3_3_SHA256,
        "candidate_id": CANDIDATE_ID,
        "calibration_method": METHOD,
        "development_counts": {"known": 54, "unknown": 54, "total": 108},
        "threshold_candidates_count": selected["threshold_candidates_count"],
        "selected_threshold": threshold,
        "decision_operator": ">=",
        "selected_threshold_metrics": selected["metrics"],
        "selection_trace": selected["selection_trace"],
        "r3_3_nested_estimate": source["candidates"][CANDIDATE_ID]["global_metrics"],
        "breakdowns": breakdown,
        "per_query_decisions": audited,
        "deployment_artifact_hashes": artifacts,
        "heldouts_opened": False,
        "heldout_result_json_loaded": False,
        "edge_calibrated": False,
        "new_heldout_evaluated": False,
        "calibration_fit_not_generalization": True,
    }


def build_reference_freeze_manifest(result: dict, calibration_sha256: str) -> dict:
    """Congela somente a referência FP32; política Edge continua pendente."""
    if result["candidate_id"] != CANDIDATE_ID or len(calibration_sha256) != 64:
        raise ValueError("Calibração incompatível com o freeze R3.4.")
    artifacts = result["deployment_artifact_hashes"]
    return {
        "state": "REJECTION_3_REFERENCE_POLICY_FROZEN",
        "format_version": 1,
        "protocol_version": result["protocol_version"],
        "protocol_sha256": result["protocol_sha256"],
        "r3_3_nested_evaluation_sha256": result["r3_3_nested_evaluation_sha256"],
        "calibration_result_path": CALIBRATION_PATH.as_posix(),
        "calibration_result_sha256": calibration_sha256,
        "candidate_id": CANDIDATE_ID,
        "selected_threshold": result["selected_threshold"],
        "decision_operator": ">=",
        "score": "cos_pred",
        "labels": list(DEFAULT_VISUAL_LABELS),
        "deployment_artifact_hashes": artifacts,
        "centroid_reference_sha256": artifacts.get("centroids", {}).get("sha256"),
        "preprocessing_config_fingerprints": {
            name: artifacts[name]["sha256"]
            for name in (
                "positive_classifier_config",
                "roi_manifest",
                "positive_embedding_manifest",
            )
            if name in artifacts
        },
        "calibration_method": METHOD,
        "heldout_prohibition": list(FORBIDDEN_SOURCES),
        "heldout_result_json_loaded": False,
        "edge_policy_pending": True,
    }


def verify_deployment_artifacts(repository_root: Path) -> dict:
    """Confere SHA e reconstrói centroides das 54 positivas sem inferência."""
    root = Path(repository_root).resolve()
    expected = {
        "positive_classifier_checkpoint": (
            CHECKPOINT_RELATIVE_PATH,
            POSITIVE_CHECKPOINT_SHA256,
        ),
        "positive_classifier_config": (CONFIG_RELATIVE_PATH, POSITIVE_CONFIG_SHA256),
        "swinlip_checkpoint": (SWINLIP_CHECKPOINT_PATH, SWINLIP_CHECKPOINT_SHA256),
        "centroids": (CENTROID_RELATIVE_PATH, CENTROID_SHA256),
        "legacy_centroid_config": (
            CONFIG_FINAL_RELATIVE_PATH,
            REFERENCE_CONFIG_SHA256,
        ),
        "roi_manifest": (ROI_MANIFEST_RELATIVE_PATH, ROI_MANIFEST_SHA256),
        "positive_embedding_manifest": (
            EMBEDDING_MANIFEST_PATH,
            EMBEDDING_MANIFEST_SHA256,
        ),
    }
    artifacts = {}
    for name, (relative, digest) in expected.items():
        path = guard_repository_path(root, relative)
        if sha256_file(path) != digest:
            raise ValueError(f"Artefato final divergiu do SHA congelado: {name}.")
        artifacts[name] = {"path": relative.as_posix(), "sha256": digest}
    artifacts["legacy_centroid_config"][
        "role"
    ] = "centroid_provenance_only; embedded R2 threshold is not the R3 policy"
    reference = load_frozen_clip_rejection(root / CONFIG_FINAL_RELATIVE_PATH, root)
    positives = preflight_hybrid_loso(root)["samples"]
    if len(positives) != 54 or not np.array_equal(
        build_final_clip_centroids(positives), reference.centroids
    ):
        raise ValueError("Centroide final não reproduz as 54 positivas.")
    return artifacts


def preflight_repository(repository_root: Path) -> dict:
    """Valida todas as fontes e o commit antes de qualquer busca de threshold."""
    root = Path(repository_root).resolve()
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip()
    if status:
        raise ValueError("Worktree precisa estar limpo antes da calibração real.")
    for relative in (CALIBRATION_PATH, FREEZE_PATH):
        if guard_repository_path(root, relative).exists():
            raise FileExistsError(f"Resultado/freeze anterior já existe: {relative}")
    expected = (
        (PROTOCOL_PATH, PROTOCOL_SHA256),
        (DIAGNOSTICS_PATH, DIAGNOSTICS_SHA256),
        (R3_3_PATH, R3_3_SHA256),
    )
    for relative, digest in expected:
        if sha256_file(guard_repository_path(root, relative)) != digest:
            raise ValueError(f"SHA-256 de proveniência divergiu: {relative}")
    protocol = json.loads(
        guard_repository_path(root, PROTOCOL_PATH).read_text(encoding="utf-8")
    )
    source = json.loads(
        guard_repository_path(root, R3_3_PATH).read_text(encoding="utf-8")
    )
    rows = validate_cross_fitted_source(source, protocol)
    artifacts = verify_deployment_artifacts(root)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    return {
        "root": root,
        "protocol": protocol,
        "source": source,
        "rows": rows,
        "artifacts": artifacts,
        "commit": commit,
    }


def persist_outputs_once(
    repository_root: Path, result_bytes: bytes, manifest_bytes: bytes
) -> tuple[str, str]:
    """Cria ambos os artefatos uma única vez e confere o conteúdo por SHA."""
    root = Path(repository_root).resolve()
    output = guard_repository_path(root, CALIBRATION_PATH)
    freeze = guard_repository_path(root, FREEZE_PATH)
    if output.exists() or freeze.exists():
        raise FileExistsError("Resultado/freeze já existe; calibração única protegida.")
    result_sha256 = hashlib.sha256(result_bytes).hexdigest()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    with output.open("xb") as stream:
        stream.write(result_bytes)
    with freeze.open("xb") as stream:
        stream.write(manifest_bytes)
    if sha256_file(output) != result_sha256 or sha256_file(freeze) != manifest_sha256:
        raise ValueError("Auditoria de SHA após a gravação falhou; não reexecutar.")
    return result_sha256, manifest_sha256


def run_real_final_calibration(repository_root: Path) -> tuple[dict, str, str]:
    """Executa uma busca real e persiste resultado e freeze sem sobrescrever."""
    prepared = preflight_repository(repository_root)
    report = build_calibration_report(
        prepared["rows"],
        prepared["protocol"],
        prepared["source"],
        prepared["commit"],
        prepared["artifacts"],
    )
    result_bytes = canonical_result_bytes(report)
    result_sha256 = hashlib.sha256(result_bytes).hexdigest()
    manifest = build_reference_freeze_manifest(report, result_sha256)
    manifest_bytes = canonical_result_bytes(manifest)
    root = prepared["root"]
    for relative, expected in (
        (PROTOCOL_PATH, PROTOCOL_SHA256),
        (DIAGNOSTICS_PATH, DIAGNOSTICS_SHA256),
        (R3_3_PATH, R3_3_SHA256),
    ):
        if sha256_file(guard_repository_path(root, relative)) != expected:
            raise ValueError("Fonte de calibração mudou após o preflight.")
    hashes = persist_outputs_once(root, result_bytes, manifest_bytes)
    return report, *hashes
