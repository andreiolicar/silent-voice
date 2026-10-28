"""Avaliação única do held-out R3 com a política Edge congelada."""

import hashlib
import json
import math
import os
import subprocess
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import onnxruntime as ort

from scripts.evaluation.qc_rejection_3_heldout import (
    _attempt_path,
    _canonical_file_sha256,
    validate_frozen_plan,
)
from silent_voice.edge.cycle_06_final_heldout import prepare_query, wilson_interval
from silent_voice.edge.preheldout_freeze import (
    load_frozen_edge_pipeline,
    validate_edge_config,
)
from silent_voice.edge.rejection_3_edge_parity import (
    CANDIDATE_ID,
    THRESHOLD,
)
from silent_voice.rejection.rejection_metrics import calculate_rejection_metrics
from silent_voice.rejection.rejection_protocol import NEGATIVE_CATEGORIES
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.positive_classifier_final import (
    CHECKPOINT_RELATIVE_PATH,
    CONFIG_RELATIVE_PATH,
    load_frozen_positive_classifier,
)
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


LABELS = tuple(DEFAULT_VISUAL_LABELS)
CATEGORIES = tuple(NEGATIVE_CATEGORIES)
SESSIONS = tuple(f"r3_heldout_session_{number:02d}" for number in (1, 2, 3))
PLAN = Path("docs/cycles/rejection_3_heldout_capture_plan.json")
FREEZE = Path("docs/cycles/rejection_3_heldout_freeze.json")
OUTPUT = Path("data/processed/evaluation/rejection_3_final_heldout_evaluation.json")
ATTEMPT = Path("data/processed/evaluation/rejection_3_final_heldout_attempt.json")
PROVENANCE = {
    "r3_1_1_protocol": (
        Path("docs/cycles/rejection_3_protocol.json"),
        "1a7d178c5ea9fd5e8376622db260828561efaf3cfa3afb0734d58d076c35ebf7",
    ),
    "r3_4_reference_freeze": (
        Path("docs/cycles/rejection_3_reference_freeze.json"),
        "8bd8d33e5b9e020fadd8a1acdcf852368895c563f9e40a74416c7d0676f19418",
    ),
    "r3_5_edge_parity_result": (
        Path("data/processed/evaluation/rejection_3_edge_parity.json"),
        "307c9d9a11f323d485d5501dc2b3c38b3ba01f8d30c04932fb84cd2f8b36fbc3",
    ),
    "r3_5_edge_freeze": (
        Path("docs/cycles/rejection_3_edge_freeze.json"),
        "1a67bcc8890d3f2f4e93f2346844d38a89db1de4448e0855cdb66d0b64af54ff",
    ),
    "r3_6b_qc": (
        Path("data/processed/evaluation/rejection_3_heldout_qc.json"),
        "2e5ee0be3b0e036283b765048134a5756bd652d545c6ff9c5686431eb1182e83",
    ),
    "r3_6b_heldout_freeze": (
        FREEZE,
        "20083016d75eab45069e451abdb6ed7b1cd67bf9b5dbd6e02ecbc08fbdf7e433",
    ),
}
PLAN_SHA256 = "24f16a85e64ba9eed9f22c62dd5427b2c4afedefc41d60c1de307685c8614965"
CAPTURE_MANIFEST = Path(
    "data/processed/evaluation/rejection_3_heldout_capture_manifest.json"
)
EDGE_CONFIG = Path(
    "data/processed/evaluation/cycle_06_edge_preheldout_final_config.json"
)
EXPECTED_RUNTIME = "1.30.0"
R3_6B_COMMIT = "267ece43b42b8a91b683920bb7665afb4b7c607f"
OLD_HELDOUT_NAMES = (
    "sessao_04",
    "rejeicao_heldout_01",
    "cycle_06_heldout_session_01",
    "cycle_06_heldout_session_02",
)


