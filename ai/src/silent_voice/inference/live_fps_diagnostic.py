"""Medições opcionais da aquisição visual, sem armazenar mídia."""

import json
from pathlib import Path
from queue import Empty, Queue
from statistics import mean
from threading import Event, Thread
from threading import Lock
import time
from uuid import uuid4

import cv2
import numpy as np

from scripts.demo import msv_temporal_capture as temporal
from silent_voice.inference.global_live_visual_tester import (
    capture_state,
    initial_state,
    render_dashboard,
)


class FpsCaptureTrace:
    """Agrupa tempos de uma tentativa e persiste somente metadados técnicos."""

    def __init__(self, root: Path, *, camera_index: int, mode: str) -> None:
        if mode not in {"NORMAL", "NO_REDRAW"}:
            raise ValueError("Modo de diagnóstico FPS inválido.")
        self.root = Path(root).resolve()
        self.attempt_id = uuid4().hex
        self.camera_index = camera_index
        self.mode = mode
        self.started_ns = time.perf_counter_ns()
        self._lock = Lock()
        self._reads: list[dict] = []
        self._ui_updates: list[dict] = []
        self._gate: dict | None = None
        self._active = True

    def record_capture(self, event: dict) -> None:
        with self._lock:
            if not self._active:
                return
            if event["kind"] == "read":
                self._reads.append(dict(event))
            elif event["kind"] == "gate":
                self._gate = dict(event)
                self._active = False

    def record_ui(self, start_ns: int, end_ns: int) -> None:
        with self._lock:
            if self._active:
                self._ui_updates.append({"start_ns": start_ns, "end_ns": end_ns})

    def finish(self, *, error: str | None = None) -> Path:
        """Fecha a tentativa em JSON exclusivo, inclusive quando o gate bloqueia."""
        with self._lock:
            self._active = False
            reads = list(self._reads)
            updates = list(self._ui_updates)
            gate = dict(self._gate) if self._gate is not None else None
        timestamps = [
            item["policy_timestamp_ns"]
            for item in reads
            if item.get("policy_timestamp_ns") is not None
        ]
        duration = (
            (timestamps[-1] - timestamps[0]) / 1e9 if len(timestamps) > 1 else None
        )
        fps = (len(timestamps) - 1) / duration if duration and duration > 0 else None
        payload = {
            "format_version": 1,
            "attempt_id": self.attempt_id,
            "camera_index": self.camera_index,
            "mode": self.mode,
            "clock": "perf_counter_ns",
            "started_ns": self.started_ns,
            "finished_ns": time.perf_counter_ns(),
            "reads": reads,
            "ui_updates": updates,
            "source_frame_count": len(timestamps),
            "acquisition_duration_seconds": duration,
            "source_fps_effective": fps,
            "gate": gate,
            "error": error,
        }
        folder = self.root / "data" / "processed" / "live_tester" / "logs"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"fps_diagnostic_{self.attempt_id}.json"
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        return path


