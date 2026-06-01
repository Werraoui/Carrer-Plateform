"""
Idempotent seed data for target jobs, skills, and job_skills.

Run from backend/:
    python -m app.db.seed
"""

from __future__ import annotations

import logging
from decimal import Decimal
from app.db.database import SessionLocal
from app.db import models as db_models

log = logging.getLogger(__name__)

# ── Reference data ────────────────────────────────────────────────────────────

TARGET_JOBS: list[dict] = [
    {
        "name": "Data Engineer",
        "description": "Build and maintain data pipelines, warehouses, and ETL workflows.",
        "sector": "Data",
    },
    {
        "name": "Data Analyst",
        "description": "Analyze data to support business decisions and reporting.",
        "sector": "Data",
    },
    {
        "name": "Data Scientist",
        "description": "Develop statistical and machine learning models on complex datasets.",
        "sector": "Data",
    },
    {
        "name": "ML Engineer",
        "description": "Deploy and operate machine learning systems in production.",
        "sector": "Data",
    },
    {
        "name": "Backend Developer",
        "description": "Design and implement server-side APIs and business logic.",
        "sector": "Software",
    },
    {
        "name": "DevOps Engineer",
        "description": "Automate delivery, infrastructure, and reliability for software teams.",
        "sector": "Infrastructure",
    },
    {
        "name": "Cloud Engineer",
        "description": "Architect and operate cloud-native infrastructure and services.",
        "sector": "Infrastructure",
    },
    {
        "name": "Fullstack Developer",
        "description": "Build end-to-end web applications across frontend and backend.",
        "sector": "Software",
    },
]

# skill_name -> category
SKILLS: dict[str, str] = {
    "python": "language",
    "sql": "database",
    "spark": "data",
    "airflow": "data",
    "docker": "devops",
    "kubernetes": "devops",
    "aws": "cloud",
    "kafka": "data",
    "etl": "data",
    "pandas": "data",
    "numpy": "data",
    "machine learning": "ml",
    "tensorflow": "ml",
    "pytorch": "ml",
    "scikit-learn": "ml",
    "mlflow": "ml",
    "fastapi": "backend",
    "django": "backend",
    "rest api": "backend",
    "javascript": "frontend",
    "typescript": "frontend",
    "react": "frontend",
    "git": "tooling",
    "linux": "devops",
    "terraform": "devops",
    "ansible": "devops",
    "jenkins": "devops",
    "postgresql": "database",
    "mongodb": "database",
    "redis": "database",
    "azure": "cloud",
    "gcp": "cloud",
    "tableau": "analytics",
    "power bi": "analytics",
}

# job_name -> list of (skill_name, importance_score, frequency)
JOB_SKILLS: dict[str, list[tuple[str, float, float]]] = {
    "Data Engineer": [
        ("python", 0.95, 98.0),
        ("sql", 0.95, 97.0),
        ("spark", 0.90, 92.0),
        ("airflow", 0.85, 88.0),
        ("docker", 0.80, 85.0),
        ("aws", 0.85, 90.0),
        ("kafka", 0.80, 82.0),
        ("etl", 0.90, 95.0),
    ],
    "Data Analyst": [
        ("python", 0.85, 88.0),
        ("sql", 0.95, 99.0),
        ("pandas", 0.90, 94.0),
        ("tableau", 0.80, 80.0),
        ("power bi", 0.75, 78.0),
        ("numpy", 0.70, 75.0),
        ("postgresql", 0.75, 72.0),
        ("machine learning", 0.65, 68.0),
    ],
    "Data Scientist": [
        ("python", 0.95, 99.0),
        ("sql", 0.85, 90.0),
        ("pandas", 0.90, 93.0),
        ("machine learning", 0.95, 97.0),
        ("scikit-learn", 0.90, 92.0),
        ("tensorflow", 0.80, 85.0),
        ("pytorch", 0.80, 84.0),
        ("numpy", 0.85, 88.0),
    ],
    "ML Engineer": [
        ("python", 0.95, 98.0),
        ("machine learning", 0.95, 96.0),
        ("pytorch", 0.90, 90.0),
        ("tensorflow", 0.85, 88.0),
        ("docker", 0.85, 87.0),
        ("kubernetes", 0.80, 82.0),
        ("mlflow", 0.85, 85.0),
        ("aws", 0.80, 80.0),
    ],
    "Backend Developer": [
        ("python", 0.90, 92.0),
        ("sql", 0.90, 94.0),
        ("fastapi", 0.85, 86.0),
        ("django", 0.75, 78.0),
        ("rest api", 0.90, 91.0),
        ("docker", 0.80, 83.0),
        ("postgresql", 0.85, 88.0),
        ("git", 0.85, 90.0),
        ("redis", 0.70, 72.0),
    ],
    "DevOps Engineer": [
        ("docker", 0.95, 96.0),
        ("kubernetes", 0.90, 94.0),
        ("terraform", 0.90, 92.0),
        ("linux", 0.90, 95.0),
        ("git", 0.85, 90.0),
        ("aws", 0.85, 88.0),
        ("jenkins", 0.80, 82.0),
        ("ansible", 0.75, 78.0),
        ("python", 0.70, 75.0),
    ],
    "Cloud Engineer": [
        ("aws", 0.95, 97.0),
        ("terraform", 0.90, 93.0),
        ("docker", 0.85, 88.0),
        ("kubernetes", 0.90, 92.0),
        ("linux", 0.85, 90.0),
        ("azure", 0.75, 80.0),
        ("gcp", 0.75, 78.0),
        ("ansible", 0.70, 72.0),
    ],
    "Fullstack Developer": [
        ("javascript", 0.90, 94.0),
        ("typescript", 0.85, 88.0),
        ("react", 0.90, 92.0),
        ("python", 0.80, 85.0),
        ("sql", 0.85, 87.0),
        ("fastapi", 0.75, 78.0),
        ("docker", 0.70, 72.0),
        ("git", 0.85, 90.0),
        ("rest api", 0.80, 82.0),
    ],
}


