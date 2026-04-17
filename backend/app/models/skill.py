from pydantic import BaseModel
from typing import List, Optional


# ── Un skill normalisé (correspond à skill_taxonomy.json) ─────────
class SkillItem(BaseModel):
    id: str        # ex: "python"
    label: str     # ex: "Python"
    category: str  # ex: "programming" | "database" | "ml" | "cloud" | "tool"


# ── Résultat du Career Gap ────────────────────────────────────────
class GapResult(BaseModel):
    acquired: List[str]         # skills que l'étudiant a déjà
    missing: List[str]          # skills manquants
    employability_score: float  # score 0-100
    match_percentage: float     # % de skills acquis sur total requis


# ── Requête pour lancer une analyse de gap ────────────────────────
class GapAnalysisRequest(BaseModel):
    cv_id: int
    target_job: str             # ex: "Data Engineer"
    offer_id: Optional[int] = None  # si comparaison avec une offre spécifique


# ── Une étape dans la roadmap ─────────────────────────────────────
class RoadmapStep(BaseModel):
    week: int                   # numéro de semaine ex: 1
    skill: str                  # skill ciblé ex: "spark"
    title: str                  # ex: "Introduction à Apache Spark"
    description: str            # ce qu'il faut apprendre
    resources: List[str]        # liens cours / docs
    project: Optional[str] = None  # mini projet suggéré


# ── Roadmap complète générée par le LLM ──────────────────────────
class RoadmapResponse(BaseModel):
    target_job: str
    total_weeks: int
    missing_skills: List[str]
    steps: List[RoadmapStep]


# ── Requête pour générer une roadmap ─────────────────────────────
class RoadmapRequest(BaseModel):
    missing_skills: List[str]
    target_job: str
    level: Optional[str] = "débutant"