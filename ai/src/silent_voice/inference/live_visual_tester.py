"""Demo interativa com o pipeline positivo e o scorer Edge congelados no R4."""

import hashlib
import json
import math
import os
import re
import statistics
import threading
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from scripts.demo import msv_temporal_capture as temporal
from silent_voice.edge import rejection_4_final_heldout as r4
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


TESTER_VERSION = "LIVE_VISUAL_TESTER_R4"
SCIENTIFIC_STATUS = "DEMO_DIAGNOSTIC_NOT_BENCHMARK"
CANDIDATE_ID = r4.CANDIDATE
K = r4.K
THRESHOLD = r4.THRESHOLD
FINAL_FREEZE_PATH = Path("docs/cycles/rejection_4_final_freeze.json")
FINAL_FREEZE_SHA256 = "d2d37118ce0278192a7777951d30c7aefbfb4a3d1caa60858c1394f2fded19e1"
FINAL_RESULT_SHA256 = "e501474e879c274fd515d1791cca5b8464565d29984cb3e9607899425580e763"
EXPECTED_EDGE_FREEZE_SHA256 = r4.PROVENANCE["edge_freeze"][1]
EXPECTED_RUNTIME = "1.30.0"
WINDOW_NAME = "Silent Voice — Live Visual Tester — Rejection 4"
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
DIAGNOSTIC_ROOT = Path("data/processed/live_tester")
ARTIFACT_PATHS = {
    name: r4.PROVENANCE[name][0]
    for name in (
        "encoder",
        "head",
        "edge_scorer",
        "positive_checkpoint",
        "positive_config",
        "reference_bank",
    )
}
# Allowlist explícita: nenhum plano, manifesto, QC ou arquivo do held-out.
LIVE_PROVENANCE_NAMES = (
    "reference_freeze",
    "reference_bank",
    "reference_bank_manifest",
    "edge_scorer",
    "edge_manifest",
    "edge_freeze",
    "encoder",
    "head",
    "positive_checkpoint",
    "positive_config",
    "edge_config",
    "edge_centroids",
    "edge_origin_manifest",
)
PUBLIC_PROVENANCE_NAMES = ("reference_freeze", "edge_manifest", "edge_freeze")


class CaptureCancelled(Exception):
    """O operador encerrou countdown ou gravação por ESC/Q."""


