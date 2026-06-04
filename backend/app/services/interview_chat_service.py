"""
Simulateur d'entretien en chat : offre collée → questions mixtes (QCM + ouvert) → bilan final Gemini.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.config import settings
from app.models.interview_chat import (
    AnswerReviewItem,
    ChatMessage,
    InterviewChatResponse,
    InterviewFinalReport,
    McqQuestion,
)

log = logging.getLogger("interview_chat")

SYSTEM_PROMPT_BASE = """Tu es un interviewer TECHNIQUE senior (ingénieur / lead) menant un entretien réaliste en français.

RÈGLE D'OR — ANCRAGE OFFRE
Chaque question DOIT citer ou viser explicitement un élément de l'offre fournie ci-dessous :
- intitulé du poste, entreprise si mentionnée
- technologies, langages, frameworks, outils (ex. Python, SQL, Spark, Power BI…)
- missions, livrables, secteur, niveau d'expérience, responsabilités
Interdiction de poser des questions génériques type "parlez-moi de vous" sans lien avec l'offre.

PROFIL DES QUESTIONS (6 à 8 au total)
- Au moins 70 % de questions TECHNIQUES (implémentation, architecture, données, debugging, bonnes pratiques).
- Alterne QCM (question_type=mcq) et ouvert (question_type=open).
- QCM : 4 choix A) B) C) D) ; distracteurs techniquement plausibles mais incorrects pour CE poste.
- Ouvert : scénario concret tiré d'une mission de l'offre ("Comment traiteriez-vous…", "Décrivez votre approche pour…").
- Varie les thèmes : stack, data/ML, système, collaboration, livraison — selon ce qui est dans l'offre.

DÉROULÉ
1. Premier tour : accueil (2 phrases), synthèse précise du poste (entreprise + rôle + 2-3 technos clés), puis 1ère question technique ancrée offre.
2. Après chaque réponse : feedback court (correct/partiel/incorrect) + transition fluide + une nouvelle question.
3. Dernier tour : interview_complete=true, pas de nouvelle question, final_report détaillé.

BILAN FINAL (final_report)
- score_percent : 0-100 (réaliste selon les réponses)
- score_label : ex. "Excellent", "Bon potentiel", "À renforcer"
- overall_advice : 2-3 phrases actionnables pour le candidat
- summary : paragraphe de synthèse de la performance
- answers_review : une entrée par question posée (numérotée), avec correction ou amélioration

Réponds UNIQUEMENT en JSON valide (sans markdown) :

Pendant l'entretien :
{
  "assistant_message": "feedback + transition + énoncé de la question si besoin",
  "question_type": "mcq" | "open",
  "mcq": {"question": "...", "choices": ["A) ...", "B) ...", "C) ...", "D) ..."]} ou null,
  "open_question": "texte de la question ouverte" ou null,
  "interview_complete": false,
  "final_report": null
}

