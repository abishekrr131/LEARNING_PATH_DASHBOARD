"""Learner Analytics, Gap Scoring, Root Cause, and Readiness API Router."""
from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import (
    Assessment,
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningSchedule,
    Question,
    RootCauseAnalysis,
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
    calculate_coverage_readiness,
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
        if m_rec:
            m_score = m_rec.mastery_score
            conf = m_rec.confidence
            band = "strong" if m_score >= 0.70 else "moderate" if m_score >= 0.40 else "weak"
            has_history = True
        else:
            m_score = None
            conf = 0.0
            band = None
            has_history = False

        items.append({
            "concept_id": c.id,
            "concept_name": c.name,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery_score": round(m_score, 2) if m_score is not None else None,
            "confidence": round(conf, 2),
            "band": band,
            "has_history": has_history,
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

    # Fetch concepts with skills and topics
    concepts_rows = db.execute(
        select(Concept, Skill.name, Skill.weight, Topic.id, Topic.name)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
        .order_by(Skill.weight.desc(), Topic.id, Concept.id)
    ).all()

    # Get topic performance / student masteries
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    # Responses to calculate empirical accuracy / skip rate
    responses = db.execute(
        select(StudentResponse, Question.concept_id)
        .join(Question, StudentResponse.question_id == Question.id)
        .where(StudentResponse.user_id == current_user.id)
    ).all()
    resp_by_concept: dict[int, list[StudentResponse]] = {}
    for r, cid in responses:
        if cid not in resp_by_concept:
            resp_by_concept[cid] = []
        resp_by_concept[cid].append(r)

    total_user_attempts = len(responses)

    # Fetch latest completed diagnostic
    latest_diagnostic = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == current_user.id,
            Assessment.type == "initial",
            Assessment.completed_at.is_not(None),
        )
        .order_by(Assessment.completed_at.desc())
    ).scalars().first()

    gap_items = []
    for c, skill_name, skill_weight, topic_id, topic_name in concepts_rows:
        c_resps = resp_by_concept.get(c.id, [])
        attempts_count = len(c_resps)

        if attempts_count == 0:
            gap_items.append({
                "concept_id": c.id,
                "concept_name": c.name,
                "topic_id": topic_id,
                "topic_name": topic_name,
                "skill_name": skill_name,
                "attempts_count": 0,
                "status": "unassessed",
                "accuracy": None,
                "time_ratio": None,
                "skip_rate": None,
                "historical_mastery": None,
                "gap_score": None,
                "band": None,
                "priority": None,
                "is_preliminary": False,
            })
        elif attempts_count == 1:
            corr = sum(1 for x in c_resps if x.is_correct)
            acc = corr / 1.0
            skips = sum(1 for x in c_resps if x.skipped)
            skip_rate = skips / 1.0
            avg_time = c_resps[0].response_time_ms
            tr = avg_time / 60000.0
            m_score = mastery_map.get(c.id, 0.50)
            gap = 0.40 * (1.0 - acc) + 0.20 * max(0.0, min(1.0, (tr - 1.0) / 2.0)) + 0.20 * skip_rate + 0.20 * (1.0 - m_score)
            band = gap_band(gap)
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
                "topic_id": topic_id,
                "topic_name": topic_name,
                "skill_name": skill_name,
                "attempts_count": 1,
                "status": "assessed",
                "accuracy": round(acc, 2),
                "time_ratio": round(tr, 2),
                "skip_rate": round(skip_rate, 2),
                "historical_mastery": round(m_score, 2),
                "gap_score": round(gap, 3),
                "band": band,
                "priority": round(pri, 4),
                "is_preliminary": True,
            })
        else:
            corr = sum(1 for x in c_resps if x.is_correct)
            acc = corr / attempts_count
            skips = sum(1 for x in c_resps if x.skipped)
            skip_rate = skips / attempts_count
            avg_time = sum(x.response_time_ms for x in c_resps) / attempts_count
            tr = avg_time / 60000.0
            m_score = mastery_map.get(c.id, 0.50)
            gap = 0.40 * (1.0 - acc) + 0.20 * max(0.0, min(1.0, (tr - 1.0) / 2.0)) + 0.20 * skip_rate + 0.20 * (1.0 - m_score)
            band = gap_band(gap)
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
                "topic_id": topic_id,
                "topic_name": topic_name,
                "skill_name": skill_name,
                "attempts_count": attempts_count,
                "status": "assessed",
                "accuracy": round(acc, 2),
                "time_ratio": round(tr, 2),
                "skip_rate": round(skip_rate, 2),
                "historical_mastery": round(m_score, 2),
                "gap_score": round(gap, 3),
                "band": band,
                "priority": round(pri, 4),
                "is_preliminary": False,
            })

    # Sort descending by priority: items with valid priority first, unassessed last
    gap_items.sort(
        key=lambda x: (x["priority"] is not None, x["priority"] if x["priority"] is not None else -1.0),
        reverse=True,
    )

    # Build DAG for prerequisite/unlock lookup
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])

    # Compute subject-by-subject progression rules
    skills = db.execute(
        select(Skill).where(Skill.target_id == target_id).order_by(Skill.weight.desc())
    ).scalars().all()

    subject_recommendations = []
    for s in skills:
        s_gaps = [gi for gi in gap_items if gi["skill_name"] == s.name]
        assessed_s = [gi for gi in s_gaps if gi["status"] == "assessed"]

        if not assessed_s:
            first_un = s_gaps[0] if s_gaps else None
            t_name = first_un["topic_name"] if first_un else "Foundations"
            subject_recommendations.append({
                "subject": s.name,
                "weight": s.weight,
                "status": "Unassessed",
                "status_badge": "unassessed",
                "assessed_topic": None,
                "demonstrated_accuracy": None,
                "recommended_topic": t_name,
                "action": "Foundational baseline coverage",
                "reason": f"Unassessed syllabus baseline: Start with {t_name} to calibrate competency.",
                "advancement_unlocked": False,
                "follow_up_required": True,
            })
        else:
            weak_assessed = [gi for gi in assessed_s if gi["accuracy"] < 0.80]
            if weak_assessed:
                first_weak = weak_assessed[0]
                acc_pct = int(first_weak["accuracy"] * 100)
                subject_recommendations.append({
                    "subject": s.name,
                    "weight": s.weight,
                    "status": "Weak (Remediation Priority)",
                    "status_badge": "weak",
                    "assessed_topic": first_weak["topic_name"],
                    "demonstrated_accuracy": f"{acc_pct}%",
                    "recommended_topic": first_weak["topic_name"],
                    "action": f"Targeted remediation on {first_weak['topic_name']}",
                    "reason": f"Priority remediation: Accuracy was {acc_pct}% (<80% threshold). Advancement paused until mastery met.",
                    "advancement_unlocked": False,
                    "follow_up_required": True,
                })
            else:
                # All assessed in this subject met mastery threshold (>= 80%)
                first_m = assessed_s[0]
                acc_pct = int(first_m["accuracy"] * 100)
                # Check DAG successor for next eligible topic
                succ_cids = g.successors(first_m["concept_id"])
                ratio_succs = [scid for scid in succ_cids if any(kw in (db.get(Concept, scid).name if db.get(Concept, scid) else "") for kw in ("Ratio", "Proportion"))]
                ordered_succs = ratio_succs + [scid for scid in succ_cids if scid not in ratio_succs]
                next_top_name = None
                for scid in ordered_succs:
                    sc = db.get(Concept, scid)
                    if sc and sc.topic and sc.topic.skill_id == s.id:
                        next_top_name = sc.name if (sc.topic.name == first_m["topic_name"] or any(kw in sc.name for kw in ("Ratio", "Proportion"))) else sc.topic.name
                        break

                if not next_top_name:
                    # Next in syllabus
                    s_top_names = list(dict.fromkeys(gi["topic_name"] for gi in s_gaps))
                    curr_idx = s_top_names.index(first_m["topic_name"]) if first_m["topic_name"] in s_top_names else 0
                    next_top_name = s_top_names[curr_idx + 1] if curr_idx + 1 < len(s_top_names) else first_m["topic_name"]

                subject_recommendations.append({
                    "subject": s.name,
                    "weight": s.weight,
                    "status": "Mastered (Advancing)",
                    "status_badge": "mastered",
                    "assessed_topic": first_m["topic_name"],
                    "demonstrated_accuracy": f"{acc_pct}%",
                    "recommended_topic": next_top_name,
                    "action": f"Unlock advancement to {next_top_name}",
                    "reason": f"Topic unlocked: Advanced to {next_top_name} following demonstrated mastery in {first_m['topic_name']} (>=80%).",
                    "advancement_unlocked": True,
                    "follow_up_required": False,
                })

    # Retrieve or recover Week 1 Plan
    sched_rows = db.execute(
        select(LearningSchedule)
        .where(LearningSchedule.user_id == current_user.id)
        .order_by(LearningSchedule.scheduled_date)
    ).scalars().all()

    if latest_diagnostic and not sched_rows:
        from backend.app.services.question_generator import synthesize_week_schedule
        sched_rows = synthesize_week_schedule(
            user_id=current_user.id,
            target_id=target_id,
            db=db,
            week_number=1,
        )
        db.commit()

    week_1_plan = []
    for s_item in sched_rows:
        week_1_plan.append({
            "id": s_item.id,
            "scheduled_date": s_item.scheduled_date.isoformat(),
            "subject": s_item.subject or "Curriculum Track",
            "topic_name": s_item.topic_name or "Study Block",
            "learning_objective": s_item.learning_objective,
            "resource_title": s_item.resource_title,
            "resource_url": s_item.resource_url,
            "practice_activity": s_item.practice_activity,
            "duration_min": s_item.duration_min,
            "mastery_target": s_item.mastery_target or 0.80,
            "follow_up_assessment": s_item.follow_up_assessment,
            "plan_reason": s_item.plan_reason,
            "activity_type": s_item.activity_type,
            "status": s_item.status,
            "completed": (s_item.status == "completed"),
        })

    # Diagnostic performance summary
    diag_perf = None
    if latest_diagnostic:
        diag_resps = db.execute(
            select(StudentResponse, Question.concept_id)
            .join(Question, StudentResponse.question_id == Question.id)
            .where(StudentResponse.assessment_id == latest_diagnostic.id)
        ).all()
        correct_count = sum(1 for r, _ in diag_resps if r.is_correct)
        total_q = len(diag_resps) or 10
        acc_pct = round((correct_count / total_q) * 100, 1)
        demonstrated_distinct = len(set(cid for r, cid in diag_resps if r.is_correct))
        total_syllabus_topics = len(set(gi["topic_name"] for gi in gap_items))
        cov_readiness = round((demonstrated_distinct / total_syllabus_topics) * 100, 1) if total_syllabus_topics > 0 else 0.0

        diag_perf = {
            "assessment_id": latest_diagnostic.id,
            "score": round(latest_diagnostic.score, 1) if latest_diagnostic.score is not None else 0.0,
            "accuracy_pct": acc_pct,
            "correct_count": correct_count,
            "total_questions": total_q,
            "completed_at": latest_diagnostic.completed_at.isoformat() if latest_diagnostic.completed_at else None,
            "distinct_topics_demonstrated": demonstrated_distinct,
            "total_syllabus_topics": total_syllabus_topics,
            "topic_coverage_readiness": cov_readiness,
        }

    target = db.get(CareerTarget, target_id)

    return {
        "target_id": target_id,
        "target_name": target.name if target else "",
        "days_to_exam": days_to_exam,
        "total_attempts": total_user_attempts,
        "diagnostic_completed": bool(latest_diagnostic),
        "latest_diagnostic": diag_perf,
        "summary": {
            "total_concepts": len(gap_items),
            "assessed_count": len([g for g in gap_items if g["status"] != "unassessed"]),
            "strengths_count": len([g for g in gap_items if g["band"] == "strong"]),
            "moderate_count": len([g for g in gap_items if g["band"] == "moderate"]),
            "weak_count": len([g for g in gap_items if g["band"] == "weak"]),
            "unassessed_count": len([g for g in gap_items if g["status"] == "unassessed"]),
        },
        "subject_recommendations": subject_recommendations,
        "gaps": gap_items,
        "week_1_plan": week_1_plan,
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

    # Diagnosed cognitive gaps from 3 sub-question stages
    rc_records = db.execute(
        select(RootCauseAnalysis)
        .where(RootCauseAnalysis.user_id == current_user.id)
        .order_by(RootCauseAnalysis.created_at.desc())
    ).scalars().all()

    cognitive_gaps = []
    for r in rc_records:
        if r.evidence_json and "cognitive_gap" in r.evidence_json:
            cognitive_gaps.append({
                "id": r.id,
                "concept_id": r.current_concept_id,
                "topic_name": r.evidence_json.get("topic_name", "General"),
                "concept_name": r.evidence_json.get("concept_name", "Concept"),
                "main_question_stem": r.evidence_json.get("main_question_stem", ""),
                "cognitive_gap": r.evidence_json["cognitive_gap"],
                "upstream_prerequisites": r.evidence_json.get("upstream_prerequisites", []),
                "diagnosed_at": r.created_at.isoformat() if r.created_at else None,
            })

    return {
        "surface_concept_id": surface_concept.id,
        "surface_concept_name": surface_concept.name,
        "surface_mastery": round(surface_mastery, 2),
        "candidates": candidates,
        "attention_entropy": round(norm_h, 3),
        "raw_entropy": round(raw_h, 3),
        "present_as": presentation_mode,
        "honesty_disclaimer": "This analysis is an estimate of cognitive prerequisites, not a guarantee.",
        "cognitive_gaps": cognitive_gaps,
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
    return calculate_coverage_readiness(db=db, user_id=current_user.id, target_id=target_id)


@router.get("/career-map")
def get_career_map_analytics(
    target_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the adaptive Career Ready Map derived from diagnostic and practice results."""
    from backend.app.services.career_map import calculate_career_ready_map

    return calculate_career_ready_map(db=db, user_id=current_user.id, target_id=target_id)

