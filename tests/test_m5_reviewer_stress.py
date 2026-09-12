"""
Adversarial Stress Testing for Milestone 5 Reviewer.
Verifies real candidate data (data_folder/plain_text_resume.yaml) against
real-world job fixtures (tests/fixtures/jobs_200_dataset.json).
"""
import json
from pathlib import Path
import pytest
import pypdf

from src.config_loader import load_resume
from src.models import Job
from src.resume_tailor import validate_and_sanitize_tailored, detect_role_lens
from src.pdf_generator import generate_resume_pdf, generate_pdf


@pytest.fixture(scope="module")
def candidate_data():
    return load_resume()


@pytest.fixture(scope="module")
def fixture_jobs():
    fixtures_path = Path(__file__).parent / "fixtures" / "jobs_200_dataset.json"
    with open(fixtures_path, encoding="utf-8") as f:
        return json.load(f)


def test_real_fixture_jobs_all_target_roles(tmp_path, candidate_data, fixture_jobs):
    """Stress test 1-page generation across real jobs in fixtures for all 4 roles."""
    roles = ["qa", "java", "dotnet", "fullstack"]
    tested_count = 0
    
    for target in roles:
        matching = [j for j in fixture_jobs if j.get("target_role") == target and j.get("is_relevant")]
        assert len(matching) > 0, f"No fixture jobs found for role {target}"
        # Test the first 2 jobs in each role
        for job_dict in matching[:2]:
            job = Job(
                title=job_dict["title"],
                company=job_dict["company"],
                location=job_dict["location"],
                description=job_dict["description"],
                url=job_dict["url"]
            )
            job.target_role = job_dict["target_role"]
            job.is_testing_role = (target == "qa")
            role_lens = detect_role_lens(job)
            
            tailored = validate_and_sanitize_tailored(candidate_data, candidate_data, role_lens, job=job)
            pdf_path = tmp_path / f"{job_dict['id']}_{role_lens}.pdf"
            
            out = generate_resume_pdf(tailored, str(pdf_path), job=job)
            assert Path(out).exists()
            
            reader = pypdf.PdfReader(out)
            assert len(reader.pages) == 1, f"Job {job_dict['id']} produced {len(reader.pages)} pages instead of 1!"
            
            text = reader.pages[0].extract_text()
            assert "Kaustubh" in text
            assert "PROFILE SUMMARY" in text
            assert "TECHNICAL SKILLS" in text
            assert "EDUCATION" in text
            assert "CERTIFICATIONS" in text
            assert "CWIPedia" in text
            assert "SmartApply" in text
            assert "CampFlow" in text
            assert "Neon-Pulse" in text
            
            pos_exp = text.find("WORK EXPERIENCE")
            pos_proj = text.find("TECHNICAL PROJECTS")
            assert pos_exp != -1 and pos_proj != -1
            if job.is_testing_role:
                assert pos_exp < pos_proj, f"QA job {job_dict['id']} must have WORK EXPERIENCE before PROJECTS"
            else:
                assert pos_proj < pos_exp, f"Non-QA job {job_dict['id']} must have PROJECTS before WORK EXPERIENCE"
            tested_count += 1

    assert tested_count == 8, f"Expected 8 jobs tested, got {tested_count}"


def test_adversarial_long_summary_budgeting(tmp_path, candidate_data):
    """Adversarially test long profile summary to ensure it stays within 1 page."""
    import copy
    long_data = copy.deepcopy(candidate_data)
    # Give candidate a 3-sentence meaty summary
    long_data["profile_summary"] = (
        "Accomplished Software Engineer with strong background in backend systems, automated testing, "
        "and cloud infrastructures. Proven expertise in building scalable microservices with Java, Python, and SQL, "
        "reducing latency by 35% across high-throughput distributed architectures."
    )
    job = Job(
        title="Software Engineer Fresher",
        company="Global Enterprise Inc.",
        location="Pune, India",
        description="Looking for Software Engineer with strong Python and backend development skills.",
        url="https://linkedin.com/jobs/view/9999"
    )
    job.is_testing_role = False
    
    tailored = validate_and_sanitize_tailored(long_data, candidate_data, "fullstack", job=job)
    pdf_path = tmp_path / "long_summary.pdf"
    generate_resume_pdf(tailored, str(pdf_path), job=job)
    
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 1, f"Long summary overflowed to {len(reader.pages)} pages!"


def test_adversarial_special_characters_in_company_and_title(tmp_path, candidate_data):
    """Test weird characters in title / company for Windows file path safety."""
    from playwright.sync_api import sync_playwright
    import os
    
    job = Job(
        title="Senior/Lead C# & .NET Developer (Fresher <Level 1>)? *Pune*",
        company="Persistent/TCS | India \"Tech\" : Corp",
        location="Pune, India",
        description="Software development role",
        url="https://test.com"
    )
    date_str = "2026-09-06"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            pdf_path = generate_pdf(job, candidate_data, date_str, page)
            assert pdf_path != "", "generate_pdf failed with special characters"
            assert Path(pdf_path).exists(), f"PDF does not exist at {pdf_path}"
            # Ensure invalid characters are not in filename
            invalid = [':', '/', '\\', '*', '?', '"', '<', '>', '|']
            for char in invalid:
                assert char not in Path(pdf_path).name
        finally:
            browser.close()


def test_no_residual_scale_hack_in_codebase():
    """Verify that neither pdf_generator.py nor resume_template.html contain any scaling hacks."""
    src_pdf = (Path(__file__).parent.parent / "src" / "pdf_generator.py").read_text(encoding="utf-8")
    tpl_html = (Path(__file__).parent.parent / "templates" / "resume_template.html").read_text(encoding="utf-8")
    
    for bad_token in ["scaleFactor", "transform: scale", "document.body.style.transform"]:
        assert bad_token not in src_pdf, f"Found {bad_token} in src/pdf_generator.py"
        assert bad_token not in tpl_html, f"Found {bad_token} in templates/resume_template.html"
