"""Paridade de implementação FP32 × ONNX FP16 da política R3 congelada."""

import hashlib
import json
import math
import os
import subprocess
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from silent_voice.edge.preheldout_freeze import (
    FREEZE_MANIFEST as CYCLE_6_FREEZE_PATH,
    load_frozen_edge_pipeline,
    load_task_69_audit,
    validate_edge_config,
    validate_freeze_manifest,
)
from silent_voice.edge.parity import FROZEN_THRESHOLD as CYCLE_6_FP32_THRESHOLD
from silent_voice.edge.swinlip_export import (
    FROZEN_PATHS,
    SwinLipClipEncoder,
    validate_frozen_hashes,
)
from silent_voice.rejection.hybrid_rejection_final import (
    load_frozen_clip_rejection,
    score_unknown_clip,
)
from silent_voice.rejection.hybrid_rejection_nested_loso import (
    preflight_real_nested_loso,
    validate_development_pairs,
)
from silent_voice.rejection.rejection_3_final_calibration import (
    CALIBRATION_PATH,
    FREEZE_PATH,
    R3_3_PATH,
    R3_3_SHA256,
    guard_repository_path,
)
from silent_voice.rejection.rejection_3_nested_selection import (
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    canonical_result_bytes,
)
from silent_voice.rejection.rejection_protocol import NEGATIVE_CATEGORIES
from silent_voice.vision.hybrid_features import HybridSample
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.positive_classifier_final import (
    load_frozen_positive_classifier,
)
from silent_voice.vision.swinlip_frozen_encoder import load_official_model
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

CANDIDATE_ID = "R2_GLOBAL_CLIP_COSINE"
THRESHOLD = 0.6367948055267334
REFERENCE_FREEZE_SHA256 = (
    "8bd8d33e5b9e020fadd8a1acdcf852368895c563f9e40a74416c7d0676f19418"
)
CALIBRATION_SHA256 = "89a384fd94e708c4e56c0e514f2224bbf4da5caae212b196022e3f5827d1574d"
EDGE_CONFIG_PATH = Path(
    "data/processed/evaluation/cycle_06_edge_preheldout_final_config.json"
)
EDGE_CONFIG_SHA256 = "a761de851e7dc22ed8974dbd3dc98e23963d384057488bdfe9aae0ef406eb4d4"
CYCLE_6_FREEZE_SHA256 = (
    "41cf1f308a1c153bfc0f533c70676309139d63531cce9ce31363c74643e611bd"
)
RESULT_PATH = Path("data/processed/evaluation/rejection_3_edge_parity.json")
ATTEMPT_PATH = Path("data/processed/evaluation/rejection_3_edge_parity_attempt.json")
EDGE_FREEZE_PATH = Path("docs/cycles/rejection_3_edge_freeze.json")
STATE_PASS = "REJECTION_3_EDGE_POLICY_FROZEN"
STATE_FAIL = "REJECTION_3_EDGE_PARITY_FAILED"


def validate_policy_freeze(freeze: dict, calibration: dict) -> float:
    """Exige exatamente a família e o threshold pré-selecionados na R3.4."""
    if (
        freeze.get("state") != "REJECTION_3_REFERENCE_POLICY_FROZEN"
        or freeze.get("candidate_id") != CANDIDATE_ID
        or freeze.get("score") != "cos_pred"
        or freeze.get("decision_operator") != ">="
        or freeze.get("selected_threshold") != THRESHOLD
        or freeze.get("edge_policy_pending") is not True
        or calibration.get("candidate_id") != CANDIDATE_ID
        or calibration.get("selected_threshold") != THRESHOLD
        or calibration.get("heldouts_opened") is not False
        or calibration.get("heldout_result_json_loaded") is not False
    ):
        raise ValueError("Política R3.4 divergente; paridade Edge proibida.")
    return THRESHOLD


def verify_artifact_hashes(root: Path, inventory: dict[str, tuple[str, str]]) -> dict:
    """Rejeita path não autorizado antes de ler e confere cada SHA-256."""
    verified = {}
    for name, (relative, expected) in inventory.items():
        path = guard_repository_path(root, relative)
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"Artefato ausente ou SHA-256 divergente: {name}.")
        verified[name] = {"path": Path(relative).as_posix(), "sha256": expected}
    return verified


