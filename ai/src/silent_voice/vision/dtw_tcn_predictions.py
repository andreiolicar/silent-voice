from dataclasses import dataclass
from pathlib import Path

import torch

from silent_voice.models.compact_tcn import CompactTcn
from silent_voice.models.compact_tcn_config import CompactTcnConfig
from silent_voice.models.compact_tcn_training import visual_training_dataset_to_tensors
from silent_voice.vision.feature_sample import VisualFeatureSample
from silent_voice.vision.strong_dtw_classifier import StrongDtwVisualClassifier
from silent_voice.vision.strong_dtw_experiment import (
    build_frozen_strong_dtw_candidates,
)
from silent_voice.vision.visual_cross_validation import (
    build_leave_one_session_out_folds,
)
from silent_voice.vision.visual_experiment_defaults import (
    SESSION_IDS,
    build_default_segmentation_config,
)
from silent_voice.vision.visual_sample_segmentation import (
    segment_visual_feature_sample,
)
from silent_voice.vision.visual_training_dataset import (
    DEFAULT_VISUAL_LABELS,
    build_visual_training_dataset,
)


CHECKPOINT_FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class SamplePrediction:
    sample_id: str
    validation_session_id: str
    expected_label: str
    expected_label_index: int
    predicted_label: str
    predicted_label_index: int
    correct: bool


@dataclass(frozen=True, slots=True)
class PairedPredictions:
    labels: tuple[str, ...]
    dtw_predictions: tuple[SamplePrediction, ...]
    tcn_predictions: tuple[SamplePrediction, ...]


def _validate_samples(samples: tuple[VisualFeatureSample, ...]) -> None:
    if not samples:
        raise ValueError("O dataset de comparação não pode ser vazio.")

    sample_ids = [sample.sample_id for sample in samples]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("O dataset possui sample_id duplicado.")

    for sample in samples:
        if sample.session_id not in SESSION_IDS:
            raise ValueError(f"Sessão fora dos folds congelados: {sample.session_id}.")
        if sample.label not in DEFAULT_VISUAL_LABELS:
            raise ValueError(f"Label fora do vocabulário congelado: {sample.label}.")


def _load_checkpoint(
    checkpoint_path: Path,
    validation_session_id: str,
    training_sample_ids: tuple[str, ...],
    validation_sample_ids: tuple[str, ...],
) -> CompactTcn:
    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=True,
    )

    if checkpoint.get("format_version") != CHECKPOINT_FORMAT_VERSION:
        raise ValueError(f"format_version inválido em {checkpoint_path}.")
    if checkpoint.get("validation_session_id") != validation_session_id:
        raise ValueError(f"validation_session_id inválido em {checkpoint_path}.")
    if tuple(checkpoint.get("labels", ())) != DEFAULT_VISUAL_LABELS:
        raise ValueError(f"labels inválidos em {checkpoint_path}.")
    if tuple(checkpoint.get("training_sample_ids", ())) != training_sample_ids:
        raise ValueError(f"training_sample_ids inválidos em {checkpoint_path}.")
    if tuple(checkpoint.get("validation_sample_ids", ())) != validation_sample_ids:
        raise ValueError(f"validation_sample_ids inválidos em {checkpoint_path}.")

    metadata = checkpoint.get("model_config")
    if not isinstance(metadata, dict):
        raise ValueError(f"model_config ausente em {checkpoint_path}.")

    config_fields = (
        "frame_count",
        "input_feature_count",
        "hidden_channel_count",
        "class_count",
        "kernel_size",
        "dilations",
        "convolutions_per_block",
        "dropout",
    )
    try:
        config_values = {field: metadata[field] for field in config_fields}
        config_values["dilations"] = tuple(config_values["dilations"])
        config = CompactTcnConfig(**config_values)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"model_config inválido em {checkpoint_path}.") from error

    if (
        config.frame_count != 64
        or config.input_feature_count != 160
        or config.class_count != len(DEFAULT_VISUAL_LABELS)
    ):
        raise ValueError(f"model_config incompatível em {checkpoint_path}.")
    if metadata.get("receptive_field_frames") != config.receptive_field_frames:
        raise ValueError(f"receptive_field_frames inválido em {checkpoint_path}.")

    model = CompactTcn(config=config)
    state_dict = checkpoint.get("state_dict")
    if not isinstance(state_dict, dict):
        raise ValueError(f"state_dict ausente em {checkpoint_path}.")
    model.load_state_dict(state_dict, strict=True)
    model.to("cpu")
    model.eval()
    return model


