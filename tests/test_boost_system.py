"""
test_boost_system.py — Comprehensive Unit & Integration Test Suite for the Job Application Boost System.

Validates all 5 pillars:
1. Fast polling / early-applicant detection (<20 applicants rule)
2. Deduplication and consultancy/spam repost veto filtering
3. ATS resume matching and compliance without hallucination
4. Local profile and credential persistence (profile.json) leveraging Desktop resume
5. Automated application workflow / tracker with verified submission auditing and morning digest reporting
"""

import os
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from src.models import Job
from src.profile_manager import (
    load_desktop_resume_yaml,
    build_profile_from_resume,
    validate_profile_ats_invariants,
    sync_profile_from_desktop,
    get_profile
)
from src.early_applicant import (
    extract_applicant_count_and_tier,
    evaluate_job_early_applicant,
    filter_early_applicants,
    FastPollingEngine
)
from src.consultancy_veto import (
    is_consultancy_or_spam,
    deduplicate_and_veto_reposts,
    normalize_url_for_dedup,
    compute_job_fingerprint,
    compute_description_hash
)
from src.tracker import (
    init_db,
    upsert_job,
    batch_upsert_jobs,
    record_submission_audit,
    get_daily_metrics,
    get_pending_early_opportunities,
    get_recent_submission_audits
)
from src.morning_digest import (
    generate_morning_digest,
    build_morning_digest_markdown
)
from ats_verifier import audit_resume_pdf


# ── PILLAR 4 TESTS: LOCAL PROFILE PERSISTENCE & DESKTOP RESUME SYNC ──

def test_pillar4_load_and_build_profile():
    """Verify loading resume from Desktop and building normalized profile."""
    resume_data = load_desktop_resume_yaml()
    assert "personal_information" in resume_data
    assert resume_data["personal_information"]["name"] == "Kaustubh"
    assert resume_data["personal_information"]["surname"] == "Kale"

    profile = build_profile_from_resume(resume_data)
    assert profile["name"] == "Kaustubh Kale"
    assert profile["contact"]["phone"] == "+91-9975526627"
    assert "Pune" in profile["contact"]["location"]
    assert len(profile["skills"]) >= 20
    assert len(profile["projects"]) >= 3
    assert "skills_structured" in profile
    assert "Core Languages" in profile["skills_structured"]
    assert "eeo_answers" in profile
    assert profile["eeo_answers"]["gender"] == "Male"
    assert profile["eeo_answers"]["citizenship"] == "India"


def test_pillar4_ats_invariants_validation():
    """Verify ATS Golden Standard compliance: 4-digit years, phone, CGPA, 10th/12th."""
    profile = get_profile()
    is_valid, errors = validate_profile_ats_invariants(profile)
    assert is_valid is True, f"Profile failed ATS invariants: {errors}"
    assert len(errors) == 0


def test_pillar4_sync_workflow():
    """Verify sync_profile_from_desktop creates valid config/profile.json."""
    result = sync_profile_from_desktop(save_to_desktop=False)
    assert result["success"] is True
    assert result["skills_count"] > 30
    assert result["ats_valid"] is True


# ── PILLAR 1 TESTS: EARLY APPLICANT (<20 RULE) DETECTION ──

def test_pillar1_applicant_count_extraction():
    """Verify applicant count extraction across various portal patterns."""
    cases = [
        ("Be among the first 25 applicants for this Java role", 25, True),
        ("Under 10 applicants have applied so far", 10, True),
        ("< 20 applicants", 20, True),
        ("Applicants: 7. Apply before it closes.", 7, False),
        ("14 applicants applied", 14, False),
        ("Over 200 applicants applied", 200, False),
    ]
    for text, expected_count, is_explicit_early in cases:
        res = extract_applicant_count_and_tier(text)
        assert res["applicant_count"] == expected_count, f"Failed on text: {text}"
        if is_explicit_early:
            assert res["explicit_early_badge"] is True