def serialize_result(payload: dict) -> bytes:
    """Serializa de modo determinístico, sem NaN e com LF final."""
    return (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def verify_provenance(root: Path, records: dict = PROVENANCE) -> dict:
    """Verifica SHA diretamente sem abrir held-outs anteriores."""
    verified = {}
    for name, (relative, expected) in records.items():
        path = (Path(root) / relative).resolve()
        if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
            raise ValueError(f"Proveniência ausente ou inválida: {name}")
        if sha256_file(path) != expected:
            raise ValueError(f"SHA-256 divergente: {name}")
        verified[name] = expected
    return verified


def decision_for_score(score: float) -> str:
    """Aplica a igualdade ACCEPT do threshold R3.4."""
    if not isinstance(score, (int, float)) or not math.isfinite(score):
        raise ValueError("cos_pred não finito.")
    return "ACCEPT" if score >= THRESHOLD else "REJECT"


def ensure_one_shot(output: Path, attempt: Path) -> None:
    """Qualquer tentativa prévia impede reavaliação automática."""
    if (
        output.exists()
        or attempt.exists()
        or output.with_name(output.name + ".pending").exists()
    ):
        raise FileExistsError("Held-out R3 já consumido ou avaliação iniciada.")


def _plan_rows(plan: dict) -> list[dict]:
    return [row for session in plan["sessions"] for row in session["schedule"]]


def validate_selected_samples(plan: dict, freeze: dict) -> tuple[dict, ...]:
    """Exige os 72 attempts congelados, pareados ao plano e ao audit."""
    rows = _plan_rows(plan)
    samples = freeze.get("samples", [])
    if len(rows) != 72 or len(samples) != 72:
        raise ValueError("São exigidas exatamente 72 amostras.")
    if len({row.get("sample_id") for row in samples}) != 72:
        raise ValueError("Sample ID duplicado no freeze.")
    if len({row.get("relative_path") for row in samples}) != 72:
        raise ValueError("Path duplicado no freeze.")
    if [block.get("session_id") for block in plan["sessions"]] != list(SESSIONS):
        raise ValueError("Sessões fora da ordem congelada.")
    counts = Counter((row.get("session_id"), row.get("sample_kind")) for row in samples)
    if counts != Counter(
        (session, kind)
        for session in SESSIONS
        for kind in ("KNOWN", "UNKNOWN")
        for _ in range(12)
    ):
        raise ValueError("Contagens por sessão ou tipo divergentes.")
    classes = Counter(
        row.get("expected_label")
        for row in samples
        if row.get("sample_kind") == "KNOWN"
    )
    categories = Counter(
        row.get("negative_category")
        for row in samples
        if row.get("sample_kind") == "UNKNOWN"
    )
    if classes != Counter({label: 6 for label in LABELS}) or categories != Counter(
        {category: 6 for category in CATEGORIES}
    ):
        raise ValueError("Contagens de classes ou categorias divergentes.")
    audit = {entry["sample_id"]: entry for entry in freeze.get("recapture_audit", [])}
    if len(audit) != len(freeze.get("recapture_audit", [])):
        raise ValueError("Recaptura duplicada no audit.")
    if set(audit) != {
        sample["sample_id"] for sample in samples if sample["selected_attempt"] > 1
    }:
        raise ValueError("Auditoria não corresponde aos attempts selecionados.")
    for source, sample in zip(rows, samples, strict=True):
        if any(
            source.get(field) != sample.get(field)
            for field in (
                "sample_id",
                "session_id",
                "sample_kind",
                "expected_label",
                "negative_category",
            )
        ):
            raise ValueError("Amostra não pareada com o plano.")
        attempt = sample.get("selected_attempt")
        if type(attempt) is not int or attempt < 1:
            raise ValueError("Número de attempt inválido.")
        selected = _attempt_path(source, attempt).as_posix()
        if sample.get("relative_path") != selected:
            raise ValueError("Path do attempt selecionado divergiu.")
        if any(name in selected for name in OLD_HELDOUT_NAMES):
            raise ValueError("Held-out antigo proibido.")
        if attempt > 1:
            entry = audit.get(sample["sample_id"])
            if (
                entry is None
                or entry.get("final_attempt_number") != attempt
                or entry.get("final_path") != selected
                or entry.get("final_sha256") != sample.get("sha256")
                or entry.get("before_model_inference") is not True
            ):
                raise ValueError("Attempt de recaptura sem auditoria correspondente.")
        elif sample["sample_id"] in audit:
            raise ValueError("Recaptura auditada não foi selecionada.")
        if (
            sample.get("technical_qc_decision") != "PASS"
            or sample.get("technical_qc_reasons") != []
            or type(sample.get("byte_size")) is not int
            or sample["byte_size"] <= 0
            or not isinstance(sample.get("sha256"), str)
            or len(sample["sha256"]) != 64
        ):
            raise ValueError("QC, tamanho ou SHA da amostra inválido.")
    return tuple(samples)


def verify_selected_file(root: Path, sample: dict) -> Path:
    """Verifica path, tamanho e SHA do MP4 selecionado sem decodificar."""
    base = (Path(root) / "data/raw/rejection_3_heldout").resolve()
    path = (Path(root) / sample["relative_path"]).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Path do vídeo fora do held-out R3.")
    if not path.is_file() or path.stat().st_size != sample["byte_size"]:
        raise ValueError(f"Tamanho/ausência do MP4: {sample['sample_id']}")
    if sha256_file(path) != sample["sha256"]:
        raise ValueError(f"SHA-256 do MP4 divergiu: {sample['sample_id']}")
    return path


def _validate_edge(root: Path, edge: dict, config: dict) -> dict:
    if (
        edge.get("state") != "REJECTION_3_EDGE_POLICY_FROZEN"
        or edge.get("candidate_id") != CANDIDATE_ID
        or edge.get("reference_threshold") != THRESHOLD
        or edge.get("decision_operator") != ">="
        or edge.get("runtime_specific_threshold") is not False
        or edge.get("pipeline_fingerprint_sha256")
        != config.get("pipeline_fingerprint_sha256")
        or config.get("cycle_06_heldout_evaluation_candidate") != "ONNX_FP16"
    ):
        raise ValueError("Política Edge R3 congelada divergiu.")
    if (
        ort.__version__ != EXPECTED_RUNTIME
        or "CPUExecutionProvider" not in ort.get_available_providers()
    ):
        raise ValueError("Runtime ONNX congelado indisponível.")
    validate_edge_config(root, config)
    artifact_hashes = {}
    for name in ("encoder", "classifier", "edge_centroids"):
        record = edge["selected_edge_artifacts"][name]
        relative = Path(record["path"])
        path = (root / relative).resolve()
        if not path.is_relative_to((root / "data/processed/models/edge").resolve()):
            raise ValueError(f"Path Edge inválido: {name}")
        if sha256_file(path) != record["sha256"]:
            raise ValueError(f"SHA-256 Edge divergiu: {name}")
        artifact_hashes[name] = record["sha256"]
    if (
        edge["selected_edge_artifacts"]["final_config"]["sha256"]
        != sha256_file(root / EDGE_CONFIG)
        or config["encoder"]["sha256"] != artifact_hashes["encoder"]
        or config["classifier"]["sha256"] != artifact_hashes["classifier"]
        or config["rejection"]["centroid_sha256"] != artifact_hashes["edge_centroids"]
    ):
        raise ValueError("Configuração e artefatos Edge não pareiam.")
    return artifact_hashes


def preflight(root: Path, require_clean_worktree: bool = True) -> dict:
    """Valida contratos e hashes sem decodificar ou predizer os 72 vídeos."""
    root = Path(root).resolve()
    ensure_one_shot(root / OUTPUT, root / ATTEMPT)
    if (
        require_clean_worktree
        and subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True
        ).strip()
    ):
        raise ValueError("Worktree versionável deve estar limpo.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", R3_6B_COMMIT, commit],
            cwd=root,
            check=False,
            capture_output=True,
        ).returncode
        != 0
    ):
        raise ValueError("Commit R3.6B não é ancestral do código de avaliação.")
    provenance = verify_provenance(root)
    reference = json.loads(
        (root / PROVENANCE["r3_4_reference_freeze"][0]).read_text(encoding="utf-8")
    )
    if (
        reference.get("candidate_id") != CANDIDATE_ID
        or reference.get("selected_threshold") != THRESHOLD
        or reference.get("score") != "cos_pred"
        or reference.get("decision_operator") != ">="
    ):
        raise ValueError("Política de referência R3.4 divergente.")
    if _canonical_file_sha256(root / PLAN) != PLAN_SHA256:
        raise ValueError("SHA-256 do capture plan divergente.")
    provenance["r3_6a_capture_plan"] = PLAN_SHA256
    plan = json.loads((root / PLAN).read_text(encoding="utf-8"))
    validate_frozen_plan(plan, PLAN_SHA256, provenance["r3_5_edge_freeze"])
    freeze = json.loads((root / FREEZE).read_text(encoding="utf-8"))
    if (
        freeze.get("state") != "REJECTION_3_HELDOUT_QC_PASSED"
        or freeze.get("heldout_evaluated") is not False
        or freeze.get("model_inference_performed") is not False
        or freeze.get("capture_plan_sha256") != PLAN_SHA256
        or freeze.get("edge_freeze_sha256") != provenance["r3_5_edge_freeze"]
        or freeze.get("qc_result") != "PASS"
    ):
        raise ValueError("Freeze R3.6B não autoriza avaliação.")
    if sha256_file(root / CAPTURE_MANIFEST) != freeze["capture_manifest_sha256"]:
        raise ValueError("SHA-256 do manifesto de captura divergiu.")
    provenance["capture_manifest"] = freeze["capture_manifest_sha256"]
    samples = validate_selected_samples(plan, freeze)
    paths = tuple(verify_selected_file(root, row) for row in samples)
    edge = json.loads(
        (root / PROVENANCE["r3_5_edge_freeze"][0]).read_text(encoding="utf-8")
    )
    config = json.loads((root / EDGE_CONFIG).read_text(encoding="utf-8"))
    artifact_hashes = _validate_edge(root, edge, config)
    for name, relative, expected in (
        (
            "positive_config",
            CONFIG_RELATIVE_PATH,
            config["classifier"]["source_config_sha256"],
        ),
        (
            "positive_checkpoint",
            CHECKPOINT_RELATIVE_PATH,
            config["classifier"]["source_checkpoint_sha256"],
        ),
    ):
        if sha256_file(root / relative) != expected:
            raise ValueError(f"SHA-256 divergente: {name}")
        artifact_hashes[name] = expected
    return {
        "root": root,
        "commit": commit,
        "plan": plan,
        "freeze": freeze,
        "samples": samples,
        "sample_paths": paths,
        "provenance": provenance,
        "artifact_hashes": artifact_hashes,
        "pipeline_fingerprint_sha256": edge["pipeline_fingerprint_sha256"],
        "sample_count": 72,
        "semantic_predictions": 0,
        "old_heldouts_opened": False,
    }


