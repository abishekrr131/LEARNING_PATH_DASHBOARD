"""Automated tests verifying strict Combined Test distribution rules.

Tests cover:
1. A 40-question Government Combined Test contains exactly 10 questions per category.
2. A 20-question test contains exactly 5 per category.
3. Remainder distribution (e.g., 22 questions → 6, 6, 5, 5).
4. No duplicate question IDs occur in one test.
5. Questions belong to the user's selected exam and category.
6. Insufficient category inventory produces a clear HTTP 400 error.
7. Refreshing or reopening a test does not unexpectedly replace its question set.
8. Topic counts reflect validated records, not hardcoded values.
9. Category mapping correctness for all government exam skill names.
"""
from __future__ import annotations

import pytest
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.core import (
    Assessment,
    AssessmentQuestion,
    CareerTarget,
    Concept,
    Question,
    Skill,
    Topic,
    User,
)
from backend.app.services.question_generator import (
    generate_practice_questions,
    map_govt_skill_to_category,
    to_options_list,
)
from backend.app.services.dataset_service import (
    get_dataset_verification_report,
    get_labeled_dataset_for_target,
    difficulty_to_label,
    DATASET_CATALOG,
)
from fastapi import HTTPException


@pytest.fixture
def db():
    """Provides a fresh database session for each test."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def banking_target(db: Session) -> CareerTarget:
    """Retrieves the Banking (IBPS PO) career target."""
    target = db.execute(
        select(CareerTarget).where(CareerTarget.name == "Banking (IBPS PO)")
    ).scalar_one_or_none()
    assert target is not None, "Banking (IBPS PO) target must exist in database"
    return target


@pytest.fixture
def ssc_target(db: Session) -> CareerTarget:
    """Retrieves the SSC CGL career target."""
    target = db.execute(
        select(CareerTarget).where(CareerTarget.name == "SSC CGL")
    ).scalar_one_or_none()
    assert target is not None, "SSC CGL target must exist in database"
    return target


@pytest.fixture
def test_user(db: Session) -> User:
    """Creates or retrieves a test user for assessment creation."""
    user = db.execute(
        select(User).where(User.email == "combined_test_user@test.internal")
    ).scalar_one_or_none()
    if not user:
        user = User(
            email="combined_test_user@test.internal",
            name="Combined Test User",
            picture_url="",
            google_sub="combined_test_user_gid",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _cleanup_test_assessments(db: Session, user_id: int):
    """Removes all practice assessments created by the test user to ensure test isolation."""
    assessments = db.execute(
        select(Assessment).where(
            Assessment.user_id == user_id,
            Assessment.type == "practice",
        )
    ).scalars().all()
    for a in assessments:
        db.delete(a)
    db.commit()


def _count_questions_by_category(items: list[dict], db: Session) -> dict[str, int]:
    """Counts questions per standard category from returned items."""
    cat_counts: dict[str, int] = {}
    for item in items:
        q = db.get(Question, item["question_id"])
        concept = db.get(Concept, q.concept_id)
        topic = db.get(Topic, concept.topic_id)
        skill = db.get(Skill, topic.skill_id)
        target = db.get(CareerTarget, skill.target_id)

        cat = map_govt_skill_to_category(skill.name) if target.category == "govt_exam" else skill.name
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    return cat_counts


class TestCategoryMapping:
    """Tests that government exam skill names are correctly mapped to categories."""

    def test_banking_skills_mapping(self):
        assert map_govt_skill_to_category("Quantitative Aptitude & Data Interpretation") == "Aptitude"
        assert map_govt_skill_to_category("Reasoning Ability & Computer Aptitude") == "Reasoning"
        assert map_govt_skill_to_category("English Language") == "Verbal"
        assert map_govt_skill_to_category("General & Banking Awareness") == "General Awareness"

    def test_ssc_skills_mapping(self):
        assert map_govt_skill_to_category("Quantitative Aptitude") == "Aptitude"
        assert map_govt_skill_to_category("General Intelligence & Reasoning") == "Reasoning"
        assert map_govt_skill_to_category("English Comprehension") == "Verbal"
        assert map_govt_skill_to_category("General Awareness") == "General Awareness"

    def test_it_skills_passthrough(self):
        """IT career skills should pass through unchanged."""
        assert map_govt_skill_to_category("Frontend Architecture") == "Frontend Architecture"
        assert map_govt_skill_to_category("Core Machine Learning") == "Core Machine Learning"


class TestCombinedTestDistribution:
    """Tests strict Combined Test 4-category distribution for Government exams."""

    def test_40_question_banking_combined_has_10_per_category(
        self, db: Session, banking_target: CareerTarget, test_user: User
    ):
        """40-question Government Combined Test must contain exactly 10 per category."""
        _cleanup_test_assessments(db, test_user.id)

        asmt_id, items = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=40,
            practice_mode="combined",
        )

        assert len(items) == 40
        cat_counts = _count_questions_by_category(items, db)

        assert cat_counts.get("Aptitude", 0) == 10, f"Aptitude: expected 10, got {cat_counts.get('Aptitude', 0)}"
        assert cat_counts.get("Reasoning", 0) == 10, f"Reasoning: expected 10, got {cat_counts.get('Reasoning', 0)}"
        assert cat_counts.get("Verbal", 0) == 10, f"Verbal: expected 10, got {cat_counts.get('Verbal', 0)}"
        assert cat_counts.get("General Awareness", 0) == 10, f"GA: expected 10, got {cat_counts.get('General Awareness', 0)}"

        _cleanup_test_assessments(db, test_user.id)

    def test_20_question_banking_combined_has_5_per_category(
        self, db: Session, banking_target: CareerTarget, test_user: User
    ):
        """20-question Government Combined Test must contain exactly 5 per category."""
        _cleanup_test_assessments(db, test_user.id)

        asmt_id, items = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=20,
            practice_mode="combined",
        )

        assert len(items) == 20
        cat_counts = _count_questions_by_category(items, db)

        assert cat_counts.get("Aptitude", 0) == 5
        assert cat_counts.get("Reasoning", 0) == 5
        assert cat_counts.get("Verbal", 0) == 5
        assert cat_counts.get("General Awareness", 0) == 5

        _cleanup_test_assessments(db, test_user.id)

    def test_remainder_distribution_22_questions(
        self, db: Session, banking_target: CareerTarget, test_user: User
    ):
        """22 questions → base=5, rem=2 → Aptitude:6, Reasoning:6, Verbal:5, GA:5."""
        _cleanup_test_assessments(db, test_user.id)

        asmt_id, items = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=22,
            practice_mode="combined",
        )

        assert len(items) == 22
        cat_counts = _count_questions_by_category(items, db)

        # First 2 categories in canonical order get base+1
        assert cat_counts.get("Aptitude", 0) == 6
        assert cat_counts.get("Reasoning", 0) == 6
        assert cat_counts.get("Verbal", 0) == 5
        assert cat_counts.get("General Awareness", 0) == 5

        # Category counts differ by at most 1
        counts = list(cat_counts.values())
        assert max(counts) - min(counts) <= 1

        _cleanup_test_assessments(db, test_user.id)

    def test_100_question_banking_combined_has_25_per_category(
        self, db: Session, banking_target: CareerTarget, test_user: User
    ):
        """100-question Combined Test needs 25 per category.
        Banking has Aptitude:76, Reasoning:36, Verbal:49, GA:25 — all >= 25.
        """
        _cleanup_test_assessments(db, test_user.id)

        asmt_id, items = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=100,
            practice_mode="combined",
        )

        assert len(items) == 100
        cat_counts = _count_questions_by_category(items, db)

        assert cat_counts.get("Aptitude", 0) == 25
        assert cat_counts.get("Reasoning", 0) == 25
        assert cat_counts.get("Verbal", 0) == 25
        assert cat_counts.get("General Awareness", 0) == 25

        _cleanup_test_assessments(db, test_user.id)


class TestNoDuplicateQuestions:
    """Tests that no duplicate question IDs occur within a single test."""

    def test_no_duplicate_ids_in_40_question_combined(
        self, db: Session, banking_target: CareerTarget, test_user: User
    ):
        _cleanup_test_assessments(db, test_user.id)

        asmt_id, items = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=40,
            practice_mode="combined",
        )

        q_ids = [item["question_id"] for item in items]
        assert len(q_ids) == len(set(q_ids)), (
            f"Duplicate question IDs found: {[x for x in q_ids if q_ids.count(x) > 1]}"
        )

        _cleanup_test_assessments(db, test_user.id)


class TestExamAndCategoryFiltering:
    """Tests that questions belong to the user's selected exam and correct categories."""

    def test_questions_belong_to_selected_target(
        self, db: Session, banking_target: CareerTarget, test_user: User
    ):
        _cleanup_test_assessments(db, test_user.id)

        asmt_id, items = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=20,
            practice_mode="combined",
        )

        for item in items:
            q = db.get(Question, item["question_id"])
            concept = db.get(Concept, q.concept_id)
            topic = db.get(Topic, concept.topic_id)
            skill = db.get(Skill, topic.skill_id)
            assert skill.target_id == banking_target.id, (
                f"Question {q.id} belongs to target {skill.target_id}, "
                f"expected {banking_target.id}"
            )

        _cleanup_test_assessments(db, test_user.id)


