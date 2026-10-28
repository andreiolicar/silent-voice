"""Dataset derivado de ROI labial, sem inferência de modelo."""

import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from silent_voice.vision.dataset_collection_plan import (
    VisualCollectionPlanItem,
    build_visual_collection_plan,
)
from silent_voice.vision.detector import MediaPipeMouthDetector
from silent_voice.vision.feature_sample_storage import load_visual_feature_sample
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


FORMAT_VERSION = 1
ROI_SIZE = 96
ROI_COLOR_MODE = "GRAYSCALE"
ROI_RELATIVE_ROOT = Path("data/processed/visual_mouth_roi")
MANIFEST_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_mouth_roi_manifest.json"
)
CONTACT_SHEET_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_mouth_roi_contact_sheet.png"
)
FORBIDDEN_SESSIONS = ("sessao_04", "rejeicao_heldout_01")


@dataclass(frozen=True, slots=True)
class MouthRoiConfig:
    """Parâmetros geométricos pré-definidos, independentes de accuracy."""

    crop_scale: float = 1.6
    smoothing_window: int = 5
    max_missing_rate: float = 0.10
    max_consecutive_missing: int = 3

    def __post_init__(self) -> None:
        if not math.isfinite(self.crop_scale) or self.crop_scale <= 1.0:
            raise ValueError("crop_scale deve ser finito e maior que um.")
        if self.smoothing_window < 1 or self.smoothing_window % 2 == 0:
            raise ValueError("smoothing_window deve ser positivo e ímpar.")
        if not 0.0 <= self.max_missing_rate < 1.0:
            raise ValueError("max_missing_rate deve estar em [0, 1).")
        if self.max_consecutive_missing < 0:
            raise ValueError("max_consecutive_missing não pode ser negativo.")


@dataclass(frozen=True, slots=True)
class MouthRoiSample:
    format_version: int
    sample_id: str
    label: str
    label_index: int
    session_id: str
    source_video_path: str
    source_video_sha256: str
    source_npz_path: str
    source_npz_sha256: str
    frame_count: int
    fps: float
    roi_height: int
    roi_width: int
    color_mode: str
    dtype: str
    frame_indices: np.ndarray
    timestamps_ms: np.ndarray
    mouth_rois: np.ndarray
    detection_valid_mask: np.ndarray
    crop_centers_xy: np.ndarray
    crop_angles_deg: np.ndarray
    crop_side_px: float
    decoded_frame_count: int
    detected_landmark_frame_count: int
    missing_detection_count: int
    missing_detection_rate: float
    max_consecutive_missing: int
    preprocessing_config: MouthRoiConfig


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plan() -> tuple[VisualCollectionPlanItem, ...]:
    return build_visual_collection_plan(SESSION_IDS, DEFAULT_VISUAL_LABELS, 3)


def _label_directory(item: VisualCollectionPlanItem) -> str:
    return item.sample_id.split("_")[0].upper()


def _source_paths(
    repository_root: Path, item: VisualCollectionPlanItem
) -> tuple[Path, Path]:
    folder = _label_directory(item)
    video = (
        repository_root
        / "data/raw/visual_dataset"
        / item.session_id
        / folder
        / f"{item.sample_id}.mp4"
    )
    feature = (
        repository_root / "data/processed/visual" / folder / f"{item.sample_id}.npz"
    )
    return video, feature


def _max_missing_run(mask: np.ndarray) -> int:
    maximum = current = 0
    for detected in mask:
        current = 0 if detected else current + 1
        maximum = max(maximum, current)
    return maximum


def _smooth(values: np.ndarray, window: int) -> np.ndarray:
    if window == 1:
        return values.copy()
    padding = window // 2
    padded = np.pad(values, (padding, padding), mode="edge")
    return np.convolve(padded, np.ones(window) / window, mode="valid")


def _interpolate_and_smooth(
    values: np.ndarray, detected_indices: np.ndarray, frame_count: int, window: int
) -> np.ndarray:
    interpolated = np.interp(
        np.arange(frame_count), detected_indices, values[detected_indices]
    )
    return _smooth(interpolated, window)


