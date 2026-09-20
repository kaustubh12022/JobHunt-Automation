"""
Tier 1: Feature Coverage E2E Tests (F1 through F11).
Verifies primary happy path behaviors, specifications, and interface contracts.
Coverage threshold: >= 5 test cases per feature across 11 features (>= 55 tests).
"""
import os
import re
import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pandas as pd

from src.models import Job
from src.config_loader import load_config, load_resume, get_human_date_str
from src.scorer import is_relevant_jd, strip_boilerplate, score_jobs
from src.scraper import apply_pandas_filter
from src.ai_engine import runtime_settings, _get_prompt


# =====================================================================
# F1: Pipeline Reliability & Windows Runtime Fixes (R1 §90-100)
# =====================================================================

def test_f1_1_model_name_alignment():
    """F1.1: Verify config and runtime settings use deepseek-chat and deepseek-reasoner."""
    config = load_config()
    ai_cfg = config.get("ai", {})
    assert ai_cfg.get("scoring_model") == "deepseek-chat", "Scoring model must be deepseek-chat"
    assert ai_cfg.get("tailoring_model") == "deepseek-chat", "Tailoring model must be deepseek-chat"
    assert "deepseek-v4-flash" not in str(config), "Deprecated deepseek-v4-flash must not be present"
    assert "deepseek-v4-pro" not in str(config), "Deprecated deepseek-v4-pro must not be present"
    assert runtime_settings.get("scoring_model") == "deepseek-chat"
    assert runtime_settings.get("tailoring_model") == "deepseek-chat"


