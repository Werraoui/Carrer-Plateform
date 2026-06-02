import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import models as db_models
from app.db.database import get_db
from app.models.offer import (
    MarketOfferResponse,
    OfferResponse,
    OfferSkillItem,
    OfferSkillsListResponse,
    OfferSkillsResponse,
    OfferSubmitRequest,
    OfferSubmitResponse,
    UserOfferResponse,
)
from app.routers.auth import get_current_user
from app.services.offer_service import (
    extract_offer_skills,
    list_offer_skills,
    submit_user_pasted_offer,
)

log = logging.getLogger("router.offers")
router = APIRouter()


@router.post("/submit", response_model=OfferSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_offer(
    body: OfferSubmitRequest,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Coller une offre (LinkedIn, Indeed, etc.) : crée l'offre, extrait les skills,
    point d'entrée du pipeline gap → ATS.
    """
    result = await submit_user_pasted_offer(
        db,
        current_user.id,
        title=body.title,
        company=body.company,
        raw_text=body.raw_text,
        target_job_id=body.target_job_id,
    )
    return OfferSubmitResponse(**result)


@router.get("/", response_model=List[UserOfferResponse])
def list_user_offers(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Offres collées par l'utilisateur connecté, avec leurs compétences."""
    offers = (
        db.query(db_models.Offer)
        .filter(
            db_models.Offer.user_id == current_user.id,
            db_models.Offer.source_type == "user_pasted",
        )
        .order_by(db_models.Offer.scraped_at.desc())
        .all()
    )

    result: List[UserOfferResponse] = []
    for offer in offers:
        skills = list_offer_skills(db, offer.id)
        result.append(
            UserOfferResponse(
                id=offer.id,
                title=offer.title,
                company=offer.company,
                target_job_id=offer.target_job_id,
                source_type=offer.source_type,
                scraped_at=offer.scraped_at,
                skills=[
                    OfferSkillItem(
                        skill_id=s["skill_id"],
                        name=s["name"],
                        importance=s["importance"],
                    )
                    for s in skills
                ],
            )
        )
    return result


@router.get("/market/{target_job_id}", response_model=List[MarketOfferResponse])
def list_market_offers(
    target_job_id: int,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """20 offres scrapées les plus récentes pour un métier cible."""
    tj = db.query(db_models.TargetJob).filter(db_models.TargetJob.id == target_job_id).first()
    if not tj:
        raise HTTPException(status_code=404, detail="Métier cible introuvable")

    offers = (
        db.query(db_models.Offer)
        .filter(
            db_models.Offer.source_type == "scraped",
            db_models.Offer.target_job_id == target_job_id,
        )
        .order_by(db_models.Offer.scraped_at.desc())
        .limit(limit)
        .all()
    )

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
        MarketOfferResponse(
            id=o.id,
            title=o.title,
            company=o.company,
            target_job_id=o.target_job_id,
            scraped_at=o.scraped_at,
            skills_extracted=o.id in with_skills,
        )
        for o in offers
    ]


@router.get("/{offer_id}", response_model=OfferResponse)
def get_offer(
    offer_id: int,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offer = db.query(db_models.Offer).filter(db_models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offer.source_type == "user_pasted" and offer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à cette offre")

    has_skills = bool(list_offer_skills(db, offer_id))
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
def get_offer_skills(
    offer_id: int,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offer = db.query(db_models.Offer).filter(db_models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offer.source_type == "user_pasted" and offer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à cette offre")

    rows = list_offer_skills(db, offer_id)
    return OfferSkillsListResponse(
        offer_id=offer_id,
        skills=[
            OfferSkillItem(skill_id=s["skill_id"], name=s["name"], importance=s["importance"])
            for s in rows
        ],
    )


@router.post("/{offer_id}/skills", response_model=OfferSkillsResponse)
async def reextract_offer_skills(
    offer_id: int,
    force: bool = Query(True),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offer = db.query(db_models.Offer).filter(db_models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offer.source_type == "user_pasted" and offer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à cette offre")

    result = await extract_offer_skills(db, offer_id, force=force)
    return OfferSkillsResponse(**result)
