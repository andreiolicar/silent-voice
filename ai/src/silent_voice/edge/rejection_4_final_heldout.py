"""Protocolo R4 final: preflight sem modelos e avaliação explicitamente única."""

import hashlib
import json
import math
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.evaluation.qc_rejection_4_heldout import (
    NO_INFERENCE,
    _fingerprint,
    _safe_path,
)
from silent_voice.rejection.rejection_4_heldout_plan import (
    FROZEN_POLICY,
    KNOWN_LABELS,
    PLAN_SHA256,
    SESSION_IDS,
    UNKNOWN_CATEGORIES,
    assert_capture_path,
    validate_capture_plan,
)
from silent_voice.rejection.rejection_metrics import calculate_rejection_metrics


LABELS = KNOWN_LABELS
CATEGORIES = UNKNOWN_CATEGORIES
SESSIONS = SESSION_IDS
CANDIDATE = FROZEN_POLICY["candidate"]
K = FROZEN_POLICY["k"]
THRESHOLD = FROZEN_POLICY["threshold"]
INPUT_STATE = "REJECTION_4_HELDOUT_DATASET_FROZEN"
PROTOCOL_STATE = "REJECTION_4_FINAL_HELDOUT_PROTOCOL_FROZEN"
DATASET_FINGERPRINT = "e43b8420374527f01ec4cc1af01aa68c8222e47d7c803523e790e4465ac584d7"
PIPELINE_FINGERPRINT = (
    "e8394f470520f61d096bc0f1a4f5997f5ae5692af412707c4905519ae602c48b"
)
STARTING_COMMIT = "8e4b3789b9f91325e89f0eef29e4db89bc146df7"
PLAN = Path("docs/cycles/rejection_4_heldout_capture_plan.json")
FREEZE = Path("docs/cycles/rejection_4_heldout_freeze.json")
PROTOCOL_PATH = Path("docs/cycles/rejection_4_final_heldout_protocol.md")
OUTPUT = Path("data/processed/evaluation/rejection_4_final_heldout_evaluation.json")
ATTEMPT = Path("data/processed/evaluation/rejection_4_final_heldout_attempt.json")
PREFLIGHT_PATH = Path(
    "data/processed/evaluation/rejection_4_final_heldout_preflight.json"
)
EVENTS = ATTEMPT.with_suffix(".events.jsonl")
VERSIONED_FILES = (
    Path("src/silent_voice/edge/rejection_4_final_heldout.py"),
    Path("scripts/evaluation/evaluate_rejection_4_final_heldout.py"),
    Path("tests/unit/edge/test_rejection_4_final_heldout.py"),
    PROTOCOL_PATH,
    Path("AGENTS.md"),
)
PROVENANCE = {
    "plan": (PLAN, PLAN_SHA256),
    "heldout_freeze": (
        FREEZE,
        "1afa885323c28387f30f6d5057771193de43d89aa8f6a0175e3b8e595b7b137a",
    ),
    "capture_manifest": (
        Path("data/processed/evaluation/rejection_4_heldout_capture_manifest.json"),
        "91a52aae51c6d79500526bce25ecdb7b74228001a6fe5875ab0f8a2afd43a806",
    ),
    "qc_json": (
        Path("data/processed/evaluation/rejection_4_heldout_qc.json"),
        "e2fb18b6d88f48e09f2b932eabb6307ed57899095a1f93d747a73417f6fc839b",
    ),
    "reference_freeze": (
        Path("docs/cycles/rejection_4_reference_freeze.json"),
        "79015c1b7f39ae64027a1a69253ba0411cdb8351a339d0a687d0ec4e75714a3c",
    ),
    "reference_bank": (
        Path("data/processed/models/rejection_4/rejection_4_top3_reference_bank.npz"),
        "e0fefb568ee3f689c75354cd1c75696d7cef91e215bd7cb3a99039ecf092a34c",
    ),
    "reference_bank_manifest": (
        Path("docs/cycles/rejection_4_reference_bank_manifest.json"),
        "9d1ea4aa1ad869a6dc9076ecbbd9f81510b262c5c293600d54a84908a47456b5",
    ),
    "edge_scorer": (
        Path("data/processed/models/rejection_4/rejection_4_top3_policy.onnx"),
        "28b214850ce53fdcb7170c0fab52620cf8a6c97c2be712092686658b81d5169f",
    ),
    "edge_manifest": (
        Path("docs/cycles/rejection_4_edge_policy_manifest.json"),
        "cf10de54fb136d79287863950de3e69dc4ef20442ace7e9d2f8f8716c39c9cd4",
    ),
    "edge_freeze": (
        Path("docs/cycles/rejection_4_edge_policy_freeze.json"),
        "cf9c2976698e515c468567961783aad885dcafba86ec0cbcebaa49c71c6df4e9",
    ),
    "encoder": (
        Path("data/processed/models/edge/cycle_06_swinlip_clip_encoder_fp16.onnx"),
        "ff81172639263a6a74975e7147d63e62af944b947e48f53fba6980af732c91a7",
    ),
    "head": (
        Path("data/processed/models/edge/cycle_06_positive_head_fp32.onnx"),
        "eb299d65e4f2b9a15108f79b8044355068911d2180161d46806a9c0269fa9261",
    ),
    "positive_checkpoint": (
        Path("data/processed/models/cycle_06_hybrid_positive_classifier.pt"),
        "33a0d1f1f564dc75f83ebc08fc2dca255840da60ca40a9c41fdd36d4ad0cc6a2",
    ),
    "positive_config": (
        Path(
            "data/processed/evaluation/cycle_06_positive_classifier_final_config.json"
        ),
        "29b7df189ac8f3b5b01ce2b5b5b03870dd37b678ccb6f6f536e8ac9debaa7a1e",
    ),
    "edge_config": (
        Path("data/processed/evaluation/cycle_06_edge_preheldout_final_config.json"),
        "a761de851e7dc22ed8974dbd3dc98e23963d384057488bdfe9aae0ef406eb4d4",
    ),
    "edge_centroids": (
        Path(
            "data/processed/models/edge/cycle_06_onnx_fp16_rejection_clip_centroids.npz"
        ),
        "d7cece625425d09cb313830e0491121b42d116f409bd400bf9c18f7ea53e0a61",
    ),
    "edge_origin_manifest": (
        Path("data/processed/evaluation/cycle_06_preheldout_freeze_manifest.json"),
        "41cf1f308a1c153bfc0f533c70676309139d63531cce9ce31363c74643e611bd",
    ),
}
AUTHORIZED_ARTIFACTS = frozenset(record[0] for record in PROVENANCE.values())


