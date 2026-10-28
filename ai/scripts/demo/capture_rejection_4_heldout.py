"""Captura cega do held-out R4; não carrega modelos nem produz scores."""

import argparse
import hashlib
import json
import os
import textwrap
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from silent_voice.rejection.rejection_4_heldout_plan import (
    EDGE_FREEZE_PATH,
    EDGE_FREEZE_SHA256,
    FROZEN_POLICY,
    KNOWN_LABELS,
    MANIFEST_PATH,
    PLAN_PATH,
    RECAPTURE_REASONS,
    REFERENCE_FREEZE_PATH,
    REFERENCE_FREEZE_SHA256,
    SCIENTIFIC_STATUS,
    SESSION_IDS,
    assert_capture_path,
    load_capture_plan,
    plan_sha256,
    validate_capture_plan,
)


ROOT = Path(__file__).resolve().parents[2]
WINDOW_NAME = "R4 — Held-out cego"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ascii(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()


def _show(camera, lines: list[str]) -> None:
    success, frame = camera.read()
    if not success or frame is None or frame.shape[:2] != (480, 640):
        raise RuntimeError("A câmera deve entregar frames 640 × 480.")
    panel = np.full((480, 560, 3), (24, 24, 24), dtype=np.uint8)
    wrapped = [
        part
        for line in lines
        for part in textwrap.wrap(
            _ascii(line), width=52, break_long_words=False, break_on_hyphens=False
        )
    ]
    for index, line in enumerate(wrapped):
        cv2.putText(
            panel,
            line,
            (12, 35 + index * 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    cv2.imshow(WINDOW_NAME, np.concatenate((frame, panel), axis=1))


def _present_target(camera, row: dict, order: int, total: int) -> bool:
    """Mostra somente o alvo pré-registrado; SPACE inicia a contagem."""
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    while True:
        _show(
            camera,
            [
                "R4 — Held-out cego",
                f"Trial {order}/{total}",
                row["prompt_or_action"],
                "ESPAÇO — gravar",
                "ESC/Q — interromper",
            ],
        )
        key = cv2.waitKey(1) & 0xFF
        if key == 32:
            return True
        if key in (27, ord("q"), ord("Q")):
            return False


def _show_saved(camera) -> None:
    _show(camera, ["AMOSTRA SALVA", "Próximo trial sem resultado de modelo."])
    cv2.waitKey(600)


def _open_camera(index: int):
    if type(index) is not int or index < 0:
        raise ValueError("Índice da câmera deve ser inteiro não negativo.")
    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
    camera = cv2.VideoCapture(index, backend)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(f"Iriun/câmera indisponível no índice {index}.")
    try:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        success, frame = camera.read()
        if not success or frame is None or frame.shape[:2] != (480, 640):
            raise RuntimeError("A câmera não entregou frame 640 × 480.")
    except Exception:
        camera.release()
        raise
    return camera


def _safe_output_path(root: Path, relative: str) -> Path:
    authorized = assert_capture_path(relative)
    root = Path(root).resolve()
    output = root.joinpath(*authorized.parts)
    current = root
    for part in authorized.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink em path de captura R4 não é permitido.")
    return output


def _attempt_path(relative: str, number: int) -> str:
    if number < 1:
        raise ValueError("Número de attempt inválido.")
    base = assert_capture_path(relative)
    if number == 1:
        return base.as_posix()
    return base.with_name(f"{base.stem}.attempt_{number:02d}.mp4").as_posix()


def _partial_path(relative: str) -> str:
    base = assert_capture_path(relative)
    return base.with_name(f"{base.stem}.partial.mp4").as_posix()


def _record_raw_sample(camera, row: dict, output: Path, order: int, total: int):
    """Reusa o gravador bruto validado; não chama processamento de amostra."""
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
        output_path=output,
        sample_number=order,
        sample_count=total,
        auto_start=True,
        preserve_partial=True,
        allow_overwrite=False,
        display_kind=row["sample_kind"],
        preview_action="ARTICULE" if row["sample_kind"] == "KNOWN" else "AÇÃO",
        window_name=WINDOW_NAME,
    )


def build_capture_manifest(value: dict, digest: str) -> dict:
    validate_capture_plan(value)
    if digest != plan_sha256(value):
        raise ValueError("SHA-256 do plano divergiu do manifesto.")
    return {
        "format_version": 1,
        "state": "REJECTION_4_HELDOUT_CAPTURE_IN_PROGRESS",
        "scientific_status": SCIENTIFIC_STATUS,
        "plan_sha256": digest,
        "sessions": {},
        "samples": [],
        "recaptures": [],
        "models_loaded": False,
        "model_inference_performed": False,
    }


def _load_manifest(path: Path, value: dict) -> dict:
    expected = build_capture_manifest(value, plan_sha256(value))
    if not path.exists():
        return expected
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (
        manifest.get("format_version") != 1
        or manifest.get("scientific_status") != SCIENTIFIC_STATUS
        or manifest.get("plan_sha256") != expected["plan_sha256"]
        or manifest.get("models_loaded") is not False
        or manifest.get("model_inference_performed") is not False
        or not isinstance(manifest.get("sessions"), dict)
        or not isinstance(manifest.get("samples"), list)
        or not isinstance(manifest.get("recaptures"), list)
    ):
        raise ValueError("Manifesto held-out R4 divergiu do plano cego.")
    rows = {
        row["sample_id"]: row
        for session in value["sessions"]
        for row in session["schedule"]
    }
    ids = [item.get("sample_id") for item in manifest["samples"]]
    if len(ids) != len(set(ids)) or any(sample_id not in rows for sample_id in ids):
        raise ValueError("Sample ID inválido ou duplicado no manifesto R4.")
    for item in manifest["samples"]:
        row = rows[item["sample_id"]]
        number = item.get("selected_attempt_number")
        if (
            item.get("session_id") != row["session_id"]
            or item.get("trial_order") != row["order"]
            or item.get("sample_kind") != row["sample_kind"]
            or item.get("expected_label") != row["expected_label"]
            or item.get("negative_category") != row["negative_category"]
            or item.get("oov_prompt") != row["oov_prompt"]
            or not isinstance(number, int)
            or number < 1
            or item.get("selected_path") != _attempt_path(row["raw_video_path"], number)
            or not isinstance(item.get("attempts"), list)
            or any(
                key in item
                for key in (
                    "score",
                    "prediction",
                    "confidence",
                    "threshold",
                    "decision",
                )
            )
        ):
            raise ValueError("Manifesto R4 contém sample fora do plano.")
    return manifest


def _save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending")
    raw = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def check_session_gap(manifest: dict, session_id: str, now: datetime) -> float | None:
    index = SESSION_IDS.index(session_id)
    if index == 0:
        return None
    previous = manifest["sessions"].get(SESSION_IDS[index - 1], {})
    if not previous.get("ended_at_utc"):
        raise ValueError("A sessão anterior precisa terminar antes da próxima.")
    seconds = (now - datetime.fromisoformat(previous["ended_at_utc"])).total_seconds()
    if seconds < 1200:
        raise ValueError("Intervalo mínimo de 20 minutos ainda não cumprido.")
    return seconds


def _session_rows(value: dict, session_id: str) -> list[dict]:
    if session_id not in SESSION_IDS:
        raise ValueError("Sessão R4 desconhecida.")
    return next(
        session["schedule"]
        for session in value["sessions"]
        if session["session_id"] == session_id
    )


def _camera_metadata(value: dict, index: int) -> dict:
    return {
        "device": value["device"],
        "acquisition": value["acquisition"],
        "camera_index": index,
    }


def _sample_entry(
    row: dict,
    path: str,
    number: int,
    reason: str | None,
    value: dict,
    index: int,
    environment: str,
    lighting: str,
) -> dict:
    timestamp = _now().isoformat()
    return {
        "sample_id": row["sample_id"],
        "session_id": row["session_id"],
        "trial_order": row["order"],
        "sample_kind": row["sample_kind"],
        "expected_label": row["expected_label"],
        "negative_category": row["negative_category"],
        "oov_prompt": row["oov_prompt"],
        "repetition_index": row["repetition_index"],
        "prompt_or_action": row["prompt_or_action"],
        "selected_attempt_number": number,
        "selected_path": path,
        "attempts": [
            {
                "number": number,
                "path": path,
                "timestamp_utc": timestamp,
                "reason": reason,
            }
        ],
        "capture_timestamp_utc": timestamp,
        "capture_configuration": _camera_metadata(value, index),
        "environment_note": environment,
        "lighting_note": lighting,
    }


def _validate_notes(environment: str, lighting: str, camera_index: int) -> None:
    if not environment.strip() or not lighting.strip():
        raise ValueError("Ambiente e iluminação declarados são obrigatórios.")
    if type(camera_index) is not int or camera_index < 0:
        raise ValueError("Índice da câmera deve ser inteiro não negativo.")


def _verify_preserved_attempts(manifest: dict, root: Path) -> None:
    """Bloqueia nova gravação quando uma tentativa auditada desapareceu."""
    for sample in manifest["samples"]:
        for attempt in sample["attempts"]:
            path = _safe_output_path(root, attempt["path"])
            if not path.is_file():
                raise FileNotFoundError(f"Attempt anterior ausente: {path}")


def capture_session(
    value: dict,
    session_id: str,
    root: Path = ROOT,
    *,
    camera_index: int = 1,
    environment_note: str,
    lighting_note: str,
    camera_factory=None,
    presenter=None,
    recorder=None,
) -> int:
    """Grava apenas novos trials em ordem; retoma prefixo já auditado."""
    validate_capture_plan(value)
    _validate_notes(environment_note, lighting_note, camera_index)
    rows = _session_rows(value, session_id)
    root = Path(root).resolve()
    manifest_path = root / MANIFEST_PATH
    manifest = _load_manifest(manifest_path, value)
    from scripts.evaluation.qc_rejection_4_heldout import ensure_capture_allowed

    ensure_capture_allowed(root, manifest, session_id)
    _verify_preserved_attempts(manifest, root)
    recorded = {item["sample_id"]: item for item in manifest["samples"]}
    completed = [row for row in rows if row["sample_id"] in recorded]
    if [row["order"] for row in completed] != list(range(1, len(completed) + 1)):
        raise ValueError("Manifesto R4 não forma prefixo da ordem congelada.")
    for row in rows:
        base = _safe_output_path(root, row["raw_video_path"])
        selected = recorded.get(row["sample_id"])
        if selected:
            if not _safe_output_path(root, selected["selected_path"]).is_file():
                raise FileNotFoundError(
                    f"Attempt selecionado ausente: {row['sample_id']}"
                )
        elif base.exists() or base.with_name(f"{base.stem}.partial.mp4").exists():
            raise FileExistsError(
                f"Arquivo sem seleção; exige auditoria: {row['sample_id']}"
            )
    if len(completed) == 24:
        if not manifest["sessions"].get(session_id, {}).get("ended_at_utc"):
            raise ValueError("Sessão completa sem timestamp final no manifesto.")
        return 0
    now = _now()
    event = manifest["sessions"].get(session_id)
    if event is None:
        if session_id != SESSION_IDS[0]:
            prior = SESSION_IDS[SESSION_IDS.index(session_id) - 1]
            if sum(item["session_id"] == prior for item in manifest["samples"]) != 24:
                raise ValueError("Sessão anterior ainda não tem 24 amostras.")
        gap = check_session_gap(manifest, session_id, now)
    else:
        if event.get("ended_at_utc"):
            raise ValueError("Sessão marcada como encerrada, mas incompleta.")
        gap = None
    factory = camera_factory or _open_camera
    show = presenter or _present_target
    record = recorder or _record_raw_sample
    camera = factory(camera_index)
    run = None
    try:
        if event is None:
            manifest["sessions"][session_id] = {
                "started_at_utc": now.isoformat(),
                "ended_at_utc": None,
                "interval_since_previous_seconds": gap,
                "capture_runs": [],
            }
        run = {
            "started_at_utc": now.isoformat(),
            "ended_at_utc": None,
            "camera_index": camera_index,
            "environment_note": environment_note,
            "lighting_note": lighting_note,
        }
        manifest["sessions"][session_id]["capture_runs"].append(run)
        _save_manifest(manifest_path, manifest)
        new_count = 0
        for row in rows:
            if row["order"] <= len(completed):
                continue
            if not show(camera, row, row["order"], 24):
                break
            path = _safe_output_path(root, row["raw_video_path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            if not record(camera, row, path, row["order"], 24):
                break
            if not path.is_file():
                raise RuntimeError(
                    "Gravador não produziu MP4; manifesto não atualizado."
                )
            manifest["samples"].append(
                _sample_entry(
                    row,
                    row["raw_video_path"],
                    1,
                    None,
                    value,
                    camera_index,
                    environment_note,
                    lighting_note,
                )
            )
            _save_manifest(manifest_path, manifest)
            new_count += 1
            if presenter is None:
                _show_saved(camera)
        run["ended_at_utc"] = _now().isoformat()
        if len(completed) + new_count == 24:
            manifest["sessions"][session_id]["ended_at_utc"] = run["ended_at_utc"]
        _save_manifest(manifest_path, manifest)
        return new_count
    finally:
        try:
            if run is not None and run["ended_at_utc"] is None:
                run["ended_at_utc"] = _now().isoformat()
                _save_manifest(manifest_path, manifest)
        finally:
            camera.release()
            if camera_factory is None:
                cv2.destroyAllWindows()


def technical_recapture(
    value: dict,
    session_id: str,
    sample_id: str,
    reason: str,
    root: Path = ROOT,
    *,
    camera_index: int = 1,
    environment_note: str = "",
    lighting_note: str = "",
    camera_factory=None,
    presenter=None,
    recorder=None,
) -> str:
    """Preserva attempt anterior e registra nova seleção técnica explícita."""
    if reason not in RECAPTURE_REASONS:
        raise ValueError("Recaptura exige motivo técnico/procedural autorizado.")
    validate_capture_plan(value)
    _validate_notes(environment_note, lighting_note, camera_index)
    row = next(
        (
            item
            for item in _session_rows(value, session_id)
            if item["sample_id"] == sample_id
        ),
        None,
    )
    if row is None:
        raise ValueError("Sample ID fora do plano R4.")
    root = Path(root).resolve()
    manifest_path = root / MANIFEST_PATH
    manifest = _load_manifest(manifest_path, value)
    from scripts.evaluation.qc_rejection_4_heldout import ensure_capture_allowed

    ensure_capture_allowed(root, manifest, session_id)
    _verify_preserved_attempts(manifest, root)
    if session_id not in manifest["sessions"]:
        raise ValueError("Sessão R4 ainda não foi iniciada.")
    if (
        SESSION_IDS.index(session_id) < 2
        and SESSION_IDS[SESSION_IDS.index(session_id) + 1] in manifest["sessions"]
    ):
        raise ValueError("Não recapturar sessão após iniciar a sessão seguinte.")
    selected = next(
        (item for item in manifest["samples"] if item["sample_id"] == sample_id), None
    )
    if selected:
        previous_path = selected["selected_path"]
        number = selected["selected_attempt_number"] + 1
    else:
        rows = _session_rows(value, session_id)
        recorded = {
            item["sample_id"]
            for item in manifest["samples"]
            if item["session_id"] == session_id
        }
        completed = [item for item in rows if item["sample_id"] in recorded]
        if [item["order"] for item in completed] != list(
            range(1, len(completed) + 1)
        ) or row["order"] != len(completed) + 1:
            raise ValueError("Recaptura sem seleção exige o próximo trial da ordem.")
        partial = _partial_path(row["raw_video_path"])
        if _safe_output_path(root, partial).is_file():
            previous_path = partial
            number = 2
        elif _safe_output_path(root, row["raw_video_path"]).is_file():
            previous_path = row["raw_video_path"]
            number = 2
        elif reason == "arquivo_nao_salvo":
            previous_path = None
            number = 1
        else:
            raise FileNotFoundError(
                "Nenhum attempt ou parcial anterior foi encontrado."
            )
    if (
        previous_path is not None
        and not _safe_output_path(root, previous_path).is_file()
    ):
        raise FileNotFoundError(
            "Attempt ou parcial anterior ausente; recaptura bloqueada."
        )
    final_path = _attempt_path(row["raw_video_path"], number)
    output = _safe_output_path(root, final_path)
    if output.exists() or output.with_name(f"{output.stem}.partial.mp4").exists():
        raise FileExistsError(
            "Attempt de recaptura já existe; preservado sem sobrescrita."
        )
    factory = camera_factory or _open_camera
    show = presenter or _present_target
    record = recorder or _record_raw_sample
    camera = factory(camera_index)
    try:
        if not show(camera, row, row["order"], 24):
            raise RuntimeError("Recaptura cancelada sem alterar seleção.")
        output.parent.mkdir(parents=True, exist_ok=True)
        if not record(camera, row, output, row["order"], 24):
            raise RuntimeError("Recaptura interrompida; attempt anterior preservado.")
        if not output.is_file():
            raise RuntimeError("Novo MP4 ausente; seleção anterior preservada.")
        timestamp = _now().isoformat()
        if selected is None:
            selected = _sample_entry(
                row,
                final_path,
                number,
                reason,
                value,
                camera_index,
                environment_note,
                lighting_note,
            )
            if previous_path is not None:
                selected["attempts"].insert(
                    0,
                    {
                        "number": 1,
                        "path": previous_path,
                        "timestamp_utc": None,
                        "reason": reason,
                        "selected": False,
                    },
                )
            manifest["samples"].append(selected)
            manifest["samples"].sort(
                key=lambda item: (
                    SESSION_IDS.index(item["session_id"]),
                    item["trial_order"],
                )
            )
        else:
            selected["selected_path"] = final_path
            selected["selected_attempt_number"] = number
            selected["capture_timestamp_utc"] = timestamp
            selected["capture_configuration"] = _camera_metadata(value, camera_index)
            selected["environment_note"] = environment_note
            selected["lighting_note"] = lighting_note
            selected["attempts"].append(
                {
                    "number": number,
                    "path": final_path,
                    "timestamp_utc": timestamp,
                    "reason": reason,
                }
            )
        manifest["recaptures"].append(
            {
                "sample_id": sample_id,
                "session_id": session_id,
                "reason": reason,
                "previous_path": previous_path,
                "final_path": final_path,
                "final_attempt_number": number,
                "timestamp_utc": timestamp,
                "before_model_inference": True,
                "authorized_without_model_output": True,
                "environment_note": environment_note,
                "lighting_note": lighting_note,
            }
        )
        event = manifest["sessions"].get(session_id)
        if (
            event
            and sum(item["session_id"] == session_id for item in manifest["samples"])
            == 24
        ):
            event["ended_at_utc"] = _now().isoformat()
        _save_manifest(manifest_path, manifest)
        if presenter is None:
            _show_saved(camera)
        return final_path
    finally:
        camera.release()
        if camera_factory is None:
            cv2.destroyAllWindows()


def check_preflight(root: Path) -> dict:
    """Confere os freezes documentais sem abrir câmera nem carregar modelos."""
    root = Path(root).resolve()
    value = load_capture_plan(root / PLAN_PATH)
    for relative, expected_sha, expected_state in (
        (EDGE_FREEZE_PATH, EDGE_FREEZE_SHA256, "REJECTION_4_EDGE_POLICY_FROZEN"),
        (
            REFERENCE_FREEZE_PATH,
            REFERENCE_FREEZE_SHA256,
            "REJECTION_4_REFERENCE_POLICY_FROZEN",
        ),
    ):
        raw = (root / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError(f"SHA-256 do freeze divergiu: {relative}.")
        frozen = json.loads(raw.decode("utf-8"))
        if frozen.get("state") != expected_state:
            raise ValueError(f"Estado do freeze divergiu: {relative}.")
        if relative == EDGE_FREEZE_PATH and any(
            frozen.get(key) != expected
            for key, expected in (
                ("candidate_id", FROZEN_POLICY["candidate"]),
                ("k", FROZEN_POLICY["k"]),
                ("threshold", FROZEN_POLICY["threshold"]),
                ("operator", FROZEN_POLICY["operator"]),
                ("labels", list(KNOWN_LABELS)),
            )
        ):
            raise ValueError("Política R4 divergiu do contrato congelado.")
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    if (
        "REJECTION_3_CLOSED" not in agents
        or "LIVE_VISUAL_TESTER_V1_READY" not in agents
    ):
        raise ValueError("R3 ou Live Tester não estão no estado pré-registrado.")
    from scripts.evaluation.qc_rejection_4_heldout import validate_provenance

    validate_provenance(root)
    return {"plan_sha256": plan_sha256(value)}


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, default=1)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--check", action="store_true", help="Plano e freezes, sem câmera."
    )
    action.add_argument(
        "--session", choices=SESSION_IDS, help="Captura sessão planejada."
    )
    parser.add_argument("--technical-recapture", metavar="SAMPLE_ID")
    parser.add_argument("--technical-reason", choices=RECAPTURE_REASONS)
    args = parser.parse_args(arguments)
    try:
        _execute(args, parser)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.exit(2, f"Falha técnica: {error}\n")


def _execute(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.check:
        if args.technical_recapture or args.technical_reason:
            parser.error("Recaptura não pode acompanhar --check.")
        result = check_preflight(ROOT)
        print(f"Preflight R4.7A: plano {result['plan_sha256']}; zero inferências.")
        return
    check_preflight(ROOT)
    from scripts.evaluation.qc_rejection_4_heldout import preflight

    preflight(ROOT)
    value = load_capture_plan(ROOT / PLAN_PATH)
    if bool(args.technical_recapture) != bool(args.technical_reason):
        parser.error("Recaptura exige sample ID e motivo técnico explícitos.")
    environment = input("Ambiente/local declarado: ").strip()
    lighting = input("Iluminação declarada: ").strip()
    if args.technical_recapture:
        path = technical_recapture(
            value,
            args.session,
            args.technical_recapture,
            args.technical_reason,
            camera_index=args.camera_index,
            environment_note=environment,
            lighting_note=lighting,
        )
        print(f"Recaptura técnica registrada: {path}")
    else:
        count = capture_session(
            value,
            args.session,
            camera_index=args.camera_index,
            environment_note=environment,
            lighting_note=lighting,
        )
        print(f"Clipes held-out concluídos nesta execução: {count}.")


if __name__ == "__main__":
    main()
