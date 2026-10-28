import os, sys
sys.path.insert(0, os.path.abspath("."))
os.environ['DATABASE_URL'] = 'sqlite:///C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/palp_local.db'
from backend.app.db.session import SessionLocal
from backend.app.models.core import User
from backend.app.api.analytics import get_readiness_analytics, get_mistake_history

db = SessionLocal()
u1 = db.query(User).filter(User.id == 1).first()
u8 = db.query(User).filter(User.id == 8).first()

r1 = get_readiness_analytics(current_user=u1, db=db)
h1 = get_mistake_history(current_user=u1, db=db)

print("=== User 1 (Assessed) ===")
print("Readiness is_assessed:", r1.get("is_assessed"))
print("Target:", r1.get("target_name"))
print("Skills count:", len(r1.get("skill_components", [])))
for s in r1.get("skill_components", []):
    print(f" - {s['skill_name']}: weight={s['weight']}, mastery={s['skill_percentage']}%, demonstrated={s['demonstrated_topics']}/{s['total_topics']}")
print("Mistake history sessions count:", h1.get("total_sessions"))
for sess in h1.get("sessions", []):
    print(f" - {sess['short_label']}: score={sess['score_pct']}%, completed_at={sess['completed_at']}")

r8 = get_readiness_analytics(current_user=u8, db=db)
h8 = get_mistake_history(current_user=u8, db=db)

print("\n=== User 8 (Unassessed) ===")
print("Readiness is_assessed:", r8.get("is_assessed"))
print("Target:", r8.get("target_name"))
print("Skills count:", len(r8.get("skill_components", [])))
for s in r8.get("skill_components", []):
    print(f" - {s['skill_name']}: weight={s['weight']}, mastery={s['skill_percentage']}%, demonstrated={s['demonstrated_topics']}/{s['total_topics']}")
print("Mistake history sessions count:", h8.get("total_sessions"))
