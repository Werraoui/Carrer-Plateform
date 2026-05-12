import os
import re
import csv
import time
import random
import logging
import argparse
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from dotenv import load_dotenv
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_FILE   = os.path.join(_SCRIPT_DIR, ".env")

if not os.path.exists(_ENV_FILE):
    _ENV_FILE = os.path.join(_SCRIPT_DIR, "..", ".env")
if not os.path.exists(_ENV_FILE):
    _ENV_FILE = os.path.join(_SCRIPT_DIR, "..", "..", ".env")

load_dotenv(_ENV_FILE)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")


JOB_PROFILES = {
    "data engineer": {
        "target_job_id":  1,
        "adzuna_query":   "data engineer",
        "remoteok_tags":  ["data", "engineer", "python"],
        "jobicy_tag":     "engineering",
        "jobicy_search":  "data engineer",
    },
    "data scientist": {
        "target_job_id":  2,
        "adzuna_query":   "data scientist",
        "remoteok_tags":  ["data", "science", "python"],
        "jobicy_tag":     "data",
        "jobicy_search":  "data scientist",
    },
    "data analyst": {
        "target_job_id":  3,
        "adzuna_query":   "data analyst",
        "remoteok_tags":  ["analyst", "data", "sql"],
        "jobicy_tag":     "data",
        "jobicy_search":  "data analyst",
    },
    "ml engineer": {
        "target_job_id":  4,
        "adzuna_query":   "machine learning engineer",
        "remoteok_tags":  ["machine-learning", "python", "ai"],
        "jobicy_tag":     "engineering",
        "jobicy_search":  "machine learning",
    },
    "cloud engineer": {
        "target_job_id":  5,
        "adzuna_query":   "cloud engineer",
        "remoteok_tags":  ["cloud", "devops", "aws"],
        "jobicy_tag":     "engineering",
        "jobicy_search":  "cloud engineer",
    },
    "devops": {
        "target_job_id":  6,
        "adzuna_query":   "devops engineer",
        "remoteok_tags":  ["devops", "docker", "kubernetes"],
        "jobicy_tag":     "devops",
        "jobicy_search":  "devops",
    },
    "backend": {
        "target_job_id":  7,
        "adzuna_query":   "backend developer",
        "remoteok_tags":  ["backend", "python", "node"],
        "jobicy_tag":     "engineering",
        "jobicy_search":  "backend developer",
    },
    "fullstack": {
        "target_job_id":  8,
        "adzuna_query":   "fullstack developer",
        "remoteok_tags":  ["fullstack", "javascript", "react"],
        "jobicy_tag":     "engineering",
        "jobicy_search":  "fullstack developer",
    },
}

# Colonnes CSV offres_finales
CSV_COLUMNS = [
    "id", "title", "company", "description",
    "offer_source", "source_type", "raw_text",
    "target_job_id", "url", "scraped_at",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
]

