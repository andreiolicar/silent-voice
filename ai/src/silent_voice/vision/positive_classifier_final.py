"""Congelamento e inferência do classificador positivo híbrido selecionado."""

import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch
from torch import nn

from silent_voice.vision.hybrid_features import (
    HYBRID_EPSILON,
    HybridSample,
    class_minimum_dtw_distances,
    equal_energy_fusion,
    normalized_reciprocal_evidence,
    raw_current_dtw_distance,
)
from silent_voice.vision.hybrid_linear_probe import train_hybrid_linear
from silent_voice.vision.hybrid_loso import (
    A_NAME,
    OUTPUT_RELATIVE_PATH as HYBRID_RESULT_RELATIVE_PATH,
    _validate_hybrid_samples,
    preflight_hybrid_loso,
)
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.swinlip_embedding_dataset import (
    OUTPUT_MANIFEST_RELATIVE_PATH,
)
from silent_voice.vision.swinlip_frozen_loso import EMBEDDING_MANIFEST_SHA256
from silent_voice.vision.swinlip_frozen_probe import (
    LINEAR_EPOCHS,
    LINEAR_GRADIENT_CLIP_NORM,
    LINEAR_LEARNING_RATE,
    LINEAR_SEED,
    LINEAR_WEIGHT_DECAY,
)
from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

CLASSIFIER_ID = A_NAME
REPRESENTATION_ID = "HYBRID_CLIP_DTW_EVIDENCE"
FROZEN_STATE = "POSITIVE_CLASSIFIER_FROZEN_BEFORE_REJECTION"
FORMAT_VERSION = 1
INPUT_DIMENSION = 1670
OUTPUT_DIMENSION = 6
CHECKPOINT_RELATIVE_PATH = Path(
    "data/processed/models/cycle_06_hybrid_positive_classifier.pt"
)
CONFIG_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_positive_classifier_final_config.json"
)
ROI_MANIFEST_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_mouth_roi_manifest.json"
)
ROI_MANIFEST_SHA256 = "e6f8b2952f40ccfa8c2988d0909c35a14dd6ae42821e9fc55cb7f5abe3995ee2"
HYBRID_RESULT_SHA256 = (
    "1344d4271dfa3d19c06c273846a4efb39cc738d399ebef65552fcddbefcd39e0"
)
SWINLIP_SOURCE = "https://github.com/park-ing/SwinLip.git"
SWINLIP_COMMIT = "0be70b224e42619f72ad283e85303f5e10544004"
SWINLIP_CHECKPOINT_SHA256 = (
    "32f77c3ac7ff6cc4e970bf8dd53b1dade84d1905dd7b30d95ca105380b6cd6f5"
)
SWINLIP_PARAMETER_COUNT = 53844608


def segmented_feature_sha256(features: np.ndarray) -> str:
    """Hash canônico dos valores float32 segmentados, com shape no domínio."""
    array = np.asarray(features)
    if (
        array.ndim != 2
        or array.shape[0] == 0
        or array.shape[1] != 160
        or array.dtype != np.float32
        or not np.isfinite(array).all()
    ):
        raise ValueError("Template segmentado exige float32 finito (T,160).")
    digest = hashlib.sha256()
    digest.update(f"float32:{array.shape[0]}:160:".encode("ascii"))
    digest.update(np.ascontiguousarray(array.astype("<f4")).tobytes())
    return digest.hexdigest()


def clip_embedding_sha256(clip: np.ndarray) -> str:
    """Hash do conteúdo do clip usado, além do hash do NPZ de origem."""
    values = np.asarray(clip)
    if (
        values.shape != (1664,)
        or values.dtype != np.float32
        or not np.isfinite(values).all()
    ):
        raise ValueError("clip_embedding deve ser float32 finito de 1664-D.")
    digest = hashlib.sha256(b"float32:1664:")
    digest.update(np.ascontiguousarray(values.astype("<f4")).tobytes())
    return digest.hexdigest()