Fin d'entretien :
{
  "assistant_message": "Message de clôture motivant incluant le score (ex. Vous obtenez 78/100…)",
  "question_type": null,
  "mcq": null,
  "open_question": null,
  "interview_complete": true,
  "final_report": {
    "score_percent": 78,
    "score_label": "Bon potentiel",
    "overall_advice": "...",
    "summary": "...",
    "answers_review": [
      {
        "question_number": 1,
        "question_type": "mcq",
        "question_text": "...",
        "user_answer": "reprise de la réponse du candidat",
        "is_correct": true,
        "feedback": "pourquoi c'est correct ou incorrect",
        "improvement": "formulation idéale ou piste d'amélioration (null si parfait)"
      }
    ]
  }
}
"""

_sessions: dict[str, dict[str, Any]] = {}
MAX_OFFER_CHARS = 14_000


def _capture_offer_text(session: dict, message: str) -> None:
    """Conserve le texte d'offre le plus complet envoyé par l'utilisateur."""
    if len(message) < 80:
        return
    prev = session.get("offer_text") or ""
    if len(message) > len(prev):
        session["offer_text"] = message[:MAX_OFFER_CHARS]


def _build_system_instruction(session: dict) -> str:
    offer = (session.get("offer_text") or "").strip()
    if not offer:
        for m in session.get("messages", []):
            if m.get("role") == "user" and len(m.get("content", "")) > 80:
                offer = m["content"][:MAX_OFFER_CHARS]
                break
    block = (
        f"\n\n━━━ OFFRE D'EMPLOI DU CANDIDAT (source unique — cite-la dans chaque question) ━━━\n{offer}\n━━━ FIN OFFRE ━━━"
        if offer
        else "\n\n(Aucune offre détectée : demande au candidat de coller l'offre complète.)"
    )
    return SYSTEM_PROMPT_BASE + block


def gemini_configured() -> bool:
    key = (settings.LLM_API_KEY or "").strip()
    return bool(key) and key not in ("dummy", "your-key")


async def check_gemini_health() -> dict:
    """Vérifie clé API + disponibilité d'au moins un modèle Gemini."""
    if not gemini_configured():
        return {
            "configured": False,
            "ok": False,
            "message": "LLM_API_KEY absente ou invalide dans backend/.env",
            "model_tested": None,
        }

    base = settings.LLM_BASE_URL.rstrip("/")
    key = settings.LLM_API_KEY.strip()
    last_error = ""

    for model in settings.llm_model_candidates:
        url = f"{base}/models/{model}:generateContent?key={key}"
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": 'Réponds {"status":"ok"} en JSON.'}]}],
                        "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 64},
                    },
                )
            if resp.status_code == 200:
                return {
                    "configured": True,
                    "ok": True,
                    "message": "Gemini opérationnel",
                    "model_tested": model,
                    "models_available": settings.llm_model_candidates,
                }
            last_error = f"{model}: HTTP {resp.status_code} — {resp.text[:200]}"
            log.warning("Gemini health %s", last_error)
        except Exception as e:
            last_error = f"{model}: {e}"

    return {
        "configured": True,
        "ok": False,
        "message": last_error or "Aucun modèle Gemini disponible",
        "model_tested": None,
        "models_available": settings.llm_model_candidates,
    }


def _safe_parse_json(text: str) -> Optional[dict]:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


