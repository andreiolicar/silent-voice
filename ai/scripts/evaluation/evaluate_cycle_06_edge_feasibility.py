"""Avalia export Edge congelado somente no corpus de desenvolvimento."""

import argparse
import json
import platform
import statistics
import subprocess
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from silent_voice.edge.parity import (
    FROZEN_THRESHOLD,
    aggregate_candidate,
    compare_downstream,
    embedding_parity,
    leading_technical_candidate,
)
from silent_voice.edge.swinlip_export import (
    FROZEN_PATHS,
    SwinLipClipEncoder,
    export_fp32_encoder,
    export_positive_head,
    select_golden_records,
    validate_frozen_hashes,
)
from silent_voice.rejection.hybrid_rejection_final import load_frozen_clip_rejection
from silent_voice.rejection.hybrid_rejection_nested_loso import (
    preflight_real_nested_loso,
)
from silent_voice.vision.hybrid_features import (
    HybridSample,
    class_minimum_dtw_distances,
    equal_energy_fusion,
    normalized_reciprocal_evidence,
)
from silent_voice.vision.mouth_roi_dataset import sha256_file
from silent_voice.vision.positive_classifier_final import (
    load_frozen_positive_classifier,
)
from silent_voice.vision.swinlip_frozen_encoder import (
    load_official_model,
    prepare_input,
)

OUTPUT = Path("data/processed/evaluation/cycle_06_edge_feasibility.json")
MODEL_DIR = Path("data/processed/models/edge")
MANIFESTS = {
    "KNOWN": (
        Path("data/processed/evaluation/cycle_06_mouth_roi_manifest.json"),
        Path("data/processed/evaluation/cycle_06_swinlip_embedding_manifest.json"),
        Path("data/processed/visual_swinlip_embeddings"),
    ),
    "UNKNOWN": (
        Path(
            "data/processed/evaluation/cycle_06_rejection_dev_mouth_roi_manifest.json"
        ),
        Path(
            "data/processed/evaluation/"
            "cycle_06_rejection_dev_swinlip_embedding_manifest.json"
        ),
        Path("data/processed/rejection_visual_swinlip_embeddings"),
    ),
}
MANIFEST_HASHES = {
    "KNOWN": "e6f8b2952f40ccfa8c2988d0909c35a14dd6ae42821e9fc55cb7f5abe3995ee2",
    "UNKNOWN": "cacab11fb0d4890558bc292c9b68087d8e5a5f42a9fdd8db0a6877185d08c0c4",
    "UNKNOWN_EMBEDDING": (
        "8b59f0c07a9947a06416eea2359a0acc86921d3c16a51c4349edca0689909d46"
    ),
}


def _manifest_records(root: Path) -> tuple[tuple[dict, ...], dict]:
    """Valida todos os caminhos antes do primeiro I/O de NPZ."""
    roi_records = {}
    embedding_records = {}
    hashes = {}
    for kind, (roi_relative, embedding_relative, embedding_root) in MANIFESTS.items():
        roi_hash = sha256_file(root / roi_relative)
        embedding_hash = sha256_file(root / embedding_relative)
        if roi_hash != MANIFEST_HASHES[kind] or (
            kind == "UNKNOWN" and embedding_hash != MANIFEST_HASHES["UNKNOWN_EMBEDDING"]
        ):
            raise ValueError(f"Manifesto {kind} divergiu do desenvolvimento congelado.")
        hashes[kind] = {"roi": roi_hash, "embedding": embedding_hash}
        roi_records[kind] = json.loads((root / roi_relative).read_text("utf-8"))[
            "samples"
        ]
        entries = json.loads((root / embedding_relative).read_text("utf-8"))["samples"]
        if len(entries) != 54 or len({row["sample_id"] for row in entries}) != 54:
            raise ValueError("Manifesto de embeddings incompleto ou duplicado.")
        embedding_records[kind] = {row["sample_id"]: row for row in entries}
        for row in entries:
            if (
                row["session_id"] not in ("sessao_01", "sessao_02", "sessao_03")
                if kind == "KNOWN"
                else row["session_id"]
                not in ("rejeicao_dev_01", "rejeicao_dev_02", "rejeicao_dev_03")
            ) or Path(row["embedding_path"]) != embedding_root / (
                row["sample_id"] + ".npz"
            ):
                raise ValueError("Path de embedding fora do development permitido.")
    selected = select_golden_records(root, roi_records["KNOWN"], roi_records["UNKNOWN"])
    if any(
        set(embedding_records[kind])
        != {row["sample_id"] for row in selected if row["kind"] == kind}
        for kind in MANIFESTS
    ):
        raise ValueError("ROI e embeddings não pareiam 1:1.")
    return selected, {"hashes": hashes, "embeddings": embedding_records}


