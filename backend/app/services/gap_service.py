import logging
import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional

from app.db import models as db_models

log = logging.getLogger("gap_service")
from app.models.skill import GapResult, GapSkillDetail
from app.config import settings


async def _get_cv_skills(cv: db_models.CV, db: Session) -> list[str]:
    """Retourne les skills du CV depuis la BDD."""
    cv_skills = db.query(db_models.CVSkill, db_models.Skill).join(
        db_models.Skill, db_models.CVSkill.skill_id == db_models.Skill.id
    ).filter(db_models.CVSkill.cv_id == cv.id).all()
    return [skill.name for _, skill in cv_skills]


def _persist_cv_skills(db: Session, cv: db_models.CV, skill_names: list[str]) -> None:
    """Enregistre les skills extraits par le ML sur le CV."""
    for name in skill_names:
        name_clean = name.lower().strip()
        if not name_clean:
            continue

        skill = db.query(db_models.Skill).filter(
            db_models.Skill.name == name_clean
        ).first()
        if not skill:
            skill = db_models.Skill(name=name_clean)
            db.add(skill)
            db.flush()

        exists = db.query(db_models.CVSkill).filter(
            db_models.CVSkill.cv_id == cv.id,
            db_models.CVSkill.skill_id == skill.id,
        ).first()
        if not exists:
            db.add(db_models.CVSkill(cv_id=cv.id, skill_id=skill.id))


async def _get_market_skills(target_job_id: int, db: Session) -> list[dict]:
    """
    Retourne les skills du marché pour un poste cible
    (agrégat des job_skills + offer_skills).
    """
    job_skills = db.query(db_models.JobSkill, db_models.Skill).join(
        db_models.Skill, db_models.JobSkill.skill_id == db_models.Skill.id
    ).filter(db_models.JobSkill.target_job_id == target_job_id).all()

    return [
        {
            "name": skill.name,
            "importance": float(js.importance_score or 0.5),
            "frequency": float(js.frequency or 1.0),
        }
        for js, skill in job_skills
    ]


async def _get_offer_skills(offer_id: int, db: Session) -> list[dict]:
    """Retourne les skills d'une offre spécifique."""
    offer_skills = db.query(db_models.OfferSkill, db_models.Skill).join(
        db_models.Skill, db_models.OfferSkill.skill_id == db_models.Skill.id
    ).filter(db_models.OfferSkill.offer_id == offer_id).all()

    return [
        {
            "name": skill.name,
            "importance": float(os_.importance_score or 0.5),
            "frequency": 1.0,
        }
        for os_, skill in offer_skills
    ]


def _local_fallback(
    cv_skills: list[str],
    market_skills: list[dict],
    cv_text: str = "",
) -> dict:
    """
    Calcul local quand le ML service est indisponible.
    Scanne aussi le texte du CV pour les noms de skills du marché.
    """
    import re

    market_names = [s["name"] for s in market_skills]

    cv_set = set(s.lower().strip() for s in cv_skills if s)
    if cv_text:
        text_lower = cv_text.lower()
        for name in market_names:
            if re.search(r"\b" + re.escape(name) + r"\b", text_lower):
                cv_set.add(name)

    market_set = set(market_names)

    acquired = list(cv_set & market_set)
    missing  = list(market_set - cv_set)

    match_percentage = round(
        (len(acquired) / len(market_set)) * 100, 2
    ) if market_set else 0.0

    # scorer.py: {skill: weight} dict
    job_skills_weighted = {s["name"]: s["importance"] for s in market_skills}
    total_weight = sum(job_skills_weighted.values())
    score = sum(
        job_skills_weighted[skill]
        for skill in cv_skills
        if skill in job_skills_weighted
    )
    employability_score = round(
        (score / total_weight) * 100, 2
    ) if total_weight > 0 else 0.0

    return {
        "gap": {
            "acquired":         acquired,
            "missing":          missing,
            "match_percentage": match_percentage,
        },
        "score": employability_score,
    }