class TemporalCaptureError(RuntimeError):
    """A captura de demo não atende à integridade temporal congelada."""


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo congelado ausente: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_sources(
    root: Path,
    *,
    public_root: Path | None = None,
    freeze_sha256: str = FINAL_FREEZE_SHA256,
    result_sha256: str = FINAL_RESULT_SHA256,
) -> dict:
    """Valida R4 fechado e artefatos sem abrir held-out, câmera ou modelos."""
    root = Path(root).resolve()
    public_root = Path(
        public_root if public_root is not None else temporal.ROOT
    ).resolve()
    freeze_path = r4._safe_path(root, FINAL_FREEZE_PATH)
    if _sha256(freeze_path) != freeze_sha256:
        raise ValueError("SHA-256 do freeze final R4 divergente.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if (
        freeze.get("state") != "REJECTION_4_CLOSED"
        or freeze.get("candidate_id") != CANDIDATE_ID
        or type(freeze.get("k")) is not int
        or freeze.get("k") != K
        or type(freeze.get("threshold")) is not float
        or freeze.get("threshold") != THRESHOLD
        or freeze.get("operator") != ">="
        or freeze.get("labels") != list(DEFAULT_VISUAL_LABELS)
        or freeze.get("positive_classifier_id") != "HYBRID_CLIP_DTW_EVIDENCE_LINEAR"
        or freeze.get("pipeline_fingerprint_sha256") != r4.PIPELINE_FINGERPRINT
        or type(freeze.get("evaluation_run_count")) is not int
        or freeze.get("evaluation_run_count") != 1
        or freeze.get("heldout_consumed") is not True
        or freeze.get("heldout_evaluated") is not True
        or freeze.get("heldout_status") != "CONSUMED"
    ):
        raise ValueError("Política ou estado do freeze R4 inválido.")
    # O SHA do resultado é atestado pelo freeze; o resultado consumido não é aberto.
    if freeze.get("evaluation_result_sha256") != result_sha256:
        raise ValueError("SHA-256 do resultado registrado no freeze R4 divergente.")
    if freeze.get("edge_freeze_sha256") != EXPECTED_EDGE_FREEZE_SHA256:
        raise ValueError("SHA-256 do Edge freeze registrado divergiu.")
    records = {name: r4.PROVENANCE[name] for name in LIVE_PROVENANCE_NAMES}
    public_records = {name: records[name] for name in PUBLIC_PROVENANCE_NAMES}
    private_records = {
        name: record for name, record in records.items() if name not in public_records
    }
    provenance = {
        **r4.verify_provenance(public_root, records=public_records),
        **r4.verify_provenance(root, records=private_records),
    }
    if any(
        freeze.get("provenance_sha256", {}).get(name) != value
        for name, value in provenance.items()
    ):
        raise ValueError("SHA-256 da proveniência R4 divergiu do freeze final.")
    recorded = freeze.get("artifact_sha256", {})
    if set(recorded) != set(ARTIFACT_PATHS) or any(
        recorded[name] != provenance[name] for name in ARTIFACT_PATHS
    ):
        raise ValueError("Inventário/SHA-256 de artefatos Edge R4 divergente.")
    edge = json.loads(
        r4._safe_path(public_root, records["edge_freeze"][0]).read_bytes()
    )
    r4.validate_policy(edge)
    implementation = r4._validate_positive_config(
        root,
        json.loads(r4._safe_path(root, records["edge_config"][0]).read_bytes()),
        implementation_root=Path(__file__).resolve().parents[1],
    )
    if (
        ort.__version__ != EXPECTED_RUNTIME
        or "CPUExecutionProvider" not in ort.get_available_providers()
    ):
        raise ValueError("ONNX Runtime 1.30.0/CPUExecutionProvider indisponível.")
    return {
        "candidate_id": CANDIDATE_ID,
        "k": K,
        "threshold": THRESHOLD,
        "operator": ">=",
        "freeze_sha256": freeze_sha256,
        "result_sha256": result_sha256,
        "edge_freeze_sha256": provenance["edge_freeze"],
        "pipeline_fingerprint_sha256": r4.PIPELINE_FINGERPRINT,
        "artifact_sha256": dict(recorded),
        "provenance_sha256": provenance,
        "implementation_sha256": implementation,
        "runtime": EXPECTED_RUNTIME,
        "provider": "CPUExecutionProvider",
    }


def load_live_pipeline(root: Path):
    """Reutiliza o runtime R4 congelado; não aciona o evaluator held-out."""
    root = Path(root).resolve()
    verify_frozen_sources(root)
    return r4._load_runtime({"root": root})


