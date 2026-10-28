"""Interface local experimental GLOBAL com o runtime visual R4."""

import argparse
import json
from math import isfinite
from pathlib import Path

from silent_voice.inference.global_live_visual_tester_window import (
    launch_global_tester,
)
from silent_voice.inference.live_visual_tester import validate_camera_index
from silent_voice.inference.live_fps_diagnostic import run_auto_fps_diagnostic
from silent_voice.inference.personal_live_visual_tester import LocalProfileStore


ROOT = Path(__file__).resolve().parents[2]


def _camera_index(value: str) -> int:
    try:
        return validate_camera_index(int(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Informe um inteiro positivo.") from error
    if number <= 0:
        raise argparse.ArgumentTypeError("Informe um inteiro positivo.")
    return number


def _context_age(value: str) -> int:
    try:
        seconds = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Informe segundos positivos.") from error
    if not isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("Informe segundos positivos e finitos.")
    nanoseconds = round(seconds * 1_000_000_000)
    if nanoseconds <= 0:
        raise argparse.ArgumentTypeError("O prazo é menor que um nanossegundo.")
    return nanoseconds


def _profile_id(value: str) -> str:
    try:
        return LocalProfileStore(ROOT, profile_id=value).profile_id
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Raiz autorizada dos artefatos privados e dados locais.",
    )
    parser.add_argument(
        "--camera-index",
        type=_camera_index,
        default=1,
        help="Índice OpenCV da câmera frontal (padrão: 1).",
    )
    parser.add_argument(
        "--profile-id",
        type=_profile_id,
        help="Perfil TWO-SHOT local selecionado explicitamente.",
    )
    parser.add_argument(
        "--camera-backend",
        choices=("ANY", "DSHOW", "MSMF"),
        help="Backend OpenCV opt-in; sem flag, mantém DSHOW no Windows.",
    )
    parser.add_argument(
        "--visual-preview",
        action="store_true",
        help="Exibe apenas a interface sintética; não abre câmera nem modelos.",
    )
    parser.add_argument(
        "--keep-clips",
        action="store_true",
        help="Retém vídeos somente na área diagnóstica do tester.",
    )
    parser.add_argument(
        "--fps-diagnostic",
        action="store_true",
        help="Registra tempos por tentativa; F alterna próximo teste sem redesenho.",
    )
    parser.add_argument(
        "--fps-auto-diagnostic",
        action="store_true",
        help="Mede automaticamente NORMAL/NO_REDRAW duas vezes sem modelo ou MP4.",
    )
    parser.add_argument(
        "--whisper-model-path",
        type=Path,
        help="Checkpoint Whisper local; necessário para ativar áudio na janela.",
    )
    parser.add_argument(
        "--audio-device", type=int, help="Índice do dispositivo de entrada de áudio."
    )
    parser.add_argument(
        "--audio-sample-rate", type=_positive_int, help="Taxa solicitada em Hz."
    )
    parser.add_argument(
        "--context-max-age-seconds",
        type=_context_age,
        help="Prazo contextual desta execução; sem valor, temporalidade desconhecida.",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> None:
    args = parse_arguments(arguments)
    if args.artifact_root is None and not args.visual_preview:
        raise SystemExit("Informe --artifact-root para uso operacional ou diagnóstico.")
    private_root = args.artifact_root.resolve() if args.artifact_root else ROOT
    if args.artifact_root is not None and not private_root.is_dir():
        raise SystemExit(
            "A raiz autorizada de artefatos deve ser um diretório existente."
        )
    if args.fps_auto_diagnostic:
        if (
            args.visual_preview
            or args.keep_clips
            or args.fps_diagnostic
            or args.whisper_model_path is not None
            or args.audio_device is not None
            or args.audio_sample_rate is not None
            or args.context_max_age_seconds is not None
            or args.profile_id is not None
        ):
            raise SystemExit(
                "--fps-auto-diagnostic aceita apenas --camera-index "
                "como opção adicional."
            )
        diagnostic_options = {"camera_index": args.camera_index}
        if args.camera_backend is not None:
            diagnostic_options["camera_backend"] = args.camera_backend
        result = run_auto_fps_diagnostic(private_root, **diagnostic_options)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return
    if args.visual_preview and args.keep_clips:
        raise SystemExit("--keep-clips não se aplica à prévia sintética.")
    options = {
        "camera_index": args.camera_index,
        "visual_preview": args.visual_preview,
        "keep_clips": args.keep_clips,
    }
    if args.camera_backend is not None:
        options["camera_backend"] = args.camera_backend
    if args.profile_id is not None:
        options["profile_id"] = args.profile_id
    if args.fps_diagnostic:
        options["fps_diagnostic"] = True
    if args.whisper_model_path is not None:
        options["whisper_model_path"] = args.whisper_model_path
    if args.audio_device is not None:
        options["audio_device"] = args.audio_device
    if args.audio_sample_rate is not None:
        options["audio_sample_rate"] = args.audio_sample_rate
    if args.context_max_age_seconds is not None:
        options["max_context_age_ns"] = args.context_max_age_seconds
    launch_global_tester(private_root, **options)


if __name__ == "__main__":
    main()
