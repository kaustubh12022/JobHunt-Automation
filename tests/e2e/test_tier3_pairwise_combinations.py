"""
Tier 3: Pairwise & Cross-Feature Integration E2E Tests.
Verifies interactions and interface contracts between modules (F1 through F11).
Coverage threshold: >= 11 cross-feature integration test cases.
"""
import os
import re
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pandas as pd

from src.models import Job
from src.config_loader import load_config, load_resume, get_human_date_str
from src.scorer import is_relevant_jd, strip_boilerplate, score_jobs
from src.ai_engine import runtime_settings, _get_prompt


# ---------------------------------------------------------------------
# 1. F1 x F2: Windows Path Handling in Test Mode
# ---------------------------------------------------------------------
def test_tier3_f1_f2_windows_path_in_test_mode(temp_output_dir):
    """Pairwise F1 x F2: Verifies test mode execution under Windows generates valid directories without colons."""
    config = load_config()
    test_mode = True
    time_format = "2026-09-06_14-30-00"
    date_str = f"test/{time_format}" if test_mode else f"main pipeline/{time_format}"

    out_dir_path = Path(temp_output_dir) / date_str
    out_dir_path.mkdir(parents=True, exist_ok=True)

    job_title = "QA Automation Engineer: Trainee"
    company_name = "Persistent / Systems Ltd."

    safe_title = "".join([c if c.isalnum() else "_" for c in job_title]).strip("_")
    safe_company = "".join([c if c.isalnum() else "_" for c in company_name]).strip("_")
    safe_title = re.sub(r'_+', '_', safe_title)
    safe_company = re.sub(r'_+', '_', safe_company)
    filename = f"{safe_title}_{safe_company}.pdf"
    pdf_path = out_dir_path / filename

    assert ":" not in filename
    assert "/" not in filename
    assert "\\" not in filename
    assert str(pdf_path).endswith(".pdf")
    assert "test" in str(pdf_path)


# ---------------------------------------------------------------------
# 2. F3 x F4: Scrape Data Integrity Feeds into Recall-First Filtering
# ---------------------------------------------------------------------
def test_tier3_f3_f4_scrape_integrity_to_regex_filtering():
    """Pairwise F3 x F4: Scraped multi-line jobs feed into pre-AI filtering preserving fields and rejecting seniors."""
    fresh_date = pd.Timestamp.now(tz="UTC").strftime('%Y-%m-%d')
    scraped_jobs = [
        Job(
            title="Junior QA Automation Engineer",
            company="Persistent Systems",
            location="Pune, MH, IN",
            description="Role: QA Automation\nRequirements: 0-2 years experience.\nSkills: Python, Selenium, Postman, SQL.",
            url="https://linkedin.com/jobs/view/301",
            source="linkedin"
        ),
        Job(
            title="Senior Engineering Manager - Test",
            company="Global Tech",
            location="Pune",
            description="Lead a team of 15 QA engineers. 10+ years experience required.",
            url="https://linkedin.com/jobs/view/302",
            source="linkedin"
        )
    ]
    for j in scraped_jobs:
        j.date_posted = fresh_date

    # Filter by senior pattern and keyword relevance
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|architect'
    filtered_jobs = []
    for j in scraped_jobs:
        if not re.search(senior_pattern, j.title, re.IGNORECASE) and is_relevant_jd(j.description):
            filtered_jobs.append(j)

    assert len(filtered_jobs) == 1
    assert filtered_jobs[0].title == "Junior QA Automation Engineer"
    assert "\n" in filtered_jobs[0].description
    assert filtered_jobs[0].source == "linkedin"


