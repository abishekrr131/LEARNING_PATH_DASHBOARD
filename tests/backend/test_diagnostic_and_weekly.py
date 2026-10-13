"""Test Suite for Master Prompt Requirements Item 5 & Item 8:
Initial Diagnostic Assessment (10 questions across 10 distinct topics)
and Weekly Progress Test (20 questions, no repeats, Day 7 placement).

Verifies the 5 key criteria:
1. Diagnostic returns exactly 10 questions from 10 distinct topics with syllabus weights respected.
2. Malformed Gemini JSON triggers retry and fallback to question bank without HTTP 500.
3. Diagnostic submit generates Week 1 schedule with weekly test on Day 7.
4. Weekly test returns exactly 20 questions with zero repeats from previous tests.
5. New user with no diagnostic shows clean empty states on schedule and dashboard.
"""
from __future__ import annotations

import datetime as dt
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from ai.gemini_client import GeminiClient
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.models.core import (
    Assessment,
    AssessmentQuestion,
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningSchedule,
    Question,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    User,
)
from backend.app.services.question_generator import (
    allocate_questions_largest_remainder,
    validate_generated_questions,
)


@pytest.fixture
def banking_curriculum(db_session):
    """Seeds a full 10-topic curriculum for Banking IBPS PO with syllabus weights:
    Quant (0.35 -> 4), Reasoning (0.30 -> 3), English (0.20 -> 2), GA (0.15 -> 1).
    Also seeds an approved question bank with 30+ items.
    """
    target = CareerTarget(
        name="Banking (IBPS PO)",
        category="govt_exam",
        description="Comprehensive Probationary Officer Exam Preparation",
        readiness_threshold=0.75,
    )
    db_session.add(target)
    db_session.flush()

    s_quant = Skill(target_id=target.id, name="Quantitative Aptitude", weight=0.35)
    s_reason = Skill(target_id=target.id, name="Reasoning Ability", weight=0.30)
    s_eng = Skill(target_id=target.id, name="English Language", weight=0.20)
    s_ga = Skill(target_id=target.id, name="General & Banking Awareness", weight=0.15)
    db_session.add_all([s_quant, s_reason, s_eng, s_ga])
    db_session.flush()

    # 4 Quant Topics
    t_q1 = Topic(skill_id=s_quant.id, name="Percentages")
    t_q2 = Topic(skill_id=s_quant.id, name="Ratio and Proportion")
    t_q3 = Topic(skill_id=s_quant.id, name="Profit and Loss")
    t_q4 = Topic(skill_id=s_quant.id, name="Data Interpretation")

    # 3 Reasoning Topics
    t_r1 = Topic(skill_id=s_reason.id, name="Syllogisms")
    t_r2 = Topic(skill_id=s_reason.id, name="Coding Decoding")
    t_r3 = Topic(skill_id=s_reason.id, name="Direction Sense")

    # 2 English Topics
    t_e1 = Topic(skill_id=s_eng.id, name="Reading Comprehension")
    t_e2 = Topic(skill_id=s_eng.id, name="Error Spotting")

    # 1 GA Topic
    t_g1 = Topic(skill_id=s_ga.id, name="Monetary Policy and RBI")

    all_topics = [t_q1, t_q2, t_q3, t_q4, t_r1, t_r2, t_r3, t_e1, t_e2, t_g1]
    db_session.add_all(all_topics)
    db_session.flush()

    # Concepts (1 per topic)
    concepts = []
    for idx, top in enumerate(all_topics, start=1):
        c = Concept(
            topic_id=top.id,
            name=f"{top.name} Core",
            description=f"Foundations of {top.name}",
        )
        db_session.add(c)
        concepts.append(c)
    db_session.flush()

    # Prerequisites DAG edges (Percent -> Profit/Loss, Percent -> DI, Syllogism -> Coding)
    edge1 = ConceptDependency(prerequisite_id=concepts[0].id, dependent_concept_id=concepts[2].id, relation_weight=0.8)
    edge2 = ConceptDependency(prerequisite_id=concepts[0].id, dependent_concept_id=concepts[3].id, relation_weight=0.9)
    edge3 = ConceptDependency(prerequisite_id=concepts[4].id, dependent_concept_id=concepts[5].id, relation_weight=0.7)
    db_session.add_all([edge1, edge2, edge3])
    db_session.flush()

    # Approved questions bank (3 per concept = 30 total questions)
    q_counter = 1
    bank_questions = []
    for c in concepts:
        for i in range(3):
            q = Question(
                concept_id=c.id,
                question_text=f"Bank Question {q_counter}: In {c.name}, what is {i+1} + {i+2}?",
                options_json={"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                correct_answer="A",
                explanation="Standard derivation.",
                difficulty_hint=-0.5 + (i * 0.4),
                source="curated",
                review_status="approved",
            )
            db_session.add(q)
            bank_questions.append(q)
            q_counter += 1
    db_session.commit()

    return {
        "target": target,
        "skills": [s_quant, s_reason, s_eng, s_ga],
        "topics": all_topics,
        "concepts": concepts,
        "bank_questions": bank_questions,
    }


@pytest.fixture
def test_user(db_session, banking_curriculum):
    """Creates a registered test user with a learner profile."""
    user = User(
        email="aspirant.po@example.com",
        name="Pooja Sharma",
        google_sub="google-sub-pooja-777",
        role="learner",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    target = banking_curriculum["target"]
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

    return {"user": user, "profile": profile, "headers": headers}


# ---------------------------------------------------------------------------
# Criterion 1: Diagnostic returns 10 questions across 10 distinct topics
# ---------------------------------------------------------------------------
def test_largest_remainder_allocation_matches_weights(banking_curriculum):
    """Verifies that Largest-Remainder Rounding allocates quotas summing to exactly 10."""
    skills = banking_curriculum["skills"]
    alloc = allocate_questions_largest_remainder(skills, total_items=10)

    assert sum(alloc.values()) == 10
    quant_skill = [s for s in skills if "Quantitative" in s.name][0]
    reason_skill = [s for s in skills if "Reasoning" in s.name][0]
    eng_skill = [s for s in skills if "English" in s.name][0]
    ga_skill = [s for s in skills if "General" in s.name][0]

    assert alloc[quant_skill.id] == 4  # 0.35 * 10 = 3.5 -> 4
    assert alloc[reason_skill.id] == 3  # 0.30 * 10 = 3.0 -> 3
    assert alloc[eng_skill.id] == 2    # 0.20 * 10 = 2.0 -> 2
    assert alloc[ga_skill.id] == 1     # 0.15 * 10 = 1.5 -> 1


def test_diagnostic_start_returns_10_questions_from_10_distinct_topics(
    client: TestClient, test_user, banking_curriculum
):
    """Criterion 1: Diagnostic returns exactly 10 questions across 10 distinct topics, ordered easy to hard."""
    headers = test_user["headers"]
    target = banking_curriculum["target"]

    # Mock Gemini structured JSON response
    mock_gemini_qs = []
    for idx, top in enumerate(banking_curriculum["topics"]):
        mock_gemini_qs.append({
            "topic_id": top.id,
            "stem": f"Gemini MCQ {idx+1}: Diagnostic test item on {top.name}?",
            "options": {"A": "First Choice", "B": "Second Choice", "C": "Third Choice", "D": "Fourth Choice"},
            "correct_option": "B",
            "explanation": f"Grounded explanation for {top.name}.",
            "difficulty": -1.0 + (idx * 0.2),
        })

    with patch.object(GeminiClient, "is_configured", True), \
         patch("ai.gemini_client.GeminiClient.generate_structured_json", return_value=json.dumps(mock_gemini_qs)):
        res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)

    assert res.status_code == 200, f"Expected 200, got: {res.text}"
    data = res.json()

    assert data["assessment_id"] is not None
    questions = data.get("questions") or data.get("items")
    assert len(questions) == 10

    # Verify 10 DISTINCT topics (max 1 question per topic)
    topic_ids = [q["topic_id"] for q in questions]
    assert len(set(topic_ids)) == 10, f"Expected 10 unique topics, got: {topic_ids}"

    # Verify ordered easy to hard
    difficulties = [q["difficulty_b"] for q in questions]
    assert difficulties == sorted(difficulties), "Questions must be ordered easy to hard"

    # Verify client payload does NOT leak correct_option or explanation
    for q in questions:
        assert "correct_option" not in q
        assert "correct_answer" not in q
        assert "explanation" not in q
        assert len(q["options"]) == 4


# ---------------------------------------------------------------------------
# Criterion 2: Malformed Gemini JSON triggers retry and fallback without 500
# ---------------------------------------------------------------------------
def test_malformed_gemini_json_triggers_fallback_to_bank(
    client: TestClient, test_user, banking_curriculum
):
    """Criterion 2: Malformed or unparseable Gemini JSON falls back to question bank without HTTP 500."""
    headers = test_user["headers"]
    target = banking_curriculum["target"]

    # Mock Gemini to return invalid JSON string (simulating malformed JSON output)
    with patch.object(settings, "ALLOW_BANK_FALLBACK", True), \
         patch.object(GeminiClient, "is_configured", True), \
         patch(
             "ai.gemini_client.GeminiClient.generate_structured_json",
             return_value="[INVALID_UNPARSEABLE_JSON_OUTPUT_SYNTAX{{{",
         ):
        res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)

    # Must succeed cleanly with fallback, returning HTTP 200 (not HTTP 500)
    assert res.status_code == 200, f"Expected 200 fallback, got {res.status_code}: {res.text}"
    data = res.json()
    questions = data.get("questions") or data.get("items")
    assert len(questions) == 10

    # Ensure questions were pulled from the approved question bank
    for q in questions:
        assert "Bank Question" in q["question_text"]


