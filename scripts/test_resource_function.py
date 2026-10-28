"""Direct unit test for get_resource_detail in backend/app/api/learning.py."""
import os
import sys

base_dir = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard"
sys.path.insert(0, base_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Connect directly to palp_local.db
db_path = os.path.join(base_dir, "palp_local.db")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

from backend.app.models.core import User, LearningResource, Concept
from backend.app.api.learning import get_resource_detail

user = db.query(User).first()
if not user:
    user = User(id=1, email="test@example.com", name="Test User", role="learner")

print("--- Testing with Sample Learning Resources ---")
resources = db.query(LearningResource).limit(3).all()
for r in resources:
    result = get_resource_detail(resource_id=r.id, current_user=user, db=db)
    print(f"ID {r.id}:")
    print(f"  Title: {result['title']}")
    print(f"  Concept: {result['concept_name']}")
    print(f"  Topic: {result['topic_name']}")
    print(f"  Target: {result['target_name']}")
    print(f"  Is Internal: {result['is_internal']}")
    print(f"  External URL: {result['external_url']}")
    print(f"  Key points: {result['key_points']}")
    print(f"  Worked examples count: {len(result['worked_examples'])}")
    print(f"  External references: {[ref['title'] for ref in result['external_references']]}")

print("\n--- Testing UPSC Concept specifically ---")
upsc_concepts = db.query(Concept).filter(Concept.name.in_([
    "Indus Valley Civilization",
    "Mauryan & Gupta Empires",
    "Delhi Sultanate & Mughal Administration"
])).all()

for c in upsc_concepts:
    result = get_resource_detail(resource_id=c.id, current_user=user, db=db)
    print(f"\nUPSC Concept {c.id} ({c.name}):")
    print(f"  Title: {result['title']}")
    print(f"  Target: {result['target_name']}")
    print(f"  Topic: {result['topic_name']}")
    print(f"  Key Points: {result['key_points']}")
    print(f"  Worked Examples: {len(result['worked_examples'])}")
    if result['worked_examples']:
        print(f"  Sample Question: {result['worked_examples'][0]['question_text']}")
        print(f"  Sample Options: {result['worked_examples'][0]['options']}")
        print(f"  Sample Explanation: {result['worked_examples'][0]['explanation']}")
    print(f"  External Refs: {[ref['source'] + ': ' + ref['title'] for ref in result['external_references']]}")

# Test 404
print("\n--- Testing 404 for invalid ID ---")
try:
    get_resource_detail(resource_id=999999, current_user=user, db=db)
    print("FAILED: Expected 404 exception!")
except Exception as e:
    print(f"SUCCESS: Caught expected exception: {e}")

db.close()
print("\n[ALL FUNCTION TESTS COMPLETED SUCCESSFULLY!]")
