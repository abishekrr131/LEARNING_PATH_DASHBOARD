"""Unit tests verifying Phase 2 bug fixes and Phase 3 hardening:
1. Schedule returns empty list + 200 for user with no attempts
2. New user readiness is null/none (not 0.5)
3. Diagnostic 10-question allocation across skills matches syllabus weights and sums to exactly 10
4. Chatbot prompt includes the specific topic name and user query (not generic)
5. Weak topics returns unassessed status for user with no attempts
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from ai.gemini_client import GeminiClient, load_template
from backend.app.api.ai import resolve_syllabus_context
from backend.app.api.diagnostic import allocate_questions_largest_remainder
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.models.core import (
    CareerTarget,
    Concept,
    LearnerProfile,
    Question,
    Skill,
    Topic,
    User,
)


@pytest.fixture
def learner_client(db_session, client: TestClient):
    """Sets up an authenticated test learner with an assigned career target (Banking IBPS PO)."""
    target = CareerTarget(
        name="Banking (IBPS PO)",
        category="govt_exam",
        description="Probationary Officer exam preparation",
        readiness_threshold=0.75,
    )
    db_session.add(target)
    db_session.commit()

    # Skills with standard IBPS PO syllabus weights
    s_quant = Skill(target_id=target.id, name="Quantitative Aptitude", weight=0.35)
    s_reason = Skill(target_id=target.id, name="Reasoning Ability", weight=0.30)
    s_eng = Skill(target_id=target.id, name="English Language", weight=0.20)
    s_ga = Skill(target_id=target.id, name="General & Banking Awareness", weight=0.15)
    db_session.add_all([s_quant, s_reason, s_eng, s_ga])
    db_session.commit()

    # Topics & Concepts
    t_quant = Topic(skill_id=s_quant.id, name="Percentages and Fractions")
    t_reason = Topic(skill_id=s_reason.id, name="Syllogisms")
    t_eng = Topic(skill_id=s_eng.id, name="Reading Comprehension")
    t_ga = Topic(skill_id=s_ga.id, name="Banking Awareness")
    db_session.add_all([t_quant, t_reason, t_eng, t_ga])
    db_session.commit()

    c_quant = Concept(topic_id=t_quant.id, name="Percentages", description="Percentage calculations and fractions")
    c_reason = Concept(topic_id=t_reason.id, name="Categorical Syllogisms", description="Deductive logic venn diagrams")
    c_eng = Concept(topic_id=t_eng.id, name="Inference Questions", description="Contextual passage reasoning")
    c_ga = Concept(topic_id=t_ga.id, name="Monetary Policy", description="RBI repo rates and liquidity")
    db_session.add_all([c_quant, c_reason, c_eng, c_ga])
    db_session.commit()

    # User and LearnerProfile
    user = User(
        email="new_candidate@ibps.internal",
        name="New Banking Aspirant",
        role="learner",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = LearnerProfile(
        user_id=user.id,
        target_id=target.id,
        target_type="govt_exam",
        current_level="Beginner",
        study_hours_per_day=2.0,
    )
    db_session.add(profile)
    db_session.commit()

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    return {
        "client": client,
        "headers": headers,
        "user": user,
        "target": target,
        "skills": [s_quant, s_reason, s_eng, s_ga],
        "concepts": [c_quant, c_reason, c_eng, c_ga],
    }


def test_schedule_returns_empty_list_for_user_with_no_attempts(learner_client):
    """1. Schedule returns empty list + 200 for user with no attempts."""
    client = learner_client["client"]
    headers = learner_client["headers"]

    res = client.get("/api/schedule", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    data = res.json()
    assert "schedule" in data
    assert isinstance(data["schedule"], list)
    assert len(data["schedule"]) == 0
    assert data["total_count"] == 0
    assert data["completed_count"] == 0
    assert data["pending_count"] == 0
    assert data["overdue_count"] == 0


def test_new_user_readiness_is_null_not_point_five(learner_client):
    """2. New user readiness is null/none (not 0.5)."""
    client = learner_client["client"]
    headers = learner_client["headers"]

    res = client.get("/api/analytics/readiness", headers=headers)
    assert res.status_code == 200

    data = res.json()
    # Must NOT return default prior 0.5 / 50%
    assert data["readiness_score"] in (None, 0.0)
    assert data["readiness_percentage"] in (None, 0)
    assert data["is_assessed"] is False
    assert data["total_attempts"] == 0
    assert data["label"] in ("Not assessed yet", "Take the Initial Diagnostic")

    # Per-skill breakdown must show 0.0 or None for unassessed masteries
    for sk in data["skill_components"]:
        assert sk["mean_mastery"] in (None, 0.0)


def test_diagnostic_10_question_allocation_sums_to_10(learner_client, db_session):
    """3. Diagnostic 10-question allocation across skills matches syllabus weights and sums to exactly 10."""
    skills = learner_client["skills"]
    # Test allocation math (Quant 0.35, Reasoning 0.30, English 0.20, Awareness 0.15)
    quotas = allocate_questions_largest_remainder(skills, total_items=10)

    assert sum(quotas.values()) == 10
    s_map = {s.name: quotas[s.id] for s in skills}
    # Expected largest-remainder allocation for weights [0.35, 0.30, 0.20, 0.15]:
    # 0.35*10=3.5 (b=3, r=0.5 -> gets +1 => 4)
    # 0.30*10=3.0 (b=3, r=0.0 => 3)
    # 0.20*10=2.0 (b=2, r=0.0 => 2)
    # 0.15*10=1.5 (b=1, r=0.5 => 1)
    assert s_map["Quantitative Aptitude"] == 4
    assert s_map["Reasoning Ability"] == 3
    assert s_map["English Language"] == 2
    assert s_map["General & Banking Awareness"] == 1

    # Seed approved questions to satisfy quotas
    concepts = learner_client["concepts"]
    for idx, (s, c) in enumerate(zip(skills, concepts)):
        quota = quotas[s.id]
        for q_idx in range(quota + 2):
            q = Question(
                concept_id=c.id,
                question_text=f"Sample {s.name} item {q_idx}?",
                options={"A": "Alpha", "B": "Beta", "C": "Gamma", "D": "Delta"},
                correct_answer="A",
                difficulty_b=(q_idx * 0.2) - 0.5,
                source="curated",
                review_status="approved",
            )
            db_session.add(q)
    db_session.commit()

    client = learner_client["client"]
    headers = learner_client["headers"]
    target = learner_client["target"]

    # Call POST /api/diagnostic/start with question bank fallback enabled
    with patch.object(settings, "ALLOW_BANK_FALLBACK", True):
        res = client.post("/api/diagnostic/start", headers=headers, json={"target_id": target.id})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    start_data = res.json()

    assert start_data["total_items"] == 10
    assert len(start_data["items"]) == 10

    # Verify questions are ordered easy -> hard
    diffs = [it["difficulty_b"] for it in start_data["items"]]
    for i in range(len(diffs) - 1):
        assert diffs[i] <= diffs[i + 1]


def test_chatbot_prompt_includes_specific_topic_and_user_query(learner_client, db_session):
    """4. Chatbot prompt includes the specific topic name and user query (not generic)."""
    user = learner_client["user"]

    user_query = "Can you explain percentages calculation tricks for banking exams?"
    topic_name, syllabus_metadata, *_ = resolve_syllabus_context(
        db_session, user.id, concept_id=None, user_message=user_query
    )

    # Must resolve specifically to Percentages topic or domain, NOT generic "General Syllabus"
    assert "Percentages" in topic_name
    assert "Banking" in syllabus_metadata

    # Test rendering of tutor_chat template
    tpl = load_template("tutor_chat")
    rendered = tpl.render({
        "topic_name": topic_name,
        "syllabus_metadata": syllabus_metadata,
        "user_message": user_query,
    })

    # Assert rendered prompt includes the specific topic and exact user query
    assert topic_name in rendered
    assert user_query in rendered
    assert "Percentages" in rendered


def test_weak_topics_returns_unassessed_status_for_new_user(learner_client):
    """5. Weak topics returns unassessed status for user with no attempts."""
    client = learner_client["client"]
    headers = learner_client["headers"]

    res = client.get("/api/analytics/gaps", headers=headers)
    assert res.status_code == 200

    data = res.json()
    assert data["total_attempts"] == 0
    assert len(data["gaps"]) > 0

    for item in data["gaps"]:
        assert item["status"] == "unassessed"
        assert item["attempts_count"] == 0
        assert item["accuracy"] is None
        assert item["time_ratio"] is None
        assert item["skip_rate"] is None
        assert item["historical_mastery"] is None
        assert item["gap_score"] is None
        assert item["band"] is None
        assert item["priority"] is None


def test_diagnostic_submit_generates_roadmap_and_root_causes(learner_client, db_session):
    """Verifies submit diagnostic updates mastery, attributes root causes, and generates topological roadmap."""
    client = learner_client["client"]
    headers = learner_client["headers"]
    target = learner_client["target"]
    skills = learner_client["skills"]
    concepts = learner_client["concepts"]

    # Seed dependencies: concept 0 -> concept 1
    from backend.app.models.core import ConceptDependency
    dep = ConceptDependency(prerequisite_id=concepts[0].id, concept_id=concepts[1].id, strength=1.0)
    db_session.add(dep)
    db_session.commit()

    quotas = allocate_questions_largest_remainder(skills, total_items=10)
    for s, c in zip(skills, concepts):
        quota = quotas[s.id]
        for q_idx in range(quota):
            q = Question(
                concept_id=c.id,
                question_text=f"Diag Q {s.name} {q_idx}",
                options={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="A",
                difficulty_b=0.0,
                review_status="approved",
            )
            db_session.add(q)
    db_session.commit()

    with patch.object(settings, "ALLOW_BANK_FALLBACK", True), \
         patch.object(GeminiClient, "is_configured", False):
        start_res = client.post("/api/diagnostic/start", headers=headers, json={"target_id": target.id})
    assert start_res.status_code == 200
    start_data = start_res.json()
    asmt_id = start_data["assessment_id"]

    # Deliberately submit wrong answers
    responses = [
        {
            "question_id": item["question_id"],
            "selected_answer": "B",
            "skipped": False,
            "timed_out": False,
            "response_time_ms": 35000,
            "attempt_no": 1,
        }
        for item in start_data["items"]
    ]

    sub_res = client.post(
        "/api/diagnostic/submit",
        headers=headers,
        json={"assessment_id": asmt_id, "responses": responses},
    )
    assert sub_res.status_code == 200, f"Submit failed: {sub_res.text}"
    sub_data = sub_res.json()

    assert sub_data["score"] == 0.0
    assert len(sub_data["weak_topics"]) > 0
    assert "roadmap" in sub_data
    assert len(sub_data["roadmap"]) > 0
    assert sub_data["readiness_percentage"] is not None