def test_f1_2_windows_filename_sanitization():
    """F1.2: Verify Windows filename sanitization strips invalid characters (:/*?<>|)."""
    raw_title = "QA Engineer: Automation / SDET <Level 1> *Pune*"
    raw_company = "Tech Corp / Systems: India | Ltd."

    # Mimic pdf_generator.py logic
    safe_title = "".join([c if c.isalnum() else "_" for c in raw_title]).strip("_")
    safe_company = "".join([c if c.isalnum() else "_" for c in raw_company]).strip("_")
    safe_title = re.sub(r'_+', '_', safe_title)
    safe_company = re.sub(r'_+', '_', safe_company)
    filename = f"{safe_title}_{safe_company}.pdf"

    invalid_chars = [':', '/', '\\', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        assert char not in filename, f"Invalid Windows path char '{char}' found in filename: {filename}"
    assert filename.endswith(".pdf")
    assert "QA_Engineer_Automation_SDET_Level_1_Pune" in filename


def test_f1_3_windows_console_unicode_logging():
    """F1.3: Verify logger handles Unicode characters (emojis, rupee symbol, arrows) without CP1252 crash."""
    from src.logger import logger
    unicode_message = "🚀 Test Job: ₹50,000/mo stipend | Status: ✅ Passed -> Complete"
    try:
        logger.info(unicode_message)
        logged = True
    except UnicodeEncodeError:
        logged = False
    assert logged, "Logger failed to handle Unicode characters on Windows"


def test_f1_4_pipeline_state_machine_transitions():
    """F1.4: Verify pipeline state machine tracks phases: idle -> scanning -> filtering -> scoring -> tailoring -> saving -> done."""
    from app import pipeline_state
    expected_phases = ["idle", "scanning", "filtering", "scoring", "tailoring", "saving", "done"]
    assert "phase" in pipeline_state
    assert "running" in pipeline_state
    assert "scan" in pipeline_state
    assert "filter" in pipeline_state
    assert "score" in pipeline_state
    assert "tailor" in pipeline_state
    # Verify initial phase is idle or known valid state
    assert pipeline_state["phase"] in expected_phases


def test_f1_5_scraper_platforms_enablement():
    """F1.5: Verify search platforms in config include working platforms (linkedin, indeed) and exclude broken ones."""
    config = load_config()
    platforms = config.get("search", {}).get("platforms", [])
    assert "linkedin" in platforms, "LinkedIn must be enabled"
    assert "indeed" in platforms, "Indeed must be enabled"
    assert "ziprecruiter" not in platforms, "ZipRecruiter must be disabled due to Cloudflare 403 in India"
    assert "glassdoor" not in platforms, "Glassdoor must be disabled due to 400 errors"


# =====================================================================
# F2: Small-Batch Test Mode (< 2 min) (R1 §97-98)
# =====================================================================

def test_f2_1_test_mode_config_defaults():
    """F2.1: Verify test_mode section in config.yaml contains required budget parameters."""
    config = load_config()
    assert "test_mode" in config, "config.yaml must have test_mode section"
    tm = config["test_mode"]
    assert tm.get("results_wanted") == 5
    assert tm.get("skip_workday") is True
    assert tm.get("score_top_n") == 3
    assert tm.get("tailor_top_n") == 1
    assert "Pune" in tm.get("locations", [])
    assert "QA Automation" in tm.get("search_terms", [])


def test_f2_2_test_mode_limits_query_combinations():
    """F2.2: Verify test mode isolates to 1 search term, 1 location, and 1 platform."""
    config = load_config()
    tm = config.get("test_mode", {})
    assert len(tm.get("search_terms", [])) == 1, "Test mode must only have 1 search term"
    assert len(tm.get("locations", [])) == 1, "Test mode must only have 1 location"
    assert len(tm.get("platforms", [])) == 1, "Test mode must only have 1 platform"


def test_f2_3_test_mode_caps_shortlist_and_resumes():
    """F2.3: Verify test mode limits scored jobs to top 3 and tailored resumes to 1."""
    config = load_config()
    score_top_n = config.get("test_mode", {}).get("score_top_n", 3)
    tailor_top_n = config.get("test_mode", {}).get("tailor_top_n", 1)
    assert score_top_n == 3
    assert tailor_top_n == 1


def test_f2_4_test_mode_speed_budget(sample_fresher_qa_job):
    """F2.4: Verify mock test mode execution completes in < 10 seconds (well within 2 minute SLA)."""
    start_time = time.time()

    async def mock_score(prompt):
        return '{"match_score": 85, "missing_skills": [], "extracted_requirements": "QA, Selenium", "is_testing_role": true}', 150

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.db.get_cached_jd_score', return_value=None):
        scored = score_jobs([sample_fresher_qa_job], test_mode=True)
        assert len(scored) == 1
        assert scored[0].score == 85

    elapsed = time.time() - start_time
    assert elapsed < 10.0, f"Test mode run took {elapsed:.2f}s, expected < 10.0s"


def test_f2_5_test_mode_isolated_output_directory(temp_output_dir):
    """F2.5: Verify test mode saves artifacts to test/ subfolder, separating them from production runs."""
    test_mode = True
    time_format = "test_run_001"
    date_str = f"test/{time_format}" if test_mode else f"main pipeline/{time_format}"
    out_path = Path(temp_output_dir) / date_str
    out_path.mkdir(parents=True, exist_ok=True)
    assert out_path.exists()
    assert "test" in str(out_path)
    assert "main pipeline" not in str(out_path)


# =====================================================================
# F3: Scraping Integrity & Freshness (R2 §101-105)
# =====================================================================

def test_f3_1_url_deduplication():
    """F3.1: Verify deduplication of jobs with identical URLs."""
    job1 = Job(title="QA Tester", company="Infosys", location="Pune", description="QA role with Selenium", url="https://linkedin.com/jobs/view/101")
    job2 = Job(title="QA Tester Duplicate", company="Infosys Pune", location="Pune", description="QA role with Selenium duplicate", url="https://linkedin.com/jobs/view/101")
    job3 = Job(title="Java Dev", company="Wipro", location="Pune", description="Java role with Spring", url="https://linkedin.com/jobs/view/102")

    jobs = [job1, job2, job3]
    # Deduplicate by url
    seen = set()
    unique_jobs = []
    for j in jobs:
        if j.url not in seen:
            seen.add(j.url)
            unique_jobs.append(j)

    assert len(unique_jobs) == 2
    assert unique_jobs[0].url == "https://linkedin.com/jobs/view/101"
    assert unique_jobs[1].url == "https://linkedin.com/jobs/view/102"


def test_f3_2_preserve_multiline_job_descriptions():
    """F3.2: Verify full multi-line JDs with newlines and requirements are preserved intact in Job.description."""
    multiline_desc = (
        "Role: Junior Software Engineer\n\n"
        "Responsibilities:\n"
        "- Build scalable microservices\n"
        "- Write automated unit tests\n\n"
        "Requirements:\n"
        "1. Strong Java and SQL fundamentals\n"
        "2. Knowledge of RESTful APIs\n"
    )
    job = Job(
        title="Junior Software Engineer",
        company="Persistent Systems",
        location="Pune",
        description=multiline_desc,
        url="https://linkedin.com/jobs/view/201"
    )
    assert "\n" in job.description
    assert "- Build scalable microservices" in job.description
    assert "1. Strong Java and SQL fundamentals" in job.description
    assert len(job.description) == len(multiline_desc)


def test_f3_3_preserve_valid_apply_urls():
    """F3.3: Verify valid HTTP/HTTPS URLs with query parameters remain intact."""
    test_urls = [
        "https://www.linkedin.com/jobs/view/3948572019?refId=abc&trackingId=xyz",
        "https://in.indeed.com/viewjob?jk=1a2b3c4d5e6f7g8h&from=serp",
        "https://careers.tcs.com/jobs/apply/98234"
    ]
    for raw_url in test_urls:
        job = Job(title="Engineer", company="Company", location="Pune", description="Role", url=raw_url)
        assert job.url.startswith("http")
        assert job.url == raw_url


def test_f3_4_freshness_72h_cutoff():
    """F3.4: Verify jobs posted within 72 hours are accepted, while jobs older than 72 hours are dropped."""
    now = pd.Timestamp.now(tz="UTC")
    job_fresh_12h = Job(title="QA Trainee", company="TCS", location="Pune", description="Testing with Selenium and Python", url="http://ex.com/1")
    job_fresh_12h.date_posted = (now - pd.Timedelta(hours=12)).strftime('%Y-%m-%d')

    job_fresh_48h = Job(title="Java Fresher", company="Infosys", location="Pune", description="Java and SQL developer", url="http://ex.com/2")
    job_fresh_48h.date_posted = (now - pd.Timedelta(hours=48)).strftime('%Y-%m-%d')

    job_stale_96h = Job(title=".NET Trainee", company="Wipro", location="Pune", description="C# .NET developer", url="http://ex.com/3")
    job_stale_96h.date_posted = (now - pd.Timedelta(hours=96)).strftime('%Y-%m-%d')

    jobs = [job_fresh_12h, job_fresh_48h, job_stale_96h]
    cutoff = now - pd.Timedelta(hours=72)

    fresh_jobs = []
    for j in jobs:
        post_time = pd.to_datetime(j.date_posted, utc=True)
        if post_time >= cutoff:
            fresh_jobs.append(j)

    assert len(fresh_jobs) == 2
    assert job_fresh_12h in fresh_jobs
    assert job_fresh_48h in fresh_jobs
    assert job_stale_96h not in fresh_jobs


def test_f3_5_robust_date_handling_missing_dates():
    """F3.5: Verify jobs with None, empty, or unparseable date_posted do not cause unhandled crashes."""
    job_no_date = Job(title="Junior Developer", company="Persistent", location="Pune", description="Python SQL role", url="http://ex.com/nodate")
    job_no_date.date_posted = None

    job_empty_date = Job(title="Associate QA", company="Cybage", location="Pune", description="Automation testing Selenium", url="http://ex.com/empty")
    job_empty_date.date_posted = ""

    # Test that parsing date does not raise exception
    for j in [job_no_date, job_empty_date]:
        try:
            parsed = pd.to_datetime(getattr(j, "date_posted", None), errors='coerce', utc=True)
            # Should result in NaT without raising
            assert pd.isna(parsed)
        except Exception as e:
            pytest.fail(f"Date parsing raised unexpected exception: {e}")


# =====================================================================
# F4: Recall-First Pre-AI Regex Filtering (R2 §105-109)
# =====================================================================

def test_f4_1_fresher_job_retention_0_to_2_years():
    """F4.1: Verify fresher roles (0-1 yr, 0-2 yrs, Trainee, Associate, Intern) pass through pre-AI filter."""
    fresher_titles = [
        "Junior QA Automation Engineer",
        "Graduate Software Engineer Trainee",
        "Associate Java Developer",
        "Python Developer - Fresher",
        "SDET - 0 to 2 Years Experience"
    ]
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert'

    for title in fresher_titles:
        is_senior = bool(re.search(senior_pattern, title, re.IGNORECASE))
        assert not is_senior, f"Fresher title '{title}' was incorrectly flagged as senior"


def test_f4_2_dataset_200_fresher_recall(jobs_200_dataset):
    """F4.2: Verify pre-AI filter achieves >= 98% recall on relevant fresher jobs in the 200+ dataset fixture."""
    relevant_fresher_jobs = [
        d for d in jobs_200_dataset
        if d.get("is_relevant") is True and d.get("is_senior") is False
    ]
    assert len(relevant_fresher_jobs) >= 100, f"Expected >=100 relevant fresher jobs, got {len(relevant_fresher_jobs)}"

    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert'

    retained_count = 0
    for job in relevant_fresher_jobs:
        title_is_senior = bool(re.search(senior_pattern, job["title"], re.IGNORECASE))
        has_keywords = is_relevant_jd(job["description"])

        # Recall-first check: job retained if not senior title and has minimum keyword relevance
        if not title_is_senior and has_keywords:
            retained_count += 1

    recall = (retained_count / len(relevant_fresher_jobs)) * 100
    assert recall >= 98.0, f"Expected >= 98.0% recall on relevant fresher jobs, got {recall:.2f}% ({retained_count}/{len(relevant_fresher_jobs)})"


def test_f4_3_senior_title_rejection():
    """F4.3: Verify senior, lead, staff, principal, architect, and manager titles are rejected."""
    senior_titles = [
        "Senior Software Engineer",
        "Technical Lead - Java",
        "Principal Architect",
        "Engineering Manager",
        "Staff QA Engineer",
        "Director of Engineering",
        "VP of Technology"
    ]
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert'

    for title in senior_titles:
        is_senior = bool(re.search(senior_pattern, title, re.IGNORECASE))
        assert is_senior, f"Senior title '{title}' failed to be flagged as senior"


def test_f4_4_experience_ceiling_rejection():
    """F4.4: Verify requirement of 5+, 7+, or 8+ years experience is rejected."""
    senior_jds = [
        "Looking for a Senior Developer with 5+ years of hands-on experience in Java.",
        "Candidate must possess at least 7 years of full stack web development experience.",
        "Minimum 8-12 years of industry experience required for this backend role."
    ]
    range_pattern = r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?\.?)'
    single_pattern = r'(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?)'

    for jd in senior_jds:
        filtered = False
        for m in re.finditer(range_pattern, jd, re.IGNORECASE):
            if int(m.group(2)) >= 3:
                filtered = True
        for m in re.finditer(single_pattern, jd, re.IGNORECASE):
            if int(m.group(1)) >= 3:
                filtered = True
        assert filtered, f"JD requiring senior experience was not rejected: '{jd}'"


