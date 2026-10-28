"""Adapter isolado do SwinLip oficial para embeddings congelados em CPU."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable

import numpy as np
import torch
from torch import nn

from silent_voice.vision.visual_experiment_defaults import SESSION_IDS
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

SOURCE_REPOSITORY = "https://github.com/park-ing/SwinLip.git"
SOURCE_COMMIT = "0be70b224e42619f72ad283e85303f5e10544004"
CHECKPOINT_SHA256 = "32f77c3ac7ff6cc4e970bf8dd53b1dade84d1905dd7b30d95ca105380b6cd6f5"
CHECKPOINT_SIZE_BYTES = 256873713
SWINLIP_TARGET_FRAME_COUNT = 29
SPATIAL_CROP_SIZE = 88
SPATIAL_MEAN = 0.421
SPATIAL_STD = 0.165
EMBEDDING_FORMAT_VERSION = 1


def _git_identity(source: Path) -> tuple[str, str]:
    dirty = subprocess.check_output(
        ["git", "-C", str(source), "status", "--porcelain"], text=True
    ).strip()
    if dirty:
        raise ValueError("Checkout oficial SwinLip contém alterações locais.")
    commit = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    remote = subprocess.check_output(
        ["git", "-C", str(source), "remote", "get-url", "origin"], text=True
    ).strip()
    return commit, remote


def validate_external_source(
    source: Path, identity_reader: Callable[[Path], tuple[str, str]] = _git_identity
) -> str:
    """Aceita somente o checkout e a configuração oficiais no commit fixado."""
    source = Path(source).resolve()
    if (
        not (source / "LICENSE").is_file()
        or not (source / "configs/swinlip.json").is_file()
    ):
        raise FileNotFoundError("LICENSE ou configuração SwinLip oficial ausente.")
    commit, remote = identity_reader(source)
    if commit != SOURCE_COMMIT or remote.rstrip("/").removesuffix(".git") != (
        SOURCE_REPOSITORY.removesuffix(".git")
    ):
        raise ValueError("Fonte SwinLip não corresponde ao repositório/commit oficial.")
    return commit


def validate_checkpoint_file(
    path: Path, expected_sha256: str = CHECKPOINT_SHA256
) -> str:
    """Rejeita pesos de origem diferente mesmo se tiverem as mesmas chaves."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Checkpoint oficial SwinLip Base ausente.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    observed = digest.hexdigest()
    if observed != expected_sha256:
        raise ValueError("SHA-256 do checkpoint SwinLip Base inesperado.")
    return observed


def select_source_frame_indices(
    start_frame: int, end_frame_exclusive: int
) -> np.ndarray:
    """Amostra 29 índices reais uniformes, incluindo início e fim."""
    if start_frame < 0 or end_frame_exclusive <= start_frame:
        raise ValueError("Intervalo temporal inválido.")
    positions = np.linspace(
        start_frame, end_frame_exclusive - 1, SWINLIP_TARGET_FRAME_COUNT
    )
    return np.rint(positions).astype(np.int32)


def prepare_input(rois: np.ndarray, selected_indices: np.ndarray) -> torch.Tensor:
    """Aplica o pipeline LRW determinístico 96→88 e retorna B,C,T,H,W."""
    if rois.ndim != 3 or rois.shape[1:] != (96, 96) or rois.dtype != np.uint8:
        raise ValueError("ROIs devem ser uint8 com shape (T,96,96).")
    indices = np.asarray(selected_indices)
    if (
        indices.shape != (SWINLIP_TARGET_FRAME_COUNT,)
        or not np.issubdtype(indices.dtype, np.integer)
        or np.any(indices < 0)
        or np.any(indices >= len(rois))
        or np.any(np.diff(indices) < 0)
    ):
        raise ValueError("Os 29 índices reais selecionados são inválidos.")
    selected = rois[indices, 4:92, 4:92].astype(np.float32)
    normalized = (selected / 255.0 - SPATIAL_MEAN) / SPATIAL_STD
    tensor = torch.from_numpy(normalized.copy()).unsqueeze(0).unsqueeze(0)
    if tensor.shape != (1, 1, 29, 88, 88) or not torch.isfinite(tensor).all():
        raise ValueError("Tensor de entrada inválido.")
    return tensor


def freeze_model(model: nn.Module) -> nn.Module:
    model.eval()
    model.requires_grad_(False)
    if model.training or any(p.requires_grad for p in model.parameters()):
        raise ValueError("O encoder não está integralmente congelado.")
    return model


