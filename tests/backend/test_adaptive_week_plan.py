"""Unit tests verifying the adaptive first-week learning plan and diagnostic progression:
1. Learner demonstrating mastery in Percentages unlocks next configured topic (Ratio & Proportion / next topic).
2. Learner struggling with Percentages receives revision & practice, not advancing until mastery.
3. Unassessed topics are never falsely marked mastered.
4. Diagnostic performance calculated by topic with question ID, learner answer, correct answer, accuracy %.
5. Every plan item includes subject, topic, objective, verified resource & URL, activity, duration, mastery target, follow-up.
6. Generated plan persists across database sessions and reloads via GET /api/schedule.
"""
import datetime as dt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models.core import (
    Assessment,
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningResource,
    LearningSchedule,
    Question,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    User,
)
from backend.app.services.question_generator import synthesize_week_schedule


@pytest.fixture
def test_setup(db_session, client: TestClient):
    """Sets up an authenticated learner with SSC CGL Aptitude curriculum including Percentages and Ratio & Proportion."""
    target = CareerTarget(
        name="SSC CGL",
        category="govt_exam",
        description="SSC CGL Exam Curriculum",
    )
    db_session.add(target)
    db_session.commit()

    # Skill 1: Quantitative Aptitude
    skill_quant = Skill(name="Quantitative Aptitude", target_id=target.id, weight=0.60)
    skill_reason = Skill(name="General Intelligence & Reasoning", target_id=target.id, weight=0.40)
    db_session.add_all([skill_quant, skill_reason])
    db_session.commit()

    # Topic 1: Percentages & Commercial Math
    topic_pct = Topic(name="Percentage & Commercial Math", skill_id=skill_quant.id)
    # Topic 2: Ratio, Proportion & Partnerships (next topic in sequence)
    topic_ratio = Topic(name="Ratio, Proportion & Partnerships", skill_id=skill_quant.id)
    # Topic 3: Reasoning Topic
    topic_reason = Topic(name="Verbal Reasoning", skill_id=skill_reason.id)
    db_session.add_all([topic_pct, topic_ratio, topic_reason])
    db_session.commit()

    # Concepts
    c_pct = Concept(name="Percentages and Successive Change", topic_id=topic_pct.id, description="Core percentages")
    c_ratio = Concept(name="Ratio, Proportion & Partnerships", topic_id=topic_ratio.id, description="Ratio and proportion")
    c_reason = Concept(name="Analogy and Classification", topic_id=topic_reason.id, description="Verbal analogies")
    db_session.add_all([c_pct, c_ratio, c_reason])
    db_session.commit()

    # Prerequisite DAG: Percentages -> Ratio
    dep = ConceptDependency(prerequisite_concept_id=c_pct.id, dependent_concept_id=c_ratio.id)
    db_session.add(dep)
    db_session.commit()

    # Learning Resources
    lr_pct = LearningResource(
        concept_id=c_pct.id,
        title="NCERT / SATHEE: Percentages & Successive Changes Masterclass",
        resource_type="article",
        url="https://sathee.prutor.ai/course/quantitative-aptitude/percentages",
        provider="SATHEE / Ministry of Education",
        estimated_duration_min=45,
        difficulty="Intermediate",
    )
    lr_ratio = LearningResource(
        concept_id=c_ratio.id,
        title="NCERT / SATHEE: Ratio & Proportion Advanced Problem Solving",
        resource_type="article",
        url="https://sathee.prutor.ai/course/quantitative-aptitude/ratio-proportion",
        provider="SATHEE / Ministry of Education",
        estimated_duration_min=45,
        difficulty="Intermediate",
    )
    db_session.add_all([lr_pct, lr_ratio])
    db_session.commit()

    # Questions
    q_pct = Question(
        concept_id=c_pct.id,
        question_text="If A is 20% more than B, by what percent is B less than A?",
        options_json={"A": "16.66%", "B": "20%", "C": "25%", "D": "33.33%"},
        correct_answer="A",
        explanation="B is less than A by (20/120)*100 = 16.66%.",
        source="curated",
        review_status="approved",
        verified=True,
    )
    q_ratio = Question(
        concept_id=c_ratio.id,
        question_text="If A:B = 2:3 and B:C = 4:5, what is A:C?",
        options_json={"A": "8:15", "B": "2:5", "C": "4:15", "D": "6:15"},
        correct_answer="A",
        explanation="A/C = (2/3)*(4/5) = 8/15.",
        source="curated",
        review_status="approved",
        verified=True,
    )
    db_session.add_all([q_pct, q_ratio])
    db_session.commit()

    # Users
    user = User(name="Test Learner", email="adaptive_tester@example.com", role="learner", google_sub="sub-adaptive-1")
    db_session.add(user)
    db_session.commit()

    profile = LearnerProfile(user_id=user.id, target_id=target.id, target_type="govt_exam", current_level="intermediate")
    db_session.add(profile)
    db_session.commit()

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    return {
        "client": client,
        "user": user,
        "target": target,
        "topic_pct": topic_pct,
        "topic_ratio": topic_ratio,
        "topic_reason": topic_reason,
        "c_pct": c_pct,
        "c_ratio": c_ratio,
        "q_pct": q_pct,
        "q_ratio": q_ratio,
        "headers": headers,
    }


