"""Tests verifying Root-Cause Diagnosis (Area F), Learning Path Per-Skill Progression (Area E),
and Coverage-Based Readiness Invariants (Area C).
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token
from backend.app.models.core import (
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    Question,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    User,
)


@pytest.fixture
def banking_setup(db_session, client: TestClient):
    """Sets up a complete Banking PO target curriculum with topological DAG and questions."""
    target = CareerTarget(
        name="Banking (IBPS PO)",
        category="govt_exam",
        description="Probationary Officer test",
        readiness_threshold=0.75,
    )
    db_session.add(target)
    db_session.commit()

    # 4 skills
    s_quant = Skill(target_id=target.id, name="Quantitative Aptitude", weight=0.35)
    s_reason = Skill(target_id=target.id, name="Reasoning Ability", weight=0.30)
    s_eng = Skill(target_id=target.id, name="English Language", weight=0.20)
    s_ga = Skill(target_id=target.id, name="General & Banking Awareness", weight=0.15)
    db_session.add_all([s_quant, s_reason, s_eng, s_ga])
    db_session.commit()

    # Topics for Quant (Sequential: N=1 -> N=2 -> N=3)
    t_q1 = Topic(skill_id=s_quant.id, name="Percentages and Fractions")
    t_q2 = Topic(skill_id=s_quant.id, name="Profit, Loss and Discount")
    t_q3 = Topic(skill_id=s_quant.id, name="Simple and Compound Interest")

    # Topic for Reasoning
    t_r1 = Topic(skill_id=s_reason.id, name="Syllogisms")

    db_session.add_all([t_q1, t_q2, t_q3, t_r1])
    db_session.commit()

    c_q1 = Concept(topic_id=t_q1.id, name="Base Percentages")
    c_q2 = Concept(topic_id=t_q2.id, name="Profit and Loss Margins")
    c_q3 = Concept(topic_id=t_q3.id, name="Compound Interest Compounding")
    c_r1 = Concept(topic_id=t_r1.id, name="Categorical Syllogism Venns")
    db_session.add_all([c_q1, c_q2, c_q3, c_r1])
    db_session.commit()

    # DAG Dependency: Percentages (c_q1) -> Profit & Loss (c_q2) -> Compound Interest (c_q3)
    dep1 = ConceptDependency(prerequisite_id=c_q1.id, dependent_concept_id=c_q2.id, relation_weight=0.9)
    dep2 = ConceptDependency(prerequisite_id=c_q2.id, dependent_concept_id=c_q3.id, relation_weight=0.85)
    db_session.add_all([dep1, dep2])
    db_session.commit()

    # Question for c_q2 (Profit and Loss)
    q_pl = Question(
        concept_id=c_q2.id,
        question_text="A merchant sells an article for Rs. 240 making a 20% profit. What was the cost price?",
        options_json={"A": "180", "B": "200", "C": "210", "D": "220"},
        correct_answer="B",
        explanation="CP = 240 / 1.2 = 200.",
        difficulty_hint=0.1,
        source="curated",
        review_status="approved",
    )
    db_session.add(q_pl)
    db_session.commit()

    from backend.app.models.core import SubQuestion
    sq1 = SubQuestion(
        parent_question_id=q_pl.id,
        stage="formula",
        order=1,
        stem="Formula Recall: What is the cost price formula when selling at a profit P%?",
        options={"A": "CP = SP / (1 + P/100)", "B": "CP = SP * (1 + P/100)", "C": "CP = SP - P", "D": "CP = SP / P"},
        correct_answer="A",
        time_limit_sec=30,
    )
    sq2 = SubQuestion(
        parent_question_id=q_pl.id,
        stage="substitution",
        order=2,
        stem="Substitution: With SP = 240 and P = 20%, what is the correct substituted expression?",
        options={"A": "240 / 1.20", "B": "240 * 1.20", "C": "240 - 20", "D": "240 / 20"},
        correct_answer="A",
        time_limit_sec=30,
    )
    sq3 = SubQuestion(
        parent_question_id=q_pl.id,
        stage="calculation",
        order=3,
        stem="Timed Calculation (20s): Compute 240 / 1.20:",
        options={"A": "180", "B": "200", "C": "210", "D": "220"},
        correct_answer="B",
        time_limit_sec=20,
    )
    db_session.add_all([sq1, sq2, sq3])
    db_session.commit()

    # User setup
    user = User(
        email="test_learner_po@ibps.internal",
        name="Aspirant Learner",
        role="learner",
    )
    db_session.add(user)
    db_session.commit()

    profile = LearnerProfile(
        user_id=user.id,
        target_id=target.id,
        target_type="govt_exam",
        current_level="Beginner",
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
        "topics": [t_q1, t_q2, t_q3, t_r1],
        "concepts": [c_q1, c_q2, c_q3, c_r1],
        "q_pl": q_pl,
    }


def test_root_cause_sub_questions_generation(banking_setup):
    """Area F: Test generation of the 3 sub-questions in strict order: Formula, Substitution, Timed Calculation."""
    import json
    from unittest.mock import patch
    from ai.gemini_client import GeminiClient

    client = banking_setup["client"]
    headers = banking_setup["headers"]
    q_pl = banking_setup["q_pl"]

    mock_sub_q_json = json.dumps([
        {
            "stage": "formula",
            "stem": "Formula Recall: What is the cost price formula when selling at a profit P%?",
            "options": {"A": "CP = SP / (1 + P/100)", "B": "CP = SP * (1 + P/100)", "C": "CP = SP - P", "D": "CP = SP / P"},
            "correct_option": "A",
            "explanation": "Cost price is SP / (1 + P%).",
        },
        {
            "stage": "substitution",
            "stem": "Substitution: With SP = 240 and P = 20%, what is the correct substituted expression?",
            "options": {"A": "240 / 1.20", "B": "240 * 1.20", "C": "240 - 20", "D": "240 / 20"},
            "correct_option": "A",
            "explanation": "Substitute 240 and 1 + 0.20 = 1.20.",
        },
        {
            "stage": "calculation",
            "stem": "Timed Calculation (20s): Compute 240 / 1.20:",
            "options": {"A": "180", "B": "200", "C": "210", "D": "220"},
            "correct_option": "B",
            "explanation": "240 / 1.2 = 200.",
        },
    ])

    with patch.object(GeminiClient, "is_configured", True), \
         patch("ai.gemini_client.GeminiClient.generate_structured_json", return_value=mock_sub_q_json):
        res = client.post(
            "/api/assessments/root-cause/sub-questions",
            json={"question_id": q_pl.id},
            headers=headers,
        )
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()

    assert data["question_id"] == q_pl.id
    assert "sub_questions" in data
    sub_qs = data["sub_questions"]
    assert len(sub_qs) == 3

    # Check strict stages
    assert sub_qs[0]["stage"] == "formula"
    assert "formula" in sub_qs[0]["stem"].lower() or "formula" in sub_qs[0]["explanation"].lower()
    assert sub_qs[1]["stage"] == "substitution"
    assert sub_qs[2]["stage"] == "calculation"
    assert sub_qs[2]["time_limit_sec"] == 20


def test_root_cause_cognitive_gap_classifications(banking_setup):
    """Area F: Test all 5 cognitive gap classifications from the 3 sub-question stages."""
    client = banking_setup["client"]
    headers = banking_setup["headers"]
    q_pl = banking_setup["q_pl"]

    # 1. Formula wrong -> Formula knowledge gap
    r1 = client.post(
        "/api/assessments/root-cause/evaluate",
        json={
            "question_id": q_pl.id,
            "formula_correct": False,
            "substitution_correct": True,
            "calculation_correct": True,
            "calculation_time_ms": 10000,
        },
        headers=headers,
    ).json()
    assert r1["gap_type"] == "Formula knowledge gap"
    assert r1["action"] == "formula_sheet"
    assert "formula sheet" in r1["study_task"].lower()

    # 2. Formula right, substitution wrong -> Application/setup gap
    r2 = client.post(
        "/api/assessments/root-cause/evaluate",
        json={
            "question_id": q_pl.id,
            "formula_correct": True,
            "substitution_correct": False,
            "calculation_correct": True,
            "calculation_time_ms": 10000,
        },
        headers=headers,
    ).json()
    assert r2["gap_type"] == "Application/setup gap"
    assert r2["action"] == "worked_examples"
    assert "worked examples" in r2["study_task"].lower()

    # 3. Formula and substitution right, calculation wrong -> Calculation accuracy gap
    r3 = client.post(
        "/api/assessments/root-cause/evaluate",
        json={
            "question_id": q_pl.id,
            "formula_correct": True,
            "substitution_correct": True,
            "calculation_correct": False,
            "calculation_time_ms": 10000,
        },
        headers=headers,
    ).json()
    assert r3["gap_type"] == "Calculation accuracy gap"
    assert r3["action"] == "calculation_drills"

    # 4. Calculation right but time above threshold (20s) -> Calculation speed gap
    r4 = client.post(
        "/api/assessments/root-cause/evaluate",
        json={
            "question_id": q_pl.id,
            "formula_correct": True,
            "substitution_correct": True,
            "calculation_correct": True,
            "calculation_time_ms": 25000,  # > 20000ms
        },
        headers=headers,
    ).json()
    assert r4["gap_type"] == "Calculation speed gap"
    assert r4["action"] == "timed_drills"
    assert "timed" in r4["study_task"].lower()

    # 5. All right within time limit -> Careless error
    r5 = client.post(
        "/api/assessments/root-cause/evaluate",
        json={
            "question_id": q_pl.id,
            "formula_correct": True,
            "substitution_correct": True,
            "calculation_correct": True,
            "calculation_time_ms": 12000,
        },
        headers=headers,
    ).json()
    assert r5["gap_type"] == "Careless error"
    assert r5["action"] == "mindful_review"

    # 6. All three fail -> traces upstream prerequisite in DAG
    r6 = client.post(
        "/api/assessments/root-cause/evaluate",
        json={
            "question_id": q_pl.id,
            "formula_correct": False,
            "substitution_correct": False,
            "calculation_correct": False,
            "calculation_time_ms": 25000,
        },
        headers=headers,
    ).json()
    assert r6["all_three_failed"] is True
    assert len(r6["upstream_prerequisites"]) > 0
    # Prerequisite of c_q2 (Profit and Loss) is c_q1 (Base Percentages)
    prereq_names = [p["concept_name"] for p in r6["upstream_prerequisites"]]
    assert "Base Percentages" in prereq_names


def test_learning_path_per_skill_progression(banking_setup, db_session):
    """Area E: Test per-skill progression: demonstrating topic N unlocks and recommends topic N+1 in the SAME skill."""
    client = banking_setup["client"]
    headers = banking_setup["headers"]
    user = banking_setup["user"]
    concepts = banking_setup["concepts"]

    # Initially, user has not demonstrated Base Percentages (c_q1)
    res1 = client.get("/api/learning/path", headers=headers)
    assert res1.status_code == 200
    path_data1 = res1.json()
    assert "skill_paths" in path_data1
    quant_path1 = next(sp for sp in path_data1["skill_paths"] if sp["skill_name"] == "Quantitative Aptitude")
    # First recommendation in Quant is Base Percentages
    assert quant_path1["recommended_concept_name"] == "Base Percentages"

    # Learner demonstrates topic N (Base Percentages) with correct response
    q1 = Question(
        concept_id=concepts[0].id,
        question_text="What is 50% of 200?",
        options_json={"A": "100", "B": "150", "C": "50", "D": "200"},
        correct_answer="A",
        difficulty_hint=-0.5,
        source="curated",
        review_status="approved",
    )
    db_session.add(q1)
    db_session.flush()

    from backend.app.models.core import Assessment
    asmt = Assessment(user_id=user.id, type="practice", target_id=banking_setup["target"].id)
    db_session.add(asmt)
    db_session.flush()

    resp = StudentResponse(
        user_id=user.id,
        assessment_id=asmt.id,
        question_id=q1.id,
        selected_answer="A",
        is_correct=True,
        response_time_ms=10000,
        attempt_no=1,
    )
    db_session.add(resp)
    db_session.commit()

    # Re-fetch learning path: topic N+1 (Profit and Loss Margins) in the SAME skill must now be recommended!
    res2 = client.get("/api/learning/path", headers=headers)
    assert res2.status_code == 200
    path_data2 = res2.json()
    quant_path2 = next(sp for sp in path_data2["skill_paths"] if sp["skill_name"] == "Quantitative Aptitude")
    assert quant_path2["recommended_concept_name"] == "Profit and Loss Margins"
    assert "1 of 3 done" in quant_path2["progress_text"]
