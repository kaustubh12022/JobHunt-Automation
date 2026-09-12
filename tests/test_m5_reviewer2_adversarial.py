"""
Milestone 5 Reviewer 2 Adversarial & Quality Verification Suite.
Evaluates:
1. ATS machine readability and clean plain text extraction.
2. Single-page budgeting under real jobs and edge case payloads.
3. Retention and clean formatting of all 3 projects (SmartApply, CampFlow, Neon-Pulse).
4. Edge cases: long project descriptions, long URLs, missing optional sections.
5. Backwards compatibility of PDF generation interfaces.
6. Typography and absence of transform: scale() hacks.
"""
import copy
import json
import os
import re
from pathlib import Path
import pytest
import pypdf
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from src.models import Job
from src.config_loader import load_resume, load_config
from src.resume_tailor import validate_and_sanitize_tailored
from src.pdf_generator import generate_pdf, generate_resume_pdf


@pytest.fixture(scope="module")
def master_resume():
    return load_resume()


@pytest.fixture(scope="module")
def real_jobs_dataset():
    fixture_path = Path(__file__).parent / "fixtures" / "jobs_200_dataset.json"
    assert fixture_path.exists(), f"Fixtures not found at {fixture_path}"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_r2_integrity_no_hardcoded_or_facade_hacks():
    """Verify src/pdf_generator.py and templates/resume_template.html have no hardcoded dummy text or scale hacks."""
    gen_path = Path(__file__).parent.parent / "src" / "pdf_generator.py"
    gen_code = gen_path.read_text(encoding="utf-8")

    assert "transform: scale" not in gen_code
    assert "scaleFactor" not in gen_code
    assert "page.evaluate" not in gen_code
    assert "A4_HEIGHT_PX" not in gen_code

    template_path = Path(__file__).parent.parent / "templates" / "resume_template.html"
    tmpl_code = template_path.read_text(encoding="utf-8")
    assert "transform: scale" not in tmpl_code
    assert "#1e40af" in tmpl_code
    assert "Inter" in tmpl_code


def test_r2_real_candidate_all_3_projects_retained(tmp_path, master_resume, real_jobs_dataset):
    """
    Verify all 3 candidate projects (SmartApply, CampFlow, Neon-Pulse) are strictly retained
    and rendered cleanly for real jobs from jobs_200_dataset.json.
    """
    # Pick a real job
    sample_raw = real_jobs_dataset[0]
    job = Job(
        title=sample_raw["title"],
        company=sample_raw["company"],
        location=sample_raw["location"],
        description=sample_raw["description"],
        url=sample_raw["url"]
    )
    job.is_testing_role = "qa" in sample_raw.get("target_role", "").lower()

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "qa", job=job)
    pdf_path = tmp_path / "real_job_projects.pdf"
    out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)

    assert Path(out_path).exists()
    reader = pypdf.PdfReader(out_path)
    assert len(reader.pages) == 1, f"Expected 1 page, got {len(reader.pages)}"

    text = reader.pages[0].extract_text()
    assert "SmartApply" in text, "SmartApply project missing from PDF text"
    assert "CampFlow" in text, "CampFlow project missing from PDF text"
    assert "Neon-Pulse" in text, "Neon-Pulse project missing from PDF text"


def test_r2_plain_text_reading_order_and_no_scrambled_columns(tmp_path, master_resume, real_jobs_dataset):
    """
    Verify plain text extracted from rendered PDF has standard ATS headings in correct order,
    and no scrambled columns or corrupted characters.
    """
    job = Job(
        title="Fresher Software Engineer",
        company="Tata Consultancy Services",
        location="Pune, India",
        description="Looking for entry level software engineer with Java and Python.",
        url="https://tcs.com/jobs/1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "fullstack", job=job)
    pdf_path = tmp_path / "test_reading_order.pdf"
    out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)

    reader = pypdf.PdfReader(out_path)
    text = reader.pages[0].extract_text()

    # Candidate Name must be first line or top of text
    first_lines = text.strip().split("\n")[:3]
    top_text = " ".join(first_lines)
    assert "Kaustubh" in top_text and "Kale" in top_text, f"Candidate name not at top: {top_text}"

    # Verify standard ATS headings
    headings = ["PROFILE SUMMARY", "TECHNICAL SKILLS", "TECHNICAL PROJECTS", "WORK EXPERIENCE", "EDUCATION", "CERTIFICATIONS"]
    indices = [text.find(h) for h in headings]
    for h, idx in zip(headings, indices):
        assert idx != -1, f"Missing heading '{h}'"

    # Headings must appear in sequential order
    for i in range(len(indices) - 1):
        assert indices[i] < indices[i + 1], f"Heading '{headings[i]}' (pos {indices[i]}) appeared after '{headings[i+1]}' (pos {indices[i+1]})"

    # Integrity check: no null bytes or replacement chars
    assert "\x00" not in text, "Null byte found in PDF text"
    assert "\ufffd" not in text, "Unicode replacement character found in PDF text"


