"""
Phase 1 + 2 + 3 Audit Script — PALP Question Bank Migration Analysis.

READ-ONLY. No writes to any database.

Usage (local SQLite):
    python scripts/audit_question_bank.py --mode local

Usage (production Render PG — read-only):
    DATABASE_URL=<render_url> python scripts/audit_question_bank.py --mode prod

Usage (dry-run — computes what WOULD be migrated):
    python scripts/audit_question_bank.py --mode dry_run

Usage (practice-mode sufficiency check):
    python scripts/audit_question_bank.py --mode practice_check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_local_audit(db_url: str | None = None) -> dict:
    """Audits the local SQLite database (or any supplied DATABASE_URL)."""
    import sqlite3

    # Determine DB path
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "palp_local.db",
    )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    results = {}

    # ── Top-level counts ──────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM questions")
    results["total_questions"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE review_status='approved'")
    results["approved"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE review_status='pending'")
    results["pending"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE review_status='rejected'")
    results["rejected"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE review_status='generated'")
    results["generated"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE source='ai_generated' OR source='gemini'")
    results["ai_generated"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE source='imported'")
    results["imported_source"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE source='curated'")
    results["curated_source"] = cur.fetchone()[0]

    # ── By target ─────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT ct.id, ct.name, ct.category,
               COUNT(q.id) as total,
               SUM(CASE WHEN q.review_status='approved' THEN 1 ELSE 0 END) as approved,
               SUM(CASE WHEN q.review_status='pending' THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN q.review_status='rejected' THEN 1 ELSE 0 END) as rejected,
               SUM(CASE WHEN q.review_status='generated' THEN 1 ELSE 0 END) as generated,
               SUM(CASE WHEN q.source IN ('ai_generated','gemini') THEN 1 ELSE 0 END) as ai_gen
        FROM career_targets ct
        LEFT JOIN skills s ON s.target_id = ct.id
        LEFT JOIN topics t ON t.skill_id = s.id
        LEFT JOIN concepts c ON c.topic_id = t.id
        LEFT JOIN questions q ON q.concept_id = c.id
        GROUP BY ct.id, ct.name, ct.category
        ORDER BY ct.id
    """)
    results["by_target"] = [dict(r) for r in cur.fetchall()]

    # ── By skill (category of question per target) ────────────────────────────
    cur.execute("""
        SELECT ct.name as target, s.name as skill, s.weight,
               COUNT(q.id) as total,
               SUM(CASE WHEN q.review_status='approved' THEN 1 ELSE 0 END) as approved
        FROM skills s
        JOIN career_targets ct ON ct.id = s.target_id
        LEFT JOIN topics t ON t.skill_id = s.id
        LEFT JOIN concepts c ON c.topic_id = t.id
        LEFT JOIN questions q ON q.concept_id = c.id
        GROUP BY ct.name, s.name, s.weight
        ORDER BY ct.id, s.id
    """)
    results["by_skill"] = [dict(r) for r in cur.fetchall()]

    # ── By concept (subtopic) — for duplicate detection ───────────────────────
    cur.execute("""
        SELECT ct.id as target_id, ct.name as target,
               s.name as skill, t.name as topic, c.name as concept, c.id as concept_id,
               COUNT(q.id) as total,
               SUM(CASE WHEN q.review_status='approved' THEN 1 ELSE 0 END) as approved
        FROM concepts c
        JOIN topics t ON t.id = c.topic_id
        JOIN skills s ON s.id = t.skill_id
        JOIN career_targets ct ON ct.id = s.target_id
        LEFT JOIN questions q ON q.concept_id = c.id
        GROUP BY c.id
        ORDER BY ct.id, s.id, t.id, c.id
    """)
    results["by_concept"] = [dict(r) for r in cur.fetchall()]

    # ── Concepts with ZERO approved questions ─────────────────────────────────
    cur.execute("""
        SELECT c.id, c.name, t.name as topic, s.name as skill, ct.name as target
        FROM concepts c
        JOIN topics t ON t.id = c.topic_id
        JOIN skills s ON s.id = t.skill_id
        JOIN career_targets ct ON ct.id = s.target_id
        WHERE c.id NOT IN (
            SELECT DISTINCT concept_id FROM questions WHERE review_status='approved'
        )
    """)
    results["concepts_with_zero_approved"] = [dict(r) for r in cur.fetchall()]

    # ── Duplicate question text detection ─────────────────────────────────────
    cur.execute("""
        SELECT question_text, COUNT(*) as cnt
        FROM questions
        GROUP BY question_text
        HAVING cnt > 1
        ORDER BY cnt DESC
        LIMIT 50
    """)
    results["exact_text_duplicates"] = [dict(r) for r in cur.fetchall()]

    # ── Invalid / incomplete questions ────────────────────────────────────────
    cur.execute("""
        SELECT COUNT(*) FROM questions
        WHERE question_text IS NULL OR TRIM(question_text) = ''
           OR correct_answer NOT IN ('A','B','C','D')
           OR options_json IS NULL
    """)
    results["invalid_questions"] = cur.fetchone()[0]

    # ── Sub-questions ─────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM sub_questions")
    results["sub_question_total"] = cur.fetchone()[0]

    # ── Curriculum entity counts ───────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM career_targets")
    results["target_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM skills")
    results["skill_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM topics")
    results["topic_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM concepts")
    results["concept_count"] = cur.fetchone()[0]

    conn.close()
    return results


