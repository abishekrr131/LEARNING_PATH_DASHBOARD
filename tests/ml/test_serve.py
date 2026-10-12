"""Tests for Standalone ML Inference Microservice (Spec §30)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ml.rct_gat.serve import app, HAS_TORCH


@pytest.fixture
def client():
    return TestClient(app)


def test_model_version_endpoint(client):
    res = client.get("/model/version")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "rct-gat" in data["model_version"]


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed in this environment")
def test_inference_endpoint(client):
    req_data = {
        "concept_indices": [1, 2, 3],
        "continuous_features": [
            [0.0, 2.5, 3.4, 0.0, 0.0, -0.2],
            [1.0, 3.1, 3.4, 0.0, 0.0, 0.1],
            [1.0, 1.8, 3.4, 0.0, 0.0, 0.5],
        ],
    }
    res = client.post("/infer", json=req_data)
    assert res.status_code == 200
    data = res.json()
    assert "predicted_next_prob" in data
    assert 0.0 <= data["predicted_next_prob"] <= 1.0
    assert "concept_mastery" in data


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed in this environment")
def test_root_cause_endpoint(client):
    req_data = {
        "target_concept_id": 10,
        "candidate_prerequisite_ids": [2, 3, 5],
    }
    res = client.post("/root-cause", json=req_data)
    assert res.status_code == 200
    data = res.json()
    assert data["target_concept_id"] == 10
    assert "normalized_entropy" in data
    assert 0.0 <= data["normalized_entropy"] <= 1.0
    assert "two_candidates_recommended" in data
    assert len(data["ranked_candidates"]) == 3
