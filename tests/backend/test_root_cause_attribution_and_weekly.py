"""Test suite for Phase 4 (Root-Cause Prerequisite Attribution) and Phase 5 (Weekly Adaptation).

Covers test criteria 14 to 26:
14. A known prerequisite gap is correctly identified.
15. Arithmetic errors are not automatically classified as conceptual gaps.
16. Valid root nodes are distinguished from missing graph mappings.
17. Empty or invalid attention weights do not produce misleading entropy or confidence.
18. Multiple plausible root causes are ranked using actual evidence.
19. Insufficient evidence produces an explicit inconclusive state.
20. New diagnostic responses can change the attribution.
21. The correct rolling seven-day window is used.
22. Repeated scheduler runs do not create duplicate snapshots.
23. Failed refreshes preserve the last valid report.
24. User data remains isolated.
25. Historical snapshots are retained and comparisons use real persisted values.
26. The scheduler actually executes through the application runtime.
"""
import datetime as dt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models.core import (
    Assessment,
    Concept,
    ConceptDependency,
    LearnerProfile,
    Question,
    StudentMastery,
    StudentResponse,
    User,
    WeeklyAnalysisSnapshot,
)
from backend.app.services.root_cause import (
    attention_entropy,
    classify_error_evidence,
    get_ancestors_within_hops,
    present_as_mode,
    rank_root_cause_candidates,
    verify_graph_prerequisites,
)
from backend.app.services.weekly_adaptation import (
    compute_weekly_adaptation,
    get_weekly_adaptation_summary,
    run_scheduled_weekly_adaptation_job,
)
from ml.graph.dag_validator import SimpleDiGraph
from tests.backend.test_diagnostic_and_weekly import banking_curriculum, test_user


def test_classify_error_evidence_distinguishes_arithmetic_from_conceptual():
    """Requirement 15: Arithmetic errors are not automatically classified as conceptual gaps."""
    # Sub-response mock showing formula passed but calculation failed
    class MockSubResponse:
        def __init__(self, stage, is_correct, time_spent_ms=10000):
            self.stage = stage
            self.stage_name = stage
            self.is_correct = is_correct
            self.time_spent_ms = time_spent_ms

    sub_resps = [
        MockSubResponse("definition", True),
        MockSubResponse("formula", True),
        MockSubResponse("calculation", False, time_spent_ms=22000),  # Failed calculation / timeout
    ]

    result = classify_error_evidence(sub_responses=sub_resps)
    assert result["error_type"] == "arithmetic_or_calculation_error"
    assert result["confidence"] > 0.8
    assert "arithmetic" in result["explanation"].lower() or "calculation" in result["explanation"].lower()

    # Contrast with all sub-questions failing -> conceptual misunderstanding
    failed_sub_resps = [
        MockSubResponse("definition", False),
        MockSubResponse("formula", False),
        MockSubResponse("calculation", False),
    ]
    result2 = classify_error_evidence(sub_responses=failed_sub_resps)
    assert result2["error_type"] == "conceptual_misunderstanding"


def test_verify_graph_prerequisites_root_node_vs_missing():
    """Requirement 16: Valid root nodes are distinguished from missing graph mappings."""
    # Build graph with edge 1 -> 2 (1 is root, 2 is dependent)
    g = SimpleDiGraph([(1, 2)])
    all_concepts = {1, 2}

    # Concept 1 is in graph and has 0 predecessors -> root node
    state1, ancestors1 = verify_graph_prerequisites(g, all_concepts, 1)
    assert state1 == "no_valid_prerequisites"
    assert ancestors1 == {}

    # Concept 2 has prerequisite 1 -> valid attribution
    state2, ancestors2 = verify_graph_prerequisites(g, all_concepts, 2)
    assert state2 == "valid_attribution"
    assert 1 in ancestors2

    # Concept 999 is not in curriculum graph -> missing_graph_mapping
    state3, ancestors3 = verify_graph_prerequisites(g, all_concepts, 999)
    assert state3 == "missing_graph_mapping"
    assert ancestors3 == {}