def _crop_frame(
    frame: np.ndarray, center_x: float, center_y: float, angle_deg: float, side: float
) -> np.ndarray:
    radians = math.radians(angle_deg)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    scale = ROI_SIZE / side
    transform = np.array(
        [
            [
                scale * cosine,
                scale * sine,
                ROI_SIZE / 2 - scale * (cosine * center_x + sine * center_y),
            ],
            [
                -scale * sine,
                scale * cosine,
                ROI_SIZE / 2 - scale * (-sine * center_x + cosine * center_y),
            ],
        ],
        dtype=np.float64,
    )
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.warpAffine(
        gray,
        transform,
        (ROI_SIZE, ROI_SIZE),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )


def _decode_and_detect(
    video_path: Path, detector: object
) -> tuple[list[np.ndarray], float, np.ndarray, np.ndarray, np.ndarray]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Vídeo ilegível: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    reported_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not math.isfinite(fps) or fps <= 0:
        capture.release()
        raise ValueError(f"FPS inválido: {video_path}")
    frames = []
    geometry = []
    detected = []
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            index = len(frames)
            timestamp_ms = index * 1000.0 / fps
            landmarks = detector.extract(frame, index, timestamp_ms)
            frames.append(frame)
            if landmarks is None:
                geometry.append((np.nan, np.nan, np.nan, np.nan))
                detected.append(False)
                continue
            if landmarks.frame_index != index:
                raise ValueError("O detector retornou um frame_index incorreto.")
            points = np.asarray(landmarks.points, dtype=np.float64)
            if points.shape != (40, 2) or not np.all(np.isfinite(points)):
                raise ValueError("Landmarks da boca inválidos.")
            left, right = points[0], points[10]
            delta = right - left
            width = float(np.linalg.norm(delta))
            if width <= 0:
                raise ValueError("A largura da boca deve ser positiva.")
            center = (left + right) / 2.0
            geometry.append(
                (center[0], center[1], math.atan2(delta[1], delta[0]), width)
            )
            detected.append(True)
    finally:
        capture.release()
    if not frames or (reported_count > 0 and len(frames) != reported_count):
        raise ValueError(f"Contagem de frames decodificados inválida: {video_path}")
    return (
        frames,
        fps,
        np.asarray(geometry, dtype=np.float64),
        np.asarray(detected, dtype=np.bool_),
        np.arange(len(frames), dtype=np.float64) * 1000.0 / fps,
    )


def derive_mouth_roi_sample(
    repository_root: Path,
    video_path: Path,
    source_npz_path: Path,
    item: VisualCollectionPlanItem,
    detector: object,
    config: MouthRoiConfig = MouthRoiConfig(),
) -> MouthRoiSample:
    """Mantém cada frame real; interpola somente a transformação de gaps curtos."""
    root = Path(repository_root).resolve()
    if item not in _plan():
        raise ValueError(
            "A amostra ou sessão não pertence ao desenvolvimento permitido."
        )
    expected_video, expected_npz = _source_paths(root, item)
    video_path = Path(video_path).resolve()
    source_npz_path = Path(source_npz_path).resolve()
    if (video_path, source_npz_path) != (expected_video, expected_npz):
        raise ValueError("Caminhos de origem inesperados para a amostra.")
    if not video_path.is_file() or not source_npz_path.is_file():
        raise FileNotFoundError(f"Origem ausente para {item.sample_id}.")
    features = load_visual_feature_sample(source_npz_path)
    if (features.sample_id, features.label, features.session_id) != (
        item.sample_id,
        item.label,
        item.session_id,
    ):
        raise ValueError(f"Metadados NPZ inconsistentes: {item.sample_id}")

    frames, fps, geometry, mask, timestamps = _decode_and_detect(video_path, detector)
    count = len(frames)
    if features.frame_count != count:
        raise ValueError(
            f"Vídeo e NPZ divergem na contagem de frames: {item.sample_id}"
        )
    missing = count - int(mask.sum())
    missing_rate = missing / count
    max_gap = _max_missing_run(mask)
    if not np.any(mask):
        raise ValueError(f"Nenhuma detecção de boca: {item.sample_id}")
    if missing_rate > config.max_missing_rate:
        raise ValueError(f"Taxa de detecções ausentes excedida: {item.sample_id}")
    if max_gap > config.max_consecutive_missing:
        raise ValueError(
            f"Maior sequência consecutiva ausente excedida: {item.sample_id}"
        )

    detected_indices = np.flatnonzero(mask)
    angles = geometry[:, 2].copy()
    angles[detected_indices] = np.unwrap(angles[detected_indices])
    centers = np.column_stack(
        [
            _interpolate_and_smooth(
                geometry[:, axis], detected_indices, count, config.smoothing_window
            )
            for axis in (0, 1)
        ]
    )
    smoothed_angles = _interpolate_and_smooth(
        angles, detected_indices, count, config.smoothing_window
    )
    crop_side = config.crop_scale * float(np.median(geometry[mask, 3]))
    rois = np.stack(
        [
            _crop_frame(
                frame,
                float(centers[index, 0]),
                float(centers[index, 1]),
                math.degrees(float(smoothed_angles[index])),
                crop_side,
            )
            for index, frame in enumerate(frames)
        ]
    )
    sample = MouthRoiSample(
        format_version=FORMAT_VERSION,
        sample_id=item.sample_id,
        label=item.label,
        label_index=DEFAULT_VISUAL_LABELS.index(item.label),
        session_id=item.session_id,
        source_video_path=video_path.relative_to(root).as_posix(),
        source_video_sha256=sha256_file(video_path),
        source_npz_path=source_npz_path.relative_to(root).as_posix(),
        source_npz_sha256=sha256_file(source_npz_path),
        frame_count=count,
        fps=fps,
        roi_height=ROI_SIZE,
        roi_width=ROI_SIZE,
        color_mode=ROI_COLOR_MODE,
        dtype="uint8",
        frame_indices=np.arange(count, dtype=np.int32),
        timestamps_ms=timestamps,
        mouth_rois=rois,
        detection_valid_mask=mask,
        crop_centers_xy=centers,
        crop_angles_deg=np.degrees(smoothed_angles),
        crop_side_px=crop_side,
        decoded_frame_count=count,
        detected_landmark_frame_count=count - missing,
        missing_detection_count=missing,
        missing_detection_rate=missing_rate,
        max_consecutive_missing=max_gap,
        preprocessing_config=config,
    )
    validate_mouth_roi_sample(sample)
    return sample