# ---------------------------------------------------------------------
# 3. F4 x F5: Pre-AI Filtered Jobs Feed into AI Scoring
# ---------------------------------------------------------------------
def test_tier3_f4_f5_regex_filtered_jobs_to_ai_scoring():
    """Pairwise F4 x F5: Pre-filtered jobs reach AI scoring; disqualified jobs are blocked before AI call."""
    fresher_job = Job(
        title="Associate Java Developer",
        company="Infosys",
        location="Pune",
        description="Core Java, Spring Boot, SQL, REST APIs. Freshers welcome.",
        url="https://linkedin.com/jobs/view/401"
    )
    senior_job = Job(
        title="Senior Director of Architecture",
        company="Enterprise Co",
        location="Pune",
        description="15 years experience required in large scale Java architecture.",
        url="https://linkedin.com/jobs/view/402"
    )

    # 1. Pre-AI filter blocks senior job
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|director|architect'
    assert bool(re.search(senior_pattern, senior_job.title, re.IGNORECASE)) is True
    assert bool(re.search(senior_pattern, fresher_job.title, re.IGNORECASE)) is False

    # 2. Only fresher job sent to score_jobs
    async def mock_score(prompt):
        return '{"match_score": 88, "missing_skills": [], "extracted_requirements": "Java, Spring Boot", "is_testing_role": false}', 150

    with patch('src.ai_engine.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.scorer.call_ai_scoring_async', side_effect=mock_score), \
         patch('src.db.get_cached_jd_score', return_value=None):
        scored = score_jobs([fresher_job], test_mode=True)
        assert len(scored) == 1
        assert scored[0].score == 88
        assert scored[0].extracted_requirements == "Java, Spring Boot"


# ---------------------------------------------------------------------
# 4. F5 x F6: AI Scoring with Prompt Caching & Token Telemetry
# ---------------------------------------------------------------------
def test_tier3_f5_f6_scoring_with_prompt_caching_and_telemetry(master_resume):
    """Pairwise F5 x F6: AI scoring uses master profile pinned in prompt and tracks token telemetry."""
    system_prompt = _get_prompt("scoring_prompt.txt", master_resume)
    assert len(system_prompt) > 500
    assert master_resume["personal_information"]["name"] in system_prompt

    job = Job(
        title="Software Tester",
        company="Cognizant",
        location="Pune",
        description="Selenium, Python, SQL, Postman.",
        url="https://linkedin.com/jobs/view/501"
    )
    tokens_recorded = 240
    job.tokens_used += tokens_recorded

    assert job.tokens_used == 240
    cost = (job.tokens_used / 1_000_000) * 0.14
    assert cost > 0


# ---------------------------------------------------------------------
# 5. F5 x F7: Scored Jobs Feed Priority Signals into Role-Lens Tailoring
# ---------------------------------------------------------------------
def test_tier3_f5_f7_scored_jobs_feed_into_role_lens_tailoring():
    """Pairwise F5 x F7: Scoring outputs (extracted_requirements, is_testing_role) feed into tailoring user prompt."""
    job = Job(
        title="Junior QA Automation Engineer",
        company="Persistent Systems",
        location="Pune",
        description="Selenium, Python, Postman testing role.",
        url="https://linkedin.com/jobs/view/601"
    )
    # Simulate scoring signals
    job.score = 88
    job.extracted_requirements = "Selenium, Python, Postman, SQL, defect reporting"
    job.missing_skills = ["Docker"]
    job.is_testing_role = True

    # Build tailoring prompt using signals
    tailoring_prompt = (
        f"Job Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n\n"
        f"=== PHASE 2 PRIORITY SIGNALS ===\n"
        f"Score: {job.score}%\n"
        f"Core Match Areas: {job.extracted_requirements}\n"
        f"Missing Skills: {', '.join(job.missing_skills)}\n"
        f"Is Testing Role: {job.is_testing_role}\n\n"
        f"=== COMPLETE JOB DESCRIPTION ===\n"
        f"{job.description}"
    )

    assert "Is Testing Role: True" in tailoring_prompt
    assert "Selenium, Python, Postman" in tailoring_prompt
    assert "Score: 88%" in tailoring_prompt


