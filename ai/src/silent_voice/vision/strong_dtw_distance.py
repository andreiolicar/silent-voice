from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class StrongDtwDistanceConfig:
    normalize_by_path_length: bool
    max_normalized_warping: float | None = None

    def __post_init__(self) -> None:
        if self.max_normalized_warping is None:
            return

        if not np.isfinite(self.max_normalized_warping):
            raise ValueError("O limite normalizado de warping " "deve ser finito.")

        if not (0.0 <= self.max_normalized_warping <= 1.0):
            raise ValueError(
                "O limite normalizado de warping " "deve estar entre 0.0 e 1.0."
            )


@dataclass(frozen=True, slots=True)
class StrongDtwDistanceResult:
    total_cost: float
    path_length: int
    distance: float


def _validate_sequences(
    sequence_a: np.ndarray,
    sequence_b: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:
    validated_a = np.asarray(
        sequence_a,
        dtype=np.float64,
    )

    validated_b = np.asarray(
        sequence_b,
        dtype=np.float64,
    )

    if validated_a.ndim != 2 or validated_b.ndim != 2:
        raise ValueError("As sequências DTW devem ser " "matrizes bidimensionais.")

    if validated_a.shape[0] == 0 or validated_b.shape[0] == 0:
        raise ValueError("Uma sequência DTW não pode ser vazia.")

    if validated_a.shape[1] == 0 or validated_b.shape[1] == 0:
        raise ValueError(
            "A dimensão de features das sequências " "DTW não pode ser vazia."
        )

    if validated_a.shape[1] != validated_b.shape[1]:
        raise ValueError(
            "As sequências DTW devem possuir " "a mesma dimensão de features."
        )

    if not np.all(np.isfinite(validated_a)) or not np.all(np.isfinite(validated_b)):
        raise ValueError("As sequências DTW devem conter " "apenas valores finitos.")

    return (
        validated_a,
        validated_b,
    )


def _select_predecessor(
    candidates: tuple[
        tuple[
            float,
            int,
        ],
        ...,
    ],
) -> tuple[
    float,
    int,
]:
    return min(
        candidates,
        key=lambda candidate: (
            candidate[0],
            candidate[1],
        ),
    )


def _normalized_position(
    frame_index: int,
    frame_count: int,
) -> float:
    if frame_count == 1:
        return 0.0

    return frame_index / (frame_count - 1)


def _is_alignment_allowed(
    frame_index_a: int,
    frame_count_a: int,
    frame_index_b: int,
    frame_count_b: int,
    max_normalized_warping: float | None,
) -> bool:
    if max_normalized_warping is None:
        return True

    position_a = _normalized_position(
        frame_index=frame_index_a,
        frame_count=frame_count_a,
    )

    position_b = _normalized_position(
        frame_index=frame_index_b,
        frame_count=frame_count_b,
    )

    return abs(position_a - position_b) <= max_normalized_warping


def calculate_strong_dtw_distance(
    sequence_a: np.ndarray,
    sequence_b: np.ndarray,
    config: StrongDtwDistanceConfig,
) -> StrongDtwDistanceResult:
    (
        validated_a,
        validated_b,
    ) = _validate_sequences(
        sequence_a=sequence_a,
        sequence_b=sequence_b,
    )

    frame_count_a = validated_a.shape[0]

    frame_count_b = validated_b.shape[0]

    infinity = float("inf")

    unreachable_path_length = np.iinfo(np.int64).max

    previous_costs = np.full(
        frame_count_b + 1,
        infinity,
        dtype=np.float64,
    )

    previous_lengths = np.full(
        frame_count_b + 1,
        unreachable_path_length,
        dtype=np.int64,
    )

    previous_costs[0] = 0.0
    previous_lengths[0] = 0

    for frame_index_a in range(
        1,
        frame_count_a + 1,
    ):
        current_costs = np.full(
            frame_count_b + 1,
            infinity,
            dtype=np.float64,
        )

        current_lengths = np.full(
            frame_count_b + 1,
            unreachable_path_length,
            dtype=np.int64,
        )

        for frame_index_b in range(
            1,
            frame_count_b + 1,
        ):
            if not _is_alignment_allowed(
                frame_index_a=(frame_index_a - 1),
                frame_count_a=frame_count_a,
                frame_index_b=(frame_index_b - 1),
                frame_count_b=frame_count_b,
                max_normalized_warping=(config.max_normalized_warping),
            ):
                continue

            local_cost = float(
                np.linalg.norm(
                    validated_a[frame_index_a - 1] - validated_b[frame_index_b - 1]
                )
            )

            (
                predecessor_cost,
                predecessor_length,
            ) = _select_predecessor(
                (
                    (
                        previous_costs[frame_index_b - 1],
                        int(previous_lengths[frame_index_b - 1]),
                    ),
                    (
                        previous_costs[frame_index_b],
                        int(previous_lengths[frame_index_b]),
                    ),
                    (
                        current_costs[frame_index_b - 1],
                        int(current_lengths[frame_index_b - 1]),
                    ),
                )
            )

            if not np.isfinite(predecessor_cost):
                continue

            current_costs[frame_index_b] = predecessor_cost + local_cost

            current_lengths[frame_index_b] = predecessor_length + 1

        previous_costs = current_costs

        previous_lengths = current_lengths

    total_cost = float(previous_costs[frame_count_b])

    path_length = int(previous_lengths[frame_count_b])

    if not np.isfinite(total_cost) or path_length == unreachable_path_length:
        raise ValueError(
            "Não existe alinhamento válido " "para o limite de warping informado."
        )

    if config.normalize_by_path_length:
        distance = total_cost / path_length
    else:
        distance = total_cost

    return StrongDtwDistanceResult(
        total_cost=total_cost,
        path_length=path_length,
        distance=float(distance),
    )
