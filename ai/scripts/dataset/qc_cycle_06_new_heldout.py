"""Audita somente a integridade técnica dos MP4 do novo held-out visual."""

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

import cv2

from scripts.dataset.capture_cycle_06_heldout_raw import (
    PLAN_PATH,
    REPOSITORY_ROOT,
    SESSION_IDS,
    load_capture_plan,
)


EDGE_CONFIG_PATH = (
    REPOSITORY_ROOT
    / "data/processed/evaluation/cycle_06_edge_preheldout_final_config.json"
)
FREEZE_MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "data/processed/evaluation/cycle_06_preheldout_freeze_manifest.json"
)
OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data/processed/evaluation/cycle_06_new_heldout_dataset_manifest.json"
)
EXPECTED_PROVENANCE = {
    "capture_plan_sha256": (
        "cd0d54815acd4b1a67d3b0bb483bc80a4165c990656783be0fa99aeff3889cd7"
    ),
    "edge_config_sha256": (
        "a761de851e7dc22ed8974dbd3dc98e23963d384057488bdfe9aae0ef406eb4d4"
    ),
    "freeze_manifest_sha256": (
        "41cf1f308a1c153bfc0f533c70676309139d63531cce9ce31363c74643e611bd"
    ),
    "pipeline_fingerprint_sha256": (
        "e8394f470520f61d096bc0f1a4f5997f5ae5692af412707c4905519ae602c48b"
    ),
}


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 por streaming sem alterar o arquivo."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_provenance(
    plan_path: Path,
    edge_config_path: Path,
    freeze_manifest_path: Path,
    expected: dict = EXPECTED_PROVENANCE,
) -> dict:
    """Valida o freeze antes de qualquer acesso aos vídeos."""
    canonical_plan = Path(plan_path).read_bytes().replace(b"\r\n", b"\n")
    actual = {
        "capture_plan_sha256": hashlib.sha256(canonical_plan).hexdigest(),
        "edge_config_sha256": sha256_file(edge_config_path),
        "freeze_manifest_sha256": sha256_file(freeze_manifest_path),
    }
    config = json.loads(Path(edge_config_path).read_text(encoding="utf-8"))
    freeze = json.loads(Path(freeze_manifest_path).read_text(encoding="utf-8"))
    config_fingerprint = config.get("pipeline_fingerprint_sha256")
    freeze_fingerprint = freeze.get("pipeline_fingerprint_sha256")
    if config_fingerprint != freeze_fingerprint:
        raise ValueError("Divergência de proveniência: fingerprints não coincidem.")
    actual["pipeline_fingerprint_sha256"] = config_fingerprint
    if actual != expected:
        raise ValueError("Divergência de proveniência do protocolo congelado.")
    return actual


def _allowed_path(row: dict) -> Path:
    """Rejeita paths fora das duas sessões permitidas antes de I/O."""
    session_id = row["session_id"]
    relative = Path(row["raw_video_path"])
    parts = relative.parts
    if (
        session_id not in SESSION_IDS
        or len(parts) != 6
        or parts[:4] != ("data", "raw", "visual_dataset", session_id)
        or relative.suffix.lower() != ".mp4"
        or relative.stem != row["sample_id"]
        or any(part in {".", ".."} for part in parts)
    ):
        raise ValueError("Path ou sessão não autorizada para QC.")
    return relative


def validate_inventory(rows: tuple[dict, ...], root: Path) -> tuple[Path, ...]:
    """Compara inventário exato dentro das duas raízes permitidas."""
    rows = tuple(rows)
    expected = []
    sample_ids = set()
    for row in rows:
        relative = _allowed_path(row)
        if row["sample_id"] in sample_ids:
            raise ValueError(f"Sample ID duplicado: {row['sample_id']}")
        sample_ids.add(row["sample_id"])
        expected.append(relative)
    if len(set(expected)) != len(expected):
        raise ValueError("Path duplicado no plano.")

    root = Path(root)
    actual = set()
    for session_id in SESSION_IDS:
        session_root = root / "data/raw/visual_dataset" / session_id
        if session_root.is_dir():
            for path in session_root.rglob("*"):
                if path.is_file():
                    actual.add(path.relative_to(root))
    missing = sorted(set(expected) - actual)
    extras = sorted(actual - set(expected))
    if missing or extras:
        raise ValueError(
            f"Inventário inválido: ausente={list(map(str, missing))}; "
            f"inesperado={list(map(str, extras))}"
        )
    actual_ids = [path.stem for path in actual]
    duplicates = sorted(
        name for name, count in Counter(actual_ids).items() if count > 1
    )
    if duplicates:
        raise ValueError(f"Sample ID duplicado no filesystem: {duplicates}")
    return tuple(root / relative for relative in expected)


