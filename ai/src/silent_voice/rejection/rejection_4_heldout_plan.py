"""Plano determinístico e cego do novo held-out independente R4.7A."""

import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath

from silent_voice.rejection.rejection_3_heldout_plan import ACTION_DEFINITIONS


SESSION_IDS = tuple(f"r4_heldout_session_{index:02d}" for index in range(1, 4))
KNOWN_LABELS = ("SIM", "NÃO", "AJUDA", "ÁGUA", "BANHEIRO", "PARAR")
UNKNOWN_CATEGORIES = (
    "BOCA_PARADA",
    "SORRISO",
    "ABRE_FECHA",
    "MOV_CABECA",
    "MOV_BOCA_ALEATORIO",
    "FALA_FORA_VOCAB",
)
OOV_POOL = (
    "TELEFONE",
    "CHUVA",
    "PESSOA",
    "DORMIR",
    "FAMÍLIA",
    "TRABALHO",
    "RUA",
    "RÁPIDO",
    "ACORDAR",
)
OOV_SEED = "REJECTION_4_FINAL_HELDOUT_OOV_V1"
ORDER_SEED = "R4_FINAL_HELDOUT_ORDER_V1"
PLAN_PATH = Path("docs/cycles/rejection_4_heldout_capture_plan.json")
RAW_ROOT = "data/raw/rejection_4_heldout"
MANIFEST_PATH = "data/processed/evaluation/rejection_4_heldout_capture_manifest.json"
SCIENTIFIC_STATUS = "SAME_SPEAKER_NEW_SESSION"
EDGE_FREEZE_PATH = Path("docs/cycles/rejection_4_edge_policy_freeze.json")
EDGE_FREEZE_SHA256 = "cf9c2976698e515c468567961783aad885dcafba86ec0cbcebaa49c71c6df4e9"
REFERENCE_FREEZE_PATH = Path("docs/cycles/rejection_4_reference_freeze.json")
REFERENCE_FREEZE_SHA256 = (
    "79015c1b7f39ae64027a1a69253ba0411cdb8351a339d0a687d0ec4e75714a3c"
)
FROZEN_POLICY = {
    "candidate": "R4_REFERENCE_BANK_TOP3_GLOBAL",
    "k": 3,
    "threshold": 0.5666271450980487,
    "operator": ">=",
}
LIVE_TESTER_POLICY = "R3"
RECAPTURE_REASONS = (
    "camera_caiu",
    "arquivo_nao_salvo",
    "gravacao_interrompida",
    "prompt_errado",
    "acao_nao_executada",
    "interferencia_externa",
    "arquivo_corrompido",
    "fonte_camera_incorreta",
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug(text: str) -> str:
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .replace(" ", "_")
    )


def selected_oov_prompts() -> list[dict]:
    """Seleciona seis palavras por hash, duas para cada sessão."""
    ranked = sorted((_sha256(f"{OOV_SEED}|{word}"), word) for word in OOV_POOL)
    return [
        {
            "prompt_display": word,
            "prompt_id": _slug(word),
            "selection_hash": digest,
            "selection_rank": rank,
            "session_id": SESSION_IDS[(rank - 1) // 2],
        }
        for rank, (digest, word) in enumerate(ranked[:6], start=1)
    ]


def canonical_trial_descriptor(row: dict) -> str:
    """Identidade estável para a chave de ordenação, sem a ordem final."""
    parts = [
        row["session_id"],
        row["sample_kind"],
        (
            row["expected_label"]
            if row["sample_kind"] == "KNOWN"
            else row["negative_category"]
        ),
        row["repetition_index"],
        row["oov_prompt"]["prompt_display"] if row["oov_prompt"] else None,
    ]
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))