def serialize_result(payload: dict) -> bytes:
    """JSON UTF-8 canônico, finito, sem dependência de CRLF."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read(root: Path, relative: Path) -> dict:
    return json.loads(_safe_path(root, relative).read_bytes())


def verify_provenance(root: Path, records=None) -> dict:
    """Somente artefatos nomeados; nunca procura datasets/held-outs antigos."""
    actual = {}
    for name, (relative, expected) in (
        PROVENANCE if records is None else records
    ).items():
        if Path(relative) not in AUTHORIZED_ARTIFACTS:
            raise ValueError(f"Path não autorizado: {name}")
        path = _safe_path(root, relative)
        if not path.is_file() or _sha(path) != expected:
            raise ValueError(f"SHA-256 divergente: {name}")
        actual[name] = expected
    return actual


def decision_for_score(score: float) -> str:
    if type(score) not in (int, float) or not math.isfinite(score):
        raise ValueError("Score deve ser numérico e finito.")
    return "ACCEPT" if score >= THRESHOLD else "REJECT"


def validate_policy(edge: dict) -> None:
    expected = {
        "state": "REJECTION_4_EDGE_POLICY_FROZEN",
        "candidate_id": CANDIDATE,
        "k": K,
        "threshold": THRESHOLD,
        "operator": ">=",
        "labels": list(LABELS),
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
        "provider": "CPUExecutionProvider",
        "runtime": "1.30.0",
    }
    if (
        any(edge.get(key) != value for key, value in expected.items())
        or type(edge.get("k")) is not int
        or type(edge.get("threshold")) is not float
    ):
        raise ValueError("Política Edge não corresponde à R4 congelada.")


def validate_selected_samples(plan: dict, freeze: dict) -> tuple[dict, ...]:
    """Valida identidade, ground truth, tentativas e fingerprint sem decodificar."""
    validate_capture_plan(plan)
    expected = {
        "state": INPUT_STATE,
        "format_version": 1,
        "scientific_scope": "SAME_SPEAKER_NEW_SESSION",
        "qc_result": "PASS",
        "logical_sample_count": 72,
        "known_labels": list(LABELS),
        "unknown_categories": list(CATEGORIES),
        "session_ids": list(SESSIONS),
        "session_counts": dict.fromkeys(SESSIONS, 24),
        "type_counts": {"KNOWN": 36, "UNKNOWN": 36},
        "known_class_counts": dict.fromkeys(LABELS, 6),
        "unknown_category_counts": dict.fromkeys(CATEGORIES, 6),
        "selected_oov_prompts": plan["selected_oov_prompts"],
        "recapture_audit": [],
        **NO_INFERENCE,
    }
    if any(
        freeze.get(key) != value or type(freeze.get(key)) is not type(value)
        for key, value in expected.items()
    ):
        raise ValueError("Estado/contagens do freeze held-out não autorizam avaliação.")
    samples = freeze.get("samples", [])
    if (
        len(samples) != 72
        or len({item.get("sample_id") for item in samples}) != 72
        or len({item.get("relative_path") for item in samples}) != 72
    ):
        raise ValueError("Inventário deve conter exatamente 72 records únicos.")
    sources = [row for session in plan["sessions"] for row in session["schedule"]]
    for sample, source in zip(samples, sources, strict=True):
        assert_capture_path(sample["relative_path"])
        if (
            any(
                sample.get(key) != source[key]
                for key in (
                    "sample_id",
                    "session_id",
                    "sample_kind",
                    "expected_label",
                    "negative_category",
                    "oov_prompt",
                    "repetition_index",
                    "prompt_or_action",
                )
            )
            or sample.get("trial_order") != source["order"]
            or sample["relative_path"] != source["raw_video_path"]
            or type(sample.get("selected_attempt")) is not int
            or sample["selected_attempt"] != 1
            or sample.get("technical_qc_decision") != "PASS"
            or sample.get("technical_qc_reasons") != []
            or type(sample.get("byte_size")) is not int
            or sample["byte_size"] <= 0
            or not isinstance(sample.get("sha256"), str)
            or len(sample["sha256"]) != 64
        ):
            raise ValueError("Sample não pareado ao plano/QC congelado.")
    if freeze.get("dataset_fingerprint") != _fingerprint(samples):
        raise ValueError("Dataset fingerprint inconsistente.")
    return tuple(samples)


def verify_selected_file(root: Path, sample: dict) -> Path:
    assert_capture_path(sample["relative_path"])
    path = _safe_path(root, sample["relative_path"])
    if (
        not path.is_file()
        or path.stat().st_size != sample["byte_size"]
        or _sha(path) != sample["sha256"]
    ):
        raise ValueError(f"Bytes/SHA do MP4 divergem: {sample['sample_id']}")
    return path


def _git_state(root: Path) -> tuple[str, str]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True)
    status = subprocess.check_output(["git", "status", "--short"], cwd=root, text=True)
    return commit.strip(), status.rstrip()


def _ensure_unconsumed(root: Path) -> None:
    for relative in (
        OUTPUT,
        ATTEMPT,
        EVENTS,
        OUTPUT.with_name(OUTPUT.name + ".pending"),
        ATTEMPT.with_name(ATTEMPT.name + ".pending"),
    ):
        if _safe_path(root, relative).exists():
            raise FileExistsError(
                f"Avaliação/tentativa/evidência anterior existe: {relative}"
            )


def _validate_positive_config(
    root: Path, config: dict, *, implementation_root: Path | None = None
) -> dict:
    # Estes helpers validam bytes/metadados; não carregam pesos ou sessões ONNX.
    from silent_voice.edge.cycle_06_final_heldout import _frozen_implementation_hashes
    from silent_voice.edge.preheldout_freeze import (
        validate_edge_config,
        validate_freeze_manifest,
    )

    validate_edge_config(root, config)
    validate_freeze_manifest(
        root, _read(root, PROVENANCE["edge_origin_manifest"][0]), config
    )
    if config["pipeline_fingerprint_sha256"] != PIPELINE_FINGERPRINT:
        raise ValueError("Pipeline positivo divergente.")
    for section, name in (("encoder", "encoder"), ("classifier", "head")):
        if (
            config[section]["path"] != PROVENANCE[name][0].as_posix()
            or config[section]["sha256"] != PROVENANCE[name][1]
        ):
            raise ValueError("Artefato positivo substituído.")
    if implementation_root is None:
        return _frozen_implementation_hashes(root, config)
    return _frozen_implementation_hashes(
        root, config, implementation_root=implementation_root
    )


def _validate_state_document(root: Path, execution: bool = False) -> None:
    text = _safe_path(root, "AGENTS.md").read_text(encoding="utf-8")
    tokens = ("REJECTION_3_CLOSED", "LIVE_VISUAL_TESTER_V1_READY")
    if any(token not in text for token in tokens):
        raise ValueError("R3/Live Tester não correspondem ao checkpoint obrigatório.")
    if execution:
        if f"R4.8A `CLOSED` / `PASS`: estado `{PROTOCOL_STATE}`" not in text:
            raise ValueError("Protocolo R4.8A ainda não congelado para inferência.")
    elif INPUT_STATE not in text and PROTOCOL_STATE not in text:
        raise ValueError("Estado de entrada R4 divergente.")


def preflight(root: Path, require_clean_worktree: bool = True) -> dict:
    """Valida bytes/contratos; zero modelos, ROI, queries ou scores."""
    root = Path(root).resolve()
    _ensure_unconsumed(root)
    commit, status = _git_state(root)
    if require_clean_worktree and status:
        raise ValueError("Worktree versionável deve estar limpo.")
    if not require_clean_worktree and any(
        line[3:].strip('"') not in {path.as_posix() for path in VERSIONED_FILES}
        for line in status.splitlines()
    ):
        raise ValueError("Worktree contém mudanças fora da R4.8A.")
    _validate_state_document(root)
    provenance = verify_provenance(root)
    plan, freeze = _read(root, PLAN), _read(root, FREEZE)
    samples = validate_selected_samples(plan, freeze)
    if freeze["dataset_fingerprint"] != DATASET_FINGERPRINT:
        raise ValueError("Fingerprint não corresponde ao held-out R4.7B.")
    for field, name in (
        ("capture_plan_sha256", "plan"),
        ("capture_manifest_sha256", "capture_manifest"),
        ("qc_json_sha256", "qc_json"),
        ("source_edge_freeze_sha256", "edge_freeze"),
    ):
        if freeze.get(field) != provenance[name]:
            raise ValueError(f"Freeze/proveniência divergente: {field}")
    edge = _read(root, PROVENANCE["edge_freeze"][0])
    validate_policy(edge)
    implementation = _validate_positive_config(
        root, _read(root, PROVENANCE["edge_config"][0])
    )
    paths = tuple(verify_selected_file(root, item) for item in samples)
    return {
        "root": root,
        "commit": commit,
        "worktree_clean": not bool(status),
        "worktree_status": status,
        "plan": plan,
        "freeze": freeze,
        "samples": samples,
        "sample_paths": paths,
        "sample_count": 72,
        "hashes_valid": 72,
        "provenance": provenance,
        "artifact_hashes": {
            name: value
            for name, value in provenance.items()
            if name
            in (
                "encoder",
                "head",
                "edge_scorer",
                "positive_checkpoint",
                "positive_config",
                "reference_bank",
            )
        },
        "implementation_hashes": implementation,
        "heldout_freeze_sha256": provenance["heldout_freeze"],
        "edge_freeze_sha256": provenance["edge_freeze"],
        "dataset_fingerprint": freeze["dataset_fingerprint"],
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
        "input_state": INPUT_STATE,
        "heldout_status": "UNEVALUATED",
        "evaluation_run_count": 0,
        "queries_executed": 0,
        "evaluator_source_sha256": {
            relative.as_posix(): hashlib.sha256(
                _safe_path(root, relative).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
            for relative in VERSIONED_FILES
            if _safe_path(root, relative).is_file()
        },
        **NO_INFERENCE,
    }


def preflight_report(prepared: dict) -> dict:
    """Extrai somente fatos de preflight serializáveis, sem previsão/accuracy."""
    return {
        key: value
        for key, value in prepared.items()
        if key not in ("root", "plan", "freeze", "samples", "sample_paths")
    }


def _outcome(row: dict) -> str:
    if row["sample_kind"] == "UNKNOWN":
        return "UR" if row["decision"] == "REJECT" else "UFA"
    if row["decision"] == "REJECT":
        return "KR"
    return "KCA" if row["predicted_label"] == row["expected_label"] else "KWA"


def _validate_predictions(rows: list[dict], plan: dict, freeze: dict) -> None:
    samples = validate_selected_samples(plan, freeze)
    if len(rows) != 72:
        raise ValueError("Resultado deve conter 72 queries, sem excluir falhas.")
    for row, sample in zip(rows, samples, strict=True):
        identity = (
            "sample_id",
            "session_id",
            "sample_kind",
            "expected_label",
            "negative_category",
            "oov_prompt",
            "relative_path",
            "selected_attempt",
        )
        if any(row.get(key) != sample[key] for key in identity):
            raise ValueError("Previsão não pareada ao freeze.")
        label = row.get("predicted_label")
        if (
            row.get("mp4_sha256") != sample["sha256"]
            or label not in LABELS
            or type(row.get("predicted_label_index")) is not int
            or row["predicted_label_index"] != LABELS.index(label)
            or type(row.get("threshold")) is not float
            or row["threshold"] != THRESHOLD
            or row.get("decision") != decision_for_score(row.get("score"))
            or row.get("outcome") != _outcome(row)
            or row.get("emitted_label")
            != (label if row["decision"] == "ACCEPT" else None)
            or row.get("positive_prediction_correct")
            != (
                label == row["expected_label"]
                if row["sample_kind"] == "KNOWN"
                else None
            )
            or any(
                row.get(key) != "PASS"
                for key in (
                    "technical_qc_decision",
                    "decode_status",
                    "roi_status",
                    "inference_status",
                )
            )
            or row.get("segmentation_status") not in ("DETECTED", "FALLBACK")
            or type(row.get("segmentation_fallback")) is not bool
            or row["segmentation_fallback"]
            != (row["segmentation_status"] == "FALLBACK")
        ):
            raise ValueError("Contrato técnico/decisão individual divergente.")


def calculate_metrics(rows: list[dict], plan: dict, freeze: dict) -> dict:
    """Métricas pré-registradas, reutilizando o cálculo comum de rejection."""
    _validate_predictions(rows, plan, freeze)
    values = calculate_rejection_metrics(
        tuple(rows), tuple(row["decision"] == "ACCEPT" for row in rows)
    )
    kca, kwa, kr, ur, ufa = (
        values[key]
        for key in (
            "KNOWN_CORRECT_ACCEPT",
            "KNOWN_WRONG_ACCEPT",
            "KNOWN_REJECT",
            "UNKNOWN_REJECT",
            "UNKNOWN_FALSE_ACCEPT",
        )
    )
    if kca + kwa + kr != 36 or ur + ufa != 36:
        raise ValueError("Partição KNOWN/UNKNOWN inválida.")
    by_class, by_category, by_prompt = [], [], []
    for index, label in enumerate(LABELS):
        group = [row for row in rows if row["expected_label"] == label]
        counts = Counter(row["outcome"] for row in group)
        by_class.append(
            {
                "label": label,
                "label_index": index,
                "count": len(group),
                "closed_set_correct": sum(
                    row["positive_prediction_correct"] for row in group
                ),
                **{name: counts[name] for name in ("KCA", "KWA", "KR")},
            }
        )
    for category in CATEGORIES:
        group = [row for row in rows if row["negative_category"] == category]
        counts = Counter(row["outcome"] for row in group)
        by_category.append(
            {
                "category": category,
                "count": len(group),
                "UR": counts["UR"],
                "UFA": counts["UFA"],
            }
        )
    for prompt in plan["selected_oov_prompts"]:
        group = [row for row in rows if row["oov_prompt"] == prompt]
        counts = Counter(row["outcome"] for row in group)
        by_prompt.append(
            {
                "prompt": prompt["prompt_display"],
                "session_id": prompt["session_id"],
                "count": len(group),
                "UR": counts["UR"],
                "UFA": counts["UFA"],
            }
        )
    return {
        "labels": list(LABELS),
        "known": {
            "count": 36,
            "closed_set_correct": sum(
                row["positive_prediction_correct"]
                for row in rows
                if row["sample_kind"] == "KNOWN"
            ),
            "closed_set_accuracy": values["known_closed_set_accuracy"],
            "KCA": kca,
            "KWA": kwa,
            "KR": kr,
            "KCAR": values["known_correct_accept_rate"],
            "coverage": values["known_coverage"],
            "accepted_accuracy": kca / (kca + kwa) if kca + kwa else None,
        },
        "unknown": {
            "count": 36,
            "UR": ur,
            "UFA": ufa,
            "URR": values["unknown_rejection_rate"],
        },
        "primary_balanced_score": values["rejection_balanced_score"],
        "safe_decision_accuracy": (kca + ur) / 72,
        "by_known_class": by_class,
        "by_unknown_category": by_category,
        "by_oov_prompt": by_prompt,
    }


def _validate_execution_context(prepared: dict) -> None:
    root = prepared["root"]
    commit, status = _git_state(root)
    if status or commit != prepared["commit"]:
        raise ValueError("Código mudou ou worktree não está limpo após preflight.")
    _validate_state_document(root, execution=True)
    message = subprocess.check_output(
        ["git", "log", "-1", "--format=%s"], cwd=root, text=True
    ).strip()
    if message != "feat: congela avaliacao final do rejection 4":
        raise ValueError("HEAD não é o checkpoint pré-avaliação autorizado da R4.8A.")
    for relative in VERSIONED_FILES:
        committed = subprocess.check_output(
            ["git", "show", f"{commit}:{relative.as_posix()}"], cwd=root
        )
        # Git pode normalizar CRLF; compara o conteúdo versionável.
        if committed.replace(b"\r\n", b"\n") != _safe_path(
            root, relative
        ).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("Evaluator/protocolo/teste não corresponde ao commit.")
    if verify_provenance(root) != prepared["provenance"]:
        raise ValueError("Proveniência mudou após preflight.")
    config = _read(root, PROVENANCE["edge_config"][0])
    if _validate_positive_config(root, config) != prepared["implementation_hashes"]:
        raise ValueError("Implementação positiva mudou após preflight.")


def _write_once(path: Path, payload: dict) -> None:
    with path.open("xb") as stream:
        stream.write(serialize_result(payload))
        stream.flush()
        os.fsync(stream.fileno())


def _update_marker(path: Path, marker: dict) -> None:
    pending = path.with_name(path.name + ".pending")
    _write_once(pending, marker)
    os.replace(pending, path)


def _load_runtime(prepared: dict):
    """Carregamento exclusivo da execução futura, após reservar o marker."""
    import onnxruntime as ort

    from silent_voice.edge.preheldout_freeze import _ort_session
    from silent_voice.vision.positive_classifier_final import (
        load_frozen_positive_classifier,
    )

    if ort.__version__ != "1.30.0":
        raise ValueError("Runtime deve ser ONNX Runtime 1.30.0 CPU.")
    root = prepared["root"]
    positive = load_frozen_positive_classifier(
        root / PROVENANCE["positive_checkpoint"][0],
        root / PROVENANCE["positive_config"][0],
    )
    sessions = tuple(
        _ort_session(root / PROVENANCE[name][0])
        for name in ("encoder", "head", "edge_scorer")
    )
    for session, inputs, outputs in zip(
        sessions,
        (
            (("roi_input", [1, 1, 29, 88, 88], "tensor(float)"),),
            (("hybrid_features", [1, 1670], "tensor(float)"),),
            (
                ("clip_embedding", [1, 1664], "tensor(float)"),
                ("predicted_label_index", [1], "tensor(int64)"),
            ),
        ),
        (("clip_embedding", [1, 1664]), ("logits", [1, 6]), ("top3_pred_score", [1])),
        strict=True,
    ):
        if (
            [(item.name, item.shape, item.type) for item in session.get_inputs()]
            != list(inputs)
            or [(item.name, item.shape) for item in session.get_outputs()] != [outputs]
            or session.get_providers() != ["CPUExecutionProvider"]
        ):
            raise ValueError("Contrato ONNX divergiu dos artefatos congelados.")
    metadata = sessions[2].get_modelmeta().custom_metadata_map
    for key, value in {
        "candidate_id": CANDIDATE,
        "k": "3",
        "labels": "|".join(LABELS),
        "bank_sha256": PROVENANCE["reference_bank"][1],
        "reference_freeze_sha256": PROVENANCE["reference_freeze"][1],
    }.items():
        if metadata.get(key) != value:
            raise ValueError("Metadados do scorer R4 divergentes.")
    return _R4Runtime(*sessions, positive.templates)


class _R4Runtime:
    """Somente encoder/head positivos e scorer ONNX R4, sem scorer alternativo."""

    def __init__(self, encoder, head, scorer, templates):
        self.encoder, self.head, self.scorer = encoder, head, scorer
        self.templates = templates

    def predict(self, sample: dict, path: Path) -> dict:
        import numpy as np

        from silent_voice.edge.cycle_06_final_heldout import prepare_query
        from silent_voice.edge.preheldout_freeze import validate_edge_embedding
        from silent_voice.vision.hybrid_features import (
            class_minimum_dtw_distances,
            equal_energy_fusion,
            normalized_reciprocal_evidence,
        )
        from silent_voice.vision.positive_classifier_final import clip_embedding_sha256

        query, tensor, diagnostics = prepare_query(sample, path)
        output = self.encoder.run(None, {"roi_input": tensor})
        if len(output) != 1 or np.asarray(output[0]).shape != (1, 1664):
            raise ValueError("Saída do encoder ONNX inválida.")
        clip = validate_edge_embedding(np.asarray(output[0])[0])
        distances = class_minimum_dtw_distances(query, self.templates)
        feature = equal_energy_fusion(
            clip, normalized_reciprocal_evidence(distances), 1670
        )
        output = self.head.run(None, {"hybrid_features": feature[None, :]})
        if (
            len(output) != 1
            or np.asarray(output[0]).shape != (1, 6)
            or not np.isfinite(output[0]).all()
        ):
            raise ValueError("Logits ONNX inválidos.")
        index = int(np.argmax(output[0][0]))
        output = self.scorer.run(
            None,
            {
                "clip_embedding": clip[None, :],
                "predicted_label_index": np.array([index], dtype=np.int64),
            },
        )
        if len(output) != 1 or np.asarray(output[0]).shape != (1,):
            raise ValueError("Saída do scorer R4 ONNX inválida.")
        score = float(output[0][0])
        decision_for_score(score)
        return {
            "predicted_label": LABELS[index],
            "predicted_label_index": index,
            "score": score,
            "decode_status": "PASS",
            "roi_status": "PASS",
            "inference_status": "PASS",
            "segmentation_status": (
                "FALLBACK" if diagnostics["segmentation_fallback"] else "DETECTED"
            ),
            **diagnostics,
            "dtw_distances": distances.tolist(),
            "clip_embedding_sha256": clip_embedding_sha256(clip),
        }


def run_one_shot(prepared: dict) -> dict:
    """Avaliação futura: reserva exclusiva antes de modelos, preserva interrupções."""
    root = prepared["root"]
    _ensure_unconsumed(root)
    _validate_execution_context(prepared)
    samples = validate_selected_samples(prepared["plan"], prepared["freeze"])
    if list(samples) != list(prepared["samples"]):
        raise ValueError("Prepared não corresponde ao freeze.")
    paths = tuple(verify_selected_file(root, sample) for sample in samples)
    if list(paths) != list(prepared["sample_paths"]):
        raise ValueError("Paths preparados divergentes.")
    marker_path, output_path, events_path = (
        _safe_path(root, relative) for relative in (ATTEMPT, OUTPUT, EVENTS)
    )
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "state": "CREATED",
        "evaluation_run_count": 1,
        "queries_executed": 0,
        "dataset_fingerprint": prepared["dataset_fingerprint"],
        "heldout_freeze_sha256": prepared["heldout_freeze_sha256"],
        "evaluator_commit_sha256": prepared["commit"],
        "protocol_commit_sha256": prepared["commit"],
        "edge_freeze_sha256": prepared["edge_freeze_sha256"],
        "pipeline_fingerprint_sha256": prepared["pipeline_fingerprint_sha256"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "partial_results": [],
    }
    _write_once(marker_path, marker)
    predictions = []
    try:
        with events_path.open("xb") as events:
            runtime = _load_runtime(prepared)
            for sample, path in zip(samples, paths, strict=True):
                # Revalida bytes imediatamente antes de consumir cada consulta.
                verify_selected_file(root, sample)
                prediction = runtime.predict(sample, path)
                label = prediction["predicted_label"]
                row = {
                    **sample,
                    **prediction,
                    "mp4_sha256": sample["sha256"],
                    "threshold": THRESHOLD,
                    "decision": decision_for_score(prediction["score"]),
                }
                row["emitted_label"] = label if row["decision"] == "ACCEPT" else None
                row["positive_prediction_correct"] = (
                    label == sample["expected_label"]
                    if sample["sample_kind"] == "KNOWN"
                    else None
                )
                row["outcome"] = _outcome(row)
                predictions.append(row)
                events.write(serialize_result(row) + b"\n")
                events.flush()
                os.fsync(events.fileno())
                marker.update(
                    state="INFERENCE_STARTED",
                    queries_executed=len(predictions),
                    partial_results=predictions,
                )
                _update_marker(marker_path, marker)
        metrics = calculate_metrics(predictions, prepared["plan"], prepared["freeze"])
        result = {
            "format_version": 1,
            "state": "REJECTION_4_HELDOUT_EVALUATED",
            "heldout_evaluated": True,
            "evaluation_run_count": 1,
            "evaluation_commit": prepared["commit"],
            "candidate_id": CANDIDATE,
            "k": K,
            "threshold": THRESHOLD,
            "operator": ">=",
            "dataset_fingerprint": prepared["dataset_fingerprint"],
            "heldout_freeze_sha256": prepared["heldout_freeze_sha256"],
            "edge_freeze_sha256": prepared["edge_freeze_sha256"],
            "pipeline_fingerprint_sha256": prepared["pipeline_fingerprint_sha256"],
            "provenance_sha256": prepared["provenance"],
            "artifact_sha256": prepared["artifact_hashes"],
            "per_sample": predictions,
            "metrics": metrics,
            "post_heldout_tuning": False,
            "old_heldouts_opened": False,
            "live_tester_updated_to_r4": False,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        pending = output_path.with_name(output_path.name + ".pending")
        _write_once(pending, result)
        # NTFS hard link: promove bytes completos sem poder substituir um resultado.
        os.link(pending, output_path)
        pending.unlink()
        marker.update(state="COMPLETED", result_sha256=_sha(output_path))
        _update_marker(marker_path, marker)
        return result
    except BaseException as error:
        marker.update(
            state="INTERRUPTED_REQUIRES_REVIEW",
            error_type=type(error).__name__,
            error_message=str(error),
            queries_executed=len(predictions),
            partial_results=predictions,
        )
        _update_marker(marker_path, marker)
        raise
