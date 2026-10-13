"""Study Schedule and Decay-Based Review Dates API Router."""
from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import Concept, LearnerProfile, LearningSchedule, StudentMastery, User
from backend.app.services.scoring import review_interval

router = APIRouter()


class ScheduleUpdateIn(BaseModel):
    completed: bool | None = None
    reschedule_days: int | None = None


@router.get("")
def get_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the learner's study schedule with review intervals derived from F16 (Screen 16).
    For users with no attempts, returns 200 with an empty list and zero counts.
    """
    items = db.execute(
        select(LearningSchedule)
        .where(LearningSchedule.user_id == current_user.id)
        .order_by(LearningSchedule.scheduled_date)
    ).scalars().all()

    today = dt.date.today()
    out = []

    # If user has no scheduled items yet, return clean empty list with zero counts
    if not items:
        return {
            "schedule": [],
            "total_count": 0,
            "completed_count": 0,
            "pending_count": 0,
            "overdue_count": 0,
            "message": "No scheduled reviews yet. Complete assessments to calibrate spaced review dates.",
        }

    completed_count = 0
    overdue_count = 0
    pending_count = 0

    for item in items:
        concept = db.get(Concept, item.concept_id)
        cname = concept.name if concept else f"Concept {item.concept_id}"

        is_completed = (item.status == "completed")
        is_overdue = not is_completed and item.scheduled_date < today

        if is_completed:
            completed_count += 1
        elif is_overdue:
            overdue_count += 1
            pending_count += 1
        else:
            pending_count += 1

        is_test = (item.activity_type == "weekly_test")
        displayName = "Weekly Progress Test (20 Qs)" if is_test else cname

        topic_obj = concept.topic if concept else None
        skill_obj = topic_obj.skill if topic_obj else None

        subj = item.subject or (skill_obj.name if skill_obj else "General Curriculum")
        top_name = item.topic_name or (topic_obj.name if topic_obj else cname)
        obj = item.learning_objective or (
            "Comprehensive 20-item milestone assessment evaluating weekly retention."
            if is_test
            else f"Master conceptual principles and problem-solving techniques for {cname}."
        )
        res_title = item.resource_title or ("LearnPath Assessment Engine" if is_test else f"Official Curriculum Guide: {cname}")
        res_url = item.resource_url or ("https://learnpath.internal/assessments/weekly" if is_test else "https://sathee.prutor.ai/")
        act = item.practice_activity or ("Weekly Progress Test (20 Questions - Timed)" if is_test else f"Targeted 5-question practice set on {top_name}")
        target_m = item.mastery_target or 0.80
        follow_up = item.follow_up_assessment or ("Calibrate Week 2 Adaptive Learning Plan" if is_test else "Weekly Progress Test (Day 7)")
        reason = item.plan_reason or ("Milestone assessment" if is_test else f"Curriculum learning block for {top_name}")

        out.append({
            "id": item.id,
            "concept_id": item.concept_id,
            "concept_name": displayName,
            "subject": subj,
            "topic": top_name,
            "topic_name": top_name,
            "learning_objective": obj,
            "resource_title": res_title,
            "resource_url": res_url,
            "practice_activity": act,
            "mastery_target": target_m,
            "follow_up_assessment": follow_up,
            "plan_reason": reason,
            "activity_type": item.activity_type,
            "scheduled_date": item.scheduled_date.isoformat(),
            "planned_minutes": item.duration_min,
            "duration_min": item.duration_min,
            "completed": is_completed,
            "status": item.status,
            "is_overdue": is_overdue,
            "is_weekly_test": is_test,
        })

    return {
        "schedule": out,
        "total_count": len(out),
        "completed_count": completed_count,
        "pending_count": pending_count,
        "overdue_count": overdue_count,
    }


@router.patch("/{schedule_id}")
def update_schedule_item(
    schedule_id: int,
    req: ScheduleUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark item completed or reschedule downstream items."""
    item = db.get(LearningSchedule, schedule_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule item not found")

    if req.completed is not None:
        item.status = "completed" if req.completed else "pending"
        item.completed_at = dt.datetime.now(dt.timezone.utc) if req.completed else None

    if req.reschedule_days is not None:
        item.scheduled_date = dt.date.today() + dt.timedelta(days=req.reschedule_days)

    db.commit()
    db.refresh(item)

    concept = db.get(Concept, item.concept_id)
    return {
        "id": item.id,
        "concept_id": item.concept_id,
        "concept_name": concept.name if concept else f"Concept {item.concept_id}",
        "scheduled_date": item.scheduled_date.isoformat(),
        "planned_minutes": item.duration_min,
        "completed": (item.status == "completed"),
        "status": item.status,
    }