def inspect_video(path: Path) -> dict:
    """Decodifica sequencialmente para verificar integridade, sem analisar pixels."""
    result = {
        "container_readable": False,
        "codec": "",
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "frame_count": 0,
        "duration_seconds": 0.0,
        "decoded_frame_count": 0,
        "first_frame_decodes": False,
        "middle_frame_decodes": False,
        "last_frame_decodes": False,
        "technical_qc_decision": "TECHNICAL_QC_FAIL",
        "technical_qc_reasons": [],
    }
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            result["technical_qc_reasons"].append("container_unreadable")
            return result
        result["container_readable"] = True
        fourcc = int(capture.get(cv2.CAP_PROP_FOURCC))
        result["codec"] = "".join(
            chr((fourcc >> (8 * shift)) & 0xFF) for shift in range(4)
        )
        result["width"] = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        result["height"] = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        result["fps"] = float(capture.get(cv2.CAP_PROP_FPS))
        result["frame_count"] = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = result["fps"]
        if math.isfinite(fps) and fps > 0:
            result["duration_seconds"] = result["frame_count"] / fps
        count = 0
        while True:
            decoded, _ = capture.read()
            if not decoded:
                break
            count += 1
        result["decoded_frame_count"] = count
        result["first_frame_decodes"] = count >= 1
        result["middle_frame_decodes"] = count >= 3
        result["last_frame_decodes"] = count >= 3 and count == result["frame_count"]
        reasons = result["technical_qc_reasons"]
        if (result["width"], result["height"]) != (640, 480):
            reasons.append("wrong_dimensions")
        if not math.isfinite(fps) or abs(fps - 30.0) > 1e-6:
            reasons.append("wrong_nominal_fps")
        if result["codec"].lower() not in {"fmp4", "mp4v"}:
            reasons.append("unexpected_codec")
        if result["frame_count"] < 3 or count != result["frame_count"]:
            reasons.append("frame_decode_or_count_failure")
        if (
            not math.isfinite(result["duration_seconds"])
            or result["duration_seconds"] <= 0
        ):
            reasons.append("invalid_duration")
        if not reasons:
            result["technical_qc_decision"] = "PASS"
        return result
    finally:
        capture.release()


