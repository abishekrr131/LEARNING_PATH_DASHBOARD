"""Test get_resource_detail endpoint with FastAPI TestClient using palp_local.db."""
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

# Set database URL to palp_local.db for test script
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(base_dir, 'palp_local.db').replace(os.sep, '/')}"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.models.core import User, LearningResource, Concept

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

db = TestingSessionLocal()
user = db.query(User).first()
if not user:
    user = User(email="test_study@example.com", name="Test User", google_sub="sub-test-study", role="learner")
    db.add(user)
    db.commit()
    db.refresh(user)

token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
headers = {"Authorization": f"Bearer {token}"}

# Check sample resources:
sample_resources = db.query(LearningResource).limit(3).all()
print(f"Testing {len(sample_resources)} sample resources from database:")
for r in sample_resources:
    resp = client.get(f"/api/learning/resources/{r.id}", headers=headers)
    print(f"\nResource ID {r.id}: status {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200 but got {resp.status_code}: {resp.text}"
    data = resp.json()
    print(f"  Title: {data.get('title')}")
    print(f"  Concept: {data.get('concept_name')}")
    print(f"  Topic: {data.get('topic_name')}")
    print(f"  Target: {data.get('target_name')}")
    print(f"  Is Internal: {data.get('is_internal')}")
    print(f"  Key points: {len(data.get('key_points', []))}")
    print(f"  Worked examples: {len(data.get('worked_examples', []))}")
    print(f"  External refs: {[ref['title'] for ref in data.get('external_references', [])]}")

# Also test UPSC resources if present
upsc_concept = db.query(Concept).filter(Concept.name.ilike("%Indus Valley%")).first()
if upsc_concept:
    print(f"\nTesting UPSC Concept #{upsc_concept.id} ({upsc_concept.name}):")
    resp = client.get(f"/api/learning/resources/{upsc_concept.id}", headers=headers)
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    print(f"  Title: {data.get('title')}")
    print(f"  Description: {data.get('description')}")
    print(f"  Key Points: {data.get('key_points')}")
    print(f"  Worked Examples Count: {len(data.get('worked_examples', []))}")
    if data.get('worked_examples'):
        print(f"  Sample Example Question: {data['worked_examples'][0]['question_text']}")
    print(f"  External References: {[ref['title'] for ref in data.get('external_references', [])]}")

# Test 404
resp_404 = client.get("/api/learning/resources/999999", headers=headers)
print(f"\nStatus for resource 999999: {resp_404.status_code} (Expected 404)")
assert resp_404.status_code == 404

print("\n[ALL TESTS PASSED SUCCESSFULLY!]")
db.close()