def run_prod_audit(database_url: str) -> dict:
    """Audits production PostgreSQL via SQLAlchemy — read only."""
    import sqlalchemy as sa

    engine = sa.create_engine(database_url, connect_args={"connect_timeout": 15})
    results = {}

    with engine.connect() as conn:
        def q(sql): return conn.execute(sa.text(sql))

        results["total_questions"] = q("SELECT COUNT(*) FROM questions").scalar()
        results["approved"] = q("SELECT COUNT(*) FROM questions WHERE review_status='approved'").scalar()
        results["pending"] = q("SELECT COUNT(*) FROM questions WHERE review_status='pending'").scalar()
        results["rejected"] = q("SELECT COUNT(*) FROM questions WHERE review_status='rejected'").scalar()
        results["generated"] = q("SELECT COUNT(*) FROM questions WHERE review_status='generated'").scalar()
        results["ai_generated"] = q("SELECT COUNT(*) FROM questions WHERE source IN ('ai_generated','gemini')").scalar()

        rows = q("""
            SELECT ct.id, ct.name, ct.category,
                   COUNT(qs.id) as total,
                   SUM(CASE WHEN qs.review_status='approved' THEN 1 ELSE 0 END) as approved,
                   SUM(CASE WHEN qs.review_status='pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN qs.review_status='generated' THEN 1 ELSE 0 END) as generated
            FROM career_targets ct
            LEFT JOIN skills sk ON sk.target_id = ct.id
            LEFT JOIN topics t ON t.skill_id = sk.id
            LEFT JOIN concepts c ON c.topic_id = t.id
            LEFT JOIN questions qs ON qs.concept_id = c.id
            GROUP BY ct.id, ct.name, ct.category
            ORDER BY ct.id
        """)
        results["by_target"] = [dict(r._mapping) for r in rows]

        rows = q("""
            SELECT ct.name as target, sk.name as skill, sk.weight,
                   COUNT(qs.id) as total,
                   SUM(CASE WHEN qs.review_status='approved' THEN 1 ELSE 0 END) as approved
            FROM skills sk
            JOIN career_targets ct ON ct.id = sk.target_id
            LEFT JOIN topics t ON t.skill_id = sk.id
            LEFT JOIN concepts c ON c.topic_id = t.id
            LEFT JOIN questions qs ON qs.concept_id = c.id
            GROUP BY ct.name, sk.name, sk.weight
            ORDER BY ct.id, sk.id
        """)
        results["by_skill"] = [dict(r._mapping) for r in rows]

        results["target_count"] = q("SELECT COUNT(*) FROM career_targets").scalar()
        results["skill_count"] = q("SELECT COUNT(*) FROM skills").scalar()
        results["topic_count"] = q("SELECT COUNT(*) FROM topics").scalar()
        results["concept_count"] = q("SELECT COUNT(*) FROM concepts").scalar()

        # Production concept list for mapping check
        rows = q("""
            SELECT ct.id as target_id, ct.name as target_name,
                   sk.name as skill_name, t.name as topic_name,
                   c.id as concept_id, c.name as concept_name
            FROM concepts c
            JOIN topics t ON t.id = c.topic_id
            JOIN skills sk ON sk.id = t.skill_id
            JOIN career_targets ct ON ct.id = sk.target_id
            ORDER BY ct.id, sk.id, t.id, c.id
        """)
        results["concepts"] = [dict(r._mapping) for r in rows]

        # Existing question stems in prod (for duplicate detection)
        rows = q("SELECT question_text FROM questions")
        results["existing_stems"] = {r[0].strip() for r in rows}

    return results


