"""Graph Attention Network (GAT) and Temporal Sequence Layers for RCT-GAT.

Conforms to Spec Section 7, 24, 25:
- Prerequisite DAG Graph Attention Layer with multi-head attention.
- Explicit retention and extraction of attention weights alpha_ij for root-cause analysis (Formula 8).
- Temporal causal sequence encoder with strict lower-triangular attention mask.
- Single binary cross-entropy (BCE) objective; concept mastery and root causes are derived from predictions.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    # Fallback stubs for linting/typechecking if torch is not yet imported
    class nn:
        class Module:
            def __init__(self): pass
        class Linear: pass
        class Parameter: pass
    torch = None


if HAS_TORCH:
    class PrerequisiteGATLayer(nn.Module):
        """Graph Attention Layer over the curriculum prerequisite DAG.

        Calculates attention weights alpha_ij between concept i and its DAG prerequisites j:
            alpha_ij = softmax_j( LeakyReLU( a^T [W h_i || W h_j] ) )
        """

        def __init__(
            self,
            in_features: int,
            out_features: int,
            num_heads: int = 4,
            dropout: float = 0.1,
            alpha_leaky: float = 0.2,
        ):
            super().__init__()
            self.in_features = in_features
            self.out_features = out_features
            self.num_heads = num_heads
            self.head_dim = out_features // num_heads
            assert out_features % num_heads == 0, "out_features must be divisible by num_heads"

            self.linear_w = nn.Linear(in_features, out_features, bias=False)
            self.attn_src = nn.Parameter(torch.Tensor(1, num_heads, self.head_dim))
            self.attn_dst = nn.Parameter(torch.Tensor(1, num_heads, self.head_dim))
            self.leaky_relu = nn.LeakyReLU(alpha_leaky)
            self.dropout = nn.Dropout(dropout)

            # Cached attention matrix from most recent forward pass: shape (num_nodes, num_nodes)
            self.last_attention_weights: Optional[torch.Tensor] = None

            self.reset_parameters()

        def reset_parameters(self):
            nn.init.xavier_uniform_(self.linear_w.weight)
            nn.init.xavier_uniform_(self.attn_src)
            nn.init.xavier_uniform_(self.attn_dst)

        def forward(self, h_nodes: torch.Tensor, adj_matrix: torch.Tensor) -> torch.Tensor:
            """
            Args:
                h_nodes: Concept node embeddings of shape (N, in_features).
                adj_matrix: Binary or weighted adjacency matrix (N, N), including self-loops.
            Returns:
                Updated concept node embeddings of shape (N, out_features).
            """
            N = h_nodes.size(0)
            # Project nodes: (N, num_heads, head_dim)
            h_proj = self.linear_w(h_nodes).view(N, self.num_heads, self.head_dim)

            # Compute attention scores: e_ij = a_src^T h_i + a_dst^T h_j
            score_src = (h_proj * self.attn_src).sum(dim=-1)  # (N, num_heads)
            score_dst = (h_proj * self.attn_dst).sum(dim=-1)  # (N, num_heads)

            # Broadcast across pairs: (N, N, num_heads)
            scores = score_src.unsqueeze(1) + score_dst.unsqueeze(0)
            scores = self.leaky_relu(scores)

            # Mask out non-edges in the DAG (where adj_matrix == 0)
            # adj_matrix is (N, N); broadcast to (N, N, num_heads)
            mask = (adj_matrix == 0).unsqueeze(-1).expand_as(scores)
            scores = scores.masked_fill(mask, -1e9)

            # Softmax over incoming neighbors (dim 1)
            alpha = F.softmax(scores, dim=1)  # (N, N, num_heads)
            # Cache averaged un-dropped attention weights across heads for root-cause diagnosis (N, N)
            self.last_attention_weights = alpha.mean(dim=-1).detach()
            alpha_dropped = self.dropout(alpha)

            # Aggregate: sum_j alpha_ij * h_proj_j
            out = torch.einsum("ijh,jhd->ihd", alpha_dropped, h_proj)
            out = out.reshape(N, self.out_features)
            return out


    class CausalSequenceEncoder(nn.Module):
        """Temporal interaction sequence encoder with strict causal masking (Invariant 2)."""

        def __init__(
            self,
            embed_dim: int,
            num_heads: int = 4,
            dim_feedforward: int = 128,
            dropout: float = 0.1,
        ):
            super().__init__()
            self.embed_dim = embed_dim
            self.self_attn = nn.MultiheadAttention(
                embed_dim=embed_dim,
                num_heads=num_heads,
                dropout=dropout,
                batch_first=True,
            )
            self.linear1 = nn.Linear(embed_dim, dim_feedforward)
            self.linear2 = nn.Linear(dim_feedforward, embed_dim)
            self.norm1 = nn.LayerNorm(embed_dim)
            self.norm2 = nn.LayerNorm(embed_dim)
            self.dropout = nn.Dropout(dropout)
            self.activation = nn.GELU()

        def forward(
            self,
            x: torch.Tensor,
            causal_mask: Optional[torch.Tensor] = None,
        ) -> torch.Tensor:
            """
            Args:
                x: Interaction tokens of shape (B, T, embed_dim)
                causal_mask: Boolean mask of shape (T, T) where False indicates positions that CANNOT be attended to.
            """
            T = x.size(1)
            # MultiheadAttention requires attn_mask of shape (T, T) where True/1.0 indicates masked (forbidden)
            # In our convention, causal_mask is True for allowed (j <= i).
            # Convert to forbidden mask:
            if causal_mask is not None:
                attn_mask = ~causal_mask
            else:
                # Lower triangular: 0 for allowed, float('-inf') or bool True for forbidden
                attn_mask = torch.triu(torch.ones(T, T, dtype=torch.bool, device=x.device), diagonal=1)

            # Attention block
            attn_out, _ = self.self_attn(
                query=x,
                key=x,
                value=x,
                attn_mask=attn_mask,
                need_weights=False,
            )
            x = self.norm1(x + self.dropout(attn_out))

            # Feed-forward block
            ff_out = self.linear2(self.dropout(self.activation(self.linear1(x))))
            x = self.norm2(x + self.dropout(ff_out))
            return x


    class RCTGATModel(nn.Module):
        """Unified RCT-GAT Model (Spec §7, §24).

        Combines:
        1. Concept Graph Attention over prerequisite DAG.
        2. Interaction embedding (concept + continuous telemetry, NO learner ID).
        3. Causal temporal encoder.
        4. Next-item correctness prediction head.
        5. Concept mastery extraction head.
        """

        def __init__(
            self,
            num_concepts: int,
            continuous_dim: int = 6,
            embed_dim: int = 64,
            gat_heads: int = 4,
            temporal_heads: int = 4,
            dropout: float = 0.1,
        ):
            super().__init__()
            self.num_concepts = num_concepts
            self.embed_dim = embed_dim

            # Raw concept embeddings
            self.concept_embeddings = nn.Embedding(num_concepts, embed_dim)

            # Continuous interaction projection (normalized time, time limit, timed_out, skipped, difficulty_b)
            self.continuous_proj = nn.Linear(continuous_dim, embed_dim)

            # DAG Graph Attention Layer
            self.gat_layer = PrerequisiteGATLayer(
                in_features=embed_dim,
                out_features=embed_dim,
                num_heads=gat_heads,
                dropout=dropout,
            )

            # Temporal Causal Sequence Encoder
            self.sequence_encoder = CausalSequenceEncoder(
                embed_dim=embed_dim,
                num_heads=temporal_heads,
                dim_feedforward=embed_dim * 2,
                dropout=dropout,
            )

            # Next-Item Prediction Head
            self.prediction_head = nn.Sequential(
                nn.Linear(embed_dim, embed_dim // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(embed_dim // 2, 1),
            )

            # Concept Mastery Extraction Projection (w_m^T [s_T * h_c])
            self.mastery_head = nn.Sequential(
                nn.Linear(embed_dim, 1),
                nn.Sigmoid(),
            )

        def forward(
            self,
            concept_indices: torch.Tensor,       # (B, T)
            continuous_features: torch.Tensor,   # (B, T, continuous_dim)
            adj_matrix: torch.Tensor,            # (num_concepts, num_concepts)
            causal_mask: Optional[torch.Tensor] = None,  # (T, T)
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Returns:
                pred_correctness: (B, T, 1) predicted probability of correctness
                last_state: (B, embed_dim) summary state at step T
            """
            # 1. Update concept embeddings via DAG GAT
            all_concepts = torch.arange(self.num_concepts, device=concept_indices.device)
            raw_h = self.concept_embeddings(all_concepts)  # (N, D)
            gat_h = self.gat_layer(raw_h, adj_matrix)      # (N, D)

            # 2. Look up GAT concept representations for interaction sequence
            seq_concept_h = F.embedding(concept_indices, gat_h)  # (B, T, D)

            # 3. Project continuous telemetry
            seq_cont_h = self.continuous_proj(continuous_features)  # (B, T, D)

            # 4. Interaction token fusion
            tokens = seq_concept_h + seq_cont_h  # (B, T, D)

            # 5. Causal temporal encoding
            hidden_states = self.sequence_encoder(tokens, causal_mask=causal_mask)  # (B, T, D)

            # 6. Predict next-item correctness
            logits = self.prediction_head(hidden_states)  # (B, T, 1)
            pred_probs = torch.sigmoid(logits)

            last_state = hidden_states[:, -1, :]  # (B, D)
            return pred_probs, last_state

        def get_concept_mastery(
            self,
            last_state: torch.Tensor,
            adj_matrix: torch.Tensor,
        ) -> torch.Tensor:
            """Extracts derived concept masteries for all curriculum concepts (B, num_concepts)."""
            all_concepts = torch.arange(self.num_concepts, device=last_state.device)
            raw_h = self.concept_embeddings(all_concepts)
            gat_h = self.gat_layer(raw_h, adj_matrix)  # (N, D)

            # For each concept, score affinity with learner state:
            # last_state: (B, D) -> broadcast with gat_h: (N, D)
            B = last_state.size(0)
            N = gat_h.size(0)
            # Interaction: elementwise product (B, N, D)
            fused = last_state.unsqueeze(1) * gat_h.unsqueeze(0)
            masteries = self.mastery_head(fused).squeeze(-1)  # (B, N)
            return masteries

        def extract_root_cause_attention(self, concept_id: int) -> Optional[torch.Tensor]:
            """Extracts attention vector alpha_{k, :} from the GAT layer for root cause tracing."""
            if self.gat_layer.last_attention_weights is None:
                return None
            return self.gat_layer.last_attention_weights[concept_id]
