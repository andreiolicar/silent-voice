"""Extração auditável de embeddings SwinLip somente do desenvolvimento."""

import json
import statistics
import time
from collections import Counter
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch

from silent_voice.vision.dataset_collection_plan import build_visual_collection_plan
from silent_voice.vision.feature_sample_storage import load_visual_feature_sample
from silent_voice.vision.mouth_roi_dataset import (
    MANIFEST_RELATIVE_PATH,
    ROI_RELATIVE_ROOT,
    _load_sample,
    sha256_file,
    validate_mouth_roi_dataset,
)
from silent_voice.vision.swinlip_frozen_encoder import (
    EMBEDDING_FORMAT_VERSION,
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
    extract_embeddings,
    load_official_model,
    prepare_input,
    save_embedding_sample,
    select_source_frame_indices,
    validate_embedding_sample,
    validate_external_source,
)
from silent_voice.vision.visual_experiment_defaults import (
    SESSION_IDS,
    build_default_segmentation_config,
)
from silent_voice.vision.visual_sample_segmentation import segment_visual_feature_sample
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

ROI_MANIFEST_SHA256 = "e6f8b2952f40ccfa8c2988d0909c35a14dd6ae42821e9fc55cb7f5abe3995ee2"
OUTPUT_RELATIVE_ROOT = Path("data/processed/visual_swinlip_embeddings")
OUTPUT_MANIFEST_RELATIVE_PATH = Path(
    "data/processed/evaluation/cycle_06_swinlip_embedding_manifest.json"
)
SOURCE_RELATIVE_ROOT = Path("data/external/swinlip/source")
CHECKPOINT_RELATIVE_PATH = Path("data/external/swinlip/checkpoints/lrw_swinlip.pth")
SOURCE_FILES = (
    "LICENSE",
    "configs/swinlip.json",
    "models/__init__.py",
    "models/swinlip.py",
    "models/swinlip_blocks.py",
    "models/conformer.py",
    "models/densetcn.py",
    "models/se_module.py",
    "models/swish.py",
)


def aligned_segment_indices(roi: object, source: object) -> tuple[np.ndarray, object]:
    """Usa a segmentação 4.2 nos landmarks e mapeia aos mesmos frames ROI."""
    if (
        roi.sample_id != source.sample_id
        or roi.session_id != source.session_id
        or roi.label != source.label
        or roi.session_id not in SESSION_IDS
    ):
        raise ValueError("ROI e landmarks não representam a mesma amostra permitida.")
    count = roi.frame_count
    if (
        source.features.shape != (count, 160)
        or roi.frame_indices.shape != (count,)
        or not np.array_equal(roi.frame_indices, np.arange(count))
    ):
        raise ValueError("Frame indices ROI/landmarks divergentes.")
    if (
        roi.timestamps_ms.shape != (count,)
        or source.timestamps_ms.shape != (count,)
        or not np.allclose(roi.timestamps_ms, source.timestamps_ms, rtol=0, atol=1.0)
    ):
        raise ValueError("timestamp ROI/landmarks divergente.")
    segment = segment_visual_feature_sample(
        source, build_default_segmentation_config()
    ).segment
    if not segment.detected:
        raise ValueError(f"Segmentação congelada não detectou {roi.sample_id}.")
    indices = select_source_frame_indices(
        segment.start_frame, segment.end_frame_exclusive
    )
    if indices[0] != segment.start_frame or indices[-1] != (
        segment.end_frame_exclusive - 1
    ):
        raise ValueError("A seleção temporal não preservou as bordas do segmento.")
    return indices, segment


def validate_embedding_manifest(manifest: dict) -> None:
    """Confere cardinalidade e partição sem comparar previsão com rótulo."""
    expected = build_visual_collection_plan(SESSION_IDS, DEFAULT_VISUAL_LABELS, 3)
    samples = manifest.get("samples")
    if (
        manifest.get("format_version") != EMBEDDING_FORMAT_VERSION
        or manifest.get("sample_count") != 54
        or manifest.get("heldouts_used") is not False
        or not isinstance(samples, list)
        or len(samples) != 54
    ):
        raise ValueError("Manifesto SwinLip não contém 54 amostras de desenvolvimento.")
    by_id = {item.sample_id: item for item in expected}
    ids = [entry.get("sample_id") for entry in samples]
    if len(set(ids)) != 54 or set(ids) != set(by_id):
        raise ValueError("sample_id ausente, repetido ou fora do desenvolvimento.")
    counts_session = Counter()
    counts_label = Counter()
    for entry in samples:
        item = by_id[entry["sample_id"]]
        if (
            entry.get("session_id") != item.session_id
            or entry.get("label") != item.label
            or entry.get("label_index") != DEFAULT_VISUAL_LABELS.index(item.label)
            or any(
                not isinstance(entry.get(name), str)
                or len(entry[name]) != 64
                or any(ch not in "0123456789abcdef" for ch in entry[name])
                for name in ("embedding_sha256", "source_roi_sha256")
            )
        ):
            raise ValueError("Metadados ou SHA-256 de amostra inválidos.")
        counts_session[item.session_id] += 1
        counts_label[item.label] += 1
    if counts_session != Counter({session: 18 for session in SESSION_IDS}) or (
        counts_label != Counter({label: 9 for label in DEFAULT_VISUAL_LABELS})
    ):
        raise ValueError("Distribuição do desenvolvimento inesperada.")


