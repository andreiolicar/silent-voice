"""Contratos sintéticos do Live Visual Tester, sem câmera ou modelos reais."""

import copy
import hashlib
import json
import math
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest
import numpy as np

from silent_voice.inference import live_visual_tester as tester
from silent_voice.edge import rejection_4_final_heldout as r4


LABELS = ("SIM", "NÃO", "AJUDA", "ÁGUA", "BANHEIRO", "PARAR")
R4_THRESHOLD = 0.5666271450980487
R4_CANDIDATE = "R4_REFERENCE_BANK_TOP3_GLOBAL"
FINAL_FREEZE = Path("docs/cycles/rejection_4_final_freeze.json")
FINAL_RESULT_SHA = "e501474e879c274fd515d1791cca5b8464565d29984cb3e9607899425580e763"
PIPELINE_FINGERPRINT = (
    "e8394f470520f61d096bc0f1a4f5997f5ae5692af412707c4905519ae602c48b"
)
EXCLUDED_HELDOUT_PROVENANCE = {
    "plan",
    "heldout_freeze",
    "capture_manifest",
    "qc_json",
}
LIVE_ARTIFACT_NAMES = {
    "encoder",
    "head",
    "edge_scorer",
    "positive_checkpoint",
    "positive_config",
    "reference_bank",
}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    return _sha(path.read_bytes())


@pytest.fixture
def frozen_fixture(tmp_path, monkeypatch):
    """Artefatos fictícios completos; nenhum vídeo ou resultado held-out existe."""
    records = {}
    policy = {
        "state": "REJECTION_4_EDGE_POLICY_FROZEN",
        "candidate_id": R4_CANDIDATE,
        "k": 3,
        "threshold": R4_THRESHOLD,
        "operator": ">=",
        "labels": list(LABELS),
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
        "runtime": "1.30.0",
        "provider": "CPUExecutionProvider",
    }
    for name, (relative, _) in r4.PROVENANCE.items():
        if name in EXCLUDED_HELDOUT_PROVENANCE:
            continue
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == "edge_freeze":
            _write_json(path, policy)
        elif path.suffix == ".json":
            _write_json(path, {"synthetic_artifact": name})
        else:
            path.write_bytes(name.encode("ascii"))
        records[name] = (relative, _sha(path.read_bytes()))
    bank_manifest = {
        "state": "REJECTION_4_REFERENCE_POLICY_FROZEN",
        "candidate_id": R4_CANDIDATE,
        "k": 3,
        "labels": list(LABELS),
        "final_reference_count": 126,
        "references_per_class": [21] * 6,
        "embedding_shape": [126, 1664],
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
        "bank_path": records["reference_bank"][0].as_posix(),
        "bank_sha256": records["reference_bank"][1],
        "heldouts_opened": False,
        "source_counts": {"historical": 54, "r4_known": 72},
    }
    relative, _ = records["reference_bank_manifest"]
    records["reference_bank_manifest"] = (
        relative,
        _write_json(tmp_path / relative, bank_manifest),
    )
    reference_freeze = {
        "state": "REJECTION_4_REFERENCE_POLICY_FROZEN",
        "candidate_id": R4_CANDIDATE,
        "k": 3,
        "labels": list(LABELS),
        "selected_threshold": R4_THRESHOLD,
        "decision_operator": ">=",
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
        "final_reference_count": 126,
        "references_per_class": 21,
        "bank_path": records["reference_bank"][0].as_posix(),
        "bank_sha256": records["reference_bank"][1],
        "bank_manifest_sha256": records["reference_bank_manifest"][1],
    }
    relative, _ = records["reference_freeze"]
    records["reference_freeze"] = (
        relative,
        _write_json(tmp_path / relative, reference_freeze),
    )
    edge_manifest = {
        **policy,
        "reference_bank_sha256": records["reference_bank"][1],
        "reference_bank_manifest_sha256": records["reference_bank_manifest"][1],
        "reference_policy_freeze_sha256": records["reference_freeze"][1],
        "scorer_sha256": records["edge_scorer"][1],
        "scorer_path": records["edge_scorer"][0].as_posix(),
    }
    relative, _ = records["edge_manifest"]
    records["edge_manifest"] = (
        relative,
        _write_json(tmp_path / relative, edge_manifest),
    )
    monkeypatch.setattr(r4, "PROVENANCE", records)
    monkeypatch.setattr(
        r4, "_validate_positive_config", lambda root, config, **kwargs: config
    )
    monkeypatch.setattr(
        tester,
        "EXPECTED_EDGE_FREEZE_SHA256",
        records["edge_freeze"][1],
        raising=False,
    )
    monkeypatch.setattr(tester.ort, "__version__", "1.30.0")
    monkeypatch.setattr(
        tester.ort, "get_available_providers", lambda: ["CPUExecutionProvider"]
    )
    freeze = {
        "format_version": 1,
        "state": "REJECTION_4_CLOSED",
        "task": "R4.8B",
        "task_status": "CLOSED",
        "technical_status": "PASS",
        "candidate_id": R4_CANDIDATE,
        "k": 3,
        "threshold": R4_THRESHOLD,
        "operator": ">=",
        "labels": list(LABELS),
        "pipeline_fingerprint_sha256": PIPELINE_FINGERPRINT,
        "positive_classifier_id": "HYBRID_CLIP_DTW_EVIDENCE_LINEAR",
        "evaluation_run_count": 1,
        "heldout_consumed": True,
        "heldout_evaluated": True,
        "heldout_status": "CONSUMED",
        "expected_sample_count": 72,
        "result_record_count": 72,
        "evaluation_result_path": r4.OUTPUT.as_posix(),
        "evaluation_result_sha256": FINAL_RESULT_SHA,
        "edge_freeze_sha256": records["edge_freeze"][1],
        "artifact_sha256": {name: records[name][1] for name in LIVE_ARTIFACT_NAMES},
        "provenance_sha256": {name: record[1] for name, record in records.items()},
        "contamination_audit": {
            "post_heldout_tuning": False,
            "threshold_changed": False,
            "k_changed": False,
            "bank_changed": False,
            "rerun_performed": False,
            "heldout_modified": False,
        },
    }
    freeze_sha = _write_json(tmp_path / FINAL_FREEZE, freeze)
    return SimpleNamespace(
        root=tmp_path,
        freeze=freeze,
        freeze_sha=freeze_sha,
        records=records,
    )


