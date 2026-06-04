import os
import logging
import httpx

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models as db_models
from app.models.cv import CVResponse, CVUploadResponse
from app.routers.auth import get_current_user
from app.config import settings
from app.services.cv_service import delete_cv_and_dependencies

log    = logging.getLogger("router.cv")
router = APIRouter()


def _extract_text(file_path: str) -> str:
    """Extrait le texte d'un PDF ou DOCX. Retourne '' si échec."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            import fitz  # PyMuPDF
            doc  = fitz.open(file_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        elif ext in (".docx", ".doc"):
            from docx import Document
            return "\n".join(p.text for p in Document(file_path).paragraphs)
    except Exception as e:
        log.warning(f"Extraction texte échouée pour {file_path} : {e}")
    return ""


async def _extract_skills_via_ml(text: str) -> list[str]:
    """Appelle le ML service pour extraire les skills. Retourne [] si indisponible."""
    if not text.strip():
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/extract-skills",
                json={"text": text},
            )
            resp.raise_for_status()
            data = resp.json()
            skills = data.get("skills", [])
            source = data.get("source", "unknown")
            log.info(f"ML extraction ({source}): {len(skills)} skills")
            return skills
    except Exception as e:
        log.warning(f"ML service indisponible pour extraction skills : {e}")
        return []


async def _save_skills_to_db(cv: db_models.CV, skill_names: list[str], db: Session):
    """Crée les skills en BDD et les lie au CV via CVSkill."""
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

        existing = db.query(db_models.CVSkill).filter(
            db_models.CVSkill.cv_id   == cv.id,
            db_models.CVSkill.skill_id == skill.id,
        ).first()
        if not existing:
            db.add(db_models.CVSkill(cv_id=cv.id, skill_id=skill.id))

    db.commit()


# ── POST /cv/upload ────────────────────────────────────────────────────────────

@router.post("/upload", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file:         UploadFile                  = File(...),
    current_user: db_models.User              = Depends(get_current_user),
    db:           Session                     = Depends(get_db),
):
    """
    Upload un CV (PDF ou DOCX).
    - Sauvegarde le fichier sur disque
    - Extrait le texte avec PyMuPDF / python-docx
    - Appelle le ML service pour extraire les skills (non bloquant)
    - Sauvegarde tout en BDD
    """
    # Vérifier l'extension
    allowed = {".pdf", ".docx", ".doc"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format non supporté. Formats acceptés : {', '.join(allowed)}",
        )

    # Vérifier la taille (lecture partielle)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content   = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop grand. Maximum : {settings.MAX_FILE_SIZE_MB} MB",
        )

    # Créer le dossier uploads si besoin
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    # Nom de fichier unique (timestamp + original)
    import time
    safe_name = f"{int(time.time())}_{os.path.basename(file.filename or 'cv')}"
    file_path = os.path.join(upload_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)
    log.info(f"CV sauvegardé : {file_path}")

    # Extraire le texte
    extracted_text = _extract_text(file_path)
    log.info(f"Texte extrait : {len(extracted_text)} caractères")

    # Créer l'entrée CV en BDD
    cv = db_models.CV(
        user_id        = current_user.id,
        file_path      = file_path,
        extracted_text = extracted_text or None,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)

    # Extraire les skills via ML service (non bloquant)
    skill_names = await _extract_skills_via_ml(extracted_text)
    if skill_names:
        await _save_skills_to_db(cv, skill_names, db)
        log.info(f"CV {cv.id} → {len(skill_names)} skills extraits")
    else:
        log.info(f"CV {cv.id} → ML service indisponible, 0 skills extraits")

    return CVUploadResponse(
        cv_id       = cv.id,
        message     = "CV uploadé avec succès",
        skills      = skill_names,
        skill_count = len(skill_names),
    )


# ── GET /cv/ ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[CVResponse])
def list_cvs(
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Liste tous les CVs de l'utilisateur connecté."""
    cvs = db.query(db_models.CV).filter(
        db_models.CV.user_id == current_user.id
    ).order_by(db_models.CV.uploaded_at.desc()).all()

    result = []
    for cv in cvs:
        skill_names = [
            cs.skill.name
            for cs in db.query(db_models.CVSkill).filter(
                db_models.CVSkill.cv_id == cv.id
            ).all()
            if cs.skill
        ]
        result.append(CVResponse(
            id               = cv.id,
            user_id          = cv.user_id,
            file_path        = os.path.basename(cv.file_path),
            uploaded_at      = cv.uploaded_at,
            skills_extracted = skill_names,
        ))

    return result


# ── DELETE /cv/{cv_id} ─────────────────────────────────────────────────────────

@router.delete("/{cv_id}", status_code=status.HTTP_200_OK)
def delete_cv(
    cv_id:        int,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Supprime un CV (fichier disque + gap analyses + roadmaps + BDD)."""
    cv = db.query(db_models.CV).filter(
        db_models.CV.id      == cv_id,
        db_models.CV.user_id == current_user.id,
    ).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV introuvable")

    file_path = cv.file_path
    try:
        stats = delete_cv_and_dependencies(db, cv)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        log.error("Suppression CV %s — contrainte FK : %s", cv_id, e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de supprimer ce CV : des données liées bloquent encore la suppression.",
        ) from e

    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            log.info("Fichier supprimé : %s", file_path)
    except OSError as e:
        log.warning("Fichier déjà absent ou non supprimable %s : %s", file_path, e)

    log.info("CV %s supprimé — %s", cv_id, stats)
    return {
        "message": "CV supprimé avec succès",
        "cv_id": cv_id,
        "deleted": stats,
    }