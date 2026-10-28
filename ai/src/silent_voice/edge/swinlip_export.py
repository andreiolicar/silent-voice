"""Wrapper mínimo do clip embedding oficial e guardas de proveniência."""

from collections import Counter
from pathlib import Path

import torch
from torch import nn

from silent_voice.vision.mouth_roi_dataset import sha256_file

FROZEN_PATHS = {
    "encoder": "data/external/swinlip/checkpoints/lrw_swinlip.pth",
    "classifier": "data/processed/models/cycle_06_hybrid_positive_classifier.pt",
    "positive_config": (
        "data/processed/evaluation/cycle_06_positive_classifier_final_config.json"
    ),
    "centroids": "data/processed/models/cycle_06_rejection_2_clip_centroids.npz",
    "rejection_config": (
        "data/processed/evaluation/cycle_06_rejection_2_final_config.json"
    ),
    "embedding_manifest": (
        "data/processed/evaluation/cycle_06_swinlip_embedding_manifest.json"
    ),
}
FROZEN_HASHES = {
    "encoder": "32f77c3ac7ff6cc4e970bf8dd53b1dade84d1905dd7b30d95ca105380b6cd6f5",
    "classifier": "33a0d1f1f564dc75f83ebc08fc2dca255840da60ca40a9c41fdd36d4ad0cc6a2",
    "positive_config": (
        "29b7df189ac8f3b5b01ce2b5b5b03870dd37b678ccb6f6f536e8ac9debaa7a1e"
    ),
    "centroids": "3fd4b54a7f092ce9b09f064b8076c76e71b1833e3eab3786b4295f07e023a87e",
    "rejection_config": (
        "c13b81c22a3c04972a15ce4ca3382eb9c30ef6156e32af1a7acb4fd4a524dff1"
    ),
    "embedding_manifest": (
        "13a45412538e9a67756884dbafcdb3d22bbfd0126892dcf2e0f4e8f52db49b17"
    ),
}
ROI_ROOTS = {
    "KNOWN": Path("data/processed/visual_mouth_roi"),
    "UNKNOWN": Path("data/processed/rejection_visual_mouth_roi"),
}
ALLOWED_SESSIONS = {
    "KNOWN": ("sessao_01", "sessao_02", "sessao_03"),
    "UNKNOWN": ("rejeicao_dev_01", "rejeicao_dev_02", "rejeicao_dev_03"),
}


def validate_frozen_hashes(
    root: Path, paths: dict = FROZEN_PATHS, expected: dict = FROZEN_HASHES
) -> dict:
    """Confere todas as fontes fixadas antes de export, paridade ou benchmark."""
    if set(paths) != set(expected) or len(paths) != 6:
        raise ValueError("Inventário congelado de seis arquivos incompleto.")
    observed = {}
    for name, relative in paths.items():
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Path de proveniência inválido: {name}")
        observed[name] = sha256_file(Path(root) / candidate)
        if observed[name] != expected[name]:
            raise ValueError(f"SHA-256 congelado divergiu: {name}")
    return observed


def authorized_roi_path(root: Path, record: dict, kind: str) -> Path:
    """Recusa held-out e path adulterado por metadados, antes de abrir NPZ."""
    if kind not in ROI_ROOTS:
        raise ValueError("Tipo de amostra inválido.")
    session = record.get("session_id")
    sample_id = record.get("sample_id")
    if (
        session not in ALLOWED_SESSIONS[kind]
        or not isinstance(sample_id, str)
        or session not in sample_id
        or not sample_id
        or any(char in sample_id for char in ("/", "\\", "."))
    ):
        raise ValueError("Amostra fora do development permitido.")
    relative = ROI_ROOTS[kind] / f"{sample_id}.npz"
    if Path(record.get("derived_roi_path", "")) != relative:
        raise ValueError("Caminho ROI divergiu do sample_id permitido.")
    return Path(root) / relative