def validate_camera_index(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("O índice da câmera deve ser um inteiro não negativo.")
    return value


def open_camera(index: int, *, backend: str | None = None):
    """Abre Iriun/OpenCV e exige frame 640×480; não grava."""
    validate_camera_index(index)
    backends = {
        "ANY": cv2.CAP_ANY,
        "DSHOW": cv2.CAP_DSHOW,
        "MSMF": cv2.CAP_MSMF,
    }
    if backend is None:
        selected_backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
    else:
        if backend not in backends:
            raise ValueError("O backend da câmera deve ser ANY, DSHOW ou MSMF.")
        selected_backend = backends[backend]
    camera = cv2.VideoCapture(index, selected_backend)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(f"Não foi possível abrir a câmera no índice {index}.")
    try:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        success, frame = camera.read()
        if not success or frame is None:
            raise RuntimeError("A câmera abriu, mas não entregou frames.")
        if frame.shape[:2] != (CAMERA_HEIGHT, CAMERA_WIDTH):
            raise RuntimeError(
                "A câmera deve entregar frames 640×480 em enquadramento 4:3."
            )
    except Exception:
        camera.release()
        raise
    return camera


def check_camera(index: int) -> dict:
    """Lê somente um frame para validar a câmera configurada."""
    camera = open_camera(index)
    try:
        return {
            "camera_index": index,
            "width": CAMERA_WIDTH,
            "height": CAMERA_HEIGHT,
            "fps_nominal": CAMERA_FPS,
        }
    finally:
        camera.release()


def ensure_diagnostic_path(root: Path, path: Path) -> Path:
    """Restringe acessos à área diagnóstica ignorada, sem base redirecionada."""
    root = Path(root).resolve()
    expected_base = root / DIAGNOSTIC_ROOT
    base = expected_base.resolve()
    if base != expected_base:
        raise ValueError("A área diagnóstica não pode ser redirecionada por links.")
    target = Path(path).resolve()
    if not target.is_relative_to(base):
        raise ValueError("Live Tester não pode acessar dataset ou artefato científico.")
    relative = target.relative_to(base)
    if len(relative.parts) < 2 or relative.parts[0] not in {
        "tmp",
        "clips",
        "logs",
    }:
        raise ValueError("Path fora da área diagnóstica do Live Tester.")
    return target


def clip_path(root: Path, session_id: str, number: int, *, keep: bool) -> Path:
    """Gera nome único por sessão/trial em pasta própria, sem sobrescrita."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id) or number < 1:
        raise ValueError("ID de sessão ou número de trial inválido.")
    folder = "clips" if keep else "tmp"
    relative = DIAGNOSTIC_ROOT / folder / f"{session_id}_{number:03d}.mp4"
    return ensure_diagnostic_path(root, Path(root) / relative)


_temporary_ownership = threading.local()


def _owned_clips():
    if not hasattr(_temporary_ownership, "clips"):
        _temporary_ownership.clips = {}
    return _temporary_ownership.clips


def cleanup_temporary_clip(root: Path, path: Path) -> None:
    """Remove somente o MP4 temporário e seu timing criado pelo Live Tester."""
    target = ensure_diagnostic_path(root, path)
    temporary = (Path(root).resolve() / DIAGNOSTIC_ROOT / "tmp").resolve()
    if not target.is_relative_to(temporary):
        raise ValueError("Somente clipe temporário pode ser removido.")
    identities = _owned_clips().pop(target, None)
    if identities is None:
        return
    for candidate, identity in zip((target, temporal.sidecar_path(target)), identities):
        if not candidate.is_symlink() and candidate.exists():
            current = candidate.stat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                candidate.unlink()


def mark_retained_clip(root: Path, path: Path) -> Path:
    """Cria marcador auditável de demo ao lado de um vídeo retido."""
    target = ensure_diagnostic_path(root, path)
    retained = (Path(root).resolve() / DIAGNOSTIC_ROOT / "clips").resolve()
    if not target.is_relative_to(retained) or not target.is_file():
        raise ValueError("Clipe retido inválido ou fora da pasta diagnóstica.")
    sidecar = target.with_suffix(".json")
    payload = {
        "clip": target.name,
        "scientific_status": SCIENTIFIC_STATUS,
        "tester_version": TESTER_VERSION,
        "rejection_version": "R4",
        "candidate_id": CANDIDATE_ID,
    }
    with sidecar.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return sidecar


def infer_clip(
    pipeline,
    video: Path,
    sample_id: str,
    session_id: str,
    *,
    root: Path | None = None,
) -> dict:
    """Consulta somente clipe casual, com preprocessing/scorer R4 congelados."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    video = ensure_diagnostic_path(root, video)
    relative = video.relative_to((root / DIAGNOSTIC_ROOT).resolve())
    if relative.parts[0] not in {"tmp", "clips"} or video.suffix.lower() != ".mp4":
        raise ValueError("Inferência aceita somente MP4 da área casual do tester.")
    started = time.perf_counter()
    row = {
        "sample_id": sample_id,
        "session_id": session_id,
        "sample_kind": "UNKNOWN",
        "expected_label": "UNKNOWN",
    }
    prediction = pipeline.predict(row, video)
    processing_ms = (time.perf_counter() - started) * 1000
    label = prediction["predicted_label"]
    score = prediction["score"]
    decision = r4.decision_for_score(score)
    if (
        label not in DEFAULT_VISUAL_LABELS
        or type(prediction.get("predicted_label_index")) is not int
        or prediction.get("predicted_label_index") != DEFAULT_VISUAL_LABELS.index(label)
        or any(
            prediction.get(key) != "PASS"
            for key in ("decode_status", "roi_status", "inference_status")
        )
        or type(prediction.get("segmentation_fallback")) is not bool
        or prediction.get("segmentation_status")
        != ("FALLBACK" if prediction["segmentation_fallback"] else "DETECTED")
    ):
        raise ValueError("Saída da inferência divergiu do contrato R4 congelado.")
    logits = prediction.get("logits")
    second = None
    if (
        isinstance(logits, list)
        and len(logits) == len(DEFAULT_VISUAL_LABELS)
        and all(
            isinstance(value, (int, float)) and math.isfinite(value) for value in logits
        )
    ):
        second_index = sorted(
            range(len(logits)), key=lambda index: logits[index], reverse=True
        )[1]
        second = DEFAULT_VISUAL_LABELS[second_index]
    return {
        "sample_id": sample_id,
        "predicted_label": label,
        "second_best_label": second,
        "score": score,
        "threshold": THRESHOLD,
        "decision": decision,
        "emitted_label": label if decision == "ACCEPT" else None,
        "segmentation_status": prediction["segmentation_status"],
        "segmentation_fallback": prediction["segmentation_fallback"],
        "source_frame_count": prediction["source_frame_count"],
        "end_to_end_latency_ms": processing_ms,
        "runtime": f"ONNX Runtime {ort.__version__} / CPUExecutionProvider",
    }


def format_result_lines(trial: dict, *, debug: bool) -> list[str]:
    """Identifica R4 e distingue hipótese interna de palavra emitida."""
    result = trial["emitted_label"] or "REJEITADO"
    lines = [
        "Live Visual Tester — Rejection 4",
        (
            f"REJECT — hipótese interna: {trial['predicted_label']}"
            if trial["decision"] == "REJECT"
            else f"ACCEPT — predição visual: {trial['predicted_label']}"
        ),
        f"Resultado: {result}",
        f"Score R4 de similaridade: {trial['score']:.6f}",
        f"Threshold R4: {trial['threshold']:.16f}",
        f"Latência: {trial['end_to_end_latency_ms']:.0f} ms",
    ]
    if debug:
        if trial.get("second_best_label"):
            lines.append(f"Segundo candidato: {trial['second_best_label']}")
        lines.extend(
            [
                f"Margin: {trial['score'] - trial['threshold']:+.6f}",
                f"Segmentação: {trial['segmentation_status']}",
                f"Fallback: {'SIM' if trial['segmentation_fallback'] else 'NÃO'}",
                f"Frames: {trial['source_frame_count']}",
                trial.get("runtime", "ONNX Runtime 1.30.0 / CPUExecutionProvider"),
            ]
        )
    return lines


def build_log_record(
    trial: dict,
    *,
    timestamp_utc: str,
    camera_index: int,
    clip_retained: bool,
    clip_path: Path | None,
    sources: dict | None = None,
) -> dict:
    """Constrói log de demo sem ground truth ou métrica de acurácia."""
    return {
        "timestamp_utc": timestamp_utc,
        "tester_version": TESTER_VERSION,
        "scientific_status": SCIENTIFIC_STATUS,
        "rejection_version": "R4",
        "candidate_id": CANDIDATE_ID,
        "k": K,
        "operator": ">=",
        "r4_final_freeze_sha256": FINAL_FREEZE_SHA256,
        "edge_freeze_sha256": EXPECTED_EDGE_FREEZE_SHA256,
        "pipeline_fingerprint_sha256": r4.PIPELINE_FINGERPRINT,
        "edge_artifact_sha256": (sources["artifact_sha256"] if sources else None),
        "provenance_sha256": (sources["provenance_sha256"] if sources else None),
        "camera": {
            "index": validate_camera_index(camera_index),
            "width": CAMERA_WIDTH,
            "height": CAMERA_HEIGHT,
            "fps_nominal": CAMERA_FPS,
        },
        "sample_id": trial.get("sample_id"),
        "predicted_label": trial["predicted_label"],
        "second_best_label": trial.get("second_best_label"),
        "score": trial["score"],
        "threshold": trial["threshold"],
        "decision": trial["decision"],
        "emitted_label": trial["emitted_label"],
        "segmentation_status": trial["segmentation_status"],
        "segmentation_fallback": trial["segmentation_fallback"],
        "source_frame_count": trial["source_frame_count"],
        "capture_timing": trial.get("capture_timing"),
        "end_to_end_latency_ms": trial["end_to_end_latency_ms"],
        "runtime": trial.get("runtime", "ONNX Runtime 1.30.0 / CPUExecutionProvider"),
        "clip_retained": clip_retained,
        "clip_path": str(clip_path) if clip_retained and clip_path else None,
    }


def serialize_log_record(record: dict) -> bytes:
    """JSONL determinístico para o mesmo registro, UTF-8 com LF."""
    return (
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def append_log(path: Path, record: dict) -> None:
    with Path(path).open("ab") as stream:
        stream.write(serialize_log_record(record))


def summarize_session(records: list[dict]) -> dict:
    """Resume decisões observadas sem atribuir ground truth ou acurácia."""
    count = Counter(record["decision"] for record in records)
    labels = Counter(record["predicted_label"] for record in records)
    latencies = [record["end_to_end_latency_ms"] for record in records]
    return {
        "total": len(records),
        "accepted": count["ACCEPT"],
        "rejected": count["REJECT"],
        "predicted_labels": dict(sorted(labels.items())),
        "median_end_to_end_latency_ms": (
            statistics.median(latencies) if latencies else None
        ),
    }


def _exit_key(key: int) -> bool:
    return key in (27, ord("q"), ord("Q"))


def record_clip(
    camera,
    path: Path,
    *,
    clock_ns=time.perf_counter_ns,
    show_frame=None,
    read_key=None,
    diagnostic_callback=None,
    cleanup_on_error=True,
) -> dict:
    """Valida aquisição monotônica e grava 121 posições temporais a 30 FPS."""
    path = Path(path)
    _owned_clips().pop(path.resolve(), None)
    if path.exists() or temporal.sidecar_path(path).exists():
        raise FileExistsError(f"Clipe de demo já existe: {path}")
    policy = temporal.load_policy(version=2)
    frames = []
    timestamps_ns = []
    duration_ns = int(policy["acquisition_seconds"] * 1_000_000_000)
    while True:
        read_start_ns = time.perf_counter_ns() if diagnostic_callback else None
        success, frame = camera.read()
        read_end_ns = time.perf_counter_ns() if diagnostic_callback else None
        if not success or frame is None:
            if diagnostic_callback:
                diagnostic_callback(
                    {
                        "kind": "read",
                        "read_status": "READ_FAILURE",
                        "frame_index": len(frames),
                        "read_start_ns": read_start_ns,
                        "read_end_ns": read_end_ns,
                        "policy_timestamp_ns": None,
                        "copy_start_ns": None,
                        "copy_end_ns": None,
                        "ui_update_start_ns": None,
                        "ui_update_end_ns": None,
                    }
                )
            raise TemporalCaptureError("Falha de leitura da câmera; sem inferência.")
        timestamp_ns = clock_ns()
        if frame.shape != (CAMERA_HEIGHT, CAMERA_WIDTH, 3):
            if diagnostic_callback:
                diagnostic_callback(
                    {
                        "kind": "read",
                        "read_status": "INVALID_FRAME_SHAPE",
                        "frame_index": len(frames),
                        "read_start_ns": read_start_ns,
                        "read_end_ns": read_end_ns,
                        "policy_timestamp_ns": None,
                        "copy_start_ns": None,
                        "copy_end_ns": None,
                        "ui_update_start_ns": None,
                        "ui_update_end_ns": None,
                    }
                )
            raise TemporalCaptureError("A captura deve ser BGR 640×480.")
        copy_start_ns = time.perf_counter_ns() if diagnostic_callback else None
        frames.append(frame.copy())
        copy_end_ns = time.perf_counter_ns() if diagnostic_callback else None
        timestamps_ns.append(timestamp_ns)
        elapsed_ns = timestamp_ns - timestamps_ns[0]
        ui_update_start_ns = time.perf_counter_ns() if diagnostic_callback else None
        if show_frame is not None:
            show_frame(
                frame, max(0.0, policy["acquisition_seconds"] - elapsed_ns / 1e9)
            )
        if diagnostic_callback:
            diagnostic_callback(
                {
                    "kind": "read",
                    "read_status": "OK",
                    "frame_index": len(frames) - 1,
                    "read_start_ns": read_start_ns,
                    "read_end_ns": read_end_ns,
                    "policy_timestamp_ns": timestamp_ns,
                    "copy_start_ns": copy_start_ns,
                    "copy_end_ns": copy_end_ns,
                    "ui_update_start_ns": ui_update_start_ns,
                    "ui_update_end_ns": time.perf_counter_ns(),
                }
            )
        if elapsed_ns >= duration_ns:
            break
        if read_key is not None and _exit_key(read_key()):
            raise CaptureCancelled("Gravação cancelada pelo operador.")
    try:
        report = temporal.analyze_timestamps(timestamps_ns, policy)
    except ValueError as error:
        raise TemporalCaptureError(
            f"Timestamps de captura inválidos: {error}"
        ) from error
    if diagnostic_callback:
        diagnostic_callback(
            {
                "kind": "gate",
                "source_frame_count": report["source_frame_count"],
                "acquisition_duration_seconds": report["acquisition_duration_seconds"],
                "source_fps_effective": report["source_fps_effective"],
                "max_source_gap_seconds": report["max_source_gap_seconds"],
                "hold_count": report["hold_count"],
                "technical_decision": report["technical_decision"],
                "technical_failures": report["technical_failures"],
            }
        )
    if report["technical_decision"] != "PASS":
        reasons = ", ".join(report["technical_failures"])
        raise TemporalCaptureError(
            f"Gate temporal bloqueou: {reasons}; "
            f"{report['source_frame_count']} frames, "
            f"{report['acquisition_duration_seconds']:.3f} s, "
            f"{report['source_fps_effective']:.2f} FPS."
        )

    def remember_ownership(video_identity, sidecar_identity):
        if cleanup_on_error:
            _owned_clips()[path.resolve()] = (video_identity, sidecar_identity)

    return temporal.write_video_with_sidecar(
        path,
        frames,
        timestamps_ns,
        policy,
        cleanup_on_error=cleanup_on_error,
        ownership_callback=remember_ownership,
    )


def _ascii_for_opencv(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()


def _show_overlay(frame, lines: list[str], *, compact: bool) -> None:
    """Mostra as instruções ao lado da câmera, sem cobrir rosto ou boca."""
    height = frame.shape[0]
    panel = np.full((height, 480, 3), (24, 24, 24), dtype=np.uint8)
    line_height = 23
    top = 0 if compact else 12
    for index, line in enumerate(lines):
        y = top + 24 + index * line_height
        if y >= height:
            break
        cv2.putText(
            panel,
            _ascii_for_opencv(line),
            (12, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    canvas = np.concatenate((frame, panel), axis=1)
    cv2.imshow(WINDOW_NAME, canvas)


def _countdown(camera) -> None:
    started = time.perf_counter()
    while True:
        remaining = 3.0 - (time.perf_counter() - started)
        if remaining <= 0:
            return
        success, frame = camera.read()
        if not success or frame is None:
            raise RuntimeError("Câmera falhou durante o countdown.")
        _show_overlay(frame, [f"Prepare-se: {math.ceil(remaining)}"], compact=True)
        if _exit_key(cv2.waitKey(1) & 0xFF):
            raise CaptureCancelled("Countdown cancelado pelo operador.")


def _new_session_id() -> str:
    return "live_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def run_live_session(
    root: Path, *, camera_index: int = 1, debug: bool = False, keep_clips: bool = False
) -> dict:
    """Loop SPACE → captura → inferência → resultado até ESC/Q."""
    root = Path(root).resolve()
    sources = verify_frozen_sources(root)
    pipeline = load_live_pipeline(root)
    camera = open_camera(camera_index)
    session_id = _new_session_id()
    log_path = ensure_diagnostic_path(
        root,
        root / DIAGNOSTIC_ROOT / "logs" / f"live_visual_tester_{session_id}.jsonl",
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    current_trial = None
    capture_error = None
    trial_number = 0
    window_open = False
    try:
        log_path.touch(exist_ok=False)
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        window_open = True
        while True:
            success, frame = camera.read()
            if not success or frame is None:
                raise RuntimeError("Câmera parou de entregar frames.")
            if capture_error is not None:
                lines = [
                    f"Erro técnico de captura: {capture_error}",
                    "ESPAÇO — repetir | ESC/Q — sair",
                ]
                _show_overlay(frame, lines, compact=False)
            elif current_trial is None:
                lines = [
                    "Live Visual Tester — Rejection 4",
                    "ESPAÇO — testar",
                    "D — modo debug | ESC/Q — sair",
                ]
                _show_overlay(frame, lines, compact=True)
            else:
                lines = format_result_lines(current_trial, debug=debug)
                lines.append("ESPAÇO — novo teste | D — debug | ESC/Q — sair")
                _show_overlay(frame, lines, compact=False)
            key = cv2.waitKey(1) & 0xFF
            if _exit_key(key):
                break
            if key in (ord("d"), ord("D")):
                debug = not debug
                continue
            if key != 32:
                continue
            capture_error = None
            _countdown(camera)
            trial_number += 1
            video = clip_path(root, session_id, trial_number, keep=keep_clips)
            video.parent.mkdir(parents=True, exist_ok=True)
            clip_created = False
            try:
                timing = record_clip(
                    camera,
                    video,
                    cleanup_on_error=not keep_clips,
                    show_frame=lambda image, remaining: _show_overlay(
                        image, [f"GRAVANDO: {remaining:.1f} s"], compact=True
                    ),
                    read_key=lambda: cv2.waitKey(1) & 0xFF,
                )
                clip_created = True
                if keep_clips:
                    mark_retained_clip(root, video)
                _show_overlay(frame, ["PROCESSANDO..."], compact=True)
                cv2.waitKey(1)
                sample_id = f"{session_id}_{trial_number:03d}"
                current_trial = infer_clip(
                    pipeline, video, sample_id, session_id, root=root
                )
                current_trial["recorded_frame_count"] = timing["output_frame_count"]
                current_trial["capture_timing"] = timing
                record = build_log_record(
                    current_trial,
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    camera_index=camera_index,
                    clip_retained=keep_clips,
                    clip_path=video if keep_clips else None,
                    sources=sources,
                )
                append_log(log_path, record)
                records.append(record)
            except CaptureCancelled:
                raise
            except TemporalCaptureError as error:
                current_trial = None
                capture_error = str(error)
                print(f"Erro técnico de captura: {error}")
            except Exception as error:
                _show_overlay(frame, [f"Erro técnico: {error}"], compact=False)
                cv2.waitKey(1800)
                raise
            finally:
                if not keep_clips and clip_created:
                    cleanup_temporary_clip(root, video)
    except CaptureCancelled:
        print("Captura encerrada pelo operador.")
    finally:
        camera.release()
        if window_open:
            cv2.destroyWindow(WINDOW_NAME)
    summary = summarize_session(records)
    print(f"Testes: {summary['total']}")
    print(f"Aceitos: {summary['accepted']} | Rejeitados: {summary['rejected']}")
    print(f"Predições visuais: {summary['predicted_labels']}")
    if summary["median_end_to_end_latency_ms"] is not None:
        print(
            "Latência mediana de processamento: "
            f"{summary['median_end_to_end_latency_ms']:.0f} ms"
        )
    print(f"Log de demo: {log_path}")
    return {"summary": summary, "log_path": log_path}
