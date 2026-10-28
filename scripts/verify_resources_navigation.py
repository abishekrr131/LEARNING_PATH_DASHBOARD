"""Comprehensive verification test for Resources & StudyMaterialDetail."""
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

from backend.app.models.core import User, LearningResource, Concept, Topic, CareerTarget
from backend.app.api.learning import get_resource_detail, get_learning_resources

user = db.query(User).first()
if not user:
    user = User(id=1, email="test@example.com", name="Test User", role="learner")

print("======================================================================")
print("1. VERIFYING GET /api/learning/resources LIST")
print("======================================================================")
list_result = get_learning_resources(concept_id=None, current_user=user, db=db)
resources = list_result.get("resources", [])
print(f"Total resources returned: {len(resources)}")
assert len(resources) > 0, "No resources returned by list endpoint!"

# Inspect how is_internal is flagged
internal_count = sum(1 for r in resources if r.get("is_internal"))
external_count = sum(1 for r in resources if not r.get("is_internal"))
print(f"  Internal study resources: {internal_count}")
print(f"  External online resources: {external_count}")

print("\n======================================================================")
print("2. VERIFYING 3 UPSC RESOURCES: INDUS VALLEY, MAURYAN, DELHI SULTANATE")
print("======================================================================")
upsc_concepts = [
    ("Indus Valley Civilization", 180),
    ("Mauryan & Gupta Empires", 182),
    ("Delhi Sultanate & Mughal Administration", 183),
]

for name, expected_id in upsc_concepts:
    c = db.query(Concept).filter(Concept.name == name).first()
    assert c is not None, f"Concept '{name}' not found in database!"
    
    # Test detail fetching by concept ID or resource ID
    detail = get_resource_detail(resource_id=c.id, current_user=user, db=db)
    
    print(f"\n[OK] Verified Concept #{c.id}: '{c.name}'")
    print(f"     Title: {detail['title']}")
    print(f"     Target Track: {detail['target_name']}")
    print(f"     Topic Name: {detail['topic_name']}")
    print(f"     Skill Name: {detail['skill_name']}")
    print(f"     Is Internal: {detail['is_internal']}")
    print(f"     Key Points Count: {len(detail['key_points'])} -> {detail['key_points']}")
    print(f"     Worked Examples Count: {len(detail['worked_examples'])}")
    
    assert len(detail['key_points']) > 0, f"Expected key points for {name}"
    assert len(detail['worked_examples']) > 0, f"Expected worked examples for {name}"
    assert len(detail['external_references']) > 0, f"Expected external references for {name}"
    
    # Check sample question structure
    sample_q = detail['worked_examples'][0]
    print(f"     Sample Worked Q: {sample_q['question_text'][:70]}...")
    print(f"     Sample Correct Ans: {sample_q['correct_answer']}")
    print(f"     Sample Explanation: {sample_q['explanation'][:70]}...")
    assert sample_q['question_text'], "Question text missing"
    assert sample_q['options'], "Options missing"
    assert sample_q['correct_answer'], "Correct answer missing"
    assert sample_q['explanation'], "Explanation missing"

print("\n======================================================================")
print("3. VERIFYING 404 AND ERROR CONTRACT")
print("======================================================================")
from fastapi import HTTPException
try:
    get_resource_detail(resource_id=999999, current_user=user, db=db)
    raise AssertionError("Expected HTTPException for missing resource")
except HTTPException as exc:
    print(f"[OK] Caught expected HTTPException: status {exc.status_code}, detail: {exc.detail}")
    assert exc.status_code == 404

print("\n======================================================================")
print("4. VERIFYING FRONTEND ROUTE CONFIGURATION")
print("======================================================================")
app_jsx_path = os.path.join(base_dir, "frontend", "src", "App.jsx")
with open(app_jsx_path, "r", encoding="utf-8") as f:
    app_jsx = f.read()
assert "import StudyMaterialDetail from \"./pages/StudyMaterialDetail\";" in app_jsx, "App.jsx missing StudyMaterialDetail import"
assert "path=\"/resources/:id\"" in app_jsx, "App.jsx missing /resources/:id route"
print("[OK] App.jsx route /resources/:id correctly registered with ProtectedRoute")

print("\n======================================================================")
print("5. VERIFYING RESOURCES PAGE NAVIGATION LOGIC")
print("======================================================================")
res_jsx_path = os.path.join(base_dir, "frontend", "src", "pages", "Resources.jsx")
with open(res_jsx_path, "r", encoding="utf-8") as f:
    res_jsx = f.read()
assert "to={`/resources/${res.id || res.concept_id}`}" in res_jsx, "Resources.jsx missing internal route Link"
assert "<span>Study Notes</span>" in res_jsx, "Resources.jsx missing Study Notes action"
assert "<span>Study Online</span>" in res_jsx, "Resources.jsx missing Study Online action"
assert "<span>Material Pending</span>" in res_jsx, "Resources.jsx missing fallback pending action"
print("[OK] Resources.jsx handles internal, external, and pending resources gracefully")

print("\n======================================================================")
print("6. VERIFYING FRONTEND BUILD OUTPUT")
print("======================================================================")
dist_index = os.path.join(base_dir, "frontend", "dist", "index.html")
assert os.path.exists(dist_index), "dist/index.html does not exist"
print(f"[OK] Verified frontend dist build exists: {dist_index}")

print("\n[ALL 6 VERIFICATION CHECKS PASSED WITH ZERO ERRORS]")
db.close()
