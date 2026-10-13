from __future__ import annotations
import datetime as dt
from typing import Any
from sqlalchemy import (
    ForeignKey, String, Float, Integer, Boolean, Text,
    DateTime, Date, CheckConstraint, UniqueConstraint, Index, func, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType
    class Vector(UserDefinedType):
        def __init__(self, dim: int = 384):
            self.dim = dim
        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

from backend.app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="learner")  # learner, reviewer, admin
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped[LearnerProfile | None] = relationship("LearnerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    responses: Mapped[list[StudentResponse]] = relationship("StudentResponse", back_populates="user", cascade="all, delete-orphan")
    mastery_scores: Mapped[list[StudentMastery]] = relationship("StudentMastery", back_populates="user", cascade="all, delete-orphan")


class CareerTarget(Base):
    __tablename__ = "career_targets"
    __table_args__ = (
        CheckConstraint("category IN ('it_career', 'govt_exam')", name="category_enum"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30), index=True)  # it_career or govt_exam
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    readiness_threshold: Mapped[float] = mapped_column(Float, default=0.70)

    skills: Mapped[list[Skill]] = relationship("Skill", back_populates="target", cascade="all, delete-orphan")


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    target_type: Mapped[str] = mapped_column(String(30))  # it_career or govt_exam
    target_id: Mapped[int] = mapped_column(ForeignKey("career_targets.id"), index=True)
    current_level: Mapped[str] = mapped_column(String(20), default="intermediate")  # beginner, intermediate, advanced
    study_hours_per_day: Mapped[float] = mapped_column(Float, default=2.0)
    preferred_schedule: Mapped[str] = mapped_column(String(50), default="evening")
    exam_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    trial_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship("User", back_populates="profile")
    target: Mapped[CareerTarget] = relationship("CareerTarget")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("career_targets.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    weight: Mapped[float] = mapped_column(Float)  # sum to 1.0 per target

    target: Mapped[CareerTarget] = relationship("CareerTarget", back_populates="skills")
    topics: Mapped[list[Topic]] = relationship("Topic", back_populates="skill", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")

    skill: Mapped[Skill] = relationship("Skill", back_populates="topics")
    concepts: Mapped[list[Concept]] = relationship("Concept", back_populates="topic", cascade="all, delete-orphan")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    mastery_threshold: Mapped[float] = mapped_column(Float, default=0.70)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)

    topic: Mapped[Topic] = relationship("Topic", back_populates="concepts")
    questions: Mapped[list[Question]] = relationship("Question", back_populates="concept")
    resources: Mapped[list[LearningResource]] = relationship("LearningResource", back_populates="concept")


class ConceptDependency(Base):
    __tablename__ = "concept_dependencies"
    __table_args__ = (
        CheckConstraint("prerequisite_concept_id <> dependent_concept_id", name="no_self_edge"),
        UniqueConstraint("prerequisite_concept_id", "dependent_concept_id", name="uniq_edge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    prerequisite_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    dependent_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    relation_weight: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(20), default="expert")  # expert, imported

    prerequisite_id = synonym("prerequisite_concept_id")
    concept_id = synonym("dependent_concept_id")
    strength = synonym("relation_weight")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("source IN ('curated','ai_generated','imported','gemini')", name="src_enum"),
        CheckConstraint("review_status IN ('pending','approved','rejected','generated')", name="rev_enum"),
        CheckConstraint("source IN ('curated','gemini') OR review_status IN ('approved','generated')", name="scorable_items_must_be_reviewed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    options_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(10))
    explanation: Mapped[str] = mapped_column(Text, default="")
    difficulty_hint: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20), default="curated")
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending by default, approved after human review
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exam_year: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)

    def __init__(self, **kwargs: Any):
        if "options" in kwargs and "options_json" not in kwargs:
            kwargs["options_json"] = kwargs.pop("options")
        if "difficulty_b" in kwargs and "difficulty_hint" not in kwargs:
            kwargs["difficulty_hint"] = kwargs.pop("difficulty_b")
        if "difficulty" in kwargs and "difficulty_hint" not in kwargs:
            kwargs["difficulty_hint"] = kwargs.pop("difficulty")
        if "stem" in kwargs and "question_text" not in kwargs:
            kwargs["question_text"] = kwargs.pop("stem")
        if "correct_option" in kwargs and "correct_answer" not in kwargs:
            kwargs["correct_answer"] = kwargs.pop("correct_option")
        if "status" in kwargs and "review_status" not in kwargs:
            kwargs["review_status"] = kwargs.pop("status")
        super().__init__(**kwargs)

    @property
    def options(self) -> dict[str, Any]:
        return self.options_json

    @options.setter
    def options(self, val: dict[str, Any]) -> None:
        self.options_json = val

    @property
    def difficulty_b(self) -> float:
        return self.difficulty_hint

    @difficulty_b.setter
    def difficulty_b(self, val: float) -> None:
        self.difficulty_hint = val

    @property
    def difficulty(self) -> float:
        return self.difficulty_hint

    @difficulty.setter
    def difficulty(self, val: float) -> None:
        self.difficulty_hint = val

    @property
    def stem(self) -> str:
        return self.question_text

    @stem.setter
    def stem(self, val: str) -> None:
        self.question_text = val

    @property
    def correct_option(self) -> str:
        return self.correct_answer

    @correct_option.setter
    def correct_option(self, val: str) -> None:
        self.correct_answer = val

    @property
    def status(self) -> str:
        return self.review_status

    @status.setter
    def status(self, val: str) -> None:
        self.review_status = val

    @property
    def topic_id(self) -> int | None:
        return self.concept.topic_id if self.concept else None

    @property
    def skill_id(self) -> int | None:
        return self.concept.topic.skill_id if self.concept and self.concept.topic else None

    concept: Mapped[Concept] = relationship("Concept", back_populates="questions")
    irt_params: Mapped[list[QuestionIrtParam]] = relationship("QuestionIrtParam", back_populates="question")
    sub_questions: Mapped[list[SubQuestion]] = relationship(
        "SubQuestion", back_populates="parent_question", cascade="all, delete-orphan", order_by="SubQuestion.order"
    )


class SubQuestion(Base):
    __tablename__ = "sub_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(50))  # formula | substitution | calculation | concept_recall | elimination | final_answer
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(10))
    time_limit_sec: Mapped[int] = mapped_column(Integer, default=20)
    order: Mapped[int] = mapped_column(Integer, default=1)

    parent_question: Mapped[Question] = relationship("Question", back_populates="sub_questions")

    def __init__(self, **kwargs: Any):
        if "options" in kwargs and "options_json" not in kwargs:
            kwargs["options_json"] = kwargs.pop("options")
        if "correct_option" in kwargs and "correct_answer" not in kwargs:
            kwargs["correct_answer"] = kwargs.pop("correct_option")
        super().__init__(**kwargs)

    @property
    def options(self) -> dict[str, Any]:
        return self.options_json

    @options.setter
    def options(self, val: dict[str, Any]) -> None:
        self.options_json = val

    @property
    def correct_option(self) -> str:
        return self.correct_answer

    @correct_option.setter
    def correct_option(self, val: str) -> None:
        self.correct_answer = val


class QuestionIrtParam(Base):
    __tablename__ = "question_irt_params"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    calibration_run_id: Mapped[int | None] = mapped_column(ForeignKey("calibration_runs.id"), nullable=True)
    a: Mapped[float] = mapped_column(Float, default=1.0)  # discrimination
    b: Mapped[float] = mapped_column(Float, default=0.0)  # difficulty
    n_responses: Mapped[int] = mapped_column(Integer, default=0)
    fitted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question: Mapped[Question] = relationship("Question", back_populates="irt_params")


class CalibrationRun(Base):
    __tablename__ = "calibration_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_date: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sample_size: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(20), default="2PL")  # 1PL, 2PL
    convergence_metric: Mapped[float | None] = mapped_column(Float, nullable=True)


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint("type IN ('initial','verification','practice','followup','probe','special','weekly_test')", name="assessment_type_enum"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(30))  # initial, verification, practice, followup, probe, special
    target_id: Mapped[int] = mapped_column(ForeignKey("career_targets.id"), index=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    questions: Mapped[list[AssessmentQuestion]] = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    responses: Mapped[list[StudentResponse]] = relationship("StudentResponse", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'main' or 'sub' for special mode
    block_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    assessment: Mapped[Assessment] = relationship("Assessment", back_populates="questions")
    question: Mapped[Question] = relationship("Question")


class StudentResponse(Base):
    __tablename__ = "student_responses"
    __table_args__ = (
        CheckConstraint("response_time_ms BETWEEN 0 AND 3600000", name="sane_time"),
        CheckConstraint("attempt_no BETWEEN 1 AND 20", name="sane_attempt"),
        CheckConstraint("NOT skipped OR selected_answer IS NULL", name="skip_has_no_answer"),
        Index("idx_responses_user_time", "user_id", "answered_at"),
        Index("idx_responses_concept", "question_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    selected_answer: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    response_time_ms: Mapped[int] = mapped_column(Integer)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    answered_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Special Test Mode extensions
    phase: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'main' or 'sub'
    parent_response_id: Mapped[int | None] = mapped_column(ForeignKey("student_responses.id", ondelete="SET NULL"), nullable=True)
    time_limit_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)

    assessment: Mapped[Assessment] = relationship("Assessment", back_populates="responses")
    question: Mapped[Question] = relationship("Question")
    user: Mapped[User] = relationship("User", back_populates="responses")

    @property
    def concept_id(self) -> int | None:
        return self.question.concept_id if self.question else None

    @property
    def topic_id(self) -> int | None:
        return self.question.concept.topic_id if self.question and self.question.concept else None


class VerificationProbe(Base):
    __tablename__ = "verification_probes"
    __table_args__ = (
        CheckConstraint("trigger IN ('model_flag','epsilon_random')", name="trigger_enum"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[str] = mapped_column(String(20))  # model_flag or epsilon_random
    suspected_mastery: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)  # confirmed_gap, rejected_gap
    items_served: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InterventionAssignment(Base):
    __tablename__ = "intervention_assignments"
    __table_args__ = (
        CheckConstraint("arm IN ('root_cause','surface')", name="arm_enum"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    surface_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"))
    arm: Mapped[str] = mapped_column(String(20))  # root_cause or surface
    assigned_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"))
    pre_score: Mapped[float] = mapped_column(Float)
    post_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    minutes_planned: Mapped[int] = mapped_column(Integer)
    minutes_actual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentMastery(Base):
    __tablename__ = "student_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uniq_learner_concept"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    mastery_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    model_version: Mapped[str] = mapped_column(String(80))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship("User", back_populates="mastery_scores")
    concept: Mapped[Concept] = relationship("Concept")


class MasteryHistory(Base):
    __tablename__ = "mastery_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    mastery_score: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_version: Mapped[str] = mapped_column(String(80))


class TopicPerformance(Base):
    __tablename__ = "topic_performance"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    accuracy: Mapped[float] = mapped_column(Float)
    avg_time_ms: Mapped[int] = mapped_column(Integer)
    skip_rate: Mapped[float] = mapped_column(Float)
    gap_score: Mapped[float] = mapped_column(Float)
    band: Mapped[str] = mapped_column(String(20))  # strong, moderate, weak
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RootCauseAnalysis(Base):
    __tablename__ = "root_cause_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    current_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    candidate_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    root_score: Mapped[float] = mapped_column(Float)  # R(c,h)
    attention_alpha: Mapped[float] = mapped_column(Float)
    attention_entropy: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    resource_type: Mapped[str] = mapped_column(String(50))  # article, video, doc, interactive
    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0)
    provider: Mapped[str] = mapped_column(String(150), default="")
    estimated_duration_min: Mapped[int] = mapped_column(Integer, default=30)
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate")
    attribution: Mapped[str] = mapped_column(Text, default="")
    license: Mapped[str] = mapped_column(String(100), default="")

    concept: Mapped[Concept] = relationship("Concept", back_populates="resources")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("learning_resources.id", ondelete="CASCADE"), index=True)
    similarity: Mapped[float] = mapped_column(Float)
    priority: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearningSchedule(Base):
    __tablename__ = "learning_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    activity_type: Mapped[str] = mapped_column(String(50))  # review, practice, test, weekly_test
    scheduled_date: Mapped[dt.date] = mapped_column(Date)
    duration_min: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, completed, skipped
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Adaptive plan extensions
    subject: Mapped[str | None] = mapped_column(String(150), nullable=True)
    topic_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    learning_objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    practice_activity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mastery_target: Mapped[float] = mapped_column(Float, default=0.80)
    follow_up_assessment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class LearningActivity(Base):
    __tablename__ = "learning_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    activity_type: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class AiInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    prompt_type: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(40))
    prompt_text: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(80))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    model_name: Mapped[str] = mapped_column(String(80))
    dataset_version: Mapped[str] = mapped_column(String(80))
    commit_sha: Mapped[str] = mapped_column(String(40))
    hyperparams_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    prediction_type: Mapped[str] = mapped_column(String(50))  # next_item_correctness, mastery
    predicted_value: Mapped[float] = mapped_column(Float)
    probability: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(ForeignKey("model_runs.version"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