async def _call_gemini_chat(session: dict, contents: list[dict]) -> Optional[str]:
    if not gemini_configured():
        log.warning("Gemini: LLM_API_KEY non chargée — vérifiez backend/.env (guillemets sur DATABASE_URL)")
        return None

    base = settings.LLM_BASE_URL.rstrip("/")
    key = settings.LLM_API_KEY.strip()
    system_text = _build_system_instruction(session)

    payload = {
        "system_instruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }

    last_err = ""
    async with httpx.AsyncClient(timeout=90.0) as client:
        for model in settings.llm_model_candidates:
            url = f"{base}/models/{model}:generateContent?key={key}"
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    session["gemini_model"] = model
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                last_err = f"{model} HTTP {resp.status_code}"
                if resp.status_code in (429, 503, 500, 502, 504):
                    log.warning("Gemini %s, essai modèle suivant…", last_err)
                    continue
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                last_err = f"{model}: {e.response.status_code}"
                if e.response.status_code in (429, 503, 404):
                    continue
            except Exception as e:
                last_err = str(e)

    log.warning("Gemini interview: tous les modèles ont échoué — %s", last_err)
    return None


def _build_gemini_contents(session: dict) -> list[dict]:
    contents = []
    for msg in session["messages"]:
        role = "user" if msg["role"] == "user" else "model"
        if msg["role"] == "assistant" and msg.get("model_turn_json"):
            text = msg["model_turn_json"]
        else:
            text = msg["content"]
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


def _count_questions_asked(session: dict) -> int:
    return sum(
        1
        for m in session["messages"]
        if m["role"] == "assistant" and m.get("question_type") in ("mcq", "open")
    )


def _parse_final_report(raw: Any) -> Optional[dict]:
    if not raw or not isinstance(raw, dict):
        return None
    try:
        review = []
        for item in raw.get("answers_review") or []:
            if not isinstance(item, dict):
                continue
            review.append(
                {
                    "question_number": int(item.get("question_number", len(review) + 1)),
                    "question_type": str(item.get("question_type", "mcq")),
                    "question_text": str(item.get("question_text", "")),
                    "user_answer": str(item.get("user_answer", "")),
                    "is_correct": bool(item.get("is_correct")),
                    "feedback": str(item.get("feedback", "")),
                    "improvement": item.get("improvement"),
                }
            )
        score = int(raw.get("score_percent", 0))
        score = max(0, min(100, score))
        return {
            "score_percent": score,
            "score_label": str(raw.get("score_label") or "Évaluation"),
            "overall_advice": str(raw.get("overall_advice") or ""),
            "summary": str(raw.get("summary") or ""),
            "answers_review": review,
        }
    except (TypeError, ValueError):
        return None


def _parse_llm_turn(raw: Optional[str], session: dict) -> dict:
    parsed = _safe_parse_json(raw) if raw else None
    if not parsed:
        return _fallback_reply(session)

    if parsed.get("interview_complete"):
        report = _parse_final_report(parsed.get("final_report"))
        return {
            "assistant_message": str(
                parsed.get("assistant_message") or "Entretien terminé. Merci pour votre participation."
            ),
            "question_type": None,
            "mcq": None,
            "open_question": None,
            "interview_complete": True,
            "final_report": report or _demo_final_report(session),
        }

    q_type = parsed.get("question_type")
    if q_type not in ("mcq", "open"):
        q_type = "mcq" if parsed.get("mcq") else "open" if parsed.get("open_question") else "mcq"

    mcq = None
    mcq_raw = parsed.get("mcq")
    if q_type == "mcq" and mcq_raw and isinstance(mcq_raw, dict) and mcq_raw.get("question"):
        choices = mcq_raw.get("choices") or []
        if len(choices) >= 2:
            mcq = {
                "question": str(mcq_raw["question"]),
                "choices": [str(c) for c in choices[:6]],
            }
            q_type = "mcq"

    open_q = None
    if q_type == "open":
        open_q = str(parsed.get("open_question") or "").strip() or None
        if not open_q and mcq:
            q_type = "mcq"
        elif not open_q:
            open_q = "Décrivez une situation professionnelle en lien avec ce poste."

    if q_type == "mcq" and not mcq:
        q_type = "open"
        open_q = open_q or "Expliquez comment vos compétences correspondent à cette offre."

    msg = str(parsed.get("assistant_message") or "Continuons l'entretien.")
    if q_type == "open" and open_q and open_q not in msg:
        msg = f"{msg}\n\n{open_q}"

    return {
        "assistant_message": msg,
        "question_type": q_type if not parsed.get("interview_complete") else None,
        "mcq": mcq,
        "open_question": open_q if q_type == "open" else None,
        "interview_complete": False,
        "final_report": None,
    }


def _demo_final_report(session: dict) -> dict:
    n = _count_questions_asked(session)
    return {
        "score_percent": 65,
        "score_label": "À renforcer (mode démo)",
        "overall_advice": "Configurez LLM_API_KEY pour un bilan personnalisé basé sur vos réponses.",
        "summary": f"Vous avez répondu à {n} question(s) en mode démo.",
        "answers_review": [],
    }


def _fallback_reply(session: dict) -> dict:
    n_q = _count_questions_asked(session)
    n_turn = sum(1 for m in session["messages"] if m["role"] == "assistant")

    if n_turn == 0:
        return {
            "assistant_message": (
                "Bonjour ! Gemini n'est pas joignable (vérifiez LLM_API_KEY dans backend/.env "
                "et GET /interview/gemini-health). Mode démo — première question technique :"
            ),
            "question_type": "mcq",
            "mcq": {
                "question": "Quelle compétence technique de l'offre est la plus critique pour ce rôle ?",
                "choices": [
                    "A) Uniquement la communication écrite",
                    "B) Les outils et langages explicitement mentionnés dans l'offre",
                    "C) La gestion de projet sans aspect technique",
                    "D) Aucune compétence technique requise",
                ],
            },
            "open_question": None,
            "interview_complete": False,
            "final_report": None,
        }

    if n_q >= 6:
        report = _demo_final_report(session)
        return {
            "assistant_message": (
                f"Entretien terminé. Score : {report['score_percent']}/100 — {report['score_label']}. "
                f"{report['overall_advice']}"
            ),
            "question_type": None,
            "mcq": None,
            "open_question": None,
            "interview_complete": True,
            "final_report": report,
        }

    use_open = n_q % 2 == 1
    if use_open:
        return {
            "assistant_message": "Merci. Voici une question ouverte pour approfondir :",
            "question_type": "open",
            "mcq": None,
            "open_question": (
                "Décrivez concrètement comment vous utiliseriez une compétence clé de l'offre "
                "dans votre premier mois sur ce poste."
            ),
            "interview_complete": False,
            "final_report": None,
        }

    return {
        "assistant_message": "Bien noté. Question suivante (choix multiple) :",
        "question_type": "mcq",
        "mcq": {
            "question": f"Question {n_q + 1} : face à une exigence technique de l'offre, quelle approche adoptez-vous ?",
            "choices": [
                "A) J'ignore la contrainte et j'improvise",
                "B) J'analyse le besoin, je m'appuie sur la doc et je teste",
                "C) Je délègue sans comprendre le sujet",
                "D) Je refuse toute tâche technique",
            ],
        },
        "open_question": None,
        "interview_complete": False,
        "final_report": None,
    }


def _turn_to_model_json(turn: dict) -> str:
    return json.dumps(turn, ensure_ascii=False)


def _history_from_session(session: dict) -> list[ChatMessage]:
    out: list[ChatMessage] = []
    for m in session["messages"]:
        if m["role"] != "assistant":
            out.append(ChatMessage(role="user", content=m["content"]))
            continue
        mcq = McqQuestion(**m["mcq"]) if m.get("mcq") else None
        report = (
            InterviewFinalReport(**m["final_report"]) if m.get("final_report") else None
        )
        out.append(
            ChatMessage(
                role="assistant",
                content=m["content"],
                question_type=m.get("question_type"),
                mcq=mcq,
                open_question=m.get("open_question"),
                final_report=report,
            )
        )
    return out


def _response_from_turn(session_id: str, session: dict, turn: dict) -> InterviewChatResponse:
    report_model = None
    if turn.get("final_report"):
        fr = turn["final_report"]
        report_model = InterviewFinalReport(
            score_percent=fr["score_percent"],
            score_label=fr["score_label"],
            overall_advice=fr["overall_advice"],
            summary=fr["summary"],
            answers_review=[AnswerReviewItem(**a) for a in fr.get("answers_review", [])],
        )

    mcq_model = McqQuestion(**turn["mcq"]) if turn.get("mcq") else None

    return InterviewChatResponse(
        session_id=session_id,
        assistant_message=turn["assistant_message"],
        question_type=turn.get("question_type"),
        mcq=mcq_model,
        open_question=turn.get("open_question"),
        interview_complete=turn["interview_complete"],
        final_report=report_model,
        history=_history_from_session(session),
    )


async def handle_chat_message(
    user_id: int, session_id: Optional[str], message: str
) -> InterviewChatResponse:
    message = message.strip()
    if not message:
        raise ValueError("Message vide")

    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        if session["user_id"] != user_id:
            raise PermissionError("Session introuvable")
        if session.get("completed"):
            raise ValueError("Cet entretien est terminé. Démarrez une nouvelle session.")
    else:
        session_id = str(uuid.uuid4())
        session = {
            "user_id": user_id,
            "offer_text": None,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed": False,
            "gemini_model": None,
        }
        _sessions[session_id] = session

    _capture_offer_text(session, message)
    session["messages"].append({"role": "user", "content": message})

    raw = await _call_gemini_chat(session, _build_gemini_contents(session))
    turn = _parse_llm_turn(raw, session)

    assistant_entry: dict[str, Any] = {
        "role": "assistant",
        "content": turn["assistant_message"],
        "question_type": turn.get("question_type"),
        "model_turn_json": _turn_to_model_json(turn),
    }
    if turn.get("mcq"):
        assistant_entry["mcq"] = turn["mcq"]
    if turn.get("open_question"):
        assistant_entry["open_question"] = turn["open_question"]
    if turn.get("final_report"):
        assistant_entry["final_report"] = turn["final_report"]

    session["messages"].append(assistant_entry)
    if turn["interview_complete"]:
        session["completed"] = True

    return _response_from_turn(session_id, session, turn)


def get_session_for_user(session_id: str, user_id: int) -> Optional[InterviewChatResponse]:
    session = _sessions.get(session_id)
    if not session or session["user_id"] != user_id:
        return None

    last_assistant = next(
        (m for m in reversed(session["messages"]) if m["role"] == "assistant"),
        None,
    )
    if not last_assistant:
        return InterviewChatResponse(
            session_id=session_id,
            assistant_message="",
            history=_history_from_session(session),
        )

    turn = {
        "assistant_message": last_assistant["content"],
        "question_type": last_assistant.get("question_type"),
        "mcq": last_assistant.get("mcq"),
        "open_question": last_assistant.get("open_question"),
        "interview_complete": session.get("completed", False),
        "final_report": last_assistant.get("final_report"),
    }
    return _response_from_turn(session_id, session, turn)
