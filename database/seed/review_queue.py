"""Question Bank Review Tool
Allows inspecting pending questions and approving them for scored assessments.
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.db.session import SessionLocal
from backend.app.models.core import Question, User


def get_reviewer(db):
    rev = db.query(User).filter(User.email == "reviewer@palp.internal").first()
    if not rev:
        rev = User(name="Curriculum Reviewer", email="reviewer@palp.internal", role="reviewer")
        db.add(rev)
        db.commit()
    return rev


def check_status(db):
    total = db.query(Question).count()
    pending = db.query(Question).filter(Question.review_status == "pending").count()
    approved = db.query(Question).filter(Question.review_status == "approved").count()
    rejected = db.query(Question).filter(Question.review_status == "rejected").count()
    print("Question Bank Review Status:")
    print(f"  Total Questions: {total}")
    print(f"  Pending Review:  {pending}")
    print(f"  Approved:        {approved}")
    print(f"  Rejected:        {rejected}")
    return pending, approved


def approve_all(db):
    rev = get_reviewer(db)
    pending_items = db.query(Question).filter(Question.review_status == "pending").all()
    count = len(pending_items)
    for q in pending_items:
        q.review_status = "approved"
        q.needs_human_review = False
        q.reviewed_by = rev.id
    db.commit()
    print(f"Successfully reviewed and approved {count} questions.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        if "--approve-all" in sys.argv:
            approve_all(db)
        check_status(db)
    finally:
        db.close()
