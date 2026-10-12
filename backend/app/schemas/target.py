"""Pydantic schemas for career targets and curriculum hierarchies."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class ConceptOut(BaseModel):
    id: int
    name: str
    description: str | None
    difficulty_level: str
    topic_id: int
    topic_name: str | None = None
    skill_id: int | None = None
    skill_name: str | None = None


class TopicOut(BaseModel):
    id: int
    name: str
    order_index: int
    skill_id: int
    concepts: list[ConceptOut] = []


class SkillOut(BaseModel):
    id: int
    name: str
    weight: float
    topics: list[TopicOut] = []


class TargetSummaryOut(BaseModel):
    id: int
    name: str
    category: str
    description: str | None
    skill_count: int
    concept_count: int
    question_count: int


class TargetDetailOut(BaseModel):
    id: int
    name: str
    category: str
    description: str | None
    readiness_threshold: float
    skills: list[SkillOut] = []


class GraphNodeOut(BaseModel):
    id: int
    name: str
    skill_name: str
    difficulty_level: str
    status: str = "available"  # completed, in_progress, available, locked


class GraphEdgeOut(BaseModel):
    source: int  # prerequisite concept id
    target: int  # dependent concept id
    weight: float = 1.0


class TargetGraphOut(BaseModel):
    target_id: int
    target_name: str
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    is_dag: bool
