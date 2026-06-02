"""
Extract and persist skills for a single job offer (user-selected).

`offer_skills` is filled only when the user picks an offer and triggers extraction
(via POST /offers/{id}/skills or POST /gap/analyze with offer_id).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import models as db_models

log = logging.getLogger("offer_service")


async def _extract_skills_via_ml(text: str) -> list[str]:
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


async def extract_offer_skills(
    db: Session,
    offer_id: int,
    *,
    force: bool = False,
) -> dict:
    """
    Run ML on the offer description and upsert offer_skills for this offer only.

    If skills already exist and force=False, returns cached skills without calling ML.
    """
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
        extracted = await _extract_skills_via_ml(description)
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

    db.query(db_models.OfferSkill).filter(
        db_models.OfferSkill.offer_id == offer_id
    ).delete(synchronize_session=False)

    for name in extracted:
        skill = _get_or_create_skill(db, name)
        db.add(
            db_models.OfferSkill(
                offer_id=offer_id,
                skill_id=skill.id,
                importance_score=Decimal("0.5"),
            )
        )

    db.commit()
    log.info("offer_skills: offer_id=%s count=%s", offer_id, len(extracted))

    return {
        "offer_id": offer_id,
        "skills_count": len(extracted),
        "cached": False,
        "skills": extracted,
    }


async def ensure_offer_skills(db: Session, offer_id: int) -> list[dict]:
    """Ensure offer_skills exist; extract on first use."""
    existing = list_offer_skills(db, offer_id)
    if existing:
        return [
            {"name": s["name"], "importance": s["importance"], "frequency": 1.0}
            for s in existing
        ]
    result = await extract_offer_skills(db, offer_id, force=False)
    return [
        {"name": n, "importance": 0.5, "frequency": 1.0}
        for n in result["skills"]
    ]
