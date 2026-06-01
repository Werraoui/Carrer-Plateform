import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.db import models as db_models
from app.models.skill import (
    GapAnalysisRequest,
    GapResult,
    GapSkillDetail,
    TargetJobResponse,
    UserTargetJobRequest,
    UserTargetJobResponse,
)
from app.routers.auth import get_current_user
from app.services.gap_service import compute_and_save_gap

log    = logging.getLogger("router.gap")
router = APIRouter()


# ── POST /gap/target-job ───────────────────────────────────────────────────────

@router.post("/target-job", response_model=UserTargetJobResponse, status_code=status.HTTP_201_CREATED)
def set_target_job(
    request:      UserTargetJobRequest,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """
    Définit (ou change) le métier cible de l'utilisateur.
    L'ancien UserTargetJob actif est désactivé automatiquement.
    """
    # Vérifier que le métier cible existe
    target_job = db.query(db_models.TargetJob).filter(
        db_models.TargetJob.id == request.target_job_id
    ).first()
    if not target_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Métier cible id={request.target_job_id} introuvable",
        )

    # Désactiver l'ancien UserTargetJob actif
    db.query(db_models.UserTargetJob).filter(
        db_models.UserTargetJob.user_id   == current_user.id,
        db_models.UserTargetJob.is_active == True,
    ).update({"is_active": False})

    # Créer le nouveau
    utj = db_models.UserTargetJob(
        user_id       = current_user.id,
        target_job_id = request.target_job_id,
        is_active     = True,
    )
    db.add(utj)
    db.commit()
    db.refresh(utj)

    log.info(f"User {current_user.id} → nouveau métier cible : {target_job.name}")

    return UserTargetJobResponse(
        id            = utj.id,
        user_id       = utj.user_id,
        target_job_id = utj.target_job_id,
        is_active     = utj.is_active,
        target_job    = TargetJobResponse(
            id          = target_job.id,
            name        = target_job.name,
            description = target_job.description,
            sector      = target_job.sector,
        ),
    )


# ── GET /gap/target-jobs ───────────────────────────────────────────────────────

@router.get("/target-jobs", response_model=list[UserTargetJobResponse])
def list_target_jobs(
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Liste tous les métiers cibles de l'utilisateur (actifs et anciens)."""
    utjs = db.query(db_models.UserTargetJob).filter(
        db_models.UserTargetJob.user_id == current_user.id
    ).order_by(db_models.UserTargetJob.selected_at.desc()).all()

    result = []
    for utj in utjs:
        tj = utj.target_job
        result.append(UserTargetJobResponse(
            id            = utj.id,
            user_id       = utj.user_id,
            target_job_id = utj.target_job_id,
            is_active     = utj.is_active,
            target_job    = TargetJobResponse(
                id          = tj.id,
                name        = tj.name,
                description = tj.description,
                sector      = tj.sector,
            ) if tj else None,
        ))
    return result


# ── GET /gap/target-jobs/available ────────────────────────────────────────────

@router.get("/target-jobs/available", response_model=list[TargetJobResponse])
def list_available_jobs(db: Session = Depends(get_db)):
    """Liste tous les métiers disponibles dans la plateforme (sans auth)."""
    jobs = db.query(db_models.TargetJob).order_by(db_models.TargetJob.name).all()
    return [
        TargetJobResponse(
            id          = j.id,
            name        = j.name,
            description = j.description,
            sector      = j.sector,
        )
        for j in jobs
    ]


# ── POST /gap/analyze ──────────────────────────────────────────────────────────

@router.post("/analyze", response_model=GapResult, status_code=status.HTTP_201_CREATED)
async def analyze_gap(
    request:      GapAnalysisRequest,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """
    Calcule le career gap d'un CV.

    Deux scénarios :
    - request.target_job_id → comparaison contre le marché général du métier
    - request.offer_id      → comparaison contre une offre spécifique

    Si les deux sont fournis, offer_id a la priorité.
    """
    # 1. Vérifier que le CV appartient à l'utilisateur
    cv = db.query(db_models.CV).filter(
        db_models.CV.id      == request.cv_id,
        db_models.CV.user_id == current_user.id,
    ).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV introuvable")

    if not cv.extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Le CV n'a pas encore été analysé (texte non extrait). "
                   "Essayez de le réuploader.",
        )

    # 2. Trouver l'UserTargetJob actif (ou utiliser target_job_id fourni)
    if request.target_job_id:
        # Chercher un UTJ existant pour ce job, sinon en créer un temporairement
        utj = db.query(db_models.UserTargetJob).filter(
            db_models.UserTargetJob.user_id       == current_user.id,
            db_models.UserTargetJob.target_job_id == request.target_job_id,
        ).order_by(db_models.UserTargetJob.selected_at.desc()).first()

        if not utj:
            # Créer un UTJ à la volée
            utj = db_models.UserTargetJob(
                user_id       = current_user.id,
                target_job_id = request.target_job_id,
                is_active     = True,
            )
            db.add(utj)
            db.flush()
    else:
        # Utiliser l'UTJ actif de l'utilisateur
        utj = db.query(db_models.UserTargetJob).filter(
            db_models.UserTargetJob.user_id   == current_user.id,
            db_models.UserTargetJob.is_active == True,
        ).first()

        if not utj:
            raise HTTPException(
                status_code=400,
                detail="Aucun métier cible défini. "
                       "Appelez d'abord POST /gap/target-job.",
            )

    # 3. Vérifier l'offre si fournie
    offer_id = request.offer_id
    if offer_id:
        offer = db.query(db_models.Offer).filter(
            db_models.Offer.id == offer_id
        ).first()
        if not offer:
            raise HTTPException(status_code=404, detail="Offre introuvable")

    log.info(
        f"Gap analysis — user={current_user.id} | cv={cv.id} | "
        f"utj={utj.id} | offer={offer_id}"
    )

    # 4. Déléguer au service
    result = await compute_and_save_gap(
        db              = db,
        cv              = cv,
        user_target_job = utj,
        offer_id        = offer_id,
    )

    return result


# ── GET /gap/history ───────────────────────────────────────────────────────────

@router.get("/history", response_model=list[GapResult])
def gap_history(
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Historique de toutes les analyses gap de l'utilisateur."""
    # Récupérer tous les UTJ de l'utilisateur
    utj_ids = [
        r.id for r in db.query(db_models.UserTargetJob.id).filter(
            db_models.UserTargetJob.user_id == current_user.id
        ).all()
    ]

    analyses = db.query(db_models.CareerGapAnalysis).filter(
        db_models.CareerGapAnalysis.user_target_job_id.in_(utj_ids)
    ).order_by(db_models.CareerGapAnalysis.created_at.desc()).all()

    results = []
    for analysis in analyses:
        details = db.query(db_models.GapDetail, db_models.Skill).join(
            db_models.Skill, db_models.GapDetail.skill_id == db_models.Skill.id
        ).filter(
            db_models.GapDetail.career_gap_id == analysis.id
        ).all()

        acquired = [s.name for gd, s in details if gd.status == "acquired"]
        missing  = [s.name for gd, s in details if gd.status == "missing"]
        gap_det  = [
            GapSkillDetail(
                skill_name = s.name,
                status     = gd.status,
                weight     = float(gd.weight or 0.5),
            )
            for gd, s in details
        ]

        results.append(GapResult(
            career_gap_id       = analysis.id,
            employability_score = float(analysis.employability_score or 0),
            acquired_skills     = acquired,
            missing_skills      = missing,
            gap_details         = gap_det,
            created_at          = analysis.created_at,
        ))

    return results