def _outcome(row: dict) -> str:
    if row["sample_kind"] == "UNKNOWN":
        return "UFA" if row["decision"] == "ACCEPT" else "UR"
    if row["decision"] == "REJECT":
        return "KR"
    return "KCA" if row["predicted_label"] == row["expected_label"] else "KWA"


def _validate_predictions(rows: list[dict], plan: dict, freeze: dict) -> None:
    samples = validate_selected_samples(plan, freeze)
    sources = _plan_rows(plan)
    if len(rows) != 72:
        raise ValueError("Resultado deve conter 72 previsões.")
    if len({row.get("sample_id") for row in rows}) != 72:
        raise ValueError("Sample ID duplicado nas previsões.")
    for row, source, sample in zip(rows, sources, samples, strict=True):
        if any(
            row.get(field) != source[field]
            for field in (
                "sample_id",
                "session_id",
                "sample_kind",
                "expected_label",
                "negative_category",
                "oov_prompt",
            )
        ) or any(
            row.get(field) != sample[sample_field]
            for field, sample_field in (
                ("selected_attempt", "selected_attempt"),
                ("relative_path", "relative_path"),
                ("mp4_sha256", "sha256"),
            )
        ):
            raise ValueError("Previsão não pareada ao plano/freeze.")
        label = row.get("predicted_label")
        score = row.get("cos_pred")
        if (
            label not in LABELS
            or row.get("predicted_label_index") != LABELS.index(label)
            or row.get("threshold") != THRESHOLD
            or row.get("decision") != decision_for_score(score)
            or row.get("emitted_label")
            != (label if row["decision"] == "ACCEPT" else None)
            or row.get("outcome") != _outcome(row)
            or row.get("positive_prediction_correct")
            != (
                (label == row["expected_label"])
                if row["sample_kind"] == "KNOWN"
                else None
            )
            or row.get("technical_qc_decision") != "PASS"
            or row.get("decode_status") != "PASS"
            or row.get("roi_status") != "PASS"
            or row.get("segmentation_status") not in ("DETECTED", "FALLBACK")
            or type(row.get("segmentation_fallback")) is not bool
            or row.get("inference_status") != "PASS"
        ):
            raise ValueError("Decisão, threshold ou outcome divergente.")


