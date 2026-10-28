import torch
from torch import nn

from silent_voice.models.compact_tcn_config import (
    CompactTcnConfig,
    build_default_compact_tcn_config,
)


class TemporalResidualBlock(nn.Module):
    def __init__(
        self,
        channel_count: int,
        kernel_size: int,
        dilation: int,
        convolutions_per_block: int,
        dropout: float,
    ) -> None:
        super().__init__()

        if channel_count <= 0:
            raise ValueError("O número de canais deve ser positivo.")

        if kernel_size <= 0 or kernel_size % 2 == 0:
            raise ValueError("O kernel deve ser positivo e ímpar.")

        if dilation <= 0:
            raise ValueError("A dilation deve ser positiva.")

        if convolutions_per_block <= 0:
            raise ValueError("O número de convoluções deve ser positivo.")

        if dropout < 0.0 or dropout >= 1.0:
            raise ValueError("O dropout deve estar no intervalo " "[0.0, 1.0).")

        padding = dilation * (kernel_size - 1) // 2

        layers = []

        for _ in range(convolutions_per_block):
            layers.extend(
                (
                    nn.Conv1d(
                        in_channels=channel_count,
                        out_channels=channel_count,
                        kernel_size=kernel_size,
                        dilation=dilation,
                        padding=padding,
                    ),
                    nn.ReLU(),
                    nn.Dropout(p=dropout),
                )
            )

        self.network = nn.Sequential(*layers)

        self.output_activation = nn.ReLU()

    def forward(
        self,
        inputs: torch.Tensor,
    ) -> torch.Tensor:
        transformed = self.network(inputs)

        if transformed.shape != inputs.shape:
            raise RuntimeError(
                "O bloco temporal residual deve " "preservar o formato da entrada."
            )

        return self.output_activation(inputs + transformed)


class CompactTcn(nn.Module):
    def __init__(
        self,
        config: CompactTcnConfig,
    ) -> None:
        super().__init__()

        self.config = config

        self.input_projection = nn.Conv1d(
            in_channels=(config.input_feature_count),
            out_channels=(config.hidden_channel_count),
            kernel_size=1,
        )

        self.temporal_blocks = nn.ModuleList(
            TemporalResidualBlock(
                channel_count=(config.hidden_channel_count),
                kernel_size=config.kernel_size,
                dilation=dilation,
                convolutions_per_block=(config.convolutions_per_block),
                dropout=config.dropout,
            )
            for dilation in config.dilations
        )

        self.classifier = nn.Linear(
            in_features=(config.hidden_channel_count),
            out_features=config.class_count,
        )

    def _validate_inputs(
        self,
        inputs: torch.Tensor,
    ) -> None:
        if inputs.ndim != 3:
            raise ValueError(
                "A entrada do Compact TCN deve ser "
                "tridimensional: "
                "(batch, frames, features)."
            )

        batch_size = inputs.shape[0]
        frame_count = inputs.shape[1]
        feature_count = inputs.shape[2]

        if batch_size <= 0:
            raise ValueError("O batch do Compact TCN não pode ser vazio.")

        if frame_count != self.config.frame_count:
            raise ValueError(
                "A entrada do Compact TCN deve possuir "
                f"{self.config.frame_count} frames."
            )

        if feature_count != self.config.input_feature_count:
            raise ValueError(
                "A entrada do Compact TCN deve possuir "
                f"{self.config.input_feature_count} features."
            )

    def forward(
        self,
        inputs: torch.Tensor,
    ) -> torch.Tensor:
        self._validate_inputs(inputs)

        features = inputs.transpose(
            1,
            2,
        )

        features = self.input_projection(features)

        for block in self.temporal_blocks:
            features = block(features)

        pooled_features = torch.mean(
            features,
            dim=2,
        )

        return self.classifier(pooled_features)


def build_default_compact_tcn() -> CompactTcn:
    return CompactTcn(config=(build_default_compact_tcn_config()))
