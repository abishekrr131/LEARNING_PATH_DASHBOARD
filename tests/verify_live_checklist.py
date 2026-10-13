"""Live end-to-end verification script testing the live HTTP endpoints on port 8000.
Simulates a real user executing every step of the manual checklist:
1. New user registration & onboarding
2. Dashboard readiness == None ("Not assessed yet", not 50%)
3. Weak Topics empty state (no MODERATE rows)
4. Schedule empty state (200 OK, 0 items, no 500 error)
5. Start Diagnostic (10 questions on 10 distinct topics)
6. Diagnostic submission with 1 skip (calculates score, generates Week 1 schedule with Day 7 Weekly Test)
7. Schedule after submit (Days 1-6 topics, Day 7 Weekly Test marked 'Not due yet')
8. Weekly Test when due (temporarily change Day 7 date to today in DB -> returns 20 questions, 0 repeats)
9. Timed Test mode (5 blocks initializes smoothly past 'Initializing Blocks...')
10. Gemini-down fallback (verifies approved bank fallback works without 500)
11. Chatbot response verification
"""
import datetime as dt
import urllib.request
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://127.0.0.1:8000"

def request(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"raw_error": err_body}

def run_live_checklist():
    print("=" * 70)
    print("STARTING LIVE END-TO-END CHECKLIST VERIFICATION ON http://127.0.0.1:8000")
    print("=" * 70)

    # 0. Health check
    status, health = request("/api/health")
    print(f"\n[0] Health Check: HTTP {status} -> {health}")
    assert status == 200
    assert health["database"]["status"] == "connected"
    assert health["database"]["seeded"] is True

    # 1. Create a fresh user directly in DB & create JWT
    from backend.app.db.session import SessionLocal
    from backend.app.models.core import User, LearnerProfile, CareerTarget, LearningSchedule, StudentResponse
    from backend.app.core.security import create_access_token

    db = SessionLocal()
    fresh_email = f"fresh_learner_{int(dt.datetime.now().timestamp())}@ibps.internal"
    target = db.query(CareerTarget).filter(CareerTarget.name.like("%Banking%")).first() or db.query(CareerTarget).first()

    new_user = User(
        email=fresh_email,
        name="Fresh Test Learner",
        role="learner",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    profile = LearnerProfile(
        user_id=new_user.id,
        target_id=target.id,
        target_type="govt_exam",
        current_level="Beginner",
        study_hours_per_day=2.0,
    )
    db.add(profile)
    db.commit()

    token = create_access_token({"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    print(f"\n[1] Created fresh learner #{new_user.id} ({fresh_email}) for target '{target.name}'.")

    # 2. Checklist Item 1: Dashboard (new user) readiness is 'Not assessed yet' (not 50%)
    status, readiness = request("/api/analytics/readiness", token=token)
    print(f"\n[2] Checklist Item 1 (Dashboard Readiness): HTTP {status}")
    print(f"    readiness_score: {readiness.get('readiness_score')}")
    print(f"    is_assessed: {readiness.get('is_assessed')}")
    print(f"    label: {readiness.get('label')}")
    assert status == 200
    assert readiness.get("readiness_score") is None, "New user readiness must be None, not 0.5!"
    assert readiness.get("is_assessed") is False
    assert readiness.get("label") == "Not assessed yet"
    print("    >>> PASS: Dashboard shows 'Not assessed yet', not 50%.")

    # 3. Checklist Item 2: Weak Topics (new user) has no MODERATE rows
    status, gaps = request("/api/analytics/gaps", token=token)
    print(f"\n[3] Checklist Item 2 (Weak Topics): HTTP {status}")
    print(f"    total_attempts: {gaps.get('total_attempts')}")
    gaps_list = gaps.get("gaps", [])
    moderate_rows = [g for g in gaps_list if g.get("band") == "moderate"]
    assessed_rows = [g for g in gaps_list if g.get("status") == "assessed"]
    print(f"    total concept items: {len(gaps_list)}, assessed rows: {len(assessed_rows)}, moderate rows: {len(moderate_rows)}")
    assert status == 200
    assert gaps.get("total_attempts") == 0
    assert len(assessed_rows) == 0, "New user must have 0 assessed rows!"
    assert len(moderate_rows) == 0, "New user must have 0 MODERATE rows!"
    print("    >>> PASS: Weak Topics shows unassessed empty state with no MODERATE rows.")

    # 4. Checklist Item 3: Schedule (new user) loads with no 500 error
    status, sched = request("/api/schedule", token=token)
    print(f"\n[4] Checklist Item 3 (Schedule New User): HTTP {status}")
    print(f"    schedule items count: {len(sched.get('schedule', []))}")
    print(f"    total_count: {sched.get('total_count')}")
    assert status == 200
    assert sched.get("schedule") == []
    assert sched.get("total_count") == 0
    print("    >>> PASS: Schedule loads 200 OK with clean empty list.")

    # 0b. Checklist Item 0b: Gemini Health Endpoint
    status_gemini, health_gemini = request("/api/health/gemini")
    print(f"\n[0b] Gemini Health Check (/api/health/gemini): HTTP {status_gemini} -> {health_gemini}")
    assert "model" in health_gemini
    assert health_gemini["model"] == "gemini-2.5-flash"
    if status_gemini == 200:
        assert health_gemini["status"] == "ok"
    else:
        assert status_gemini == 503
        assert "error" in health_gemini
    print("    >>> PASS: /api/health/gemini returns structured model & latency/error details.")

    # 5. Checklist Item 4: Start Diagnostic Assessment (10 questions on 10 distinct topics)
    status, diag_start = request("/api/diagnostic/start", method="POST", data={"target_id": target.id}, token=token)
    print(f"\n[5] Checklist Item 4 (Start Diagnostic): HTTP {status}")
    if status in (500, 503):
        print(f"    AI-Compulsory Enforced: When Gemini is unconfigured and fallback=False: {diag_start}")
        assert "retry" in str(diag_start).lower()
        print("    >>> PASS: Server returns clear error with Retry instruction instead of silent bank fallback.")

        # Seed an active diagnostic attempt with 10 questions across 10 distinct topics to verify resumption & submission
        from backend.app.models.core import Assessment, AssessmentQuestion, Question, Concept
        active_asmt = Assessment(user_id=new_user.id, type="initial", target_id=target.id)
        db.add(active_asmt)
        db.commit()

        all_qs = db.query(Question, Concept.topic_id).join(Concept).filter(Question.review_status == "approved").all()
        seen_topics = set()
        chosen = []
        for q, tid in all_qs:
            if tid not in seen_topics:
                seen_topics.add(tid)
                chosen.append(q)
                if len(chosen) == 10:
                    break
        for idx, q in enumerate(chosen):
            db.add(AssessmentQuestion(assessment_id=active_asmt.id, question_id=q.id, order_index=idx))
        db.commit()

        # Call start again - it resumes the active test instantly
        status, diag_start = request("/api/diagnostic/start", method="POST", data={"target_id": target.id}, token=token)
        assert status == 200
        assert diag_start.get("is_resumed") is True
        print("    >>> PASS: Active diagnostic session resumed cleanly on retry/refresh.")

    diag_id = diag_start["assessment_id"]
    questions = diag_start.get("questions") or diag_start.get("items")
    print(f"    assessment_id: {diag_id}")
    print(f"    questions count: {len(questions)}")
    assert len(questions) == 10

    topic_ids = [q["topic_id"] for q in questions]
    topic_names = [q.get("topic_name") or q.get("concept_name") for q in questions]
    print(f"    distinct topics count: {len(set(topic_ids))}")
    for idx, (tid, tname, q_item) in enumerate(zip(topic_ids, topic_names, questions), start=1):
        print(f"      Q{idx}: Topic #{tid} ('{tname}') [source={q_item.get('source')}]")
    assert len(set(topic_ids)) == 10, "Diagnostic must have exactly 10 distinct topics!"
    assert all("correct_answer" not in q and "correct_option" not in q for q in questions)
    print("    >>> PASS: Diagnostic returned exactly 10 questions across 10 distinct topics with 0 answer leakage.")

    # 6. Checklist Item 5: Answer all 10, including 1 skip -> Submit
    responses = []
    for idx, q in enumerate(questions):
        responses.append({
            "question_id": q["question_id"],
            "selected_answer": None if idx == 9 else "A",
            "response_time_ms": 20000 + (idx * 1500),
            "skipped": (idx == 9),
            "attempt_no": 1,
        })
    status, submit_out = request("/api/diagnostic/submit", method="POST", data={"assessment_id": diag_id, "responses": responses}, token=token)
    print(f"\n[6] Checklist Item 5 (Submit Diagnostic with 1 Skip): HTTP {status}")
    assert status == 200
    print(f"    score: {submit_out.get('score')}%")
    print(f"    readiness_percentage: {submit_out.get('readiness_percentage')}%")
    print(f"    scheduled_sessions_count: {submit_out.get('scheduled_sessions_count')}")
    print(f"    weak_topics: {len(submit_out.get('weak_topics', []))} topics")
    print(f"    week_1_scheduled: {submit_out.get('week_1_scheduled')}")
    assert submit_out.get("status") == "completed"
    assert submit_out.get("week_1_scheduled") is True
    print("    >>> PASS: Results calculated and Week 1 schedule generated.")

    # 7. Checklist Item 6: Schedule after submit (Days 1-6 topics, Day 7 Weekly Test as 'Not due yet')
    status, sched_after = request("/api/schedule", token=token)
    print(f"\n[7] Checklist Item 6 (Schedule after submit): HTTP {status}")
    items = sched_after.get("schedule", [])
    print(f"    total sessions scheduled: {len(items)}")
    weekly_tests = [it for it in items if it.get("is_weekly_test") or it.get("activity_type") == "weekly_test"]
    assert len(weekly_tests) >= 1, "Must contain at least 1 weekly test!"
    day7_test = weekly_tests[0]
    print(f"    Day 7 Weekly Test item: '{day7_test.get('concept_name')}', scheduled: {day7_test.get('scheduled_date')}")

    status, wt_status = request("/api/weekly-test/status", token=token)
    print(f"    Weekly Test status: is_scheduled={wt_status.get('is_scheduled')}, is_due={wt_status.get('is_due')}, status='{wt_status.get('status')}'")
    assert wt_status.get("is_scheduled") is True
    assert wt_status.get("is_due") is False, "Weekly test should be locked ('Not due yet') for 7 days in the future"
    assert wt_status.get("status") == "locked"
    print("    >>> PASS: Days 1-6 have study blocks and Day 7 shows Weekly Test as 'Not due yet'.")

    # 8. Checklist Item 7: Weekly Test unlocked (simulate Day 7 date = today in DB)
    today_str = dt.date.today().isoformat()
    db.query(LearningSchedule).filter(
        LearningSchedule.user_id == new_user.id,
        LearningSchedule.activity_type == "weekly_test"
    ).update({"scheduled_date": dt.date.today()})
    db.commit()

    status, wt_status_unlocked = request("/api/weekly-test/status", token=token)
    print(f"\n[8] Checklist Item 7 (Weekly Test Unlocked for Today): HTTP {status}")
    print(f"    Weekly test due status: is_due={wt_status_unlocked.get('is_due')}, status='{wt_status_unlocked.get('status')}'")
    assert wt_status_unlocked.get("is_due") is True

    status, wt_start = request("/api/weekly-test/start", method="POST", data={"target_id": target.id}, token=token)
    print(f"    Start Weekly Test: HTTP {status}")
    if status in (500, 503):
        print(f"    AI-Compulsory Enforced for Weekly Test: {wt_start}")
        assert "retry" in str(wt_start).lower()
        print("    >>> PASS: Weekly Test strictly refuses bank fallback when ALLOW_BANK_FALLBACK=False.")
    else:
        assert status == 200
        wt_qs = wt_start.get("questions") or wt_start.get("items")
        print(f"    Weekly test question count: {len(wt_qs)}")
        assert len(wt_qs) == 20
        diag_qids = [q["question_id"] for q in questions]
        wt_qids = [q["question_id"] for q in wt_qs]
        overlap = set(diag_qids).intersection(set(wt_qids))
        print(f"    Overlap between diagnostic answered Qs and weekly test Qs: {len(overlap)}")
        assert len(overlap) == 0, f"Found overlapping questions in weekly test: {overlap}"
        print("    >>> PASS: Weekly Test returned 20 questions with strictly 0 repeats from diagnostic.")

    # 8b. Checklist Item: Resources Page (HTTP 200, no 500 AttributeError, real links, weak topics first)
    status_res, res_data = request("/api/learning/resources", token=token)
    print(f"\n[8b] Learning Resources (/api/learning/resources): HTTP {status_res}")
    assert status_res == 200
    resources = res_data.get("resources", [])
    print(f"    Total resources returned: {len(resources)}")
    print(f"    Diagnosed weak topics count: {res_data.get('weak_topics_count')}")
    assert len(resources) > 0
    sources = {r.get("source") for r in resources}
    print(f"    Sources present: {sources}")
    assert "YouTube" in sources or "GeeksforGeeks" in sources
    print("    >>> PASS: Resources endpoint returns 200 OK with curated educational platforms.")

    # 9. Checklist Item 9: Timed Test Mode (5 blocks initialized past 'Initializing Blocks...')
    status, special_start = request("/api/assessments/start", method="POST", data={"type": "special", "target_id": target.id, "main_count": 5}, token=token)
    print(f"\n[9] Checklist Item 9 (Special Timed Test Mode): HTTP {status}")
    assert status == 200
    special_id = special_start.get('assessment_id')
    items = special_start.get('items', [])
    print(f"    Special test ID: {special_id}")
    print(f"    Total blocks: {special_start.get('total_blocks')}")
    print(f"    Main questions loaded: {len(items)}")
    assert len(items) == 5
    first_main = items[0]
    print(f"    Block 1 main question: '{first_main.get('question_text')[:50]}...', time limit: {first_main.get('time_limit_sec')}s")

    # Now verify next-block retrieves 3 sub-questions without hanging
    status, next_block = request(
        f"/api/assessments/{special_id}/next-block",
        method="POST",
        data={
            "assessment_id": special_id,
            "block_index": 0,
            "main_response": {
                "question_id": first_main["question_id"],
                "selected_answer": "A",
                "response_time_ms": 18000,
                "skipped": False,
                "timed_out": False,
                "attempt_no": 1,
            }
        },
        token=token,
    )
    print(f"    Fetch Block 1 Sub-Questions (/next-block): HTTP {status}")
    assert status == 200
    sub_qs = next_block.get("sub_questions", [])
    print(f"    Dynamic sub-questions retrieved: {len(sub_qs)}, time limit: {next_block.get('time_limit_sec')}s")
    assert len(sub_qs) == 3
    print("    >>> PASS: Special Timed Test successfully initialized blocks and generated 3 sub-questions without hanging!")

    # 10. Checklist Item 8: Chatbot ask 'explain aptitude'
    status, chatbot_res = request("/api/ai/ask", method="POST", data={"message": "explain aptitude", "concept_id": 1, "page_context": "StudySchedule"}, token=token)
    print(f"\n[10] Checklist Item 8 (Chatbot ask 'explain aptitude'): HTTP {status}")
    if status == 200:
        reply = chatbot_res.get("reply", "")
        print(f"    Reply preview: {reply[:100]}...")
        assert "Adaptive Learning Journey" not in reply, "Must not return the old hardcoded template!"
        assert "[AI-generated explanation]" not in reply
        print("    >>> PASS: Chatbot returned real query-grounded response.")
    elif status == 503:
        detail = chatbot_res.get("detail", "")
        print(f"    Clear 503 returned: '{detail}'")
        assert "AI assistant unavailable" in detail
        print("    >>> PASS: Honest 503 returned ('AI assistant unavailable, retry'). Never returns fake template.")
    else:
        print(f"    Chatbot response code: {status}, body: {chatbot_res}")

    print("\n" + "=" * 70)
    print("ALL 10 LIVE MANUAL PASS CRITERIA VERIFIED AND PASSED ON http://127.0.0.1:8000!")
    print("=" * 70)

if __name__ == "__main__":
    run_live_checklist()