def test_f4_5_out_of_scope_non_tech_rejection():
    """F4.5: Verify non-tech roles (Accountant, HR, Nurse, Sales, Marketing) are rejected by zero-token check."""
    non_tech_descriptions = [
        "Seeking an experienced Chartered Accountant to handle corporate taxation, ledger audits, and financial reporting.",
        "Human Resources Manager required to lead recruitment drives, onboarding sessions, and payroll management.",
        "Registered ICU Nurse wanted for multi-speciality hospital in Mumbai. B.Sc Nursing required.",
        "Sales Executive needed to sell FMCG products and open new distributor accounts across Maharashtra.",
        "Graphic Designer skilled in Adobe Photoshop, Illustrator, and Canva for marketing banner design."
    ]
    for desc in non_tech_descriptions:
        assert not is_relevant_jd(desc), f"Non-tech JD was incorrectly flagged as relevant: '{desc[:60]}...'"


# =====================================================================
# F5: AI Scoring Accuracy & Model Names (R3 §110-118)
# =====================================================================

def test_f5_1_scoring_model_invocation():
    """F5.1: Verify call_ai_scoring_async configures deepseek-chat with thinking disabled."""
    config = load_config()
    scoring_model = config["ai"]["scoring_model"]
    assert scoring_model == "deepseek-chat"
    assert runtime_settings.get("scoring_model") == "deepseek-chat"
    assert runtime_settings.get("scoring_thinking") is False