def validate_corpus(corpus: list[dict]) -> None:
    """Aceita somente as 108 queries únicas do development autorizado."""
    if len(corpus) != 108 or len({row.get("sample_id") for row in corpus}) != 108:
        raise ValueError("Corpus de paridade exige 108 sample_id únicos.")
    allowed = {
        "KNOWN": ("sessao_01", "sessao_02", "sessao_03"),
        "UNKNOWN": ("rejeicao_dev_01", "rejeicao_dev_02", "rejeicao_dev_03"),
    }
    counts = Counter((row.get("sample_kind"), row.get("session_id")) for row in corpus)
    if counts != Counter(
        (kind, session)
        for kind, sessions in allowed.items()
        for session in sessions
        for _ in range(18)
    ):
        raise ValueError("Corpus de paridade contém sessão ou contagem inválida.")
    for row in corpus:
        kind = row["sample_kind"]
        expected = row.get("true_label_or_category")
        if (
            not isinstance(row["sample_id"], str)
            or not isinstance(expected, str)
            or not expected
            or (kind == "KNOWN" and expected not in DEFAULT_VISUAL_LABELS)
            or (kind == "UNKNOWN" and expected not in NEGATIVE_CATEGORIES)
        ):
            raise ValueError("Metadados da query fora do development permitido.")


def pair_prediction(
    source: dict, reference: dict, edge: dict, threshold: float
) -> dict:
    """Pareia uma query e calcula decisões com um único threshold inclusivo."""
    if (
        threshold != THRESHOLD
        or reference.get("sample_id") != source.get("sample_id")
        or edge.get("sample_id") != source.get("sample_id")
    ):
        raise ValueError("Threshold ou sample_id não corresponde ao contrato R3.5.")
    labels = (reference.get("predicted_label"), edge.get("predicted_label"))
    scores = (reference.get("cos_pred"), edge.get("cos_pred"))
    if any(label not in DEFAULT_VISUAL_LABELS for label in labels) or any(
        not isinstance(score, (int, float)) or not math.isfinite(score)
        for score in scores
    ):
        raise ValueError("Label ou cos_pred inválido na paridade.")
    fp32_score, fp16_score = map(float, scores)
    fp32_decision = "ACCEPT" if fp32_score >= threshold else "REJECT"
    fp16_decision = "ACCEPT" if fp16_score >= threshold else "REJECT"
    fp32_emitted = labels[0] if fp32_decision == "ACCEPT" else None
    fp16_emitted = labels[1] if fp16_decision == "ACCEPT" else None
    if (
        edge.get("threshold") != threshold
        or edge.get("decision") != fp16_decision
        or edge.get("accepted_label") != fp16_emitted
    ):
        raise ValueError("Runtime Edge não aplicou exatamente a política R3.4.")
    return {
        **source,
        "fp32_predicted_label": labels[0],
        "fp16_predicted_label": labels[1],
        "label_match": labels[0] == labels[1],
        "fp32_cos_pred": fp32_score,
        "fp16_cos_pred": fp16_score,
        "signed_score_difference": fp16_score - fp32_score,
        "absolute_score_difference": abs(fp16_score - fp32_score),
        "reference_threshold": threshold,
        "fp32_decision": fp32_decision,
        "fp16_decision": fp16_decision,
        "rejection_decision_match": fp32_decision == fp16_decision,
        "fp32_emitted_label": fp32_emitted,
        "fp16_emitted_label": fp16_emitted,
        "emitted_result_match": fp32_emitted == fp16_emitted,
        "fp32_absolute_distance_to_threshold": abs(fp32_score - threshold),
        "fp16_absolute_distance_to_threshold": abs(fp16_score - threshold),
    }