ALL_SKILLS = [
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


def extract_skills(text: str) -> list:
    if not text:
        return []
    text_lower = text.lower()
    return [s for s in ALL_SKILLS if re.search(r"\b" + re.escape(s) + r"\b", text_lower)]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def make_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept":     "application/json, text/html, */*",
    }


def fetch_full_description_from_page(url: str) -> str:
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=make_headers(), timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    SELECTORS = [
        "#jobDescriptionText",
        "[data-testid='job-description']",
        ".job-description",
        "#job-description",
        ".jobDescription",
        "#jobDescription",
        ".description__text",
        ".description",
        "#description",
        "article",
        "main",
    ]
    for sel in SELECTORS:
        elem = soup.select_one(sel)
        if elem:
            text = elem.get_text(separator=" ")
            if len(text.strip()) > 300:
                return clean_text(text)

    divs = soup.find_all("div")
    if divs:
        best = max(divs, key=lambda d: len(d.get_text()))
        text = best.get_text(separator=" ")
        if len(text.strip()) > 300:
            return clean_text(text)

    return ""


def get_next_id(path: str) -> int:
    """Retourne le prochain id disponible en lisant le max existant dans le CSV."""
    if not os.path.exists(path):
        return 1
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            max_id = 0
            for row in csv.DictReader(f):
                try:
                    val = int(row.get("id") or 0)
                    if val > max_id:
                        max_id = val
                except (ValueError, TypeError):
                    pass
            return max_id + 1
    except Exception:
        return 1


def build_offre(raw: dict, target_job_id: int, row_id: int) -> dict:
    desc = raw.get("description_full", "")
    return {
        "id":            row_id,
        "title":         raw.get("title", ""),
        "company":       raw.get("company", ""),
        "description":   desc,
        "offer_source":  raw.get("source", ""),
        "source_type":   "scraped",
        "raw_text":      desc,
        "target_job_id": target_job_id,
        "url":           raw.get("url", ""),
        "scraped_at":    raw.get("scraped_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
    }


# Source 1 : RemoteOK

class RemoteOKScraper:
    BASE_URL = "https://remoteok.com/api"

    def fetch(self, job_category: str, tags: list, limit: int = 30) -> list:
        log.info(f"  [RemoteOK] Récupération des offres...")

        try:
            resp = requests.get(self.BASE_URL, headers=make_headers(), timeout=25)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.error(f"  [RemoteOK] Erreur : {e}")
            return []

        try:
            data = resp.json()
        except Exception:
            log.error("  [RemoteOK] Réponse non-JSON")
            return []

        all_jobs = [x for x in data if isinstance(x, dict) and x.get("position")]
        log.info(f"  [RemoteOK] {len(all_jobs)} offres totales reçues")

        keywords = [job_category.lower()] + [t.lower().replace("-", " ") for t in tags]
        matching = []

        for job in all_jobs:
            position  = job.get("position", "").lower()
            job_tags  = [t.lower() for t in job.get("tags", []) if isinstance(t, str)]
            text      = position + " " + " ".join(job_tags)
            if any(kw in text for kw in keywords):
                matching.append(job)

        log.info(f"  [RemoteOK] {len(matching)} offres correspondent à '{job_category}'")

        offers = []
        seen   = set()

        for job in matching[:limit]:
            uid = str(job.get("id", ""))
            if uid in seen or not uid:
                continue
            seen.add(uid)

            description = job.get("description", "")
            job_tags    = [t.lower() for t in job.get("tags", []) if isinstance(t, str)]
            skills      = list(dict.fromkeys(job_tags + extract_skills(description)))

            salary = ""
            if job.get("salary_min") and job.get("salary_max"):
                salary = f"${int(job['salary_min'])}–${int(job['salary_max'])}/yr"

            offers.append({
                "scraped_at":       datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "source":           "remoteok",
                "job_category":     job_category,
                "title":            job.get("position", ""),
                "company":          job.get("company", ""),
                "location":         "Remote",
                "remote":           "yes",
                "posted_date":      (job.get("date") or "")[:10],
                "salary":           salary,
                "url":              job.get("url") or f"https://remoteok.com/remote-jobs/{uid}",
                "skills_mentioned": " | ".join(skills[:15]),
                "skills_count":     len(skills),
                "description_full": clean_text(description),
            })

        log.info(f"  [RemoteOK] {len(offers)} offres extraites")
        return offers


# Source 2 : Jobicy

class JobicyScraper:
    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    def fetch(self, job_category: str, keyword: str, limit: int = 30) -> list:
        log.info(f"  [Jobicy] Recherche keyword='{keyword}'...")

        try:
            resp = requests.get(
                self.BASE_URL,
                params={"count": min(limit, 50), "keyword": keyword},
                headers=make_headers(),
                timeout=25,
            )
            resp.raise_for_status()
        except requests.HTTPError:
            return self._fetch_all_and_filter(job_category, keyword, limit)
        except requests.RequestException as e:
            log.error(f"  [Jobicy] Erreur réseau : {e}")
            return []

        try:
            data = resp.json()
        except Exception:
            log.error("  [Jobicy] Réponse non-JSON")
            return []

        jobs = data.get("jobs", [])
        log.info(f"  [Jobicy] {len(jobs)} offres reçues")
        return self._parse_jobs(jobs, job_category, limit)

    def _fetch_all_and_filter(self, job_category: str, keyword: str, limit: int) -> list:
        log.info(f"  [Jobicy] Fallback — récupération sans filtre...")
        try:
            resp = requests.get(
                self.BASE_URL,
                params={"count": 50},
                headers=make_headers(),
                timeout=25,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.error(f"  [Jobicy] Fallback échoué : {e}")
            return []

        all_jobs = data.get("jobs", [])
        kw_lower = keyword.lower()
        filtered = [
            j for j in all_jobs
            if kw_lower in j.get("jobTitle", "").lower()
            or kw_lower in " ".join(j.get("jobIndustry", [])).lower()
        ]
        log.info(f"  [Jobicy] Fallback : {len(filtered)}/{len(all_jobs)} offres correspondent")
        return self._parse_jobs(filtered, job_category, limit)

    def _parse_jobs(self, jobs: list, job_category: str, limit: int) -> list:
        offers = []
        seen   = set()

        for job in jobs[:limit]:
            uid = str(job.get("id", ""))
            if uid in seen or not uid:
                continue
            seen.add(uid)

            description = job.get("jobDescription", "")
            industry    = " ".join(job.get("jobIndustry", []))
            skills      = extract_skills(description + " " + industry)

            salary = ""
            s_min  = job.get("annualSalaryMin")
            s_max  = job.get("annualSalaryMax")
            curr   = job.get("salaryCurrency", "USD")
            if s_min and s_max:
                salary = f"{s_min}–{s_max} {curr}/yr"

            offers.append({
                "scraped_at":       datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "source":           "jobicy",
                "job_category":     job_category,
                "title":            job.get("jobTitle", ""),
                "company":          job.get("companyName", ""),
                "location":         job.get("jobGeo", "Worldwide"),
                "remote":           "yes",
                "posted_date":      (job.get("pubDate") or "")[:10],
                "salary":           salary,
                "url":              job.get("url", ""),
                "skills_mentioned": " | ".join(skills[:15]),
                "skills_count":     len(skills),
                "description_full": clean_text(description),
            })

        log.info(f"  [Jobicy] {len(offers)} offres extraites")
        return offers


# Source 3 : Adzuna

class AdzunaScraper:
    BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

    def __init__(self, app_id: str, api_key: str):
        self.app_id  = app_id.strip() if app_id else ""
        self.api_key = api_key.strip() if api_key else ""

    def is_configured(self) -> bool:
        return bool(self.app_id and self.api_key)

    def fetch(self, job_category: str, query: str, country: str = "gb", limit: int = 30) -> list:
        if not self.is_configured():
            log.info("  [Adzuna] Clé non configurée — source ignorée")
            return []

        log.info(f"  [Adzuna] Recherche '{query}' | pays='{country}'...")

        offers = []
        seen   = set()
        page   = 1

        while len(offers) < limit:
            url = self.BASE_URL.format(country=country, page=page)
            try:
                resp = requests.get(
                    url,
                    params={
                        "app_id":           self.app_id,
                        "app_key":          self.api_key,
                        "what":             query,
                        "results_per_page": min(limit, 50),
                        "sort_by":          "date",
                        "content-type":     "application/json",
                    },
                    headers=make_headers(),
                    timeout=20,
                )
            except requests.RequestException as e:
                log.error(f"  [Adzuna] Erreur réseau : {e}")
                break

            if resp.status_code == 401:
                log.error("  [Adzuna] Clé invalide (401)")
                break
            elif resp.status_code == 429:
                log.warning("  [Adzuna] Rate limit — pause 60s")
                time.sleep(60)
                continue
            elif resp.status_code != 200:
                log.error(f"  [Adzuna] HTTP {resp.status_code}")
                break

            try:
                data = resp.json()
            except Exception:
                log.error("  [Adzuna] Réponse non-JSON")
                break

            results = data.get("results", [])
            if not results:
                log.info("  [Adzuna] Plus de résultats")
                break

            for job in results:
                uid = job.get("id", "")
                if uid in seen:
                    continue
                seen.add(uid)

                description  = job.get("description", "")
                redirect_url = job.get("redirect_url", "")

                if len(description) <= 500 and redirect_url:
                    full = fetch_full_description_from_page(redirect_url)
                    if full and len(full) > len(description):
                        description = full
                        log.info(f"    [Adzuna] Description complète ({len(description)} chars)")
                    time.sleep(random.uniform(1.0, 2.0))

                skills = extract_skills(description + " " + job.get("title", ""))

                salary = ""
                if job.get("salary_min") and job.get("salary_max"):
                    curr   = job.get("salary_currency_code", "GBP")
                    salary = f"{int(job['salary_min'])}–{int(job['salary_max'])} {curr}/yr"

                loc = job.get("location", {}).get("display_name", country.upper())

                offers.append({
                    "scraped_at":       datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "source":           "adzuna",
                    "job_category":     job_category,
                    "title":            job.get("title", ""),
                    "company":          job.get("company", {}).get("display_name", ""),
                    "location":         loc,
                    "remote":           "unknown",
                    "posted_date":      (job.get("created") or "")[:10],
                    "salary":           salary,
                    "url":              redirect_url,
                    "skills_mentioned": " | ".join(skills[:15]),
                    "skills_count":     len(skills),
                    "description_full": clean_text(description),
                })

            page += 1
            time.sleep(1.2)

        result = offers[:limit]
        log.info(f"  [Adzuna] {len(result)} offres extraites")
        return result


# Déduplication

def deduplicate(offers: list) -> list:
    seen, result = set(), []
    priority = {"adzuna": 0, "remoteok": 1, "jobicy": 2}
    for offer in sorted(offers, key=lambda o: priority.get(o.get("source", ""), 9)):
        key = (offer.get("title", "").lower().strip(), offer.get("company", "").lower().strip())
        if key not in seen and any(k for k in key):
            seen.add(key)
            result.append(offer)
    removed = len(offers) - len(result)
    if removed:
        log.info(f"  Déduplication : -{removed} doublons → {len(result)} uniques")
    return result


# Sauvegarde CSV offres_finales

def load_existing_keys(path: str) -> set:
    keys = set()
    if not os.path.exists(path):
        return keys
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                url = (row.get("url") or "").strip()
                if url:
                    keys.add(url)
                title   = (row.get("title",   "") or "").lower().strip()
                company = (row.get("company", "") or "").lower().strip()
                if title or company:
                    keys.add((title, company))
    except Exception as e:
        log.warning(f"  Impossible de lire le CSV existant : {e}")
    return keys


def save_to_offres_finales(offers: list, path: str, mode: str = "a") -> int:
    
    if not offers:
        log.warning("Aucune offre à sauvegarder")
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    # Filtrer les doublons déjà présents
    existing_keys = load_existing_keys(path)
    if existing_keys:
        new_offers = []
        for o in offers:
            url     = (o.get("url")     or "").strip()
            title   = (o.get("title",   "") or "").lower().strip()
            company = (o.get("company", "") or "").lower().strip()
            if url and url in existing_keys:
                continue
            if (title, company) in existing_keys:
                continue
            new_offers.append(o)
        skipped = len(offers) - len(new_offers)
        if skipped:
            log.info(f"  Anti-doublons CSV : {skipped} offres déjà présentes ignorées")
        offers = new_offers

    if not offers:
        log.info("  Aucune nouvelle offre à ajouter (tout est déjà présent)")
        return 0

    write_header = not os.path.exists(path)
    next_id      = get_next_id(path)

    with open(path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore", quoting=csv.QUOTE_ALL)
        if write_header:
            writer.writeheader()
        for offer in offers:
            offer["id"] = next_id
            writer.writerow(offer)
            next_id += 1

    log.info(f"  → Sauvegardé dans offres_finales : {path}  ({len(offers)} lignes)")
    return len(offers)


# affichage résumé

def print_summary(offers: list, csv_path: str):
    BOLD  = "\033[1m"; RESET = "\033[0m"
    BLUE  = "\033[94m"; GREEN = "\033[92m"; CYAN = "\033[96m"

    sources = {}
    for o in offers:
        src = o.get("offer_source", "?")
        sources[src] = sources.get(src, 0) + 1

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  {len(offers)} offres ajoutées dans offres_finales{RESET}")
    for src, count in sorted(sources.items()):
        color = {"adzuna": BLUE, "remoteok": GREEN, "jobicy": CYAN}.get(src, RESET)
        print(f"    {color}• {src:<12}{RESET} : {count} offres")
    print(f"{BOLD}{'═'*60}{RESET}\n")

    for i, o in enumerate(offers[:15], 1):
        color = {"adzuna": BLUE, "remoteok": GREEN, "jobicy": CYAN}.get(o["offer_source"], RESET)
        print(f"  [{i:02d}] {BOLD}{o['title']}{RESET}  {color}[{o['offer_source']}]{RESET}  target_job_id={o['target_job_id']}")
        print(f"        {o['company']}")
        print()

    if len(offers) > 15:
        print(f"  ... +{len(offers)-15} offres dans le CSV\n")

    print(f"  {BOLD}Fichier CSV : {csv_path}{RESET}\n")


# Main

def main():
    parser = argparse.ArgumentParser(
        description="Scraper → offres_finales.csv (schéma id/title/company/description/...)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python scraper_offres_finales.py --job "data analyst"
  python scraper_offres_finales.py --job "data engineer" --job "ml engineer"
  python scraper_offres_finales.py --all-jobs
  python scraper_offres_finales.py --list-jobs
        """,
    )

    parser.add_argument("--job", "-j", action="append", default=[],
                        help="Titre du poste (répétable)")
    parser.add_argument("--country", "-c", default="gb",
                        help="Code pays Adzuna : ma, fr, gb, us (défaut: gb)")
    parser.add_argument("--limit", "-n", type=int, default=25,
                        help="Offres max par source par métier (défaut: 25)")
    parser.add_argument("--adzuna-id",  default="",
                        help="Adzuna App ID (ou ADZUNA_APP_ID dans .env)")
    parser.add_argument("--adzuna-key", default="",
                        help="Adzuna API Key (ou ADZUNA_API_KEY dans .env)")
    parser.add_argument("--output", "-o", default="",
                        help="Chemin CSV de sortie (défaut: scraped_data/offres_finales.csv)")
    parser.add_argument("--all-jobs", "-A", action="store_true",
                        help="Scraper tous les métiers de JOB_PROFILES")
    parser.add_argument("--list-jobs", action="store_true",
                        help="Lister les métiers disponibles avec leur target_job_id")

    args = parser.parse_args()

    if args.list_jobs:
        print("\nMétiers disponibles :\n")
        for name, cfg in JOB_PROFILES.items():
            print(f"  [{cfg['target_job_id']}] {name}")
        print()
        return

    if args.all_jobs:
        args.job = list(JOB_PROFILES.keys())
        log.info(f"Mode --all-jobs : {len(args.job)} profils sélectionnés")
    elif not args.job:
        parser.error("Spécifiez au moins un --job ou utilisez --all-jobs")

    adzuna_id  = args.adzuna_id  or os.getenv("ADZUNA_APP_ID",  "")
    adzuna_key = args.adzuna_key or os.getenv("ADZUNA_API_KEY", "")

    log.info(f"Fichier .env utilisé : {_ENV_FILE}")
    if adzuna_id:
        log.info(f"Adzuna App ID chargé : {adzuna_id[:6]}...")
    else:
        log.info("Adzuna : aucune clé (RemoteOK + Jobicy seulement)")

    csv_path = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "scraped_data", "offres_finales.csv"
    )

    remoteok = RemoteOKScraper()
    jobicy   = JobicyScraper()
    adzuna   = AdzunaScraper(adzuna_id, adzuna_key)

    all_formatted = []

    for job_title in args.job:
        profile = JOB_PROFILES.get(job_title.lower(), {
            "target_job_id":  0,
            "adzuna_query":   job_title,
            "remoteok_tags":  [job_title.lower().replace(" ", "-")],
            "jobicy_tag":     "engineering",
            "jobicy_search":  job_title,
        })

        target_job_id = profile["target_job_id"]

        log.info(f"\n{'─'*55}")
        log.info(f"Métier : {job_title.upper()}  (target_job_id={target_job_id})")

        raw_offers = []

        #  RemoteOK
        try:
            raw_offers.extend(remoteok.fetch(job_title, profile["remoteok_tags"], limit=args.limit))
        except Exception as e:
            log.error(f"RemoteOK exception : {e}")

        time.sleep(random.uniform(2, 4))

        #  Jobicy
        try:
            raw_offers.extend(jobicy.fetch(job_title, profile["jobicy_search"], limit=args.limit))
        except Exception as e:
            log.error(f"Jobicy exception : {e}")

        time.sleep(random.uniform(1, 3))

        #  Adzuna
        try:
            raw_offers.extend(adzuna.fetch(job_title, profile["adzuna_query"],
                                           country=args.country, limit=args.limit))
        except Exception as e:
            log.error(f"Adzuna exception : {e}")

        raw_offers = deduplicate(raw_offers)
        log.info(f"  → '{job_title}' : {len(raw_offers)} offres uniques")

        for raw in raw_offers:
            all_formatted.append(build_offre(raw, target_job_id, row_id=0))

        if len(args.job) > 1 and job_title != args.job[-1]:
            pause = random.uniform(5, 10)
            log.info(f"Pause inter-métiers : {pause:.0f}s")
            time.sleep(pause)

    saved = save_to_offres_finales(all_formatted, csv_path)
    if saved:
        
        display = all_formatted[:saved]
        print_summary(display, csv_path)
    else:
        log.info("Aucune nouvelle offre ajoutée.")


if __name__ == "__main__":
    main()