def validate_mouth_roi_sample(sample: MouthRoiSample) -> None:
    if sample.format_version != FORMAT_VERSION:
        raise ValueError("format_version de ROI incompatível.")
    if sample.session_id not in SESSION_IDS:
        raise ValueError("A sessão não pertence ao desenvolvimento permitido.")
    if sample.label not in DEFAULT_VISUAL_LABELS:
        raise ValueError("Label fora do vocabulário congelado.")
    if sample.label_index != DEFAULT_VISUAL_LABELS.index(sample.label):
        raise ValueError("label_index inconsistente.")
    item = next(
        (entry for entry in _plan() if entry.sample_id == sample.sample_id), None
    )
    if item is None or (item.label, item.session_id) != (
        sample.label,
        sample.session_id,
    ):
        raise ValueError("sample_id, label ou sessão inconsistentes.")
    if sample.color_mode != ROI_COLOR_MODE or sample.mouth_rois.ndim == 4:
        raise ValueError("O dataset deve conter apenas ROI grayscale.")
    if (
        sample.roi_height != ROI_SIZE
        or sample.roi_width != ROI_SIZE
        or sample.mouth_rois.ndim != 3
        or sample.mouth_rois.shape[1:] != (ROI_SIZE, ROI_SIZE)
    ):
        raise ValueError("Cada ROI deve ter tamanho 96 × 96.")
    if sample.dtype != "uint8" or sample.mouth_rois.dtype != np.uint8:
        raise ValueError("O dtype do ROI deve ser uint8.")
    count = sample.frame_count
    if count <= 0 or sample.decoded_frame_count != count:
        raise ValueError("Contagem de frames inválida.")
    if sample.mouth_rois.shape[0] != count:
        raise ValueError("Quantidade de ROIs inconsistente.")
    if sample.frame_indices.shape != (count,) or not np.array_equal(
        sample.frame_indices, np.arange(count)
    ):
        raise ValueError("frame_indices devem representar todos os frames reais.")
    if sample.timestamps_ms.shape != (count,) or not np.all(
        np.isfinite(sample.timestamps_ms)
    ):
        raise ValueError("timestamps inválidos.")
    if count > 1 and not np.all(np.diff(sample.timestamps_ms) > 0):
        raise ValueError("timestamps devem ser estritamente monotônicos.")
    if sample.detection_valid_mask.shape != (count,) or (
        sample.detection_valid_mask.dtype != np.bool_
    ):
        raise ValueError("Máscara de detecção inválida.")
    if sample.crop_centers_xy.shape != (count, 2) or sample.crop_angles_deg.shape != (
        count,
    ):
        raise ValueError("Geometria de crop inválida.")
    if not np.all(np.isfinite(sample.crop_centers_xy)) or not np.all(
        np.isfinite(sample.crop_angles_deg)
    ):
        raise ValueError("Geometria de crop deve ser finita.")
    if not math.isfinite(sample.crop_side_px) or sample.crop_side_px <= 0:
        raise ValueError("Escala de crop inválida.")
    if not math.isfinite(sample.fps) or sample.fps <= 0:
        raise ValueError("FPS inválido.")
    detected = int(sample.detection_valid_mask.sum())
    missing = count - detected
    if (
        detected != sample.detected_landmark_frame_count
        or missing != sample.missing_detection_count
        or not math.isclose(sample.missing_detection_rate, missing / count)
        or sample.max_consecutive_missing
        != _max_missing_run(sample.detection_valid_mask)
    ):
        raise ValueError("Estatísticas de detecção inconsistentes.")
    if (
        not detected
        or sample.missing_detection_rate > sample.preprocessing_config.max_missing_rate
        or sample.max_consecutive_missing
        > sample.preprocessing_config.max_consecutive_missing
    ):
        raise ValueError("Limites de detecção excedidos.")
    if not all(
        len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)
        for value in (sample.source_video_sha256, sample.source_npz_sha256)
    ):
        raise ValueError("Hash de origem inválido.")
    expected_video, expected_npz = _source_paths(Path("."), item)
    if sample.source_video_path != expected_video.as_posix() or (
        sample.source_npz_path != expected_npz.as_posix()
    ):
        raise ValueError("Caminhos de origem inesperados.")


