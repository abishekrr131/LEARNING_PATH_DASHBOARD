"""Test script to verify diagnostic status, empty stub handling, and question generation."""
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

from backend.app.models.core import User, CareerTarget, Assessment, AssessmentQuestion, StudentResponse, Question, Skill, Topic, Concept

# Check total approved questions in palp_local.db
total_q = db.query(Question).count()
approved_q = db.query(Question).filter(Question.review_status.in_(["approved", "curated", "generated"])).count()
print(f"Total questions in local db: {total_q}, Approved/Curated: {approved_q}")

# Check targets
targets = db.query(CareerTarget).all()
print(f"Total career targets: {len(targets)}")
for t in targets:
    t_q_count = db.query(Question).join(Concept).join(Topic).join(Skill).filter(Skill.target_id == t.id).count()
    print(f"  Target {t.id} ({t.name}): {t_q_count} questions")

db.close()
print("\n[DB CHECK COMPLETE]")