def _load_corpus(root: Path, selected: tuple[dict, ...], records: dict) -> list[dict]:
    corpus = []
    for row in selected:
        kind = row["kind"]
        sample_id = row["sample_id"]
        roi_record = row["roi_record"]
        embedding_record = records[kind][sample_id]
        if (
            sha256_file(row["roi_path"]) != roi_record["derived_roi_sha256"]
            or embedding_record["source_roi_sha256"] != roi_record["derived_roi_sha256"]
        ):
            raise ValueError(f"Hash ROI divergiu: {sample_id}")
        embedding_path = root / embedding_record["embedding_path"]
        if sha256_file(embedding_path) != embedding_record["embedding_sha256"]:
            raise ValueError(f"Hash embedding divergiu: {sample_id}")
        with np.load(row["roi_path"], allow_pickle=False) as data:
            roi = np.asarray(data["mouth_rois"]).copy()
        with np.load(embedding_path, allow_pickle=False) as data:
            frozen_clip = np.asarray(data["clip_embedding"]).copy()
            frozen_indices = np.asarray(data["selected_source_frame_indices"]).copy()
        indices = np.asarray(embedding_record["selected_source_frame_indices"])
        if (
            indices.shape != (29,)
            or not np.array_equal(indices, frozen_indices)
            or frozen_clip.shape != (1664,)
            or frozen_clip.dtype != np.float32
            or not np.isfinite(frozen_clip).all()
        ):
            raise ValueError(f"Embedding congelado inválido: {sample_id}")
        tensor = prepare_input(roi, indices).numpy()
        corpus.append(
            {
                "sample_id": sample_id,
                "sample_kind": kind,
                "session_id": row["session_id"],
                "input": tensor,
                "frozen_clip": frozen_clip,
            }
        )
    return corpus


def _session(path: Path) -> ort.InferenceSession:
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    return ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


def _artifact(path: Path) -> dict:
    graph = onnx.load(str(path))
    onnx.checker.check_model(graph)
    return {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "input_name": graph.graph.input[0].name,
        "output_name": graph.graph.output[0].name,
        "input_shape": [
            dim.dim_value for dim in graph.graph.input[0].type.tensor_type.shape.dim
        ],
        "output_shape": [
            dim.dim_value for dim in graph.graph.output[0].type.tensor_type.shape.dim
        ],
        "opsets": [
            {"domain": item.domain, "version": item.version}
            for item in graph.opset_import
        ],
        "operators": dict(
            sorted(Counter(node.op_type for node in graph.graph.node).items())
        ),
        "checker": "PASSED",
    }


def _benchmark(session: ort.InferenceSession, tensor: np.ndarray) -> dict:
    name = session.get_inputs()[0].name
    for _ in range(10):
        session.run(None, {name: tensor})
    durations = []
    for _ in range(50):
        start = time.perf_counter_ns()
        session.run(None, {name: tensor})
        durations.append((time.perf_counter_ns() - start) / 1e6)
    return {
        "benchmark_id": "HOST_FEASIBILITY_BENCHMARK",
        "batch_size": 1,
        "cpu_threads": 4,
        "warmup_runs": 10,
        "measured_runs": 50,
        "p50_ms": float(np.percentile(durations, 50)),
        "p95_ms": float(np.percentile(durations, 95)),
        "mean_ms": statistics.mean(durations),
        "min_ms": min(durations),
        "max_ms": max(durations),
        "peak_rss_bytes": None,
    }