def _load_official_package(source: Path) -> ModuleType:
    package_path = source / "models/__init__.py"
    spec = importlib.util.spec_from_file_location(
        "silent_voice_official_swinlip",
        package_path,
        submodule_search_locations=[str(package_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError("Não foi possível importar o SwinLip oficial.")
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    return package


def load_official_model(source: Path, checkpoint_path: Path) -> tuple[nn.Module, dict]:
    """Carrega o Base LRW estritamente, sem conversão nem fine-tuning."""
    validate_external_source(source)
    config = json.loads((source / "configs/swinlip.json").read_text("utf-8"))
    if (
        config.get("model_name") != "SwinLip"
        or config.get("use_boundary") is not False
        or config.get("num_classes") != 500
    ):
        raise ValueError("Configuração SwinLip Base inesperada.")
    if Path(checkpoint_path).stat().st_size != CHECKPOINT_SIZE_BYTES:
        raise ValueError("Tamanho do checkpoint SwinLip Base inesperado.")
    validate_checkpoint_file(checkpoint_path)
    package = _load_official_package(Path(source))
    model = package.SwinLip(config)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        checkpoint = checkpoint["model_state_dict"]
    if not isinstance(checkpoint, dict) or not checkpoint:
        raise ValueError("state_dict do checkpoint é inválido.")
    model.load_state_dict(checkpoint, strict=True)
    return freeze_model(model.cpu()), config


def extract_embeddings(
    model: nn.Module, input_tensor: torch.Tensor
) -> tuple[np.ndarray, np.ndarray]:
    """Executa os módulos oficiais uma vez, parando antes do classificador LRW."""
    if (
        input_tensor.shape != (1, 1, 29, 88, 88)
        or input_tensor.dtype != torch.float32
        or input_tensor.device.type != "cpu"
        or not torch.isfinite(input_tensor).all()
    ):
        raise ValueError("Entrada SwinLip deve ser CPU float32 (1,1,29,88,88).")
    if model.training or any(p.requires_grad for p in model.parameters()):
        raise ValueError("O modelo precisa estar em eval e integralmente congelado.")
    with torch.no_grad():
        frontend = model.frontend3D(input_tensor)
        batch, channels, frames, height, width = frontend.shape
        flat = frontend.transpose(1, 2).reshape(batch * frames, channels, height, width)
        frame_tensor = model.trunk(flat, batch, frames)
        temporal = model.tcn.tcn_trunk(frame_tensor.transpose(1, 2))
        clip_tensor = model.tcn.consensus_func(temporal, [frames], batch)
    if (
        frame_tensor.ndim != 3
        or frame_tensor.shape[:2] != (1, 29)
        or clip_tensor.ndim != 2
        or clip_tensor.shape[0] != 1
    ):
        raise ValueError("Dimensões dos embeddings oficiais inesperadas.")
    frame_embedding = frame_tensor[0].detach().cpu().numpy().astype(np.float32)
    clip_embedding = clip_tensor[0].detach().cpu().numpy().astype(np.float32)
    if (
        not np.isfinite(frame_embedding).all()
        or not np.isfinite(clip_embedding).all()
        or frame_embedding.shape[1] == 0
        or clip_embedding.size == 0
    ):
        raise ValueError("Embedding ausente ou não finito.")
    return frame_embedding, clip_embedding


def validate_embedding_sample(record: dict) -> None:
    """Valida rótulos como metadados, sem qualquer cálculo de classificação."""
    if record.get("format_version") != EMBEDDING_FORMAT_VERSION:
        raise ValueError("Versão do formato de embedding incompatível.")
    session = record.get("session_id")
    label = record.get("label")
    sample_id = record.get("sample_id")
    if session not in SESSION_IDS or label not in DEFAULT_VISUAL_LABELS:
        raise ValueError("Sessão ou label fora do desenvolvimento permitido.")
    if record.get("label_index") != DEFAULT_VISUAL_LABELS.index(label):
        raise ValueError("Índice do label inconsistente.")
    if not isinstance(sample_id, str) or session not in sample_id:
        raise ValueError("sample_id incompatível com a sessão.")
    indices = record.get("selected_source_frame_indices")
    frame = record.get("frame_embeddings")
    clip = record.get("clip_embedding")
    if (
        not isinstance(indices, np.ndarray)
        or indices.shape != (29,)
        or not np.issubdtype(indices.dtype, np.integer)
        or np.any(np.diff(indices) < 0)
        or not isinstance(frame, np.ndarray)
        or frame.ndim != 2
        or frame.shape[0] != 29
        or frame.dtype != np.float32
        or not np.isfinite(frame).all()
        or not isinstance(clip, np.ndarray)
        or clip.ndim != 1
        or clip.dtype != np.float32
        or not np.isfinite(clip).all()
    ):
        raise ValueError("Contrato de embedding inválido.")


def save_embedding_sample(record: dict, path: Path) -> None:
    validate_embedding_sample(record)
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Embedding já existe: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path, **{key: np.asarray(value) for key, value in record.items()}
    )