def _trial(session_id: str, kind: str, target: str, repetition: int, oov: dict | None):
    folder = session_id.removeprefix("r4_heldout_")
    suffix = f"_{oov['prompt_id']}" if oov else ""
    sample_id = f"r4h_{_slug(target)}_{folder}_{repetition:03d}{suffix}"
    prompt = (
        f"Articule uma vez: {target}"
        if kind == "KNOWN"
        else (
            f"Articule uma vez: {oov['prompt_display']}"
            if oov
            else ACTION_DEFINITIONS[target]
        )
    )
    row = {
        "sample_id": sample_id,
        "session_id": session_id,
        "sample_kind": kind,
        "expected_label": target if kind == "KNOWN" else "UNKNOWN",
        "negative_category": target if kind == "UNKNOWN" else None,
        "repetition_index": repetition,
        "oov_prompt": oov,
        "prompt_or_action": prompt,
        "raw_video_path": (
            f"{RAW_ROOT}/{folder}/{_slug(target).upper()}/{sample_id}.mp4"
        ),
    }
    row["order_hash"] = _sha256(
        f"{ORDER_SEED}|{session_id}|{canonical_trial_descriptor(row)}"
    )
    return row


def build_capture_plan() -> dict:
    """Constrói o contrato R4 sem abrir datasets ou artefatos de modelo."""
    selected = selected_oov_prompts()
    sessions = []
    for session_id in SESSION_IDS:
        assigned = [row for row in selected if row["session_id"] == session_id]
        rows = [
            _trial(session_id, "KNOWN", label, repetition, None)
            for label in KNOWN_LABELS
            for repetition in range(1, 3)
        ]
        rows.extend(
            _trial(
                session_id,
                "UNKNOWN",
                category,
                repetition,
                assigned[repetition - 1] if category == "FALA_FORA_VOCAB" else None,
            )
            for category in UNKNOWN_CATEGORIES
            for repetition in range(1, 3)
        )
        rows.sort(key=lambda row: row["order_hash"])
        for order, row in enumerate(rows, start=1):
            row["order"] = order
        sessions.append({"session_id": session_id, "schedule": rows})
    return {
        "format_version": 1,
        "state": "REJECTION_4_HELDOUT_CAPTURE_PROTOCOL_FROZEN",
        "purpose": "INDEPENDENT_HELDOUT_AFTER_R4_EDGE_FREEZE",
        "scientific_scope": SCIENTIFIC_STATUS,
        "source_edge_freeze_sha256": EDGE_FREEZE_SHA256,
        "source_reference_freeze_sha256": REFERENCE_FREEZE_SHA256,
        "frozen_policy": FROZEN_POLICY,
        "live_tester_policy": LIVE_TESTER_POLICY,
        "participant_contract": (
            "Mesmo participante principal de sessao_01–03 e do R4 diagnostic; "
            "não substituir participante."
        ),
        "counts": {
            "sessions": 3,
            "per_session": 24,
            "total": 72,
            "known_per_session": 12,
            "unknown_per_session": 12,
            "known_total": 36,
            "unknown_total": 36,
            "repetitions_per_target_per_session": 2,
        },
        "known_labels": list(KNOWN_LABELS),
        "unknown_categories": list(UNKNOWN_CATEGORIES),
        "unknown_action_definitions": {
            name: ACTION_DEFINITIONS[name] for name in UNKNOWN_CATEGORIES
        },
        "oov_pool": list(OOV_POOL),
        "oov_selection": {
            "seed": OOV_SEED,
            "hash_expression": "SHA256(UTF8(seed + '|' + palavra))",
            "rule": "hash hexadecimal ascendente; primeiras seis; duas por sessão",
        },
        "selected_oov_prompts": selected,
        "trial_ordering": {
            "seed": ORDER_SEED,
            "descriptor_format": (
                "JSON compacto UTF-8 [session,type,class_or_category,"
                "repetition,oov_prompt_or_null]"
            ),
            "hash_expression": (
                "SHA256(UTF8(seed + '|' + session_id + '|' + descriptor))"
            ),
            "rule": "hash hexadecimal ascendente; sem rearranjo manual",
        },
        "session_gap_seconds_minimum": 1200,
        "session_reset": [
            "sair da posição e retornar após pelo menos 20 minutos",
            "reiniciar Iriun quando aplicável",
            "reposicionar naturalmente câmera e participante",
            "registrar ambiente e iluminação declarados",
        ],
        "device": {
            "phone": "iPhone 17",
            "camera_facing": "FRONT",
            "workflow": "Iriun/OpenCV",
            "default_camera_index": 1,
            "same_speaker": True,
        },
        "acquisition": {
            "raw_root": RAW_ROOT,
            "width_px": 640,
            "height_px": 480,
            "fps_nominal": 30,
            "recording_clock_seconds": 4.0,
            "container": "MP4",
            "encoder_fourcc_requested": "mp4v",
            "capture_frame_orientation": "LANDSCAPE_4_3",
            "physical_phone_orientation": "NOT_REQUIRED_FOR_PROTOCOL",
            "environment": "Ambiente interno utilizável; sem extremos artificiais.",
            "framing": "Face e boca visíveis; reposicionamento natural entre sessões.",
        },
        "capture_manifest": {
            "path": MANIFEST_PATH,
            "no_model_output": True,
            "ground_truth_from_plan": True,
        },
        "no_model_output": True,
        "recapture_policy": {
            "allowed_reasons": list(RECAPTURE_REASONS),
            "forbidden": [
                "articulação percebida como feia ou difícil",
                "score, prediction ou resultado de modelo",
                "ajuste por desempenho ou threshold",
            ],
            "preserve_previous_attempts": True,
        },
        "no_inference_during_capture": True,
        "next_allowed_operation": "R4.7B — human capture + technical QC",
        "sessions": sessions,
    }


