"""Learner Analytics, Gap Scoring, Root Cause, and Readiness API Router."""
from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import (
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    TopicPerformance,
    User,
)
from backend.app.services.root_cause import (
    attention_entropy,
    get_ancestors_within_hops,
    present_as_mode,
    rank_root_cause_candidates,
)
from backend.app.services.scoring import (
    adaptive_priority,
    gap_band,
    readiness_score,
)
from ml.graph.dag_validator import SimpleDiGraph

router = APIRouter()


@router.get("/mastery")
def get_mastery_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns concept masteries, confidence, and cold-start banner flag (Screen 10)."""
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    target_id = profile.target_id if profile else 1

    # Fetch concepts for user's target
    concepts_rows = db.execute(
        select(Concept, Skill.name, Skill.id)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
        .order_by(Concept.id)
    ).all()

    # Get student masteries
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastery_map = {m.concept_id: m for m in masteries}

    # Count learner interactions for honesty rule (< 20 -> cold start banner)
    interaction_count = db.execute(
        select(func.count(StudentResponse.id)).where(StudentResponse.user_id == current_user.id)
    ).scalar() or 0
    cold_start = interaction_count < 20

    items = []
    for c, skill_name, skill_id in concepts_rows:
        m_rec = mastery_map.get(c.id)
        m_score = m_rec.mastery_score if m_rec else 0.50
        conf = m_rec.confidence if m_rec else 0.20
        band = "strong" if m_score >= 0.70 else "moderate" if m_score >= 0.40 else "weak"

        items.append({
            "concept_id": c.id,
            "concept_name": c.name,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery_score": round(m_score, 2),
            "confidence": round(conf, 2),
            "band": band,
            "has_history": m_rec is not None,
        })

    return {
        "target_id": target_id,
        "interaction_count": interaction_count,
        "cold_start": cold_start,
        "concepts": items,
        "model_signal": "cold_start_heuristic" if cold_start else "calibrated_mastery",
    }


@router.get("/gaps")
def get_gap_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns prioritised weak topics list with F12 terms and F14 priority rank (Screen 12)."""
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    target_id = profile.target_id if profile else 1
    days_to_exam = 60
    if profile and profile.exam_date:
        today = dt.date.today()
        days_to_exam = max(1, (profile.exam_date - today).days)

    # Fetch concepts with skills
    concepts_rows = db.execute(
        select(Concept, Skill.name, Skill.weight)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
    ).all()

    # Get topic performance / student masteries
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    # Responses to calculate empirical accuracy / skip rate
    responses = db.execute(
        select(StudentResponse).where(StudentResponse.user_id == current_user.id)
    ).scalars().all()
    resp_by_concept: dict[int, list[StudentResponse]] = {}
    for r in responses:
        if r.concept_id not in resp_by_concept:
            resp_by_concept[r.concept_id] = []
        resp_by_concept[r.concept_id].append(r)

    gap_items = []
    for c, skill_name, skill_weight in concepts_rows:
        c_resps = resp_by_concept.get(c.id, [])
        m_score = mastery_map.get(c.id, 0.50)
        
        if c_resps:
            corr = sum(1 for x in c_resps if x.is_correct)
            acc = corr / len(c_resps)
            skips = sum(1 for x in c_resps if x.skipped)
            skip_rate = skips / len(c_resps)
            avg_time = sum(x.response_time_ms for x in c_resps) / len(c_resps)
            tr = avg_time / 60000.0  # approximate expected time
        else:
            acc = m_score
            skip_rate = 0.0
            tr = 1.0

        # Gap score (F12)
        gap = 0.40 * (1.0 - acc) + 0.20 * max(0.0, min(1.0, (tr - 1.0) / 2.0)) + 0.20 * skip_rate + 0.20 * (1.0 - m_score)
        band = gap_band(gap)

        # F14 Adaptive Priority
        pri = adaptive_priority(
            gap=gap,
            days_to_target=days_to_exam,
            skill_weight=skill_weight,
            dag_distance=0,
            horizon=120.0,
        )

        gap_items.append({
            "concept_id": c.id,
            "concept_name": c.name,
            "skill_name": skill_name,
            "accuracy": round(acc, 2),
            "time_ratio": round(tr, 2),
            "skip_rate": round(skip_rate, 2),
            "historical_mastery": round(m_score, 2),
            "gap_score": round(gap, 3),
            "band": band,
            "priority": round(pri, 4),
        })

    # Sort descending by priority (highest remediation need first)
    gap_items.sort(key=lambda x: x["priority"], reverse=True)

    return {
        "target_id": target_id,
        "days_to_exam": days_to_exam,
        "gaps": gap_items,
    }