def _save_sample(sample: MouthRoiSample, output_path: Path) -> None:
    validate_mouth_roi_sample(sample)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"ROI derivado já existe: {output_path}")
    scalars = {
        field: np.asarray(getattr(sample, field))
        for field in (
            "format_version",
            "sample_id",
            "label",
            "label_index",
            "session_id",
            "source_video_path",
            "source_video_sha256",
            "source_npz_path",
            "source_npz_sha256",
            "frame_count",
            "fps",
            "roi_height",
            "roi_width",
            "color_mode",
            "dtype",
            "crop_side_px",
            "decoded_frame_count",
            "detected_landmark_frame_count",
            "missing_detection_count",
            "missing_detection_rate",
            "max_consecutive_missing",
        )
    }
    arrays = {
        field: getattr(sample, field)
        for field in (
            "frame_indices",
            "timestamps_ms",
            "mouth_rois",
            "detection_valid_mask",
            "crop_centers_xy",
            "crop_angles_deg",
        )
    }
    np.savez_compressed(
        output_path,
        **scalars,
        **arrays,
        preprocessing_config_json=np.asarray(
            json.dumps(asdict(sample.preprocessing_config), sort_keys=True)
        ),
    )


def _load_sample(path: Path) -> MouthRoiSample:
    with np.load(path, allow_pickle=False) as data:
        integer_fields = (
            "format_version",
            "label_index",
            "frame_count",
            "roi_height",
            "roi_width",
            "decoded_frame_count",
            "detected_landmark_frame_count",
            "missing_detection_count",
            "max_consecutive_missing",
        )
        float_fields = ("fps", "crop_side_px", "missing_detection_rate")
        string_fields = (
            "sample_id",
            "label",
            "session_id",
            "source_video_path",
            "source_video_sha256",
            "source_npz_path",
            "source_npz_sha256",
            "color_mode",
            "dtype",
        )
        values = {name: int(data[name].item()) for name in integer_fields}
        values.update({name: float(data[name].item()) for name in float_fields})
        values.update({name: str(data[name].item()) for name in string_fields})
        values.update(
            {
                name: np.asarray(data[name]).copy()
                for name in (
                    "frame_indices",
                    "timestamps_ms",
                    "mouth_rois",
                    "detection_valid_mask",
                    "crop_centers_xy",
                    "crop_angles_deg",
                )
            }
        )
        values["preprocessing_config"] = MouthRoiConfig(
            **json.loads(str(data["preprocessing_config_json"].item()))
        )
    sample = MouthRoiSample(**values)
    validate_mouth_roi_sample(sample)
    return sample


def _expected_output_path(
    repository_root: Path, item: VisualCollectionPlanItem
) -> Path:
    return repository_root / ROI_RELATIVE_ROOT / f"{item.sample_id}.npz"