def test_pillar1_tier_classification_less_than_20():
    """Verify <20 applicant rule maps to Tier 1 / Tier 2 priorities."""
    tier1_res = extract_applicant_count_and_tier("Applicants: 5")
    assert tier1_res["early_priority_tier"] == "TIER_1_IMMEDIATE"
    assert tier1_res["is_early_applicant"] is True
    assert tier1_res["priority_score_boost"] == 25

    tier2_res = extract_applicant_count_and_tier("18 applicants")
    assert tier2_res["early_priority_tier"] == "TIER_2_EARLY"
    assert tier2_res["is_early_applicant"] is True
    assert tier2_res["priority_score_boost"] == 15

    tier4_res = extract_applicant_count_and_tier("Over 150 applicants")
    assert tier4_res["early_priority_tier"] == "TIER_4_SATURATED"
    assert tier4_res["is_early_applicant"] is False
    assert tier4_res["priority_score_boost"] < 0


def test_pillar1_evaluate_and_filter_early_applicants():
    """Verify filtering separates <20 applicants from saturated postings."""
    jobs = [
        Job(title="Junior Java Developer", company="InnoTech", location="Pune", description="Under 15 applicants. Java, Spring Boot.", url="http://job1.com"),
        Job(title="Backend Engineer", company="GlobalCorp", location="Bangalore", description="Over 120 applicants. Python, Django.", url="http://job2.com"),
        Job(title="QA Automation Intern", company="TestLab", location="Pune", description="Be among the first 25 applicants. Selenium.", url="http://job3.com"),
    ]
    early, other = filter_early_applicants(jobs, max_applicants=20)
    assert len(early) >= 1
    assert any(j.company == "InnoTech" for j in early)
    assert any(j.company == "GlobalCorp" for j in other)


def test_pillar1_fast_polling_engine():
    """Verify FastPollingEngine tracks seen URLs and alerts on early applicants."""
    alerts = []
    poller = FastPollingEngine(
        poll_interval_seconds=1,
        max_applicants_rule=20,
        on_early_applicant_found=lambda j: alerts.append(j.company)
    )

    batch1 = [
        Job(title="Dev 1", company="Alpha", location="Pune", description="Applicants: 8. Java.", url="http://poll1.com"),
        Job(title="Dev 2", company="Beta", location="Pune", description="Applicants: 80. Java.", url="http://poll2.com")
    ]
    processed = poller.process_incoming_jobs(batch1)
    assert len(processed) == 2
    assert "Alpha" in alerts
    assert "Beta" not in alerts

    # Re-processing same URLs should be ignored as duplicates
    processed_again = poller.process_incoming_jobs(batch1)
    assert len(processed_again) == 0


# ── PILLAR 2 TESTS: CONSULTANCY & REPOST VETO FILTERING ──

def test_pillar2_fee_trap_veto():
    """Verify absolute rejection of fee traps and pay-for-placement scams."""
    fee_jobs = [
        Job(title="Java Fresher", company="ScamHub", location="Pune", description="Candidate must pay registration charges of Rs 500.", url="http://s1.com"),
        Job(title="Software Trainee", company="Placement Agency", location="Pune", description="Pay after placement scheme applies.", url="http://s2.com"),
        Job(title="Junior Developer", company="Training Inst", location="Pune", description="100% placement guarantee with training fees.", url="http://s3.com"),
        Job(title="Associate Dev", company="FakeCorp", location="Pune", description="Security deposit refundable after 6 months.", url="http://s4.com"),
    ]
    for j in fee_jobs:
        vetoed, reason, matched = is_consultancy_or_spam(j)
        assert vetoed is True, f"Failed to veto fee trap: {j.description}"
        assert "Fee Trap" in reason


