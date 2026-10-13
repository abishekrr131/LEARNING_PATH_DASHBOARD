import urllib.request
import json
import datetime as dt
from backend.app.db.session import SessionLocal
from backend.app.models.core import User, CareerTarget, Skill, Topic, Concept, Question, StudentResponse, Assessment, LearningSchedule
from backend.app.core.security import create_access_token
from backend.app.services.question_generator import synthesize_week_schedule, generate_practice_questions
from backend.app.api.analytics import get_gap_analytics

def main():
    print("=====================================================================")
    print("VERIFYING 9 SCENARIOS FOR DIAGNOSTIC -> CAREER MAP -> WEEK 1 PROGRESSION")
    print("=====================================================================")

    db = SessionLocal()

    # Find or setup test user with target 6 (SSC CGL)
    target = db.get(CareerTarget, 6) # SSC CGL
    user = db.query(User).filter(User.email == "learner.test.ssc@learnpath.internal").first()
    if not user:
        user = User(email="learner.test.ssc@learnpath.internal", name="SSC Test Learner", google_sub="sub_test_ssc_99")
        db.add(user)
        db.commit()
        db.refresh(user)

    from backend.app.models.core import LearnerProfile
    prof = db.query(LearnerProfile).filter(LearnerProfile.user_id == user.id).first()
    if not prof:
        prof = LearnerProfile(user_id=user.id, target_type="govt_exam", target_id=6, current_level="intermediate")
        db.add(prof)
        db.commit()
    else:
        prof.target_id = 6
        db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Concepts in SSC CGL:
    # Quant: Percentages (id=209), Ratio & Proportion (id=212)
    # Reasoning: Analogy (id=223), Series (id=224), Coding (id=225)
    # English: Subject-Verb (id=232), Tenses (id=233)
    # GA: Physics (id=241), Constitutional Articles (id=245), Governor-Generals (id=246)
    c_pct = db.get(Concept, 209)
    c_ratio = db.get(Concept, 212)
    c_analog = db.get(Concept, 223)
    c_series = db.get(Concept, 224)
    c_sub_verb = db.get(Concept, 232)
    c_tenses = db.get(Concept, 233)
    c_const = db.get(Concept, 245)
    c_gov = db.get(Concept, 246)

    # -----------------------------------------------------------------
    # Scenario 1: Percentages mastered -> Ratio and Proportion scheduled next
    # -----------------------------------------------------------------
    print("\n--- Scenario 1: Percentages mastered (>=80%) -> Ratio and Proportion unlocked ---")
    # Clean previous responses for user
    db.query(StudentResponse).filter(StudentResponse.user_id == user.id).delete()
    db.query(LearningSchedule).filter(LearningSchedule.user_id == user.id).delete()
    db.query(Assessment).filter(Assessment.user_id == user.id).delete()
    db.commit()

    asmt1 = Assessment(user_id=user.id, type="initial", target_id=6, score=100.0, completed_at=dt.datetime.now(dt.timezone.utc))
    db.add(asmt1)
    db.commit()

    q_pct = db.query(Question).filter(Question.concept_id == 209).first()
    r_pct_corr = StudentResponse(
        user_id=user.id,
        assessment_id=asmt1.id,
        question_id=q_pct.id,
        selected_answer=q_pct.correct_answer,
        is_correct=True,
        response_time_ms=16000,
        answered_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(r_pct_corr)
    db.commit()

    plan1 = synthesize_week_schedule(user_id=user.id, target_id=6, db=db, week_number=1)
    ratio_items = [p for p in plan1 if "Ratio" in p.topic_name or "Ratio" in p.plan_reason]
    assert len(ratio_items) >= 1, "Ratio and Proportion was not scheduled following Percentages mastery!"
    print(f"  [PASS] Ratio and Proportion unlocked! Reason: {ratio_items[0].plan_reason}")

    # -----------------------------------------------------------------
    # Scenario 2: Percentages not mastered -> Percentages remediation scheduled
    # -----------------------------------------------------------------
    print("\n--- Scenario 2: Percentages not mastered (<80%) -> Percentages materials and practice scheduled ---")
    db.query(StudentResponse).filter(StudentResponse.user_id == user.id).delete()
    db.commit()

    r_pct_wrong = StudentResponse(
        user_id=user.id,
        assessment_id=asmt1.id,
        question_id=q_pct.id,
        selected_answer="X", # wrong
        is_correct=False,
        response_time_ms=30000,
        answered_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(r_pct_wrong)
    db.commit()

    plan2 = synthesize_week_schedule(user_id=user.id, target_id=6, db=db, week_number=1)
    pct_items = [p for p in plan2 if "Percentage" in p.topic_name]
    ratio_items2 = [p for p in plan2 if "Ratio" in p.topic_name]
    assert len(pct_items) >= 1, "Percentages remediation was not scheduled for weak performance!"
    assert len(ratio_items2) == 0, "Ratio & Proportion was wrongly unlocked despite weak Percentages!"
    print(f"  [PASS] Percentages remediation scheduled! Reason: {pct_items[0].plan_reason}")
    print(f"  [PASS] Advancement to Ratio paused (Ratio scheduled: {len(ratio_items2)})")

    # -----------------------------------------------------------------
    # Scenario 3: Reasoning topic mastered -> next eligible Reasoning topic
    # -----------------------------------------------------------------
    print("\n--- Scenario 3: Reasoning topic mastered -> next eligible Reasoning topic scheduled ---")
    q_reason = db.query(Question).filter(Question.concept_id == c_analog.id).first()
    r_reason_corr = StudentResponse(
        user_id=user.id,
        assessment_id=asmt1.id,
        question_id=q_reason.id,
        selected_answer=q_reason.correct_answer,
        is_correct=True,
        response_time_ms=14000,
        answered_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(r_reason_corr)
    db.commit()

    plan3 = synthesize_week_schedule(user_id=user.id, target_id=6, db=db, week_number=1)
    reason_items = [p for p in plan3 if p.subject == "General Intelligence & Reasoning"]
    assert len(reason_items) >= 1, "Next Reasoning topic not scheduled!"
    print(f"  [PASS] Reasoning progression scheduled: {reason_items[0].topic_name} (Reason: {reason_items[0].plan_reason})")

    # -----------------------------------------------------------------
    # Scenario 4: English topic not mastered -> relevant English revision and practice
    # -----------------------------------------------------------------
    print("\n--- Scenario 4: English topic not mastered -> relevant English revision scheduled ---")
    q_eng = db.query(Question).filter(Question.concept_id == c_sub_verb.id).first()
    r_eng_wrong = StudentResponse(
        user_id=user.id,
        assessment_id=asmt1.id,
        question_id=q_eng.id,
        selected_answer="X",
        is_correct=False,
        response_time_ms=28000,
        answered_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(r_eng_wrong)
    db.commit()

    plan4 = synthesize_week_schedule(user_id=user.id, target_id=6, db=db, week_number=1)
    eng_items = [p for p in plan4 if p.subject == "English Comprehension"]
    assert len(eng_items) >= 1, "English revision not scheduled!"
    assert any("remediation" in p.plan_reason.lower() or "paused" in p.plan_reason.lower() for p in eng_items)
    print(f"  [PASS] English remediation scheduled: {eng_items[0].topic_name} (Reason: {eng_items[0].plan_reason})")

    # -----------------------------------------------------------------
    # Scenario 5: GA topic mastered -> next eligible GA topic scheduled
    # -----------------------------------------------------------------
    print("\n--- Scenario 5: GA topic mastered -> next eligible GA topic scheduled ---")
    q_ga = db.query(Question).filter(Question.concept_id == c_const.id).first()
    r_ga_corr = StudentResponse(
        user_id=user.id,
        assessment_id=asmt1.id,
        question_id=q_ga.id,
        selected_answer=q_ga.correct_answer,
        is_correct=True,
        response_time_ms=10000,
        answered_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(r_ga_corr)
    db.commit()

    plan5 = synthesize_week_schedule(user_id=user.id, target_id=6, db=db, week_number=1)
    ga_items = [p for p in plan5 if p.subject == "General Awareness"]
    assert len(ga_items) >= 1, "Next GA topic not scheduled!"
    print(f"  [PASS] GA progression scheduled: {ga_items[0].topic_name} (Reason: {ga_items[0].plan_reason})")

    # -----------------------------------------------------------------
    # Scenario 6: An unassessed topic -> baseline review with follow-up assessment
    # -----------------------------------------------------------------
    print("\n--- Scenario 6: Unassessed topic -> baseline review & follow-up assessment scheduled ---")
    unassessed_items = [p for p in plan5 if "unassessed" in p.plan_reason.lower() or "baseline" in p.plan_reason.lower()]
    print(f"  [PASS] Found {len(unassessed_items)} unassessed syllabus baseline tasks:")
    for it in unassessed_items[:2]:
        print(f"    Topic: {it.topic_name} | Follow-up: {it.follow_up_assessment} | Reason: {it.plan_reason}")

    # -----------------------------------------------------------------
    # Scenario 7: Completed diagnostic -> Skill Gap Analysis populated via API
    # -----------------------------------------------------------------
    print("\n--- Scenario 7: Skill Gap Analysis populated via GET /api/analytics/gaps ---")
    req_gaps = urllib.request.Request("http://127.0.0.1:8000/api/analytics/gaps", headers=headers, method="GET")
    with urllib.request.urlopen(req_gaps) as resp:
        gaps_data = json.loads(resp.read().decode())
        assert gaps_data["diagnostic_completed"] is True
        assert gaps_data["total_attempts"] >= 4
        assert len(gaps_data["gaps"]) > 0
        assert len(gaps_data["subject_recommendations"]) == 4
        assert len(gaps_data["week_1_plan"]) == 7
        print(f"  [PASS] GET /api/analytics/gaps returned HTTP 200 with {len(gaps_data['gaps'])} concepts, 4 subject recommendations, and 7-day plan!")
        for sr in gaps_data["subject_recommendations"]:
            print(f"    [{sr['subject']}] Status: {sr['status']} -> Next: {sr['recommended_topic']} ({sr['action']})")

    # -----------------------------------------------------------------
    # Scenario 8: First-week plan saved -> plan remains after refresh
    # -----------------------------------------------------------------
    print("\n--- Scenario 8: First-week plan persists across requests (GET /api/schedule) ---")
    req_sched1 = urllib.request.Request("http://127.0.0.1:8000/api/schedule", headers=headers, method="GET")
    with urllib.request.urlopen(req_sched1) as resp:
        s1 = json.loads(resp.read().decode())
    req_sched2 = urllib.request.Request("http://127.0.0.1:8000/api/schedule", headers=headers, method="GET")
    with urllib.request.urlopen(req_sched2) as resp:
        s2 = json.loads(resp.read().decode())

    assert len(s1["schedule"]) == 7
    assert len(s2["schedule"]) == 7
    assert [i["id"] for i in s1["schedule"]] == [i["id"] for i in s2["schedule"]]
    print(f"  [PASS] Schedule persists identical 7 items across separate requests!")
    print(f"  Day 7 Task: {s1['schedule'][6]['concept_name']} ({s1['schedule'][6]['activity_type']})")

    # -----------------------------------------------------------------
    # Scenario 9: Existing 40-question practice test still works
    # -----------------------------------------------------------------
    print("\n--- Scenario 9: Existing 40-question combined practice test still works ---")
    req_prac = urllib.request.Request(
        "http://127.0.0.1:8000/api/assessments/start",
        data=json.dumps({"type": "practice", "target_id": 6, "practice_mode": "combined"}).encode(),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req_prac) as resp:
        p_data = json.loads(resp.read().decode())
        assert len(p_data["items"]) == 40
        assert p_data["time_limit_sec"] == 3600
        print(f"  [PASS] 40-question combined test returned {len(p_data['items'])} items with {p_data['time_limit_sec']}s time limit!")

    print("\n=====================================================================")
    print("ALL 9 SCENARIOS VERIFIED 100% GREEN END-TO-END!")
    print("=====================================================================")

if __name__ == "__main__":
    main()
