"""Master Seed Script for Personalized Learning Path Dashboard (RCT-GAT)
Seeds all 7 targets (4 IT, 3 Govt) with skills, topics, concepts, DAG edges, and ~60 questions each.
"""
from __future__ import annotations
import sys
import os

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ml.graph.dag_validator import create_graph, is_directed_acyclic_graph, find_cycle

from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal, engine
from backend.app.models.base import Base
from backend.app.models.core import (
    CareerTarget, Skill, Topic, Concept, ConceptDependency,
    Question, LearningResource, User
)

from database.seed.data.it_ml_engineer import TARGET as ML_ENG
from database.seed.data.it_full_stack import TARGET as FULL_STACK
from database.seed.data.it_cyber_security import TARGET as CYBER_SEC
from database.seed.data.it_genai import TARGET as GENAI
from database.seed.data.govt_upsc import TARGET as UPSC
from database.seed.data.govt_ssc_cgl import TARGET as SSC_CGL
from database.seed.data.govt_banking import TARGET as BANKING

ALL_TARGETS = [ML_ENG, FULL_STACK, CYBER_SEC, GENAI, UPSC, SSC_CGL, BANKING]


def validate_curricula():
    """Validates that all targets satisfy DAG acyclicity and weight invariants."""
    print("Validating curricula invariants across all 7 targets...")
    for item in ALL_TARGETS:
        name = item["target"]["name"]
        
        # 1. Validate skill weights sum to 1.0
        total_weight = sum(s["weight"] for s in item["skills"])
        assert abs(total_weight - 1.0) < 1e-6, f"Target '{name}': Skill weights sum to {total_weight}, must be 1.0"
        
        # 2. Count concepts
        concept_count = sum(len(c_list) for c_list in item["concepts"].values())
        assert concept_count >= 35, f"Target '{name}': Has {concept_count} concepts, expected >= 35"
        
        # 3. Validate DAG
        g = create_graph()
        for p, d, w in item["dependencies"]:
            g.add_edge(p, d, weight=w)
        
        assert is_directed_acyclic_graph(g), f"Target '{name}': Cycle detected in dependency graph: {find_cycle(g)}"
        
        # 4. Check questions
        q_count = len(item["questions"])
        assert q_count >= 40, f"Target '{name}': Has {q_count} questions, expected >= 40"
        
        print(f"  [OK] {name}: {len(item['skills'])} skills, {concept_count} concepts, {len(item['dependencies'])} DAG edges, {q_count} questions (DAG valid)")
    print("All curricula invariants verified successfully.\n")


def seed_database(db: Session, auto_approve: bool = False):
    """Inserts curricula, DAG edges, and questions into PostgreSQL."""
    validate_curricula()

    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)

    # 1. Ensure a default reviewer user exists
    reviewer = db.query(User).filter(User.email == "reviewer@palp.internal").first()
    if not reviewer:
        reviewer = User(
            name="Curriculum Reviewer",
            email="reviewer@palp.internal",
            role="reviewer"
        )
        db.add(reviewer)
        db.flush()

    total_targets = 0
    total_skills = 0
    total_topics = 0
    total_concepts = 0
    total_edges = 0
    total_questions = 0

    for item in ALL_TARGETS:
        t_data = item["target"]
        target = db.query(CareerTarget).filter(CareerTarget.name == t_data["name"]).first()
        if not target:
            target = CareerTarget(
                category=t_data["category"],
                name=t_data["name"],
                description=t_data["description"],
                readiness_threshold=t_data["readiness_threshold"],
            )
            db.add(target)
            db.flush()
        total_targets += 1

        concept_name_to_id: dict[str, int] = {}

        # Skills
        for s_data in item["skills"]:
            skill = db.query(Skill).filter(
                Skill.target_id == target.id,
                Skill.name == s_data["name"]
            ).first()
            if not skill:
                skill = Skill(target_id=target.id, name=s_data["name"], weight=s_data["weight"])
                db.add(skill)
                db.flush()
            total_skills += 1

            # Topics under skill
            topic_names = item["topics"].get(s_data["name"], [])
            for t_name in topic_names:
                topic = db.query(Topic).filter(
                    Topic.skill_id == skill.id,
                    Topic.name == t_name
                ).first()
                if not topic:
                    topic = Topic(skill_id=skill.id, name=t_name, description=f"Topic covering {t_name}")
                    db.add(topic)
                    db.flush()
                total_topics += 1

                # Concepts under topic
                concept_tuples = item["concepts"].get(t_name, [])
                for c_name, c_desc in concept_tuples:
                    concept = db.query(Concept).filter(
                        Concept.topic_id == topic.id,
                        Concept.name == c_name
                    ).first()
                    if not concept:
                        concept = Concept(
                            topic_id=topic.id,
                            name=c_name,
                            description=c_desc,
                            mastery_threshold=0.70
                        )
                        db.add(concept)
                        db.flush()
                    concept_name_to_id[c_name] = concept.id
                    total_concepts += 1

                    # Add a default learning resource for the concept if none exists
                    res = db.query(LearningResource).filter(LearningResource.concept_id == concept.id).first()
                    if not res:
                        db.add(LearningResource(
                            concept_id=concept.id,
                            title=f"Core Foundations: {c_name}",
                            resource_type="article",
                            url=f"https://learn.internal/docs/{concept.id}",
                            description=c_desc,
                            quality_score=0.95
                        ))

        # Dependencies
        for prereq_name, dep_name, weight in item["dependencies"]:
            p_id = concept_name_to_id.get(prereq_name)
            d_id = concept_name_to_id.get(dep_name)
            if p_id and d_id:
                dep = db.query(ConceptDependency).filter(
                    ConceptDependency.prerequisite_concept_id == p_id,
                    ConceptDependency.dependent_concept_id == d_id
                ).first()
                if not dep:
                    dep = ConceptDependency(
                        prerequisite_concept_id=p_id,
                        dependent_concept_id=d_id,
                        relation_weight=weight,
                        source="expert"
                    )
                    db.add(dep)
                    db.flush()
                total_edges += 1

        # Questions (flagged as pending review by default)
        for q_data in item["questions"]:
            c_id = concept_name_to_id.get(q_data["concept"])
            if c_id:
                existing_q = db.query(Question).filter(
                    Question.concept_id == c_id,
                    Question.question_text == q_data["text"]
                ).first()
                if not existing_q:
                    status = "approved" if auto_approve else "pending"
                    reviewed_by_id = reviewer.id if auto_approve else None
                    needs_rev = False if auto_approve else True
                    q = Question(
                        concept_id=c_id,
                        question_text=q_data["text"],
                        options_json=q_data["options"],
                        correct_answer=q_data["answer"],
                        explanation=q_data["explanation"],
                        difficulty_hint=q_data.get("difficulty_hint", 0.0),
                        source="curated",
                        review_status=status,
                        reviewed_by=reviewed_by_id,
                        needs_human_review=needs_rev
                    )
                    db.add(q)
                total_questions += 1

    db.commit()
    print("Database seeding completed:")
    print(f"  Targets: {total_targets}")
    print(f"  Skills: {total_skills}")
    print(f"  Topics: {total_topics}")
    print(f"  Concepts: {total_concepts}")
    print(f"  Prerequisite DAG Edges: {total_edges}")
    print(f"  Curated Questions: {total_questions} (Status: {'approved' if auto_approve else 'pending review'})")


if __name__ == "__main__":
    auto = "--approve-all" in sys.argv
    db = SessionLocal()
    try:
        seed_database(db, auto_approve=auto)
    finally:
        db.close()
