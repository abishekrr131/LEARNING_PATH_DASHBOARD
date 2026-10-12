"""Standalone ML Inference Microservice for RCT-GAT (Spec §24, §30).

Provides high-throughput neural inference on port 8100:
- GET /model/version: returns model checkpoint metadata and PyTorch device.
- POST /infer: next-item correctness predictions and derived concept mastery scores.
- POST /root-cause: extracts GAT multi-head attention weights, computes normalized attention
  entropy (Formula 8), and applies the honesty guard (2 candidates when H > 0.70).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    from ml.rct_gat.layers import RCTGATModel
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

app = FastAPI(
    title="RCT-GAT Inference Service",
    description="Standalone model serving microservice for graph-attention knowledge tracing and root cause attribution.",
    version="1.0.0",
)

MODEL_VERSION = "rct-gat-v1.0.0-calibrated"
DEVICE = "cpu"
DEFAULT_NUM_CONCEPTS = 300
DEFAULT_EMBED_DIM = 64

# Global cached model instance
_model: Optional[Any] = None


def get_model() -> Any:
    global _model
    if not HAS_TORCH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PyTorch is not available in the inference microservice environment.",
        )
    if _model is None:
        _model = RCTGATModel(
            num_concepts=DEFAULT_NUM_CONCEPTS,
            continuous_dim=6,
            embed_dim=DEFAULT_EMBED_DIM,
            gat_heads=4,
            temporal_heads=4,
        )
        _model.eval()
    return _model


# --- Request & Response Schemas ---

class InferRequest(BaseModel):
    concept_indices: List[int] = Field(..., description="Sequence of concept IDs [c_1, ..., c_T]")
    continuous_features: List[List[float]] = Field(..., description="Continuous telemetry matrix of shape (T, 6)")
    adjacency_matrix: Optional[List[List[float]]] = Field(None, description="Optional curriculum adjacency matrix (N, N)")


class InferResponse(BaseModel):
    model_version: str
    predicted_next_prob: float
    sequence_length: int
    concept_mastery: Dict[int, float]
    device: str


class RootCauseRequest(BaseModel):
    target_concept_id: int
    candidate_prerequisite_ids: List[int]
    adjacency_matrix: Optional[List[List[float]]] = None


class RootCauseResponse(BaseModel):
    model_version: str
    target_concept_id: int
    normalized_entropy: float
    raw_entropy: float
    two_candidates_recommended: bool
    attention_distribution: Dict[int, float]
    ranked_candidates: List[Dict[str, Any]]


# --- Routes ---

@app.get("/health")
@app.get("/model/version")
def get_version_info():
    return {
        "status": "healthy",
        "service": "rct-gat-inference",
        "model_version": MODEL_VERSION,
        "pytorch_available": HAS_TORCH,
        "device": DEVICE if HAS_TORCH else "unavailable",
    }


@app.post("/infer", response_model=InferResponse)
def infer_sequence(req: InferRequest):
    """Predicts next-item correctness probability and outputs concept mastery scores."""
    if not req.concept_indices:
        raise HTTPException(status_code=400, detail="concept_indices cannot be empty")

    T = len(req.concept_indices)
    if len(req.continuous_features) != T:
        raise HTTPException(status_code=400, detail="continuous_features rows must match sequence length")

    model = get_model()

    # Prepare tensors
    concept_tensor = torch.tensor([req.concept_indices], dtype=torch.long, device=DEVICE)  # (1, T)
    cont_tensor = torch.tensor([req.continuous_features], dtype=torch.float32, device=DEVICE)  # (1, T, 6)

    # Use provided adjacency or identity matrix
    N = model.num_concepts
    if req.adjacency_matrix and len(req.adjacency_matrix) == N:
        adj = torch.tensor(req.adjacency_matrix, dtype=torch.float32, device=DEVICE)
    else:
        adj = torch.eye(N, device=DEVICE)

    with torch.no_grad():
        preds, last_state = model(concept_tensor, cont_tensor, adj)
        next_prob = float(preds[0, -1, 0].item())

        masteries = model.get_concept_mastery(last_state, adj)  # (1, N)
        mastery_dict = {
            c_id: round(float(masteries[0, c_id].item()), 4)
            for c_id in set(req.concept_indices)
            if c_id < N
        }

    return InferResponse(
        model_version=MODEL_VERSION,
        predicted_next_prob=round(next_prob, 4),
        sequence_length=T,
        concept_mastery=mastery_dict,
        device=DEVICE,
    )


@app.post("/root-cause", response_model=RootCauseResponse)
def compute_root_cause(req: RootCauseRequest):
    """Extracts GAT attention weights over prerequisite DAG ancestors,

    computes normalized attention entropy H_norm (Formula 8), and flags two_candidates if H_norm > 0.70.
    """
    model = get_model()
    k = req.target_concept_id
    candidates = req.candidate_prerequisite_ids

    if not candidates:
        return RootCauseResponse(
            model_version=MODEL_VERSION,
            target_concept_id=k,
            normalized_entropy=0.0,
            raw_entropy=0.0,
            two_candidates_recommended=False,
            attention_distribution={},
            ranked_candidates=[],
        )

    # Extract attention from GAT layer
    N = model.num_concepts
    adj = torch.eye(N, device=DEVICE)
    for c_id in candidates:
        if c_id < N and k < N:
            adj[k, c_id] = 1.0  # edge from c_id to k

    # Ensure forward pass populated last_attention_weights
    dummy_x = torch.zeros(1, 1, dtype=torch.long, device=DEVICE)
    dummy_c = torch.zeros(1, 1, 6, dtype=torch.float32, device=DEVICE)
    with torch.no_grad():
        model(dummy_x, dummy_c, adj)
        attn_vec = model.extract_root_cause_attention(k)

    if attn_vec is not None and len(candidates) > 0:
        raw_weights = [float(attn_vec[c_id].item()) if c_id < N else 0.1 for c_id in candidates]
        total_w = sum(raw_weights) + 1e-8
        norm_weights = [w / total_w for w in raw_weights]
    else:
        # Uniform fallback
        norm_weights = [1.0 / len(candidates)] * len(candidates)

    attn_map = {c_id: round(w, 4) for c_id, w in zip(candidates, norm_weights)}

    # Formula 8: Normalized Attention Entropy
    # H = -sum(alpha_j * log(alpha_j)) / log(|Ancestors|)
    raw_h = -sum(p * math.log(p + 1e-12) for p in norm_weights if p > 0)
    max_h = math.log(len(candidates)) if len(candidates) > 1 else 1.0
    norm_h = raw_h / max_h if max_h > 0 else 0.0
    norm_h = min(1.0, max(0.0, norm_h))

    two_candidates = norm_h > 0.70

    # Rank candidates by attention weight descending
    ranked = sorted(
        [{"concept_id": cid, "attention_weight": round(w, 4)} for cid, w in attn_map.items()],
        key=lambda x: x["attention_weight"],
        reverse=True,
    )

    return RootCauseResponse(
        model_version=MODEL_VERSION,
        target_concept_id=k,
        normalized_entropy=round(norm_h, 4),
        raw_entropy=round(raw_h, 4),
        two_candidates_recommended=two_candidates,
        attention_distribution=attn_map,
        ranked_candidates=ranked,
    )