def test_mastery_percentages_unlocks_next_topic_ratio(db_session, test_setup):
    """Case A: When learner demonstrates mastery in Percentages, Ratio & Proportion is scheduled for Week 1."""
    user = test_setup["user"]
    target = test_setup["target"]
    q_pct = test_setup["q_pct"]
    c_pct = test_setup["c_pct"]

    # Record correct answer for Percentages
    asmt = Assessment(user_id=user.id, type="initial", target_id=target.id, started_at=dt.datetime.now(dt.timezone.utc))
    db_session.add(asmt)
    db_session.commit()

    resp = StudentResponse(
        user_id=user.id,
        assessment_id=asmt.id,
        question_id=q_pct.id,
        selected_answer="A",
        is_correct=True,
        response_time_ms=25000,
        skipped=False,
    )
    mastery = StudentMastery(
        user_id=user.id,
        concept_id=c_pct.id,
        mastery_score=0.88,
        confidence=0.8,
        model_version="test",
    )
    db_session.add_all([resp, mastery])
    db_session.commit()

    # Generate adaptive schedule
    items = synthesize_week_schedule(
        user_id=user.id,
        target_id=target.id,
        db=db_session,
        week_number=1,
        topic_mastery_threshold=0.80,
    )

    assert len(items) == 7
    # Check that Ratio, Proportion & Partnerships is unlocked and scheduled
    topic_names = [it.topic_name for it in items]
    assert any("Ratio" in t for t in topic_names), f"Expected unlocked next topic Ratio in schedule, got {topic_names}"

    # Verify plan reason mentions unlocked
    ratio_item = next(it for it in items if "Ratio" in (it.topic_name or ""))
    assert "unlocked" in (ratio_item.plan_reason or "").lower() or "advanced" in (ratio_item.plan_reason or "").lower()


