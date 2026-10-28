"""Dois probes fixos para clip embeddings SwinLip, sem executar o encoder."""

import random
from collections import Counter
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

EMBEDDING_DIMENSION = 1664
EMBEDDING_NORMALIZATION_EPSILON = 1e-12
LINEAR_SEED = 2026
LINEAR_EPOCHS = 500
LINEAR_LEARNING_RATE = 0.01
LINEAR_WEIGHT_DECAY = 0.01
LINEAR_GRADIENT_CLIP_NORM = 1.0


@dataclass(frozen=True, slots=True)
class ProbeSample:
    sample_id: str
    session_id: str
    label: str
    label_index: int
    clip_embedding: np.ndarray


def l2_normalize(values: np.ndarray) -> np.ndarray:
    """Normaliza cada vetor independentemente, inclusive em entrada matricial."""
    matrix = np.asarray(values)
    if matrix.ndim not in (1, 2) or not np.issubdtype(matrix.dtype, np.number):
        raise ValueError("Embedding deve ser vetor ou matriz numérica.")
    if not np.isfinite(matrix).all():
        raise ValueError("Embedding contém valores não finitos.")
    normalized = matrix.astype(np.float64)
    lengths = np.linalg.norm(normalized, axis=-1, keepdims=True)
    normalized = normalized / np.maximum(lengths, EMBEDDING_NORMALIZATION_EPSILON)
    return normalized.astype(np.float32)


def _training_arrays(samples: tuple[ProbeSample, ...]) -> tuple[np.ndarray, np.ndarray]:
    if len(samples) != 36 or len({item.sample_id for item in samples}) != 36:
        raise ValueError("Cada fold exige 36 sample_id únicos de treino.")
    if Counter(item.label_index for item in samples) != Counter(
        {index: 6 for index in range(len(DEFAULT_VISUAL_LABELS))}
    ):
        raise ValueError("Cada classe exige seis amostras de treino.")
    for item in samples:
        if (
            item.label != DEFAULT_VISUAL_LABELS[item.label_index]
            or item.clip_embedding.shape != (EMBEDDING_DIMENSION,)
            or item.clip_embedding.dtype != np.float32
        ):
            raise ValueError("Contrato do clip embedding de treino inválido.")
    embeddings = l2_normalize(np.stack([item.clip_embedding for item in samples]))
    labels = np.asarray([item.label_index for item in samples], dtype=np.int64)
    return embeddings, labels


def train_centroids(samples: tuple[ProbeSample, ...]) -> np.ndarray:
    """Média de seis clips normalizados por classe, depois L2 por centroide."""
    embeddings, labels = _training_arrays(samples)
    centers = np.stack([embeddings[labels == index].mean(axis=0) for index in range(6)])
    return l2_normalize(centers)


def predict_centroid(
    centers: np.ndarray, sample: ProbeSample
) -> tuple[int, tuple[float, ...]]:
    if centers.shape != (6, EMBEDDING_DIMENSION) or not np.isfinite(centers).all():
        raise ValueError("Centroides inválidos.")
    if sample.clip_embedding.shape != (EMBEDDING_DIMENSION,):
        raise ValueError("Dimensão do clip embedding inválida.")
    query = l2_normalize(sample.clip_embedding)
    similarities = np.asarray(centers @ query, dtype=np.float32)
    # np.argmax retorna o primeiro índice no caso de empate exato.
    return int(np.argmax(similarities)), tuple(float(value) for value in similarities)


def train_linear_probe(
    samples: tuple[ProbeSample, ...],
) -> tuple[nn.Linear, dict[str, int | float]]:
    """Treina somente Linear(1664,6) por 500 épocas full batch em CPU."""
    embeddings, labels = _training_arrays(samples)
    random.seed(LINEAR_SEED)
    np.random.seed(LINEAR_SEED)
    torch.manual_seed(LINEAR_SEED)
    torch.use_deterministic_algorithms(True)
    inputs = torch.from_numpy(embeddings).to("cpu")
    targets = torch.from_numpy(labels).to("cpu")
    model = nn.Linear(EMBEDDING_DIMENSION, len(DEFAULT_VISUAL_LABELS), bias=True)
    model.to("cpu")
    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LINEAR_LEARNING_RATE, weight_decay=LINEAR_WEIGHT_DECAY
    )
    criterion = nn.CrossEntropyLoss()
    for _ in range(LINEAR_EPOCHS):
        optimizer.zero_grad(set_to_none=True)
        logits = model(inputs)
        loss = criterion(logits, targets)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), LINEAR_GRADIENT_CLIP_NORM)
        optimizer.step()
    model.eval()
    with torch.no_grad():
        final_logits = model(inputs)
        final_loss = criterion(final_logits, targets)
        final_accuracy = (torch.argmax(final_logits, dim=1) == targets).float().mean()
    diagnostics = {
        "sample_count": len(samples),
        "epochs_completed": LINEAR_EPOCHS,
        "final_training_loss": float(final_loss.item()),
        "final_training_accuracy": float(final_accuracy.item()),
    }
    return model, diagnostics


def predict_linear(
    model: nn.Linear, sample: ProbeSample
) -> tuple[int, tuple[float, ...]]:
    if (
        model.in_features != EMBEDDING_DIMENSION
        or model.out_features != len(DEFAULT_VISUAL_LABELS)
        or sample.clip_embedding.shape != (EMBEDDING_DIMENSION,)
    ):
        raise ValueError("Modelo ou clip embedding incompatível.")
    query = torch.from_numpy(l2_normalize(sample.clip_embedding)).to("cpu")
    with torch.no_grad():
        logits = model(query)
    return int(torch.argmax(logits).item()), tuple(float(x) for x in logits.tolist())