def _verify(fixture):
    return tester.verify_frozen_sources(
        fixture.root,
        public_root=fixture.root,
        freeze_sha256=fixture.freeze_sha,
        result_sha256=FINAL_RESULT_SHA,
    )


@pytest.mark.parametrize("change", ["missing", "wrong_hash"])
def test_preflight_separates_public_resources_from_private_artifacts(
    frozen_fixture, tmp_path, change
):
    fixture = frozen_fixture
    public = tmp_path / "installed_public"
    for name in tester.PUBLIC_PROVENANCE_NAMES:
        relative = fixture.records[name][0]
        destination = public / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        (fixture.root / relative).rename(destination)
    result = tester.verify_frozen_sources(
        fixture.root,
        public_root=public,
        freeze_sha256=fixture.freeze_sha,
        result_sha256=FINAL_RESULT_SHA,
    )
    assert set(result["provenance_sha256"]) == set(tester.LIVE_PROVENANCE_NAMES)
    path = public / fixture.records["edge_freeze"][0]
    if change == "missing":
        path.unlink()
    else:
        path.write_bytes(b"wrong bytes")
    with pytest.raises(ValueError):
        tester.verify_frozen_sources(
            fixture.root,
            public_root=public,
            freeze_sha256=fixture.freeze_sha,
            result_sha256=FINAL_RESULT_SHA,
        )


def test_check_accepts_r4_without_reading_heldout_or_loading_models(
    frozen_fixture, monkeypatch
):
    fixture = frozen_fixture
    monkeypatch.setattr(
        r4, "_load_runtime", lambda *args: pytest.fail("Preflight não carrega modelos.")
    )
    monkeypatch.setattr(
        tester, "open_camera", lambda *args: pytest.fail("Preflight não abre câmera.")
    )
    assert not (fixture.root / r4.OUTPUT).exists()
    assert not (fixture.root / "data/raw/rejection_4_heldout").exists()
    verified = _verify(fixture)
    assert verified["candidate_id"] == R4_CANDIDATE
    assert verified["threshold"] == R4_THRESHOLD
    assert verified["k"] == 3
    assert verified["operator"] == ">="
    assert set(verified["artifact_sha256"]) == LIVE_ARTIFACT_NAMES


@pytest.mark.parametrize(
    "artifact",
    [
        "edge_freeze",
        "edge_manifest",
        "edge_scorer",
        "encoder",
        "head",
        "positive_checkpoint",
        "positive_config",
        "reference_bank",
        "reference_freeze",
        "reference_bank_manifest",
        "edge_config",
        "edge_centroids",
        "edge_origin_manifest",
    ],
)
def test_check_rejects_changed_artifact_bytes(frozen_fixture, artifact):
    fixture = frozen_fixture
    relative, _ = fixture.records[artifact]
    (fixture.root / relative).write_bytes(b"alterado")
    with pytest.raises(ValueError, match="SHA|artefato|artifact"):
        _verify(fixture)


def test_check_rejects_changed_final_freeze_bytes(frozen_fixture):
    fixture = frozen_fixture
    (fixture.root / FINAL_FREEZE).write_bytes(b"freeze alterado")
    with pytest.raises(ValueError, match="SHA"):
        _verify(fixture)


@pytest.mark.parametrize(
    "key,value",
    [
        ("state", "REJECTION_3_CLOSED"),
        ("state", "REJECTION_4_IN_PROGRESS"),
        ("candidate_id", "R2_GLOBAL_CLIP_COSINE"),
        ("k", 5),
        ("k", 3.0),
        ("threshold", 0.6367948055267334),
        ("threshold", 0.5666271450980488),
        ("operator", ">"),
        ("pipeline_fingerprint_sha256", "0" * 64),
        ("labels", list(reversed(LABELS))),
        ("positive_classifier_id", "OTHER_CLASSIFIER"),
        ("evaluation_run_count", 0),
        ("evaluation_run_count", 2),
        ("heldout_consumed", False),
        ("heldout_status", "UNEVALUATED"),
        ("evaluation_result_sha256", "0" * 64),
    ],
)
def test_check_rejects_semantically_invalid_r4_freeze(frozen_fixture, key, value):
    fixture = frozen_fixture
    fixture.freeze[key] = value
    fixture.freeze_sha = _write_json(fixture.root / FINAL_FREEZE, fixture.freeze)
    with pytest.raises(ValueError):
        _verify(fixture)


def test_check_rejects_edge_policy_metadata_change_despite_valid_byte_hash(
    frozen_fixture, monkeypatch
):
    fixture = frozen_fixture
    relative, _ = fixture.records["edge_freeze"]
    policy = json.loads((fixture.root / relative).read_bytes())
    policy["pipeline_fingerprint_sha256"] = "0" * 64
    changed_sha = _write_json(fixture.root / relative, policy)
    fixture.records["edge_freeze"] = (relative, changed_sha)
    fixture.freeze["edge_freeze_sha256"] = changed_sha
    fixture.freeze["provenance_sha256"]["edge_freeze"] = changed_sha
    fixture.freeze_sha = _write_json(fixture.root / FINAL_FREEZE, fixture.freeze)
    monkeypatch.setattr(tester, "EXPECTED_EDGE_FREEZE_SHA256", changed_sha)
    with pytest.raises(ValueError):
        _verify(fixture)