async def compute_and_save_gap(
    db: Session,
    cv: db_models.CV,
    user_target_job: db_models.UserTargetJob,
    offer_id: Optional[int] = None,
) -> GapResult:
    """
    Orchestre le calcul du career gap :
    1. Récupère les skills du CV depuis la BDD
    2. Récupère les skills du marché ou de l'offre depuis la BDD
    3. Appelle POST /calculate-gap sur le ML micro-service (M1)
       → fallback local si le service est indisponible
    4. Sauvegarde CareerGapAnalysis + GapDetail en BDD
    5. Retourne GapResult
    """
    # ── 1. Skills du CV ───────────────────────────────────────────────────────
    cv_skills = await _get_cv_skills(cv, db)

    # ── 2. Skills cibles ──────────────────────────────────────────────────────
    if offer_id:
        market_skills = await _get_offer_skills(offer_id, db)
    else:
        market_skills = await _get_market_skills(user_target_job.target_job_id, db)

    if not market_skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun skill de référence trouvé pour ce poste. Lancez d'abord le scraping.",
        )

    market_names = [s["name"] for s in market_skills]
    job_weights = {s["name"]: s["importance"] for s in market_skills}

    cv_text = (cv.extracted_text or "").strip()
    if not cv_text and cv_skills:
        cv_text = " ".join(cv_skills)
    if not cv_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le CV n'a pas de texte extrait. Réuploadez le CV.",
        )

    # ── 3. Appel ML service — CV parser (model-best) sur le texte complet du CV ─
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ML_SERVICE_URL}/calculate-gap",
                json={
                    "cv_text": cv_text,
                    "market_skills": market_names,
                    "job_weights": job_weights,
                },
            )
            response.raise_for_status()
            gap_data = response.json()

        ml_cv_skills = gap_data.get("cv_skills") or []
        extraction_source = gap_data.get("extraction_source", "?")
        log.info(
            "Gap ML — source=%s | cv_skills=%s | acquired=%s",
            extraction_source,
            ml_cv_skills,
            gap_data.get("gap", {}).get("acquired"),
        )
        if ml_cv_skills:
            _persist_cv_skills(db, cv, ml_cv_skills)
            cv_skills = ml_cv_skills

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        log.warning("ML service indisponible pour gap : %s", e)
        gap_data = _local_fallback(cv_skills, market_skills, cv_text=cv_text)

    acquired = gap_data["gap"]["acquired"]
    missing  = gap_data["gap"]["missing"]
    employability_score = gap_data["score"]

    # ── 4. Sauvegarde CareerGapAnalysis ───────────────────────────────────────
    analysis = db_models.CareerGapAnalysis(
        user_target_job_id=user_target_job.id,
        cv_id=cv.id,
        offer_id=offer_id,
        employability_score=employability_score,
    )
    db.add(analysis)
    db.flush()  # obtenir analysis.id avant d'insérer les GapDetail

    # ── 5. Sauvegarde GapDetail (un par skill) ────────────────────────────────
    for skill_name in set(acquired + missing):
        # Créer le skill s'il n'existe pas encore
        skill = db.query(db_models.Skill).filter(
            db_models.Skill.name == skill_name.lower()
        ).first()
        if not skill:
            skill = db_models.Skill(name=skill_name.lower())
            db.add(skill)
            db.flush()

        status_val = "acquired" if skill_name in acquired else "missing"

        weight = next(
            (s["importance"] for s in market_skills if s["name"] == skill_name),
            0.5,
        )

        detail = db_models.GapDetail(
            career_gap_id=analysis.id,
            skill_id=skill.id,
            status=status_val,
            weight=weight,
        )
        db.add(detail)

    db.commit()
    db.refresh(analysis)

    # ── 6. Construire la réponse ──────────────────────────────────────────────
    gap_details_response = [
        GapSkillDetail(
            skill_name=skill_name,
            status="acquired" if skill_name in acquired else "missing",
            weight=next(
                (s["importance"] for s in market_skills if s["name"] == skill_name),
                0.5,
            ),
        )
        for skill_name in set(acquired + missing)
    ]

    return GapResult(
        career_gap_id=analysis.id,
        employability_score=float(employability_score),
        acquired_skills=acquired,
        missing_skills=missing,
        gap_details=gap_details_response,
        created_at=analysis.created_at,
    )