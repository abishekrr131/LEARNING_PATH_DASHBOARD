"""Inspect users, assessments, and responses in the pre-migration snapshot."""
import json
import os

snapshot_path = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/exports/backups/palp_render_snapshot_20261027_164401.json"

with open(snapshot_path, "r", encoding="utf-8") as f:
    data = json.load(f)

tables = data.get("tables", {})

print("--- USERS IN SNAPSHOT ---")
users = tables.get("users", [])
for u in users:
    print(f"User ID: {u.get('id')}, Name: {u.get('name')}, Email: {u.get('email')}, GoogleSub: {u.get('google_sub')}")

print("\n--- LEARNER PROFILES IN SNAPSHOT ---")
profiles = tables.get("learner_profiles", [])
for p in profiles:
    print(f"Profile ID: {p.get('id')}, User ID: {p.get('user_id')}, Target ID: {p.get('target_id')}")

print("\n--- ASSESSMENTS IN SNAPSHOT ---")
assessments = tables.get("assessments", [])
for a in assessments:
    print(f"Assessment ID: {a.get('id')}, User ID: {a.get('user_id')}, Type: {a.get('type')}, Status: {a.get('status')}, Score: {a.get('score')}, Started: {a.get('started_at')}, Completed: {a.get('completed_at')}")

print("\n--- STUDENT RESPONSES IN SNAPSHOT ---")
responses = tables.get("student_responses", [])
print(f"Total Student Responses in snapshot: {len(responses)}")
for r in responses[:15]:
    print(f"  Resp ID: {r.get('id')}, User ID: {r.get('user_id')}, Asmt ID: {r.get('assessment_id')}, Q ID: {r.get('question_id')}, Correct: {r.get('is_correct')}, Skipped: {r.get('skipped')}")

print("\n--- STUDENT MASTERY IN SNAPSHOT ---")
mastery = tables.get("student_mastery", [])
print(f"Total Student Mastery records: {len(mastery)}")
for m in mastery[:10]:
    print(f"  User ID: {m.get('user_id')}, Concept ID: {m.get('concept_id')}, Mastery: {m.get('mastery_score')}")

print("\n--- TOPIC PERFORMANCE IN SNAPSHOT ---")
topic_perf = tables.get("topic_performance", [])
print(f"Total Topic Performance records: {len(topic_perf)}")
for tp in topic_perf[:10]:
    print(f"  User ID: {tp.get('user_id')}, Topic ID: {tp.get('topic_id')}, Demonstrations: {tp.get('demonstrations_count')}")