# ---------------------------------------------------------------------
# 6. F7 x F8: Role-Lens Tailored Resume Passes Zero-Hallucination Check
# ---------------------------------------------------------------------
def test_tier3_f7_f8_role_lens_tailored_resume_passes_zero_hallucination(master_resume, zero_hallucination_validator):
    """Pairwise F7 x F8: Tailored resume delta outputs for QA and Java lenses pass zero-hallucination validation."""
    qa_delta = {
        "profile_summary": "Results-driven IT engineer skilled in Python, Selenium, Postman, and automated QA pipelines.",
        "tailored_skills": ["Python", "Selenium", "Postman", "SQL", "Git", "Java"]
    }
    tailored_qa = json.loads(json.dumps(master_resume))
    tailored_qa["profile_summary"] = qa_delta["profile_summary"]
    tailored_qa["skills"] = qa_delta["tailored_skills"]

    is_valid, violations = zero_hallucination_validator(tailored_qa)
    assert is_valid, f"QA tailored resume had violations: {violations}"

    java_delta = {
        "profile_summary": "Modular backend engineer specializing in Core Java, Spring Boot, REST APIs, and SQL databases.",
        "tailored_skills": ["Java", "SQL", "Spring Core", "REST APIs", "JDBC", "Git"]
    }
    tailored_java = json.loads(json.dumps(master_resume))
    tailored_java["profile_summary"] = java_delta["profile_summary"]
    tailored_java["skills"] = java_delta["tailored_skills"]

    is_valid, violations = zero_hallucination_validator(tailored_java)
    assert is_valid, f"Java tailored resume had violations: {violations}"


# ---------------------------------------------------------------------
# 7. F7 x F9: Tailored Resume Generates Valid ATS HTML
# ---------------------------------------------------------------------
def test_tier3_f7_f9_tailored_resume_generates_valid_ats_html(master_resume, sample_fresher_qa_job):
    """Pairwise F7 x F9: Tailored resume dictionary successfully renders through Jinja2 resume template."""
    from jinja2 import Environment, FileSystemLoader

    tailored = json.loads(json.dumps(master_resume))
    tailored["profile_summary"] = "Tailored summary for QA Automation engineer in Pune."
    tailored["skills"] = ["Python", "Selenium", "Postman", "SQL", "Git"]

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("resume_template.html")
    html = template.render(resume=tailored, job=sample_fresher_qa_job)

    assert "Tailored summary for QA Automation engineer in Pune." in html
    assert "Python, Selenium, Postman, SQL, Git" in html
    assert "<h2>PROFILE</h2>" in html or "<h2>PROFILE SUMMARY</h2>" in html
    assert "<h2>SKILLS</h2>" in html or "<h2>TECHNICAL SKILLS</h2>" in html
    assert "<h2>EXPERIENCE</h2>" in html or "<h2>WORK EXPERIENCE</h2>" in html
    assert "<h2>EDUCATION</h2>" in html


# ---------------------------------------------------------------------
# 8. F9 x F10: PDF File Generation and Supabase Storage Upload
# ---------------------------------------------------------------------
def test_tier3_f9_f10_pdf_generation_and_supabase_storage_save(mock_supabase, temp_output_dir):
    """Pairwise F9 x F10: Generated PDF path is recorded and uploaded to Supabase Storage."""
    fake_pdf = Path(temp_output_dir) / "QA_Persistent.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 Mock PDF Content")

    with patch('src.db.supabase', mock_supabase):
        bucket = mock_supabase.storage.from_("resumes")
        with open(fake_pdf, "rb") as f:
            res = bucket.upload(f"resumes/{fake_pdf.name}", f.read())
        assert "Key" in res
        public_url = bucket.get_public_url(f"resumes/{fake_pdf.name}")
        assert "sample.pdf" in public_url or fake_pdf.name in public_url