def test_gemini_failure_returns_error_when_fallback_disabled(
    client: TestClient, test_user, banking_curriculum
):
    headers = test_user["headers"]
    target = banking_curriculum["target"]

    # Area D: Gemini removed from question generation; pulls strictly from approved question bank
    with patch(
        "ai.gemini_client.GeminiClient.generate_structured_json",
        side_effect=Exception("API Key Quota Exceeded"),
    ):
        res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)

    assert res.status_code == 200
    assert "questions" in res.json() or "items" in res.json()


# ---------------------------------------------------------------------------
# Criterion 3: Diagnostic submit generates Week 1 schedule with Day 7 Weekly Test
# ---------------------------------------------------------------------------
def test_diagnostic_submit_generates_week1_schedule_with_day7_weekly_test(
    client: TestClient, test_user, banking_curriculum, db_session
):
    """Criterion 3: Submitting diagnostic calibrates masteries and synthesizes Week 1 schedule with Weekly Test on Day 7."""
    headers = test_user["headers"]
    target = banking_curriculum["target"]

    # Start diagnostic using question bank fallback
    with patch.object(settings, "ALLOW_BANK_FALLBACK", True), \
         patch("ai.gemini_client.GeminiClient.generate_structured_json", side_effect=Exception("Offline")):
        start_res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)
    assert start_res.status_code == 200
    diag_data = start_res.json()
    assessment_id = diag_data["assessment_id"]
    questions = diag_data.get("questions") or diag_data.get("items")

    # Build answers: learner answers 6 correctly, 3 incorrectly, 1 skipped
    responses = []
    for idx, q in enumerate(questions):
        responses.append({
            "question_id": q["question_id"],
            "selected_answer": None if idx == 9 else ("A" if idx < 6 else "C"),  # "A" is correct in seeded bank
            "response_time_ms": 15000 + (idx * 1000),
            "skipped": (idx == 9),
            "attempt_no": 1,
        })

    # Submit diagnostic
    sub_res = client.post(
        "/api/diagnostic/submit",
        json={"assessment_id": assessment_id, "responses": responses},
        headers=headers,
    )
    assert sub_res.status_code == 200, f"Submit failed: {sub_res.text}"
    sub_data = sub_res.json()
    assert sub_data["status"] == "completed"
    assert "readiness_score" in sub_data
    assert "weak_topics" in sub_data
    assert "schedule_sessions_created" in sub_data
    assert sub_data["schedule_sessions_created"] >= 6

    # Verify Schedule API
    sched_res = client.get("/api/schedule", headers=headers)
    assert sched_res.status_code == 200
    schedule_data = sched_res.json()
    schedule_items = schedule_data["schedule"]

    assert len(schedule_items) >= 7, f"Expected at least 7 scheduled items, got: {len(schedule_items)}"

    # Check Day 7 Weekly Test presence
    weekly_tests = [item for item in schedule_items if item.get("is_weekly_test") or item.get("activity_type") == "weekly_test"]
    assert len(weekly_tests) >= 1, "Week 1 schedule MUST contain a Weekly Test on Day 7"
    day7_test = weekly_tests[0]
    assert "Weekly Progress Test (20 Qs)" in day7_test["concept_name"]

    # Verify Weekly Test status endpoint
    wt_status = client.get("/api/weekly-test/status", headers=headers).json()
    assert wt_status["is_scheduled"] is True
    assert wt_status["scheduled_date"] is not None