def test_camera_index_and_paths_reject_scientific_datasets(tmp_path):
    assert tester.validate_camera_index(1) == 1
    with pytest.raises(ValueError):
        tester.validate_camera_index(-1)
    temporary = tester.clip_path(tmp_path, "session", 1, keep=False)
    retained = tester.clip_path(tmp_path, "session", 1, keep=True)
    assert temporary.is_relative_to(tmp_path / "data/processed/live_tester/tmp")
    assert retained.is_relative_to(tmp_path / "data/processed/live_tester/clips")
    for forbidden in (
        tmp_path / "data/raw/rejection_3_heldout/x.mp4",
        tmp_path / "data/raw/rejection_4_heldout/x.mp4",
        tmp_path / "data/raw/cycle_06_new_heldout/x.mp4",
        tmp_path / "data/raw/visual_dataset/sessao_04/x.mp4",
        tmp_path / "data/raw/visual_dataset/x.mp4",
        tmp_path / "data/processed/models/edge/x.onnx",
        tmp_path / "data/processed/evaluation/x.json",
    ):
        with pytest.raises(ValueError):
            tester.ensure_diagnostic_path(tmp_path, forbidden)


def test_camera_backend_is_opt_in_and_keeps_windows_default(monkeypatch):
    observed = []

    class Camera:
        def isOpened(self):
            return True

        def set(self, *_args):
            return True

        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            observed.append("released")

    monkeypatch.setattr(
        tester.cv2,
        "VideoCapture",
        lambda index, backend: (observed.append((index, backend)), Camera())[1],
    )
    for chosen in (None, "MSMF", "ANY"):
        camera = tester.open_camera(1, backend=chosen)
        camera.release()
    default = tester.cv2.CAP_DSHOW if tester.os.name == "nt" else tester.cv2.CAP_ANY
    assert observed == [
        (1, default),
        "released",
        (1, tester.cv2.CAP_MSMF),
        "released",
        (1, tester.cv2.CAP_ANY),
        "released",
    ]
    with pytest.raises(ValueError, match="backend"):
        tester.open_camera(1, backend="INVALID")


def _prediction(*, score=R4_THRESHOLD):
    return {
        "predicted_label": "BANHEIRO",
        "predicted_label_index": 4,
        "score": score,
        "decode_status": "PASS",
        "roi_status": "PASS",
        "inference_status": "PASS",
        "segmentation_status": "DETECTED",
        "segmentation_fallback": False,
        "source_frame_count": 120,
        "dtw_distances": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "clip_embedding_sha256": "a" * 64,
    }


@pytest.mark.parametrize(
    "score,decision,emitted",
    [
        (R4_THRESHOLD, "ACCEPT", "BANHEIRO"),
        (math.nextafter(R4_THRESHOLD, math.inf), "ACCEPT", "BANHEIRO"),
        (math.nextafter(R4_THRESHOLD, -math.inf), "REJECT", None),
        (0.6, "ACCEPT", "BANHEIRO"),
        (0.2, "REJECT", None),
    ],
)
def test_infer_calls_r4_runtime_once_and_applies_inclusive_host_threshold(
    tmp_path, score, decision, emitted
):
    video = tester.clip_path(tmp_path, "session", 1, keep=False)
    calls = []

    class FakePipeline:
        def predict(self, row, path):
            calls.append((dict(row), path))
            return _prediction(score=score)

    trial = tester.infer_clip(
        FakePipeline(), video, "live_session_001", "session", root=tmp_path
    )
    assert len(calls) == 1
    row, received_path = calls[0]
    assert row["sample_id"] == "live_session_001"
    assert row["session_id"] == "session"
    assert row["sample_kind"] == "UNKNOWN"
    assert row["expected_label"] == "UNKNOWN"
    assert received_path == video
    assert trial["score"] == score
    assert trial["threshold"] == R4_THRESHOLD
    assert trial["decision"] == decision
    assert trial["emitted_label"] == emitted
    assert trial["segmentation_fallback"] is False
    assert trial["end_to_end_latency_ms"] >= 0.0
    assert "inference_latency_ms" not in trial


@pytest.mark.parametrize(
    "relative",
    [
        "data/raw/rejection_4_heldout/session_01/SIM/clip.mp4",
        "data/raw/rejection_3_heldout/session_01/SIM/clip.mp4",
        "data/raw/cycle_06_new_heldout/session_01/clip.mp4",
        "data/raw/visual_dataset/sessao_04/clip.mp4",
        "data/processed/live_tester/logs/clip.mp4",
        "data/processed/live_tester/tmp/../../evaluation/clip.mp4",
    ],
)
def test_infer_rejects_noncasual_path_before_preprocessing(tmp_path, relative):
    class ForbiddenPipeline:
        def predict(self, row, path):
            pytest.fail("Path proibido chegou ao preprocessing/runtime.")

    with pytest.raises(ValueError):
        tester.infer_clip(
            ForbiddenPipeline(),
            tmp_path / relative,
            "live_session_001",
            "session",
            root=tmp_path,
        )


@pytest.mark.parametrize("destination", ["heldout", "outside_repository"])
def test_infer_rejects_redirected_diagnostic_root_before_runtime(
    tmp_path, monkeypatch, destination
):
    root = tmp_path / "synthetic_repository"
    diagnostic_root = root / "data/processed/live_tester"
    video = diagnostic_root / "tmp/casual_clip.mp4"
    redirected_root = (
        root / "data/raw/rejection_4_heldout"
        if destination == "heldout"
        else tmp_path / "outside_repository"
    )
    original_resolve = Path.resolve

    def resolve_redirected(path, *args, **kwargs):
        canonical = original_resolve(path, *args, **kwargs)
        if canonical.is_relative_to(diagnostic_root):
            relative = canonical.relative_to(diagnostic_root)
            return original_resolve(redirected_root / relative, *args, **kwargs)
        return canonical

    class ForbiddenPipeline:
        def predict(self, row, path):
            pytest.fail("Raiz diagnóstica redirecionada chegou ao runtime.")

    monkeypatch.setattr(Path, "resolve", resolve_redirected)
    with pytest.raises(ValueError):
        tester.infer_clip(
            ForbiddenPipeline(),
            video,
            "live_session_001",
            "session",
            root=root,
        )


