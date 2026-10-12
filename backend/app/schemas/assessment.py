"""Pydantic schemas for assessments and responses.

Follows Section 25 of the Specification with additions for Special Test Mode.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

AssessmentType = Literal["initial", "verification", "practice", "followup", "special", "probe"]
SCORED_TYPES = {"initial", "verification", "followup", "special"}


class ItemOut(BaseModel):
    """What the runner renders. The correct answer is never sent to the client."""
    question_id: int
    concept_id: int
    concept_name: str
    order_index: int
    question_text: str
    options: dict[str, str]
    difficulty_b: float = 0.0
    phase: Literal["main", "sub"] | None = None
    time_limit_sec: int | None = None
    block_index: int | None = None


class AssessmentStartIn(BaseModel):
    type: AssessmentType = "initial"
    target_id: int
    main_count: int = 5  # For special test mode: 5 or 10


class AssessmentStartOut(BaseModel):
    assessment_id: int
    type: AssessmentType
    items: list[ItemOut]
    time_limit_sec: int | None = None
    total_blocks: int | None = None


class ResponseIn(BaseModel):
    question_id: int
    selected_answer: str | None = None
    skipped: bool = False
    timed_out: bool = False
    response_time_ms: int = Field(ge=0, le=3_600_000)
    attempt_no: int = Field(default=1, ge=1, le=20)
    phase: Literal["main", "sub"] | None = None
    parent_response_id: int | None = None

    # NOTE: No client timestamp. The server assigns answered_at.
    @field_validator("selected_answer")
    @classmethod
    def skip_or_timeout_has_no_answer(cls, v: str | None, info: Any) -> str | None:
        data = info.data
        if (data.get("skipped") or data.get("timed_out")) and v is not None:
            raise ValueError("a skipped or timed_out item cannot carry an answer")
        return v


class AssessmentSubmitIn(BaseModel):
    responses: list[ResponseIn] = Field(min_length=1)


class ConceptScore(BaseModel):
    concept_id: int
    concept_name: str
    accuracy: float
    mean_time_ratio: float
    skip_rate: float
    gap_score: float
    band: Literal["strong", "moderate", "weak"]


class AssessmentSubmitOut(BaseModel):
    assessment_id: int
    score: float
    total_questions: int
    correct_count: int
    skip_count: int
    timed_out_count: int
    mean_time_ratio: float
    per_concept: list[ConceptScore]
    signal_mode: Literal["irt_only", "gap_score", "full_model"]
    probe_queued: list[int] = []
    path_changed: bool = False
    cold_start: bool = True  # True if <20 historical interactions


# Special Test Mode schemas
class SpecialNextBlockIn(BaseModel):
    assessment_id: int
    main_response: ResponseIn
    block_index: int


class SpecialNextBlockOut(BaseModel):
    assessment_id: int
    block_index: int
    main_response_id: int
    sub_questions: list[ItemOut]
    trigger: Literal["prerequisite_bias", "difficulty_boost", "epsilon_random"]


class SpecialBlockEndIn(BaseModel):
    assessment_id: int
    block_index: int
    main_response_id: int
    sub_responses: list[ResponseIn]


class SpecialBlockEndOut(BaseModel):
    block_index: int
    main_correct: bool
    main_timed_out: bool
    sub_results: list[dict[str, Any]]
    suspected_weak_prerequisite: str | None = None
