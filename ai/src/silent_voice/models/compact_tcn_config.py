from dataclasses import dataclass
from math import isfinite

from silent_voice.vision.visual_training_dataset import (
    DEFAULT_VISUAL_LABELS,
    VISUAL_TRAINING_FRAME_COUNT,
)


@dataclass(frozen=True, slots=True)
class CompactTcnConfig:
    frame_count: int
    input_feature_count: int
    hidden_channel_count: int
    class_count: int
    kernel_size: int
    dilations: tuple[int, ...]
    convolutions_per_block: int
    dropout: float

    def __post_init__(self) -> None:
        positive_integer_fields = (
            (
                "frame_count",
                self.frame_count,
            ),
            (
                "input_feature_count",
                self.input_feature_count,
            ),
            (
                "hidden_channel_count",
                self.hidden_channel_count,
            ),
            (
                "convolutions_per_block",
                self.convolutions_per_block,
            ),
        )

        for field_name, value in positive_integer_fields:
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} deve ser um inteiro positivo.")

        if (
            not isinstance(self.class_count, int)
            or isinstance(self.class_count, bool)
            or self.class_count < 2
        ):
            raise ValueError("O modelo TCN deve possuir pelo menos " "duas classes.")

        if (
            not isinstance(self.kernel_size, int)
            or isinstance(self.kernel_size, bool)
            or self.kernel_size <= 0
            or self.kernel_size % 2 == 0
        ):
            raise ValueError("O kernel do TCN deve ser um inteiro " "positivo e ímpar.")

        if not self.dilations:
            raise ValueError("A configuração de dilations não " "pode ser vazia.")

        if any(
            not isinstance(dilation, int) or isinstance(dilation, bool) or dilation <= 0
            for dilation in self.dilations
        ):
            raise ValueError("Todas as dilations devem ser " "inteiros positivos.")

        if not isfinite(self.dropout) or self.dropout < 0.0 or self.dropout >= 1.0:
            raise ValueError(
                "O dropout deve ser finito e estar " "no intervalo [0.0, 1.0)."
            )

    @property
    def receptive_field_frames(
        self,
    ) -> int:
        dilation_sum = sum(self.dilations)

        expansion_per_convolution = self.kernel_size - 1

        return (
            1 + expansion_per_convolution * self.convolutions_per_block * dilation_sum
        )


def build_default_compact_tcn_config() -> CompactTcnConfig:
    return CompactTcnConfig(
        frame_count=VISUAL_TRAINING_FRAME_COUNT,
        input_feature_count=160,
        hidden_channel_count=32,
        class_count=len(DEFAULT_VISUAL_LABELS),
        kernel_size=3,
        dilations=(
            1,
            2,
            4,
            8,
        ),
        convolutions_per_block=2,
        dropout=0.10,
    )
