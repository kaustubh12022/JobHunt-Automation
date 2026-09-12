"""
Milestone 3 Challenger 2 Adversarial Stress Test Suite:
1. Zero Wasted Calls:
   - Senior / Lead / Staff / Principal / Level / Roman numeral title rejection.
   - Leakage check on out-of-scope stacks (PHP, Ruby, iOS) with realistic JDs (mentioning unit testing, APIs, Git).
2. Token Accounting:
   - Summation over 10 scored jobs where only 2 are shortlisted (verified in save_pipeline_results).
   - Slicing boundary leak: demonstrates token loss when scored_jobs is sliced (e.g. in run.py, app.py, test_pipeline.py).
3. JSON Error Handling:
   - Markdown-wrapped JSON (```json ... ```).
   - Truncated / malformed JSON recovery.
   - String match_score type crash ('85' vs 60).
   - Missing fields and null content handling.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.models import Job
from src.ai_engine import call_ai_scoring_async, TokenUsage
from src.scorer import (
    score_jobs,
    matches_senior_title,
    requires_3_plus_years,
    is_relevant_jd,
    ScoredJobList,
)
from src.db import save_pipeline_results


# ==============================================================================
# SECTION 1: Zero Wasted AI Calls (Senior & Out-of-Scope Roles)
# ==============================================================================

def test_adversarial_senior_lead_staff_principal_blocked():
    """Verify matches_senior_title blocks senior, lead, staff, principal, and corporate level designations."""
    senior_titles = [
        "Senior Software Engineer",
        "Lead QA Engineer",
        "Staff Software Engineer",
        "Principal Software Engineer",
        "Director of Engineering",
        "Engineering Manager",
        "VP of Technology",
        "Software Architect",
        "Software Engineer II",
        "Software Engineer III",
        "Software Engineer IV",
        "Software Engineer Level 2",
        "Software Engineer Level 3",
        "Software Engineer L2",
        "Software Engineer L3",
        "Software Engineer (3-5 years)",
        "Software Engineer (5+ years)",
        "Tech Lead",
        "Team Lead",
        "Head of QA",
        "Sr. Software Engineer",
        "Sr Software Engineer",
        "Sr. QA Automation Engineer",
    ]
    for title in senior_titles:
        assert matches_senior_title(title) is True, f"Failed to block senior/lead role: {title}"


def test_adversarial_fresher_roles_not_blocked():
    """Verify matches_senior_title preserves legitimate entry-level and fresher titles."""
    fresher_titles = [
        "Software Engineer I",
        "QA Engineer Level 1",
        "Junior Developer",
        "Associate Software Engineer",
        "Graduate Engineer Trainee",
        "Software Developer (0-2 years)",
        "QA Tester (1-3 yrs)",
        "Python Developer Trainee",
        "Software Engineer - Fresher",
    ]
    for title in fresher_titles:
        assert matches_senior_title(title) is False, f"Wrongly blocked fresher role: {title}"


def test_adversarial_senior_roles_zero_ai_calls():
    """Verify senior/lead/staff/principal roles are filtered out before reaching AI scoring."""
    senior_jobs = [
        Job(title="Senior Java Developer", company="C1", location="Pune", description="Java Spring REST APIs SQL", url="http://s1"),
        Job(title="Lead Automation Engineer", company="C2", location="Pune", description="Selenium Python automation testing", url="http://s2"),
        Job(title="Staff Software Engineer", company="C3", location="Pune", description="Backend microservices Java", url="http://s3"),
        Job(title="Principal QA Architect", company="C4", location="Pune", description="QA architecture testing Selenium", url="http://s4"),
        Job(title="Software Engineer II", company="C5", location="Pune", description="Java Spring development", url="http://s5"),
        Job(title="QA Engineer Level 2", company="C6", location="Pune", description="Automated testing Python SQL", url="http://s6"),
    ]
    ai_calls = []
    async def mock_ai(prompt):
        ai_calls.append(prompt)
        return json.dumps({"match_score": 80, "missing_skills": []}), 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None):
        results = score_jobs(senior_jobs)

    assert len(ai_calls) == 0, f"Leak detected! Expected 0 AI calls for senior roles, but got {len(ai_calls)}"
    assert len(results) == 0


def test_adversarial_outofscope_stacks_leakage_reproduction():
    """
    CRITICAL EMPIRICAL CHALLENGE:
    Out-of-scope stacks (PHP, Ruby on Rails, iOS Swift) with realistic JDs
    mentioning standard software engineering responsibilities ('unit testing', 'REST APIs', 'Git', 'MySQL').
    Reveals that is_relevant_jd matches generic 'test' and tech tools, leaking these jobs to AI scoring.
    """
    outofscope_jobs = [
        Job(
            title="iOS Developer",
            company="MobileCo",
            location="Pune",
            description="Develop iOS applications using Swift and UIKit. Write automated unit tests for code. Work with REST APIs and Git.",
            url="http://ios1.com"
        ),
        Job(
            title="PHP Developer",
            company="WebCo",
            location="Pune",
            description="Develop backend features in Laravel and PHP. Design MySQL database schemas. Write test cases for APIs. Maintain Git repository.",
            url="http://php1.com"
        ),
        Job(
            title="Ruby on Rails Developer",
            company="RubyCo",
            location="Pune",
            description="Build scalable web applications with Ruby on Rails. Maintain automated test suites using RSpec. Integrate RESTful APIs.",
            url="http://ruby1.com"
        ),
    ]

    ai_calls = []
    async def mock_ai(prompt):
        ai_calls.append(prompt)
        return json.dumps({"match_score": 15, "missing_skills": ["Java", "QA"]}), 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None):
        results = score_jobs(outofscope_jobs)

    # After remediation: out-of-scope roles are filtered before AI scoring (zero wasted calls)
    assert len(ai_calls) == 0, f"Expected 0 AI calls for out-of-scope roles, got {len(ai_calls)}"
    assert len(results) == 0


# ==============================================================================
# SECTION 2: Token Accounting & Summation Invariants
# ==============================================================================

def test_adversarial_token_accounting_10_scored_2_shortlisted():
    """
    Verify save_pipeline_results accounts for ALL 10 scored jobs when only 2 are shortlisted
    and passed via ScoredJobList.
    """
    mock_jobs = [
        Job(title=f"QA Tester {i}", company=f"Company {i}", location="Pune", description="Selenium Python testing SQL", url=f"http://job{i}.com")
        for i in range(10)
    ]

    ai_call_idx = 0
    async def mock_ai(prompt):
        nonlocal ai_call_idx
        ai_call_idx += 1
        score = 80 if ai_call_idx <= 2 else 40
        return json.dumps({"match_score": score, "reason": "test", "missing_skills": []}), {
            "total_tokens": 150,
            "prompt_tokens": 100,
            "prompt_cache_hit_tokens": 80,
            "prompt_cache_miss_tokens": 20,
            "completion_tokens": 50,
            "cost_usd": 0.0001
        }

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None):
        shortlisted = score_jobs(mock_jobs)

    assert len(shortlisted) == 2
    assert hasattr(shortlisted, "all_scored_jobs")
    assert len(shortlisted.all_scored_jobs) == 10

    # Test DB persistence with ScoredJobList
    captured_payloads = []
    def fake_insert(payload):
        captured_payloads.append(dict(payload))
        m = MagicMock()
        m.execute.return_value.data = [{"id": "run-1"}]
        return m

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.side_effect = fake_insert
    pipeline_state = {"mode": "test", "scan": {"total_found": 10}, "filter": {"after": 10}}

    with patch("src.db.supabase", mock_sb):
        save_pipeline_results(pipeline_state, shortlisted, ["pdf1.pdf", "pdf2.pdf"])

    run_payload = captured_payloads[0]
    assert run_payload["tokens_used"] == 1500, f"Expected 1500 tokens across all 10 jobs, got {run_payload['tokens_used']}"
    assert run_payload["ai_metrics"]["total_tokens"] == 1500
    assert run_payload["ai_metrics"]["jobs_scored_count"] == 10
    assert run_payload["ai_metrics"]["jobs_shortlisted_count"] == 2
    assert run_payload["ai_metrics"]["total_cost_usd"] == pytest.approx(0.001, rel=1e-4)


def test_adversarial_token_accounting_slice_leak_reproduction():
    """
    CRITICAL EMPIRICAL CHALLENGE:
    Demonstrates that slicing scored_jobs (e.g. scored_jobs[:top_n] in run.py, app.py, test_pipeline.py)
    strips the all_scored_jobs attribute because ScoredJobList does not override __getitem__.
    This causes save_pipeline_results to silently drop 90% of token accounting.
    """
    all_scored = [
        Job(title=f"Job {i}", company=f"C{i}", location="Pune", description="QA", url=f"http://{i}", score=80 if i < 2 else 40)
        for i in range(10)
    ]
    for j in all_scored:
        j.tokens_used = 150
        j.cost_usd = 0.0001
        j.token_usage = {"prompt_tokens": 100, "completion_tokens": 50}

    scored_jobs = ScoredJobList(all_scored[:2], all_scored_jobs=all_scored)

    # In run.py lines 123-124:
    top_n = 3
    shortlisted = scored_jobs[:top_n]      # Slices ScoredJobList -> returns plain list!
    tailor_targets = shortlisted[:1]       # In test mode, takes first job

    # Slicing retains ScoredJobList and all_scored_jobs attribute
    assert isinstance(shortlisted, ScoredJobList)
    assert hasattr(shortlisted, "all_scored_jobs"), "Expected all_scored_jobs attribute on sliced shortlist"
    assert len(shortlisted.all_scored_jobs) == 10
    assert hasattr(tailor_targets, "all_scored_jobs"), "Expected all_scored_jobs attribute on sliced tailor_targets"
    assert len(tailor_targets.all_scored_jobs) == 10

    captured_payloads = []
    def fake_insert(payload):
        captured_payloads.append(dict(payload))
        m = MagicMock()
        m.execute.return_value.data = [{"id": "run-1"}]
        return m

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.side_effect = fake_insert
    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 10},
        "filter": {"after": 10},
        "score": {"scored": len(scored_jobs), "shortlisted": len(shortlisted)}
    }

    with patch("src.db.supabase", mock_sb):
        # When tailor_targets is passed as in run.py line 207:
        save_pipeline_results(pipeline_state, tailor_targets, ["pdf1.pdf"])

    run_payload = captured_payloads[0]
    # Slicing preservation + fallback ensures all 1500 tokens across all 10 scored jobs are accounted for:
    assert run_payload["tokens_used"] == 1500, f"Expected 1500 tokens across all 10 jobs, got {run_payload['tokens_used']}"
    assert run_payload["ai_metrics"]["jobs_scored_count"] == 10


# ==============================================================================
# SECTION 3: JSON Error Handling & Resiliency
# ==============================================================================

def test_adversarial_json_markdown_wrapped_successful():
    """Verify markdown code block wrapped JSON is successfully extracted and parsed."""
    wrapped_json = "```json\n{\n  \"match_score\": 78,\n  \"missing_skills\": [\"Docker\"],\n  \"reason\": \"Strong Java skills\"\n}\n```"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=wrapped_json))]
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=80, prompt_cache_hit_tokens=64, prompt_cache_miss_tokens=16, completion_tokens=20)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_client.close = AsyncMock()

    async def run():
        with patch("src.ai_engine._get_async_client", return_value=(mock_client, "deepseek-chat")):
            content, tokens = await call_ai_scoring_async("Score this JD")
            parsed = json.loads(content)
            assert parsed["match_score"] == 78
            assert parsed["missing_skills"] == ["Docker"]

    import asyncio
    asyncio.run(run())


def test_adversarial_json_with_preamble_and_postscript():
    """Verify JSON with conversational preamble and postscript is cleanly extracted."""
    noisy_response = (
        "Here is the evaluation of the candidate for this position:\n\n"
        "```json\n"
        "{\"match_score\": 92, \"reason\": \"Excellent QA fit\", \"missing_skills\": []}\n"
        "```\n\n"
        "Please let me know if you need further evaluation."
    )

    job = Job(title="QA Trainee", company="TechCorp", location="Pune", description="Selenium and Python testing", url="http://t1")
    async def mock_ai(p):
        return noisy_response, 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None):
        scored = score_jobs([job])

    assert len(scored) == 1
    assert scored[0].score == 92
    assert scored[0].reasons == "Excellent QA fit"


def test_adversarial_corrupted_truncated_json_does_not_crash_pipeline():
    """Verify corrupted / truncated JSON is safely caught and does not crash score_jobs."""
    truncated_json = "{\"match_score\": 85, \"reason\": \"Incomplete"

    job = Job(title="QA Trainee", company="TechCorp", location="Pune", description="Selenium and Python testing", url="http://t2")
    async def mock_ai(p):
        return truncated_json, 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None):
        scored = score_jobs([job])

    # Should return empty list because truncated JSON could not be parsed
    assert len(scored) == 0


def test_adversarial_string_match_score_coerced_without_crash():
    """
    Verify that if LLM returns a string score ('85' instead of int 85),
    safe coercion int(float(raw_score)) safely converts it to int 85 without crashing with TypeError.
    """
    string_score_json = json.dumps({"match_score": "85", "missing_skills": []})

    job = Job(title="QA Trainee", company="TechCorp", location="Pune", description="Selenium and Python testing", url="http://t3")
    async def mock_ai(p):
        return string_score_json, 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None):
        scored = score_jobs([job])

    assert len(scored) == 1
    assert scored[0].score == 85


# Backward-compatible alias for test runners expecting the original name
test_adversarial_string_match_score_crashes_pipeline_reproduction = test_adversarial_string_match_score_coerced_without_crash


def test_adversarial_missing_match_score_fallback():
    """Verify that if 'match_score' key is missing, fallback to 'score' key or 0 is handled."""
    # LLM returns alternative key 'score' instead of 'match_score'
    alt_json = json.dumps({"score": 75, "missing_skills": []})
    job = Job(title="QA Trainee", company="TechCorp", location="Pune", description="Selenium and Python testing", url="http://t4")
    async def mock_ai(p):
        return alt_json, 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None):
        scored = score_jobs([job])

    assert len(scored) == 1
    assert scored[0].score == 75