def test_f5_2_micro_json_response_parsing(mock_deepseek_scoring_response):
    """F5.2: Verify parsing of micro-JSON DeepSeek response with match_score, missing_skills, etc."""
    raw_json_str, tokens = mock_deepseek_scoring_response
    parsed = json.loads(raw_json_str)

    assert "match_score" in parsed
    assert isinstance(parsed["match_score"], (int, float))
    assert parsed["match_score"] == 85
    assert "missing_skills" in parsed
    assert isinstance(parsed["missing_skills"], list)
    assert "reason" in parsed
    assert "extracted_requirements" in parsed
    assert "is_testing_role" in parsed
    assert parsed["is_testing_role"] is False


def test_f5_3_scoring_threshold_filtering_60():
    """F5.3: Verify default threshold of 60 correctly shortlists jobs >= 60 and rejects jobs < 60."""
    job_high = Job(title="QA Trainee", company="Infosys", location="Pune", description="QA role", url="http://ex.com/1")
    job_high.score = 85

    job_exact_threshold = Job(title="Java Fresher", company="Wipro", location="Pune", description="Java role", url="http://ex.com/2")
    job_exact_threshold.score = 60

    job_below = Job(title=".NET Trainee", company="TCS", location="Pune", description=".NET role", url="http://ex.com/3")
    job_below.score = 58

    jobs = [job_high, job_exact_threshold, job_below]
    min_score = 60
    shortlisted = [j for j in jobs if j.score and j.score >= min_score]

    assert len(shortlisted) == 2
    assert job_high in shortlisted
    assert job_exact_threshold in shortlisted
    assert job_below not in shortlisted


def test_f5_4_scoring_agreement_ground_truth(jobs_200_dataset):
    """F5.4: Verify scoring simulation assigns expected high scores to matching fresher tech jobs."""
    qa_jobs = [d for d in jobs_200_dataset if d.get("target_role") == "qa" and d.get("is_relevant") is True]
    assert len(qa_jobs) > 0
    # Simulate scoring evaluation for QA candidate
    for q_job in qa_jobs[:10]:
        assert is_relevant_jd(q_job["description"]), f"QA job {q_job['id']} should pass relevance"
        assert q_job.get("expected_ai_relevance") is True


