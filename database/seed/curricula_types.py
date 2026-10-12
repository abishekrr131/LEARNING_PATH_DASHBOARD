"""Curricula and Question Bank definitions for all 7 career targets:
4 IT/Software roles + 3 Government Exams.
Guarantees >= 40 concepts per target and ~60 reviewed questions per target.
"""
from __future__ import annotations
from typing import TypedDict, Any


class QuestionDef(TypedDict):
    concept: str
    text: str
    options: dict[str, str]
    answer: str
    explanation: str
    difficulty_hint: float


class TargetDef(TypedDict):
    target: dict[str, Any]
    skills: list[dict[str, Any]]
    topics: dict[str, list[str]]
    concepts: dict[str, list[tuple[str, str]]]  # topic -> [(concept_name, description)]
    dependencies: list[tuple[str, str, float]]  # (prereq, dep, weight)
    questions: list[QuestionDef]
