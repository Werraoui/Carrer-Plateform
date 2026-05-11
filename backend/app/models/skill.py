from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime




class SkillBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class SkillResponse(SkillBase):
    id: int

    class Config:
        from_attributes = True




class GapAnalysisRequest(BaseModel):
    cv_id: int
    target_job_id: Optional[int] = None
    offer_id: Optional[int] = None


class GapSkillDetail(BaseModel):
    skill_name: str
    status: str  
    weight: float


class GapResult(BaseModel):
    career_gap_id: int
    employability_score: float
    acquired_skills: List[str]
    missing_skills: List[str]
    gap_details: List[GapSkillDetail]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Roadmap Schemas ──────────────────────────────────────────────────────────

class RoadmapRequest(BaseModel):
    career_gap_id: int
    duration_weeks: Optional[int] = 8


class RoadmapStepResponse(BaseModel):
    week_number: Optional[int] = None
    title: Optional[str] = None
    skill_name: Optional[str]
    type: str  # "course", "project", "reading"
    resource_link: Optional[str]

    class Config:
        from_attributes = True


class RoadmapResponse(BaseModel):
    roadmap_id: int
    duration_weeks: int
    steps: List[RoadmapStepResponse]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Interview Schemas ────────────────────────────────────────────────────────

class InterviewRequest(BaseModel):
    user_target_job_id: int
    offer_id: Optional[int] = None
    num_questions: Optional[int] = 5


class InterviewQuestion(BaseModel):
    question_text: str
    related_skill: Optional[str]


class InterviewSessionResponse(BaseModel):
    session_id: int
    questions: List[InterviewQuestion]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Target Job Schemas ───────────────────────────────────────────────────────

class TargetJobResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    sector: Optional[str]

    class Config:
        from_attributes = True


class UserTargetJobRequest(BaseModel):
    target_job_id: int


class UserTargetJobResponse(BaseModel):
    id: int
    user_id: int
    target_job_id: int
    is_active: bool
    target_job: Optional[TargetJobResponse]

    class Config:
        from_attributes = True