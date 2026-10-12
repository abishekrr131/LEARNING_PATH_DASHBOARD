"""Randomized Controlled Trial (RCT) Engine (Spec §11).

Assigns learners to trial arms:
- Arm A ('root_cause'): Remediation path prioritizes diagnosed DAG root-cause ancestors first.
- Arm B ('surface'): Standard sequential curriculum navigation addressing only surface failure.

Measures post-test learning gain Delta y = y_post - y_pre and trial effect sizes.
"""
from __future__ import annotations

import random
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.models.core import User, LearnerProfile, Assessment


def assign_trial_arm(user_id: int, db: Session, seed: Optional[int] = None) -> str:
    """Randomly assigns consenting learner to trial arm with 50/50 allocation."""
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == user_id)
    ).scalar_one_or_none()

    if not profile or not profile.trial_consent:
        return "surface"  # Non-consenting users receive standard baseline sequential path

    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random(user_id)

    # 50/50 arm assignment
    arm = "root_cause" if rng.random() >= 0.50 else "surface"
    return arm


def calculate_learning_gain(
    user_id: int,
    db: Session,
) -> Dict[str, Any]:
    """Calculates individual pre/post score gain Delta y."""
    initial_test = db.execute(
        select(Assessment)
        .where(Assessment.user_id == user_id, Assessment.type == "initial", Assessment.completed_at.is_not(None))
        .order_by(Assessment.completed_at.desc())
    ).scalars().first()

    followup_test = db.execute(
        select(Assessment)
        .where(Assessment.user_id == user_id, Assessment.type == "followup", Assessment.completed_at.is_not(None))
        .order_by(Assessment.completed_at.desc())
    ).scalars().first()

    pre_score = initial_test.score if initial_test else None
    post_score = followup_test.score if followup_test else None

    gain = None
    if pre_score is not None and post_score is not None:
        gain = round(post_score - pre_score, 4)

    return {
        "user_id": user_id,
        "pre_score": pre_score,
        "post_score": post_score,
        "absolute_gain": gain,
        "has_completed_trial": gain is not None,
    }
