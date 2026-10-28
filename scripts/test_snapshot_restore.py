"""
Verification of JSON snapshot restore into a separate, disposable in-memory test database.
DOES NOT TOUCH PRODUCTION.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, date
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models.base import Base
import backend.app.models.core

SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "exports", "backups", "palp_render_snapshot_20261027_164401.json"
)

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
        # Try datetime
        try:
            return datetime.fromisoformat(v)
        except Exception:
            pass
        # Try date
        if len(v) == 10 and v[4] == '-' and v[7] == '-':
            try:
                return date.fromisoformat(v)
            except Exception:
                pass
    return v


def test_restore_simulation():
    print("=" * 70)
    print("  SIMULATION: RESTORING SNAPSHOT INTO DISPOSABLE TEST DATABASE")
    print("  (Zero production access -- isolated in-memory test)")
    print("=" * 70)

    if not os.path.exists(SNAPSHOT_PATH):
        print(f"Error: Snapshot not found at {SNAPSHOT_PATH}")
        return False

    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    test_engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    print("[1/4] Created complete clean schema in disposable database.")

    total_restored = 0
    errors = []

    with test_engine.begin() as conn:
        for tname in RESTORE_ORDER:
            rows = snapshot.get("tables", {}).get(tname, [])
            if not rows:
                print(f"  [-] Table '{tname}': 0 rows to restore.")
                continue

            table = Base.metadata.tables.get(tname)
            if table is None:
                errors.append(f"Table '{tname}' not found in metadata.")
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

            try:
                conn.execute(table.insert(), cleaned_rows)
                total_restored += len(cleaned_rows)
                print(f"  [OK] Table '{tname}': restored {len(cleaned_rows)} rows cleanly.")
            except Exception as e:
                errors.append(f"Error restoring table '{tname}': {e}")
                print(f"  [FAIL] Table '{tname}': {e}")

    print("\n[2/4] Verifying record counts in test database...")
    counts_matched = True
    with test_engine.connect() as conn:
        for tname in RESTORE_ORDER:
            cnt = conn.execute(sa.text(f"SELECT COUNT(*) FROM {tname}")).scalar()
            expected = len(snapshot.get("tables", {}).get(tname, []))
            match = "MATCH" if cnt == expected else f"MISMATCH (expected {expected})"
            if cnt != expected:
                counts_matched = False
            print(f"  Table {tname:<25}: {cnt:>5} rows ({match})")

    print("\n[3/4] Testing foreign key traversal on restored data...")
    with test_engine.connect() as conn:
        q_count = conn.execute(sa.text("""
            SELECT COUNT(q.id)
            FROM questions q
            JOIN concepts c ON c.id = q.concept_id
            JOIN topics t ON t.id = c.topic_id
            JOIN skills s ON s.id = t.skill_id
            JOIN career_targets ct ON ct.id = s.target_id
        """)).scalar()
        print(f"  Traversed Question -> Target hierarchy: {q_count}/355 questions fully linked.")

        p_count = conn.execute(sa.text("""
            SELECT COUNT(lp.id)
            FROM learner_profiles lp
            JOIN users u ON u.id = lp.user_id
            JOIN career_targets ct ON ct.id = lp.target_id
        """)).scalar()
        print(f"  Traversed LearnerProfile -> User & Target: {p_count}/3 profiles fully linked.")

        u_count = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
        t_count = conn.execute(sa.text("SELECT COUNT(*) FROM career_targets")).scalar()
        c_count = conn.execute(sa.text("SELECT COUNT(*) FROM concepts")).scalar()

    print("\n[4/4] Restore Simulation Result:")
    if not errors and counts_matched and q_count == 355 and p_count == 3:
        print("  >>> SUCCESS: Snapshot is 100% reconstructible with all keys, IDs, and relations! <<<")
        print(f"  Total records reconstructed: {total_restored}")
        return True
    else:
        print(f"  >>> FAILED with {len(errors)} errors <<<")
        for err in errors:
            print(f"    - {err}")
        return False


if __name__ == "__main__":
    test_restore_simulation()
