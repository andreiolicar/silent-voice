"""QC estritamente técnica dos 72 MP4 R3; não importa inferência."""

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

from scripts.dataset.qc_cycle_06_new_heldout import inspect_video, sha256_file


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = Path("docs/cycles/rejection_3_heldout_capture_plan.json")
EDGE_FREEZE_PATH = Path("docs/cycles/rejection_3_edge_freeze.json")
MANIFEST_PATH = Path(
    "data/processed/evaluation/rejection_3_heldout_capture_manifest.json"
)
RESULT_PATH = Path("data/processed/evaluation/rejection_3_heldout_qc.json")
FREEZE_PATH = Path("docs/cycles/rejection_3_heldout_freeze.json")
RAW_ROOT = Path("data/raw/rejection_3_heldout")
PLAN_SHA256 = "24f16a85e64ba9eed9f22c62dd5427b2c4afedefc41d60c1de307685c8614965"
EDGE_FREEZE_SHA256 = "1a67bcc8890d3f2f4e93f2346844d38a89db1de4448e0855cdb66d0b64af54ff"
SESSION_IDS = tuple(f"r3_heldout_session_{number:02d}" for number in (1, 2, 3))
RECORD_FIELDS = (
    "sample_id",
    "session_id",
    "trial_order",
    "prompt_or_action",
    "output_path",
    "capture_timestamp_utc",
    "attempt_number",
    "recapture_reason",
    "capture_configuration",
)


def canonical_bytes(payload: dict) -> bytes:
    """JSON determinístico, UTF-8/LF, sem NaN."""
    return (
        json.dumps(
            payload, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2
        )
        + "\n"
    ).encode("utf-8")


def _canonical_file_sha256(path: Path) -> str:
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in raw:
        raise ValueError("Quebra de linha inválida no plano congelado.")
    return hashlib.sha256(raw).hexdigest()


def _planned_path(row: dict) -> Path:
    session_id = row.get("session_id")
    if session_id not in SESSION_IDS:
        raise ValueError("Sessão fora do plano R3.")
    session_folder = session_id.removeprefix("r3_heldout_")
    relative = Path(row.get("raw_video_path", ""))
    parts = relative.parts
    if (
        len(parts) != 6
        or parts[:4] != ("data", "raw", "rejection_3_heldout", session_folder)
        or relative.stem != row.get("sample_id")
        or relative.suffix != ".mp4"
        or not relative.stem.startswith("r3_")
        or any(part in {".", ".."} for part in parts)
        or ":" in str(relative)
    ):
        raise ValueError("Path do plano fora do held-out R3 autorizado.")
    return relative


def _attempt_path(row: dict, number: int) -> Path:
    planned = _planned_path(row)
    if number == 1:
        return planned
    if not isinstance(number, int) or number < 2:
        raise ValueError("Número de attempt inválido.")
    return planned.with_name(f"{planned.stem}.attempt_{number:02d}.mp4")


def validate_frozen_plan(plan: dict, plan_sha: str, edge_sha: str) -> int:
    """Confere freeze e todos os 72 paths antes de ler vídeo."""
    sessions = plan.get("sessions", [])
    rows = [row for session in sessions for row in session.get("schedule", [])]
    if (
        plan_sha != PLAN_SHA256
        or edge_sha != EDGE_FREEZE_SHA256
        or plan.get("state") != "REJECTION_3_HELDOUT_CAPTURE_PROTOCOL_FROZEN"
        or plan.get("source_edge_freeze_sha256") != edge_sha
        or [session.get("session_id") for session in sessions] != list(SESSION_IDS)
        or [len(session.get("schedule", [])) for session in sessions] != [24, 24, 24]
        or len(rows) != 72
        or Counter(row.get("sample_kind") for row in rows)
        != {"KNOWN": 36, "UNKNOWN": 36}
        or len({row.get("sample_id") for row in rows}) != 72
        or len({row.get("raw_video_path") for row in rows}) != 72
        or plan.get("no_model_inference_before_r3_7") is not True
    ):
        raise ValueError("Plano R3.6A diverge do freeze pré-captura.")
    for session in sessions:
        for order, row in enumerate(session["schedule"], start=1):
            if (
                row.get("order") != order
                or row.get("session_id") != session["session_id"]
            ):
                raise ValueError("Ordem ou sessão do plano inválida.")
            _planned_path(row)
    return len(rows)