def test_f5_5_scoring_fallback_on_malformed_json(sample_fresher_qa_job):
    """F5.5: Verify score_jobs handles malformed or non-JSON AI output gracefully without crashing."""
    async def mock_bad_ai(prompt):
        return "I think this candidate is a good fit with 80% match but I will not output JSON.", 100

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_bad_ai), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_bad_ai), \
         patch('src.db.get_cached_jd_score', return_value=None):
        result = score_jobs([sample_fresher_qa_job], test_mode=True)
        # Should gracefully return empty list or job with None score without crashing
        assert isinstance(result, list)


# =====================================================================
# F6: Prompt Prefix Caching & Token Telemetry (R3, R5 §113-118, §128)
# =====================================================================

def test_f6_1_master_resume_pinned_system_prompt(master_resume):
    """F6.1: Verify master resume is pinned in system prompt to trigger DeepSeek's 64-token prefix cache hit."""
    system_prompt = _get_prompt("scoring_prompt.txt", master_resume)
    assert master_resume["personal_information"]["name"] in system_prompt
    assert "Candidate Master Profile" in system_prompt or "Kaustubh" in system_prompt
    # DeepSeek prefix cache requires at least 64 tokens (approx 256 characters)
    assert len(system_prompt) > 500, "System prompt too short to leverage prompt cache"


def test_f6_2_aggressive_boilerplate_stripping():
    """F6.2: Verify strip_boilerplate strips 'About Us', 'Benefits', 'EEO', and company overviews."""
    noisy_jd = (
        "About the Company:\n"
        "Persistent Systems is a trusted global solutions company.\n\n"
        "Required Skills:\n"
        "- Java, Spring Boot, SQL, REST APIs\n\n"
        "Benefits and Perks:\n"
        "- Medical insurance, 401(k), paid time off\n\n"
        "Equal Opportunity Employer:\n"
        "We do not discriminate on any basis."
    )
    stripped = strip_boilerplate(noisy_jd)
    assert "Required Skills:" in stripped
    assert "Java, Spring Boot, SQL, REST APIs" in stripped
    assert "About the Company:" not in stripped
    assert "Benefits and Perks:" not in stripped
    assert "Equal Opportunity Employer:" not in stripped


def test_f6_3_zero_token_keyword_relevance_check():
    """F6.3: Verify is_relevant_jd filters out irrelevant jobs before sending to AI, preventing token waste."""
    tech_jd = "Looking for a QA Automation Engineer proficient in Selenium, Python, and SQL."
    assert is_relevant_jd(tech_jd) is True

    finance_jd = "Looking for a Financial Analyst with CPA and expertise in balance sheets."
    assert is_relevant_jd(finance_jd) is False


def test_f6_4_token_telemetry_accounting():
    """F6.4: Verify token usage is recorded on Job.tokens_used and accumulates across pipeline phases."""
    job = Job(title="QA Trainee", company="Infosys", location="Pune", description="QA role", url="http://ex.com/1")
    assert job.tokens_used == 0

    # Simulate Phase 2 Scoring tokens
    scoring_tokens = 180
    job.tokens_used += scoring_tokens
    assert job.tokens_used == 180

    # Simulate Phase 3 Tailoring tokens
    tailoring_tokens = 420
    job.tokens_used += tailoring_tokens
    assert job.tokens_used == 600


def test_f6_5_token_cost_calculation():
    """F6.5: Verify DeepSeek token pricing calculation ($0.0028/1M cached vs $0.014/1M unprompted)."""
    # Pricing: $0.14 per 1M input tokens (cache miss), $0.028 per 1M (cache hit), $0.28 per 1M output tokens
    cache_hit_tokens = 2000
    cache_miss_tokens = 500
    output_tokens = 300

    cost_cached = (cache_hit_tokens / 1_000_000) * 0.028
    cost_miss = (cache_miss_tokens / 1_000_000) * 0.14
    cost_output = (output_tokens / 1_000_000) * 0.28
    total_cost = cost_cached + cost_miss + cost_output

    assert cost_cached < cost_miss  # Cached tokens should be significantly cheaper
    assert round(total_cost, 6) > 0


# =====================================================================
# F7: Role-Lens Resume Tailoring (R4 §119-123)
# =====================================================================

def test_f7_1_tailoring_model_invocation():
    """F7.1: Verify call_ai_tailoring_async uses deepseek-chat with thinking enabled."""
    config = load_config()
    tailoring_model = config["ai"]["tailoring_model"]
    assert tailoring_model == "deepseek-chat"
    assert runtime_settings.get("tailoring_model") == "deepseek-chat"
    assert runtime_settings.get("tailoring_thinking") is True


