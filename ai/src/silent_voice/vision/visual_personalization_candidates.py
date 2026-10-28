"""PERS.1E: four frozen candidate algorithms, independent of real media."""

import random
from collections import Counter
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from silent_voice.vision.hybrid_features import raw_current_dtw_distance
from silent_voice.vision.personalization_development_protocol import (
    CONFIG_IDS,
    LABELS,
    safe_reject_output,
)
from silent_voice.vision.swinlip_frozen_probe import l2_normalize


FROZEN_THRESHOLD = 0.5666271450980487
HEAD_RECIPE = {
    "seed": 2026,
    "epochs": 500,
    "optimizer": "AdamW",
    "learning_rate": 0.01,
    "weight_decay": 0.01,
    "loss": "CrossEntropyLoss",
    "gradient_clip_norm": 1.0,
    "batch": "full enrollment subset",
    "device": "CPU",
    "swinlip_trainable": False,
    "early_stopping": False,
    "torch_deterministic_algorithms": True,
}


@dataclass(frozen=True, slots=True)
class EnrollmentFeature:
    sample_id: str
    label: str
    label_index: int
    clip_embedding: np.ndarray
    temporal_features: np.ndarray


@dataclass(frozen=True, slots=True)
class _DtwSample:
    features: np.ndarray


def _validate_features(features: tuple[EnrollmentFeature, ...]) -> int:
    if len(features) not in (6, 12, 24):
        raise ValueError("Subset deve conter 6, 12 ou 24 clips.")
    shots = len(features) // len(LABELS)
    if len({item.sample_id for item in features}) != len(features):
        raise ValueError("sample_id duplicado no enrollment.")
    if Counter(item.label_index for item in features) != {
        index: shots for index in range(len(LABELS))
    }:
        raise ValueError("Subset exige igual número por classe.")
    for item in features:
        if (
            item.label != LABELS[item.label_index]
            or item.clip_embedding.shape != (1664,)
            or item.clip_embedding.dtype != np.float32
            or not np.isfinite(item.clip_embedding).all()
            or item.temporal_features.ndim != 2
            or item.temporal_features.shape[0] < 1
            or item.temporal_features.shape[1] != 160
            or item.temporal_features.dtype != np.float32
            or not np.isfinite(item.temporal_features).all()
        ):
            raise ValueError("Feature de enrollment incompatível.")
    return shots


def select_frozen_subset(
    all_features: tuple[EnrollmentFeature, ...],
    frozen_ids: list[str],
    shots_per_class: int,
) -> tuple[EnrollmentFeature, ...]:
    """Select by exact frozen membership, never by feature quality."""
    if shots_per_class not in (1, 2, 4):
        raise ValueError("Shot regime inválido.")
    indexed = {item.sample_id: item for item in all_features}
    if (
        len(indexed) != len(all_features)
        or len(frozen_ids) != 6 * shots_per_class
        or len(set(frozen_ids)) != len(frozen_ids)
        or not set(frozen_ids) <= indexed.keys()
    ):
        raise ValueError("Frozen subset membership inválido.")
    selected = tuple(indexed[sample_id] for sample_id in frozen_ids)
    if _validate_features(selected) != shots_per_class:
        raise ValueError("Frozen subset membership por classe inválido.")
    return selected


def build_personal_prototypes(
    features: tuple[EnrollmentFeature, ...],
) -> np.ndarray:
    """Mean of L2 clips per class, then L2 of each class center."""
    _validate_features(features)
    clips = l2_normalize(np.stack([item.clip_embedding for item in features]))
    labels = np.asarray([item.label_index for item in features], dtype=np.int64)
    centers = np.stack([clips[labels == index].mean(axis=0) for index in range(6)])
    return l2_normalize(centers)


def predict_prototype(centers: np.ndarray, clip: np.ndarray) -> tuple[int, np.ndarray]:
    if (
        centers.shape != (6, 1664)
        or centers.dtype != np.float32
        or clip.shape != (1664,)
        or clip.dtype != np.float32
        or not np.isfinite(centers).all()
        or not np.isfinite(clip).all()
    ):
        raise ValueError("Protótipos ou clip inválidos.")
    cosine = np.asarray(centers @ l2_normalize(clip), dtype=np.float32)
    return int(np.argmax(cosine)), cosine


def _descending_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(-values, kind="stable")
    ranks = np.empty(6, dtype=np.int64)
    ranks[order] = np.arange(6, dtype=np.int64)
    return ranks