def select_golden_records(
    root: Path, positive_records: list[dict], negative_records: list[dict]
) -> tuple[dict, ...]:
    """Valida os 108 paths e IDs antes de abrir qualquer ROI ou embedding."""
    if len(positive_records) != 54 or len(negative_records) != 54:
        raise ValueError("Corpus Edge exige 54 KNOWN e 54 UNKNOWN.")
    selected = []
    for kind, records in (("KNOWN", positive_records), ("UNKNOWN", negative_records)):
        counts = Counter(row.get("session_id") for row in records)
        if counts != Counter({session: 18 for session in ALLOWED_SESSIONS[kind]}):
            raise ValueError("Sessões do corpus Edge divergentes.")
        for record in records:
            selected.append(
                {
                    "kind": kind,
                    "sample_id": record["sample_id"],
                    "session_id": record["session_id"],
                    "roi_path": authorized_roi_path(root, record, kind),
                    "roi_record": record,
                }
            )
    if len({row["sample_id"] for row in selected}) != 108:
        raise ValueError("sample_id duplicado no corpus Edge.")
    return tuple(selected)


class SwinLipClipEncoder(nn.Module):
    """Expõe somente o clip após frontend, Swin/Conformer e DenseTCN."""

    def __init__(self, official_model: nn.Module):
        super().__init__()
        self.model = official_model
        if official_model.training or any(
            parameter.requires_grad for parameter in official_model.parameters()
        ):
            raise ValueError("SwinLip precisa estar em eval e congelado.")
        self.eval()

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        if (
            tensor.ndim != 5
            or tensor.shape[1:] != (1, 29, 88, 88)
            or tensor.dtype != torch.float32
            or tensor.device.type != "cpu"
            or not bool(torch.isfinite(tensor).all())
        ):
            raise ValueError("Entrada deve ser CPU float32 (N,1,29,88,88) finita.")
        frontend = self.model.frontend3D(tensor)
        batch, channels, frames, height, width = frontend.shape
        flat = frontend.transpose(1, 2).reshape(batch * frames, channels, height, width)
        frame_tensor = self.model.trunk(flat, batch, frames)
        temporal = self.model.tcn.tcn_trunk(frame_tensor.transpose(1, 2))
        clip = self.model.tcn.consensus_func(temporal, [frames] * batch, batch)
        if (
            clip.shape != (batch, 1664)
            or clip.dtype != torch.float32
            or not bool(torch.isfinite(clip).all())
        ):
            raise ValueError("Clip embedding precisa ser finito (N,1664).")
        return clip


def export_fp32_encoder(wrapper: SwinLipClipEncoder, output: Path) -> dict:
    """Exporta batch 1 fixo, opset 18, sem converter pesos ou matemática."""
    path = Path(output)
    if path.exists():
        raise FileExistsError(f"Export FP32 já existe: {path}")
    if wrapper.training:
        raise ValueError("Wrapper precisa estar em eval para export.")
    path.parent.mkdir(parents=True, exist_ok=True)
    example = torch.zeros((1, 1, 29, 88, 88), dtype=torch.float32)
    torch.onnx.export(
        wrapper,
        (example,),
        str(path),
        input_names=["roi_input"],
        output_names=["clip_embedding"],
        opset_version=18,
        dynamo=False,
        dynamic_axes=None,
        do_constant_folding=True,
    )
    return {"exporter": "torch.onnx.export(dynamo=False)", "opset": 18}


def export_positive_head(head: nn.Linear, output: Path) -> dict:
    """Exporta a cabeça congelada Linear(1670,6) separadamente."""
    path = Path(output)
    if path.exists():
        raise FileExistsError(f"Export da cabeça já existe: {path}")
    if head.training or head.in_features != 1670 or head.out_features != 6:
        raise ValueError("Cabeça deve ser Linear(1670,6) em eval.")
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        head,
        (torch.zeros((1, 1670), dtype=torch.float32),),
        str(path),
        input_names=["hybrid_features"],
        output_names=["logits"],
        opset_version=18,
        dynamo=False,
        dynamic_axes=None,
    )
    return {"exporter": "torch.onnx.export(dynamo=False)", "opset": 18}
