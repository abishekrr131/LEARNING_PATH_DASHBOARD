"""Check targets 8, 9, 12 and their questions in the pre-migration snapshot."""
import json

snapshot_path = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/exports/backups/palp_render_snapshot_20261027_164401.json"
data = json.load(open(snapshot_path, "r", encoding="utf-8"))
tables = data.get("tables", {})

targets = tables.get("career_targets", [])
target_map = {t["id"]: t["name"] for t in targets}
print("Target 8:", target_map.get(8))
print("Target 9:", target_map.get(9))
print("Target 12:", target_map.get(12))

skills = tables.get("skills", [])
topics = tables.get("topics", [])
concepts = tables.get("concepts", [])
questions = tables.get("questions", [])

# Find concepts belonging to target 12
skills_12 = [s["id"] for s in skills if s.get("target_id") == 12]
topics_12 = [t["id"] for t in topics if t.get("skill_id") in skills_12]
concepts_12 = [c["id"] for c in concepts if c.get("topic_id") in topics_12]
questions_12 = [q for q in questions if q.get("concept_id") in concepts_12]
approved_q_12 = [q for q in questions_12 if q.get("review_status") == "approved"]

print(f"\nTarget 12 ({target_map.get(12)}):")
print(f"  Skills: {len(skills_12)}")
print(f"  Topics: {len(topics_12)}")
print(f"  Concepts: {len(concepts_12)}")
print(f"  Questions: {len(questions_12)}")
print(f"  Approved Questions: {len(approved_q_12)}")

# Same for target 8 and 9
for tid in [8, 9]:
    s_ids = [s["id"] for s in skills if s.get("target_id") == tid]
    t_ids = [t["id"] for t in topics if t.get("skill_id") in s_ids]
    c_ids = [c["id"] for c in concepts if c.get("topic_id") in t_ids]
    q_ids = [q for q in questions if q.get("concept_id") in c_ids]
    app_q = [q for q in q_ids if q.get("review_status") == "approved"]
    print(f"\nTarget {tid} ({target_map.get(tid)}):")
    print(f"  Skills: {len(s_ids)}, Topics: {len(t_ids)}, Concepts: {len(c_ids)}")
    print(f"  Questions: {len(q_ids)}, Approved Questions: {len(app_q)}")
