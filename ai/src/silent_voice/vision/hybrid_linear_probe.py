"""Cabeça linear dos híbridos com hiperparâmetros da Task 6.4 congelados."""

import random
from collections import Counter

import numpy as np
import torch
from torch import nn

from silent_voice.vision.swinlip_frozen_probe import (
    LINEAR_EPOCHS,
    LINEAR_GRADIENT_CLIP_NORM,
    LINEAR_LEARNING_RATE,
    LINEAR_SEED,
    LINEAR_WEIGHT_DECAY,
)


def train_hybrid_linear(
    features: np.ndarray, labels: np.ndarray
) -> tuple[nn.Linear, dict]:
    """Treina só Linear(input_dim,6) por 500 épocas full batch em CPU."""
    inputs = np.asarray(features)
    targets = np.asarray(labels)
    class_size = inputs.shape[0] // 6
    if (
        inputs.ndim != 2
        or inputs.shape not in ((18, 1670), (36, 1670), (36, 1984), (54, 1670))
        or inputs.dtype != np.float32
        or not np.isfinite(inputs).all()
        or targets.shape != (inputs.shape[0],)
        or Counter(int(item) for item in targets)
        != Counter({index: class_size for index in range(6)})
    ):
        raise ValueError("Treino híbrido exige 18, 36 ou 54 vetores balanceados.")
    random.seed(LINEAR_SEED)
    np.random.seed(LINEAR_SEED)
    torch.manual_seed(LINEAR_SEED)
    torch.use_deterministic_algorithms(True)
    data = torch.from_numpy(inputs).to("cpu")
    labels_tensor = torch.from_numpy(targets.astype(np.int64)).to("cpu")
    model = nn.Linear(inputs.shape[1], 6, bias=True).to("cpu")
    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LINEAR_LEARNING_RATE, weight_decay=LINEAR_WEIGHT_DECAY
    )
    criterion = nn.CrossEntropyLoss()
    for _ in range(LINEAR_EPOCHS):
        optimizer.zero_grad(set_to_none=True)
        logits = model(data)
        loss = criterion(logits, labels_tensor)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), LINEAR_GRADIENT_CLIP_NORM)
        optimizer.step()
    model.eval()
    with torch.no_grad():
        final_logits = model(data)
        final_loss = criterion(final_logits, labels_tensor)
        final_accuracy = (
            (torch.argmax(final_logits, dim=1) == labels_tensor).float().mean()
        )
    return model, {
        "sample_count": len(inputs),
        "epochs_completed": LINEAR_EPOCHS,
        "final_training_loss": float(final_loss.item()),
        "final_training_accuracy": float(final_accuracy.item()),
    }


def predict_hybrid_linear(
    model: nn.Linear, features: np.ndarray
) -> tuple[int, tuple[float, ...]]:
    vector = np.asarray(features)
    if (
        vector.shape != (model.in_features,)
        or vector.dtype != np.float32
        or not np.isfinite(vector).all()
        or model.out_features != 6
    ):
        raise ValueError("Vetor ou cabeça linear híbrida incompatível.")
    with torch.no_grad():
        logits = model(torch.from_numpy(vector).to("cpu"))
    return int(torch.argmax(logits).item()), tuple(
        float(item) for item in logits.tolist()
    )