def test_r2_edge_case_long_project_descriptions(tmp_path, master_resume):
    """
    Edge Case 1: Long project descriptions (extra detailed bullets, ~200 chars each).
    Verify that single-page budgeting still holds strictly (len(pages) == 1).
    """
    long_resume = copy.deepcopy(master_resume)
    for p in long_resume["projects"]:
        p["description_bullets"] = [
            "Engineered high-performance microservices utilizing modern design patterns and REST APIs, ensuring sub-50ms latency across 10,000+ daily requests while achieving high availability and fault tolerance.",
            "Designed and implemented automated CI/CD deployment pipelines integrating pytest, Playwright, and GitHub Actions, reducing manual testing effort by 85% and improving release cadence."
        ]

    job = Job(
        title="Full Stack Developer Fresher",
        company="Capgemini",
        location="Pune, India",
        description="Full stack role with Java and JavaScript.",
        url="https://capgemini.com/jobs/1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(long_resume, master_resume, "fullstack", job=job)
    pdf_path = tmp_path / "edge_long_descriptions.pdf"
    out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)

    reader = pypdf.PdfReader(out_path)
    assert len(reader.pages) == 1, f"Long descriptions caused page overflow: {len(reader.pages)} pages"


def test_r2_edge_case_long_urls_and_contact_fields(tmp_path, master_resume):
    """
    Edge Case 2: Long URLs and extended contact items.
    Verify clean rendering without horizontal overflow or crashing.
    """
    long_url_resume = copy.deepcopy(master_resume)
    long_url_resume["personal_information"]["email"] = "kaustubh.kale.extra.long.professional.email.identifier@subdomain.domain.co.in"
    long_url_resume["personal_information"]["linkedin"] = "https://www.linkedin.com/in/kaustubh-kale-software-development-engineer-entry-level-specialist"
    long_url_resume["personal_information"]["github"] = "https://github.com/kaustubh12022-super-long-open-source-portfolio-profile-repository"

    job = Job(
        title="Software Engineer Trainee",
        company="Wipro",
        location="Pune, India",
        description="Java, SQL, Git",
        url="https://wipro.com/jobs/1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(long_url_resume, master_resume, "java", job=job)
    pdf_path = tmp_path / "edge_long_urls.pdf"
    out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)

    assert Path(out_path).exists()
    reader = pypdf.PdfReader(out_path)
    assert len(reader.pages) == 1, f"Long URLs caused page overflow: {len(reader.pages)} pages"
    text = reader.pages[0].extract_text()
    assert "kaustubh.kale" in text


def test_r2_edge_case_missing_optional_sections(tmp_path, master_resume):
    """
    Edge Case 3: Missing optional fields (e.g. no phone prefix, no city, empty certifications, no summary).
    Verify Jinja2 template handles missing data gracefully without rendering 'None' or crashing.
    """
    sparse_resume = copy.deepcopy(master_resume)
    sparse_resume["personal_information"]["phone_prefix"] = ""
    sparse_resume["personal_information"]["city"] = ""
    sparse_resume["personal_information"]["country"] = ""
    sparse_resume["personal_information"]["address"] = "Pune"
    sparse_resume["personal_information"]["github"] = ""
    sparse_resume["certifications"] = []
    sparse_resume["profile_summary"] = ""

    job = Job(
        title="Junior Tester",
        company="Cognizant",
        location="Pune, India",
        description="Testing fundamentals, Selenium",
        url="https://cognizant.com/jobs/1"
    )
    job.is_testing_role = True

    # Tailor without profile_summary fallback to test empty summary handling in template
    tailored = validate_and_sanitize_tailored(sparse_resume, master_resume, "qa", job=job)
    tailored["profile_summary"] = ""  # explicitly empty
    tailored["certifications"] = []

    pdf_path = tmp_path / "edge_sparse.pdf"
    out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)

    assert Path(out_path).exists()
    reader = pypdf.PdfReader(out_path)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()

    assert "None" not in text, f"Found literal 'None' in extracted sparse resume text: {text}"
    assert "CERTIFICATIONS" not in text, "Empty certifications section was unexpectedly rendered"


def test_r2_backwards_compatibility_generate_pdf(tmp_path, master_resume):
    """
    Verify original generate_pdf(job, tailored_resume, date_str, page) signature
    works seamlessly with shared Playwright page (as used in app.py and run.py).
    """
    job = Job(
        title="Associate Software Engineer",
        company="Oracle Financial Services",
        location="Pune, India",
        description="Java, SQL, Spring",
        url="https://oracle.com/jobs/1"
    )
    job.is_testing_role = False
    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "java", job=job)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            pdf_path_str = generate_pdf(job, tailored, "2026-09-06", page)
            assert pdf_path_str != "", "generate_pdf returned empty string"
            assert Path(pdf_path_str).exists(), f"File {pdf_path_str} was not created"
            reader = pypdf.PdfReader(pdf_path_str)
            assert len(reader.pages) == 1, f"Legacy generate_pdf generated {len(reader.pages)} pages"
        finally:
            browser.close()
