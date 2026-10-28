from typing import Any

import cv2
import mediapipe as mp

from silent_voice.vision.landmarks import MouthLandmarksFrame


MOUTH_LANDMARK_INDICES = (
    61,
    146,
    91,
    181,
    84,
    17,
    314,
    405,
    321,
    375,
    291,
    308,
    324,
    318,
    402,
    317,
    14,
    87,
    178,
    88,
    95,
    185,
    40,
    39,
    37,
    0,
    267,
    269,
    270,
    409,
    415,
    310,
    311,
    312,
    13,
    82,
    81,
    42,
    183,
    78,
)


class MediaPipeMouthDetector:
    def __init__(
        self,
        mesh: Any | None = None,
    ) -> None:
        if mesh is None:
            mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

        self.mesh = mesh

    def extract(
        self,
        frame,
        frame_index: int,
        timestamp_ms: float,
    ) -> MouthLandmarksFrame | None:
        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        result = self.mesh.process(rgb_frame)

        if not result.multi_face_landmarks:
            return None

        face = result.multi_face_landmarks[0]

        frame_height, frame_width = frame.shape[:2]

        points = tuple(
            (
                float(face.landmark[index].x * frame_width),
                float(face.landmark[index].y * frame_height),
            )
            for index in MOUTH_LANDMARK_INDICES
        )

        return MouthLandmarksFrame(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            points=points,
        )
