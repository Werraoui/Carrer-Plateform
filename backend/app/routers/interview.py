"""
Simulateur d'entretien en chatbot (Gemini).

Offre collée → questions mixtes (QCM + réponses ouvertes) → bilan final avec score.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import models as db_models
from app.models.interview_chat import InterviewChatRequest, InterviewChatResponse
from app.routers.auth import get_current_user
from app.services.interview_chat_service import (
    check_gemini_health,
    gemini_configured,
    get_session_for_user,
    handle_chat_message,
)

log = logging.getLogger("router.interview")
router = APIRouter()


@router.get("/gemini-health")
async def interview_gemini_health():
    """
    Vérifie que Gemini est configuré et répond.
    Utile avant de lancer l'Interview Simulator.
    """
    result = await check_gemini_health()
    result["gemini_configured"] = gemini_configured()
    return result


@router.post("/chat", response_model=InterviewChatResponse)
async def interview_chat(
    body: InterviewChatRequest,
    current_user: db_models.User = Depends(get_current_user),
):
    """
    Chatbot d'entretien simulé (Google Gemini).

    **Premier message** : coller l'offre + demander la simulation d'entretien.
    **Ensuite** : répondre aux QCM (A/B/C/D) ou aux questions ouvertes (texte libre).
    **Fin** : `interview_complete=true` + `final_report` (score, bilan, corrections).

    Champs utiles pour l'UI :
    - `question_type` : "mcq" | "open"
    - `mcq` ou `open_question`
    - `final_report` : score_percent, answers_review, overall_advice
    """
    try:
        return await handle_chat_message(
            user_id=current_user.id,
            session_id=body.session_id,
            message=body.message,
        )
    except PermissionError:
        raise HTTPException(status_code=404, detail="Session introuvable")
    except ValueError as e:
        code = 409 if "terminé" in str(e).lower() else 400
        raise HTTPException(status_code=code, detail=str(e))


@router.get("/chat/{session_id}", response_model=InterviewChatResponse)
def get_interview_chat_session(
    session_id: str,
    current_user: db_models.User = Depends(get_current_user),
):
    """Récupère l'historique d'une session de chat."""
    result = get_session_for_user(session_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return result
