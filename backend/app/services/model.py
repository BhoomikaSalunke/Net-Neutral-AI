import torch
import torch.nn as nn


class TransformerClassifier(nn.Module):
    def __init__(
        self,
        vocab_size: int = 10_000,
        embed_dim: int = 128,
        num_heads: int = 4,
        ffn_dim: int = 256,
        num_layers: int = 2,
        max_len: int = 128,
        dropout: float = 0.1,
        num_classes: int = 2,
    ):
        super().__init__()

        self.token_embedding = nn.Embedding(
            vocab_size,
            embed_dim,
            padding_idx=0,
        )

        self.position_embedding = nn.Embedding(
            max_len,
            embed_dim,
        )

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=ffn_dim,
            dropout=dropout,
            batch_first=True,
        )

        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
        )

        self.classifier = nn.Linear(embed_dim, num_classes)
        self.dropout = nn.Dropout(dropout)
        self.max_len = max_len

        self._init_weights()

    def _init_weights(self):
        nn.init.xavier_uniform_(self.classifier.weight)
        nn.init.zeros_(self.classifier.bias)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len = input_ids.shape

        if seq_len > self.max_len:
            input_ids = input_ids[:, :self.max_len]
            seq_len = self.max_len

        token_embeds = self.token_embedding(input_ids)

        positions = torch.arange(
            seq_len,
            device=input_ids.device,
        )
        positions = positions.unsqueeze(0).expand(batch_size, -1)

        position_embeds = self.position_embedding(positions)

        x = self.dropout(token_embeds + position_embeds)

        padding_mask = input_ids == 0

        x = self.transformer_encoder(
            x,
            src_key_padding_mask=padding_mask,
        )

        valid_mask = (~padding_mask).float().unsqueeze(-1)

        x = (
            (x * valid_mask).sum(dim=1)
            / valid_mask.sum(dim=1).clamp(min=1e-9)
        )

        x = self.dropout(x)

        return self.classifier(x)