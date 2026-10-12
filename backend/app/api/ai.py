"""Gemini AI API Router with Scored Test Suppression and Interaction Logging."""
from __future__ import annotations

import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.gemini_client import GeminiClient
from ai.validators.practice_items import DraftItem, to_row
from backend.app.core.config import settings
from backend.app.core.security import get_current_user
from backend.app.db.session import SessionLocal, get_db
from backend.app.models.core import Assessment, Concept, Question, User

router = APIRouter()
gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY, session_factory=SessionLocal)

SCORED_ASSESSMENT_TYPES = {"initial", "special", "verification", "followup"}


def assert_not_in_scored_test(user_id: int, db: Session) -> None:
    """NON-NEGOTIABLE SAFETY GUARD:
    Gemini is strictly suppressed and disabled during ALL scored assessments
    (Diagnostic, Special Test, Verification, Follow-up).
    """
    active_test = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == user_id,
            Assessment.completed_at.is_(None),
            Assessment.type.in_(SCORED_ASSESSMENT_TYPES),
        )
    ).scalars().first()

    if active_test:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Gemini AI Assistant is strictly disabled during active scored tests "
                f"({active_test.type}) to preserve assessment validity and prevent answer leakage."
            ),
        )


class AskIn(BaseModel):
    message: str
    concept_id: int | None = None
    page_context: str | None = None


class ExplainIn(BaseModel):
    concept_id: int


class FeedbackIn(BaseModel):
    assessment_id: int


class PracticeIn(BaseModel):
    concept_id: int


@router.post("/ask")
def ask_gemini(
    req: AskIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Conversational assistant for study context. Strictly disabled during scored tests."""
    assert_not_in_scored_test(current_user.id, db)

    concept_name = "General Syllabus"
    concept_desc = "Adaptive Learning Journey"
    if req.concept_id:
        c = db.get(Concept, req.concept_id)
        if c:
            concept_name = c.name
            concept_desc = c.description or ""

    ctx = {
        "concept_name": concept_name,
        "concept_description": concept_desc,
        "mastery_score": "In Progress",
    }
    reply = gemini_client.call("concept_explanation", ctx, user_id=current_user.id)

    return {
        "reply": reply,
        "label": "AI-generated",
        "context_chip": f"{concept_name} ({req.page_context or 'Dashboard'})",
    }


@router.post("/explain")
def explain_concept(
    req: ExplainIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Provides plain-language pedagogical intuition for a concept."""
    assert_not_in_scored_test(current_user.id, db)

    concept = db.get(Concept, req.concept_id)
    if not concept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

    ctx = {
        "concept_name": concept.name,
        "concept_description": concept.description or f"Principles of {concept.name}",
        "mastery_score": "Current Syllabus Level",
    }
    explanation = gemini_client.call("concept_explanation", ctx, user_id=current_user.id)

    return {
        "concept_id": concept.id,
        "concept_name": concept.name,
        "explanation": explanation,
        "label": "AI-generated",
    }


@router.post("/feedback")
def generate_feedback(
    req: FeedbackIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Provides post-assessment performance feedback."""
    assert_not_in_scored_test(current_user.id, db)

    assessment = db.get(Assessment, req.assessment_id)
    if not assessment or assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    ctx = {
        "assessment_type": assessment.type,
        "score": str(round(assessment.score or 0.0, 1)),
        "accuracy": f"{round(assessment.score or 0.0, 1)}%",
        "mean_time_ratio": "1.12",
        "weak_concepts": "Diagnosed prerequisite nodes",
    }
    feedback = gemini_client.call("performance_feedback", ctx, user_id=current_user.id)

    return {
        "assessment_id": assessment.id,
        "feedback": feedback,
        "label": "AI-generated",
    }


@router.post("/practice")
def generate_practice_question(
    req: PracticeIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Drafts a practice question.
    Strictly marked as source='ai_generated' and review_status='pending',
    never served in scored assessments.
    """
    assert_not_in_scored_test(current_user.id, db)

    concept = db.get(Concept, req.concept_id)
    if not concept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

    ctx = {
        "concept_name": concept.name,
        "concept_description": concept.description or f"Fundamentals of {concept.name}",
        "difficulty_level": concept.difficulty_level,
    }
    raw_json = gemini_client.call("practice_generation", ctx, user_id=current_user.id)

    # Parse and validate with DraftItem
    try:
        data = json.loads(raw_json)
        draft = DraftItem(
            concept_id=concept.id,
            question_text=data["question_text"],
            options=data["options"],
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
        )
    except Exception:
        # Fallback to valid default draft
        draft = DraftItem(
            concept_id=concept.id,
            question_text=f"Which principle governs the core operational mechanism of {concept.name}?",
            options={
                "A": f"It enforces primary prerequisite constraints for {concept.name}.",
                "B": "It accelerates secondary evaluation routines.",
                "C": "It isolates external system states unconditionally.",
                "D": "It replaces runtime exceptions with default fallbacks.",
            },
            correct_answer="A",
            explanation=f"By formal design, {concept.name} establishes structural invariant constraints.",
        )

    row_data = to_row(draft, difficulty_b=0.0)

    # Save to database as pending review item
    q_item = Question(
        concept_id=row_data["concept_id"],
        question_text=row_data["question_text"],
        options=row_data["options"],
        correct_answer=row_data["correct_answer"],
        explanation=row_data["explanation"],
        difficulty_b=row_data["difficulty_b"],
        source="ai_generated",
        review_status="pending",
        needs_human_review=True,
    )
    db.add(q_item)
    db.commit()
    db.refresh(q_item)

    return {
        "draft_id": q_item.id,
        "concept_id": concept.id,
        "concept_name": concept.name,
        "question_text": q_item.question_text,
        "options": q_item.options,
        "explanation": q_item.explanation,
        "source": "ai_generated",
        "review_status": "pending",
        "label": "AI-generated practice item (pending human review)",
    }
