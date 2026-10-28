"""Apply backend changes for auth, diagnostic status, analytics, and question generator."""
import os

base_dir = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard"

# 1. Update backend/app/api/auth.py
auth_path = os.path.join(base_dir, "backend", "app", "api", "auth.py")
with open(auth_path, "r", encoding="utf-8") as f:
    auth_text = f.read().replace("\r\n", "\n")

# Ensure sqlalchemy func is imported
if "from sqlalchemy import func" not in auth_text:
    auth_text = auth_text.replace("from sqlalchemy.orm import Session", "from sqlalchemy import func\nfrom sqlalchemy.orm import Session")

# Case-insensitive user lookup
old_lookup = 'user = db.query(User).filter((User.google_sub == sub) | (User.email == email)).first()'
new_lookup = 'user = db.query(User).filter((User.google_sub == sub) | (func.lower(User.email) == email.lower())).first()'
if old_lookup in auth_text:
    auth_text = auth_text.replace(old_lookup, new_lookup)

with open(auth_path, "w", encoding="utf-8") as f:
    f.write(auth_text)
print("[OK] backend/app/api/auth.py updated")

# 2. Update backend/app/services/question_generator.py
qgen_path = os.path.join(base_dir, "backend", "app", "services", "question_generator.py")
with open(qgen_path, "r", encoding="utf-8") as f:
    qgen_text = f.read().replace("\r\n", "\n")

old_qgen_create = """    # 3. Create Assessment record
    assessment = Assessment("""

new_qgen_create = """    if not final_db_questions:
        raise ValueError(f"No questions available in question bank for target '{target.name}'.")

    # 3. Create Assessment record
    assessment = Assessment("""

if old_qgen_create in qgen_text and "if not final_db_questions:" not in qgen_text:
    qgen_text = qgen_text.replace(old_qgen_create, new_qgen_create)
    with open(qgen_path, "w", encoding="utf-8") as f:
        f.write(qgen_text)
    print("[OK] backend/app/services/question_generator.py updated")
else:
    print("question_generator.py already updated or not matched")

# 3. Update backend/app/api/diagnostic.py
diag_path = os.path.join(base_dir, "backend", "app", "api", "diagnostic.py")
with open(diag_path, "r", encoding="utf-8") as f:
    diag_text = f.read().replace("\r\n", "\n")

helper_fn = '''
def find_valid_initial_assessment(user_id: int, db: Session) -> tuple[Assessment | None, int, int]:
    """Returns the most recent valid completed initial diagnostic assessment,
    along with (response_count, question_count).
    An assessment is only considered valid if it has actual responses (or linked questions).
    Empty 0-question/0-response stubs created by interrupted runs are filtered out.
    """
    completed_asmts = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == user_id,
            Assessment.type == "initial",
            Assessment.completed_at.is_not(None),
        )
        .order_by(Assessment.completed_at.desc())
    ).scalars().all()

    for asmt in completed_asmts:
        resp_count = db.execute(
            select(func.count(StudentResponse.id))
            .where(StudentResponse.assessment_id == asmt.id)
        ).scalar() or 0
        aq_count = db.execute(
            select(func.count(AssessmentQuestion.id))
            .where(AssessmentQuestion.assessment_id == asmt.id)
        ).scalar() or 0

        # Legacy compatibility check: If assessment has no direct assessment_id responses,
        # check if student responses exist for this user in the same time window
        if resp_count == 0 and asmt.started_at and asmt.completed_at:
            time_window_resps = db.execute(
                select(StudentResponse).where(
                    StudentResponse.user_id == user_id,
                    StudentResponse.answered_at >= asmt.started_at,
                    StudentResponse.answered_at <= asmt.completed_at + dt.timedelta(seconds=60),
                )
            ).scalars().all()
            if time_window_resps:
                for r in time_window_resps:
                    r.assessment_id = asmt.id
                db.commit()
                resp_count = len(time_window_resps)

        if resp_count > 0:
            return asmt, resp_count, aq_count

    return None, 0, 0
'''

if "def find_valid_initial_assessment" not in diag_text:
    diag_text = diag_text.replace("class DiagnosticSubmitIn(BaseModel):", helper_fn.strip() + "\n\n\nclass DiagnosticSubmitIn(BaseModel):")