@pytest.mark.parametrize("score", [None, True, float("nan"), float("inf")])
def test_infer_rejects_nonfinite_or_invalid_score(tmp_path, score):
    class FakePipeline:
        def predict(self, row, path):
            return _prediction(score=score)

    video = tester.clip_path(tmp_path, "session", 1, keep=False)
    with pytest.raises(ValueError):
        tester.infer_clip(
            FakePipeline(), video, "live_session_001", "session", root=tmp_path
        )


def test_infer_rejects_inconsistent_positive_label_index(tmp_path):
    class FakePipeline:
        def predict(self, row, path):
            prediction = _prediction()
            prediction["predicted_label_index"] = 0
            return prediction

    video = tester.clip_path(tmp_path, "session", 1, keep=False)
    with pytest.raises(ValueError):
        tester.infer_clip(
            FakePipeline(), video, "live_session_001", "session", root=tmp_path
        )


def test_infer_propagates_technical_failure_instead_of_reject(tmp_path):
    class BrokenPipeline:
        def predict(self, row, path):
            raise RuntimeError("ROI inválida")

    video = tester.clip_path(tmp_path, "session", 1, keep=False)
    with pytest.raises(RuntimeError, match="ROI inválida"):
        tester.infer_clip(
            BrokenPipeline(), video, "live_session_001", "session", root=tmp_path
        )


def test_live_runtime_uses_positive_argmax_for_r4_scorer_without_mutating_bank(
    frozen_fixture, monkeypatch
):
    from silent_voice.edge import cycle_06_final_heldout as preparation
    from silent_voice.edge import rejection_3_final_heldout as old_policy
    from silent_voice.vision import hybrid_features

    fixture = frozen_fixture
    video = tester.clip_path(fixture.root, "session", 1, keep=False)
    events = []
    clip_embedding = np.ones((1, 1664), dtype=np.float32)
    templates = (SimpleNamespace(sample_id="historical_template"),)
    bank_path = fixture.root / fixture.records["reference_bank"][0]
    original_bank_bytes = bank_path.read_bytes()

    def prepare(row, path):
        events.append("prepare")
        assert row["expected_label"] == "UNKNOWN"
        assert path == video
        return (
            SimpleNamespace(sample_id=row["sample_id"]),
            np.zeros((1, 1, 29, 88, 88), dtype=np.float32),
            {"segmentation_fallback": False, "source_frame_count": 120},
        )

    def distances(query, frozen_templates):
        events.append("dtw")
        assert query.sample_id == "live_session_001"
        assert frozen_templates is templates
        return np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    class Encoder:
        def run(self, outputs, inputs):
            events.append("encoder")
            assert inputs["roi_input"].shape == (1, 1, 29, 88, 88)
            return [clip_embedding.copy()]

    class Head:
        def run(self, outputs, inputs):
            events.append("head")
            assert inputs["hybrid_features"].shape == (1, 1670)
            return [np.array([[0, 0, 0, 0, 0, 9]], dtype=np.float32)]

    class Scorer:
        def run(self, outputs, inputs):
            events.append("r4_scorer")
            index = inputs["predicted_label_index"]
            assert index.dtype == np.int64
            np.testing.assert_array_equal(index, [5])
            np.testing.assert_array_equal(inputs["clip_embedding"], clip_embedding)
            return [np.array([0.6], dtype=np.float32)]

    monkeypatch.setattr(preparation, "prepare_query", prepare)
    monkeypatch.setattr(hybrid_features, "class_minimum_dtw_distances", distances)
    monkeypatch.setattr(
        old_policy,
        "decision_for_score",
        lambda score: pytest.fail("A decisão final não pode usar R3."),
    )
    runtime = r4._R4Runtime(Encoder(), Head(), Scorer(), templates)
    trial = tester.infer_clip(
        runtime, video, "live_session_001", "session", root=fixture.root
    )
    assert events == ["prepare", "encoder", "dtw", "head", "r4_scorer"]
    assert trial["predicted_label"] == "PARAR"
    assert trial["score"] == pytest.approx(0.6)
    assert trial["decision"] == "ACCEPT"
    assert trial["emitted_label"] == "PARAR"
    assert bank_path.read_bytes() == original_bank_bytes
    assert runtime.templates is templates
    assert len(runtime.templates) == 1


def test_load_pipeline_verifies_sources_before_loading_frozen_r4_runtime(
    tmp_path, monkeypatch
):
    events = []
    prepared_values = []
    runtime = object()

    def verify(root):
        assert root == tmp_path.resolve()
        events.append("verify")
        return {}

    def load(prepared):
        events.append("load_r4")
        prepared_values.append(prepared)
        return runtime

    monkeypatch.setattr(tester, "verify_frozen_sources", verify)
    monkeypatch.setattr(r4, "_load_runtime", load)
    assert tester.load_live_pipeline(tmp_path) is runtime
    assert events == ["verify", "load_r4"]
    assert len(prepared_values) == 1
    assert prepared_values[0]["root"] == tmp_path.resolve()


def test_provenance_failure_stops_live_session_before_camera_or_models(
    tmp_path, monkeypatch
):
    def invalid_sources(root):
        raise ValueError("SHA-256 do scorer divergente")

    monkeypatch.setattr(tester, "verify_frozen_sources", invalid_sources)
    monkeypatch.setattr(
        tester, "load_live_pipeline", lambda root: pytest.fail("Modelo foi carregado.")
    )
    monkeypatch.setattr(
        tester, "open_camera", lambda index: pytest.fail("Câmera foi aberta.")
    )
    with pytest.raises(ValueError, match="SHA-256"):
        tester.run_live_session(tmp_path)
    assert not (tmp_path / "data/processed/live_tester").exists()