def canonical_plan_bytes(value: dict) -> bytes:
    """Uma linha UTF-8 sem BOM/CRLF, estável com core.autocrlf=true."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def plan_sha256(value: dict) -> str:
    return hashlib.sha256(canonical_plan_bytes(value)).hexdigest()


PLAN_SHA256 = "075b1eba875ea193b0affb55d7f136e70c9b11d062dbff5621dddd92e9c7e1af"


def assert_capture_path(path: str | Path) -> PurePosixPath:
    normalized = str(path).replace("\\", "/")
    relative = PurePosixPath(normalized)
    parts = relative.parts
    if (
        relative.is_absolute()
        or len(parts) != 6
        or parts[:3] != ("data", "raw", "rejection_4_heldout")
        or parts[3] not in ("session_01", "session_02", "session_03")
        or parts[4]
        not in {_slug(name).upper() for name in (*KNOWN_LABELS, *UNKNOWN_CATEGORIES)}
        or not parts[5].startswith("r4h_")
        or relative.suffix != ".mp4"
        or any(part in (".", "..") for part in normalized.split("/"))
        or ":" in normalized
    ):
        raise ValueError("Path fora do novo held-out R4 autorizado.")
    return relative


def validate_capture_plan(value: dict) -> None:
    if value != build_capture_plan():
        raise ValueError("Plano R4.7A divergiu do contrato determinístico.")
    rows = [row for session in value["sessions"] for row in session["schedule"]]
    if (
        len(rows) != 72
        or len({row["sample_id"] for row in rows}) != 72
        or len({row["raw_video_path"] for row in rows}) != 72
        or Counter(row["sample_kind"] for row in rows) != {"KNOWN": 36, "UNKNOWN": 36}
    ):
        raise ValueError("Inventário R4 inválido ou duplicado.")
    for row in rows:
        assert_capture_path(row["raw_video_path"])


def load_capture_plan(path: Path = PLAN_PATH) -> dict:
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in raw or hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise ValueError("SHA-256 do plano R4.7A divergiu.")
    value = json.loads(raw.decode("utf-8"))
    validate_capture_plan(value)
    return value
