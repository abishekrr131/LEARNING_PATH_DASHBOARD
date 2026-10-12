"""Learning Path and Educational Resources API Router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.session import get_db
from backend.app.models.core import (
    Concept,
    ConceptDependency,
    LearnerProfile,
    LearningResource,
    Skill,
    StudentMastery,
    Topic,
    User,
)
from backend.app.services.path import build_curriculum_path, insert_remediation, topological_order
from ml.graph.dag_validator import SimpleDiGraph

router = APIRouter()


@router.get("/path")
def get_learning_path(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the personalised adaptive learning path with topological sorting
    and dynamically inserted root-cause remediations (Screen 14).
    """
    profile = db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    target_id = profile.target_id if profile else 1

    # Fetch concepts for this target
    concepts_rows = db.execute(
        select(Concept, Topic.name, Skill.name)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target_id)
        .order_by(Concept.id)
    ).all()
    concept_map = {c.id: (c, tname, sname) for c, tname, sname in concepts_rows}
    all_concept_ids = list(concept_map.keys())

    # Build DAG
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])

    # Get mastered concepts (> 0.70 mastery)
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == current_user.id)
    ).scalars().all()
    mastered_ids = {m.concept_id for m in masteries if m.mastery_score >= 0.70}
    weak_ids = [m.concept_id for m in masteries if m.mastery_score < 0.40]

    # Dynamically find if weak concepts have unmastered prerequisites to insert
    remediations: list[tuple[int, int]] = []
    for weak_c in weak_ids:
        preds = list(g.predecessors(weak_c))
        for p in preds:
            if p in all_concept_ids and p not in mastered_ids:
                remediations.append((weak_c, p))

    path_items = build_curriculum_path(
        graph=g,
        all_target_concept_ids=all_concept_ids,
        mastered_concept_ids=mastered_ids,
        remediations=remediations,
    )

    enriched_path = []
    for item in path_items:
        c_id = item["concept_id"]
        c_obj, tname, sname = concept_map.get(c_id, (None, "", ""))
        if not c_obj:
            continue

        is_remediation = any(r[1] == c_id for r in remediations)

        enriched_path.append({
            "concept_id": c_id,
            "concept_name": c_obj.name,
            "topic_name": tname,
            "skill_name": sname,
            "order_index": item["order_index"],
            "status": item["status"],
            "difficulty_level": c_obj.difficulty_level,
            "is_remediation_inserted": is_remediation,
            "remediation_reason": "Prerequisite root cause flagged for prior mastery" if is_remediation else None,
            "unmet_prerequisites": item["unmet_prerequisites"],
        })

    return {
        "target_id": target_id,
        "total_nodes": len(enriched_path),
        "completed_count": len(mastered_ids),
        "remediations_active": len(remediations),
        "path": enriched_path,
    }


@router.get("/resources")
def get_learning_resources(
    concept_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns curated learning resources ranked by relevance (Screen 15)."""
    q = select(LearningResource)
    if concept_id:
        q = q.where(LearningResource.concept_id == concept_id)

    resources = db.execute(q.limit(20)).scalars().all()

    out = []
    for r in resources:
        concept = db.get(Concept, r.concept_id)
        cname = concept.name if concept else f"Concept {r.concept_id}"
        out.append({
            "id": r.id,
            "concept_id": r.concept_id,
            "concept_name": cname,
            "title": r.title,
            "resource_type": r.resource_type,
            "url": r.url,
            "description": r.description,
            "source": r.source,
            "difficulty_level": r.difficulty_level,
            "why_recommended": "Core prerequisite material for targeted remediation",
        })

    # If database has no seeded learning resources yet, provide standard curated recommendations
    if not out:
        c_id = concept_id or 1
        concept = db.get(Concept, c_id)
        cname = concept.name if concept else "Foundations"
        out = [
            {
                "id": 101,
                "concept_id": c_id,
                "concept_name": cname,
                "title": f"Comprehensive Guide: {cname}",
                "resource_type": "article",
                "url": "https://en.wikipedia.org/wiki/" + cname.replace(" ", "_"),
                "description": f"In-depth theoretical walkthrough and conceptual principles of {cname}.",
                "source": "curated",
                "difficulty_level": "intermediate",
                "why_recommended": "Targeted remediation for diagnosed gap",
            },
            {
                "id": 102,
                "concept_id": c_id,
                "concept_name": cname,
                "title": f"Interactive Video Tutorial: {cname}",
                "resource_type": "video",
                "url": "https://www.youtube.com/results?search_query=" + cname.replace(" ", "+"),
                "description": f"Step-by-step visual demonstration and worked examples covering {cname}.",
                "source": "curated",
                "difficulty_level": "beginner",
                "why_recommended": "Recommended for visual comprehension before next diagnostic",
            },
        ]

    return {"resources": out}
