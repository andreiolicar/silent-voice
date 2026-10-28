"""Perfil visual local TWO-SHOT, sem alterar os artefatos GLOBAL/R4."""

from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import time

import numpy as np
import torch

from silent_voice.edge.landmark_gap_runtime import (
    REASON,
    decode_query,
    prepare_decoded_query,
)
from silent_voice.edge.preheldout_freeze import validate_edge_embedding
from silent_voice.inference import live_visual_tester as legacy
from silent_voice.vision.visual_personalization_candidates import (
    EnrollmentFeature,
    HEAD_RECIPE,
    fit_lightweight_personal_head,
    predict_personal_head,
)
from silent_voice.vision.visual_personalization_feature_build import (
    validate_feature_arrays,
)
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS


LABELS = tuple(DEFAULT_VISUAL_LABELS)
CANDIDATE_ID = "LIGHTWEIGHT_PERSONAL_HEAD__2SHOT"
PROFILE_VERSION = 1


def _json_bytes(payload: dict) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _source_identity(sources: dict) -> str:
    if not isinstance(sources, dict) or not sources.get("freeze_sha256"):
        raise ValueError("Proveniência R4 ausente.")
    payload = {
        "r4_freeze_sha256": sources["freeze_sha256"],
        "artifact_sha256": sources.get("artifact_sha256"),
        "temporal_policy_v2_sha256": legacy.temporal.POLICY_V2_FILE_SHA256,
        "candidate_id": CANDIDATE_ID,
        "class_order": LABELS,
        "recipe": HEAD_RECIPE,
    }
    return sha256(_json_bytes(payload)).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    pending = path.with_name(path.name + ".pending")
    with pending.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, path)


