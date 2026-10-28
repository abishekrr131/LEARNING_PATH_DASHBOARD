"""
Idempotent, transactional migration script: local SQLite -> production PostgreSQL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIGRATION_TAG = "PALP_MIGRATION_20261027_V1"


def normalize_stem(text: str) -> str:
    """
    Documented Question Stem Normalization:
    1. Strip leading and trailing whitespace.
    2. Normalize internal repeated whitespace, tabs, and newlines to a single space.
    3. Lowercase all characters.
    4. Normalize common typography: curly quotes -> straight quotes, em/en-dashes -> hyphens.
    """
    if not text:
        return ""
    t = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u2014", "-").replace("\u2013", "-")
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def compute_stem_hash(text: str) -> str:
    """Computes SHA-256 hash of the normalized stem."""
    return hashlib.sha256(normalize_stem(text).encode("utf-8")).hexdigest()


def validate_production_connection_string(url: str, allow_local_for_testing: bool = False) -> tuple[bool, str]:
    if not url:
        return False, "DATABASE_URL environment variable is empty."

    url_lower = url.lower()
    if "sqlite" in url_lower:
        return False, "SAFETY VIOLATION: DATABASE_URL points to SQLite. Migration must target PostgreSQL."

    if not (url_lower.startswith("postgresql://") or url_lower.startswith("postgresql+psycopg://") or url_lower.startswith("postgresql+psycopg2://")):
        return False, "Invalid scheme in DATABASE_URL. Must start with postgresql:// or postgresql+psycopg://."

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        dbname = parsed.path.lstrip("/")
        username = parsed.username or ""

        if not allow_local_for_testing and hostname in ("localhost", "127.0.0.1", "::1"):
            return False, (
                "SAFETY GUARD: DATABASE_URL points to localhost (127.0.0.1).\n"
                "To target Render production PostgreSQL, provide the production Render connection string\n"
                "(from Render Dashboard -> PostgreSQL -> Connect -> External Connection String)."
            )

        masked_host = hostname[:4] + "***" + hostname[-6:] if len(hostname) > 10 else "***"
        return True, f"Host: {masked_host} | Database: {dbname} | User: {username}"
    except Exception as exc:
        return False, f"Could not parse DATABASE_URL: {exc}"


def build_prod_concept_map(prod_engine) -> dict[tuple, int]:
    import sqlalchemy as sa

    prod_map = {}
    with prod_engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT ct.name as target_name,
                   sk.name as skill_name,
                   t.name  as topic_name,
                   c.name  as concept_name,
                   c.id    as prod_concept_id
            FROM concepts c
            JOIN topics t  ON t.id  = c.topic_id
            JOIN skills sk ON sk.id = t.skill_id
            JOIN career_targets ct ON ct.id = sk.target_id
        """))
        for r in rows:
            key = (
                r.target_name.strip().lower(),
                r.skill_name.strip().lower(),
                r.topic_name.strip().lower(),
                r.concept_name.strip().lower(),
            )
            prod_map[key] = r.prod_concept_id
    return prod_map


def get_prod_stems_and_hashes(prod_engine) -> tuple[set[str], set[str]]:
    """Returns (set of raw stripped stems, set of normalized stem hashes) already in production."""
    import sqlalchemy as sa

    raw_stems = set()
    hashes = set()
    with prod_engine.connect() as conn:
        rows = conn.execute(sa.text("SELECT question_text FROM questions"))
        for r in rows:
            if r[0]:
                raw_stems.add(r[0].strip())
                hashes.add(compute_stem_hash(r[0]))
    return raw_stems, hashes


