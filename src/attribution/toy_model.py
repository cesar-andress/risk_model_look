"""Deterministic tiny causal toy model for CPU attribution integration tests.

Do not download LLMs. This module is for shape/sign/completeness tests only.
"""

from __future__ import annotations

import torch
from torch import Tensor, nn


class TinyCausalScorer(nn.Module):
    """Minimal differentiable model: embeddings -> two logits via linear read.

    Designed so individual token embedding dimensions can drive signed risk.
    """

    def __init__(self, dim: int = 8, vocab: int = 32, n_layers: int = 2, n_heads: int = 2):
        super().__init__()
        self.dim = dim
        self.vocab = vocab
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.embed = nn.Embedding(vocab, dim)
        # Per-layer fake attention params (for shape tests)
        self.q_proj = nn.ModuleList([nn.Linear(dim, dim, bias=False) for _ in range(n_layers)])
        self.k_proj = nn.ModuleList([nn.Linear(dim, dim, bias=False) for _ in range(n_layers)])
        self.out = nn.Linear(dim, 2, bias=False)
        self._init_deterministic()

    def _init_deterministic(self) -> None:
        torch.manual_seed(0)
        for p in self.parameters():
            if p.dim() >= 2:
                nn.init.xavier_uniform_(p)
            else:
                nn.init.zeros_(p)
        # Make dim-0 of each token contribute positively to logit_1 - logit_0
        with torch.no_grad():
            self.out.weight.zero_()
            self.out.weight[1, 0] = 1.0
            self.out.weight[0, 0] = -1.0

    def embeddings(self, input_ids: Tensor) -> Tensor:
        return self.embed(input_ids)

    def attention_maps(self, embeddings: Tensor) -> Tensor:
        """Return (n_layers, n_heads, T, T) causal attention weights."""
        b, t, d = embeddings.shape
        assert b == 1
        maps = []
        head_dim = d // self.n_heads
        causal = torch.tril(torch.ones(t, t, device=embeddings.device))
        for layer in range(self.n_layers):
            q = self.q_proj[layer](embeddings).view(b, t, self.n_heads, head_dim)
            k = self.k_proj[layer](embeddings).view(b, t, self.n_heads, head_dim)
            # (b, heads, t, t)
            att = torch.einsum("bthd,bshd->bhts", q, k) / (head_dim**0.5)
            att = att.masked_fill(causal.view(1, 1, t, t) == 0, -1e9)
            att = torch.softmax(att, dim=-1)
            maps.append(att[0])  # (heads, t, t)
        return torch.stack(maps, dim=0)

    def logits_from_embeddings(self, embeddings: Tensor, *, query_index: int) -> tuple[Tensor, Tensor]:
        h = embeddings[0, query_index]  # (D,)
        logits = self.out(h)  # (2,)
        return logits[0], logits[1]

    def score_from_embeddings(self, embeddings: Tensor, *, query_index: int) -> Tensor:
        l0, l1 = self.logits_from_embeddings(embeddings, query_index=query_index)
        return l1 - l0

    def forward_score(self, input_ids: Tensor, *, query_index: int) -> Tensor:
        return self.score_from_embeddings(self.embeddings(input_ids), query_index=query_index)


class LinearPathToy(nn.Module):
    """Even simpler: s = sum_t w · e_t  for IG completeness tests."""

    def __init__(self, dim: int = 4):
        super().__init__()
        self.w = nn.Parameter(torch.tensor([1.0, -0.5, 0.25, 0.0][:dim], dtype=torch.float32))

    def score(self, embeddings: Tensor) -> Tensor:
        # embeddings: (1, T, D)
        return (embeddings * self.w.view(1, 1, -1)).sum()