def _preflight(root: Path) -> tuple[dict, list[tuple[object, np.ndarray, object]]]:
    roi_manifest_path = root / MANIFEST_RELATIVE_PATH
    if sha256_file(roi_manifest_path) != ROI_MANIFEST_SHA256:
        raise ValueError("SHA-256 do manifesto ROI difere do congelado na Task 6.2.")
    roi_manifest = validate_mouth_roi_dataset(root)
    if (root / OUTPUT_RELATIVE_ROOT).exists() or (
        root / OUTPUT_MANIFEST_RELATIVE_PATH
    ).exists():
        raise FileExistsError("Embeddings ou manifesto já existem; não sobrescrever.")
    prepared = []
    for entry in roi_manifest["samples"]:
        roi_path = root / entry["derived_roi_path"]
        roi = _load_sample(roi_path)
        source = load_visual_feature_sample(root / entry["source_npz_path"])
        indices, segment = aligned_segment_indices(roi, source)
        prepared.append((roi, indices, segment))
    if len(prepared) != 54:
        raise ValueError("Preflight exige exatamente 54 amostras.")
    return roi_manifest, prepared


def _metadata(root: Path, model: torch.nn.Module) -> dict:
    source = root / SOURCE_RELATIVE_ROOT
    checkpoint = root / CHECKPOINT_RELATIVE_PATH
    validate_external_source(source)
    if not checkpoint.is_file():
        raise FileNotFoundError("Checkpoint SwinLip Base oficial ausente.")
    return {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "source_file_sha256": {
            name: sha256_file(source / name) for name in SOURCE_FILES
        },
        "license": "Apache-2.0 (código oficial)",
        "config_path": "configs/swinlip.json",
        "config_sha256": sha256_file(source / "configs/swinlip.json"),
        "checkpoint_path": CHECKPOINT_RELATIVE_PATH.as_posix(),
        "checkpoint_sha256": sha256_file(checkpoint),
        "checkpoint_size_bytes": checkpoint.stat().st_size,
        "roi_manifest_sha256": ROI_MANIFEST_SHA256,
        "dependency_versions": {
            name: version(name)
            for name in (
                "torch",
                "torchvision",
                "timm",
                "numpy",
                "opencv-contrib-python",
            )
        },
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "trainable_parameter_count": sum(
            p.numel() for p in model.parameters() if p.requires_grad
        ),
        "preprocessing": {
            "source_size": [96, 96],
            "center_crop_size": [88, 88],
            "scale_divisor": 255.0,
            "mean": 0.421,
            "std": 0.165,
            "target_frame_count": 29,
            "temporal_sampling": "rint(linspace(start,end_inclusive,29))",
        },
        "segmentation_config": asdict(build_default_segmentation_config()),
    }


def preflight_development_embeddings(repository_root: Path) -> dict:
    """Valida as 54 fontes e o checkpoint sem executar qualquer inferência."""
    root = Path(repository_root).resolve()
    _, prepared = _preflight(root)
    model, _ = load_official_model(
        root / SOURCE_RELATIVE_ROOT, root / CHECKPOINT_RELATIVE_PATH
    )
    metadata = _metadata(root, model)
    return {"sample_count": len(prepared), **metadata}


