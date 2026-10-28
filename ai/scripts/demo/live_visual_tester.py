"""CLI do Live Visual Tester com a política congelada Rejection 4."""

import argparse
from pathlib import Path

from silent_voice.inference.live_visual_tester import (
    check_camera,
    run_live_session,
    validate_camera_index,
    verify_frozen_sources,
)


ROOT = Path(__file__).resolve().parents[2]


def _camera_index(value: str) -> int:
    try:
        return validate_camera_index(int(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--camera-index",
        type=_camera_index,
        default=1,
        help="Índice OpenCV da câmera Iriun (padrão: 1).",
    )
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument(
        "--preflight",
        action="store_true",
        help="Valida proveniência R4 sem abrir câmera, carregar modelos ou inferir.",
    )
    checks.add_argument(
        "--check",
        action="store_true",
        help="Confere freeze, artefatos e câmera; não grava nem infere.",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Inicia com diagnóstico visível."
    )
    parser.add_argument(
        "--keep-clips",
        action="store_true",
        help="Retém MP4 em área de demo, fora dos datasets.",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> None:
    args = parse_arguments(arguments)
    if args.preflight or args.check:
        verified = verify_frozen_sources(ROOT)
        print("Live Visual Tester R4: proveniência PASS; zero gravações e inferências.")
        print(f"Freeze R4 SHA-256: {verified['freeze_sha256']}")
        print(f"Candidato: {verified['candidate_id']}")
        print(f"k: {verified['k']} | Operador: {verified['operator']}")
        print(f"Threshold: {verified['threshold']}")
        if args.check:
            camera = check_camera(args.camera_index)
            print(f"Câmera: índice {camera['camera_index']}, 640×480, 30 FPS nominal.")
        else:
            print("Câmera não aberta; modelos não carregados.")
        return
    run_live_session(
        ROOT,
        camera_index=args.camera_index,
        debug=args.debug,
        keep_clips=args.keep_clips,
    )


if __name__ == "__main__":
    main()
