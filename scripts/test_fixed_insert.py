"""
Safe rollback-on-completion test script: tests the exact SQLAlchemy insert statement
against an isolated in-memory test database and checks batch handling.
"""
from __future__ import annotations

import json
import sys
import os
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models.base import Base
from backend.app.models.core import Question
from scripts.migrate_to_production import execute_migration, MIGRATION_TAG

def test_insert_mechanism():
    print("Testing insert execution in disposable database...")
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    sample_items = [
        {
            "local_id": i,
            "prod_concept_id": 1,
            "target": "Machine Learning Engineering",
            "skill": "Mathematics for ML",
            "topic": "Linear Algebra",
            "concept": "Vectors and Matrices",
            "question_text": f"Question {i} test stem?",
            "options_json": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "B",
            "explanation": f"Explanation {i}",
            "difficulty_hint": 0.25,
            "source": "imported",
            "source_title": "Benchmark CS",
            "source_url": "http://example.com",
            "license": "CC-BY-4.0",
            "exam_year": MIGRATION_TAG,
            "review_status": "approved",
            "needs_human_review": False,
            "verified": True,
        }
        for i in range(1, 15)
    ]

    res = execute_migration(engine, sample_items, batch_size=5, dry_run=False)
    print("Execution result:", res)
    assert res["inserted"] == 14
    assert res["failed_batches"] == 0
    assert res["success"] is True

    with engine.connect() as conn:
        cnt = conn.execute(sa.text("SELECT COUNT(*) FROM questions WHERE exam_year = :t"), {"t": MIGRATION_TAG}).scalar()
        print(f"Verified count in test database: {cnt} rows inserted with tag {MIGRATION_TAG}")
        assert cnt == 14

    print("ALL TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    test_insert_mechanism()