def dataset_fingerprint(samples: list[dict]) -> str:
    """Usa a ordem canônica do plano e apenas identidade, path e hash."""
    triples = [
        [sample["sample_id"], sample["relative_path"], sample["file_sha256"]]
        for sample in samples
    ]
    canonical = json.dumps(triples, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def serialize_manifest(payload: dict) -> bytes:
    """Serialização estável, sem timestamp ou ordem dependente do filesystem."""
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _distribution(values: list[float]) -> dict:
    return {
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
    }


def build_manifest(plan: dict, paths: tuple[Path, ...], provenance: dict, root: Path):
    """Produz snapshot técnico completo e determinístico."""
    rows = [row for session in plan["sessions"] for row in session["schedule"]]
    samples = []
    for row, path in zip(rows, paths, strict=True):
        item = {
            "sample_id": row["sample_id"],
            "session_id": row["session_id"],
            "sample_kind": row["sample_kind"],
            "expected_label": row["expected_label"],
            "negative_category": row["negative_category"],
            "relative_path": path.relative_to(root).as_posix(),
            "byte_size": path.stat().st_size,
            "file_sha256": sha256_file(path),
        }
        if item["byte_size"] == 0:
            item["technical_qc_decision"] = "TECHNICAL_QC_FAIL"
            item["technical_qc_reasons"] = ["empty_file"]
        else:
            item.update(inspect_video(path))
        samples.append(item)
    frames = [item["frame_count"] for item in samples]
    durations = [item["duration_seconds"] for item in samples]
    per_session = {
        session_id: _distribution(
            [
                item["frame_count"]
                for item in samples
                if item["session_id"] == session_id
            ]
        )
        for session_id in SESSION_IDS
    }
    failures = [
        {"sample_id": item["sample_id"], "reasons": item["technical_qc_reasons"]}
        for item in samples
        if item["technical_qc_decision"] != "PASS"
    ]
    return {
        "format_version": 1,
        "state": (
            "CYCLE_06_NEW_HELDOUT_DATASET_FROZEN"
            if not failures
            else "FAILED_RETAKE_REQUIRED"
        ),
        "heldout_technical_qc": "PASS" if not failures else "FAILED_RETAKE_REQUIRED",
        "provenance": provenance,
        "capture_plan_sha256": provenance["capture_plan_sha256"],
        "session_names": list(SESSION_IDS),
        "total_sample_count": len(samples),
        "type_counts": dict(
            sorted(Counter(item["sample_kind"] for item in samples).items())
        ),
        "known_class_counts": dict(
            sorted(
                Counter(
                    item["expected_label"]
                    for item in samples
                    if item["sample_kind"] == "KNOWN"
                ).items()
            )
        ),
        "unknown_category_counts": dict(
            sorted(
                Counter(
                    item["negative_category"]
                    for item in samples
                    if item["sample_kind"] == "UNKNOWN"
                ).items()
            )
        ),
        "frame_count_distribution": _distribution(frames),
        "frame_count_by_session": per_session,
        "duration_seconds_distribution": _distribution(durations),
        "fps_distribution": dict(
            sorted(Counter(str(item["fps"]) for item in samples).items())
        ),
        "byte_size_distribution": _distribution(
            [item["byte_size"] for item in samples]
        ),
        "technical_failures": failures,
        "heldout_dataset_fingerprint_sha256": dataset_fingerprint(samples),
        "no_semantic_inference": True,
        "models_loaded": False,
        "old_heldouts_opened": False,
        "samples": samples,
    }


def run_qc(root: Path = REPOSITORY_ROOT, output: Path = OUTPUT_PATH) -> dict:
    """Executa QC técnico somente após validar proveniência congelada."""
    root = Path(root)
    provenance = validate_provenance(
        root / PLAN_PATH.relative_to(REPOSITORY_ROOT),
        root / EDGE_CONFIG_PATH.relative_to(REPOSITORY_ROOT),
        root / FREEZE_MANIFEST_PATH.relative_to(REPOSITORY_ROOT),
    )
    plan = load_capture_plan(root / PLAN_PATH.relative_to(REPOSITORY_ROOT))
    if Path(output).exists():
        raise FileExistsError(f"Manifesto de QC já existe: {output}")
    rows = tuple(row for session in plan["sessions"] for row in session["schedule"])
    paths = validate_inventory(rows, root)
    manifest = build_manifest(plan, paths, provenance, root)
    if manifest["heldout_technical_qc"] != "PASS":
        raise RuntimeError(
            "HELDOUT_TECHNICAL_QC = FAILED_RETAKE_REQUIRED: "
            + json.dumps(manifest["technical_failures"], ensure_ascii=False)
        )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as destination:
        destination.write(serialize_manifest(manifest))
    return manifest


def main() -> None:
    manifest = run_qc()
    print("HELDOUT_TECHNICAL_QC = PASS")
    print(f"Amostras: {manifest['total_sample_count']}")
    print(f"Fingerprint: {manifest['heldout_dataset_fingerprint_sha256']}")
    print(f"Manifesto: {OUTPUT_PATH}")
    print(f"SHA-256: {sha256_file(OUTPUT_PATH)}")


if __name__ == "__main__":
    main()
