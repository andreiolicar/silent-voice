"""Aquisição monotônica e normalização CFR opt-in para MSV.1B."""

from bisect import bisect_right
import hashlib
import json
import math
from pathlib import Path
import time

import cv2


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path("docs/cycles/multispeaker_visual_01_temporal_policy.json")
POLICY_SHA256 = "204ebd508b6464acbb6f4311784b1d6f09330f8750268731310184cbbde47edb"
POLICY_V2_PATH = Path("docs/cycles/multispeaker_visual_01_temporal_policy_v2.json")
POLICY_V2_SHA256 = "7e113726683b58ecec1c906c7017a0bcb34833a4c20ee7f53ede307281831246"
POLICY_V2_FILE_SHA256 = (
    "4680a3fb47866d470fb98223c8f8d654d19150905d4ba7289096e80d8a6f39a1"
)


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def policy_fingerprint(policy: dict) -> str:
    return hashlib.sha256(canonical_bytes(policy)).hexdigest()


def load_policy(root: Path = ROOT, *, version: int = 1) -> dict:
    if version not in (1, 2):
        raise ValueError("Versão da policy temporal não suportada.")
    path = Path(root) / (POLICY_PATH if version == 1 else POLICY_V2_PATH)
    policy = json.loads(path.read_bytes())
    expected_version = f"MSV_01_TEMPORAL_V{version}"
    expected_sha = POLICY_SHA256 if version == 1 else POLICY_V2_SHA256
    if (
        policy.get("version") != expected_version
        or policy.get("format_version") != 1
        or policy.get("required_frame_size") != [640, 480]
        or policy.get("output_fps") != 30
        or policy.get("output_frame_count") != 121
        or policy.get("acquisition_seconds") != 4.0
        or policy.get("time_source") != "perf_counter_ns"
        or policy_fingerprint(policy) != expected_sha
        or (version == 2 and sha256_file(path) != POLICY_V2_FILE_SHA256)
        or (
            version == 2
            and (
                policy.get("max_hold_positions") != 24
                or policy.get("conditional_hold_max_positions") != 32
                or policy.get("conditional_minimum_source_fps") != 29.0
                or policy.get("conditional_max_source_gap_seconds") != 0.05
                or policy.get("conditional_minimum_frames_per_second") != 27
            )
        )
    ):
        raise ValueError("Policy temporal MSV ausente ou modificada.")
    return policy


def sidecar_path(video: Path) -> Path:
    return Path(str(video) + ".timing.json")