def test_cli_preflight_validates_r4_without_opening_camera_or_runtime(
    tmp_path, monkeypatch, capsys
):
    from scripts.demo import live_visual_tester as cli

    verified_roots = []
    sources = {
        "freeze_sha256": "f" * 64,
        "candidate_id": R4_CANDIDATE,
        "k": 3,
        "threshold": R4_THRESHOLD,
        "operator": ">=",
    }

    def verify(root):
        verified_roots.append(root)
        return sources

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "verify_frozen_sources", verify)
    monkeypatch.setattr(
        cli, "check_camera", lambda index: pytest.fail("Preflight abriu câmera.")
    )
    monkeypatch.setattr(
        cli, "run_live_session", lambda *args, **kwargs: pytest.fail("Demo iniciada.")
    )
    monkeypatch.setattr(
        r4, "_load_runtime", lambda prepared: pytest.fail("Preflight carregou modelos.")
    )
    cli.main(["--artifact-root", str(tmp_path), "--preflight"])
    output = capsys.readouterr().out
    assert verified_roots == [tmp_path]
    assert "R4" in output or "Rejection 4" in output
    assert R4_CANDIDATE in output
    assert str(R4_THRESHOLD) in output
    assert "PASS" in output


def test_cli_check_keeps_explicit_camera_check_after_provenance(tmp_path, monkeypatch):
    from scripts.demo import live_visual_tester as cli

    events = []

    def verify(root):
        events.append("verify")
        return {
            "freeze_sha256": "f" * 64,
            "candidate_id": R4_CANDIDATE,
            "threshold": R4_THRESHOLD,
            "k": 3,
            "operator": ">=",
        }

    def camera(index):
        assert index == 1
        events.append("camera")
        return {"camera_index": index}

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "verify_frozen_sources", verify)
    monkeypatch.setattr(cli, "check_camera", camera)
    monkeypatch.setattr(
        cli, "run_live_session", lambda *args, **kwargs: pytest.fail("Demo iniciada.")
    )
    cli.main(["--artifact-root", str(tmp_path), "--check", "--camera-index", "1"])
    assert events == ["verify", "camera"]


def test_rejection_shows_positive_label_without_probability_claim():
    trial = {
        "predicted_label": "BANHEIRO",
        "second_best_label": "PARAR",
        "score": 0.2,
        "threshold": R4_THRESHOLD,
        "decision": "REJECT",
        "emitted_label": None,
        "segmentation_status": "FALLBACK",
        "segmentation_fallback": True,
        "source_frame_count": 118,
        "end_to_end_latency_ms": 1700.0,
    }
    clean = tester.format_result_lines(trial, debug=False)
    debug = tester.format_result_lines(trial, debug=True)
    for lines in (clean, debug):
        assert any("Rejection 4" in line for line in lines)
        assert any("BANHEIRO" in line for line in lines)
        assert any("REJECT" in line or "REJEITADO" in line for line in lines)
        assert any("hipótese" in line.lower() for line in lines)
        assert any("score" in line.lower() and "0.200000" in line for line in lines)
        assert any("threshold" in line.lower() for line in lines)
        assert "Resultado: BANHEIRO" not in lines
    assert any("Margin" in line for line in debug)
    assert any("PARAR" in line for line in debug)
    assert not any("probabilidade" in line.lower() or "%" in line for line in debug)


def test_log_schema_has_no_truth_and_summary_has_no_accuracy(tmp_path):
    trial = {
        "predicted_label": "SIM",
        "second_best_label": "NÃO",
        "score": 0.75,
        "threshold": R4_THRESHOLD,
        "decision": "ACCEPT",
        "emitted_label": "SIM",
        "segmentation_fallback": False,
        "segmentation_status": "DETECTED",
        "source_frame_count": 120,
        "end_to_end_latency_ms": 1400.0,
    }
    record = tester.build_log_record(
        trial,
        timestamp_utc="2026-10-01T00:00:00+00:00",
        camera_index=1,
        clip_retained=False,
        clip_path=None,
    )
    assert record["scientific_status"] == "DEMO_DIAGNOSTIC_NOT_BENCHMARK"
    assert record["rejection_version"] == "R4"
    assert record["candidate_id"] == R4_CANDIDATE
    assert record["k"] == 3
    assert record["operator"] == ">="
    assert record["score"] == 0.75
    assert record["threshold"] == R4_THRESHOLD
    assert record["r4_final_freeze_sha256"] == (
        "d2d37118ce0278192a7777951d30c7aefbfb4a3d1caa60858c1394f2fded19e1"
    )
    assert "r3_final_freeze_sha256" not in record
    assert "cos_pred" not in record
    assert "expected_label" not in record and "true_label" not in record
    path = tmp_path / "demo.jsonl"
    tester.append_log(path, record)
    assert path.read_bytes() == tester.serialize_log_record(record)
    summary = tester.summarize_session([record, copy.deepcopy(record)])
    assert summary["total"] == 2
    assert summary["accepted"] == 2 and summary["rejected"] == 0
    assert summary["predicted_labels"] == {"SIM": 2}
    assert summary["median_end_to_end_latency_ms"] == 1400.0
    prohibited = {"accuracy", "balanced", "KCA", "KWA", "KR", "UR", "UFA"}
    assert prohibited.isdisjoint(record)
    assert prohibited.isdisjoint(summary)
    assert "accuracy" not in json.dumps(summary).lower()


