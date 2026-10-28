"""Política LGH.1A de gaps, sem alterar detecções nem a sequência temporal."""

from dataclasses import dataclass

import numpy as np

from silent_voice.vision.mouth_roi_dataset import _max_missing_run


POLICY_ID = "LANDMARK_GAP_POLICY_V1"
POLICY_SHA256 = "d2dce59d6be92dcd3ec2e66b18a23db2e49c4d42e3fb9caa243fd7a2101cfd8a"
ORIGINAL_PATH = "ORIGINAL_PATH"
BOUNDED_INTERPOLATION = "BOUNDED_INTERPOLATION"
SAFE_REJECT = "SAFE_REJECT_INSUFFICIENT_VISUAL_EVIDENCE"


@dataclass(frozen=True, slots=True)
class GapPolicy:
    """Limites congelados; não permite parâmetros alternativos ou tuning."""

    min_frames: int = 3
    min_detections: int = 2
    max_missing_fraction: float = 0.10
    max_missing_run: int = 3

    def __post_init__(self) -> None:
        if (
            self.min_frames != 3
            or self.min_detections != 2
            or self.max_missing_fraction != 0.10
            or self.max_missing_run != 3
        ):
            raise ValueError(
                "Os limites da política de landmark gaps estão congelados."
            )


@dataclass(frozen=True, slots=True)
class GapResult:
    """Coordenadas completas ou insuficientes, com a máscara observada original."""

    coordinates: np.ndarray
    valid_mask: np.ndarray
    action: str
    interpolation_indices: tuple[int, ...]
    diagnostics: dict[str, object]


def _validate_schema(points: np.ndarray, mask: np.ndarray) -> None:
    if (
        not isinstance(points, np.ndarray)
        or points.dtype != np.dtype(np.float64)
        or points.ndim != 3
        or points.shape[1:] != (40, 2)
    ):
        raise ValueError("As coordenadas devem ser um array float64 [T,40,2].")
    if (
        not isinstance(mask, np.ndarray)
        or mask.dtype != np.dtype(np.bool_)
        or mask.ndim != 1
        or len(mask) != len(points)
    ):
        raise ValueError("A máscara deve ser um array bool [T] alinhado aos pontos.")


def _valid_geometry(points: np.ndarray) -> np.ndarray:
    """Valida centro, delta e largura com a aritmética geométrica histórica."""
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        left = points[:, 0]
        right = points[:, 10]
        centers = (left + right) / 2.0
        deltas = right - left
        widths = np.linalg.norm(deltas, axis=1)
    return (
        np.isfinite(centers).all(axis=1)
        & np.isfinite(deltas).all(axis=1)
        & np.isfinite(widths)
        & (widths > 0.0)
    )


def _result(
    coordinates: np.ndarray,
    mask: np.ndarray,
    diagnostics: dict[str, object],
    action: str,
    violations: list[str],
    interpolation_indices: tuple[int, ...] = (),
) -> GapResult:
    safe_reject = action == SAFE_REJECT
    diagnostics.update(
        {
            "landmark_gap_action": action,
            "interpolation_count": len(interpolation_indices),
            "interpolation_indices": list(interpolation_indices),
            "preprocessing_status": (
                "SAFE_REJECTED" if safe_reject else "READY_FOR_INFERENCE"
            ),
            "violated_conditions": violations,
            "technical_reason": (
                "INSUFFICIENT_VISUAL_EVIDENCE" if safe_reject else None
            ),
        }
    )
    return GapResult(
        coordinates=coordinates,
        valid_mask=mask.copy(),
        action=action,
        interpolation_indices=interpolation_indices,
        diagnostics=diagnostics,
    )


def analyze_and_reconstruct(
    points: np.ndarray, mask: np.ndarray, policy: GapPolicy = GapPolicy()
) -> GapResult:
    """Preenche somente gaps limitados; insuficiência visual vira safe reject.

    O dtype e o alinhamento são contratos técnicos estritos. Coordenadas
    inválidas, frames insuficientes ou limites excedidos são evidência visual
    insuficiente. A saída nunca promove uma reconstrução a detecção observada.
    """
    _validate_schema(points, mask)
    if not isinstance(policy, GapPolicy):
        raise ValueError("A configuração deve usar a política congelada GapPolicy.")

    coordinates = points.copy()
    frame_count = len(mask)
    detected_indices = np.flatnonzero(mask)
    missing_indices = np.flatnonzero(~mask)
    detected_count = len(detected_indices)
    missing_count = len(missing_indices)
    maximum_run = _max_missing_run(mask)
    diagnostics: dict[str, object] = {
        "policy_id": POLICY_ID,
        "policy_sha256": POLICY_SHA256,
        "decoded_frame_count": frame_count,
        "landmark_detected_count": detected_count,
        "landmark_missing_count": missing_count,
        "landmark_missing_fraction": (
            missing_count / frame_count if frame_count else None
        ),
        "landmark_max_consecutive_missing": maximum_run,
        "landmark_missing_indices": missing_indices.tolist(),
        "detection_valid_mask": mask.tolist(),
        "preprocessing_stage": "LANDMARK_GAP_ANALYSIS",
    }
    violations = []
    if frame_count < policy.min_frames:
        violations.append("INSUFFICIENT_DECODED_FRAMES")
    if detected_count < policy.min_detections:
        violations.append("INSUFFICIENT_VALID_DETECTIONS")
    if 10 * missing_count > frame_count:
        violations.append("MISSING_FRACTION_EXCEEDS_LIMIT")
    if maximum_run > policy.max_missing_run:
        violations.append("MISSING_RUN_EXCEEDS_LIMIT")
    if frame_count and detected_count == 0:
        violations.append("ALL_LANDMARKS_MISSING")

    observed = coordinates[detected_indices]
    if not np.isfinite(observed).all():
        violations.append("NON_FINITE_OBSERVED_COORDINATES")
    if not _valid_geometry(observed).all():
        violations.append("INVALID_OBSERVED_GEOMETRY")
    if violations:
        return _result(coordinates, mask, diagnostics, SAFE_REJECT, violations)
    if missing_count == 0:
        return _result(coordinates, mask, diagnostics, ORIGINAL_PATH, [])

    diagnostics["preprocessing_stage"] = "LANDMARK_GAP_RECONSTRUCTION"
    for point_index in range(40):
        for axis in range(2):
            coordinates[missing_indices, point_index, axis] = np.interp(
                missing_indices,
                detected_indices,
                observed[:, point_index, axis],
            )

    reconstructed = coordinates[missing_indices]
    finite_frames = np.isfinite(reconstructed).all(axis=(1, 2))
    valid_geometry = _valid_geometry(reconstructed)
    completed = tuple(
        int(index) for index in missing_indices[finite_frames & valid_geometry]
    )
    if not finite_frames.all():
        violations.append("NON_FINITE_RECONSTRUCTED_COORDINATES")
    if not valid_geometry.all():
        violations.append("INVALID_RECONSTRUCTED_GEOMETRY")
    action = SAFE_REJECT if violations else BOUNDED_INTERPOLATION
    return _result(coordinates, mask, diagnostics, action, violations, completed)