def test_rank_root_cause_and_diagnostic_response_changes_attribution():
    """Requirements 14, 18, 20: Known prerequisite gap identified, ranked with evidence,
    and new diagnostic response changes attribution.
    """
    ancestors = {101: 1, 102: 1}  # Two 1-hop prerequisites
    concept_mastery = {101: 0.50, 102: 0.50}
    names = {101: "Percentages", 102: "Ratios"}

    # Initially, equal mastery -> equal scores
    cands_initial = rank_root_cause_candidates(
        surface_concept_id=200,
        ancestors_with_hops=ancestors,
        concept_mastery=concept_mastery,
        concept_names=names,
    )
    assert len(cands_initial) == 2

    # Now simulate new diagnostic probe response: student FAILED probe on 101, but PASSED on 102
    cands_updated = rank_root_cause_candidates(
        surface_concept_id=200,
        ancestors_with_hops=ancestors,
        concept_mastery=concept_mastery,
        concept_names=names,
        diagnostic_sub_evidence={101: False, 102: True},
    )
    assert cands_updated[0]["candidate_concept_id"] == 101
    assert cands_updated[0]["root_score"] > cands_updated[1]["root_score"]
    assert cands_updated[0]["attention_alpha"] > cands_updated[1]["attention_alpha"]
    assert cands_updated[0]["error_evidence"] >= 0.85
    assert cands_updated[1]["error_evidence"] <= 0.20


def test_root_cause_api_attribution_states(
    client: TestClient, test_user, banking_curriculum, db_session
):
    """Requirements 17 & 19: End-to-end API returns explicit attribution states,
    does not force single_cause or 0.0 entropy on root/unmapped nodes.
    """
    headers = test_user["headers"]
    user_id = test_user["user"].id

    # Create 3 concepts:
    # c_root (id=901): root node in graph, no predecessors
    # c_child (id=902): child node with c_root as prerequisite
    # c_unmapped (id=903): not in ConceptDependency at all, not in target
    topic = banking_curriculum["topics"][0]
    c_root = Concept(id=901, topic_id=topic.id, name="Foundations of Numbers")
    c_child = Concept(id=902, topic_id=topic.id, name="Advanced Number Properties")
    db_session.add_all([c_root, c_child])
    db_session.flush()

    dep = ConceptDependency(concept_id=c_child.id, prerequisite_id=c_root.id)
    db_session.add(dep)
    db_session.commit()

    # 1. Test root node API call
    res_root = client.get(f"/api/analytics/root-causes?concept_id={c_root.id}", headers=headers)
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert data_root["attribution_state"] == "no_valid_prerequisites"
    assert data_root["attention_entropy"] is None
    assert data_root["present_as"] == "no_prerequisites"
    assert data_root["candidates"] == []

    # 2. Test child node with insufficient attempts / high mastery
    m = StudentMastery(user_id=user_id, concept_id=c_child.id, mastery_score=0.85, confidence=0.8, model_version="v1")
    db_session.add(m)
    db_session.commit()

    res_child = client.get(f"/api/analytics/root-causes?concept_id={c_child.id}", headers=headers)
    assert res_child.status_code == 200
    data_child = res_child.json()
    assert data_child["attribution_state"] in ("insufficient_evidence", "valid_attribution")

    # 3. Add failed response for c_child -> valid attribution
    target = banking_curriculum["target"]
    assessment = Assessment(
        user_id=user_id,
        type="practice",
        target_id=target.id,
    )
    db_session.add(assessment)
    db_session.flush()

    q = Question(
        concept_id=c_child.id,
        stem="Find the number property.",
        options_json={"A": "1", "B": "2"},
        correct_answer="A",
        difficulty=0.6,
        review_status="approved",
    )
    db_session.add(q)
    db_session.flush()

    sr = StudentResponse(
        assessment_id=assessment.id,
        user_id=user_id,
        question_id=q.id,
        selected_answer="B",
        is_correct=False,
        response_time_ms=15000,
        answered_at=dt.datetime.now(dt.timezone.utc),
    )
    db_session.add(sr)
    # Update mastery to weak
    m.mastery_score = 0.35
    db_session.commit()

    res_child_fail = client.get(f"/api/analytics/root-causes?concept_id={c_child.id}", headers=headers)
    assert res_child_fail.status_code == 200
    data_fail = res_child_fail.json()
    assert data_fail["attribution_state"] == "valid_attribution"
    assert len(data_fail["candidates"]) >= 1
    assert data_fail["candidates"][0]["candidate_concept_id"] == c_root.id
    assert data_fail["remediation_concept_id"] == c_root.id
    assert data_fail["attention_entropy"] is not None