class LocalProfileStore:
    """Um perfil pseudônimo, isolado na área local ignorada pelo Git."""

    def __init__(self, root: Path, profile_id: str = "local_default") -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", profile_id):
            raise ValueError("Identidade local do perfil inválida.")
        self.root = Path(root).resolve()
        self.profile_id = profile_id
        self.base = self.root / legacy.DIAGNOSTIC_ROOT / "profiles"
        self.folder = self.base / profile_id
        if self.folder.resolve() != self.folder:
            raise ValueError("Pasta local do perfil redirecionada.")

    def _path(self, name: str) -> Path:
        if self.base.resolve() != self.base:
            raise ValueError("Pasta local de perfis redirecionada.")
        if self.folder.resolve() != self.folder:
            raise ValueError("Pasta local do perfil redirecionada.")
        target = self.folder / name
        if not target.resolve().is_relative_to(self.base):
            raise ValueError("Arquivo de perfil fora da área local.")
        return target

    @property
    def head_path(self) -> Path:
        return self._path("head.npz")

    @property
    def manifest_path(self) -> Path:
        return self._path("manifest.json")

    def example_path(self, label: str, repetition: int) -> Path:
        if label not in LABELS:
            raise ValueError("Palavra de enrollment inválida.")
        if type(repetition) is not int or repetition not in (1, 2):
            raise ValueError("Exemplo TWO-SHOT inválido.")
        return self._path(f"example_{LABELS.index(label)}_{repetition}.npz")

    def progress(self) -> dict[str, int]:
        return {
            label: sum(self.example_path(label, rep).is_file() for rep in (1, 2))
            for label in LABELS
        }

    def total(self) -> int:
        return sum(self.progress().values())

    def save_example(
        self,
        label: str,
        repetition: int,
        clip: np.ndarray,
        temporal: np.ndarray,
        sources: dict,
    ) -> None:
        target = self.example_path(label, repetition)
        if not isinstance(clip, np.ndarray) or clip.shape != (1664,):
            raise ValueError("clip_embedding é uma feature inválida.")
        validate_feature_arrays(clip[None, :], temporal)
        source_id = _source_identity(sources)
        self.folder.mkdir(parents=True, exist_ok=True)
        stream = BytesIO()
        np.savez_compressed(
            stream,
            clip_embedding=clip,
            temporal_features=temporal,
            source_identity=np.asarray(source_id),
        )
        _atomic_write(target, stream.getvalue())
        for artifact in (self.manifest_path, self.head_path):
            artifact.unlink(missing_ok=True)

    def _read_example(
        self, label: str, repetition: int, source_id: str
    ) -> EnrollmentFeature:
        path = self.example_path(label, repetition)
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != {
                "clip_embedding",
                "temporal_features",
                "source_identity",
            }:
                raise ValueError("Arquivo de exemplo incompatível.")
            clip = archive["clip_embedding"].copy()
            temporal = archive["temporal_features"].copy()
            identity = str(archive["source_identity"].item())
        if identity != source_id:
            raise ValueError("Exemplo incompatível com a proveniência R4 atual.")
        validate_feature_arrays(clip[None, :], temporal)
        return EnrollmentFeature(
            sample_id=f"{self.profile_id}_{LABELS.index(label)}_{repetition}",
            label=label,
            label_index=LABELS.index(label),
            clip_embedding=clip,
            temporal_features=temporal,
        )

    def build(self, sources: dict) -> torch.nn.Linear:
        if self.total() != 12:
            raise ValueError("O perfil exige exatamente 12 exemplos válidos.")
        source_id = _source_identity(sources)
        features = tuple(
            self._read_example(label, repetition, source_id)
            for label in LABELS
            for repetition in (1, 2)
        )
        model, recipe = fit_lightweight_personal_head(features)
        weight = model.weight.detach().cpu().numpy().astype(np.float32)
        bias = model.bias.detach().cpu().numpy().astype(np.float32)
        if (
            weight.shape != (6, 1664)
            or bias.shape != (6,)
            or not np.isfinite(weight).all()
            or not np.isfinite(bias).all()
            or recipe != HEAD_RECIPE
        ):
            raise ValueError("Head TWO-SHOT incompatível com o recipe histórico.")
        stream = BytesIO()
        np.savez_compressed(stream, head_weight=weight, head_bias=bias)
        head_bytes = stream.getvalue()
        examples = {
            self.example_path(label, rep)
            .name: sha256(self.example_path(label, rep).read_bytes())
            .hexdigest()
            for label in LABELS
            for rep in (1, 2)
        }
        self.folder.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.head_path, head_bytes)
        manifest = {
            "format_version": PROFILE_VERSION,
            "profile_id": self.profile_id,
            "candidate_id": CANDIDATE_ID,
            "class_order": list(LABELS),
            "example_count": 12,
            "examples_sha256": examples,
            "head_sha256": sha256(head_bytes).hexdigest(),
            "source_identity": source_id,
            "recipe": recipe,
            "rejection": {
                "candidate_id": legacy.CANDIDATE_ID,
                "threshold": legacy.THRESHOLD,
                "k": legacy.K,
                "operator": ">=",
            },
        }
        _atomic_write(self.manifest_path, _json_bytes(manifest))
        return model

    def load(self, sources: dict) -> torch.nn.Linear | None:
        manifest_path, head_path = self.manifest_path, self.head_path
        if not manifest_path.exists() and not head_path.exists():
            return None
        if not manifest_path.is_file() or not head_path.is_file():
            raise ValueError("Perfil incompleto ou incompatível.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("format_version") != PROFILE_VERSION
            or manifest.get("profile_id") != self.profile_id
            or manifest.get("candidate_id") != CANDIDATE_ID
            or manifest.get("class_order") != list(LABELS)
            or manifest.get("example_count") != 12
            or manifest.get("source_identity") != _source_identity(sources)
            or manifest.get("recipe") != HEAD_RECIPE
            or manifest.get("rejection")
            != {
                "candidate_id": legacy.CANDIDATE_ID,
                "threshold": legacy.THRESHOLD,
                "k": legacy.K,
                "operator": ">=",
            }
        ):
            raise ValueError("Perfil incompatível com o runtime congelado.")
        expected_examples = {
            self.example_path(label, rep).name for label in LABELS for rep in (1, 2)
        }
        recorded = manifest.get("examples_sha256")
        if not isinstance(recorded, dict) or set(recorded) != expected_examples:
            raise ValueError("Inventário do perfil incompatível.")
        for name, digest in recorded.items():
            path = self._path(name)
            if not path.is_file() or sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("SHA dos exemplos do perfil divergente.")
        head_bytes = head_path.read_bytes()
        if sha256(head_bytes).hexdigest() != manifest.get("head_sha256"):
            raise ValueError("SHA do head pessoal divergente.")
        with np.load(BytesIO(head_bytes), allow_pickle=False) as archive:
            if set(archive.files) != {"head_weight", "head_bias"}:
                raise ValueError("Componentes do head pessoal incompletos.")
            weight = archive["head_weight"].copy()
            bias = archive["head_bias"].copy()
        if (
            weight.shape != (6, 1664)
            or weight.dtype != np.float32
            or bias.shape != (6,)
            or bias.dtype != np.float32
            or not np.isfinite(weight).all()
            or not np.isfinite(bias).all()
        ):
            raise ValueError("Parâmetros do head pessoal inválidos.")
        model = torch.nn.Linear(1664, 6).to("cpu")
        with torch.no_grad():
            model.weight.copy_(torch.from_numpy(weight))
            model.bias.copy_(torch.from_numpy(bias))
        model.eval()
        return model

    def delete(self) -> None:
        artifacts = {
            self.example_path(label, rep).name for label in LABELS for rep in (1, 2)
        } | {"head.npz", "manifest.json"}
        known = artifacts | {f"{name}.pending" for name in artifacts}
        if not self.folder.exists():
            return
        present = {entry.name for entry in self.folder.iterdir()}
        if present - known:
            raise ValueError(
                "Perfil contém arquivos não reconhecidos; exclusão bloqueada."
            )
        for name in known:
            self._path(name).unlink(missing_ok=True)
        self.folder.rmdir()