def _preflight_sources(repository_root: Path) -> None:
    expected_videos = set()
    for item in _plan():
        video, feature = _source_paths(repository_root, item)
        if not video.is_file() or not feature.is_file():
            raise FileNotFoundError(f"Vídeo ou NPZ ausente: {item.sample_id}")
        expected_videos.add(video)
    observed_files = {
        path
        for session in SESSION_IDS
        for path in (repository_root / "data/raw/visual_dataset" / session).rglob("*")
        if path.is_file()
    }
    if observed_files != expected_videos:
        raise ValueError("Arquivo de desenvolvimento ausente ou inesperado.")


def _manifest_entry(
    sample: MouthRoiSample, roi_path: Path, repository_root: Path
) -> dict:
    return {
        "sample_id": sample.sample_id,
        "label": sample.label,
        "label_index": sample.label_index,
        "session_id": sample.session_id,
        "source_video_path": sample.source_video_path,
        "source_video_sha256": sample.source_video_sha256,
        "source_npz_path": sample.source_npz_path,
        "source_npz_sha256": sample.source_npz_sha256,
        "derived_roi_path": roi_path.relative_to(repository_root).as_posix(),
        "derived_roi_sha256": sha256_file(roi_path),
        "frame_count": sample.frame_count,
        "fps": sample.fps,
        "detected_landmark_frame_count": sample.detected_landmark_frame_count,
        "missing_detection_count": sample.missing_detection_count,
        "missing_detection_rate": sample.missing_detection_rate,
        "max_consecutive_missing": sample.max_consecutive_missing,
        "crop_side_px": sample.crop_side_px,
        "center_x_min": float(sample.crop_centers_xy[:, 0].min()),
        "center_x_max": float(sample.crop_centers_xy[:, 0].max()),
        "center_y_min": float(sample.crop_centers_xy[:, 1].min()),
        "center_y_max": float(sample.crop_centers_xy[:, 1].max()),
        "angle_deg_min": float(sample.crop_angles_deg.min()),
        "angle_deg_max": float(sample.crop_angles_deg.max()),
    }


def _contact_sheet(samples: tuple[MouthRoiSample, ...], output_path: Path) -> None:
    rows = []
    for label in DEFAULT_VISUAL_LABELS:
        sample = next(
            sample
            for sample in samples
            if sample.label == label
            and sample.session_id == SESSION_IDS[0]
            and sample.sample_id.endswith("_001")
        )
        valid = np.flatnonzero(sample.detection_valid_mask)
        indices = (int(valid[0]), sample.frame_count // 2, int(valid[-1]))
        rows.append(np.hstack([sample.mouth_rois[index] for index in indices]))
    sheet = np.vstack(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), sheet):
        raise OSError(f"Falha ao escrever contact sheet: {output_path}")


