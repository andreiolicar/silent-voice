"""Plano cego, determinístico e pré-registrado do held-out R3.6."""

import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath


SESSION_IDS = (
    "r3_heldout_session_01",
    "r3_heldout_session_02",
    "r3_heldout_session_03",
)
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
    "ACORDAR",
    "CAFÉ",
    "ESCOLA",
    "DEPOIS",
    "FAMÍLIA",
    "TELEFONE",
    "TRABALHO",
    "JANELA",
    "CAMISA",
    "SAPATO",
    "LIVRO",
    "CHUVA",
    "RUA",
    "NOITE",
    "DINHEIRO",
    "MERCADO",
    "PESSOA",
    "AMIGO",
    "DORMIR",
    "CADERNO",
    "PORTA",
    "TEMPO",
    "BONITO",
    "RÁPIDO",
)
HISTORICAL_OOV_PROMPTS = ("CASA", "COMIDA", "HOJE", "MÃE", "OBRIGADO", "QUERO")
EDGE_FREEZE_SHA256 = "1a67bcc8890d3f2f4e93f2346844d38a89db1de4448e0855cdb66d0b64af54ff"
CYCLE_6_PLAN_SHA256 = "cd0d54815acd4b1a67d3b0bb483bc80a4165c990656783be0fa99aeff3889cd7"
PLAN_PATH = Path("docs/cycles/rejection_3_heldout_capture_plan.json")
RAW_ROOT = "data/raw/rejection_3_heldout"
ACTION_DEFINITIONS = {
    "BOCA_PARADA": "Rosto visível e boca neutra, sem fala intencional.",
    "SORRISO": "Sorria naturalmente uma vez, sem articular palavra.",
    "ABRE_FECHA": "Abra e feche a boca de modo não linguístico, sem formar palavra.",
    "MOV_CABECA": (
        "Mova a cabeça naturalmente para o lado e/ou levemente na vertical; "
        "boca neutra."
    ),
    "MOV_BOCA_ALEATORIO": (
        "Faça movimentos variados e não linguísticos da boca, sem formar "
        "palavra conhecida."
    ),
    "FALA_FORA_VOCAB": "Articule uma vez a palavra OOV indicada nesta linha.",
}
RECAPTURE_REASONS = (
    "arquivo_nao_salvo",
    "camera_desconectada",
    "gravacao_interrompida",
    "prompt_errado",
    "acao_nao_executada",
    "interferencia_externa",
    "arquivo_corrompido_indecodavel",
)
CAPTURE_RECORD_FIELDS = (
    "sample_id",
    "session_id",
    "trial_order",
    "prompt_or_action",
    "output_path",
    "capture_timestamp_utc",
    "attempt_number",
    "recapture_reason",
    "capture_configuration",
)


