import logging
from typing import Optional

from app.services.roadmap.rag.vector_store import search

log = logging.getLogger("retriever")


# ─── Retrieval par skill ──────────────────────────────────────────────────────

def retrieve_for_skill(
    skill:      str,
    job_name:   str  = "",
    user_level: str  = "débutant",
    n_results:  int  = 4,
) -> dict:
    result = {
        "skill":        skill,
        "courses":      [],
        "projects":     [],
        "market":       [],
        "context_text": "",
    }

    # ── Requête 1 : Cours pour ce skill ──────────────────────────
    course_query = f"{skill} {job_name} formation cours tutoriel apprentissage {user_level}"
    course_hits  = search(
        query     = course_query,
        n_results = n_results,
        filter_by = {"type": "course"},
    )
    for hit in course_hits:
        if hit["relevance"] >= 0.3:   # Seuil de pertinence minimum
            result["courses"].append({
                "text":      hit["text"],
                "url":       hit["metadata"].get("url", ""),
                "platform":  hit["metadata"].get("platform", ""),
                "title":     hit["metadata"].get("title", ""),
                "relevance": hit["relevance"],
            })

    # ── Requête 2 : Projets pratiques ────────────────────────────
    project_query = f"{skill} projet pratique hands-on {job_name}"
    project_hits  = search(
        query     = project_query,
        n_results = n_results,
        filter_by = {"type": "project"},
    )
    for hit in project_hits:
        if hit["relevance"] >= 0.3:
            result["projects"].append({
                "text":       hit["text"],
                "title":      hit["metadata"].get("title", ""),
                "difficulty": hit["metadata"].get("difficulty", ""),
                "relevance":  hit["relevance"],
            })

    # ── Requête 3 : Offres du marché ──────────────────────────────
    market_query = f"{skill} {job_name} offre stage requis demandé entreprise"
    market_hits  = search(
        query     = market_query,
        n_results = n_results,
        filter_by = {"source": "scraper"},
    )
    for hit in market_hits:
        if hit["relevance"] >= 0.25:   # Seuil plus bas pour les offres
            result["market"].append({
                "text":     hit["text"],
                "company":  hit["metadata"].get("company", ""),
                "title":    hit["metadata"].get("title", ""),
                "skills":   hit["metadata"].get("skills", ""),
                "relevance": hit["relevance"],
            })

    # ── Construire le context_text pour le prompt LLM ─────────────
    result["context_text"] = _build_context_text(skill, result)

    log.debug(
        f"RAG [{skill}] : {len(result['courses'])} cours, "
        f"{len(result['projects'])} projets, "
        f"{len(result['market'])} offres marché"
    )

    return result


def _build_context_text(skill: str, retrieval: dict) -> str:
    parts = [f"=== Contexte pour le skill : {skill.upper()} ===\n"]

    if retrieval["courses"]:
        parts.append(" RESSOURCES DE FORMATION :")
        for i, c in enumerate(retrieval["courses"][:2], 1):  # Max 2 cours
            parts.append(f"  [{i}] {c['text']}")
        parts.append("")

    if retrieval["projects"]:
        parts.append(" PROJETS PRATIQUES :")
        for i, p in enumerate(retrieval["projects"][:2], 1):  # Max 2 projets
            parts.append(f"  [{i}] {p['text']}")
        parts.append("")

    if retrieval["market"]:
        parts.append(" DONNÉES MARCHÉ (offres réelles) :")
        for i, m in enumerate(retrieval["market"][:2], 1):   # Max 2 offres
            parts.append(f"  [{i}] {m['text']}")
        parts.append("")

    if not retrieval["courses"] and not retrieval["projects"] and not retrieval["market"]:
        parts.append(f"Aucun contexte spécifique trouvé pour {skill}.")
        parts.append(f"Se baser sur les connaissances générales pour ce skill.")

    return "\n".join(parts)


# ─── Retrieval pour une roadmap complète ─────────────────────────────────────

def retrieve_for_roadmap(
    skills_order: list[str],
    job_name:     str = "",
    user_level:   str = "débutant",
    n_per_skill:  int = 3,
) -> dict:
    if not skills_order:
        return {"global_context": ""}

    all_retrievals = {}
    global_parts   = []

    log.info(f"RAG : récupération contexte pour {len(skills_order)} skills...")

    for skill in skills_order:
        retrieval = retrieve_for_skill(
            skill      = skill,
            job_name   = job_name,
            user_level = user_level,
            n_results  = n_per_skill,
        )
        all_retrievals[skill]  = retrieval
        global_parts.append(retrieval["context_text"])

    # Contexte global = tous les skills concaténés
    all_retrievals["global_context"] = "\n\n".join(global_parts)

    total_courses  = sum(len(r["courses"])  for k, r in all_retrievals.items() if k != "global_context")
    total_projects = sum(len(r["projects"]) for k, r in all_retrievals.items() if k != "global_context")
    total_market   = sum(len(r["market"])   for k, r in all_retrievals.items() if k != "global_context")

    log.info(
        f"RAG terminé : {total_courses} cours, "
        f"{total_projects} projets, "
        f"{total_market} offres marché récupérés"
    )

    return all_retrievals


# ─── Recherche libre ──────────────────────────────────────────────────────────

def search_knowledge(
    query:     str,
    n_results: int           = 5,
    doc_type:  Optional[str] = None,
) -> list[dict]:
    filter_by = {"type": doc_type} if doc_type else None

    hits = search(query=query, n_results=n_results, filter_by=filter_by)

    return [
        {
            "text":      hit["text"],
            "type":      hit["metadata"].get("type", ""),
            "skill":     hit["metadata"].get("skill", ""),
            "source":    hit["metadata"].get("source", ""),
            "relevance": hit["relevance"],
            "metadata":  hit["metadata"],
        }
        for hit in hits
    ]