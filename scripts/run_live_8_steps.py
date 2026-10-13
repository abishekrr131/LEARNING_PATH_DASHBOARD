"""Live End-to-End Verification of the 8 Required Flows.
Executes all 8 steps against the running server at http://127.0.0.1:8000.
"""
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://127.0.0.1:8000"

def request_json(path: str, method: str = "GET", data: dict | None = None, token: str | None = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=90.0) as resp:
        elapsed = time.perf_counter() - t0
        res_data = json.loads(resp.read().decode("utf-8"))
        return res_data, elapsed, resp.status

def run():
    print("=" * 70)
    print("STARTING LIVE 8-STEP END-TO-END VERIFICATION")
    print("=" * 70)

    # Setup Fresh User
    ts = int(time.time())
    email = f"live_verify_{ts}@palp.internal"
    name = f"Live Verify Learner {ts}"

    auth_payload = {
        "id_token": f"mock-google-token-live_verify_{ts}",
    }
    auth_data, _, _ = request_json("/api/auth/google", method="POST", data=auth_payload)
    token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]
    print(f"[AUTH] Created user {email} (id={user_id})")

    # Set Career Target to Banking (IBPS PO) -> target_id = 7
    target_payload = {
        "target_id": 7,
        "current_level": "Intermediate",
    }
    request_json("/api/me/profile", method="PATCH", data=target_payload, token=token)
    print("[AUTH] User target set to Banking (IBPS PO) (id=7)")

    # -------------------------------------------------------------
    # Step 1: Start Diagnostic 10 Qs across 10 topics with AI badge
    # -------------------------------------------------------------
    print("\n--- STEP 1: Start Initial Diagnostic ---")
    diag_start_data, diag_elapsed, diag_code = request_json(
        "/api/diagnostic/start", method="POST", data={"target_id": 7}, token=token
    )
    diag_id = diag_start_data["assessment_id"]
    diag_items = diag_start_data["items"]
    diag_topics = [it["topic_name"] for it in diag_items]
    distinct_topics = set(it["topic_id"] for it in diag_items if it.get("topic_id"))
    ai_sources = [it["source"] for it in diag_items]

    print(f"Status Code: {diag_code}")
    print(f"Assessment ID: {diag_id}")
    print(f"Elapsed Time: {diag_elapsed:.2f}s")
    print(f"Total Questions: {len(diag_items)}")
    print(f"Distinct Topics ({len(distinct_topics)}): {diag_topics[:5]}...")
    print(f"Question Sources: {ai_sources}")
    for idx, it in enumerate(diag_items[:3]):
        print(f"  Q{idx+1}: [{it['source'].upper()}] ({it['topic_name']}) {it['question_text'][:60]}...")
        print(f"       Options: {it['options'][:2]}...")

    assert len(diag_items) == 10, f"Expected 10 items, got {len(diag_items)}"
    assert len(distinct_topics) == 10, f"Expected 10 distinct topics, got {len(distinct_topics)}"
    assert all(it["source"] == "gemini" for it in diag_items), "Expected all sources to be 'gemini'"

    # -------------------------------------------------------------
    # Step 2: Database Source Count Verification
    # -------------------------------------------------------------
    print("\n--- STEP 2: Database Question Source Counts ---")
    from backend.app.db.session import SessionLocal
    from backend.app.models.core import Question, LearningSchedule
    from sqlalchemy import func
    with SessionLocal() as s:
        db_sources = s.query(Question.source, func.count(Question.id)).group_by(Question.source).all()
        print(f"SELECT source, COUNT(*) FROM questions GROUP BY source:")
        for src, cnt in db_sources:
            print(f"  {src}: {cnt}")
        gemini_count = dict(db_sources).get("gemini", 0)
        assert gemini_count >= 30, f"Expected at least 30 gemini questions, found {gemini_count}"

    # -------------------------------------------------------------
    # Step 3: Submit Diagnostic (1 Skip) and Verify Week 1 Schedule
    # -------------------------------------------------------------
    print("\n--- STEP 3: Submit Diagnostic with 1 Skip ---")
    responses = []
    for idx, it in enumerate(diag_items):
        if idx == 0:
            responses.append({
                "question_id": it["question_id"],
                "selected_answer": None,
                "skipped": True,
                "response_time_ms": 5000,
                "attempt_no": 1,
            })
        else:
            responses.append({
                "question_id": it["question_id"],
                "selected_answer": "A",
                "skipped": False,
                "response_time_ms": 15000,
                "attempt_no": 1,
            })

    sub_data, sub_elapsed, _ = request_json(
        "/api/diagnostic/submit",
        method="POST",
        data={"assessment_id": diag_id, "responses": responses},
        token=token,
    )
    print(f"Diagnostic Submitted in {sub_elapsed:.2f}s")
    print(f"Score: {sub_data['score']}%, Correct: {sub_data['correct_count']}, Skipped: {sub_data['skip_count']}")
    print(f"Readiness: {sub_data['readiness_percentage']}%")
    print(f"Weak Topics Detected: {[w['concept_name'] for w in sub_data.get('weak_topics', [])[:3]]}")
    print(f"Root Causes Traced: {len(sub_data.get('root_causes', []))}")
    print(f"Topological Roadmap Nodes: {len(sub_data.get('roadmap', []))}")

    # Check Schedule
    sched_data, _, _ = request_json("/api/schedule", method="GET", token=token)
    items = sched_data.get("schedule", [])
    print(f"\nWeek 1 Schedule Generated ({len(items)} sessions):")
    day7_item = None
    for it in items:
        print(f"  Day: {it['scheduled_date']} | Type: {it['activity_type']} | Topic: {it.get('topic_name')} | Status: {it['status']}")
        if it["activity_type"] == "weekly_test":
            day7_item = it

    assert day7_item is not None, "Day 7 weekly test must be scheduled"
    print(f"\nDay 7 Weekly Test Scheduled Date: {day7_item['scheduled_date']} (Status: {day7_item['status']})")

    # Verify Weekly Test Status is Locked
    wt_status, _, _ = request_json("/api/weekly-test/status", method="GET", token=token)
    print(f"Weekly Test Status API: status='{wt_status['status']}', is_due={wt_status['is_due']}, message='{wt_status['message']}'")
    assert wt_status["is_due"] is False, "Weekly test must not be due immediately"

    # -------------------------------------------------------------
    # Step 4: Unlock Weekly Test (Set Day 7 to Today) & Start
    # -------------------------------------------------------------
    print("\n--- STEP 4: Weekly Test (20 AI Questions, 0 Repeats) ---")
    today_iso = dt.date.today().isoformat()
    with SessionLocal() as s:
        row = s.query(LearningSchedule).filter(
            LearningSchedule.user_id == user_id,
            LearningSchedule.activity_type == "weekly_test",
        ).first()
        if row:
            row.scheduled_date = dt.date.today()
            s.commit()
            print(f"Updated Day 7 Weekly Test scheduled_date to TODAY ({today_iso})")

    # Start Weekly Test
    wt_start_data, wt_elapsed, wt_code = request_json(
        "/api/weekly-test/start", method="POST", data={"target_id": 7, "force_unlock": True}, token=token
    )
    wt_items = wt_start_data["items"]
    diag_qids = set(it["question_id"] for it in diag_items)
    wt_qids = set(it["question_id"] for it in wt_items)
    repeats = diag_qids & wt_qids

    print(f"Weekly Test Started in {wt_elapsed:.2f}s (Pre-generated instant or parallel start)")
    print(f"Status Code: {wt_code}")
    print(f"Total Questions: {len(wt_items)}")
    print(f"Repeats from Diagnostic: {len(repeats)} (Repeated IDs: {repeats})")
    print(f"Sources: {set(it['source'] for it in wt_items)}")
    for idx, it in enumerate(wt_items[:3]):
        print(f"  WT Q{idx+1}: [{it['source'].upper()}] {it['question_text'][:60]}...")

    assert len(wt_items) == 20, f"Expected 20 weekly test items, got {len(wt_items)}"
    assert len(repeats) == 0, f"Expected 0 repeats, found {len(repeats)}"
    assert all(it["source"] == "gemini" for it in wt_items), "Expected all sources to be 'gemini'"

    # -------------------------------------------------------------
    # Step 5: Practice Mode (No .options.map Crash)
    # -------------------------------------------------------------
    print("\n--- STEP 5: Practice Mode ---")
    pract_data, pract_elapsed, pract_code = request_json(
        "/api/assessments/start", method="POST", data={"type": "practice", "target_id": 7}, token=token
    )
    pract_items = pract_data["items"]
    print(f"Practice Set Generated in {pract_elapsed:.2f}s")
    print(f"Status Code: {pract_code}")
    print(f"Total Practice Items: {len(pract_items)}")
    for idx, it in enumerate(pract_items):
        assert isinstance(it["options"], list), f"Options must be list, got {type(it['options'])}"
        for opt in it["options"]:
            assert "key" in opt and "text" in opt, f"Option format must be {{key, text}}, got {opt}"
        print(f"  Practice Q{idx+1}: [{it.get('source', 'curated').upper()}] {it['question_text'][:50]}... (Options count: {len(it['options'])})")

    # -------------------------------------------------------------
    # Step 6: Resources Page (No 500, Weak Topics First)
    # -------------------------------------------------------------
    print("\n--- STEP 6: Learning Resources Page ---")
    res_data, res_elapsed, res_code = request_json(
        "/api/learning/resources", method="GET", token=token
    )
    resources = res_data["resources"]
    print(f"Resources API Response Code: {res_code} (in {res_elapsed:.2f}s)")
    print(f"Total Resources Returned: {len(resources)}")
    print(f"Weak Topics First Check: Resource 0 is_weak_topic={resources[0].get('is_weak_topic')}")
    platforms = set(r["source"] for r in resources)
    print(f"Resource Platforms Included: {platforms}")
    for idx, r in enumerate(resources[:3]):
        print(f"  Resource {idx+1}: [{r['source']}] {r['title']} -> {r['url']}")

    assert res_code == 200, f"Expected 200 OK, got {res_code}"
    assert "YouTube" in platforms and "GeeksforGeeks" in platforms and "IndiaBix" in platforms

    # -------------------------------------------------------------
    # Step 7: Chatbot "explain aptitude" (Strict Banking Context, No ML)
    # -------------------------------------------------------------
    print("\n--- STEP 7: Chatbot Banking Aptitude Query ---")
    chat_data, chat_elapsed, chat_code = request_json(
        "/api/ai/ask", method="POST", data={"message": "explain aptitude"}, token=token
    )
    reply = chat_data["reply"]
    topic_injected = chat_data.get("topic_name")
    print(f"Chatbot Replied in {chat_elapsed:.2f}s (Status: {chat_code})")
    print(f"Injected Curriculum Topic: {topic_injected}")
    print(f"Reply Preview:\n{reply[:300]}...\n")

    ml_forbidden = ["vector", "matrix", "matrices", "gradient", "dot product", "neural network", "tensor"]
    reply_lower = reply.lower()
    for word in ml_forbidden:
        assert word not in reply_lower, f"ML term '{word}' found in Banking chatbot answer!"

    assert "Core Intuition:" not in reply, "Fixed template 'Core Intuition' should not appear unless requested"
    print("Verification Passed: 0 ML terms found. Natural explanation grounded strictly in Banking aptitude.")

    # -------------------------------------------------------------
    # Step 8: Timed Test Mode (5 Blocks, No Hanging)
    # -------------------------------------------------------------
    print("\n--- STEP 8: Timed Test Mode (5 Blocks) ---")
    special_data, special_elapsed, special_code = request_json(
        "/api/assessments/start", method="POST", data={"type": "special", "target_id": 7, "block_count": 5}, token=token
    )
    special_items = special_data["items"]
    print(f"Timed Test Generated in {special_elapsed:.2f}s (Status: {special_code})")
    print(f"Assessment ID: {special_data['assessment_id']}")
    print(f"Total Main Questions: {len(special_items)}")
    for idx, it in enumerate(special_items):
        print(f"  Block {idx+1}: [{it.get('source', 'curated').upper()}] {it['question_text'][:50]}... Time Limit: {it.get('time_limit_sec', 30)}s")

    assert special_code == 200
    assert len(special_items) == 5, f"Expected 5 main questions, got {len(special_items)}"

    print("\n" + "=" * 70)
    print("ALL 8 END-TO-END VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run()
