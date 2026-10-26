import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app.models.core import Assessment, Question, StudentResponse, StudentMastery, RootCauseAnalysis
from tests.backend.test_diagnostic_and_weekly import banking_curriculum, test_user

def test_adaptive_prerequisite_sub_questions_flow(
    client: TestClient, test_user, banking_curriculum, db_session
):
    headers = test_user["headers"]
    target = banking_curriculum["target"]
    concepts = banking_curriculum["concepts"]

    # Concept 2 (Profit and Loss) depends on Concept 0 (Percentages) via edge1
    # We find a question on Concept 2 (dependent)
    profit_loss_q = db_session.execute(
        select(Question).where(Question.concept_id == concepts[2].id)
    ).scalars().first()
    assert profit_loss_q is not None

    # Start a practice test
    start_res = client.post(
        "/api/assessments/start",
        json={"type": "practice", "target_id": target.id, "count": 5},
        headers=headers,
    )
    assert start_res.status_code == 200
    asmt_id = start_res.json()["assessment_id"]

    # 1. Learner answers the main question incorrectly
    sub_q_res = client.post(
        "/api/assessments/root-cause/sub-questions",
        json={
            "question_id": profit_loss_q.id,
            "assessment_id": asmt_id,
            "selected_answer": "D",  # Incorrect (correct is "A")
            "response_time_ms": 14000,
            "timed_out": False,
        },
        headers=headers,
    )
    assert sub_q_res.status_code == 200
    data = sub_q_res.json()
    assert data["has_sub_questions"] is True
    assert len(data["sub_questions"]) >= 1
    assert data["parent_response_id"] is not None
    parent_resp_id = data["parent_response_id"]

    # Verify main question response was persisted in database
    main_db_resp = db_session.get(StudentResponse, parent_resp_id)
    assert main_db_resp is not None
    assert main_db_resp.phase == "main"
    assert main_db_resp.is_correct is False
    assert main_db_resp.selected_answer == "D"

    # 2. Learner submits responses to the prerequisite diagnostic sub-questions
    sub_qs = data["sub_questions"]
    sub_responses = [
        {
            "question_id": sq["id"],
            "stage": sq["stage"],
            "selected_answer": sq.get("correct_option", "A"),
            "is_correct": True,
            "response_time_ms": 11000,
        }
        for sq in sub_qs
    ]

    eval_res = client.post(
        "/api/assessments/root-cause/evaluate",
        json={
            "question_id": profit_loss_q.id,
            "assessment_id": asmt_id,
            "parent_response_id": parent_resp_id,
            "formula_correct": True,
            "substitution_correct": True,
            "calculation_correct": True,
            "calculation_time_ms": 11000,
            "sub_responses": sub_responses,
        },
        headers=headers,
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert "gap_type" in eval_data
    assert "study_task" in eval_data

    # Verify sub-responses were persisted and linked to parent attempt
    sub_db_resps = db_session.execute(
        select(StudentResponse).where(StudentResponse.parent_response_id == parent_resp_id)
    ).scalars().all()
    assert len(sub_db_resps) == len(sub_qs)
    for sr in sub_db_resps:
        assert sr.phase == "sub"
        assert sr.parent_response_id == parent_resp_id

    # Verify RootCauseAnalysis record was created with evidence
    rc_db = db_session.execute(
        select(RootCauseAnalysis).where(
            RootCauseAnalysis.user_id == test_user["user"].id,
            RootCauseAnalysis.current_concept_id == profit_loss_q.concept_id,
        )
    ).scalars().first()
    assert rc_db is not None
    assert rc_db.evidence_json is not None
