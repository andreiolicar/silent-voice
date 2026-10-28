"""Snapshot auditável dos negativos de desenvolvimento, sem inferência."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from silent_voice.rejection.rejection_dataset import (
    TECHNICAL_REASONS,
    NegativeGlobalReport,
    validate_all_rejection_sessions,
)
from silent_voice.rejection.rejection_protocol import (
    NEGATIVE_CATEGORIES,
    NEGATIVE_DEVELOPMENT_SESSIONS,
)


SNAPSHOT_FORMAT_VERSION = 1
CAPTURED_STATUS = "REJECTION_DEV_CAPTURED"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _video_path(raw_root: Path, sample) -> Path:
    return (
        Path(raw_root)
        / sample.session_id
        / sample.negative_category
        / f"{sample.sample_id}.mp4"
    )


def _video_paths(report: NegativeGlobalReport, raw_root: Path) -> dict[str, Path]:
    raw_root = Path(raw_root)
    expected = {
        sample.sample_id: _video_path(raw_root, sample) for sample in report.samples
    }
    actual = set(raw_root.rglob("*.mp4"))
    if actual != set(expected.values()):
        raise ValueError("Os 54 vídeos brutos não correspondem ao plano negativo.")
    return expected


def validate_existing_capture_manifest(
    report: NegativeGlobalReport, raw_root: Path, manifest: dict
) -> None:
    """Confere a captura já marcada como concluída sem reescrever o manifesto."""
    if (
        manifest.get("protocol_status") != CAPTURED_STATUS
        or manifest.get("negative_development_captured") is not True
        or manifest.get("real_rejection_experiment_executed") is not False
    ):
        raise ValueError("Estado do manifesto incompatível com captura pré-scores.")
    details = manifest.get("negative_development_capture")
    if not isinstance(details, dict):
        raise ValueError("Resumo da captura ausente no manifesto.")
    expected_ids = [sample.sample_id for sample in report.samples]
    expected_hashes = {
        sample.sample_id: file_sha256(sample.path) for sample in report.samples
    }
    if (
        details.get("sample_count") != 54
        or details.get("session_ids") != list(NEGATIVE_DEVELOPMENT_SESSIONS)
        or details.get("counts_by_category") != report.counts_by_category
        or details.get("sample_ids") != expected_ids
        or details.get("npz_sha256") != expected_hashes
        or details.get("raw_video_count") != 54
    ):
        raise ValueError("IDs, contagens ou hashes divergem do manifesto de captura.")
    _video_paths(report, raw_root)


def _capture_manifest(manifest_path: Path, report, raw_root: Path) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    validate_existing_capture_manifest(report, raw_root, manifest)
    return manifest


def _audit_records(processed_root: Path, raw_root: Path, report) -> list[dict]:
    processed_root = Path(processed_root)
    raw_root = Path(raw_root)
    samples = {sample.sample_id: sample for sample in report.samples}
    records = []
    for audit_path in sorted(processed_root.rglob("*.recapture-*.json")):
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Auditoria de recaptura inválida: {audit_path}"
            ) from error
        sample = samples.get(audit.get("sample_id"))
        if (
            sample is None
            or audit.get("session_id") != sample.session_id
            or audit.get("negative_category") != sample.negative_category
            or audit.get("reason") not in TECHNICAL_REASONS
            or audit.get("model_scores_used") is not False
            or audit.get("performed_before_rejection_calibration") is not True
            or not isinstance(audit.get("backups"), list)
            or not audit["backups"]
        ):
            raise ValueError(
                f"Auditoria de recaptura inválida ou com score: {audit_path}"
            )
        expected_parent = sample.path.parent.resolve()
        if audit_path.parent.resolve() != expected_parent:
            raise ValueError(f"Auditoria de recaptura fora da categoria: {audit_path}")
        backups = []
        for backup_name in audit["backups"]:
            backup = Path(backup_name).resolve()
            if not backup.is_file() or ".technical-backup-" not in backup.name:
                raise ValueError(f"Backup de recaptura ausente: {backup_name}")
            if backup.is_relative_to(processed_root.resolve()):
                tree = "processed"
                relative = backup.relative_to(processed_root.resolve())
            elif backup.is_relative_to(raw_root.resolve()):
                tree = "raw"
                relative = backup.relative_to(raw_root.resolve())
            else:
                raise ValueError(f"Backup de recaptura fora do dataset: {backup_name}")
            backups.append(
                {
                    "tree": tree,
                    "path": relative.as_posix(),
                    "sha256": file_sha256(backup),
                }
            )
        records.append(
            {
                "path": audit_path.relative_to(processed_root).as_posix(),
                "sha256": file_sha256(audit_path),
                "sample_id": sample.sample_id,
                "session_id": sample.session_id,
                "negative_category": sample.negative_category,
                "reason": audit["reason"],
                "model_scores_used": False,
                "backups": backups,
            }
        )
    return records


def _expected_structure(report) -> dict:
    return {
        "session_ids": list(NEGATIVE_DEVELOPMENT_SESSIONS),
        "category_order": list(NEGATIVE_CATEGORIES),
        "total_sample_count": report.sample_count,
        "per_session_counts": {
            session.session_id: session.sample_count for session in report.sessions
        },
        "per_category_counts": report.counts_by_category,
        "sample_ids": [sample.sample_id for sample in report.samples],
        "oov_prompts": {
            sample.sample_id: sample.oov_prompt
            for sample in report.samples
            if sample.negative_category == "FALA_FORA_VOCAB"
        },
    }


def build_rejection_capture_snapshot(
    processed_root: Path,
    raw_root: Path,
    manifest_path: Path,
    git_commit: str,
) -> dict:
    """Lê somente dados congelados e produz um documento sem resultados de modelo."""
    if len(git_commit) != 40 or any(
        char not in "0123456789abcdef" for char in git_commit
    ):
        raise ValueError("Commit Git inválido para o snapshot.")
    report = validate_all_rejection_sessions(processed_root)
    _capture_manifest(manifest_path, report, raw_root)
    videos = _video_paths(report, raw_root)
    snapshot = {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "status": CAPTURED_STATUS,
        "capture_completed_before_rejection_experiments": True,
        "rejection_scores_observed_before_snapshot": False,
        "git_commit": git_commit,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **_expected_structure(report),
        "npz_sha256": {
            sample.sample_id: file_sha256(sample.path) for sample in report.samples
        },
        "mp4_sha256": {
            sample_id: file_sha256(path) for sample_id, path in videos.items()
        },
        "recapture_audits": _audit_records(processed_root, raw_root, report),
    }
    return snapshot


def save_rejection_capture_snapshot(snapshot: dict, path: Path) -> None:
    """Cria uma única vez o snapshot; nunca substitui um registro anterior."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(snapshot, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def validate_rejection_capture_snapshot(
    snapshot_path: Path,
    processed_root: Path,
    raw_root: Path,
    verify_videos: bool = True,
) -> dict:
    """Verifica o dataset contra o snapshot antes de qualquer score futuro."""
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    if (
        snapshot.get("format_version") != SNAPSHOT_FORMAT_VERSION
        or snapshot.get("status") != CAPTURED_STATUS
        or snapshot.get("capture_completed_before_rejection_experiments") is not True
        or snapshot.get("rejection_scores_observed_before_snapshot") is not False
    ):
        raise ValueError("Contrato do snapshot de rejection inválido.")
    report = validate_all_rejection_sessions(processed_root)
    expected = _expected_structure(report)
    if any(snapshot.get(key) != value for key, value in expected.items()):
        raise ValueError("Contagens ou metadados divergem do snapshot de rejection.")
    current_npz = {
        sample.sample_id: file_sha256(sample.path) for sample in report.samples
    }
    if snapshot.get("npz_sha256") != current_npz:
        raise ValueError("SHA-256 dos NPZ diverge do snapshot de rejection.")
    if verify_videos:
        videos = _video_paths(report, raw_root)
        current_mp4 = {
            sample_id: file_sha256(path) for sample_id, path in videos.items()
        }
        if snapshot.get("mp4_sha256") != current_mp4:
            raise ValueError("SHA-256 dos MP4 diverge do snapshot de rejection.")
    if snapshot.get("recapture_audits") != _audit_records(
        processed_root, raw_root, report
    ):
        raise ValueError("Auditoria de recaptura diverge do snapshot.")
    return snapshot
