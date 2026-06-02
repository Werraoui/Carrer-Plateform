"""
Skill extraction using the trained spaCy CV parser (model-best).

Model path (first match):
  - CV_PARSER_MODEL_DIR env var
  - ml/cv_parser/model/output/model-best
  - ml/cv_parser/model/saved_model
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

log = logging.getLogger(__name__)

_nlp = None
_MODEL_DIR: Optional[str] = None

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CANDIDATES = [
    os.path.join(_BASE_DIR, "model", "output", "model-best"),
    os.path.join(_BASE_DIR, "model", "saved_model"),
]


def resolve_model_dir() -> Optional[str]:
    env_path = os.environ.get("CV_PARSER_MODEL_DIR")
    candidates = ([env_path] if env_path else []) + _DEFAULT_CANDIDATES
    for path in candidates:
        if path and os.path.isdir(path) and os.path.isfile(os.path.join(path, "meta.json")):
            return path
    return None


def is_model_ready() -> bool:
    return resolve_model_dir() is not None


def load_model() -> bool:
    """Load spaCy pipeline once. Returns True on success."""
    global _nlp, _MODEL_DIR

    if _nlp is not None:
        return True

    _MODEL_DIR = resolve_model_dir()
    if not _MODEL_DIR:
        log.warning("CV parser model not found (expected model-best under cv_parser/model/)")
        return False

    try:
        import spacy

        _nlp = spacy.load(_MODEL_DIR)
        log.info("CV parser model loaded from %s", _MODEL_DIR)
        return True
    except Exception as e:
        log.error("Failed to load CV parser model: %s", e)
        _nlp = None
        return False


def _normalize_skill(text: str) -> str:
    """Normalize extracted span to canonical lowercase form."""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return cleaned


def extract_skills_from_text(text: str) -> Optional[dict]:
    """
    Extract SKILL entities from raw CV/job text.

    Returns None if model is not loaded (caller should fallback).
    """
    if not text or not text.strip():
        return {"skills": [], "by_category": {"SKILL": []}, "source": "cv_parser"}

    if _nlp is None and not load_model():
        return None

    doc = _nlp(text)
    skills: list[str] = []
    seen: set[str] = set()

    for ent in doc.ents:
        if ent.label_ != "SKILL":
            continue
        name = _normalize_skill(ent.text)
        if len(name) < 2:
            continue
        if name not in seen:
            seen.add(name)
            skills.append(name)

    return {
        "skills": skills,
        "by_category": {"SKILL": skills, "TECH": [], "SOFT": [], "TOOL": []},
        "source": "cv_parser",
    }
