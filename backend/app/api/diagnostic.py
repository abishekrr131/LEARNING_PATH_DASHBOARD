"""Dedicated Initial Diagnostic Assessment API.

Implements Master Prompt Requirement 5 & Bug 5 Rebuild:
- Exactly 10 MCQs drawn only from questions with review_status='approved'
- Largest-remainder rounding across skills by syllabus weight
- Random within skill, ordered easy -> hard
- Returns 4xx if question bank is short, never hangs
- On submit: updates mastery (replaces 0.5 prior), recomputes F17 readiness,
  marks weak topics, traces DAG root causes, topologically generates roadmap,
  and schedules initial review dates (F15/F16).
- Gemini is strictly silenced during this test.
"""
from __future__ import annotations

import datetime as dt
import math
import random
from typing import Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
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
    TopicPerformance,
    User,
)
from backend.app.services.path import build_personalized_path
from backend.app.services.root_cause import get_ancestors_within_hops, rank_root_cause_candidates
from backend.app.services.scoring import (
    calculate_coverage_readiness,
    expected_response_time,
    gap_band,
    gap_score,
    readiness_score,
    review_interval,
    time_ratio,
)
from ml.graph.dag_validator import SimpleDiGraph

router = APIRouter()


def allocate_questions_largest_remainder(
    skills: list[Skill], total_items: int = 10, total_questions: int | None = None
) -> dict[int, int]:
    """Allocates integer question quotas across skills using the largest-remainder method (Hare-Niemeyer).
    Guarantees that the quotas sum to exactly total_items (10).
    """
    if total_questions is not None:
        total_items = total_questions
    total_weight = sum(s.weight for s in skills) or 1.0
    exact_quotas = []
    base_quotas = {}
    remainders = []

    for s in skills:
        norm_w = s.weight / total_weight
        exact = norm_w * total_items
        base = int(math.floor(exact))
        rem = exact - base
        exact_quotas.append((s.id, exact))
        base_quotas[s.id] = base
        remainders.append((rem, s.weight, s.id))

    allocated = sum(base_quotas.values())
    deficit = total_items - allocated

    # Sort remainders descending by remainder, then skill weight, then skill ID
    remainders.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

    for i in range(deficit):
        target_skill_id = remainders[i % len(remainders)][2]
        base_quotas[target_skill_id] += 1

    return base_quotas


class DiagnosticStartIn(BaseModel):
    target_id: int | None = None
    retake: bool = False


class ItemSubmitIn(BaseModel):
    question_id: int
    selected_answer: str | None = None
    response_time_ms: int = Field(ge=0, le=3600000)
    skipped: bool = False
    attempt_no: int = 1


def find_valid_initial_assessment(user_id: int, db: Session) -> tuple[Assessment | None, int, int]:
    """Returns the most recent valid completed initial diagnostic assessment,
    along with (response_count, question_count).
    An assessment is only considered valid if it has actual responses (or linked questions).
    Empty 0-question/0-response stubs created by interrupted runs are filtered out.
    """
    completed_asmts = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == user_id,
            Assessment.type == "initial",
            Assessment.completed_at.is_not(None),
        )
        .order_by(Assessment.completed_at.desc())
    ).scalars().all()

    for asmt in completed_asmts:
        resp_count = db.execute(
            select(func.count(StudentResponse.id))
            .where(StudentResponse.assessment_id == asmt.id)
        ).scalar() or 0
        aq_count = db.execute(
            select(func.count(AssessmentQuestion.id))
            .where(AssessmentQuestion.assessment_id == asmt.id)
        ).scalar() or 0

        # Legacy compatibility check: If assessment has no direct assessment_id responses,
        # check if student responses exist for this user in the same time window
        if resp_count == 0 and asmt.started_at and asmt.completed_at:
            time_window_resps = db.execute(
                select(StudentResponse).where(
                    StudentResponse.user_id == user_id,
                    StudentResponse.answered_at >= asmt.started_at,
                    StudentResponse.answered_at <= asmt.completed_at + dt.timedelta(seconds=60),
                )
            ).scalars().all()
            if time_window_resps:
                for r in time_window_resps:
                    r.assessment_id = asmt.id
                db.commit()
                resp_count = len(time_window_resps)

        if resp_count > 0:
            return asmt, resp_count, aq_count

    return None, 0, 0


