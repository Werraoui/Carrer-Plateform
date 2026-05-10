import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from db import models as db_models
from app.routers.auth import get_current_user

log    = logging.getLogger("router.roadmap")
router = APIRouter()


# Schemas 

class RoadmapGenerateRequest(BaseModel):
    career_gap_id:  int
    duration_weeks: Optional[int] = 8
    use_rag:        Optional[bool] = True
    use_llm:        Optional[bool] = True


class RoadmapStepOut(BaseModel):
    id:            int
    week_number:   int
    title:         str
    skill_name:    Optional[str]
    type:          str
    resource_link: Optional[str]
    description:   Optional[str]
    tip:           Optional[str]

    class Config:
        from_attributes = True


class RoadmapOut(BaseModel):
    roadmap_id:     int
    job_name:       str
    duration_weeks: int
    engine:         str
    intro:          Optional[str]
    market_insight: Optional[str]
    steps:          List[RoadmapStepOut]
    summary:        dict
    created_at:     datetime

    class Config:
        from_attributes = True


class ProgressUpdate(BaseModel):
    step_id: int
    status:  str   # "completed", "in_progress", "not_started"


#  POST /roadmap/generate 

@router.post("/generate", response_model=RoadmapOut, status_code=status.HTTP_201_CREATED)
async def generate_roadmap(
    request:      RoadmapGenerateRequest,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):

    # 1. Vérifier l'analyse de gap
    analysis = db.query(db_models.CareerGapAnalysis).filter(
        db_models.CareerGapAnalysis.id == request.career_gap_id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse de gap introuvable")

    utj = db.query(db_models.UserTargetJob).filter(
        db_models.UserTargetJob.id == analysis.user_target_job_id,
        db_models.UserTargetJob.user_id == current_user.id,
    ).first()
    if not utj:
        raise HTTPException(status_code=403, detail="Accès refusé")

    # 2. Récupérer les skills manquants et acquis depuis le gap
    all_details = db.query(db_models.GapDetail, db_models.Skill).join(
        db_models.Skill, db_models.GapDetail.skill_id == db_models.Skill.id
    ).filter(
        db_models.GapDetail.career_gap_id == request.career_gap_id,
    ).all()

    missing_skills  = [s.name for gd, s in all_details if gd.status == "missing"]
    acquired_skills = [s.name for gd, s in all_details if gd.status == "acquired"]

    if not missing_skills:
        raise HTTPException(
            status_code=400,
            detail="Aucun skill manquant — pas besoin de roadmap !",
        )

    job_name   = utj.target_job.name if utj.target_job else "Poste cible"
    user_level = current_user.level or "débutant"

    log.info(
        f"Génération roadmap — user={current_user.id} | job={job_name} | "
        f"missing={missing_skills} | weeks={request.duration_weeks}"
    )

    # 3. Appeler le pipeline RAG complet
    from app.services.roadmap.roadmap_service import generate_roadmap as rag_pipeline

    try:
        roadmap_data = await rag_pipeline(
            missing_skills  = missing_skills,
            acquired_skills = acquired_skills,
            duration_weeks  = request.duration_weeks,
            user_level      = user_level,
            job_name        = job_name,
            use_rag         = request.use_rag,
            use_llm         = request.use_llm,
        )
    except Exception as e:
        log.error(f"Pipeline RAG échoué : {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération : {str(e)}",
        )

    # 4. Sauvegarder la roadmap en BDD
    roadmap_record = db_models.Roadmap(
        user_target_job_id = utj.id,
        career_gap_id      = request.career_gap_id,
        duration_weeks     = request.duration_weeks,
    )
    db.add(roadmap_record)
    db.flush()

    saved_steps = []
    for step_data in roadmap_data.get("steps", []):
        skill_id   = None
        skill_name = step_data.get("skill_name", "")
        if skill_name:
            skill = db.query(db_models.Skill).filter(
                db_models.Skill.name == skill_name.lower().strip()
            ).first()
            if skill:
                skill_id = skill.id

        step_record = db_models.RoadmapStep(
            roadmap_id    = roadmap_record.id,
            skill_id      = skill_id,
            week_number   = step_data.get("week_number", 1),
            title         = step_data.get("title", ""),
            type          = step_data.get("type", "course"),
            resource_link = step_data.get("resource_link"),
        )
        db.add(step_record)
        db.flush()

        saved_steps.append(RoadmapStepOut(
            id            = step_record.id,
            week_number   = step_record.week_number,
            title         = step_record.title,
            skill_name    = skill_name or None,
            type          = step_record.type,
            resource_link = step_record.resource_link,
            description   = step_data.get("description"),
            tip           = step_data.get("tip"),
        ))

    db.commit()
    db.refresh(roadmap_record)

    log.info(
        f"Roadmap {roadmap_record.id} sauvegardée — "
        f"{len(saved_steps)} steps | moteur: {roadmap_data.get('engine')}"
    )

    return RoadmapOut(
        roadmap_id     = roadmap_record.id,
        job_name       = job_name,
        duration_weeks = roadmap_record.duration_weeks,
        engine         = roadmap_data.get("engine", "rule_based"),
        intro          = roadmap_data.get("intro"),
        market_insight = roadmap_data.get("market_insight"),
        steps          = saved_steps,
        summary        = roadmap_data.get("summary", {}),
        created_at     = roadmap_record.created_at,
    )


# GET /roadmap/{roadmap_id} 

@router.get("/{roadmap_id}", response_model=RoadmapOut)
def get_roadmap(
    roadmap_id:   int,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Récupère une roadmap existante par son ID."""
    roadmap = db.query(db_models.Roadmap).filter(
        db_models.Roadmap.id == roadmap_id
    ).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap introuvable")

    utj = db.query(db_models.UserTargetJob).filter(
        db_models.UserTargetJob.id == roadmap.user_target_job_id,
        db_models.UserTargetJob.user_id == current_user.id,
    ).first()
    if not utj:
        raise HTTPException(status_code=403, detail="Accès refusé")

    job_name = utj.target_job.name if utj.target_job else "Poste cible"

    steps_db = db.query(db_models.RoadmapStep, db_models.Skill).outerjoin(
        db_models.Skill, db_models.RoadmapStep.skill_id == db_models.Skill.id
    ).filter(
        db_models.RoadmapStep.roadmap_id == roadmap_id
    ).order_by(db_models.RoadmapStep.week_number).all()

    steps_out = [
        RoadmapStepOut(
            id            = step.id,
            week_number   = step.week_number,
            title         = step.title,
            skill_name    = skill.name if skill else None,
            type          = step.type,
            resource_link = step.resource_link,
            description   = None,
            tip           = None,
        )
        for step, skill in steps_db
    ]

    courses_count  = sum(1 for s in steps_out if s.type == "course")
    projects_count = sum(1 for s in steps_out if s.type == "project")

    return RoadmapOut(
        roadmap_id     = roadmap.id,
        job_name       = job_name,
        duration_weeks = roadmap.duration_weeks,
        engine         = "rule_based",
        intro          = None,
        market_insight = None,
        steps          = steps_out,
        summary        = {
            "courses_count":  courses_count,
            "projects_count": projects_count,
            "weeks_used":     max((s.week_number for s in steps_out), default=0),
        },
        created_at = roadmap.created_at,
    )


# GET /roadmap/ 

@router.get("/", response_model=List[RoadmapOut])
def list_roadmaps(
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Liste toutes les roadmaps de l'utilisateur connecté."""
    utj_ids = [
        r.id for r in db.query(db_models.UserTargetJob.id).filter(
            db_models.UserTargetJob.user_id == current_user.id
        ).all()
    ]

    roadmaps = db.query(db_models.Roadmap).filter(
        db_models.Roadmap.user_target_job_id.in_(utj_ids)
    ).order_by(db_models.Roadmap.created_at.desc()).all()

    results = []
    for roadmap in roadmaps:
        utj = db.query(db_models.UserTargetJob).filter(
            db_models.UserTargetJob.id == roadmap.user_target_job_id
        ).first()
        job_name    = utj.target_job.name if utj and utj.target_job else "Poste cible"
        steps_count = db.query(db_models.RoadmapStep).filter(
            db_models.RoadmapStep.roadmap_id == roadmap.id
        ).count()

        results.append(RoadmapOut(
            roadmap_id     = roadmap.id,
            job_name       = job_name,
            duration_weeks = roadmap.duration_weeks,
            engine         = "rule_based",
            intro          = None,
            market_insight = None,
            steps          = [],
            summary        = {"total_steps": steps_count},
            created_at     = roadmap.created_at,
        ))

    return results


# PATCH /roadmap/progress 

@router.patch("/progress", status_code=status.HTTP_200_OK)
def update_step_progress(
    update:       ProgressUpdate,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Met à jour la progression d'un step """
    step = db.query(db_models.RoadmapStep).filter(
        db_models.RoadmapStep.id == update.step_id
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step introuvable")

    roadmap = db.query(db_models.Roadmap).filter(
        db_models.Roadmap.id == step.roadmap_id
    ).first()
    utj = db.query(db_models.UserTargetJob).filter(
        db_models.UserTargetJob.id == roadmap.user_target_job_id,
        db_models.UserTargetJob.user_id == current_user.id,
    ).first()
    if not utj:
        raise HTTPException(status_code=403, detail="Accès refusé")

    if step.skill_id:
        progress = db.query(db_models.UserSkillProgress).filter(
            db_models.UserSkillProgress.user_id  == current_user.id,
            db_models.UserSkillProgress.skill_id == step.skill_id,
        ).first()
        if progress:
            progress.status = update.status
        else:
            db.add(db_models.UserSkillProgress(
                user_id  = current_user.id,
                skill_id = step.skill_id,
                status   = update.status,
            ))

    db.commit()
    return {"step_id": update.step_id, "status": update.status, "message": "Progression mise à jour"}


# GET /roadmap/{roadmap_id}/progress
@router.get("/{roadmap_id}/progress")
def get_roadmap_progress(
    roadmap_id:   int,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Retourne la progression et le pourcentage de complétion d'une roadmap."""
    roadmap = db.query(db_models.Roadmap).filter(
        db_models.Roadmap.id == roadmap_id
    ).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap introuvable")

    utj = db.query(db_models.UserTargetJob).filter(
        db_models.UserTargetJob.id == roadmap.user_target_job_id,
        db_models.UserTargetJob.user_id == current_user.id,
    ).first()
    if not utj:
        raise HTTPException(status_code=403, detail="Accès refusé")

    steps = db.query(db_models.RoadmapStep).filter(
        db_models.RoadmapStep.roadmap_id == roadmap_id
    ).all()

    skill_ids = [s.skill_id for s in steps if s.skill_id]
    progress_map = {
        p.skill_id: p.status
        for p in db.query(db_models.UserSkillProgress).filter(
            db_models.UserSkillProgress.user_id  == current_user.id,
            db_models.UserSkillProgress.skill_id.in_(skill_ids),
        ).all()
    }

    completed           = 0
    steps_with_progress = []
    for step in steps:
        prog = progress_map.get(step.skill_id, "not_started") if step.skill_id else "not_started"
        if prog == "completed":
            completed += 1
        steps_with_progress.append({
            "step_id": step.id,
            "week":    step.week_number,
            "title":   step.title,
            "type":    step.type,
            "status":  prog,
        })

    total          = len(steps)
    completion_pct = round((completed / total * 100) if total > 0 else 0, 1)

    return {
        "roadmap_id":      roadmap_id,
        "total_steps":     total,
        "completed_steps": completed,
        "completion_pct":  completion_pct,
        "steps":           steps_with_progress,
    }