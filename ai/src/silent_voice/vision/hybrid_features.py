"""Features dos dois híbridos e seleção de NPZ autorizados antes de I/O."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from silent_voice.vision.dataset_collection_plan import build_visual_collection_plan
from silent_voice.vision.feature_sample import VisualFeatureSample
from silent_voice.vision.feature_sample_storage import load_visual_feature_sample
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.strong_dtw_distance import (
    StrongDtwDistanceConfig,
    calculate_strong_dtw_distance,
)
from silent_voice.vision.swinlip_embedding_dataset import (
    OUTPUT_RELATIVE_ROOT,
    validate_embedding_manifest,
)
from silent_voice.vision.swinlip_frozen_probe import (
    EMBEDDING_DIMENSION,
    l2_normalize,
)
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

HYBRID_EPSILON = 1e-12
FORBIDDEN_SESSION_IDS = ("sessao_04", "rejeicao_heldout_01")
CURRENT_DTW_CONFIG = StrongDtwDistanceConfig(
    normalize_by_path_length=False, max_normalized_warping=None
)


@dataclass(frozen=True, slots=True)
class HybridSample:
    sample_id: str
    session_id: str
    label: str
    label_index: int
    clip_embedding: np.ndarray
    features: np.ndarray


def _expected_plan() -> dict[str, object]:
    return {
        item.sample_id: item
        for item in build_visual_collection_plan(SESSION_IDS, DEFAULT_VISUAL_LABELS, 3)
    }


def select_authorized_visual_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    """Valida 54 IDs de development somente por nome antes de abrir NPZ."""
    expected_ids = set(_expected_plan())
    selected = []
    for path in paths:
        candidate = Path(path)
        if candidate.suffix != ".npz" or candidate.stem not in expected_ids:
            continue
        if any(
            forbidden in part
            for part in candidate.parts
            for forbidden in FORBIDDEN_SESSION_IDS
        ):
            raise ValueError("Caminho proibido associado a sample_id autorizado.")
        selected.append(candidate)
    ids = [path.stem for path in selected]
    if len(ids) != 54 or len(set(ids)) != 54 or set(ids) != expected_ids:
        raise ValueError("É obrigatório selecionar exatamente 54 NPZ autorizados.")
    return tuple(sorted(selected))


def load_authorized_visual_samples(
    dataset_root: Path,
) -> tuple[tuple[VisualFeatureSample, ...], tuple[Path, ...]]:
    """Executa todo o filtro e validação de paths antes do primeiro reader."""
    root = Path(dataset_root)
    if not root.is_dir():
        raise FileNotFoundError(f"Diretório visual não encontrado: {root}")
    paths = select_authorized_visual_paths(tuple(root.rglob("*.npz")))
    expected = _expected_plan()
    samples = []
    for path in paths:
        sample = load_visual_feature_sample(path)
        plan = expected[path.stem]
        if (
            sample.sample_id != plan.sample_id
            or sample.session_id != plan.session_id
            or sample.label != plan.label
            or not np.isfinite(sample.features).all()
        ):
            raise ValueError("NPZ visual não corresponde ao caminho autorizado.")
        samples.append(sample)
    return tuple(samples), paths


def select_authorized_embedding_paths(
    root: Path, manifest: dict
) -> tuple[tuple[dict, Path], ...]:
    """Confere IDs e paths do manifesto antes de abrir ou hashear embeddings."""
    validate_embedding_manifest(manifest)
    expected = _expected_plan()
    selected = []
    for entry in manifest["samples"]:
        sample_id = entry["sample_id"]
        if sample_id not in expected or entry["session_id"] not in SESSION_IDS:
            raise ValueError("Embedding fora das sessões autorizadas.")
        relative = Path(entry["embedding_path"])
        if relative != OUTPUT_RELATIVE_ROOT / f"{sample_id}.npz":
            raise ValueError("Path de embedding não corresponde ao sample_id.")
        path = Path(root) / relative
        selected.append((entry, path))
    if len(selected) != 54 or len({item[0]["sample_id"] for item in selected}) != 54:
        raise ValueError("É obrigatório selecionar 54 embeddings autorizados.")
    return tuple(selected)


def load_authorized_clip_embeddings(
    root: Path, manifest: dict
) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Lê somente clip_embedding de paths já validados por metadata."""
    selected = select_authorized_embedding_paths(root, manifest)
    clips = {}
    hashes = {}
    for entry, path in selected:
        digest = sha256_file(path)
        if digest != entry["embedding_sha256"]:
            raise ValueError("SHA-256 de embedding divergiu do manifesto.")
        with np.load(path, allow_pickle=False) as data:
            clip = np.asarray(data["clip_embedding"]).copy()
        if (
            clip.shape != (EMBEDDING_DIMENSION,)
            or clip.dtype != np.float32
            or not np.isfinite(clip).all()
        ):
            raise ValueError(
                "clip_embedding deve ser float32 finito de 1664 dimensões."
            )
        clips[entry["sample_id"]] = clip
        hashes[entry["sample_id"]] = digest
    return clips, hashes


