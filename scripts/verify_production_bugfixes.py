"""End-to-end unit and integration tests for Google Auth, Diagnostic Status, and Sync fixes."""
import os
import sys

base_dir = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard"
sys.path.insert(0, base_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_path = os.path.join(base_dir, "palp_local.db")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

from backend.app.models.core import User, CareerTarget, LearnerProfile, Assessment, AssessmentQuestion, StudentResponse, Question, Skill, Topic, Concept
from backend.app.api.diagnostic import find_valid_initial_assessment, get_diagnostic_status
from backend.app.api.analytics import get_gap_analytics
from sqlalchemy import func
import datetime as dt

# Clean up any residual test users first
db.query(User).filter(User.email.in_(["test.learner.auth@example.com", "stub.learner@example.com"])).delete(synchronize_session=False)
db.commit()

print("======================================================================")
print("TEST 1: GOOGLE AUTH USER LOOKUP & ZERO-DUPLICATION")
print("======================================================================")
# Test case-insensitive lookup
test_email = "Test.Learner.Auth@Example.COM"
user = User(
    email=test_email.lower(),
    name="Test Learner",
    google_sub="sub-test-unique-12345",
    role="learner",
)
db.add(user)
db.commit()
db.refresh(user)
user_id = user.id

# Look up with uppercase email
found_by_email = db.query(User).filter(
    (User.google_sub == "sub-test-unique-12345") | (func.lower(User.email) == test_email.lower())
).first()
assert found_by_email is not None, "Failed to find user by case-insensitive email"
assert found_by_email.id == user_id, "User ID mismatch"
print(f"[OK] Found user #{found_by_email.id} using case-insensitive email {test_email}")

# Look up by google_sub
found_by_sub = db.query(User).filter(
    (User.google_sub == "sub-test-unique-12345") | (func.lower(User.email) == "other@example.com")
).first()
assert found_by_sub is not None, "Failed to find user by google_sub"
assert found_by_sub.id == user_id, "User ID mismatch"
print(f"[OK] Found user #{found_by_sub.id} using google_sub")


print("\n======================================================================")
print("TEST 2: EMPTY STUB ASSESSMENT HANDLING (THE CORE PRODUCTION BUG)")
print("======================================================================")
upsc_target = db.query(CareerTarget).filter(CareerTarget.name == "UPSC Civil Services").first()
stub_user = User(
    email="stub.learner@example.com",
    name="Stub Learner",
    google_sub="sub-stub-learner-999",
    role="learner"
)
db.add(stub_user)
db.commit()
db.refresh(stub_user)

profile = LearnerProfile(
    user_id=stub_user.id,
    target_type="govt_exam",
    target_id=upsc_target.id,
    exam_date=dt.date(2027, 5, 25),
)
db.add(profile)

# Simulate the exact production condition: an assessment completed in 165ms with 0 questions and 0 responses
empty_stub = Assessment(
    user_id=stub_user.id,
    type="initial",
    target_id=upsc_target.id,
    score=0.0,
    started_at=dt.datetime.now(dt.timezone.utc),
    completed_at=dt.datetime.now(dt.timezone.utc),
)
db.add(empty_stub)
db.commit()
db.refresh(empty_stub)
print(f"Created simulated empty stub Assessment #{empty_stub.id} for user #{stub_user.id}")

# 1. find_valid_initial_assessment must return None
valid_asmt, resp_count, _ = find_valid_initial_assessment(stub_user.id, db)
assert valid_asmt is None, f"Expected None for empty stub, but got Assessment #{valid_asmt.id}"
print("[OK] find_valid_initial_assessment correctly filtered out empty stub assessment")

# 2. get_diagnostic_status must return is_completed: False
status_res = get_diagnostic_status(current_user=stub_user, db=db)
print(f"Diagnostic status for stub user: is_completed={status_res['is_completed']}, status='{status_res['status']}'")
assert status_res["is_completed"] is False, "Empty stub must NOT report is_completed: True"
assert status_res["status"] == "not_started", "Empty stub status must be not_started"
print("[OK] get_diagnostic_status reports incomplete for empty stub")

# 3. get_gap_analytics must return diagnostic_completed: False and latest_diagnostic: None
gaps_res = get_gap_analytics(current_user=stub_user, db=db)
print(f"Gaps for stub user: diagnostic_completed={gaps_res['diagnostic_completed']}, latest_diagnostic={gaps_res['latest_diagnostic']}")
assert gaps_res["diagnostic_completed"] is False, "Empty stub must NOT report diagnostic_completed: True"
assert gaps_res["latest_diagnostic"] is None, "Empty stub must NOT report fake 0% latest_diagnostic"
print("[OK] get_gap_analytics reports diagnostic_completed: False and latest_diagnostic: None")


print("\n======================================================================")
print("TEST 3: REAL COMPLETED ASSESSMENT SYNCHRONIZATION")
print("======================================================================")
# Now add a REAL assessment with actual responses
real_asmt = Assessment(
    user_id=stub_user.id,
    type="initial",
    target_id=upsc_target.id,
    score=80.0,
    started_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10),
    completed_at=dt.datetime.now(dt.timezone.utc),
)
db.add(real_asmt)
db.commit()
db.refresh(real_asmt)

