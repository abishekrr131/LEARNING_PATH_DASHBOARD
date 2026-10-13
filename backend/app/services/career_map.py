"""Adaptive Career Ready Map Service.

Implements Master Prompt Requirements 4 & 5:
- Topic coverage readiness (%) = (distinct topics demonstrated correctly / total relevant syllabus topics) * 100
- Distinct from raw accuracy (%)
- Learning stage categorization: Foundation (<25%), Developing (25-49%), Proficient (50-74%), Career Ready (>=75%)
- Categorization into:
  * Demonstrated topics (proven in diagnostic or practice)
  * Weak topics & concepts with DAG root-cause prerequisite tracing
  * Unassessed topics (syllabus topics not covered in 10-Q diagnostic, flagged for follow-up)
  * Prerequisite gaps with priority levels (HIGH, MEDIUM, LOW)
  * Recommended verified study materials & targeted practice tests
  * Next topic to unlock per skill and overall
  * Progress milestones toward 100% readiness
- Consistent persistence across page reloads and logins.
"""
from __future__ import annotations

import datetime as dt
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.core import (
    CareerTarget,
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningResource,
    Question,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    TopicPerformance,
    User,
)
from backend.app.services.path import topological_order
from backend.app.services.root_cause import get_ancestors_within_hops, rank_root_cause_candidates
from ml.graph.dag_validator import SimpleDiGraph


