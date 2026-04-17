from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ── Réponse après upload d'un CV ──────────────────────────────────
class CVUploadResponse(BaseModel):
    cv_id: int
    filename: str
    extracted_skills: List[str]  # liste des skill ids normalisés ex: ["python", "sql"]
    message: str = "CV uploadé et analysé avec succès"


# ── Détail d'un CV stocké ─────────────────────────────────────────
class CVDetail(BaseModel):
    id: int
    file_path: str
    extracted_text: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Liste des CVs d'un utilisateur ───────────────────────────────
class CVListResponse(BaseModel):
    cvs: List[CVDetail]
    total: int