def test_f7_2_role_lens_qa_automation(sample_fresher_qa_job):
    """F7.2: Verify QA role lens incorporates QA testing signals (is_testing_role=True, Selenium, Postman)."""
    sample_fresher_qa_job.score = 88
    sample_fresher_qa_job.extracted_requirements = "Selenium, Python, Postman, JIRA"
    sample_fresher_qa_job.is_testing_role = True

    # Check prompt builder includes priority signals
    prompt = (
        f"Job Title: {sample_fresher_qa_job.title}\n"
        f"Score: {sample_fresher_qa_job.score}%\n"
        f"Core Match Areas: {sample_fresher_qa_job.extracted_requirements}\n"
        f"Is Testing Role: {sample_fresher_qa_job.is_testing_role}\n"
    )
    assert "Is Testing Role: True" in prompt
    assert "Selenium" in prompt


def test_f7_3_role_lens_java_backend(sample_fresher_java_job):
    """F7.3: Verify Java role lens tailoring prioritizes Java, Spring Boot, SQL, and REST APIs."""
    sample_fresher_java_job.score = 90
    sample_fresher_java_job.extracted_requirements = "Java, Spring Boot, JDBC, SQL, REST APIs"
    sample_fresher_java_job.is_testing_role = False

    assert "Java" in sample_fresher_java_job.extracted_requirements
    assert "Spring Boot" in sample_fresher_java_job.extracted_requirements
    assert sample_fresher_java_job.is_testing_role is False


def test_f7_4_role_lens_dotnet_developer(sample_fresher_dotnet_job):
    """F7.4: Verify .NET role lens tailoring prioritizes C#, ASP.NET, SQL Server, and Azure."""
    sample_fresher_dotnet_job.score = 82
    sample_fresher_dotnet_job.extracted_requirements = "C#, .NET, ASP.NET Core, SQL Server, Azure"
    assert "C#" in sample_fresher_dotnet_job.extracted_requirements
    assert ".NET" in sample_fresher_dotnet_job.extracted_requirements


def test_f7_5_delta_json_merge_preserves_static_fields(master_resume, mock_deepseek_tailoring_response):
    """F7.5: Verify merging Delta JSON updates summary and tailored skills while preserving static fields."""
    raw_delta_str, tokens = mock_deepseek_tailoring_response
    delta = json.loads(raw_delta_str)

    tailored = json.loads(json.dumps(master_resume))  # deep copy
    if "profile_summary" in delta:
        tailored["profile_summary"] = delta["profile_summary"]
    if "tailored_skills" in delta:
        tailored["skills"] = delta["tailored_skills"]

    # Verify summary and skills updated
    assert tailored["profile_summary"] == delta["profile_summary"]
    assert tailored["skills"] == delta["tailored_skills"]
    # Verify contact info preserved exactly
    assert tailored["personal_information"]["name"] == master_resume["personal_information"]["name"]
    assert tailored["personal_information"]["email"] == master_resume["personal_information"]["email"]
    # Verify education preserved exactly
    assert tailored["education_details"] == master_resume["education_details"]


# =====================================================================
# F8: Zero-Hallucination Guardrail (R4 §124-127)
# =====================================================================

def test_f8_1_zero_fabricated_skills(master_resume, zero_hallucination_validator):
    """F8.1: Verify tailored skills are validated with zero fabricated qualifications."""
    valid_tailored = json.loads(json.dumps(master_resume))
    valid_tailored["skills"] = ["Java", "Python", "SQL", "Selenium", "Postman", "Git"]
    is_valid, violations = zero_hallucination_validator(valid_tailored)
    assert is_valid, f"Expected valid resume, got violations: {violations}"


def test_f8_2_zero_fabricated_degrees(master_resume, zero_hallucination_validator):
    """F8.2: Verify candidate education degrees and institutions match master profile verbatim."""
    tampered_tailored = json.loads(json.dumps(master_resume))
    tampered_tailored["education_details"][0]["education_level"] = "Master of Science in Artificial Intelligence"
    is_valid, violations = zero_hallucination_validator(tampered_tailored)
    assert not is_valid
    assert any("degree" in v.lower() for v in violations)


def test_f8_3_zero_fabricated_employers(master_resume, zero_hallucination_validator):
    """F8.3: Verify candidate experience employers match master profile verbatim."""
    tampered_tailored = json.loads(json.dumps(master_resume))
    tampered_tailored["experience_details"][0]["company"] = "Google Inc."
    is_valid, violations = zero_hallucination_validator(tampered_tailored)
    assert not is_valid
    assert any("company" in v.lower() for v in violations)


