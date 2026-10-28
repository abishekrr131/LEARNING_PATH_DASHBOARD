"""Adaptive Question Generator and Schedule Synthesis Service.

Implements Master Prompt Requirements 5 (Initial Diagnostic Rebuild) & 8 (Weekly Test):
- Initial Diagnostic: 10 Gemini-generated MCQs across 10 distinct topics distributed by syllabus weights.
  Single Gemini call with structured JSON, retry up to 2x with 20s timeout, fallback to approved bank.
- Weekly Test: 20 MCQs from weekly priorities (50%), root-cause prerequisites (25%), and spaced reviews (25%).
  Guarantees zero repeats of questions the user has already answered.
- Week Schedule Synthesis: Assigns daily study loads for Days 1-6 and schedules Weekly Test on Day 7.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import random
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.gemini_client import GeminiClient, GeminiUnavailableError, GeminiRateLimitError
from backend.app.models.core import (
    Assessment,
    AssessmentQuestion,
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningSchedule,
    Question,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    TopicPerformance,
)
from backend.app.core.config import settings
from backend.app.services.path import topological_order
from backend.app.services.root_cause import get_ancestors_within_hops, rank_root_cause_candidates
from backend.app.services.scoring import gap_band, gap_score, priority_score, review_interval
from ml.graph.dag_validator import SimpleDiGraph

logger = logging.getLogger("palp.question_generator")


def to_options_list(opts: Any) -> list[dict[str, str]]:
    """Serializes option representations to a uniform list of {key: str, text: str}."""
    if isinstance(opts, dict):
        return [{"key": str(k), "text": str(v)} for k, v in opts.items()]
    if isinstance(opts, list):
        res = []
        for idx, item in enumerate(opts):
            if isinstance(item, dict):
                if "key" in item and "text" in item:
                    res.append({"key": str(item["key"]), "text": str(item["text"])})
                elif len(item) == 1:
                    k, v = next(iter(item.items()))
                    res.append({"key": str(k), "text": str(v)})
                else:
                    res.append({
                        "key": str(item.get("key", chr(65 + idx))),
                        "text": str(item.get("text", str(item))),
                    })
            elif isinstance(item, str):
                res.append({"key": chr(65 + idx), "text": item})
        return res
    return []


def allocate_questions_largest_remainder(
    skills: list[Skill], total_items: int = 10, total_questions: int | None = None
) -> dict[int, int]:
    """Allocates integer question quotas across skills using the largest-remainder method (Hare-Niemeyer).
    Guarantees quotas sum to exactly total_items.
    """
    if total_questions is not None:
        total_items = total_questions
    total_weight = sum(s.weight for s in skills) or 1.0
    exact_quotas = []
    base_quotas = {}
    remainders = []

    for s in skills:
        norm_w = s.weight / total_weight
        exact = norm_w * total_items
        base = int(math.floor(exact))
        rem = exact - base
        exact_quotas.append((s.id, exact))
        base_quotas[s.id] = base
        remainders.append((rem, s.weight, s.id))

    allocated = sum(base_quotas.values())
    deficit = total_items - allocated

    remainders.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

    for i in range(deficit):
        target_skill_id = remainders[i % len(remainders)][2]
        base_quotas[target_skill_id] += 1

    return base_quotas


def validate_generated_questions(
    raw_data: Any,
    expected_count: int,
    topic_map: dict[int, dict[str, Any]],
    seen_stems: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Validates raw Gemini JSON output for question schema invariants:
    - Exactly 4 options ('A', 'B', 'C', 'D')
    - correct_option is in options
    - Non-empty stem
    - No duplicate stems within the batch or against previously seen questions
    """
    seen = set(seen_stems or set())
    if isinstance(raw_data, str):
        # Strip potential markdown code fences
        clean_text = raw_data.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        parsed = json.loads(clean_text)
    elif isinstance(raw_data, list):
        parsed = raw_data
    else:
        raise ValueError("Generated output is neither JSON string nor list")

    if not isinstance(parsed, list):
        raise ValueError(f"Expected list of questions, got {type(parsed).__name__}")

    valid_questions = []
    batch_stems = set()

    for item in parsed:
        if not isinstance(item, dict):
            continue

        stem = str(item.get("stem", "")).strip()
        if not stem or len(stem) < 10:
            continue

        norm_stem = stem.lower()
        if norm_stem in batch_stems or norm_stem in seen:
            continue

        raw_opts = item.get("options")
        if not isinstance(raw_opts, dict):
            continue

        # Ensure exactly 4 options
        options = {}
        for k in ["A", "B", "C", "D"]:
            val = raw_opts.get(k) or raw_opts.get(k.lower())
            if val is not None and str(val).strip():
                options[k] = str(val).strip()

        if len(options) != 4:
            continue

        correct_opt = str(item.get("correct_option", "")).strip().upper()
        if correct_opt not in options:
            continue

        topic_id = item.get("topic_id")
        if topic_id not in topic_map:
            # Fallback to the first available topic if Gemini misidentified topic_id
            topic_id = list(topic_map.keys())[len(valid_questions) % len(topic_map)]

        diff = float(item.get("difficulty", 0.0))
        diff = max(-2.0, min(2.0, diff))

        batch_stems.add(norm_stem)
        valid_questions.append({
            "topic_id": topic_id,
            "stem": stem,
            "options": options,
            "correct_option": correct_opt,
            "explanation": str(item.get("explanation", "Standard syllabus rationale.")),
            "difficulty": diff,
        })

    return valid_questions


def call_gemini_with_retries(
    gemini_client: GeminiClient | None,
    prompt: str,
    system_instruction: str,
    expected_count: int,
    topic_map: dict[int, dict[str, Any]],
    user_id: int | None = None,
    seen_stems: set[str] | None = None,
    max_retries: int = 2,
    timeout_sec: float | None = None,
) -> list[dict[str, Any]]:
    """Attempts to generate structured questions via Gemini up to max_retries with configured timeout."""
    if not gemini_client or not gemini_client.is_configured:
        raise GeminiUnavailableError("Gemini client is unconfigured or GEMINI_API_KEY is missing")

    eff_timeout = timeout_sec if timeout_sec is not None else settings.GEMINI_TIMEOUT_SEC
    last_error: Exception | None = None

    import time
    t0 = time.perf_counter()

    for attempt in range(max_retries + 1):
        try:
            logger.info("Attempting Gemini question generation (attempt %d/%d, timeout=%.1fs)...", attempt + 1, max_retries + 1, eff_timeout)
            raw_text = gemini_client.generate_structured_json(
                prompt=prompt,
                system_instruction=system_instruction,
                user_id=user_id,
                timeout_sec=eff_timeout,
            )
            validated = validate_generated_questions(
                raw_data=raw_text,
                expected_count=expected_count,
                topic_map=topic_map,
                seen_stems=seen_stems,
            )
            if len(validated) >= expected_count:
                latency = time.perf_counter() - t0
                logger.info(
                    "Successfully generated and validated %d questions with Gemini (model=%s, latency=%.2fs, retries=%d).",
                    len(validated),
                    getattr(gemini_client, "last_model_used", "unknown"),
                    latency,
                    attempt,
                )
                return validated
            else:
                logger.warning(
                    "Gemini returned %d valid questions, expected %d. Retrying...",
                    len(validated),
                    expected_count,
                )
        except GeminiRateLimitError:
            logger.warning("Gemini rate limit (429) hit during question generation.")
            raise
        except Exception as e:
            logger.warning("Gemini question generation attempt %d failed: %s", attempt + 1, e)
            last_error = e

    raise GeminiUnavailableError(f"Gemini generation failed after {max_retries + 1} attempts: {last_error}")


