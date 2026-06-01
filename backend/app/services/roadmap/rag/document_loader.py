import os
import re
import csv
import logging
import hashlib

log = logging.getLogger("document_loader")

# Skills à détecter dans les descriptions (pour enrichir les chunks scraper)
_SKILLS_LIST = [
    "python", "java", "scala", "javascript", "typescript", "c++", "c#",
    "go", "rust", "bash", "sql", "r",
    "spark", "airflow", "kafka", "hadoop", "hive", "dbt",
    "pandas", "numpy", "polars", "pyspark",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "cassandra", "bigquery", "snowflake", "redshift", "dynamodb",
    "tensorflow", "pytorch", "scikit-learn", "keras", "mlflow",
    "xgboost", "lightgbm", "hugging face",
    "aws", "azure", "gcp", "s3", "ec2", "lambda",
    "kubernetes", "docker", "terraform", "ansible",
    "jenkins", "gitlab", "github", "ci/cd",
    "power bi", "tableau", "looker", "metabase",
    "fastapi", "django", "flask", "spring", "node.js",
    "react", "vue", "angular", "rest api", "graphql",
    "git", "linux", "agile", "scrum", "jira",
    "machine learning", "deep learning", "nlp", "computer vision",
    "data warehouse", "data lake", "etl",
]

# Mapping target_job_id → nom lisible (synchronisé avec JOB_PROFILES du scraper)
_TARGET_JOB_NAMES = {
    "1": "data engineer",
    "2": "data scientist",
    "3": "data analyst",
    "4": "ml engineer",
    "5": "cloud engineer",
    "6": "devops",
    "7": "backend",
    "8": "fullstack",
}



def make_doc(text: str, metadata: dict) -> dict:
    """
    Crée un document standard pour ChromaDB.
    L'ID est un hash MD5 du texte pour éviter les doublons.
    """
    doc_id = hashlib.md5(text.encode("utf-8")).hexdigest()
    return {
        "id":       doc_id,
        "text":     text.strip(),
        "metadata": metadata,
    }


def _extract_skills_inline(text: str) -> list[str]:
    """Extrait les skills mentionnés dans un texte."""
    if not text:
        return []
    text_lower = text.lower()
    return [s for s in _SKILLS_LIST if re.search(r"\b" + re.escape(s) + r"\b", text_lower)]


def _split_text(text: str, max_chars: int = 500) -> list[str]:
    """Découpe un texte long en chunks de max_chars caractères."""
    if len(text) <= max_chars:
        return [text]
    chunks   = []
    sentences = text.replace("\n", " ").split(". ")
    current  = ""
    for sentence in sentences:
        if len(current) + len(sentence) < max_chars:
            current += sentence + ". "
        else:
            if current:
                chunks.append(current.strip())
            current = sentence + ". "
    if current:
        chunks.append(current.strip())
    return chunks if chunks else [text[:max_chars]]


#Source 1 : Knowledge Base 

def load_documents_from_knowledge_base() -> list[dict]:
    """
    Transforme la knowledge_base.py en documents indexables.

    Pour chaque skill génère :
      - Un chunk "overview"  : résumé du skill (catégorie, durée, prérequis)
      - Un chunk "course"    : par ressource de formation
      - Un chunk "project"   : par projet pratique
    """
    from app.services.roadmap.knowledge_base import SKILL_KNOWLEDGE_BASE

    documents = []

    for skill_name, info in SKILL_KNOWLEDGE_BASE.items():
        category = info.get("category", "general")
        priority = info.get("priority", 2)
        weeks    = info.get("weeks", 1)
        prereqs  = info.get("prereqs", [])

        # ── Chunk overview ─────────────────────────────────────
        prereqs_str   = f"Prérequis : {', '.join(prereqs)}." if prereqs else "Aucun prérequis."
        overview_text = (
            f"Skill : {skill_name}. "
            f"Catégorie : {category}. "
            f"Durée d'apprentissage estimée : {weeks} semaine(s). "
            f"Priorité : {priority} (1=critique, 3=utile). "
            f"{prereqs_str}"
        )
        documents.append(make_doc(
            text     = overview_text,
            metadata = {
                "source":   "knowledge_base",
                "type":     "overview",
                "skill":    skill_name,
                "category": category,
                "weeks":    str(weeks),
                "priority": str(priority),
            }
        ))

        # ── Chunks cours ───────────────────────────────────────
        for course in info.get("courses", []):
            course_text = (
                f"Formation {skill_name} : {course['title']}. "
                f"Plateforme : {course['platform']}. "
                f"Durée : {course['duration']}. "
                f"URL : {course['url']}. "
                f"Ce cours couvre les fondamentaux de {skill_name} "
                f"dans le domaine {category}."
            )
            documents.append(make_doc(
                text     = course_text,
                metadata = {
                    "source":   "knowledge_base",
                    "type":     "course",
                    "skill":    skill_name,
                    "category": category,
                    "platform": course["platform"],
                    "url":      course["url"],
                    "title":    course["title"],
                }
            ))

        # ── Chunks projets ─────────────────────────────────────
        for project in info.get("projects", []):
            project_text = (
                f"Projet pratique {skill_name} : {project['title']}. "
                f"Description : {project['description']}. "
                f"Niveau : {project['difficulty']}. "
                f"Ce projet permet de pratiquer {skill_name} concrètement."
            )
            documents.append(make_doc(
                text     = project_text,
                metadata = {
                    "source":     "knowledge_base",
                    "type":       "project",
                    "skill":      skill_name,
                    "category":   category,
                    "difficulty": project["difficulty"],
                    "title":      project["title"],
                }
            ))

    log.info(f"Knowledge Base : {len(documents)} chunks depuis {len(SKILL_KNOWLEDGE_BASE)} skills")
    return documents