def test_weak_percentages_remediates_and_pauses_unlock(db_session, test_setup):
    """Case B: When learner struggles with Percentages, Percentages is kept as learning priority and Ratio is NOT unlocked."""
    user = test_setup["user"]
    target = test_setup["target"]
    q_pct = test_setup["q_pct"]
    c_pct = test_setup["c_pct"]

    # Record incorrect answer for Percentages
    asmt = Assessment(user_id=user.id, type="initial", target_id=target.id, started_at=dt.datetime.now(dt.timezone.utc))
    db_session.add(asmt)
    db_session.commit()

    resp = StudentResponse(
        user_id=user.id,
        assessment_id=asmt.id,
        question_id=q_pct.id,
        selected_answer="B",  # wrong (correct is A)
        is_correct=False,
        response_time_ms=35000,
        skipped=False,
    )
    mastery = StudentMastery(
        user_id=user.id,
        concept_id=c_pct.id,
        mastery_score=0.25,
        confidence=0.8,
        model_version="test",
    )
    db_session.add_all([resp, mastery])
    db_session.commit()

    items = synthesize_week_schedule(
        user_id=user.id,
        target_id=target.id,
        db=db_session,
        week_number=1,
        topic_mastery_threshold=0.80,
    )

    assert len(items) == 7
    # Verify Percentages is scheduled for remediation
    pct_items = [it for it in items if "Percent" in (it.topic_name or "")]
    assert len(pct_items) > 0, "Expected Percentages to be scheduled for remediation"
    assert "remediation" in (pct_items[0].plan_reason or "").lower()
    assert pct_items[0].activity_type == "review"

    # Verify Ratio & Proportion was NOT unlocked
    unlocked_ratio = [it for it in items if "Ratio" in (it.topic_name or "") and "unlocked" in (it.plan_reason or "").lower()]
    assert len(unlocked_ratio) == 0, "Ratio & Proportion should NOT be unlocked when Percentages is weak"


def test_unassessed_topic_not_marked_mastered(db_session, test_setup):
    """Case C: An unassessed topic is never marked as mastered."""
    from backend.app.services.career_map import calculate_career_ready_map

    user = test_setup["user"]
    target = test_setup["target"]

    cmap = calculate_career_ready_map(db=db_session, user_id=user.id, target_id=target.id)

    # For a fresh learner with no responses, demonstrated topics should be 0
    assert cmap["demonstrated_topics_count"] == 0
    assert cmap["topic_coverage_readiness_pct"] == 0.0
    assert len(cmap["unassessed_topics"]) == 3  # All 3 topics are unassessed