def _measure_auto_attempt(camera, policy, trace, *, clock_ns, size):
    """Reproduz aquisição e atualização visual sem escrever MP4 ou inferir."""
    events = Queue()
    finished = Event()
    timestamps_ns = []
    errors = []
    duration_ns = int(policy["acquisition_seconds"] * 1_000_000_000)

    def acquire():
        try:
            while True:
                read_start_ns = time.perf_counter_ns()
                success, frame = camera.read()
                read_end_ns = time.perf_counter_ns()
                if not success or frame is None:
                    errors.append("Falha de leitura da câmera.")
                    trace.record_capture(
                        {
                            "kind": "read",
                            "read_status": "READ_FAILURE",
                            "frame_index": len(timestamps_ns),
                            "read_start_ns": read_start_ns,
                            "read_end_ns": read_end_ns,
                            "policy_timestamp_ns": None,
                        }
                    )
                    break
                if frame.shape != (480, 640, 3):
                    errors.append("A câmera deve entregar BGR 640×480.")
                    break
                stamp = clock_ns()
                copy_start_ns = time.perf_counter_ns()
                copied = frame.copy()
                copy_end_ns = time.perf_counter_ns()
                events.put(copied.copy())
                ui_update_end_ns = time.perf_counter_ns()
                trace.record_capture(
                    {
                        "kind": "read",
                        "read_status": "OK",
                        "frame_index": len(timestamps_ns),
                        "read_start_ns": read_start_ns,
                        "read_end_ns": read_end_ns,
                        "policy_timestamp_ns": stamp,
                        "copy_start_ns": copy_start_ns,
                        "copy_end_ns": copy_end_ns,
                        "ui_update_start_ns": copy_end_ns,
                        "ui_update_end_ns": ui_update_end_ns,
                    }
                )
                timestamps_ns.append(stamp)
                if stamp - timestamps_ns[0] >= duration_ns:
                    break
        except Exception as error:
            errors.append(str(error))
        finally:
            finished.set()

    worker = Thread(target=acquire, daemon=True)
    worker.start()
    last_frame = None
    state = capture_state(initial_state(trace.camera_index))
    try:
        while not finished.is_set() or not events.empty():
            while True:
                try:
                    last_frame = events.get_nowait()
                except Empty:
                    break
            if trace.mode == "NORMAL":
                ui_start_ns = time.perf_counter_ns()
                picture = render_dashboard(state, frame=last_frame, size=size)
                cv2.imshow(
                    "Silent Voice FPS automatic diagnostic",
                    cv2.cvtColor(np.asarray(picture), cv2.COLOR_RGB2BGR),
                )
                trace.record_ui(ui_start_ns, time.perf_counter_ns())
            cv2.waitKey(1)
    finally:
        worker.join()
    report = None
    if len(timestamps_ns) >= 2:
        report = temporal.analyze_timestamps(
            timestamps_ns, policy, read_failures=len(errors)
        )
        trace.record_capture(
            {
                "kind": "gate",
                **{
                    key: report[key]
                    for key in (
                        "source_frame_count",
                        "acquisition_duration_seconds",
                        "source_fps_effective",
                        "max_source_gap_seconds",
                        "hold_count",
                        "technical_decision",
                        "technical_failures",
                    )
                },
            }
        )
    path = trace.finish(error="; ".join(errors) if errors else None)
    payload = json.loads(path.read_text(encoding="utf-8"))
    read_ms = [
        (item["read_end_ns"] - item["read_start_ns"]) / 1e6 for item in payload["reads"]
    ]
    copy_ms = [
        (item["copy_end_ns"] - item["copy_start_ns"]) / 1e6
        for item in payload["reads"]
        if item.get("copy_start_ns") is not None
    ]
    ui_ms = [
        (item["end_ns"] - item["start_ns"]) / 1e6 for item in payload["ui_updates"]
    ]
    return {
        "mode": trace.mode,
        "attempt_id": trace.attempt_id,
        "trace_path": str(path),
        "source_frame_count": len(timestamps_ns),
        "read_failures": len(errors),
        "gate": report["technical_decision"] if report else "BLOCKED",
        "technical_failures": (
            report["technical_failures"] if report else ["insufficient_frames"]
        ),
        "source_fps_effective": report["source_fps_effective"] if report else None,
        "acquisition_duration_seconds": (
            report["acquisition_duration_seconds"] if report else None
        ),
        "max_source_gap_seconds": report["max_source_gap_seconds"] if report else None,
        "hold_count": report["hold_count"] if report else None,
        "read_mean_ms": mean(read_ms) if read_ms else None,
        "copy_mean_ms": mean(copy_ms) if copy_ms else None,
        "ui_mean_ms": mean(ui_ms) if ui_ms else None,
        "error": "; ".join(errors) if errors else None,
    }


def run_auto_fps_diagnostic(
    root,
    *,
    camera_index=1,
    camera_backend=None,
    camera_opener=None,
    clock_ns=time.perf_counter_ns,
    warmup_frames=30,
):
    """Compara A/B/A/B na câmera, sem teclas, modelos ou mídia persistida."""
    if camera_opener is None:
        from silent_voice.inference import live_visual_tester

        if camera_backend is None:
            camera_opener = live_visual_tester.open_camera
        else:

            def camera_opener(index):
                return live_visual_tester.open_camera(index, backend=camera_backend)

    policy = temporal.load_policy(version=2)
    camera = camera_opener(camera_index)
    window_created = False
    try:
        for _ in range(warmup_frames):
            success, frame = camera.read()
            if not success or frame is None or frame.shape != (480, 640, 3):
                raise RuntimeError("A câmera falhou durante o aquecimento diagnóstico.")
        name = "Silent Voice FPS automatic diagnostic"
        cv2.namedWindow(name, cv2.WINDOW_NORMAL)
        window_created = True
        size = (1280, 720)
        cv2.resizeWindow(name, *size)
        negotiated = {
            "fps": camera.get(cv2.CAP_PROP_FPS),
            "width": camera.get(cv2.CAP_PROP_FRAME_WIDTH),
            "height": camera.get(cv2.CAP_PROP_FRAME_HEIGHT),
            "fourcc": int(camera.get(cv2.CAP_PROP_FOURCC)),
        }
        attempts = []
        for mode in ("NORMAL", "NO_REDRAW", "NORMAL", "NO_REDRAW"):
            trace = FpsCaptureTrace(root, camera_index=camera_index, mode=mode)
            attempt = _measure_auto_attempt(
                camera, policy, trace, clock_ns=clock_ns, size=size
            )
            attempts.append(attempt)
            if attempt["error"] is not None:
                break
        return {
            "camera_index": camera_index,
            "negotiated": negotiated,
            "attempts": attempts,
        }
    finally:
        camera.release()
        if window_created:
            cv2.destroyWindow(name)