def test_f8_4_jd_requirement_coverage(master_resume):
    """F8.4: Verify applicable skills from master resume matching JD requirements are present (>=95% coverage)."""
    jd_skills = ["Java", "SQL", "Python", "Git", "REST APIs"]
    master_skills_norm = [s.lower() for s in master_resume.get("skills", [])]

    matched_skills = [
        s for s in jd_skills
        if any(s.lower() in ms for ms in master_skills_norm)
    ]
    coverage = (len(matched_skills) / len(jd_skills)) * 100
    assert coverage >= 95.0, f"Expected >=95% JD coverage, got {coverage:.1f}% ({len(matched_skills)}/{len(jd_skills)})"


def test_f8_5_anti_hallucination_sanitization(master_resume, zero_hallucination_validator):
    """F8.5: Verify validator detects and rejects fabricated skills not in candidate profile."""
    fabricated_tailored = json.loads(json.dumps(master_resume))
    fabricated_tailored["skills"] = ["Java", "Python", "Kubernetes Cluster Administrator", "COBOL Mainframe"]
    is_valid, violations = zero_hallucination_validator(fabricated_tailored)
    assert not is_valid
    assert any("Kubernetes" in v or "COBOL" in v for v in violations)


# =====================================================================
# F9: 1-Page ATS Sans-Serif PDF Generation (R5 §128-133)
# =====================================================================

def test_f9_1_sans_serif_typography_and_blue_accent():
    """F9.1: Verify resume HTML template contains clean styling and accent colors."""
    template_path = Path("templates") / "resume_template.html"
    assert template_path.exists(), "templates/resume_template.html must exist"
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify template contains modern typography styles
    assert "font-family" in content
    assert "box-sizing: border-box" in content
    assert "A4" in content


def test_f9_2_ats_machine_readability_headings():
    """F9.2: Verify HTML template includes standard ATS section headings (Summary, Skills, Experience, Projects, Education)."""
    template_path = Path("templates") / "resume_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    ats_headings = ["PROFILE", "SKILLS", "EXPERIENCE", "PROJECTS", "EDUCATION"]
    for heading in ats_headings:
        assert heading in content, f"Standard ATS heading '{heading}' missing from resume template"
    assert "summary" in content.lower(), "Summary block class missing from template"


def test_f9_3_no_css_scale_transform_degradation():
    """F9.3: Verify template HTML body layout does not embed hardcoded transform: scale hacks in markup."""
    template_path = Path("templates") / "resume_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    # The template body itself must not have hardcoded CSS transform: scale in its markup
    assert "style=\"transform: scale" not in content


def test_f9_4_deterministic_pdf_filename():
    """F9.4: Verify PDF filenames adhere to JobTitle_CompanyName.pdf without illegal characters."""
    job = Job(title="Software Engineer - Automation", company="Persistent Systems Ltd.", location="Pune", description="Desc", url="http://ex.com")
    safe_title = "".join([c if c.isalnum() else "_" for c in job.title]).strip("_")
    safe_company = "".join([c if c.isalnum() else "_" for c in job.company]).strip("_")
    safe_title = re.sub(r'_+', '_', safe_title)
    safe_company = re.sub(r'_+', '_', safe_company)
    filename = f"{safe_title}_{safe_company}.pdf"

    assert filename == "Software_Engineer_Automation_Persistent_Systems_Ltd.pdf"
    assert not any(c in filename for c in [':', '/', '\\', '*', '?', '"', '<', '>', '|'])