def _get_or_create_skill(db, name: str, category: str | None = None) -> db_models.Skill:
    key = name.lower().strip()
    skill = db.query(db_models.Skill).filter(db_models.Skill.name == key).first()
    if skill:
        if category and not skill.category:
            skill.category = category
        return skill
    skill = db_models.Skill(name=key, category=category)
    db.add(skill)
    db.flush()
    return skill


def _get_or_create_target_job(db, data: dict) -> db_models.TargetJob:
    job = db.query(db_models.TargetJob).filter(db_models.TargetJob.name == data["name"]).first()
    if job:
        if data.get("description") and not job.description:
            job.description = data["description"]
        if data.get("sector") and not job.sector:
            job.sector = data["sector"]
        return job
    job = db_models.TargetJob(
        name=data["name"],
        description=data.get("description"),
        sector=data.get("sector"),
    )
    db.add(job)
    db.flush()
    return job


def _get_or_create_job_skill(
    db,
    target_job_id: int,
    skill_id: int,
    importance: float,
    frequency: float,
) -> db_models.JobSkill:
    link = db.query(db_models.JobSkill).filter(
        db_models.JobSkill.target_job_id == target_job_id,
        db_models.JobSkill.skill_id == skill_id,
    ).first()
    if link:
        link.importance_score = Decimal(str(importance))
        link.frequency = Decimal(str(frequency))
        return link
    link = db_models.JobSkill(
        target_job_id=target_job_id,
        skill_id=skill_id,
        importance_score=Decimal(str(importance)),
        frequency=Decimal(str(frequency)),
    )
    db.add(link)
    db.flush()
    return link


def _ensure_skills(db) -> dict[str, db_models.Skill]:
    """Create all skills referenced in JOB_SKILLS and SKILLS."""
    names: set[str] = set(SKILLS.keys())
    for entries in JOB_SKILLS.values():
        for skill_name, _, _ in entries:
            names.add(skill_name.lower().strip())

    result: dict[str, db_models.Skill] = {}
    for name in sorted(names):
        category = SKILLS.get(name)
        result[name] = _get_or_create_skill(db, name, category)
    return result


def seed() -> dict[str, int]:
    """Insert reference data. Safe to run multiple times."""
    db = SessionLocal()
    stats = {"target_jobs": 0, "skills": 0, "job_skills": 0}
    try:
        skill_map = _ensure_skills(db)
        stats["skills"] = len(skill_map)

        for job_data in TARGET_JOBS:
            job = _get_or_create_target_job(db, job_data)
            stats["target_jobs"] += 1

            for skill_name, importance, frequency in JOB_SKILLS.get(job.name, []):
                skill = skill_map.get(skill_name.lower().strip())
                if not skill:
                    skill = _get_or_create_skill(
                        db, skill_name, SKILLS.get(skill_name.lower().strip())
                    )
                    skill_map[skill.name] = skill
                _get_or_create_job_skill(db, job.id, skill.id, importance, frequency)
                stats["job_skills"] += 1

        db.commit()
        log.info(
            "Seed complete: %d jobs, %d skills, %d job_skill links processed",
            stats["target_jobs"],
            stats["skills"],
            stats["job_skills"],
        )
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_if_empty() -> bool:
    """
    Run seed only when target_jobs table has no rows.
    Returns True if seed ran, False if skipped.
    """
    db = SessionLocal()
    try:
        count = db.query(db_models.TargetJob).count()
        if count > 0:
            log.info("Seed skipped: %d target job(s) already present", count)
            return False
    finally:
        db.close()

    seed()
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = seed()
    print(
        f"Seeded successfully: {result['target_jobs']} jobs, "
        f"{result['skills']} skills, {result['job_skills']} job_skill rows"
    )
