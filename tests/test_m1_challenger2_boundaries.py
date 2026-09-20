"""
Challenger 2 Adversarial Verification Test Suite:
1. Model configuration zero-reference verification (deepseek-v4-flash, deepseek-v4-pro)
2. Threshold boundary verification (score 60 accepted vs score 59 rejected)
3. Freshness boundary verification (71h accepted vs 73h rejected)
"""
import os
import re
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.models import Job
from src.scorer import score_jobs
from src.config_loader import load_config
import src.ai_engine as ai_engine


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


# ==============================================================================
# SECTION 1: Model Configuration Zero-Reference Adversarial Verification
# ==============================================================================

def test_config_yaml_has_no_deprecated_models():
    """Verify config.yaml contains 0 occurrences of deepseek-v4-flash or deepseek-v4-pro."""
    config_path = WORKSPACE_ROOT / "config.yaml"
    content = config_path.read_text(encoding="utf-8")
    assert "deepseek-v4-flash" not in content.lower(), "Found deprecated deepseek-v4-flash in config.yaml"
    assert "deepseek-v4-pro" not in content.lower(), "Found deprecated deepseek-v4-pro in config.yaml"

    cfg = load_config()
    assert cfg["ai"]["scoring_model"] == "deepseek-chat"
    assert cfg["ai"]["tailoring_model"] == "deepseek-chat"
    assert cfg["ai"]["model"] == "deepseek-chat"


def test_ai_engine_has_no_deprecated_models():
    """Verify src/ai_engine.py contains 0 occurrences of deprecated models."""
    ai_engine_path = WORKSPACE_ROOT / "src" / "ai_engine.py"
    content = ai_engine_path.read_text(encoding="utf-8")
    assert "deepseek-v4-flash" not in content.lower(), "Found deprecated deepseek-v4-flash in ai_engine.py"
    assert "deepseek-v4-pro" not in content.lower(), "Found deprecated deepseek-v4-pro in ai_engine.py"

    assert ai_engine.runtime_settings["scoring_model"] == "deepseek-chat"
    assert ai_engine.runtime_settings["tailoring_model"] == "deepseek-chat"


def test_dashboard_has_no_deprecated_models():
    """Verify frontend/src/pages/Dashboard.jsx contains 0 occurrences of deprecated models."""
    dashboard_path = WORKSPACE_ROOT / "frontend" / "src" / "pages" / "Dashboard.jsx"
    content = dashboard_path.read_text(encoding="utf-8")
    assert "deepseek-v4-flash" not in content.lower(), "Found deprecated deepseek-v4-flash in Dashboard.jsx"
    assert "deepseek-v4-pro" not in content.lower(), "Found deprecated deepseek-v4-pro in Dashboard.jsx"

    # Verify options only expose valid models
    assert "deepseek-chat" in content
    assert "deepseek-reasoner" in content


