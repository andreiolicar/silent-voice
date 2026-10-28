"""Contratos da calibração Edge pré-held-out do Cycle 6."""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

from silent_voice.rejection.hybrid_rejection_final import (
    POLICY,
    _validate_centroids,
    build_final_clip_centroids,
    calibration_observation,
    score_unknown_clip,
)
from silent_voice.rejection.hybrid_rejection_scores import (
    acceptance_decision,
    calculate_detailed_metrics,
    select_calibrated_threshold,
)
from silent_voice.vision.hybrid_features import (
    HybridSample,
    class_minimum_dtw_distances,
    equal_energy_fusion,
    normalized_reciprocal_evidence,
)
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.positive_classifier_final import (
    CLASSIFIER_ID,
    clip_embedding_sha256,
)
from silent_voice.vision.visual_training_dataset import DEFAULT_VISUAL_LABELS

TASK_69_AUDIT = Path("data/processed/evaluation/cycle_06_edge_feasibility.json")
TASK_69_AUDIT_SHA256 = (
    "ef08f42edf5cc57cee2078b8255bc16a87ebda8eb304d20f77a6ed5582c9f539"
)
STATE = "CYCLE_06_PREHELDOUT_EDGE_FROZEN"
ENCODER_ID = "ONNX_FP16"
ARTIFACT_ROOT = Path("data/processed/models/edge")
FREEZE_MANIFEST = Path(
    "data/processed/evaluation/cycle_06_preheldout_freeze_manifest.json"
)