def test_keep_clip_sidecar_marks_demo_and_default_cleanup_is_local(tmp_path):
    temporary = tester.clip_path(tmp_path, "session", 1, keep=False)
    temporary.parent.mkdir(parents=True)
    temporary.write_bytes(b"video")
    timing = Path(str(temporary) + ".timing.json")
    timing.write_bytes(b"synthetic timing")
    tester.cleanup_temporary_clip(tmp_path, temporary)
    assert temporary.read_bytes() == b"video"
    assert timing.read_bytes() == b"synthetic timing"
    retained = tester.clip_path(tmp_path, "session", 1, keep=True)
    retained.parent.mkdir(parents=True)
    retained.write_bytes(b"video")
    sidecar = tester.mark_retained_clip(tmp_path, retained)
    assert retained.exists()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["scientific_status"] == (
        "DEMO_DIAGNOSTIC_NOT_BENCHMARK"
    )
    with pytest.raises(ValueError):
        tester.cleanup_temporary_clip(tmp_path, retained)


def _synthetic_temporal_capture(tmp_path, monkeypatch, timestamps_ns, *, fail_at=None):
    written = []
    observed = {}

    class FakeCamera:
        def read(self):
            index = observed.get("reads", 0)
            observed["reads"] = index + 1
            if index == fail_at or index >= len(timestamps_ns):
                return False, None
            return True, np.full((480, 640, 3), index, dtype=np.uint8)

    class FakeWriter:
        def isOpened(self):
            return True

        def write(self, frame):
            written.append(int(frame[0, 0, 0]))

        def release(self):
            observed["released"] = True
            Path(observed["path"]).write_bytes(b"synthetic mp4")

    def writer_factory(path, fourcc, fps, size):
        observed.update(path=path, fps=fps, size=size)
        return FakeWriter()

    monkeypatch.setattr(tester.cv2, "VideoWriter", writer_factory)
    monkeypatch.setattr(tester.cv2, "VideoWriter_fourcc", lambda *letters: "mp4v")
    ticks = iter(timestamps_ns)
    path = tmp_path / "data/processed/live_tester/tmp/test.mp4"
    path.parent.mkdir(parents=True)
    return FakeCamera(), path, lambda: next(ticks), written, observed


def test_recorder_normalizes_valid_capture_and_records_real_timestamps(
    tmp_path, monkeypatch
):
    timestamps = [round(index * 1_000_000_000 / 30) for index in range(121)]
    camera, path, clock, written, observed = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps
    )
    report = tester.record_clip(camera, path, clock_ns=clock)
    assert report["technical_decision"] == "PASS"
    assert report["source_frame_count"] == 121
    assert report["output_frame_count"] == 121
    assert report["source_timestamps_relative_ns"] == timestamps
    assert report["source_fps_effective"] == pytest.approx(30.0)
    assert len(written) == 121
    assert written[0] == 0 and written[-1] == 120
    assert observed["fps"] == 30 and observed["size"] == (640, 480)
    assert observed["released"] is True
    assert path.is_file()
    tester.cleanup_temporary_clip(tmp_path, path)
    assert not path.exists()
    assert not tester.temporal.sidecar_path(path).exists()


def test_cleanup_preserves_sidecar_replaced_after_capture(tmp_path, monkeypatch):
    timestamps = [round(index * 1_000_000_000 / 30) for index in range(121)]
    camera, path, clock, _, _ = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps
    )
    tester.record_clip(camera, path, clock_ns=clock)
    sidecar = tester.temporal.sidecar_path(path)
    sidecar.rename(sidecar.with_suffix(".original"))
    sidecar.write_bytes(b"different attempt")
    tester.cleanup_temporary_clip(tmp_path, path)
    assert not path.exists()
    assert sidecar.read_bytes() == b"different attempt"


def test_failed_new_attempt_cannot_cleanup_prior_attempt(tmp_path, monkeypatch):
    timestamps = [round(index * 1_000_000_000 / 30) for index in range(121)]
    camera, path, clock, _, _ = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps
    )
    tester.record_clip(camera, path, clock_ns=clock)
    original_video = path.read_bytes()
    sidecar = tester.temporal.sidecar_path(path)
    original_sidecar = sidecar.read_bytes()
    with pytest.raises(FileExistsError):
        tester.record_clip(camera, path, clock_ns=clock)
    tester.cleanup_temporary_clip(tmp_path, path)
    assert path.read_bytes() == original_video
    assert sidecar.read_bytes() == original_sidecar


def test_colliding_thread_cannot_invalidate_owners_cleanup(tmp_path, monkeypatch):
    timestamps = [round(index * 1_000_000_000 / 30) for index in range(121)]
    camera, path, clock, _, _ = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps
    )
    tester.record_clip(camera, path, clock_ns=clock)

    def competing_attempt():
        try:
            tester.record_clip(camera, path, clock_ns=clock)
        except FileExistsError:
            tester.cleanup_temporary_clip(tmp_path, path)

    thread = Thread(target=competing_attempt)
    thread.start()
    thread.join()
    assert path.exists()
    tester.cleanup_temporary_clip(tmp_path, path)
    assert not path.exists()


@pytest.mark.parametrize(
    ("timestamps", "expected_failure"),
    [
        ([index * 50_000_000 for index in range(81)], "source_fps_below_minimum"),
        (
            [
                index * 33_333_334 + (120_000_000 if index >= 60 else 0)
                for index in range(121)
            ],
            "source_gap_above_maximum",
        ),
    ],
)
def test_recorder_blocks_bad_cadence_before_writing(
    tmp_path, monkeypatch, timestamps, expected_failure
):
    camera, path, clock, written, _ = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps
    )
    with pytest.raises(tester.TemporalCaptureError, match=expected_failure):
        tester.record_clip(camera, path, clock_ns=clock)
    assert written == []
    assert not path.exists()


