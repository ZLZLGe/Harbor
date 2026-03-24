from dataclasses import dataclass
import math

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class GridForecastConfig:
    input_dim: int
    lookback: int = 72
    horizon: int = 24
    model_dim: int = 72
    depth: int = 4
    num_heads: int = 6
    mlp_ratio: int = 2
    dropout: float = 0.0


class TemporalSelfAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        if config.model_dim % config.num_heads != 0:
            raise ValueError("model_dim must be divisible by num_heads")

        self.num_heads = config.num_heads
        self.head_dim = config.model_dim // config.num_heads
        self.qkv = nn.Linear(config.model_dim, 3 * config.model_dim)
        self.proj = nn.Linear(config.model_dim, config.model_dim)

    def forward(self, x):
        batch_size, seq_len, hidden_dim = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q = q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        scale = 1.0 / math.sqrt(self.head_dim)
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        attn = F.softmax(attn, dim=-1)
        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(batch_size, seq_len, hidden_dim)
        return self.proj(out)


class FeedForward(nn.Module):
    def __init__(self, config):
        super().__init__()
        hidden_dim = config.model_dim * config.mlp_ratio
        self.net = nn.Sequential(
            nn.Linear(config.model_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, config.model_dim),
        )

    def forward(self, x):
        return self.net(x)


class TimeMixBlock(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.norm1 = nn.LayerNorm(config.model_dim)
        self.time_mixer = TemporalSelfAttention(config)
        self.norm2 = nn.LayerNorm(config.model_dim)
        self.ffn = FeedForward(config)

    def forward(self, x):
        x = x + self.time_mixer(self.norm1(x))
        x = x + self.ffn(self.norm2(x))
        return x


class GridLoadTransformer(nn.Module):
    def __init__(self, config: GridForecastConfig):
        super().__init__()
        self.config = config
        self.input_proj = nn.Linear(config.input_dim, config.model_dim)
        self.pos_embed = nn.Parameter(torch.zeros(1, config.lookback, config.model_dim))
        self.blocks = nn.ModuleList([TimeMixBlock(config) for _ in range(config.depth)])
        self.norm = nn.LayerNorm(config.model_dim)
        self.head = nn.Sequential(
            nn.Linear(config.model_dim, config.model_dim),
            nn.GELU(),
            nn.Linear(config.model_dim, config.horizon),
        )

        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, x, targets=None):
        x = self.input_proj(x)
        x = x + self.pos_embed[:, : x.shape[1]]
        for block in self.blocks:
            x = block(x)
        context = self.norm(x[:, -8:].mean(dim=1))
        forecast = self.head(context)
        loss = None
        if targets is not None:
            loss = F.mse_loss(forecast, targets)
        return forecast, loss
