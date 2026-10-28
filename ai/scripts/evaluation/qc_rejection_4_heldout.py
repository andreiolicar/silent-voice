"""QC físico do held-out R4.7B; nenhum modelo ou conteúdo semântico."""

import argparse
import hashlib
import json
import math
import os
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from scripts.dataset.qc_cycle_06_new_heldout import inspect_video, sha256_file
from scripts.evaluation.qc_rejection_3_heldout import evaluate_video_metadata
from silent_voice.rejection.rejection_4_heldout_plan import (
    EDGE_FREEZE_PATH,
    EDGE_FREEZE_SHA256,
    KNOWN_LABELS,
    MANIFEST_PATH,
    PLAN_PATH,
    PLAN_SHA256,
    RAW_ROOT,
    RECAPTURE_REASONS,
    REFERENCE_FREEZE_PATH,
    REFERENCE_FREEZE_SHA256,
    SCIENTIFIC_STATUS,
    SESSION_IDS,
    UNKNOWN_CATEGORIES,
    assert_capture_path,
    load_capture_plan,
    validate_capture_plan,
)


ROOT = Path(__file__).resolve().parents[2]
RESULT_PATH = Path("data/processed/evaluation/rejection_4_heldout_qc.json")
FREEZE_PATH = Path("docs/cycles/rejection_4_heldout_freeze.json")
RESULTS_DOC_PATH = Path("docs/cycles/rejection_4_heldout_qc_results.md")
SESSION_QC_ROOT = Path("data/processed/evaluation/rejection_4_heldout_qc_sessions")
PLAN_COMMIT = "e849c1d5efbd4235220504a0806b708c58ded583"
EXPECTED_PROVENANCE = {
    PLAN_PATH.as_posix(): PLAN_SHA256,
    REFERENCE_FREEZE_PATH.as_posix(): REFERENCE_FREEZE_SHA256,
    EDGE_FREEZE_PATH.as_posix(): EDGE_FREEZE_SHA256,
    "docs/cycles/rejection_4_edge_policy_manifest.json": (
        "cf10de54fb136d79287863950de3e69dc4ef20442ace7e9d2f8f8716c39c9cd4"
    ),
    "data/processed/models/rejection_4/rejection_4_top3_policy.onnx": (
        "28b214850ce53fdcb7170c0fab52620cf8a6c97c2be712092686658b81d5169f"
    ),
}
NO_INFERENCE = {
    "models_loaded": False,
    "model_inference_performed": False,
    "embeddings_computed": False,
    "scores_computed": False,
    "predictions_computed": False,
    "old_heldouts_opened": False,
    "live_tester_updated_to_r4": False,
    "heldout_evaluated": False,
    "heldout_evaluation_count": 0,
}


