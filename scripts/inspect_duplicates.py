import sqlite3, os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "palp_local.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Inspect the 3 duplicate stems
cur.execute("""
    SELECT question_text, COUNT(*) as cnt
    FROM questions
    GROUP BY question_text
    HAVING cnt > 1
""")
dups = cur.fetchall()
print(f"Total duplicate question stems in palp_local.db: {len(dups)}")
for d in dups:
    cur.execute("""
        SELECT q.id, q.concept_id, q.source, q.review_status, c.name as concept_name, ct.name as target_name
        FROM questions q
        JOIN concepts c ON c.id = q.concept_id
        JOIN topics t ON t.id = c.topic_id
        JOIN skills s ON s.id = t.skill_id
        JOIN career_targets ct ON ct.id = s.target_id
        WHERE q.question_text = ?
    """, (d["question_text"],))
    rows = cur.fetchall()
    print(f"\nStem: {d['question_text'][:80]}...")
    for r in rows:
        print(f"  id={r['id']} | concept={r['concept_name']} ({r['concept_id']}) | target={r['target_name']} | source={r['source']} | status={r['review_status']}")

conn.close()
