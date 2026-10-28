"""Interface experimental GLOBAL construída sobre o runtime R4 existente."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import cv2

from silent_voice.inference import live_visual_tester as legacy
from silent_voice.inference.personal_live_visual_tester import LABELS


BACKGROUND = "#0B1120"
CARD = "#172033"
SURFACE = "#1E293B"
BLUE = "#38BDF8"
GREEN = "#22C55E"
RED = "#EF4444"
YELLOW = "#F59E0B"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"


@dataclass(frozen=True, slots=True)
class DashboardState:
    phase: str
    camera_index: int
    camera_status: str
    model_status: str
    session_status: str
    headline: str
    detail: str
    decision: str | None = None
    word: str | None = None
    predicted_label: str | None = None
    score: float | None = None
    score_label: str = "Score do modelo R4"
    fps: float | None = None
    latency_ms: float | None = None
    temporal_status: str = "AGUARDANDO"
    can_capture: bool = False
    debug: bool = False
    remaining_seconds: float | None = None
    mode: str = "GLOBAL"
    profile_id: str = "local_default"
    profile_open: bool = False
    profile_progress: tuple[int, ...] = (0, 0, 0, 0, 0, 0)
    profile_status: str = "NÃO CRIADO"
    profile_message: str = "Grave dois exemplos por palavra para criar seu perfil."
    active_slot: tuple[int, int] | None = None
    profile_processing: bool = False
    audio_enabled: bool = False
    ai_enabled: bool = False
    audio_status: str = "DESATIVADO"
    whisper_status: str = "AGUARDANDO"
    groq_status: str = "DESATIVADO"
    context_topic: str | None = None
    context_words: tuple[str, ...] = ()
    relationship: str | None = None
    context_warning: str | None = None
    audio_latency_ms: float | None = None
    whisper_latency_ms: float | None = None
    groq_latency_ms: float | None = None
    context_age_ms: float | None = None


def initial_state(
    camera_index: int,
    *,
    visual_preview: bool = False,
    profile_id: str = "local_default",
) -> DashboardState:
    legacy.validate_camera_index(camera_index)
    return DashboardState(
        phase="AGUARDANDO",
        camera_index=camera_index,
        camera_status="PRÉVIA SINTÉTICA" if visual_preview else "CONECTANDO",
        model_status="DESLIGADO" if visual_preview else "CARREGANDO",
        session_status="PRÉVIA SINTÉTICA" if visual_preview else "INICIANDO",
        headline="Pronto para começar" if visual_preview else "Preparando sessão",
        detail=(
            "Visualização sintética; câmera e modelos não são abertos."
            if visual_preview
            else "Verificando o runtime visual e a câmera."
        ),
        profile_id=profile_id,
    )


def capture_state(state: DashboardState) -> DashboardState:
    return replace(
        state,
        phase="CAPTURANDO",
        headline="Capturando movimento",
        detail="Mantenha o rosto visível durante os quatro segundos.",
        decision=None,
        word=None,
        predicted_label=None,
        score=None,
        latency_ms=None,
        temporal_status="EM AQUISIÇÃO",
        can_capture=False,
        remaining_seconds=4.0,
        relationship=None,
        context_warning=None,
        context_topic=None,
        context_words=(),
        audio_latency_ms=None,
        whisper_latency_ms=None,
        groq_latency_ms=None,
        context_age_ms=None,
    )


def processing_state(state: DashboardState) -> DashboardState:
    return replace(
        state,
        phase="PROCESSANDO",
        headline="Analisando captura",
        detail="Gate temporal aprovado. Processando o pipeline visual R4.",
        temporal_status="PASS",
        remaining_seconds=None,
    )


def result_state(state: DashboardState, trial: dict) -> DashboardState:
    decision = trial["decision"]
    if decision not in {"ACCEPT", "REJECT"}:
        raise ValueError("Decisão visual R4 inválida.")
    emitted = trial["emitted_label"]
    if emitted != (trial["predicted_label"] if decision == "ACCEPT" else None):
        raise ValueError("A palavra emitida divergiu da decisão R4.")
    timing = trial.get("capture_timing", {})
    if timing.get("technical_decision") != "PASS":
        raise ValueError("Resultado sem gate temporal PASS.")
    return replace(
        state,
        phase=decision,
        headline=emitted if decision == "ACCEPT" else "Sem palavra reconhecida",
        detail=(
            "Palavra visual aceita pelo R4."
            if decision == "ACCEPT"
            else (
                "Evidência visual insuficiente; nenhuma palavra foi emitida."
                if trial.get("technical_reason")
                else "O R4 rejeitou a captura. Tente novamente se desejar."
            )
        ),
        decision=decision,
        word=emitted,
        predicted_label=trial["predicted_label"],
        score=trial["score"],
        fps=timing.get("source_fps_effective"),
        latency_ms=trial["end_to_end_latency_ms"],
        temporal_status="PASS",
        can_capture=state.camera_status == "ATIVA",
        remaining_seconds=None,
    )


def error_state(
    state: DashboardState, message: str, *, camera: bool = True
) -> DashboardState:
    return replace(
        state,
        phase="ERRO TÉCNICO",
        headline="Captura indisponível" if not camera else "Captura bloqueada",
        detail=str(message),
        camera_status=state.camera_status if camera else "INDISPONÍVEL",
        decision=None,
        word=None,
        predicted_label=None,
        score=None,
        latency_ms=None,
        temporal_status="FALHA TÉCNICA",
        can_capture=camera and state.camera_status == "ATIVA",
        remaining_seconds=None,
    )


def closed_state(state: DashboardState) -> DashboardState:
    return replace(
        state,
        phase="ENCERRADA",
        session_status="ENCERRADA",
        can_capture=False,
        remaining_seconds=None,
    )


def profile_state(
    state: DashboardState,
    *,
    progress: tuple[int, ...],
    status: str,
    message: str,
    open_panel: bool | None = None,
) -> DashboardState:
    if len(progress) != 6 or any(
        type(value) is not int or value not in (0, 1, 2) for value in progress
    ):
        raise ValueError("Progresso do perfil inválido.")
    return replace(
        state,
        profile_progress=progress,
        profile_status=status,
        profile_message=message,
        profile_open=state.profile_open if open_panel is None else open_panel,
    )


def select_mode(state: DashboardState, mode: str) -> DashboardState:
    if mode not in {"GLOBAL", "PERSONALIZED"}:
        raise ValueError("Modo visual inválido.")
    if mode == "PERSONALIZED" and state.profile_status != "PRONTO":
        raise ValueError("O perfil personalizado ainda não está pronto.")
    return replace(state, mode=mode)


def perform_capture(
    root: Path,
    camera,
    pipeline,
    sources: dict,
    *,
    camera_index: int,
    session_id: str,
    number: int,
    keep_clips: bool = False,
    backend=legacy,
    show_frame=None,
    read_key=None,
    processing_callback=None,
    diagnostic_callback=None,
    profile_id: str | None = None,
    profile_version: int | None = None,
) -> dict:
    """Reutiliza a policy v2 e o R4; não infere se a aquisição reprovar."""
    root = Path(root).resolve()
    video = backend.clip_path(root, session_id, number, keep=keep_clips)
    log_path = legacy.ensure_diagnostic_path(
        root,
        root
        / legacy.DIAGNOSTIC_ROOT
        / "logs"
        / f"global_visual_tester_{session_id}.jsonl",
    )
    video.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        capture_options = {"show_frame": show_frame, "read_key": read_key}
        capture_options["cleanup_on_error"] = not keep_clips
        if diagnostic_callback is not None:
            capture_options["diagnostic_callback"] = diagnostic_callback
        timing = backend.record_clip(camera, video, **capture_options)
        created = True
        if timing["technical_decision"] != "PASS":
            raise legacy.TemporalCaptureError("Gate temporal não aprovado.")
        if keep_clips:
            backend.mark_retained_clip(root, video)
        if processing_callback is not None:
            processing_callback()
        sample_id = f"{session_id}_{number:03d}"
        if hasattr(pipeline, "infer_clip"):
            trial = pipeline.infer_clip(video, sample_id, session_id)
        else:
            trial = backend.infer_clip(
                pipeline, video, sample_id, session_id, root=root
            )
        trial["recorded_frame_count"] = timing["output_frame_count"]
        trial["capture_timing"] = timing
        record = backend.build_log_record(
            trial,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            camera_index=camera_index,
            clip_retained=keep_clips,
            clip_path=video if keep_clips else None,
            sources=sources,
        )
        if profile_id is not None:
            record["profile_id"] = profile_id
            record["profile_version"] = profile_version
        log_path.parent.mkdir(parents=True, exist_ok=True)
        backend.append_log(log_path, record)
        return trial
    finally:
        if created and not keep_clips:
            backend.cleanup_temporary_clip(root, video)


def _font(size: int, *, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)
    except OSError:
        return ImageFont.load_default(size=size)


def _lines(draw, text: str, font, width: int, maximum: int) -> list[str]:
    lines = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= maximum:
            break
    if current and len(lines) < maximum:
        lines.append(current)
    if len(lines) == maximum and " ".join(lines) != text:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def _badge(draw, x: int, y: int, text: str, color: str, font) -> int:
    width = int(draw.textlength(text, font=font)) + 29
    draw.rounded_rectangle((x, y, x + width, y + 28), radius=14, fill=SURFACE)
    draw.ellipse((x + 9, y + 10, x + 17, y + 18), fill=color)
    draw.text((x + 22, y + 5), text, font=font, fill=TEXT)
    return width


def action_bounds(size: tuple[int, int]) -> dict[str, tuple[int, int, int, int]]:
    width, height = size
    margin = max(20, round(width * 0.025))
    top = height - 75
    return {
        "capture": (margin, top, margin + 218, top + 46),
        "debug": (margin + 231, top, margin + 367, top + 46),
        "profile": (margin + 380, top, margin + 540, top + 46),
        "exit": (width - margin - 96, top, width - margin, top + 46),
    }


def profile_action_bounds(
    size: tuple[int, int],
) -> dict[str, tuple[int, int, int, int]]:
    width, height = size
    left, right = round(width * 0.06), round(width * 0.94)
    top = round(height * 0.07)
    scale = height / 720
    unit = (right - left) / 1126
    x1 = left + round(365 * unit)
    x2 = left + round(525 * unit)
    slot_width = round(138 * unit)
    bounds = {}
    for index in range(6):
        y = top + round((112 + 66 * index) * scale)
        for repetition, x in ((1, x1), (2, x2)):
            bounds[f"slot_{index}_{repetition}"] = (
                x,
                y,
                x + slot_width,
                y + round(42 * scale),
            )
    bottom = height - top - round(61 * scale)
    bounds.update(
        {
            "build": (left + 25, bottom, left + round(205 * unit), bottom + 42),
            "mode_global": (
                left + round(230 * unit),
                bottom,
                left + round(365 * unit),
                bottom + 42,
            ),
            "mode_personalized": (
                left + round(377 * unit),
                bottom,
                left + round(555 * unit),
                bottom + 42,
            ),
            "delete": (
                left + round(575 * unit),
                bottom,
                left + round(740 * unit),
                bottom + 42,
            ),
            "close": (right - round(130 * unit), bottom, right - 24, bottom + 42),
        }
    )
    return bounds


def context_action_bounds(
    size: tuple[int, int],
) -> dict[str, tuple[int, int, int, int]]:
    width, height = size
    margin = max(20, round(width * 0.025))
    gap = max(17, round(width * 0.018))
    camera_width = round((width - 2 * margin - gap) * 0.63)
    right = margin + camera_width + gap
    card_right = width - margin - 17
    top = height - 95 - 172
    available = card_right - right - 48
    button_width = max(102, (available - 10) // 2)
    x = right + 32
    return {
        "audio": (x, top + 34, x + button_width, top + 62),
        "ai": (x + button_width + 10, top + 34, x + 2 * button_width + 10, top + 62),
    }


def _draw_profile_panel(image: Image.Image, state: DashboardState) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    left, right = round(width * 0.06), round(width * 0.94)
    top = round(height * 0.07)
    bottom = height - top
    scale = height / 720
    title = _font(max(23, round(28 * scale)), bold=True)
    body = _font(max(14, round(17 * scale)))
    small = _font(max(11, round(14 * scale)))
    draw.rounded_rectangle((left, top, right, bottom), radius=20, fill=CARD)
    draw.text((left + 27, top + 19), "MEU PERFIL", font=title, fill=TEXT)
    draw.text((left + 230, top + 27), state.profile_id, font=small, fill=BLUE)
    progress_caption = (
        f"TWO-SHOT · {sum(state.profile_progress)}/12 exemplos"
        f" · {state.profile_status}"
    )
    draw.text(
        (left + 28, top + round(60 * scale)),
        progress_caption,
        font=body,
        fill=BLUE,
    )
    message = (
        f"Gravando {LABELS[state.active_slot[0]]} · exemplo {state.active_slot[1]}"
        if state.active_slot is not None
        else state.profile_message
    )
    for index, line in enumerate(_lines(draw, message, small, right - left - 56, 2)):
        draw.text(
            (left + 28, top + round((84 + index * 20) * scale)),
            line,
            font=small,
            fill=YELLOW if state.active_slot else MUTED,
        )
    bounds = profile_action_bounds(image.size)
    for index, label in enumerate(LABELS):
        slot = bounds[f"slot_{index}_1"]
        draw.text((left + 28, slot[1] + 10), label, font=body, fill=TEXT)
        draw.text(
            (slot[0] - 70, slot[1] + 12),
            f"{state.profile_progress[index]}/2",
            font=small,
            fill=BLUE,
        )
        for repetition in (1, 2):
            name = f"slot_{index}_{repetition}"
            area = bounds[name]
            available = state.profile_progress[index] >= repetition
            draw.rounded_rectangle(area, radius=9, fill=SURFACE)
            draw.text(
                (area[0] + 10, area[1] + 10),
                f"{repetition} · {'Regravar' if available else 'Gravar'}",
                font=small,
                fill=GREEN if available else TEXT,
            )
    for action, caption in (
        ("build", "Criar perfil"),
        ("mode_global", "GLOBAL"),
        ("mode_personalized", "PERSONALIZED"),
        ("delete", "Excluir perfil"),
        ("close", "Voltar"),
    ):
        area = bounds[action]
        selected = action == f"mode_{state.mode.lower()}"
        enabled = (
            sum(state.profile_progress) == 12
            and state.camera_status == "ATIVA"
            and not state.profile_processing
            if action == "build"
            else action != "mode_personalized" or state.profile_status == "PRONTO"
        )
        fill = BLUE if selected or (action == "build" and enabled) else SURFACE
        draw.rounded_rectangle(area, radius=9, fill=fill if enabled else BACKGROUND)
        draw.text(
            (area[0] + 10, area[1] + 11),
            caption,
            font=small,
            fill=BACKGROUND if selected or (action == "build" and enabled) else TEXT,
        )


def render_dashboard(
    state: DashboardState,
    *,
    frame=None,
    size: tuple[int, int] = (1280, 720),
) -> Image.Image:
    """Desenha os estados em memória, inclusive a prévia sem câmera/modelos."""
    width, height = size
    if width < 960 or height < 620:
        raise ValueError("A janela deve ter pelo menos 960×620.")
    image = Image.new("RGB", size, BACKGROUND)
    draw = ImageDraw.Draw(image)
    scale = min(width / 1280, height / 720)
    title = _font(max(24, round(30 * scale)), bold=True)
    heading = _font(max(22, round(31 * scale)), bold=True)
    body = _font(max(14, round(17 * scale)))
    small = _font(max(12, round(14 * scale)))
    badge = _font(max(11, round(12 * scale)), bold=True)
    margin = max(20, round(width * 0.025))
    gap = max(17, round(width * 0.018))
    camera_width = round((width - 2 * margin - gap) * 0.63)
    left = margin
    right = left + camera_width + gap
    right_width = width - margin - right
    top = 141
    bottom = height - 95

    draw.text((margin, 21), "SILENT VOICE", font=title, fill=TEXT)
    draw.text((margin, 64), "Global Live Tester", font=body, fill=MUTED)
    draw.text(
        (width - margin - 430, 46),
        f"PERFIL {state.profile_id}",
        font=small,
        fill=MUTED,
    )
    draw.text(
        (width - margin - 275, 69),
        f"MODO {state.mode}",
        font=badge,
        fill=BLUE if state.mode == "GLOBAL" else GREEN,
    )
    draw.text((width - margin - 120, 31), "EXPERIMENTAL", font=badge, fill=YELLOW)
    badge_x = margin
    for label, color in (
        ("GLOBAL", BLUE),
        (
            f"CÂMERA {state.camera_status}",
            GREEN if state.camera_status == "ATIVA" else YELLOW,
        ),
        (
            f"MODELO {state.model_status}",
            GREEN if state.model_status == "PRONTO" else YELLOW,
        ),
        (f"SESSÃO {state.session_status}", BLUE),
    ):
        badge_x += _badge(draw, badge_x, 98, label, color, badge) + 8

    draw.rounded_rectangle(
        (left, top, left + camera_width, bottom), radius=19, fill=CARD
    )
    draw.rounded_rectangle((right, top, width - margin, bottom), radius=19, fill=CARD)
    draw.text((left + 20, top + 17), "CÂMERA AO VIVO", font=badge, fill=MUTED)
    draw.text(
        (left + camera_width - 122, top + 17),
        f"ÍNDICE {state.camera_index}  ·  4:3",
        font=badge,
        fill=MUTED,
    )
    viewport = (left + 18, top + 49, left + camera_width - 18, bottom - 60)
    draw.rounded_rectangle(viewport, radius=12, fill="#101827")
    vx0, vy0, vx1, vy1 = viewport
    if frame is not None:
        camera_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        camera_image.thumbnail((vx1 - vx0, vy1 - vy0), Image.Resampling.BILINEAR)
        px = vx0 + (vx1 - vx0 - camera_image.width) // 2
        py = vy0 + (vy1 - vy0 - camera_image.height) // 2
        image.paste(camera_image, (px, py))
    else:
        label = (
            "PRÉVIA SINTÉTICA · SEM CÂMERA"
            if state.session_status == "PRÉVIA SINTÉTICA"
            else "AGUARDANDO CÂMERA"
        )
        text_width = draw.textlength(label, font=body)
        draw.text(
            (vx0 + (vx1 - vx0 - text_width) / 2, (vy0 + vy1) / 2),
            label,
            font=body,
            fill=MUTED,
        )
    dot = RED if state.phase == "CAPTURANDO" else BLUE
    draw.ellipse((left + 22, bottom - 38, left + 32, bottom - 28), fill=dot)
    caption = (
        "CAPTURA EM CURSO" if state.phase == "CAPTURANDO" else "TRANSMISSÃO VISUAL"
    )
    draw.text((left + 41, bottom - 43), caption, font=small, fill=TEXT)
    draw.text(
        (left + camera_width - 159, bottom - 43),
        f"TEMPO · {state.temporal_status}",
        font=small,
        fill=MUTED,
    )

    accent = (
        GREEN
        if state.phase == "ACCEPT"
        else (
            RED
            if state.phase in {"REJECT", "ERRO TÉCNICO"}
            else YELLOW if state.phase == "CAPTURANDO" else BLUE
        )
    )
    draw.rounded_rectangle(
        (right + 20, top + 22, right + 25, top + 77), radius=2, fill=accent
    )
    draw.text((right + 41, top + 18), "RECONHECIMENTO VISUAL", font=badge, fill=MUTED)
    draw.text((right + 41, top + 44), state.phase, font=small, fill=accent)
    for index, line in enumerate(
        _lines(draw, state.headline, heading, right_width - 52, 2)
    ):
        draw.text((right + 23, top + 94 + index * 38), line, font=heading, fill=TEXT)
    detail_lines = 1 if height < 700 else 2
    for index, line in enumerate(
        _lines(draw, state.detail, body, right_width - 50, detail_lines)
    ):
        draw.text((right + 23, top + 180 + index * 24), line, font=body, fill=MUTED)
    if state.phase == "ERRO TÉCNICO" and height >= 700:
        draw.text(
            (right + 23, top + 244),
            "Clique para ver a mensagem completa",
            font=small,
            fill=BLUE,
        )
    if state.phase == "CAPTURANDO" and state.remaining_seconds is not None:
        draw.text(
            (right + 23, top + 270),
            f"{state.remaining_seconds:.1f} s restantes",
            font=body,
            fill=YELLOW,
        )

    context_top = bottom - 172
    draw.rounded_rectangle(
        (right + 17, context_top, width - margin - 17, bottom - 17),
        radius=12,
        fill=SURFACE,
    )
    draw.text(
        (right + 32, context_top + 12),
        "CONTEXTO COM IA · texto enviado à Groq quando ativo",
        font=badge,
        fill=MUTED,
    )
    bounds = context_action_bounds(size)
    for action, caption, active in (
        (
            "audio",
            "ÁUDIO LIGADO" if state.audio_enabled else "ATIVAR ÁUDIO",
            state.audio_enabled,
        ),
        ("ai", "IA LIGADA" if state.ai_enabled else "ATIVAR IA", state.ai_enabled),
    ):
        area = bounds[action]
        fill = GREEN if active else SURFACE
        draw.rounded_rectangle(area, radius=7, fill=fill)
        draw.text(
            (area[0] + 8, area[1] + 7),
            caption,
            font=badge,
            fill=BACKGROUND if active else TEXT,
        )
    status_line = f"Áudio {state.audio_status} · Whisper {state.whisper_status}"
    for line in _lines(draw, status_line, small, right_width - 62, 1):
        draw.text((right + 32, context_top + 70), line, font=small, fill=TEXT)
    groq_line = f"Groq {state.groq_status} · {state.relationship or 'sem relação'}"
    for line in _lines(draw, groq_line, small, right_width - 62, 1):
        draw.text((right + 32, context_top + 90), line, font=small, fill=TEXT)
    topic = state.context_topic or "assunto indisponível"
    words = ", ".join(state.context_words) if state.context_words else "—"
    for line in _lines(
        draw, f"{topic} · palavras: {words}", small, right_width - 62, 1
    ):
        draw.text((right + 32, context_top + 110), line, font=small, fill=MUTED)
    latency = (
        f"C1 {state.audio_latency_ms:.0f} ms"
        if state.audio_latency_ms is not None
        else "C1 —"
    )
    latency += (
        f" · Whisper {state.whisper_latency_ms:.0f} ms"
        if state.whisper_latency_ms is not None
        else " · Whisper —"
    )
    latency += (
        f" · Groq {state.groq_latency_ms:.0f} ms"
        if state.groq_latency_ms is not None
        else ""
    )
    for line in _lines(draw, latency, small, right_width - 62, 1):
        draw.text((right + 32, context_top + 130), line, font=small, fill=MUTED)
    if state.context_warning:
        for line in _lines(draw, state.context_warning, small, right_width - 62, 1):
            draw.text((right + 32, context_top + 149), line, font=small, fill=YELLOW)
    if state.debug:
        diagnostic = (
            f"R4 · hipótese interna {state.predicted_label or '—'} · "
            f"{state.score_label}: {state.score if state.score is not None else '—'}"
        )
        for line in _lines(draw, diagnostic, small, right_width - 50, 1):
            draw.text((right + 23, context_top - 28), line, font=small, fill=MUTED)

    draw.rounded_rectangle(
        (margin, height - 85, width - margin, height - 13), radius=15, fill=CARD
    )
    for name, label, fill in (
        (
            "capture",
            "ESPAÇO  Capturar / repetir",
            BLUE if state.can_capture else SURFACE,
        ),
        ("debug", "D  Depuração", SURFACE),
        ("profile", "MEU PERFIL", SURFACE),
        ("exit", "ESC  Sair", SURFACE),
    ):
        bounds = action_bounds(size)[name]
        draw.rounded_rectangle(bounds, radius=10, fill=fill)
        color = BACKGROUND if name == "capture" and state.can_capture else TEXT
        draw.text((bounds[0] + 13, bounds[1] + 12), label, font=small, fill=color)
    metrics_x = action_bounds(size)["profile"][2] + 18
    for metric in (
        f"FPS {state.fps:.1f}" if state.fps is not None else "FPS —",
        (
            f"LATÊNCIA {state.latency_ms:.0f} ms"
            if state.latency_ms is not None
            else "LATÊNCIA —"
        ),
    ):
        draw.text((metrics_x, height - 62), metric, font=small, fill=MUTED)
        metrics_x += 114
    if state.profile_open:
        _draw_profile_panel(image, state)
    return image
