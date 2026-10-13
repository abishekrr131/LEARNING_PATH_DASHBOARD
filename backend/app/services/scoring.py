"""Psychometric and gap scoring formula services.

Implements all core mathematical formulations specified in Section 8 of the
RCT-GAT Specification:
- F10: Expected response time per difficulty band
- F11: Response-time ratio
- F12: Learning Gap Score (the interpretable cold-start baseline)
- F14: Adaptive remediation priority
- F15: Ebbinghaus mastery decay
- F16: Decay-based review scheduling
- F17: Coverage-weighted readiness score
"""
from __future__ import annotations

import math
from typing import Literal, Sequence


def expected_response_time(difficulty_b: float) -> float:
    """Expected response time in seconds based on difficulty parameter b (F10).

    Default band mapping:
    - b <= -0.5 (easy): 45.0 seconds
    - -0.5 < b <= 0.5 (medium): 60.0 seconds
    - b > 0.5 (hard): 90.0 seconds
    """
    if difficulty_b <= -0.5:
        return 45.0
    elif difficulty_b <= 0.5:
        return 60.0
    return 90.0


def time_ratio(response_time_ms: int | float, expected_time_sec: float) -> float:
    """Computes response time ratio normalised by difficulty (F11).

    TimeRatio = tau_student / ExpectedTime(b_question)

    Examples:
        >>> round(time_ratio(142000, 95.0), 2)
        1.49
        >>> round(time_ratio(38000, 95.0), 2)
        0.4
    """
    tau_sec = max(0.0, float(response_time_ms) / 1000.0)
    exp_sec = max(1e-6, float(expected_time_sec))
    return tau_sec / exp_sec


def time_penalty(time_ratio_val: float) -> float:
    """Time penalty term for Formula 12:

    TimePenalty_c = clip((TimeRatio_c - 1) / 2, 0, 1)

    Examples:
        >>> round(time_penalty(1.49), 3)
        0.245
        >>> time_penalty(0.5)
        0.0
        >>> time_penalty(3.5)
        1.0
    """
    raw = (time_ratio_val - 1.0) / 2.0
    return max(0.0, min(1.0, raw))


def gap_score(
    accuracy: float,
    time_ratio_val: float,
    skip_rate: float,
    hist_mastery: float,
    weights: tuple[float, float, float, float] = (0.40, 0.20, 0.20, 0.20),
) -> float:
    """Computes interpretable Learning Gap Score G_c (F12).

    G_c = w1*(1 - Accuracy_c) + w2*TimePenalty_c + w3*SkipRate_c + w4*(1 - M_c^hist)

    Examples:
        >>> round(gap_score(accuracy=0.35, time_ratio_val=1.49, skip_rate=0.25, hist_mastery=0.40), 3)
        0.479
    """
    w1, w2, w3, w4 = weights
    acc_term = 1.0 - max(0.0, min(1.0, accuracy))
    tp_term = time_penalty(time_ratio_val)
    skip_term = max(0.0, min(1.0, skip_rate))
    hist_term = 1.0 - max(0.0, min(1.0, hist_mastery))
    return w1 * acc_term + w2 * tp_term + w3 * skip_term + w4 * hist_term


def gap_band(score: float) -> Literal["strong", "moderate", "weak"]:
    """Discretises Learning Gap Score into standard bands:
    - < 0.30: strong (no significant gap)
    - 0.30 - 0.60: moderate (actionable gap, eligible for probe)
    - > 0.60: weak (severe gap, priority remediation)

    Examples:
        >>> gap_band(0.25)
        'strong'
        >>> gap_band(0.479)
        'moderate'
        >>> gap_band(0.68)
        'weak'
    """
    if score < 0.30:
        return "strong"
    elif score <= 0.60:
        return "moderate"
    return "weak"


def adaptive_priority(
    gap: float,
    days_to_target: int | float,
    skill_weight: float,
    dag_distance: int = 0,
    horizon: float = 120.0,
) -> float:
    """Computes priority rank for concept remediation queue (F14).

    Priority_c = Gap_c * Urgency_c * Relevance_c
    Urgency_c = clip(1 - days_to_target / H, 0.1, 1.0)
    Relevance_c = w_skill * (1 / (1 + dist_DAG(c, target)))

    Examples:
        >>> round(adaptive_priority(0.479, days_to_target=40, skill_weight=0.30, dag_distance=0, horizon=120.0), 3)
        0.096
    """
    urgency = max(0.1, min(1.0, 1.0 - float(days_to_target) / horizon))
    relevance = skill_weight * (1.0 / (1.0 + float(dag_distance)))
    return gap * urgency * relevance