def extract_enrollment_feature(path: Path, encoder, sample_id: str):
    """Mesmo preparo com landmark gap usado pelo runtime PERS congelado."""
    row = {
        "sample_id": sample_id,
        "session_id": "LIVE_PERSONAL_ENROLLMENT",
        "sample_kind": "UNKNOWN",
        "expected_label": "UNKNOWN",
    }
    prepared = prepare_decoded_query(
        row,
        decode_query(path),
        diagnostic_sink=lambda diagnostics: None,
        runtime_commit="C4.P_LIVE_TESTER",
        models_loaded_process=True,
    )
    if prepared.query is None:
        raise ValueError("Evidência visual insuficiente para este exemplo.")
    encoded = encoder.run(None, {"roi_input": prepared.tensor})
    if len(encoded) != 1 or np.asarray(encoded[0]).shape != (1, 1664):
        raise ValueError("Saída SwinLip incompatível com TWO-SHOT.")
    clip = validate_edge_embedding(np.asarray(encoded[0])[0])
    temporal = prepared.query.features.copy()
    validate_feature_arrays(clip[None, :], temporal)
    return clip, temporal


def record_enrollment(
    root: Path,
    camera,
    encoder,
    store: LocalProfileStore,
    sources: dict,
    label: str,
    repetition: int,
    session_id: str,
    number: int,
    *,
    show_frame=None,
    read_key=None,
) -> dict:
    """Só uma ação explícita produz um exemplo; MP4 é sempre temporário."""
    store.example_path(label, repetition)
    path = legacy.clip_path(root, session_id, number, keep=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        timing = legacy.record_clip(
            camera, path, show_frame=show_frame, read_key=read_key
        )
        if timing["technical_decision"] != "PASS":
            raise legacy.TemporalCaptureError("Gate temporal do exemplo reprovado.")
        clip, temporal = extract_enrollment_feature(
            path, encoder, f"{store.profile_id}_{LABELS.index(label)}_{repetition}"
        )
        store.save_example(label, repetition, clip, temporal, sources)
        return timing
    finally:
        legacy.cleanup_temporary_clip(root, path)


class PersonalizedPipeline:
    """Head histórico TWO-SHOT + encoder e scorer globais congelados."""

    def __init__(self, global_pipeline, head: torch.nn.Linear) -> None:
        if head.in_features != 1664 or head.out_features != 6:
            raise ValueError("Head pessoal incompatível.")
        self.base = global_pipeline
        self.head = head

    def infer_clip(self, video: Path, sample_id: str, session_id: str) -> dict:
        started = time.perf_counter()
        row = {
            "sample_id": sample_id,
            "session_id": session_id,
            "sample_kind": "UNKNOWN",
            "expected_label": "UNKNOWN",
        }
        prepared = prepare_decoded_query(
            row,
            decode_query(Path(video)),
            diagnostic_sink=lambda diagnostics: None,
            runtime_commit="C4.P_LIVE_TESTER",
            models_loaded_process=True,
        )
        diagnostics = prepared.diagnostics
        common = {
            "sample_id": sample_id,
            "threshold": legacy.THRESHOLD,
            "segmentation_status": (
                "FALLBACK" if diagnostics.get("segmentation_fallback") else "DETECTED"
            ),
            "segmentation_fallback": bool(diagnostics.get("segmentation_fallback")),
            "source_frame_count": diagnostics.get("source_frame_count"),
            "runtime": "SwinLip ONNX / personal Linear CPU / R4 ONNX",
        }
        if prepared.query is None:
            return {
                **common,
                "predicted_label": None,
                "second_best_label": None,
                "score": None,
                "decision": "REJECT",
                "emitted_label": None,
                "technical_reason": REASON,
                "end_to_end_latency_ms": (time.perf_counter() - started) * 1000,
            }
        encoded = self.base.encoder.run(None, {"roi_input": prepared.tensor})
        if len(encoded) != 1 or np.asarray(encoded[0]).shape != (1, 1664):
            raise ValueError("Saída SwinLip inválida.")
        clip = validate_edge_embedding(np.asarray(encoded[0])[0])
        index, logits = predict_personal_head(self.head, clip)
        if type(index) is not int or index not in range(6):
            raise ValueError("Classe do head pessoal inválida.")
        output = self.base.scorer.run(
            None,
            {
                "clip_embedding": clip[None, :],
                "predicted_label_index": np.asarray([index], dtype=np.int64),
            },
        )
        if len(output) != 1 or np.asarray(output[0]).shape != (1,):
            raise ValueError("Saída do scorer R4 inválida.")
        score = float(output[0][0])
        decision = legacy.r4.decision_for_score(score)
        label = LABELS[index]
        second = LABELS[int(np.argsort(-np.asarray(logits))[1])]
        return {
            **common,
            "predicted_label": label,
            "second_best_label": second,
            "score": score,
            "decision": decision,
            "emitted_label": label if decision == "ACCEPT" else None,
            "end_to_end_latency_ms": (time.perf_counter() - started) * 1000,
        }