# ─── Source 2 : CSV Scraper (offres_finales.csv) ──────────────────────────────

def load_documents_from_csv(csv_paths: list[str]) -> list[dict]:
    documents    = []
    total_offers = 0

    for csv_path in csv_paths:
        if not os.path.exists(csv_path):
            log.warning(f"CSV introuvable : {csv_path}")
            continue

        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # ── Lecture colonnes exactes offres_finales.csv ──
                    title         = (row.get("title",         "") or "").strip()
                    company       = (row.get("company",        "") or "").strip()
                    description   = (row.get("description",    "") or "").strip()
                    offer_source  = (row.get("offer_source",   "") or "").strip()
                    target_job_id = (row.get("target_job_id",  "") or "").strip()
                    url           = (row.get("url",            "") or "").strip()
                    scraped_at    = (row.get("scraped_at",     "") or "").strip()

                    # Fallback sur raw_text si description vide
                    if not description:
                        description = (row.get("raw_text", "") or "").strip()

                    if not title:
                        continue

                    # Résoudre le nom du poste depuis target_job_id
                    job_name = _TARGET_JOB_NAMES.get(target_job_id, f"poste_{target_job_id}")

                    # Extraire les skills depuis la description
                    skills_list  = _extract_skills_inline(description)
                    skills_clean = ", ".join(skills_list) if skills_list else "non spécifiés"

                    # ── Chunk résumé de l'offre ────────────────────
                    summary_text = (
                        f"Offre de stage : {title} chez {company}. "
                        f"Domaine : {job_name}. "
                        f"Skills requis : {skills_clean}. "
                        f"Source : {offer_source}. "
                        f"Date : {scraped_at[:10] if scraped_at else ''}."
                    )
                    documents.append(make_doc(
                        text     = summary_text,
                        metadata = {
                            "source":         "scraper",
                            "type":           "offer_summary",
                            "title":          title,
                            "company":        company,
                            "location":       "",
                            "job_category":   job_name,
                            "skills":         skills_clean,
                            "posted_date":    scraped_at[:10] if scraped_at else "",
                            "target_job_id":  target_job_id,
                            "offer_source":   offer_source,
                        }
                    ))

                    # ── Chunks description complète ───────────────
                    if description and len(description) > 100:
                        chunks = _split_text(description, max_chars=500)
                        for i, chunk in enumerate(chunks):
                            chunk_text = (
                                f"Description offre {title} ({company}) "
                                f"[partie {i+1}/{len(chunks)}] : {chunk}"
                            )
                            documents.append(make_doc(
                                text     = chunk_text,
                                metadata = {
                                    "source":         "scraper",
                                    "type":           "offer_description",
                                    "title":          title,
                                    "company":        company,
                                    "job_category":   job_name,
                                    "target_job_id":  target_job_id,
                                    "chunk_index":    str(i),
                                }
                            ))

                    total_offers += 1

            log.info(f"CSV '{os.path.basename(csv_path)}' : {total_offers} offres chargées")

        except Exception as e:
            log.error(f"Erreur lecture CSV {csv_path} : {e}")

    log.info(f"Scraper CSV : {len(documents)} chunks depuis {total_offers} offres")
    return documents


# ─── Chargement global ────────────────────────────────────────────────────────

def load_all_documents(csv_dir: str = None) -> list[dict]:
    all_docs = []

    # Source 1 : Knowledge Base
    log.info("Chargement Knowledge Base...")
    kb_docs = load_documents_from_knowledge_base()
    all_docs.extend(kb_docs)

    # Source 2 : CSV scraper
    if csv_dir is None:
        candidates = [
            "data/scraper/scraped_data",
            "../data/scraper/scraped_data",
            "../../data/scraper/scraped_data",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "scraper", "scraped_data"),
        ]
        for path in candidates:
            if os.path.exists(path):
                csv_dir = path
                break

    if csv_dir and os.path.exists(csv_dir):
        # Priorité à offres_finales.csv, puis les autres
        all_csv = os.listdir(csv_dir)
        priority_files = [f for f in all_csv if f == "offres_finales.csv"]
        other_files    = [f for f in all_csv if f.endswith(".csv") and f != "offres_finales.csv"]
        ordered_files  = priority_files + other_files

        csv_files = [os.path.join(csv_dir, f) for f in ordered_files]

        if csv_files:
            log.info(f"Chargement {len(csv_files)} CSV depuis {csv_dir}...")
            csv_docs = load_documents_from_csv(csv_files)
            all_docs.extend(csv_docs)
        else:
            log.info(f"Aucun CSV dans {csv_dir} — Knowledge Base uniquement")
    else:
        log.info("Dossier CSV non trouvé — Knowledge Base uniquement")

    # Déduplication par ID 
    seen, unique = set(), []
    for doc in all_docs:
        if doc["id"] not in seen:
            seen.add(doc["id"])
            unique.append(doc)

    removed = len(all_docs) - len(unique)
    if removed:
        log.info(f"Déduplication : {removed} doublons supprimés")

    log.info(f"Total documents indexables : {len(unique)}")
    return unique