# Update get_diagnostic_status implementation
old_get_status = '''@router.get("/status")
def get_diagnostic_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns persistent diagnostic completion status for the authenticated user."""
    completed_asmt = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == current_user.id,
            Assessment.type == "initial",
            Assessment.completed_at.is_not(None),
        )
        .order_by(Assessment.completed_at.desc())
    ).scalars().first()

    if completed_asmt:
        total_questions = db.execute(
            select(func.count(AssessmentQuestion.id))
            .where(AssessmentQuestion.assessment_id == completed_asmt.id)
        ).scalar() or 0

        correct_count = db.execute(
            select(func.count(StudentResponse.id))
            .where(
                StudentResponse.assessment_id == completed_asmt.id,
                StudentResponse.user_id == current_user.id,
                StudentResponse.is_correct.is_(True),
            )
        ).scalar() or 0

        target = db.get(CareerTarget, completed_asmt.target_id)

        return {
            "is_completed": True,
            "status": "completed",
            "assessment_id": completed_asmt.id,
            "completed_at": completed_asmt.completed_at.isoformat() if completed_asmt.completed_at else None,
            "score": completed_asmt.score,
            "total_questions": total_questions if total_questions > 0 else 10,
            "correct_answers": correct_count,
            "target_id": completed_asmt.target_id,
            "target_name": target.name if target else "Unknown",
        }'''

new_get_status = '''@router.get("/status")
def get_diagnostic_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns persistent diagnostic completion status for the authenticated user.
    Only treats an assessment as completed if it contains verified questions and responses.
    """
    valid_asmt, resp_count, aq_count = find_valid_initial_assessment(current_user.id, db)

    if valid_asmt:
        correct_count = db.execute(
            select(func.count(StudentResponse.id))
            .where(
                StudentResponse.assessment_id == valid_asmt.id,
                StudentResponse.user_id == current_user.id,
                StudentResponse.is_correct.is_(True),
            )
        ).scalar() or 0

        target = db.get(CareerTarget, valid_asmt.target_id)
        total_q = resp_count if resp_count > 0 else (aq_count if aq_count > 0 else 10)
        score_val = valid_asmt.score if valid_asmt.score is not None else round((correct_count / total_q) * 100, 1)

        return {
            "is_completed": True,
            "status": "completed",
            "assessment_id": valid_asmt.id,
            "completed_at": valid_asmt.completed_at.isoformat() if valid_asmt.completed_at else None,
            "score": score_val,
            "total_questions": total_q,
            "correct_answers": correct_count,
            "target_id": valid_asmt.target_id,
            "target_name": target.name if target else "Unknown",
            "has_valid_responses": resp_count > 0,
        }'''

if old_get_status in diag_text:
    diag_text = diag_text.replace(old_get_status, new_get_status)

# Update return for not_started to include has_valid_responses
old_not_started = '''    return {
        "is_completed": False,
        "status": "not_started",
        "assessment_id": None,
        "completed_at": None,
        "score": None,
        "total_questions": 10,
        "correct_answers": 0,
        "target_id": target_id,
        "target_name": target.name if target else "Unknown",
    }'''

new_not_started = '''    return {
        "is_completed": False,
        "status": "not_started",
        "assessment_id": None,
        "completed_at": None,
        "score": None,
        "total_questions": 10,
        "correct_answers": 0,
        "target_id": target_id,
        "target_name": target.name if target else "Unknown",
        "has_valid_responses": False,
    }'''

if old_not_started in diag_text:
    diag_text = diag_text.replace(old_not_started, new_not_started)

# Update start_diagnostic check
old_start_check = '''    # Check if user already completed an initial diagnostic
    completed_asmt = db.execute(
        select(Assessment).where(
            Assessment.user_id == current_user.id,
            Assessment.type == "initial",
            Assessment.completed_at.is_not(None),
        ).order_by(Assessment.completed_at.desc())
    ).scalars().first()

    if completed_asmt and not req.retake:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial diagnostic assessment has already been completed.",
        )'''

new_start_check = '''    # Check if user already completed a valid initial diagnostic with actual responses
    valid_asmt, resp_count, _ = find_valid_initial_assessment(current_user.id, db)

    if valid_asmt and not req.retake:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial diagnostic assessment has already been completed.",
        )'''

if old_start_check in diag_text:
    diag_text = diag_text.replace(old_start_check, new_start_check)

# Update submit_diagnostic empty check
old_submit_start = '''    answered_at = dt.datetime.now(dt.timezone.utc)
    target = db.get(CareerTarget, assessment.target_id)'''

new_submit_start = '''    if not req.responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit an initial diagnostic with zero responses.",
        )

    answered_at = dt.datetime.now(dt.timezone.utc)
    target = db.get(CareerTarget, assessment.target_id)'''

if old_submit_start in diag_text and "if not req.responses:" not in diag_text:
    diag_text = diag_text.replace(old_submit_start, new_submit_start)

with open(diag_path, "w", encoding="utf-8") as f:
    f.write(diag_text)
print("[OK] backend/app/api/diagnostic.py updated")

