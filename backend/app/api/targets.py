"""Career Targets and Curricula API Router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.core import CareerTarget, Concept, ConceptDependency, Question, Skill, Topic
from backend.app.schemas.target import (
    ConceptOut,
    GraphEdgeOut,
    GraphNodeOut,
    SkillOut,
    TargetDetailOut,
    TargetGraphOut,
    TargetSummaryOut,
    TopicOut,
)
from ml.graph.dag_validator import SimpleDiGraph, is_directed_acyclic_graph
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[TargetSummaryOut])
def list_targets(db: Session = Depends(get_db)):
    """List all career targets with high-level statistics."""
    targets = db.execute(select(CareerTarget).order_by(CareerTarget.category, CareerTarget.id)).scalars().all()
    if not targets:
        try:
            from database.seed.seed_all import seed_database
            logger.info("No targets found in database; auto-seeding default curricula...")
            seed_database(db, auto_approve=True)
            db.commit()
            targets = db.execute(select(CareerTarget).order_by(CareerTarget.category, CareerTarget.id)).scalars().all()
        except Exception as exc:
            db.rollback()
            logger.error("Auto-seeding in list_targets failed: %s", exc)

    out = []
    for t in targets:
        skill_count = db.execute(
            select(func.count(Skill.id)).where(Skill.target_id == t.id)
        ).scalar() or 0
        
        concept_count = db.execute(
            select(func.count(Concept.id))
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(Skill.target_id == t.id)
        ).scalar() or 0

        question_count = db.execute(
            select(func.count(Question.id))
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .where(Skill.target_id == t.id)
        ).scalar() or 0

        out.append(
            TargetSummaryOut(
                id=t.id,
                name=t.name,
                category=t.category,
                description=t.description,
                skill_count=skill_count,
                concept_count=concept_count,
                question_count=question_count,
            )
        )
    return out


@router.get("/{target_id}", response_model=TargetDetailOut)
def get_target_detail(target_id: int, db: Session = Depends(get_db)):
    """Fetch complete hierarchical curriculum for a specific target."""
    target = db.get(CareerTarget, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    skills = db.execute(
        select(Skill).where(Skill.target_id == target.id).order_by(Skill.id)
    ).scalars().all()

    skills_out = []
    for s in skills:
        topics = db.execute(
            select(Topic).where(Topic.skill_id == s.id).order_by(Topic.id)
        ).scalars().all()
        
        topics_out = []
        for idx, tp in enumerate(topics, start=1):
            concepts = db.execute(
                select(Concept).where(Concept.topic_id == tp.id).order_by(Concept.id)
            ).scalars().all()
            
            concepts_out = [
                ConceptOut(
                    id=c.id,
                    name=c.name,
                    description=c.description,
                    difficulty_level="intermediate",
                    topic_id=tp.id,
                    topic_name=tp.name,
                    skill_id=s.id,
                    skill_name=s.name,
                )
                for c in concepts
            ]
            topics_out.append(
                TopicOut(
                    id=tp.id,
                    name=tp.name,
                    order_index=idx,
                    skill_id=s.id,
                    concepts=concepts_out,
                )
            )

        skills_out.append(
            SkillOut(
                id=s.id,
                name=s.name,
                weight=s.weight,
                topics=topics_out,
            )
        )

    return TargetDetailOut(
        id=target.id,
        name=target.name,
        category=target.category,
        description=target.description,
        readiness_threshold=target.readiness_threshold,
        skills=skills_out,
    )


@router.get("/{target_id}/graph", response_model=TargetGraphOut)
def get_target_graph(target_id: int, db: Session = Depends(get_db)):
    """Fetch concept prerequisite DAG for visualization and path navigation."""
    target = db.get(CareerTarget, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    concepts_rows = db.execute(
        select(Concept, Skill.name)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Skill, Topic.skill_id == Skill.id)
        .where(Skill.target_id == target.id)
    ).all()

    concept_ids = {c.id for c, _ in concepts_rows}
    nodes = [
        GraphNodeOut(
            id=c.id,
            name=c.name,
            skill_name=skill_name,
            difficulty_level="intermediate",
            status="available",
        )
        for c, skill_name in concepts_rows
    ]

    edges_rows = db.execute(
        select(ConceptDependency).where(
            ConceptDependency.prerequisite_id.in_(concept_ids),
            ConceptDependency.concept_id.in_(concept_ids),
        )
    ).scalars().all()

    edges = [
        GraphEdgeOut(
            source=e.prerequisite_id,
            target=e.concept_id,
            weight=e.strength,
        )
        for e in edges_rows
    ]

    # Validate acyclicity
    g = SimpleDiGraph([(e.source, e.target) for e in edges])
    is_dag = is_directed_acyclic_graph(g)

    return TargetGraphOut(
        target_id=target.id,
        target_name=target.name,
        nodes=nodes,
        edges=edges,
        is_dag=is_dag,
    )