def _counts(group: list[dict]) -> dict:
    accepted = tuple(row["decision"] == "ACCEPT" for row in group)
    return calculate_rejection_metrics(tuple(group), accepted)


def calculate_metrics(rows: list[dict], plan: dict, freeze: dict) -> dict:
    """Calcula métricas pré-registradas sem excluir queries."""
    _validate_predictions(rows, plan, freeze)
    counts = _counts(rows)
    known = [row for row in rows if row["sample_kind"] == "KNOWN"]
    unknown = [row for row in rows if row["sample_kind"] == "UNKNOWN"]
    kca, kwa, kr = (
        counts[key]
        for key in ("KNOWN_CORRECT_ACCEPT", "KNOWN_WRONG_ACCEPT", "KNOWN_REJECT")
    )
    ur, ufa = (counts[key] for key in ("UNKNOWN_REJECT", "UNKNOWN_FALSE_ACCEPT"))
    if (len(known), len(unknown), kca + kwa + kr, ur + ufa) != (36, 36, 36, 36):
        raise ValueError("Identidades de contagem KNOWN/UNKNOWN inválidas.")
    closed = sum(row["positive_prediction_correct"] for row in known)
    matrix = [[0] * 6 for _ in LABELS]
    for row in known:
        matrix[LABELS.index(row["expected_label"])][row["predicted_label_index"]] += 1
    by_class = []
    for label in LABELS:
        group = [row for row in known if row["expected_label"] == label]
        values = Counter(row["outcome"] for row in group)
        by_class.append(
            {
                "label": label,
                "label_index": LABELS.index(label),
                "total": 6,
                "closed_set_correct": sum(
                    row["positive_prediction_correct"] for row in group
                ),
                "predicted_label_counts": {
                    name: sum(row["predicted_label"] == name for row in group)
                    for name in LABELS
                },
                "KCA": values["KCA"],
                "KWA": values["KWA"],
                "KR": values["KR"],
                "KCAR": values["KCA"] / 6,
                "coverage": (values["KCA"] + values["KWA"]) / 6,
            }
        )
    by_category = []
    for category in CATEGORIES:
        group = [row for row in unknown if row["negative_category"] == category]
        false_accepts = [
            {
                "sample_id": row["sample_id"],
                "predicted_label": row["predicted_label"],
                "oov_prompt": row["oov_prompt"],
            }
            for row in group
            if row["outcome"] == "UFA"
        ]
        by_category.append(
            {
                "category": category,
                "total": 6,
                "UR": 6 - len(false_accepts),
                "UFA": len(false_accepts),
                "rejection_rate": (6 - len(false_accepts)) / 6,
                "false_accepts": false_accepts,
            }
        )
    by_session = []
    for session_id in SESSIONS:
        group = [row for row in rows if row["session_id"] == session_id]
        detail = _counts(group)
        skca = detail["KNOWN_CORRECT_ACCEPT"]
        sur = detail["UNKNOWN_REJECT"]
        by_session.append(
            {
                "session_id": session_id,
                "known_total": 12,
                "unknown_total": 12,
                "closed_set_correct": sum(
                    row["positive_prediction_correct"]
                    for row in group
                    if row["sample_kind"] == "KNOWN"
                ),
                "KCA": skca,
                "KWA": detail["KNOWN_WRONG_ACCEPT"],
                "KR": detail["KNOWN_REJECT"],
                "UR": sur,
                "UFA": detail["UNKNOWN_FALSE_ACCEPT"],
                "KCAR": skca / 12,
                "URR": sur / 12,
                "balanced": detail["rejection_balanced_score"],
                "safe_decisions": skca + sur,
                "segmentation_fallback": sum(
                    row["segmentation_fallback"] for row in group
                ),
            }
        )
    safe = kca + ur
    return {
        "labels": list(LABELS),
        "known": {
            "total": 36,
            "closed_set_correct": closed,
            "closed_set_wrong": 36 - closed,
            "closed_set_accuracy": closed / 36,
            "KCA": kca,
            "KWA": kwa,
            "KR": kr,
            "KCAR": kca / 36,
            "coverage": (kca + kwa) / 36,
            "accepted_accuracy": kca / (kca + kwa) if kca + kwa else None,
        },
        "unknown": {"total": 36, "UR": ur, "UFA": ufa, "URR": ur / 36},
        "primary_balanced_score": counts["rejection_balanced_score"],
        "safe_decision": {"correct": safe, "total": 72, "rate": safe / 72},
        "wilson_95": {
            "closed_set_accuracy": wilson_interval(closed, 36),
            "KCAR": wilson_interval(kca, 36),
            "URR": wilson_interval(ur, 36),
            "safe_decision_rate": wilson_interval(safe, 72),
        },
        "confusion_matrix": matrix,
        "known_by_class": by_class,
        "unknown_by_category": by_category,
        "oov_prompts": [
            {
                "sample_id": row["sample_id"],
                "prompt": row["oov_prompt"],
                "decision": row["decision"],
                "emitted_label": row["emitted_label"],
            }
            for row in unknown
            if row["negative_category"] == "FALA_FORA_VOCAB"
        ],
        "by_session": by_session,
        "technical": {
            "valid": 72,
            "failures": 0,
            "segmentation_fallback": sum(row["segmentation_fallback"] for row in rows),
        },
    }