def build_parity_report(
    rows: list[dict], *, commit: str, provenance: dict, runtime: str
) -> dict:
    """Agrega apenas diferenças de implementação, sem métricas de generalização."""
    validate_corpus(rows)
    if any(row["reference_threshold"] != THRESHOLD for row in rows):
        raise ValueError("Threshold por query divergiu da referência única.")
    differences = np.asarray(
        [row["absolute_score_difference"] for row in rows], dtype=np.float64
    )
    parity = {
        "predicted_label_match_count": sum(row["label_match"] for row in rows),
        "rejection_decision_match_count": sum(
            row["rejection_decision_match"] for row in rows
        ),
        "emitted_result_match_count": sum(row["emitted_result_match"] for row in rows),
        "total": 108,
    }
    passed = all(parity[name] == 108 for name in parity if name != "total")
    closest_fp32 = min(
        rows,
        key=lambda row: (row["fp32_absolute_distance_to_threshold"], row["sample_id"]),
    )
    closest_fp16 = min(
        rows,
        key=lambda row: (row["fp16_absolute_distance_to_threshold"], row["sample_id"]),
    )
    boundary_fields = (
        "sample_id",
        "fp32_cos_pred",
        "fp16_cos_pred",
        "fp32_absolute_distance_to_threshold",
        "fp16_absolute_distance_to_threshold",
    )

    def boundary(row: dict) -> dict:
        return {key: row[key] for key in boundary_fields}

    return {
        "format_version": 1,
        "state": STATE_PASS if passed else STATE_FAIL,
        "scientific_scope": "IMPLEMENTATION_PARITY_NOT_GENERALIZATION",
        "code_commit": commit,
        "candidate_id": CANDIDATE_ID,
        "score": "cos_pred",
        "reference_threshold": THRESHOLD,
        "decision_operator": ">=",
        "runtime": runtime,
        "provenance": provenance,
        "query_count": 108,
        "development_counts": {"KNOWN": 54, "UNKNOWN": 54},
        "per_query": rows,
        "parity": parity,
        "score_drift": {
            "max_abs": float(np.max(differences)),
            "mean_abs": float(np.mean(differences)),
            "median_abs": float(np.median(differences)),
            "p95_abs": float(np.quantile(differences, 0.95, method="linear")),
            "quantile_method": "linear",
        },
        "boundary_audit": {
            "closest_fp32": boundary(closest_fp32),
            "closest_fp16": boundary(closest_fp16),
            "minimum_fp32_absolute_margin": closest_fp32[
                "fp32_absolute_distance_to_threshold"
            ],
            "minimum_fp16_absolute_margin": closest_fp16[
                "fp16_absolute_distance_to_threshold"
            ],
            "within_0_01": [
                boundary(row)
                for row in rows
                if min(
                    row["fp32_absolute_distance_to_threshold"],
                    row["fp16_absolute_distance_to_threshold"],
                )
                < 0.01
            ],
        },
        "divergences": [
            row
            for row in rows
            if not (
                row["label_match"]
                and row["rejection_decision_match"]
                and row["emitted_result_match"]
            )
        ],
        "heldouts_opened": False,
        "heldout_result_json_loaded": False,
        "edge_threshold_recalibrated": False,
        "new_heldout_evaluated": False,
    }


def build_edge_freeze_manifest(report: dict, result_sha256: str) -> dict:
    """Congela Edge apenas se os três gates por query forem perfeitos."""
    if report.get("state") != STATE_PASS or any(
        report.get("parity", {}).get(name) != 108
        for name in (
            "predicted_label_match_count",
            "rejection_decision_match_count",
            "emitted_result_match_count",
        )
    ):
        raise ValueError("Paridade insuficiente para congelar política Edge.")
    provenance = report["provenance"]
    return {
        "format_version": 1,
        "state": STATE_PASS,
        "reference_freeze_sha256": provenance.get("reference_freeze_sha256"),
        "edge_parity_result_sha256": result_sha256,
        "candidate_id": CANDIDATE_ID,
        "score": "cos_pred",
        "reference_threshold": THRESHOLD,
        "decision_operator": ">=",
        "selected_edge_artifacts": provenance.get("edge_artifacts", {}),
        "reference_artifacts": provenance.get("reference_artifacts", {}),
        "runtime": report["runtime"],
        "pipeline_fingerprint_sha256": provenance.get("pipeline_fingerprint_sha256"),
        "preprocessing_fingerprint_sha256": provenance.get(
            "preprocessing_fingerprint_sha256"
        ),
        "parity": report["parity"],
        "runtime_specific_threshold": False,
        "heldout_prohibition": [
            "sessao_04",
            "rejeicao_heldout_01",
            "cycle_06_heldout_session_01",
            "cycle_06_heldout_session_02",
        ],
        "android_integration_pending": True,
    }