@router.get("/root-causes")
def get_root_cause_analytics(
    concept_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns root-cause attribution with honesty guard:
    - Normalised entropy H_bar (F8)
    - present_as: 'two_candidates' if H_bar > 0.7, else 'single_cause' (Screen 13).
    """
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    target_id = profile.target_id if profile else 1

    # If no concept_id specified, pick the weakest concept
    if not concept_id:
        weakest = db.execute(
            select(StudentMastery)
            .where(StudentMastery.user_id == current_user.id)
            .order_by(StudentMastery.mastery_score.asc())
        ).scalars().first()
        if weakest:
            concept_id = weakest.concept_id
        else:
            first_c = db.execute(select(Concept.id)).scalars().first()
            concept_id = first_c or 1

    surface_concept = db.get(Concept, concept_id)
    if not surface_concept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

    # Build DAG
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    ancestors = get_ancestors_within_hops(g, surface_concept.id, max_hops=2)

    # Masteries for candidates
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    # Concept names
    all_cs = db.execute(select(Concept)).scalars().all()
    name_map = {c.id: c.name for c in all_cs}

    candidates = rank_root_cause_candidates(
        surface_concept_id=surface_concept.id,
        ancestors_with_hops=ancestors,
        concept_mastery=mastery_map,
        concept_names=name_map,
    )

    alphas = [c["attention_alpha"] for c in candidates]
    raw_h, norm_h = attention_entropy(alphas)
    presentation_mode = present_as_mode(norm_h)

    surface_mastery = mastery_map.get(surface_concept.id, 0.45)

    return {
        "surface_concept_id": surface_concept.id,
        "surface_concept_name": surface_concept.name,
        "surface_mastery": round(surface_mastery, 2),
        "candidates": candidates,
        "attention_entropy": round(norm_h, 3),
        "raw_entropy": round(raw_h, 3),
        "present_as": presentation_mode,
        "honesty_disclaimer": "This analysis is an estimate of cognitive prerequisites, not a guarantee.",
    }


@router.get("/readiness")
def get_readiness_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns coverage-weighted readiness score (F17) across target skills (Screen 11, 20)."""
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    target_id = profile.target_id if profile else 1
    target = db.get(CareerTarget, target_id)

    skills = db.execute(
        select(Skill).where(Skill.target_id == target_id)
    ).scalars().all()

    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    skill_components = []
    readiness_input = []

    for s in skills:
        concepts = db.execute(
            select(Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .where(Topic.skill_id == s.id)
        ).scalars().all()

        if concepts:
            mean_m = sum(mastery_map.get(cid, 0.50) for cid in concepts) / len(concepts)
        else:
            mean_m = 0.50

        skill_components.append({
            "skill_id": s.id,
            "skill_name": s.name,
            "weight": s.weight,
            "mean_mastery": round(mean_m, 2),
            "concept_count": len(concepts),
        })
        readiness_input.append((s.weight, mean_m))

    overall_readiness = readiness_score(readiness_input)
    threshold = target.readiness_threshold if target else 0.75
    is_ready = overall_readiness >= threshold

    return {
        "target_id": target_id,
        "target_name": target.name if target else "Unknown",
        "readiness_score": round(overall_readiness, 2),
        "readiness_percentage": round(overall_readiness * 100, 1),
        "readiness_threshold": threshold,
        "is_ready": is_ready,
        "skill_components": skill_components,
        "label": "estimate, not guarantee",
    }
