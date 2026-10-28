"""Matcher legado de distância ponderada, DTW normalizado e média K3."""

import numpy as np

LEGACY_SHAPE_WEIGHT = 0.35
LEGACY_MOVEMENT_WEIGHT = 0.65
LEGACY_K = 3
FEATURE_COUNT = 160
SHAPE_COUNT = 80
CLASS_COUNT = 6


def _validate_sequence(features: np.ndarray) -> np.ndarray:
    array = np.asarray(features, dtype=np.float64)
    if array.ndim != 2 or array.shape[0] == 0 or array.shape[1] != FEATURE_COUNT:
        raise ValueError("A sequência deve possuir frames com 160 features.")
    if not np.isfinite(array).all():
        raise ValueError("A sequência deve conter apenas valores finitos.")
    return array


def legacy_frame_distance(frame_a: np.ndarray, frame_b: np.ndarray) -> float:
    """sqrt(0.35 * MSE shape + 0.65 * MSE movement)."""
    a = np.asarray(frame_a, dtype=np.float64)
    b = np.asarray(frame_b, dtype=np.float64)
    if a.shape != (FEATURE_COUNT,) or b.shape != (FEATURE_COUNT,):
        raise ValueError("Cada frame deve possuir 160 features.")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Os frames devem conter apenas valores finitos.")
    difference = a - b
    shape_distance = float(np.mean(np.square(difference[:SHAPE_COUNT])))
    movement_distance = float(np.mean(np.square(difference[SHAPE_COUNT:])))
    return float(
        np.sqrt(
            LEGACY_SHAPE_WEIGHT * shape_distance
            + LEGACY_MOVEMENT_WEIGHT * movement_distance
        )
    )


def legacy_normalized_dtw_distance(query: np.ndarray, template: np.ndarray) -> float:
    """DTW acumulado sem janela, dividido pela soma dos comprimentos."""
    a = _validate_sequence(query)
    b = _validate_sequence(template)
    shape_difference = a[:, None, :SHAPE_COUNT] - b[None, :, :SHAPE_COUNT]
    movement_difference = a[:, None, SHAPE_COUNT:] - b[None, :, SHAPE_COUNT:]
    local_costs = np.sqrt(
        LEGACY_SHAPE_WEIGHT * np.mean(np.square(shape_difference), axis=2)
        + LEGACY_MOVEMENT_WEIGHT * np.mean(np.square(movement_difference), axis=2)
    )
    previous = np.full(len(b) + 1, np.inf, dtype=np.float64)
    previous[0] = 0.0
    for row in local_costs:
        current = np.full(len(b) + 1, np.inf, dtype=np.float64)
        for column, cost in enumerate(row, start=1):
            current[column] = float(cost) + min(
                previous[column], current[column - 1], previous[column - 1]
            )
        previous = current
    return float(previous[-1] / (len(a) + len(b)))


def predict_legacy_weighted_dtw(
    query: np.ndarray,
    templates: tuple[tuple[str, int, np.ndarray], ...],
) -> tuple[int, tuple[float, ...]]:
    """Média das três menores distâncias em cada uma das seis classes."""
    validated_query = _validate_sequence(query)
    distances: list[list[float]] = [[] for _ in range(CLASS_COUNT)]
    for sample_id, label_index, features in templates:
        if not sample_id or type(label_index) is not int or label_index not in range(6):
            raise ValueError("Template com sample_id ou label_index inválido.")
        distances[label_index].append(
            legacy_normalized_dtw_distance(validated_query, features)
        )
    if any(len(items) < LEGACY_K for items in distances):
        raise ValueError("Cada classe exige pelo menos três templates de treino.")
    scores = tuple(float(np.mean(sorted(items)[:LEGACY_K])) for items in distances)
    return min(range(CLASS_COUNT), key=lambda index: (scores[index], index)), scores