def priority_score(
    gap: float,
    skill_weight: float,
    days_to_exam: int | float = 60,
    dag_distance: int = 0,
    horizon: float = 120.0,
) -> float:
    """Formula 14 adaptive priority calculation alias."""
    return adaptive_priority(
        gap=gap,
        days_to_target=days_to_exam,
        skill_weight=skill_weight,
        dag_distance=dag_distance,
        horizon=horizon,
    )


def mastery_decay(
    m0: float,
    elapsed_days: float,
    tau: float = 60.0,
) -> tuple[float, float]:
    """Computes mastery retention after elapsed time and half-life (F15).

    M_c(t) = M_c(t0) * exp(-(t - t0) / tau_c)
    t_half = tau_c * ln(2)

    Returns:
        (current_mastery, half_life_days)

    Examples:
        >>> m, t_half = mastery_decay(m0=0.80, elapsed_days=21.0, tau=60.0)
        >>> round(m, 3)
        0.564
        >>> round(t_half, 1)
        41.6
    """
    m_t = m0 * math.exp(-float(elapsed_days) / tau)
    t_half = tau * math.log(2.0)
    return m_t, t_half


def review_interval(
    m_current: float,
    m_target: float = 0.60,
    tau: float = 60.0,
) -> float:
    """Computes review interval in days before mastery decays to m_target (F16).

    delta_t_review = tau_c * ln(M_current / M_target)

    Examples:
        >>> round(review_interval(m_current=0.80, m_target=0.60, tau=60.0), 1)
        17.3
    """
    if m_current <= m_target:
        return 0.0
    return tau * math.log(m_current / m_target)


def readiness_score(
    skills_data: Sequence[dict[str, float] | tuple[float, float]],
) -> float:
    """Computes coverage-weighted readiness score across target skills (F17).

    Readiness = sum_s w_s * [ sum_{c in s} cov_c * M_c / sum_{c in s} cov_c ]

    Accepts list of dicts with keys 'weight' and 'mean_mastery', or (weight, mean_mastery) tuples.

    Examples:
        >>> # Spec rounded intermediate 0.35 * 0.55 = 0.1925 to 0.193 -> 0.681; exact float is 0.6805:
        >>> round(readiness_score([(0.40, 0.72), (0.35, 0.55), (0.25, 0.80)]), 2)
        0.68
        >>> round(readiness_score([(0.40, 0.72), (0.35, 0.553), (0.25, 0.80)]), 3)
        0.682
    """
    total = 0.0
    for item in skills_data:
        if isinstance(item, tuple):
            w_s, m_s = item
        else:
            w_s = item["weight"]
            m_s = item["mean_mastery"]
        total += w_s * m_s
    return total


