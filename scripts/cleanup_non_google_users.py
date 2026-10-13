"""Cleanup script to remove non-Google users and their associated telemetry.

Requirements (Area B):
- Dry-run mode by default: prints counts of users and associated rows before modifying anything.
- Execute mode (--execute): safely deletes all non-Google users and their related rows.
- Never deletes questions, concepts, topics, or skills. Sets Question.reviewed_by = NULL.
"""
from __future__ import annotations

import argparse
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import engine
from backend.app.models.core import (
    AiInteraction,
    Assessment,
    AssessmentQuestion,
    InterventionAssignment,
    LearnerProfile,
    LearningSchedule,
    MasteryHistory,
    Question,
    RootCauseAnalysis,
    StudentMastery,
    StudentResponse,
    TopicPerformance,
    User,
    VerificationProbe,
)


def get_non_google_user_ids(db: Session) -> list[int]:
    """Finds IDs of all users not created via genuine Google sign-in.
    
    A user is considered non-Google if:
    - google_sub is NULL or empty
    - google_sub starts with 'mock-sub-'
    - email ends with '@test.palp.internal' or '@ibps.internal'
    """
    users = db.query(User).all()
    non_google_ids = []
    for u in users:
        is_mock_sub = bool(u.google_sub and u.google_sub.startswith("mock-sub-"))
        is_internal_domain = u.email.endswith("@test.palp.internal") or u.email.endswith("@ibps.internal")
        if not u.google_sub or is_mock_sub or is_internal_domain:
            non_google_ids.append(u.id)
    return non_google_ids


def inspect_counts(db: Session, user_ids: list[int]) -> dict[str, int]:
    if not user_ids:
        return {}
    counts = {
        "users": len(user_ids),
        "learner_profiles": db.query(LearnerProfile).filter(LearnerProfile.user_id.in_(user_ids)).count(),
        "assessments": db.query(Assessment).filter(Assessment.user_id.in_(user_ids)).count(),
        "student_responses": db.query(StudentResponse).filter(StudentResponse.user_id.in_(user_ids)).count(),
        "student_masteries": db.query(StudentMastery).filter(StudentMastery.user_id.in_(user_ids)).count(),
        "mastery_histories": db.query(MasteryHistory).filter(MasteryHistory.user_id.in_(user_ids)).count(),
        "topic_performances": db.query(TopicPerformance).filter(TopicPerformance.user_id.in_(user_ids)).count(),
        "learning_schedules": db.query(LearningSchedule).filter(LearningSchedule.user_id.in_(user_ids)).count(),
        "root_cause_analyses": db.query(RootCauseAnalysis).filter(RootCauseAnalysis.user_id.in_(user_ids)).count(),
        "verification_probes": db.query(VerificationProbe).filter(VerificationProbe.user_id.in_(user_ids)).count(),
        "intervention_assignments": db.query(InterventionAssignment).filter(InterventionAssignment.user_id.in_(user_ids)).count(),
        "ai_interactions": db.query(AiInteraction).filter(AiInteraction.user_id.in_(user_ids)).count(),
    }
    return counts


def execute_cleanup(db: Session, user_ids: list[int]) -> None:
    if not user_ids:
        return

    # 1. Nullify reviewed_by on questions so questions are NEVER deleted
    db.query(Question).filter(Question.reviewed_by.in_(user_ids)).update(
        {Question.reviewed_by: None}, synchronize_session=False
    )

    # 2. Delete assessment questions for assessments belonging to these users
    asmt_ids = [a.id for a in db.query(Assessment.id).filter(Assessment.user_id.in_(user_ids)).all()]
    if asmt_ids:
        db.query(AssessmentQuestion).filter(AssessmentQuestion.assessment_id.in_(asmt_ids)).delete(
            synchronize_session=False
        )

    # 3. Delete dependent rows
    db.query(AiInteraction).filter(AiInteraction.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(InterventionAssignment).filter(InterventionAssignment.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(VerificationProbe).filter(VerificationProbe.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(RootCauseAnalysis).filter(RootCauseAnalysis.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(LearningSchedule).filter(LearningSchedule.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(TopicPerformance).filter(TopicPerformance.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(MasteryHistory).filter(MasteryHistory.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(StudentMastery).filter(StudentMastery.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(StudentResponse).filter(StudentResponse.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(Assessment).filter(Assessment.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(LearnerProfile).filter(LearnerProfile.user_id.in_(user_ids)).delete(synchronize_session=False)

    # 4. Delete user rows
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


def main():
    parser = argparse.ArgumentParser(description="Cleanup non-Google users.")
    parser.add_argument("--execute", action="store_true", help="Execute deletion (default is dry-run)")
    args = parser.parse_args()

    with Session(engine) as db:
        all_users_before = db.query(User).all()
        print("=" * 60)
        print(f"DATABASE CLEANUP AUDIT (Total Users in DB: {len(all_users_before)})")
        print("=" * 60)
        print("BEFORE Users in DB:")
        for u in all_users_before:
            print(f"  ID {u.id:2d}: {u.email:<35} | Name: {u.name:<22} | Google Sub: {u.google_sub}")

        non_google_ids = get_non_google_user_ids(db)
        print(f"\nNon-Google Users Identified: {len(non_google_ids)}")

        counts = inspect_counts(db, non_google_ids)
        print("\nAssociated records to be removed:")
        for table_name, count in counts.items():
            print(f"  {table_name:<30}: {count}")

        if args.execute:
            print("\nExecuting database cleanup...")
            execute_cleanup(db, non_google_ids)
            all_users_after = db.query(User).all()
            print("\nAFTER Users in DB:")
            if not all_users_after:
                print("  (0 user rows remaining - ready for fresh Google Sign-In)")
            else:
                for u in all_users_after:
                    print(f"  ID {u.id:2d}: {u.email:<35} | Google Sub: {u.google_sub}")
            print(f"\nSuccessfully purged {len(non_google_ids)} non-Google user accounts and all associated data.")
        else:
            print("\n[DRY RUN MODE] No changes were written to the database.")
            print("To execute this cleanup, run: py -3.13 scripts/cleanup_non_google_users.py --execute")


if __name__ == "__main__":
    main()
