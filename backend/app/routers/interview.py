import logging
import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models as db_models
from app.models.skill import InterviewRequest, InterviewSessionResponse, InterviewQuestion
from app.routers.auth import get_current_user
from app.config import settings

log    = logging.getLogger("router.interview")
router = APIRouter()

# ── Questions de secours si LLM indisponible ──────────────────────────────────
_FALLBACK_QUESTIONS: dict[str, list[str]] = {
    "data engineer": [
        "Expliquez la différence entre un pipeline batch et un pipeline streaming.",
        "Comment gérez-vous la qualité des données dans un pipeline ETL ?",
        "Quelle est la différence entre OLTP et OLAP ? Donnez un exemple concret.",
        "Comment optimiser une requête SQL qui tourne sur plusieurs millions de lignes ?",
        "Décrivez l'architecture d'un data lakehouse moderne.",
    ],
    "data analyst": [
        "Comment détectez-vous et traitez-vous les valeurs aberrantes dans un dataset ?",
        "Quelle est la différence entre une jointure LEFT JOIN et INNER JOIN ?",
        "Comment présenteriez-vous une analyse complexe à un public non technique ?",
        "Expliquez le concept de normalisation de données.",
        "Comment construiriez-vous un tableau de bord pour suivre les KPIs d'une équipe ?",
    ],
    "data scientist": [
        "Quelle est la différence entre overfitting et underfitting ?",
        "Comment choisissez-vous entre régression et classification ?",
        "Expliquez le fonctionnement d'un Random Forest.",
        "Comment gérez-vous un dataset déséquilibré (imbalanced classes) ?",
        "Quelle métrique utilisez-vous pour évaluer un modèle de recommandation ?",
    ],
    "ml engineer": [
        "Comment mettez-vous un modèle ML en production ?",
        "Qu'est-ce que le model drift et comment le détectez-vous ?",
        "Expliquez la différence entre serving online et offline.",
        "Comment optimisez-vous la latence d'inférence d'un modèle ?",
        "Qu'est-ce qu'un feature store et pourquoi est-il utile ?",
    ],
    "backend developer": [
        "Quelle est la différence entre REST et GraphQL ?",
        "Comment gérez-vous l'authentification et les tokens JWT ?",
        "Expliquez les principes SOLID avec un exemple.",
        "Comment optimisez-vous les performances d'une API FastAPI ?",
        "Quelle est la différence entre une architecture monolithique et microservices ?",
    ],
    "devops": [
        "Expliquez le principe du CI/CD avec un exemple concret.",
        "Quelle est la différence entre Docker et une VM ?",
        "Comment gérez-vous les secrets dans un pipeline Kubernetes ?",
        "Qu'est-ce que l'infrastructure as code ? Citez un outil.",
        "Comment orchestrez-vous le déploiement de plusieurs microservices ?",
    ],
    "cloud engineer": [
        "Quelle est la différence entre IaaS, PaaS et SaaS ?",
        "Comment gérez-vous la haute disponibilité sur AWS/GCP ?",
        "Expliquez le concept de VPC et pourquoi c'est important.",
        "Comment optimisez-vous les coûts cloud sur un compte actif ?",
        "Qu'est-ce que Terraform et comment gère-t-il l'état ?",
    ],
    "fullstack": [
        "Quelle est la différence entre SSR et CSR dans React ?",
        "Comment sécurisez-vous une API REST exposée publiquement ?",
        "Expliquez le fonctionnement du virtual DOM.",
        "Comment gérez-vous la gestion d'état dans une grande application React ?",
        "Quelle est votre approche pour optimiser les performances d'une webapp ?",
    ],
}

_DEFAULT_QUESTIONS = [
    "Décrivez votre expérience la plus marquante dans votre domaine.",
    "Comment gérez-vous les situations de stress et les deadlines serrées ?",
    "Quelle est votre approche pour apprendre une nouvelle technologie rapidement ?",
    "Décrivez un projet difficile et comment vous l'avez mené à bien.",
    "Pourquoi ce poste vous intéresse-t-il ?",
]