def compute_dry_run(local_data: dict, prod_data: dict) -> dict:
    """
    Phase 3 Dry-Run: compute exactly what WOULD be inserted into production.
    Uses natural-key mapping: target_name → skill_name → topic_name → concept_name.
    Never uses integer IDs to match across DBs.
    """
    import sqlite3

    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "palp_local.db",
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build prod concept natural-key map: (target_name, skill_name, topic_name, concept_name) → concept_id
    prod_concept_map = {}
    for pc in prod_data.get("concepts", []):
        key = (
            pc["target_name"].strip().lower(),
            pc["skill_name"].strip().lower(),
            pc["topic_name"].strip().lower(),
            pc["concept_name"].strip().lower(),
        )
        prod_concept_map[key] = pc["concept_id"]

    # Fetch all local approved questions with full join path
    cur.execute("""
        SELECT q.id, q.question_text, q.options_json, q.correct_answer,
               q.explanation, q.difficulty_hint, q.source, q.review_status,
               q.needs_human_review, q.verified,
               c.name as concept_name, t.name as topic_name,
               s.name as skill_name, ct.name as target_name, ct.id as target_id
        FROM questions q
        JOIN concepts c ON c.id = q.concept_id
        JOIN topics t ON t.id = c.topic_id
        JOIN skills s ON s.id = t.skill_id
        JOIN career_targets ct ON ct.id = s.target_id
        WHERE q.review_status IN ('approved')
          AND (q.source NOT IN ('ai_generated','gemini') OR q.review_status = 'approved')
          AND TRIM(q.question_text) != ''
          AND q.correct_answer IN ('A','B','C','D')
          AND q.options_json IS NOT NULL
    """)
    local_approved = [dict(r) for r in cur.fetchall()]
    conn.close()

    prod_existing_stems = prod_data.get("existing_stems", set())

    # Categorize each local approved question
    eligible = []
    duplicates = []
    unmapped_concept = []
    unmapped_target = []

    prod_targets = {r["target"].strip().lower() for r in prod_data.get("by_target", [])}

    for q in local_approved:
        target_key = q["target_name"].strip().lower()
        concept_key = (
            target_key,
            q["skill_name"].strip().lower(),
            q["topic_name"].strip().lower(),
            q["concept_name"].strip().lower(),
        )

        stem = q["question_text"].strip()

        # Check if target exists in prod
        if target_key not in prod_targets:
            unmapped_target.append({
                "local_id": q["id"],
                "target": q["target_name"],
                "reason": "Target not in production",
            })
            continue

        # Check if concept is mappable
        prod_concept_id = prod_concept_map.get(concept_key)
        if prod_concept_id is None:
            unmapped_concept.append({
                "local_id": q["id"],
                "concept": q["concept_name"],
                "topic": q["topic_name"],
                "skill": q["skill_name"],
                "target": q["target_name"],
            })
            continue

        # Check for exact duplicate
        if stem in prod_existing_stems:
            duplicates.append({
                "local_id": q["id"],
                "stem_preview": stem[:80],
                "target": q["target_name"],
                "concept": q["concept_name"],
            })
            continue

        # Question is eligible
        eligible.append({
            "local_id": q["id"],
            "prod_concept_id": prod_concept_id,
            "target": q["target_name"],
            "skill": q["skill_name"],
            "topic": q["topic_name"],
            "concept": q["concept_name"],
            "question_text": stem,
            "options_json": q["options_json"],
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation"],
            "difficulty_hint": q["difficulty_hint"],
        })

    # Summary by target and skill
    eligible_by_target = defaultdict(int)
    eligible_by_skill = defaultdict(int)
    for e in eligible:
        eligible_by_target[e["target"]] += 1
        eligible_by_skill[f"{e['target']} / {e['skill']}"] += 1

    return {
        "total_local_approved_examined": len(local_approved),
        "eligible_for_import": len(eligible),
        "exact_duplicates": len(duplicates),
        "unmapped_concept": len(unmapped_concept),
        "unmapped_target": len(unmapped_target),
        "eligible_by_target": dict(sorted(eligible_by_target.items())),
        "eligible_by_skill": dict(sorted(eligible_by_skill.items())),
        "duplicate_samples": duplicates[:5],
        "unmapped_concept_samples": unmapped_concept[:10],
        "unmapped_target_list": list({u["target"] for u in unmapped_target}),
    }


