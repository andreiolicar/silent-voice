from dataclasses import dataclass

from silent_voice.vision.feature_sample import (
    VisualFeatureSample,
)


@dataclass(frozen=True, slots=True)
class VisualCrossValidationFold:
    validation_session_id: str
    train: tuple[
        VisualFeatureSample,
        ...,
    ]
    validation: tuple[
        VisualFeatureSample,
        ...,
    ]


def build_leave_one_session_out_folds(
    samples: tuple[
        VisualFeatureSample,
        ...,
    ],
    session_ids: tuple[
        str,
        ...,
    ],
) -> tuple[
    VisualCrossValidationFold,
    ...,
]:
    if len(session_ids) < 2:
        raise ValueError("A validação cruzada exige " "pelo menos duas sessões.")

    if len(set(session_ids)) != len(session_ids):
        raise ValueError("As sessões declaradas " "não podem estar duplicadas.")

    declared_sessions = set(session_ids)

    for sample in samples:
        if sample.session_id is None:
            raise ValueError(
                "Todas as amostras devem possuir " "session_id para validação cruzada."
            )

        if sample.session_id not in declared_sessions:
            raise ValueError(
                "A amostra pertence a uma sessão " "não declarada no protocolo."
            )

    observed_sessions = {sample.session_id for sample in samples}

    missing_sessions = declared_sessions - observed_sessions

    if missing_sessions:
        missing_text = ", ".join(sorted(missing_sessions))

        raise ValueError(
            "As sessões declaradas devem possuir "
            "amostras no dataset. "
            f"Ausentes: {missing_text}."
        )

    folds = []

    for validation_session_id in session_ids:
        train = tuple(
            sample for sample in samples if sample.session_id != validation_session_id
        )

        validation = tuple(
            sample for sample in samples if sample.session_id == validation_session_id
        )

        folds.append(
            VisualCrossValidationFold(
                validation_session_id=(validation_session_id),
                train=train,
                validation=validation,
            )
        )

    return tuple(folds)
