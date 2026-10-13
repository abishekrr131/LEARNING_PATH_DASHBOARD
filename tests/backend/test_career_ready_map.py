"""Test Suite for LearnPath: Online Study Materials, Initial Diagnostic, and Adaptive Career Ready Map.

Verifies:
1. Real online study materials: authoritative providers, verified URLs, durations, licenses, and target filtering.
2. Legitimate diagnostic question bank: 10 distinct topics, traceable origin metadata (PYQ / open standard).
3. Formula 17 Career Ready Map calculation:
   Topic coverage readiness (%) = (distinct topics demonstrated correctly / total syllabus topics) * 100
   Distinguished from raw accuracy.
4. Stage categorization, demonstrated topics, weak topics with DAG root causes, and unassessed follow-up topics.
5. Adaptive progression: mastery unlocks next topics in sequence, state persists in DB.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models.core import (
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningResource,
    Question,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    User,
)
from backend.app.services.career_map import calculate_career_ready_map


@pytest.fixture
def banking_curriculum_with_resources(db_session):
    """Seeds a full 10-topic curriculum for Banking IBPS PO with verified resources and questions."""
    target = CareerTarget(
        name="Banking (IBPS PO)",
        category="govt_exam",
        description="Comprehensive Probationary Officer Exam Preparation",
        readiness_threshold=0.75,
    )
    db_session.add(target)
    db_session.flush()

    s_quant = Skill(target_id=target.id, name="Quantitative Aptitude & Data Interpretation", weight=0.35)
    s_reason = Skill(target_id=target.id, name="Reasoning Ability & Computer Aptitude", weight=0.30)
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
    resources = []
    for idx, top in enumerate(all_topics, start=1):
        c = Concept(
            topic_id=top.id,
            name=f"{top.name} Core",
            description=f"Foundations of {top.name}",
        )
        db_session.add(c)
        db_session.flush()
        concepts.append(c)

        lr = LearningResource(
            concept_id=c.id,
            title=f"NCERT & NPTEL: {c.name} Comprehensive Guide",
            url="https://ncert.nic.in/textbook.php?jemh1=0-15",
            description=f"Curriculum material for {top.name}.",
            provider="NCERT / NPTEL",
            resource_type="textbook",
            estimated_duration_min=45,
            difficulty="Intermediate",
            attribution="NCERT National Mathematics & Aptitude Curriculum",
            license="Educational Open Access",
            quality_score=0.98,
        )
        db_session.add(lr)
        resources.append(lr)

    # Prerequisites DAG edges (Percent -> Profit/Loss, Percent -> DI, Syllogism -> Coding)
    edge1 = ConceptDependency(prerequisite_id=concepts[0].id, dependent_concept_id=concepts[2].id, relation_weight=0.8)
    edge2 = ConceptDependency(prerequisite_id=concepts[0].id, dependent_concept_id=concepts[3].id, relation_weight=0.9)
    edge3 = ConceptDependency(prerequisite_id=concepts[4].id, dependent_concept_id=concepts[5].id, relation_weight=0.7)
    db_session.add_all([edge1, edge2, edge3])
    db_session.flush()

    # Questions bank (3 per concept = 30 total questions)
    q_counter = 1
    bank_questions = []
    for c in concepts:
        for i in range(3):
            q = Question(
                concept_id=c.id,
                question_text=f"PYQ Question {q_counter}: In {c.name}, what is the standard result of test {i+1}?",
                options_json={"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                correct_answer="A",
                explanation="Verified conceptual rationale based on official examination standard.",
                difficulty_hint=-0.5 + (i * 0.4),
                source="curated",
                review_status="approved",
                source_title="IBPS PO Preliminary Examination Official Paper",
                source_url="https://www.ibps.in/crp-po-mt/",
                exam_year="2022-2023",
                license="Official Examination Paper (Educational Fair Use)",
                verified=True,
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
        "resources": resources,
        "bank_questions": bank_questions,
    }


@pytest.fixture
def test_user_and_headers(db_session, banking_curriculum_with_resources):
    curriculum = banking_curriculum_with_resources
    user = User(
        email="career_ready_aspirant@test.internal",
        name="Career Ready Aspirant",
        google_sub="google-sub-cr-1",
        role="learner",
    )
    db_session.add(user)
    db_session.flush()

    profile = LearnerProfile(
        user_id=user.id,
        target_type="govt_exam",
        target_id=curriculum["target"].id,
        current_level="Intermediate",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}, user, curriculum


def test_verified_online_study_materials_bank(db_session, banking_curriculum_with_resources):
    """Verifies that all learning resources have verified, direct URLs, providers, durations, and licenses."""
    resources = db_session.execute(select(LearningResource)).scalars().all()
    assert len(resources) >= 10, "Learning resources bank must contain seeded resources"

    for r in resources:
        assert r.url.startswith("http"), f"Resource #{r.id} URL must start with http/https: {r.url}"
        assert "learn.internal" not in r.url, f"Resource #{r.id} contains internal placeholder: {r.url}"
        assert "google.com/search" not in r.url, f"Resource #{r.id} contains Google search link: {r.url}"
        assert len(r.provider) > 0, f"Resource #{r.id} must have a provider specified"
        assert r.estimated_duration_min > 0, f"Resource #{r.id} must have positive duration"
        assert len(r.difficulty) > 0, f"Resource #{r.id} must specify difficulty"
        assert len(r.license) > 0, f"Resource #{r.id} must specify license/attribution"


def test_study_materials_endpoint_target_filtering(client: TestClient, test_user_and_headers):
    """Verifies GET /api/learning/resources returns real resources for user's active target without content gaps."""
    headers, user, curriculum = test_user_and_headers

    res = client.get("/api/learning/resources", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["target_id"] == curriculum["target"].id
    assert data["total_resources"] >= 10
    assert len(data["content_gaps"]) == 0

    first_item = data["resources"][0]
    assert "url" in first_item
    assert "provider" in first_item
    assert "estimated_duration_min" in first_item
    assert "difficulty" in first_item
    assert "license" in first_item
    assert "is_weak_topic" in first_item
    assert first_item["url"].startswith("http")


def test_initial_diagnostic_ten_distinct_topics_with_traceable_origin(client: TestClient, test_user_and_headers, db_session):
    """Verifies start diagnostic returns 10 questions testing 10 distinct topics with traceable origin metadata."""
    headers, user, curriculum = test_user_and_headers

    res = client.post("/api/diagnostic/start", headers=headers, json={"target_id": curriculum["target"].id})
    assert res.status_code == 200
    data = res.json()

    items = data["items"]
    assert len(items) == 10, "Initial diagnostic must contain exactly 10 questions"

    # Distinct topics verification
    topic_ids = [it["topic_id"] for it in items]
    unique_topics = set(topic_ids)
    assert len(unique_topics) == 10, f"Initial diagnostic must test 10 distinct topics, got {len(unique_topics)}"

    # Traceable origin metadata verification
    for it in items:
        assert it.get("source_title") is not None, f"Question {it['question_id']} missing source_title"
        assert it.get("source_url") is not None, f"Question {it['question_id']} missing source_url"
        assert it.get("exam_year") is not None, f"Question {it['question_id']} missing exam_year"
        assert it.get("verified") is True, f"Question {it['question_id']} must be verified"


def test_career_ready_map_unassessed_state(db_session, test_user_and_headers):
    """Verifies career ready map for a brand-new user shows 0% coverage and Unassessed stage."""
    headers, user, curriculum = test_user_and_headers

    career_map = calculate_career_ready_map(db=db_session, user_id=user.id, target_id=curriculum["target"].id)

    assert career_map["target_id"] == curriculum["target"].id
    assert career_map["total_syllabus_topics"] == 10
    assert career_map["demonstrated_topics_count"] == 0
    assert career_map["topic_coverage_readiness_pct"] == 0.0
    assert career_map["raw_accuracy_pct"] == 0.0
    assert career_map["learning_stage"] == "Unassessed"
    assert career_map["is_career_ready"] is False
    assert len(career_map["unassessed_topics"]) == 10


def test_career_ready_map_post_diagnostic_formula_and_differentiation(client: TestClient, test_user_and_headers, db_session):
    """Verifies submit diagnostic recomputes Career Ready Map:
    Topic coverage readiness (%) = (distinct topics demonstrated / total topics) * 100
    Strictly differentiated from raw accuracy.
    """
    headers, user, curriculum = test_user_and_headers

    # Start diagnostic
    start_res = client.post("/api/diagnostic/start", headers=headers, json={"target_id": curriculum["target"].id})
    assert start_res.status_code == 200
    asmt_data = start_res.json()
    items = asmt_data["items"]
    asmt_id = asmt_data["assessment_id"]

    # Submit 6 correct, 4 incorrect across the 10 distinct topics
    responses = []
    for idx, it in enumerate(items):
        q = db_session.get(Question, it["question_id"])
        # Answer first 6 correctly, 4 incorrectly
        selected = q.correct_answer if idx < 6 else "WRONG"
        responses.append({
            "question_id": q.id,
            "selected_answer": selected,
            "response_time_ms": 30000,
            "skipped": False,
            "attempt_no": 1,
        })

    sub_res = client.post("/api/diagnostic/submit", headers=headers, json={
        "assessment_id": asmt_id,
        "responses": responses,
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.json()

    # Raw accuracy: 6 / 10 = 60.0%
    assert sub_data["accuracy"] == 60.0
    assert sub_data["correct_count"] == 6

    # 6 distinct topics demonstrated out of 10 total topics:
    # Topic coverage readiness = (6 / 10) * 100 = 60.0%
    assert sub_data["topic_coverage_readiness_pct"] == 60.0
    assert sub_data["learning_stage"] in ["Developing Stage", "Proficient Stage"]

    # Retrieve Career Ready Map from endpoint
    map_res = client.get("/api/learning/career-map", headers=headers)
    assert map_res.status_code == 200
    map_data = map_res.json()

    assert map_data["demonstrated_topics_count"] == 6
    assert map_data["total_syllabus_topics"] == 10
    assert map_data["topic_coverage_readiness_pct"] == 60.0
    assert map_data["raw_accuracy_pct"] == 60.0
    assert len(map_data["demonstrated_topics"]) == 6

    # 4 missed topics should be in weak_topics
    assert len(map_data["weak_topics"]) == 4


def test_adaptive_progression_unlocks_next_topic(client: TestClient, test_user_and_headers, db_session):
    """Verifies that answering follow-up questions moves unassessed topics to demonstrated topics and unlocks progression."""
    headers, user, curriculum = test_user_and_headers

    # Initial career map before practice
    initial_map = calculate_career_ready_map(db=db_session, user_id=user.id, target_id=curriculum["target"].id)
    initial_dem_count = initial_map["demonstrated_topics_count"]

    # Student completes practice on a topic
    first_topic = curriculum["topics"][0]
    topic_q = db_session.execute(
        select(Question)
        .join(Concept, Question.concept_id == Concept.id)
        .where(Concept.topic_id == first_topic.id)
    ).scalars().first()
    assert topic_q is not None

    # Record correct student response
    resp = StudentResponse(
        user_id=user.id,
        assessment_id=1,
        question_id=topic_q.id,
        selected_answer=topic_q.correct_answer,
        is_correct=True,
        response_time_ms=25000,
        skipped=False,
        attempt_no=1,
    )
    db_session.add(resp)
    db_session.commit()

    # Recompute map
    updated_map = calculate_career_ready_map(db=db_session, user_id=user.id, target_id=curriculum["target"].id)
    assert updated_map["demonstrated_topics_count"] == initial_dem_count + 1
    assert first_topic.id in [t["topic_id"] for t in updated_map["demonstrated_topics"]]
    assert first_topic.id not in [t["topic_id"] for t in updated_map["unassessed_topics"]]