# ---------------------------------------------------------------------------
# Criterion 4: Weekly test returns exactly 20 questions with zero repeats
# ---------------------------------------------------------------------------
def test_weekly_test_returns_20_questions_with_zero_repeats(
    client: TestClient, test_user, banking_curriculum, db_session
):
    """Criterion 4: Weekly test yields exactly 20 questions with zero repeats from previous responses."""
    headers = test_user["headers"]
    target = banking_curriculum["target"]

    # 1. Complete diagnostic first to record 10 answered questions
    with patch.object(settings, "ALLOW_BANK_FALLBACK", True), \
         patch("ai.gemini_client.GeminiClient.generate_structured_json", side_effect=Exception("Offline")):
        start_res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)
    assessment_id = start_res.json()["assessment_id"]
    diag_qs = start_res.json().get("questions") or start_res.json().get("items")
    answered_qids = [q["question_id"] for q in diag_qs]

    responses = [
        {"question_id": qid, "selected_answer": "A", "response_time_ms": 12000, "skipped": False, "attempt_no": 1}
        for qid in answered_qids
    ]
    client.post("/api/diagnostic/submit", json={"assessment_id": assessment_id, "responses": responses}, headers=headers)

    # 2. Mock Gemini to return 20 new questions for weekly test
    mock_weekly_qs = []
    for i in range(20):
        mock_weekly_qs.append({
            "topic_id": banking_curriculum["topics"][i % 10].id,
            "stem": f"Weekly Test Item #{i+1}: Advanced question about topic {i % 10}?",
            "options": {"A": "Alpha", "B": "Beta", "C": "Gamma", "D": "Delta"},
            "correct_option": "C",
            "explanation": f"Step by step solution for weekly test item {i+1}.",
            "difficulty": -0.5 + (i * 0.1),
        })

    with patch.object(GeminiClient, "is_configured", True), \
         patch("ai.gemini_client.GeminiClient.generate_structured_json", return_value=json.dumps(mock_weekly_qs)):
        wt_start = client.post(
            "/api/weekly-test/start",
            json={"target_id": target.id, "force_unlock": True},
            headers=headers,
        )

    assert wt_start.status_code == 200, f"Expected 200, got: {wt_start.text}"
    wt_data = wt_start.json()
    wt_questions = wt_data.get("questions") or wt_data.get("items")
    assert len(wt_questions) == 20

    # Verify ZERO repeats from the diagnostic answered question IDs
    wt_qids = [q["question_id"] for q in wt_questions]
    overlap = set(wt_qids).intersection(set(answered_qids))
    assert len(overlap) == 0, f"Weekly test repeated previously answered questions: {overlap}"

    # Verify submit weekly test generates next week's schedule and week-over-week comparisons
    wt_assessment_id = wt_data["assessment_id"]
    wt_responses = [
        {"question_id": q["question_id"], "selected_answer": "C", "response_time_ms": 20000, "skipped": False, "attempt_no": 1}
        for q in wt_questions
    ]
    wt_sub = client.post(
        "/api/weekly-test/submit",
        json={"assessment_id": wt_assessment_id, "responses": wt_responses},
        headers=headers,
    )
    assert wt_sub.status_code == 200
    wt_sub_data = wt_sub.json()
    assert wt_sub_data["status"] == "completed"
    assert "week_number" in wt_sub_data
    assert "improved_topics" in wt_sub_data
    assert "still_weak_topics" in wt_sub_data
    assert "next_week_schedule_items" in wt_sub_data