def _authorized_artifact(root: Path, path: str) -> Path:
    """Resolve apenas artefato Edge registrado dentro do repositório."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(root) / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to((Path(root) / ARTIFACT_ROOT).resolve()):
        raise ValueError("Path de artefato Edge fora da área autorizada.")
    return candidate


def load_task_69_audit(root: Path, expected_sha256: str = TASK_69_AUDIT_SHA256) -> dict:
    """Recupera contratos e hashes exatos do JSON da 6.9 antes do uso real."""
    root = Path(root).resolve()
    path = root / TASK_69_AUDIT
    if sha256_file(path) != expected_sha256:
        raise ValueError("SHA-256 do resultado da Task 6.9 divergiu.")
    audit = json.loads(path.read_text(encoding="utf-8"))
    if (
        audit.get("state") != "EDGE_EXPORT_FEASIBLE"
        or audit.get("heldouts_used") is not False
        or audit.get("leading_technical_candidate") != ENCODER_ID
    ):
        raise ValueError("Task 6.9 não autoriza o candidato ONNX_FP16.")
    matches = [row for row in audit["candidates"] if row.get("id") == ENCODER_ID]
    if len(matches) != 1:
        raise ValueError("É exigido exatamente um candidato ONNX_FP16.")
    selected = matches[0]
    aggregate = selected["aggregate"]
    head = audit["positive_head"]
    if (
        aggregate.get("status") != "DECISION_IDENTICAL"
        or aggregate.get("finite_count") != 108
        or aggregate.get("label_agreement_count") != 108
        or aggregate.get("decision_agreement_count") != 108
        or head.get("equivalent") is not True
        or head.get("argmax_agreement_count") != 108
        or head.get("max_abs_logit_error", float("inf")) > 1e-5
    ):
        raise ValueError("Paridade da 6.9 não autoriza o pipeline Edge.")
    encoder = selected["artifact"]
    classifier = head["artifact"]
    if (
        encoder.get("input_name") != "roi_input"
        or encoder.get("output_name") != "clip_embedding"
        or encoder.get("input_shape") != [1, 1, 29, 88, 88]
        or encoder.get("output_shape") != [1, 1664]
        or encoder.get("opsets") != [{"domain": "", "version": 18}]
        or classifier.get("input_name") != "hybrid_features"
        or classifier.get("output_name") != "logits"
        or classifier.get("input_shape") != [1, 1670]
        or classifier.get("output_shape") != [1, 6]
        or classifier.get("opsets") != [{"domain": "", "version": 18}]
        or selected.get("method", {}).get("tool") != "onnxconverter-common"
        or not selected["method"].get("version")
    ):
        raise ValueError("Contrato ONNX registrado na 6.9 divergiu.")
    encoder_path = _authorized_artifact(root, encoder["path"])
    head_path = _authorized_artifact(root, classifier["path"])
    for name, actual, record in (
        ("encoder", encoder_path, encoder),
        ("classifier", head_path, classifier),
    ):
        if (
            sha256_file(actual) != record["sha256"]
            or actual.stat().st_size != record["size_bytes"]
        ):
            raise ValueError(f"SHA-256 ou tamanho do artefato {name} divergiu.")
    return {
        "audit": audit,
        "audit_sha256": expected_sha256,
        "encoder": encoder,
        "encoder_path": encoder_path,
        "encoder_method": selected["method"],
        "head": classifier,
        "head_path": head_path,
    }


def validate_edge_embedding(clip: np.ndarray) -> np.ndarray:
    """Exige clip FP32 finito de 1664 posições, sem normalizá-lo."""
    value = np.asarray(clip)
    if (
        value.shape != (1664,)
        or value.dtype != np.float32
        or not np.isfinite(value).all()
        or np.linalg.norm(value) <= 1e-12
    ):
        raise ValueError("Embedding Edge deve ser FP32 finito e não nulo de 1664-D.")
    return value.copy()


def build_edge_centroids(positives: tuple[HybridSample, ...]) -> np.ndarray:
    """Reusa a regra 6.8C: nove clips normalizados, média e L2 por classe."""
    return build_final_clip_centroids(positives)


def edge_calibration_observations(
    positives: tuple, negatives: tuple, predictions: dict[str, int]
) -> tuple[dict, ...]:
    """Reusa self exclusion KNOWN e centroide completo UNKNOWN da 6.8C."""
    queries = (*positives, *negatives)
    if (
        not positives
        or not negatives
        or len({row.sample_id for row in queries}) != len(queries)
        or set(predictions) != {row.sample_id for row in queries}
        or any(index not in range(6) for index in predictions.values())
    ):
        raise ValueError("Queries ou previsões de calibração Edge inválidas.")
    centroids = build_edge_centroids(positives)
    return tuple(
        calibration_observation(row, predictions[row.sample_id], positives, centroids)
        for row in queries
    )


def calibrate_edge(observations: tuple[dict, ...]) -> dict:
    """Aplica somente CLIP_CLASS_COSINE e desempate existente da 6.8C."""
    selected = select_calibrated_threshold(POLICY, observations)
    threshold = selected["thresholds"][0]
    if not math.isfinite(threshold):
        raise ValueError("Threshold não finito não pode congelar inferência Edge.")
    decisions = tuple(
        acceptance_decision(POLICY, row, (threshold,)) for row in observations
    )
    return {
        "threshold": threshold,
        "candidate_count": selected["candidate_count"],
        "decisions": decisions,
        "metrics": calculate_detailed_metrics(observations, decisions),
    }


def canonical_fingerprint(config: dict) -> str:
    """SHA-256 do JSON UTF-8 sorted, compacto e sem o próprio fingerprint."""
    payload = {
        key: value
        for key, value in config.items()
        if key != "pipeline_fingerprint_sha256"
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_edge_config(root: Path, config: dict) -> None:
    """Confere estado, fingerprint e hashes sem abrir dados de amostras."""
    if (
        config.get("state") != STATE
        or config.get("heldouts_used") is not False
        or config.get("labels") != list(DEFAULT_VISUAL_LABELS)
        or config.get("rejection", {}).get("policy") != POLICY
        or not isinstance(config["rejection"].get("threshold"), (int, float))
        or not math.isfinite(config["rejection"]["threshold"])
        or config.get("pipeline_fingerprint_sha256") != canonical_fingerprint(config)
    ):
        raise ValueError("Estado ou pipeline fingerprint Edge inválido.")
    encoder = config.get("encoder", {})
    classifier = config.get("classifier", {})
    preprocessing = config.get("preprocessing", {})
    dtw = config.get("dtw", {})
    if (
        encoder.get("candidate_id") != ENCODER_ID
        or encoder.get("input_name") != "roi_input"
        or encoder.get("output_name") != "clip_embedding"
        or encoder.get("input_shape") != [1, 1, 29, 88, 88]
        or encoder.get("output_shape") != [1, 1664]
        or encoder.get("opset") != [{"domain": "", "version": 18}]
        or classifier.get("model_id") != CLASSIFIER_ID
        or classifier.get("input_name") != "hybrid_features"
        or classifier.get("output_name") != "logits"
        or classifier.get("input_shape") != [1, 1670]
        or classifier.get("output_shape") != [1, 6]
        or preprocessing.get("input_shape") != [1, 1, 29, 88, 88]
        or preprocessing.get("frame_count") != 29
        or preprocessing.get("center_crop_size") != [88, 88]
        or preprocessing.get("normalization")
        != {"scale_divisor": 255.0, "mean": 0.421, "std": 0.165}
        or dtw.get("id") != "CURRENT_DTW"
        or dtw.get("distance_config")
        != {"normalize_by_path_length": False, "max_normalized_warping": None}
        or dtw.get("template_count") != 54
        or config.get("policy_reselected") is not False
        or config.get("architecture_changed") is not False
        or config.get("edge_threshold_calibrated_on_development_only") is not True
    ):
        raise ValueError("Config contém contrato congelado ONNX/DTW incompatível.")
    for section, path_key, hash_key in (
        ("encoder", "path", "sha256"),
        ("classifier", "path", "sha256"),
        ("rejection", "centroid_path", "centroid_sha256"),
    ):
        data = config[section]
        artifact_path = _authorized_artifact(root, data[path_key])
        if sha256_file(artifact_path) != data[hash_key]:
            raise ValueError(f"SHA-256 de {section} divergiu.")


def validate_freeze_manifest(root: Path, manifest: dict, config: dict) -> None:
    """Confere todos os artefatos nomeados pelo manifesto sem auto-hash."""
    if (
        manifest.get("state") != STATE
        or manifest.get("heldouts_used") is not False
        or manifest.get("cycle_06_heldout_evaluation_candidate") != ENCODER_ID
        or manifest.get("final_android_runtime") != "UNFROZEN"
        or manifest.get("pipeline_fingerprint_sha256")
        != config.get("pipeline_fingerprint_sha256")
        or "final_config" not in manifest.get("artifacts", {})
    ):
        raise ValueError("Manifesto Edge não corresponde ao config congelado.")
    allowed = (Path(root) / "data/processed").resolve()
    for name, record in manifest["artifacts"].items():
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Path inválido no manifesto: {name}")
        path = (Path(root) / relative).resolve()
        if not path.is_relative_to(allowed) or sha256_file(path) != record["sha256"]:
            raise ValueError(f"SHA-256 ou path de {name} divergiu do manifesto.")


def _ort_session(path: Path) -> ort.InferenceSession:
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    return ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


@dataclass(slots=True)
class FrozenEdgePipeline:
    """Inferência explícita ONNX + DTW + cosseno, sem fallback neural."""

    encoder_session: object
    classifier_session: object
    templates: tuple[HybridSample, ...]
    centroids: np.ndarray
    threshold: float
    fingerprint: str

    def predict(self, query: object, tensor: np.ndarray) -> dict:
        """Prediz uma amostra já preparada, sem acessar vídeo ou diretórios."""
        values = np.asarray(tensor)
        if (
            values.shape != (1, 1, 29, 88, 88)
            or values.dtype != np.float32
            or not np.isfinite(values).all()
        ):
            raise ValueError("Tensor Edge deve ser FP32 finito (1,1,29,88,88).")
        # Falhas do ONNX são propagadas; não existe caminho PyTorch alternativo.
        output = self.encoder_session.run(None, {"roi_input": values})
        if len(output) != 1 or np.asarray(output[0]).shape != (1, 1664):
            raise ValueError("Saída do encoder ONNX incompatível.")
        clip = validate_edge_embedding(np.asarray(output[0])[0])
        return self.predict_from_clip(query, clip)

    def predict_from_clip(self, query: object, clip: np.ndarray) -> dict:
        """Reusa clip Edge já calculado para calibração, com DTW e head ONNX."""
        clip = validate_edge_embedding(clip)
        future_query = HybridSample(
            query.sample_id + "__edge_query",
            query.session_id,
            getattr(query, "label", ""),
            getattr(query, "label_index", -1),
            clip,
            query.features,
        )
        distances = class_minimum_dtw_distances(future_query, self.templates)
        evidence = normalized_reciprocal_evidence(distances)
        feature = equal_energy_fusion(clip, evidence, 1670)
        logits_output = self.classifier_session.run(
            None, {"hybrid_features": feature[None, :]}
        )
        if len(logits_output) != 1:
            raise ValueError("Saída do head ONNX ausente.")
        logits = np.asarray(logits_output[0])
        if logits.shape != (1, 6) or not np.isfinite(logits).all():
            raise ValueError("Logits ONNX inválidos.")
        index = int(np.argmax(logits[0]))
        label = DEFAULT_VISUAL_LABELS[index]
        score = score_unknown_clip(clip, index, self.centroids)
        accepted = score >= self.threshold
        return {
            "sample_id": query.sample_id,
            "predicted_label": label,
            "predicted_label_index": index,
            "logits": [float(value) for value in logits[0]],
            "clip_class_cosine": score,
            "threshold": self.threshold,
            "decision": "ACCEPT" if accepted else "REJECT",
            "accepted_label": label if accepted else None,
            "dtw_distances": distances.tolist(),
            "clip_embedding_sha256": clip_embedding_sha256(clip),
            "pipeline_fingerprint_sha256": self.fingerprint,
        }


def load_frozen_edge_pipeline(
    root: Path,
    config_path: Path,
    templates: tuple[HybridSample, ...],
    require_manifest: bool = True,
) -> FrozenEdgePipeline:
    """Carrega somente ONNX e centroides íntegros da configuração congelada."""
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    validate_edge_config(root, config)
    if require_manifest:
        manifest = json.loads((Path(root) / FREEZE_MANIFEST).read_text("utf-8"))
        validate_freeze_manifest(root, manifest, config)
    centroid_path = _authorized_artifact(root, config["rejection"]["centroid_path"])
    with np.load(centroid_path, allow_pickle=False) as archive:
        if set(archive.files) != {
            "centroids",
            "labels",
            "format_version",
            "encoder_candidate_id",
        }:
            raise ValueError("Campos do centroide Edge divergentes.")
        centroids = np.asarray(archive["centroids"]).copy()
        labels = archive["labels"].tolist()
        version = int(archive["format_version"])
        candidate = str(archive["encoder_candidate_id"])
    if labels != list(DEFAULT_VISUAL_LABELS) or version != 1 or candidate != ENCODER_ID:
        raise ValueError("Metadados do centroide Edge divergentes.")
    _validate_centroids(centroids)
    encoder = _ort_session(_authorized_artifact(root, config["encoder"]["path"]))
    head = _ort_session(_authorized_artifact(root, config["classifier"]["path"]))
    if (
        encoder.get_inputs()[0].name != "roi_input"
        or encoder.get_inputs()[0].shape != [1, 1, 29, 88, 88]
        or encoder.get_outputs()[0].name != "clip_embedding"
        or encoder.get_outputs()[0].shape != [1, 1664]
        or head.get_inputs()[0].name != "hybrid_features"
        or head.get_inputs()[0].shape != [1, 1670]
        or head.get_outputs()[0].name != "logits"
        or head.get_outputs()[0].shape != [1, 6]
    ):
        raise ValueError("Contrato do runtime ONNX divergiu do freeze.")
    return FrozenEdgePipeline(
        encoder,
        head,
        templates,
        centroids,
        float(config["rejection"]["threshold"]),
        config["pipeline_fingerprint_sha256"],
    )
