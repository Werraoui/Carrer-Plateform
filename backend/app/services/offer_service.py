"""
Offer skills extraction and user-pasted offer submission.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import models as db_models

log = logging.getLogger("offer_service")

USER_PASTED_IMPORTANCE = Decimal("0.8")
DEFAULT_IMPORTANCE = Decimal("0.5")


async def extract_skills_from_text(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.ML_SERVICE_URL}/extract-skills",
            json={"text": text},
        )
        resp.raise_for_status()
        data = resp.json()
    seen: set[str] = set()
    out: list[str] = []
    for s in data.get("skills", []):
        key = (s or "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _get_or_create_skill(db: Session, name: str) -> db_models.Skill:
    key = name.lower().strip()
    skill = db.query(db_models.Skill).filter(db_models.Skill.name == key).first()
    if skill:
        return skill
    skill = db_models.Skill(name=key)
    db.add(skill)
    db.flush()
    return skill


def _resolve_target_job_id_for_user(
    db: Session,
    user_id: int,
    target_job_id: Optional[int],
) -> Optional[int]:
    if target_job_id is not None:
        tj = db.query(db_models.TargetJob).filter(db_models.TargetJob.id == target_job_id).first()
        if not tj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Métier cible id={target_job_id} introuvable",
            )
        return tj.id

    utj = (
        db.query(db_models.UserTargetJob)
        .filter(
            db_models.UserTargetJob.user_id == user_id,
            db_models.UserTargetJob.is_active == True,
        )
        .order_by(db_models.UserTargetJob.selected_at.desc())
        .first()
    )
    if utj:
        return utj.target_job_id
    return None


def save_offer_skills(
    db: Session,
    offer_id: int,
    skill_names: list[str],
    *,
    importance: Decimal = DEFAULT_IMPORTANCE,
    replace: bool = True,
) -> int:
    if replace:
        db.query(db_models.OfferSkill).filter(
            db_models.OfferSkill.offer_id == offer_id
        ).delete(synchronize_session=False)

    n = 0
    for name in skill_names:
        skill = _get_or_create_skill(db, name)
        db.add(
            db_models.OfferSkill(
                offer_id=offer_id,
                skill_id=skill.id,
                importance_score=importance,
            )
        )
        n += 1
    return n


def list_offer_skills(db: Session, offer_id: int) -> list[dict]:
    rows = (
        db.query(db_models.OfferSkill, db_models.Skill)
        .join(db_models.Skill, db_models.OfferSkill.skill_id == db_models.Skill.id)
        .filter(db_models.OfferSkill.offer_id == offer_id)
        .all()
    )
    return [
        {
            "skill_id": skill.id,
            "name": skill.name,
            "importance": float(os_.importance_score or 0.5),
        }
        for os_, skill in rows
    ]


async def submit_user_pasted_offer(
    db: Session,
    user_id: int,
    *,
    title: str,
    company: str,
    raw_text: str,
    target_job_id: Optional[int] = None,
) -> dict:
    """
    Create a user-pasted offer, extract skills via ML, persist offer_skills.
    """
    text = raw_text.strip()
    if len(text) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le texte de l'offre doit contenir au moins 50 caractères.",
        )

    resolved_job_id = _resolve_target_job_id_for_user(db, user_id, target_job_id)

    try:
        extracted = await extract_skills_from_text(text)
    except Exception as e:
        log.error("ML extract-skills failed on submit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service ML indisponible pour extraire les compétences.",
        ) from e

    if not extracted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucune compétence extraite de cette offre.",
        )

    offer = db_models.Offer(
        title=title.strip(),
        company=company.strip(),
        description=text,
        raw_text=text,
        offer_source="user_submit",
        source_type="user_pasted",
        target_job_id=resolved_job_id,
        user_id=user_id,
        url=f"user-pasted://{uuid.uuid4()}",
    )
    db.add(offer)
    db.flush()

    save_offer_skills(
        db,
        offer.id,
        extracted,
        importance=USER_PASTED_IMPORTANCE,
        replace=False,
    )
    db.commit()
    db.refresh(offer)

    log.info(
        "user_pasted offer id=%s user=%s skills=%s",
        offer.id,
        user_id,
        len(extracted),
    )

    return {
        "offer_id": offer.id,
        "skills_extracted": extracted,
        "target_job_id": offer.target_job_id,
        "next_steps": ["gap", "ats"],
    }


async def extract_offer_skills(
    db: Session,
    offer_id: int,
    *,
    force: bool = False,
) -> dict:
    offer = db.query(db_models.Offer).filter(db_models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre introuvable")

    existing = list_offer_skills(db, offer_id)
    if existing and not force:
        return {
            "offer_id": offer_id,
            "skills_count": len(existing),
            "cached": True,
            "skills": [s["name"] for s in existing],
        }

    description = (offer.description or offer.raw_text or "").strip()
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette offre n'a pas de description à analyser.",
        )

    try:
        extracted = await extract_skills_from_text(description)
    except Exception as e:
        log.error("ML extract-skills failed for offer %s: %s", offer_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service ML indisponible pour extraire les compétences.",
        ) from e

    if not extracted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucune compétence extraite de cette offre.",
        )

    importance = (
        USER_PASTED_IMPORTANCE
        if offer.source_type == "user_pasted"
        else DEFAULT_IMPORTANCE
    )
    save_offer_skills(db, offer_id, extracted, importance=importance, replace=True)
    db.commit()

    return {
        "offer_id": offer_id,
        "skills_count": len(extracted),
        "cached": False,
        "skills": extracted,
    }


async def ensure_offer_skills(db: Session, offer_id: int) -> list[dict]:
    existing = list_offer_skills(db, offer_id)
    if existing:
        return [
            {"name": s["name"], "importance": s["importance"], "frequency": 1.0}
            for s in existing
        ]
    result = await extract_offer_skills(db, offer_id, force=False)
    return [
        {"name": n, "importance": 0.8, "frequency": 1.0}
        for n in result["skills"]
    ]
