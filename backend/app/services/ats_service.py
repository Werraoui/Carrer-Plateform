"""
ats_service.py
--------------
ATS analysis — ported from the standalone ATS Checker project.

Logic includes:
  - Keyword extraction (stopword filtering)
  - Semantic matching via spaCy (falls back to exact match)
  - CV format / section completeness checks
  - Subscores: keyword, format, completeness
  - Final weighted score
  - Matched / missing keywords
  - Formatting warnings
  - Suggestions

Exposes:
  - ats_service   (ATSService singleton)
  - analyze_cv_for_ats(cv_text, offer_text)   ← async wrapper used by the router
"""

from __future__ import annotations

import re
from typing import Optional

# ── spaCy with graceful fallback ──────────────────────────────────────────────
try:
    import spacy
    try:
        _nlp = spacy.load("en_core_web_md")
    except Exception:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            _nlp = spacy.blank("en")
            if "sentencizer" not in _nlp.pipe_names:
                _nlp.add_pipe("sentencizer")
    _SPACY_OK = True
except ImportError:
    _nlp = None
    _SPACY_OK = False

# ── Stopwords (NLTK with hardcoded fallback) ──────────────────────────────────
try:
    from nltk.corpus import stopwords as _sw
    _STOP: set = set(_sw.words("english"))
except Exception:
    _STOP: set = {
        "a", "an", "the", "and", "or", "but", "if", "while", "with", "for",
        "to", "from", "by", "on", "in", "of", "is", "are", "was", "were",
        "be", "been", "being", "as", "at", "this", "that", "these", "those",
        "it", "its", "into", "about", "over", "under", "after", "before",
        "between", "within", "without", "not", "i", "you", "he", "she", "we",
        "they", "my", "your", "his", "her", "our", "their", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should",
    }

_BASIC: set = {
    "i", "you", "he", "she", "it", "we", "they",
    "a", "an", "the", "and", "or", "but", "if", "is",
    "are", "was", "were", "in", "on", "for", "of", "to",
    "with", "as", "by", "at", "from", "this", "that",
    "these", "those", "my", "your", "his", "her", "its",
    "our", "their", "be", "have", "has", "had", "not",
}

_ALL_STOP = _STOP | _BASIC

# ── Sections to check for CV completeness ────────────────────────────────────
_SECTION_HINTS = ["experience", "education", "skills", "projects", "certification", "summary"]


class ATSService:
    """
    Port of the ATS Checker project's scoring logic into a service class.
    All heavy computation is synchronous; the async wrapper below handles FastAPI.
    """

    # ── Text helpers ──────────────────────────────────────────────────────────

    def _clean(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return text

    def _extract_keywords(self, text: str) -> set:
        """
        Extract meaningful keywords from text.
        Removes stopwords and very short tokens.
        """
        words = set(self._clean(text).split())
        return {w for w in words if w not in _ALL_STOP and len(w) > 1}

    # ── Semantic matching (mirrors main.py::semantic_match) ───────────────────

    def _semantic_match(self, resume_kws: set, jd_kws: set) -> tuple[set, set]:
        """
        1. Exact overlap first.
        2. spaCy semantic similarity for remaining terms (threshold 0.75).
        Falls back gracefully when vectors are unavailable.
        """
        matched: set = set()
        missing: set = set(jd_kws)

        # exact
        for word in list(missing):
            if word in resume_kws:
                matched.add(word)
                missing.discard(word)

        # semantic
        if _SPACY_OK and _nlp is not None and missing:
            resume_doc = _nlp(" ".join(resume_kws))
            resume_tokens = [t for t in resume_doc if t.text.strip()]

            for word in list(missing):
                word_doc = _nlp(word)
                if not getattr(word_doc, "vector_norm", 0):
                    continue
                sims = []
                for token in resume_tokens:
                    if not getattr(token, "vector_norm", 0):
                        continue
                    try:
                        sims.append(word_doc.similarity(token))
                    except Exception:
                        continue
                if sims and max(sims) >= 0.75:
                    matched.add(word)
                    missing.discard(word)

        return matched, missing

    # ── Format / section checks (mirrors main.py::check_cv_format) ───────────

    def _section_completeness(self, text: str) -> dict:
        low = (text or "").lower()
        return {s: (s in low) for s in _SECTION_HINTS}

    def _format_warnings(self, text: str) -> list:
        warnings = []
        sections = ["experience", "education", "skills", "projects"]
        for s in sections:
            if s not in text.lower():
                warnings.append(f"Section '{s}' is missing")
        if not re.search(r"\b[\w.-]+@[\w.-]+\.\w{2,4}\b", text):
            warnings.append("No valid email found")
        if not re.search(r"\+?\d[\d\s-]{7,}\d", text):
            warnings.append("No valid phone number found")
        if len(re.findall(r"[\u2022\-*]", text)) < 3:
            warnings.append("Few bullet points; consider using bullets for clarity")
        return warnings

    # ── Suggestions ───────────────────────────────────────────────────────────

    def _suggestions(self, warnings: list, missing: set, keyword_score: float, format_score: float) -> list:
        s = []
        if warnings:
            s.append("Fix formatting issues: " + "; ".join(warnings))
        if missing:
            top = sorted(list(missing))[:10]
            s.append("Add missing keywords: " + ", ".join(top))
        if keyword_score < 50 or format_score < 50:
            s.append("⚠️ CV has low match or poor format — review carefully before applying.")
        return s

    # ── Main analysis ─────────────────────────────────────────────────────────

    def analyze(self, cv_text: str, offer_text: str) -> dict:
        """
        Full ATS analysis — mirrors compute_score() from the ATS Checker project.

        Weights  (from scoring.py defaults):
          keywords     65 %
          completeness 20 %
          format       15 %
        """
        resume_kws = self._extract_keywords(cv_text)
        jd_kws     = self._extract_keywords(offer_text)

        matched, missing = self._semantic_match(resume_kws, jd_kws)

        # Subscores
        kw_score   = (len(matched) / max(1, len(jd_kws))) * 100
        sect       = self._section_completeness(cv_text)
        comp_score = (sum(1 for v in sect.values() if v) / len(sect)) * 100
        warnings   = self._format_warnings(cv_text)
        fmt_score  = max(0.0, 100.0 - 25.0 * len(warnings))

        final_score = round(0.65 * kw_score + 0.20 * comp_score + 0.15 * fmt_score, 1)

        suggestions = self._suggestions(warnings, missing, kw_score, fmt_score)

        return {
            "ats_score":        final_score,
            "keyword_score":    round(kw_score, 1),
            "format_score":     round(fmt_score, 1),
            "completeness_score": round(comp_score, 1),
            "matched_keywords": sorted(list(matched)),
            "missing_keywords": sorted(list(missing)),
            "warnings":         warnings,
            "sections":         sect,
            "suggestions":      suggestions,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
ats_service = ATSService()


# ── Async wrapper used by routers/ats.py ─────────────────────────────────────
async def analyze_cv_for_ats(
    cv_text: str,
    offer_text: Optional[str] = None,
) -> dict:
    if not offer_text:
        offer_text = (
            "skills experience python sql data analysis machine learning "
            "communication teamwork project management agile problem solving"
        )
    return ats_service.analyze(cv_text, offer_text)