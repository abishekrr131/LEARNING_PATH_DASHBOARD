"""Detailed by-skill and concept breakdown of local SQLite — READ ONLY."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "palp_local.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT ct.id as tid, ct.name as target, s.name as skill, s.weight,
           COUNT(q.id) as total,
           SUM(CASE WHEN q.review_status='approved' THEN 1 ELSE 0 END) as approved,
           SUM(CASE WHEN q.source IN ('ai_generated','gemini') THEN 1 ELSE 0 END) as ai_gen
    FROM skills s
    JOIN career_targets ct ON ct.id = s.target_id
    LEFT JOIN topics t ON t.skill_id = s.id
    LEFT JOIN concepts c ON c.topic_id = t.id
    LEFT JOIN questions q ON q.concept_id = c.id
    GROUP BY ct.id, s.id
    ORDER BY ct.id, s.id
""")
rows = cur.fetchall()
print("TID | TARGET | SKILL | WEIGHT | TOTAL | APPROVED | AI_GEN")
print("-"*100)
for r in rows:
    print(f"[{r['tid']}] {r['target'][:28]:<28} | {r['skill'][:32]:<32} | w={r['weight']:.2f} | total={r['total']:>5} | approved={r['approved']:>5} | ai={r['ai_gen']:>4}")

cur.execute("""
    SELECT COUNT(*) as cnt FROM concepts c
    WHERE c.id NOT IN (SELECT DISTINCT concept_id FROM questions WHERE review_status='approved')
""")
zero_approved = cur.fetchone()['cnt']
print(f"\nConcepts with 0 approved questions: {zero_approved}")

print("\nBanking (IBPS PO) question source/status breakdown:")
cur.execute("""
    SELECT q.source, q.review_status, COUNT(*) as cnt
    FROM questions q
    JOIN concepts c ON c.id = q.concept_id
    JOIN topics t ON t.id = c.topic_id
    JOIN skills s ON s.id = t.skill_id
    WHERE s.target_id = 7
    GROUP BY q.source, q.review_status
    ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  source={r['source']:<15} status={r['review_status']:<12} count={r['cnt']}")

print("\nML Engineering (target 1) question source/status breakdown:")
cur.execute("""
    SELECT q.source, q.review_status, COUNT(*) as cnt
    FROM questions q
    JOIN concepts c ON c.id = q.concept_id
    JOIN topics t ON t.id = c.topic_id
    JOIN skills s ON s.id = t.skill_id
    WHERE s.target_id = 1
    GROUP BY q.source, q.review_status
    ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  source={r['source']:<15} status={r['review_status']:<12} count={r['cnt']}")

print("\nTop 5 concepts by question count:")
cur.execute("""
    SELECT ct.name as target, c.name as concept, COUNT(q.id) as cnt
    FROM questions q
    JOIN concepts c ON c.id = q.concept_id
    JOIN topics t ON t.id = c.topic_id
    JOIN skills s ON s.id = t.skill_id
    JOIN career_targets ct ON ct.id = s.target_id
    WHERE q.review_status = 'approved'
    GROUP BY c.id
    ORDER BY cnt DESC
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"  {r['target'][:30]:<30} | {r['concept'][:40]:<40} | count={r['cnt']}")

conn.close()
print("\nDone.")