def canonical_config_sha256(config: dict) -> str:
    """Digest do payload JSON, excluindo seu próprio campo de hash."""
    payload = {key: value for key, value in config.items() if key != "config_sha256"}
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_swinlip_provenance(manifest: dict) -> None:
    """Confere a fonte oficial congelada sem executar o encoder."""
    expected = {
        "source_repository": SWINLIP_SOURCE,
        "source_commit": SWINLIP_COMMIT,
        "checkpoint_sha256": SWINLIP_CHECKPOINT_SHA256,
        "roi_manifest_sha256": ROI_MANIFEST_SHA256,
        "parameter_count": SWINLIP_PARAMETER_COUNT,
        "trainable_parameter_count": 0,
        "sample_count": 54,
        "heldouts_used": False,
        "clip_embedding_shape": [1664],
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Proveniência SwinLip congelada divergente.")


def build_final_training_matrix(
    samples: tuple[HybridSample, ...],
    distance_fn: Callable[[object, object], float] = raw_current_dtw_distance,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Evidência leave-self-out dos 54 exemplos, com 54 templates autorizados."""
    _validate_hybrid_samples(samples)
    for item in samples:
        segmented_feature_sha256(item.features)
    distances_cache: dict[tuple[str, str], float] = {}

    def cached_distance(first: HybridSample, second: HybridSample) -> float:
        key = tuple(sorted((first.sample_id, second.sample_id)))
        if key not in distances_cache:
            distances_cache[key] = float(distance_fn(first, second))
        return distances_cache[key]

    vectors = []
    records = []
    for sample in samples:
        distances = class_minimum_dtw_distances(sample, samples, cached_distance)
        evidence = normalized_reciprocal_evidence(distances)
        vectors.append(equal_energy_fusion(sample.clip_embedding, evidence, 1670))
        records.append(
            {
                "sample_id": sample.sample_id,
                "dtw_distances": distances.tolist(),
                "evidence_values": evidence.tolist(),
                "class_template_counts": [
                    sum(
                        template.label_index == index
                        and template.sample_id != sample.sample_id
                        for template in samples
                    )
                    for index in range(6)
                ],
            }
        )
    return (
        np.stack(vectors).astype(np.float32),
        np.asarray([item.label_index for item in samples], dtype=np.int64),
        records,
    )


def build_future_feature(
    query: HybridSample,
    templates: tuple[HybridSample, ...],
    distance_fn: Callable[[object, object], float] = raw_current_dtw_distance,
) -> tuple[np.ndarray, list[float]]:
    """Query nova usa todos os 54 templates; ID existente é recusado."""
    _validate_hybrid_samples(templates)
    if query.sample_id in {item.sample_id for item in templates}:
        raise ValueError("Query nova não pode reutilizar sample_id do template bank.")
    if (
        query.clip_embedding.shape != (1664,)
        or query.clip_embedding.dtype != np.float32
        or not np.isfinite(query.clip_embedding).all()
        or query.features.ndim != 2
        or query.features.shape[1] != 160
        or not np.isfinite(query.features).all()
    ):
        raise ValueError("Query positiva híbrida inválida.")
    distances = class_minimum_dtw_distances(query, templates, distance_fn)
    evidence = normalized_reciprocal_evidence(distances)
    return equal_energy_fusion(query.clip_embedding, evidence, 1670), distances.tolist()


@dataclass(frozen=True, slots=True)
class FrozenPositiveClassifier:
    model: nn.Linear
    templates: tuple[HybridSample, ...]
    config: dict

    def predict_feature(self, feature_vector: np.ndarray) -> dict:
        """Retorna somente logits e classe, sem interpretação de rejection."""
        vector = np.asarray(feature_vector)
        if (
            vector.shape != (INPUT_DIMENSION,)
            or vector.dtype != np.float32
            or not np.isfinite(vector).all()
        ):
            raise ValueError("Vetor híbrido deve ser float32 finito de 1670-D.")
        self.model.eval()
        with torch.no_grad():
            logits = self.model(torch.from_numpy(vector).to("cpu"))
        index = int(torch.argmax(logits).item())
        return {
            "logits": [float(value) for value in logits.tolist()],
            "predicted_label_index": index,
            "predicted_label": DEFAULT_VISUAL_LABELS[index],
        }

    def predict_query(self, query: HybridSample) -> dict:
        """Forma feature com todas as templates para query nova."""
        vector, distances = build_future_feature(query, self.templates)
        return {**self.predict_feature(vector), "dtw_distances": distances}


def save_frozen_positive_classifier(
    model: nn.Linear,
    samples: tuple[HybridSample, ...],
    provenance: dict,
    diagnostics: dict,
    checkpoint_path: Path,
    config_path: Path,
) -> dict:
    """Persiste cabeça e banco em formato seguro; nunca sobrescreve."""
    _validate_hybrid_samples(samples)
    if model.in_features != INPUT_DIMENSION or model.out_features != OUTPUT_DIMENSION:
        raise ValueError("Cabeça final deve ser Linear(1670,6).")
    if checkpoint_path.exists() or config_path.exists():
        raise FileExistsError("Checkpoint ou config final já existe.")
    ids = {item.sample_id for item in samples}
    for key in ("source_npz_sha256", "embedding_npz_sha256"):
        if set(provenance[key]) != ids:
            raise ValueError("Hashes de inputs não cobrem as 54 amostras.")
    templates = [
        {
            "sample_id": item.sample_id,
            "session_id": item.session_id,
            "label": item.label,
            "label_index": item.label_index,
            "source_npz_sha256": provenance["source_npz_sha256"][item.sample_id],
            "embedding_npz_sha256": provenance["embedding_npz_sha256"][item.sample_id],
            "clip_embedding_sha256": clip_embedding_sha256(item.clip_embedding),
            "segmented_feature_sha256": segmented_feature_sha256(item.features),
            "shape": list(item.features.shape),
        }
        for item in samples
    ]
    checkpoint = {
        "format_version": FORMAT_VERSION,
        "model_id": CLASSIFIER_ID,
        "representation_id": REPRESENTATION_ID,
        "input_dim": INPUT_DIMENSION,
        "output_dim": OUTPUT_DIMENSION,
        "labels": list(DEFAULT_VISUAL_LABELS),
        "state_dict": {key: value.cpu() for key, value in model.state_dict().items()},
        "template_features": [
            torch.from_numpy(np.ascontiguousarray(item.features.copy()))
            for item in samples
        ],
        "template_sample_ids": [item.sample_id for item in samples],
    }
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint_path.open("xb") as stream:
        torch.save(checkpoint, stream)
    config = {
        "format_version": FORMAT_VERSION,
        "state": FROZEN_STATE,
        "model_id": CLASSIFIER_ID,
        "representation_id": REPRESENTATION_ID,
        "input_dim": INPUT_DIMENSION,
        "output_dim": OUTPUT_DIMENSION,
        "labels": list(DEFAULT_VISUAL_LABELS),
        "code_commit": provenance["code_commit"],
        "selection_loso": {"correct_count": 51, "sample_count": 54},
        "swinlip": {
            "encoder_id": "SWINLIP_BASE_FROZEN",
            "source_repository": SWINLIP_SOURCE,
            "source_commit": SWINLIP_COMMIT,
            "checkpoint_sha256": SWINLIP_CHECKPOINT_SHA256,
            "parameter_count": SWINLIP_PARAMETER_COUNT,
            "frozen": True,
        },
        "roi_manifest_sha256": provenance["roi_manifest_sha256"],
        "embedding_manifest_sha256": provenance["embedding_manifest_sha256"],
        "segmentation": {
            "velocity_start_index": 80,
            "smoothing_window": 5,
            "threshold_ratio": 0.25,
            "padding_frames": 6,
            "minimum_segment_frames": 18,
            "minimum_activity_range": 1e-6,
        },
        "dtw": {
            "cost": "raw_accumulated",
            "warping": "unrestricted",
            "class_evidence": "minimum_distance",
            "train_self_exclusion": True,
            "future_query_template_count": 54,
            "path_normalization": False,
            "class_scaling": False,
        },
        "fusion": {
            "epsilon": HYBRID_EPSILON,
            "evidence": "reciprocal_then_l2",
            "clip": "l2",
            "branch_scale": "1/sqrt(2)",
        },
        "training": {
            "seed": LINEAR_SEED,
            "device": "cpu",
            "epochs": LINEAR_EPOCHS,
            "optimizer": "AdamW",
            "learning_rate": LINEAR_LEARNING_RATE,
            "weight_decay": LINEAR_WEIGHT_DECAY,
            "loss": "CrossEntropyLoss",
            "batch_size": 54,
            "gradient_clip_norm": LINEAR_GRADIENT_CLIP_NORM,
            "checkpoint_rule": "epoch_500_only",
        },
        "training_dataset": {
            "sample_count": 54,
            "sample_ids": [item.sample_id for item in samples],
            "session_ids": list(SESSION_IDS),
            "heldouts_used": False,
            "negatives_used": False,
            "rejection_data_used": False,
        },
        "template_bank": {
            "sample_count": 54,
            "class_counts": [9] * 6,
            "templates": templates,
        },
        "checkpoint": {
            "file_name": checkpoint_path.name,
            "sha256": sha256_file(checkpoint_path),
        },
        "final_development_fit_loss": diagnostics["final_training_loss"],
        "final_development_fit_accuracy": diagnostics["final_training_accuracy"],
        "classifier_frozen_before_rejection": True,
        "heldouts_used": False,
        "negatives_used": False,
        "rejection_data_used": False,
    }
    config["config_sha256"] = canonical_config_sha256(config)
    with config_path.open("x", encoding="utf-8") as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return config


def load_frozen_positive_classifier(
    checkpoint_path: Path, config_path: Path
) -> FrozenPositiveClassifier:
    """Valida hashes, metadados, pesos e 54 templates antes de inferência."""
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if config.get("config_sha256") != canonical_config_sha256(config):
        raise ValueError("SHA do config final divergiu.")
    expected = {
        "format_version": FORMAT_VERSION,
        "state": FROZEN_STATE,
        "model_id": CLASSIFIER_ID,
        "representation_id": REPRESENTATION_ID,
        "input_dim": INPUT_DIMENSION,
        "output_dim": OUTPUT_DIMENSION,
        "labels": list(DEFAULT_VISUAL_LABELS),
        "roi_manifest_sha256": ROI_MANIFEST_SHA256,
        "embedding_manifest_sha256": EMBEDDING_MANIFEST_SHA256,
        "classifier_frozen_before_rejection": True,
        "heldouts_used": False,
        "negatives_used": False,
        "rejection_data_used": False,
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError("Metadados, labels ou estado do config final inválidos.")
    expected_swinlip = {
        "encoder_id": "SWINLIP_BASE_FROZEN",
        "source_repository": SWINLIP_SOURCE,
        "source_commit": SWINLIP_COMMIT,
        "checkpoint_sha256": SWINLIP_CHECKPOINT_SHA256,
        "parameter_count": SWINLIP_PARAMETER_COUNT,
        "frozen": True,
    }
    if config.get("swinlip") != expected_swinlip:
        raise ValueError("Proveniência SwinLip do config final inválida.")
    if config["checkpoint"]["file_name"] != Path(checkpoint_path).name:
        raise ValueError("Caminho do checkpoint final divergente.")
    if sha256_file(checkpoint_path) != config["checkpoint"]["sha256"]:
        raise ValueError("SHA do checkpoint final divergiu.")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    for key in (
        "format_version",
        "model_id",
        "representation_id",
        "input_dim",
        "output_dim",
        "labels",
    ):
        if checkpoint.get(key) != config[key]:
            raise ValueError("Checkpoint final incompatível com config.")
    model = nn.Linear(INPUT_DIMENSION, OUTPUT_DIMENSION, bias=True).to("cpu")
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval()
    records = config["template_bank"]["templates"]
    tensors = checkpoint["template_features"]
    ids = checkpoint["template_sample_ids"]
    if (
        len(records) != 54
        or len(tensors) != 54
        or len(ids) != 54
        or [item["sample_id"] for item in records] != ids
        or Counter(item["label_index"] for item in records)
        != Counter({index: 9 for index in range(6)})
        or config["template_bank"]["sample_count"] != 54
        or config["template_bank"]["class_counts"] != [9] * 6
    ):
        raise ValueError("Banco final não possui 54 templates válidos.")
    templates = []
    for record, tensor in zip(records, tensors):
        values = tensor.numpy()
        if (
            record["session_id"] not in SESSION_IDS
            or record["label"] != DEFAULT_VISUAL_LABELS[record["label_index"]]
            or list(values.shape) != record["shape"]
            or segmented_feature_sha256(values) != record["segmented_feature_sha256"]
        ):
            raise ValueError("Hash ou metadados de template final inválidos.")
        templates.append(
            HybridSample(
                record["sample_id"],
                record["session_id"],
                record["label"],
                record["label_index"],
                np.zeros(1664, dtype=np.float32),
                values.copy(),
            )
        )
    bank = tuple(templates)
    _validate_hybrid_samples(bank)
    return FrozenPositiveClassifier(model, bank, config)


def preflight_final_positive_fit(repository_root: Path) -> dict:
    """Valida os 54 inputs e protocolo sem treinar nem prever."""
    root = Path(repository_root).resolve()
    if (root / CHECKPOINT_RELATIVE_PATH).exists() or (
        root / CONFIG_RELATIVE_PATH
    ).exists():
        raise FileExistsError("Classificador positivo final já foi gerado.")
    prepared = preflight_hybrid_loso(root)
    selection_path = root / HYBRID_RESULT_RELATIVE_PATH
    if sha256_file(selection_path) != HYBRID_RESULT_SHA256:
        raise ValueError("SHA do resultado de seleção 6.6 divergiu.")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if (
        selection.get("development_preferred_positive_classifier") != CLASSIFIER_ID
        or selection["candidates"][CLASSIFIER_ID]["metrics"]["correct_count"] != 51
    ):
        raise ValueError("Seleção pré-registrada do híbrido A divergiu.")
    if sha256_file(root / ROI_MANIFEST_RELATIVE_PATH) != ROI_MANIFEST_SHA256:
        raise ValueError("SHA do manifesto ROI divergiu.")
    manifest = json.loads(
        (root / OUTPUT_MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    validate_swinlip_provenance(manifest)
    samples = prepared["samples"]
    for sample in samples:
        segmented_feature_sha256(sample.features)
    return {
        **prepared,
        "sample_count": len(samples),
        "class_counts": [
            sum(item.label_index == index for item in samples) for index in range(6)
        ],
        "output_absent": True,
        "selection_result_sha256": HYBRID_RESULT_SHA256,
        "roi_manifest_sha256": ROI_MANIFEST_SHA256,
        "swinlip_parameter_count": SWINLIP_PARAMETER_COUNT,
    }


def run_final_positive_fit(repository_root: Path) -> dict:
    """Treina uma vez após commit limpo e congela checkpoint/config."""
    root = Path(repository_root).resolve()
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError("Worktree versionável deve estar limpo antes do fit.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    prepared = preflight_final_positive_fit(root)
    samples = prepared["samples"]
    matrix, labels, evidence_records = build_final_training_matrix(samples)
    model, diagnostics = train_hybrid_linear(matrix, labels)
    source_hashes = {
        Path(path).stem: digest for path, digest in prepared["visual_hashes"].items()
    }
    provenance = {
        "code_commit": commit,
        "source_npz_sha256": source_hashes,
        "embedding_npz_sha256": prepared["embedding_hashes"],
        "embedding_manifest_sha256": prepared["embedding_manifest_sha256"],
        "roi_manifest_sha256": prepared["roi_manifest_sha256"],
    }
    checkpoint_path = root / CHECKPOINT_RELATIVE_PATH
    config_path = root / CONFIG_RELATIVE_PATH
    config = save_frozen_positive_classifier(
        model, samples, provenance, diagnostics, checkpoint_path, config_path
    )
    frozen = load_frozen_positive_classifier(checkpoint_path, config_path)
    predictions = [
        frozen.predict_feature(vector)["predicted_label_index"] for vector in matrix
    ]
    fit_accuracy = (
        sum(predicted == expected for predicted, expected in zip(predictions, labels))
        / 54
    )
    if fit_accuracy != config["final_development_fit_accuracy"]:
        raise ValueError("Fit técnico após reload divergiu do diagnóstico de treino.")
    return {
        "state": FROZEN_STATE,
        "sample_count": 54,
        "class_counts": [9] * 6,
        "checkpoint_path": CHECKPOINT_RELATIVE_PATH.as_posix(),
        "checkpoint_sha256": config["checkpoint"]["sha256"],
        "config_path": CONFIG_RELATIVE_PATH.as_posix(),
        "config_sha256": config["config_sha256"],
        "config_file_sha256": sha256_file(config_path),
        "final_development_fit_loss": config["final_development_fit_loss"],
        "final_development_fit_accuracy": fit_accuracy,
        "training_epochs": LINEAR_EPOCHS,
        "model_id": CLASSIFIER_ID,
        "code_commit": commit,
        "heldouts_used": False,
        "negatives_used": False,
        "rejection_data_used": False,
        "training_evidence_count": len(evidence_records),
    }
