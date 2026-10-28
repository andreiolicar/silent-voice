from typing import Any

import cv2

from silent_voice.vision.landmarks import MouthLandmarksFrame


def extract_video_sequence(
    capture: Any,
    detector: Any,
) -> tuple[MouthLandmarksFrame, ...]:
    fps = float(capture.get(cv2.CAP_PROP_FPS))

    if fps <= 0.0:
        raise ValueError("O FPS da captura deve ser maior que zero.")

    detected_frames = []
    frame_index = 0

    try:
        while True:
            success, frame = capture.read()

            if not success:
                break

            timestamp_ms = frame_index * 1000.0 / fps

            landmarks = detector.extract(
                frame=frame,
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
            )

            if landmarks is not None:
                detected_frames.append(landmarks)

            frame_index += 1

    finally:
        capture.release()

    return tuple(detected_frames)