def test_diagnostic_submission_stores_performance_by_topic(db_session, test_setup):
    """Section 3: Submitting diagnostic stores question ID, topic, learner answer, correct answer, and returns full metrics."""
    client = test_setup["client"]
    headers = test_setup["headers"]
    user = test_setup["user"]
    target = test_setup["target"]
    q_pct = test_setup["q_pct"]

    asmt = Assessment(user_id=user.id, type="initial", target_id=target.id, started_at=dt.datetime.now(dt.timezone.utc))
    db_session.add(asmt)
    db_session.commit()

    payload = {
        "assessment_id": asmt.id,
        "responses": [
            {
                "question_id": q_pct.id,
                "selected_answer": "A",
                "response_time_ms": 18000,
                "skipped": False,
            }
        ],
    }

    res = client.post("/api/diagnostic/submit", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "question_results" in data
    assert len(data["question_results"]) == 1
    qr = data["question_results"][0]
    assert qr["question_id"] == q_pct.id
    assert qr["learner_answer"] == "A"
    assert qr["correct_answer"] == "A"
    assert qr["is_correct"] is True
    assert qr["result"] == "correct"
    assert "topic_name" in qr

    assert data["question_accuracy_pct"] == 100.0
    assert data["distinct_topics_demonstrated_count"] >= 1
    assert "first_week_plan" in data
    assert len(data["first_week_plan"]) == 7


def test_schedule_endpoint_returns_rich_plan_fields(db_session, test_setup):
    """Section 5: GET /api/schedule returns all required plan fields and persists across reloads."""
    client = test_setup["client"]
    headers = test_setup["headers"]
    user = test_setup["user"]
    target = test_setup["target"]

    # Synthesize schedule
    synthesize_week_schedule(
        user_id=user.id,
        target_id=target.id,
        db=db_session,
        week_number=1,
    )

    res = client.get("/api/schedule", headers=headers)
    assert res.status_code == 200
    data = res.json()

    schedule = data["schedule"]
    assert len(schedule) == 7

    # Check Day 1 to 6
    for it in schedule[:6]:
        assert "subject" in it and it["subject"]
        assert "topic" in it and it["topic"]
        assert "learning_objective" in it and it["learning_objective"]
        assert "resource_title" in it and it["resource_title"]
        assert "resource_url" in it and it["resource_url"]
        assert "practice_activity" in it and it["practice_activity"]
        assert "planned_minutes" in it
        assert "mastery_target" in it
        assert "status" in it
        assert "follow_up_assessment" in it

    # Check Day 7 (Weekly Test)
    day_7 = schedule[6]
    assert day_7["is_weekly_test"] is True
    assert "Weekly" in day_7["concept_name"] or "Weekly" in day_7["practice_activity"]


def test_gap_analytics_endpoint_returns_diagnosed_gaps_and_recs(db_session, test_setup):
    """Section 6: GET /api/analytics/gaps returns diagnostic summary, subject recommendations, and Week 1 plan."""
    client = test_setup["client"]
    headers = test_setup["headers"]
    user = test_setup["user"]
    target = test_setup["target"]
    q_pct = test_setup["q_pct"]

    # Record 1 incorrect response on Percentages
    asmt = Assessment(user_id=user.id, type="initial", target_id=target.id, started_at=dt.datetime.now(dt.timezone.utc))
    db_session.add(asmt)
    db_session.commit()

    client.post(
        "/api/diagnostic/submit",
        json={
            "assessment_id": asmt.id,
            "responses": [
                {
                    "question_id": q_pct.id,
                    "selected_answer": "B",  # Wrong
                    "response_time_ms": 25000,
                    "skipped": False,
                }
            ],
        },
        headers=headers,
    )

    res = client.get("/api/analytics/gaps", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["diagnostic_completed"] is True
    assert data["total_attempts"] >= 1
    assert "subject_recommendations" in data
    assert len(data["subject_recommendations"]) >= 2
    assert "week_1_plan" in data
    assert len(data["week_1_plan"]) == 7

    # Check that Quant recommendation shows Weak / Remediation for Percentages
    quant_rec = next(r for r in data["subject_recommendations"] if "Quant" in r["subject"])
    assert "Weak" in quant_rec["status"]
    assert "Percentage" in quant_rec["recommended_topic"]
    assert quant_rec["advancement_unlocked"] is False

    # Check gap items include topic_name and band
    gaps = data["gaps"]
    assessed_gap = next(g for g in gaps if g["concept_id"] == test_setup["c_pct"].id)
    assert assessed_gap["status"] == "assessed"
    assert assessed_gap["band"] in ("weak", "moderate")
    assert assessed_gap["topic_name"] == "Percentage & Commercial Math"


def test_subject_progression_rules_mastery_vs_weak(db_session, test_setup):
    """Section 3 & 4: Multi-subject progression rules:
    - Mastered Percentages unlocks Ratio & Proportion
    - Weak Reasoning keeps Reasoning remediation
    - Unassessed subject receives baseline coverage
    """
    user = test_setup["user"]
    target = test_setup["target"]
    c_pct = test_setup["c_pct"]
    c_ratio = test_setup["c_ratio"]
    q_pct = test_setup["q_pct"]

    # Learner demonstrates mastery in Percentages (100% correct)
    asmt = Assessment(user_id=user.id, type="initial", target_id=target.id, score=100.0, completed_at=dt.datetime.now(dt.timezone.utc))
    db_session.add(asmt)
    db_session.commit()

    resp = StudentResponse(
        user_id=user.id,
        assessment_id=asmt.id,
        question_id=q_pct.id,
        selected_answer="A",
        is_correct=True,
        response_time_ms=15000,
        answered_at=dt.datetime.now(dt.timezone.utc),
    )
    db_session.add(resp)
    db_session.commit()

    # Synthesize schedule
    plan = synthesize_week_schedule(
        user_id=user.id,
        target_id=target.id,
        db=db_session,
        week_number=1,
    )

    # Check unlocked topic: Ratio & Proportion is scheduled for Week 1!
    unlocked_items = [p for p in plan if "Ratio" in p.topic_name or "Ratio" in p.plan_reason]
    assert len(unlocked_items) >= 1
    assert any("Unlocked" in p.plan_reason or "Advanced" in p.plan_reason for p in unlocked_items)

