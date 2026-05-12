import json
import logging
import httpx
from typing import Optional

from app.config import settings

log = logging.getLogger("gemini_engine")


# ─── Prompts ──────────────────────────────────────────────────────────────────

ENRICHMENT_SYSTEM_PROMPT = """Tu es un expert en orientation de carrière tech.
Tu reçois une roadmap structurée + du contexte réel issu d'une base de connaissances
et d'offres de stages scrapées. Tu dois enrichir la roadmap avec ce contexte.
Réponds UNIQUEMENT en JSON valide, sans texte avant ou après, sans balises markdown.
"""

ENRICHMENT_USER_TEMPLATE = """
Tu dois enrichir une roadmap d'apprentissage pour un étudiant.

POSTE CIBLE   : {job_name}
NIVEAU        : {user_level}
DURÉE         : {duration_weeks} semaines
SKILLS (ordre): {skills_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE RÉEL RÉCUPÉRÉ PAR LE SYSTÈME RAG
(issu de la base de connaissances + offres marché scrapées)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROADMAP STRUCTURÉE À ENRICHIR :
{current_steps_json}

INSTRUCTIONS :
- Utilise le contexte RAG pour enrichir les descriptions avec des données réelles
- Mentionne les ressources concrètes issues du contexte quand pertinent
- Adapte le ton et la complexité au niveau : {user_level}
- NE PAS changer week_number, skill_name, type, source
- NE PAS ajouter ou supprimer des steps

Retourne EXACTEMENT ce JSON :
{{
  "intro": "2-3 phrases motivantes présentant le parcours {job_name}, ancré dans les données marché réelles",
  "market_insight": "1 phrase sur ce que les vraies offres demandent pour {job_name}",
  "enriched_steps": [
    {{
      "week_number": <reprendre tel quel>,
      "title": <améliorer si trop générique, sinon garder>,
      "description": <enrichir avec contexte RAG : importance du skill, données marché, ressource concrète>,
      "tip": <conseil pratique 1 phrase basé sur les vraies offres marché>
    }}
  ]
}}
"""


# ─── Client Gemini ────────────────────────────────────────────────────────────