def _write_attempt(path: Path, payload: dict) -> None:
    raw = serialize_result(payload)
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(raw)
        return
    pending = path.with_name(path.name + ".pending")
    with pending.open("xb") as stream:
        stream.write(raw)
    os.replace(pending, path)


def run_one_shot(prepared: dict) -> dict:
    """Processa 72 vídeos uma vez e grava apenas resultado completo."""
    root = prepared["root"]
    output = root / OUTPUT
    attempt_path = root / ATTEMPT
    ensure_one_shot(output, attempt_path)
    positive = load_frozen_positive_classifier(
        root / CHECKPOINT_RELATIVE_PATH, root / CONFIG_RELATIVE_PATH
    )
    pipeline = replace(
        load_frozen_edge_pipeline(root, root / EDGE_CONFIG, positive.templates),
        threshold=THRESHOLD,
    )
    if (
        pipeline.fingerprint != prepared["pipeline_fingerprint_sha256"]
        or pipeline.threshold != THRESHOLD
    ):
        raise ValueError("Pipeline Edge divergiu do freeze R3.5.")
    attempt_path.parent.mkdir(parents=True, exist_ok=True)
    attempt = {
        "phase": "SEMANTIC_PROCESSING_STARTED",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_commit": prepared["commit"],
        "prediction_count": 0,
        "partial_results": [],
    }
    _write_attempt(attempt_path, attempt)
    predictions = []
    try:
        sources = _plan_rows(prepared["plan"])
        ready = [
            prepare_query(source, path)
            for source, path in zip(sources, prepared["sample_paths"], strict=True)
        ]
        if len(ready) != 72:
            raise ValueError("Pré-processamento não produziu 72 queries.")
        attempt["phase"] = "INFERENCE_STARTED"
        _write_attempt(attempt_path, attempt)
        for source, sample, (query, tensor, diagnostics) in zip(
            sources, prepared["samples"], ready, strict=True
        ):
            prediction = pipeline.predict(query, tensor)
            if (
                prediction["pipeline_fingerprint_sha256"]
                != prepared["pipeline_fingerprint_sha256"]
            ):
                raise ValueError("Fingerprint divergiu durante inferência.")
            row = {
                "sample_id": source["sample_id"],
                "session_id": source["session_id"],
                "sample_kind": source["sample_kind"],
                "expected_label": source["expected_label"],
                "negative_category": source["negative_category"],
                "oov_prompt": source["oov_prompt"],
                "selected_attempt": sample["selected_attempt"],
                "relative_path": sample["relative_path"],
                "mp4_sha256": sample["sha256"],
                "technical_qc_decision": sample["technical_qc_decision"],
                "decode_status": "PASS",
                "roi_status": "PASS",
                "segmentation_status": (
                    "FALLBACK" if diagnostics["segmentation_fallback"] else "DETECTED"
                ),
                "inference_status": "PASS",
                **diagnostics,
                "predicted_label": prediction["predicted_label"],
                "predicted_label_index": prediction["predicted_label_index"],
                "positive_prediction_correct": (
                    prediction["predicted_label"] == source["expected_label"]
                    if source["sample_kind"] == "KNOWN"
                    else None
                ),
                "cos_pred": prediction["clip_class_cosine"],
                "threshold": prediction["threshold"],
                "decision": prediction["decision"],
                "emitted_label": prediction["accepted_label"],
                "logits": prediction["logits"],
                "dtw_distances": prediction["dtw_distances"],
                "clip_embedding_sha256": prediction["clip_embedding_sha256"],
            }
            row["outcome"] = _outcome(row)
            predictions.append(row)
            attempt["prediction_count"] = len(predictions)
            attempt["partial_results"] = predictions
            _write_attempt(attempt_path, attempt)
        metrics = calculate_metrics(predictions, prepared["plan"], prepared["freeze"])
        current_result_sha256 = hashlib.sha256(
            serialize_result({"per_sample": predictions, "metrics": metrics})
        ).hexdigest()
        attempt["phase"] = "CURRENT_RESULT_FROZEN"
        attempt["current_result_sha256"] = current_result_sha256
        _write_attempt(attempt_path, attempt)
        result = {
            "format_version": 1,
            "state": "REJECTION_3_CLOSED",
            "evaluation_run_count": 1,
            "heldout_consumed": True,
            "heldout_modified_after_freeze": False,
            "threshold_modified": False,
            "model_modified": False,
            "evaluation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "evaluation_commit": prepared["commit"],
            "candidate_id": CANDIDATE_ID,
            "threshold": THRESHOLD,
            "decision_operator": ">=",
            "runtime": {
                "onnxruntime": ort.__version__,
                "provider": "CPUExecutionProvider",
            },
            "provenance_sha256": prepared["provenance"],
            "artifact_sha256": prepared["artifact_hashes"],
            "pipeline_fingerprint_sha256": prepared["pipeline_fingerprint_sha256"],
            "dataset_counts": {"total": 72, "known": 36, "unknown": 36, "sessions": 3},
            "per_sample": predictions,
            "metrics": metrics,
            "current_result_sha256_before_historical_comparison": current_result_sha256,
            "capture_context": {
                "session_01": "ETEC / parede azul",
                "session_02": (
                    "Início na ETEC; attempts válidos finais e retomada em "
                    "casa / parede branca, conforme auditoria"
                ),
                "session_03": "Casa / parede branca",
                "causal_claim": False,
            },
            "historical_comparison": {
                "source": (
                    "aggregates históricos pré-documentados; "
                    "nenhum held-out antigo aberto"
                ),
                "cycle_06_closed_set_correct": 35,
                "cycle_06_KCA": 17,
                "cycle_06_KWA": 0,
                "cycle_06_KR": 19,
                "cycle_06_UR": 36,
                "cycle_06_UFA": 0,
                "cycle_06_balanced_reported": 0.6415,
                "cycle_06_safe_decisions": 53,
                "r3_3_nested_development_balanced_reported": 0.8788,
                "r3_4_calibration_fit_balanced_reported": 0.9344,
                "calibration_fit_is_generalization": False,
            },
            "old_heldouts_opened": False,
            "post_heldout_tuning": False,
        }
        pending = output.with_name(output.name + ".pending")
        with pending.open("xb") as stream:
            stream.write(serialize_result(result))
        os.rename(pending, output)
        attempt["phase"] = "COMPLETED"
        attempt["result_sha256"] = sha256_file(output)
        _write_attempt(attempt_path, attempt)
        return result
    except Exception as error:
        attempt["phase"] = "FAILED_AFTER_SEMANTIC_PROCESSING_STARTED"
        attempt["error_type"] = type(error).__name__
        attempt["error_message"] = str(error)
        attempt["prediction_count"] = len(predictions)
        attempt["partial_results"] = predictions
        _write_attempt(attempt_path, attempt)
        raise