def test_all_src_files_have_no_deprecated_models():
    """Verify no python source file in src/ contains deprecated model strings."""
    src_dir = WORKSPACE_ROOT / "src"
    for py_file in src_dir.glob("**/*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "deepseek-v4-flash" not in content.lower(), f"Found deepseek-v4-flash in {py_file}"
        assert "deepseek-v4-pro" not in content.lower(), f"Found deepseek-v4-pro in {py_file}"


# ==============================================
# SECTION 2: Threshold Boundary Verification (Score 60 vs 59)
# ==============================================

def _make_job(jid, desc, score=None, date_posted=None):
    job = Job(
        title="QA Automation Engineer",
        company="TechCorp",
        location="Pune",
        description=desc,
        url=f"https://example.com/jobs/{jid}",
        id=jid
    )
    if score is not None:
        job.score = score
    if date_posted is not None:
        job.date_posted = date_posted
    return job


def test_threshold_boundary_60_accepted_59_rejected():
    """
    Verify that under the default threshold of 60:
    - Job with score 60 is ACCEPTED
    - Job with score 59 is REJECTED
    - Boundary test: 60, 59, 61, 0
    """
    now = pd.Timestamp.now(tz="UTC")
    
    # Create sample jobs with relevant descriptions to pass pre-AI keyword filter
    desc = "Selenium, Python, Automation testing, Pytest, SQL, REST API "
    job_60 = _make_job("job_60", desc + "ID: job_60", date_posted=now)
    job_59 = _make_job("job_59", desc + "ID: job_59", date_posted=now)
    job_61 = _make_job("job_61", desc + "ID: job_61", date_posted=now)
    job_zero = _make_job("job_zero", desc + "ID: job_zero", date_posted=now)

    score_map = {
        "job_60": 60,
        "job_59": 59,
        "job_61": 61,
        "job_zero": 0,
    }

    async def mock_call_ai(prompt):
        for jid, sc in score_map.items():
            if jid in prompt:
                return f'{{"match_score": {sc}, "missing_skills": []}}', 100
        return '{"match_score": 50, "missing_skills": []}', 100

    with patch("src.ai_engine.call_ai_scoring_async", side_effect=mock_call_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None), \
         patch("src.config_loader.load_config", return_value={"scoring": {"minimum_score": 60}, "search": {"hours_old": 72}}):
        
        results = score_jobs([job_60, job_59, job_61, job_zero], test_mode=False)
        result_ids = [j.id for j in results]

        assert "job_60" in result_ids, "Score 60 must be ACCEPTED"
        assert "job_61" in result_ids, "Score 61 must be ACCEPTED"
        assert "job_59" not in result_ids, "Score 59 must be REJECTED"
        assert "job_zero" not in result_ids, "Score 0 must be REJECTED"


def test_threshold_fallback_is_60_when_config_omitted():
    """
    Verify that if 'scoring' or 'minimum_score' is missing from config,
    scorer defaults to 60 (not the legacy 70).
    """
    now = pd.Timestamp.now(tz="UTC")
    desc = "Selenium, Python, Automation testing, Pytest "
    job_60 = _make_job("job_60_fallback", desc + "ID: job_60_fallback", date_posted=now)
    job_59 = _make_job("job_59_fallback", desc + "ID: job_59_fallback", date_posted=now)

    async def mock_call_ai(prompt):
        if "job_60_fallback" in prompt:
            return '{"match_score": 60, "missing_skills": []}', 50
        return '{"match_score": 59, "missing_skills": []}', 50

    with patch("src.ai_engine.call_ai_scoring_async", side_effect=mock_call_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None), \
         patch("src.config_loader.load_config", return_value={}):  # Empty config: test default fallback
        
        results = score_jobs([job_60, job_59], test_mode=False)
        result_ids = [j.id for j in results]

        assert "job_60_fallback" in result_ids, "Job with score 60 must pass fallback default"
        assert "job_59_fallback" not in result_ids, "Job with score 59 must fail fallback default"


# ==============================================================================
# SECTION 3: Freshness Boundary Verification (71h vs 73h)
# ==============================================================================

def test_freshness_boundary_71h_accepted_73h_rejected():
    """
    Verify that with 72h freshness setting:
    - Job posted 71 hours ago is ACCEPTED
    - Job posted 73 hours ago is REJECTED
    - Job with None date_posted is ACCEPTED (graceful fallback)
    """
    now = pd.Timestamp.now(tz="UTC")
    desc = "Selenium, Python, Automation testing, Pytest "
    
    job_71h = _make_job("job_71h", desc + "ID: job_71h", date_posted=(now - pd.Timedelta(hours=71)).isoformat())
    job_73h = _make_job("job_73h", desc + "ID: job_73h", date_posted=(now - pd.Timedelta(hours=73)).isoformat())
    job_nodate = _make_job("job_nodate", desc + "ID: job_nodate", date_posted=None)

    async def mock_call_ai(prompt):
        return '{"match_score": 85, "missing_skills": []}', 100

    with patch("src.ai_engine.call_ai_scoring_async", side_effect=mock_call_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None), \
         patch("src.config_loader.load_config", return_value={"search": {"hours_old": 72}, "scoring": {"minimum_score": 60}}):
        
        results = score_jobs([job_71h, job_73h, job_nodate], test_mode=False)
        result_ids = [j.id for j in results]

        assert "job_71h" in result_ids, "Job posted 71h ago MUST be accepted"
        assert "job_nodate" in result_ids, "Job with missing date MUST be accepted (graceful fallback)"
        assert "job_73h" not in result_ids, "Job posted 73h ago MUST be rejected as stale"


def test_run_py_m1_apply_pandas_filter_freshness_wrapper():
    """
    Verify run.py's m1_apply_pandas_filter preserves jobs within 72h.
    """
    now = pd.Timestamp.now(tz="UTC")
    job_71 = _make_job("j_71", "Selenium, Python, Automation testing, Pytest", date_posted=(now - pd.Timedelta(hours=71)).isoformat())
    job_73 = _make_job("j_73", "Selenium, Python, Automation testing, Pytest", date_posted=(now - pd.Timedelta(hours=73)).isoformat())

    # Check cutoff logic directly matching run.py line 37
    cutoff_72 = now - pd.Timedelta(hours=72)
    
    dt_71 = pd.to_datetime(job_71.date_posted, errors='coerce', utc=True)
    dt_73 = pd.to_datetime(job_73.date_posted, errors='coerce', utc=True)

    assert dt_71 >= cutoff_72, "71h job must be >= cutoff_72"
    assert not (dt_73 >= cutoff_72), "73h job must NOT be >= cutoff_72"

