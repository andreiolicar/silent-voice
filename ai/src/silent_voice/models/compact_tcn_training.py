import random
from dataclasses import dataclass
from math import isfinite

import numpy as np
import torch
from torch import nn

from silent_voice.models.compact_tcn import (
    CompactTcn,
)
from silent_voice.models.compact_tcn_config import (
    CompactTcnConfig,
)
from silent_voice.vision.visual_training_dataset import (
    VisualTrainingDataset,
)


@dataclass(frozen=True, slots=True)
class CompactTcnTrainingConfig:
    seed: int
    epochs: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    gradient_clip_norm: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.seed, int)
            or isinstance(self.seed, bool)
            or self.seed < 0
        ):
            raise ValueError("A seed deve ser um inteiro " "maior ou igual a zero.")

        positive_integer_fields = (
            (
                "epochs",
                self.epochs,
            ),
            (
                "batch_size",
                self.batch_size,
            ),
        )

        for field_name, value in positive_integer_fields:
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} deve ser um " "inteiro positivo.")

        if not isfinite(self.learning_rate) or self.learning_rate <= 0.0:
            raise ValueError("O learning rate deve ser finito " "e positivo.")

        if not isfinite(self.weight_decay) or self.weight_decay < 0.0:
            raise ValueError(
                "O weight decay deve ser finito " "e maior ou igual a zero."
            )

        if not isfinite(self.gradient_clip_norm) or self.gradient_clip_norm <= 0.0:
            raise ValueError("O gradient clip deve ser finito " "e positivo.")


@dataclass(frozen=True, slots=True)
class CompactTcnEvaluationMetrics:
    loss: float
    accuracy: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class CompactTcnEpochMetrics:
    epoch: int
    training: CompactTcnEvaluationMetrics
    validation: CompactTcnEvaluationMetrics


@dataclass(frozen=True, slots=True)
class CompactTcnTrainingResult:
    history: tuple[
        CompactTcnEpochMetrics,
        ...,
    ]
    best_epoch: int
    best_validation_accuracy: float
    best_validation_loss: float
    best_state_dict: dict[
        str,
        torch.Tensor,
    ]


@dataclass(frozen=True, slots=True)
class CompactTcnFinalEpochMetrics:
    epoch: int
    training: CompactTcnEvaluationMetrics


@dataclass(frozen=True, slots=True)
class CompactTcnFinalTrainingResult:
    history: tuple[CompactTcnFinalEpochMetrics, ...]
    final_epoch: int
    final_training_metrics: CompactTcnEvaluationMetrics
    final_state_dict: dict[str, torch.Tensor]


def build_default_compact_tcn_training_config() -> CompactTcnTrainingConfig:
    return CompactTcnTrainingConfig(
        seed=2026,
        epochs=80,
        batch_size=12,
        learning_rate=0.001,
        weight_decay=0.0001,
        gradient_clip_norm=1.0,
    )


def configure_compact_tcn_reproducibility(
    seed: int,
) -> None:
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("A seed deve ser um inteiro " "maior ou igual a zero.")

    random.seed(seed)

    np.random.seed(seed % (2**32))

    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    torch.use_deterministic_algorithms(True)

    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def build_reproducible_compact_tcn(
    model_config: CompactTcnConfig,
    training_config: CompactTcnTrainingConfig,
) -> CompactTcn:
    configure_compact_tcn_reproducibility(seed=training_config.seed)

    return CompactTcn(config=model_config)


def visual_training_dataset_to_tensors(
    dataset: VisualTrainingDataset,
) -> tuple[
    torch.Tensor,
    torch.Tensor,
]:
    if not dataset.samples:
        raise ValueError("O dataset de treinamento não pode ser vazio.")

    feature_arrays = tuple(sample.features.copy() for sample in dataset.samples)

    features_array = np.stack(
        feature_arrays,
        axis=0,
    ).astype(
        np.float32,
        copy=False,
    )

    label_indices = tuple(sample.label_index for sample in dataset.samples)

    features = torch.tensor(
        features_array,
        dtype=torch.float32,
    )

    labels = torch.tensor(
        label_indices,
        dtype=torch.int64,
    )

    return (
        features,
        labels,
    )


def _clone_state_dict(
    model: CompactTcn,
) -> dict[
    str,
    torch.Tensor,
]:
    return {
        name: tensor.detach().cpu().clone()
        for name, tensor in model.state_dict().items()
    }


def evaluate_compact_tcn(
    model: CompactTcn,
    dataset: VisualTrainingDataset,
    device: str | torch.device,
) -> CompactTcnEvaluationMetrics:
    features, labels = visual_training_dataset_to_tensors(dataset)

    torch_device = torch.device(device)

    model.to(torch_device)

    features = features.to(torch_device)

    labels = labels.to(torch_device)

    criterion = nn.CrossEntropyLoss(reduction="sum")

    model.eval()

    with torch.no_grad():
        logits = model(features)

        total_loss = float(
            criterion(
                logits,
                labels,
            ).item()
        )

        predictions = torch.argmax(
            logits,
            dim=1,
        )

        correct_count = int((predictions == labels).sum().item())

    sample_count = int(labels.shape[0])

    return CompactTcnEvaluationMetrics(
        loss=(total_loss / sample_count),
        accuracy=(correct_count / sample_count),
        sample_count=sample_count,
    )


