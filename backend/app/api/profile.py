"""Learner Profile, Compliance & Data Export API Router."""
from __future__ import annotations

import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import (
    AiInteraction,
    Assessment,
    AssessmentQuestion,
    CareerTarget,
    LearnerProfile,
    StudentMastery,
    StudentResponse,
    TopicPerformance,
    User,
)
from backend.app.schemas.profile import ProfileOut, ProfileUpdateIn, UserExportOut

router = APIRouter()


@router.get("", response_model=ProfileOut)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the current authenticated user's profile and learning configuration."""
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    target_name = None
    target_category = None
    if profile and profile.target_id:
        target = db.get(CareerTarget, profile.target_id)
        if target:
            target_name = target.name
            target_category = target.category

    return ProfileOut(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        target_id=profile.target_id if profile else None,
        target_name=target_name,
        target_category=target_category,
        current_level=profile.current_level if profile else None,
        target_exam_date=profile.exam_date if profile else None,
        daily_study_hours=profile.study_hours_per_day if profile else 2.0,
        trial_consent=profile.trial_consent if profile else False,
        intervention_arm=None,
        created_at=current_user.created_at,
    )


@router.patch("/profile", response_model=ProfileOut)
def update_my_profile(
    update_data: ProfileUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update target, target exam date, study hours, or trial consent."""
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    if not profile:
        first_target = db.execute(select(CareerTarget)).scalars().first()
        t_id = update_data.target_id or (first_target.id if first_target else 1)
        t_cat = first_target.category if first_target else "it_career"
        profile = LearnerProfile(
            user_id=current_user.id,
            target_id=t_id,
            target_type=t_cat,
        )
        db.add(profile)

    if update_data.target_id is not None:
        target = db.get(CareerTarget, update_data.target_id)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected career target does not exist",
            )
        profile.target_id = update_data.target_id
        profile.target_type = target.category

    if update_data.current_level is not None:
        profile.current_level = update_data.current_level
    if update_data.target_exam_date is not None:
        profile.exam_date = update_data.target_exam_date
    if update_data.daily_study_hours is not None:
        profile.study_hours_per_day = update_data.daily_study_hours
    if update_data.trial_consent is not None:
        profile.trial_consent = update_data.trial_consent

    profile.updated_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(profile)

    return get_my_profile(current_user=current_user, db=db)


@router.get("/export", response_model=UserExportOut)
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full GDPR / research telemetry export of learner data."""
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    assessments = db.execute(
        select(Assessment).where(Assessment.user_id == current_user.id)
    ).scalars().all()

    responses = db.execute(
        select(StudentResponse).where(StudentResponse.user_id == current_user.id)
    ).scalars().all()

    mastery = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()

    return UserExportOut(
        user={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat(),
        },
        profile={
            "target_id": profile.target_id,
            "current_level": profile.current_level,
            "target_exam_date": profile.exam_date.isoformat() if profile.exam_date else None,
            "daily_study_hours": profile.study_hours_per_day,
            "trial_consent": profile.trial_consent,
        } if profile else None,
        assessments=[
            {
                "id": a.id,
                "type": a.type,
                "score": a.score,
                "completed": a.completed_at is not None,
                "created_at": a.started_at.isoformat() if a.started_at else None,
            }
            for a in assessments
        ],
        responses=[
            {
                "id": r.id,
                "question_id": r.question_id,
                "concept_id": r.concept_id,
                "is_correct": r.is_correct,
                "response_time_ms": r.response_time_ms,
                "skipped": r.skipped,
                "timed_out": getattr(r, "timed_out", False),
                "phase": getattr(r, "phase", None),
                "answered_at": r.answered_at.isoformat() if r.answered_at else None,
            }
            for r in responses
        ],
        mastery_records=[
            {
                "concept_id": m.concept_id,
                "mastery_score": m.mastery_score,
                "confidence": m.confidence,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            }
            for m in mastery
        ],
        exported_at=dt.datetime.now(dt.timezone.utc),
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete account deletion with cascade of all learner responses and analytics."""
    # Delete child tables
    db.execute(delete(StudentResponse).where(StudentResponse.user_id == current_user.id))
    db.execute(delete(AssessmentQuestion).where(
        AssessmentQuestion.assessment_id.in_(
            select(Assessment.id).where(Assessment.user_id == current_user.id)
        )
    ))
    db.execute(delete(Assessment).where(Assessment.user_id == current_user.id))
    db.execute(delete(StudentMastery).where(StudentMastery.user_id == current_user.id))
    db.execute(delete(TopicPerformance).where(TopicPerformance.user_id == current_user.id))
    db.execute(delete(AiInteraction).where(AiInteraction.user_id == current_user.id))
    db.execute(delete(LearnerProfile).where(LearnerProfile.user_id == current_user.id))
    db.execute(delete(User).where(User.id == current_user.id))
    db.commit()
    return None