def landmark_stats(sequence: np.ndarray) -> tuple[np.ndarray, str, float]:
    """Concatena mean e std populacional; hash cobre o resumo pré-normalização."""
    features = np.asarray(sequence, dtype=np.float64)
    if features.ndim != 2 or features.shape[0] == 0 or features.shape[1] != 160:
        raise ValueError("Landmarks segmentados devem ter shape (T,160).")
    if not np.isfinite(features).all():
        raise ValueError("Landmarks contêm valores não finitos.")
    summary = np.concatenate(
        (np.mean(features, axis=0), np.std(features, axis=0, ddof=0))
    ).astype(np.float32)
    digest = hashlib.sha256(summary.astype("<f4").tobytes()).hexdigest()
    norm = float(np.linalg.norm(summary.astype(np.float64)))
    return summary, digest, norm


def raw_current_dtw_distance(first: object, second: object) -> float:
    """Chama a distância CURRENT_DTW acumulada e irrestrita já congelada."""
    return calculate_strong_dtw_distance(
        first.features, second.features, CURRENT_DTW_CONFIG
    ).distance


def class_minimum_dtw_distances(
    query: object,
    templates: tuple[object, ...],
    distance_fn: Callable[[object, object], float] = raw_current_dtw_distance,
) -> np.ndarray:
    """Menor distância por classe, excluindo self no treino."""
    class_distances: list[list[float]] = [[] for _ in DEFAULT_VISUAL_LABELS]
    for template in templates:
        if template.sample_id == query.sample_id:
            continue
        if template.label not in DEFAULT_VISUAL_LABELS:
            raise ValueError("Template fora do vocabulário congelado.")
        distance = float(distance_fn(query, template))
        if not np.isfinite(distance) or distance < 0:
            raise ValueError("Distância CURRENT_DTW deve ser finita e não negativa.")
        class_distances[DEFAULT_VISUAL_LABELS.index(template.label)].append(distance)
    if any(not values for values in class_distances):
        raise ValueError("Falta template de uma classe na evidência geométrica.")
    return np.asarray([min(values) for values in class_distances], dtype=np.float64)


def normalized_reciprocal_evidence(distances: np.ndarray) -> np.ndarray:
    values = np.asarray(distances, dtype=np.float64)
    if values.shape != (6,) or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("São exigidas seis distâncias de classe válidas.")
    evidence = 1.0 / np.maximum(values, HYBRID_EPSILON)
    return l2_normalize(evidence)


def equal_energy_fusion(
    clip: np.ndarray, geometry: np.ndarray, expected_dimension: int
) -> np.ndarray:
    visual = np.asarray(clip)
    geometric = np.asarray(geometry)
    if (
        visual.shape != (EMBEDDING_DIMENSION,)
        or geometric.ndim != 1
        or expected_dimension not in (1670, 1984)
        or visual.size + geometric.size != expected_dimension
    ):
        raise ValueError("Dimensão inválida para fusão híbrida equal-energy.")
    scale = np.sqrt(2.0)
    fused = np.concatenate(
        (l2_normalize(visual) / scale, l2_normalize(geometric) / scale)
    ).astype(np.float32)
    if fused.shape != (expected_dimension,) or not np.isfinite(fused).all():
        raise ValueError("Vetor híbrido inválido.")
    return fused
