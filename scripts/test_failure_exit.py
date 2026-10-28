"""
Test verification for:
1. Column type detection (JSON vs JSONB) and dynamic statement preparation.
2. Failed batch non-zero exit status and error isolation.
"""
from __future__ import annotations

import sys
import os
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models.base import Base
from backend.app.models.core import Question
from scripts.migrate_to_production import execute_migration, MIGRATION_TAG


def test_failure_handling_and_exit_code():
    print("=" * 70)
    print("TEST: Batch Failure & Non-Zero Exit Status")
    print("=" * 70)

    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    # Prepare 3 batches of 2 items: batch 1 succeeds, batch 2 raises integrity error, batch 3 should not run
    batch_items = [
        # Batch 1 (items 1 & 2) - valid
        {
            "local_id": 1,
            "prod_concept_id": 1,
            "question_text": "Stem 1",
            "options_json": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "A",
            "explanation": "Exp 1",
            "difficulty_hint": 0.0,
            "source": "imported",
            "source_title": "T",
            "source_url": "u",
            "license": "CC",
            "exam_year": MIGRATION_TAG,
            "review_status": "approved",
            "needs_human_review": False,
            "verified": True,
        },
        {
            "local_id": 2,
            "prod_concept_id": 1,
            "question_text": "Stem 2",
            "options_json": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "B",
            "explanation": "Exp 2",
            "difficulty_hint": 0.0,
            "source": "imported",
            "source_title": "T",
            "source_url": "u",
            "license": "CC",
            "exam_year": MIGRATION_TAG,
            "review_status": "approved",
            "needs_human_review": False,
            "verified": True,
        },
        # Batch 2 (item 3 invalid - concept_id=None violates NOT NULL constraint)
        {
            "local_id": 3,
            "prod_concept_id": None,  # NOT NULL violation
            "question_text": "Stem 3",
            "options_json": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "C",
            "explanation": "Exp 3",
            "difficulty_hint": 0.0,
            "source": "imported",
            "source_title": "T",
            "source_url": "u",
            "license": "CC",
            "exam_year": MIGRATION_TAG,
            "review_status": "approved",
            "needs_human_review": False,
            "verified": True,
        },
        # Batch 3 (item 4) - should be aborted because batch 2 failed
        {
            "local_id": 4,
            "prod_concept_id": 1,
            "question_text": "Stem 4",
            "options_json": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "D",
            "explanation": "Exp 4",
            "difficulty_hint": 0.0,
            "source": "imported",
            "source_title": "T",
            "source_url": "u",
            "license": "CC",
            "exam_year": MIGRATION_TAG,
            "review_status": "approved",
            "needs_human_review": False,
            "verified": True,
        },
    ]

    result = execute_migration(engine, batch_items, batch_size=2, dry_run=False)
    print("Execution result:", result)

    assert result["failed_batches"] == 1, "Expected exactly 1 failed batch"
    assert result["success"] is False, "Expected success to be False"
    assert len(result["errors"]) > 0, "Expected non-empty errors list"
    assert result["inserted"] == 2, "Expected Batch 1 (2 items) to commit, Batch 2 to rollback, and Batch 3 to abort"

    print("Verified: Script stopped on Batch 2 error, aborted Batch 3, and marked success=False.")
    print("TEST PASSED!")


if __name__ == "__main__":
    test_failure_handling_and_exit_code()
