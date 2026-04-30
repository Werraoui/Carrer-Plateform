from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CVResponse(BaseModel):
    id: int
    user_id: int
    file_path: str
    uploaded_at: datetime
    skills_extracted: Optional[List[str]] = []

    class Config:
        from_attributes = True


class CVUploadResponse(BaseModel):
    cv_id: int
    message: str
    skills: List[str]
    skill_count: int


class SkillList(BaseModel):
    skills: List[str]


class CVOptimizationRequest(BaseModel):
    cv_id: int
    offer_id: Optional[int] = None
    offer_text: Optional[str] = None


class CVOptimizationResponse(BaseModel):
    cv_id: int
    ats_score: float
    missing_keywords: str  
    suggestions: str
    created_at: datetime

    class Config:
        from_attributes = True