def test_recorder_reports_read_timing_and_policy_timestamps_on_block(
    tmp_path, monkeypatch
):
    timestamps = [index * 50_000_000 for index in range(81)]
    camera, path, clock, _, _ = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps
    )
    events = []
    with pytest.raises(tester.TemporalCaptureError, match="source_fps_below_minimum"):
        tester.record_clip(
            camera, path, clock_ns=clock, diagnostic_callback=events.append
        )
    reads = [event for event in events if event["kind"] == "read"]
    assert len(reads) == 81
    assert [event["policy_timestamp_ns"] for event in reads] == timestamps
    assert [event["frame_index"] for event in reads] == list(range(81))
    assert all(
        event["read_start_ns"]
        <= event["read_end_ns"]
        <= event["copy_end_ns"]
        <= event["ui_update_end_ns"]
        for event in reads
    )
    assert events[-1]["kind"] == "gate"
    assert events[-1]["technical_decision"] == "BLOCKED"
    assert "source_fps_below_minimum" in events[-1]["technical_failures"]
    assert not path.exists()


def test_recorder_diagnostic_keeps_failed_and_invalid_reads(tmp_path, monkeypatch):
    timestamps = [index * 33_333_334 for index in range(121)]
    camera, path, clock, _, _ = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps, fail_at=0
    )
    events = []
    with pytest.raises(tester.TemporalCaptureError, match="Falha de leitura"):
        tester.record_clip(
            camera, path, clock_ns=clock, diagnostic_callback=events.append
        )
    assert len(events) == 1
    assert events[0]["read_status"] == "READ_FAILURE"
    assert events[0]["policy_timestamp_ns"] is None
    assert events[0]["read_start_ns"] <= events[0]["read_end_ns"]

    class InvalidCamera:
        def read(self):
            return True, np.zeros((10, 10, 3), dtype=np.uint8)

    events = []
    with pytest.raises(tester.TemporalCaptureError, match="BGR 640×480"):
        tester.record_clip(
            InvalidCamera(),
            path,
            clock_ns=lambda: 123,
            diagnostic_callback=events.append,
        )
    assert len(events) == 1
    assert events[0]["read_status"] == "INVALID_FRAME_SHAPE"
    assert events[0]["policy_timestamp_ns"] is None


@pytest.mark.parametrize("fail_at", [0, 20])
def test_recorder_blocks_empty_or_interrupted_capture_before_writing(
    tmp_path, monkeypatch, fail_at
):
    timestamps = [index * 33_333_334 for index in range(121)]
    camera, path, clock, written, _ = _synthetic_temporal_capture(
        tmp_path, monkeypatch, timestamps, fail_at=fail_at
    )
    with pytest.raises(tester.TemporalCaptureError):
        tester.record_clip(camera, path, clock_ns=clock)
    assert written == []
    assert not path.exists()


def test_temporal_failure_shows_error_allows_manual_retry_and_never_infers(
    tmp_path, monkeypatch
):
    state = {"error_visible": False, "camera_released": False}

    class FakeCamera:
        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            state["camera_released"] = True

    def show(image, lines, *, compact):
        if any("Erro técnico" in line for line in lines):
            state["error_visible"] = True

    monkeypatch.setattr(tester, "verify_frozen_sources", lambda root: {})
    monkeypatch.setattr(tester, "load_live_pipeline", lambda root: object())
    monkeypatch.setattr(tester, "open_camera", lambda index: FakeCamera())
    monkeypatch.setattr(tester, "_show_overlay", show)
    monkeypatch.setattr(tester, "_countdown", lambda camera: None)
    monkeypatch.setattr(
        tester,
        "record_clip",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            tester.TemporalCaptureError("source_fps_below_minimum")
        ),
    )
    monkeypatch.setattr(
        tester,
        "infer_clip",
        lambda *args, **kwargs: pytest.fail("Captura inválida chegou à inferência."),
    )
    monkeypatch.setattr(tester.cv2, "namedWindow", lambda *args: None)
    monkeypatch.setattr(tester.cv2, "destroyWindow", lambda *args: None)
    monkeypatch.setattr(
        tester.cv2,
        "waitKey",
        lambda delay: 27 if state["error_visible"] else 32,
    )
    result = tester.run_live_session(tmp_path)
    assert result["summary"]["total"] == 0
    assert state == {"error_visible": True, "camera_released": True}


def test_valid_temporal_capture_continues_to_original_r4_path(tmp_path, monkeypatch):
    state = {"infer_count": 0, "camera_released": False, "keys": 0}

    class FakeCamera:
        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            state["camera_released"] = True

    report = {
        "technical_decision": "PASS",
        "source_frame_count": 121,
        "output_frame_count": 121,
        "source_timestamps_relative_ns": [0, 4_000_000_000],
    }

    def infer(pipeline, path, sample_id, session_id, *, root):
        state["infer_count"] += 1
        return {
            "sample_id": sample_id,
            "predicted_label": "SIM",
            "second_best_label": None,
            "score": 0.75,
            "threshold": R4_THRESHOLD,
            "decision": "ACCEPT",
            "emitted_label": "SIM",
            "segmentation_status": "DETECTED",
            "segmentation_fallback": False,
            "source_frame_count": 121,
            "end_to_end_latency_ms": 10.0,
        }

    def key(delay):
        state["keys"] += 1
        return 32 if state["keys"] == 1 else 27

    monkeypatch.setattr(tester, "verify_frozen_sources", lambda root: {})
    monkeypatch.setattr(tester, "load_live_pipeline", lambda root: object())
    monkeypatch.setattr(tester, "open_camera", lambda index: FakeCamera())
    monkeypatch.setattr(tester, "_show_overlay", lambda *args, **kwargs: None)
    monkeypatch.setattr(tester, "_countdown", lambda camera: None)
    monkeypatch.setattr(tester, "record_clip", lambda *args, **kwargs: report)
    monkeypatch.setattr(tester, "infer_clip", infer)
    monkeypatch.setattr(tester.cv2, "namedWindow", lambda *args: None)
    monkeypatch.setattr(tester.cv2, "destroyWindow", lambda *args: None)
    monkeypatch.setattr(tester.cv2, "waitKey", key)
    result = tester.run_live_session(tmp_path)
    assert result["summary"]["total"] == 1
    assert result["summary"]["accepted"] == 1
    assert state["infer_count"] == 1 and state["camera_released"] is True
    log = next((tmp_path / "data/processed/live_tester/logs").glob("*.jsonl"))
    record = json.loads(log.read_text(encoding="utf-8"))
    assert record["capture_timing"] == report


