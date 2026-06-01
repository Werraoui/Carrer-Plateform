import json
import os
import re
import sys
import logging
from typing import List, Optional
 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
 
# ── Path setup ────────────────────────────────────────────────────────────────
# ml/api/ml_server.py  →  we need to reach ml/bert/ and ml/gap_engine/
_API_DIR    = os.path.dirname(os.path.abspath(__file__))
_ML_DIR     = os.path.dirname(_API_DIR)               # ml/
_BERT_DIR   = os.path.join(_ML_DIR, "bert")           # ml/bert/
_ENGINE_DIR = os.path.join(_ML_DIR, "gap_engine")     # ml/gap_engine/
_MODEL_DIR  = os.path.join(_BERT_DIR, "model")        # ml/bert/model/
 
sys.path.insert(0, _ML_DIR)
sys.path.insert(0, _BERT_DIR)
sys.path.insert(0, _ENGINE_DIR)
 
from gap_engine.gap_calculator import calculate_gap
from gap_engine.scorer import compute_score
 
# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
 
# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Career Platform — ML Service",
    description="Skill extraction (BERT NER) + gap analysis",
    version="2.0.0",
)
 
# ── Taxonomy fallback ─────────────────────────────────────────────────────────
_TAXONOMY_PATH = os.path.join(_ENGINE_DIR, "skill_taxonomy.json")
_alias_to_skill: dict = {}
 
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
    """Regex-based fallback when BERT model is not available."""
    text_lower = text.lower()
    skills = set()
    for alias, canonical in _alias_to_skill.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", text_lower):
            skills.add(canonical)
    return list(skills)
 
 
# ── BERT model ────────────────────────────────────────────────────────────────
_extractor = None   # SkillExtractor instance, loaded at startup
 
def _model_is_ready() -> bool:
    """Check that the model directory contains actual weights."""
    if not os.path.isdir(_MODEL_DIR):
        return False
    files = os.listdir(_MODEL_DIR)
    has_weights = any(f in files for f in ("pytorch_model.bin", "model.safetensors"))
    has_config  = "config.json" in files
    return has_weights and has_config
 
 
@app.on_event("startup")
def load_model():
    global _extractor
    _load_taxonomy()
 
    if _model_is_ready():
        try:
            from bert.infer import SkillExtractor
            _extractor = SkillExtractor(_MODEL_DIR)
            logger.info(f"✅ BERT model loaded from {_MODEL_DIR}")
        except Exception as e:
            logger.error(f"❌ Failed to load BERT model: {e}")
            logger.warning("   Falling back to taxonomy extraction")
            _extractor = None
    else:
        logger.warning(
            f"⚠️  Model weights not found in {_MODEL_DIR} — "
            "using taxonomy fallback. Run ml/bert/train.py to train."
        )
 
 
def extract_skills_from_text(text: str) -> dict:
    """
    Core extraction function used by both endpoints.
 
    Returns:
      {
        "skills":      ["python", "docker", ...],
        "by_category": {"TECH": [...], "SOFT": [...], "TOOL": [...]},
        "source":      "bert" | "taxonomy"
      }
    """
    if _extractor is not None:
        result = _extractor.predict(text)
        skills = [s.text.lower() for s in result.skills]
        by_category = {
            "TECH": [s.text for s in result.skills if s.label == "TECH"],
            "SOFT": [s.text for s in result.skills if s.label == "SOFT"],
            "TOOL": [s.text for s in result.skills if s.label == "TOOL"],
        }
        return {"skills": skills, "by_category": by_category, "source": "bert"}
    else:
        skills = _taxonomy_extract(text)
        return {
            "skills": skills,
            "by_category": {"TECH": skills, "SOFT": [], "TOOL": []},
            "source": "taxonomy",
        }
 
 
# ── Pydantic schemas ──────────────────────────────────────────────────────────
 
class TextInput(BaseModel):
    text: str
 
class GapInput(BaseModel):
    cv_text:     str
    market_text: str
    job_weights: Optional[dict] = None   # {"python": 2, "docker": 1, ...}
 
 
# ── Routes ────────────────────────────────────────────────────────────────────
 
@app.get("/health")
def health():
    return {
        "status":       "ok",
        "model_loaded": _extractor is not None,
        "model_dir":    _MODEL_DIR,
        "extraction":   "bert" if _extractor else "taxonomy_fallback",
    }
 
 
@app.post("/extract-skills")
def extract_skills(data: TextInput):
    """
    Extract skills from a CV or job description text.
 
    Returns skills grouped by category (TECH / SOFT / TOOL)
    plus the flat list used downstream for gap analysis.
    """
    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
 
    result = extract_skills_from_text(data.text)
    return {
        "skills":      result["skills"],
        "by_category": result["by_category"],
        "count":       len(result["skills"]),
        "source":      result["source"],
    }
 
 
@app.post("/calculate-gap")
def calculate_gap_api(data: GapInput):
    """
    Compare CV skills against market/job description skills.
 
    Returns:
      - cv_skills / market_skills (flat lists)
      - gap: { acquired, missing, match_percentage }
      - score: weighted match score (0–100)
      - category breakdown for both CV and JD
    """
    if not data.cv_text.strip() or not data.market_text.strip():
        raise HTTPException(status_code=400, detail="cv_text and market_text cannot be empty")
 
    # Extract skills from both texts
    cv_result     = extract_skills_from_text(data.cv_text)
    market_result = extract_skills_from_text(data.market_text)
 
    cv_skills     = cv_result["skills"]
    market_skills = market_result["skills"]
 
    # Gap analysis
    gap = calculate_gap(cv_skills, market_skills)
 
    # Weighted scoring — use provided weights or default to 1 per skill
    job_weights = data.job_weights or {skill: 1 for skill in market_skills}
    score = compute_score(cv_skills, job_weights)
 
    return {
        "cv_skills":     cv_skills,
        "market_skills": market_skills,
        "gap":           gap,           # {acquired, missing, match_percentage}
        "score":         score,         # 0–100
        "cv_by_category":     cv_result["by_category"],
        "market_by_category": market_result["by_category"],
        "extraction_source":  cv_result["source"],
    }
 