def rerank_global_and_personal(
    global_logits: np.ndarray, personal_cosines: np.ndarray
) -> tuple[int, np.ndarray]:
    """Frozen 1:1 rank sum; global rank then class index breaks ties."""
    global_values = np.asarray(global_logits)
    personal_values = np.asarray(personal_cosines)
    if (
        global_values.shape != (6,)
        or personal_values.shape != (6,)
        or not np.isfinite(global_values).all()
        or not np.isfinite(personal_values).all()
    ):
        raise ValueError("São exigidas seis evidências finitas por fonte.")
    global_ranks = _descending_ranks(global_values)
    personal_ranks = _descending_ranks(personal_values)
    combined = -global_ranks - personal_ranks
    index = min(range(6), key=lambda i: (-combined[i], global_ranks[i], i))
    return index, combined


def predict_personal_dtw(
    query_features: np.ndarray,
    templates: tuple[EnrollmentFeature, ...],
    distance_fn=raw_current_dtw_distance,
) -> tuple[int, np.ndarray]:
    """Minimum accumulated unrestricted CURRENT_DTW per personal class."""
    _validate_features(templates)
    query = np.asarray(query_features)
    if (
        query.ndim != 2
        or query.shape[0] < 1
        or query.shape[1] != 160
        or query.dtype != np.float32
        or not np.isfinite(query).all()
    ):
        raise ValueError("Sequência temporal da query inválida.")
    sample = _DtwSample(query)
    distances = [[] for _ in LABELS]
    for template in templates:
        distance = float(distance_fn(sample, _DtwSample(template.temporal_features)))
        if not np.isfinite(distance) or distance < 0:
            raise ValueError("Distância DTW inválida.")
        distances[template.label_index].append(distance)
    minima = np.asarray([min(values) for values in distances], dtype=np.float64)
    return int(np.argmin(minima)), minima


def fit_lightweight_personal_head(
    features: tuple[EnrollmentFeature, ...],
) -> tuple[nn.Linear, dict]:
    """Fixed synthetic-testable recipe; real fit is forbidden in PERS.1E."""
    _validate_features(features)
    random.seed(HEAD_RECIPE["seed"])
    np.random.seed(HEAD_RECIPE["seed"])
    torch.manual_seed(HEAD_RECIPE["seed"])
    torch.use_deterministic_algorithms(True)
    inputs = torch.from_numpy(
        l2_normalize(np.stack([item.clip_embedding for item in features]))
    ).to("cpu")
    targets = torch.tensor(
        [item.label_index for item in features], dtype=torch.int64, device="cpu"
    )
    model = nn.Linear(1664, len(LABELS), bias=True).to("cpu")
    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=HEAD_RECIPE["learning_rate"],
        weight_decay=HEAD_RECIPE["weight_decay"],
    )
    criterion = nn.CrossEntropyLoss()
    for _ in range(HEAD_RECIPE["epochs"]):
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(inputs), targets)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), HEAD_RECIPE["gradient_clip_norm"])
        optimizer.step()
    model.eval()
    return model, dict(HEAD_RECIPE)


def predict_personal_head(model: nn.Linear, clip: np.ndarray) -> tuple[int, np.ndarray]:
    if (
        model.in_features != 1664
        or model.out_features != len(LABELS)
        or clip.shape != (1664,)
        or clip.dtype != np.float32
        or not np.isfinite(clip).all()
    ):
        raise ValueError("Cabeça pessoal ou clip incompatível.")
    with torch.no_grad():
        logits = model(torch.from_numpy(l2_normalize(clip)).to("cpu"))
    values = logits.detach().cpu().numpy()
    return int(np.argmax(values)), values.copy()


def classify_with_frozen_rejection(
    query_id: str, config_id: str, gap_action: str, classifier, scorer
) -> dict:
    """Pure adapter: safety gate first, candidate class, frozen R4 scorer."""
    if config_id not in CONFIG_IDS:
        raise ValueError("Configuração fora da matriz congelada.")
    if gap_action == "SAFE_REJECT_INSUFFICIENT_VISUAL_EVIDENCE":
        return safe_reject_output(query_id, config_id)
    if gap_action not in ("ORIGINAL_PATH", "BOUNDED_INTERPOLATION"):
        raise ValueError("Ação landmark gap inválida.")
    index = classifier()
    if type(index) is not int or index not in range(6):
        raise ValueError("Classe prevista inválida.")
    score = float(scorer(index))
    if not np.isfinite(score):
        raise ValueError("Score R4 inválido.")
    return {
        "query_id": query_id,
        "config_id": config_id,
        "predicted_label": LABELS[index],
        "predicted_label_index": index,
        "score": score,
        "decision": "ACCEPT" if score >= FROZEN_THRESHOLD else "REJECT",
        "inference_performed": True,
        "reason": None,
    }


def predict_global_baseline(runtime, neutral_row: dict, media_path) -> dict:
    """Delegate unchanged to the hardened R4 runtime, without enrollment."""
    return runtime.predict(neutral_row, media_path)
