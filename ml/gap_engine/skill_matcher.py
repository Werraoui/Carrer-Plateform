"""
Align CV skill extraction with canonical market skills (from DB seed).

Uses taxonomy aliases + full-text keyword scan so gap is not empty when
the NER model returns spans like "aws machine" instead of "aws".
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

_ALIAS_TO_CANONICAL: dict[str, str] | None = None


def _taxonomy_path() -> str:
    return os.path.join(os.path.dirname(__file__), "skill_taxonomy.json")


def load_alias_map() -> dict[str, str]:
    global _ALIAS_TO_CANONICAL
    if _ALIAS_TO_CANONICAL is not None:
        return _ALIAS_TO_CANONICAL

    path = _taxonomy_path()
    alias_map: dict[str, str] = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            taxonomy = json.load(f)
        for canonical, aliases in taxonomy.items():
            canon = canonical.lower().strip()
            alias_map[canon] = canon
            for alias in aliases:
                alias_map[alias.lower().strip()] = canon

    _ALIAS_TO_CANONICAL = alias_map
    return alias_map


def _word_in_text(term: str, text_lower: str) -> bool:
    if not term or len(term) < 2:
        return False
    return bool(re.search(r"\b" + re.escape(term) + r"\b", text_lower))


def extract_skills_from_text_taxonomy(text: str, alias_map: Optional[dict] = None) -> list[str]:
    """Find canonical skills mentioned in text via taxonomy aliases."""
    if not text or not text.strip():
        return []

    alias_map = alias_map or load_alias_map()
    text_lower = text.lower()
    found: set[str] = set()

    for alias, canonical in alias_map.items():
        if _word_in_text(alias, text_lower):
            found.add(canonical)

    return sorted(found)


def align_cv_to_market(
    ner_skills: list[str],
    market_skills: list[str],
    cv_text: str,
) -> tuple[list[str], list[str], list[str]]:
    """
    Returns (cv_skills_detected, acquired, missing).

    cv_skills_detected: all skills found on the CV (for storage/display)
    acquired / missing: relative to market_skills list
    """
    alias_map = load_alias_map()
    market = [m.lower().strip() for m in market_skills if m and m.strip()]
    market_set = set(market)
    text_lower = (cv_text or "").lower()

    # Union: NER + taxonomy on full CV text
    detected: set[str] = set()
    for raw in ner_skills:
        s = raw.lower().strip()
        if not s:
            continue
        detected.add(alias_map.get(s, s))
        detected.add(s)

    for s in extract_skills_from_text_taxonomy(cv_text, alias_map):
        detected.add(s)

    acquired: list[str] = []
    for m in market:
        if m in detected:
            acquired.append(m)
            continue
        if _word_in_text(m, text_lower):
            acquired.append(m)
            continue
        for d in detected:
            if m in d or d in m:
                acquired.append(m)
                break
        else:
            canon = alias_map.get(m, m)
            for alias, c in alias_map.items():
                if c == m and _word_in_text(alias, text_lower):
                    acquired.append(m)
                    break

    missing = [m for m in market if m not in acquired]
    return sorted(detected), acquired, missing


def compute_gap_aligned(
    ner_skills: list[str],
    market_skills: list[str],
    cv_text: str,
    job_weights: dict[str, float],
) -> dict:
    """Gap + weighted score using aligned matching."""
    detected, acquired, missing = align_cv_to_market(ner_skills, market_skills, cv_text)
    market_set = set(market_skills)

    match_percentage = round(
        (len(acquired) / len(market_set)) * 100, 2
    ) if market_set else 0.0

    total_weight = sum(job_weights.get(m, 1.0) for m in market_skills)
    score = sum(job_weights.get(s, 1.0) for s in acquired)
    employability = round((score / total_weight) * 100, 2) if total_weight > 0 else 0.0

    return {
        "cv_skills": detected,
        "acquired": acquired,
        "missing": missing,
        "match_percentage": match_percentage,
        "score": employability,
    }