def preflight_repository(repository_root: Path) -> dict:
    """Valida hashes, corpus e estado limpo sem executar previsões."""
    root = Path(repository_root).resolve()
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError(
            "Worktree versionável deve estar limpo antes da paridade real."
        )
    for relative in (RESULT_PATH, ATTEMPT_PATH, EDGE_FREEZE_PATH):
        if guard_repository_path(root, relative).exists():
            raise FileExistsError("Resultado R3.5 já existe; execução única protegida.")
    sources = verify_artifact_hashes(
        root,
        {
            "protocol": (PROTOCOL_PATH.as_posix(), PROTOCOL_SHA256),
            "r3_3_nested_evaluation": (R3_3_PATH.as_posix(), R3_3_SHA256),
            "r3_4_calibration": (CALIBRATION_PATH.as_posix(), CALIBRATION_SHA256),
            "r3_4_reference_freeze": (FREEZE_PATH.as_posix(), REFERENCE_FREEZE_SHA256),
            "cycle_6_edge_config": (EDGE_CONFIG_PATH.as_posix(), EDGE_CONFIG_SHA256),
            "cycle_6_edge_freeze": (
                CYCLE_6_FREEZE_PATH.as_posix(),
                CYCLE_6_FREEZE_SHA256,
            ),
        },
    )
    freeze = json.loads((root / FREEZE_PATH).read_text(encoding="utf-8"))
    calibration = json.loads((root / CALIBRATION_PATH).read_text(encoding="utf-8"))
    validate_policy_freeze(freeze, calibration)
    if (
        freeze.get("calibration_result_sha256") != CALIBRATION_SHA256
        or freeze.get("protocol_sha256") != PROTOCOL_SHA256
        or freeze.get("r3_3_nested_evaluation_sha256") != R3_3_SHA256
    ):
        raise ValueError("Proveniência do freeze R3.4 divergente.")
    config = json.loads((root / EDGE_CONFIG_PATH).read_text(encoding="utf-8"))
    cycle_freeze = json.loads((root / CYCLE_6_FREEZE_PATH).read_text(encoding="utf-8"))
    validate_edge_config(root, config)
    validate_freeze_manifest(root, cycle_freeze, config)
    if (
        config.get("pipeline_fingerprint_sha256")
        != cycle_freeze.get("pipeline_fingerprint_sha256")
        or config.get("cycle_06_heldout_evaluation_candidate") != "ONNX_FP16"
    ):
        raise ValueError("Fingerprint ou candidato Edge divergiu.")
    original = validate_frozen_hashes(root)
    edge = verify_artifact_hashes(
        root,
        {
            name: (record["path"], record["sha256"])
            for name, record in cycle_freeze["artifacts"].items()
        },
    )
    if (
        edge["encoder"]["sha256"] != config["encoder"]["sha256"]
        or edge["classifier"]["sha256"] != config["classifier"]["sha256"]
        or edge["edge_centroids"]["sha256"] != config["rejection"]["centroid_sha256"]
    ):
        raise ValueError("Artefato Edge não corresponde à configuração 6.10.")
    from scripts.evaluation.evaluate_cycle_06_edge_feasibility import (
        _load_corpus,
        _manifest_records,
    )

    selected, manifests = _manifest_records(root)
    corpus = _load_corpus(root, selected, manifests["embeddings"])
    development = preflight_real_nested_loso(root)
    validate_development_pairs(development["positives"], development["negatives"])
    samples = {
        row.sample_id: row
        for row in (*development["positives"], *development["negatives"])
    }
    if set(samples) != {row["sample_id"] for row in corpus}:
        raise ValueError("ROI, embeddings e features não pareiam por sample_id.")
    metadata = []
    for row in corpus:
        sample = samples[row["sample_id"]]
        if sample.session_id != row["session_id"]:
            raise ValueError("Sessão do corpus não pareia com o sample_id.")
        metadata.append(
            {
                "sample_id": row["sample_id"],
                "sample_kind": row["sample_kind"],
                "session_id": row["session_id"],
                "true_label_or_category": (
                    sample.label
                    if row["sample_kind"] == "KNOWN"
                    else sample.negative_category
                ),
            }
        )
    validate_corpus(metadata)
    return {
        "root": root,
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "corpus": corpus,
        "metadata": metadata,
        "samples": samples,
        "config": config,
        "provenance": {
            **sources,
            "reference_freeze_sha256": REFERENCE_FREEZE_SHA256,
            "reference_artifacts": freeze["deployment_artifact_hashes"],
            "edge_artifacts": edge,
            "original_artifact_hashes": original,
            "pipeline_fingerprint_sha256": config["pipeline_fingerprint_sha256"],
            "preprocessing_fingerprint_sha256": hashlib.sha256(
                canonical_result_bytes(config["preprocessing"])
            ).hexdigest(),
        },
        "semantic_predictions": 0,
    }