def _train_one_epoch(
    model: CompactTcn,
    features: torch.Tensor,
    labels: torch.Tensor,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    config: CompactTcnTrainingConfig,
    device: torch.device,
    generator: torch.Generator,
) -> None:
    model.train()

    sample_count = int(features.shape[0])

    indices = torch.randperm(
        sample_count,
        generator=generator,
    )

    for batch_start in range(
        0,
        sample_count,
        config.batch_size,
    ):
        batch_end = min(
            batch_start + config.batch_size,
            sample_count,
        )

        batch_indices = indices[batch_start:batch_end]

        batch_features = features[batch_indices].to(device)

        batch_labels = labels[batch_indices].to(device)

        optimizer.zero_grad(set_to_none=True)

        logits = model(batch_features)

        loss = criterion(
            logits,
            batch_labels,
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=(config.gradient_clip_norm),
        )

        optimizer.step()


def _is_better_checkpoint(
    validation: CompactTcnEvaluationMetrics,
    best_accuracy: float | None,
    best_loss: float | None,
) -> bool:
    if best_accuracy is None or best_loss is None:
        return True

    if validation.accuracy > best_accuracy:
        return True

    if validation.accuracy == best_accuracy and validation.loss < best_loss:
        return True

    return False


def train_compact_tcn(
    model: CompactTcn,
    training_dataset: VisualTrainingDataset,
    validation_dataset: VisualTrainingDataset,
    config: CompactTcnTrainingConfig,
    device: str | torch.device,
) -> CompactTcnTrainingResult:
    configure_compact_tcn_reproducibility(seed=config.seed)

    training_features, training_labels = visual_training_dataset_to_tensors(
        training_dataset
    )

    visual_training_dataset_to_tensors(validation_dataset)

    torch_device = torch.device(device)

    model.to(torch_device)

    generator = torch.Generator(device="cpu")

    generator.manual_seed(config.seed)

    criterion = nn.CrossEntropyLoss()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    history = []

    best_epoch = 0
    best_accuracy = None
    best_loss = None
    best_state_dict = None

    for epoch in range(
        1,
        config.epochs + 1,
    ):
        _train_one_epoch(
            model=model,
            features=training_features,
            labels=training_labels,
            optimizer=optimizer,
            criterion=criterion,
            config=config,
            device=torch_device,
            generator=generator,
        )

        training_metrics = evaluate_compact_tcn(
            model=model,
            dataset=training_dataset,
            device=torch_device,
        )

        validation_metrics = evaluate_compact_tcn(
            model=model,
            dataset=validation_dataset,
            device=torch_device,
        )

        epoch_metrics = CompactTcnEpochMetrics(
            epoch=epoch,
            training=training_metrics,
            validation=validation_metrics,
        )

        history.append(epoch_metrics)

        if _is_better_checkpoint(
            validation=validation_metrics,
            best_accuracy=best_accuracy,
            best_loss=best_loss,
        ):
            best_epoch = epoch
            best_accuracy = validation_metrics.accuracy
            best_loss = validation_metrics.loss
            best_state_dict = _clone_state_dict(model)

    if best_state_dict is None or best_accuracy is None or best_loss is None:
        raise RuntimeError(
            "Nenhum checkpoint válido foi " "produzido durante o treinamento."
        )

    model.load_state_dict(best_state_dict)

    model.eval()

    return CompactTcnTrainingResult(
        history=tuple(history),
        best_epoch=best_epoch,
        best_validation_accuracy=(best_accuracy),
        best_validation_loss=best_loss,
        best_state_dict=(
            {name: tensor.clone() for name, tensor in (best_state_dict.items())}
        ),
    )


def train_compact_tcn_fixed_epochs(
    model: CompactTcn,
    training_dataset: VisualTrainingDataset,
    config: CompactTcnTrainingConfig,
    device: str | torch.device,
) -> CompactTcnFinalTrainingResult:
    configure_compact_tcn_reproducibility(seed=config.seed)
    training_features, training_labels = visual_training_dataset_to_tensors(
        training_dataset
    )
    torch_device = torch.device(device)
    model.to(torch_device)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(config.seed)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    history = []
    for epoch in range(1, config.epochs + 1):
        _train_one_epoch(
            model=model,
            features=training_features,
            labels=training_labels,
            config=config,
            device=torch_device,
            generator=generator,
            criterion=criterion,
            optimizer=optimizer,
        )
        training_metrics = evaluate_compact_tcn(
            model=model,
            dataset=training_dataset,
            device=torch_device,
        )
        history.append(
            CompactTcnFinalEpochMetrics(epoch=epoch, training=training_metrics)
        )

    return CompactTcnFinalTrainingResult(
        history=tuple(history),
        final_epoch=config.epochs,
        final_training_metrics=history[-1].training,
        final_state_dict=_clone_state_dict(model),
    )
