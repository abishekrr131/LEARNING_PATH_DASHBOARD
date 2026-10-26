import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.core.config import settings
from ai.gemini_client import GeminiClient
from tests.backend.test_diagnostic_and_weekly import banking_curriculum, test_user

def test_diagnostic_persistence_and_status(
    client: TestClient, test_user, banking_curriculum, db_session
):
    headers = test_user["headers"]
    target = banking_curriculum["target"]

    # 1. Initially, status should be not_started
    res = client.get("/api/diagnostic/status", headers=headers)
    assert res.status_code == 200
    status_data = res.json()
    assert status_data["is_completed"] is False
    assert status_data["status"] == "not_started"

    # 2. Start diagnostic using question bank fallback
    with patch.object(settings, "ALLOW_BANK_FALLBACK", True), \
         patch("ai.gemini_client.GeminiClient.generate_structured_json", side_effect=Exception("Offline")):
        start_res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)
    assert start_res.status_code == 200
    diag_data = start_res.json()
    assessment_id = diag_data["assessment_id"]

    # 3. Status should now be in_progress
    res = client.get("/api/diagnostic/status", headers=headers)
    assert res.status_code == 200
    status_data = res.json()
    assert status_data["is_completed"] is False
    assert status_data["status"] == "in_progress"
    assert status_data["assessment_id"] == assessment_id

    # 4. Submit diagnostic
    questions = diag_data.get("questions") or diag_data.get("items")
    responses = [
        {"question_id": q["question_id"], "selected_answer": "A", "response_time_ms": 12000, "skipped": False, "attempt_no": 1}
        for q in questions
    ]
    sub_res = client.post(
        "/api/diagnostic/submit",
        json={"assessment_id": assessment_id, "responses": responses},
        headers=headers,
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "completed"

    # 5. Status should now be completed
    res = client.get("/api/diagnostic/status", headers=headers)
    assert res.status_code == 200
    status_data = res.json()
    assert status_data["is_completed"] is True
    assert status_data["status"] == "completed"
    assert status_data["assessment_id"] == assessment_id
    assert status_data["completed_at"] is not None
    assert status_data["total_questions"] == 10
    assert status_data["score"] is not None

    # 6. Attempting to start diagnostic again should be rejected with HTTP 400
    dup_res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)
    assert dup_res.status_code == 400
    assert "already been completed" in dup_res.json()["detail"]

    # 7. Submitting again should be idempotent (succeed with completed status)
    sub2_res = client.post(
        "/api/diagnostic/submit",
        json={"assessment_id": assessment_id, "responses": responses},
        headers=headers,
    )
    assert sub2_res.status_code == 200
    assert sub2_res.json()["status"] == "completed"
