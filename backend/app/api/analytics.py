"""Learner Analytics, Gap Scoring, Root Cause, and Readiness API Router."""
from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.api.diagnostic import find_valid_initial_assessment
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
    classify_error_evidence,
    get_ancestors_within_hops,
    present_as_mode,
    rank_root_cause_candidates,
    verify_graph_prerequisites,
)
from backend.app.services.weekly_adaptation import (
    compute_weekly_adaptation,
    get_weekly_adaptation_summary,
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

    # Fetch latest completed diagnostic with verified responses
    latest_diagnostic, diag_resp_count, _ = find_valid_initial_assessment(current_user.id, db)

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
        .order_by(LearningSchedule.scheduled_date, LearningSchedule.id)
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

    today = dt.date.today()
    if sched_rows and any(s.scheduled_date < today for s in sched_rows if s.status == "pending"):
        for idx, s_item in enumerate(sched_rows):
            s_item.scheduled_date = today + dt.timedelta(days=idx)
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
    if latest_diagnostic and diag_resp_count > 0:
        diag_resps = db.execute(
            select(StudentResponse, Question.concept_id)
            .join(Question, StudentResponse.question_id == Question.id)
            .where(StudentResponse.assessment_id == latest_diagnostic.id)
        ).all()
        if diag_resps:
            correct_count = sum(1 for r, _ in diag_resps if r.is_correct)
            total_q = len(diag_resps)
            acc_pct = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0
            demonstrated_distinct = len(set(cid for r, cid in diag_resps if r.is_correct))
            total_syllabus_topics = len(set(gi["topic_name"] for gi in gap_items))
            cov_readiness = round((demonstrated_distinct / total_syllabus_topics) * 100, 1) if total_syllabus_topics > 0 else 0.0

            diag_perf = {
                "assessment_id": latest_diagnostic.id,
                "score": round(latest_diagnostic.score, 1) if latest_diagnostic.score is not None else acc_pct,
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
        "diagnostic_completed": bool(latest_diagnostic and diag_resp_count > 0),
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
    target_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns root-cause prerequisite attribution (Phase 4):
    - Validates curriculum concept mapping and DAG prerequisite ancestors.
    - Scopes concept selection, masteries, and DAG strictly to active career target.
    - Classifies cognitive error type from student response and diagnostic probe evidence.
    - Computes attention weights and normalized entropy H_bar (F8) with honesty guard.
    - Explicitly returns attribution states:
      'valid_attribution', 'no_valid_prerequisites', 'missing_graph_mapping', 'insufficient_evidence'.
    """
    if target_id is None:
        profile = db.execute(
            select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
        ).scalar_one_or_none()
        target_id = profile.target_id if (profile and profile.target_id) else 1

    target_obj = db.get(CareerTarget, target_id)
    if not target_obj:
        target_id = 1
        target_obj = db.get(CareerTarget, 1)

    target_name = target_obj.name if target_obj else "General Curriculum"

    # Load all curriculum concepts strictly for this target
    target_concepts_rows = db.execute(
        select(Concept, Topic.name, Skill.name)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
        .order_by(Skill.id, Topic.id, Concept.id)
    ).all()

    if not target_concepts_rows:
        target_id = 1
        target_obj = db.get(CareerTarget, 1)
        target_name = target_obj.name if target_obj else "General Curriculum"
        target_concepts_rows = db.execute(
            select(Concept, Topic.name, Skill.name)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(Skill.target_id == 1)
            .order_by(Skill.id, Topic.id, Concept.id)
        ).all()

    target_concept_map = {c.id: (c, tname, sname) for c, tname, sname in target_concepts_rows}
    target_concept_ids = set(target_concept_map.keys())

    # Masteries map for user strictly within this target
    masteries = db.execute(
        select(StudentMastery).where(
            StudentMastery.user_id == current_user.id,
            StudentMastery.concept_id.in_(target_concept_ids),
        )
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    # Query user responses strictly within this target to compute mistake counts per concept
    all_user_resps = db.execute(
        select(StudentResponse.question_id, StudentResponse.is_correct, Question.concept_id)
        .join(Question, StudentResponse.question_id == Question.id)
        .where(
            StudentResponse.user_id == current_user.id,
            Question.concept_id.in_(target_concept_ids),
        )
    ).all()
    mistakes_by_concept: dict[int, int] = {}
    attempts_by_concept: dict[int, int] = {}
    for qid, is_corr, cid in all_user_resps:
        attempts_by_concept[cid] = attempts_by_concept.get(cid, 0) + 1
        if not is_corr:
            mistakes_by_concept[cid] = mistakes_by_concept.get(cid, 0) + 1

    target_concepts_list = []
    for c_obj, tname, sname in target_concepts_rows:
        m_score = mastery_map.get(c_obj.id, 0.50)
        m_cnt = mistakes_by_concept.get(c_obj.id, 0)
        att_cnt = attempts_by_concept.get(c_obj.id, 0)
        is_weak = (m_score < 0.65) or (m_cnt > 0)
        target_concepts_list.append({
            "concept_id": c_obj.id,
            "concept_name": c_obj.name,
            "topic_name": tname,
            "skill_name": sname,
            "mastery": round(m_score, 2),
            "mistakes_count": m_cnt,
            "attempts_count": att_cnt,
            "is_weak": is_weak,
        })

    # 1. Validate provided concept_id: must belong strictly to this target curriculum
    if concept_id is not None and concept_id not in target_concept_ids:
        concept_id = None

    # 2. If no valid concept_id specified, pick the best candidate in THIS target
    if not concept_id:
        concepts_with_mistakes = [tc for tc in target_concepts_list if tc["mistakes_count"] > 0]
        if concepts_with_mistakes:
            concept_id = concepts_with_mistakes[0]["concept_id"]
        else:
            weakest = db.execute(
                select(StudentMastery)
                .where(
                    StudentMastery.user_id == current_user.id,
                    StudentMastery.concept_id.in_(target_concept_ids),
                )
                .order_by(StudentMastery.mastery_score.asc())
            ).scalars().first()
            if weakest and weakest.concept_id in target_concept_ids:
                concept_id = weakest.concept_id
            elif target_concepts_list:
                concept_id = target_concepts_list[0]["concept_id"]
            else:
                concept_id = next(iter(target_concept_ids))

    surface_concept = db.get(Concept, concept_id)
    if not surface_concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concept not found in target curriculum",
        )

    surface_mastery = mastery_map.get(surface_concept.id, 0.45)

    # Concept names mapped strictly for this target
    name_map = {c.id: c.name for c, _, _ in target_concepts_rows}

    # Build curriculum DAG scoped strictly to this target's concept dependencies
    deps = db.execute(
        select(ConceptDependency).where(
            ConceptDependency.prerequisite_concept_id.in_(target_concept_ids),
            ConceptDependency.dependent_concept_id.in_(target_concept_ids),
        )
    ).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    # Ensure all target nodes exist in graph
    for cid in target_concept_ids:
        g.add_node(cid)

    # Verify prerequisite relationship on scoped target DAG
    attr_state, ancestors = verify_graph_prerequisites(
        graph=g,
        all_concept_ids=target_concept_ids,
        concept_id=surface_concept.id,
        max_hops=2,
    )

    # Query student's responses on this surface concept
    user_resps = db.execute(
        select(StudentResponse)
        .join(Question, StudentResponse.question_id == Question.id)
        .where(
            StudentResponse.user_id == current_user.id,
            Question.concept_id == surface_concept.id,
        )
        .order_by(StudentResponse.answered_at.desc())
    ).scalars().all()

    # Detailed mistake history for surface concept
    recent_mistakes = []
    for resp in user_resps:
        if not resp.is_correct:
            q = db.get(Question, resp.question_id)
            if q:
                recent_mistakes.append({
                    "response_id": resp.id,
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "options": q.options,
                    "user_answer": getattr(resp, "selected_answer", getattr(resp, "selected_option", "")),
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation or "Standard step-by-step syllabus solution.",
                    "response_time_ms": resp.response_time_ms,
                    "answered_at": resp.answered_at.isoformat() if resp.answered_at else None,
                })

    # Ancestor mistakes (prerequisite mistakes demonstrating upstream root cause)
    ancestor_mistakes = []
    for aid in ancestors:
        anc_resps = db.execute(
            select(StudentResponse, Question)
            .join(Question, StudentResponse.question_id == Question.id)
            .where(
                StudentResponse.user_id == current_user.id,
                Question.concept_id == aid,
                StudentResponse.is_correct == False,
            )
            .order_by(StudentResponse.answered_at.desc())
            .limit(3)
        ).all()
        for a_resp, a_q in anc_resps:
            ancestor_mistakes.append({
                "ancestor_concept_id": aid,
                "ancestor_concept_name": name_map.get(aid, f"Concept {aid}"),
                "question_id": a_q.id,
                "question_text": a_q.question_text,
                "user_answer": getattr(a_resp, "selected_answer", getattr(a_resp, "selected_option", "")),
                "correct_answer": a_q.correct_answer,
                "explanation": a_q.explanation or "Standard step-by-step solution.",
            })

    # Direct incoming and outgoing prerequisite edges within target
    direct_prerequisites = []
    for p_id in g.predecessors(surface_concept.id):
        if p_id in target_concept_ids:
            p_c = db.get(Concept, p_id)
            if p_c:
                direct_prerequisites.append({
                    "concept_id": p_c.id,
                    "concept_name": p_c.name,
                    "mastery": round(mastery_map.get(p_c.id, 0.5), 2),
                })

    direct_dependents = []
    for d_id in g.successors(surface_concept.id):
        if d_id in target_concept_ids:
            d_c = db.get(Concept, d_id)
            if d_c:
                direct_dependents.append({
                    "concept_id": d_c.id,
                    "concept_name": d_c.name,
                    "mastery": round(mastery_map.get(d_c.id, 0.5), 2),
                })

    failed_resp = next((r for r in user_resps if not r.is_correct), None)
    sub_resps = []
    if failed_resp:
        sub_resps = db.execute(
            select(StudentResponse)
            .where(StudentResponse.parent_response_id == failed_resp.id)
        ).scalars().all()

    concept_acc = (sum(1 for r in user_resps if r.is_correct) / len(user_resps)) if user_resps else None
    failed_q = db.get(Question, failed_resp.question_id) if failed_resp else None

    # Classify cognitive error
    error_classification = classify_error_evidence(
        main_response=failed_resp,
        sub_responses=sub_resps,
        question=failed_q,
        user_concept_accuracy=concept_acc,
        prerequisite_mastery={aid: mastery_map.get(aid, 0.5) for aid in ancestors},
    )

    # Check for insufficient evidence if graph mapping exists but user has no history/failures
    if attr_state == "valid_attribution" and not user_resps and surface_mastery >= 0.70:
        final_state = "insufficient_evidence"
    else:
        final_state = attr_state

    # Diagnosed cognitive gaps from 3 sub-question stages within target
    rc_records = db.execute(
        select(RootCauseAnalysis)
        .where(
            RootCauseAnalysis.user_id == current_user.id,
            RootCauseAnalysis.current_concept_id.in_(target_concept_ids),
        )
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

    if final_state == "valid_attribution":
        # Extract diagnostic evidence from sub-responses if available
        diag_evidence = {}
        for sr in sub_resps:
            sq = db.get(Question, sr.question_id)
            if sq and sq.concept_id in ancestors:
                diag_evidence[sq.concept_id] = sr.is_correct

        candidates = rank_root_cause_candidates(
            surface_concept_id=surface_concept.id,
            ancestors_with_hops=ancestors,
            concept_mastery=mastery_map,
            concept_names=name_map,
            diagnostic_sub_evidence=diag_evidence,
        )

        alphas = [c["attention_alpha"] for c in candidates]
        raw_h, norm_h = attention_entropy(alphas)
        presentation_mode = present_as_mode(norm_h)
        remediation_concept_id = candidates[0]["candidate_concept_id"] if candidates else surface_concept.id
        remediation_concept_name = candidates[0]["candidate_name"] if candidates else surface_concept.name
        honesty_disclaimer = "Graph-attention attribution computed across 2-hop prerequisite neighborhood."
    elif final_state == "no_valid_prerequisites":
        candidates = []
        raw_h = None
        norm_h = None
        presentation_mode = "no_prerequisites"
        remediation_concept_id = surface_concept.id
        remediation_concept_name = surface_concept.name
        honesty_disclaimer = f"'{surface_concept.name}' is a foundational root node in the curriculum graph with no prior prerequisites."
    elif final_state == "missing_graph_mapping":
        candidates = []
        raw_h = None
        norm_h = None
        presentation_mode = "missing_graph_mapping"
        remediation_concept_id = surface_concept.id
        remediation_concept_name = surface_concept.name
        honesty_disclaimer = f"Concept '{surface_concept.name}' is not currently linked in the curriculum dependency DAG."
    else:  # insufficient_evidence
        candidates = []
        raw_h = None
        norm_h = None
        presentation_mode = "insufficient_evidence"
        remediation_concept_id = surface_concept.id
        remediation_concept_name = surface_concept.name
        honesty_disclaimer = "No failed question attempts recorded for this concept. Further practice drills will calibrate prerequisite attribution."

    return {
        "target_id": target_id,
        "target_name": target_name,
        "surface_concept_id": surface_concept.id,
        "surface_concept_name": surface_concept.name,
        "surface_mastery": round(surface_mastery, 2),
        "attribution_state": final_state,
        "candidates": candidates,
        "attention_entropy": round(norm_h, 3) if norm_h is not None else None,
        "raw_entropy": round(raw_h, 3) if raw_h is not None else None,
        "present_as": presentation_mode,
        "error_classification": error_classification,
        "remediation_concept_id": remediation_concept_id,
        "remediation_concept_name": remediation_concept_name,
        "honesty_disclaimer": honesty_disclaimer,
        "cognitive_gaps": cognitive_gaps,
        "target_concepts": target_concepts_list,
        "recent_mistakes": recent_mistakes,
        "ancestor_mistakes": ancestor_mistakes,
        "direct_prerequisites": direct_prerequisites,
        "direct_dependents": direct_dependents,
    }


@router.get("/weekly-snapshots")
def get_weekly_snapshots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns rolling 7-day adaptation summary, WoW comparison, and root causes (Phase 5)."""
    return get_weekly_adaptation_summary(db=db, user_id=current_user.id)


@router.post("/refresh-weekly")
def refresh_weekly_adaptation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authorized manual refresh for weekly adaptation calculation."""
    compute_weekly_adaptation(db=db, user_id=current_user.id, force=True)
    return get_weekly_adaptation_summary(db=db, user_id=current_user.id)


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



@router.get("/mistake-history")
def get_mistake_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns assessment sessions (Initial Diagnostic, Week 1 Mistakes, Week 2 Mistakes, etc.)
    with the student's mistakes, selected options, correct answers, and explanations.
    """
    # Fetch all completed assessments for the current user in chronological order
    assessments = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == current_user.id,
            Assessment.completed_at.is_not(None),
        )
        .order_by(Assessment.completed_at.asc())
    ).scalars().all()

    weekly_count = 0
    initial_count = 0
    practice_count = 0

    sessions = []
    for asmt in assessments:
        # Determine title according to session type
        if asmt.type == "initial":
            initial_count += 1
            title = "Initial Diagnostic Mistakes" if initial_count == 1 else f"Initial Diagnostic (Retake {initial_count - 1}) Mistakes"
            short_label = "Initial Diagnostic" if initial_count == 1 else f"Initial Diagnostic #{initial_count}"
        elif asmt.type == "weekly_test":
            weekly_count += 1
            title = f"Week {weekly_count} Mistakes"
            short_label = f"Week {weekly_count}"
        elif asmt.type == "practice":
            practice_count += 1
            title = f"Practice Session #{practice_count} Mistakes"
            short_label = f"Practice #{practice_count}"
        elif asmt.type == "verification":
            title = "Verification Probe Mistakes"
            short_label = "Verification"
        elif asmt.type == "special":
            title = "Special Test Mode Mistakes"
            short_label = "Special Test"
        else:
            title = f"{asmt.type.replace('_', ' ').title()} Mistakes"
            short_label = asmt.type.replace('_', ' ').title()

        # Query responses for this assessment with question, concept, topic, skill details
        resps = db.execute(
            select(
                StudentResponse,
                Question,
                func.coalesce(Concept.name, "General Concept"),
                func.coalesce(Topic.name, "General Topic"),
                func.coalesce(Skill.name, "General Skill"),
            )
            .join(Question, StudentResponse.question_id == Question.id)
            .outerjoin(Concept, Question.concept_id == Concept.id)
            .outerjoin(Topic, Concept.topic_id == Topic.id)
            .outerjoin(Skill, Topic.skill_id == Skill.id)
            .where(StudentResponse.assessment_id == asmt.id)
            .order_by(StudentResponse.id.asc())
        ).all()

        items = []
        mistakes = []
        correct_count = 0

        for resp, q, concept_name, topic_name, skill_name in resps:
            opts = q.options_json if isinstance(q.options_json, dict) else {}
            corr_ans = q.correct_answer or ""
            corr_text = opts.get(corr_ans, corr_ans)
            sel_ans = resp.selected_answer
            sel_text = opts.get(sel_ans, sel_ans) if sel_ans else ("Skipped" if resp.skipped else "No answer")

            item_data = {
                "question_id": q.id,
                "question_text": q.question_text,
                "options": opts,
                "selected_answer": sel_ans,
                "selected_text": sel_text,
                "correct_answer": corr_ans,
                "correct_text": corr_text,
                "is_correct": bool(resp.is_correct),
                "skipped": bool(resp.skipped),
                "timed_out": bool(resp.timed_out),
                "response_time_ms": resp.response_time_ms,
                "explanation": q.explanation or "No explanation provided.",
                "concept_name": concept_name,
                "topic_name": topic_name,
                "skill_name": skill_name,
            }

            items.append(item_data)
            if resp.is_correct:
                correct_count += 1
            else:
                mistakes.append(item_data)

        total_q = len(items)
        if total_q == 0:
            continue

        score_pct = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0

        sessions.append({
            "assessment_id": asmt.id,
            "type": asmt.type,
            "title": title,
            "short_label": short_label,
            "completed_at": asmt.completed_at.isoformat() if asmt.completed_at else None,
            "score": asmt.score if asmt.score is not None else score_pct,
            "score_pct": score_pct,
            "total_questions": total_q,
            "correct_count": correct_count,
            "mistakes_count": len(mistakes),
            "mistakes": mistakes,
            "all_items": items,
        })

    # Return newest sessions first
    sessions.reverse()

    return {
        "total_sessions": len(sessions),
        "total_mistakes": sum(s["mistakes_count"] for s in sessions),
        "sessions": sessions,
    }
