import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import models as db_models
from app.db.database import get_db
from app.models.offer import (
    OfferResponse,
    OfferSkillItem,
    OfferSkillsListResponse,
    OfferSkillsResponse,
)
from app.routers.auth import get_current_user
from app.services.offer_service import extract_offer_skills, list_offer_skills

log = logging.getLogger("router.offers")
router = APIRouter()


@router.get("", response_model=list[OfferResponse])
def list_offers(
    target_job_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, description="Search in title or company"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Liste les offres importées (catalogue). Ne remplit pas offer_skills."""
    query = db.query(db_models.Offer).order_by(db_models.Offer.scraped_at.desc())
    if target_job_id is not None:
        query = query.filter(db_models.Offer.target_job_id == target_job_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            (db_models.Offer.title.ilike(pattern)) | (db_models.Offer.company.ilike(pattern))
        )

    offers = query.offset(offset).limit(limit).all()
    offer_ids = [o.id for o in offers]
    with_skills: set[int] = set()
    if offer_ids:
        rows = (
            db.query(db_models.OfferSkill.offer_id)
            .filter(db_models.OfferSkill.offer_id.in_(offer_ids))
            .distinct()
            .all()
        )
        with_skills = {r[0] for r in rows}

    return [
        OfferResponse(
            id=o.id,
            title=o.title,
            company=o.company,
            description=o.description,
            target_job_id=o.target_job_id,
            url=o.url,
            scraped_at=o.scraped_at,
            skills_extracted=o.id in with_skills,
        )
        for o in offers
    ]


@router.get("/{offer_id}", response_model=OfferResponse)
def get_offer(offer_id: int, db: Session = Depends(get_db)):
    offer = db.query(db_models.Offer).filter(db_models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    has_skills = (
        db.query(db_models.OfferSkill)
        .filter(db_models.OfferSkill.offer_id == offer_id)
        .first()
        is not None
    )
    return OfferResponse(
        id=offer.id,
        title=offer.title,
        company=offer.company,
        description=offer.description,
        target_job_id=offer.target_job_id,
        url=offer.url,
        scraped_at=offer.scraped_at,
        skills_extracted=has_skills,
    )


@router.get("/{offer_id}/skills", response_model=OfferSkillsListResponse)
def get_offer_skills(offer_id: int, db: Session = Depends(get_db)):
    """Compétences déjà extraites pour cette offre (vide si l'utilisateur n'a pas encore lancé l'extraction)."""
    offer = db.query(db_models.Offer).filter(db_models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    rows = list_offer_skills(db, offer_id)
    return OfferSkillsListResponse(
        offer_id=offer_id,
        skills=[
            OfferSkillItem(skill_id=s["skill_id"], name=s["name"], importance=s["importance"])
            for s in rows
        ],
    )


@router.post("/{offer_id}/skills", response_model=OfferSkillsResponse)
async def extract_skills_for_offer(
    offer_id: int,
    force: bool = Query(False, description="Re-extraire même si des skills existent déjà"),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    L'utilisateur sélectionne une offre : extraction ML de la description → offer_skills.
    """
    _ = current_user
    result = await extract_offer_skills(db, offer_id, force=force)
    return OfferSkillsResponse(**result)