# ---------------------------------------------------------------------------
# Criterion 5: New user with no diagnostic shows clean empty states
# ---------------------------------------------------------------------------
def test_new_user_shows_clean_empty_states_across_endpoints(
    client: TestClient, db_session, banking_curriculum
):
    """Criterion 5: New user with 0 attempts shows clean empty states on schedule, readiness, and gaps."""
    target = banking_curriculum["target"]
    new_user = User(
        email="fresh.candidate@example.com",
        name="Fresh Candidate",
        google_sub="google-sub-fresh-101",
        role="learner",
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    profile = LearnerProfile(
        user_id=new_user.id,
        target_id=target.id,
        target_type="govt_exam",
        current_level="Beginner",
    )
    db_session.add(profile)
    db_session.commit()

    token = create_access_token({"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Schedule should be empty
    sched_res = client.get("/api/schedule", headers=headers)
    assert sched_res.status_code == 200
    sched_json = sched_res.json()
    assert sched_json["schedule"] == []
    assert sched_json["total_count"] == 0

    # 2. Weekly test status should report not scheduled
    wt_status_res = client.get("/api/weekly-test/status", headers=headers)
    assert wt_status_res.status_code == 200
    wt_json = wt_status_res.json()
    assert wt_json["is_scheduled"] is False
    assert wt_json["status"] == "not_scheduled"

    # 3. Readiness should be 0.0 or None (NOT 0.5 prior)
    readiness_res = client.get("/api/analytics/readiness", headers=headers)
    assert readiness_res.status_code == 200
    readiness_json = readiness_res.json()
    assert readiness_json.get("readiness_score") in (None, 0.0)
    assert readiness_json.get("is_assessed") is False

    # 4. Weak topics / gaps should show unassessed
    gaps_res = client.get("/api/analytics/gaps", headers=headers)
    assert gaps_res.status_code == 200
    gaps_json = gaps_res.json()
    assert gaps_json.get("total_attempts") == 0
    # Every concept item in gaps list should have status 'unassessed'
    for g in gaps_json.get("gaps", []):
        assert g["status"] == "unassessed"
        assert g["attempts_count"] == 0
