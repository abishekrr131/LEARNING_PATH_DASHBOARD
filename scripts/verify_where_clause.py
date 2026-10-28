import sqlite3

conn = sqlite3.connect('palp_local.db')
cur = conn.cursor()

# Test the exact WHERE clause from fetch_local_eligible
cur.execute("""
    SELECT COUNT(*) FROM questions q
    WHERE q.review_status = 'approved'
      AND q.source NOT IN ('ai_generated', 'gemini')
      AND TRIM(q.question_text) != ''
      AND q.correct_answer IN ('A','B','C','D')
      AND q.options_json IS NOT NULL
""")
count_matched = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM questions")
total_q = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM questions
    WHERE review_status != 'approved' OR source IN ('ai_generated', 'gemini')
""")
unapproved_or_ai = cur.fetchone()[0]

print(f"Total questions: {total_q}")
print(f"Matched by eligible query: {count_matched}")
print(f"Unapproved or AI: {unapproved_or_ai}")
print(f"Sum check: {count_matched + unapproved_or_ai == total_q}")

# Breakdown of the 160
cur.execute("""
    SELECT source, review_status, COUNT(*)
    FROM questions
    WHERE review_status != 'approved' OR source IN ('ai_generated', 'gemini')
    GROUP BY source, review_status
""")
for r in cur.fetchall():
    print(f"  Excluded category: source={r[0]}, status={r[1]}, count={r[2]}")

conn.close()
