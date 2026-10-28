import argparse
import time
from math import ceil
from pathlib import Path

import cv2

from silent_voice.vision.dataset_collection_plan import (
    VisualCollectionPlanItem,
    build_visual_collection_plan,
    normalize_label_for_sample_id,
)


CAMERA_INDEX = 1
RECORDING_DURATION_SECONDS = 4.0
OUTPUT_FPS = 30.0

WINDOW_NAME = "Silent Voice - Coleta Visual"

SESSION_IDS = (
    "sessao_01",
    "sessao_02",
    "sessao_03",
)

LABELS = (
    "SIM",
    "NÃO",
    "AJUDA",
    "ÁGUA",
    "BANHEIRO",
    "PARAR",
)

REPETITIONS_PER_LABEL = 3


def parse_arguments(
    arguments: list[str] | None = None,
):
    parser = argparse.ArgumentParser(
        description=("Executa uma sessão guiada de coleta " "visual do Silent Voice.")
    )

    parser.add_argument(
        "--session-id",
        required=True,
        choices=SESSION_IDS,
        help="Sessão que será coletada.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=("Mostra o plano da sessão sem abrir " "a câmera ou gerar arquivos."),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=("Sobrescreve vídeos e amostras " "processadas existentes."),
    )

    parser.add_argument(
        "--camera-index",
        type=int,
        default=CAMERA_INDEX,
        help="Índice OpenCV da câmera.",
    )

    return parser.parse_args(arguments)


def build_session_plan(
    session_id: str,
) -> tuple[VisualCollectionPlanItem, ...]:
    return build_visual_collection_plan(
        session_ids=(session_id,),
        labels=LABELS,
        repetitions_per_label=(REPETITIONS_PER_LABEL),
    )


def build_safe_label_directory(
    label: str,
) -> str:
    return normalize_label_for_sample_id(label).upper()


def build_raw_video_path(
    item: VisualCollectionPlanItem,
) -> Path:
    label_directory = build_safe_label_directory(item.label)

    return (
        Path("data")
        / "raw"
        / "visual_dataset"
        / item.session_id
        / label_directory
        / f"{item.sample_id}.mp4"
    )


def build_partial_video_path(
    final_path: Path,
) -> Path:
    return final_path.with_name(f"{final_path.stem}.partial" f"{final_path.suffix}")


def build_processed_sample_path(
    item: VisualCollectionPlanItem,
) -> Path:
    label_directory = build_safe_label_directory(item.label)

    return (
        Path("data")
        / "processed"
        / "visual"
        / label_directory
        / f"{item.sample_id}.npz"
    )


def print_collection_plan(
    plan: tuple[VisualCollectionPlanItem, ...],
) -> None:
    print("=" * 72)
    print("SILENT VOICE - PLANO DE COLETA VISUAL")
    print("=" * 72)

    for index, item in enumerate(
        plan,
        start=1,
    ):
        raw_path = build_raw_video_path(item)

        processed_path = build_processed_sample_path(item)

        print(
            f"[{index:02d}/{len(plan):02d}] "
            f"{item.label:<9} "
            f"repetição {item.repetition}"
        )

        print(f"  ID: {item.sample_id}")

        print(f"  RAW: {raw_path}")

        print(f"  NPZ: {processed_path}")

    print("=" * 72)


