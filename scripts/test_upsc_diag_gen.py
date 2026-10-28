"""Test generate_initial_diagnostic_questions with UPSC Civil Services."""
import os
import sys

base_dir = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard"
sys.path.insert(0, base_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_path = os.path.join(base_dir, "palp_local.db")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

from backend.app.models.core import User, CareerTarget
from backend.app.services.question_generator import generate_initial_diagnostic_questions

user = db.query(User).first()
upsc = db.query(CareerTarget).filter(CareerTarget.name == "UPSC Civil Services").first()

print(f"User: {user.id} ({user.email}), Target: {upsc.id} ({upsc.name})")

asmt_id, items = generate_initial_diagnostic_questions(
    db=db,
    target=upsc,
    current_user_id=user.id,
    gemini_client=None,
)

print(f"Generated Assessment ID: {asmt_id}")
print(f"Total items generated: {len(items)}")
for idx, it in enumerate(items):
    print(f"  {idx+1}. [{it['topic_name']}] Concept: {it['concept_name']} - Q: {it['question_text'][:50]}... (diff: {it['difficulty_b']})")

assert len(items) == 10, f"Expected 10 items but got {len(items)}"
db.rollback()
db.close()
print("\n[UPSC DIAGNOSTIC GENERATION TEST PASSED!]")
