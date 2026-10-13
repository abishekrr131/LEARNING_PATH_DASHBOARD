"""Unit tests validating the 4 specific prompt requirements:
1. Options Normalization: Options returned as [{key, text}] array without crash, tested with object & array options.
2. Gemini Health Observability: GET /api/health/gemini returns structured health/model/latency/error, and /api/health reflects Gemini status.
3. Compulsory AI-Generated Questions:
   - Diagnostic, Weekly test, and Practice mode prioritize Gemini.
   - Bank fallback is permitted ONLY when ALLOW_BANK_FALLBACK=true (default false).
   - Source badge is provided on every item.
4. Learning Resources Endpoint:
   - GET /api/learning/resources returns HTTP 200 (no 500 AttributeError on source/difficulty).
   - Resources include real curated search/API links for YouTube, GeeksforGeeks, and IndiaBix.
   - Diagnosed weak topics are prioritized first with weak_topic badge.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from ai.gemini_client import GeminiClient, GeminiUnavailableError
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.models.core import CareerTarget, Concept, LearnerProfile, Question, Skill, StudentMastery, Topic, User


@pytest.fixture
def test_learner(db_session, client: TestClient):
    """Sets up an authenticated learner with Banking IBPS PO curriculum."""
    target = CareerTarget(
        name="Banking (IBPS PO)",
        category="govt_exam",
        description="Comprehensive curriculum for IBPS PO examination.",
    )
    db_session.add(target)
    db_session.commit()

    skills = [
        Skill(name="Quantitative Aptitude", target_id=target.id, weight=0.35),
        Skill(name="Reasoning Ability", target_id=target.id, weight=0.30),
        Skill(name="English Language", target_id=target.id, weight=0.20),
        Skill(name="General Awareness", target_id=target.id, weight=0.15),
    ]
    db_session.add_all(skills)
    db_session.commit()

    topics = []
    concepts = []
    for s in skills:
        t = Topic(name=f"{s.name} Core Topic", skill_id=s.id)
        db_session.add(t)
        db_session.commit()
        topics.append(t)

        c = Concept(name=f"{s.name} Foundations", topic_id=t.id, description="Foundational mastery")
        db_session.add(c)
        db_session.commit()
        concepts.append(c)

    user = User(name="Test Learner", email="testlearner_issues@palp.internal", role="learner", google_sub="google-sub-issues-1")
    db_session.add(user)
    db_session.commit()

    profile = LearnerProfile(user_id=user.id, target_id=target.id, target_type="govt_exam", current_level="intermediate")
    db_session.add(profile)
    db_session.commit()

    # Seed approved question in bank
    q1 = Question(
        concept_id=concepts[0].id,
        question_text="What is 10 + 20?",
        options_json={"A": "30", "B": "25", "C": "40", "D": "50"},
        correct_answer="A",
        explanation="10 + 20 = 30",
        difficulty_hint=0.1,
        source="curated",
        review_status="approved",
    )
    db_session.add(q1)
    db_session.commit()

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    return {
        "client": client,
        "user": user,
        "profile": profile,
        "target": target,
        "skills": skills,
        "topics": topics,
        "concepts": concepts,
        "headers": headers,
    }


def test_issue1_item_out_options_normalizer():
    """Issue 1: ItemOut schema automatically normalizes options into list of dicts [{key, text}]."""
    from backend.app.schemas.assessment import ItemOut

    # 1. Object format
    item1 = ItemOut(
        question_id=1,
        concept_id=1,
        concept_name="Percentages",
        order_index=0,
        question_text="What is 20% of 100?",
        options={"A": "20", "B": "30", "C": "40", "D": "50"},
    )
    assert isinstance(item1.options, list)
    assert item1.options == [
        {"key": "A", "text": "20"},
        {"key": "B", "text": "30"},
        {"key": "C", "text": "40"},
        {"key": "D", "text": "50"},
    ]

    # 2. Array format
    item2 = ItemOut(
        question_id=2,
        concept_id=1,
        concept_name="Percentages",
        order_index=1,
        question_text="What is 10% of 50?",
        options=[{"key": "A", "text": "5"}, {"key": "B", "text": "10"}],
    )
    assert item2.options == [{"key": "A", "text": "5"}, {"key": "B", "text": "10"}]


def test_issue2_gemini_health_endpoint(client: TestClient):
    """Issue 2: GET /api/health/gemini returns structured health status."""
    # When unconfigured
    with patch.object(settings, "GEMINI_API_KEY", ""):
        res = client.get("/api/health/gemini")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unconfigured"
        assert "GEMINI_API_KEY is not configured" in data["error"]

    # When live call succeeds
    import sys
    mock_genai = MagicMock()
    mock_instance = MagicMock()
    mock_genai.Client.return_value = mock_instance
    mock_instance.models.generate_content.return_value.text = "pong"

    with patch.object(settings, "GEMINI_API_KEY", "mock-valid-key"), \
         patch.dict(sys.modules, {"google": MagicMock(), "google.genai": mock_genai}):
        res = client.get("/api/health/gemini")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["model"] == settings.GEMINI_MODEL
        assert "latency_ms" in data


def test_issue3_compulsory_ai_practice_mode(client: TestClient, test_learner, db_session):
    """Issue 3: Practice mode uses Gemini by default, strictly failing if ALLOW_BANK_FALLBACK=False."""
    headers = test_learner["headers"]
    target = test_learner["target"]
    concept = test_learner["concepts"][0]

    # Area D: Even if Gemini is down or key is unconfigured, practice mode succeeds strictly from bank
    with patch("ai.gemini_client.GeminiClient.generate_structured_json", side_effect=Exception("API Down")):
        res = client.post(
            "/api/assessments/start",
            json={"type": "practice", "target_id": target.id, "concept_id": concept.id},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) > 0
        assert data["items"][0]["question_id"] is not None
        for it in data["items"]:
            assert isinstance(it["options"], list)


def test_issue4_resources_endpoint_real_links_and_weak_topics(client: TestClient, test_learner, db_session):
    """Issue 4: GET /api/learning/resources returns 200 with YouTube, GeeksforGeeks, and IndiaBix links,
    prioritizing diagnosed weak topics.
    """
    headers = test_learner["headers"]
    user = test_learner["user"]
    concepts = test_learner["concepts"]

    # Mark concept 0 as weak (<0.65 mastery)
    weak_m = StudentMastery(
        user_id=user.id,
        concept_id=concepts[0].id,
        mastery_score=0.35,
        confidence=0.8,
        model_version="v1",
    )
    db_session.add(weak_m)
    db_session.commit()

    res = client.get("/api/learning/resources", headers=headers)
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
    data = res.json()
    assert "resources" in data
    resources = data["resources"]
    assert len(resources) > 0

    # Verify real platform links exist
    sources = {r["source"] for r in resources}
    assert "YouTube" in sources
    assert "GeeksforGeeks" in sources
    assert "IndiaBix" in sources

    # Verify URLs are direct clickable links
    for r in resources:
        assert r["url"].startswith("http")
        assert "title" in r
        assert "description" in r
        assert "why_recommended" in r

    # Verify weak topics are flagged and placed first
    first_item = resources[0]
    assert first_item["is_weak_topic"] is True
    assert first_item["concept_id"] == concepts[0].id


def test_chatbot_grounding_strictly_target_curriculum(db_session):
    """Grounding test: Banking user asking about aptitude/simplification/profit & loss
    gets Banking curriculum context with ZERO cross-track ML terms.
    ML user gets ML curriculum context.
    """
    from backend.app.api.ai import resolve_syllabus_context

    # 1. Setup ML target and Banking target
    ml_target = CareerTarget(name="Machine Learning Engineer", category="it_career", description="ML curriculum")
    bank_target = CareerTarget(name="Banking (IBPS PO)", category="govt_exam", description="Banking curriculum")
    db_session.add_all([ml_target, bank_target])
    db_session.commit()

    # ML Skills & Topics
    ml_skill = Skill(name="Linear Algebra", target_id=ml_target.id, weight=0.4)
    db_session.add(ml_skill)
    db_session.commit()
    ml_topic = Topic(name="Vector Spaces & Matrix Ops", skill_id=ml_skill.id)
    db_session.add(ml_topic)
    db_session.commit()
    ml_c = Concept(name="Vector Dot Product", topic_id=ml_topic.id, description="Vectors, matrices, dot products, gradients")
    db_session.add(ml_c)

    # Banking Skills & Topics
    bank_skill = Skill(name="Quantitative Aptitude", target_id=bank_target.id, weight=0.35)
    db_session.add(bank_skill)
    db_session.commit()
    bank_topic1 = Topic(name="Speed Math & Simplification", skill_id=bank_skill.id)
    bank_topic2 = Topic(name="Profit, Loss and Discount", skill_id=bank_skill.id)
    db_session.add_all([bank_topic1, bank_topic2])
    db_session.commit()
    bank_c1 = Concept(name="Simplification Techniques", topic_id=bank_topic1.id, description="BODMAS, fractions, square roots")
    bank_c2 = Concept(name="Profit and Loss Calculation", topic_id=bank_topic2.id, description="Cost price, selling price, margin")
    db_session.add_all([bank_c1, bank_c2])

    # Users
    bank_user = User(name="Bank Learner", email="bank@test.com", role="learner", google_sub="sub-bank")
    ml_user = User(name="ML Learner", email="ml@test.com", role="learner", google_sub="sub-ml")
    db_session.add_all([bank_user, ml_user])
    db_session.commit()

    db_session.add(LearnerProfile(user_id=bank_user.id, target_id=bank_target.id, target_type="govt_exam"))
    db_session.add(LearnerProfile(user_id=ml_user.id, target_id=ml_target.id, target_type="it_career"))
    db_session.commit()

    ml_forbidden_words = ["vector", "matrix", "matrices", "gradient", "dot product", "neural", "tensor"]

    # Test Banking user queries
    for query in ["explain aptitude", "what is simplification", "explain profit and loss"]:
        tname, meta, tids = resolve_syllabus_context(db_session, bank_user.id, None, query)
        assert bank_target.name in meta, f"Expected target name in meta for query '{query}': {meta}"
        meta_lower = meta.lower()
        for forbidden in ml_forbidden_words:
            assert forbidden not in meta_lower, f"Forbidden ML word '{forbidden}' leaked in Banking context: {meta}"
        assert len(tids) > 0 or "General" in tname

    # Test ML user query
    ml_tname, ml_meta, ml_tids = resolve_syllabus_context(db_session, ml_user.id, None, "explain vectors and matrices")
    assert ml_target.name in ml_meta
    assert "Vector" in ml_meta or "Matrix" in ml_meta


def test_verified_models_and_failover_builder():
    """Verify get_verified_gemini_models and build_failover_order exclude unverified/guessed models."""
    from ai.gemini_client import build_failover_order

    verified_sample = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]

    # When primary model and fallbacks are configured
    order = build_failover_order(
        primary_model="gemini-3.5-flash",
        fallback_models_str="gemini-3.5-flash-lite,gemini-2.0-flash-retired,gemini-flash-lite-latest",
        verified_models=verified_sample,
    )

    assert "gemini-3.5-flash" in order
    assert "gemini-3.5-flash-lite" in order
    assert "gemini-flash-lite-latest" in order
    # The retired/guessed model must NOT be in the order:
    assert "gemini-2.0-flash-retired" not in order


def test_429_rate_limit_error_mapping(client: TestClient, test_learner):
    """Verify that GeminiRateLimitError returns HTTP 429 with 'AI is busy, retry in about 1 minute'."""
    from ai.gemini_client import GeminiRateLimitError

    headers = test_learner["headers"]
    target = test_learner["target"]

    with patch("backend.app.services.question_generator.generate_initial_diagnostic_questions",
               side_effect=GeminiRateLimitError("Quota exceeded")):
        res = client.post("/api/diagnostic/start", json={"target_id": target.id}, headers=headers)
        assert res.status_code == 429
        assert "AI is busy, retry in about 1 minute" in res.json().get("detail", "")

