"""Janela OpenCV do Global Live Tester; prévia não abre hardware."""

from collections import deque
from dataclasses import replace
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw

from silent_voice.inference import live_visual_tester as legacy
from silent_voice.inference.live_fps_diagnostic import FpsCaptureTrace
from silent_voice.inference.global_live_visual_tester import (
    BACKGROUND,
    CARD,
    MUTED,
    TEXT,
    _font,
    _lines,
    action_bounds,
    capture_state,
    closed_state,
    context_action_bounds,
    error_state,
    initial_state,
    perform_capture,
    processing_state,
    profile_action_bounds,
    profile_state,
    render_dashboard,
    result_state,
    select_mode,
)
from silent_voice.inference.personal_live_visual_tester import (
    LABELS,
    PROFILE_VERSION,
    LocalProfileStore,
    PersonalizedPipeline,
    record_enrollment,
)
from silent_voice.inference.live_context_session import (
    ContextAttempt,
    LiveContextSession,
)
from silent_voice.fusion.context_advisory import VisualTechnicalFailure


WINDOW_NAME = "Silent Voice · Global Live Tester"
DETAIL_WINDOW = "Silent Voice · Detalhes técnicos"


class GlobalTesterWindow:
    """A interface não lê a câmera enquanto o worker captura ou infere."""

    def __init__(
        self,
        root: Path,
        *,
        camera_index: int = 1,
        camera_backend: str | None = None,
        visual_preview: bool = False,
        keep_clips: bool = False,
        whisper_model_path: Path | None = None,
        audio_device: int | None = None,
        audio_sample_rate: int | None = None,
        max_context_age_ns: int | None = None,
        fps_diagnostic: bool = False,
        profile_id: str = "local_default",
    ) -> None:
        self.root_path = Path(root).resolve()
        self.camera_index = legacy.validate_camera_index(camera_index)
        self.camera_backend = camera_backend
        self.visual_preview = visual_preview
        self.keep_clips = keep_clips
        self.fps_diagnostic = fps_diagnostic
        self._fps_mode = "NORMAL"
        self._fps_trace: FpsCaptureTrace | None = None
        self._profile_store = LocalProfileStore(self.root_path, profile_id)
        self.state = initial_state(
            camera_index,
            visual_preview=visual_preview,
            profile_id=self._profile_store.profile_id,
        )
        self._events = Queue()
        self._abort = Event()
        self._capture_cancel = Event()
        self._camera_owned_by_worker = Event()
        self._worker = None
        self._camera = None
        self._pipeline = None
        self._sources = None
        self._personal_pipeline = None
        self._context = (
            LiveContextSession(
                whisper_model_path,
                device=audio_device,
                sample_rate=audio_sample_rate,
                max_context_age_ns=max_context_age_ns,
            )
            if whisper_model_path is not None and not visual_preview
            else None
        )
        self._session_id = legacy._new_session_id()
        self._trial_number = 0
        self._last_frame = None
        self._frame_times = deque(maxlen=30)
        self._closing = False
        self._size = (1280, 720)
        self._detail_open = False

    def run(self) -> None:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_NAME, *self._size)
        cv2.setMouseCallback(WINDOW_NAME, self._on_click)
        if not self.visual_preview:
            self._worker = Thread(target=self._initialize, daemon=True)
            self._worker.start()
        try:
            while True:
                if self._closing:
                    if self._worker is None or not self._worker.is_alive():
                        break
                    self._worker.join(timeout=0.05)
                    continue
                try:
                    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                        self.close()
                        continue
                except cv2.error:
                    self.close()
                    continue
                self._tick()
                self._on_key(cv2.waitKey(1) & 0xFF)
                try:
                    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                        self.close()
                except cv2.error:
                    self.close()
        finally:
            self._abort.set()
            if self._worker is not None:
                self._worker.join()
            self._drain_events(closing=True)
            if self._camera is not None:
                self._camera.release()
                self._camera = None
            if self._context is not None:
                self._context.close()
            self.state = closed_state(self.state)
            if self._detail_open:
                try:
                    cv2.destroyWindow(DETAIL_WINDOW)
                except cv2.error:
                    pass
            try:
                cv2.destroyWindow(WINDOW_NAME)
            except cv2.error:
                pass

    def _initialize(self) -> None:
        camera = None
        try:
            sources = legacy.verify_frozen_sources(self.root_path)
            pipeline = legacy.load_live_pipeline(self.root_path)
            self._events.put(("model_ready", None))
            if self._abort.is_set():
                return
            if self.camera_backend is None:
                camera = legacy.open_camera(self.camera_index)
            else:
                camera = legacy.open_camera(
                    self.camera_index, backend=self.camera_backend
                )
            if self._abort.is_set():
                camera.release()
                return
            head = None
            profile_error = None
            try:
                head = self._profile_store.load(sources)
            except (OSError, ValueError, KeyError) as error:
                profile_error = str(error)
            self._events.put(("ready", (camera, pipeline, sources, head)))
            if profile_error:
                self._events.put(("profile_error", profile_error))
        except Exception as error:
            if camera is not None:
                camera.release()
            self._events.put(("startup_error", str(error)))

    def _capture(self) -> None:
        trace = self._fps_trace
        capture_error = None
        try:
            attempt = None
            if self._context is not None and self._context.audio_enabled:
                attempt = self._context.capture_context(
                    cancel=self._capture_cancel,
                    on_stage=lambda stage: self._events.put(("context_stage", stage)),
                )
                if self._capture_cancel.is_set() or self._abort.is_set():
                    raise legacy.CaptureCancelled("Captura contextual cancelada.")
            self._events.put(("visual_start", None))
            self._camera_owned_by_worker.set()
            pipeline = (
                self._personal_pipeline
                if self.state.mode == "PERSONALIZED"
                else self._pipeline
            )
            trial = perform_capture(
                self.root_path,
                self._camera,
                pipeline,
                self._sources,
                camera_index=self.camera_index,
                session_id=self._session_id,
                number=self._trial_number,
                keep_clips=self.keep_clips,
                show_frame=lambda frame, remaining: self._events.put(
                    ("capture_frame", (frame.copy(), remaining))
                ),
                read_key=lambda: (
                    27 if self._abort.is_set() or self._capture_cancel.is_set() else -1
                ),
                processing_callback=lambda: self._events.put(("processing", None)),
                diagnostic_callback=trace.record_capture if trace is not None else None,
                profile_id=(
                    self._profile_store.profile_id
                    if self.state.mode == "PERSONALIZED"
                    else None
                ),
                profile_version=(
                    PROFILE_VERSION if self.state.mode == "PERSONALIZED" else None
                ),
            )
            self._events.put(("result", (trial, attempt, time.perf_counter_ns())))
        except legacy.CaptureCancelled:
            capture_error = "Captura cancelada pelo operador."
            self._events.put(("cancelled", None))
        except Exception as error:
            capture_error = str(error)
            advisory = None
            if attempt is not None and self._context is not None:
                try:
                    advisory = self._context.annotate(
                        VisualTechnicalFailure(reason=str(error)),
                        attempt,
                        visual_decision_ns=time.perf_counter_ns(),
                    )
                except (KeyError, TypeError, ValueError):
                    advisory = None
            self._events.put(("capture_error", (str(error), attempt, advisory)))
        finally:
            self._camera_owned_by_worker.clear()
            if trace is not None:
                try:
                    path = trace.finish(error=capture_error)
                    print(f"Diagnóstico FPS salvo em: {path}")
                except OSError as error:
                    print(f"Não foi possível salvar o diagnóstico FPS: {error}")
                self._fps_trace = None

    def _capture_enrollment(self, label: str, repetition: int) -> None:
        try:
            timing = record_enrollment(
                self.root_path,
                self._camera,
                self._pipeline.encoder,
                self._profile_store,
                self._sources,
                label,
                repetition,
                self._session_id,
                self._trial_number,
                show_frame=lambda frame, remaining: self._events.put(
                    ("capture_frame", (frame.copy(), remaining))
                ),
                read_key=lambda: (
                    27 if self._abort.is_set() or self._capture_cancel.is_set() else -1
                ),
            )
            self._events.put(("enrolled", (label, repetition, timing)))
        except legacy.CaptureCancelled:
            self._events.put(("enrollment_error", "Gravação cancelada."))
        except Exception as error:
            self._events.put(("enrollment_error", str(error)))

    def _build_profile(self) -> None:
        try:
            model = self._profile_store.build(self._sources)
            self._events.put(("profile_built", model))
        except Exception as error:
            self._events.put(("profile_error", str(error)))

    def request_enrollment(self, label: str, repetition: int) -> None:
        if (
            self.visual_preview
            or self._closing
            or not self.state.profile_open
            or self._camera is None
            or self._pipeline is None
            or (self._worker is not None and self._worker.is_alive())
        ):
            return
        self._profile_store.example_path(label, repetition)
        self._capture_cancel.clear()
        self._trial_number += 1
        self.state = replace(
            capture_state(self.state),
            active_slot=(LABELS.index(label), repetition),
        )
        self._worker = Thread(
            target=self._capture_enrollment, args=(label, repetition), daemon=True
        )
        self._worker.start()

    def request_build_profile(self) -> None:
        if (
            self.visual_preview
            or self._closing
            or self._sources is None
            or self._profile_store.total() != 12
            or (self._worker is not None and self._worker.is_alive())
        ):
            return
        self.state = replace(
            self.state,
            profile_processing=True,
            profile_message="Criando o head pessoal TWO-SHOT…",
            can_capture=False,
        )
        self._worker = Thread(target=self._build_profile, daemon=True)
        self._worker.start()

    def request_mode(self, mode: str) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        if mode == "PERSONALIZED" and self._personal_pipeline is None:
            raise ValueError("O perfil personalizado ainda não está pronto.")
        self.state = select_mode(self.state, mode)

    def request_delete_profile(self) -> None:
        if self.visual_preview or (
            self._worker is not None and self._worker.is_alive()
        ):
            return
        self._profile_store.delete()
        self._personal_pipeline = None
        self.state = profile_state(
            select_mode(self.state, "GLOBAL"),
            progress=(0,) * 6,
            status="NÃO CRIADO",
            message="Perfil excluído desta máquina.",
            open_panel=True,
        )

    def request_capture(self) -> None:
        if not self.state.can_capture or self._closing:
            return
        if self._worker is not None and self._worker.is_alive():
            return
        self._capture_cancel.clear()
        self._trial_number += 1
        if self.fps_diagnostic:
            self._fps_trace = FpsCaptureTrace(
                self.root_path, camera_index=self.camera_index, mode=self._fps_mode
            )
        self.state = capture_state(self.state)
        if self.state.audio_enabled:
            self.state = replace(
                self.state,
                phase="ÁUDIO CONTEXTUAL",
                headline="Capturando contexto",
                detail="Fale após o bip; a captura visual virá em seguida.",
                remaining_seconds=None,
                audio_status="CAPTURANDO",
                whisper_status="AGUARDANDO",
                groq_status="AGUARDANDO" if self.state.ai_enabled else "DESATIVADO",
            )
        self._worker = Thread(target=self._capture, daemon=True)
        self._worker.start()

    def request_toggle_audio(self) -> bool:
        if self.visual_preview or self._context is None or self._closing:
            return False
        enabled = not self._context.audio_enabled
        if enabled and self._worker is not None and self._worker.is_alive():
            return False
        self._context.set_audio_enabled(enabled)
        self.state = replace(
            self.state,
            audio_enabled=self._context.audio_enabled,
            ai_enabled=self._context.ai_enabled,
            audio_status="PRONTO" if enabled else "DESATIVADO",
            whisper_status="AGUARDANDO",
            groq_status="PRONTO" if self._context.ai_enabled else "DESATIVADO",
            context_warning=None,
            context_topic=None,
            context_words=(),
            relationship=None,
            context_age_ms=None,
        )
        return enabled

    def request_toggle_ai(self) -> bool:
        if self.visual_preview or self._context is None or self._closing:
            return False
        enabled = not self._context.ai_enabled
        if enabled and self._worker is not None and self._worker.is_alive():
            return False
        self._context.set_ai_enabled(enabled)
        self.state = replace(
            self.state,
            ai_enabled=self._context.ai_enabled,
            groq_status="PRONTO" if enabled else "DESATIVADO",
            context_topic=None,
            context_words=(),
            relationship=None,
            context_age_ms=None,
            context_warning=(
                "Envio automático de texto autorizado nesta sessão."
                if enabled
                else "Envio contextual encerrado nesta sessão."
            ),
        )
        return enabled

    def _show_context(self, attempt, advisory) -> None:
        if advisory is None:
            return
        if not isinstance(attempt, ContextAttempt):
            self.state = replace(self.state, relationship=advisory["relationship"])
            return
        context = attempt.context if advisory.get("context") else None
        temporal = advisory["temporal"]
        warning = (
            advisory["relationship"]
            if advisory["relationship"] in {"STALE_CONTEXT", "TEMPORAL_UNKNOWN"}
            else context.error if context is not None else None
        )
        self.state = replace(
            self.state,
            audio_status=(
                "CAPTURADO"
                if attempt.audio.status.value == "TRANSCRIPTION_AVAILABLE"
                else attempt.audio.status.value
            ),
            whisper_status=attempt.audio.status.value,
            groq_status=(context.status.value if context is not None else "DESATIVADO"),
            context_topic=context.topic if context is not None else None,
            context_words=(context.relevant_known_words if context is not None else ()),
            relationship=advisory["relationship"],
            context_warning=warning,
            audio_latency_ms=attempt.capture_latency_ms,
            whisper_latency_ms=attempt.whisper_latency_ms,
            groq_latency_ms=(attempt.groq_latency_ms if context is not None else None),
            context_age_ms=(
                temporal["capture_age_ns"] / 1e6
                if "capture_age_ns" in temporal
                else None
            ),
        )

    def _handle_event(self, kind: str, payload) -> None:
        if kind == "model_ready":
            self.state = replace(self.state, model_status="PRONTO")
        elif kind == "ready":
            self._camera, self._pipeline, self._sources, head = payload
            self.state = replace(
                self.state,
                camera_status="ATIVA",
                model_status="PRONTO",
                session_status="EM CURSO",
                headline="Pronto para capturar",
                detail="Pressione ESPAÇO ou use o botão para iniciar.",
                can_capture=True,
            )
            if head is not None:
                self._personal_pipeline = PersonalizedPipeline(self._pipeline, head)
            self.state = profile_state(
                self.state,
                progress=tuple(self._profile_store.progress().values()),
                status="PRONTO" if head is not None else "INCOMPLETO",
                message=(
                    "Perfil pessoal compatível carregado."
                    if head is not None
                    else "Grave dois exemplos por palavra para criar seu perfil."
                ),
            )
        elif kind == "startup_error":
            self.state = error_state(self.state, payload, camera=False)
            self.state = replace(self.state, session_status="BLOQUEADA")
        elif kind == "capture_frame":
            self._last_frame, remaining = payload
            self.state = replace(self.state, remaining_seconds=remaining)
        elif kind == "processing":
            self.state = processing_state(self.state)
        elif kind == "visual_start":
            self.state = capture_state(self.state)
        elif kind == "context_stage":
            if payload == "TRANSCRIBINDO":
                self.state = replace(
                    self.state,
                    phase="ÁUDIO CONTEXTUAL",
                    whisper_status="PROCESSANDO",
                    audio_status="LIBERADO",
                )
            elif payload == "CONSULTANDO GROQ":
                self.state = replace(self.state, groq_status="PROCESSANDO")
        elif kind == "result":
            trial, attempt, visual_decision_ns = payload
            try:
                self.state = result_state(self.state, trial)
            except (KeyError, TypeError, ValueError) as error:
                self.state = error_state(self.state, str(error))
            else:
                if self._context is not None:
                    try:
                        advisory = self._context.annotate(
                            trial, attempt, visual_decision_ns=visual_decision_ns
                        )
                        self._show_context(attempt, advisory)
                    except (KeyError, TypeError, ValueError) as error:
                        self.state = replace(
                            self.state,
                            context_warning=f"Contexto indisponível: {error}",
                        )
        elif kind == "capture_error":
            message, attempt, advisory = payload
            self.state = error_state(self.state, message)
            try:
                self._show_context(attempt, advisory)
            except (KeyError, TypeError, ValueError) as error:
                self.state = replace(
                    self.state, context_warning=f"Contexto indisponível: {error}"
                )
        elif kind == "cancelled":
            self.state = replace(
                self.state,
                phase="AGUARDANDO",
                headline="Captura cancelada",
                detail="Inicie outra captura quando desejar.",
                decision=None,
                word=None,
                predicted_label=None,
                score=None,
                remaining_seconds=None,
                can_capture=True,
            )
        elif kind == "enrolled":
            label, repetition, timing = payload
            self._personal_pipeline = None
            message = (
                f"{label} · exemplo {repetition} válido; "
                f"{timing['source_fps_effective']:.1f} FPS."
            )
            self.state = profile_state(
                select_mode(self.state, "GLOBAL"),
                progress=tuple(self._profile_store.progress().values()),
                status="INCOMPLETO",
                message=message,
                open_panel=True,
            )
            self.state = replace(
                self.state, phase="AGUARDANDO", active_slot=None, can_capture=True
            )
        elif kind == "enrollment_error":
            self.state = error_state(self.state, payload)
            self.state = replace(
                self.state,
                active_slot=None,
                profile_open=True,
                profile_message=f"Gravação inválida: {payload}",
            )
        elif kind == "profile_built":
            self._personal_pipeline = PersonalizedPipeline(self._pipeline, payload)
            self.state = profile_state(
                self.state,
                progress=tuple(self._profile_store.progress().values()),
                status="PRONTO",
                message="Perfil pessoal pronto. Selecione PERSONALIZED para usar.",
                open_panel=True,
            )
            self.state = replace(self.state, profile_processing=False, can_capture=True)
        elif kind == "profile_error":
            self.state = profile_state(
                self.state,
                progress=tuple(self._profile_store.progress().values()),
                status="INCOMPATÍVEL",
                message=f"Perfil indisponível: {payload}",
                open_panel=True,
            )
            self.state = replace(self.state, profile_processing=False, can_capture=True)

    def _drain_events(self, *, closing: bool = False) -> None:
        while True:
            try:
                kind, payload = self._events.get_nowait()
            except Empty:
                return
            if closing:
                if kind == "ready":
                    payload[0].release()
            else:
                self._handle_event(kind, payload)

    def _window_size(self) -> tuple[int, int]:
        try:
            _, _, width, height = cv2.getWindowImageRect(WINDOW_NAME)
            if width >= 960 and height >= 620:
                self._size = (width, height)
        except cv2.error:
            pass
        return self._size

    def _tick(self) -> None:
        self._drain_events(closing=self._closing)
        trace = self._fps_trace
        if (
            trace is not None
            and trace.mode == "NO_REDRAW"
            and self.state.phase == "CAPTURANDO"
        ):
            return
        if (
            not self._closing
            and self._camera is not None
            and not self._camera_owned_by_worker.is_set()
            and self.state.phase not in {"CAPTURANDO", "PROCESSANDO"}
        ):
            success, frame = self._camera.read()
            if not success or frame is None:
                self._camera.release()
                self._camera = None
                self.state = error_state(
                    self.state, "A câmera parou de entregar frames.", camera=False
                )
            else:
                self._last_frame = frame
                now = time.perf_counter_ns()
                self._frame_times.append(now)
                if len(self._frame_times) > 1:
                    elapsed = (now - self._frame_times[0]) / 1e9
                    if elapsed > 0:
                        self.state = replace(
                            self.state, fps=(len(self._frame_times) - 1) / elapsed
                        )
        ui_start_ns = time.perf_counter_ns() if trace is not None else None
        picture = render_dashboard(
            self.state, frame=self._last_frame, size=self._window_size()
        )
        cv2.imshow(WINDOW_NAME, cv2.cvtColor(np.asarray(picture), cv2.COLOR_RGB2BGR))
        if trace is not None and self.state.phase == "CAPTURANDO":
            trace.record_ui(ui_start_ns, time.perf_counter_ns())

    def _on_key(self, key: int) -> None:
        if key == 27 and self.state.phase in {
            "CAPTURANDO",
            "ÁUDIO CONTEXTUAL",
            "PROCESSANDO",
        }:
            self._capture_cancel.set()
        elif self.state.profile_open and key == 27:
            self.state = replace(self.state, profile_open=False)
        elif key in (ord("f"), ord("F")) and self.fps_diagnostic:
            if self.state.can_capture and (
                self._worker is None or not self._worker.is_alive()
            ):
                self._fps_mode = "NO_REDRAW" if self._fps_mode == "NORMAL" else "NORMAL"
                print(f"Diagnóstico FPS: próxima captura em {self._fps_mode}.")
        elif key == 32 and not self.state.profile_open:
            self.request_capture()
        elif key in (ord("d"), ord("D")):
            self.state = replace(self.state, debug=not self.state.debug)
        elif legacy._exit_key(key):
            self.close()

    def _on_click(self, event, x, y, _flags, _param) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if self.state.profile_open:
            for action, (left, top, right, bottom) in profile_action_bounds(
                self._size
            ).items():
                if left <= x <= right and top <= y <= bottom:
                    try:
                        if action.startswith("slot_"):
                            _, index, repetition = action.split("_")
                            self.request_enrollment(LABELS[int(index)], int(repetition))
                        elif action == "build":
                            self.request_build_profile()
                        elif action == "mode_global":
                            self.request_mode("GLOBAL")
                        elif action == "mode_personalized":
                            self.request_mode("PERSONALIZED")
                        elif action == "delete":
                            self.request_delete_profile()
                        elif action == "close":
                            self.state = replace(self.state, profile_open=False)
                    except (OSError, ValueError) as error:
                        self.state = replace(self.state, profile_message=str(error))
                    return
            return
        for action, (left, top, right, bottom) in action_bounds(self._size).items():
            if left <= x <= right and top <= y <= bottom:
                if action == "capture":
                    self.request_capture()
                elif action == "debug":
                    self.state = replace(self.state, debug=not self.state.debug)
                elif action == "profile":
                    self.state = replace(self.state, profile_open=True)
                else:
                    self.close()
                return
        for action, (left, top, right, bottom) in context_action_bounds(
            self._size
        ).items():
            if left <= x <= right and top <= y <= bottom:
                try:
                    if action == "audio":
                        self.request_toggle_audio()
                    else:
                        self.request_toggle_ai()
                except (RuntimeError, ValueError) as error:
                    self.state = replace(self.state, context_warning=str(error))
                return
        if self.state.phase == "ERRO TÉCNICO":
            self._show_error_details()

    def _show_error_details(self) -> None:
        print(f"Erro técnico de captura: {self.state.detail}")
        image = Image.new("RGB", (900, 350), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((20, 20, 880, 330), radius=16, fill=CARD)
        draw.text(
            (42, 39), "DETALHES DO ERRO TÉCNICO", font=_font(22, bold=True), fill=TEXT
        )
        for index, line in enumerate(
            _lines(draw, self.state.detail, _font(17), 805, 9)
        ):
            draw.text((42, 91 + index * 24), line, font=_font(17), fill=MUTED)
        cv2.namedWindow(DETAIL_WINDOW, cv2.WINDOW_AUTOSIZE)
        cv2.imshow(DETAIL_WINDOW, cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR))
        self._detail_open = True

    def close(self) -> None:
        self._closing = True
        self._abort.set()
        self._capture_cancel.set()
        if self._context is not None:
            if self._worker is None or not self._worker.is_alive():
                self._context.close()
            else:
                self._context.set_audio_enabled(False)
        self.state = replace(self.state, audio_enabled=False, ai_enabled=False)


def launch_global_tester(
    root: Path,
    *,
    camera_index: int = 1,
    camera_backend: str | None = None,
    visual_preview: bool = False,
    keep_clips: bool = False,
    whisper_model_path: Path | None = None,
    audio_device: int | None = None,
    audio_sample_rate: int | None = None,
    max_context_age_ns: int | None = None,
    fps_diagnostic: bool = False,
    profile_id: str = "local_default",
) -> None:
    GlobalTesterWindow(
        root,
        camera_index=camera_index,
        camera_backend=camera_backend,
        visual_preview=visual_preview,
        keep_clips=keep_clips,
        whisper_model_path=whisper_model_path,
        audio_device=audio_device,
        audio_sample_rate=audio_sample_rate,
        max_context_age_ns=max_context_age_ns,
        fps_diagnostic=fps_diagnostic,
        profile_id=profile_id,
    ).run()