def _historical_cycle_6(root: Path, config: dict) -> dict:
    """Recupera histórico somente após agregar a paridade R3.5."""
    audit = load_task_69_audit(root)
    sanity_path = (
        root / "data/processed/evaluation/cycle_06_edge_postfreeze_sanity.json"
    )
    sanity = json.loads(sanity_path.read_text(encoding="utf-8"))
    if (
        sanity.get("sample_count") != 108
        or sanity.get("label_agreement_to_task_69_count") != 108
        or sanity.get("decision_agreement_to_task_69_count") != 108
    ):
        raise ValueError("Histórico de sanidade Cycle 6 divergiu.")
    candidate = next(
        row for row in audit["audit"]["candidates"] if row["id"] == "ONNX_FP16"
    )
    return {
        "comparison_kind": "DESCRIPTIVE_DIFFERENT_POLICY_THRESHOLD",
        "task_6_9_label_parity": candidate["aggregate"]["label_agreement_count"],
        "task_6_9_rejection_parity": candidate["aggregate"]["decision_agreement_count"],
        "task_6_10_sanity_label_parity": sanity["label_agreement_to_task_69_count"],
        "task_6_10_sanity_decision_parity": sanity[
            "decision_agreement_to_task_69_count"
        ],
        "task_6_10_historical_edge_threshold": config["rejection"]["threshold"],
        "task_6_9_historical_fp32_threshold": CYCLE_6_FP32_THRESHOLD,
        "used_to_select_r3_5_policy": False,
    }


def claim_one_shot_attempt(root: Path, commit: str) -> Path:
    """Marca a primeira inferência antes de processar qualquer query real."""
    attempt = guard_repository_path(root, ATTEMPT_PATH)
    attempt.parent.mkdir(parents=True, exist_ok=True)
    if (Path(root) / RESULT_PATH).exists():
        raise FileExistsError("Resultado R3.5 já existe; avaliação não será repetida.")
    with attempt.open("xb") as stream:
        stream.write(
            canonical_result_bytes(
                {
                    "phase": "INFERENCE_STARTED",
                    "code_commit": commit,
                    "prediction_count_exposed": 0,
                }
            )
        )
    return attempt


def _update_attempt(attempt: Path, payload: dict) -> None:
    pending = attempt.with_name(attempt.name + ".pending")
    with pending.open("xb") as stream:
        stream.write(canonical_result_bytes(payload))
    os.replace(pending, attempt)


def _predict_all(
    prepared: dict,
    positive: object,
    rejection: object,
    wrapper: object,
    edge: object,
    rows: list[dict],
) -> None:
    """Executa FP32 e FP16 no mesmo tensor, sem imprimir resultados parciais."""
    with torch.no_grad():
        for source, metadata in zip(
            prepared["corpus"], prepared["metadata"], strict=True
        ):
            sample = prepared["samples"][source["sample_id"]]
            clip = wrapper(torch.from_numpy(source["input"]))[0].numpy().copy()
            query = HybridSample(
                sample.sample_id + "__r3_parity_query",
                sample.session_id,
                (
                    metadata["true_label_or_category"]
                    if metadata["sample_kind"] == "KNOWN"
                    else ""
                ),
                sample.label_index if metadata["sample_kind"] == "KNOWN" else -1,
                clip,
                sample.features,
            )
            fp32_prediction = positive.predict_query(query)
            fp32_score = score_unknown_clip(
                clip, fp32_prediction["predicted_label_index"], rejection.centroids
            )
            fp16_prediction = edge.predict(sample, source["input"])
            rows.append(
                pair_prediction(
                    metadata,
                    {
                        "sample_id": sample.sample_id,
                        "predicted_label": fp32_prediction["predicted_label"],
                        "cos_pred": fp32_score,
                    },
                    {
                        "sample_id": sample.sample_id,
                        "predicted_label": fp16_prediction["predicted_label"],
                        "cos_pred": fp16_prediction["clip_class_cosine"],
                        "threshold": fp16_prediction["threshold"],
                        "decision": fp16_prediction["decision"],
                        "accepted_label": fp16_prediction["accepted_label"],
                    },
                    THRESHOLD,
                )
            )


