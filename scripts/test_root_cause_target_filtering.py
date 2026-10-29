import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ['DATABASE_URL'] = 'sqlite:///C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/palp_local.db'

from backend.app.db.session import SessionLocal
from backend.app.models.core import User, LearnerProfile
from backend.app.api.analytics import get_root_cause_analytics

db = SessionLocal()
u = db.query(User).filter(User.id == 4).first()
prof = db.query(LearnerProfile).filter(LearnerProfile.user_id == u.id).first()
orig_target = prof.target_id

prof.target_id = 5 # UPSC
db.commit()

# Current behavior when concept_id=1 is passed while target is UPSC (ID 5)
res_with_foreign_id = get_root_cause_analytics(concept_id=1, current_user=u, db=db)
print("When target is UPSC (5) and concept_id=1 is passed:")
print("  Target Name:", res_with_foreign_id.get("target_name"))
print("  Surface Concept:", res_with_foreign_id.get("surface_concept_id"), res_with_foreign_id.get("surface_concept_name"))
print("  Is Concept 1 in UPSC target_concepts?", any(tc["concept_id"] == 1 for tc in res_with_foreign_id.get("target_concepts", [])))

# Current behavior when concept_id=None and user has no mistakes in UPSC
res_none = get_root_cause_analytics(concept_id=None, current_user=u, db=db)
print("\nWhen target is UPSC (5) and concept_id=None:")
print("  Target Name:", res_none.get("target_name"))
print("  Surface Concept:", res_none.get("surface_concept_id"), res_none.get("surface_concept_name"))
print("  Is Surface Concept in UPSC target_concepts?", any(tc["concept_id"] == res_none.get("surface_concept_id") for tc in res_none.get("target_concepts", [])))

prof.target_id = orig_target
db.commit()