def test_pillar2_non_tech_role_veto():
    """Verify non-technical telecalling/BPO roles disguised as tech are vetoed."""
    non_tech_jobs = [
        Job(title="Software Trainee - Telecalling", company="CallTech", location="Pune", description="Make outbound calls to leads.", url="http://nt1.com"),
        Job(title="Junior Associate / BPO Voice Process", company="BPO Global", location="Pune", description="Inbound call handling.", url="http://nt2.com"),
        Job(title="Data Entry Operator & Trainee", company="OfficeData", location="Pune", description="Type records into Excel.", url="http://nt3.com"),
    ]
    for j in non_tech_jobs:
        vetoed, reason, _ = is_consultancy_or_spam(j)
        assert vetoed is True, f"Failed to veto non-tech role: {j.title}"
        assert "Non-Technical" in reason


def test_pillar2_deduplication_and_repost_filter():
    """Verify URL deduplication and multi-city duplicate description flood veto."""
    identical_jd = "Our company is seeking 20 freshers for Java, SQL, and Spring Boot backend engineering. Immediate joining."
    jobs = [
        Job(title="Java Developer", company="AgencyX", location="Pune", description=identical_jd, url="http://dup.com/1?utm_source=naukri"),
        Job(title="Java Developer", company="AgencyX", location="Mumbai", description=identical_jd, url="http://dup.com/1?utm_source=linkedin"), # Duplicate URL
        Job(title="Java Developer", company="AgencyX", location="Bangalore", description=identical_jd, url="http://dup.com/2"), # Repost 2
        Job(title="Java Developer", company="AgencyX", location="Hyderabad", description=identical_jd, url="http://dup.com/3"), # Repost 3 (Flood veto)
    ]
    valid, vetoed, metrics = deduplicate_and_veto_reposts(jobs)
    assert len(valid) == 2  # First unique URL + second city, 3rd city triggers flood veto
    assert len(vetoed) == 2
    assert metrics["vetoed_duplicate_urls"] >= 1


# ── PILLAR 3 TESTS: ATS RESUME COMPLIANCE & ZERO HALLUCINATION ──

def test_pillar3_desktop_resume_ats_compliance():
    """Verify candidate's base resume PDF on Desktop passes ATS standards."""
    desktop_pdf = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop" / "Resume_Dev_Updated.pdf"
    if desktop_pdf.exists():
        audit = audit_resume_pdf(str(desktop_pdf))
        assert audit["passed"] is True, f"Desktop resume failed ATS audit: {audit['errors']}"
        assert audit["details"]["page_count"] == 1


# ── PILLAR 5 TESTS: APPLICATION TRACKER & MORNING DIGEST ──

def test_pillar5_tracker_db_workflow():
    """Verify SQLite tracking database upserts and submission auditing."""
    init_db()
    test_job = Job(
        id="test-job-999",
        title="Associate Java Engineer",
        company="BoostTech Solutions",
        location="Pune",
        description="Java, Spring Boot, REST APIs.",
        url="https://boosttech.io/apply/999",
        applicant_count=12,
        is_early_applicant=True,
        early_priority_tier="TIER_2_EARLY",
        score=88
    )
    upsert_job(test_job, status="SHORTLISTED")

    # Record verified submission audit
    audit_id = record_submission_audit(
        job_id="test-job-999",
        portal="Naukri",
        company="BoostTech Solutions",
        title="Associate Java Engineer",
        confirmation_id="CONF-TEST-999",
        verified=True,
        notes="Verified 1-Click Submission"
    )
    assert audit_id > 0

    recent_audits = get_recent_submission_audits(limit=5)
    assert any(a["confirmation_id"] == "CONF-TEST-999" for a in recent_audits)


def test_pillar5_morning_digest_generation():
    """Verify Morning Digest builds valid Markdown and JSON telemetry files."""
    res = generate_morning_digest()
    assert res["success"] is True
    assert os.path.exists(res["markdown_path"])
    assert os.path.exists(res["json_path"])

    with open(res["markdown_path"], "r", encoding="utf-8") as f:
        content = f.read()
    assert "JobHunt Executive Morning Digest" in content
    assert "Daily Application Funnel" in content
    assert "Early-Applicant Opportunities" in content
    assert "Consultancy, Fee-Trap & Repost Veto Summary" in content