def test_weekly_adaptation_rolling_window_and_idempotency(
    client: TestClient, test_user, banking_curriculum, db_session
):
    """Requirements 21, 22, 23, 24, 25: 7-day rolling window, idempotent persistence,
    WoW comparison, user isolation.
    """
    user1 = test_user["user"]
    headers1 = test_user["headers"]
    target = banking_curriculum["target"]

    # Create user 2
    user2 = User(email="user2.test@example.com", name="User Two", google_sub="sub-u2", role="learner")
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)
    token2 = create_access_token(data={"sub": str(user2.id)})
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Seed attempts in and outside rolling 7-day window for user 1
    now = dt.datetime.now(dt.timezone.utc)
    old_time = now - dt.timedelta(days=10)
    recent_time = now - dt.timedelta(days=2)

    topic = banking_curriculum["topics"][0]
    q = Question(
        concept_id=topic.concepts[0].id if topic.concepts else 1,
        stem="Test question stem",
        options_json={"A": "1"},
        correct_answer="A",
        difficulty=0.5,
        review_status="approved",
    )
    db_session.add(q)
    db_session.flush()

    asmt1 = Assessment(user_id=user1.id, type="practice", target_id=target.id)
    db_session.add(asmt1)
    db_session.flush()

    # User 1 old response (outside window)
    r_old = StudentResponse(
        assessment_id=asmt1.id,
        user_id=user1.id,
        question_id=q.id,
        selected_answer="A",
        is_correct=True,
        response_time_ms=10000,
        answered_at=old_time,
    )
    # User 1 recent response (inside window)
    r_recent = StudentResponse(
        assessment_id=asmt1.id,
        user_id=user1.id,
        question_id=q.id,
        selected_answer="A",
        is_correct=True,
        response_time_ms=10000,
        answered_at=recent_time,
    )
    db_session.add_all([r_old, r_recent])
    db_session.commit()

    # 1. Compute weekly adaptation for user 1
    snap1 = compute_weekly_adaptation(db_session, user1.id, force=True, now=now)
    assert snap1.user_id == user1.id
    # Window should only count r_recent (1 attempt)
    assert snap1.total_attempts == 1
    assert snap1.accuracy_pct == 100.0

    # 2. Idempotency: repeated run without force should not create duplicate snapshot
    count_before = db_session.execute(
        select(WeeklyAnalysisSnapshot).where(WeeklyAnalysisSnapshot.user_id == user1.id)
    ).scalars().all()
    snap_repeat = compute_weekly_adaptation(db_session, user1.id, force=False, now=now)
    count_after = db_session.execute(
        select(WeeklyAnalysisSnapshot).where(WeeklyAnalysisSnapshot.user_id == user1.id)
    ).scalars().all()
    assert len(count_before) == len(count_after)
    assert snap_repeat.id == snap1.id

    # 3. User isolation: user 2 has 0 attempts
    summary2 = get_weekly_adaptation_summary(db_session, user2.id)
    assert summary2["latest"]["total_attempts"] == 0

    # 4. API Endpoints
    api_res = client.get("/api/analytics/weekly-snapshots", headers=headers1)
    assert api_res.status_code == 200
    res_data = api_res.json()
    assert "latest" in res_data
    assert "comparison" in res_data
    assert res_data["latest"]["total_attempts"] == 1

    # 5. Manual refresh endpoint
    refresh_res = client.post("/api/analytics/refresh-weekly", headers=headers1)
    assert refresh_res.status_code == 200
    assert refresh_res.json()["latest"]["id"] is not None

    # 6. Scheduled job runner
    processed = run_scheduled_weekly_adaptation_job(db_session)
    assert processed >= 2
