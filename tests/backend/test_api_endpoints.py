"""Integration tests for all Phase 2 API endpoints:
- Targets, Curricula & DAG Graph
- Profile, Trial Consent, Export & Delete
- Diagnostic Assessment (10 items, easy->hard, ms timers, F12 scoring)
- Special Test Mode (timed blocks, sub-questions biased by correctness/timeout)
- Gemini AI Scored Test Suppression Guard
"""
import datetime as dt
import pytest
from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token
from backend.app.models.core import Assessment, CareerTarget, Concept, Question, Skill, Topic, User


@pytest.fixture
def auth_headers(db_session):
    user = User(
        email="learner@example.com",
        name="Test Learner",
        google_sub="google-sub-learner-1",
        role="learner",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}, user


def test_targets_api(client: TestClient, db_session):
    # Seed 1 career target with skill, topic, concepts
    target = CareerTarget(name="ML Engineering", category="it_career", description="Machine Learning")
    db_session.add(target)
    db_session.commit()

    skill = Skill(target_id=target.id, name="Foundations", weight=1.0)
    db_session.add(skill)
    db_session.commit()

    topic = Topic(skill_id=skill.id, name="Math")
    db_session.add(topic)
    db_session.commit()

    c1 = Concept(topic_id=topic.id, name="Linear Algebra")
    c2 = Concept(topic_id=topic.id, name="Matrix Decompositions")
    db_session.add_all([c1, c2])
    db_session.commit()

    # List targets
    res = client.get("/api/targets")
    assert res.status_code == 200
    targets = res.json()
    assert len(targets) >= 1

    # Target detail
    res_det = client.get(f"/api/targets/{target.id}")
    assert res_det.status_code == 200
    assert res_det.json()["name"] == "ML Engineering"

    # Target graph
    res_graph = client.get(f"/api/targets/{target.id}/graph")
    assert res_graph.status_code == 200
    assert res_graph.json()["is_dag"] is True