def _evaluate_candidate(
    candidate_id: str,
    path: Path,
    corpus: list[dict],
    reference: list[dict],
    classifier: object,
    rejection: object,
    benchmark_input: np.ndarray,
) -> dict:
    artifact = _artifact(path)
    session = _session(path)
    if (
        session.get_inputs()[0].name != "roi_input"
        or session.get_inputs()[0].shape != [1, 1, 29, 88, 88]
        or session.get_outputs()[0].name != "clip_embedding"
        or session.get_outputs()[0].shape != [1, 1664]
    ):
        raise ValueError(f"Contrato ONNX de {candidate_id} inválido.")
    rows = []
    for source, expected in zip(corpus, reference, strict=True):
        clip = np.asarray(
            session.run(None, {"roi_input": source["input"]})[0][0],
            dtype=np.float32,
        )
        parity = embedding_parity(expected["clip"], clip)
        if parity["finite"]:
            feature = equal_energy_fusion(clip, expected["dtw_evidence"], 1670)
            prediction = classifier.predict_feature(feature)
            decision = rejection.decide(
                clip, prediction["predicted_label"], prediction["predicted_label_index"]
            )
            downstream = compare_downstream(
                expected["prediction"]["predicted_label"],
                prediction["predicted_label"],
                expected["decision"]["clip_class_cosine"],
                decision["clip_class_cosine"],
            )
        else:
            downstream = {
                "labels_equal": False,
                "decisions_equal": False,
                "rejection_score_abs_diff": None,
                "reference_predicted_label": expected["prediction"]["predicted_label"],
                "edge_predicted_label": None,
                "reference_decision": expected["decision"]["decision"],
                "edge_decision": None,
                "reference_rejection_score": expected["decision"]["clip_class_cosine"],
                "edge_rejection_score": None,
            }
        rows.append(
            {
                "sample_id": source["sample_id"],
                "sample_kind": source["sample_kind"],
                "session_id": source["session_id"],
                **parity,
                **downstream,
            }
        )
    aggregate = aggregate_candidate(candidate_id, rows)
    benchmark = _benchmark(session, benchmark_input)
    return {
        "id": candidate_id,
        "artifact": artifact,
        "load_success": True,
        "inference_success": True,
        "per_sample": rows,
        "aggregate": aggregate,
        "benchmark": benchmark,
        "requires_edge_recalibration_in_task_6_10": (
            candidate_id != "ONNX_FP32" and aggregate["status"] == "DECISION_CHANGED"
        ),
    }


def _matrix_row(candidate: dict) -> dict:
    aggregate = candidate["aggregate"]
    return {
        "id": candidate["id"],
        "artifact": candidate["artifact"]["path"],
        "size_mb": candidate["artifact"]["size_bytes"] / 1e6,
        "load_success": candidate["load_success"],
        "inference_success": candidate["inference_success"],
        "finite_count": aggregate["finite_count"],
        "min_embedding_cosine": aggregate["min_embedding_cosine"],
        "max_abs_embedding_error": aggregate["max_abs_embedding_error"],
        "label_agreement_count": aggregate["label_agreement_count"],
        "decision_agreement_count": aggregate["decision_agreement_count"],
        "host_p50_ms": candidate["benchmark"]["p50_ms"],
        "host_p95_ms": candidate["benchmark"]["p95_ms"],
        "conversion_blockers": [],
        "requires_edge_recalibration_in_task_6_10": candidate[
            "requires_edge_recalibration_in_task_6_10"
        ],
        "status": aggregate["status"],
        "size_bytes": candidate["artifact"]["size_bytes"],
    }


