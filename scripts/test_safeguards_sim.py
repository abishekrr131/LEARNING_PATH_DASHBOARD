import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from collections import defaultdict
from scripts.migrate_to_production import normalize_stem, compute_stem_hash, classify_questions, fetch_local_eligible
import sqlite3

from database.seed.data.it_ml_engineer import TARGET as ML_ENG
from database.seed.data.it_full_stack import TARGET as FULL_STACK
from database.seed.data.it_cyber_security import TARGET as CYBER_SEC
from database.seed.data.it_genai import TARGET as GENAI
from database.seed.data.govt_upsc import TARGET as UPSC
from database.seed.data.govt_ssc_cgl import TARGET as SSC_CGL
from database.seed.data.govt_banking import TARGET as BANKING

prod_existing_stems = set()
prod_existing_hashes = set()
for t in [ML_ENG, FULL_STACK, CYBER_SEC, GENAI, UPSC, SSC_CGL, BANKING]:
    for q in t["questions"]:
        stem = q["text"].strip()
        prod_existing_stems.add(stem)
        prod_existing_hashes.add(compute_stem_hash(stem))

with open("database/seed/concepts_dump.json", "r", encoding="utf-8") as f:
    concepts = json.load(f)

prod_concept_map = {}
for c in concepts:
    key = (
        c["target_name"].strip().lower(),
        c["skill_name"].strip().lower(),
        c["topic_name"].strip().lower(),
        c["concept_name"].strip().lower(),
    )
    prod_concept_map[key] = c["concept_id"]

prod_targets = {k[0] for k in prod_concept_map.keys()}

local_qs = fetch_local_eligible("palp_local.db")

classified = classify_questions(
    local_qs, prod_concept_map, prod_existing_stems, prod_existing_hashes, prod_targets
)

print(f"Total evaluated: {len(local_qs)}")
print(f"Eligible: {len(classified['eligible'])}")
print(f"Exact duplicates (skipped): {len(classified['exact_duplicates'])}")
print(f"Normalized duplicates (skipped): {len(classified['normalized_duplicates'])}")
print(f"Unmapped concept: {len(classified['unmapped_concept'])}")
print(f"Unmapped target: {len(classified['unmapped_target'])}")
print(f"Invalid: {len(classified['invalid'])}")

by_target = defaultdict(int)
for e in classified["eligible"]:
    by_target[e["target"]] += 1

print("\nEligible by target:")
for t, c in sorted(by_target.items()):
    print(f"  {t}: {c}")