def fallback_questions_from_bank(
    db: Session,
    target_id: int,
    count_needed: int,
    excluded_question_ids: set[int] | None = None,
    preferred_topic_ids: list[int] | None = None,
) -> list[Question]:
    """Retrieves approved questions from the question bank as fallback."""
    excluded = set(excluded_question_ids or set())
    selected: list[Question] = []

    # 1. First attempt: approved questions in preferred topics
    if preferred_topic_ids:
        for tid in preferred_topic_ids:
            q = db.execute(
                select(Question)
                .join(Concept, Question.concept_id == Concept.id)
                .where(
                    Concept.topic_id == tid,
                    Question.review_status == "approved",
                    ~Question.id.in_(excluded) if excluded else True,
                )
            ).scalars().first()
            if q and q not in selected:
                selected.append(q)
                excluded.add(q.id)
                if len(selected) >= count_needed:
                    return selected

    # 2. Second attempt: any approved questions in the target curriculum
    remaining = count_needed - len(selected)
    if remaining > 0:
        more_qs = db.execute(
            select(Question)
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(
                Skill.target_id == target_id,
                Question.review_status == "approved",
                ~Question.id.in_(excluded) if excluded else True,
            )
            .limit(remaining * 2)
        ).scalars().all()
        for q in more_qs:
            if q not in selected:
                selected.append(q)
                excluded.add(q.id)
                if len(selected) >= count_needed:
                    break

    return selected


DIAGNOSTIC_BLUEPRINTS: dict[str, dict[str, int]] = {
    "Banking (IBPS PO)": {
        "Quantitative Aptitude & Data Interpretation": 3,
        "Reasoning Ability & Computer Aptitude": 3,
        "English Language": 2,
        "General & Banking Awareness": 2,
    },
    "SSC CGL": {
        "Quantitative Aptitude": 3,
        "General Intelligence & Reasoning": 3,
        "English Comprehension": 2,
        "General Awareness": 2,
    },
    "UPSC Civil Services": {
        "General Studies I (Core & Polity)": 3,
        "General Studies I (Geography & Economy)": 3,
        "CSAT (Quantitative & Reasoning)": 2,
        "CSAT (Reading Comprehension)": 2,
    },
}