def analyze_timestamps(
    timestamps_ns: list[int],
    policy: dict,
    *,
    read_failures: int = 0,
    interrupted: bool = False,
) -> dict:
    """Mapeia a grade 0..4 s ao último frame real disponível."""
    if (
        not isinstance(timestamps_ns, list)
        or len(timestamps_ns) < 2
        or any(type(value) is not int or value < 0 for value in timestamps_ns)
        or any(b <= a for a, b in zip(timestamps_ns, timestamps_ns[1:]))
    ):
        raise ValueError("timestamps de aquisição ausentes ou fora de ordem.")
    if type(read_failures) is not int or read_failures < 0:
        raise ValueError("Contagem de falhas de leitura inválida.")
    relative = [value - timestamps_ns[0] for value in timestamps_ns]
    duration = relative[-1] / 1e9
    intervals = [(b - a) / 1e9 for a, b in zip(relative, relative[1:])]
    fps = (len(relative) - 1) / duration
    output_count = policy["output_frame_count"]
    output_fps = policy["output_fps"]
    targets = [round(i * 1e9 / output_fps) for i in range(output_count)]
    mapping = [max(0, bisect_right(relative, target) - 1) for target in targets]
    source_to_output = [[] for _ in relative]
    for output_index, source_index in enumerate(mapping):
        source_to_output[source_index].append(output_index)
    holds = sum(a == b for a, b in zip(mapping, mapping[1:]))
    playback = output_count / output_fps
    failures = []
    if interrupted:
        failures.append("recording_interrupted")
    if read_failures:
        failures.append("source_read_failure")
    if duration < policy["acquisition_seconds"]:
        failures.append("acquisition_too_short")
    if duration > (
        policy["acquisition_seconds"] + policy["max_capture_overrun_seconds"]
    ):
        failures.append("acquisition_too_long")
    if fps < policy["minimum_source_fps"]:
        failures.append("source_fps_below_minimum")
    if max(intervals) > policy["max_source_gap_seconds"]:
        failures.append("source_gap_above_maximum")
    conditional = policy["version"] == "MSV_01_TEMPORAL_V2"
    frames_per_second = (
        [
            sum(second <= value / 1e9 < second + 1 for value in relative)
            for second in range(4)
        ]
        if conditional
        else None
    )
    if holds > policy["max_hold_positions"]:
        if not conditional or holds > policy["conditional_hold_max_positions"]:
            failures.append("hold_count_above_maximum")
        else:
            if fps < policy["conditional_minimum_source_fps"]:
                failures.append("conditional_source_fps_below_minimum")
            if max(intervals) > policy["conditional_max_source_gap_seconds"]:
                failures.append("conditional_source_gap_above_maximum")
            if min(frames_per_second) < policy["conditional_minimum_frames_per_second"]:
                failures.append("conditional_sustained_frame_loss")
    if abs(playback - duration) > policy["max_acquisition_playback_difference_seconds"]:
        failures.append("acquisition_playback_mismatch")
    report = {
        "acquisition_duration_seconds": duration,
        "source_frame_count": len(relative),
        "source_timestamps_relative_ns": relative,
        "source_intervals_seconds": intervals,
        "source_fps_effective": fps,
        "max_source_gap_seconds": max(intervals),
        "output_frame_count": output_count,
        "output_fps": output_fps,
        "playback_duration_seconds": playback,
        "output_to_source_index": mapping,
        "source_to_output_indices": source_to_output,
        "hold_count": holds,
        "read_failures": read_failures,
        "interrupted": interrupted,
        "technical_failures": failures,
        "technical_decision": "BLOCKED" if failures else "PASS",
    }
    if conditional:
        report["source_frames_per_second"] = frames_per_second
        report["distinct_output_source_frames"] = len(set(mapping))
    return report


def write_video_with_sidecar(
    video: Path,
    frames: list,
    timestamps_ns: list[int],
    policy: dict,
    *,
    read_failures: int = 0,
    interrupted: bool = False,
) -> dict:
    """Escreve vídeo e sidecar sem sobrescrever um attempt existente."""
    video = Path(video)
    sidecar = sidecar_path(video)
    if video.exists() or sidecar.exists():
        raise FileExistsError("Attempt ou sidecar temporal já existe.")
    if len(frames) != len(timestamps_ns) or not frames:
        raise ValueError("Frames e timestamps de aquisição divergentes.")
    width, height = policy["required_frame_size"]
    if any(frame.shape != (height, width, 3) for frame in frames):
        raise ValueError("Resolução/formato de frame divergente da policy.")
    report = analyze_timestamps(
        timestamps_ns, policy, read_failures=read_failures, interrupted=interrupted
    )
    video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(video),
        cv2.VideoWriter_fourcc(*policy["requested_fourcc"]),
        policy["output_fps"],
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError("Falha de codificação MP4 no attempt temporal.")
    try:
        for index in report["output_to_source_index"]:
            writer.write(frames[index])
    finally:
        writer.release()
    report.update(
        {
            "format_version": 1,
            "policy_version": policy["version"],
            "policy_sha256": policy_fingerprint(policy),
            "video_sha256": sha256_file(video),
        }
    )
    with sidecar.open("xb") as stream:
        stream.write(canonical_bytes(report))
    return report


