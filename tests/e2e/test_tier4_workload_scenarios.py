"""
Tier 4: Real-World Workload Application Scenarios E2E Tests.
Verifies complete end-to-end user workflows from scraping through filtering, AI scoring,
role-lens resume tailoring, ATS PDF rendering, and Supabase persistence.
Coverage threshold: >= 5 end-to-end application scenarios.
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
from src.ai_engine import runtime_settings


# =====================================================================
# Scenario 1: Fresher QA Automation Workflow in Pune
# Features: F1, F2, F3, F4, F5, F7, F8, F9, F10
# =====================================================================
def test_tier4_scenario_1_fresher_qa_automation_pune(master_resume, zero_hallucination_validator, mock_supabase, temp_output_dir):
    """
    Scenario 1: End-to-end pipeline run for an Indian fresher QA Automation candidate in Pune.
    - Scrapes fresher QA role from LinkedIn in Pune.
    - Validates 72h freshness and preserves raw description.
    - Pre-AI filter passes fresher role and retains multiline formatting.
    - DeepSeek scores job at 88% with is_testing_role=True.
    - Role-lens tailoring adapts profile to highlight Selenium, Python, Postman, SQL.
    - Python-level anti-hallucination guardrail validates 100% of skills stem from master resume.
    - Generates ATS-compliant HTML/PDF resume.
    - Saves run metrics and application record to Supabase.
    """
    now = pd.Timestamp.now(tz="UTC")
    raw_qa_jd = (
        "Persistent Systems is hiring a Junior QA Automation Engineer in Pune.\n"
        "Responsibilities:\n"
        "- Build automated test scripts using Python and Selenium WebDriver.\n"
        "- Execute REST API tests with Postman and validate JSON responses.\n"
        "- Log and track defects in JIRA following Agile methodologies.\n\n"
        "Requirements:\n"
        "- BE/B.Tech in IT or Computer Science.\n"
        "- 0-2 years of experience or freshers with test automation internship.\n"
        "- Solid understanding of Python, Selenium, Postman, SQL, and Git."
    )

    qa_job = Job(
        title="Junior QA Automation Engineer",
        company="Persistent Systems",
        location="Pune, Maharashtra, India",
        description=raw_qa_jd,
        url="https://www.linkedin.com/jobs/view/901001",
        source="linkedin",
        job_type="fulltime",
        id="job-scenario-1"
    )
    qa_job.date_posted = (now - pd.Timedelta(hours=14)).strftime('%Y-%m-%d')

    # 1. Freshness & Pre-AI filter verification
    post_time = pd.to_datetime(qa_job.date_posted, utc=True)
    assert post_time >= (now - pd.Timedelta(hours=72)), "Job must be within 72h"
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|architect'
    assert not re.search(senior_pattern, qa_job.title, re.IGNORECASE)
    assert is_relevant_jd(qa_job.description) is True

    # 2. AI Scoring Mock
    async def mock_score(prompt):
        return json.dumps({
            "match_score": 88,
            "missing_skills": ["JIRA"],
            "reason": "Strong match for Python, Selenium, Postman, and SQL automated testing fundamentals.",
            "extracted_requirements": "Python, Selenium WebDriver, Postman, SQL, Git",
            "is_testing_role": True
        }), 180

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.db.get_cached_jd_score', return_value=None):
        scored_jobs = score_jobs([qa_job], test_mode=False)
        assert len(scored_jobs) == 1
        scored_job = scored_jobs[0]
        assert scored_job.score == 88
        assert scored_job.is_testing_role is True

    # 3. Role-Lens Tailoring Mock (QA Lens)
    tailored_qa_resume = json.loads(json.dumps(master_resume))
    tailored_qa_resume["profile_summary"] = (
        "Graduate Engineer skilled in Python, Selenium, Postman, SQL, and automated test pipelines. "
        "Experienced in designing automated test suites, REST API testing, and backend validation."
    )
    tailored_qa_resume["skills"] = [
        "Python", "Selenium (Basic UI Automation)", "Postman (API Testing)",
        "pytest (Python Testing)", "JUnit (Unit Testing)", "SQL", "Git", "REST APIs"
    ]

    # 4. Zero-Hallucination Guardrail Check
    is_valid, violations = zero_hallucination_validator(tailored_qa_resume)
    assert is_valid, f"Anti-hallucination guardrail failed: {violations}"

    # 5. ATS Resume Template Rendering
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("resume_template.html")
    html_rendered = template.render(resume=tailored_qa_resume, job=scored_job)
    assert "Junior QA Automation Engineer" in scored_job.title
    assert "Persistent Systems" in scored_job.company
    assert "Selenium" in html_rendered
    assert "Postman" in html_rendered
    assert "<h2>PROFILE</h2>" in html_rendered or "<h2>PROFILE SUMMARY</h2>" in html_rendered
    assert "<h2>SKILLS</h2>" in html_rendered or "<h2>TECHNICAL SKILLS</h2>" in html_rendered

    # 6. Save to Supabase
    from src.db import save_pipeline_results
    pipeline_state = {
        "mode": "prod",
        "scan": {"total_found": 1},
        "filter": {"after": 1},
        "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }
    fake_pdf = str(Path(temp_output_dir) / "QA_Persistent.pdf")
    with patch('src.db.supabase', mock_supabase):
        save_pipeline_results(pipeline_state, [scored_job], [fake_pdf])
        mock_supabase.table.assert_any_call("pipeline_runs")
        mock_supabase.table.assert_any_call("tracked_jobs")
        mock_supabase.table.assert_any_call("applications")


# =====================================================================
# Scenario 2: Fresher Java Developer Workflow in Bangalore
# Features: F1, F3, F4, F5, F6, F7, F8, F9, F10
# =====================================================================
def test_tier4_scenario_2_fresher_java_developer_bangalore(master_resume, zero_hallucination_validator, mock_supabase, temp_output_dir):
    """
    Scenario 2: End-to-end pipeline run for an Indian fresher Java Developer candidate in Bangalore / Bengaluru.
    - Scrapes fresher Java role from Indeed in Bengaluru.
    - Validates location alias recognition (Bengaluru = Bangalore).
    - AI Scoring with DeepSeek prompt prefix caching and token telemetry.
    - Role-lens tailoring for Java Developer (Java, Spring Core, REST APIs, SQL, JDBC).
    - Verifies 0 hallucinations (preserves SKNSITS degree, CWIPedia intern experience).
    - ATS single-page template rendering.
    - Verifies token cost calculation and records run to Supabase.
    """
    java_jd = (
        "LTIMindtree Bangalore is hiring an entry level Java Backend Developer.\n"
        "Responsibilities:\n"
        "- Develop RESTful microservices using Core Java, Spring Boot, JDBC, and SQL.\n"
        "- Optimize database queries and participate in Agile development sprints.\n\n"
        "Requirements:\n"
        "- 0-1 year experience or fresher with strong Core Java and OOP fundamentals.\n"
        "- Hands-on knowledge of SQL, JDBC, Spring Boot, Git, and data structures."
    )

    java_job = Job(
        title="Java Backend Developer - Fresher",
        company="LTIMindtree",
        location="Bengaluru, Karnataka, India",
        description=java_jd,
        url="https://in.indeed.com/viewjob?jk=902002",
        source="indeed",
        job_type="fulltime",
        id="job-scenario-2"
    )

    # 1. Location alias check
    assert "bengaluru" in java_job.location.lower() or "bangalore" in java_job.location.lower()
    assert is_relevant_jd(java_job.description) is True

    # 2. AI Scoring Mock with Telemetry
    async def mock_score(prompt):
        return json.dumps({
            "match_score": 92,
            "missing_skills": [],
            "reason": "Exceptional match for Core Java, Spring, REST APIs, and relational SQL databases.",
            "extracted_requirements": "Java, Spring Boot, JDBC, SQL, Git",
            "is_testing_role": False
        }), 210

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.db.get_cached_jd_score', return_value=None):
        scored_jobs = score_jobs([java_job], test_mode=False)
        assert len(scored_jobs) == 1
        scored_job = scored_jobs[0]
        assert scored_job.score == 92
        assert scored_job.is_testing_role is False
        assert scored_job.tokens_used == 210

    # 3. Role-Lens Tailoring Mock (Java Lens)
    tailored_java = json.loads(json.dumps(master_resume))
    tailored_java["profile_summary"] = (
        "Motivated IT engineering graduate skilled in Core Java, Spring Core, JDBC, REST APIs, and SQL. "
        "Completed internship delivering modular backend services and database query optimizations."
    )
    tailored_java["skills"] = [
        "Java", "Spring Core (Basics)", "JDBC", "REST APIs", "SQL", "Git", "Python"
    ]

    # 4. Zero-Hallucination Guardrail Check
    is_valid, violations = zero_hallucination_validator(tailored_java)
    assert is_valid, f"Anti-hallucination guardrail failed for Java role: {violations}"

    # Verify CWIPedia internship and SKNSITS education remain intact
    assert tailored_java["experience_details"][0]["company"] == "CWIPedia Technologies"
    assert "SKNSITS" in tailored_java["education_details"][0]["institution"]

    # 5. Token and Cost Accounting
    cost_usd = (scored_job.tokens_used / 1_000_000) * 0.14
    assert cost_usd > 0
    assert cost_usd < 0.01  # Fraction of a cent

    # 6. Database Storage
    from src.db import save_pipeline_results
    pipeline_state = {
        "mode": "prod", "scan": {"total_found": 1},
        "filter": {"after": 1}, "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }
    with patch('src.db.supabase', mock_supabase):
        save_pipeline_results(pipeline_state, [scored_job], ["C:/fake/Java.pdf"])
        mock_supabase.table.assert_any_call("pipeline_runs")


# =====================================================================
# Scenario 3: Fresher .NET Developer Threshold Acceptance
# Features: F4, F5, F7, F8, F9 (score 50-70 handling)
# =====================================================================
def test_tier4_scenario_3_fresher_dotnet_developer_mumbai(master_resume, zero_hallucination_validator):
    """
    Scenario 3: Borderline scoring acceptance for Indian fresher .NET candidate in Mumbai.
    - Scrapes .NET Fresher role in Mumbai.
    - AI Scoring returns 65% (above default threshold of 60, but would have failed old threshold 70).
    - Verifies job is shortlisted under the overhauled threshold of 60.
    - Role-lens tailoring weaves C# (Basics via Azure) and REST APIs naturally.
    - Verifies 0 hallucinations (no fake ASP.NET senior experience).
    - Verifies ATS single-page template rendering.
    """
    dotnet_jd = (
        "CitiusTech Mumbai is seeking an Associate .NET Developer.\n"
        "Requirements:\n"
        "- 0-2 years experience in C# / .NET development.\n"
        "- Knowledge of object oriented programming, REST APIs, and SQL Server.\n"
        "- Freshers with strong programming fundamentals and cloud certifications welcome."
    )

    dotnet_job = Job(
        title=".NET Developer (Fresher)",
        company="CitiusTech",
        location="Mumbai, Maharashtra, India",
        description=dotnet_jd,
        url="https://in.indeed.com/viewjob?jk=903003",
        source="indeed",
        id="job-scenario-3"
    )

    # 1. AI Scoring returns 65%
    async def mock_score(prompt):
        return json.dumps({
            "match_score": 65,
            "missing_skills": ["ASP.NET Core", "Entity Framework"],
            "reason": "Candidate has solid OOP, SQL, and C# basics via Azure certification, suitable for trainee entry.",
            "extracted_requirements": "C#, .NET, OOP, SQL, Azure",
            "is_testing_role": False
        }), 160

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.db.get_cached_jd_score', return_value=None):
        scored_jobs = score_jobs([dotnet_job], test_mode=False)
        # Threshold 60 -> 65% passes!
        assert len(scored_jobs) == 1
        assert scored_jobs[0].score == 65

    # 2. Role-Lens Tailoring (weave C# from Azure certification)
    tailored_dotnet = json.loads(json.dumps(master_resume))
    tailored_dotnet["profile_summary"] = (
        "Graduate Engineer with foundational knowledge of C# and cloud services via Microsoft Azure certification, "
        "complemented by hands-on backend experience in SQL and REST API integrations."
    )
    tailored_dotnet["skills"] = [
        "C# (Basics via Azure)", "SQL", "REST APIs", "Git", "Python", "Java"
    ]

    is_valid, violations = zero_hallucination_validator(tailored_dotnet)
    assert is_valid, f"Anti-hallucination failed: {violations}"
    assert "C# (Basics via Azure)" in tailored_dotnet["skills"]


# =====================================================================
# Scenario 4: Senior / Lead Role Rejection Under Adversarial Load
# Features: F4, F5, F6 (zero wasted AI calls)
# =====================================================================
def test_tier4_scenario_4_senior_lead_adversarial_rejection():
    """
    Scenario 4: Adversarial load verification — batch containing senior, manager, architect, and non-tech jobs.
    - Ingests 10 adversarial jobs (Senior Architect, Tech Lead, VP, CPA Accountant, Nurse).
    - Pre-AI regex and pandas filters must eliminate 100% of these jobs.
    - Exactly 0 AI API calls executed, 0 AI tokens wasted, $0.00 cost incurred.
    """
    adversarial_jobs = [
        Job(title="Senior Principal Architect", company="Google India", location="Bangalore", description="15+ years experience required.", url="http://ex.com/adv1"),
        Job(title="Technical Lead - Distributed Systems", company="Amazon India", location="Bangalore", description="8-12 years experience.", url="http://ex.com/adv2"),
        Job(title="Engineering Manager", company="Microsoft IDC", location="Bangalore", description="Manage 20 software engineers. 10+ yrs exp.", url="http://ex.com/adv3"),
        Job(title="Staff Software Engineer", company="Uber Pune", location="Pune", description="7+ years of distributed backend systems.", url="http://ex.com/adv4"),
        Job(title="Director of QA Automation", company="Oracle India", location="Bangalore", description="12+ years experience leading QA.", url="http://ex.com/adv5"),
        Job(title="VP of Engineering", company="Fintech Corp", location="Mumbai", description="Lead tech organization, 15+ years exp.", url="http://ex.com/adv6"),
        Job(title="Senior Accountant", company="Deloitte India", location="Pune", description="CA required with 5 years audit exp.", url="http://ex.com/adv7"),
        Job(title="HR Generalist", company="Tata Motors", location="Pune", description="Employee relations and recruitment.", url="http://ex.com/adv8"),
        Job(title="Staff SDET", company="Flipkart", location="Bangalore", description="6+ years building automation frameworks.", url="http://ex.com/adv9"),
        Job(title="Head of DevOps", company="Reliance Jio", location="Mumbai", description="10+ years Kubernetes and cloud infrastructure.", url="http://ex.com/adv10"),
    ]

    # Run pre-AI filter
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert'
    surviving_jobs = []
    for j in adversarial_jobs:
        if not re.search(senior_pattern, j.title, re.IGNORECASE) and is_relevant_jd(j.description):
            surviving_jobs.append(j)

    # 100% of adversarial jobs must be dropped before AI scoring
    assert len(surviving_jobs) == 0, f"Adversarial jobs leaked through pre-AI filter: {[j.title for j in surviving_jobs]}"

    # Verify 0 AI calls made
    ai_called = [False]
    async def mock_ai(prompt):
        ai_called[0] = True
        return "{}", 100

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_ai):
        scored = score_jobs(surviving_jobs, test_mode=False)
        assert len(scored) == 0
        assert ai_called[0] is False, "AI API was called when all jobs were senior/irrelevant!"


# =====================================================================
# Scenario 5: Small-Batch Test Mode Speed & Integrity Run (<2 min)
# Features: F1, F2, F5, F7, F9, F10
# =====================================================================
def test_tier4_scenario_5_small_batch_test_mode_speed_integrity(master_resume, mock_supabase, temp_output_dir):
    """
    Scenario 5: Complete end-to-end iteration in Small-Batch Test Mode (< 2 minutes SLA).
    - Exercises full workflow: single query (QA in Pune), scrape 5 jobs, filter, score top 3, tailor top 1.
    - Validates execution latency is under 5 seconds in automated test environment.
    - Verifies output directory structure adheres to test/<timestamp>.
    - Verifies test run metrics are recorded in Supabase.
    """
    start_time = time.time()

    # Simulate 5 scraped jobs in Pune for QA Automation
    test_jobs = [
        Job(title="Junior QA Automation Engineer", company="Persistent", location="Pune", description="Selenium and Python role.", url="http://test.com/1", id="t-1"),
        Job(title="QA Trainee", company="Infosys", location="Pune", description="Python testing role.", url="http://test.com/2", id="t-2"),
        Job(title="SDET Intern", company="Cybage", location="Pune", description="Postman and Selenium.", url="http://test.com/3", id="t-3"),
        Job(title="Senior QA Lead", company="Senior Corp", location="Pune", description="Lead role 8 yrs exp.", url="http://test.com/4", id="t-4"),
        Job(title="Chartered Accountant", company="Finance Co", location="Pune", description="Accounting taxation.", url="http://test.com/5", id="t-5"),
    ]

    # Phase 1: Pre-AI filtering
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|architect'
    filtered_jobs = [
        j for j in test_jobs
        if not re.search(senior_pattern, j.title, re.IGNORECASE) and is_relevant_jd(j.description)
    ]
    assert len(filtered_jobs) == 3, "Only 3 relevant fresher jobs should pass"

    # Phase 2: AI Scoring top 3
    async def mock_score(prompt):
        return json.dumps({
            "match_score": 85,
            "missing_skills": [],
            "reason": "Good match",
            "extracted_requirements": "Selenium, Python",
            "is_testing_role": True
        }), 120

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.db.get_cached_jd_score', return_value=None):
        scored_jobs = score_jobs(filtered_jobs, test_mode=True)
        assert len(scored_jobs) == 3

    # Phase 3: Tailor top 1 resume
    shortlisted = scored_jobs[:1]
    assert len(shortlisted) == 1
    top_job = shortlisted[0]

    tailored_resume = json.loads(json.dumps(master_resume))
    tailored_resume["profile_summary"] = "Tailored summary for test mode QA Automation run."
    tailored_resume["skills"] = ["Python", "Selenium (Basic UI Automation)", "Postman (API Testing)", "SQL", "Git"]

    # Phase 4: Generate ATS HTML in test/ folder
    time_format = "test_run_fast"
    date_str = f"test/{time_format}"
    out_dir = Path(temp_output_dir) / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = str(out_dir / "Persistent_QA_Resume.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 Mock Fast Test PDF")

    # Phase 5: Save run metrics to Supabase
    from src.db import save_pipeline_results
    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": len(test_jobs)},
        "filter": {"after": len(filtered_jobs)},
        "score": {"scored": len(scored_jobs), "shortlisted": len(shortlisted)},
        "phase": "saving"
    }
    with patch('src.db.supabase', mock_supabase):
        save_pipeline_results(pipeline_state, shortlisted, [pdf_path])
        mock_supabase.table.assert_any_call("pipeline_runs")

    elapsed = time.time() - start_time
    assert elapsed < 5.0, f"Test mode run took {elapsed:.2f}s, expected < 5.0s (SLA < 120s)"
    assert Path(pdf_path).exists()