# ── ROBUSTNESS & EDGE CASE TESTS: FIX VERIFICATION ──

def test_pillar1_evaluate_job_early_applicant_idempotency():
    """Verify evaluating early applicant metrics multiple times is strictly idempotent."""
    job = Job(
        title="Junior Java Developer",
        company="IdempotentCo",
        location="Pune",
        description="Under 5 applicants. Core Java and Spring.",
        url="http://idem.co/job/1"
    )
    job.score = 70

    # First evaluation: Tier 1 (+25 boost) -> score 95
    evaluate_job_early_applicant(job)
    assert job.score == 95
    assert job.early_priority_tier == "TIER_1_IMMEDIATE"
    assert job.is_early_applicant is True

    # Second evaluation: must remain 95 (NOT 100 or higher)
    evaluate_job_early_applicant(job)
    assert job.score == 95

    # Third evaluation: must still remain 95
    evaluate_job_early_applicant(job)
    assert job.score == 95


def test_pillar1_linkedin_and_naukri_phrasing_detection():
    """Verify extraction of LinkedIn 'Be one of the first 25 applicants' and Naukri count formats."""
    # LinkedIn: "Be one of the first 25 applicants" (Must be Early Tier 2, not standard!)
    li_res = extract_applicant_count_and_tier("Be one of the first 25 applicants")
    assert li_res["is_early_applicant"] is True
    assert li_res["early_priority_tier"] == "TIER_2_EARLY"
    assert li_res["explicit_early_badge"] is True

    # LinkedIn: "Less than 10 applicants"
    less10 = extract_applicant_count_and_tier("Less than 10 applicants")
    assert less10["is_early_applicant"] is True
    assert less10["applicant_count"] == 10

    # Naukri: "0 - 5 applicants"
    naukri_res = extract_applicant_count_and_tier("0 - 5 applicants")
    assert naukri_res["applicant_count"] == 5
    assert naukri_res["is_early_applicant"] is True

    # Candidate applied phrases: "12 candidates applied"
    cand_res = extract_applicant_count_and_tier("12 candidates applied")
    assert cand_res["applicant_count"] == 12
    assert cand_res["is_early_applicant"] is True

    # People applied: "8 people have applied"
    ppl_res = extract_applicant_count_and_tier("8 people have applied")
    assert ppl_res["applicant_count"] == 8
    assert ppl_res["is_early_applicant"] is True


def test_pillar2_adversarial_and_spaced_fee_traps():
    """Verify rejection of adversarial spaced text and comprehensive scam patterns."""
    adversarial_cases = [
        "r e g i s t r a t i o n   c h a r g e s required for entry",
        "Candidate is required to pay 500 for training",
        "Candidate needs to pay onboarding fee",
        "Candidate will have to pay registration charges",
        "Assessment fee of Rs 350 for online test",
        "Exam fee required before interview scheduling",
        "Interview charges: Rs 300 to be paid upfront",
        "Pay Rs 1000 for verification and badge",
        "Pay INR 500 for application fee",
        "Candidate has to deposit Rs 5000",
        "Laptop security deposit of Rs 10000",
        "Training and placement program with nominal fees",
        "Upfront fee of Rs 2000 required"
    ]
    for desc in adversarial_cases:
        job = Job(title="Java Trainee", company="ScamCo", location="Pune", description=desc, url="http://scam.org")
        vetoed, reason, matched = is_consultancy_or_spam(job)
        assert vetoed is True, f"Failed to veto fee trap with description: '{desc}'"
        assert "Fee Trap" in reason or "Direct Upfront Payment" in reason


