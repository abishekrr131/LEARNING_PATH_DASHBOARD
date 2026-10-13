"""Gemini AI API Router with Scored Test Suppression and Interaction Logging."""
from __future__ import annotations

import json
import logging
import re
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.gemini_client import GeminiClient, GeminiUnavailableError, GeminiRateLimitError
from ai.validators.practice_items import DraftItem, to_row
from backend.app.core.config import settings
from backend.app.core.security import get_current_user
from backend.app.db.session import SessionLocal, get_db
from backend.app.models.core import (
    Assessment,
    CareerTarget,
    Concept,
    LearnerProfile,
    Question,
    Skill,
    Topic,
    User,
)

logger = logging.getLogger("palp.api.ai")
router = APIRouter()

gemini_client = GeminiClient(
    api_key=settings.GEMINI_API_KEY,
    model_name=settings.GEMINI_MODEL,
    session_factory=SessionLocal,
)

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


def resolve_syllabus_context(
    db: Session,
    user_id: int,
    concept_id: int | None,
    user_message: str,
) -> tuple[str, str, list[int]]:
    """Resolves curriculum topic and syllabus metadata grounded STRICTLY in user's active career target.
    Never injects concepts or topics from other tracks (e.g. ML) into a Banking user's prompt.
    Returns: (topic_name, syllabus_metadata, injected_topic_ids)
    """
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == user_id)
    ).scalar_one_or_none()
    target_id = profile.target_id if profile else 1
    target = db.get(CareerTarget, target_id)
    target_title = target.name if target else "General Syllabus"

    # 1. If explicit concept_id is provided, verify it strictly belongs to user's target!
    if concept_id:
        c = db.get(Concept, concept_id)
        if c and c.topic and c.topic.skill and c.topic.skill.target_id == target_id:
            topic = c.topic
            skill = topic.skill
            topic_name = topic.name
            meta = (
                f"Career Target: {target_title}. Skill Domain: {skill.name}. "
                f"Topic: {topic_name}. Concept: {c.name}. Syllabus context: {c.description or 'Core syllabus concept'}."
            )
            return topic_name, meta, [topic.id]

    query_lower = user_message.lower()
    query_tokens = set(re.findall(r"\w+", query_lower))
    common_stopwords = {
        "explain", "what", "is", "are", "the", "a", "an", "and", "or", "in", "for", "to",
        "of", "about", "how", "tell", "me", "details", "give", "some", "can", "you", "help"
    }
    meaningful_tokens = query_tokens - common_stopwords

    # 2. Match concepts strictly in target curriculum
    concepts_rows = db.execute(
        select(Concept, Topic, Skill)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
    ).all()

    best_concept = None
    best_concept_score = 0
    for c, topic, skill in concepts_rows:
        c_lower = c.name.lower()
        t_lower = topic.name.lower()
        score = 0
        if c_lower in query_lower or query_lower in c_lower:
            score += 10
        if t_lower in query_lower or query_lower in t_lower:
            score += 8
        c_tokens = set(re.findall(r"\w+", c_lower)) - common_stopwords
        t_tokens = set(re.findall(r"\w+", t_lower)) - common_stopwords
        concept_words = c_tokens | t_tokens
        overlap = 0
        for qw in meaningful_tokens:
            for cw in concept_words:
                if qw == cw or (len(qw) >= 4 and len(cw) >= 4 and (qw.startswith(cw) or cw.startswith(qw))):
                    overlap += 1
        score += overlap * 3
        if score > best_concept_score:
            best_concept_score = score
            best_concept = (c, topic, skill)

    if best_concept and best_concept_score >= 3:
        c, topic, skill = best_concept
        meta = (
            f"Career Target: {target_title}. Domain: {skill.name}. "
            f"Topic: {topic.name}. Concept: {c.name}. Syllabus context: {c.description or 'Core syllabus concept in ' + target_title}."
        )
        return topic.name, meta, [topic.id]

    # 3. Match skill domain strictly in target curriculum (e.g. 'Quantitative Aptitude' for 'aptitude')
    skills_rows = db.execute(
        select(Skill).where(Skill.target_id == target_id)
    ).scalars().all()

    best_skill = None
    best_skill_score = 0
    for s in skills_rows:
        s_lower = s.name.lower()
        s_tokens = set(re.findall(r"\w+", s_lower)) - common_stopwords
        overlap = len(s_tokens & meaningful_tokens)
        score = 0
        if any(word in s_lower for word in meaningful_tokens if len(word) >= 4):
            score += 6
        score += overlap * 3
        if score > best_skill_score:
            best_skill_score = score
            best_skill = s

    if best_skill and best_skill_score >= 3:
        # Find primary foundational topics under this skill
        topics_in_skill = db.execute(
            select(Topic).where(Topic.skill_id == best_skill.id).order_by(Topic.id)
        ).scalars().all()
        topic_name = topics_in_skill[0].name if topics_in_skill else best_skill.name
        topic_ids = [t.id for t in topics_in_skill]
        meta = (
            f"Career Target: {target_title}. Skill Domain: {best_skill.name} (Exam weight: {best_skill.weight}). "
            f"Relevant Topics: {', '.join(t.name for t in topics_in_skill[:3])}. "
            f"Syllabus Context: Foundational syllabus area for {target_title}."
        )
        return topic_name, meta, topic_ids

    # 4. No confident match within target syllabus
    # General response stating syllabus scope, NEVER injecting concepts from other tracks
    skills_summary = ", ".join(f"{s.name}" for s in skills_rows)
    meta = (
        f"Career Target: {target_title}. Syllabus Structure: {skills_summary}. "
        f"Note: The user's query is broad and does not match a single narrow concept in {target_title}. "
        f"Answer generally from the perspective of the {target_title} curriculum without forcing any unrelated track topic."
    )
    return f"{target_title} General Syllabus", meta, []


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

    topic_name, syllabus_metadata, injected_topic_ids = resolve_syllabus_context(
        db, current_user.id, req.concept_id, req.message
    )

    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    target_id = profile.target_id if profile else 1
    target = db.get(CareerTarget, target_id)
    target_name = target.name if target else "General"

    logger.info(
        "AI Chatbot: user_id=%s, target='%s', injected_topic_ids=%s, topic_name='%s', query='%s'",
        current_user.id,
        target_name,
        injected_topic_ids,
        topic_name,
        req.message,
    )

    ctx = {
        "topic_name": topic_name,
        "syllabus_metadata": syllabus_metadata,
        "user_message": req.message,
    }

    if not settings.GEMINI_CHATBOT_ENABLED:
        return {
            "reply": "AI Chatbot is currently disabled in system configuration.",
            "label": "Notice",
            "topic_name": topic_name,
            "injected_topic_ids": injected_topic_ids,
            "context_chip": f"{topic_name} ({req.page_context or 'Dashboard'})",
        }

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        return {
            "reply": f"AI Assistant is unconfigured (GEMINI_API_KEY is not set). Topic context: {topic_name}. Please configure GEMINI_API_KEY in .env to enable live AI responses.",
            "label": "Notice",
            "topic_name": topic_name,
            "injected_topic_ids": injected_topic_ids,
            "context_chip": f"{topic_name} ({req.page_context or 'Dashboard'})",
        }

    try:
        reply = gemini_client.call("tutor_chat", ctx, user_id=current_user.id)
    except GeminiRateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI is busy, retry in about 1 minute",
        )
    except GeminiUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant unavailable, retry",
        )

    return {
        "reply": reply,
        "label": "AI-generated",
        "topic_name": topic_name,
        "injected_topic_ids": injected_topic_ids,
        "context_chip": f"{topic_name} ({req.page_context or 'Dashboard'})",
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
    try:
        explanation = gemini_client.call("concept_explanation", ctx, user_id=current_user.id)
    except GeminiUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant unavailable, retry",
        )

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
    try:
        feedback = gemini_client.call("performance_feedback", ctx, user_id=current_user.id)
    except GeminiUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant unavailable, retry",
        )

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
    try:
        raw_json = gemini_client.call("practice_generation", ctx, user_id=current_user.id)
    except GeminiUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant unavailable, retry",
        )

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
    except Exception as e:
        logger.exception("Failed to parse Gemini practice JSON response: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Generated practice item format invalid, retry",
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
