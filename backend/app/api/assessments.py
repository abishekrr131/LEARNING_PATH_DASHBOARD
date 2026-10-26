"""Assessment API Router for Diagnostic, Special Test Mode, Verification, and Practice."""
from __future__ import annotations

import datetime as dt
import logging
import math
import random
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import (
    Assessment,
    AssessmentQuestion,
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningSchedule,
    Question,
    RootCauseAnalysis,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    TopicPerformance,
    User,
    VerificationProbe,
)
from backend.app.schemas.assessment import (
    AssessmentStartIn,
    AssessmentStartOut,
    AssessmentSubmitIn,
    AssessmentSubmitOut,
    ConceptScore,
    ItemOut,
    RootCauseEvaluateIn,
    RootCauseEvaluateOut,
    RootCauseSubQuestionsIn,
    RootCauseSubQuestionsOut,
    SpecialBlockEndIn,
    SpecialBlockEndOut,
    SpecialNextBlockIn,
    SpecialNextBlockOut,
)
from backend.app.services.question_generator import (
    classify_root_cause_gap,
    generate_root_cause_sub_questions,
    to_options_list,
)
from backend.app.services.root_cause import (
    get_ancestors_within_hops,
    select_verification_probes,
    rank_root_cause_candidates,
    attention_entropy,
    present_as_mode,
)
from backend.app.services.scoring import (
    expected_response_time,
    gap_band,
    gap_score,
    time_ratio,
)
from ml.graph.dag_validator import SimpleDiGraph

router = APIRouter()

# Special Test Configuration Constants
MAIN_Q_TIME_SEC = 30
SUB_Q_COUNT = 3
SUB_Q_TIME_SEC = 20


