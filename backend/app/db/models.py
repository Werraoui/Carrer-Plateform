from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    level = Column(String(30))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    cvs = relationship("CV", back_populates="user", cascade="all, delete-orphan")
    user_target_jobs = relationship(
        "UserTargetJob", back_populates="user", cascade="all, delete-orphan"
    )
    user_skill_progress = relationship(
        "UserSkillProgress", back_populates="user", cascade="all, delete-orphan"
    )
    offers = relationship("Offer", back_populates="user")


class TargetJob(Base):
    __tablename__ = "target_jobs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    sector = Column(String(100))

    user_target_jobs = relationship(
        "UserTargetJob", back_populates="target_job", cascade="all, delete-orphan"
    )
    job_skills = relationship("JobSkill", back_populates="target_job", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="target_job")


class UserTargetJob(Base):
    __tablename__ = "user_target_jobs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_job_id = Column(
        Integer, ForeignKey("target_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active = Column(Boolean, server_default="true", nullable=False)
    selected_at = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at = Column(DateTime)

    user = relationship("User", back_populates="user_target_jobs")
    target_job = relationship("TargetJob", back_populates="user_target_jobs")

    career_gap_analyses = relationship(
        "CareerGapAnalysis", back_populates="user_target_job", cascade="all, delete-orphan"
    )
    roadmaps = relationship("Roadmap", back_populates="user_target_job", cascade="all, delete-orphan")
    interview_sessions = relationship(
        "InterviewSession", back_populates="user_target_job", cascade="all, delete-orphan"
    )


class CV(Base):
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    extracted_text = Column(Text)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="cvs")
    cv_skills = relationship("CVSkill", back_populates="cv", cascade="all, delete-orphan")
    career_gap_analyses = relationship(
        "CareerGapAnalysis", back_populates="cv", cascade="all, delete-orphan"
    )
    cv_optimizations = relationship(
        "CVOptimization", back_populates="cv", cascade="all, delete-orphan"
    )


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    category = Column(String(100))
    description = Column(Text)

    cv_skills = relationship("CVSkill", back_populates="skill", cascade="all, delete-orphan")
    job_skills = relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")
    offer_skills = relationship("OfferSkill", back_populates="skill", cascade="all, delete-orphan")
    gap_details = relationship("GapDetail", back_populates="skill", cascade="all, delete-orphan")
    roadmap_steps = relationship("RoadmapStep", back_populates="skill")
    user_skill_progress = relationship("UserSkillProgress", back_populates="skill", cascade="all, delete-orphan")
    interview_questions = relationship("InterviewQuestion", back_populates="related_skill")