async def _generate_questions_with_llm(
    job_name: str,
    num_questions: int,
    skill_names: list[str],
) -> list[str] | None:
    """Appelle Gemini pour générer des questions techniques. Retourne None si échec."""
    if not settings.LLM_API_KEY or settings.LLM_API_KEY in ("", "your-key", "dummy"):
        return None

    prompt = (
        f"Tu es un interviewer technique senior pour le poste de {job_name}. "
        f"Le candidat maîtrise : {', '.join(skill_names[:10]) if skill_names else 'compétences générales'}.\n\n"
        f"Génère exactement {num_questions} questions d'entretien technique pertinentes. "
        f"Chaque question doit être précise, challengeante et adaptée au niveau intermédiaire. "
        f"Réponds UNIQUEMENT avec une liste numérotée, une question par ligne, sans explication."
    )

    try:
        url = (
            f"{settings.LLM_BASE_URL}/models/{settings.LLM_MODEL}"
            f":generateContent?key={settings.LLM_API_KEY}"
        )
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            resp.raise_for_status()
            data = resp.json()

        raw_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        if not raw_text:
            return None

        questions = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Nettoyer les numéros (1. 2. 1) etc.)
            import re
            cleaned = re.sub(r"^[\d]+[.)]\s*", "", line).strip()
            if cleaned:
                questions.append(cleaned)

        return questions[:num_questions] if questions else None

    except Exception as e:
        log.warning(f"LLM échoué pour questions interview : {e}")
        return None


def _get_fallback_questions(job_name: str, num_questions: int) -> list[str]:
    """Retourne des questions prédéfinies selon le métier."""
    key = job_name.lower().strip()
    questions = _FALLBACK_QUESTIONS.get(key, _DEFAULT_QUESTIONS)
    # Retourner les N premières, ou toutes si moins de N disponibles
    return questions[:num_questions]


# ── POST /interview/start ──────────────────────────────────────────────────────

@router.post("/start", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_interview(
    request:      InterviewRequest,
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """
    Lance une nouvelle session d'entretien simulé.
    - Génère N questions techniques via Gemini LLM (fallback si indisponible)
    - Sauvegarde la session et les questions en BDD
    """
    # Vérifier l'UserTargetJob
    utj = db.query(db_models.UserTargetJob).filter(
        db_models.UserTargetJob.id      == request.user_target_job_id,
        db_models.UserTargetJob.user_id == current_user.id,
    ).first()
    if not utj:
        raise HTTPException(status_code=404, detail="UserTargetJob introuvable")

    job_name = utj.target_job.name if utj.target_job else "Poste cible"
    num_q    = max(1, min(request.num_questions or 5, 15))  # Entre 1 et 15

    # Récupérer les skills maîtrisés pour personnaliser les questions
    cv = db.query(db_models.CV).filter(
        db_models.CV.user_id == current_user.id
    ).order_by(db_models.CV.uploaded_at.desc()).first()

    skill_names = []
    if cv:
        skill_names = [
            cs.skill.name for cs in
            db.query(db_models.CVSkill).filter(db_models.CVSkill.cv_id == cv.id).all()
            if cs.skill
        ]

    # Créer la session
    session = db_models.InterviewSession(
        user_target_job_id = utj.id,
        offer_id           = request.offer_id,
    )
    db.add(session)
    db.flush()

    # Générer les questions (LLM d'abord, fallback ensuite)
    question_texts = await _generate_questions_with_llm(job_name, num_q, skill_names)
    if not question_texts:
        question_texts = _get_fallback_questions(job_name, num_q)
        log.info(f"Session {session.id} → fallback questions ({job_name})")
    else:
        log.info(f"Session {session.id} → LLM questions ({len(question_texts)} générées)")

    # Sauvegarder les questions en BDD
    saved_questions = []
    for q_text in question_texts:
        q = db_models.InterviewQuestion(
            session_id    = session.id,
            question_text = q_text,
        )
        db.add(q)
        db.flush()
        saved_questions.append(InterviewQuestion(
            question_text = q.question_text,
            related_skill = None,
        ))

    db.commit()
    db.refresh(session)

    log.info(
        f"Interview session {session.id} créée — "
        f"user={current_user.id} | job={job_name} | {len(saved_questions)} questions"
    )

    return InterviewSessionResponse(
        session_id = session.id,
        questions  = saved_questions,
        created_at = session.created_at,
    )


# ── GET /interview/sessions ────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[InterviewSessionResponse])
def list_sessions(
    current_user: db_models.User = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    """Liste toutes les sessions d'entretien de l'utilisateur."""
    utj_ids = [
        r.id for r in db.query(db_models.UserTargetJob.id).filter(
            db_models.UserTargetJob.user_id == current_user.id
        ).all()
    ]

    sessions = db.query(db_models.InterviewSession).filter(
        db_models.InterviewSession.user_target_job_id.in_(utj_ids)
    ).order_by(db_models.InterviewSession.created_at.desc()).all()

    results = []
    for session in sessions:
        questions = [
            InterviewQuestion(
                question_text = q.question_text,
                related_skill = q.related_skill.name if q.related_skill else None,
            )
            for q in session.questions
        ]
        results.append(InterviewSessionResponse(
            session_id = session.id,
            questions  = questions,
            created_at = session.created_at,
        ))

    return results