@router.get("/active")
def get_active_assessment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Checks whether the user currently has an unfinished scored assessment.
    Used by the Gemini AI layer to enforce total test-time suppression.
    """
    scored_types = ["initial", "special", "verification", "followup"]
    active = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == current_user.id,
            Assessment.completed_at.is_(None),
            Assessment.type.in_(scored_types),
        )
        .order_by(Assessment.started_at.desc())
    ).scalars().first()

    return {
        "has_active_test": active is not None,
        "assessment_id": active.id if active else None,
        "type": active.type if active else None,
    }


@router.post("/start", response_model=AssessmentStartOut)
def start_assessment(
    req: AssessmentStartIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initiates an assessment session:
    - initial: exactly 10 questions proportional to skill weight, easy -> hard, approved only
    - special: Special Test Mode with timed blocks (5 or 10 main questions)
    - verification: 2-3 probes for suspected gaps or epsilon-random checks
    - practice / followup: practice rep or trial evaluation
    """
    target = db.get(CareerTarget, req.target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    # Get all target skills and concepts
    skills = db.execute(
        select(Skill).where(Skill.target_id == target.id).order_by(Skill.weight.desc())
    ).scalars().all()

    if not skills:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target has no configured skills")

    # Fetch available approved questions
    # Fallback to pending if approved is empty in test environment
    def get_candidate_questions(concept_filter=None):
        q_filter = [Question.review_status == "approved"]
        if concept_filter:
            q_filter.append(Question.concept_id.in_(concept_filter))

        approved_qs = db.execute(
            select(Question, Concept.name)
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(Skill.target_id == target.id, *q_filter)
        ).all()

        if not approved_qs:
            # Fallback for unapproved queue in dev
            approved_qs = db.execute(
                select(Question, Concept.name)
                .join(Concept, Question.concept_id == Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .join(Skill, Topic.skill_id == Skill.id)
                .where(Skill.target_id == target.id)
            ).all()
        return approved_qs

    selected_questions: list[tuple[Question, str]] = []

    if req.type == "initial":
        # Exactly 10 questions, allocated using largest-remainder rounding across skills by syllabus weight
        # Random within skill, ordered easy -> hard
        from backend.app.api.diagnostic import allocate_questions_largest_remainder

        skill_quotas = allocate_questions_largest_remainder(skills, total_items=10)
        selected_questions = []

        for s in skills:
            quota = skill_quotas.get(s.id, 0)
            if quota <= 0:
                continue

            approved_qs = db.execute(
                select(Question, Concept.name)
                .join(Concept, Question.concept_id == Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .join(Skill, Topic.skill_id == Skill.id)
                .where(
                    Skill.id == s.id,
                    Question.review_status == "approved",
                )
            ).all()

            if len(approved_qs) < quota:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Question bank not seeded: Insufficient approved questions for skill '{s.name}'. "
                        f"Required {quota}, found {len(approved_qs)}."
                    ),
                )

            sample = random.sample(approved_qs, quota)
            selected_questions.extend(sample)

        selected_questions.sort(key=lambda x: x[0].difficulty_b)

    elif req.type == "special":
        # Main question block count: 5 or 10
        main_count = req.main_count if req.main_count in (5, 10) else 5
        all_pool = get_candidate_questions()
        random.shuffle(all_pool)
        selected_questions = all_pool[:main_count]

    elif req.type == "verification":
        # 2-3 items for suspected gaps
        all_pool = get_candidate_questions()
        random.shuffle(all_pool)
        selected_questions = all_pool[:3]

    elif req.type == "practice":
        from backend.app.services.question_generator import generate_practice_questions

        practice_mode = req.practice_mode or "untimed"
        count = req.count or (40 if practice_mode == "combined" else (10 if practice_mode == "speed" else 5))
        try:
            asmt_id, practice_items = generate_practice_questions(
                db=db,
                target=target,
                current_user_id=current_user.id,
                concept_id=req.concept_id,
                topic_id=req.topic_id,
                count=count,
                practice_mode=practice_mode,
            )
            time_limit = 3600 if practice_mode == "combined" else (90 if practice_mode == "speed" else None)
            return AssessmentStartOut(
                assessment_id=asmt_id,
                type="practice",
                items=[ItemOut(**it) for it in practice_items],
                time_limit_sec=time_limit,
                practice_mode=practice_mode,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Practice session initialization error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not initialize practice session: {str(e)}",
            )

    else:
        # Followup or generic
        all_pool = get_candidate_questions()
        random.shuffle(all_pool)
        selected_questions = all_pool[:10]

    # Create assessment in database
    assessment = Assessment(
        user_id=current_user.id,
        type=req.type,
        target_id=target.id,
        started_at=dt.datetime.now(dt.timezone.utc),
        completed_at=None,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Record assessment questions
    items_out: list[ItemOut] = []
    for order_idx, (q, cname) in enumerate(selected_questions):
        phase = "main" if req.type == "special" else None
        time_limit = MAIN_Q_TIME_SEC if req.type == "special" else None

        db.add(
            AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=q.id,
                order_index=order_idx,
                phase=phase,
                block_index=order_idx if req.type == "special" else None,
            )
        )
        items_out.append(
            ItemOut(
                question_id=q.id,
                concept_id=q.concept_id,
                concept_name=cname,
                order_index=order_idx,
                question_text=q.question_text,
                options=q.options,
                difficulty_b=q.difficulty_b,
                phase=phase,
                time_limit_sec=time_limit,
                block_index=order_idx if req.type == "special" else None,
                source=getattr(q, "source", "curated") or "curated",
            )
        )

    db.commit()

    return AssessmentStartOut(
        assessment_id=assessment.id,
        type=req.type,
        items=items_out,
        time_limit_sec=MAIN_Q_TIME_SEC if req.type == "special" else None,
        total_blocks=len(items_out) if req.type == "special" else None,
    )


@router.post("/{assessment_id}/next-block", response_model=SpecialNextBlockOut)
def get_special_next_block(
    assessment_id: int,
    req: SpecialNextBlockIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dynamically serves 3 sub-questions following a main question in Special Test Mode.
    Server decides sub-question selection based on main question outcome (wrong/timeout -> prerequisite bias).
    """
    assessment = db.get(Assessment, assessment_id)
    if not assessment or assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    main_q = db.get(Question, req.main_response.question_id)
    if not main_q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Server authoritative timestamp and correctness validation
    answered_at = dt.datetime.now(dt.timezone.utc)
    is_correct = (
        not req.main_response.skipped
        and not req.main_response.timed_out
        and (req.main_response.selected_answer == main_q.correct_answer)
    )

    # Save main response
    main_resp = StudentResponse(
        user_id=current_user.id,
        assessment_id=assessment.id,
        question_id=main_q.id,
        selected_answer=req.main_response.selected_answer,
        is_correct=is_correct,
        response_time_ms=req.main_response.response_time_ms,
        skipped=req.main_response.skipped,
        attempt_no=req.main_response.attempt_no,
        phase="main",
        time_limit_ms=MAIN_Q_TIME_SEC * 1000,
        timed_out=req.main_response.timed_out,
        answered_at=answered_at,
    )
    db.add(main_resp)
    db.commit()
    db.refresh(main_resp)

    # Build DAG for prerequisite lookup
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    ancestors = get_ancestors_within_hops(g, main_q.concept_id, max_hops=2)

    # Sub-question selection logic
    epsilon_probe = random.random() < 0.10
    trigger: Literal["prerequisite_bias", "difficulty_boost", "epsilon_random"] = "prerequisite_bias"
    target_concept_ids: list[int] = []

    if epsilon_probe:
        # Epsilon-random probe across unflagged concepts
        all_concepts = db.execute(select(Concept.id)).scalars().all()
        target_concept_ids = random.sample(all_concepts, min(3, len(all_concepts)))
        trigger = "epsilon_random"
        # Record verification probe trigger
        for cid in target_concept_ids:
            db.add(
                VerificationProbe(
                    user_id=current_user.id,
                    concept_id=cid,
                    trigger="epsilon_random",
                )
            )
        db.commit()

    elif not is_correct or req.main_response.timed_out:
        # Wrong or Timed Out -> 3-stage Root-Cause Sub-Questions (Formula, Substitution, Timed Calculation)
        trigger = "prerequisite_bias"
        for cid in (list(ancestors.keys())[:2] if ancestors else [main_q.concept_id]):
            db.add(
                VerificationProbe(
                    user_id=current_user.id,
                    concept_id=cid,
                    trigger="model_flag",
                )
            )

        concept = db.get(Concept, main_q.concept_id)
        topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None
        tname = topic.name if topic else (concept.name if concept else "Topic")
        cname = concept.name if concept else "Concept"

        from ai.gemini_client import GeminiClient
        client = GeminiClient()
        generated_sub_specs = generate_root_cause_sub_questions(
            topic_name=tname,
            concept_name=cname,
            main_question_stem=main_q.question_text,
            gemini_client=client,
        )

        sub_items_out: list[ItemOut] = []
        for s_idx, spec in enumerate(generated_sub_specs):
            sub_q = Question(
                concept_id=main_q.concept_id,
                question_text=spec["stem"],
                options_json={opt["key"]: opt["text"] for opt in spec["options"]},
                correct_answer=spec["correct_option"],
                explanation=spec.get("explanation", ""),
                difficulty_hint=-0.2 + (s_idx * 0.2),
                source="gemini",
                review_status="generated",
            )
            db.add(sub_q)
            db.flush()
            sub_items_out.append(
                ItemOut(
                    question_id=sub_q.id,
                    concept_id=sub_q.concept_id,
                    concept_name=cname,
                    order_index=s_idx,
                    question_text=sub_q.question_text,
                    options=spec["options"],
                    difficulty_b=sub_q.difficulty_b,
                    phase="sub",
                    time_limit_sec=spec.get("time_limit_sec", 20 if s_idx == 2 else 30),
                    block_index=req.block_index,
                    source="gemini",
                )
            )
        db.commit()
        return SpecialNextBlockOut(
            assessment_id=assessment.id,
            block_index=req.block_index,
            main_response_id=main_resp.id,
            sub_questions=sub_items_out,
            trigger=trigger,
        )
    else:
        # Correct -> BIAS TOWARD SAME CONCEPT AT HIGHER DIFFICULTY
        trigger = "difficulty_boost"
        target_concept_ids = [main_q.concept_id]

    # Query approved sub-questions
    sub_qs = db.execute(
        select(Question, Concept.name)
        .join(Concept, Question.concept_id == Concept.id)
        .where(
            Question.concept_id.in_(target_concept_ids),
            Question.id != main_q.id,
            Question.review_status == "approved",
        )
    ).all()

    if len(sub_qs) < SUB_Q_COUNT:
        # Fallback to any questions in target concepts
        sub_qs = db.execute(
            select(Question, Concept.name)
            .join(Concept, Question.concept_id == Concept.id)
            .where(
                Question.concept_id.in_(target_concept_ids),
                Question.id != main_q.id,
            )
        ).all()

    if len(sub_qs) < SUB_Q_COUNT:
        # Fallback to approved bank questions across learner's target curriculum
        existing_ids = {sq[0].id for sq in sub_qs} | {main_q.id}
        curriculum_qs = db.execute(
            select(Question, Concept.name)
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(
                Skill.target_id == assessment.target_id,
                Question.id.not_in(existing_ids),
                Question.review_status == "approved",
            )
        ).all()
        random.shuffle(curriculum_qs)
        sub_qs = list(sub_qs) + curriculum_qs[: (SUB_Q_COUNT - len(sub_qs))]

    # Pick up to SUB_Q_COUNT
    random.shuffle(sub_qs)
    chosen_sub = sub_qs[:SUB_Q_COUNT]

    sub_items_out: list[ItemOut] = []
    for s_idx, (sq, cname) in enumerate(chosen_sub):
        sub_items_out.append(
            ItemOut(
                question_id=sq.id,
                concept_id=sq.concept_id,
                concept_name=cname,
                order_index=s_idx,
                question_text=sq.question_text,
                options=sq.options,
                difficulty_b=sq.difficulty_b,
                phase="sub",
                time_limit_sec=SUB_Q_TIME_SEC,
                block_index=req.block_index,
                source=getattr(sq, "source", "curated") or "curated",
            )
        )

    return SpecialNextBlockOut(
        assessment_id=assessment.id,
        block_index=req.block_index,
        main_response_id=main_resp.id,
        sub_questions=sub_items_out,
        trigger=trigger,
    )


@router.post("/{assessment_id}/block-end", response_model=SpecialBlockEndOut)
def record_special_block_end(
    assessment_id: int,
    req: SpecialBlockEndIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Processes sub-responses for a Special Test block, evaluates weak prerequisites,
    and returns block-end diagnostic summary.
    """
    main_resp = db.get(StudentResponse, req.main_response_id)
    answered_at = dt.datetime.now(dt.timezone.utc)

    sub_results = []
    weak_prereq_name = None

    for sub_r in req.sub_responses:
        sub_q = db.get(Question, sub_r.question_id)
        if not sub_q:
            continue

        is_sub_correct = (
            not sub_r.skipped
            and not sub_r.timed_out
            and (sub_r.selected_answer == sub_q.correct_answer)
        )

        db_sub_resp = StudentResponse(
            user_id=current_user.id,
            assessment_id=assessment_id,
            question_id=sub_q.id,
            selected_answer=sub_r.selected_answer,
            is_correct=is_sub_correct,
            response_time_ms=sub_r.response_time_ms,
            skipped=sub_r.skipped,
            attempt_no=sub_r.attempt_no,
            phase="sub",
            parent_response_id=main_resp.id if main_resp else None,
            time_limit_ms=SUB_Q_TIME_SEC * 1000,
            timed_out=sub_r.timed_out,
            answered_at=answered_at,
        )
        db.add(db_sub_resp)

        concept = db.get(Concept, sub_q.concept_id)
        cname = concept.name if concept else f"Concept {sub_q.concept_id}"

        if not is_sub_correct and not weak_prereq_name:
            weak_prereq_name = cname

        sub_results.append({
            "question_id": sub_q.id,
            "concept_name": cname,
            "is_correct": is_sub_correct,
            "timed_out": sub_r.timed_out,
            "skipped": sub_r.skipped,
            "response_time_ms": sub_r.response_time_ms,
        })

    classification = None
    if len(sub_results) >= 3:
        sub_0_corr = sub_results[0]["is_correct"]
        sub_1_corr = sub_results[1]["is_correct"]
        sub_2_corr = sub_results[2]["is_correct"]
        sub_2_time = sub_results[2]["response_time_ms"]
        classification = classify_root_cause_gap(
            formula_correct=sub_0_corr,
            substitution_correct=sub_1_corr,
            calculation_correct=sub_2_corr,
            calculation_time_ms=sub_2_time,
            time_threshold_ms=20000,
        )

        main_concept = db.get(Concept, main_resp.question.concept_id) if (main_resp and main_resp.question) else None
        main_topic = db.get(Topic, main_concept.topic_id) if (main_concept and main_concept.topic_id) else None

        if main_resp and (not main_resp.is_correct or main_resp.timed_out):
            rc_entry = RootCauseAnalysis(
                user_id=current_user.id,
                current_concept_id=main_resp.question.concept_id,
                candidate_concept_id=main_resp.question.concept_id,
                root_score=0.90 if classification["all_three_failed"] else 0.75,
                attention_alpha=0.85,
                attention_entropy=0.20,
                rank=1,
                evidence_json={
                    "topic_id": main_topic.id if main_topic else None,
                    "topic_name": main_topic.name if main_topic else (main_concept.name if main_concept else "Topic"),
                    "concept_name": main_concept.name if main_concept else "Concept",
                    "cognitive_gap": classification,
                    "main_question_stem": main_resp.question.question_text if main_resp.question else "",
                },
                model_version="root_cause_sub_q_v1",
            )
            db.add(rc_entry)

    db.commit()

    return SpecialBlockEndOut(
        block_index=req.block_index,
        main_correct=main_resp.is_correct if main_resp else False,
        main_timed_out=main_resp.timed_out if main_resp else False,
        sub_results=sub_results,
        suspected_weak_prerequisite=weak_prereq_name,
        cognitive_gap=classification,
        gap_type=classification["gap_type"] if classification else None,
        study_task=classification["study_task"] if classification else None,
    )


@router.post("/{assessment_id}/submit", response_model=AssessmentSubmitOut)
def submit_assessment(
    assessment_id: int,
    req: AssessmentSubmitIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits and scores assessment responses:
    - Server stamps answered_at
    - Computes Formula 12 gap score per concept
    - Updates TopicPerformance and StudentMastery
    - Determines cold-start flag (<20 learner interactions)
    """
    assessment = db.get(Assessment, assessment_id)
    if not assessment or assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    answered_at = dt.datetime.now(dt.timezone.utc)
    responses_by_concept: dict[int, list[dict[str, Any]]] = {}

    correct_count = 0
    skip_count = 0
    timed_out_count = 0
    total_time_ratio = 0.0

    for r in req.responses:
        q = db.get(Question, r.question_id)
        if not q:
            continue

        is_corr = (not r.skipped and not r.timed_out and (r.selected_answer == q.correct_answer))
        if is_corr:
            correct_count += 1
        if r.skipped:
            skip_count += 1
        if r.timed_out:
            timed_out_count += 1

        exp_time = expected_response_time(q.difficulty_b)
        tr = time_ratio(r.response_time_ms, exp_time)
        total_time_ratio += tr

        # Insert student response
        db_resp = StudentResponse(
            user_id=current_user.id,
            assessment_id=assessment.id,
            question_id=q.id,
            selected_answer=r.selected_answer,
            is_correct=is_corr,
            response_time_ms=r.response_time_ms,
            skipped=r.skipped,
            attempt_no=r.attempt_no,
            phase=r.phase,
            parent_response_id=r.parent_response_id,
            timed_out=r.timed_out,
            answered_at=answered_at,
        )
        db.add(db_resp)

        if q.concept_id not in responses_by_concept:
            responses_by_concept[q.concept_id] = []
        responses_by_concept[q.concept_id].append({
            "is_correct": is_corr,
            "skipped": r.skipped,
            "timed_out": r.timed_out,
            "time_ratio": tr,
            "response_time_ms": r.response_time_ms,
        })

    # Historical interaction count for cold-start flag
    hist_count = db.execute(
        select(func.count(StudentResponse.id)).where(StudentResponse.user_id == current_user.id)
    ).scalar() or 0
    cold_start = hist_count < 20

    # Compute F12 Gap Scores per Concept
    concept_scores: list[ConceptScore] = []
    probe_queue: list[int] = []

    for c_id, item_resps in responses_by_concept.items():
        concept = db.get(Concept, c_id)
        cname = concept.name if concept else f"Concept {c_id}"

        c_correct = sum(1 for x in item_resps if x["is_correct"])
        c_skips = sum(1 for x in item_resps if x["skipped"])
        c_accuracy = c_correct / len(item_resps)
        c_skip_rate = c_skips / len(item_resps)
        c_mean_tr = sum(x["time_ratio"] for x in item_resps) / len(item_resps)

        # Historical mastery if present
        hist_m_row = db.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == current_user.id,
                StudentMastery.concept_id == c_id,
            )
        ).scalar_one_or_none()
        hist_m = hist_m_row.mastery_score if hist_m_row else 0.50

        # Calculate F12 Gap Score
        g_c = gap_score(
            accuracy=c_accuracy,
            time_ratio_val=c_mean_tr,
            skip_rate=c_skip_rate,
            hist_mastery=hist_m,
        )
        band = gap_band(g_c)

        if band in ("moderate", "weak"):
            probe_queue.append(c_id)

        # Update or create student mastery
        new_mastery = max(0.05, min(0.95, 1.0 - g_c))
        if hist_m_row:
            hist_m_row.mastery_score = new_mastery
            hist_m_row.confidence = min(0.95, hist_m_row.confidence + 0.1)
            hist_m_row.updated_at = answered_at
        else:
            db.add(
                StudentMastery(
                    user_id=current_user.id,
                    concept_id=c_id,
                    mastery_score=new_mastery,
                    confidence=0.40,
                    model_version="f12_baseline",
                    updated_at=answered_at,
                )
            )

        # Update TopicPerformance
        if concept and concept.topic_id:
            tp_row = db.execute(
                select(TopicPerformance).where(
                    TopicPerformance.user_id == current_user.id,
                    TopicPerformance.topic_id == concept.topic_id,
                )
            ).scalar_one_or_none()
            if tp_row:
                tp_row.accuracy = (tp_row.accuracy + c_accuracy) / 2.0
                tp_row.gap_score = (tp_row.gap_score + g_c) / 2.0
                tp_row.band = gap_band(tp_row.gap_score)
                tp_row.updated_at = answered_at
            else:
                db.add(
                    TopicPerformance(
                        user_id=current_user.id,
                        topic_id=concept.topic_id,
                        accuracy=c_accuracy,
                        avg_time_ms=int(sum(x["response_time_ms"] for x in item_resps) / len(item_resps)),
                        skip_rate=c_skip_rate,
                        gap_score=g_c,
                        band=band,
                        updated_at=answered_at,
                    )
                )

        concept_scores.append(
            ConceptScore(
                concept_id=c_id,
                concept_name=cname,
                accuracy=round(c_accuracy, 3),
                mean_time_ratio=round(c_mean_tr, 3),
                skip_rate=round(c_skip_rate, 3),
                gap_score=round(g_c, 3),
                band=band,
            )
        )

    # Complete assessment
    total_q = len(req.responses)
    final_score = (correct_count / total_q) * 100.0 if total_q > 0 else 0.0
    assessment.score = final_score
    assessment.completed_at = answered_at

    extra_readiness_pct = None
    extra_skill_breakdown = None
    extra_weak_topics = None
    extra_roadmap = None

    if assessment.type == "initial":
        today = dt.date.today()
        from backend.app.services.scoring import review_interval, readiness_score
        from backend.app.services.path import build_personalized_path
        from backend.app.services.root_cause import rank_root_cause_candidates
        from backend.app.services.question_generator import synthesize_week_schedule

        synthesize_week_schedule(
            user_id=current_user.id,
            target_id=assessment.target_id,
            db=db,
            week_number=1,
            start_date=today,
        )

        # Build skill breakdown & readiness score
        skills = db.execute(
            select(Skill).where(Skill.target_id == assessment.target_id)
        ).scalars().all()
        masteries = db.execute(
            select(StudentMastery).where(StudentMastery.user_id == current_user.id)
        ).scalars().all()
        mastery_map = {m.concept_id: m.mastery_score for m in masteries}
        all_cs = db.execute(select(Concept)).scalars().all()
        name_map = {c.id: c.name for c in all_cs}

        skill_bds = []
        readiness_in = []
        for s in skills:
            s_cids = db.execute(
                select(Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .where(Topic.skill_id == s.id)
            ).scalars().all()
            assessed_m = [mastery_map[cid] for cid in s_cids if cid in mastery_map]
            mean_m = sum(assessed_m) / len(assessed_m) if assessed_m else 0.50
            skill_bds.append({
                "skill_id": s.id,
                "skill_name": s.name,
                "weight": s.weight,
                "accuracy": round(mean_m * 100, 1),
                "mean_mastery": round(mean_m, 2),
            })
            readiness_in.append((s.weight, mean_m))

        r_score = readiness_score(readiness_in)
        extra_readiness_pct = round(r_score * 100, 1)
        extra_skill_breakdown = skill_bds

        # Weak topics from concept_scores
        extra_weak_topics = [
            {
                "concept_id": cs.concept_id,
                "concept_name": cs.concept_name,
                "gap_score": cs.gap_score,
                "band": cs.band,
                "accuracy": cs.accuracy,
            }
            for cs in concept_scores
            if cs.band in ("weak", "moderate")
        ]

        # Topological roadmap
        deps = db.execute(select(ConceptDependency)).scalars().all()
        g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
        root_causes = []
        for wt in extra_weak_topics[:3]:
            ancestors = get_ancestors_within_hops(g, wt["concept_id"], max_hops=2)
            cands = rank_root_cause_candidates(
                surface_concept_id=wt["concept_id"],
                ancestors_with_hops=ancestors,
                concept_mastery=mastery_map,
                concept_names=name_map,
            )
            if cands:
                primary_c = cands[0]
                cause_id = primary_c.get("candidate_concept_id") or primary_c.get("concept_id")
                if cause_id is not None:
                    root_causes.append(cause_id)

        extra_roadmap = build_personalized_path(
            g=g,
            concept_names=name_map,
            weak_concept_ids=[wt["concept_id"] for wt in extra_weak_topics],
            remediation_prereq_ids=root_causes,
            limit=12,
        )

    db.commit()

    mean_tr = total_time_ratio / total_q if total_q > 0 else 1.0

    return AssessmentSubmitOut(
        assessment_id=assessment.id,
        score=round(final_score, 1),
        total_questions=total_q,
        correct_count=correct_count,
        skip_count=skip_count,
        timed_out_count=timed_out_count,
        mean_time_ratio=round(mean_tr, 2),
        per_concept=concept_scores,
        signal_mode="gap_score",
        probe_queued=probe_queue,
        path_changed=len(probe_queue) > 0,
        cold_start=cold_start,
        readiness_percentage=extra_readiness_pct,
        skill_breakdown=extra_skill_breakdown,
        weak_topics=extra_weak_topics,
        roadmap=extra_roadmap,
    )


@router.get("/{assessment_id}")
def get_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details, status, and questions for an assessment."""
    assessment = db.get(Assessment, assessment_id)
    if not assessment or assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    questions_rows = db.execute(
        select(AssessmentQuestion, Question, Concept.name)
        .join(Question, AssessmentQuestion.question_id == Question.id)
        .join(Concept, Question.concept_id == Concept.id)
        .where(AssessmentQuestion.assessment_id == assessment.id)
        .order_by(AssessmentQuestion.order_index)
    ).all()

    items = [
        ItemOut(
            question_id=q.id,
            concept_id=q.concept_id,
            concept_name=cname,
            order_index=aq.order_index,
            question_text=q.question_text,
            options=q.options,
            difficulty_b=q.difficulty_b,
            phase=aq.phase,
            block_index=aq.block_index,
            source=getattr(q, "source", "curated") or "curated",
        )
        for aq, q, cname in questions_rows
    ]

    responses = db.execute(
        select(StudentResponse).where(StudentResponse.assessment_id == assessment.id)
    ).scalars().all()

    return {
        "assessment_id": assessment.id,
        "type": assessment.type,
        "completed": assessment.completed_at is not None,
        "score": assessment.score,
        "items": items,
        "responses_count": len(responses),
    }


@router.post("/root-cause/sub-questions", response_model=RootCauseSubQuestionsOut)
def get_root_cause_sub_questions_endpoint(
    req: RootCauseSubQuestionsIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves or generates up to 3 relevant prerequisite diagnostic questions for a main question.
    Persists the main question attempt if assessment_id is provided.
    Inspects curriculum DAG ancestors up to 2 hops, selects verified prerequisite questions,
    and returns them immediately before advancing to the next main question.
    """
    question = db.get(Question, req.question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    concept = db.get(Concept, question.concept_id)
    topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None
    tname = topic.name if topic else (concept.name if concept else "Topic")
    cname = concept.name if concept else "Concept"

    # Persist the main question attempt if assessment_id is provided
    main_resp = None
    if req.assessment_id:
        main_resp = db.execute(
            select(StudentResponse).where(
                StudentResponse.user_id == current_user.id,
                StudentResponse.assessment_id == req.assessment_id,
                StudentResponse.question_id == question.id,
                StudentResponse.phase == "main",
            )
        ).scalars().first()

        if not main_resp:
            is_corr = (not req.timed_out) and (req.selected_answer is not None) and (
                str(req.selected_answer).strip().upper() == str(question.correct_answer).strip().upper()
            )
            main_resp = StudentResponse(
                user_id=current_user.id,
                assessment_id=req.assessment_id,
                question_id=question.id,
                selected_answer=req.selected_answer,
                is_correct=is_corr,
                response_time_ms=req.response_time_ms,
                skipped=(req.selected_answer is None and not req.timed_out),
                timed_out=req.timed_out,
                phase="main",
                answered_at=dt.datetime.now(dt.timezone.utc),
            )
            db.add(main_resp)
            db.commit()
            db.refresh(main_resp)

    from backend.app.models.core import SubQuestion
    from backend.app.services.question_generator import to_options_list, generate_root_cause_sub_questions

    # 1. Check if explicit SubQuestion stages exist for this question
    stored_sqs = (
        db.query(SubQuestion)
        .filter(SubQuestion.parent_question_id == question.id)
        .order_by(SubQuestion.order.asc())
        .all()
    )

    if stored_sqs:
        sub_qs = [
            {
                "id": sq.id,
                "stage": sq.stage,
                "order": sq.order,
                "stem": sq.stem,
                "options": to_options_list(sq.options),
                "correct_option": sq.correct_answer,
                "time_limit_sec": sq.time_limit_sec,
            }
            for sq in stored_sqs
        ]
        return RootCauseSubQuestionsOut(
            question_id=question.id,
            topic_name=tname,
            concept_name=cname,
            main_question_stem=question.question_text,
            sub_questions=sub_qs,
            has_sub_questions=True,
            parent_response_id=main_resp.id if main_resp else None,
            message="3-stage sub-questions retrieved from question bank",
        )

    # 2. Inspect prerequisite concepts in Curriculum DAG (1-hop and 2-hop)
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    ancestors = get_ancestors_within_hops(g, question.concept_id, max_hops=2)

    prereq_qs = []
    if ancestors:
        ordered_anc_ids = sorted(ancestors.keys(), key=lambda aid: ancestors[aid])
        for anc_id in ordered_anc_ids:
            qs = db.execute(
                select(Question, Concept.name)
                .join(Concept, Question.concept_id == Concept.id)
                .where(
                    Question.concept_id == anc_id,
                    Question.id != question.id,
                    Question.review_status == "approved",
                )
            ).all()
            for q_item, c_name in qs:
                prereq_qs.append((q_item, c_name, f"prerequisite: {c_name}"))
                if len(prereq_qs) >= 3:
                    break
            if len(prereq_qs) >= 3:
                break

    # 3. Fallback to approved bank questions on same topic / concept if needed
    if len(prereq_qs) < 3:
        same_concept_qs = db.execute(
            select(Question, Concept.name)
            .join(Concept, Question.concept_id == Concept.id)
            .where(
                Question.concept_id == question.concept_id,
                Question.id != question.id,
                Question.review_status == "approved",
            )
        ).all()
        for q_item, c_name in same_concept_qs:
            if not any(pq[0].id == q_item.id for pq in prereq_qs):
                prereq_qs.append((q_item, c_name, f"diagnostic_probe: {c_name}"))
                if len(prereq_qs) >= 3:
                    break

    # 4. If still empty, use generated template sub-questions
    if not prereq_qs:
        generated = generate_root_cause_sub_questions(question)
        if generated:
            sub_qs = [
                {
                    "id": 900000 + idx,
                    "stage": g_item["stage"],
                    "order": g_item["order"],
                    "stem": g_item["stem"],
                    "options": to_options_list(g_item["options"]),
                    "correct_option": g_item["correct_answer"],
                    "time_limit_sec": g_item["time_limit_sec"],
                }
                for idx, g_item in enumerate(generated)
            ]
            return RootCauseSubQuestionsOut(
                question_id=question.id,
                topic_name=tname,
                concept_name=cname,
                main_question_stem=question.question_text,
                sub_questions=sub_qs,
                has_sub_questions=True,
                parent_response_id=main_resp.id if main_resp else None,
                message="Sub-questions generated from question template",
            )

    sub_qs = []
    for idx, (q_item, c_name, stage_name) in enumerate(prereq_qs[:3]):
        sub_qs.append({
            "id": q_item.id,
            "stage": stage_name,
            "order": idx + 1,
            "stem": q_item.question_text,
            "options": to_options_list(q_item.options),
            "correct_option": q_item.correct_answer,
            "time_limit_sec": 30,
        })

    return RootCauseSubQuestionsOut(
        question_id=question.id,
        topic_name=tname,
        concept_name=cname,
        main_question_stem=question.question_text,
        sub_questions=sub_qs,
        has_sub_questions=len(sub_qs) > 0,
        parent_response_id=main_resp.id if main_resp else None,
        message=f"{len(sub_qs)} prerequisite diagnostic questions retrieved",
    )


@router.post("/root-cause/evaluate", response_model=RootCauseEvaluateOut)
def evaluate_root_cause_endpoint(
    req: RootCauseEvaluateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Classifies cognitive root-cause gap based on sub-question responses.
    Persists sub-responses with phase='sub' and parent_response_id.
    Updates prerequisite concept mastery and records evidence in RootCauseAnalysis.
    """
    question = db.get(Question, req.question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    concept = db.get(Concept, question.concept_id)
    topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None
    tname = topic.name if topic else (concept.name if concept else "Topic")
    cname = concept.name if concept else "Concept"

    # Persist sub-responses if provided
    if req.sub_responses:
        for s_res in req.sub_responses:
            s_qid = s_res.get("question_id")
            s_q = db.get(Question, s_qid) if s_qid else None
            is_sub_corr = bool(s_res.get("is_correct", False))

            db_sub = StudentResponse(
                user_id=current_user.id,
                assessment_id=req.assessment_id or 1,
                question_id=s_qid or question.id,
                selected_answer=s_res.get("selected_answer"),
                is_correct=is_sub_corr,
                response_time_ms=s_res.get("response_time_ms", 12000),
                skipped=bool(s_res.get("skipped", False)),
                phase="sub",
                parent_response_id=req.parent_response_id,
                answered_at=dt.datetime.now(dt.timezone.utc),
            )
            db.add(db_sub)

            # Update prerequisite concept mastery in StudentMastery
            if s_q and s_q.concept_id:
                m_rec = db.execute(
                    select(StudentMastery).where(
                        StudentMastery.user_id == current_user.id,
                        StudentMastery.concept_id == s_q.concept_id,
                    )
                ).scalar_one_or_none()
                delta = 0.08 if is_sub_corr else -0.12
                if m_rec:
                    m_rec.mastery_score = max(0.05, min(0.95, m_rec.mastery_score + delta))
                    m_rec.updated_at = dt.datetime.now(dt.timezone.utc)
                else:
                    db.add(
                        StudentMastery(
                            user_id=current_user.id,
                            concept_id=s_q.concept_id,
                            mastery_score=0.65 if is_sub_corr else 0.35,
                            confidence=0.50,
                            model_version="rct_gat_sub_probe",
                        )
                    )
                    db.flush()

    # Classify cognitive gap
    classification = classify_root_cause_gap(
        formula_correct=req.formula_correct,
        substitution_correct=req.substitution_correct,
        calculation_correct=req.calculation_correct,
        calculation_time_ms=req.calculation_time_ms,
        time_threshold_ms=req.time_threshold_ms,
    )

    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    ancestors = get_ancestors_within_hops(g, question.concept_id, max_hops=2)

    upstream_prereqs = []
    for anc_id, hop in ancestors.items():
        anc_c = db.get(Concept, anc_id)
        if anc_c:
            upstream_prereqs.append({
                "concept_id": anc_c.id,
                "concept_name": anc_c.name,
                "hops": hop,
            })

    # Fetch learner masteries to compute ranking and attention entropy
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}
    all_cs = db.execute(select(Concept)).scalars().all()
    name_map = {c.id: c.name for c in all_cs}

    candidates = rank_root_cause_candidates(
        surface_concept_id=question.concept_id,
        ancestors_with_hops=ancestors,
        concept_mastery=mastery_map,
        concept_names=name_map,
    )

    alphas = [c["attention_alpha"] for c in candidates]
    raw_h, norm_h = attention_entropy(alphas)

    primary_candidate_id = candidates[0]["candidate_concept_id"] if candidates else question.concept_id
    primary_alpha = candidates[0]["attention_alpha"] if candidates else 1.0

    rc_entry = RootCauseAnalysis(
        user_id=current_user.id,
        current_concept_id=question.concept_id,
        candidate_concept_id=primary_candidate_id,
        root_score=candidates[0]["root_score"] if candidates else 0.75,
        attention_alpha=round(primary_alpha, 4),
        attention_entropy=round(norm_h, 4),
        rank=1,
        evidence_json={
            "topic_id": topic.id if topic else None,
            "topic_name": tname,
            "concept_name": cname,
            "cognitive_gap": classification,
            "main_question_stem": question.question_text,
            "upstream_prerequisites": upstream_prereqs,
            "candidates": candidates[:3],
        },
        model_version="rct_gat_sub_probe_v2",
    )
    db.add(rc_entry)
    db.commit()

    return RootCauseEvaluateOut(
        question_id=question.id,
        topic_name=tname,
        concept_name=cname,
        gap_type=classification["gap_type"],
        study_task=classification["study_task"],
        action=classification["action"],
        all_three_failed=classification["all_three_failed"],
        stages=classification["stages"],
        upstream_prerequisites=upstream_prereqs,
    )
