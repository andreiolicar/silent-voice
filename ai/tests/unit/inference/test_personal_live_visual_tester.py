"""Contratos sintéticos do perfil TWO-SHOT do Live Tester."""

import json

import numpy as np
import pytest

from silent_voice.inference import personal_live_visual_tester as personal


SOURCES = {"freeze_sha256": "a" * 64, "artifact_sha256": {"encoder": "b" * 64}}
LABELS = ("SIM", "NÃO", "AJUDA", "ÁGUA", "BANHEIRO", "PARAR")


def feature(label_index: int, repetition: int):
    clip = np.zeros(1664, dtype=np.float32)
    clip[label_index] = 1.0
    clip[6 + repetition] = 0.1
    temporal = np.ones((30, 160), dtype=np.float32) * (label_index + repetition)
    return clip, temporal


def fill(store):
    for index, label in enumerate(LABELS):
        for repetition in (1, 2):
            store.save_example(label, repetition, *feature(index, repetition), SOURCES)


def test_exact_two_shot_progress_and_label_membership(tmp_path):
    store = personal.LocalProfileStore(tmp_path)
    assert store.progress() == {label: 0 for label in LABELS}
    for index, label in enumerate(LABELS):
        store.save_example(label, 1, *feature(index, 1), SOURCES)
    assert sum(store.progress().values()) == 6
    with pytest.raises(ValueError, match="12 exemplos"):
        store.build(SOURCES)
    for index, label in enumerate(LABELS):
        store.save_example(label, 2, *feature(index, 2), SOURCES)
    assert store.progress() == {label: 2 for label in LABELS}
    assert store.total() == 12
    with pytest.raises(ValueError, match="Palavra"):
        store.save_example("LEITE", 1, *feature(0, 1), SOURCES)


def test_invalid_capture_not_counted_and_rerecord_invalidates_head(tmp_path):
    store = personal.LocalProfileStore(tmp_path)
    clip, temporal = feature(0, 1)
    with pytest.raises(ValueError, match="feature"):
        store.save_example("SIM", 1, clip[:10], temporal, SOURCES)
    assert store.total() == 0
    fill(store)
    store.build(SOURCES)
    assert store.load(SOURCES) is not None
    changed = clip.copy()
    changed[12] = 0.2
    store.save_example("SIM", 1, changed, temporal, SOURCES)
    assert store.total() == 12
    assert store.load(SOURCES) is None
    with np.load(store.example_path("SIM", 1), allow_pickle=False) as archive:
        assert np.array_equal(archive["clip_embedding"], changed)


def test_historical_head_fit_compatible_load_and_delete(tmp_path, monkeypatch):
    store = personal.LocalProfileStore(tmp_path)
    fill(store)
    historical = personal.fit_lightweight_personal_head
    calls = []

    def observed(features):
        calls.append(tuple(item.label for item in features))
        return historical(features)

    monkeypatch.setattr(personal, "fit_lightweight_personal_head", observed)
    model = store.build(SOURCES)
    assert calls == [tuple(label for label in LABELS for _ in (1, 2))]
    assert model.in_features == 1664 and model.out_features == 6
    loaded = store.load(SOURCES)
    assert loaded is not None
    assert np.array_equal(loaded.weight.detach().numpy(), model.weight.detach().numpy())
    assert store.manifest_path.exists()
    manifest = json.loads(store.manifest_path.read_text(encoding="utf-8"))
    assert manifest["candidate_id"] == "LIGHTWEIGHT_PERSONAL_HEAD__2SHOT"
    assert manifest["class_order"] == list(LABELS)
    assert manifest["example_count"] == 12
    store.delete()
    assert store.total() == 0
    assert store.load(SOURCES) is None


def test_incompatible_sources_and_tampered_head_are_rejected(tmp_path):
    store = personal.LocalProfileStore(tmp_path)
    fill(store)
    store.build(SOURCES)
    with pytest.raises(ValueError, match="incompatível"):
        store.load(
            {"freeze_sha256": "c" * 64, "artifact_sha256": SOURCES["artifact_sha256"]}
        )
    store.head_path.write_bytes(b"alterado")
    with pytest.raises(ValueError, match="SHA"):
        store.load(SOURCES)


def test_personal_pipeline_uses_head_class_with_global_r4_scorer(monkeypatch):
    class Session:
        def __init__(self):
            self.calls = []

        def run(self, unused, inputs):
            self.calls.append(inputs)
            if "roi_input" in inputs:
                clip, _ = feature(3, 1)
                return [clip[None, :]]
            return [np.array([0.9], dtype=np.float32)]

    class Base:
        encoder = Session()
        scorer = Session()

    class Prepared:
        query = object()
        tensor = np.zeros((1, 1, 29, 88, 88), dtype=np.float32)
        diagnostics = {"segmentation_fallback": False, "source_frame_count": 121}

    monkeypatch.setattr(personal, "decode_query", lambda path: object())
    monkeypatch.setattr(personal, "prepare_decoded_query", lambda *a, **k: Prepared())
    monkeypatch.setattr(
        personal, "predict_personal_head", lambda model, clip: (3, np.zeros(6))
    )
    pipeline = personal.PersonalizedPipeline(Base(), personal.torch.nn.Linear(1664, 6))
    result = pipeline.infer_clip("synthetic.mp4", "sample", "session")
    assert result["predicted_label"] == "ÁGUA"
    assert result["decision"] == "ACCEPT"
    assert result["emitted_label"] == "ÁGUA"
    assert Base.scorer.calls[-1]["predicted_label_index"].tolist() == [3]