class TestInsufficientInventory:
    """Tests that insufficient category inventory produces a clear HTTP 400 error."""

    def test_ssc_40_question_raises_insufficient_error(
        self, db: Session, ssc_target: CareerTarget, test_user: User
    ):
        """Requesting 2000 questions (500 per category) exceeds category inventory and must fail with 400."""
        _cleanup_test_assessments(db, test_user.id)

        with pytest.raises(HTTPException) as exc_info:
            generate_practice_questions(
                db=db,
                target=ssc_target,
                current_user_id=test_user.id,
                count=2000,
                practice_mode="combined",
            )

        assert exc_info.value.status_code == 400
        assert "Insufficient question bank inventory" in str(exc_info.value.detail)

        _cleanup_test_assessments(db, test_user.id)


class TestSessionResumption:
    """Tests that refreshing or reopening a test does not replace its question set."""

    def test_reopening_returns_same_questions(
        self, db: Session, banking_target: CareerTarget, test_user: User
    ):
        """Calling generate_practice_questions twice without completing should return
        the same persisted questions (session resumption).
        """
        _cleanup_test_assessments(db, test_user.id)

        asmt_id_1, items_1 = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=20,
            practice_mode="combined",
        )

        # Second call without completing the first assessment
        asmt_id_2, items_2 = generate_practice_questions(
            db=db,
            target=banking_target,
            current_user_id=test_user.id,
            count=20,
            practice_mode="combined",
        )

        # Should return the same assessment and questions
        assert asmt_id_1 == asmt_id_2, "Reopening should return the same assessment"
        q_ids_1 = [item["question_id"] for item in items_1]
        q_ids_2 = [item["question_id"] for item in items_2]
        assert q_ids_1 == q_ids_2, "Reopening should return the same question set in the same order"

        _cleanup_test_assessments(db, test_user.id)


