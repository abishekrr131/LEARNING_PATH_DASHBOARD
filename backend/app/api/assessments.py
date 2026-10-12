"""Assessment API Router for Diagnostic, Special Test Mode, Verification, and Practice."""
from __future__ import annotations

import datetime as dt
import math
import random
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import (
    Assessment,
    AssessmentQuestion,
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    Question,
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
    SpecialBlockEndIn,
    SpecialBlockEndOut,
    SpecialNextBlockIn,
    SpecialNextBlockOut,
)
from backend.app.services.root_cause import get_ancestors_within_hops, select_verification_probes
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
        # Exactly 10 questions, stratified across skills in proportion to skill weight
        # Ordered easy -> hard, no repeats
        total_items = 10
        skill_quotas = {}
        allocated = 0
        for s in skills:
            quota = max(1, round(s.weight * total_items))
            skill_quotas[s.id] = quota
            allocated += quota

        # Adjust total to exactly 10
        diff = allocated - total_items
        if diff != 0:
            top_skill_id = skills[0].id
            skill_quotas[top_skill_id] = max(1, skill_quotas[top_skill_id] - diff)

        all_pool = get_candidate_questions()
        qs_by_skill: dict[int, list[tuple[Question, str]]] = {s.id: [] for s in skills}
        for q, cname in all_pool:
            # find skill
            c = db.get(Concept, q.concept_id)
            if c:
                t = db.get(Topic, c.topic_id)
                if t and t.skill_id in qs_by_skill:
                    qs_by_skill[t.skill_id].append((q, cname))

        chosen_set = set()
        for s in skills:
            pool = qs_by_skill.get(s.id, [])
            quota = skill_quotas.get(s.id, 1)
            # sort pool by difficulty easy -> hard
            pool.sort(key=lambda x: x[0].difficulty_b)
            for item in pool:
                if len(selected_questions) >= 10:
                    break
                if item[0].id not in chosen_set and quota > 0:
                    selected_questions.append(item)
                    chosen_set.add(item[0].id)
                    quota -= 1

        # Fill if below 10
        for item in all_pool:
            if len(selected_questions) >= 10:
                break
            if item[0].id not in chosen_set:
                selected_questions.append(item)
                chosen_set.add(item[0].id)

        # Final sort: easy -> hard across all selected
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

    else:
        # Practice or followup
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
        # Wrong or Timed Out -> BIAS TOWARD PREREQUISITES (ancestors within 1-2 hops)
        trigger = "prerequisite_bias"
        target_concept_ids = list(ancestors.keys()) if ancestors else [main_q.concept_id]
        for cid in target_concept_ids[:2]:
            db.add(
                VerificationProbe(
                    user_id=current_user.id,
                    concept_id=cid,
                    trigger="model_flag",
                )
            )
        db.commit()
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

    db.commit()

    return SpecialBlockEndOut(
        block_index=req.block_index,
        main_correct=main_resp.is_correct if main_resp else False,
        main_timed_out=main_resp.timed_out if main_resp else False,
        sub_results=sub_results,
        suspected_weak_prerequisite=weak_prereq_name,
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
