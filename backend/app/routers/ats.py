from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models as db_models
from app.models.cv import CVOptimizationRequest, CVOptimizationResponse
from app.routers.auth import get_current_user
from app.services.ats_service import analyze_cv_for_ats

router = APIRouter()


@router.post("/optimize", response_model=CVOptimizationResponse, status_code=status.HTTP_201_CREATED)
async def optimize_cv(
    request: CVOptimizationRequest,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyse un CV et génère des suggestions d'optimisation pour les ATS.
    Peut comparer contre une offre spécifique ou le marché général.
    """
    cv = db.query(db_models.CV).filter(
        db_models.CV.id == request.cv_id,
        db_models.CV.user_id == current_user.id,
    ).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV introuvable")

    if not cv.extracted_text:
        raise HTTPException(status_code=400, detail="Le CV n'a pas encore été analysé")

    offer_text = request.offer_text
    if request.offer_id and not offer_text:
        offer = db.query(db_models.Offer).filter(
            db_models.Offer.id == request.offer_id
        ).first()
        if not offer:
            raise HTTPException(status_code=404, detail="Offre introuvable")
        offer_text = offer.description

    # Run full ATS analysis
    ats_result = await analyze_cv_for_ats(
        cv_text=cv.extracted_text,
        offer_text=offer_text,
    )

    import json

    # Sauvegarder le résultat
    # missing_keywords and suggestions stored in existing Text columns
    # Extra fields (warnings, scores) packed into suggestions as JSON prefix
    extra = {
        "keyword_score":      ats_result["keyword_score"],
        "format_score":       ats_result["format_score"],
        "completeness_score": ats_result["completeness_score"],
        "matched_keywords":   ats_result["matched_keywords"],
        "warnings":           ats_result["warnings"],
    }
    suggestions_blob = (
        "__extra__:" + json.dumps(extra) + "\n---\n"
        + "\n".join(ats_result["suggestions"])
    )

    optimization = db_models.CVOptimization(
        cv_id=cv.id,
        offer_id=request.offer_id,
        ats_score=ats_result["ats_score"],
        missing_keywords=", ".join(ats_result["missing_keywords"]),
        suggestions=suggestions_blob,
    )
    db.add(optimization)
    db.commit()
    db.refresh(optimization)

    return CVOptimizationResponse(
        cv_id=cv.id,
        ats_score=float(optimization.ats_score),
        keyword_score=ats_result["keyword_score"],
        format_score=ats_result["format_score"],
        completeness_score=ats_result["completeness_score"],
        matched_keywords=ats_result["matched_keywords"],
        missing_keywords=ats_result["missing_keywords"],
        warnings=ats_result["warnings"],
        suggestions=ats_result["suggestions"],
        created_at=optimization.created_at,
    )


@router.get("/history/{cv_id}", response_model=list[CVOptimizationResponse])
def optimization_history(
    cv_id: int,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historique des optimisations ATS pour un CV."""
    cv = db.query(db_models.CV).filter(
        db_models.CV.id == cv_id,
        db_models.CV.user_id == current_user.id,
    ).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV introuvable")

    optimizations = db.query(db_models.CVOptimization).filter(
        db_models.CVOptimization.cv_id == cv_id
    ).order_by(db_models.CVOptimization.created_at.desc()).all()

    import json
    results = []
    for opt in optimizations:
        raw = opt.suggestions or ""
        keyword_score = 0.0
        format_score = 0.0
        completeness_score = 0.0
        matched_keywords = []
        warnings = []
        suggestions = []

        if raw.startswith("__extra__:"):
            try:
                meta_line, rest = raw.split("\n---\n", 1)
                extra = json.loads(meta_line[len("__extra__:"):])
                keyword_score      = extra.get("keyword_score", 0.0)
                format_score       = extra.get("format_score", 0.0)
                completeness_score = extra.get("completeness_score", 0.0)
                matched_keywords   = extra.get("matched_keywords", [])
                warnings           = extra.get("warnings", [])
                suggestions        = [s for s in rest.splitlines() if s.strip()]
            except Exception:
                suggestions = [s for s in raw.splitlines() if s.strip()]
        else:
            suggestions = [s for s in raw.splitlines() if s.strip()]

        results.append(CVOptimizationResponse(
            cv_id=opt.cv_id,
            ats_score=float(opt.ats_score),
            keyword_score=keyword_score,
            format_score=format_score,
            completeness_score=completeness_score,
            matched_keywords=matched_keywords,
            missing_keywords=[k.strip() for k in (opt.missing_keywords or "").split(",") if k.strip()],
            warnings=warnings,
            suggestions=suggestions,
            created_at=opt.created_at,
        ))

    return results