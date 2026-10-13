"""Import Questions from CSV or JSON into PALP Question Bank.

Supports previous-year papers, mock tests, and open datasets.
All imported questions default to review_status='pending' and needs_human_review=True,
unless explicitly flagged with --approved.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.db.session import SessionLocal
from backend.app.models.core import Concept, Question, User


def load_file(file_path: Path) -> list[dict[str, Any]]:
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "questions" in data:
                return data["questions"]
            raise ValueError("JSON must be a list of questions or an object with 'questions' key.")

    elif suffix in (".csv", ".tsv"):
        delimiter = "\t" if suffix == ".tsv" else ","
        items = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                items.append(dict(row))
        return items
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Use .csv or .json.")


def normalize_question(item: dict[str, Any], default_approved: bool = False) -> dict[str, Any]:
    # Extract stem
    stem = item.get("stem") or item.get("question_text") or item.get("question") or ""
    if not stem:
        raise ValueError("Item missing stem / question_text.")

    # Extract options
    options = item.get("options")
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except Exception:
            pass
    if not isinstance(options, dict):
        # Look for option_a, option_b, etc.
        opt_dict = {}
        for key in ("A", "B", "C", "D"):
            v = item.get(f"option_{key.lower()}") or item.get(f"option_{key}") or item.get(key)
            if v:
                opt_dict[key] = str(v)
        if opt_dict:
            options = opt_dict
        else:
            raise ValueError("Item missing options dict or option_a/b/c/d columns.")

    # Extract correct answer
    correct = item.get("correct_option") or item.get("correct_answer") or item.get("answer") or ""
    correct = str(correct).strip().upper()
    if correct not in ("A", "B", "C", "D"):
        if correct.startswith("OPTION "):
            correct = correct.split(" ")[1]
        elif correct in options:
            pass
        else:
            # Check by value
            for k, v in options.items():
                if str(v).strip().lower() == correct.lower():
                    correct = k
                    break

    explanation = item.get("explanation") or ""
    try:
        difficulty = float(item.get("difficulty") or item.get("difficulty_b") or item.get("difficulty_hint") or 0.0)
    except (ValueError, TypeError):
        difficulty = 0.0

    source = item.get("source") or "imported"
    raw_status = (item.get("status") or item.get("review_status") or "").lower()
    if default_approved or raw_status == "approved":
        review_status = "approved"
        needs_review = False
    else:
        review_status = "pending"
        needs_review = True

    return {
        "concept_id": item.get("concept_id"),
        "concept_name": item.get("concept_name"),
        "stem": stem,
        "options": options,
        "correct_option": correct,
        "explanation": explanation,
        "difficulty": difficulty,
        "source": source,
        "review_status": review_status,
        "needs_human_review": needs_review,
    }


def import_questions(file_path: str, default_approved: bool = False) -> int:
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found at {path}")
        return 0

    raw_items = load_file(path)
    print(f"Loaded {len(raw_items)} raw items from {path.name}")

    db = SessionLocal()
    imported_count = 0
    try:
        concepts = db.query(Concept).all()
        concept_by_id = {c.id: c for c in concepts}
        concept_by_name = {c.name.strip().lower(): c for c in concepts}

        default_reviewer = None
        if default_approved:
            default_reviewer = db.query(User).filter(User.email == "reviewer@palp.internal").first()

        for idx, raw in enumerate(raw_items, 1):
            try:
                norm = normalize_question(raw, default_approved=default_approved)
            except Exception as e:
                print(f"Row {idx} skipped: invalid schema ({e})")
                continue

            # Resolve concept
            c = None
            if norm["concept_id"] and int(norm["concept_id"]) in concept_by_id:
                c = concept_by_id[int(norm["concept_id"])]
            elif norm["concept_name"]:
                c = concept_by_name.get(str(norm["concept_name"]).strip().lower())

            if not c:
                # Fallback to first concept
                c = concepts[0] if concepts else None

            if not c:
                print(f"Row {idx} skipped: no concepts exist in database.")
                continue

            q = Question(
                concept_id=c.id,
                stem=norm["stem"],
                options=norm["options"],
                correct_option=norm["correct_option"],
                explanation=norm["explanation"],
                difficulty=norm["difficulty"],
                source=norm["source"],
                status=norm["review_status"],
                needs_human_review=norm["needs_human_review"],
                reviewed_by=default_reviewer.id if default_reviewer and default_approved else None,
            )
            db.add(q)
            imported_count += 1

        db.commit()
        print(f"Successfully imported {imported_count} questions into database.")
        return imported_count
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Import questions from CSV/JSON into question bank.")
    parser.add_argument("file", help="Path to CSV or JSON file")
    parser.add_argument("--approved", action="store_true", help="Mark imported questions as approved")
    args = parser.parse_args()

    import_questions(args.file, default_approved=args.approved)


if __name__ == "__main__":
    main()
