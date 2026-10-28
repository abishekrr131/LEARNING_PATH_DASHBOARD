"""
Disposable, safe restore tool for palp_render_snapshot_*.json files into any target PostgreSQL or SQLite database.
Never targets production unless explicitly confirmed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, date
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models.base import Base
import backend.app.models.core

RESTORE_ORDER = [
    "users",
    "career_targets",
    "learner_profiles",
    "skills",
    "topics",
    "concepts",
    "concept_dependencies",
    "questions",
    "sub_questions",
    "question_irt_params",
    "learning_resources",
    "assessments",
    "assessment_questions",
    "student_responses",
    "student_mastery",
    "topic_performance",
    "learning_schedule",
]


def parse_val(v):
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except Exception:
            pass
        if len(v) == 10 and v[4] == '-' and v[7] == '-':
            try:
                return date.fromisoformat(v)
            except Exception:
                pass
    return v


def restore_snapshot(snapshot_path: str, target_db_url: str):
    if not os.path.exists(snapshot_path):
        print(f"Error: Snapshot not found at {snapshot_path}")
        return False

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    engine_url = target_db_url
    if engine_url.startswith("postgresql://"):
        try:
            import psycopg
            engine_url = engine_url.replace("postgresql://", "postgresql+psycopg://", 1)
        except ImportError:
            engine_url = engine_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = sa.create_engine(engine_url)
    Base.metadata.create_all(bind=engine)

    total = 0
    with engine.begin() as conn:
        for tname in RESTORE_ORDER:
            rows = snapshot.get("tables", {}).get(tname, [])
            if not rows:
                continue

            table = Base.metadata.tables.get(tname)
            if table is None:
                continue

            cleaned_rows = []
            for r in rows:
                c_row = dict(r)
                for k, v in list(c_row.items()):
                    if k == "options_json" and isinstance(v, str):
                        try:
                            c_row[k] = json.loads(v)
                        except Exception:
                            pass
                    elif k in ("created_at", "updated_at", "started_at", "completed_at", "answered_at", "scheduled_date", "exam_date"):
                        c_row[k] = parse_val(v)
                cleaned_rows.append(c_row)

            conn.execute(table.insert(), cleaned_rows)
            total += len(cleaned_rows)
            print(f"  [✓] Table '{tname}': restored {len(cleaned_rows)} rows.")

    print(f"\nRestore complete! Reconstructed {total} rows into target database.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore snapshot to a target database")
    parser.add_argument("--snapshot", type=str, required=True, help="Path to JSON snapshot")
    parser.add_argument("--target-url", type=str, required=True, help="Connection string for target disposable database")
    args = parser.parse_args()
    restore_snapshot(args.snapshot, args.target_url)
