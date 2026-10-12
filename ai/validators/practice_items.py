"""Practice item schema validation and review status enforcement.

Generated items enter the bank as pending, and the database constraint
'scorable_items_must_be_reviewed' stops them reaching any scored assessment.
This validator rejects obviously broken items before any human sees the queue.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator


class DraftItem(BaseModel):
    concept_id: int
    question_text: str = Field(min_length=20)
    options: dict[str, str] = Field(min_length=3, max_length=5)
    correct_answer: str
    explanation: str = Field(min_length=20)

    @field_validator("correct_answer")
    @classmethod
    def answer_must_be_an_option(cls, v: str, info: Any) -> str:
        options = info.data.get("options", {})
        if v not in options:
            raise ValueError("correct_answer is not one of the options")
        return v

    @field_validator("options")
    @classmethod
    def options_must_be_distinct(cls, v: dict[str, str]) -> dict[str, str]:
        if len({o.strip().lower() for o in v.values()}) != len(v):
            raise ValueError("duplicate options")
        return v


def to_row(draft: DraftItem, difficulty_b: float = 0.0) -> dict[str, Any]:
    return draft.model_dump() | {
        "source": "ai_generated",
        "review_status": "pending",  # a human approves, or it is never served
        "needs_human_review": True,
        "difficulty_b": difficulty_b,
    }