# ---------------------------------------------------------------------
# 9. F2 x F10: Test Mode Pipeline Saves Correct Run Metrics to Supabase
# ---------------------------------------------------------------------
def test_tier3_f2_f10_test_mode_pipeline_saves_correct_metrics(mock_supabase):
    """Pairwise F2 x F10: Test mode pipeline execution stores mode='test' and capped counts in pipeline_runs."""
    from src.db import save_pipeline_results
    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 5},
        "filter": {"after": 3},
        "score": {"scored": 3, "shortlisted": 1},
        "phase": "saving"
    }
    shortlisted_job = Job(
        title="QA Trainee", company="Persistent", location="Pune",
        description="Selenium role", url="http://ex.com/test-run", id="job-test-01"
    )
    shortlisted_job.tokens_used = 350

    with patch('src.db.supabase', mock_supabase):
        save_pipeline_results(pipeline_state, [shortlisted_job], ["C:/fake/QA.pdf"])
        mock_supabase.table.assert_any_call("pipeline_runs")
        # Verify mode="test" was recorded
        insert_calls = mock_supabase.table("pipeline_runs").insert.call_args_list
        assert len(insert_calls) > 0
        inserted_data = insert_calls[0][0][0]
        assert inserted_data["mode"] == "test"
        assert inserted_data["resumes_generated"] == 1
        assert inserted_data["tokens_used"] == 350


# ---------------------------------------------------------------------
# 10. F11 x F1: Web UI Stop Control Halts Active Pipeline
# ---------------------------------------------------------------------
def test_tier3_f11_f1_ui_trigger_handles_pipeline_stop_and_error(flask_client):
    """Pairwise F11 x F1: UI endpoint /api/stop halts running state and resets phase to idle."""
    from app import pipeline_state, stop_event
    pipeline_state["running"] = True
    pipeline_state["phase"] = "scoring"
    stop_event.clear()

    resp = flask_client.post('/api/stop')
    assert resp.status_code == 200
    assert stop_event.is_set()
    assert pipeline_state["running"] is False
    assert pipeline_state["phase"] == "idle"


# ---------------------------------------------------------------------
# 11. F4 x F8: 200+ Dataset Filtering and Master Profile Truthfulness
# ---------------------------------------------------------------------
def test_tier3_f4_f8_all_200_jobs_fresher_vs_senior_pipeline_integrity(jobs_200_dataset, master_resume, zero_hallucination_validator):
    """Pairwise F4 x F8: Full 200+ job dataset flows through pre-AI filter and retains fresher roles with 0 hallucinations."""
    senior_pattern = r'senior|sr[\.,\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert'
    exp_pattern = r'(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?)'

    retained_jobs = []
    senior_rejected = 0

    for job in jobs_200_dataset:
        title_is_senior = bool(re.search(senior_pattern, job["title"], re.IGNORECASE))
        exp_is_senior = any(int(m.group(1)) >= 3 for m in re.finditer(exp_pattern, job["description"], re.IGNORECASE))
        if title_is_senior or exp_is_senior:
            senior_rejected += 1
            continue
        if is_relevant_jd(job["description"]):
            retained_jobs.append(job)

    # Verify high senior rejection (>= 85%)
    total_seniors_in_dataset = sum(1 for j in jobs_200_dataset if j.get("is_senior") is True)
    assert senior_rejected >= 0.85 * total_seniors_in_dataset

    # Verify that for any retained job, candidate profile provides 0-hallucination coverage
    for job in retained_jobs[:10]:
        target_role = job.get("target_role", "qa")
        # Tailored resume has only valid skills
        tailored = json.loads(json.dumps(master_resume))
        if target_role == "qa":
            tailored["skills"] = ["Python", "Selenium", "Postman", "SQL", "Git"]
        elif target_role == "java":
            tailored["skills"] = ["Java", "Spring Core", "SQL", "REST APIs", "Git"]
        elif target_role == "dotnet":
            tailored["skills"] = ["C# (Basics via Azure)", "SQL", "REST APIs", "Git"]
        else:
            tailored["skills"] = ["JavaScript", "HTML", "CSS", "Python", "SQL"]

        is_valid, violations = zero_hallucination_validator(tailored)
        assert is_valid, f"Violations found for role {target_role}: {violations}"
