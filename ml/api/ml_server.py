import json
import os
import re
import sys
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
_API_DIR    = os.path.dirname(os.path.abspath(__file__))
_ML_DIR     = os.path.dirname(_API_DIR)
_ENGINE_DIR = os.path.join(_ML_DIR, "gap_engine")
_CV_PARSER_DIR = os.path.join(_ML_DIR, "cv_parser")
_BERT_DIR   = os.path.join(_ML_DIR, "bert")
_BERT_MODEL_DIR = os.path.join(_BERT_DIR, "model")

for p in [_ML_DIR, _ENGINE_DIR, _CV_PARSER_DIR, _BERT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from skill_matcher import compute_gap_aligned, extract_skills_from_text_taxonomy

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Career Platform — ML Service",
    description="Skill extraction (CV parser NER) + gap analysis",
    version="2.1.0",
)

# ── Taxonomy fallback ─────────────────────────────────────────────────────────
_TAXONOMY_PATH = os.path.join(_ENGINE_DIR, "skill_taxonomy.json")
_alias_to_skill: dict = {}

_cv_parser_ready = False
_bert_extractor = None
_active_extractor = "taxonomy"


def _load_taxonomy():
    global _alias_to_skill
    if not os.path.exists(_TAXONOMY_PATH):
        logger.warning(f"Taxonomy not found at {_TAXONOMY_PATH} — fallback disabled")
        return
    with open(_TAXONOMY_PATH, encoding="utf-8") as f:
        taxonomy = json.load(f)
    for skill, aliases in taxonomy.items():
        _alias_to_skill[skill.lower()] = skill.lower()
        for alias in aliases:
            _alias_to_skill[alias.lower()] = skill.lower()
    logger.info(f"Taxonomy loaded: {len(_alias_to_skill)} aliases")


def _taxonomy_extract(text: str) -> List[str]:
    text_lower = text.lower()
    skills = set()
    for alias, canonical in _alias_to_skill.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", text_lower):
            skills.add(canonical)
    return list(skills)


def _bert_model_is_ready() -> bool:
    if not os.path.isdir(_BERT_MODEL_DIR):
        return False
    files = os.listdir(_BERT_MODEL_DIR)
    has_weights = any(f in files for f in ("pytorch_model.bin", "model.safetensors"))
    has_config = "config.json" in files
    return has_weights and has_config


@app.on_event("startup")
def load_model():
    global _cv_parser_ready, _bert_extractor, _active_extractor

    _load_taxonomy()

    # 1) CV parser (spaCy model-best) — primary
    try:
        from extract import load_model as load_cv_parser, is_model_ready

        if is_model_ready() and load_cv_parser():
            _cv_parser_ready = True
            _active_extractor = "cv_parser"
            logger.info("CV parser (model-best) is the primary skill extractor")
            return
    except Exception as e:
        logger.warning(f"CV parser not available: {e}")

    # 2) BERT NER — secondary
    if _bert_model_is_ready():
        try:
            from bert.infer import SkillExtractor

            _bert_extractor = SkillExtractor(_BERT_MODEL_DIR)
            _active_extractor = "bert"
            logger.info(f"BERT model loaded from {_BERT_MODEL_DIR}")
            return
        except Exception as e:
            logger.error(f"Failed to load BERT model: {e}")

    logger.warning("Using taxonomy regex fallback for skill extraction")


def extract_skills_from_text(text: str) -> dict:
    """
    Extract skills from text.

    Priority: cv_parser (model-best) → BERT → taxonomy regex.
    """
    if not text or not text.strip():
        return {"skills": [], "by_category": {}, "source": _active_extractor}

    # 1) CV parser
    if _cv_parser_ready:
        try:
            from extract import extract_skills_from_text as cv_extract

            result = cv_extract(text)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"CV parser extraction failed: {e}")

    # 2) BERT
    if _bert_extractor is not None:
        result = _bert_extractor.predict(text)
        skills = [s.text.lower() for s in result.skills]
        by_category = {
            "TECH": [s.text.lower() for s in result.skills if s.label == "TECH"],
            "SOFT": [s.text.lower() for s in result.skills if s.label == "SOFT"],
            "TOOL": [s.text.lower() for s in result.skills if s.label == "TOOL"],
        }
        return {"skills": skills, "by_category": by_category, "source": "bert"}

    # 3) Taxonomy
    skills = _taxonomy_extract(text)
    return {
        "skills": skills,
        "by_category": {"TECH": skills, "SOFT": [], "TOOL": []},
        "source": "taxonomy",
    }


def _merge_skill_lists(*lists: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for lst in lists:
        for s in lst:
            key = s.lower().strip()
            if key and key not in seen:
                seen.add(key)
                out.append(key)
    return out


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class TextInput(BaseModel):
    text: str


class GapInput(BaseModel):
    cv_text: str
    market_text: str = ""
    job_weights: Optional[dict] = None
    market_skills: Optional[List[str]] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    try:
        from extract import resolve_model_dir
        model_dir = resolve_model_dir() if _cv_parser_ready else None
    except Exception:
        model_dir = None

    return {
        "status": "ok",
        "extraction": _active_extractor,
        "cv_parser_loaded": _cv_parser_ready,
        "cv_parser_model_dir": model_dir,
        "bert_loaded": _bert_extractor is not None,
        "bert_model_dir": _BERT_MODEL_DIR,
    }


@app.post("/extract-skills")
def extract_skills(data: TextInput):
    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    result = extract_skills_from_text(data.text)
    return {
        "skills": result["skills"],
        "by_category": result["by_category"],
        "count": len(result["skills"]),
        "source": result["source"],
    }


@app.post("/calculate-gap")
def calculate_gap_api(data: GapInput):
    """Compare CV skills (cv_parser on full text) vs job_skills from DB."""
    if not data.cv_text.strip():
        raise HTTPException(status_code=400, detail="cv_text cannot be empty")

    cv_result = extract_skills_from_text(data.cv_text)
    ner_skills = cv_result["skills"]
    taxonomy_on_cv = extract_skills_from_text_taxonomy(data.cv_text)

    if data.market_skills:
        market_skills = [s.lower().strip() for s in data.market_skills if s and s.strip()]
        market_result = {"by_category": {}, "source": "database"}
    else:
        if not data.market_text.strip():
            raise HTTPException(
                status_code=400,
                detail="market_text or market_skills is required",
            )
        market_result = extract_skills_from_text(data.market_text)
        market_skills = market_result["skills"]

    if not market_skills:
        raise HTTPException(status_code=400, detail="No market skills to compare against")

    job_weights = {s: float((data.job_weights or {}).get(s, 1)) for s in market_skills}
    for skill in market_skills:
        if skill not in job_weights:
            job_weights[skill] = 1.0

    aligned = compute_gap_aligned(
        ner_skills=_merge_skill_lists(ner_skills, taxonomy_on_cv),
        market_skills=market_skills,
        cv_text=data.cv_text,
        job_weights=job_weights,
    )

    cv_skills = aligned["cv_skills"]
    gap = {
        "acquired": aligned["acquired"],
        "missing": aligned["missing"],
        "match_percentage": aligned["match_percentage"],
    }

    return {
        "cv_skills": cv_skills,
        "market_skills": market_skills,
        "gap": gap,
        "score": aligned["score"],
        "cv_by_category": cv_result.get("by_category", {}),
        "market_by_category": market_result.get("by_category", {}),
        "extraction_source": cv_result["source"],
        "market_source": market_result.get("source", cv_result["source"]),
    }