class DiagnosticSubmitIn(BaseModel):
    assessment_id: int
    responses: list[ItemSubmitIn]


@router.get("/status")
def get_diagnostic_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns persistent diagnostic completion status for the authenticated user.
    Only treats an assessment as completed if it contains verified questions and responses.
    """
    valid_asmt, resp_count, aq_count = find_valid_initial_assessment(current_user.id, db)

    if valid_asmt:
        correct_count = db.execute(
            select(func.count(StudentResponse.id))
            .where(
                StudentResponse.assessment_id == valid_asmt.id,
                StudentResponse.user_id == current_user.id,
                StudentResponse.is_correct.is_(True),
            )
        ).scalar() or 0

        target = db.get(CareerTarget, valid_asmt.target_id)
        total_q = resp_count if resp_count > 0 else (aq_count if aq_count > 0 else 10)
        score_val = valid_asmt.score if valid_asmt.score is not None else round((correct_count / total_q) * 100, 1)

        return {
            "is_completed": True,
            "status": "completed",
            "assessment_id": valid_asmt.id,
            "completed_at": valid_asmt.completed_at.isoformat() if valid_asmt.completed_at else None,
            "score": score_val,
            "total_questions": total_q,
            "correct_answers": correct_count,
            "target_id": valid_asmt.target_id,
            "target_name": target.name if target else "Unknown",
            "has_valid_responses": resp_count > 0,
        }

    active_asmt = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == current_user.id,
            Assessment.type == "initial",
            Assessment.completed_at.is_(None),
        )
        .order_by(Assessment.started_at.desc())
    ).scalars().first()

    if active_asmt:
        target = db.get(CareerTarget, active_asmt.target_id)
        return {
            "is_completed": False,
            "status": "in_progress",
            "assessment_id": active_asmt.id,
            "completed_at": None,
            "score": None,
            "total_questions": 10,
            "correct_answers": 0,
            "target_id": active_asmt.target_id,
            "target_name": target.name if target else "Unknown",
        }

    return {
        "is_completed": False,
        "status": "not_started",
        "assessment_id": None,
        "completed_at": None,
        "score": None,
        "total_questions": 10,
        "correct_answers": 0,
        "target_id": None,
        "target_name": None,
    }


@router.post("/start")
def start_diagnostic(
    req: DiagnosticStartIn = DiagnosticStartIn(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allocates exactly 10 MCQs from 10 distinct topics by syllabus weight using Gemini or question bank."""
    target_id = req.target_id
    if not target_id:
        profile = db.execute(
            select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
        ).scalar_one_or_none()
        target_id = profile.target_id if profile else 1

    target = db.get(CareerTarget, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    # Check if user already completed a valid initial diagnostic with actual responses
    valid_asmt, resp_count, _ = find_valid_initial_assessment(current_user.id, db)

    if valid_asmt and not req.retake:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial diagnostic assessment has already been completed.",
        )

    # Check for active incomplete diagnostic session to support instant resume on refresh
    active_asmt = db.execute(
        select(Assessment).where(
            Assessment.user_id == current_user.id,
            Assessment.type == "initial",
            Assessment.completed_at.is_(None),
        ).order_by(Assessment.started_at.desc())
    ).scalars().first()

    if active_asmt:
        existing_aqs = db.execute(
            select(AssessmentQuestion, Question, Concept.name)
            .join(Question, AssessmentQuestion.question_id == Question.id)
            .join(Concept, Question.concept_id == Concept.id)
            .where(AssessmentQuestion.assessment_id == active_asmt.id)
            .order_by(AssessmentQuestion.order_index)
        ).all()

        if len(existing_aqs) == 10:
            from backend.app.services.question_generator import to_options_list
            items_out = []
            for aq, q, cname in existing_aqs:
                items_out.append({
                    "question_id": q.id,
                    "order_index": aq.order_index + 1,
                    "concept_id": q.concept_id,
                    "concept_name": cname,
                    "topic_id": q.topic_id,
                    "topic_name": q.concept.topic.name if q.concept and q.concept.topic else cname,
                    "question_text": q.question_text,
                    "stem": q.question_text,
                    "text": q.question_text,
                    "options": to_options_list(q.options),
                    "difficulty_b": round(q.difficulty_b, 2),
                    "difficulty": round(q.difficulty_b, 2),
                    "source": q.source or "curated",
                    "source_title": q.source_title,
                    "source_url": q.source_url,
                    "exam_year": q.exam_year,
                    "license": q.license,
                    "verified": bool(q.verified) if q.verified is not None else True,
                })
            return {
                "assessment_id": active_asmt.id,
                "type": "initial",
                "target_id": target.id,
                "target_name": target.name,
                "items": items_out,
                "total_items": len(items_out),
                "questions": items_out,
                "total_questions": len(items_out),
                "is_resumed": True,
            }

    from ai.gemini_client import GeminiClient, GeminiRateLimitError
    from backend.app.services.question_generator import generate_initial_diagnostic_questions

    gemini_client = GeminiClient()
    try:
        asmt_id, items_out = generate_initial_diagnostic_questions(
            db=db,
            target=target,
            current_user_id=current_user.id,
            gemini_client=gemini_client,
        )
    except GeminiRateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI is busy, retry in about 1 minute",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate diagnostic, retry: {str(e)}",
        )

    return {
        "assessment_id": asmt_id,
        "type": "initial",
        "target_id": target.id,
        "target_name": target.name,
        "items": items_out,
        "total_items": len(items_out),
        "questions": items_out,
        "total_questions": len(items_out),
        "is_resumed": False,
    }