def load_preflight(root: Path = ROOT) -> dict:
    """Valida proveniência sem examinar nenhuma amostra."""
    root = Path(root)
    plan_path = root / PLAN_PATH
    edge_path = root / EDGE_FREEZE_PATH
    plan_sha = _canonical_file_sha256(plan_path)
    edge_sha = sha256_file(edge_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    validate_frozen_plan(plan, plan_sha, edge_sha)
    return plan


def _selected_relative(row: dict, record: dict) -> Path:
    if set(record) != set(RECORD_FIELDS):
        raise ValueError("Manifesto contém campos inesperados ou ausentes.")
    attempt = record["attempt_number"]
    selected = _attempt_path(row, attempt)
    if (
        record["output_path"] != selected.as_posix()
        or record["sample_id"] != row["sample_id"]
        or record["session_id"] != row["session_id"]
        or record["trial_order"] != row["order"]
        or record["prompt_or_action"] != row["prompt_or_action"]
    ):
        raise ValueError("Manifesto não corresponde ao trial congelado.")
    return selected


def validate_inventory(plan: dict, manifest: dict, root: Path) -> tuple[list, list]:
    """Inventário exato de selecionados e attempts preservados, sem modelos."""
    validate_frozen_plan(plan, PLAN_SHA256, EDGE_FREEZE_SHA256)
    if (
        set(manifest)
        != {
            "format_version",
            "state",
            "plan_sha256",
            "capture_record_fields",
            "sessions",
            "samples",
            "recaptures",
            "models_loaded",
            "model_inference_performed",
        }
        or manifest.get("format_version") != 1
        or manifest.get("plan_sha256") != PLAN_SHA256
        or manifest.get("models_loaded") is not False
        or manifest.get("model_inference_performed") is not False
        or manifest.get("capture_record_fields") != list(RECORD_FIELDS)
        or not isinstance(manifest.get("samples"), list)
        or not isinstance(manifest.get("recaptures"), list)
        or len(manifest["samples"]) != 72
    ):
        raise ValueError("Manifesto de captura incompleto ou contaminado.")
    rows = [row for session in plan["sessions"] for row in session["schedule"]]
    by_id = {row["sample_id"]: row for row in rows}
    records = manifest["samples"]
    if len({item.get("sample_id") for item in records}) != 72:
        raise ValueError("Sample ID duplicado no manifesto.")
    selected = []
    expected_existing = set()
    for record in records:
        row = by_id.get(record.get("sample_id"))
        if row is None:
            raise ValueError("Sample ID não pertence ao plano.")
        relative = _selected_relative(row, record)
        if record["capture_configuration"] != {
            "device": plan["device"],
            "acquisition": plan["acquisition"],
        }:
            raise ValueError("Configuração de captura diverge do plano.")
        if relative in expected_existing:
            raise ValueError("Path selecionado duplicado.")
        expected_existing.add(relative)
        selected.append({"row": row, "record": record, "relative_path": relative})
    audit = manifest["recaptures"]
    for event in audit:
        row = by_id.get(event.get("sample_id"))
        if (
            row is None
            or event.get("reason") not in plan["recapture_policy"]["allowed_reasons"]
        ):
            raise ValueError("Auditoria de recaptura fora do protocolo.")
        earlier = event.get("discarded_attempt_number")
        later = event.get("final_attempt_number")
        if not isinstance(earlier, int) or later != earlier + 1:
            raise ValueError("Sequência de attempts inválida.")
        prior = _attempt_path(row, earlier)
        final = _attempt_path(row, later)
        partial = prior.with_name(f"{prior.stem}.partial{prior.suffix}")
        discarded = Path(event.get("discarded_path", ""))
        if (
            event.get("final_path") != final.as_posix()
            or discarded not in (prior, partial)
            or event.get("before_model_inference") is not True
        ):
            raise ValueError("Paths ou autorização da recaptura inválidos.")
        final_full = Path(root) / final
        if not final_full.is_file() or sha256_file(final_full) != event.get(
            "final_sha256"
        ):
            raise ValueError("Hash do attempt final divergiu.")
        prior_full = Path(root) / discarded
        if prior_full.is_file():
            if sha256_file(prior_full) != event.get("discarded_sha256"):
                raise ValueError("Hash do attempt anterior divergiu.")
            expected_existing.add(discarded)
        elif (
            event["reason"] != "arquivo_nao_salvo"
            or event.get("discarded_sha256") is not None
        ):
            raise ValueError("Attempt anterior ausente sem motivo autorizado.")
    for item in selected:
        record = item["record"]
        matching = [
            event for event in audit if event["sample_id"] == record["sample_id"]
        ]
        if (
            record["attempt_number"] != len(matching) + 1
            or (
                matching
                and matching[-1]["final_attempt_number"] != record["attempt_number"]
            )
            or (not matching and record["recapture_reason"] is not None)
            or (matching and record["recapture_reason"] != matching[-1]["reason"])
        ):
            raise ValueError("Attempt selecionado não corresponde à auditoria.")
    raw_root = Path(root) / RAW_ROOT
    actual = set()
    if raw_root.is_dir():
        for path in raw_root.rglob("*"):
            if path.is_symlink():
                raise ValueError("Symlink dentro do held-out R3 proibido.")
            if path.is_file():
                actual.add(path.relative_to(root))
    if actual != expected_existing:
        missing = sorted(map(str, expected_existing - actual))
        extras = sorted(map(str, actual - expected_existing))
        raise ValueError(f"Inventário divergente: ausentes={missing}; extras={extras}")
    return selected, sorted(actual)


def _aware_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp de sessão sem fuso horário.")
    return parsed


def validate_session_timing(plan: dict, manifest: dict) -> list[float]:
    """Exige três sessões completas e >= 1.200 segundos entre elas."""
    sessions = manifest.get("sessions", {})
    if set(sessions) != set(SESSION_IDS):
        raise ValueError("Três sessões concluídas são obrigatórias.")
    gaps = []
    previous_end = None
    for session_id in SESSION_IDS:
        event = sessions[session_id]
        start = _aware_time(event["started_at_utc"])
        end = _aware_time(event["ended_at_utc"])
        if end <= start:
            raise ValueError("Timestamps de sessão em ordem inválida.")
        if previous_end is None:
            if event.get("interval_since_previous_seconds") is not None:
                raise ValueError("Primeira sessão não tem intervalo anterior.")
        else:
            gap = (start - previous_end).total_seconds()
            if gap < plan["session_gap_seconds_minimum"]:
                raise ValueError("Intervalo entre sessões menor que 20 minutos.")
            if not math.isclose(gap, event.get("interval_since_previous_seconds", -1)):
                raise ValueError("Intervalo registrado diverge dos timestamps.")
            gaps.append(gap)
        previous_end = end
    return gaps


def evaluate_video_metadata(info: dict) -> list[str]:
    """Aplica somente os bounds técnicos já pré-registrados na R3.6A."""
    reasons = []
    if info.get("container_readable") is not True:
        return ["container_unreadable"]
    if (info.get("width"), info.get("height")) != (640, 480):
        reasons.append("wrong_dimensions")
    if info.get("codec", "").lower() not in ("mp4v", "fmp4"):
        reasons.append("unexpected_codec")
    fps = info.get("fps")
    if (
        not isinstance(fps, (int, float))
        or not math.isfinite(fps)
        or abs(fps - 30) > 1e-6
    ):
        reasons.append("wrong_nominal_fps")
    frames = info.get("frame_count")
    if (
        not isinstance(frames, int)
        or frames < 3
        or info.get("decoded_frame_count") != frames
        or not all(
            info.get(f"{which}_frame_decodes") for which in ("first", "middle", "last")
        )
    ):
        reasons.append("frame_decode_or_count_failure")
    duration = info.get("duration_seconds")
    if (
        not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or duration <= 0
        or (
            isinstance(frames, int)
            and isinstance(fps, (int, float))
            and math.isfinite(fps)
            and fps > 0
            and not math.isclose(duration, frames / fps, abs_tol=1e-6)
        )
    ):
        reasons.append("invalid_duration")
    return reasons


def build_report(
    plan: dict, manifest: dict, selected: list, attempts: list, root: Path
):
    """Calcula registros técnicos; retorna falhas sem escolher por aparência."""
    gaps = validate_session_timing(plan, manifest)
    records = []
    failures = []
    for item in selected:
        relative = item["relative_path"]
        path = Path(root) / relative
        size = path.stat().st_size
        info = inspect_video(path) if size else {"container_readable": False}
        reasons = ["empty_file"] if not size else evaluate_video_metadata(info)
        record = {
            "sample_id": item["row"]["sample_id"],
            "session_id": item["row"]["session_id"],
            "sample_kind": item["row"]["sample_kind"],
            "expected_label": item["row"]["expected_label"],
            "negative_category": item["row"]["negative_category"],
            "selected_attempt": item["record"]["attempt_number"],
            "relative_path": relative.as_posix(),
            "byte_size": size,
            "sha256": sha256_file(path),
            "video_technical_metadata": info,
            "technical_qc_reasons": reasons,
            "technical_qc_decision": "PASS" if not reasons else "FAIL",
        }
        records.append(record)
        if reasons:
            failures.append(
                {"sample_id": record["sample_id"], "technical_failures": reasons}
            )
    return {
        "format_version": 1,
        "state": (
            "REJECTION_3_HELDOUT_QC_PASSED" if not failures else "TECHNICAL_QC_FAILED"
        ),
        "capture_plan_sha256": PLAN_SHA256,
        "edge_freeze_sha256": EDGE_FREEZE_SHA256,
        "qc_rules": plan["technical_qc"],
        "session_timing": manifest["sessions"],
        "session_gaps_seconds": gaps,
        "logical_sample_count": len(records),
        "type_counts": dict(Counter(row["sample_kind"] for row in records)),
        "total_mp4_attempt_files": len(attempts),
        "recaptures": manifest["recaptures"],
        "technical_failures": failures,
        "model_inference_performed": False,
        "heldout_evaluated": False,
        "old_heldouts_opened": False,
        "records": records,
    }


def run_qc(root: Path = ROOT) -> dict:
    """Persiste QC e freeze somente com 72 amostras tecnicamente válidas."""
    root = Path(root)
    qc_path = root / RESULT_PATH
    freeze_path = root / FREEZE_PATH
    if qc_path.exists() or freeze_path.exists():
        raise FileExistsError("QC/freeze R3 já existe; execução repetida proibida.")
    plan = load_preflight(root)
    manifest_path = root / MANIFEST_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected, attempts = validate_inventory(plan, manifest, root)
    report = build_report(plan, manifest, selected, attempts, root)
    report["capture_manifest_sha256"] = sha256_file(manifest_path)
    if report["technical_failures"]:
        raise ValueError(
            "QC técnica falhou: "
            + json.dumps(report["technical_failures"], ensure_ascii=False)
        )
    freeze = {
        "format_version": 1,
        "state": "REJECTION_3_HELDOUT_QC_PASSED",
        "capture_plan_sha256": PLAN_SHA256,
        "edge_freeze_sha256": EDGE_FREEZE_SHA256,
        "capture_manifest_sha256": report["capture_manifest_sha256"],
        "participant_scope": "SAME_SPEAKER_NEW_SESSION",
        "session_ids": list(SESSION_IDS),
        "session_timing": report["session_timing"],
        "session_gaps_seconds": report["session_gaps_seconds"],
        "logical_sample_count": 72,
        "total_mp4_attempt_files": report["total_mp4_attempt_files"],
        "recapture_audit": report["recaptures"],
        "qc_result": "PASS",
        "model_inference_performed": False,
        "heldout_evaluated": False,
        "samples": report["records"],
    }
    freeze_raw = canonical_bytes(freeze)
    freeze_sha = hashlib.sha256(freeze_raw).hexdigest()
    report["heldout_freeze_sha256"] = freeze_sha
    qc_raw = canonical_bytes(report)
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    qc_path.parent.mkdir(parents=True, exist_ok=True)
    with freeze_path.open("xb") as destination:
        destination.write(freeze_raw)
    with qc_path.open("xb") as destination:
        destination.write(qc_raw)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-technical-qc", action="store_true", required=True)
    parser.parse_args()
    report = run_qc()
    print("REJECTION_3_HELDOUT_QC_PASSED")
    print(f"Amostras técnicas válidas: {report['logical_sample_count']}/72")
    print(f"Freeze SHA-256: {report['heldout_freeze_sha256']}")
    print(f"QC JSON SHA-256: {sha256_file(ROOT / RESULT_PATH)}")


if __name__ == "__main__":
    main()
