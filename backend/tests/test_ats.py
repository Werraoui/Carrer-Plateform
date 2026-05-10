"""
test_ats.py — tests for ATSService (ported ATS Checker logic)

Run with:
    cd backend
    pytest tests/test_ats.py -v
"""

import pytest
from app.services.ats_service import ats_service, analyze_cv_for_ats


# ── _extract_keywords ─────────────────────────────────────────────────────────

def test_extract_keywords_returns_set():
    result = ats_service._extract_keywords("Python developer with SQL experience")
    assert isinstance(result, set)

def test_extract_keywords_removes_stopwords():
    result = ats_service._extract_keywords("and the for with by to of")
    assert result == set()

def test_extract_keywords_keeps_meaningful_words():
    result = ats_service._extract_keywords("Python SQL FastAPI")
    assert "python" in result
    assert "sql" in result
    assert "fastapi" in result

def test_extract_keywords_lowercases():
    result = ats_service._extract_keywords("PYTHON Django REST")
    assert "python" in result
    assert "django" in result

def test_extract_keywords_removes_single_chars():
    result = ats_service._extract_keywords("a b c python")
    assert "a" not in result
    assert "b" not in result
    assert "python" in result


# ── _semantic_match ───────────────────────────────────────────────────────────

def test_semantic_match_exact_overlap():
    matched, missing = ats_service._semantic_match(
        {"python", "sql", "fastapi"},
        {"python", "sql", "docker"}
    )
    assert "python" in matched
    assert "sql" in matched
    assert "docker" in missing

def test_semantic_match_no_overlap():
    matched, missing = ats_service._semantic_match(
        {"html", "css", "react"},
        {"python", "sql", "spark"}
    )
    # at minimum all jd terms start as missing (semantic may recover some)
    assert len(matched) + len(missing) == 3

def test_semantic_match_full_overlap():
    kws = {"python", "sql", "docker"}
    matched, missing = ats_service._semantic_match(kws, kws)
    assert matched == kws
    assert len(missing) == 0

def test_semantic_match_returns_two_sets():
    result = ats_service._semantic_match({"python"}, {"python", "java"})
    assert isinstance(result, tuple)
    assert len(result) == 2


# ── _section_completeness ─────────────────────────────────────────────────────

def test_section_completeness_all_present():
    text = "experience education skills projects certification summary"
    result = ats_service._section_completeness(text)
    assert all(result.values())

def test_section_completeness_none_present():
    result = ats_service._section_completeness("hello world python")
    assert not any(result.values())

def test_section_completeness_returns_dict():
    result = ats_service._section_completeness("some cv text")
    assert isinstance(result, dict)
    assert "experience" in result
    assert "education" in result
    assert "skills" in result

def test_section_completeness_case_insensitive():
    result = ats_service._section_completeness("EXPERIENCE Education SKILLS")
    assert result["experience"] is True
    assert result["education"] is True
    assert result["skills"] is True


# ── _format_warnings ──────────────────────────────────────────────────────────

def test_format_warnings_clean_cv():
    text = """
    experience education skills projects
    john@example.com
    +1 234 567 8901
    - built apis
    - managed teams
    - deployed services
    """
    warnings = ats_service._format_warnings(text)
    assert len(warnings) == 0

def test_format_warnings_missing_sections():
    warnings = ats_service._format_warnings("just some random text with no structure")
    section_warns = [w for w in warnings if "missing" in w.lower()]
    assert len(section_warns) > 0

def test_format_warnings_no_email():
    text = "experience education skills projects - bullet - bullet - bullet +1234567890"
    warnings = ats_service._format_warnings(text)
    assert any("email" in w.lower() for w in warnings)

def test_format_warnings_no_phone():
    text = "experience education skills projects - bullet - bullet - bullet john@test.com"
    warnings = ats_service._format_warnings(text)
    assert any("phone" in w.lower() for w in warnings)

def test_format_warnings_no_bullets():
    text = "experience education skills projects john@test.com +1234567890"
    warnings = ats_service._format_warnings(text)
    assert any("bullet" in w.lower() for w in warnings)

def test_format_warnings_returns_list():
    assert isinstance(ats_service._format_warnings("some text"), list)


# ── analyze (main function) ───────────────────────────────────────────────────

