"""
Import all offers from `data/scraper/jobs_dataanalyst.json`, extract skills from each
description via ML, then aggregate into `job_skills` per target job.

Pipeline:
  1. Upsert `offers` (stable url from title + description hash)
  2. ML `/extract-skills` on each description → `offer_skills` (staging)
  3. Aggregate by `target_job_id` → upsert `job_skills` (frequency + importance)

Usage (from backend/, ML on :8001):
    python -m app.db.import_jobs
    python -m app.db.import_jobs --limit 50          # smoke test
    python -m app.db.import_jobs --job-skills-only   # re-aggregate only
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.db import models as db_models
from app.db.database import SessionLocal

log = logging.getLogger("db.import_jobs")


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def _default_jobs_json_path() -> str:
    repo_root = _repo_root()
    preferred = os.path.join(repo_root, "data", "scraper", "jobs_dataanalyst.json")
    if os.path.exists(preferred):
        return preferred
    fallback = os.path.join(repo_root, "data", "scraper", "jobs.json")
    if os.path.exists(fallback):
        return fallback
    return preferred


def _slugify(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:80] if t else "job"


def _offer_url(job_title: str, job_description: str) -> str:
    h = hashlib.sha1((job_title + "\n" + (job_description or "")).encode("utf-8")).hexdigest()[:16]
    return f"jobsjson://{_slugify(job_title)}:{h}"


def _resolve_target_job_id(db, job_title: str, source_file: str = "") -> Optional[int]:
    basename = os.path.basename(source_file).lower()
    if "dataanalyst" in basename:
        tj = db.query(db_models.TargetJob).filter(
            db_models.TargetJob.name == "Data Analyst"
        ).first()
        if tj:
            return tj.id
        log.warning("TargetJob 'Data Analyst' not found — run: python -m app.db.seed")

    return _classify_target_job_id(db, job_title)


def _classify_target_job_id(db, job_title: str) -> Optional[int]:
    title = (job_title or "").lower()
    mapping = [
        ("data engineer", "Data Engineer"),
        ("etl", "Data Engineer"),
        ("data analyst", "Data Analyst"),
        ("business intelligence", "Data Analyst"),
        ("bi analyst", "Data Analyst"),
        ("data scientist", "Data Scientist"),
        ("machine learning", "ML Engineer"),
        ("ml engineer", "ML Engineer"),
        ("devops", "DevOps Engineer"),
        ("site reliability", "DevOps Engineer"),
        ("cloud architect", "Cloud Engineer"),
        ("cloud engineer", "Cloud Engineer"),
        ("full stack", "Fullstack Developer"),
        ("fullstack", "Fullstack Developer"),
        ("frontend", "Fullstack Developer"),
        ("back end", "Backend Developer"),
        ("backend", "Backend Developer"),
    ]
    target_name = None
    for needle, name in mapping:
        if needle in title:
            target_name = name
            break
    if not target_name:
        target_name = "Data Analyst"

    tj = db.query(db_models.TargetJob).filter(db_models.TargetJob.name == target_name).first()
    return tj.id if tj else None


async def _extract_skills_via_ml(
    client: httpx.AsyncClient,
    text: str,
    semaphore: asyncio.Semaphore,
) -> list[str]:
    if not text or not text.strip():
        return []
    async with semaphore:
        resp = await client.post(
            f"{settings.ML_SERVICE_URL}/extract-skills",
            json={"text": text},
        )
        resp.raise_for_status()
        data = resp.json()
    seen: set[str] = set()
    out: list[str] = []
    for s in data.get("skills", []):
        key = (s or "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _get_or_create_skill(db, name: str) -> db_models.Skill:
    key = name.lower().strip()
    skill = db.query(db_models.Skill).filter(db_models.Skill.name == key).first()
    if skill:
        return skill
    skill = db_models.Skill(name=key)
    db.add(skill)
    db.flush()
    return skill


def _upsert_offer(
    db,
    job_title: str,
    job_description: str,
    target_job_id: Optional[int],
    company: Optional[str] = None,
) -> db_models.Offer:
    url = _offer_url(job_title, job_description)
    offer = db.query(db_models.Offer).filter(db_models.Offer.url == url).first()
    if offer:
        if not offer.title and job_title:
            offer.title = job_title
        if company and not offer.company:
            offer.company = company
        if not offer.description and job_description:
            offer.description = job_description
        if not offer.raw_text and job_description:
            offer.raw_text = job_description
        if target_job_id and offer.target_job_id is None:
            offer.target_job_id = target_job_id
        offer.offer_source = offer.offer_source or "jobs_dataanalyst.json"
        offer.source_type = offer.source_type or "scraped"
        return offer

    offer = db_models.Offer(
        title=job_title,
        company=company,
        description=job_description,
        offer_source="jobs_dataanalyst.json",
        raw_text=job_description,
        target_job_id=target_job_id,
        url=url,
    )
    db.add(offer)
    db.flush()
    return offer


def _offer_has_skills(db, offer_id: int) -> bool:
    return (
        db.query(db_models.OfferSkill.id)
        .filter(db_models.OfferSkill.offer_id == offer_id)
        .first()
        is not None
    )


def _replace_offer_skills(db, offer_id: int, skill_names: list[str]) -> int:
    db.query(db_models.OfferSkill).filter(
        db_models.OfferSkill.offer_id == offer_id
    ).delete(synchronize_session=False)
    n = 0
    for name in skill_names:
        skill = _get_or_create_skill(db, name)
        db.add(
            db_models.OfferSkill(
                offer_id=offer_id,
                skill_id=skill.id,
                importance_score=Decimal("0.5"),
            )
        )
        n += 1
    return n


async def import_offers_from_jobs_json(
    jobs_json_path: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    extract_skills: bool = True,
    workers: int = 4,
    batch_size: int = 10,
    skip_existing_skills: bool = True,
    force_reextract: bool = False,
) -> dict:
    path = os.path.abspath(
        jobs_json_path or os.environ.get("JOBS_JSON_PATH") or _default_jobs_json_path()
    )
    log.info("Repo root: %s", _repo_root())
    log.info("Importing from %s (extract=%s, workers=%s)", path, extract_skills, workers)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Jobs file not found: {path}")

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise ValueError("JSON must be an array of job objects")

    rows = payload[:limit] if limit else payload
    parsed: list[dict] = []
    skipped = 0
    for row in rows:
        title = (row or {}).get("job_title") or (row or {}).get("title")
        desc = (
            (row or {}).get("job_description")
            or (row or {}).get("job_desc")
            or (row or {}).get("description")
        )
        company = (row or {}).get("company")
        if not title or not desc:
            skipped += 1
            continue
        parsed.append({"title": title, "desc": desc, "company": company})

    imported = 0
    skills_total = 0
    extract_errors = 0
    semaphore = asyncio.Semaphore(max(1, workers))

    db = SessionLocal()
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            for start in range(0, len(parsed), batch_size):
                chunk = parsed[start : start + batch_size]
                offers_in_chunk: list[tuple[db_models.Offer, str, bool]] = []

                for item in chunk:
                    target_job_id = _resolve_target_job_id(db, item["title"], path)
                    offer = _upsert_offer(
                        db,
                        item["title"],
                        item["desc"],
                        target_job_id,
                        company=item["company"],
                    )
                    needs_extract = extract_skills and (
                        force_reextract
                        or not (skip_existing_skills and _offer_has_skills(db, offer.id))
                    )
                    offers_in_chunk.append((offer, item["desc"], needs_extract))
                    imported += 1

                to_extract = [d for _, d, need in offers_in_chunk if need]
                skill_lists: list[list[str]] = []
                if to_extract:
                    tasks = [
                        _extract_skills_via_ml(client, desc, semaphore)
                        for desc in to_extract
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for r in results:
                        if isinstance(r, Exception):
                            log.warning("ML extract failed: %s", r)
                            skill_lists.append([])
                            extract_errors += 1
                        else:
                            skill_lists.append(r)

                extract_idx = 0
                for offer, desc, needs_extract in offers_in_chunk:
                    if not needs_extract:
                        continue
                    skills = skill_lists[extract_idx] if extract_idx < len(skill_lists) else []
                    extract_idx += 1
                    if skills:
                        skills_total += _replace_offer_skills(db, offer.id, skills)

                db.commit()
                done = min(start + batch_size, len(parsed))
                log.info("Progress: %d / %d offers", done, len(parsed))

        return {
            "offers_processed": imported,
            "offers_skipped": skipped,
            "offer_skills_rows": skills_total,
            "extract_errors": extract_errors,
            "jobs_json_path": path,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def rebuild_job_skills_from_offers(
    min_offers_per_job: int = 1,
    max_skills_per_job: int = 30,
) -> dict:
    """
    Aggregate offer_skills by target_job_id → job_skills.
    importance = 0.5 + 0.45 * (count / max_count)
    frequency = number of offers mentioning the skill
    """
    db = SessionLocal()
    try:
        offers = db.query(db_models.Offer).filter(db_models.Offer.target_job_id.isnot(None)).all()
        by_job: dict[int, list[int]] = defaultdict(list)
        for o in offers:
            by_job[o.target_job_id].append(o.id)

        updated_links = 0
        jobs_updated = 0
        job_names: dict[int, str] = {}

        for job_id, offer_ids in by_job.items():
            if len(offer_ids) < min_offers_per_job:
                continue

            tj = db.query(db_models.TargetJob).filter(db_models.TargetJob.id == job_id).first()
            if tj:
                job_names[job_id] = tj.name

            rows = db.query(db_models.OfferSkill.skill_id).filter(
                db_models.OfferSkill.offer_id.in_(offer_ids)
            ).all()
            counts = Counter(r[0] for r in rows)
            if not counts:
                log.warning("No offer_skills for target_job_id=%s (%s)", job_id, job_names.get(job_id))
                continue

            max_count = max(counts.values()) or 1
            top = counts.most_common(max_skills_per_job)

            for skill_id, cnt in top:
                link = db.query(db_models.JobSkill).filter(
                    db_models.JobSkill.target_job_id == job_id,
                    db_models.JobSkill.skill_id == skill_id,
                ).first()
                importance = 0.5 + 0.45 * (cnt / max_count)
                freq = float(cnt)
                if link:
                    link.importance_score = Decimal(str(round(importance, 3)))
                    link.frequency = Decimal(str(round(freq, 2)))
                else:
                    db.add(
                        db_models.JobSkill(
                            target_job_id=job_id,
                            skill_id=skill_id,
                            importance_score=Decimal(str(round(importance, 3))),
                            frequency=Decimal(str(round(freq, 2))),
                        )
                    )
                updated_links += 1

            jobs_updated += 1
            log.info(
                "job_skills: %s - top %s skills (from %d offers)",
                job_names.get(job_id, job_id),
                len(top),
                len(offer_ids),
            )

        db.commit()
        return {
            "jobs_updated": jobs_updated,
            "job_skill_links_upserted": updated_links,
            "by_job": job_names,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(
        description="Import jobs_dataanalyst.json → offers → offer_skills → job_skills"
    )
    parser.add_argument("--file", help="Path to JSON (default: jobs_dataanalyst.json)")
    parser.add_argument("--limit", type=int, help="Max rows (debug)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel ML requests")
    parser.add_argument("--batch-size", type=int, default=10, help="Offers per DB commit")
    parser.add_argument(
        "--offers-only",
        action="store_true",
        help="Import offers without ML extraction or job_skills rebuild",
    )
    parser.add_argument(
        "--job-skills-only",
        action="store_true",
        help="Only rebuild job_skills from existing offer_skills",
    )
    parser.add_argument(
        "--force-reextract",
        action="store_true",
        help="Re-run ML on offers that already have offer_skills",
    )
    parser.add_argument(
        "--clear-offer-skills",
        action="store_true",
        help="Delete all offer_skills before import",
    )
    parser.add_argument(
        "--max-job-skills",
        type=int,
        default=30,
        help="Top N skills per target job after aggregation",
    )
    args = parser.parse_args()

    if args.clear_offer_skills:
        db = SessionLocal()
        try:
            n = db.query(db_models.OfferSkill).delete()
            db.commit()
            print(f"Deleted offer_skills rows: {n}")
        finally:
            db.close()
        if args.job_skills_only and not args.file and args.limit is None and args.offers_only:
            stats = rebuild_job_skills_from_offers(max_skills_per_job=args.max_job_skills)
            print("Rebuilt job_skills:", stats)
            return

    if args.job_skills_only:
        stats = rebuild_job_skills_from_offers(max_skills_per_job=args.max_job_skills)
        print("Rebuilt job_skills:", stats)
        return

    stats1 = await import_offers_from_jobs_json(
        jobs_json_path=args.file,
        limit=args.limit,
        extract_skills=not args.offers_only,
        workers=args.workers,
        batch_size=args.batch_size,
        skip_existing_skills=not args.force_reextract,
        force_reextract=args.force_reextract,
    )
    print("Imported:", stats1)

    if not args.offers_only:
        stats2 = rebuild_job_skills_from_offers(max_skills_per_job=args.max_job_skills)
        print("job_skills:", stats2)


if __name__ == "__main__":
    asyncio.run(main())
