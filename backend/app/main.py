from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, cv, gap, roadmap, interview, ats
from app.db.database import engine
from app.db import models as db_models

db_models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Career Guidance Platform",
    description="API pour l'orientation de carrière intelligente des étudiants",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(cv.router, prefix="/cv", tags=["CV"])
app.include_router(gap.router, prefix="/gap", tags=["Career Gap"])
app.include_router(roadmap.router, prefix="/roadmap", tags=["Roadmap"])
app.include_router(interview.router, prefix="/interview", tags=["Interview"])
app.include_router(ats.router, prefix="/ats", tags=["ATS Optimization"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Career Guidance API is running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}