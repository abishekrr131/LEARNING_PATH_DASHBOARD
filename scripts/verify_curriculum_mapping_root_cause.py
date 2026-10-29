import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ['DATABASE_URL'] = 'sqlite:///C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/palp_local.db'

from backend.app.db.session import SessionLocal
from backend.app.models.core import User, CareerTarget, Concept, Topic, Skill
from backend.app.api.analytics import get_root_cause_analytics

db = SessionLocal()
u = db.query(User).filter(User.id == 4).first()

# Map of target ID to expected concept ranges and names
targets = db.query(CareerTarget).order_by(CareerTarget.id).all()

print("=" * 80)
print("TESTING CURRICULUM-MAPPING & ROOT CAUSE TARGET FILTERING ACROSS ALL TARGETS")
print("=" * 80)

all_passed = True

for t in targets:
    # Query valid concept IDs for this target
    valid_concepts = db.query(Concept.id, Concept.name)\
        .join(Topic, Concept.topic_id == Topic.id)\
        .join(Skill, Topic.skill_id == Skill.id)\
        .filter(Skill.target_id == t.id)\
        .all()
    valid_ids = {c[0] for c in valid_concepts}
    valid_names = {c[0]: c[1] for c in valid_concepts}
    
    # 1. Test default call with target_id
    res_default = get_root_cause_analytics(concept_id=None, target_id=t.id, current_user=u, db=db)
    surface_id = res_default.get("surface_concept_id")
    surface_name = res_default.get("surface_concept_name")
    target_name = res_default.get("target_name")
    
    assert surface_id in valid_ids, f"FAIL: Target {t.name} (ID {t.id}) returned surface concept {surface_id} ({surface_name}) not in valid concepts!"
    
    # Verify all target_concepts belong strictly to target
    returned_cids = {tc["concept_id"] for tc in res_default.get("target_concepts", [])}
    assert returned_cids == valid_ids, f"FAIL: Target {t.name} target_concepts mismatch!"
    
    # Verify prerequisites and dependents belong to target
    for p in res_default.get("direct_prerequisites", []):
        assert p["concept_id"] in valid_ids, f"FAIL: Target {t.name} prerequisite {p['concept_id']} not in target!"
    for d in res_default.get("direct_dependents", []):
        assert d["concept_id"] in valid_ids, f"FAIL: Target {t.name} dependent {d['concept_id']} not in target!"
    for cand in res_default.get("candidates", []):
        assert cand["candidate_concept_id"] in valid_ids, f"FAIL: Target {t.name} candidate {cand['candidate_concept_id']} not in target!"
    
    print(f"[OK] Target #{t.id} ({t.name}):")
    print(f"     Concepts count: {len(valid_ids)} | Default surface concept: [{surface_id}] '{surface_name}'")
    
    # 2. Test foreign concept_id rejection (e.g. concept_id = 1 on non-ML targets)
    if t.id != 1:
        # Pass concept_id = 1 (Vectors and Matrices)
        res_foreign = get_root_cause_analytics(concept_id=1, target_id=t.id, current_user=u, db=db)
        sanitized_id = res_foreign.get("surface_concept_id")
        sanitized_name = res_foreign.get("surface_concept_name")
        assert sanitized_id in valid_ids, f"FAIL: Foreign concept 1 was not sanitized for target {t.name}!"
        assert sanitized_id != 1, f"FAIL: Target {t.name} accepted foreign concept 1!"
        print(f"     Foreign concept_id=1 properly sanitized -> [{sanitized_id}] '{sanitized_name}'")
    else:
        # For ML Engineer (target 1), concept_id=1 is valid
        res_ml = get_root_cause_analytics(concept_id=1, target_id=t.id, current_user=u, db=db)
        assert res_ml.get("surface_concept_id") == 1
        print(f"     ML Engineer explicitly supports concept_id=1 -> '{res_ml.get('surface_concept_name')}'")

print("=" * 80)
print("ALL 7 TARGETS PASSED TARGET-FILTERING & CURRICULUM-MAPPING VERIFICATION!")
print("=" * 80)
