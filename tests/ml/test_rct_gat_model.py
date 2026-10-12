"""Unit and Invariant Tests for RCT-GAT Model Architecture (Spec §7, §24, §25)."""
from __future__ import annotations

import pytest

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed in this environment")
def test_prerequisite_gat_layer_attention():
    from ml.rct_gat.layers import PrerequisiteGATLayer

    num_concepts = 5
    in_dim = 16
    out_dim = 16
    gat = PrerequisiteGATLayer(in_features=in_dim, out_features=out_dim, num_heads=2)

    # Concept features
    h = torch.randn(num_concepts, in_dim)

    # Simple DAG: 0 -> 1 -> 2, 3 -> 4, with self-loops
    adj = torch.eye(num_concepts)
    adj[1, 0] = 1.0  # 0 is prereq of 1
    adj[2, 1] = 1.0  # 1 is prereq of 2
    adj[4, 3] = 1.0  # 3 is prereq of 4

    out = gat(h, adj)
    assert out.shape == (num_concepts, out_dim)

    attn = gat.last_attention_weights
    assert attn is not None
    assert attn.shape == (num_concepts, num_concepts)

    # Node 0 only has self-loop, so attn[0, 0] must be 1.0, others 0.0
    assert torch.isclose(attn[0, 0], torch.tensor(1.0), atol=1e-4)
    assert torch.isclose(attn[0, 1], torch.tensor(0.0), atol=1e-4)

    # Node 1 has incoming edges from 0 and 1 (self-loop). Their sum must be 1.0
    assert torch.isclose(attn[1, 0] + attn[1, 1], torch.tensor(1.0), atol=1e-4)
    assert torch.isclose(attn[1, 2], torch.tensor(0.0), atol=1e-4)


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed in this environment")
def test_rct_gat_model_forward_and_mastery():
    from ml.rct_gat.layers import RCTGATModel

    num_concepts = 8
    seq_len = 6
    batch_size = 2
    cont_dim = 6
    embed_dim = 32

    model = RCTGATModel(
        num_concepts=num_concepts,
        continuous_dim=cont_dim,
        embed_dim=embed_dim,
        gat_heads=2,
        temporal_heads=2,
    )

    # Inputs
    concept_idx = torch.randint(0, num_concepts, (batch_size, seq_len))
    cont_feats = torch.randn(batch_size, seq_len, cont_dim)
    adj = torch.eye(num_concepts)
    adj[2, 0] = 1.0
    adj[3, 1] = 1.0

    # Forward
    preds, last_state = model(concept_idx, cont_feats, adj)
    assert preds.shape == (batch_size, seq_len, 1)
    assert last_state.shape == (batch_size, embed_dim)

    # Predictions are valid probabilities
    assert (preds >= 0.0).all() and (preds <= 1.0).all()

    # Derived concept masteries for all concepts
    masteries = model.get_concept_mastery(last_state, adj)
    assert masteries.shape == (batch_size, num_concepts)
    assert (masteries >= 0.0).all() and (masteries <= 1.0).all()

    # Root cause attention extraction
    attn_vec = model.extract_root_cause_attention(concept_id=2)
    assert attn_vec is not None
    assert attn_vec.shape == (num_concepts,)
    # Concept 0 was prerequisite of 2, so attn[0] must be > 0
    assert attn_vec[0] > 0.0
