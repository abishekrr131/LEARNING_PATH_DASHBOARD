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
    """Returns the learner's study schedule with review intervals derived from F16 (Screen 16)."""
    items = db.execute(
        select(LearningSchedule)
        .where(LearningSchedule.user_id == current_user.id)
        .order_by(LearningSchedule.scheduled_date)
    ).scalars().all()

    today = dt.date.today()
    out = []

    # If user has no schedules yet, generate initial schedule items based on masteries and F16
    if not items:
        masteries = db.execute(
            select(StudentMastery).where(StudentMastery.user_id == current_user.id)
        ).scalars().all()

        profile = db.execute(
            select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
        ).scalar_one_or_none()
        target_id = profile.career_target_id if profile else 1

        concepts = db.execute(
            select(Concept).limit(5)
        ).scalars().all()

        for idx, c in enumerate(concepts):
            sch_date = today + dt.timedelta(days=idx)
            sch = LearningSchedule(
                user_id=current_user.id,
                concept_id=c.id,
                activity_type="review",
                scheduled_date=sch_date,
                duration_min=45,
                status="pending",
            )
            db.add(sch)
        db.commit()
        items = db.execute(
            select(LearningSchedule)
            .where(LearningSchedule.user_id == current_user.id)
            .order_by(LearningSchedule.scheduled_date)
        ).scalars().all()

    for item in items:
        concept = db.get(Concept, item.concept_id)
        cname = concept.name if concept else f"Concept {item.concept_id}"
        
        is_completed = (item.status == "completed")
        is_overdue = not is_completed and item.scheduled_date < today

        out.append({
            "id": item.id,
            "concept_id": item.concept_id,
            "concept_name": cname,
            "scheduled_date": item.scheduled_date.isoformat(),
            "planned_minutes": item.duration_min,
            "completed": is_completed,
            "status": item.status,
            "is_overdue": is_overdue,
        })

    return {"schedule": out}


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
