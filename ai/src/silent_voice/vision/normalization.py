import math

from silent_voice.vision.landmarks import (
    MOUTH_LANDMARK_COUNT,
    MouthPoints,
)


LEFT_MOUTH_CORNER_INDEX = 0
RIGHT_MOUTH_CORNER_INDEX = 10


def normalize_mouth_points(points: MouthPoints) -> MouthPoints:
    if len(points) != MOUTH_LANDMARK_COUNT:
        raise ValueError(
            "A normalização exige exatamente "
            f"{MOUTH_LANDMARK_COUNT} landmarks da boca."
        )

    left_x, left_y = points[LEFT_MOUTH_CORNER_INDEX]
    right_x, right_y = points[RIGHT_MOUTH_CORNER_INDEX]

    delta_x = right_x - left_x
    delta_y = right_y - left_y

    mouth_width = math.hypot(delta_x, delta_y)

    if mouth_width == 0.0:
        raise ValueError("Os cantos da boca não podem ocupar a mesma posição.")

    center_x = (left_x + right_x) / 2.0
    center_y = (left_y + right_y) / 2.0

    angle = math.atan2(delta_y, delta_x)

    cosine = math.cos(-angle)
    sine = math.sin(-angle)

    normalized_points = []

    for x, y in points:
        translated_x = x - center_x
        translated_y = y - center_y

        rotated_x = translated_x * cosine - translated_y * sine
        rotated_y = translated_x * sine + translated_y * cosine

        normalized_points.append(
            (
                rotated_x / mouth_width,
                rotated_y / mouth_width,
            )
        )

    return tuple(normalized_points)