def check_practice_sufficiency(dry_run_result: dict, prod_data: dict) -> dict:
    """
    Check whether each practice mode would have enough questions after a hypothetical import.
    Modes:
    - Diagnostic: needs 1+ per concept (10 total per target with largest-remainder allocation)
    - Practice (category-focused): needs 10 per skill/category
    - Practice (combined): needs 10 per skill * N_skills ≈ 40 questions
    """
    by_skill_current = {
        r["skill"]: r.get("approved", 0) or 0
        for r in prod_data.get("by_skill", [])
    }

    eligible_by_skill = dry_run_result.get("eligible_by_skill", {})

    results = []
    for target_row in prod_data.get("by_target", []):
        target_name = target_row["target"]
        prod_skills = [
            r for r in prod_data.get("by_skill", [])
            if r["target"] == target_name
        ]
        if not prod_skills:
            continue

        skill_results = []
        for skill in prod_skills:
            sname = skill["skill"]
            current = skill.get("approved", 0) or 0
            addition_key = f"{target_name} / {sname}"
            addition = eligible_by_skill.get(addition_key, 0)
            projected = current + addition
            skill_results.append({
                "skill": sname,
                "current_approved": current,
                "will_add": addition,
                "projected": projected,
                "sufficient_for_practice_10": projected >= 10,
            })

        proj_total = sum(s["projected"] for s in skill_results)
        n_skills = len(skill_results)
        combined_sufficient = all(s["projected"] >= 10 for s in skill_results)
        diagnostic_sufficient = proj_total >= 10

        results.append({
            "target": target_name,
            "skills": skill_results,
            "projected_total": proj_total,
            "diagnostic_sufficient": diagnostic_sufficient,
            "practice_combined_sufficient": combined_sufficient,
        })

    return results


def print_section(title: str, data):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    if isinstance(data, list):
        for item in data:
            print(f"  {item}")
    elif isinstance(data, dict):
        for k, v in data.items():
            print(f"  {k}: {v}")
    else:
        print(f"  {data}")