class CVSkill(Base):
    __tablename__ = "cv_skills"
    __table_args__ = (UniqueConstraint("cv_id", "skill_id", name="uq_cv_skill"),)

    id = Column(Integer, primary_key=True)
    cv_id = Column(Integer, ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence_score = Column(Numeric(4, 3))

    cv = relationship("CV", back_populates="cv_skills")
    skill = relationship("Skill", back_populates="cv_skills")


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("target_job_id", "skill_id", name="uq_job_skill"),)

    id = Column(Integer, primary_key=True)
    target_job_id = Column(
        Integer, ForeignKey("target_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    frequency = Column(Numeric(5, 2))
    importance_score = Column(Numeric(4, 3))

    target_job = relationship("TargetJob", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("url", name="offers_url_key"),
        CheckConstraint("source_type IN ('scraped', 'user_pasted')", name="ck_offers_source_type"),
    )

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    company = Column(String(150))
    description = Column(Text)
    offer_source = Column(String(100))
    source_type = Column(String(20), nullable=False, server_default="scraped")
    raw_text = Column(Text)
    target_job_id = Column(Integer, ForeignKey("target_jobs.id", ondelete="SET NULL"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    url = Column(Text, unique=True)
    scraped_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="offers")
    target_job = relationship("TargetJob", back_populates="offers")
    offer_skills = relationship("OfferSkill", back_populates="offer", cascade="all, delete-orphan")

    career_gap_analyses = relationship("CareerGapAnalysis", back_populates="offer")
    interview_sessions = relationship("InterviewSession", back_populates="offer")
    cv_optimizations = relationship("CVOptimization", back_populates="offer")


class OfferSkill(Base):
    __tablename__ = "offer_skills"
    __table_args__ = (UniqueConstraint("offer_id", "skill_id", name="uq_offer_skill"),)

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    importance_score = Column(Numeric(4, 3))

    offer = relationship("Offer", back_populates="offer_skills")
    skill = relationship("Skill", back_populates="offer_skills")


class CareerGapAnalysis(Base):
    __tablename__ = "career_gap_analyses"

    id = Column(Integer, primary_key=True)
    user_target_job_id = Column(
        Integer, ForeignKey("user_target_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cv_id = Column(Integer, ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id", ondelete="SET NULL"), index=True)
    employability_score = Column(Numeric(5, 2))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user_target_job = relationship("UserTargetJob", back_populates="career_gap_analyses")
    cv = relationship("CV", back_populates="career_gap_analyses")
    offer = relationship("Offer", back_populates="career_gap_analyses")

    gap_details = relationship("GapDetail", back_populates="career_gap", cascade="all, delete-orphan")
    roadmaps = relationship("Roadmap", back_populates="career_gap", cascade="all, delete-orphan")


class GapDetail(Base):
    __tablename__ = "gap_details"
    __table_args__ = (
        CheckConstraint("status IN ('missing', 'partial', 'acquired')", name="ck_gap_details_status"),
    )

    id = Column(Integer, primary_key=True)
    career_gap_id = Column(
        Integer, ForeignKey("career_gap_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20))
    weight = Column(Numeric(4, 3))

    career_gap = relationship("CareerGapAnalysis", back_populates="gap_details")
    skill = relationship("Skill", back_populates="gap_details")


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True)
    user_target_job_id = Column(
        Integer, ForeignKey("user_target_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    career_gap_id = Column(
        Integer, ForeignKey("career_gap_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    duration_weeks = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user_target_job = relationship("UserTargetJob", back_populates="roadmaps")
    career_gap = relationship("CareerGapAnalysis", back_populates="roadmaps")
    steps = relationship("RoadmapStep", back_populates="roadmap", cascade="all, delete-orphan")


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    id = Column(Integer, primary_key=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), index=True)
    week_number = Column(Integer)
    title = Column(String(200))
    type = Column(String(50))
    resource_link = Column(Text)

    roadmap = relationship("Roadmap", back_populates="steps")
    skill = relationship("Skill", back_populates="roadmap_steps")

    user_skill_progress = relationship("UserSkillProgress", back_populates="roadmap_step")


class UserSkillProgress(Base):
    __tablename__ = "user_skill_progress"
    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')", name="ck_user_skill_progress_status"
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_step_id = Column(Integer, ForeignKey("roadmap_steps.id", ondelete="SET NULL"), index=True)
    status = Column(String(30))
    completion_date = Column(Date)

    user = relationship("User", back_populates="user_skill_progress")
    skill = relationship("Skill", back_populates="user_skill_progress")
    roadmap_step = relationship("RoadmapStep", back_populates="user_skill_progress")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True)
    user_target_job_id = Column(
        Integer, ForeignKey("user_target_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    offer_id = Column(Integer, ForeignKey("offers.id", ondelete="SET NULL"), index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user_target_job = relationship("UserTargetJob", back_populates="interview_sessions")
    offer = relationship("Offer", back_populates="interview_sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text = Column(Text)
    related_skill_id = Column(Integer, ForeignKey("skills.id"), index=True)

    session = relationship("InterviewSession", back_populates="questions")
    related_skill = relationship("Skill", back_populates="interview_questions")


class CVOptimization(Base):
    __tablename__ = "cv_optimizations"

    id = Column(Integer, primary_key=True)
    cv_id = Column(Integer, ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id", ondelete="SET NULL"), index=True)
    ats_score = Column(Numeric(5, 2))
    missing_keywords = Column(Text)
    suggestions = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    cv = relationship("CV", back_populates="cv_optimizations")
    offer = relationship("Offer", back_populates="cv_optimizations")