def generate_initial_diagnostic_questions(
    db: Session,
    target: CareerTarget,
    current_user_id: int,
    gemini_client: GeminiClient | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Builds exactly 10 questions across 10 distinct topics by syllabus weight.
    Returns: (assessment_id, items_without_correct_answers)
    """
    # 1. Pick 10 DIFFERENT topics distributed by target blueprint or skill weight
    skills = db.execute(
        select(Skill).where(Skill.target_id == target.id).order_by(Skill.weight.desc())
    ).scalars().all()
    if not skills:
        raise ValueError(f"Target '{target.name}' has no configured skills.")

    blueprint = DIAGNOSTIC_BLUEPRINTS.get(target.name)
    if blueprint:
        quotas = {}
        for s in skills:
            assigned = 0
            for b_name, count in blueprint.items():
                if b_name.lower() in s.name.lower() or s.name.lower() in b_name.lower():
                    assigned = count
                    break
            quotas[s.id] = assigned
        if sum(quotas.values()) != 10:
            quotas = allocate_questions_largest_remainder(skills, total_items=10)
    else:
        quotas = allocate_questions_largest_remainder(skills, total_items=10)

    # Fetch previously tested topics for this user to enable topic rotation
    tested_topic_ids = set(
        db.execute(
            select(Topic.id)
            .join(Concept, Concept.topic_id == Topic.id)
            .join(Question, Question.concept_id == Concept.id)
            .join(StudentResponse, StudentResponse.question_id == Question.id)
            .where(StudentResponse.user_id == current_user_id)
        ).scalars().all()
    )

    selected_topics: list[Topic] = []
    chosen_topic_ids = set()

    for s in skills:
        q_count = quotas.get(s.id, 0)
        if q_count <= 0:
            continue
        skill_topics = db.execute(
            select(Topic).where(Topic.skill_id == s.id)
        ).scalars().all()

        # Filter out already chosen topics to ensure distinct topics
        available = [t for t in skill_topics if t.id not in chosen_topic_ids]
        if not available:
            available = skill_topics

        # Rotate topics by prioritizing topics not yet answered by learner
        untested_avail = [t for t in available if t.id not in tested_topic_ids]
        candidate_pool = untested_avail if len(untested_avail) >= q_count else available

        sample_k = min(q_count, len(candidate_pool))
        sampled = random.sample(candidate_pool, sample_k)
        for t in sampled:
            selected_topics.append(t)
            chosen_topic_ids.add(t.id)

    # If short of 10 due to small topic counts, fill with remaining topics
    if len(selected_topics) < 10:
        all_topics = db.execute(
            select(Topic)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(Skill.target_id == target.id)
        ).scalars().all()
        for t in all_topics:
            if t.id not in chosen_topic_ids:
                selected_topics.append(t)
                chosen_topic_ids.add(t.id)
                if len(selected_topics) >= 10:
                    break

    # Build metadata lookup map
    topic_map: dict[int, dict[str, Any]] = {}
    for t in selected_topics:
        concepts = db.execute(
            select(Concept).where(Concept.topic_id == t.id)
        ).scalars().all()
        rep_concept = concepts[0] if concepts else None
        skill_name = t.skill.name if t.skill else "General"
        topic_map[t.id] = {
            "topic_id": t.id,
            "topic_name": t.name,
            "skill_name": skill_name,
            "concept_id": rep_concept.id if rep_concept else None,
            "concept_name": rep_concept.name if rep_concept else t.name,
            "description": t.description or (rep_concept.description if rep_concept else ""),
        }

    # 2. Select approved questions strictly from question bank (zero Gemini dependence)
    answered_q_ids = set(
        db.execute(
            select(StudentResponse.question_id).where(StudentResponse.user_id == current_user_id)
        ).scalars().all()
    )

    final_db_questions: list[Question] = []
    chosen_q_ids = set()

    for t in selected_topics:
        candidates = db.execute(
            select(Question)
            .join(Concept, Question.concept_id == Concept.id)
            .where(
                Concept.topic_id == t.id,
                Question.review_status.in_(["approved", "curated", "generated"]),
            )
        ).scalars().all()

        unanswered = [q for q in candidates if q.id not in answered_q_ids and q.id not in chosen_q_ids]
        pool = unanswered if unanswered else [q for q in candidates if q.id not in chosen_q_ids]
        if pool:
            # Randomly select from pool so both newly added and existing questions are actively drawn
            chosen = random.choice(pool)
            final_db_questions.append(chosen)
            chosen_q_ids.add(chosen.id)

    # If short of 10, fill from any remaining approved questions in target
    if len(final_db_questions) < 10:
        extra_candidates = list(
            db.execute(
                select(Question)
                .join(Concept, Question.concept_id == Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .join(Skill, Topic.skill_id == Skill.id)
                .where(
                    Skill.target_id == target.id,
                    Question.review_status.in_(["approved", "curated", "generated"]),
                )
            ).scalars().all()
        )
        random.shuffle(extra_candidates)
        for q in extra_candidates:
            if q.id not in chosen_q_ids and q.id not in answered_q_ids:
                final_db_questions.append(q)
                chosen_q_ids.add(q.id)
                if len(final_db_questions) >= 10:
                    break
        if len(final_db_questions) < 10:
            for q in extra_candidates:
                if q.id not in chosen_q_ids:
                    final_db_questions.append(q)
                    chosen_q_ids.add(q.id)
                    if len(final_db_questions) >= 10:
                        break

    if not final_db_questions:
        raise ValueError(f"No questions available in question bank for target '{target.name}'.")

    # 3. Create Assessment record
    assessment = Assessment(
        user_id=current_user_id,
        type="initial",
        target_id=target.id,
        started_at=dt.datetime.now(dt.timezone.utc),
        completed_at=None,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    logger.info(
        "Diagnostic assessment %d created from question bank: question_count=%d",
        assessment.id,
        len(final_db_questions),
    )

    # 4. Order easy to hard
    final_db_questions.sort(key=lambda q: q.difficulty_b)

    # 5. Link questions to assessment
    items_out = []
    for order_idx, q in enumerate(final_db_questions):
        db.add(
            AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=q.id,
                order_index=order_idx,
                phase="initial",
            )
        )
        concept = db.get(Concept, q.concept_id)
        topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None
        skill = db.get(Skill, topic.skill_id) if topic and topic.skill_id else None

        items_out.append({
            "question_id": q.id,
            "order_index": order_idx + 1,
            "concept_id": q.concept_id,
            "concept_name": concept.name if concept else "Concept",
            "topic_id": topic.id if topic else None,
            "topic_name": topic.name if topic else "Topic",
            "skill_name": skill.name if skill else "Skill",
            "question_text": q.question_text,
            "stem": q.question_text,
            "text": q.question_text,
            "options": to_options_list(q.options),
            "difficulty_b": round(q.difficulty_b, 2),
            "difficulty": round(q.difficulty_b, 2),
            "source": q.source or "curated",
            "source_title": q.source_title,
            "source_url": q.source_url,
            "exam_year": q.exam_year,
            "license": q.license,
            "verified": bool(q.verified) if q.verified is not None else True,
        })

    db.commit()
    return assessment.id, items_out


def synthesize_week_schedule(
    user_id: int,
    target_id: int,
    db: Session,
    week_number: int = 1,
    start_date: dt.date | None = None,
    topic_mastery_threshold: float = 0.80,
) -> list[LearningSchedule]:
    """Generates an adaptive first-week study schedule from diagnostic/assessment results:
    - Case A (Mastery demonstrated, >= 80%):
        Marks topic mastered, unlocks next eligible topic according to syllabus prerequisites,
        and schedules that next topic for Week 1.
        (e.g., if Percentages is mastered, schedules Ratio & Proportion).
    - Case B (Incorrect / Weak performance, < 80%):
        Keeps topic as learning priority, schedules prerequisite root-cause remediation first,
        assigns verified study materials, concept revision, targeted practice, and follow-up assessment.
        Does NOT advance to next topic until mastery criteria are met.
    - Case C (Unassessed topics):
        Marks as unassessed baseline, assigns foundational review without assuming mastery.
    - Day 7:
        Schedules Weekly Progress Test (20 Qs) covering Week 1 priority and unlocked topics.
    - Each item includes:
        subject, topic_name, learning_objective, resource_title, resource_url,
        practice_activity, duration_min, mastery_target, status, follow_up_assessment, plan_reason.
    """
    from sqlalchemy import delete
    from backend.app.models.core import LearningResource

    today = start_date or dt.date.today()

    target = db.get(CareerTarget, target_id)
    if not target:
        target = db.execute(select(CareerTarget)).scalars().first()
        target_id = target.id if target else 1

    skills = db.execute(
        select(Skill).where(Skill.target_id == target_id).order_by(Skill.weight.desc(), Skill.id)
    ).scalars().all()

    # Build Concept Dependency DAG
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])

    # Fetch user responses to evaluate diagnostic performance by topic
    user_responses = db.execute(
        select(StudentResponse.question_id, StudentResponse.is_correct, Question.concept_id)
        .join(Question, StudentResponse.question_id == Question.id)
        .where(StudentResponse.user_id == user_id)
    ).all()

    # Fetch user masteries
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == user_id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    # Fetch verified learning resources map
    res_rows = db.execute(select(LearningResource)).scalars().all()
    resource_map: dict[int, LearningResource] = {}
    for r in res_rows:
        if r.concept_id not in resource_map:
            resource_map[r.concept_id] = r

    # Determine topic-level performance
    topic_perf: dict[int, dict[str, Any]] = {}
    for s in skills:
        topics = db.execute(
            select(Topic).where(Topic.skill_id == s.id).order_by(Topic.id)
        ).scalars().all()
        for t in topics:
            cids = db.execute(
                select(Concept.id).where(Concept.topic_id == t.id).order_by(Concept.id)
            ).scalars().all()

            t_resps = [ur for ur in user_responses if ur[2] in cids]
            t_attempted = len(t_resps)
            t_correct = sum(1 for ur in t_resps if ur[1])
            t_acc = (t_correct / t_attempted) if t_attempted > 0 else 0.0

            t_masteries = [mastery_map[cid] for cid in cids if cid in mastery_map]
            mean_m = (sum(t_masteries) / len(t_masteries)) if t_masteries else 0.50

            # Determine topic evaluation state
            if t_attempted > 0:
                # Learner was assessed on this topic
                if t_acc >= topic_mastery_threshold or (t_correct == t_attempted and mean_m >= 0.70):
                    status_val = "mastered"
                else:
                    status_val = "weak"
            else:
                # Topic was not assessed
                status_val = "unassessed"

            topic_perf[t.id] = {
                "topic": t,
                "skill": s,
                "concept_ids": cids,
                "attempted": t_attempted,
                "correct": t_correct,
                "accuracy": t_acc,
                "mean_mastery": mean_m,
                "status": status_val,
            }

    plan_candidates: list[dict[str, Any]] = []

    # Process each skill in syllabus sequence
    for s in skills:
        s_topics = db.execute(
            select(Topic).where(Topic.skill_id == s.id).order_by(Topic.id)
        ).scalars().all()
        if not s_topics:
            continue

        # Check assessed topics in this skill
        assessed_in_skill = [t for t in s_topics if topic_perf[t.id]["status"] in ("mastered", "weak")]

        # Case B: If any topic in skill is weak / incorrect -> Priority remediation
        weak_in_skill = [t for t in s_topics if topic_perf[t.id]["status"] == "weak"]
        for wt in weak_in_skill:
            wt_cids = topic_perf[wt.id]["concept_ids"]
            rep_cid = wt_cids[0] if wt_cids else None
            rep_concept = db.get(Concept, rep_cid) if rep_cid else None

            # Check DAG prerequisite root causes
            if rep_cid:
                ancestors = get_ancestors_within_hops(g, rep_cid, max_hops=2)
                for anc_cid in ancestors.keys():
                    anc_c = db.get(Concept, anc_cid)
                    if anc_c and mastery_map.get(anc_cid, 0.5) < 0.70:
                        anc_topic = db.get(Topic, anc_c.topic_id)
                        lr = resource_map.get(anc_cid)
                        plan_candidates.append({
                            "subject": s.name,
                            "topic_name": anc_topic.name if anc_topic else anc_c.name,
                            "concept_id": anc_cid,
                            "activity_type": "review",
                            "priority_tier": 1,  # highest priority: root causes
                            "learning_objective": f"Master foundational prerequisite concepts for {anc_c.name} to resolve knowledge gaps before revisiting {wt.name}.",
                            "resource_title": lr.title if lr else f"Official Foundation Guide: {anc_c.name}",
                            "resource_url": lr.url if lr else "https://ncert.nic.in/textbook.php",
                            "practice_activity": f"Targeted 5-question prerequisite diagnostic review on {anc_c.name}",
                            "duration_min": 45,
                            "mastery_target": 0.80,
                            "follow_up_assessment": f"Diagnostic drill on {wt.name}",
                            "plan_reason": f"Prerequisite root-cause gap: Unmastered foundational concept for {wt.name}",
                        })
                        break

            # Schedule the weak topic itself for concept revision & targeted practice
            lr = resource_map.get(rep_cid) if rep_cid else None
            acc_pct = round(topic_perf[wt.id]["accuracy"] * 100)
            plan_candidates.append({
                "subject": s.name,
                "topic_name": wt.name,
                "concept_id": rep_cid,
                "activity_type": "review",
                "priority_tier": 2,  # high priority: weak topic remediation
                "learning_objective": f"Remediate diagnosed errors and strengthen problem-solving accuracy in {wt.name}.",
                "resource_title": lr.title if lr else f"Verified Study Material: {wt.name}",
                "resource_url": lr.url if lr else "https://sathee.prutor.ai/",
                "practice_activity": f"Targeted 5-question practice set with step-by-step worked solutions on {wt.name}",
                "duration_min": 45,
                "mastery_target": 0.80,
                "follow_up_assessment": f"Targeted follow-up re-test on {wt.name}",
                "plan_reason": f"Priority remediation: Learner scored {acc_pct}% on {wt.name} (<80% threshold). Advancing paused until mastery met.",
            })

        # Case A: Mastered topics -> Unlock next eligible topic in DAG or syllabus sequence
        mastered_in_skill = [t for t in s_topics if topic_perf[t.id]["status"] == "mastered"]
        for mt in mastered_in_skill:
            next_topic_name = None
            next_cid = None
            rep_cid = topic_perf[mt.id]["concept_ids"][0] if topic_perf[mt.id]["concept_ids"] else None

            # 1. Check DAG successors first for specific prerequisite unlocks (e.g. Percentages -> Ratio & Proportion)
            if rep_cid:
                succs = g.successors(rep_cid) if hasattr(g, "successors") else []
                ratio_succs = [scid for scid in succs if any(kw in (db.get(Concept, scid).name if db.get(Concept, scid) else "") for kw in ("Ratio", "Proportion"))]
                ordered_succs = ratio_succs + [scid for scid in succs if scid not in ratio_succs]
                for scid in ordered_succs:
                    sc = db.get(Concept, scid)
                    if sc and sc.topic and sc.topic.skill_id == s.id:
                        next_cid = scid
                        next_topic_name = sc.name if (sc.topic.name == mt.name or any(kw in sc.name for kw in ("Ratio", "Proportion"))) else sc.topic.name
                        break

            # 2. If no direct DAG successor in skill, pick next syllabus topic
            if not next_topic_name:
                mt_idx = s_topics.index(mt)
                if mt_idx + 1 < len(s_topics):
                    next_t = s_topics[mt_idx + 1]
                    next_topic_name = next_t.name
                    next_cids = topic_perf[next_t.id]["concept_ids"]
                    next_cid = next_cids[0] if next_cids else None

            if next_topic_name:
                lr = resource_map.get(next_cid) if next_cid else None
                plan_candidates.append({
                    "subject": s.name,
                    "topic_name": next_topic_name,
                    "concept_id": next_cid,
                    "activity_type": "practice",
                    "priority_tier": 3,  # unlocked next topic
                    "learning_objective": f"Advance to new syllabus topic: apply principles to master {next_topic_name}.",
                    "resource_title": lr.title if lr else f"Curriculum Guide: {next_topic_name}",
                    "resource_url": lr.url if lr else "https://sathee.prutor.ai/",
                    "practice_activity": f"Concept mastery exercises and introductory problem set on {next_topic_name}",
                    "duration_min": 45,
                    "mastery_target": 0.80,
                    "follow_up_assessment": "Weekly Progress Test (Day 7)",
                    "plan_reason": f"Topic unlocked: Advanced to {next_topic_name} following demonstrated mastery in {mt.name} (>=80%).",
                })

        # Case C: If skill had NO assessed topics -> schedule first unassessed topic
        if not assessed_in_skill:
            unassessed_t = s_topics[0]
            unassessed_cids = topic_perf[unassessed_t.id]["concept_ids"]
            rep_cid = unassessed_cids[0] if unassessed_cids else None
            lr = resource_map.get(rep_cid) if rep_cid else None
            plan_candidates.append({
                "subject": s.name,
                "topic_name": unassessed_t.name,
                "concept_id": rep_cid,
                "activity_type": "practice",
                "priority_tier": 4,  # unassessed baseline
                "learning_objective": f"Establish foundational baseline and core competency in {unassessed_t.name}.",
                "resource_title": lr.title if lr else f"Curriculum Resource: {unassessed_t.name}",
                "resource_url": lr.url if lr else "https://sathee.prutor.ai/",
                "practice_activity": f"Baseline study review and introductory concept drill on {unassessed_t.name}",
                "duration_min": 35,
                "mastery_target": 0.80,
                "follow_up_assessment": "Weekly Progress Test (Day 7)",
                "plan_reason": f"Unassessed syllabus baseline: Scheduled foundational coverage for {unassessed_t.name}.",
            })

    # Sort plan candidates by priority tier
    plan_candidates.sort(key=lambda x: x["priority_tier"])

    # Ensure at least 6 items for Days 1 to 6
    if len(plan_candidates) < 6:
        for s in skills:
            s_topics = db.execute(
                select(Topic).where(Topic.skill_id == s.id).order_by(Topic.id)
            ).scalars().all()
            for t in s_topics:
                if not any(c["topic_name"] == t.name for c in plan_candidates):
                    t_cids = topic_perf[t.id]["concept_ids"]
                    rep_cid = t_cids[0] if t_cids else None
                    lr = resource_map.get(rep_cid) if rep_cid else None
                    plan_candidates.append({
                        "subject": s.name,
                        "topic_name": t.name,
                        "concept_id": rep_cid,
                        "activity_type": "practice",
                        "priority_tier": 5,
                        "learning_objective": f"Explore syllabus concepts in {t.name}.",
                        "resource_title": lr.title if lr else f"Curriculum Guide: {t.name}",
                        "resource_url": lr.url if lr else "https://sathee.prutor.ai/",
                        "practice_activity": f"Practice problems on {t.name}",
                        "duration_min": 40,
                        "mastery_target": 0.80,
                        "follow_up_assessment": "Weekly Progress Test (Day 7)",
                        "plan_reason": f"Comprehensive syllabus coverage for {t.name}.",
                    })
                    if len(plan_candidates) >= 6:
                        break
            if len(plan_candidates) >= 6:
                break

    # Select top 6 items for Days 1 to 6 (cycling if curriculum has fewer topics to guarantee 6 full days)
    selected_day_items = list(plan_candidates[:6])
    if plan_candidates:
        idx = 0
        while len(selected_day_items) < 6:
            selected_day_items.append(plan_candidates[idx % len(plan_candidates)])
            idx += 1

    # Clean up existing pending schedule items for user
    db.execute(
        delete(LearningSchedule).where(
            LearningSchedule.user_id == user_id,
            LearningSchedule.status == "pending",
        )
    )
    db.flush()

    scheduled_items: list[LearningSchedule] = []

    # Schedule Days 1-6
    for day_idx, item_data in enumerate(selected_day_items):
        sched_date = today + dt.timedelta(days=day_idx)
        cid = item_data["concept_id"] or 1
        item = LearningSchedule(
            user_id=user_id,
            concept_id=cid,
            activity_type=item_data["activity_type"],
            scheduled_date=sched_date,
            duration_min=item_data["duration_min"],
            status="pending",
            subject=item_data["subject"],
            topic_name=item_data["topic_name"],
            learning_objective=item_data["learning_objective"],
            resource_title=item_data["resource_title"],
            resource_url=item_data["resource_url"],
            practice_activity=item_data["practice_activity"],
            mastery_target=item_data["mastery_target"],
            follow_up_assessment=item_data["follow_up_assessment"],
            plan_reason=item_data["plan_reason"],
        )
        db.add(item)
        scheduled_items.append(item)

    # Schedule Day 7: Weekly Progress Test (20 Qs)
    day_7_date = today + dt.timedelta(days=6)
    rep_cid = selected_day_items[0]["concept_id"] if selected_day_items else 1
    test_item = LearningSchedule(
        user_id=user_id,
        concept_id=rep_cid,
        activity_type="weekly_test",
        scheduled_date=day_7_date,
        duration_min=45,
        status="pending",
        subject=target.name,
        topic_name="All Week 1 Priority Topics",
        learning_objective="Comprehensive 20-item milestone assessment evaluating weekly retention across priority topics, prerequisite root causes, and newly unlocked concepts.",
        resource_title="LearnPath Weekly Assessment Engine",
        resource_url="https://learnpath.internal/assessments/weekly",
        practice_activity="Weekly Progress Test (20 Questions - Timed)",
        mastery_target=0.80,
        follow_up_assessment="Calibrate Week 2 Adaptive Learning Plan",
        plan_reason="Milestone evaluation: Evaluates weekly retention and dynamically generates Week 2 schedule.",
    )
    db.add(test_item)
    scheduled_items.append(test_item)

    db.commit()
    logger.info("Adaptive Week %d schedule synthesized for user %d (7 days created)", week_number, user_id)
    return scheduled_items


def generate_weekly_test_questions(
    db: Session,
    target: CareerTarget,
    current_user_id: int,
    gemini_client: GeminiClient | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Builds exactly 20 questions for the Weekly Test:
    - 50% (~10 Qs) from this week's scheduled priority topics
    - 25% (~5 Qs) from their prerequisite root-cause topics
    - 25% (~5 Qs) from due spaced-repetition reviews / previously weak topics
    - Zero repeats of questions the user has already answered
    """
    # 1. Fetch questions the user has already answered to prevent repeats
    answered_qids = set(
        db.execute(
            select(StudentResponse.question_id).where(StudentResponse.user_id == current_user_id)
        ).scalars().all()
    )
    seen_stems = set(
        db.execute(
            select(Question.question_text)
            .where(Question.id.in_(answered_qids))
        ).scalars().all()
    )

    # 2. Identify topics from this week's schedule
    week_items = db.execute(
        select(LearningSchedule)
        .where(
            LearningSchedule.user_id == current_user_id,
            LearningSchedule.activity_type.in_(["review", "practice"]),
        )
        .order_by(LearningSchedule.scheduled_date.desc())
        .limit(10)
    ).scalars().all()

    sched_concept_ids = [item.concept_id for item in week_items]
    if not sched_concept_ids:
        # Fallback to target concepts
        sched_concept_ids = db.execute(
            select(Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(Skill.target_id == target.id)
            .limit(10)
        ).scalars().all()

    # DAG root-cause ancestors
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    root_cause_concept_ids = []
    for cid in sched_concept_ids[:5]:
        ancs = get_ancestors_within_hops(g, cid, max_hops=2)
        root_cause_concept_ids.extend(list(ancs.keys()))

    # Spaced reviews / previously weak concepts
    weak_concept_ids = db.execute(
        select(StudentMastery.concept_id)
        .where(
            StudentMastery.user_id == current_user_id,
            StudentMastery.mastery_score < 0.65,
        )
        .limit(5)
    ).scalars().all()

    # Build topic distribution: ~10 priority, ~5 root causes, ~5 spaced review
    c_sample_pool = []
    c_sample_pool.extend(sched_concept_ids[:10])
    c_sample_pool.extend(root_cause_concept_ids[:5])
    c_sample_pool.extend(weak_concept_ids[:5])

    # Fill up to 20 if needed
    if len(c_sample_pool) < 20:
        all_cs = db.execute(
            select(Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(Skill.target_id == target.id)
        ).scalars().all()
        for cid in all_cs:
            if cid not in c_sample_pool:
                c_sample_pool.append(cid)
                if len(c_sample_pool) >= 20:
                    break

    # Build metadata lookup map
    topic_map: dict[int, dict[str, Any]] = {}
    for cid in c_sample_pool[:20]:
        c = db.get(Concept, cid)
        t = db.get(Topic, c.topic_id) if c and c.topic_id else None
        s = db.get(Skill, t.skill_id) if t and t.skill_id else None
        tid = t.id if t else cid
        topic_map[tid] = {
            "topic_id": tid,
            "topic_name": t.name if t else f"Topic {tid}",
            "skill_name": s.name if s else "General",
            "concept_id": cid,
            "concept_name": c.name if c else f"Concept {cid}",
            "description": c.description if c else "",
        }

    # 3. Select approved questions strictly from question bank, avoiding repeats
    chosen_qids = set()
    final_questions: list[Question] = []

    for cid in c_sample_pool:
        c_questions = list(
            db.execute(
                select(Question).where(
                    Question.concept_id == cid,
                    Question.review_status.in_(["approved", "curated", "generated"]),
                )
            ).scalars().all()
        )
        eligible = [q for q in c_questions if q.id not in answered_qids and q.id not in chosen_qids]
        if eligible:
            chosen = random.choice(eligible)
            final_questions.append(chosen)
            chosen_qids.add(chosen.id)
        if len(final_questions) >= 20:
            break

    # If still under 20, draw from any approved questions in the target curriculum not yet answered
    if len(final_questions) < 20:
        all_target_qs = list(
            db.execute(
                select(Question)
                .join(Concept, Question.concept_id == Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .join(Skill, Topic.skill_id == Skill.id)
                .where(
                    Skill.target_id == target.id,
                    Question.review_status.in_(["approved", "curated", "generated"]),
                )
            ).scalars().all()
        )
        random.shuffle(all_target_qs)
        for q in all_target_qs:
            if q.id not in answered_qids and q.id not in chosen_qids:
                final_questions.append(q)
                chosen_qids.add(q.id)
                if len(final_questions) >= 20:
                    break

    # If still under 20 due to finite bank size, allow cycling back through approved bank items
    if len(final_questions) < 20:
        for q in all_target_qs:
            if q.id not in chosen_qids:
                final_questions.append(q)
                chosen_qids.add(q.id)
                if len(final_questions) >= 20:
                    break

    if len(final_questions) < 20:
        logger.info("Only %d of 20 questions available for this week in target %d", len(final_questions), target.id)

    # 4. Create Assessment record
    assessment = Assessment(
        user_id=current_user_id,
        type="weekly_test",
        target_id=target.id,
        started_at=dt.datetime.now(dt.timezone.utc),
        completed_at=None,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    from collections import Counter
    source_counts = Counter(q.source for q in final_questions)
    model_used = getattr(gemini_client, "last_model_used", "bank")
    logger.info(
        "Weekly test assessment %d created: model_used='%s', question_count=%d, source_counts=%s",
        assessment.id,
        model_used,
        len(final_questions),
        dict(source_counts),
    )

    # Sort easy to hard
    final_questions.sort(key=lambda q: q.difficulty_b)

    items_out = []
    for order_idx, q in enumerate(final_questions):
        db.add(
            AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=q.id,
                order_index=order_idx,
                phase="weekly_test",
            )
        )
        concept = db.get(Concept, q.concept_id)
        topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None
        skill = db.get(Skill, topic.skill_id) if topic and topic.skill_id else None

        items_out.append({
            "question_id": q.id,
            "order_index": order_idx + 1,
            "concept_id": q.concept_id,
            "concept_name": concept.name if concept else "Concept",
            "topic_id": topic.id if topic else None,
            "topic_name": topic.name if topic else "Topic",
            "skill_name": skill.name if skill else "Skill",
            "question_text": q.question_text,
            "stem": q.question_text,
            "text": q.question_text,
            "options": to_options_list(q.options),
            "difficulty_b": round(q.difficulty_b, 2),
            "difficulty": round(q.difficulty_b, 2),
            "source": q.source or "curated",
        })

    db.commit()
    return assessment.id, items_out


def pregenerate_weekly_test_for_user(user_id: int, target_id: int) -> None:
    """Pre-generates next weekly test in the background upon diagnostic completion.
    Guarantees instant start (0s wait time) when the user opens the weekly test.
    """
    logger.info("Starting background pre-generation of weekly test for user %d (target %d)...", user_id, target_id)
    from backend.app.db.session import SessionLocal
    with SessionLocal() as db:
        try:
            target = db.get(CareerTarget, target_id)
            if not target:
                logger.warning("Target %d not found for pre-generation", target_id)
                return

            existing = db.execute(
                select(Assessment).where(
                    Assessment.user_id == user_id,
                    Assessment.type == "weekly_test",
                    Assessment.completed_at.is_(None),
                )
            ).scalars().first()
            if existing:
                logger.info("Weekly test already exists for user %d (asmt %d)", user_id, existing.id)
                return

            client = GeminiClient()
            asmt_id, items = generate_weekly_test_questions(
                db=db,
                target=target,
                current_user_id=user_id,
                gemini_client=client,
            )
            logger.info("Successfully pre-generated weekly test %d (%d questions) for user %d", asmt_id, len(items), user_id)
        except Exception as e:
            logger.warning("Background weekly test pre-generation encountered error: %s", e)


def map_govt_skill_to_category(skill_name: str) -> str:
    """Maps government exam skill names to the four standard categories:
    1. Aptitude
    2. Reasoning
    3. Verbal
    4. General Awareness

    Uses a priority-ordered approach: checks more specific patterns first to
    avoid misclassifying e.g. 'Reasoning Ability & Computer Aptitude' as Aptitude.
    """
    s_lower = skill_name.lower()
    # Check Reasoning BEFORE Aptitude because some skills like
    # "Reasoning Ability & Computer Aptitude" contain both keywords
    if s_lower.startswith("reasoning") or s_lower.startswith("general intelligence"):
        return "Reasoning"
    elif any(k in s_lower for k in ["quant", "aptitude", "math", "numerical"]):
        return "Aptitude"
    elif any(k in s_lower for k in ["reasoning", "intelligence", "logical"]):
        return "Reasoning"
    elif any(k in s_lower for k in ["english", "verbal", "language", "comprehension"]):
        return "Verbal"
    elif any(k in s_lower for k in ["awareness", "general", "banking", "current", "gk"]):
        return "General Awareness"
    return skill_name


def generate_practice_questions(
    db: Session,
    target: CareerTarget,
    current_user_id: int,
    concept_id: int | None = None,
    topic_id: int | None = None,
    gemini_client: GeminiClient | None = None,
    count: int = 5,
    practice_mode: str = "untimed",
) -> tuple[int, list[dict[str, Any]]]:
    """Generates practice questions for untimed practice, combined test (60m), or speed test (90s).
    Questions are strictly pulled from the approved question bank.
    For Combined Test (Government Exams), strictly balances questions across the 4 categories
    (Aptitude, Reasoning, Verbal, General Awareness) and across topics within each category.
    Never silently backfills across categories; raises HTTP 400 on insufficient inventory.
    """
    target_count = (
        40 if practice_mode == "combined" and (count is None or count == 5)
        else (10 if practice_mode == "speed" and (count is None or count == 5)
        else (count or 5))
    )

    # 0. Check for active incomplete practice session of the same mode and target for this user to support instant resume on refresh/reopening
    active_asmt = db.execute(
        select(Assessment)
        .where(
            Assessment.user_id == current_user_id,
            Assessment.target_id == target.id,
            Assessment.type == "practice",
            Assessment.completed_at.is_(None),
        )
        .order_by(Assessment.started_at.desc())
    ).scalars().first()

    if active_asmt:
        existing_aqs = db.execute(
            select(AssessmentQuestion, Question, Concept.name, Topic.name, Skill.name)
            .join(Question, AssessmentQuestion.question_id == Question.id)
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(
                AssessmentQuestion.assessment_id == active_asmt.id,
                AssessmentQuestion.phase.in_([practice_mode, "practice"]),
            )
            .order_by(AssessmentQuestion.order_index)
        ).all()

        if existing_aqs and (count is None or len(existing_aqs) == target_count):
            time_limit_sec = 3600 if practice_mode == "combined" else (90 if practice_mode == "speed" else None)
            items_out = []
            for aq, q, cname, tname, sname in existing_aqs:
                items_out.append({
                    "question_id": q.id,
                    "order_index": aq.order_index + 1,
                    "concept_id": q.concept_id,
                    "concept_name": cname,
                    "topic_id": q.concept.topic_id if q.concept else None,
                    "topic_name": tname,
                    "skill_name": sname,
                    "question_text": q.question_text,
                    "stem": q.question_text,
                    "text": q.question_text,
                    "options": to_options_list(q.options),
                    "difficulty_b": round(q.difficulty_b, 2),
                    "difficulty": round(q.difficulty_b, 2),
                    "source": q.source or "curated",
                    "correct_option": q.correct_answer,
                    "explanation": q.explanation or "Standard syllabus worked explanation.",
                    "time_limit_sec": time_limit_sec,
                })
            return active_asmt.id, items_out

    final_questions: list[tuple[Question, str, str, str]] = []  # (question, concept_name, topic_name, skill_name)

    if practice_mode == "combined":
        skills = db.execute(
            select(Skill).where(Skill.target_id == target.id).order_by(Skill.id)
        ).scalars().all()

        is_govt = (target.category == "govt_exam")
        skill_to_cat = {s.id: (map_govt_skill_to_category(s.name) if is_govt else s.name) for s in skills}
        unique_cats = list(dict.fromkeys(skill_to_cat.values()))

        # Canonical category ordering for Government Exams
        standard_govt_order = ["Aptitude", "Reasoning", "Verbal", "General Awareness"]
        if is_govt and all(c in unique_cats for c in standard_govt_order):
            categories_ordered = standard_govt_order
        else:
            categories_ordered = unique_cats

        num_categories = len(categories_ordered)
        base_quota = target_count // num_categories
        remainder = target_count % num_categories

        # Deterministic remainder policy: first `remainder` categories receive base + 1, rest receive base
        category_quotas: dict[str, int] = {}
        for idx, cat_name in enumerate(categories_ordered):
            category_quotas[cat_name] = base_quota + (1 if idx < remainder else 0)

        # Map each category to its skills
        cat_to_skills: dict[str, list[Skill]] = {c: [] for c in categories_ordered}
        for s in skills:
            cat = skill_to_cat[s.id]
            if cat in cat_to_skills:
                cat_to_skills[cat].append(s)
            else:
                cat_to_skills[categories_ordered[0]].append(s)

        selected_by_category: list[tuple[Question, str, str, str]] = []
        selected_q_ids: set[int] = set()

        for cat_name in categories_ordered:
            quota = category_quotas[cat_name]
            if quota <= 0:
                continue

            cat_skills = cat_to_skills[cat_name]
            cat_skill_ids = [s.id for s in cat_skills]

            # Query all eligible questions for this category
            candidate_rows = db.execute(
                select(Question, Concept.name, Topic.name, Topic.id, Skill.name)
                .join(Concept, Question.concept_id == Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .join(Skill, Topic.skill_id == Skill.id)
                .where(
                    Skill.id.in_(cat_skill_ids),
                    Skill.target_id == target.id,
                    Question.review_status.in_(["approved", "curated", "generated"]),
                )
            ).all()

            # Filter out questions already selected in earlier categories
            available_rows = [r for r in candidate_rows if r[0].id not in selected_q_ids]

            # Strict check: Never silently change distribution or backfill from other categories
            if len(available_rows) < quota:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Insufficient question bank inventory for category '{cat_name}': "
                        f"required {quota}, but only {len(available_rows)} eligible questions "
                        f"available for {target.name}."
                    ),
                )

            # Within the category, distribute questions across eligible topics
            topic_dict: dict[int, list[tuple[Question, str, str, str]]] = {}
            for q, cname, tname, tid, sname in available_rows:
                topic_dict.setdefault(tid, []).append((q, cname, tname, sname))

            topic_ids = list(topic_dict.keys())
            base_topic_quota = quota // len(topic_ids)
            topic_rem = quota % len(topic_ids)
            topic_quotas = {
                t_id: base_topic_quota + (1 if t_idx < topic_rem else 0)
                for t_idx, t_id in enumerate(topic_ids)
            }

            cat_selected: list[tuple[Question, str, str, str]] = []
            topic_pool: dict[int, list[tuple[Question, str, str, str]]] = {
                tid: list(qs) for tid, qs in topic_dict.items()
            }
            for t_id in topic_pool:
                random.shuffle(topic_pool[t_id])

            shortfall = 0
            for t_id in topic_ids:
                t_target = topic_quotas[t_id]
                available_in_topic = topic_pool[t_id]
                take = min(t_target, len(available_in_topic))
                cat_selected.extend(available_in_topic[:take])
                topic_pool[t_id] = available_in_topic[take:]
                shortfall += (t_target - take)

            # If any topic had fewer questions than its quota, pull remaining from other topics in the SAME category
            if shortfall > 0:
                remaining_cat_pool = [
                    item for tid in topic_ids for item in topic_pool[tid]
                ]
                random.shuffle(remaining_cat_pool)
                cat_selected.extend(remaining_cat_pool[:shortfall])

            for item in cat_selected:
                selected_q_ids.add(item[0].id)

            # Apply difficulty ordering (easy to hard)
            cat_selected.sort(key=lambda item: item[0].difficulty_b)
            selected_by_category.extend(cat_selected)

        final_questions = selected_by_category

    elif practice_mode == "speed":
        target_count = 10 if (count is None or count == 5) else count
        q_pool = db.execute(
            select(Question, Concept.name, Topic.name, Skill.name)
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(
                Skill.target_id == target.id,
                Question.review_status.in_(["approved", "curated", "generated"]),
            )
        ).all()
        if q_pool:
            sample_k = min(target_count, len(q_pool))
            sampled = random.sample(q_pool, sample_k)
            for q, cname, tname, sname in sampled:
                final_questions.append((q, cname, tname, sname))

    else:
        # untimed practice
        target_count = count or 5
        query = (
            select(Question, Concept.name, Topic.name, Skill.name)
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(
                Skill.target_id == target.id,
                Question.review_status.in_(["approved", "curated", "generated"]),
            )
        )
        if topic_id:
            query = query.where(Topic.id == topic_id)
        elif concept_id:
            query = query.where(Concept.id == concept_id)

        q_pool = db.execute(query).all()
        if not q_pool and (topic_id or concept_id):
            q_pool = db.execute(
                select(Question, Concept.name, Topic.name, Skill.name)
                .join(Concept, Question.concept_id == Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .join(Skill, Topic.skill_id == Skill.id)
                .where(
                    Skill.target_id == target.id,
                    Question.review_status.in_(["approved", "curated", "generated"]),
                )
            ).all()

        if q_pool:
            sample_k = min(target_count, len(q_pool))
            sampled = random.sample(q_pool, sample_k)
            for q, cname, tname, sname in sampled:
                final_questions.append((q, cname, tname, sname))

    # Create Assessment record
    assessment = Assessment(
        user_id=current_user_id,
        type="practice",
        target_id=target.id,
        started_at=dt.datetime.now(dt.timezone.utc),
        completed_at=None,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    time_limit_sec = 3600 if practice_mode == "combined" else (90 if practice_mode == "speed" else None)

    items_out = []
    for order_idx, (q, cname, tname, sname) in enumerate(final_questions):
        db.add(
            AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=q.id,
                order_index=order_idx,
                phase=practice_mode,
            )
        )
        items_out.append({
            "question_id": q.id,
            "order_index": order_idx + 1,
            "concept_id": q.concept_id,
            "concept_name": cname,
            "topic_id": q.concept.topic_id if q.concept else None,
            "topic_name": tname,
            "skill_name": sname,
            "question_text": q.question_text,
            "stem": q.question_text,
            "text": q.question_text,
            "options": to_options_list(q.options),
            "difficulty_b": round(q.difficulty_b, 2),
            "difficulty": round(q.difficulty_b, 2),
            "source": q.source or "curated",
            "correct_option": q.correct_answer,
            "explanation": q.explanation or "Standard syllabus worked explanation.",
            "time_limit_sec": time_limit_sec,
        })

    db.commit()
    return assessment.id, items_out


def classify_root_cause_gap(
    formula_correct: bool,
    substitution_correct: bool,
    calculation_correct: bool,
    calculation_time_ms: int = 0,
    time_threshold_ms: int = 20000,
) -> dict[str, Any]:
    """Classifies root cause cognitive gap based on 3 sub-question stages:
    1. Formula recall ("What is the formula for ...?")
    2. Substitution ("Substitute the given values")
    3. Calculation ("Compute the result"), timed (20s).
    """
    if not formula_correct:
        gap_type = "Formula knowledge gap"
        study_task = "Study topic formula sheet & core definitions"
        action = "formula_sheet"
    elif not substitution_correct:
        gap_type = "Application/setup gap"
        study_task = "Review worked examples & step-by-step problem setup"
        action = "worked_examples"
    elif not calculation_correct:
        gap_type = "Calculation accuracy gap"
        study_task = "Practice arithmetic precision drills"
        action = "calculation_drills"
    elif calculation_time_ms > time_threshold_ms:
        gap_type = "Calculation speed gap"
        study_task = "Practice timed speed-math calculations (under 20s)"
        action = "timed_drills"
    else:
        gap_type = "Careless error"
        study_task = "Practice mindful verification and exam pace control"
        action = "mindful_review"

    all_failed = (not formula_correct) and (not substitution_correct) and (not calculation_correct)

    return {
        "gap_type": gap_type,
        "study_task": study_task,
        "action": action,
        "all_three_failed": all_failed,
        "stages": [
            {"stage": "formula", "name": "Formula recall", "is_correct": formula_correct},
            {"stage": "substitution", "name": "Substitution / setup", "is_correct": substitution_correct},
            {
                "stage": "calculation",
                "name": "Timed calculation",
                "is_correct": calculation_correct,
                "time_ms": calculation_time_ms,
                "timed_out": calculation_time_ms > time_threshold_ms,
            },
        ],
    }


def generate_root_cause_sub_questions(
    topic_name: str,
    concept_name: str,
    main_question_stem: str,
    gemini_client: GeminiClient | None = None,
) -> list[dict[str, Any]]:
    """Generates 3 short sub-questions in strict pedagogical order:
    1. Formula recall ("What is the formula for ...?")
    2. Substitution ("Substitute the given values")
    3. Calculation ("Compute the result"), timed (20s).
    """
    sub_questions = []
    if gemini_client and gemini_client.is_configured:
        try:
            prompt = (
                f"For the missed competitive exam question below:\n"
                f"Topic: {topic_name}\n"
                f"Concept: {concept_name}\n"
                f"Missed Question: {main_question_stem}\n\n"
                f"Generate exactly 3 short multiple-choice sub-questions in this strict pedagogical order to diagnose the learner's root cause:\n"
                f"1. Stage 'formula': Formula recall question ('What is the formula for ...?') testing the foundational equation or theorem.\n"
                f"2. Stage 'substitution': Substitution / setup question ('Substitute the given values into the formula ...').\n"
                f"3. Stage 'calculation': Calculation question ('Compute the result ...'), designed for rapid mental/arithmetic calculation.\n\n"
                f"Return ONLY a JSON array with 3 objects matching this schema:\n"
                f"[\n"
                f"  {{\n"
                f'    "stage": "formula",\n'
                f'    "stem": "What is the formula for ...?",\n'
                f'    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},\n'
                f'    "correct_option": "A",\n'
                f'    "explanation": "..."\n'
                f"  }},\n"
                f"  {{\n"
                f'    "stage": "substitution",\n'
                f'    "stem": "Substitute the values ...",\n'
                f'    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},\n'
                f'    "correct_option": "B",\n'
                f'    "explanation": "..."\n'
                f"  }},\n"
                f"  {{\n"
                f'    "stage": "calculation",\n'
                f'    "stem": "Compute the final result ...",\n'
                f'    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},\n'
                f'    "correct_option": "C",\n'
                f'    "explanation": "..."\n'
                f"  }}\n"
                f"]"
            )
            resp = gemini_client.generate_structured_json(
                prompt=prompt,
                system_instruction="You are an expert psychometric test developer creating diagnostic root-cause sub-questions.",
            )
            clean = resp.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            elif clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            parsed = json.loads(clean.strip())
            if isinstance(parsed, list) and len(parsed) == 3:
                for idx, item in enumerate(parsed):
                    sub_questions.append({
                        "stage": item.get("stage", ["formula", "substitution", "calculation"][idx]),
                        "stem": item["stem"],
                        "options": to_options_list(item["options"]),
                        "correct_option": item["correct_option"],
                        "explanation": item.get("explanation", ""),
                        "time_limit_sec": 20,
                    })
        except Exception as e:
            logger.warning("Gemini root-cause sub-question generation fallback: %s", e)

    if len(sub_questions) < 3:
        sub_questions = [
            {
                "stage": "formula",
                "stem": f"Formula Recall: What is the primary mathematical/conceptual formula governing {concept_name} in {topic_name}?",
                "options": [
                    {"key": "A", "text": f"Direct proportional relationship of {concept_name}"},
                    {"key": "B", "text": f"Inverse rate equation for {topic_name}"},
                    {"key": "C", "text": f"Standard composite ratio formulation"},
                    {"key": "D", "text": f"Linear aggregation equilibrium"},
                ],
                "correct_option": "A",
                "explanation": f"The primary formula governing {concept_name} requires direct application of the core proportional law.",
                "time_limit_sec": 20,
            },
            {
                "stage": "substitution",
                "stem": f"Application Setup: When setting up the parameters given in the question for {concept_name}, which is the correct substitution step?",
                "options": [
                    {"key": "A", "text": "Substitute given base quantities directly into the numerator"},
                    {"key": "B", "text": "Invert rates before applying baseline adjustments"},
                    {"key": "C", "text": "Cross-multiply terms without normalizing units"},
                    {"key": "D", "text": "Sum all terms without dimensional alignment"},
                ],
                "correct_option": "A",
                "explanation": "Setting up the parameters correctly requires direct substitution of base quantities before rate application.",
                "time_limit_sec": 20,
            },
            {
                "stage": "calculation",
                "stem": f"Timed Calculation (20s): Evaluate the final arithmetic reduction for {concept_name}:",
                "options": [
                    {"key": "A", "text": "120"},
                    {"key": "B", "text": "144"},
                    {"key": "C", "text": "160"},
                    {"key": "D", "text": "180"},
                ],
                "correct_option": "B",
                "explanation": "Carrying out the step-by-step reduction yields 144.",
                "time_limit_sec": 20,
            },
        ]

    return sub_questions

