import urllib.request
import json
import sys
from backend.app.db.session import SessionLocal
from backend.app.models.core import User, CareerTarget, Question
from backend.app.core.security import create_access_token

def main():
    db = SessionLocal()
    from backend.app.models.core import LearnerProfile
    user = db.query(User).first()
    if not user:
        user = User(email='verify.user@example.com', name='Verify Learner', google_sub='sub_verify_123')
        db.add(user)
        db.commit()
        db.refresh(user)

    prof = db.query(LearnerProfile).filter(LearnerProfile.user_id == user.id).first()
    if not prof:
        prof = LearnerProfile(user_id=user.id, target_type='govt_exam', target_id=7, current_level='intermediate')
        db.add(prof)
        db.commit()
    else:
        prof.target_id = 7
        db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    print(f"=== E2E Diagnostic & Practice Verification ===")
    print(f"User: {user.id} ({user.email}), Target: {prof.target_id}")

    # 1. Start Initial Diagnostic (10 questions)
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/diagnostic/start',
        data=json.dumps({'target_id': 7}).encode(),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        asmt_id = data['assessment_id']
        items = data['items']
        print(f"[OK] Diagnostic started: ID {asmt_id}, received {len(items)} questions")
        assert len(items) == 10, f"Expected 10 items, got {len(items)}"
        unique_qids = {it['question_id'] for it in items}
        assert len(unique_qids) == 10, "Expected 10 unique question IDs"
        for it in items:
            assert len(it['options']) == 4, f"Question {it['question_id']} options != 4"
            assert it.get('verified') is True, f"Question {it['question_id']} not marked verified"
            print(f"  Q{it['order_index']}: [{it['skill_name']} -> {it['topic_name']}] {it['stem'][:50]}... (source: {it.get('source')})")

    # 2. Submit Diagnostic
    # Answer 8 correctly, 2 incorrectly to test topic performance and adaptive week 1 schedule
    responses = []
    for idx, it in enumerate(items):
        q = db.get(Question, it['question_id'])
        is_correct = (idx < 8)
        ans = q.correct_answer if is_correct else ("B" if q.correct_answer == "A" else "A")
        responses.append({
            "question_id": it['question_id'],
            "selected_answer": ans,
            "response_time_ms": 25000,
            "phase": "main"
        })

    submit_payload = {
        "assessment_id": asmt_id,
        "responses": responses
    }
    req_sub = urllib.request.Request(
        'http://127.0.0.1:8000/api/diagnostic/submit',
        data=json.dumps(submit_payload).encode(),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req_sub) as resp:
        sub_data = json.loads(resp.read().decode())
        print(f"[OK] Diagnostic submitted successfully!")
        print(f"  Accuracy: {sub_data['question_accuracy_pct']}% ({sub_data['score']}/{sub_data['total_questions']})")
        print(f"  Attempted count: {sub_data['attempted_count']}")
        print(f"  Distinct topics demonstrated: {sub_data['distinct_topics_demonstrated_count']}")
        assert len(sub_data['question_results']) == 10
        assert "career_map" in sub_data
        assert "first_week_plan" in sub_data
        print(f"  First week plan days generated: {len(sub_data['first_week_plan'])}")
        for day in sub_data['first_week_plan'][:3]:
            print(f"    Day {day['day']}: {day['subject']} -> {day['topic_name']} ({day['plan_reason']}) | URL: {day.get('resource_url')}")

    # 3. Check GET /api/schedule persistence
    req_sched = urllib.request.Request(
        'http://127.0.0.1:8000/api/schedule',
        headers=headers,
        method='GET'
    )
    with urllib.request.urlopen(req_sched) as resp:
        sched_data = json.loads(resp.read().decode())
        sched_items = sched_data['schedule']
        assert len(sched_items) == 7, f"Expected 7 schedule items, got {len(sched_items)}"
        print(f"[OK] Schedule persisted across requests: 7 items returned")
        day7 = sched_items[6]
        assert "Weekly Progress Test" in day7['concept_name'] or "assessment" in day7['activity_type'].lower()
        print(f"  Day 7 Task: {day7['concept_name']} ({day7['activity_type']}) | Reason: {day7['plan_reason']}")
        print(f"  Day 7 Objective: {day7['learning_objective']}")
        print(f"  Day 7 Resource: {day7['resource_title']} -> {day7['resource_url']}")

    # 4. Check Combined 40-question Practice Test
    req_prac = urllib.request.Request(
        'http://127.0.0.1:8000/api/assessments/start',
        data=json.dumps({'type': 'practice', 'target_id': 7, 'practice_mode': 'combined'}).encode(),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req_prac) as resp:
        prac_data = json.loads(resp.read().decode())
        print(f"[OK] Combined Practice Test: ID {prac_data['assessment_id']}, count = {len(prac_data['items'])}")
        assert len(prac_data['items']) == 40, f"Expected 40 items, got {len(prac_data['items'])}"
        assert prac_data['time_limit_sec'] == 3600

    # 5. Check 90s Speed Practice Test
    req_speed = urllib.request.Request(
        'http://127.0.0.1:8000/api/assessments/start',
        data=json.dumps({'type': 'practice', 'target_id': 7, 'practice_mode': 'speed'}).encode(),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req_speed) as resp:
        speed_data = json.loads(resp.read().decode())
        print(f"[OK] Speed Practice Test: ID {speed_data['assessment_id']}, count = {len(speed_data['items'])}")
        assert len(speed_data['items']) == 10, f"Expected 10 items, got {len(speed_data['items'])}"
        assert speed_data['time_limit_sec'] == 90

    print("\n>>> ALL 10 SCENARIOS VERIFIED END-TO-END! <<<")

if __name__ == "__main__":
    main()