def post_run_audit(root: Path) -> dict:
    """Reconfere resultado persistido sem executar nova inferência."""
    root = Path(root).resolve()
    output = root / OUTPUT
    attempt_path = root / ATTEMPT
    if not output.is_file() or not attempt_path.is_file():
        raise FileNotFoundError("Avaliação final R3 incompleta.")
    result = json.loads(output.read_text(encoding="utf-8"))
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    plan = json.loads((root / PLAN).read_text(encoding="utf-8"))
    freeze = json.loads((root / FREEZE).read_text(encoding="utf-8"))
    if (
        result.get("state") != "REJECTION_3_CLOSED"
        or result.get("evaluation_run_count") != 1
        or result.get("heldout_consumed") is not True
        or attempt.get("phase") != "COMPLETED"
        or attempt.get("prediction_count") != 72
        or attempt.get("result_sha256") != sha256_file(output)
    ):
        raise ValueError("Auditoria de execução única inválida.")
    if calculate_metrics(result["per_sample"], plan, freeze) != result["metrics"]:
        raise ValueError("Métricas persistidas divergem das previsões.")
    current_digest = hashlib.sha256(
        serialize_result(
            {"per_sample": result["per_sample"], "metrics": result["metrics"]}
        )
    ).hexdigest()
    if (
        attempt.get("current_result_sha256") != current_digest
        or result.get("current_result_sha256_before_historical_comparison")
        != current_digest
    ):
        raise ValueError("Resultado atual não foi congelado antes da comparação.")
    return {
        "result_sha256": sha256_file(output),
        "sample_count": 72,
        "evaluation_run_count": 1,
    }