def run(root: Path) -> dict:
    root = Path(root).resolve()
    if (root / OUTPUT).exists():
        raise FileExistsError("Resultado Edge já existe; avaliação não será repetida.")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError("O worktree versionável deve estar limpo antes da avaliação.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    provenance = validate_frozen_hashes(root)
    selected, manifests = _manifest_records(root)
    prepared = preflight_real_nested_loso(root)
    corpus = _load_corpus(root, selected, manifests["embeddings"])
    samples = {
        item.sample_id: item
        for item in (*prepared["positives"], *prepared["negatives"])
    }
    if set(samples) != {row["sample_id"] for row in corpus}:
        raise ValueError("Corpus ROI e features geométricas não pareiam.")
    classifier = load_frozen_positive_classifier(
        root / FROZEN_PATHS["classifier"], root / FROZEN_PATHS["positive_config"]
    )
    rejection = load_frozen_clip_rejection(
        root / FROZEN_PATHS["rejection_config"], root
    )
    if rejection.threshold != FROZEN_THRESHOLD:
        raise ValueError("Threshold FP32 congelado divergente.")
    official, config = load_official_model(
        root / "data/external/swinlip/source", root / FROZEN_PATHS["encoder"]
    )
    wrapper = SwinLipClipEncoder(official)
    parameter_count = sum(item.numel() for item in official.parameters())
    if parameter_count != 53844608:
        raise ValueError("Contagem de parâmetros SwinLip divergente.")
    reference = []
    # O primeiro forward ocorre somente após todo corpus, modelos e hashes passarem.
    torch.set_num_threads(4)
    with torch.no_grad():
        for source in corpus:
            sample = samples[source["sample_id"]]
            if source["sample_kind"] == "KNOWN":
                query = replace(sample, sample_id=sample.sample_id + "__edge_query")
            else:
                query = HybridSample(
                    sample.sample_id,
                    sample.session_id,
                    "",
                    -1,
                    sample.clip_embedding,
                    sample.features,
                )
            dtw = class_minimum_dtw_distances(query, classifier.templates)
            evidence = normalized_reciprocal_evidence(dtw)
            clip = wrapper(torch.from_numpy(source["input"]))[0].numpy().copy()
            feature = equal_energy_fusion(clip, evidence, 1670)
            prediction = classifier.predict_feature(feature)
            decision = rejection.decide(
                clip, prediction["predicted_label"], prediction["predicted_label_index"]
            )
            reference.append(
                {
                    "clip": clip,
                    "dtw_evidence": evidence,
                    "feature": feature,
                    "prediction": prediction,
                    "decision": decision,
                    "frozen_embedding_parity": embedding_parity(
                        source["frozen_clip"], clip
                    ),
                }
            )
    encoder_path = root / MODEL_DIR / "cycle_06_swinlip_clip_encoder_fp32.onnx"
    head_path = root / MODEL_DIR / "cycle_06_positive_head_fp32.onnx"
    export_config = export_fp32_encoder(wrapper, encoder_path)
    export_positive_head(classifier.model, head_path)
    head_artifact = _artifact(head_path)
    head_session = _session(head_path)
    head_differences = []
    head_matches = 0
    for row in reference:
        logits = head_session.run(None, {"hybrid_features": row["feature"][None]})[0][0]
        expected = np.asarray(row["prediction"]["logits"])
        head_differences.append(float(np.max(np.abs(logits - expected))))
        head_matches += int(
            int(np.argmax(logits)) == row["prediction"]["predicted_label_index"]
        )
    head_parity = {
        "artifact": head_artifact,
        "max_abs_logit_error": max(head_differences),
        "argmax_agreement_count": head_matches,
        "equivalent": max(head_differences) <= 1e-5 and head_matches == 108,
    }
    candidates = [
        _evaluate_candidate(
            "ONNX_FP32",
            encoder_path,
            corpus,
            reference,
            classifier,
            rejection,
            corpus[0]["input"],
        )
    ]
    compression = []
    if candidates[0]["aggregate"]["status"] == "FP32_EDGE_NUMERICALLY_EQUIVALENT":
        # FP16 e INT8 usam somente pesos congelados; sem calibração, treino ou tuning.
        try:
            from onnxconverter_common import __version__ as converter_version
            from onnxconverter_common.float16 import convert_float_to_float16

            fp16_path = root / MODEL_DIR / "cycle_06_swinlip_clip_encoder_fp16.onnx"
            if fp16_path.exists():
                raise FileExistsError("Artefato FP16 já existe.")
            converted = convert_float_to_float16(
                onnx.load(str(encoder_path)), keep_io_types=True
            )
            onnx.save(converted, str(fp16_path))
            candidate = _evaluate_candidate(
                "ONNX_FP16",
                fp16_path,
                corpus,
                reference,
                classifier,
                rejection,
                corpus[0]["input"],
            )
            candidate["method"] = {
                "tool": "onnxconverter-common",
                "version": converter_version,
                "configuration": "float16 weights/ops; keep_io_types=True",
            }
            candidates.append(candidate)
        except Exception as error:
            compression.append(
                {"id": "ONNX_FP16", "status": "BLOCKED", "error": str(error)}
            )
        try:
            from onnxruntime.quantization import QuantType, quantize_dynamic

            int8_path = (
                root / MODEL_DIR / "cycle_06_swinlip_clip_encoder_dynamic_int8.onnx"
            )
            if int8_path.exists():
                raise FileExistsError("Artefato INT8 já existe.")
            quantize_dynamic(
                encoder_path,
                int8_path,
                weight_type=QuantType.QInt8,
                per_channel=False,
                op_types_to_quantize=["MatMul", "Gemm"],
            )
            candidate = _evaluate_candidate(
                "ONNX_DYNAMIC_INT8",
                int8_path,
                corpus,
                reference,
                classifier,
                rejection,
                corpus[0]["input"],
            )
            candidate["method"] = {
                "tool": "onnxruntime.quantization.quantize_dynamic",
                "version": ort.__version__,
                "configuration": "QInt8 weights, MatMul/Gemm only, per_channel=False",
            }
            candidates.append(candidate)
        except Exception as error:
            compression.append(
                {"id": "ONNX_DYNAMIC_INT8", "status": "BLOCKED", "error": str(error)}
            )
    rows = [_matrix_row(candidate) for candidate in candidates]
    leading = leading_technical_candidate(rows)
    reference_matrix_row = {
        "id": "PYTORCH_FP32_REFERENCE",
        "artifact": FROZEN_PATHS["encoder"],
        "size_mb": (root / FROZEN_PATHS["encoder"]).stat().st_size / 1e6,
        "load_success": True,
        "inference_success": True,
        "finite_count": 108,
        "min_embedding_cosine": 1.0,
        "max_abs_embedding_error": 0.0,
        "label_agreement_count": 108,
        "decision_agreement_count": 108,
        "host_p50_ms": None,
        "host_p95_ms": None,
        "conversion_blockers": [],
        "requires_edge_recalibration_in_task_6_10": False,
        "status": "NUMERICAL_REFERENCE",
    }
    result = {
        "task": "6.9",
        "pre_experiment_commit": commit,
        "heldouts_used": False,
        "provenance": {
            "frozen_hashes": provenance,
            "manifest_hashes": manifests["hashes"],
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": ort.__version__,
            "cpu_threads": 4,
        },
        "reference_model": {
            "parameter_count": parameter_count,
            "parameter_dtype": "float32",
            "checkpoint_size_bytes": (root / FROZEN_PATHS["encoder"]).stat().st_size,
            "input_shape": [1, 1, 29, 88, 88],
            "output_shape": [1, 1664],
            "official_config": config,
            "frozen_embedding_parity": [
                {"sample_id": row["sample_id"], **item["frozen_embedding_parity"]}
                for row, item in zip(corpus, reference, strict=True)
            ],
        },
        "export_config": export_config,
        "parity_corpus": {"KNOWN": 54, "UNKNOWN": 54, "total": 108},
        "positive_head": head_parity,
        "candidates": candidates,
        "compression_attempts": compression,
        "tflite_feasibility": {
            "status": "TFLITE_CONVERSION_NOT_ESTABLISHED",
            "direct_path_available": False,
            "intermediate_required": True,
            "real_conversion_attempted": False,
            "operator_support_verified": False,
            "math_change_required": None,
            "blocker": (
                "Toolchain atual não fornece conversão direta "
                "ONNX/PyTorch→TFLite validada."
            ),
        },
        "feasibility_matrix": [reference_matrix_row, *rows],
        "state": "EDGE_EXPORT_FEASIBLE" if leading else "EDGE_EXPORT_BLOCKED",
        "leading_technical_candidate": leading,
        "compression_candidate_available": len(candidates) > 1,
        "requires_edge_recalibration_in_task_6_10": any(
            item["requires_edge_recalibration_in_task_6_10"] for item in candidates
        ),
        "deployment_runtime_frozen": False,
        "frozen_rejection_threshold": FROZEN_THRESHOLD,
    }
    output_path = root / OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-edge-feasibility", action="store_true")
    args = parser.parse_args()
    if not args.execute_edge_feasibility:
        parser.error("Exige --execute-edge-feasibility para o experimento real.")
    result = run(Path(__file__).resolve().parents[2])
    print(
        json.dumps(
            {
                "state": result["state"],
                "leading_technical_candidate": result["leading_technical_candidate"],
                "candidate_statuses": {
                    item["id"]: item["aggregate"]["status"]
                    for item in result["candidates"]
                },
                "output": OUTPUT.as_posix(),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
