from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.routers import auth, cv, gap, roadmap, interview, ats
from app.db.database import engine
from app.db import models as db_models

db_models.Base.metadata.create_all(bind=engine)

log = logging.getLogger("main")

app = FastAPI(
    title="Career Guidance Platform",
    description="API pour l'orientation de carrière intelligente des étudiants",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/auth",      tags=["Authentication"])
app.include_router(cv.router,        prefix="/cv",         tags=["CV"])
app.include_router(gap.router,       prefix="/gap",        tags=["Career Gap"])
app.include_router(roadmap.router,   prefix="/roadmap",    tags=["Roadmap"])
app.include_router(interview.router, prefix="/interview",  tags=["Interview"])
app.include_router(ats.router,       prefix="/ats",        tags=["ATS Optimization"])


@app.on_event("startup")
async def startup_event():
    """Initialise ChromaDB au démarrage — indexe les documents si nécessaire."""
    try:
        from app.services.roadmap.rag.vector_store import initialize_vector_store
        stats = initialize_vector_store()
        log.info(
            f"ChromaDB prêt : {stats.get('total_documents', 0)} documents "
            f"(KB: {stats.get('knowledge_base_docs', 0)}, "
            f"Scraper: {stats.get('scraper_docs', 0)})"
        )
    except Exception as e:
        log.warning(f"ChromaDB init échoué (non bloquant) : {e}")
        log.warning("Le pipeline RAG utilisera le fallback rule-based")


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Career Guidance API is running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}