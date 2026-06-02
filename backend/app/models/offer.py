from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


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


class OfferSkillItem(BaseModel):
    skill_id: int
    name: str
    importance: float


class OfferSkillsResponse(BaseModel):
    offer_id: int
    skills_count: int
    cached: bool
    skills: List[str]


class OfferSkillsListResponse(BaseModel):
    offer_id: int
    skills: List[OfferSkillItem]