def extract_development_embeddings(repository_root: Path) -> dict:
    """Extrai uma vez os 54 embeddings; nunca carrega sessões held-out."""
    root = Path(repository_root).resolve()
    roi_manifest, prepared = _preflight(root)
    model, _ = load_official_model(
        root / SOURCE_RELATIVE_ROOT, root / CHECKPOINT_RELATIVE_PATH
    )
    metadata = _metadata(root, model)
    if metadata["trainable_parameter_count"] != 0:
        raise ValueError("Encoder não congelado.")
    # Aquecimento sintético, sem rótulo ou saída de classificação.
    warmup = torch.zeros((1, 1, 29, 88, 88), dtype=torch.float32)
    for _ in range(2):
        extract_embeddings(model, warmup)
    records = []
    elapsed_ms = []
    frame_shapes = set()
    clip_shapes = set()
    for roi, indices, segment in prepared:
        tensor = prepare_input(roi.mouth_rois, indices)
        start = time.perf_counter()
        frame, clip = extract_embeddings(model, tensor)
        elapsed_ms.append((time.perf_counter() - start) * 1000.0)
        frame_shapes.add(frame.shape)
        clip_shapes.add(clip.shape)
        roi_path = root / ROI_RELATIVE_ROOT / f"{roi.sample_id}.npz"
        record = {
            "format_version": EMBEDDING_FORMAT_VERSION,
            "sample_id": roi.sample_id,
            "label": roi.label,
            "label_index": roi.label_index,
            "session_id": roi.session_id,
            "source_roi_sample_hash": sha256_file(roi_path),
            "roi_manifest_sha256": metadata["roi_manifest_sha256"],
            "source_repository": SOURCE_REPOSITORY,
            "source_commit": SOURCE_COMMIT,
            "checkpoint_sha256": metadata["checkpoint_sha256"],
            "config_sha256": metadata["config_sha256"],
            "spatial_preprocessing_json": json.dumps(metadata["preprocessing"]),
            "segmentation_config_json": json.dumps(metadata["segmentation_config"]),
            "segment_start_frame": segment.start_frame,
            "segment_end_frame_exclusive": segment.end_frame_exclusive,
            "selected_source_frame_indices": indices,
            "frame_embeddings": frame,
            "clip_embedding": clip,
            "frame_embedding_shape": np.asarray(frame.shape, dtype=np.int32),
            "clip_embedding_shape": np.asarray(clip.shape, dtype=np.int32),
            "dtype": "float32",
        }
        validate_embedding_sample(record)
        records.append(record)
    if len(frame_shapes) != 1 or len(clip_shapes) != 1:
        raise ValueError("Dimensões inconsistentes entre amostras.")
    if not np.any(np.var(np.stack([r["clip_embedding"] for r in records]), axis=0)):
        raise ValueError("Todos os clip embeddings são idênticos.")
    output_root = root / OUTPUT_RELATIVE_ROOT
    output_root.mkdir(parents=True, exist_ok=False)
    entries = []
    for record in records:
        path = output_root / f"{record['sample_id']}.npz"
        save_embedding_sample(record, path)
        entries.append(
            {
                "sample_id": record["sample_id"],
                "session_id": record["session_id"],
                "label": record["label"],
                "label_index": record["label_index"],
                "source_roi_sha256": record["source_roi_sample_hash"],
                "embedding_path": path.relative_to(root).as_posix(),
                "embedding_sha256": sha256_file(path),
                "selected_source_frame_indices": record[
                    "selected_source_frame_indices"
                ].tolist(),
            }
        )
    metadata.update(
        {
            "format_version": EMBEDDING_FORMAT_VERSION,
            "sample_count": len(entries),
            "total_source_roi_frames": roi_manifest["total_frames"],
            "heldouts_used": False,
            "frame_embedding_shape": list(next(iter(frame_shapes))),
            "clip_embedding_shape": list(next(iter(clip_shapes))),
            "dtype": "float32",
            "benchmark": {
                "device": "cpu",
                "input_shape": [1, 1, 29, 88, 88],
                "threads": torch.get_num_threads(),
                "warmup_count": 2,
                "sample_count": len(elapsed_ms),
                "p50_ms": statistics.median(elapsed_ms),
                "p95_ms": float(np.percentile(elapsed_ms, 95)),
                "min_ms": min(elapsed_ms),
                "max_ms": max(elapsed_ms),
                "peak_rss_bytes": None,
            },
            "samples": entries,
        }
    )
    validate_embedding_manifest(metadata)
    manifest_path = root / OUTPUT_MANIFEST_RELATIVE_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    validate_embedding_dataset(root)
    return metadata


def validate_embedding_dataset(repository_root: Path) -> dict:
    root = Path(repository_root).resolve()
    manifest_path = root / OUTPUT_MANIFEST_RELATIVE_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_embedding_manifest(manifest)
    if sha256_file(root / MANIFEST_RELATIVE_PATH) != manifest["roi_manifest_sha256"]:
        raise ValueError("Hash do manifesto ROI divergiu.")
    if sha256_file(root / CHECKPOINT_RELATIVE_PATH) != manifest["checkpoint_sha256"]:
        raise ValueError("Hash do checkpoint divergiu.")
    observed = {
        path for path in (root / OUTPUT_RELATIVE_ROOT).rglob("*") if path.is_file()
    }
    expected = {root / entry["embedding_path"] for entry in manifest["samples"]}
    if observed != expected:
        raise ValueError("Arquivo de embedding ausente ou inesperado.")
    for entry in manifest["samples"]:
        path = root / entry["embedding_path"]
        roi_path = root / ROI_RELATIVE_ROOT / f"{entry['sample_id']}.npz"
        if (
            sha256_file(path) != entry["embedding_sha256"]
            or sha256_file(roi_path) != entry["source_roi_sha256"]
        ):
            raise ValueError("Hash de amostra ROI ou embedding divergente.")
        with np.load(path, allow_pickle=False) as data:
            record = {name: np.asarray(data[name]).copy() for name in data.files}
        for key in (
            "sample_id",
            "label",
            "session_id",
            "label_index",
            "format_version",
        ):
            record[key] = record[key].item()
        validate_embedding_sample(record)
        if (
            list(record["frame_embeddings"].shape) != manifest["frame_embedding_shape"]
            or list(record["clip_embedding"].shape) != manifest["clip_embedding_shape"]
            or record["source_roi_sample_hash"].item() != entry["source_roi_sha256"]
            or record["checkpoint_sha256"].item() != manifest["checkpoint_sha256"]
        ):
            raise ValueError("Contrato ou proveniência de embedding divergente.")
    return manifest
