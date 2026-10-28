"""Script to add get_resource_detail endpoint to backend/app/api/learning.py."""
import os

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "app", "api", "learning.py")

with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Normalize line endings to \n
text = text.replace("\r\n", "\n")

# Add is_internal to out.append in get_learning_resources
old_needle = '"url": lr.url,\n            "description": lr.description'
new_needle = '"url": lr.url,\n            "is_internal": not lr.url or "learn.internal" in lr.url or lr.url.startswith("/"),\n            "description": lr.description'

if old_needle in text:
    text = text.replace(old_needle, new_needle)

# Add is_internal to fallback items as well
fallback_old = '"url": f"https://www.youtube.com/results?search_query={c_slug}+tutorial",\n                    "description":'
fallback_new = '"url": f"https://www.youtube.com/results?search_query={c_slug}+tutorial",\n                    "is_internal": False,\n                    "description":'
if fallback_old in text:
    text = text.replace(fallback_old, fallback_new)

endpoint_code = '''

@router.get("/resources/{resource_id}")
def get_resource_detail(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns comprehensive study material and curriculum guide for a specific resource or concept."""
    from backend.app.models.core import CareerTarget, Question, StudentResponse

    # 1. Lookup LearningResource by id, or fallback by concept_id
    lr = db.get(LearningResource, resource_id)
    concept = None
    if lr:
        concept = db.get(Concept, lr.concept_id)
    else:
        # Fallback: resource_id might be a concept_id
        concept = db.get(Concept, resource_id)
        if concept:
            lr = db.execute(
                select(LearningResource).where(LearningResource.concept_id == concept.id)
            ).scalars().first()

    if not lr and not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study resource or concept with ID {resource_id} not found",
        )

    concept_id = concept.id if concept else lr.concept_id
    if not concept:
        concept = db.get(Concept, concept_id)

    topic = db.get(Topic, concept.topic_id) if concept and concept.topic_id else None
    skill = db.get(Skill, topic.skill_id) if topic and topic.skill_id else None
    target = db.get(CareerTarget, skill.target_id) if skill and skill.target_id else None

    target_id = target.id if target else 1
    target_name = target.name if target else "General Curriculum"
    topic_name = topic.name if topic else "General Topic"
    skill_name = skill.name if skill else "General Skill"
    concept_name = concept.name if concept else (lr.title if lr else "Core Concept")
    concept_desc = concept.description if concept and concept.description else (lr.description if lr and lr.description else "")

    # Mastery & weak-topic status
    mastery_record = db.execute(
        select(StudentMastery).where(
            StudentMastery.user_id == current_user.id,
            StudentMastery.concept_id == concept_id,
        )
    ).scalar_one_or_none()
    mastery_score = mastery_record.mastery_score if mastery_record else 0.0

    has_wrong = db.execute(
        select(StudentResponse.id)
        .join(Question, StudentResponse.question_id == Question.id)
        .where(
            StudentResponse.user_id == current_user.id,
            Question.concept_id == concept_id,
            StudentResponse.is_correct.is_(False),
        )
    ).first() is not None

    is_weak = (mastery_score < 0.65) or has_wrong

    # Prerequisites (concepts that this concept depends on)
    prereq_rows = db.execute(
        select(Concept, Topic.name)
        .join(ConceptDependency, ConceptDependency.prerequisite_concept_id == Concept.id)
        .outerjoin(Topic, Concept.topic_id == Topic.id)
        .where(ConceptDependency.dependent_concept_id == concept_id)
    ).all()
    prerequisites = [
        {"id": c.id, "name": c.name, "topic": tname or "General", "description": c.description or ""}
        for c, tname in prereq_rows
    ]

    # Dependent next concepts (unlocked by this concept)
    dep_rows = db.execute(
        select(Concept, Topic.name)
        .join(ConceptDependency, ConceptDependency.dependent_concept_id == Concept.id)
        .outerjoin(Topic, Concept.topic_id == Topic.id)
        .where(ConceptDependency.prerequisite_concept_id == concept_id)
    ).all()
    unlocked_concepts = [
        {"id": c.id, "name": c.name, "topic": tname or "General"}
        for c, tname in dep_rows
    ]

    # Illustrative / practice questions
    sample_questions = db.execute(
        select(Question)
        .where(Question.concept_id == concept_id)
        .limit(3)
    ).scalars().all()

    worked_examples = []
    for q in sample_questions:
        opts = q.options_json
        if isinstance(opts, str):
            try:
                opts = json.loads(opts)
            except Exception:
                opts = {}
        worked_examples.append({
            "id": q.id,
            "question_text": q.question_text,
            "options": opts,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "source": q.source,
            "exam_year": q.exam_year,
            "difficulty_hint": q.difficulty_hint,
        })

    # Substantive breakdown of concept description
    key_points = [p.strip() for p in concept_desc.split(",") if p.strip()] if concept_desc else []

    # Curate official authoritative external search references
    c_query = urllib.parse.quote_plus(concept_name)
    t_query = urllib.parse.quote_plus(f"{concept_name} {target_name}")

    ext_refs = [
        {
            "title": f"Wikipedia Overview: {concept_name}",
            "url": f"https://en.wikipedia.org/wiki/Special:Search?search={c_query}",
            "source": "Wikipedia (Open Knowledge)",
            "type": "reference",
        },
        {
            "title": f"Video Lectures: {concept_name}",
            "url": f"https://www.youtube.com/results?search_query={t_query}",
            "source": "YouTube Educational",
            "type": "video",
        },
    ]

    lower_target = target_name.lower()
    if any(k in lower_target for k in ["upsc", "civil", "ssc", "govt"]):
        ext_refs.insert(0, {
            "title": f"NCERT National Repository: {concept_name}",
            "url": "https://ncert.nic.in/textbook.php",
            "source": "NCERT Official",
            "type": "textbook",
        })
        ext_refs.insert(1, {
            "title": f"Vikaspedia Knowledge Portal: {concept_name}",
            "url": f"https://vikaspedia.in/InDGSearch?search_text={c_query}",
            "source": "Govt of India / C-DAC",
            "type": "portal",
        })
    elif any(k in lower_target for k in ["gate", "engineer", "software", "data", "developer", "ml"]):
        ext_refs.insert(0, {
            "title": f"NPTEL Course Portal: {concept_name}",
            "url": "https://nptel.ac.in/courses",
            "source": "NPTEL / IITs",
            "type": "course",
        })
        ext_refs.insert(1, {
            "title": f"GeeksforGeeks Documentation: {concept_name}",
            "url": f"https://www.geeksforgeeks.org/search/?q={c_query}",
            "source": "GeeksforGeeks",
            "type": "article",
        })
    else:
        ext_refs.insert(0, {
            "title": f"National Digital Library of India: {concept_name}",
            "url": "https://ndl.iitkgp.ac.in/",
            "source": "NDLI (MoE)",
            "type": "library",
        })

    title = lr.title if lr and lr.title else f"Core Foundations: {concept_name}"
    raw_url = lr.url if lr else ""
    is_internal = not raw_url or "learn.internal" in raw_url or raw_url.startswith("/")

    return {
        "id": lr.id if lr else resource_id,
        "concept_id": concept_id,
        "title": title,
        "resource_type": lr.resource_type if lr and lr.resource_type else "article",
        "raw_url": raw_url,
        "is_internal": is_internal,
        "external_url": None if is_internal else raw_url,
        "target_id": target_id,
        "target_name": target_name,
        "skill_name": skill_name,
        "topic_name": topic_name,
        "concept_name": concept_name,
        "description": concept_desc,
        "key_points": key_points,
        "duration_min": lr.estimated_duration_min if lr and lr.estimated_duration_min else 30,
        "difficulty": lr.difficulty if lr and lr.difficulty else "Intermediate",
        "provider": lr.provider if lr and lr.provider else "Official Curriculum Guide",
        "license": lr.license if lr and lr.license else "Educational Open Access",
        "attribution": lr.attribution if lr and lr.attribution else f"Curated for {target_name}",
        "is_weak_topic": is_weak,
        "mastery_score": round(mastery_score * 100, 1),
        "prerequisites": prerequisites,
        "unlocked_concepts": unlocked_concepts,
        "worked_examples": worked_examples,
        "external_references": ext_refs,
    }
'''

if '@router.get("/resources/{resource_id}")' not in text:
    target_str = '@router.get("/career-map")'
    text = text.replace(target_str, endpoint_code.strip() + "\n\n\n" + target_str)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("[OK] backend/app/api/learning.py updated successfully!")
