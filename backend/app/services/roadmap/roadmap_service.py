import logging
from typing import Optional

from app.config import settings

log = logging.getLogger("roadmap_service")


async def generate_roadmap(
    missing_skills:  list[str],
    acquired_skills: list[str]       = None,
    duration_weeks:  int             = 8,
    user_level:      str             = "débutant",
    job_name:        str             = "",
    use_rag:         bool            = True,
    use_llm:         bool            = True,
) -> dict:

    acquired_skills = acquired_skills or []

    log.info("=" * 55)
    log.info(f"PIPELINE ROADMAP : '{job_name}'")
    log.info(f"Skills manquants : {missing_skills}")
    log.info(f"Niveau : {user_level} | Durée : {duration_weeks} semaines")
    log.info("=" * 55)

    
    # ÉTAPE 1 : RULE-BASED ENGINE
    # Génère le squelette déterministe
    
    log.info("ÉTAPE 1 → Rule-Based Engine...")

    from app.services.roadmap.rule_based_engine import generate_roadmap_rule_based

    roadmap = generate_roadmap_rule_based(
        missing_skills  = missing_skills,
        acquired_skills = acquired_skills,
        duration_weeks  = duration_weeks,
        user_level      = user_level,
        job_name        = job_name,
    )
    roadmap["user_level"] = user_level

    log.info(
        f"  ✓ Squelette généré : {len(roadmap['steps'])} steps | "
        f"Skills : {roadmap['skills_order']}"
    )

    if not roadmap["steps"]:
        log.warning("  Aucun step généré — pipeline arrêté")
        roadmap["engine"] = "rule_based"
        return roadmap

    # ÉTAPE 2 : RAG — Retrieval
    # Récupère le contexte réel depuis ChromaDB
   
    rag_context = None

    if use_rag:
        log.info("ÉTAPE 2 → RAG Retrieval...")
        try:
            from app.services.roadmap.rag.vector_store import is_indexed
            from app.services.roadmap.rag.retriever    import retrieve_for_roadmap

            if not is_indexed():
                log.warning("  ChromaDB non indexé — initialisation automatique...")
                from app.services.roadmap.rag.vector_store import initialize_vector_store
                initialize_vector_store()

            rag_context = retrieve_for_roadmap(
                skills_order = roadmap["skills_order"],
                job_name     = job_name,
                user_level   = user_level,
                n_per_skill  = 3,
            )

            
            total_chunks = sum(
                len(v.get("courses", [])) + len(v.get("projects", [])) + len(v.get("market", []))
                for k, v in rag_context.items()
                if k != "global_context" and isinstance(v, dict)
            )
            log.info(f"  ✓ RAG : {total_chunks} chunks récupérés pour {len(roadmap['skills_order'])} skills")

        except Exception as e:
            log.warning(f"  RAG échoué ({e}) — pipeline continue sans RAG")
            rag_context = None
    else:
        log.info("ÉTAPE 2 → RAG désactivé (use_rag=False)")

    
    # ÉTAPE 3 : LLM — Gemini Flash
    # Enrichit le texte avec le contexte RAG
   
    llm_configured = bool(
        settings.LLM_API_KEY
        and settings.LLM_API_KEY not in ("", "dummy", "your-key")
    )

    if use_llm and llm_configured:
        log.info("ÉTAPE 3 → Gemini Flash enrichissement...")
        try:
            from app.services.roadmap.gemini_engine import enrich_roadmap_with_gemini

            roadmap = await enrich_roadmap_with_gemini(
                roadmap     = roadmap,
                rag_context = rag_context,
            )
            log.info(f"  ✓ Enrichissement terminé — moteur : {roadmap['engine']}")

        except Exception as e:
            log.warning(f"  Gemini échoué ({e}) — roadmap rule-based retournée")
            roadmap["engine"] = "rule_based+rag" if rag_context else "rule_based"
    else:
        if use_llm and not llm_configured:
            log.info("ÉTAPE 3 → Gemini ignoré (LLM_API_KEY non configurée)")
        else:
            log.info("ÉTAPE 3 → LLM désactivé (use_llm=False)")

        roadmap["engine"] = "rule_based+rag" if rag_context else "rule_based"

    
    # RÉSUMÉ FINAL
   
    log.info("─" * 55)
    log.info(f"PIPELINE TERMINÉ")
    log.info(f"  Moteur final    : {roadmap['engine']}")
    log.info(f"  Steps générés   : {len(roadmap['steps'])}")
    log.info(f"  Cours           : {roadmap['summary']['courses_count']}")
    log.info(f"  Projets         : {roadmap['summary']['projects_count']}")
    log.info(f"  Semaines        : {roadmap['summary']['weeks_used']}")
    log.info("─" * 55)

    return roadmap


def generate_roadmap_sync(
    missing_skills:  list[str],
    acquired_skills: list[str] = None,
    duration_weeks:  int       = 8,
    user_level:      str       = "débutant",
    job_name:        str       = "",
) -> dict:
    from app.services.roadmap.rule_based_engine import generate_roadmap_rule_based

    return generate_roadmap_rule_based(
        missing_skills  = missing_skills,
        acquired_skills = acquired_skills,
        duration_weeks  = duration_weeks,
        user_level      = user_level,
        job_name        = job_name,
    )