def calculate_career_ready_map(
    db: Session,
    user_id: int,
    target_id: int | None = None,
) -> dict[str, Any]:
    """Generates the comprehensive Career Ready Map for the learner."""
    # 1. Resolve Target
    if not target_id:
        profile = db.execute(
            select(LearnerProfile).where(LearnerProfile.user_id == user_id)
        ).scalar_one_or_none()
        target_id = profile.target_id if profile else 1

    target = db.get(CareerTarget, target_id)
    if not target:
        target = db.execute(select(CareerTarget)).scalars().first()
        target_id = target.id if target else 1

    target_name = target.name if target else "General Curriculum"
    target_category = target.category if target else "career"
    threshold = target.readiness_threshold if target else 0.70

    # 2. Retrieve Skills, Topics, Concepts for Target
    skills = db.execute(
        select(Skill).where(Skill.target_id == target_id).order_by(Skill.weight.desc(), Skill.id)
    ).scalars().all()

    topics = db.execute(
        select(Topic)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
        .order_by(Topic.id)
    ).scalars().all()

    total_syllabus_topics = len(topics)
    topic_map = {t.id: t for t in topics}

    concepts = db.execute(
        select(Concept)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
        .order_by(Concept.id)
    ).scalars().all()
    concept_map = {c.id: c for c in concepts}
    concepts_by_topic: dict[int, list[Concept]] = {}
    for c in concepts:
        concepts_by_topic.setdefault(c.topic_id, []).append(c)

    # 3. Build Concept Dependency DAG
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])
    for cid in concept_map.keys():
        g.add_node(cid)

    # 4. Fetch User Responses and Masteries
    responses = db.execute(
        select(StudentResponse).where(StudentResponse.user_id == user_id)
    ).scalars().all()

    total_attempts = len(responses)
    correct_count = sum(1 for r in responses if r.is_correct)
    raw_accuracy_pct = round((correct_count / total_attempts) * 100.0, 1) if total_attempts > 0 else 0.0

    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == user_id)
    ).scalars().all()
    mastery_map = {m.concept_id: m.mastery_score for m in masteries}

    # Responses by topic and concept
    correct_concept_ids = set()
    tested_topic_ids = set()
    topic_responses: dict[int, list[StudentResponse]] = {}

    for r in responses:
        q = db.get(Question, r.question_id)
        if not q:
            continue
        c = concept_map.get(q.concept_id)
        if c:
            tested_topic_ids.add(c.topic_id)
            topic_responses.setdefault(c.topic_id, []).append(r)
            if r.is_correct:
                correct_concept_ids.add(c.id)

    # 5. Determine Demonstrated Topics (Formula 17)
    # A topic is demonstrated if student answered questions correctly on it OR average topic mastery >= 0.60
    demonstrated_topic_ids = set()
    weak_topic_ids = set()

    for t in topics:
        t_resps = topic_responses.get(t.id, [])
        t_concepts = concepts_by_topic.get(t.id, [])
        c_masteries = [mastery_map.get(c.id, 0.50) for c in t_concepts if c.id in mastery_map]
        avg_mastery = (sum(c_masteries) / len(c_masteries)) if c_masteries else 0.0

        has_correct_answer = any(r.is_correct for r in t_resps)
        if has_correct_answer or (avg_mastery >= 0.60 and len(c_masteries) > 0):
            demonstrated_topic_ids.add(t.id)
        elif t.id in tested_topic_ids:
            weak_topic_ids.add(t.id)

    # Distinct topics demonstrated correctly count
    demonstrated_topics_count = len(demonstrated_topic_ids)

    # Topic coverage readiness (%) formula:
    # (distinct topics demonstrated correctly / total relevant syllabus topics) * 100
    if total_syllabus_topics > 0:
        topic_coverage_readiness_pct = round(
            (demonstrated_topics_count / total_syllabus_topics) * 100.0, 1
        )
    else:
        topic_coverage_readiness_pct = 0.0

    # 6. Overall Learning Stage
    if total_attempts == 0:
        learning_stage = "Unassessed"
        stage_description = "Initial diagnostic not yet taken. Complete the 10-question diagnostic to establish your personalized baseline."
    elif topic_coverage_readiness_pct < 25.0:
        learning_stage = "Foundation Stage"
        stage_description = "Establishing core conceptual foundations and resolving early prerequisite gaps."
    elif topic_coverage_readiness_pct < 50.0:
        learning_stage = "Developing Stage"
        stage_description = "Expanding topic breadth, practicing application problems, and consolidating core competencies."
    elif topic_coverage_readiness_pct < 75.0:
        learning_stage = "Proficient Stage"
        stage_description = "Strong syllabus mastery demonstrated. Closing remaining prerequisite gaps to reach career readiness."
    else:
        learning_stage = "Career Ready"
        stage_description = "Target benchmark readiness achieved! Maintain memory retention with periodic spaced review tests."

    # 7. Unassessed Topics
    unassessed_topic_ids = set(t.id for t in topics) - tested_topic_ids
    unassessed_topics = []
    for tid in sorted(unassessed_topic_ids):
        top = topic_map[tid]
        sk = db.get(Skill, top.skill_id)
        unassessed_topics.append({
            "topic_id": top.id,
            "topic_name": top.name,
            "skill_id": top.skill_id,
            "skill_name": sk.name if sk else "General",
            "status": "unassessed",
            "needs_followup": True,
            "action": "Take Follow-Up Assessment",
            "followup_url": f"/practice?topic_id={top.id}",
        })

    # 8. Demonstrated Topics Detailed List
    demonstrated_topics = []
    for tid in sorted(demonstrated_topic_ids):
        top = topic_map[tid]
        sk = db.get(Skill, top.skill_id)
        t_resps = topic_responses.get(tid, [])
        corr_in_t = sum(1 for r in t_resps if r.is_correct)
        tot_in_t = len(t_resps)
        t_acc = round((corr_in_t / tot_in_t) * 100.0, 1) if tot_in_t > 0 else 100.0
        demonstrated_topics.append({
            "topic_id": top.id,
            "topic_name": top.name,
            "skill_id": top.skill_id,
            "skill_name": sk.name if sk else "General",
            "status": "demonstrated",
            "accuracy": t_acc,
            "questions_answered": tot_in_t,
            "questions_correct": corr_in_t,
            "is_demonstrated": True,
        })

    # 9. Weak Topics, Concepts & Root Causes (Prerequisite Gaps)
    weak_topics = []
    prerequisite_gaps = []
    weak_concept_ids_all = set()

    # Preload learning resources for target concepts
    target_concept_ids = list(concept_map.keys())
    db_resources = db.execute(
        select(LearningResource).where(LearningResource.concept_id.in_(target_concept_ids))
    ).scalars().all()
    res_by_concept: dict[int, list[LearningResource]] = {}
    for r in db_resources:
        res_by_concept.setdefault(r.concept_id, []).append(r)

    for tid in sorted(weak_topic_ids):
        top = topic_map[tid]
        sk = db.get(Skill, top.skill_id)
        t_resps = topic_responses.get(tid, [])
        corr_in_t = sum(1 for r in t_resps if r.is_correct)
        tot_in_t = len(t_resps)
        t_acc = round((corr_in_t / tot_in_t) * 100.0, 1) if tot_in_t > 0 else 0.0

        t_concepts = concepts_by_topic.get(tid, [])
        topic_weak_concepts = []

        for c in t_concepts:
            m_score = mastery_map.get(c.id, 0.40)
            is_missed = (c.id not in correct_concept_ids) and (t.id in tested_topic_ids)
            if is_missed or m_score < 0.60:
                weak_concept_ids_all.add(c.id)

                # Trace DAG prerequisite root causes
                preds = list(g.predecessors(c.id)) if hasattr(g, "predecessors") else []
                unmet_preds = [p for p in preds if p not in correct_concept_ids and mastery_map.get(p, 0.0) < 0.60]

                root_causes_info = []
                for p_id in unmet_preds:
                    p_concept = concept_map.get(p_id)
                    if p_concept:
                        p_res = res_by_concept.get(p_id, [])
                        best_p_res = p_res[0] if p_res else None
                        gap_item = {
                            "prerequisite_concept_id": p_id,
                            "prerequisite_name": p_concept.name,
                            "blocks_concept_id": c.id,
                            "blocks_concept_name": c.name,
                            "priority_level": "HIGH",
                            "resource_title": best_p_res.title if best_p_res else f"Study {p_concept.name}",
                            "resource_url": best_p_res.url if best_p_res else "https://ncert.nic.in/",
                            "provider": best_p_res.provider if best_p_res else "Verified Source",
                        }
                        root_causes_info.append(gap_item)
                        prerequisite_gaps.append(gap_item)

                # Concept resources
                c_res = res_by_concept.get(c.id, [])
                primary_res = c_res[0] if c_res else None

                topic_weak_concepts.append({
                    "concept_id": c.id,
                    "concept_name": c.name,
                    "mastery_score": round(m_score, 2),
                    "priority": "HIGH" if (is_missed and m_score < 0.40) else "MEDIUM",
                    "root_causes": root_causes_info,
                    "recommended_resource": {
                        "id": primary_res.id if primary_res else None,
                        "title": primary_res.title if primary_res else f"Curated Guide on {c.name}",
                        "provider": primary_res.provider if primary_res else "Verified Partner",
                        "url": primary_res.url if primary_res else "https://ncert.nic.in/",
                        "resource_type": primary_res.resource_type if primary_res else "article",
                        "estimated_duration_min": primary_res.estimated_duration_min if primary_res else 30,
                        "difficulty": primary_res.difficulty if primary_res else "Intermediate",
                    } if primary_res else None,
                })

        weak_topics.append({
            "topic_id": top.id,
            "topic_name": top.name,
            "skill_id": top.skill_id,
            "skill_name": sk.name if sk else "General",
            "accuracy": t_acc,
            "priority": "HIGH" if t_acc < 50.0 else "MEDIUM",
            "weak_concepts": topic_weak_concepts,
            "action": "Start Targeted Practice",
            "practice_url": f"/practice?topic_id={top.id}",
        })

    # 10. Next Topic to Unlock (Per Skill and Overall Progression)
    skill_progressions = []
    overall_next_unlock = None

    for s in skills:
        s_topics = [t for t in topics if t.skill_id == s.id]
        if not s_topics:
            continue

        s_dem = [t for t in s_topics if t.id in demonstrated_topic_ids]
        s_dem_count = len(s_dem)
        s_total = len(s_topics)
        s_pct = round((s_dem_count / s_total) * 100.0, 1) if s_total > 0 else 0.0

        # Find next sequential topic in skill
        next_in_skill = None
        for t in s_topics:
            if t.id not in demonstrated_topic_ids:
                next_in_skill = {
                    "topic_id": t.id,
                    "topic_name": t.name,
                    "skill_id": s.id,
                    "skill_name": s.name,
                    "status": "ready_to_learn" if s_dem_count > 0 else "initial_focus",
                    "reason": f"Unlock by achieving mastery in {s.name}",
                }
                break

        if next_in_skill and overall_next_unlock is None:
            overall_next_unlock = next_in_skill

        skill_progressions.append({
            "skill_id": s.id,
            "skill_name": s.name,
            "weight": s.weight,
            "demonstrated_count": s_dem_count,
            "total_count": s_total,
            "progress_pct": s_pct,
            "next_unlocked_topic": next_in_skill,
        })

    # 11. Progress Milestones Toward 100% Readiness
    milestones = [
        {
            "id": "m1_diagnostic",
            "title": "Complete 10-Question Initial Diagnostic",
            "description": "Establish psychometric baseline across 10 distinct topics.",
            "completed": total_attempts >= 10,
            "progress_pct": 100 if total_attempts >= 10 else round((total_attempts / 10.0) * 100, 1),
        },
        {
            "id": "m2_remediate_roots",
            "title": "Remediate Core Prerequisite Gaps",
            "description": "Resolve high-priority foundational prerequisites identified in DAG root-cause analysis.",
            "completed": total_attempts > 0 and len(prerequisite_gaps) == 0,
            "progress_pct": 100 if (total_attempts > 0 and len(prerequisite_gaps) == 0) else max(0, 100 - (len(prerequisite_gaps) * 25)),
        },
        {
            "id": "m3_unassessed_followup",
            "title": "Assess Full Curriculum Syllabus",
            "description": "Test remaining unassessed syllabus topics via follow-up practice tests.",
            "completed": len(unassessed_topics) == 0 and total_attempts > 0,
            "progress_pct": round(((total_syllabus_topics - len(unassessed_topics)) / total_syllabus_topics) * 100.0, 1) if total_syllabus_topics > 0 else 0,
        },
        {
            "id": "m4_halfway_mastery",
            "title": "Attain 50% Topic Mastery Coverage",
            "description": "Demonstrate mastery across at least half of all target syllabus topics.",
            "completed": topic_coverage_readiness_pct >= 50.0,
            "progress_pct": min(100, round((topic_coverage_readiness_pct / 50.0) * 100, 1)),
        },
        {
            "id": "m5_career_ready",
            "title": f"Reach Target Benchmark ({int(threshold * 100)}% Coverage)",
            "description": f"Achieve career ready status for {target_name}.",
            "completed": topic_coverage_readiness_pct >= (threshold * 100.0),
            "progress_pct": min(100, round((topic_coverage_readiness_pct / (threshold * 100.0)) * 100, 1)),
        },
    ]

    return {
        "target_id": target_id,
        "target_name": target_name,
        "target_category": target_category,
        "readiness_threshold_pct": round(threshold * 100.0, 1),
        "total_syllabus_topics": total_syllabus_topics,
        "demonstrated_topics_count": demonstrated_topics_count,
        "topic_coverage_readiness_pct": topic_coverage_readiness_pct,
        "raw_accuracy_pct": raw_accuracy_pct,
        "total_attempts": total_attempts,
        "correct_count": correct_count,
        "learning_stage": learning_stage,
        "stage_description": stage_description,
        "is_career_ready": topic_coverage_readiness_pct >= (threshold * 100.0),
        "demonstrated_topics": demonstrated_topics,
        "weak_topics": weak_topics,
        "unassessed_topics": unassessed_topics,
        "prerequisite_gaps": prerequisite_gaps[:10],
        "next_unlocked_topic": overall_next_unlock,
        "skills": skill_progressions,
        "milestones": milestones,
    }