def canonical_bytes(value: dict) -> bytes:
    """JSON canônico de uma linha, independente de core.autocrlf."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: dict) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Timestamp UTC inválido no manifesto.") from error
    if result.utcoffset() != timedelta(0):
        raise ValueError("Timestamp deve registrar UTC com fuso explícito.")
    return result


def _safe_path(root: Path, relative: str | Path) -> Path:
    """Recusa traversal e redirecionamentos antes de abrir qualquer arquivo."""
    parts = str(relative).replace("\\", "/").split("/")
    if any(part in ("", ".", "..") or ":" in part for part in parts):
        raise ValueError("Path relativo inválido.")
    current = Path(root).resolve()
    for part in parts:
        current = current / part
        if current.is_symlink() or current.is_junction():
            raise ValueError("Symlink/junction em path R4 não permitido.")
    return current


def validate_provenance(root: Path) -> dict:
    """Somente bytes e documentos; o scorer não é carregado como modelo."""
    load_capture_plan(_safe_path(root, PLAN_PATH))
    actual = {}
    for relative, expected in EXPECTED_PROVENANCE.items():
        actual[relative] = sha256_file(_safe_path(root, relative))
        if actual[relative] != expected:
            raise ValueError(f"SHA-256 obrigatório divergiu: {relative}.")
    agents = _safe_path(root, "AGENTS.md").read_text(encoding="utf-8")
    for state in (
        "REJECTION_3_CLOSED",
        "LIVE_VISUAL_TESTER_V1_READY",
        "R4.7A `CLOSED`",
        "REJECTION_4_HELDOUT_CAPTURE_PROTOCOL_FROZEN",
    ):
        if state not in agents:
            raise ValueError(f"Estado obrigatório ausente em AGENTS.md: {state}.")
    return actual


def _reject_contamination(value) -> None:
    forbidden = {
        "score",
        "scores",
        "prediction",
        "predictions",
        "accuracy",
        "confidence",
        "logits",
        "embedding",
        "embeddings",
        "cosine",
        "cos_pred",
        "threshold",
        "decision",
        "accept",
        "reject",
    }
    if isinstance(value, dict):
        if forbidden.intersection(value):
            raise ValueError("Manifesto contém saída de modelo proibida.")
        for key, item in value.items():
            if key in NO_INFERENCE and item != NO_INFERENCE[key]:
                raise ValueError("Manifesto registra contaminação por inferência.")
            _reject_contamination(item)
    elif isinstance(value, list):
        for item in value:
            _reject_contamination(item)


def _validate_manifest_header(manifest: dict) -> None:
    _reject_contamination(manifest)
    if (
        manifest.get("format_version") != 1
        or manifest.get("state") != "REJECTION_4_HELDOUT_CAPTURE_IN_PROGRESS"
        or manifest.get("plan_sha256") != PLAN_SHA256
        or manifest.get("scientific_status") != SCIENTIFIC_STATUS
        or manifest.get("models_loaded") is not False
        or manifest.get("model_inference_performed") is not False
        or not isinstance(manifest.get("samples"), list)
        or not isinstance(manifest.get("sessions"), dict)
        or not isinstance(manifest.get("recaptures"), list)
    ):
        raise ValueError("Manifesto incompatível com captura held-out R4 congelada.")


def _attempt_path(row: dict, number: int) -> str:
    if type(number) is not int or number < 1:
        raise ValueError(f"{row['sample_id']}: número de attempt inválido.")
    base = assert_capture_path(row["raw_video_path"])
    return (
        base.as_posix()
        if number == 1
        else base.with_name(f"{base.stem}.attempt_{number:02d}.mp4").as_posix()
    )


def _partial_path(row: dict) -> str:
    base = assert_capture_path(row["raw_video_path"])
    return base.with_name(f"{base.stem}.partial.mp4").as_posix()


def _session_timing(manifest: dict) -> list[float]:
    events = manifest["sessions"]
    if not events or set(events) != set(SESSION_IDS[: len(events)]):
        raise ValueError("Sessões não formam prefixo das três sessões congeladas.")
    gaps = []
    previous_end = None
    for session_id in SESSION_IDS[: len(events)]:
        event = events[session_id]
        start = _timestamp(event.get("started_at_utc"))
        end = _timestamp(event.get("ended_at_utc"))
        if end <= start:
            raise ValueError(f"{session_id}: fim da sessão inválido.")
        if previous_end is None:
            if event.get("interval_since_previous_seconds") is not None:
                raise ValueError("Primeira sessão não deve ter gap anterior.")
        else:
            gap = (start - previous_end).total_seconds()
            claimed = event.get("interval_since_previous_seconds")
            if (
                gap < 1200
                or not isinstance(claimed, (int, float))
                or not math.isclose(gap, claimed, rel_tol=0, abs_tol=1e-6)
            ):
                raise ValueError(f"{session_id}: gap mínimo de 20 minutos inválido.")
            gaps.append(gap)
        runs = event.get("capture_runs")
        if not isinstance(runs, list) or not runs:
            raise ValueError(f"{session_id}: runs de captura ausentes.")
        previous_run_end = start
        for run in runs:
            run_start = _timestamp(run.get("started_at_utc"))
            run_end = _timestamp(run.get("ended_at_utc"))
            if (
                not previous_run_end <= run_start <= run_end <= end
                or type(run.get("camera_index")) is not int
                or run["camera_index"] < 0
                or not str(run.get("environment_note", "")).strip()
                or not str(run.get("lighting_note", "")).strip()
            ):
                raise ValueError(f"{session_id}: auditoria de run inválida.")
            previous_run_end = run_end
        previous_end = end
    return gaps


def _validate_record(plan: dict, row: dict, item: dict, root: Path, event: dict) -> set:
    sample_id = row["sample_id"]
    for key in (
        "sample_id",
        "session_id",
        "sample_kind",
        "expected_label",
        "negative_category",
        "oov_prompt",
        "repetition_index",
        "prompt_or_action",
    ):
        if item.get(key) != row[key]:
            raise ValueError(f"{sample_id}: metadados divergem do plano ({key}).")
    number = item.get("selected_attempt_number")
    if item.get("trial_order") != row["order"] or item.get("selected_path") != (
        _attempt_path(row, number)
    ):
        raise ValueError(f"{sample_id}: ordem/path selecionado fora do plano.")
    configuration = item.get("capture_configuration", {})
    if (
        configuration.get("device") != plan["device"]
        or configuration.get("acquisition") != plan["acquisition"]
        or type(configuration.get("camera_index")) is not int
        or configuration["camera_index"] < 0
        or not str(item.get("environment_note", "")).strip()
        or not str(item.get("lighting_note", "")).strip()
    ):
        raise ValueError(f"{sample_id}: configuração/ambiente/iluminação inválidos.")
    start, end = (_timestamp(event[key]) for key in ("started_at_utc", "ended_at_utc"))
    final_time = _timestamp(item.get("capture_timestamp_utc"))
    if not start <= final_time <= end:
        raise ValueError(f"{sample_id}: timestamp fora da sessão.")
    attempts = item.get("attempts")
    if not isinstance(attempts, list) or len(attempts) != number:
        raise ValueError(f"{sample_id}: cadeia de attempts incompleta.")
    paths = set()
    prior_time = start
    for expected_number, attempt in enumerate(attempts, start=1):
        allowed = {_attempt_path(row, expected_number)}
        if expected_number == 1:
            allowed.add(_partial_path(row))
        path = attempt.get("path")
        if attempt.get("number") != expected_number or path not in allowed:
            raise ValueError(f"{sample_id}: attempt fora da sequência/path congelado.")
        if not _safe_path(root, path).is_file():
            raise ValueError(f"{sample_id}: attempt anterior/selecionado ausente.")
        timestamp = attempt.get("timestamp_utc")
        if timestamp is None:
            if (
                expected_number != 1
                or number == 1
                or attempt.get("selected") is not False
            ):
                raise ValueError(
                    f"{sample_id}: timestamp ausente sem auditoria original."
                )
        else:
            parsed = _timestamp(timestamp)
            if not prior_time <= parsed <= end:
                raise ValueError(f"{sample_id}: chronology de attempts inválida.")
            prior_time = parsed
        if expected_number > 1 and attempt.get("reason") not in RECAPTURE_REASONS:
            raise ValueError(f"{sample_id}: motivo técnico não autorizado.")
        paths.add(path)
    if attempts[-1]["path"] != item["selected_path"] or (
        _timestamp(attempts[-1]["timestamp_utc"]) != final_time
    ):
        raise ValueError(f"{sample_id}: seleção não corresponde ao attempt final.")
    return paths


def _validate_recaptures(manifest: dict, rows: dict, samples: dict) -> None:
    audits = {}
    for audit in manifest["recaptures"]:
        row = rows.get(audit.get("sample_id"))
        if row is None or audit.get("reason") not in RECAPTURE_REASONS:
            raise ValueError("Recaptura fora do plano/motivo técnico autorizado.")
        item = samples[row["sample_id"]]
        number = audit.get("final_attempt_number")
        if type(number) is not int or number < 1 or number > len(item["attempts"]):
            raise ValueError(f"{row['sample_id']}: auditoria de attempt inválida.")
        attempt = item["attempts"][number - 1]
        previous = item["attempts"][number - 2]["path"] if number > 1 else None
        timestamp = _timestamp(audit.get("timestamp_utc"))
        event = manifest["sessions"][row["session_id"]]
        start, end = (
            _timestamp(event[key]) for key in ("started_at_utc", "ended_at_utc")
        )
        next_index = SESSION_IDS.index(row["session_id"]) + 1
        next_event = (
            manifest["sessions"].get(SESSION_IDS[next_index])
            if next_index < 3
            else None
        )
        if (
            audit.get("session_id") != row["session_id"]
            or audit.get("final_path") != _attempt_path(row, number)
            or audit.get("previous_path") != previous
            or audit.get("reason") != attempt.get("reason")
            or audit.get("before_model_inference") is not True
            or audit.get("authorized_without_model_output") is not True
            or not str(audit.get("environment_note", "")).strip()
            or not str(audit.get("lighting_note", "")).strip()
            or not start <= timestamp <= _timestamp(attempt["timestamp_utc"]) <= end
            or (next_event and timestamp >= _timestamp(next_event["started_at_utc"]))
            or (number == 1 and audit["reason"] != "arquivo_nao_salvo")
        ):
            raise ValueError(
                f"{row['sample_id']}: auditoria de recaptura inconsistente."
            )
        key = (row["sample_id"], number)
        if key in audits:
            raise ValueError(f"{row['sample_id']}: auditoria duplicada.")
        audits[key] = audit
    for sample_id, item in samples.items():
        for attempt in item["attempts"]:
            if attempt["number"] > 1 or attempt.get("reason") is not None:
                key = (sample_id, attempt["number"])
                # Uma parcial original é auditada pelo evento que gera attempt 02.
                if attempt["number"] == 1 and attempt.get("selected") is False:
                    key = (sample_id, 2)
                if key not in audits:
                    raise ValueError(f"{sample_id}: attempt adicional sem auditoria.")


def _actual_paths(root: Path) -> set[str]:
    directory = _safe_path(root, RAW_ROOT)
    actual = set()
    if directory.exists():
        for path in directory.rglob("*"):
            relative = path.relative_to(Path(root).resolve()).as_posix()
            _safe_path(root, relative)
            if path.is_file():
                actual.add(relative)
    return actual


def validate_inventory(
    plan: dict, manifest: dict, root: Path, session_id=None
) -> tuple:
    """Correspondência exata e auditoria completa, antes de decodificar vídeos."""
    validate_capture_plan(plan)
    _validate_manifest_header(manifest)
    gaps = _session_timing(manifest)
    session_count = len(manifest["sessions"])
    if session_id is None and session_count != 3:
        raise ValueError("QC final exige três sessões e 72 logical samples.")
    if session_id is not None and session_id not in manifest["sessions"]:
        raise ValueError("Sessão solicitada não está completa no manifesto.")
    rows = [
        row
        for session in plan["sessions"][:session_count]
        for row in session["schedule"]
    ]
    items = manifest["samples"]
    if len(items) != 24 * session_count or [
        item.get("sample_id") for item in items
    ] != [row["sample_id"] for row in rows]:
        raise ValueError(
            "Inventário/ordem exige exatamente 24 logical samples por sessão."
        )
    expected_paths = set()
    selected = []
    for row, item in zip(rows, items):
        expected_paths.update(
            _validate_record(
                plan, row, item, root, manifest["sessions"][row["session_id"]]
            )
        )
        if session_id is None or row["session_id"] == session_id:
            selected.append(
                {"row": row, "record": item, "relative_path": item["selected_path"]}
            )
    _validate_recaptures(
        manifest,
        {row["sample_id"]: row for row in rows},
        {item["sample_id"]: item for item in items},
    )
    actual = _actual_paths(root)
    if expected_paths != actual:
        raise ValueError(
            f"Inventário divergente: ausentes={sorted(expected_paths - actual)}; "
            f"extras={sorted(actual - expected_paths)}"
        )
    paths = [item["relative_path"] for item in selected]
    if len(paths) != len(set(paths)):
        raise ValueError("Paths selecionados duplicados.")
    return selected, sorted(actual), gaps


def _session_snapshot(manifest: dict, session_id: str) -> dict:
    if session_id not in SESSION_IDS or session_id not in manifest["sessions"]:
        raise ValueError("Sessão de QC desconhecida.")
    return {
        "plan_sha256": manifest["plan_sha256"],
        "session_id": session_id,
        "session": manifest["sessions"][session_id],
        "samples": [
            item for item in manifest["samples"] if item["session_id"] == session_id
        ],
        "recaptures": [
            item for item in manifest["recaptures"] if item["session_id"] == session_id
        ],
    }


def session_report_path(manifest: dict, session_id: str) -> Path:
    return (
        SESSION_QC_ROOT
        / f"{session_id}.{_digest(_session_snapshot(manifest, session_id))}.json"
    )


def _attempt_hashes(manifest: dict, root: Path, session_id=None) -> list[dict]:
    return [
        {
            "sample_id": item["sample_id"],
            "number": attempt["number"],
            "relative_path": attempt["path"],
            "sha256": sha256_file(_safe_path(root, attempt["path"])),
        }
        for item in manifest["samples"]
        if session_id is None or item["session_id"] == session_id
        for attempt in item["attempts"]
    ]


def _fingerprint(records: list) -> str:
    keys = (
        "sample_id",
        "session_id",
        "sample_kind",
        "expected_label",
        "negative_category",
        "oov_prompt",
        "repetition_index",
        "selected_attempt",
        "relative_path",
        "sha256",
    )
    return _digest(
        {
            "capture_plan_sha256": PLAN_SHA256,
            "samples": [{key: item[key] for key in keys} for item in records],
        }
    )


def build_report(plan: dict, manifest: dict, root: Path, session_id=None) -> dict:
    manifest_path = _safe_path(root, MANIFEST_PATH)
    manifest_before = manifest_path.read_bytes()
    if json.loads(manifest_before) != manifest:
        raise ValueError("Manifesto em memória divergiu dos bytes de proveniência.")
    selected, attempts, gaps = validate_inventory(plan, manifest, root, session_id)
    records, failures = [], []
    for item in selected:
        row, capture = item["row"], item["record"]
        path = _safe_path(root, item["relative_path"])
        before = sha256_file(path)
        size = path.stat().st_size
        info = inspect_video(path) if size else {"container_readable": False}
        reasons = evaluate_video_metadata(info) if size else ["empty_file"]
        if sha256_file(path) != before:
            raise ValueError(f"{row['sample_id']}: arquivo mudou durante QC.")
        info = {
            key: (
                None if isinstance(value, float) and not math.isfinite(value) else value
            )
            for key, value in info.items()
        }
        record = {
            key: row[key]
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
        }
        record.update(
            {
                "trial_order": row["order"],
                "selected_attempt": capture["selected_attempt_number"],
                "relative_path": item["relative_path"],
                "sha256": before,
                "byte_size": size,
                "capture_timestamp_utc": capture["capture_timestamp_utc"],
                "capture_configuration": capture["capture_configuration"],
                "environment_note": capture["environment_note"],
                "lighting_note": capture["lighting_note"],
                "video_technical_metadata": info,
                "technical_qc_decision": "FAIL" if reasons else "PASS",
                "technical_qc_reasons": reasons,
            }
        )
        records.append(record)
        failures.extend(
            {"sample_id": row["sample_id"], "rule": reason, "reason": reason}
            for reason in reasons
        )
    if manifest_path.read_bytes() != manifest_before:
        raise ValueError("Manifesto mudou durante QC.")
    session_ids = (
        list(SESSION_IDS[: len(manifest["sessions"])])
        if session_id is None
        else [session_id]
    )
    report = {
        "format_version": 1,
        "state": (
            "REJECTION_4_HELDOUT_CAPTURE_QC_BLOCKED"
            if failures
            else (
                "REJECTION_4_HELDOUT_DATASET_FROZEN"
                if session_id is None
                else "REJECTION_4_HELDOUT_SESSION_QC_PASSED"
            )
        ),
        "scientific_scope": SCIENTIFIC_STATUS,
        "scientific_status": "TECHNICAL QC ONLY — NO MODEL PERFORMANCE OBSERVED",
        "session_ids": session_ids,
        "session_id": session_id,
        "provenance": {
            "capture_plan_path": PLAN_PATH.as_posix(),
            "capture_plan_sha256": PLAN_SHA256,
            "capture_manifest_path": MANIFEST_PATH,
            "capture_manifest_sha256": hashlib.sha256(manifest_before).hexdigest(),
            "source_edge_freeze_sha256": EDGE_FREEZE_SHA256,
        },
        "logical_sample_count": len(records),
        "session_counts": dict(Counter(item["session_id"] for item in records)),
        "type_counts": dict(Counter(item["sample_kind"] for item in records)),
        "known_class_counts": dict(
            Counter(
                item["expected_label"]
                for item in records
                if item["sample_kind"] == "KNOWN"
            )
        ),
        "unknown_category_counts": dict(
            Counter(
                item["negative_category"]
                for item in records
                if item["sample_kind"] == "UNKNOWN"
            )
        ),
        "known_labels": list(KNOWN_LABELS),
        "unknown_categories": list(UNKNOWN_CATEGORIES),
        "selected_oov_prompts": plan["selected_oov_prompts"],
        "session_timing": {key: manifest["sessions"][key] for key in session_ids},
        "session_gaps_seconds": gaps,
        "total_mp4_attempt_files": len(attempts),
        "attempt_hashes": _attempt_hashes(manifest, root, session_id),
        "recapture_audit": [
            audit
            for audit in manifest["recaptures"]
            if audit["session_id"] in session_ids
        ],
        "qc_result": "FAIL" if failures else "PASS",
        "technical_failures": failures,
        "records": records,
        "dataset_fingerprint": _fingerprint(records),
        **NO_INFERENCE,
    }
    if session_id is not None:
        report["session_snapshot"] = _session_snapshot(manifest, session_id)
        report["session_snapshot_sha256"] = _digest(report["session_snapshot"])
    return report


def require_pass(report: dict, count: int) -> None:
    if (
        report.get("qc_result") != "PASS"
        or report.get("logical_sample_count") != count
        or report.get("technical_failures")
    ):
        raise ValueError(
            json.dumps(report.get("technical_failures", []), ensure_ascii=False)
        )
    if any(report.get(key) != value for key, value in NO_INFERENCE.items()):
        raise ValueError("QC contém contaminação ou flags ausentes.")
    if len(report.get("records", [])) != count:
        raise ValueError("QC contém contagens inconsistentes.")


def require_session_pass(root: Path, manifest: dict, session_id: str) -> None:
    path = _safe_path(root, session_report_path(manifest, session_id))
    if not path.is_file():
        raise ValueError(f"{session_id}: QC PASS atual da sessão anterior ausente.")
    report = json.loads(path.read_bytes())
    require_pass(report, 24)
    if report.get("session_snapshot") != _session_snapshot(
        manifest, session_id
    ) or report.get("session_snapshot_sha256") != _digest(report["session_snapshot"]):
        raise ValueError(f"{session_id}: snapshot QC divergiu do manifesto.")
    expected = _attempt_hashes(manifest, root, session_id)
    if report.get("attempt_hashes") != expected:
        raise ValueError(f"{session_id}: hashes de attempts mudaram após QC.")
    by_path = {item["relative_path"]: item["sha256"] for item in expected}
    if any(
        by_path.get(item["relative_path"]) != item["sha256"]
        for item in report["records"]
    ):
        raise ValueError(f"{session_id}: hashes selecionados inconsistentes.")
    snapshot_samples = report["session_snapshot"]["samples"]
    for item, sample in zip(report["records"], snapshot_samples):
        if (
            any(
                item.get(key) != sample.get(key)
                for key in (
                    "sample_id",
                    "session_id",
                    "trial_order",
                    "sample_kind",
                    "expected_label",
                    "negative_category",
                    "oov_prompt",
                    "repetition_index",
                    "prompt_or_action",
                )
            )
            or item.get("relative_path") != sample["selected_path"]
            or item.get("selected_attempt") != sample["selected_attempt_number"]
            or item.get("technical_qc_decision") != "PASS"
            or item.get("technical_qc_reasons") != []
            or evaluate_video_metadata(item.get("video_technical_metadata", {}))
        ):
            raise ValueError(f"{session_id}: records QC divergem da seleção/critérios.")
    if report.get("dataset_fingerprint") != _fingerprint(report["records"]):
        raise ValueError(f"{session_id}: fingerprint QC inconsistente.")


def ensure_capture_allowed(root: Path, manifest: dict, session_id: str) -> None:
    if any(_safe_path(root, path).exists() for path in (RESULT_PATH, FREEZE_PATH)):
        raise ValueError("Dataset congelado/QC final existente; captura bloqueada.")
    index = SESSION_IDS.index(session_id)
    if index and session_id not in manifest["sessions"]:
        previous = SESSION_IDS[index - 1]
        if previous not in manifest["sessions"]:
            raise ValueError("Sessão anterior ainda não iniciada/concluída.")
        require_session_pass(root, manifest, previous)


def build_freeze(report: dict) -> dict:
    require_pass(report, 72)
    records = report["records"]
    if (
        report.get("session_id") is not None
        or report.get("session_counts") != dict.fromkeys(SESSION_IDS, 24)
        or report.get("type_counts") != {"KNOWN": 36, "UNKNOWN": 36}
        or len({item["sample_id"] for item in records}) != 72
        or len({item["relative_path"] for item in records}) != 72
    ):
        raise ValueError("Freeze exige inventário final de 72 samples únicos.")
    return {
        **{
            key: value
            for key, value in report.items()
            if key not in ("records", "session_id", "technical_failures")
        },
        "state": "REJECTION_4_HELDOUT_DATASET_FROZEN",
        "samples": records,
        "qc_json_path": RESULT_PATH.as_posix(),
        "qc_json_sha256": _digest(report),
        "capture_plan_path": PLAN_PATH.as_posix(),
        "capture_plan_sha256": PLAN_SHA256,
        "capture_manifest_sha256": report["provenance"]["capture_manifest_sha256"],
        "source_edge_freeze_sha256": EDGE_FREEZE_SHA256,
    }


def _write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _results_markdown(report: dict, freeze_sha: str) -> bytes:
    lines = [
        "# Rejection 4 — QC técnico do held-out",
        "",
        report["scientific_status"],
        "",
        "Held-out UNEVALUATED; nenhuma medição de desempenho foi realizada.",
        "",
        "## Proveniência",
        "",
        f"- Capture plan SHA-256: `{PLAN_SHA256}`",
        "- Capture manifest SHA-256: "
        f"`{report['provenance']['capture_manifest_sha256']}`",
        f"- QC JSON SHA-256: `{_digest(report)}`",
        f"- Dataset fingerprint: `{report['dataset_fingerprint']}`",
        f"- Freeze SHA-256: `{freeze_sha}`",
        f"- Edge freeze SHA-256: `{EDGE_FREEZE_SHA256}`",
        "",
        "## Inventário e integridade",
        "",
        "72 logical samples: 24 por sessão, 36 KNOWN e 36 UNKNOWN.",
        "6 por classe KNOWN e 6 por categoria UNKNOWN; plano/ordem/OOV intactos.",
        "Todos os MP4 selecionados foram decodificados integralmente "
        "em 640 × 480/30 FPS.",
    ]
    for key, label in (
        ("frame_count", "Frames"),
        ("duration_seconds", "Duração em segundos"),
    ):
        values = [item["video_technical_metadata"][key] for item in report["records"]]
        lines.append(f"{label}: {min(values)}–{max(values)}.")
    sizes = [item["byte_size"] for item in report["records"]]
    codecs = sorted(
        {item["video_technical_metadata"]["codec"] for item in report["records"]}
    )
    lines.extend(
        [
            f"Bytes: {min(sizes)}–{max(sizes)}.",
            f"Codecs observados: {', '.join(codecs)}.",
            "",
            "## Sessões e intervalos",
            "",
        ]
    )
    for session_id, event in report["session_timing"].items():
        lines.append(
            f"- {session_id}: {event['started_at_utc']} → {event['ended_at_utc']}; "
            f"gap anterior {event['interval_since_previous_seconds']} s."
        )
        for run in event["capture_runs"]:
            lines.append(
                f"  - Ambiente declarado: {run['environment_note']}; "
                f"iluminação: {run['lighting_note']}."
            )
    lines.extend(["", "## Recapturas técnicas", ""])
    if not report["recapture_audit"]:
        lines.append("Nenhuma recaptura registrada.")
    for audit in report["recapture_audit"]:
        lines.append(
            f"- {audit['sample_id']}: {audit['reason']}; "
            f"attempt {audit['final_attempt_number']}; {audit['timestamp_utc']}; "
            f"anterior `{audit['previous_path']}` preservado; "
            f"ambiente {audit['environment_note']}; "
            f"iluminação {audit['lighting_note']}."
        )
    lines.extend(
        [
            "",
            "## Contaminação e estado",
            "",
            "Zero modelos carregados, inferência, embeddings, scores ou previsões.",
            "Held-outs antigos não foram abertos; Live Tester permanece R3.",
            "REJECTION_4_HELDOUT_DATASET_FROZEN; evaluation count = 0.",
            "Não alterar/recapturar arquivos após freeze. R4 permanece IN PROGRESS.",
            "Próxima avaliação one-shot não iniciada.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def run_qc(root: Path = ROOT, session_id=None) -> dict:
    root = Path(root).resolve()
    if any(
        _safe_path(root, path).exists()
        for path in (RESULT_PATH, FREEZE_PATH, RESULTS_DOC_PATH)
    ):
        raise FileExistsError("QC/freeze final já existe; não sobrescrever.")
    validate_provenance(root)
    plan = load_capture_plan(root / PLAN_PATH)
    manifest = json.loads(_safe_path(root, MANIFEST_PATH).read_bytes())
    if session_id is None:
        for identifier in SESSION_IDS:
            require_session_pass(root, manifest, identifier)
    report = build_report(plan, manifest, root, session_id)
    require_pass(report, 72 if session_id is None else 24)
    raw = canonical_bytes(report)
    if session_id is not None:
        target = _safe_path(root, session_report_path(manifest, session_id))
        if target.exists():
            prior = json.loads(target.read_bytes())
            require_session_pass(root, manifest, session_id)
            return prior
        _write_exclusive(target, raw)
    else:
        freeze_raw = canonical_bytes(build_freeze(report))
        document = _results_markdown(report, hashlib.sha256(freeze_raw).hexdigest())
        # Tudo validado em memória antes da primeira persistência. Qualquer arquivo
        # parcial bloqueia nova execução; nunca é silenciosamente substituído.
        _write_exclusive(_safe_path(root, RESULT_PATH), raw)
        _write_exclusive(_safe_path(root, FREEZE_PATH), freeze_raw)
        _write_exclusive(_safe_path(root, RESULTS_DOC_PATH), document)
    return report


def preflight(root: Path = ROOT) -> dict:
    root = Path(root).resolve()
    provenance = validate_provenance(root)
    if any(
        _safe_path(root, path).exists()
        for path in (RESULT_PATH, FREEZE_PATH, RESULTS_DOC_PATH)
    ):
        raise ValueError("QC final/freeze prévio existente.")
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise ValueError("Worktree versionável precisa estar limpo antes da captura.")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", PLAN_COMMIT, "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    plan = load_capture_plan(root / PLAN_PATH)
    manifest_path = _safe_path(root, MANIFEST_PATH)
    count = 0
    if manifest_path.exists():
        from scripts.demo.capture_rejection_4_heldout import (
            _load_manifest,
            _verify_preserved_attempts,
        )

        manifest = _load_manifest(manifest_path, plan)
        _validate_manifest_header(manifest)
        _verify_preserved_attempts(manifest, root)
        count = len(manifest["samples"])
        rows = [row for session in plan["sessions"] for row in session["schedule"]]
        if [item["sample_id"] for item in manifest["samples"]] != [
            row["sample_id"] for row in rows[:count]
        ]:
            raise ValueError("Manifesto retomável divergiu da ordem congelada.")
        expected = {
            attempt["path"]
            for item in manifest["samples"]
            for attempt in item["attempts"]
        }
        # Original/parcial do próximo trial pode exigir recaptura auditada;
        # não é uma seleção válida e não é descartado.
        pending = set()
        if count < 72:
            pending = {rows[count]["raw_video_path"], _partial_path(rows[count])}
        actual = _actual_paths(root)
        if actual - expected - pending or expected - actual:
            raise ValueError("Arquivos inesperados ou attempts ausentes no preflight.")
    elif _actual_paths(root):
        raise ValueError("Arquivos de captura existentes sem manifesto.")
    return {
        "qc_result": "PREFLIGHT_PASS",
        "commit": commit,
        "git_clean": True,
        "provenance": provenance,
        "captured_logical_samples": count,
        **NO_INFERENCE,
    }


def main(arguments=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preflight", action="store_true")
    actions.add_argument("--session", choices=SESSION_IDS)
    actions.add_argument("--freeze-dataset", action="store_true")
    args = parser.parse_args(arguments)
    try:
        report = preflight() if args.preflight else run_qc(session_id=args.session)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Falha técnica: {error}\n")
    print(
        json.dumps(
            (
                report
                if args.preflight
                else {
                    "state": report["state"],
                    "qc_result": report["qc_result"],
                    "logical_sample_count": report["logical_sample_count"],
                    "dataset_fingerprint": report["dataset_fingerprint"],
                    **NO_INFERENCE,
                }
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