def test_pillar5_tracker_status_sync_to_applied():
    """Verify upsert_job sets job.id and record_submission_audit transitions tracked_jobs to APPLIED."""
    from src.tracker import get_db_connection
    test_job = Job(
        title="Software Engineer Intern",
        company="SyncCo Innovations",
        location="Pune",
        description="Java, React, SQL.",
        url="http://syncco.io/apply/101"
    )
    assert test_job.id is None
    upsert_job(test_job, status="SHORTLISTED")
    assert test_job.id is not None
    saved_id = test_job.id

    # Record submission audit
    record_submission_audit(
        job_id=saved_id,
        portal="Naukri",
        company=test_job.company,
        title=test_job.title,
        confirmation_id="CONF-SYNC-101",
        verified=True
    )

    # Check database status is actually updated to APPLIED
    conn = get_db_connection()
    row = conn.cursor().execute("SELECT status FROM tracked_jobs WHERE id = ?", (saved_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row["status"] == "APPLIED"


def test_pillar4_pdf_resume_loading_and_extraction():
    """Verify loading from Desktop Resume_Dev_Updated.pdf succeeds and extracts valid data."""
    desktop_pdf = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop" / "Resume_Dev_Updated.pdf"
    if desktop_pdf.exists():
        data = load_desktop_resume_yaml(str(desktop_pdf))
        assert "personal_information" in data
        assert data["personal_information"]["phone"] == "+91-9975526627"
        profile = build_profile_from_resume(data)
        assert profile["name"] == "Kaustubh Kale"
        assert len(profile["skills"]) > 15


def test_pillar3_deterministic_tailoring_integration():
    """Verify zero-AI deterministic tailoring generates valid ATS resume dict for a job."""
    from src.resume_tailor import tailor_resume_deterministic
    job = Job(
        title="Java Developer",
        company="TestCorp",
        location="Pune",
        description="Hands-on experience with Java, Spring Boot, REST APIs, MySQL, and Maven required.",
        url="http://testcorp.com/apply"
    )
    tailored = tailor_resume_deterministic(job)
    assert "skills" in tailored
    assert any("java" in s.lower() for s in tailored["skills"])
    assert "experience_details" in tailored
    assert "projects" in tailored


def test_end_to_end_boost_pipeline_run(monkeypatch):
    """Verify run_full_boost_pipeline executes all 5 pillars end-to-end without crashing."""
    from boost_runner import run_full_boost_pipeline

    sample_jobs = [
        Job(
            title="Junior Software Engineer",
            company="E2E Corp",
            location="Pune",
            description="Be one of the first 10 applicants. Java, Spring Boot, MySQL.",
            url="https://e2ecorp.com/careers/1"
        ),
        Job(
            title="Full Stack Developer",
            company="Fee Trap Scam Ltd",
            location="Pune",
            description="Candidate must pay registration charges of Rs 500.",
            url="https://scam.com/careers/2"
        ),
        Job(
            title="Associate Backend Engineer",
            company="CloudTech Innovations",
            location="Bangalore",
            description="Under 15 applicants. Python, FastAPI, SQL.",
            url="https://cloudtech.com/careers/3"
        )
    ]

    # Mock scraper to return sample_jobs as tuple (jobs, stats)
    monkeypatch.setattr("src.scraper.run_scraper", lambda **kwargs: (sample_jobs, {"found": len(sample_jobs)}))

    # Run full boost pipeline
    run_full_boost_pipeline(test_mode=True, max_applicants=20)

    # Verify tracker database has E2E Corp recorded
    from src.tracker import get_db_connection
    conn = get_db_connection()
    e2e_row = conn.cursor().execute("SELECT status, applicant_count, is_early_applicant FROM tracked_jobs WHERE company = 'E2E Corp'").fetchone()
    scam_row = conn.cursor().execute("SELECT status, veto_reason FROM tracked_jobs WHERE company = 'Fee Trap Scam Ltd'").fetchone()
    conn.close()

    assert e2e_row is not None
    assert e2e_row["status"] == "APPLIED"  # Submitted and verified
    assert e2e_row["is_early_applicant"] == 1

    assert scam_row is not None
    assert scam_row["status"] == "VETOED_SPAM"
    assert "Fee Trap" in scam_row["veto_reason"]


