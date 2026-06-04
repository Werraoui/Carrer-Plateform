from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OfferSubmitRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=150)
    raw_text: str = Field(..., min_length=50)
    target_job_id: Optional[int] = None


class OfferSubmitResponse(BaseModel):
    offer_id: int
    skills_extracted: List[str]
    target_job_id: Optional[int] = None
    next_steps: List[str] = ["gap", "ats"]


class OfferSkillItem(BaseModel):
    skill_id: int
    name: str
    importance: float


class UserOfferResponse(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    target_job_id: Optional[int] = None
    source_type: str
    scraped_at: Optional[datetime] = None
    skills: List[OfferSkillItem]


class MarketOfferResponse(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    target_job_id: Optional[int] = None
    scraped_at: Optional[datetime] = None
    skills_extracted: bool = False


class OfferResponse(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    target_job_id: Optional[int] = None
    url: Optional[str] = None
    scraped_at: Optional[datetime] = None
    skills_extracted: bool = False

    class Config:
        from_attributes = True


class OfferSkillsResponse(BaseModel):
    offer_id: int
    skills_count: int
    cached: bool
    skills: List[str]


class OfferSkillsListResponse(BaseModel):
    offer_id: int
    skills: List[OfferSkillItem]
