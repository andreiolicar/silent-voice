from dataclasses import dataclass


MOUTH_LANDMARK_COUNT = 40

MouthPoint = tuple[float, float]
MouthPoints = tuple[MouthPoint, ...]


@dataclass(frozen=True, slots=True)
class MouthLandmarksFrame:
    frame_index: int
    timestamp_ms: float
    points: MouthPoints

    def __post_init__(self) -> None:
        if self.frame_index < 0:
            raise ValueError("O índice do frame não pode ser negativo.")

        if self.timestamp_ms < 0:
            raise ValueError("O timestamp do frame não pode ser negativo.")

        if len(self.points) != MOUTH_LANDMARK_COUNT:
            raise ValueError(
                "O frame deve possuir exatamente "
                f"{MOUTH_LANDMARK_COUNT} landmarks da boca."
            )
