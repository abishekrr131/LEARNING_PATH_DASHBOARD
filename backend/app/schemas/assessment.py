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
    """What the runner renders. The correct answer is never sent to the client in scored tests."""
    question_id: int
    concept_id: int
    concept_name: str
    order_index: int
    question_text: str
    options: list[dict[str, str]] = Field(default_factory=list)
    difficulty_b: float = 0.0
    phase: Literal["main", "sub", "weekly_test", "initial", "practice"] | None = None
    time_limit_sec: int | None = None
    block_index: int | None = None
    source: str = "curated"
    correct_option: str | None = None
    explanation: str | None = None
    topic_id: int | None = None
    topic_name: str | None = None
    skill_name: str | None = None

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, v: Any) -> list[dict[str, str]]:
        if isinstance(v, dict):
            return [{"key": str(k), "text": str(val)} for k, val in v.items()]
        if isinstance(v, list):
            res = []
            for idx, item in enumerate(v):
                if isinstance(item, dict):
                    if "key" in item and "text" in item:
                        res.append({"key": str(item["key"]), "text": str(item["text"])})
                    elif len(item) == 1:
                        k, val = next(iter(item.items()))
                        res.append({"key": str(k), "text": str(val)})
                    else:
                        res.append({
                            "key": str(item.get("key", chr(65 + idx))),
                            "text": str(item.get("text", str(item))),
                        })
                elif isinstance(item, str):
                    res.append({"key": chr(65 + idx), "text": item})
            return res
        return []


class AssessmentStartIn(BaseModel):
    type: AssessmentType = "initial"
    target_id: int
    main_count: int = 5  # For special test mode: 5 or 10
    concept_id: int | None = None
    topic_id: int | None = None
    practice_mode: Literal["untimed", "combined", "speed"] | None = None
    count: int | None = None


class AssessmentStartOut(BaseModel):
    assessment_id: int
    type: AssessmentType
    items: list[ItemOut]
    time_limit_sec: int | None = None
    total_blocks: int | None = None
    practice_mode: str | None = None


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
    readiness_percentage: float | None = None
    skill_breakdown: list[dict[str, Any]] | None = None
    weak_topics: list[dict[str, Any]] | None = None
    roadmap: list[dict[str, Any]] | None = None


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
    cognitive_gap: dict[str, Any] | None = None
    gap_type: str | None = None
    study_task: str | None = None


class RootCauseSubQuestionsIn(BaseModel):
    question_id: int


class RootCauseSubQuestionsOut(BaseModel):
    question_id: int
    topic_name: str
    concept_name: str
    main_question_stem: str
    sub_questions: list[dict[str, Any]]
    has_sub_questions: bool = True
    message: str | None = None


class RootCauseEvaluateIn(BaseModel):
    question_id: int
    formula_correct: bool
    substitution_correct: bool
    calculation_correct: bool
    calculation_time_ms: int = 0
    time_threshold_ms: int = 20000


class RootCauseEvaluateOut(BaseModel):
    question_id: int
    topic_name: str
    concept_name: str
    gap_type: str
    study_task: str
    action: str
    all_three_failed: bool
    stages: list[dict[str, Any]]
    upstream_prerequisites: list[dict[str, Any]] = []