def test_analyze_returns_all_keys():
    result = ats_service.analyze(
        cv_text="Python SQL developer with pandas experience",
        offer_text="We need a Python SQL Spark AWS engineer"
    )
    expected_keys = {
        "ats_score", "keyword_score", "format_score", "completeness_score",
        "matched_keywords", "missing_keywords", "warnings", "sections", "suggestions"
    }
    assert expected_keys.issubset(result.keys())

def test_analyze_score_between_0_and_100():
    result = ats_service.analyze("Python SQL", "Python SQL Spark AWS")
    assert 0.0 <= result["ats_score"] <= 100.0

def test_analyze_subscores_between_0_and_100():
    result = ats_service.analyze("Python SQL developer", "Python SQL Spark AWS engineer")
    assert 0.0 <= result["keyword_score"]     <= 100.0
    assert 0.0 <= result["format_score"]      <= 100.0
    assert 0.0 <= result["completeness_score"] <= 100.0

def test_analyze_matched_keywords_are_list():
    result = ats_service.analyze("Python SQL", "Python SQL Spark")
    assert isinstance(result["matched_keywords"], list)

def test_analyze_missing_keywords_are_list():
    result = ats_service.analyze("Python SQL", "Python SQL Spark")
    assert isinstance(result["missing_keywords"], list)

def test_analyze_suggestions_are_list():
    result = ats_service.analyze("Python SQL", "Python SQL Spark")
    assert isinstance(result["suggestions"], list)

def test_analyze_warnings_are_list():
    result = ats_service.analyze("Python SQL", "Python SQL Spark")
    assert isinstance(result["warnings"], list)

def test_analyze_sections_are_dict():
    result = ats_service.analyze("Python SQL", "Python SQL Spark")
    assert isinstance(result["sections"], dict)

def test_analyze_perfect_match_no_missing():
    cv   = "python sql spark airflow docker"
    offer = "python sql spark airflow docker"
    result = ats_service.analyze(cv, offer)
    assert len(result["missing_keywords"]) == 0

def test_analyze_empty_cv_low_score():
    result = ats_service.analyze(
        cv_text="I am motivated and hardworking",
        offer_text="Python SQL Spark AWS Docker Kubernetes"
    )
    assert result["ats_score"] < 50
    assert len(result["missing_keywords"]) > 0

def test_analyze_good_cv_higher_score_than_bad():
    good = ats_service.analyze(
        cv_text="Python SQL Spark AWS Docker experience education skills projects john@test.com +1234567890 - built - managed - deployed",
        offer_text="Python SQL Spark AWS Docker"
    )
    bad = ats_service.analyze(
        cv_text="I enjoy cooking and hiking",
        offer_text="Python SQL Spark AWS Docker"
    )
    assert good["ats_score"] > bad["ats_score"]

def test_analyze_suggestions_appear_when_keywords_missing():
    result = ats_service.analyze(
        cv_text="I am a motivated individual",
        offer_text="Python SQL Spark AWS Docker"
    )
    assert len(result["suggestions"]) > 0

def test_analyze_format_warnings_included_in_suggestions():
    result = ats_service.analyze(
        cv_text="just some plain text no structure",
        offer_text="Python SQL developer"
    )
    # format issues exist → should appear in suggestions
    if result["warnings"]:
        assert any("format" in s.lower() or "section" in s.lower() or "fix" in s.lower()
                   for s in result["suggestions"])


# ── analyze_cv_for_ats (async wrapper) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_async_wrapper_returns_dict():
    result = await analyze_cv_for_ats(
        cv_text="Python SQL developer with experience",
        offer_text="Python SQL Spark AWS"
    )
    assert isinstance(result, dict)
    assert "ats_score" in result

@pytest.mark.asyncio
async def test_async_wrapper_no_offer_uses_fallback():
    # Without offer_text it should still run (uses generic fallback)
    result = await analyze_cv_for_ats(cv_text="Python SQL developer")
    assert isinstance(result, dict)
    assert 0.0 <= result["ats_score"] <= 100.0

@pytest.mark.asyncio
async def test_async_wrapper_with_offer():
    result = await analyze_cv_for_ats(
        cv_text="Python SQL Spark developer with education and skills",
        offer_text="Python SQL Spark AWS data engineer"
    )
    assert "matched_keywords" in result
    assert "python" in result["matched_keywords"]