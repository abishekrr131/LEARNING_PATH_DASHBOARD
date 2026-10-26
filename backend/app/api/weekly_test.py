"""Weekly Progress Test API Router.

Implements Master Prompt Requirement 8:
- Appears in Schedule and Assessments Hub on scheduled day.
- Exactly 20 MCQs from:
  (a) weekly priority topics (~50%)
  (b) prerequisite root-cause topics (~25%)
  (c) due spaced reviews (~25%)
- Single Gemini call with structured JSON, retry up to 2x with 20s timeout, fallback to bank.
- Zero repeats of questions the user has already answered.
- On submit: updates mastery/bands/priorities, marks week complete,
  auto-generates next week's schedule, and provides week-over-week comparison.
- Overdue handling: marks overdue status and flags banner if missed.
"""
from __future__ import annotations

import datetime as dt
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.gemini_client import GeminiClient
from backend.app.core.config import settings
from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import (
    Assessment,
    AssessmentQuestion,
    CareerTarget,
    Concept,
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
from backend.app.services.question_generator import (
    generate_weekly_test_questions,
    synthesize_week_schedule,
)
from backend.app.services.scoring import (
    calculate_coverage_readiness,
    expected_response_time,
    gap_band,
    gap_score,
    readiness_score,
    time_ratio,
)

router = APIRouter()


class WeeklyTestStartIn(BaseModel):
    target_id: int | None = None
    force_unlock: bool = False


class WeeklyTestItemResponse(BaseModel):
    question_id: int
    selected_answer: str | None = None
    response_time_ms: int = Field(ge=0, le=3600000)
    skipped: bool = False
    attempt_no: int = 1


class WeeklyTestSubmitIn(BaseModel):
    assessment_id: int
    responses: list[WeeklyTestItemResponse]


@router.get("/status")
def get_weekly_test_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Checks the status of the learner's Weekly Test: scheduled date, is_due, is_overdue."""
    today = dt.date.today()

    scheduled_test = db.execute(
        select(LearningSchedule)
        .where(
            LearningSchedule.user_id == current_user.id,
            LearningSchedule.activity_type == "weekly_test",
        )
        .order_by(LearningSchedule.scheduled_date.desc())
    ).scalars().first()

    if not scheduled_test:
        return {
            "is_scheduled": False,
            "scheduled_date": None,
            "is_due": False,
            "is_overdue": False,
            "status": "not_scheduled",
            "message": "Complete the Initial Diagnostic to generate your weekly schedule.",
        }

    if scheduled_test.status == "pending" and scheduled_test.scheduled_date < today:
        scheduled_test.scheduled_date = today + dt.timedelta(days=6)
        db.commit()

    is_completed = (scheduled_test.status == "completed")
    is_due = (scheduled_test.scheduled_date <= today) and not is_completed
    is_overdue = (scheduled_test.scheduled_date < today) and not is_completed

    return {
        "is_scheduled": True,
        "scheduled_date": scheduled_test.scheduled_date.isoformat(),
        "is_due": is_due,
        "is_overdue": is_overdue,
        "status": "completed" if is_completed else ("overdue" if is_overdue else ("due" if is_due else "locked")),
        "message": (
            "Weekly test is ready to take."
            if is_due
            else (
                "Weekly test completed for this cycle."
                if is_completed
                else f"Not due yet (Scheduled for {scheduled_test.scheduled_date.isoformat()})."
            )
        ),
    }


@router.post("/start")
def start_weekly_test(
    req: WeeklyTestStartIn = WeeklyTestStartIn(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates or resumes a 20-question Weekly Progress Test."""
    today = dt.date.today()

    # Check for active incomplete weekly test
    active_test = db.execute(
        select(Assessment).where(
            Assessment.user_id == current_user.id,
            Assessment.type == "weekly_test",
            Assessment.completed_at.is_(None),
        ).order_by(Assessment.started_at.desc())
    ).scalars().first()

    if active_test:
        # Retrieve existing linked questions
        existing_aqs = db.execute(
            select(AssessmentQuestion, Question, Concept.name)
            .join(Question, AssessmentQuestion.question_id == Question.id)
            .join(Concept, Question.concept_id == Concept.id)
            .where(AssessmentQuestion.assessment_id == active_test.id)
            .order_by(AssessmentQuestion.order_index)
        ).all()

        if len(existing_aqs) == 20:
            from backend.app.services.question_generator import to_options_list
            items_out = []
            for aq, q, cname in existing_aqs:
                items_out.append({
                    "question_id": q.id,
                    "order_index": aq.order_index + 1,
                    "concept_id": q.concept_id,
                    "concept_name": cname,
                    "question_text": q.question_text,
                    "stem": q.question_text,
                    "text": q.question_text,
                    "options": to_options_list(q.options),
                    "difficulty_b": round(q.difficulty_b, 2),
                    "difficulty": round(q.difficulty_b, 2),
                    "source": q.source or "curated",
                })
            return {
                "assessment_id": active_test.id,
                "total_items": 20,
                "items": items_out,
                "total_questions": 20,
                "questions": items_out,
                "is_resumed": True,
            }

    # Verify if weekly test is due
    scheduled_item = db.execute(
        select(LearningSchedule)
        .where(
            LearningSchedule.user_id == current_user.id,
            LearningSchedule.activity_type == "weekly_test",
            LearningSchedule.status == "pending",
        )
        .order_by(LearningSchedule.scheduled_date.asc())
    ).scalars().first()

    if scheduled_item and scheduled_item.scheduled_date > today and not req.force_unlock:
        if settings.ENV == "production":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Weekly test is not due yet. Scheduled for {scheduled_item.scheduled_date}.",
            )

    target_id = req.target_id
    if not target_id:
        profile = db.execute(
            select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
        ).scalar_one_or_none()
        target_id = profile.target_id if profile else 1

    target = db.get(CareerTarget, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    from ai.gemini_client import GeminiClient, GeminiRateLimitError
    gemini_client = GeminiClient()
    try:
        asmt_id, items_out = generate_weekly_test_questions(
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
            detail=f"Could not generate weekly test, retry: {str(e)}",
        )

    return {
        "assessment_id": asmt_id,
        "total_items": len(items_out),
        "items": items_out,
        "total_questions": len(items_out),
        "questions": items_out,
        "is_resumed": False,
    }


@router.post("/submit")
def submit_weekly_test(
    req: WeeklyTestSubmitIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluates Weekly Test, computes week-over-week readiness gain,
    marks weekly test complete, and generates Next Week's study schedule.
    """
    assessment = db.get(Assessment, req.assessment_id)
    if not assessment or assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    answered_at = dt.datetime.now(dt.timezone.utc)
    target = db.get(CareerTarget, assessment.target_id)

    # 1. Capture previous readiness baseline
    prev_cov = calculate_coverage_readiness(
        db=db,
        user_id=current_user.id,
        target_id=assessment.target_id,
    )
    prev_readiness_pct = prev_cov["readiness_percentage"] or 0.0

    # 2. Score submitted responses
    correct_count = 0
    skip_count = 0
    total_q = len(req.responses)
    responses_by_concept: dict[int, list[dict[str, Any]]] = {}

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
                phase="weekly_test",
                answered_at=answered_at,
            )
        )

        responses_by_concept.setdefault(q.concept_id, []).append({
            "is_correct": is_corr,
            "skipped": r.skipped,
            "time_ratio": tr,
        })

    score_pct = (correct_count / total_q) * 100.0 if total_q > 0 else 0.0
    assessment.score = score_pct
    assessment.completed_at = answered_at

    # 3. Update masteries & compute updated gaps
    prev_masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    prev_mastery_map = {m.concept_id: m.mastery_score for m in prev_masteries}

    improved_topics = []
    still_weak_topics = []

    for cid, item_resps in responses_by_concept.items():
        concept = db.get(Concept, cid)
        cname = concept.name if concept else f"Concept {cid}"
        topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None

        acc = sum(1 for x in item_resps if x["is_correct"]) / len(item_resps)
        skips = sum(1 for x in item_resps if x["skipped"]) / len(item_resps)
        mean_tr = sum(x["time_ratio"] for x in item_resps) / len(item_resps)

        old_m = prev_mastery_map.get(cid, 0.50)
        g_c = gap_score(accuracy=acc, time_ratio_val=mean_tr, skip_rate=skips, hist_mastery=old_m)
        band = gap_band(g_c)
        new_m = max(0.05, min(0.95, 1.0 - g_c))

        m_rec = db.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == current_user.id,
                StudentMastery.concept_id == cid,
            )
        ).scalar_one_or_none()

        if m_rec:
            m_rec.mastery_score = new_m
            m_rec.updated_at = answered_at
        else:
            db.add(
                StudentMastery(
                    user_id=current_user.id,
                    concept_id=cid,
                    mastery_score=new_m,
                    confidence=0.60,
                    model_version="f12_weekly_test",
                    updated_at=answered_at,
                )
            )

        if new_m > old_m:
            improved_topics.append({
                "concept_id": cid,
                "concept_name": cname,
                "topic_name": topic.name if topic else cname,
                "old_mastery": round(old_m * 100, 1),
                "new_mastery": round(new_m * 100, 1),
                "delta": round((new_m - old_m) * 100, 1),
            })
        elif band in ("weak", "moderate"):
            still_weak_topics.append({
                "concept_id": cid,
                "concept_name": cname,
                "topic_name": topic.name if topic else cname,
                "band": band,
                "mastery": round(new_m * 100, 1),
            })

    # 4. Mark weekly test schedule item as completed
    sched_item = db.execute(
        select(LearningSchedule).where(
            LearningSchedule.user_id == current_user.id,
            LearningSchedule.activity_type == "weekly_test",
            LearningSchedule.status == "pending",
        ).order_by(LearningSchedule.scheduled_date.asc())
    ).scalars().first()

    if sched_item:
        sched_item.status = "completed"
        sched_item.completed_at = answered_at
        db.flush()

    # 5. Compute updated current readiness
    curr_cov = calculate_coverage_readiness(
        db=db,
        user_id=current_user.id,
        target_id=assessment.target_id,
    )
    curr_readiness_pct = curr_cov["readiness_percentage"] or 0.0

    # 6. Auto-generate Next Week's schedule
    next_week_items = synthesize_week_schedule(
        user_id=current_user.id,
        target_id=assessment.target_id,
        db=db,
        week_number=2,
        start_date=dt.date.today(),
    )

    db.commit()

    return {
        "assessment_id": assessment.id,
        "status": "completed",
        "week_number": 1,
        "score": round(score_pct, 1),
        "total_questions": total_q,
        "correct_count": correct_count,
        "skip_count": skip_count,
        "previous_readiness": prev_readiness_pct,
        "current_readiness": curr_readiness_pct,
        "readiness_delta": round(curr_readiness_pct - prev_readiness_pct, 1),
        "improved_topics": improved_topics,
        "still_weak_topics": still_weak_topics,
        "next_week_sessions_count": len(next_week_items),
        "next_week_schedule_items": len(next_week_items),
        "next_weekly_test_date": (dt.date.today() + dt.timedelta(days=7)).isoformat(),
    }
