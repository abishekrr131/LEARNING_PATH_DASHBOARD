"""Pydantic schemas for learner profile and settings."""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal
from pydantic import BaseModel, Field


class ProfileOut(BaseModel):
    user_id: int
    email: str
    name: str
    target_id: int | None = None
    target_name: str | None = None
    target_category: str | None = None
    current_level: Literal["Beginner", "Intermediate", "Advanced"] | None = None
    target_exam_date: dt.date | None = None
    daily_study_hours: float = 2.0
    trial_consent: bool = False
    intervention_arm: Literal["root_cause", "surface", "control"] | None = None
    created_at: dt.datetime


class ProfileUpdateIn(BaseModel):
    target_id: int | None = None
    current_level: Literal["Beginner", "Intermediate", "Advanced"] | None = None
    target_exam_date: dt.date | None = None
    daily_study_hours: float | None = Field(default=None, ge=0.5, le=16.0)
    trial_consent: bool | None = None


class UserExportOut(BaseModel):
    user: dict[str, Any]
    profile: dict[str, Any] | None
    assessments: list[dict[str, Any]]
    responses: list[dict[str, Any]]
    mastery_records: list[dict[str, Any]]
    exported_at: dt.datetime
