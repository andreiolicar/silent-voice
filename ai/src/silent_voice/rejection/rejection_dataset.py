"""Plano e validação estrutural das amostras negativas de desenvolvimento."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from silent_voice.rejection.rejection_protocol import (
    DEVELOPMENT_OOV_PROMPTS,
    NEGATIVE_CATEGORIES,
    NEGATIVE_DEVELOPMENT_SESSIONS,
)
from silent_voice.vision.dataset_collection_plan import normalize_label_for_sample_id
from silent_voice.vision.feature_sample import VisualFeatureSample
from silent_voice.vision.temporal_features import VISUAL_FEATURE_COUNT


INSTRUCTIONS = {
    "BOCA_PARADA": (
        "Mantenha o rosto visível e a boca relaxada, sem falar, "
        "durante toda a gravação."
    ),
    "SORRISO": (
        "Comece neutro, sorria naturalmente uma vez e volte ao repouso. "
        "Não articule nenhuma palavra."
    ),
    "ABRE_FECHA": (
        "Comece neutro, abra e feche a boca duas vezes de forma natural "
        "e volte ao repouso. Não forme palavra."
    ),
    "MOV_CABECA": (
        "Mantenha a boca em repouso. Com o rosto visível, faça um pequeno "
        "movimento natural da cabeça para um lado, para o outro e volte ao centro."
    ),
    "MOV_BOCA_ALEATORIO": (
        "Faça movimentos variados naturais com os lábios/boca sem formar "
        "nenhuma palavra conhecida ou palavra real intencionalmente."
    ),
}

TECHNICAL_REASONS = (
    "procedimento_incorreto",
    "palavra_incorreta",
    "falha_camera",
    "fora_do_quadro",
    "arquivo_corrompido",
    "captura_interrompida",
    "instrucao_nao_seguida",
)


@dataclass(frozen=True, slots=True)
class NegativeCapturePlanItem:
    sample_id: str
    session_id: str
    negative_category: str
    repetition_index: int
    oov_prompt: str
    instruction: str

    @property
    def label(self) -> str:
        return self.negative_category

    @property
    def repetition(self) -> int:
        return self.repetition_index


@dataclass(frozen=True, slots=True)
class NegativeSampleRecord:
    sample_id: str
    session_id: str
    negative_category: str
    repetition_index: int
    oov_prompt: str
    frame_count: int
    path: Path


@dataclass(frozen=True, slots=True)
class NegativeSessionReport:
    session_id: str
    sample_count: int
    complete: bool
    missing_sample_ids: tuple[str, ...]
    counts_by_category: dict[str, int]
    samples: tuple[NegativeSampleRecord, ...]


@dataclass(frozen=True, slots=True)
class NegativeGlobalReport:
    sample_count: int
    counts_by_category: dict[str, int]
    sessions: tuple[NegativeSessionReport, ...]
    samples: tuple[NegativeSampleRecord, ...]


def build_rejection_session_plan(
    session_id: str,
) -> tuple[NegativeCapturePlanItem, ...]:
    if session_id not in NEGATIVE_DEVELOPMENT_SESSIONS:
        raise ValueError(f"Sessão negativa de desenvolvimento inválida: {session_id}")
    prompts = dict(DEVELOPMENT_OOV_PROMPTS)[session_id]
    plan = []
    for category in NEGATIVE_CATEGORIES:
        for repetition in range(1, 4):
            prompt = prompts[repetition - 1] if category == "FALA_FORA_VOCAB" else ""
            instruction = (
                f"Articule naturalmente uma vez a palavra: {prompt}"
                if prompt
                else INSTRUCTIONS[category]
            )
            plan.append(
                NegativeCapturePlanItem(
                    sample_id=(
                        f"{normalize_label_for_sample_id(category)}_"
                        f"{session_id}_{repetition:03d}"
                    ),
                    session_id=session_id,
                    negative_category=category,
                    repetition_index=repetition,
                    oov_prompt=prompt,
                    instruction=instruction,
                )
            )
    return tuple(plan)


def negative_sample_path(root: Path, item: NegativeCapturePlanItem) -> Path:
    return (
        Path(root) / item.session_id / item.negative_category / f"{item.sample_id}.npz"
    )


def capture_metadata(
    camera_index: int,
    output_fps: float = 30.0,
    recording_duration_seconds: float = 4.0,
) -> dict:
    return {
        "camera_source": "Iriun",
        "camera_index": camera_index,
        "output_fps": output_fps,
        "recording_duration_seconds": recording_duration_seconds,
        "processing_pipeline": "existing_visual_feature_extractor",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _check_metadata(metadata: dict) -> None:
    required = {
        "camera_source",
        "camera_index",
        "output_fps",
        "recording_duration_seconds",
        "processing_pipeline",
        "captured_at_utc",
    }
    if not isinstance(metadata, dict) or required - metadata.keys():
        raise ValueError("capture_metadata incompleto.")
    if (
        metadata["camera_source"] != "Iriun"
        or not isinstance(metadata["camera_index"], int)
        or metadata["camera_index"] < 0
        or metadata["output_fps"] != 30.0
        or metadata["recording_duration_seconds"] != 4.0
        or metadata["processing_pipeline"] != "existing_visual_feature_extractor"
    ):
        raise ValueError("capture_metadata incompatível com o protocolo.")
    try:
        parsed = datetime.fromisoformat(metadata["captured_at_utc"])
    except (TypeError, ValueError) as error:
        raise ValueError("capture_metadata sem data válida.") from error
    if parsed.tzinfo is None:
        raise ValueError("capture_metadata sem fuso horário.")


def _check_sample(sample: VisualFeatureSample, item: NegativeCapturePlanItem) -> None:
    if sample.sample_id != item.sample_id or sample.session_id != item.session_id:
        raise ValueError("sample_id ou session_id divergente do plano.")
    if sample.label != "UNKNOWN":
        raise ValueError("label negativo deve ser UNKNOWN.")
    if sample.features.ndim != 2 or sample.features.shape[1] != VISUAL_FEATURE_COUNT:
        raise ValueError("features incompatíveis com 160 dimensões.")
    if not np.isfinite(sample.features).all():
        raise ValueError("features devem ser finitas.")
    timestamps = sample.timestamps_ms
    if (
        timestamps.ndim != 1
        or len(timestamps) != sample.frame_count
        or not np.isfinite(timestamps).all()
        or np.any(timestamps < 0)
        or np.any(np.diff(timestamps) <= 0)
    ):
        raise ValueError("timestamps inválidos.")


def save_rejection_feature_sample(
    sample: VisualFeatureSample,
    item: NegativeCapturePlanItem,
    path: Path,
    metadata: dict,
) -> None:
    _check_sample(sample, item)
    _check_metadata(metadata)
    path = Path(path)
    if path != negative_sample_path(path.parents[2], item):
        raise ValueError("Caminho NPZ divergente do plano de captura.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        np.savez_compressed(
            stream,
            sample_id=item.sample_id,
            session_id=item.session_id,
            label="UNKNOWN",
            sample_kind="UNKNOWN",
            negative_category=item.negative_category,
            repetition_index=item.repetition_index,
            oov_prompt=item.oov_prompt,
            features=sample.features,
            timestamps_ms=sample.timestamps_ms,
            capture_metadata=json.dumps(metadata, ensure_ascii=False),
        )


def _scalar(data, name: str):
    try:
        return data[name].item()
    except (KeyError, ValueError) as error:
        raise ValueError(f"Campo inválido ou ausente: {name}") from error


def validate_rejection_sample(
    path: Path, item: NegativeCapturePlanItem
) -> NegativeSampleRecord:
    path = Path(path)
    with np.load(path, allow_pickle=False) as data:
        expected = {
            "sample_id": item.sample_id,
            "session_id": item.session_id,
            "label": "UNKNOWN",
            "sample_kind": "UNKNOWN",
            "negative_category": item.negative_category,
            "repetition_index": item.repetition_index,
            "oov_prompt": item.oov_prompt,
        }
        for key, value in expected.items():
            if _scalar(data, key) != value:
                raise ValueError(f"{key} diverge do plano congelado.")
        try:
            metadata = json.loads(_scalar(data, "capture_metadata"))
            features = data["features"]
            timestamps = data["timestamps_ms"]
        except (KeyError, json.JSONDecodeError) as error:
            raise ValueError("NPZ negativo incompleto.") from error
        _check_metadata(metadata)
        if features.ndim != 2 or features.shape[1] != VISUAL_FEATURE_COUNT:
            raise ValueError("features incompatíveis com 160 dimensões.")
        if len(features) == 0 or not np.isfinite(features).all():
            raise ValueError("features devem ser finitas e não vazias.")
        if (
            timestamps.ndim != 1
            or len(timestamps) != len(features)
            or not np.isfinite(timestamps).all()
            or np.any(timestamps < 0)
            or np.any(np.diff(timestamps) <= 0)
        ):
            raise ValueError("timestamps inválidos.")
        frame_count = len(features)
    return NegativeSampleRecord(
        item.sample_id,
        item.session_id,
        item.negative_category,
        item.repetition_index,
        item.oov_prompt,
        frame_count,
        path,
    )


def validate_rejection_session(
    root: Path, session_id: str, require_complete: bool = True
) -> NegativeSessionReport:
    root = Path(root)
    plan = build_rejection_session_plan(session_id)
    session_root = root / session_id
    if session_root.is_dir():
        unexpected_categories = {
            path.name for path in session_root.iterdir() if path.is_dir()
        } - set(NEGATIVE_CATEGORIES)
        if unexpected_categories:
            raise ValueError(
                f"Categorias inesperadas em {session_id}: "
                f"{sorted(unexpected_categories)}"
            )
    expected = {negative_sample_path(root, item): item for item in plan}
    observed = set(session_root.rglob("*.npz"))
    extra = observed - expected.keys()
    if extra:
        raise ValueError(f"Arquivos NPZ inesperados na sessão: {sorted(extra)}")
    missing = tuple(
        item.sample_id for path, item in expected.items() if path not in observed
    )
    if missing and require_complete:
        raise ValueError(f"Amostras ausentes em {session_id}: {missing}")
    samples = tuple(
        validate_rejection_sample(path, item)
        for path, item in expected.items()
        if path in observed
    )
    counts = Counter(sample.negative_category for sample in samples)
    return NegativeSessionReport(
        session_id,
        len(samples),
        not missing,
        missing,
        {category: counts[category] for category in NEGATIVE_CATEGORIES},
        samples,
    )


def validate_all_rejection_sessions(root: Path) -> NegativeGlobalReport:
    root = Path(root)
    if root.is_dir():
        unexpected_sessions = {
            path.name for path in root.iterdir() if path.is_dir()
        } - set(NEGATIVE_DEVELOPMENT_SESSIONS)
        if unexpected_sessions:
            raise ValueError(f"Sessões inesperadas: {sorted(unexpected_sessions)}")
    plans = tuple(
        item
        for session in NEGATIVE_DEVELOPMENT_SESSIONS
        for item in build_rejection_session_plan(session)
    )
    expected = {negative_sample_path(root, item) for item in plans}
    extra = set(root.rglob("*.npz")) - expected
    if extra:
        raise ValueError(f"Amostras inesperadas no dataset negativo: {sorted(extra)}")
    reports = tuple(
        validate_rejection_session(root, session)
        for session in NEGATIVE_DEVELOPMENT_SESSIONS
    )
    samples = tuple(sample for report in reports for sample in report.samples)
    counts = Counter(sample.negative_category for sample in samples)
    if (
        len(samples) != 54
        or len({sample.sample_id for sample in samples}) != 54
        or any(counts[category] != 9 for category in NEGATIVE_CATEGORIES)
    ):
        raise ValueError("O dataset negativo deve conter 54 amostras únicas.")
    return NegativeGlobalReport(
        len(samples),
        {category: counts[category] for category in NEGATIVE_CATEGORIES},
        reports,
        samples,
    )