def test_manual_retry_after_temporal_failure_runs_only_second_inference(
    tmp_path, monkeypatch
):
    state = {"records": 0, "inferences": 0, "keys": 0}

    class FakeCamera:
        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            state["released"] = True

    def record(camera, path, **kwargs):
        state["records"] += 1
        if state["records"] == 1:
            raise tester.TemporalCaptureError("source_fps_below_minimum")
        return {"technical_decision": "PASS", "output_frame_count": 121}

    def infer(pipeline, path, sample_id, session_id, *, root):
        state["inferences"] += 1
        return {
            "sample_id": sample_id,
            "predicted_label": "SIM",
            "score": 0.75,
            "threshold": R4_THRESHOLD,
            "decision": "ACCEPT",
            "emitted_label": "SIM",
            "segmentation_status": "DETECTED",
            "segmentation_fallback": False,
            "source_frame_count": 121,
            "end_to_end_latency_ms": 10.0,
        }

    def key(delay):
        state["keys"] += 1
        return {1: 32, 2: 32, 3: -1, 4: 27}[state["keys"]]

    monkeypatch.setattr(tester, "verify_frozen_sources", lambda root: {})
    monkeypatch.setattr(tester, "load_live_pipeline", lambda root: object())
    monkeypatch.setattr(tester, "open_camera", lambda index: FakeCamera())
    monkeypatch.setattr(tester, "_show_overlay", lambda *args, **kwargs: None)
    monkeypatch.setattr(tester, "_countdown", lambda camera: None)
    monkeypatch.setattr(tester, "record_clip", record)
    monkeypatch.setattr(tester, "infer_clip", infer)
    monkeypatch.setattr(tester.cv2, "namedWindow", lambda *args: None)
    monkeypatch.setattr(tester.cv2, "destroyWindow", lambda *args: None)
    monkeypatch.setattr(tester.cv2, "waitKey", key)
    result = tester.run_live_session(tmp_path)
    assert result["summary"]["total"] == 1
    assert state == {"records": 2, "inferences": 1, "keys": 4, "released": True}


def test_camera_check_reads_one_frame_and_releases_without_writer(monkeypatch):
    state = {"reads": 0, "released": False}

    class FakeCamera:
        def isOpened(self):
            return True

        def set(self, prop, value):
            return True

        def read(self):
            state["reads"] += 1
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            state["released"] = True

    monkeypatch.setattr(tester.cv2, "VideoCapture", lambda index, backend: FakeCamera())
    monkeypatch.setattr(
        tester.cv2,
        "VideoWriter",
        lambda *args: pytest.fail("O modo --check não grava vídeo."),
    )
    tester.check_camera(1)
    assert state == {"reads": 1, "released": True}


def test_window_failure_releases_camera(tmp_path, monkeypatch):
    state = {"released": False}

    class FakeCamera:
        def release(self):
            state["released"] = True

    monkeypatch.setattr(tester, "verify_frozen_sources", lambda root: {})
    monkeypatch.setattr(tester, "load_live_pipeline", lambda root: object())
    monkeypatch.setattr(tester, "open_camera", lambda index: FakeCamera())
    monkeypatch.setattr(
        tester.cv2,
        "namedWindow",
        lambda *args: (_ for _ in ()).throw(RuntimeError("sem GUI")),
    )
    with pytest.raises(RuntimeError, match="sem GUI"):
        tester.run_live_session(tmp_path)
    assert state["released"] is True


def test_retained_clip_is_marked_even_if_inference_fails(tmp_path, monkeypatch):
    state = {"released": False}

    class FakeCamera:
        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self):
            state["released"] = True

    def fake_record(camera, path, **kwargs):
        path.write_bytes(b"synthetic mp4")
        return {"output_frame_count": 121}

    def fail_inference(*args, **kwargs):
        raise RuntimeError("falha técnica sintética")

    monkeypatch.setattr(tester, "verify_frozen_sources", lambda root: {})
    monkeypatch.setattr(tester, "load_live_pipeline", lambda root: object())
    monkeypatch.setattr(tester, "open_camera", lambda index: FakeCamera())
    monkeypatch.setattr(tester, "_show_overlay", lambda *args, **kwargs: None)
    monkeypatch.setattr(tester, "_countdown", lambda camera: None)
    monkeypatch.setattr(tester, "record_clip", fake_record)
    monkeypatch.setattr(tester, "infer_clip", fail_inference)
    monkeypatch.setattr(tester.cv2, "namedWindow", lambda *args: None)
    monkeypatch.setattr(tester.cv2, "destroyWindow", lambda *args: None)
    monkeypatch.setattr(tester.cv2, "waitKey", lambda delay: 32)
    with pytest.raises(RuntimeError, match="falha técnica sintética"):
        tester.run_live_session(tmp_path, keep_clips=True)
    clips = list((tmp_path / "data/processed/live_tester/clips").glob("*.mp4"))
    assert len(clips) == 1
    sidecar = clips[0].with_suffix(".json")
    assert json.loads(sidecar.read_text(encoding="utf-8"))["scientific_status"] == (
        "DEMO_DIAGNOSTIC_NOT_BENCHMARK"
    )
    assert state["released"] is True


def test_preview_text_does_not_cover_camera_frame(monkeypatch):
    displayed = {}
    frame = np.full((480, 640, 3), 123, dtype=np.uint8)
    monkeypatch.setattr(
        tester.cv2,
        "imshow",
        lambda title, image: displayed.update(title=title, image=image.copy()),
    )
    tester._show_overlay(frame, ["Predição visual: SIM"] * 12, compact=False)
    assert displayed["image"].shape[0] == 480
    assert displayed["image"].shape[1] > 640
    np.testing.assert_array_equal(displayed["image"][:, :640], frame)