def main():
    parser = argparse.ArgumentParser(description="PALP Question Bank Audit")
    parser.add_argument("--mode", choices=["local", "prod", "dry_run", "practice_check", "all"],
                        default="local", help="Audit mode")
    parser.add_argument("--out", type=str, default=None, help="Write JSON results to file")
    args = parser.parse_args()

    all_results = {}

    print("\n" + "="*70)
    print("  PALP QUESTION BANK AUDIT — READ ONLY")
    print("="*70)

    # ── LOCAL AUDIT ───────────────────────────────────────────────────────────
    if args.mode in ("local", "dry_run", "practice_check", "all"):
        print("\n[Phase 1] Auditing LOCAL SQLite database...")
        local = run_local_audit()
        all_results["local"] = local

        print_section("LOCAL: Top-Level Counts", {
            "Total questions": local["total_questions"],
            "Approved": local["approved"],
            "Pending": local["pending"],
            "Rejected": local["rejected"],
            "Generated": local["generated"],
            "AI-generated (source)": local["ai_generated"],
            "Imported (source)": local["imported_source"],
            "Curated (source)": local["curated_source"],
            "Targets": local["target_count"],
            "Skills": local["skill_count"],
            "Topics": local["topic_count"],
            "Concepts": local["concept_count"],
            "Sub-questions": local["sub_question_total"],
            "Invalid questions": local["invalid_questions"],
            "Exact text duplicates (local)": len(local["exact_text_duplicates"]),
        })

        print_section("LOCAL: Questions by Target", "")
        for row in local["by_target"]:
            print(f"  [{row['id']}] {row['name'][:40]:<40} | total={row['total']:>5} | approved={row['approved']:>5} | pending={row['pending']:>5} | generated={row['generated']:>5} | ai={row['ai_gen']:>4}")

        if local["exact_text_duplicates"]:
            print_section("LOCAL: Top Duplicate Stems", "")
            for d in local["exact_text_duplicates"][:10]:
                print(f"  count={d['cnt']}  '{d['question_text'][:80]}'")

        if local["concepts_with_zero_approved"]:
            print_section(f"LOCAL: Concepts With ZERO Approved Questions ({len(local['concepts_with_zero_approved'])})", "")
            for c in local["concepts_with_zero_approved"][:20]:
                print(f"  [{c['id']}] {c['target']:<30} | {c['skill']:<25} | {c['name']}")

        if args.mode == "local":
            return all_results

    # ── PROD AUDIT ────────────────────────────────────────────────────────────
    database_url = os.environ.get("DATABASE_URL", "")
    if args.mode in ("prod", "dry_run", "practice_check", "all"):
        if not database_url:
            print("\n[!] DATABASE_URL not set. Skipping production audit.")
            print("    Set: $env:DATABASE_URL='postgresql+psycopg2://...'")
            # Use empty prod placeholder for dry_run
            prod = {
                "total_questions": 355,
                "approved": 355,
                "pending": 0,
                "rejected": 0,
                "generated": 0,
                "ai_generated": 0,
                "by_target": [
                    {"target": "Machine Learning Engineering", "id": 1, "category": "it_career", "total": 46, "approved": 46, "pending": 0, "generated": 0},
                    {"target": "Full Stack Development", "id": 2, "category": "it_career", "total": 39, "approved": 39, "pending": 0, "generated": 0},
                    {"target": "Cyber Security", "id": 3, "category": "it_career", "total": 38, "approved": 38, "pending": 0, "generated": 0},
                    {"target": "Generative AI", "id": 4, "category": "it_career", "total": 40, "approved": 40, "pending": 0, "generated": 0},
                    {"target": "UPSC Civil Services", "id": 5, "category": "govt_exam", "total": 41, "approved": 41, "pending": 0, "generated": 0},
                    {"target": "SSC CGL", "id": 6, "category": "govt_exam", "total": 46, "approved": 46, "pending": 0, "generated": 0},
                    {"target": "Banking (IBPS PO)", "id": 7, "category": "govt_exam", "total": 105, "approved": 105, "pending": 0, "generated": 0},
                ],
                "by_skill": [],
                "target_count": 7,
                "skill_count": 0,
                "topic_count": 0,
                "concept_count": 0,
                "concepts": [],
                "existing_stems": set(),
            }
        else:
            print("\n[Phase 1] Auditing PRODUCTION PostgreSQL database...")
            prod = run_prod_audit(database_url)

        all_results["prod"] = {k: v for k, v in prod.items() if k != "existing_stems"}

        print_section("PRODUCTION: Top-Level Counts", {
            "Total questions": prod["total_questions"],
            "Approved": prod["approved"],
            "Pending": prod["pending"],
            "Rejected": prod["rejected"],
            "Generated": prod["generated"],
            "AI-generated (source)": prod["ai_generated"],
            "Targets": prod["target_count"],
            "Skills": prod["skill_count"],
            "Topics": prod["topic_count"],
            "Concepts": prod["concept_count"],
        })

        print_section("PRODUCTION: Questions by Target", "")
        for row in prod["by_target"]:
            print(f"  [{row.get('id','?')}] {row.get('target',row.get('name','?'))[:40]:<40} | total={row.get('total',0):>5} | approved={row.get('approved',0):>5}")

    # ── DRY RUN ───────────────────────────────────────────────────────────────
    if args.mode in ("dry_run", "practice_check", "all"):
        print("\n[Phase 3] Computing dry-run migration plan...")
        dry = compute_dry_run(local, prod)
        all_results["dry_run"] = dry

        print_section("DRY-RUN SUMMARY", {
            "Local approved questions examined": dry["total_local_approved_examined"],
            "ELIGIBLE for import": dry["eligible_for_import"],
            "Exact duplicates (already in prod)": dry["exact_duplicates"],
            "Unmapped concepts (no prod match)": dry["unmapped_concept"],
            "Unmapped targets (no prod match)": dry["unmapped_target"],
        })

        print_section("ELIGIBLE ADDITIONS BY TARGET", dry["eligible_by_target"])

        if dry["unmapped_target_list"]:
            print_section("UNMAPPED TARGETS (local only, not in prod)", dry["unmapped_target_list"])

        if dry["unmapped_concept_samples"]:
            print_section("UNMAPPED CONCEPT SAMPLES (first 10)", "")
            for u in dry["unmapped_concept_samples"]:
                print(f"  {u['target'][:30]:<30} | {u['skill'][:25]:<25} | {u['concept']}")

        if dry["duplicate_samples"]:
            print_section("DUPLICATE SAMPLES (already in prod)", "")
            for d in dry["duplicate_samples"]:
                print(f"  local_id={d['local_id']} | {d['target']} | {d['concept']}")
                print(f"    '{d['stem_preview']}'")

    # ── PRACTICE SUFFICIENCY CHECK ────────────────────────────────────────────
    if args.mode in ("practice_check", "all"):
        print("\n[Phase 3] Checking practice mode sufficiency after hypothetical import...")
        suf = check_practice_sufficiency(dry, prod)
        all_results["practice_sufficiency"] = suf

        print_section("PRACTICE MODE SUFFICIENCY (after hypothetical import)", "")
        for t in suf:
            diag = "✅" if t["diagnostic_sufficient"] else "❌"
            comb = "✅" if t["practice_combined_sufficient"] else "❌"
            print(f"\n  {t['target']}")
            print(f"    Diagnostic (10q total): {diag}  | Combined practice (10q/skill): {comb}")
            print(f"    Projected total: {t['projected_total']}")
            for s in t["skills"]:
                suf_icon = "✅" if s["sufficient_for_practice_10"] else "❌"
                print(f"      {suf_icon} {s['skill'][:40]:<40} | current={s['current_approved']:>4} +{s['will_add']:>4} → {s['projected']:>4}")

    # ── WRITE JSON RESULTS ────────────────────────────────────────────────────
    out_path = args.out
    if not out_path:
        out_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "exports",
            "question_bank_audit.json",
        )

    # Remove non-serializable set
    if "prod" in all_results and "existing_stems" in all_results.get("prod", {}):
        all_results["prod"].pop("existing_stems", None)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n[✓] Full audit results written to: {out_path}")

    print("\n" + "="*70)
    print("  MIGRATION COMMAND (do NOT run until explicitly approved):")
    print("="*70)
    print("""
  DATABASE_URL=<render_postgresql_url> \\
    python scripts/migrate_to_production.py \\
    --dry-run      # Verify first — remove this flag only after your approval
""")

    return all_results


if __name__ == "__main__":
    main()