def _make_prediction(
    sample_id: str,
    session_id: str,
    expected_label: str,
    predicted_label: str,
    label_to_index: dict[str, int],
) -> SamplePrediction:
    return SamplePrediction(
        sample_id=sample_id,
        validation_session_id=session_id,
        expected_label=expected_label,
        expected_label_index=label_to_index[expected_label],
        predicted_label=predicted_label,
        predicted_label_index=label_to_index[predicted_label],
        correct=predicted_label == expected_label,
    )


def generate_paired_predictions(
    samples: tuple[VisualFeatureSample, ...],
    checkpoint_directory: str | Path,
) -> PairedPredictions:
    _validate_samples(samples)
    segmentation_config = build_default_segmentation_config()
    segmented_samples = tuple(
        segment_visual_feature_sample(sample=sample, config=segmentation_config).sample
        for sample in samples
    )
    folds = build_leave_one_session_out_folds(
        samples=segmented_samples,
        session_ids=SESSION_IDS,
    )

    checkpoint_directory = Path(checkpoint_directory)
    models = {}
    for fold in folds:
        session_id = fold.validation_session_id
        models[session_id] = _load_checkpoint(
            checkpoint_path=checkpoint_directory / f"compact_tcn_{session_id}.pt",
            validation_session_id=session_id,
            training_sample_ids=tuple(sample.sample_id for sample in fold.train),
            validation_sample_ids=tuple(sample.sample_id for sample in fold.validation),
        )

    legacy_raw = next(
        candidate
        for candidate in build_frozen_strong_dtw_candidates()
        if candidate.name == "LEGACY_RAW"
    )
    label_to_index = {label: index for index, label in enumerate(DEFAULT_VISUAL_LABELS)}
    dtw_predictions = []
    tcn_predictions = []

    for fold in folds:
        session_id = fold.validation_session_id
        classifier = StrongDtwVisualClassifier(
            training_samples=fold.train,
            config=legacy_raw.config,
        )
        training_dataset = build_visual_training_dataset(fold.validation)
        features, _ = visual_training_dataset_to_tensors(training_dataset)
        with torch.no_grad():
            logits = models[session_id](features.to("cpu"))
            tcn_indices = torch.argmax(logits, dim=1).tolist()

        for sample, tcn_index in zip(fold.validation, tcn_indices, strict=True):
            dtw_label = classifier.predict(sample).label
            dtw_predictions.append(
                _make_prediction(
                    sample_id=sample.sample_id,
                    session_id=session_id,
                    expected_label=sample.label,
                    predicted_label=dtw_label,
                    label_to_index=label_to_index,
                )
            )
            tcn_predictions.append(
                _make_prediction(
                    sample_id=sample.sample_id,
                    session_id=session_id,
                    expected_label=sample.label,
                    predicted_label=DEFAULT_VISUAL_LABELS[tcn_index],
                    label_to_index=label_to_index,
                )
            )

    dtw_keys = tuple(
        (item.validation_session_id, item.sample_id) for item in dtw_predictions
    )
    tcn_keys = tuple(
        (item.validation_session_id, item.sample_id) for item in tcn_predictions
    )
    if dtw_keys != tcn_keys or len(dtw_keys) != len(set(dtw_keys)):
        raise RuntimeError("As previsões DTW e TCN não pareiam 1:1.")

    return PairedPredictions(
        labels=DEFAULT_VISUAL_LABELS,
        dtw_predictions=tuple(dtw_predictions),
        tcn_predictions=tuple(tcn_predictions),
    )
