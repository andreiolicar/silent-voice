import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisualCollectionPlanItem:
    sample_id: str
    label: str
    session_id: str
    repetition: int


def normalize_label_for_sample_id(
    label: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        label,
    )

    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )

    safe_characters = []

    for character in without_accents.lower():
        if character.isalnum():
            safe_characters.append(character)
        elif character in {
            " ",
            "-",
            "_",
        }:
            safe_characters.append("_")

    normalized_label = "".join(safe_characters)

    while "__" in normalized_label:
        normalized_label = normalized_label.replace(
            "__",
            "_",
        )

    return normalized_label.strip("_")


def build_visual_collection_plan(
    session_ids: tuple[str, ...],
    labels: tuple[str, ...],
    repetitions_per_label: int,
) -> tuple[VisualCollectionPlanItem, ...]:
    if not session_ids:
        raise ValueError("O plano exige pelo menos uma sessão.")

    if not labels:
        raise ValueError("O plano exige pelo menos um rótulo.")

    if repetitions_per_label <= 0:
        raise ValueError("A quantidade de repetições deve ser maior que zero.")

    if any(not session_id.strip() for session_id in session_ids):
        raise ValueError("Os identificadores de sessão não podem estar vazios.")

    if any(not label.strip() for label in labels):
        raise ValueError("Os rótulos não podem estar vazios.")

    plan = []

    for session_id in session_ids:
        for label in labels:
            normalized_label = normalize_label_for_sample_id(label)

            for repetition in range(
                1,
                repetitions_per_label + 1,
            ):
                sample_id = f"{normalized_label}_" f"{session_id}_" f"{repetition:03d}"

                plan.append(
                    VisualCollectionPlanItem(
                        sample_id=sample_id,
                        label=label,
                        session_id=session_id,
                        repetition=repetition,
                    )
                )

    return tuple(plan)