def calculate_coverage_readiness(
    db: Any,
    user_id: int,
    target_id: int,
) -> dict[str, Any]:
    """Calculates coverage-based readiness (Formula 17):
    - Skill readiness = demonstrated_topics / total_topics_in_skill
    - Overall readiness = sum(skill_weight * skill_readiness)
    - If total_attempts == 0 -> label "Not assessed yet", score None
    - If completed_weekly_tests < 3 -> label "Provisional estimate"
    - If completed_weekly_tests >= 3 -> label "Calibrated estimate"
    """
    from sqlalchemy import select, func
    from backend.app.models.core import (
        Assessment,
        CareerTarget,
        Concept,
        Question,
        Skill,
        StudentMastery,
        StudentResponse,
        Topic,
    )

    target = db.get(CareerTarget, target_id)
    threshold = target.readiness_threshold if target else 0.70

    skills = db.execute(
        select(Skill).where(Skill.target_id == target_id).order_by(Skill.id)
    ).scalars().all()

    # Total user attempts across assessments
    total_attempts = db.execute(
        select(func.count(StudentResponse.id)).where(StudentResponse.user_id == user_id)
    ).scalar() or 0

    # Count completed weekly tests
    completed_weekly_tests = db.execute(
        select(func.count(Assessment.id)).where(
            Assessment.user_id == user_id,
            Assessment.type.in_(["weekly", "weekly_test"]),
            Assessment.completed_at.is_not(None),
        )
    ).scalar() or 0

    if total_attempts == 0:
        skill_components = []
        for s in skills:
            concepts = db.execute(
                select(Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .where(Topic.skill_id == s.id)
            ).scalars().all()
            total_count = len(concepts)
            skill_components.append({
                "skill_id": s.id,
                "skill_name": s.name,
                "weight": s.weight,
                "demonstrated_topics": 0,
                "total_topics": total_count,
                "skill_readiness": 0.0,
                "mean_mastery": 0.0,
                "skill_percentage": 0,
                "progress_text": f"0 of {total_count} topics demonstrated",
            })
        return {
            "target_id": target_id,
            "target_name": target.name if target else "Unknown",
            "readiness_score": 0.0,
            "readiness_percentage": 0,
            "readiness_threshold": threshold,
            "is_ready": False,
            "is_assessed": False,
            "total_attempts": 0,
            "completed_weekly_tests": 0,
            "label": "Take the Initial Diagnostic",
            "skill_components": skill_components,
        }

    # Find demonstrated concepts: answered correctly in StudentResponse or mastery >= 0.60
    correct_concept_ids = set(
        db.execute(
            select(Question.concept_id)
            .join(StudentResponse, StudentResponse.question_id == Question.id)
            .where(
                StudentResponse.user_id == user_id,
                StudentResponse.is_correct.is_(True),
            )
        ).scalars().all()
    )

    high_mastery_ids = set(
        db.execute(
            select(StudentMastery.concept_id).where(
                StudentMastery.user_id == user_id,
                StudentMastery.mastery_score >= 0.60,
            )
        ).scalars().all()
    )

    demonstrated_ids = correct_concept_ids | high_mastery_ids

    skill_components = []
    overall_readiness = 0.0

    for s in skills:
        concepts = db.execute(
            select(Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .where(Topic.skill_id == s.id)
        ).scalars().all()

        total_count = len(concepts)
        demonstrated_in_skill = sum(1 for cid in concepts if cid in demonstrated_ids)
        skill_readiness = (demonstrated_in_skill / total_count) if total_count > 0 else 0.0

        overall_readiness += s.weight * skill_readiness

        skill_components.append({
            "skill_id": s.id,
            "skill_name": s.name,
            "weight": s.weight,
            "demonstrated_topics": demonstrated_in_skill,
            "total_topics": total_count,
            "skill_readiness": round(skill_readiness, 4),
            "mean_mastery": round(skill_readiness, 4),
            "skill_percentage": round(skill_readiness * 100.0, 1),
            "progress_text": f"{demonstrated_in_skill} of {total_count} topics demonstrated",
        })

    # Count distinct topics demonstrated across entire syllabus
    all_target_topics = db.execute(
        select(Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
    ).scalars().all()
    total_syllabus_topics = len(all_target_topics)

    demonstrated_topics_set = set(
        db.execute(
            select(Topic.id)
            .join(Concept, Concept.topic_id == Topic.id)
            .where(Concept.id.in_(list(demonstrated_ids)))
        ).scalars().all()
    ) if demonstrated_ids else set()

    demonstrated_topics_count = len(demonstrated_topics_set)
    topic_coverage_readiness_pct = (
        round((demonstrated_topics_count / total_syllabus_topics) * 100.0, 1)
        if total_syllabus_topics > 0
        else 0.0
    )

    if total_attempts == 0:
        learning_stage = "Unassessed"
    elif topic_coverage_readiness_pct < 25.0:
        learning_stage = "Foundation Stage"
    elif topic_coverage_readiness_pct < 50.0:
        learning_stage = "Developing Stage"
    elif topic_coverage_readiness_pct < 75.0:
        learning_stage = "Proficient Stage"
    else:
        learning_stage = "Career Ready"

    label = "Calibrated estimate" if completed_weekly_tests >= 3 else "Provisional estimate"
    is_ready = bool(overall_readiness >= threshold)

    return {
        "target_id": target_id,
        "target_name": target.name if target else "Unknown",
        "readiness_score": round(overall_readiness, 4),
        "readiness_percentage": round(overall_readiness * 100.0, 1),
        "topic_coverage_readiness_pct": topic_coverage_readiness_pct,
        "learning_stage": learning_stage,
        "demonstrated_topics_count": demonstrated_topics_count,
        "total_syllabus_topics": total_syllabus_topics,
        "readiness_threshold": threshold,
        "is_ready": is_ready,
        "is_assessed": True,
        "total_attempts": total_attempts,
        "completed_weekly_tests": completed_weekly_tests,
        "label": label,
        "skill_components": skill_components,
    }