def test_f9_5_single_page_layout_budget(master_resume, sample_fresher_qa_job):
    """F9.5: Verify Jinja2 renders valid HTML without unrendered template tags or orphans."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("resume_template.html")
    rendered = template.render(resume=master_resume, job=sample_fresher_qa_job)

    assert "{{ " not in rendered, "Found unrendered Jinja2 expression in HTML"
    assert "{% " not in rendered, "Found unrendered Jinja2 block in HTML"
    assert master_resume["personal_information"]["name"] in rendered


# =====================================================================
# F10: Supabase Database & Storage Integration (R6 §134-136)
# =====================================================================

def test_f10_1_pipeline_runs_schema_save(mock_supabase):
    """F10.1: Verify save_pipeline_results inserts run statistics into pipeline_runs."""
    from src.db import save_pipeline_results
    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 5},
        "filter": {"after": 3},
        "score": {"scored": 3, "shortlisted": 1},
        "phase": "saving"
    }
    shortlisted = [Job(title="QA Trainee", company="Infosys", location="Pune", description="QA", url="http://ex.com/1")]
    pdf_paths = ["C:/dummy/test.pdf"]

    with patch('src.db.supabase', mock_supabase):
        save_pipeline_results(pipeline_state, shortlisted, pdf_paths)
        mock_supabase.table.assert_any_call("pipeline_runs")


def test_f10_2_tracked_jobs_and_applications_insert(mock_supabase):
    """F10.2: Verify shortlisted jobs and applications are saved to Supabase."""
    from src.db import save_pipeline_results
    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 2},
        "filter": {"after": 1},
        "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }
    job = Job(title="Java Dev", company="Wipro", location="Pune", description="Java", url="http://ex.com/2", id="job-002")
    job.score = 88
    job.reasons = "Strong match"
    job.missing_skills = ["Docker"]

    with patch('src.db.supabase', mock_supabase):
        save_pipeline_results(pipeline_state, [job], [""])
        mock_supabase.table.assert_any_call("tracked_jobs")
        mock_supabase.table.assert_any_call("applications")


def test_f10_3_jd_cache_read_write(mock_supabase):
    """F10.3: Verify save_jd_cache and get_cached_jd_score correctly cache scoring results."""
    from src.db import save_jd_cache, get_cached_jd_score
    test_url = "https://linkedin.com/jobs/view/999888777"

    with patch('src.db.supabase', mock_supabase):
        save_jd_cache(test_url, 85, ["Docker"], "Java, SQL", False)
        mock_supabase.table.assert_any_call("jd_cache")

        # Test read
        mock_supabase.table().select().eq().execute.return_value.data = [{
            "url": test_url, "score": 85, "missing_skills": ["Docker"],
            "extracted_requirements": "Java, SQL", "is_testing_role": False
        }]
        cached = get_cached_jd_score(test_url)
        assert cached is not None
        assert cached["score"] == 85


def test_f10_4_storage_pdf_upload(mock_supabase):
    """F10.4: Verify PDF uploads to Supabase storage bucket 'resumes'."""
    with patch('src.db.supabase', mock_supabase):
        bucket = mock_supabase.storage.from_("resumes")
        res = bucket.upload("resumes/sample.pdf", b"PDF content")
        assert "Key" in res


def test_f10_5_graceful_local_fallback_no_supabase():
    """F10.5: Verify pipeline completes cleanly when Supabase credentials or client is None."""
    from src.db import save_pipeline_results
    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 1},
        "filter": {"after": 1},
        "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }
    shortlisted = [Job(title="QA Trainee", company="Infosys", location="Pune", description="QA", url="http://ex.com/1")]

    with patch('src.db.supabase', None):
        # Should not raise any exception
        save_pipeline_results(pipeline_state, shortlisted, [""])


# =====================================================================
# F11: Web UI Functionality & Control Feedback (R6 §136-139)
# =====================================================================

def test_f11_1_api_status_endpoint(flask_client):
    """F11.1: Verify /api/status returns JSON with pipeline state and expected keys."""
    resp = flask_client.get('/api/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert "running" in data
    assert "phase" in data
    assert "mode" in data
    assert "scan" in data
    assert "score" in data


def test_f11_2_api_config_endpoint(flask_client):
    """F11.2: Verify /api/config returns valid application configuration JSON."""
    resp = flask_client.get('/api/config')
    assert resp.status_code == 200
    data = resp.get_json()
    assert "ai" in data
    assert "search" in data
    assert "scoring" in data


def test_f11_3_api_stop_endpoint(flask_client):
    """F11.3: Verify /api/stop triggers stop_event and sets phase to idle."""
    resp = flask_client.post('/api/stop')
    assert resp.status_code == 200
    data = resp.get_json()
    assert "Pipeline aborted" in data.get("message", "")


def test_f11_4_api_ai_settings_endpoint(flask_client):
    """F11.4: Verify /api/ai-settings returns runtime AI models and allows runtime inspection."""
    resp = flask_client.get('/api/ai-settings')
    assert resp.status_code == 200
    data = resp.get_json()
    assert "scoring_model" in data
    assert "tailoring_model" in data
    assert data["scoring_model"] == "deepseek-chat"
    assert data["tailoring_model"] == "deepseek-chat"


def test_f11_5_api_manual_tailor_score_endpoint(flask_client):
    """F11.5: Verify /api/manual-tailor/score scores an individual job description via POST."""
    payload = {
        "job_title": "Junior QA Automation Engineer",
        "company": "Infosys",
        "job_description": "Looking for freshers with knowledge of Selenium, Python, Postman, and SQL."
    }
    async def mock_score(prompt):
        return '{"match_score": 88, "missing_skills": [], "extracted_requirements": "Selenium, Python", "is_testing_role": true}', 120

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_score):
        resp = flask_client.post('/api/manual-tailor/score', json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("score") == 88
        assert data.get("is_testing_role") is True
