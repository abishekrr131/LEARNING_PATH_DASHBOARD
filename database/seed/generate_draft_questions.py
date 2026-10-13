"""Pre-generate draft questions with Gemini for human review.

Strictly marked with source='ai_generated', review_status='pending', and needs_human_review=True.
Never served in scored assessments until approved by a reviewer via review_queue.py.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ai.gemini_client import GeminiClient, GeminiUnavailableError
from ai.validators.practice_items import DraftItem, to_row
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models.core import CareerTarget, Concept, Question, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("palp.seed.generate_drafts")


def generate_drafts_for_target(target_id: int, count_per_concept: int = 1) -> int:
    db = SessionLocal()
    gemini = GeminiClient(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL)

    if not gemini.is_configured:
        logger.warning(
            "Gemini API key is not configured or offline. Generating deterministic offline draft templates for review."
        )

    system_user = db.query(User).filter(User.role == "admin").first()
    user_id = system_user.id if system_user else 1

    target = db.get(CareerTarget, target_id)
    if not target:
        logger.error("CareerTarget with ID %s not found.", target_id)
        db.close()
        return 0

    concepts = (
        db.query(Concept)
        .join(Concept.topic)
        .join(Concept.topic.property.mapper.class_.skill)
        .filter(Concept.topic.property.mapper.class_.skill.property.mapper.class_.target_id == target_id)
        .all()
    )

    if not concepts:
        # Fallback to direct query
        from backend.app.models.core import Skill, Topic
        concepts = (
            db.query(Concept)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .filter(Skill.target_id == target_id)
            .all()
        )

    logger.info("Found %d concepts for target '%s'", len(concepts), target.name)
    generated_count = 0

    try:
        for c in concepts[:15]:  # Generate sample drafts
            for rep in range(count_per_concept):
                ctx = {
                    "concept_name": c.name,
                    "concept_description": c.description or f"Principles and problems on {c.name}",
                    "difficulty_level": c.difficulty_level,
                }

                if gemini.is_configured:
                    try:
                        raw_json = gemini.call("practice_generation", ctx, user_id=user_id)
                        data = json.loads(raw_json)
                        draft = DraftItem(
                            concept_id=c.id,
                            question_text=data["question_text"],
                            options=data["options"],
                            correct_answer=data["correct_answer"],
                            explanation=data["explanation"],
                        )
                    except Exception as e:
                        logger.warning("Gemini generation failed for '%s': %s", c.name, e)
                        draft = DraftItem(
                            concept_id=c.id,
                            question_text=f"Draft practice item testing core properties of {c.name} in competitive exam scenarios.",
                            options={
                                "A": f"Primary analytical property governing {c.name}.",
                                "B": "Secondary derivation constraint.",
                                "C": "Auxiliary transformation edge case.",
                                "D": "Independent baseline parameter.",
                            },
                            correct_answer="A",
                            explanation=f"Concept verification explanation for {c.name}.",
                        )
                else:
                    draft = DraftItem(
                        concept_id=c.id,
                        question_text=f"Draft practice item testing core properties of {c.name} in competitive exam scenarios.",
                        options={
                            "A": f"Primary analytical property governing {c.name}.",
                            "B": "Secondary derivation constraint.",
                            "C": "Auxiliary transformation edge case.",
                            "D": "Independent baseline parameter.",
                        },
                        correct_answer="A",
                        explanation=f"Concept verification explanation for {c.name}.",
                    )

                row = to_row(draft, difficulty_b=c.difficulty_level * 0.5)
                q = Question(
                    concept_id=row["concept_id"],
                    question_text=row["question_text"],
                    options=row["options"],
                    correct_answer=row["correct_answer"],
                    explanation=row["explanation"],
                    difficulty_b=row["difficulty_b"],
                    source="ai_generated",
                    review_status="pending",
                    needs_human_review=True,
                )
                db.add(q)
                generated_count += 1

        db.commit()
        logger.info("Successfully queued %d draft items for human review.", generated_count)
        return generated_count
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Pre-generate draft questions with Gemini for human review.")
    parser.add_argument("--target-id", type=int, default=7, help="Career target ID (default: 7 for Banking IBPS PO)")
    parser.add_argument("--count", type=int, default=1, help="Questions per concept")
    args = parser.parse_args()

    generate_drafts_for_target(args.target_id, args.count)


if __name__ == "__main__":
    main()