class TestDatasetVerification:
    """Tests that topic counts reflect validated database records, not hardcoded values."""

    def test_verification_report_matches_db_counts(self, db: Session):
        """Report counts must match actual verified questions per target in the database."""
        report = get_dataset_verification_report(db)

        assert report["total_questions"] > 0
        assert report["total_verified"] > 0
        assert len(report["datasets"]) == 7  # All 7 datasets active

        for ds in report["datasets"]:
            cat_total = sum(c["total_questions"] for c in ds["categories"])
            assert cat_total == ds["total_questions"], (
                f"Category total mismatch for {ds['target_name']}: "
                f"sum={cat_total}, reported={ds['total_questions']}"
            )

    def test_labeled_dataset_metadata_consistency(self, db: Session):
        """Every question from the labeled dataset API must have all required metadata fields."""
        required_keys = {
            "id", "sector", "exam", "category", "skill", "topic", "subtopic",
            "difficulty", "difficulty_b", "question_text", "options",
            "correct_answer", "explanation", "source_name", "source_url",
            "verification_status", "review_status",
        }

        for target_id in range(1, 8):
            labeled = get_labeled_dataset_for_target(db, target_id, verified_only=True)
            if not labeled:
                continue
            for q_meta in labeled:
                missing = required_keys - set(q_meta.keys())
                assert not missing, (
                    f"Question {q_meta.get('id')} for target {target_id} "
                    f"missing metadata keys: {missing}"
                )
                assert q_meta["difficulty"] in ("easy", "medium", "hard"), (
                    f"Invalid difficulty label '{q_meta['difficulty']}' for q {q_meta['id']}"
                )
                assert q_meta["verification_status"] == "verified"
                assert len(q_meta["options"]) == 4, (
                    f"Question {q_meta['id']} does not have exactly 4 options"
                )

    def test_difficulty_classification(self):
        """Tests the difficulty_to_label function."""
        assert difficulty_to_label(-1.5) == "easy"
        assert difficulty_to_label(-0.5) == "easy"
        assert difficulty_to_label(-0.4) == "medium"
        assert difficulty_to_label(0.0) == "medium"
        assert difficulty_to_label(0.5) == "medium"
        assert difficulty_to_label(0.6) == "hard"
        assert difficulty_to_label(1.5) == "hard"

    def test_all_seven_datasets_present_in_catalog(self):
        """Confirms all 7 dataset files are tracked in the catalog."""
        expected_files = {
            "govt_banking.py", "govt_ssc_cgl.py", "govt_upsc.py",
            "it_cyber_security.py", "it_full_stack.py", "it_genai.py",
            "it_ml_engineer.py",
        }
        catalog_files = {d["file"] for d in DATASET_CATALOG}
        assert catalog_files == expected_files
