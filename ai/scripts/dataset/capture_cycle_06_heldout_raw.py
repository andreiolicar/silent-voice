"""Grava somente MP4 brutos no plano cego do held-out do Cycle 6."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import cv2


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPOSITORY_ROOT / "docs/cycles/cycle_06_new_heldout_capture_plan.json"
PLAN_SHA256 = "cd0d54815acd4b1a67d3b0bb483bc80a4165c990656783be0fa99aeff3889cd7"
SESSION_IDS = ("cycle_06_heldout_session_01", "cycle_06_heldout_session_02")
LABEL_SLUGS = {
    "SIM": "sim",
    "NÃO": "nao",
    "AJUDA": "ajuda",
    "ÁGUA": "agua",
    "BANHEIRO": "banheiro",
    "PARAR": "parar",
}
CATEGORY_SLUGS = {
    "BOCA_PARADA": "boca_parada",
    "SORRISO": "sorriso",
    "ABRE_FECHA": "abre_fecha",
    "MOV_CABECA": "mov_cabeca",
    "MOV_BOCA_ALEATORIO": "mov_boca_aleatorio",
    "FALA_FORA_VOCAB": "fala_fora_vocab",
}
OOV_PROMPTS = {
    SESSION_IDS[0]: ["CASA", "COMIDA", "HOJE"],
    SESSION_IDS[1]: ["MÃE", "OBRIGADO", "QUERO"],
}
ROW_KEYS = {
    "order",
    "sample_id",
    "session_id",
    "sample_kind",
    "expected_label",
    "negative_category",
    "repetition_index",
    "oov_prompt",
    "prompt_or_action",
    "raw_video_path",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sort_key(session_id: str, sample_id: str) -> tuple[str, str]:
    text = f"20261001|{session_id}|{sample_id}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), sample_id


def validate_capture_plan(plan: dict) -> None:
    """Recusa alterações de quantidade, identidade, ordem, paths e feedback."""
    _require(plan.get("format_version") == 1, "Versão do plano inválida.")
    _require(
        plan.get("state") == "CYCLE_06_HELDOUT_CAPTURE_PROTOCOL_FROZEN",
        "Estado do plano inválido.",
    )
    _require(
        plan.get("randomization", {}).get("seed") == 20261001,
        "Seed de captura inválida.",
    )
    _require(
        plan.get("randomization", {}).get("algorithm") == "sha256_utf8_key_sort_v1",
        "Algoritmo de ordenação inválido.",
    )
    _require(
        plan.get("known_labels") == list(LABEL_SLUGS),
        "Vocabulário conhecido inválido.",
    )
    _require(
        plan.get("unknown_categories") == list(CATEGORY_SLUGS),
        "Categorias UNKNOWN inválidas.",
    )
    _require(
        plan.get("oov_prompts_by_session") == OOV_PROMPTS,
        "Prompts OOV inválidos.",
    )
    _require(
        plan.get("capture_device", {}).get("device") == "iPhone 17"
        and plan["capture_device"].get("opencv_camera_index") == 1
        and plan["capture_device"].get("camera_facing_historical") == "FRONT",
        "Dispositivo de captura inválido.",
    )
    acquisition = plan.get("acquisition", {})
    _require(
        acquisition.get("raw_root") == "data/raw/visual_dataset"
        and acquisition.get("width_px") == 640
        and acquisition.get("height_px") == 480
        and acquisition.get("fps_nominal") == 30
        and acquisition.get("duration_seconds_approx") == 4
        and acquisition.get("encoder_fourcc_requested") == "mp4v"
        and acquisition.get("capture_frame_orientation") == "LANDSCAPE_4_3"
        and acquisition.get("physical_phone_orientation") == "NOT_REQUIRED_FOR_PROTOCOL"
        and acquisition.get("camera_direction") == "FRONT",
        "Aquisição incompatível com development.",
    )
    _require(
        plan.get("expected_counts")
        == {
            "total": 72,
            "per_session": 36,
            "known_total": 36,
            "unknown_total": 36,
            "known_per_session": 18,
            "unknown_per_session": 18,
            "repetitions_per_class_per_session": 3,
        },
        "Contagens esperadas inválidas.",
    )
    sessions = plan.get("sessions", [])
    _require(
        [session.get("session_id") for session in sessions] == list(SESSION_IDS),
        "Sessões de captura inválidas.",
    )
    all_ids = set()
    all_paths = set()
    for session in sessions:
        session_id = session["session_id"]
        rows = session.get("schedule", [])
        _require(len(rows) == 36, f"Sessão {session_id} exige 36 clipes.")
        _require(
            [row.get("order") for row in rows] == list(range(1, 37)),
            "Ordem de captura inválida.",
        )
        _require(
            rows
            == sorted(
                rows,
                key=lambda row: _sort_key(session_id, row["sample_id"]),
            ),
            "Ordem randomizada diverge do algoritmo congelado.",
        )
        per_kind = Counter()
        per_label = Counter()
        per_category = Counter()
        per_identity = Counter()
        for row in rows:
            _require(set(row) == ROW_KEYS, "Campo de amostra inesperado.")
            _require(row["session_id"] == session_id, "Sessão da amostra inválida.")
            kind = row["sample_kind"]
            _require(kind in {"KNOWN", "UNKNOWN"}, "Tipo de amostra inválido.")
            repetition = row["repetition_index"]
            _require(
                type(repetition) is int and 1 <= repetition <= 3,
                "Repetição inválida.",
            )
            if kind == "KNOWN":
                label = row["expected_label"]
                _require(label in LABEL_SLUGS, "Label KNOWN inválido.")
                _require(
                    row["negative_category"] is None
                    and row["oov_prompt"] is None
                    and row["prompt_or_action"] == label,
                    "Prompt KNOWN inválido.",
                )
                slug = LABEL_SLUGS[label]
                folder = slug.upper()
                per_label[label] += 1
                per_identity[(kind, label, repetition)] += 1
            else:
                category = row["negative_category"]
                _require(category in CATEGORY_SLUGS, "Categoria UNKNOWN inválida.")
                _require(
                    row["expected_label"] == "UNKNOWN",
                    "Label UNKNOWN inválido.",
                )
                slug = CATEGORY_SLUGS[category]
                folder = category
                expected_oov = (
                    OOV_PROMPTS[session_id][repetition - 1]
                    if category == "FALA_FORA_VOCAB"
                    else None
                )
                _require(row["oov_prompt"] == expected_oov, "Prompt OOV inválido.")
                expected_action = (
                    f"Articule uma vez: {expected_oov}"
                    if expected_oov is not None
                    else plan["unknown_action_definitions"][category]
                )
                _require(
                    row["prompt_or_action"] == expected_action,
                    "Ação UNKNOWN inválida.",
                )
                per_category[category] += 1
                per_identity[(kind, category, repetition)] += 1
            sample_id = f"{slug}_{session_id}_{repetition:03d}"
            expected_path = (
                f"data/raw/visual_dataset/{session_id}/{folder}/{sample_id}.mp4"
            )
            _require(row["sample_id"] == sample_id, "Sample ID inválido.")
            _require(
                row["raw_video_path"] == expected_path,
                "Path fora da sessão held-out nova.",
            )
            _require(sample_id not in all_ids, "Sample ID duplicado.")
            _require(expected_path not in all_paths, "Path duplicado.")
            all_ids.add(sample_id)
            all_paths.add(expected_path)
            per_kind[kind] += 1
        _require(per_kind == {"KNOWN": 18, "UNKNOWN": 18}, "Tipos desequilibrados.")
        _require(
            per_label == dict.fromkeys(LABEL_SLUGS, 3),
            "Contagem de classe conhecida inválida.",
        )
        _require(
            per_category == dict.fromkeys(CATEGORY_SLUGS, 3),
            "Contagem de categoria desconhecida inválida.",
        )
        _require(
            len(per_identity) == 36
            and all(value == 1 for value in per_identity.values()),
            "Repetição duplicada ou ausente.",
        )
    _require(len(all_ids) == 72, "Total de amostras inválido.")


def load_capture_plan(path: Path = PLAN_PATH) -> dict:
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    _require(b"\r" not in raw, "Quebra de linha inválida no plano.")
    digest = hashlib.sha256(raw).hexdigest()
    _require(digest == PLAN_SHA256, "SHA-256 do plano congelado divergiu.")
    plan = json.loads(raw.decode("utf-8"))
    validate_capture_plan(plan)
    return plan


def _record_raw_sample(camera, row: dict, output_path: Path) -> bool:
    # Reutiliza somente a gravação MP4; process_session e detectores não são chamados.
    from scripts.dataset.collect_visual_session import record_sample

    item = SimpleNamespace(
        label=row["prompt_or_action"],
        sample_id=row["sample_id"],
        session_id=row["session_id"],
        repetition=row["repetition_index"],
    )
    return record_sample(
        camera=camera,
        item=item,
        output_path=output_path,
        sample_number=row["order"],
        sample_count=36,
        preserve_partial=True,
        allow_overwrite=False,
        display_kind=row["sample_kind"],
        preview_action="ARTICULE" if row["sample_kind"] == "KNOWN" else "AÇÃO",
    )


def capture_session(
    plan: dict,
    session_id: str,
    repository_root: Path = REPOSITORY_ROOT,
    dry_run: bool = False,
    start_order: int = 1,
) -> int:
    """Grava em ordem, sem processamento nem sobrescrita de vídeo existente."""
    validate_capture_plan(plan)
    _require(session_id in SESSION_IDS, "Sessão não autorizada.")
    _require(1 <= start_order <= 36, "Ordem de retomada inválida.")
    session = next(
        item for item in plan["sessions"] if item["session_id"] == session_id
    )
    rows = session["schedule"]
    if dry_run:
        for row in rows:
            print(
                f"{row['order']:02d}/36 {row['sample_id']} "
                f"{row['prompt_or_action']} -> {row['raw_video_path']}"
            )
        return 36

    root = Path(repository_root)
    for row in rows:
        output = root / row["raw_video_path"]
        partial = output.with_name(f"{output.stem}.partial{output.suffix}")
        if row["order"] < start_order:
            if not output.is_file() or partial.exists():
                raise FileNotFoundError(
                    f"Ordem anterior ausente ou parcial: {row['sample_id']}"
                )
        elif output.exists() or partial.exists():
            raise FileExistsError(f"Vídeo ou parcial já existente: {output}")

    camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError("iPhone 17/Iriun não disponível no índice OpenCV 1.")
    try:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        success, frame = camera.read()
        if not success or frame.shape[:2] != (480, 640):
            raise RuntimeError("A câmera não forneceu frames 640 × 480.")
        completed = 0
        pending_rows = rows[slice(start_order - 1, None)]
        for row in pending_rows:
            print(f"Ordem {row['order']:02d}/36 — {row['prompt_or_action']}")
            output = root / row["raw_video_path"]
            if not _record_raw_sample(camera, row, output):
                break
            completed += 1
        return completed
    finally:
        camera.release()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, choices=SESSION_IDS)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--capture", action="store_true")
    parser.add_argument("--start-order", type=int, default=1)
    args = parser.parse_args()
    plan = load_capture_plan()
    count = capture_session(
        plan,
        args.session,
        dry_run=args.dry_run,
        start_order=args.start_order,
    )
    if args.dry_run:
        print(f"Plano válido: {count} capturas; câmera não aberta.")
    else:
        print(f"Clipes brutos concluídos nesta execução: {count}.")


if __name__ == "__main__":
    main()