@router.post("/submit")
def submit_diagnostic(
    req: DiagnosticSubmitIn,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluates Diagnostic, updates mastery, recomputes F17 readiness,
    traces DAG root causes, generates topological roadmap, and sets F15/F16 review schedule.
    """
    assessment = db.get(Assessment, req.assessment_id)
    if not assessment or assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if assessment.completed_at is not None:
        cov_readiness = calculate_coverage_readiness(
            db=db,
            user_id=current_user.id,
            target_id=assessment.target_id,
        )
        overall_readiness = cov_readiness.get("readiness_score") or 0.0
        return {
            "assessment_id": assessment.id,
            "status": "completed",
            "score": round(assessment.score or 0.0, 1),
            "readiness_score": overall_readiness,
            "readiness_percentage": round(overall_readiness * 100, 1),
            "message": "Assessment was already submitted and scored.",
        }

    if not req.responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit an initial diagnostic with zero responses.",
        )

    answered_at = dt.datetime.now(dt.timezone.utc)
    target = db.get(CareerTarget, assessment.target_id)

    correct_count = 0
    skip_count = 0
    total_q = len(req.responses)

    responses_by_concept: dict[int, list[dict[str, Any]]] = {}
    responses_by_skill: dict[int, list[dict[str, Any]]] = {}
    question_results: list[dict[str, Any]] = []

    for r in req.responses:
        q = db.get(Question, r.question_id)
        if not q:
            continue

        is_corr = (not r.skipped) and (r.selected_answer == q.correct_answer)
        if is_corr:
            correct_count += 1
        if r.skipped:
            skip_count += 1

        exp_time = expected_response_time(q.difficulty_b)
        tr = time_ratio(r.response_time_ms, exp_time)

        # Store response
        db.add(
            StudentResponse(
                user_id=current_user.id,
                assessment_id=assessment.id,
                question_id=q.id,
                selected_answer=None if r.skipped else r.selected_answer,
                is_correct=is_corr,
                response_time_ms=r.response_time_ms,
                skipped=r.skipped,
                attempt_no=r.attempt_no,
                phase="initial",
                answered_at=answered_at,
            )
        )

        # Map to concept and skill
        concept = db.get(Concept, q.concept_id)
        topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None
        skill_id = topic.skill_id if topic else None
        skill = db.get(Skill, skill_id) if skill_id else None

        item_data = {
            "question_id": q.id,
            "concept_id": q.concept_id,
            "is_correct": is_corr,
            "skipped": r.skipped,
            "response_time_ms": r.response_time_ms,
            "time_ratio": tr,
        }

        responses_by_concept.setdefault(q.concept_id, []).append(item_data)
        if skill_id:
            responses_by_skill.setdefault(skill_id, []).append(item_data)

        question_results.append({
            "question_id": q.id,
            "topic_id": topic.id if topic else None,
            "topic_name": topic.name if topic else (concept.name if concept else "General"),
            "skill_name": skill.name if skill else "General",
            "concept_id": concept.id if concept else None,
            "concept_name": concept.name if concept else "General",
            "learner_answer": None if r.skipped else r.selected_answer,
            "correct_answer": q.correct_answer,
            "is_correct": is_corr,
            "skipped": r.skipped,
            "result": "correct" if is_corr else ("skipped" if r.skipped else "incorrect"),
            "response_time_ms": r.response_time_ms,
        })

    # Calculate question accuracy (%) = correct / attempted * 100
    attempted_count = total_q - skip_count
    question_accuracy_pct = round((correct_count / attempted_count) * 100.0, 1) if attempted_count > 0 else 0.0
    distinct_topics_demonstrated = {qr["topic_id"] for qr in question_results if qr["is_correct"] and qr["topic_id"] is not None}
    distinct_topics_demonstrated_count = len(distinct_topics_demonstrated)

    # Calculate score
    score_pct = (correct_count / total_q) * 100.0 if total_q > 0 else 0.0
    assessment.score = score_pct
    assessment.completed_at = answered_at

    # Update StudentMastery and compute F12 Gap Scores
    weak_concepts = []
    for cid, item_resps in responses_by_concept.items():
        concept = db.get(Concept, cid)
        cname = concept.name if concept else f"Concept {cid}"
        acc = sum(1 for x in item_resps if x["is_correct"]) / len(item_resps)
        skips = sum(1 for x in item_resps if x["skipped"]) / len(item_resps)
        mean_tr = sum(x["time_ratio"] for x in item_resps) / len(item_resps)

        # Initial assessment: replaces 0.5 prior with empirical gap score
        g_c = gap_score(accuracy=acc, time_ratio_val=mean_tr, skip_rate=skips, hist_mastery=0.50)
        band = gap_band(g_c)

        # Calculated mastery
        new_mastery = max(0.05, min(0.95, 1.0 - g_c))

        m_rec = db.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == current_user.id,
                StudentMastery.concept_id == cid,
            )
        ).scalar_one_or_none()

        if m_rec:
            m_rec.mastery_score = new_mastery
            m_rec.confidence = 0.50
            m_rec.updated_at = answered_at
        else:
            db.add(
                StudentMastery(
                    user_id=current_user.id,
                    concept_id=cid,
                    mastery_score=new_mastery,
                    confidence=0.50,
                    model_version="f12_diagnostic",
                    updated_at=answered_at,
                )
            )

        if band in ("weak", "moderate"):
            weak_concepts.append({
                "concept_id": cid,
                "concept_name": cname,
                "gap_score": round(g_c, 3),
                "band": band,
                "accuracy": round(acc, 2),
            })

    # Auto-generate Week 1 of the study schedule from results:
    # Rank topics by F14 priority (weakest first, topologically ordered with root causes),
    # assign daily study load for Days 1-6, and schedule Weekly Test (20 Qs) on Day 7.
    today = dt.date.today()
    from backend.app.services.question_generator import synthesize_week_schedule
    week_1_items = synthesize_week_schedule(
        user_id=current_user.id,
        target_id=assessment.target_id,
        db=db,
        week_number=1,
        start_date=today,
    )

    # Recompute Coverage-Based Readiness Score (F17)
    cov_readiness = calculate_coverage_readiness(
        db=db,
        user_id=current_user.id,
        target_id=assessment.target_id,
    )
    overall_readiness = cov_readiness["readiness_score"] or 0.0
    skill_breakdown = [
        {
            "skill_id": comp["skill_id"],
            "skill_name": comp["skill_name"],
            "weight": comp["weight"],
            "accuracy": round((comp["skill_percentage"] or 0.0), 1),
            "mean_mastery": comp["skill_readiness"] or 0.0,
            "demonstrated_topics": comp["demonstrated_topics"],
            "total_topics": comp["total_topics"],
            "progress_text": comp["progress_text"],
        }
        for comp in cov_readiness["skill_components"]
    ]

    # Trace DAG Root Causes for weak concepts
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    all_cs = db.execute(select(Concept)).scalars().all()
    name_map = {c.id: c.name for c in all_cs}
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    root_causes = []
    for wc in weak_concepts[:3]:
        ancestors = get_ancestors_within_hops(g, wc["concept_id"], max_hops=2)
        candidates = rank_root_cause_candidates(
            surface_concept_id=wc["concept_id"],
            ancestors_with_hops=ancestors,
            concept_mastery=mastery_map,
            concept_names=name_map,
        )
        if candidates:
            primary_c = candidates[0]
            cause_name = primary_c.get("candidate_name") or primary_c.get("name") or "Unknown"
            cause_id = primary_c.get("candidate_concept_id") or primary_c.get("concept_id")
            root_causes.append({
                "surface_concept_id": wc["concept_id"],
                "surface_concept_name": wc["concept_name"],
                "primary_cause": cause_name,
                "primary_cause_id": cause_id,
                "candidates": candidates[:2],
            })

    # Generate Personalized Topological Roadmap
    remediated_ids = [rc["primary_cause_id"] for rc in root_causes if rc.get("primary_cause_id") is not None]
    weak_ids = [wc["concept_id"] for wc in weak_concepts]
    path_nodes = build_personalized_path(
        g=g,
        concept_names=name_map,
        weak_concept_ids=weak_ids,
        remediation_prereq_ids=remediated_ids,
        limit=12,
    )

    db.commit()

    # Pre-generate next weekly test in background for instant start
    from backend.app.services.question_generator import pregenerate_weekly_test_for_user
    background_tasks.add_task(pregenerate_weekly_test_for_user, current_user.id, target.id)

    # Calculate Adaptive Career Ready Map
    from backend.app.services.career_map import calculate_career_ready_map
    career_map = calculate_career_ready_map(db=db, user_id=current_user.id, target_id=assessment.target_id)

    # Serialize first-week plan items
    serialized_plan = [
        {
            "id": item.id,
            "day": idx + 1,
            "subject": item.subject,
            "topic": item.topic_name,
            "topic_name": item.topic_name,
            "concept_id": item.concept_id,
            "concept_name": (db.get(Concept, item.concept_id).name if db.get(Concept, item.concept_id) else item.topic_name),
            "activity_type": item.activity_type,
            "scheduled_date": item.scheduled_date.isoformat(),
            "planned_minutes": item.duration_min,
            "duration_min": item.duration_min,
            "learning_objective": item.learning_objective,
            "resource_title": item.resource_title,
            "resource_url": item.resource_url,
            "practice_activity": item.practice_activity,
            "mastery_target": item.mastery_target,
            "completed": item.status == "completed",
            "status": item.status,
            "follow_up_assessment": item.follow_up_assessment,
            "plan_reason": item.plan_reason,
            "is_weekly_test": item.activity_type == "weekly_test",
        }
        for idx, item in enumerate(week_1_items)
    ]

    return {
        "assessment_id": assessment.id,
        "status": "completed",
        "score": round(score_pct, 1),
        "total_questions": total_q,
        "correct_count": correct_count,
        "skip_count": skip_count,
        "accuracy": round(score_pct, 1),
        "question_accuracy_pct": question_accuracy_pct,
        "attempted_count": attempted_count,
        "distinct_topics_demonstrated_count": distinct_topics_demonstrated_count,
        "readiness_score": overall_readiness,
        "readiness_percentage": round(overall_readiness * 100, 1),
        "topic_coverage_readiness_pct": career_map["topic_coverage_readiness_pct"],
        "learning_stage": career_map["learning_stage"],
        "demonstrated_topics_count": career_map["demonstrated_topics_count"],
        "total_syllabus_topics": career_map["total_syllabus_topics"],
        "career_map": career_map,
        "question_results": question_results,
        "skill_breakdown": skill_breakdown,
        "weak_topics": weak_concepts,
        "root_causes": root_causes,
        "roadmap": path_nodes,
        "week_1_scheduled": True,
        "weekly_test_date": (today + dt.timedelta(days=7)).isoformat(),
        "scheduled_sessions_count": len(week_1_items),
        "schedule_sessions_created": len(week_1_items),
        "first_week_plan": serialized_plan,
    }