def _slug(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower().replace(" ", "_")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def selected_oov_prompts() -> list[dict]:
    """Escolhe seis prompts sem sorteio nem intervenção manual."""
    seed = f"R3.6|{EDGE_FREEZE_SHA256}"
    ranked = sorted((_sha256(f"{seed}|{word}"), word) for word in OOV_POOL)
    return [
        {
            "prompt_display": word,
            "prompt_id": _slug(word),
            "selection_hash": digest,
            "selection_rank": index,
            "session_id": SESSION_IDS[(index - 1) // 2],
        }
        for index, (digest, word) in enumerate(ranked[:6], start=1)
    ]


def canonical_trial_descriptor(row: dict) -> str:
    """Identidade estável, independente da posição sorteada."""
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


def _row(session_id: str, kind: str, name: str, repetition: int, oov: dict | None):
    session_folder = session_id.removeprefix("r3_heldout_")
    name_slug = _slug(name)
    suffix = f"_{oov['prompt_id']}" if oov else ""
    sample_id = f"r3_{name_slug}_{session_folder}_{repetition:03d}{suffix}"
    action = (
        name
        if kind == "KNOWN"
        else (
            f"Articule uma vez: {oov['prompt_display']}"
            if oov
            else ACTION_DEFINITIONS[name]
        )
    )
    row = {
        "sample_id": sample_id,
        "session_id": session_id,
        "sample_kind": kind,
        "expected_label": name if kind == "KNOWN" else "UNKNOWN",
        "negative_category": name if kind == "UNKNOWN" else None,
        "repetition_index": repetition,
        "oov_prompt": oov,
        "prompt_or_action": action,
        "raw_video_path": (
            f"{RAW_ROOT}/{session_folder}/{_slug(name).upper()}/{sample_id}.mp4"
        ),
    }
    row["order_hash"] = _sha256(
        f"{EDGE_FREEZE_SHA256}|R3.6_ORDER|{session_id}|"
        f"{canonical_trial_descriptor(row)}"
    )
    return row


def build_capture_plan() -> dict:
    """Constrói todo o contrato sem ler vídeos, scores ou outros held-outs."""
    prompts = selected_oov_prompts()
    sessions = []
    for session_id in SESSION_IDS:
        assigned = [prompt for prompt in prompts if prompt["session_id"] == session_id]
        rows = [
            _row(session_id, "KNOWN", label, repetition, None)
            for label in KNOWN_LABELS
            for repetition in (1, 2)
        ]
        rows.extend(
            _row(
                session_id,
                "UNKNOWN",
                category,
                repetition,
                assigned[repetition - 1] if category == "FALA_FORA_VOCAB" else None,
            )
            for category in UNKNOWN_CATEGORIES
            for repetition in (1, 2)
        )
        rows.sort(key=lambda row: row["order_hash"])
        for order, row in enumerate(rows, start=1):
            row["order"] = order
        sessions.append({"session_id": session_id, "schedule": rows})
    return {
        "format_version": 1,
        "state": "REJECTION_3_HELDOUT_CAPTURE_PROTOCOL_FROZEN",
        "source_edge_freeze_sha256": EDGE_FREEZE_SHA256,
        "source_cycle_6_capture_plan_sha256": CYCLE_6_PLAN_SHA256,
        "purpose": "SAME_SPEAKER_NEW_SESSION_GENERALIZATION",
        "speaker_scope": "Mesmo participante de sessao_01–03; parar se indisponível.",
        "session_gap_seconds_minimum": 1200,
        "session_reset": [
            "encerrar a captura anterior",
            "levantar e sair da posição",
            "reiniciar captura/Iriun quando aplicável",
            "retornar e reposicionar naturalmente",
            "manter dispositivo e configuração nominal; "
            "evitar enquadramento pixel-perfect",
        ],
        "device": {
            "phone": "iPhone 17",
            "camera_facing": "FRONT",
            "workflow": "Iriun/OpenCV",
            "opencv_camera_index": 1,
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
            "framing": (
                "Boca e face visíveis; distância e enquadramento natural "
                "equivalentes a sessao_01–03."
            ),
            "articulation": (
                "Natural, sem exagero deliberado; repouso antes e depois "
                "de uma ação por clipe."
            ),
            "environment": (
                "Interno controlado, iluminação utilizável, sem condições "
                "extremas deliberadas."
            ),
        },
        "counts": {
            "sessions": 3,
            "per_session": 24,
            "total": 72,
            "known_per_session": 12,
            "unknown_per_session": 12,
            "known_total": 36,
            "unknown_total": 36,
            "repetitions_per_label_or_category_per_session": 2,
        },
        "known_labels": list(KNOWN_LABELS),
        "unknown_categories": list(UNKNOWN_CATEGORIES),
        "unknown_action_definitions": ACTION_DEFINITIONS,
        "historical_oov_excluded": list(HISTORICAL_OOV_PROMPTS),
        "oov_pool": list(OOV_POOL),
        "oov_selection": {
            "seed_material": f"R3.6|{EDGE_FREEZE_SHA256}",
            "hash_expression": "SHA256(UTF8(seed_material + '|' + prompt_display))",
            "ordering": (
                "hash hexadecimal ascendente; primeiras seis; "
                "pares para sessões 01, 02 e 03"
            ),
        },
        "selected_oov_prompts": prompts,
        "trial_ordering": {
            "hash_expression": (
                "SHA256(UTF8(edge_freeze_sha + '|R3.6_ORDER|' + "
                "session_id + '|' + canonical_trial_descriptor))"
            ),
            "descriptor_format": (
                "JSON compacto UTF-8 [session_id,type,label_or_category,"
                "repetition,oov_prompt_or_null]"
            ),
            "ordering": "hash hexadecimal ascendente, sem rearranjo manual",
        },
        "recapture_policy": {
            "allowed_reasons": list(RECAPTURE_REASONS),
            "forbidden": [
                "aparência ou dificuldade percebida",
                "score, cosine ou proximidade do threshold",
                "prediction, confidence ou rejection",
                "qualquer saída de modelo",
            ],
            "audit": (
                "Preservar tentativa anterior; registrar sample_id, motivo, "
                "tentativa descartada e final antes de inferência."
            ),
        },
        "technical_qc": {
            "allowed": [
                "existência e inventário exato",
                "sample_id e path únicos",
                "tamanho não nulo",
                "contêiner decodificável",
                "codec mp4v/FMP4",
                "640x480",
                "FPS nominal 30",
                "frame_count declarado >= 3",
                "frames primeiro/meio/último decodificáveis e contagem coincidente",
                "duração positiva calculada por frame_count/FPS nominal",
                "timestamps e intervalo >= 1200 segundos entre sessões",
                "manifesto corresponde ao plano e aos arquivos",
            ],
            "duration_rule": (
                "Captura termina por relógio em 4.0 s; não exigir 120 frames "
                "nem intervalo de reprodução inventado."
            ),
            "forbidden": [
                "SwinLip",
                "classificador",
                "ROI ou segmentação semântica",
                "embedding",
                "cos_pred",
                "rejection",
                "label previsto",
            ],
        },
        "capture_manifest": {
            "path": (
                "data/processed/evaluation/" "rejection_3_heldout_capture_manifest.json"
            ),
            "required_sample_fields": list(CAPTURE_RECORD_FIELDS),
            "no_model_output": True,
        },
        "old_heldouts_prohibited": [
            "sessao_04",
            "rejeicao_heldout_01",
            "cycle_06_heldout_session_01",
            "cycle_06_heldout_session_02",
            "cycle_06_final_heldout_evaluation.json",
        ],
        "no_model_inference_before_r3_7": True,
        "sessions": sessions,
    }


def canonical_plan_bytes(plan: dict) -> bytes:
    """Bytes de freeze UTF-8/LF, estáveis em Windows e Git."""
    return (
        json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def plan_sha256(plan: dict) -> str:
    return hashlib.sha256(canonical_plan_bytes(plan)).hexdigest()


PLAN_SHA256 = plan_sha256(build_capture_plan())


def assert_capture_path(path: str | Path) -> PurePosixPath:
    """Restringe I/O aos três diretórios novos, antes de acessar filesystem."""
    normalized = str(path).replace("\\", "/")
    relative = PurePosixPath(normalized)
    parts = relative.parts
    if (
        relative.is_absolute()
        or len(parts) != 6
        or parts[:3] != ("data", "raw", "rejection_3_heldout")
        or parts[3] not in ("session_01", "session_02", "session_03")
        or parts[4]
        not in {_slug(name).upper() for name in (*KNOWN_LABELS, *UNKNOWN_CATEGORIES)}
        or not parts[5].startswith("r3_")
        or relative.suffix != ".mp4"
        or any(part in (".", "..") for part in normalized.split("/"))
        or ":" in normalized
    ):
        raise ValueError("Path fora do novo held-out autorizado.")
    return relative


def validate_capture_plan(plan: dict) -> None:
    """Confere todo o plano, inclusive paths, contagens, prompts e ordem."""
    if plan != build_capture_plan():
        raise ValueError("Plano R3.6 diverge do contrato pré-registrado.")
    rows = [row for session in plan["sessions"] for row in session["schedule"]]
    ids = [row["sample_id"] for row in rows]
    paths = [row["raw_video_path"] for row in rows]
    if len(rows) != len(set(ids)) or len(rows) != len(set(paths)):
        raise ValueError("Sample ID ou path duplicado.")
    if Counter(row["sample_kind"] for row in rows) != {"KNOWN": 36, "UNKNOWN": 36}:
        raise ValueError("Distribuição KNOWN/UNKNOWN inválida.")
    for row in rows:
        assert_capture_path(row["raw_video_path"])


def load_capture_plan(path: Path = PLAN_PATH) -> dict:
    """Valida SHA canônico antes de aceitar um plano em disco."""
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in raw or hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise ValueError("SHA-256 do plano R3.6 divergiu.")
    plan = json.loads(raw.decode("utf-8"))
    validate_capture_plan(plan)
    return plan