def record_sample(
    camera,
    item: VisualCollectionPlanItem,
    output_path: Path,
    sample_number: int,
    sample_count: int,
    auto_start: bool = False,
    preserve_partial: bool = False,
    allow_overwrite: bool = True,
    display_kind: str = "Palavra",
    preview_action: str = "ARTICULE",
    window_name: str = WINDOW_NAME,
) -> bool:
    if output_path.exists() and not allow_overwrite:
        raise FileExistsError(f"Vídeo já existente: {output_path}")
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    partial_path = build_partial_video_path(output_path)

    if partial_path.is_file():
        if preserve_partial:
            raise FileExistsError(f"Vídeo parcial já existente: {partial_path}")
        partial_path.unlink()

    success, first_frame = camera.read()

    if not success:
        raise RuntimeError("Não foi possível capturar " "o primeiro frame.")

    frame_height, frame_width = first_frame.shape[:2]

    codec = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        str(partial_path),
        codec,
        OUTPUT_FPS,
        (
            frame_width,
            frame_height,
        ),
    )

    if not writer.isOpened():
        raise RuntimeError(
            "Não foi possível criar " f"o vídeo temporário: {partial_path}"
        )

    display_label = build_safe_label_directory(item.label)

    recording = False
    recording_started_at = 0.0
    recorded_frames = 0
    completed = False
    cancelled = False
    countdown_started_at = 0.0
    last_countdown_number = 0

    print()
    print("=" * 72)

    print(f"Amostra {sample_number}/{sample_count}")

    print(f"{display_kind}: {item.label}")

    print(f"Repetição: {item.repetition}")

    print(f"Sample ID: {item.sample_id}")

    if not auto_start:
        print("ESPAÇO: iniciar gravação")

    print("ESC: encerrar a sessão")

    try:
        if auto_start:
            print("Preparar...", flush=True)
            countdown_started_at = time.perf_counter()
        while True:
            success, frame = camera.read()

            if not success:
                raise RuntimeError("Falha ao capturar frame.")

            preview = frame.copy()

            if auto_start and not recording:
                countdown_remaining = 3.0 - (time.perf_counter() - countdown_started_at)
                if countdown_remaining <= 0:
                    recording = True
                    recording_started_at = time.perf_counter()
                    print("GRAVANDO", flush=True)
                else:
                    countdown_number = ceil(countdown_remaining)
                    if countdown_number != last_countdown_number:
                        print(countdown_number, flush=True)
                        last_countdown_number = countdown_number

            if not recording:
                cv2.putText(
                    preview,
                    (f"{sample_number}/" f"{sample_count} - " f"{display_label}"),
                    (
                        20,
                        40,
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (
                        0,
                        255,
                        0,
                    ),
                    2,
                    cv2.LINE_AA,
                )

                instruction = (
                    f"PREPARAR {last_countdown_number}"
                    if auto_start
                    else "ESPACO = GRAVAR"
                )
                cv2.putText(
                    preview,
                    instruction,
                    (
                        20,
                        75,
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (
                        0,
                        255,
                        0,
                    ),
                    2,
                    cv2.LINE_AA,
                )

            else:
                elapsed = time.perf_counter() - recording_started_at

                remaining = max(
                    0.0,
                    RECORDING_DURATION_SECONDS - elapsed,
                )

                writer.write(frame)

                recorded_frames += 1

                cv2.putText(
                    preview,
                    f"{preview_action}: {display_label}",
                    (
                        20,
                        40,
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (
                        0,
                        0,
                        255,
                    ),
                    2,
                    cv2.LINE_AA,
                )

                cv2.putText(
                    preview,
                    f"{remaining:.1f}s",
                    (
                        20,
                        75,
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (
                        0,
                        0,
                        255,
                    ),
                    2,
                    cv2.LINE_AA,
                )

                if elapsed >= RECORDING_DURATION_SECONDS:
                    completed = True
                    break

            cv2.imshow(
                window_name,
                preview,
            )

            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                cancelled = True
                break

            if key == 32 and not recording and not auto_start:
                recording = True
                recording_started_at = time.perf_counter()

                print(f"Gravando: {item.label}")

    except Exception:
        if partial_path.is_file() and not preserve_partial:
            partial_path.unlink()

        raise

    finally:
        writer.release()

    if cancelled:
        if partial_path.is_file() and not preserve_partial:
            partial_path.unlink()
        if preserve_partial:
            print(f"Gravação interrompida. Parcial preservado: {partial_path}")
        else:
            print("Gravação cancelada. Arquivo parcial removido.")

        return False

    if not completed or recorded_frames == 0:
        if partial_path.is_file() and not preserve_partial:
            partial_path.unlink()

        raise RuntimeError("A gravação não foi concluída.")

    if allow_overwrite:
        partial_path.replace(output_path)
    else:
        if output_path.exists():
            raise FileExistsError(f"Vídeo já existente: {output_path}")
        partial_path.rename(output_path)

    print(f"Frames gravados: {recorded_frames}")

    print(f"Vídeo salvo em: {output_path}")

    return True


def process_sample(
    item: VisualCollectionPlanItem,
    raw_path: Path,
    processed_path: Path,
) -> None:
    from silent_voice.vision.detector import MediaPipeMouthDetector
    from silent_voice.vision.visual_dataset_processing import (
        process_and_save_visual_sample,
    )

    capture = cv2.VideoCapture(str(raw_path))

    if not capture.isOpened():
        raise RuntimeError("Não foi possível abrir " f"o vídeo: {raw_path}")

    detector = MediaPipeMouthDetector()

    try:
        sample = process_and_save_visual_sample(
            sample_id=item.sample_id,
            label=item.label,
            capture=capture,
            detector=detector,
            output_path=processed_path,
            session_id=item.session_id,
        )
    finally:
        detector.mesh.close()

    print(f"Processada: {sample.sample_id}")

    print(f"Frames válidos: " f"{sample.frame_count}")

    print(f"NPZ: {processed_path}")


def collect_raw_videos(
    plan: tuple[VisualCollectionPlanItem, ...],
    camera_index: int,
    overwrite: bool,
) -> bool:
    camera = cv2.VideoCapture(
        camera_index,
        cv2.CAP_DSHOW,
    )

    if not camera.isOpened():
        raise RuntimeError("Não foi possível abrir " f"a câmera {camera_index}.")

    try:
        for index, item in enumerate(
            plan,
            start=1,
        ):
            raw_path = build_raw_video_path(item)

            if raw_path.is_file() and not overwrite:
                print()
                print("Vídeo já existente, " f"pulando: {raw_path}")
                continue

            should_continue = record_sample(
                camera=camera,
                item=item,
                output_path=raw_path,
                sample_number=index,
                sample_count=len(plan),
            )

            if not should_continue:
                print("Coleta encerrada pelo usuário.")
                return False

    finally:
        camera.release()
        cv2.destroyAllWindows()

    return True


def process_session(
    plan: tuple[VisualCollectionPlanItem, ...],
    overwrite: bool,
) -> None:
    print()
    print("=" * 72)
    print("PROCESSAMENTO DAS AMOSTRAS")
    print("=" * 72)

    for item in plan:
        raw_path = build_raw_video_path(item)

        processed_path = build_processed_sample_path(item)

        if not raw_path.is_file():
            print("RAW ausente, pulando: " f"{raw_path}")
            continue

        if processed_path.is_file() and not overwrite:
            print("NPZ já existente, pulando: " f"{processed_path}")
            continue

        process_sample(
            item=item,
            raw_path=raw_path,
            processed_path=processed_path,
        )


def main() -> None:
    arguments = parse_arguments()

    plan = build_session_plan(arguments.session_id)

    if arguments.dry_run:
        print_collection_plan(plan)
        return

    print_collection_plan(plan)

    completed = collect_raw_videos(
        plan=plan,
        camera_index=arguments.camera_index,
        overwrite=arguments.overwrite,
    )

    if not completed:
        return

    process_session(
        plan=plan,
        overwrite=arguments.overwrite,
    )

    print()
    print("=" * 72)
    print(f"SESSÃO CONCLUÍDA: " f"{arguments.session_id}")
    print("=" * 72)


if __name__ == "__main__":
    main()