def _persist_report(root: Path, report: dict) -> tuple[str, str | None]:
    """Grava resultado completo e somente no PASS grava o freeze versionável."""
    result_bytes = canonical_result_bytes(report)
    result_sha256 = hashlib.sha256(result_bytes).hexdigest()
    result_path = root / RESULT_PATH
    pending = result_path.with_name(result_path.name + ".pending")
    if result_path.exists() or pending.exists():
        raise FileExistsError("Resultado R3.5 já existe; não reexecutar.")
    with pending.open("xb") as stream:
        stream.write(result_bytes)
    os.rename(pending, result_path)
    if sha256_file(result_path) != result_sha256:
        raise ValueError("SHA-256 do resultado R3.5 divergiu após gravação.")
    if report["state"] == STATE_FAIL:
        return result_sha256, None
    manifest = build_edge_freeze_manifest(report, result_sha256)
    manifest_bytes = canonical_result_bytes(manifest)
    freeze_path = root / EDGE_FREEZE_PATH
    with freeze_path.open("xb") as stream:
        stream.write(manifest_bytes)
    freeze_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if sha256_file(freeze_path) != freeze_sha256:
        raise ValueError("SHA-256 do freeze Edge divergiu após gravação.")
    return result_sha256, freeze_sha256


def run_real_parity(repository_root: Path) -> tuple[dict, str, str | None]:
    """Executa uma avaliação real, preservando auditoria de tentativa."""
    prepared = preflight_repository(repository_root)
    root = prepared["root"]
    positive = load_frozen_positive_classifier(
        root / FROZEN_PATHS["classifier"], root / FROZEN_PATHS["positive_config"]
    )
    rejection = load_frozen_clip_rejection(
        root / FROZEN_PATHS["rejection_config"], root
    )
    official, _ = load_official_model(
        root / "data/external/swinlip/source", root / FROZEN_PATHS["encoder"]
    )
    wrapper = SwinLipClipEncoder(official)
    edge = replace(
        load_frozen_edge_pipeline(root, root / EDGE_CONFIG_PATH, positive.templates),
        threshold=THRESHOLD,
    )
    torch.set_num_threads(4)
    rows = []
    attempt = claim_one_shot_attempt(root, prepared["commit"])
    try:
        _predict_all(prepared, positive, rejection, wrapper, edge, rows)
        report = build_parity_report(
            rows,
            commit=prepared["commit"],
            provenance=prepared["provenance"],
            runtime=(
                f"onnxruntime {ort.__version__}; CPUExecutionProvider; "
                f"PyTorch {torch.__version__} CPU"
            ),
        )
        report["historical_cycle_6_comparison"] = _historical_cycle_6(
            root, prepared["config"]
        )
        result_sha, freeze_sha = _persist_report(root, report)
        _update_attempt(
            attempt,
            {
                "phase": "COMPLETED",
                "code_commit": prepared["commit"],
                "processed_count": 108,
                "result_state": report["state"],
                "result_sha256": result_sha,
                "freeze_sha256": freeze_sha,
                "prediction_count_exposed": 0,
            },
        )
        return report, result_sha, freeze_sha
    except Exception as error:
        _update_attempt(
            attempt,
            {
                "phase": "FAILED_AFTER_INFERENCE_STARTED",
                "code_commit": prepared["commit"],
                "processed_count": len(rows),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "prediction_count_exposed": 0,
            },
        )
        raise
