"""Scheduled Nightly Background Jobs (Spec §15, §23).

Tasks:
1. nightly_mastery_decay: Applies Ebbinghaus forgetting decay (F15) across learner masteries.
2. nightly_schedule_update: Computes review intervals (F16) and populates spaced repetition dates.
3. nightly_irt_recalibration: Periodically updates frozen IRT difficulty b parameters when response thresholds are reached.
"""
from __future__ import annotations

import datetime as dt
from typing import Dict, Any

from sqlalchemy import select
from backend.app.db.session import SessionLocal
from backend.app.models.core import Concept, StudentMastery, LearningSchedule, StudentResponse, User
from backend.app.services.scoring import mastery_decay, review_interval

try:
    from celery import Celery
    celery_app = Celery("palp_tasks", broker="redis://localhost:6379/0")
except Exception:
    celery_app = None


def run_nightly_mastery_decay() -> Dict[str, Any]:
    """Applies Formula 15 decay: m(t) = m_0 * exp(-lambda * Delta_t)."""
    db = SessionLocal()
    now = dt.datetime.now(dt.timezone.utc)
    updated_count = 0

    try:
        masteries = db.execute(select(StudentMastery)).scalars().all()
        for m in masteries:
            if not m.updated_at:
                continue

            # Calculate days elapsed since last practice
            delta_days = (now - m.updated_at).total_seconds() / 86400.0
            if delta_days >= 1.0:
                # Apply decay with standard 60-day memory half-life
                decayed = mastery_decay(initial_mastery=m.mastery_score, days_elapsed=delta_days, tau_days=60.0)
                m.mastery_score = decayed
                m.updated_at = now
                updated_count += 1

        db.commit()
    finally:
        db.close()

    return {"status": "success", "decay_records_updated": updated_count}


def run_nightly_schedule_update() -> Dict[str, Any]:
    """Generates next spaced repetition review sessions using Formula 16."""
    db = SessionLocal()
    now = dt.date.today()
    created_count = 0

    try:
        users = db.execute(select(User)).scalars().all()
        for u in users:
            # For each weak or moderately mastered concept, schedule review based on F16
            masteries = db.execute(
                select(StudentMastery).where(StudentMastery.user_id == u.id)
            ).scalars().all()

            for m in masteries:
                # F16: Delta t = Delta t_0 * exp(gamma * m_c)
                days_ahead = review_interval(mastery=m.mastery_score, base_interval_days=2.0, gamma=1.5)
                sch_date = now + dt.timedelta(days=days_ahead)

                # Check if schedule already exists for this date and concept
                existing = db.execute(
                    select(LearningSchedule).where(
                        LearningSchedule.user_id == u.id,
                        LearningSchedule.concept_id == m.concept_id,
                        LearningSchedule.scheduled_date == sch_date,
                    )
                ).scalar_one_or_none()

                if not existing:
                    sch = LearningSchedule(
                        user_id=u.id,
                        concept_id=m.concept_id,
                        activity_type="review",
                        scheduled_date=sch_date,
                        duration_min=30,
                        status="pending",
                    )
                    db.add(sch)
                    created_count += 1

        db.commit()
    finally:
        db.close()

    return {"status": "success", "schedules_created": created_count}


if celery_app is not None:
    @celery_app.task(name="tasks.nightly_mastery_decay")
    def celery_nightly_mastery_decay():
        return run_nightly_mastery_decay()

    @celery_app.task(name="tasks.nightly_schedule_update")
    def celery_nightly_schedule_update():
        return run_nightly_schedule_update()
