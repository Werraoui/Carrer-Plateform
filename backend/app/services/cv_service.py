"""CV lifecycle helpers."""

from sqlalchemy.orm import Session

from app.db import models as m


def delete_cv_and_dependencies(db: Session, cv: m.CV) -> dict:
    """
    Supprime un CV et toutes les données liées (gap, roadmaps, ATS, skills).

    Ordre explicite pour fonctionner même si les FK Supabase n'ont pas ON DELETE CASCADE.
    """
    cv_id = cv.id
    stats = {
        "gap_analyses": 0,
        "roadmaps": 0,
        "cv_optimizations": 0,
        "cv_skills": 0,
    }

    analysis_ids = [
        row[0]
        for row in db.query(m.CareerGapAnalysis.id)
        .filter(m.CareerGapAnalysis.cv_id == cv_id)
        .all()
    ]

    for gap_id in analysis_ids:
        roadmap_ids = [
            row[0]
            for row in db.query(m.Roadmap.id)
            .filter(m.Roadmap.career_gap_id == gap_id)
            .all()
        ]
        for roadmap_id in roadmap_ids:
            step_ids = [
                row[0]
                for row in db.query(m.RoadmapStep.id)
                .filter(m.RoadmapStep.roadmap_id == roadmap_id)
                .all()
            ]
            if step_ids:
                db.query(m.UserSkillProgress).filter(
                    m.UserSkillProgress.roadmap_step_id.in_(step_ids)
                ).delete(synchronize_session=False)
            db.query(m.RoadmapStep).filter(m.RoadmapStep.roadmap_id == roadmap_id).delete(
                synchronize_session=False
            )
            stats["roadmaps"] += 1

        db.query(m.Roadmap).filter(m.Roadmap.career_gap_id == gap_id).delete(
            synchronize_session=False
        )
        db.query(m.GapDetail).filter(m.GapDetail.career_gap_id == gap_id).delete(
            synchronize_session=False
        )

    stats["gap_analyses"] = (
        db.query(m.CareerGapAnalysis)
        .filter(m.CareerGapAnalysis.cv_id == cv_id)
        .delete(synchronize_session=False)
    )

    stats["cv_optimizations"] = (
        db.query(m.CVOptimization).filter(m.CVOptimization.cv_id == cv_id).delete(
            synchronize_session=False
        )
    )

    stats["cv_skills"] = (
        db.query(m.CVSkill).filter(m.CVSkill.cv_id == cv_id).delete(synchronize_session=False)
    )

    db.delete(cv)
    return stats