async def _call_gemini(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    Appelle Gemini Flash et retourne le texte brut.
    Retourne None si échec → fallback propre.
    """
    if not settings.LLM_API_KEY or settings.LLM_API_KEY in ("", "dummy", "your-key"):
        log.info("Gemini : LLM_API_KEY absente — enrichissement ignoré")
        return None

    _base  = settings.LLM_BASE_URL.rstrip("/")
    _model = settings.LLM_MODEL.strip()
    url    = f"{_base}/models/{_model}:generateContent?key={settings.LLM_API_KEY}"
    log.info(f"Gemini URL : {_base}/models/{_model}:generateContent?key=***")

    # Réduire le contexte RAG pour rester dans les limites de tokens
    # Prompt total estimé : ~3000 tokens input, on veut ~4000 tokens output max
    _rag_limit   = 2000   # chars max du contexte RAG injecté
    _steps_limit = 3000   # chars max du JSON steps injecté

    # Tronquer le prompt si trop long
    if len(user_prompt) > 8000:
        user_prompt = user_prompt[:8000] + "\n...[contexte tronqué pour respecter les limites]"

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents":           [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature":      0.3,
            "maxOutputTokens":  8192,   
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    except httpx.TimeoutException:
        log.warning("Gemini : timeout (30s) — fallback rule-based")
        return None
    except httpx.HTTPStatusError as e:
        log.warning(f"Gemini : HTTP {e.response.status_code} — fallback rule-based")
        log.warning(f"Gemini : URL utilisée = {url.split('?')[0]}")
        if e.response.status_code == 404:
            log.warning("Gemini 404 : vérifier LLM_MODEL dans .env (ex: gemini-1.5-flash)")
        elif e.response.status_code == 403:
            log.warning("Gemini 403 : clé API invalide ou expirée")
        return None
    except Exception as e:
        log.warning(f"Gemini : erreur ({e}) — fallback rule-based")
        return None


def _safe_parse_json(text: str) -> Optional[dict]:
    if not text:
        return None

    text = text.strip()

    # Supprimer les balises markdown
    if text.startswith("```"):
        lines = text.split("\n")
        text  = "\n".join(lines[1:-1]).strip()

    # Tentative 1 : parse direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tentative 2 : JSON tronqué → couper au dernier step complet
    log.warning("Gemini : JSON potentiellement tronqué — tentative de réparation...")
    try:
        repaired = text
        last_complete = repaired.rfind("},")
        if last_complete > 0:
            repaired = repaired[:last_complete + 1]
            open_b  = repaired.count("{")
            close_b = repaired.count("}")
            open_br  = repaired.count("[")
            close_br = repaired.count("]")
            repaired = repaired.rstrip(",")
            repaired += "]" * (open_br - close_br)
            repaired += "}" * (open_b  - close_b)

        result = json.loads(repaired)
        log.info("Gemini : JSON réparé avec succès")
        return result
    except json.JSONDecodeError as e:
        log.warning(f"Gemini : JSON invalide même après réparation ({e})")
        log.debug(f"Gemini raw preview : {text[:300]}")
        return None


# Enrichissement avec contexte RAG 

async def enrich_roadmap_with_gemini(
    roadmap:      dict,
    rag_context:  dict = None,
) -> dict:
    """
    Enrichit une roadmap rule-based avec Gemini en utilisant le contexte RAG.

    Args:
        roadmap     : Dict généré par rule_based_engine
        rag_context : Dict généré par retriever.retrieve_for_roadmap()
                      Si None → Gemini travaille sans contexte RAG

    Returns:
        Roadmap enrichie. Le champ "engine" indique ce qui a été utilisé :
          "rule_based+rag+gemini"  → pipeline complet
          "rule_based+gemini"      → sans RAG
          "rule_based"             → Gemini a échoué
    """
    if not roadmap.get("steps"):
        return roadmap

    job_name       = roadmap.get("job_name", "Poste tech")
    user_level     = roadmap.get("user_level", "débutant")
    duration_weeks = roadmap.get("duration_weeks", 8)
    skills_list    = ", ".join(roadmap.get("skills_order", []))

    # Préparer le contexte RAG pour le prompt
    if rag_context and "global_context" in rag_context:
        rag_text    = rag_context["global_context"]
        engine_tag  = "rule_based+rag+gemini"
        log.info("Gemini : enrichissement avec contexte RAG activé")
    else:
        rag_text    = "Contexte RAG non disponible — se baser sur les connaissances générales."
        engine_tag  = "rule_based+gemini"
        log.info("Gemini : enrichissement sans contexte RAG")

    # Préparer les steps pour le prompt — version minimale pour limiter les tokens
    steps_for_prompt = [
        {
            "week_number": s["week_number"],
            "skill_name":  s["skill_name"],
            "type":        s["type"],
            "title":       s["title"][:80],   
        }
        for s in roadmap["steps"]
    ]

    rag_text_limited   = rag_text[:1500] if rag_text else ""
    steps_json_compact = json.dumps(steps_for_prompt, ensure_ascii=False)

    log.info(f"Gemini : prompt estimé ~{len(rag_text_limited) + len(steps_json_compact)} chars")

    user_prompt = ENRICHMENT_USER_TEMPLATE.format(
        job_name           = job_name,
        user_level         = user_level,
        duration_weeks     = duration_weeks,
        skills_list        = skills_list,
        rag_context        = rag_text_limited,
        current_steps_json = steps_json_compact,
    )

    log.info("Gemini : appel API en cours...")
    raw = await _call_gemini(ENRICHMENT_SYSTEM_PROMPT, user_prompt)

    if not raw:
        roadmap["engine"] = "rule_based"
        return roadmap

    parsed = _safe_parse_json(raw)
    if not parsed:
        log.warning("Gemini : réponse non parseable — rule-based retourné")
        roadmap["engine"] = "rule_based"
        return roadmap

    enriched_steps = parsed.get("enriched_steps", [])

    if not enriched_steps or len(enriched_steps) != len(roadmap["steps"]):
        log.warning(
            f"Gemini : nombre de steps incorrect "
            f"(attendu {len(roadmap['steps'])}, reçu {len(enriched_steps)}) "
            f"— rule-based retourné"
        )
        roadmap["engine"] = "rule_based"
        return roadmap

    # Fusionner l'enrichissement sur les steps existants
    # On garde toutes les données rule-based et on enrichit le texte
    for original, enriched in zip(roadmap["steps"], enriched_steps):
        if enriched.get("title") and len(enriched["title"]) > 5:
            original["title"] = enriched["title"]
        if enriched.get("description"):
            original["description"] = enriched["description"]
        if enriched.get("tip"):
            original["tip"] = enriched["tip"]

    # Ajouter les métadonnées de la réponse Gemini
    if parsed.get("intro"):
        roadmap["intro"] = parsed["intro"]
    if parsed.get("market_insight"):
        roadmap["market_insight"] = parsed["market_insight"]

    # Ajouter les sources RAG utilisées pour la transparence
    if rag_context:
        rag_sources = []
        for skill, data in rag_context.items():
            if skill == "global_context" or not isinstance(data, dict):
                continue
            for course in data.get("courses", [])[:1]:
                if course.get("url"):
                    rag_sources.append({
                        "skill":    skill,
                        "type":     "course",
                        "title":    course.get("title", ""),
                        "url":      course["url"],
                        "platform": course.get("platform", ""),
                    })
        if rag_sources:
            roadmap["rag_sources"] = rag_sources

    roadmap["engine"] = engine_tag
    log.info(f"Gemini : enrichissement terminé — moteur final : {engine_tag}")
    return roadmap