def test_profile_and_consent_api(client: TestClient, auth_headers):
    headers, user = auth_headers

    # Get profile
    res = client.get("/api/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "learner@example.com"

    # Update profile with trial consent
    res_update = client.patch(
        "/api/me/profile",
        headers=headers,
        json={
            "current_level": "Intermediate",
            "daily_study_hours": 3.0,
            "trial_consent": True,
        },
    )
    assert res_update.status_code == 200
    data = res_update.json()
    assert data["current_level"] == "Intermediate"
    assert data["trial_consent"] is True

    # Data export
    res_export = client.get("/api/me/export", headers=headers)
    assert res_export.status_code == 200
    assert res_export.json()["user"]["email"] == "learner@example.com"


def test_diagnostic_assessment_flow(client: TestClient, auth_headers, db_session):
    headers, user = auth_headers

    # Create target, skill, topic, concept, and 12 questions
    target = CareerTarget(name="Diagnostic Target", category="it_career")
    db_session.add(target)
    db_session.commit()

    skill = Skill(target_id=target.id, name="Core", weight=1.0)
    db_session.add(skill)
    db_session.commit()

    topic = Topic(skill_id=skill.id, name="Core Topic")
    db_session.add(topic)
    db_session.commit()

    concept = Concept(topic_id=topic.id, name="Core Concept")
    db_session.add(concept)
    db_session.commit()

    for i in range(12):
        q = Question(
            concept_id=concept.id,
            question_text=f"What is the principle of problem {i}?",
            options={"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
            correct_answer="A",
            difficulty_b=-0.5 + (i * 0.1),
            review_status="approved",
        )
        db_session.add(q)
    db_session.commit()

    # Start Diagnostic Assessment (type: "initial")
    res_start = client.post(
        "/api/assessments/start",
        headers=headers,
        json={"type": "initial", "target_id": target.id},
    )
    assert res_start.status_code == 200
    start_data = res_start.json()
    assert start_data["type"] == "initial"
    # EXACTLY 10 QUESTIONS
    assert len(start_data["items"]) == 10
    assessment_id = start_data["assessment_id"]

    # Submit responses
    responses = [
        {
            "question_id": it["question_id"],
            "selected_answer": "A" if idx < 7 else "B",
            "skipped": False,
            "timed_out": False,
            "response_time_ms": 35000,
            "attempt_no": 1,
        }
        for idx, it in enumerate(start_data["items"])
    ]

    res_submit = client.post(
        f"/api/assessments/{assessment_id}/submit",
        headers=headers,
        json={"responses": responses},
    )
    assert res_submit.status_code == 200
    sub_data = res_submit.json()
    assert sub_data["score"] == 70.0
    assert sub_data["correct_count"] == 7
    assert sub_data["total_questions"] == 10
    assert sub_data["signal_mode"] == "gap_score"
    # Cold start flag because learner has < 20 interactions
    assert sub_data["cold_start"] is True
    assert len(sub_data["per_concept"]) == 1
    assert sub_data["per_concept"][0]["concept_name"] == "Core Concept"


def test_special_test_mode_flow(client: TestClient, auth_headers, db_session):
    headers, user = auth_headers

    target = CareerTarget(name="Special Target", category="it_career")
    db_session.add(target)
    db_session.commit()

    skill = Skill(target_id=target.id, name="Special Skill", weight=1.0)
    db_session.add(skill)
    db_session.commit()

    topic = Topic(skill_id=skill.id, name="Special Topic")
    db_session.add(topic)
    db_session.commit()

    concept = Concept(topic_id=topic.id, name="Special Concept")
    db_session.add(concept)
    db_session.commit()

    # Seed questions
    qs = []
    for i in range(10):
        q = Question(
            concept_id=concept.id,
            question_text=f"Special Question {i}?",
            options={"A": "Alpha", "B": "Beta", "C": "Gamma", "D": "Delta"},
            correct_answer="A",
            difficulty_b=0.0,
            review_status="approved",
        )
        db_session.add(q)
        qs.append(q)
    db_session.commit()

    # Start Special Test
    res_start = client.post(
        "/api/assessments/start",
        headers=headers,
        json={"type": "special", "target_id": target.id, "main_count": 5},
    )
    assert res_start.status_code == 200
    data = res_start.json()
    assert data["type"] == "special"
    assert data["time_limit_sec"] == 30
    assert len(data["items"]) == 5
    assessment_id = data["assessment_id"]
    main_item = data["items"][0]

    # Submit Main Question to next-block with timeout
    res_block = client.post(
        f"/api/assessments/{assessment_id}/next-block",
        headers=headers,
        json={
            "assessment_id": assessment_id,
            "block_index": 0,
            "main_response": {
                "question_id": main_item["question_id"],
                "selected_answer": None,
                "skipped": False,
                "timed_out": True,
                "response_time_ms": 30000,
                "attempt_no": 1,
            },
        },
    )
    assert res_block.status_code == 200
    block_data = res_block.json()
    # Expect 3 sub-questions with 20s time limit
    assert len(block_data["sub_questions"]) == 3
    assert block_data["sub_questions"][0]["time_limit_sec"] == 20
    assert block_data["sub_questions"][0]["phase"] == "sub"


def test_gemini_scored_test_suppression(client: TestClient, auth_headers, db_session):
    from unittest.mock import patch
    headers, user = auth_headers

    target = CareerTarget(name="Target Suppression", category="it_career")
    db_session.add(target)
    db_session.commit()

    with patch("backend.app.api.ai.gemini_client.call", return_value="Linear regression models relationships..."):
        # 1. No active test -> Ask Gemini works
        res_ask = client.post(
            "/api/ai/ask",
            headers=headers,
            json={"message": "Explain linear regression"},
        )
        assert res_ask.status_code == 200
        assert res_ask.json()["label"] == "AI-generated"

        # 2. Start a scored test (e.g. initial diagnostic)
        test_assessment = Assessment(
            user_id=user.id,
            type="initial",
            target_id=target.id,
            started_at=dt.datetime.now(dt.timezone.utc),
            completed_at=None,
        )
        db_session.add(test_assessment)
        db_session.commit()

        # 3. Check active test endpoint
        res_active = client.get("/api/assessments/active", headers=headers)
        assert res_active.status_code == 200
        assert res_active.json()["has_active_test"] is True

        # 4. Attempt to call Gemini -> MUST BE REFUSED WITH 403 FORBIDDEN
        res_blocked = client.post(
            "/api/ai/ask",
            headers=headers,
            json={"message": "What is the answer to question 1?"},
        )
        assert res_blocked.status_code == 403
        assert "strictly disabled during active scored tests" in res_blocked.json()["detail"]

        # 5. Complete test -> AI becomes available again
        test_assessment.completed_at = dt.datetime.now(dt.timezone.utc)
        db_session.commit()

        res_restored = client.post(
            "/api/ai/ask",
            headers=headers,
            json={"message": "Now that test is finished, explain the concept."},
        )
        assert res_restored.status_code == 200