def test_safe_reject_does_not_emit_word_or_call_scorer(monkeypatch):
    class Base:
        encoder = object()
        scorer = object()

    class Prepared:
        query = None
        tensor = None
        diagnostics = {
            "landmark_gap_action": "SAFE_REJECT_INSUFFICIENT_VISUAL_EVIDENCE",
            "source_frame_count": 121,
            "segmentation_fallback": False,
        }

    monkeypatch.setattr(personal, "decode_query", lambda path: object())
    monkeypatch.setattr(personal, "prepare_decoded_query", lambda *a, **k: Prepared())
    result = personal.PersonalizedPipeline(
        Base(), personal.torch.nn.Linear(1664, 6)
    ).infer_clip("synthetic.mp4", "sample", "session")
    assert result["decision"] == "REJECT"
    assert result["emitted_label"] is None
    assert result["score"] is None
    assert result["technical_reason"]


def test_profile_path_cannot_leave_local_area(tmp_path):
    with pytest.raises(ValueError, match="Identidade"):
        personal.LocalProfileStore(tmp_path, profile_id="../outside")


def test_selected_profile_keeps_default_examples_unchanged(tmp_path):
    default = personal.LocalProfileStore(tmp_path)
    selected = personal.LocalProfileStore(tmp_path, profile_id="synthetic_profile")
    default.save_example("SIM", 1, *feature(0, 1), SOURCES)
    original = default.example_path("SIM", 1).read_bytes()
    selected.save_example("SIM", 1, *feature(0, 2), SOURCES)
    assert default.example_path("SIM", 1).read_bytes() == original
    assert default.total() == 1
    assert selected.total() == 1
    assert selected.example_path("SIM", 1) != default.example_path("SIM", 1)


def test_redirected_profile_folder_is_rejected(tmp_path, monkeypatch):
    original_resolve = personal.Path.resolve

    def redirected(path, *args, **kwargs):
        if path.name == "synthetic_profile":
            return path.with_name("local_default")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(personal.Path, "resolve", redirected)
    with pytest.raises(ValueError, match="redirecionada"):
        personal.LocalProfileStore(tmp_path, profile_id="synthetic_profile")


def test_delete_removes_only_known_pending_profile_file(tmp_path):
    store = personal.LocalProfileStore(tmp_path)
    store.save_example("SIM", 1, *feature(0, 1), SOURCES)
    pending = store.example_path("SIM", 1).with_name("example_0_1.npz.pending")
    pending.write_bytes(b"interrupted")
    store.delete()
    assert not store.folder.exists()


def test_enrollment_temporal_failure_never_counts_or_extracts(tmp_path, monkeypatch):
    store = personal.LocalProfileStore(tmp_path)
    events = []
    video = tmp_path / "data" / "processed" / "live_tester" / "tmp" / "trial.mp4"
    monkeypatch.setattr(personal.legacy, "clip_path", lambda *a, **k: video)
    monkeypatch.setattr(
        personal.legacy,
        "record_clip",
        lambda *a, **k: {"technical_decision": "BLOCKED"},
    )
    monkeypatch.setattr(
        personal,
        "extract_enrollment_feature",
        lambda *a: pytest.fail("Extração iniciou após gate inválido."),
    )
    monkeypatch.setattr(
        personal.legacy,
        "cleanup_temporary_clip",
        lambda *a: events.append("cleanup"),
    )
    with pytest.raises(personal.legacy.TemporalCaptureError):
        personal.record_enrollment(
            tmp_path, object(), object(), store, SOURCES, "SIM", 1, "session", 1
        )
    assert store.total() == 0
    assert events == ["cleanup"]


def test_enrollment_valid_capture_writes_only_features(tmp_path, monkeypatch):
    store = personal.LocalProfileStore(tmp_path)
    video = tmp_path / "data" / "processed" / "live_tester" / "tmp" / "trial.mp4"
    monkeypatch.setattr(personal.legacy, "clip_path", lambda *a, **k: video)
    monkeypatch.setattr(
        personal.legacy,
        "record_clip",
        lambda *a, **k: {"technical_decision": "PASS"},
    )
    monkeypatch.setattr(
        personal, "extract_enrollment_feature", lambda *a: feature(0, 1)
    )
    monkeypatch.setattr(personal.legacy, "cleanup_temporary_clip", lambda *a: None)
    personal.record_enrollment(
        tmp_path, object(), object(), store, SOURCES, "SIM", 1, "session", 1
    )
    assert store.total() == 1
    assert store.example_path("SIM", 1).exists()
    assert not video.exists()