def validate_video_sidecar(video: Path, policy: dict) -> dict:
    """Confere sidecar, MP4 decodificado e cálculos temporais independentes."""
    video = Path(video)
    sidecar = sidecar_path(video)
    if not video.is_file() or not sidecar.is_file():
        raise ValueError("Vídeo ou sidecar temporal ausente.")
    report = json.loads(sidecar.read_bytes())
    if (
        report.get("format_version") != 1
        or report.get("policy_version") != policy["version"]
        or report.get("policy_sha256") != policy_fingerprint(policy)
        or report.get("video_sha256") != sha256_file(video)
    ):
        raise ValueError("Hash/identidade do sidecar temporal divergente.")
    timestamps = report.get("source_timestamps_relative_ns")
    expected = analyze_timestamps(
        timestamps,
        policy,
        read_failures=report.get("read_failures"),
        interrupted=report.get("interrupted"),
    )
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Mapa ou duração do sidecar temporal divergente.")
    if expected["technical_decision"] != "PASS":
        raise ValueError(
            "Attempt temporal bloqueado: " + str(expected["technical_failures"])
        )
    capture = cv2.VideoCapture(str(video))
    try:
        if not capture.isOpened():
            raise ValueError("MP4 temporal não abriu.")
        fps = capture.get(cv2.CAP_PROP_FPS)
        declared = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        decoded = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame is None or frame.shape[:2] != (height, width):
                raise ValueError("MP4 temporal contém frame inválido.")
            decoded += 1
    finally:
        capture.release()
    if (
        not math.isfinite(fps)
        or abs(fps - policy["output_fps"]) > 1e-6
        or [width, height] != policy["required_frame_size"]
        or declared != policy["output_frame_count"]
        or decoded != declared
        or abs(decoded / fps - expected["playback_duration_seconds"]) > 1e-6
    ):
        raise ValueError("FPS, resolução, duração ou contagem MP4 divergente.")
    return report


def record_sample(
    camera, row: dict, video: Path, policy: dict, window_name: str
) -> bool:
    """Coleta quatro segundos reais após countdown; bloqueios viram .partial."""
    video = Path(video)
    partial = video.with_name(video.stem + ".partial.mp4")
    if video.exists() or partial.exists():
        raise FileExistsError("Attempt temporal existente exige auditoria.")
    prompt = row["oov_prompt"] or row["label_or_category"]
    action = (
        "ACAO CONGELADA"
        if row["kind"] == "UNKNOWN" and row["oov_prompt"] is None
        else "ARTICULE UMA VEZ"
    )

    def show(frame, caption: str) -> int:
        preview = frame.copy()
        cv2.putText(
            preview,
            f"{row['order']}/24 {prompt}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            preview,
            caption,
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )
        cv2.imshow(window_name, preview)
        return cv2.waitKey(1) & 0xFF

    print("Preparar...", flush=True)
    countdown_start = time.perf_counter_ns()
    while (time.perf_counter_ns() - countdown_start) < 3_000_000_000:
        ok, frame = camera.read()
        if not ok or frame is None:
            raise RuntimeError("Falha na fonte Iriun antes da gravação.")
        remaining = max(0.0, 3.0 - (time.perf_counter_ns() - countdown_start) / 1e9)
        if show(frame, f"PREPARAR {math.ceil(remaining)}") == 27:
            return False
    print("GRAVANDO", flush=True)
    frames = []
    timestamps = []
    read_failures = 0
    interrupted = False
    while True:
        ok, frame = camera.read()
        timestamp = time.perf_counter_ns()
        if not ok or frame is None:
            read_failures += 1
            interrupted = True
            break
        frames.append(frame.copy())
        timestamps.append(timestamp)
        remaining = max(
            0.0, policy["acquisition_seconds"] - (timestamp - timestamps[0]) / 1e9
        )
        if show(frame, f"{action}: {remaining:.1f}s") == 27:
            interrupted = True
            break
        if (timestamp - timestamps[0]) / 1e9 >= policy["acquisition_seconds"]:
            break
    if len(frames) < 2:
        raise RuntimeError("Gravação sem frames suficientes para attempt parcial.")
    report = analyze_timestamps(
        timestamps, policy, read_failures=read_failures, interrupted=interrupted
    )
    write_video_with_sidecar(
        partial,
        frames,
        timestamps,
        policy,
        read_failures=read_failures,
        interrupted=interrupted,
    )
    if report["technical_decision"] == "PASS":
        try:
            validate_video_sidecar(partial, policy)
        except ValueError as exc:
            print(f"Codificação bloqueada; parcial preservada: {exc}", flush=True)
            return False
        if video.exists() or sidecar_path(video).exists():
            raise FileExistsError("Attempt final apareceu durante codificação.")
        partial.rename(video)
        sidecar_path(partial).rename(sidecar_path(video))
    print(
        f"Tempo real {report['acquisition_duration_seconds']:.3f}s; "
        f"FPS efetivo {report['source_fps_effective']:.2f}; "
        f"holds {report['hold_count']}; {report['technical_decision']}",
        flush=True,
    )
    return report["technical_decision"] == "PASS"
