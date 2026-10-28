import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.seed.data.it_ml_engineer import TARGET as ML_ENG
from database.seed.data.it_full_stack import TARGET as FULL_STACK
from database.seed.data.it_cyber_security import TARGET as CYBER_SEC
from database.seed.data.it_genai import TARGET as GENAI
from database.seed.data.govt_upsc import TARGET as UPSC
from database.seed.data.govt_ssc_cgl import TARGET as SSC_CGL
from database.seed.data.govt_banking import TARGET as BANKING
import sqlite3

# Collect all seed question stems (which is what is currently in production)
seed_stems = set()
for t in [ML_ENG, FULL_STACK, CYBER_SEC, GENAI, UPSC, SSC_CGL, BANKING]:
    for q in t["questions"]:
        seed_stems.add(q["text"].strip())

print(f"Total unique seed stems in python seed files: {len(seed_stems)}")

# Now check local SQLite
conn = sqlite3.connect("palp_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT q.id, q.question_text, q.source, q.review_status, ct.name as target_name, s.name as skill_name
    FROM questions q
    JOIN concepts c ON c.id = q.concept_id
    JOIN topics t ON t.id = c.topic_id
    JOIN skills s ON s.id = t.skill_id
    JOIN career_targets ct ON ct.id = s.target_id
""")
all_local = cur.fetchall()

in_seed = 0
not_in_seed = 0
approved_new = 0
unapproved = 0

by_target_new = {}
by_target_existing = {}

for r in all_local:
    stem = r["question_text"].strip()
    target = r["target_name"]
    is_seed = stem in seed_stems
    if is_seed:
        in_seed += 1
        by_target_existing[target] = by_target_existing.get(target, 0) + 1
    else:
        not_in_seed += 1
        if r["review_status"] == "approved" and r["source"] not in ("ai_generated", "gemini"):
            approved_new += 1
            by_target_new[target] = by_target_new.get(target, 0) + 1
        else:
            unapproved += 1

print(f"\nLocal questions matching existing seed: {in_seed}")
print(f"Local questions not in existing seed: {not_in_seed}")
print(f"  - Eligible approved new additions: {approved_new}")
print(f"  - Excluded (unapproved / AI): {unapproved}")

print("\nBreakdown by Target:")
for t in sorted(set(list(by_target_existing.keys()) + list(by_target_new.keys()))):
    ext = by_target_existing.get(t, 0)
    nw = by_target_new.get(t, 0)
    print(f"  {t:<35} | existing_in_seed={ext:>4} | new_approved_to_add={nw:>4} | total_after_import={ext+nw:>5}")

conn.close()
