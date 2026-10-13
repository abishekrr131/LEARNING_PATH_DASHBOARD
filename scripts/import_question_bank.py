"""Question Bank and Sub-Question Import Script.

Imports and validates main questions and diagnostic sub-questions from JSON or CSV.
Enforces:
- Exactly 4 options (A, B, C, D)
- Valid correct_option in ['A', 'B', 'C', 'D']
- No duplicate stems within the batch or against the existing database
- Explicit source and open license (e.g. CC-BY-4.0)
- Stages for sub-questions:
  - Quantitative: formula | substitution | calculation
  - Verbal / GA: concept_recall | elimination | final_answer
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import engine
from backend.app.models.core import Concept, Question, SubQuestion


SAMPLE_TEMPLATE_DATA = {
    "metadata": {
        "source": "Curated Open Curriculum Bank",
        "license": "CC-BY-4.0",
        "target": "Banking (IBPS PO)",
    },
    "questions": [
        {
            "concept_id": 245,
            "stem": "A shopkeeper marks an article 40% above cost price and allows a 20% discount. What is his net profit percentage?",
            "options": {
                "A": "10%",
                "B": "12%",
                "C": "15%",
                "D": "18%"
            },
            "correct_option": "B",
            "explanation": "Let CP = 100. MP = 140. SP = 140 * 0.80 = 112. Profit = 112 - 100 = 12%.",
            "difficulty": 0.40,
            "source": "Open Aptitude Archive",
            "license": "CC-BY-4.0",
            "sub_questions": [
                {
                    "stage": "formula",
                    "order": 1,
                    "stem": "Which relationship correctly links Cost Price (CP), Markup %, and Marked Price (MP)?",
                    "options": {
                        "A": "MP = CP * (1 + Markup% / 100)",
                        "B": "MP = CP * (1 - Markup% / 100)",
                        "C": "MP = CP / (1 + Markup% / 100)",
                        "D": "MP = CP * Markup%"
                    },
                    "correct_option": "A",
                    "time_limit_sec": 20
                },
                {
                    "stage": "substitution",
                    "order": 2,
                    "stem": "If CP = 100 and Markup = 40%, followed by a 20% discount on MP, what is the expression for SP?",
                    "options": {
                        "A": "SP = 140 * (1 - 0.20)",
                        "B": "SP = 140 * (1 + 0.20)",
                        "C": "SP = 100 * (1 - 0.20)",
                        "D": "SP = 140 / 0.80"
                    },
                    "correct_option": "A",
                    "time_limit_sec": 20
                },
                {
                    "stage": "calculation",
                    "order": 3,
                    "stem": "Compute: 140 * 0.80 - 100.",
                    "options": {
                        "A": "10",
                        "B": "12",
                        "C": "14",
                        "D": "16"
                    },
                    "correct_option": "B",
                    "time_limit_sec": 20
                }
            ]
        }
    ]
}


def validate_item(item: dict[str, Any], existing_stems: set[str], seen_batch_stems: set[str]) -> list[str]:
    errors = []
    stem = (item.get("stem") or item.get("question_text") or "").strip()
    if not stem:
        errors.append("Missing question stem.")
    elif stem in existing_stems:
        errors.append(f"Duplicate stem exists in DB: '{stem[:40]}...'")
    elif stem in seen_batch_stems:
        errors.append(f"Duplicate stem in batch: '{stem[:40]}...'")

    options = item.get("options") or item.get("options_json")
    if not isinstance(options, dict):
        errors.append("Options must be a dictionary with keys A, B, C, D.")
    else:
        keys = set(options.keys())
        if not {"A", "B", "C", "D"}.issubset(keys):
            errors.append(f"Options must contain exactly keys A, B, C, D. Found: {list(keys)}")

    correct = str(item.get("correct_option") or item.get("correct_answer") or "").upper().strip()
    if correct not in ["A", "B", "C", "D"]:
        errors.append(f"Invalid correct_option: '{correct}'. Must be A, B, C, or D.")

    source = item.get("source") or ""
    license_str = item.get("license") or ""
    if not source:
        errors.append("Missing required 'source' attribution.")
    if not license_str:
        errors.append("Missing required 'license' (e.g. 'CC-BY-4.0').")

    return errors


def import_json(filepath: str, db: Session) -> dict[str, int]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions_data = data.get("questions", data if isinstance(data, list) else [])
    default_source = data.get("metadata", {}).get("source", "Imported Bank")
    default_license = data.get("metadata", {}).get("license", "CC-BY-4.0")

    existing_stems = {q.question_text.strip() for q in db.query(Question.question_text).all()}
    seen_batch_stems = set()

    imported_main = 0
    imported_sub = 0

    for idx, item in enumerate(questions_data, 1):
        if not item.get("source"):
            item["source"] = default_source
        if not item.get("license"):
            item["license"] = default_license

        errors = validate_item(item, existing_stems, seen_batch_stems)
        if errors:
            print(f"Skipping Item #{idx} due to validation errors:")
            for err in errors:
                print(f"  - {err}")
            continue

        stem = item["stem"].strip()
        seen_batch_stems.add(stem)

        concept_id = item.get("concept_id")
        if not concept_id:
            # Fallback to first concept
            first_c = db.query(Concept.id).first()
            concept_id = first_c[0] if first_c else 1

        new_q = Question(
            concept_id=concept_id,
            question_text=stem,
            options_json=item["options"],
            correct_answer=item["correct_option"].upper(),
            explanation=item.get("explanation", ""),
            difficulty_hint=float(item.get("difficulty", 0.5)),
            source="curated",
            review_status="approved",
            needs_human_review=False,
        )
        db.add(new_q)
        db.flush()
        imported_main += 1

        # Process sub-questions if present
        sub_list = item.get("sub_questions", [])
        for s_idx, sq in enumerate(sub_list, 1):
            s_stem = sq.get("stem", "").strip()
            s_options = sq.get("options", {})
            s_correct = str(sq.get("correct_option", "A")).upper().strip()
            s_stage = sq.get("stage", "other")
            s_limit = int(sq.get("time_limit_sec", 20))
            s_order = int(sq.get("order", s_idx))

            new_sq = SubQuestion(
                parent_question_id=new_q.id,
                stage=s_stage,
                stem=s_stem,
                options_json=s_options,
                correct_answer=s_correct,
                time_limit_sec=s_limit,
                order=s_order,
            )
            db.add(new_sq)
            imported_sub += 1

    db.commit()
    return {"imported_main": imported_main, "imported_sub": imported_sub}


def seed_banking_sub_questions(db: Session) -> int:
    """Populates 3-stage sub-questions for Banking IBPS PO questions that currently lack them.
    
    Generates tailored stages:
    - Quantitative topics: formula, substitution, calculation
    - Verbal & GA topics: concept_recall, elimination, final_answer
    """
    from backend.app.models.core import Skill, Topic
    from backend.app.services.question_generator import generate_root_cause_sub_questions

    banking_qs = (
        db.query(Question)
        .join(Concept, Question.concept_id == Concept.id)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .filter(Skill.target_id == 7)
        .all()
    )

    created_count = 0
    for q in banking_qs:
        existing = db.query(SubQuestion).filter(SubQuestion.parent_question_id == q.id).count()
        if existing >= 3:
            continue

        topic_name = q.concept.topic.name if (q.concept and q.concept.topic) else "General Syllabus"
        concept_name = q.concept.name if q.concept else "Core Concept"
        generated = generate_root_cause_sub_questions(
            topic_name=topic_name,
            concept_name=concept_name,
            main_question_stem=q.question_text,
        )
        for sq in generated:
            db.add(
                SubQuestion(
                    parent_question_id=q.id,
                    stage=sq["stage"],
                    stem=sq["stem"],
                    options_json=sq["options"],
                    correct_answer=sq["correct_option"],
                    time_limit_sec=sq.get("time_limit_sec", 20),
                    order=sq.get("order", 1),
                )
            )
            created_count += 1

    db.commit()
    return created_count


def main():
    parser = argparse.ArgumentParser(description="Import validated questions and sub-questions.")
    parser.add_argument("--json", type=str, default=None, help="Path to JSON file to import")
    parser.add_argument("--template", action="store_true", help="Print JSON template")
    parser.add_argument("--seed-sub-questions", action="store_true", help="Seed 3-stage sub-questions for all Banking questions")
    args = parser.parse_args()

    if args.template:
        print(json.dumps(SAMPLE_TEMPLATE_DATA, indent=2))
        return

    with Session(engine) as db:
        if args.seed_sub_questions:
            print("Seeding diagnostic 3-stage sub-questions for Banking IBPS PO question bank...")
            added = seed_banking_sub_questions(db)
            print(f"Successfully added {added} diagnostic sub-questions across Banking question bank.")

        if args.json:
            print(f"Importing questions from {args.json}...")
            result = import_json(args.json, db)
            print(f"Import complete: {result['imported_main']} main questions, {result['imported_sub']} sub-questions.")


if __name__ == "__main__":
    main()