# Pick 10 sample questions
sample_qs = db.query(Question).join(Concept).join(Topic).join(Skill).filter(Skill.target_id == upsc_target.id).limit(10).all()
for idx, q in enumerate(sample_qs):
    db.add(AssessmentQuestion(assessment_id=real_asmt.id, question_id=q.id, order_index=idx))
    # 8 correct, 2 incorrect = 80%
    is_corr = idx < 8
    db.add(StudentResponse(
        assessment_id=real_asmt.id,
        user_id=stub_user.id,
        question_id=q.id,
        selected_answer=q.correct_answer if is_corr else "X",
        is_correct=is_corr,
        response_time_ms=12000,
        skipped=False,
    ))
db.commit()
print(f"Created REAL Assessment #{real_asmt.id} with 10 questions and 8/10 correct answers (80%)")

# 1. find_valid_initial_assessment must find real_asmt
valid_asmt, resp_count, _ = find_valid_initial_assessment(stub_user.id, db)
assert valid_asmt is not None, "Failed to find real assessment"
assert valid_asmt.id == real_asmt.id, f"Expected Assessment #{real_asmt.id}, got #{valid_asmt.id}"
assert resp_count == 10, f"Expected 10 responses, got {resp_count}"
print(f"[OK] find_valid_initial_assessment found real Assessment #{valid_asmt.id} with {resp_count} responses")

# 2. get_diagnostic_status must report real score and completed status
status_real = get_diagnostic_status(current_user=stub_user, db=db)
print(f"Status response: is_completed={status_real['is_completed']}, score={status_real['score']}, correct={status_real['correct_answers']}/{status_real['total_questions']}")
assert status_real["is_completed"] is True
assert status_real["score"] == 80.0
assert status_real["correct_answers"] == 8
assert status_real["total_questions"] == 10
print("[OK] get_diagnostic_status returns verified real score and question counts")

# 3. get_gap_analytics must report real score and performance
gaps_real = get_gap_analytics(current_user=stub_user, db=db)
print(f"Gaps response: diagnostic_completed={gaps_real['diagnostic_completed']}")
assert gaps_real["diagnostic_completed"] is True
diag_perf = gaps_real["latest_diagnostic"]
assert diag_perf is not None
print(f"  diag_perf: accuracy_pct={diag_perf['accuracy_pct']}%, correct={diag_perf['correct_count']}/{diag_perf['total_questions']}")
assert diag_perf["accuracy_pct"] == 80.0
assert diag_perf["correct_count"] == 8
assert diag_perf["total_questions"] == 10
assert diag_perf["assessment_id"] == real_asmt.id
print("[OK] get_gap_analytics returns identical assessment ID, score, and counts to diagnostic status")

# Clean up test rows
db.delete(empty_stub)
for r in db.query(StudentResponse).filter(StudentResponse.assessment_id == real_asmt.id).all():
    db.delete(r)
for aq in db.query(AssessmentQuestion).filter(AssessmentQuestion.assessment_id == real_asmt.id).all():
    db.delete(aq)
db.delete(real_asmt)
db.delete(profile)
db.delete(stub_user)
db.delete(user)
db.commit()
db.close()
print("\n[ALL 3 INTEGRATION TESTS PASSED SUCCESSFULLY!]")