def build_mouth_roi_dataset(
    repository_root: Path,
    detector_factory: Callable[[], object] = MediaPipeMouthDetector,
    config: MouthRoiConfig = MouthRoiConfig(),
) -> dict:
    """Gera apenas os 54 positivos autorizados, sem sobrescrever originais."""
    root = Path(repository_root).resolve()
    output_root = root / ROI_RELATIVE_ROOT
    manifest_path = root / MANIFEST_RELATIVE_PATH
    sheet_path = root / CONTACT_SHEET_RELATIVE_PATH
    if output_root.exists() or manifest_path.exists() or sheet_path.exists():
        raise FileExistsError("Dataset, manifesto ou diagnóstico ROI já existe.")
    _preflight_sources(root)
    samples = []
    for item in _plan():
        video, feature = _source_paths(root, item)
        detector = detector_factory()
        try:
            samples.append(
                derive_mouth_roi_sample(root, video, feature, item, detector, config)
            )
        finally:
            mesh = getattr(detector, "mesh", None)
            if mesh is not None and hasattr(mesh, "close"):
                mesh.close()
    if len(samples) != 54:
        raise ValueError("O dataset ROI exige exatamente 54 amostras.")
    entries = []
    for item, sample in zip(_plan(), samples):
        destination = _expected_output_path(root, item)
        _save_sample(sample, destination)
        entries.append(_manifest_entry(sample, destination, root))
    manifest = {
        "format_version": FORMAT_VERSION,
        "allowed_sessions": list(SESSION_IDS),
        "forbidden_sessions": list(FORBIDDEN_SESSIONS),
        "labels": list(DEFAULT_VISUAL_LABELS),
        "sample_count": len(samples),
        "total_frames": sum(sample.frame_count for sample in samples),
        "detected_landmark_frame_count": sum(
            sample.detected_landmark_frame_count for sample in samples
        ),
        "roi_height": ROI_SIZE,
        "roi_width": ROI_SIZE,
        "color_mode": ROI_COLOR_MODE,
        "dtype": "uint8",
        "crop_method": "median_mouth_width_fixed_per_sample",
        "stabilization": "linear_gap_geometry_then_center_angle_moving_average",
        "missing_detection_handling": "interpolate_spatial_transform_only",
        "preprocessing_config": asdict(config),
        "landmark_detector": "MediaPipe FaceMesh",
        "pretrained_visual_encoder_used": False,
        "samples": entries,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _contact_sheet(tuple(samples), sheet_path)
    return validate_mouth_roi_dataset(root)


def validate_mouth_roi_dataset(repository_root: Path) -> dict:
    """Confere contrato, contagens, caminhos e SHA-256 das fontes/ROIs."""
    root = Path(repository_root).resolve()
    _preflight_sources(root)
    manifest_path = root / MANIFEST_RELATIVE_PATH
    if not manifest_path.is_file():
        raise FileNotFoundError("Manifesto de mouth ROI ausente.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("format_version") != FORMAT_VERSION
        or manifest.get("allowed_sessions") != list(SESSION_IDS)
        or manifest.get("forbidden_sessions") != list(FORBIDDEN_SESSIONS)
        or manifest.get("labels") != list(DEFAULT_VISUAL_LABELS)
        or manifest.get("sample_count") != 54
        or manifest.get("roi_height") != ROI_SIZE
        or manifest.get("roi_width") != ROI_SIZE
        or manifest.get("color_mode") != ROI_COLOR_MODE
        or manifest.get("dtype") != "uint8"
        or manifest.get("landmark_detector") != "MediaPipe FaceMesh"
        or manifest.get("pretrained_visual_encoder_used") is not False
    ):
        raise ValueError("Contrato global do manifesto ROI inválido.")
    entries = manifest.get("samples")
    expected_items = _plan()
    if not isinstance(entries, list) or len(entries) != len(expected_items):
        raise ValueError("O manifesto ROI deve conter 54 amostras.")
    expected_files = {_expected_output_path(root, item) for item in expected_items}
    observed_files = {
        path for path in (root / ROI_RELATIVE_ROOT).rglob("*") if path.is_file()
    }
    if observed_files != expected_files:
        raise ValueError("Arquivo ROI ausente ou inesperado no dataset derivado.")
    sample_ids = [entry.get("sample_id") for entry in entries]
    if len(sample_ids) != len(set(sample_ids)) or set(sample_ids) != {
        item.sample_id for item in expected_items
    }:
        raise ValueError("sample_id duplicado ou inesperado no manifesto.")
    counts_by_session = Counter()
    counts_by_label = Counter()
    total_frames = total_detected = 0
    for entry in entries:
        item = next(
            item for item in expected_items if item.sample_id == entry["sample_id"]
        )
        roi_path = _expected_output_path(root, item)
        sample = _load_sample(roi_path)
        if sample.preprocessing_config != MouthRoiConfig(
            **manifest["preprocessing_config"]
        ):
            raise ValueError("Configuração ROI inconsistente com manifesto.")
        expected_entry = _manifest_entry(sample, roi_path, root)
        if entry != expected_entry:
            raise ValueError(
                f"Metadados ou hash ROI inconsistentes: {sample.sample_id}"
            )
        source_video, source_npz = _source_paths(root, item)
        if (
            sha256_file(source_video) != sample.source_video_sha256
            or sha256_file(source_npz) != sample.source_npz_sha256
        ):
            raise ValueError(f"Hash de origem inconsistente: {sample.sample_id}")
        counts_by_session[sample.session_id] += 1
        counts_by_label[sample.label] += 1
        total_frames += sample.frame_count
        total_detected += sample.detected_landmark_frame_count
    if counts_by_session != Counter({session: 18 for session in SESSION_IDS}):
        raise ValueError("O dataset ROI exige 18 amostras por sessão.")
    if counts_by_label != Counter({label: 9 for label in DEFAULT_VISUAL_LABELS}):
        raise ValueError("O dataset ROI exige 9 amostras por classe.")
    if (
        manifest.get("total_frames") != total_frames
        or manifest.get("detected_landmark_frame_count") != total_detected
    ):
        raise ValueError("Contagens globais inconsistentes no manifesto.")
    return manifest