# 4. Update backend/app/api/analytics.py
analytics_path = os.path.join(base_dir, "backend", "app", "api", "analytics.py")
with open(analytics_path, "r", encoding="utf-8") as f:
    analytics_text = f.read().replace("\r\n", "\n")

if "from backend.app.api.diagnostic import find_valid_initial_assessment" not in analytics_text:
    analytics_text = analytics_text.replace(
        "from backend.app.models.core import (",
        "from backend.app.api.diagnostic import find_valid_initial_assessment\nfrom backend.app.models.core import ("
    )

old_analytics_diag = '''    # Fetch latest completed diagnostic
    latest_diagnostic = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == current_user.id,
            Assessment.type == "initial",
            Assessment.completed_at.is_not(None),
        )
        .order_by(Assessment.completed_at.desc())
    ).scalars().first()'''

new_analytics_diag = '''    # Fetch latest completed diagnostic with verified responses
    latest_diagnostic, diag_resp_count, _ = find_valid_initial_assessment(current_user.id, db)'''

if old_analytics_diag in analytics_text:
    analytics_text = analytics_text.replace(old_analytics_diag, new_analytics_diag)

old_diag_perf_block = '''    # Diagnostic performance summary
    diag_perf = None
    if latest_diagnostic:
        diag_resps = db.execute(
            select(StudentResponse, Question.concept_id)
            .join(Question, StudentResponse.question_id == Question.id)
            .where(StudentResponse.assessment_id == latest_diagnostic.id)
        ).all()
        correct_count = sum(1 for r, _ in diag_resps if r.is_correct)
        total_q = len(diag_resps) or 10
        acc_pct = round((correct_count / total_q) * 100, 1)
        demonstrated_distinct = len(set(cid for r, cid in diag_resps if r.is_correct))
        total_syllabus_topics = len(set(gi["topic_name"] for gi in gap_items))
        cov_readiness = round((demonstrated_distinct / total_syllabus_topics) * 100, 1) if total_syllabus_topics > 0 else 0.0

        diag_perf = {
            "assessment_id": latest_diagnostic.id,
            "score": round(latest_diagnostic.score, 1) if latest_diagnostic.score is not None else 0.0,
            "accuracy_pct": acc_pct,
            "correct_count": correct_count,
            "total_questions": total_q,
            "completed_at": latest_diagnostic.completed_at.isoformat() if latest_diagnostic.completed_at else None,
            "distinct_topics_demonstrated": demonstrated_distinct,
            "total_syllabus_topics": total_syllabus_topics,
            "topic_coverage_readiness": cov_readiness,
        }'''

new_diag_perf_block = '''    # Diagnostic performance summary
    diag_perf = None
    if latest_diagnostic and diag_resp_count > 0:
        diag_resps = db.execute(
            select(StudentResponse, Question.concept_id)
            .join(Question, StudentResponse.question_id == Question.id)
            .where(StudentResponse.assessment_id == latest_diagnostic.id)
        ).all()
        if diag_resps:
            correct_count = sum(1 for r, _ in diag_resps if r.is_correct)
            total_q = len(diag_resps)
            acc_pct = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0
            demonstrated_distinct = len(set(cid for r, cid in diag_resps if r.is_correct))
            total_syllabus_topics = len(set(gi["topic_name"] for gi in gap_items))
            cov_readiness = round((demonstrated_distinct / total_syllabus_topics) * 100, 1) if total_syllabus_topics > 0 else 0.0

            diag_perf = {
                "assessment_id": latest_diagnostic.id,
                "score": round(latest_diagnostic.score, 1) if latest_diagnostic.score is not None else acc_pct,
                "accuracy_pct": acc_pct,
                "correct_count": correct_count,
                "total_questions": total_q,
                "completed_at": latest_diagnostic.completed_at.isoformat() if latest_diagnostic.completed_at else None,
                "distinct_topics_demonstrated": demonstrated_distinct,
                "total_syllabus_topics": total_syllabus_topics,
                "topic_coverage_readiness": cov_readiness,
            }'''

if old_diag_perf_block in analytics_text:
    analytics_text = analytics_text.replace(old_diag_perf_block, new_diag_perf_block)

old_diag_comp_line = '"diagnostic_completed": bool(latest_diagnostic),'
new_diag_comp_line = '"diagnostic_completed": bool(latest_diagnostic and diag_resp_count > 0),'
if old_diag_comp_line in analytics_text:
    analytics_text = analytics_text.replace(old_diag_comp_line, new_diag_comp_line)

with open(analytics_path, "w", encoding="utf-8") as f:
    f.write(analytics_text)
print("[OK] backend/app/api/analytics.py updated")