def fetch_local_eligible(local_db_path: str, target_filter: str | None = None) -> list[dict]:
    conn = sqlite3.connect(local_db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    target_clause = ""
    params: list = []
    if target_filter:
        target_clause = "AND ct.name = ?"
        params.append(target_filter)

    cur.execute(f"""
        SELECT q.id as local_id,
               q.question_text, q.options_json, q.correct_answer,
               q.explanation, q.difficulty_hint, q.source,
               q.source_title, q.source_url, q.license, q.verified,
               c.name as concept_name,
               t.name as topic_name,
               s.name as skill_name,
               ct.name as target_name,
               ct.id   as local_target_id
        FROM questions q
        JOIN concepts c ON c.id = q.concept_id
        JOIN topics t   ON t.id = c.topic_id
        JOIN skills s   ON s.id = t.skill_id
        JOIN career_targets ct ON ct.id = s.target_id
        WHERE q.review_status = 'approved'
          AND q.source NOT IN ('ai_generated', 'gemini')
          AND TRIM(q.question_text) != ''
          AND q.correct_answer IN ('A','B','C','D')
          AND q.options_json IS NOT NULL
          {target_clause}
        ORDER BY ct.id, s.id, t.id, c.id, q.id
    """, params)

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def classify_questions(
    local_questions: list[dict],
    prod_concept_map: dict[tuple, int],
    prod_existing_stems: set[str],
    prod_existing_hashes: set[str],
    prod_targets: set[str],
) -> dict:
    eligible = []
    exact_duplicates = []
    normalized_duplicates = []
    unmapped_concept = []
    unmapped_target = []
    invalid = []

    seen_batch_hashes = set()

    for q in local_questions:
        target_key = q["target_name"].strip().lower()
        stem = q["question_text"].strip()
        stem_norm_hash = compute_stem_hash(stem)

        if not stem:
            invalid.append({**q, "reason": "empty question stem"})
            continue

        try:
            options = json.loads(q["options_json"]) if isinstance(q["options_json"], str) else q["options_json"]
        except Exception:
            invalid.append({**q, "reason": "malformed options_json"})
            continue

        if not isinstance(options, dict) or not {"A", "B", "C", "D"}.issubset(set(options.keys())):
            invalid.append({**q, "reason": "options missing required keys A, B, C, D"})
            continue

        if q["correct_answer"] not in ("A", "B", "C", "D"):
            invalid.append({**q, "reason": f"invalid correct_answer: {q['correct_answer']}"})
            continue

        if target_key not in prod_targets:
            unmapped_target.append({"local_id": q["local_id"], "target": q["target_name"]})
            continue

        concept_key = (
            target_key,
            q["skill_name"].strip().lower(),
            q["topic_name"].strip().lower(),
            q["concept_name"].strip().lower(),
        )
        prod_concept_id = prod_concept_map.get(concept_key)
        if prod_concept_id is None:
            unmapped_concept.append({
                "local_id": q["local_id"],
                "target": q["target_name"],
                "skill": q["skill_name"],
                "topic": q["topic_name"],
                "concept": q["concept_name"],
            })
            continue

        # Check exact and normalized duplicates
        if stem in prod_existing_stems:
            exact_duplicates.append({
                "local_id": q["local_id"],
                "stem_preview": stem[:90],
                "target": q["target_name"],
                "concept": q["concept_name"],
                "match_type": "exact_match",
            })
            continue

        if stem_norm_hash in prod_existing_hashes:
            normalized_duplicates.append({
                "local_id": q["local_id"],
                "stem_preview": stem[:90],
                "target": q["target_name"],
                "concept": q["concept_name"],
                "match_type": "normalized_whitespace_case_match",
            })
            continue

        if stem_norm_hash in seen_batch_hashes:
            normalized_duplicates.append({
                "local_id": q["local_id"],
                "stem_preview": stem[:90],
                "target": q["target_name"],
                "concept": q["concept_name"],
                "match_type": "duplicate_within_batch",
            })
            continue

        seen_batch_hashes.add(stem_norm_hash)

        eligible.append({
            "local_id": q["local_id"],
            "prod_concept_id": prod_concept_id,
            "target": q["target_name"],
            "skill": q["skill_name"],
            "topic": q["topic_name"],
            "concept": q["concept_name"],
            "question_text": stem,
            "options_json": options,  # Native Python dictionary - SQLAlchemy handles JSON/JSONB binding cleanly
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation"] or "",
            "difficulty_hint": float(q["difficulty_hint"] or 0.0),
            "source": "imported",
            "source_title": q.get("source_title") or "",
            "source_url": q.get("source_url") or "",
            "license": q.get("license") or "CC-BY-4.0",
            "exam_year": MIGRATION_TAG,  # Unique migration tag for precise rollback
            "review_status": "approved",
            "needs_human_review": False,
            "verified": bool(q.get("verified", True)),
        })

    return {
        "eligible": eligible,
        "exact_duplicates": exact_duplicates,
        "normalized_duplicates": normalized_duplicates,
        "unmapped_concept": unmapped_concept,
        "unmapped_target": unmapped_target,
        "invalid": invalid,
    }


def get_options_json_col_type(engine):
    """Detects whether production questions.options_json column is JSON or JSONB."""
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql
    if engine.dialect.name == "postgresql":
        try:
            with engine.connect() as conn:
                row = conn.execute(sa.text("""
                    SELECT udt_name FROM information_schema.columns 
                    WHERE table_name = 'questions' AND column_name = 'options_json'
                """)).fetchone()
                if row and row[0].lower() == "jsonb":
                    return postgresql.JSONB
        except Exception:
            pass
    return sa.JSON


def execute_migration(prod_engine, eligible: list[dict], batch_size: int = 500, dry_run: bool = True) -> dict:
    import sqlalchemy as sa
    from backend.app.models.core import Question

    if dry_run:
        return {
            "mode": "DRY_RUN",
            "would_insert": len(eligible),
            "batches": (len(eligible) + batch_size - 1) // batch_size,
            "success": True,
        }

    inserted = 0
    skipped_dups = 0
    failed_batches = 0
    errors = []
    inserted_ids = []

    total_batches = (len(eligible) + batch_size - 1) // batch_size

    # Detect column type (JSON or JSONB) dynamically to match production schema exactly
    json_col_type = get_options_json_col_type(prod_engine)

    # Prepare declarative insert statement
    insert_stmt = sa.insert(Question).values(
        concept_id=sa.bindparam("concept_id"),
        question_text=sa.bindparam("question_text"),
        options_json=sa.bindparam("options_json", type_=json_col_type),
        correct_answer=sa.bindparam("correct_answer"),
        explanation=sa.bindparam("explanation"),
        difficulty_hint=sa.bindparam("difficulty_hint"),
        source=sa.bindparam("source"),
        source_title=sa.bindparam("source_title"),
        source_url=sa.bindparam("source_url"),
        license=sa.bindparam("license"),
        exam_year=sa.bindparam("exam_year"),
        review_status=sa.bindparam("review_status"),
        needs_human_review=sa.bindparam("needs_human_review"),
        verified=sa.bindparam("verified"),
    )

    for batch_idx in range(total_batches):
        batch_start = batch_idx * batch_size
        batch = eligible[batch_start : batch_start + batch_size]
        batch_num = batch_idx + 1

        try:
            with prod_engine.begin() as conn:
                # Filter out any questions that already exist (in-transaction idempotency guard)
                items_to_insert = []
                for q in batch:
                    existing = conn.execute(
                        sa.text("SELECT id FROM questions WHERE question_text = :stem LIMIT 1"),
                        {"stem": q["question_text"]}
                    ).fetchone()
                    if existing:
                        skipped_dups += 1
                        continue

                    items_to_insert.append({
                        "concept_id": q["prod_concept_id"],
                        "question_text": q["question_text"],
                        "options_json": q["options_json"],
                        "correct_answer": q["correct_answer"],
                        "explanation": q["explanation"],
                        "difficulty_hint": q["difficulty_hint"],
                        "source": q["source"],
                        "source_title": q["source_title"],
                        "source_url": q["source_url"],
                        "license": q["license"],
                        "exam_year": q["exam_year"],
                        "review_status": q["review_status"],
                        "needs_human_review": q["needs_human_review"],
                        "verified": q["verified"],
                    })

                if items_to_insert:
                    conn.execute(insert_stmt, items_to_insert)
                    inserted += len(items_to_insert)

            print(f"  [OK] Batch {batch_num}/{total_batches} committed ({len(batch)} items, total inserted={inserted})")
        except Exception as exc:
            failed_batches += 1
            err_msg = f"Batch {batch_num} failed and was rolled back: {exc}"
            print(f"  [FAIL] {err_msg}")
            errors.append(err_msg)
            # Break immediately on batch failure to prevent uncontrolled partial state
            break

    success = (failed_batches == 0 and inserted > 0)
    return {
        "mode": "EXECUTE",
        "inserted": inserted,
        "skipped_already_exists": skipped_dups,
        "failed_batches": failed_batches,
        "errors": errors,
        "success": success,
    }


def execute_rollback(prod_engine) -> dict:
    """
    Precision Rollback:
    Deletes ONLY rows tagged with MIGRATION_TAG and source = 'imported'.
    Never deletes any row where exam_year != MIGRATION_TAG or source != 'imported'.
    """
    import sqlalchemy as sa

    with prod_engine.begin() as conn:
        matching = conn.execute(
            sa.text("SELECT COUNT(*) FROM questions WHERE exam_year = :tag AND source = 'imported'"),
            {"tag": MIGRATION_TAG}
        ).scalar()

        if matching == 0:
            print(f"No records found with migration tag '{MIGRATION_TAG}'. Nothing to rollback.")
            return {"deleted": 0}

        res = conn.execute(
            sa.text("DELETE FROM questions WHERE exam_year = :tag AND source = 'imported' RETURNING id"),
            {"tag": MIGRATION_TAG}
        )
        deleted_count = len(res.fetchall())
        print(f"Successfully rolled back {deleted_count} rows tagged with '{MIGRATION_TAG}'.")
        return {"deleted": deleted_count}


def check_practice_sufficiency(prod_engine, classified: dict) -> list[dict]:
    import sqlalchemy as sa

    by_skill_addition = defaultdict(int)
    for e in classified["eligible"]:
        by_skill_addition[(e["target"], e["skill"])] += 1

    with prod_engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT ct.name as target, sk.name as skill,
                   COUNT(q.id) as total,
                   SUM(CASE WHEN q.review_status='approved' THEN 1 ELSE 0 END) as approved
            FROM skills sk
            JOIN career_targets ct ON ct.id = sk.target_id
            LEFT JOIN topics t ON t.skill_id = sk.id
            LEFT JOIN concepts c ON c.topic_id = t.id
            LEFT JOIN questions q ON q.concept_id = c.id
            GROUP BY ct.name, sk.name
            ORDER BY ct.name, sk.name
        """))
        skill_rows = [dict(r._mapping) for r in rows]

    results_by_target = defaultdict(list)
    for sr in skill_rows:
        addition = by_skill_addition.get((sr["target"], sr["skill"]), 0)
        current = sr.get("approved") or 0
        projected = current + addition
        results_by_target[sr["target"]].append({
            "skill": sr["skill"],
            "current_approved": current,
            "will_add": addition,
            "projected": projected,
            "sufficient_for_practice_10": projected >= 10,
        })

    summary = []
    for target, skills in sorted(results_by_target.items()):
        proj_total = sum(s["projected"] for s in skills)
        summary.append({
            "target": target,
            "skills": skills,
            "projected_total": proj_total,
            "diagnostic_sufficient": proj_total >= 10,
            "practice_combined_sufficient": all(s["sufficient_for_practice_10"] for s in skills),
        })
    return summary


def main():
    parser = argparse.ArgumentParser(description="Safely migrate PALP local questions to production PostgreSQL.")
    parser.add_argument("--execute", action="store_true", help="Execute writes to production (requires approval)")
    parser.add_argument("--rollback", action="store_true", help="Precision rollback of rows inserted by this migration")
    parser.add_argument("--target", type=str, default=None, help="Migrate only a specific career target")
    parser.add_argument("--batch", type=int, default=500, help="Batch size per transaction (default: 500)")
    parser.add_argument("--out", type=str, default=None, help="Path for JSON output summary")
    parser.add_argument("--allow-local", action="store_true", help="Allow localhost database for local end-to-end testing")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL", "")

    valid, msg = validate_production_connection_string(database_url, allow_local_for_testing=args.allow_local)
    if not valid:
        print(f"\n[!] CONNECTION SAFETY REJECTION:\n    {msg}\n")
        sys.exit(1)

    import sqlalchemy as sa
    engine_url = database_url
    if engine_url.startswith("postgresql://"):
        try:
            import psycopg
            engine_url = engine_url.replace("postgresql://", "postgresql+psycopg://", 1)
        except ImportError:
            engine_url = engine_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    prod_engine = sa.create_engine(engine_url, connect_args={"connect_timeout": 15})

    if args.rollback:
        print("\n" + "="*70)
        print("  PALP DATABASE MIGRATION -- PRECISION ROLLBACK MODE")
        print(f"  Target: {msg}")
        print(f"  Manifest Tag: {MIGRATION_TAG}")
        print("="*70)
        confirm = input(f"Type 'ROLLBACK' to delete only rows tagged '{MIGRATION_TAG}': ")
        if confirm.strip() != "ROLLBACK":
            print("Rollback aborted.")
            sys.exit(0)
        execute_rollback(prod_engine)
        return

    dry_run = not args.execute

    print("\n" + "="*70)
    print(f"  PALP DATABASE MIGRATION -- {'DRY RUN (0 writes)' if dry_run else 'EXECUTE MODE'}")
    print(f"  Target: {msg}")
    print(f"  Manifest Tag: {MIGRATION_TAG}")
    print("="*70)

    if not dry_run:
        confirm = input("\n[CAUTION] You are about to perform real inserts on PostgreSQL.\nType 'CONFIRM' to proceed: ")
        if confirm.strip() != "CONFIRM":
            print("Aborted by user.")
            sys.exit(0)

    local_db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "palp_local.db",
    )

    print("\n[1/5] Verifying connection to production database...")
    try:
        with prod_engine.connect() as conn:
            cnt = conn.execute(sa.text("SELECT COUNT(*) FROM questions")).scalar()
            t_cnt = conn.execute(sa.text("SELECT COUNT(*) FROM career_targets")).scalar()
            c_cnt = conn.execute(sa.text("SELECT COUNT(*) FROM concepts")).scalar()
        print(f"      Connection verified! Current counts: {t_cnt} targets, {c_cnt} concepts, {cnt} questions.")
    except Exception as exc:
        print(f"      CONNECTION ERROR: {exc}")
        sys.exit(1)

    print("\n[2/5] Building production natural-key concept map...")
    prod_concept_map = build_prod_concept_map(prod_engine)
    print(f"      {len(prod_concept_map)} concepts mapped from production.")

    print("\n[3/5] Fetching existing production question stems & normalized hashes...")
    prod_existing_stems, prod_existing_hashes = get_prod_stems_and_hashes(prod_engine)
    print(f"      {len(prod_existing_stems)} question stems retrieved for exact and normalized deduplication.")

    print("\n[4/5] Reading local SQLite questions (filter: review_status='approved', non-AI)...")
    local_questions = fetch_local_eligible(local_db_path, target_filter=args.target)
    print(f"      {len(local_questions)} eligible candidate questions loaded from palp_local.db.")

    prod_targets = {k[0] for k in prod_concept_map.keys()}

    print("\n[5/5] Classifying candidates with multi-stage deduplication...")
    classified = classify_questions(
        local_questions, prod_concept_map, prod_existing_stems, prod_existing_hashes, prod_targets
    )

    print("\n" + "="*70)
    print("  AUDIT & DRY-RUN CLASSIFICATION SUMMARY")
    print("="*70)
    print(f"  Local approved candidates evaluated : {len(local_questions):>6}")
    print(f"  ELIGIBLE for new insertion          : {len(classified['eligible']):>6}")
    print(f"  Exact duplicates (skipped)          : {len(classified['exact_duplicates']):>6}")
    print(f"  Normalized duplicates (skipped)     : {len(classified['normalized_duplicates']):>6}")
    print(f"  Unmapped concepts                   : {len(classified['unmapped_concept']):>6}")
    print(f"  Unmapped targets                    : {len(classified['unmapped_target']):>6}")
    print(f"  Invalid / malformed items           : {len(classified['invalid']):>6}")

    by_target = defaultdict(int)
    for e in classified["eligible"]:
        by_target[e["target"]] += 1

    print("\n  Proposed additions by Target:")
    for target_name, count in sorted(by_target.items()):
        print(f"    - {target_name:<40} +{count:>5}")

    print("\n  Checking practice mode sufficiency...")
    sufficiency = check_practice_sufficiency(prod_engine, classified)
    for s in sufficiency:
        diag = "PASS" if s["diagnostic_sufficient"] else "FAIL"
        comb = "PASS" if s["practice_combined_sufficient"] else "FAIL"
        print(f"    - {s['target']:<35} | Diagnostic: {diag} | Combined Test: {comb} (Projected: {s['projected_total']})")

    out_file = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "exports", "migration_manifest_dry_run.json"
    )
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    manifest_data = {
        "migration_tag": MIGRATION_TAG,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dry_run": dry_run,
        "eligible_count": len(classified["eligible"]),
        "exact_duplicates": len(classified["exact_duplicates"]),
        "normalized_duplicates": len(classified["normalized_duplicates"]),
        "unmapped_concept_count": len(classified["unmapped_concept"]),
        "unmapped_target_count": len(classified["unmapped_target"]),
        "invalid_count": len(classified["invalid"]),
        "by_target": dict(by_target),
        "manifest_sample": [
            {
                "local_id": e["local_id"],
                "target": e["target"],
                "concept": e["concept"],
                "stem_hash": compute_stem_hash(e["question_text"]),
                "exam_year_tag": e["exam_year"],
            }
            for e in classified["eligible"][:10]
        ],
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, default=str)
    print(f"\n  Migration manifest written to: {out_file}")

    if not dry_run:
        print(f"\n[MIGRATION EXECUTE] Processing {len(classified['eligible'])} questions in batches of {args.batch}...")
        result = execute_migration(prod_engine, classified["eligible"], batch_size=args.batch, dry_run=False)
        print("\n" + "="*70)
        print("  MIGRATION EXECUTION SUMMARY")
        print("="*70)
        print(f"  Successfully inserted : {result['inserted']}")
        print(f"  Duplicates skipped    : {result['skipped_already_exists']}")
        print(f"  Failed batches        : {result['failed_batches']}")
        if result["errors"]:
            print(f"  Errors encountered    : {len(result['errors'])}")
            for err in result["errors"]:
                print(f"    - {err}")
            print("\n[!] MIGRATION FAILED -- Partial state halted cleanly.")
            sys.exit(1)
        else:
            print(f"\n[OK] MIGRATION SUCCEEDED -- {result['inserted']} questions active in production.")
    else:
        print("\n" + "="*70)
        print("  DRY-RUN COMPLETE -- Zero database records modified.")
        print("="*70)


if __name__ == "__main__":
    main()
