"""
Milestone 5 Test Suite: 1-Page ATS-Friendly PDF Resume Generation.
Verifies:
1. Zero transform: scale() or scaleFactor hacks in src/pdf_generator.py.
2. Modern sans-serif typography (Inter/sans-serif) and subtle royal blue accents (#1e40af).
3. Standard ATS uppercase headings (PROFILE SUMMARY, TECHNICAL SKILLS, WORK EXPERIENCE,
   TECHNICAL PROJECTS, EDUCATION, CERTIFICATIONS).
4. Jinja2 rendering accommodates all 3 projects (SmartApply, CampFlow, Neon-Pulse) without unrendered tags.
5. Playwright generates a real, valid 1-page PDF (len(pages) == 1).
6. 100% machine-readable text extraction via pypdf preserving candidate profile and key sections.
7. Role-lens adaptations ('qa', 'java', 'dotnet', 'fullstack') all fit strictly on 1 page.
8. Standalone generate_resume_pdf() interface works cleanly.
"""
import io
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
def master_resume_data():
    return load_resume()


@pytest.fixture(scope="module")
def jinja_env():
    templates_dir = Path(__file__).parent.parent / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)))


@pytest.fixture(scope="module")
def sample_job_qa():
    job = Job(
        title="QA Automation Engineer",
        company="Infosys Ltd.",
        location="Pune, India",
        description="Looking for QA Engineer skilled in Selenium, Python, JUnit, and Postman.",
        url="https://linkedin.com/jobs/view/9001"
    )
    job.is_testing_role = True
    return job


@pytest.fixture(scope="module")
def sample_job_java():
    job = Job(
        title="Java Developer Fresher",
        company="Persistent Systems",
        location="Pune, India",
        description="Looking for Java Developer skilled in Java, Spring Boot, JDBC, and SQL.",
        url="https://linkedin.com/jobs/view/9002"
    )
    job.is_testing_role = False
    return job


def test_no_transform_scale_hack():
    """Verify that src/pdf_generator.py does not use CSS transform: scale() or scaleFactor hacks."""
    generator_path = Path(__file__).parent.parent / "src" / "pdf_generator.py"
    assert generator_path.exists(), "src/pdf_generator.py must exist"
    code = generator_path.read_text(encoding="utf-8")

    assert "transform" not in code, "CSS transform hack found in src/pdf_generator.py"
    assert "scaleFactor" not in code, "scaleFactor hack found in src/pdf_generator.py"
    assert "document.body.style.transform" not in code, "document.body.style.transform found in src/pdf_generator.py"


def test_template_sans_serif_and_blue_accent():
    """Verify templates/resume_template.html includes clean sans-serif typography and royal blue accent #1e40af."""
    template_path = Path(__file__).parent.parent / "templates" / "resume_template.html"
    assert template_path.exists(), "templates/resume_template.html must exist"
    content = template_path.read_text(encoding="utf-8")

    # Typography asserts
    assert "sans-serif" in content, "Sans-serif font family must be declared in template"
    assert "Inter" in content, "'Inter' font must be present in font-family stack"

    # Subtle royal blue accent assert
    assert "#1e40af" in content, "Royal blue accent color #1e40af must be present in template"
    assert "border-bottom" in content, "Section header bottom border accent must be present"


def test_template_ats_headings():
    """Verify templates/resume_template.html contains all 6 standard ATS section headings in uppercase."""
    template_path = Path(__file__).parent.parent / "templates" / "resume_template.html"
    content = template_path.read_text(encoding="utf-8")

    required_ats_headings = [
        "PROFILE SUMMARY",
        "TECHNICAL SKILLS",
        "WORK EXPERIENCE",
        "TECHNICAL PROJECTS",
        "EDUCATION",
        "CERTIFICATIONS",
    ]
    for heading in required_ats_headings:
        assert heading in content, f"Required standard ATS heading '{heading}' missing from template"


def test_render_html_with_all_3_projects(jinja_env, master_resume_data, sample_job_qa):
    """Verify Jinja2 template renders all 3 candidate projects cleanly with 0 unrendered Jinja tags."""
    tailored = validate_and_sanitize_tailored(master_resume_data, master_resume_data, "qa", job=sample_job_qa)
    template = jinja_env.get_template("resume_template.html")
    rendered = template.render(resume=tailored, job=sample_job_qa)

    # Jinja syntax error check
    assert "{{ " not in rendered, "Found unrendered Jinja2 expression {{ in HTML"
    assert "{% " not in rendered, "Found unrendered Jinja2 block {% in HTML"

    # All 3 projects present
    assert "SmartApply" in rendered, "SmartApply project missing from rendered HTML"
    assert "CampFlow" in rendered, "CampFlow project missing from rendered HTML"
    assert "Neon-Pulse" in rendered, "Neon-Pulse project missing from rendered HTML"

    # Experience and Education present
    assert "CWIPedia Technologies" in rendered, "CWIPedia experience missing from rendered HTML"
    assert "SKNSITS" in rendered, "SKNSITS education missing from rendered HTML"

    # Certifications present
    assert "Microsoft Azure Fundamentals" in rendered, "Azure certification missing from rendered HTML"


def test_pdf_generation_single_page(tmp_path, master_resume_data, sample_job_qa):
    """Verify Playwright renders a real PDF that is strictly 1 single page with all core sections."""
    tailored = validate_and_sanitize_tailored(master_resume_data, master_resume_data, "qa", job=sample_job_qa)
    pdf_out = tmp_path / "test_ats_single_page.pdf"

    generated_path = generate_resume_pdf(tailored, str(pdf_out), job=sample_job_qa)
    assert Path(generated_path).exists(), "Generated PDF file does not exist"

    # Read with pypdf
    reader = pypdf.PdfReader(generated_path)
    page_count = len(reader.pages)
    assert page_count == 1, f"Expected strictly 1-page PDF, but generated {page_count} pages!"

    # Text extraction verification
    text = reader.pages[0].extract_text()
    assert "Kaustubh" in text, "Candidate name not found in PDF text"
    assert "CWIPedia" in text, "Employer CWIPedia not found in PDF text"
    assert "SKNSITS" in text, "Institution SKNSITS not found in PDF text"
    assert "SmartApply" in text, "Project SmartApply not found in PDF text"
    assert "CampFlow" in text, "Project CampFlow not found in PDF text"
    assert "Neon-Pulse" in text, "Project Neon-Pulse not found in PDF text"


def test_plain_text_extractability(tmp_path, master_resume_data, sample_job_java):
    """Verify 100% machine-readability of generated PDF with standard headings and clean text flow."""
    tailored = validate_and_sanitize_tailored(master_resume_data, master_resume_data, "java", job=sample_job_java)
    pdf_out = tmp_path / "test_extractability.pdf"

    generate_resume_pdf(tailored, str(pdf_out), job=sample_job_java)
    reader = pypdf.PdfReader(str(pdf_out))
    text = reader.pages[0].extract_text()

    # Headings extracted cleanly
    expected_headers = [
        "PROFILE SUMMARY",
        "TECHNICAL SKILLS",
        "TECHNICAL PROJECTS",
        "WORK EXPERIENCE",
        "EDUCATION",
        "CERTIFICATIONS",
    ]
    for header in expected_headers:
        assert header in text, f"Heading '{header}' was not extractable from PDF text"

    # No scrambled control characters or null bytes
    assert "\x00" not in text, "Corrupt null bytes found in extracted PDF text"
    assert len(text.strip()) > 300, "Extracted text is too short, possible text layer truncation"


def test_all_role_lenses_strict_single_page(tmp_path, master_resume_data):
    """Verify all 4 role lenses ('qa', 'java', 'dotnet', 'fullstack') generate exactly 1 single page."""
    roles = [
        ("qa", True, "QA Automation Engineer"),
        ("java", False, "Java Backend Developer"),
        ("dotnet", False, ".NET C# Developer"),
        ("fullstack", False, "Full Stack Web Developer"),
    ]

    for role_lens, is_qa, title in roles:
        job = Job(
            title=title,
            company=f"Tech Corp {role_lens}",
            location="Pune, India",
            description=f"Role requiring skills for {title}",
            url=f"https://linkedin.com/jobs/view/{role_lens}"
        )
        job.is_testing_role = is_qa
        tailored = validate_and_sanitize_tailored(master_resume_data, master_resume_data, role_lens, job=job)

        pdf_out = tmp_path / f"test_role_lens_{role_lens}.pdf"
        generate_resume_pdf(tailored, str(pdf_out), job=job)

        reader = pypdf.PdfReader(str(pdf_out))
        assert len(reader.pages) == 1, (
            f"Role lens '{role_lens}' produced {len(reader.pages)} pages instead of 1 page!"
        )


def test_dynamic_section_reordering(tmp_path, master_resume_data, sample_job_qa, sample_job_java):
    """Verify QA role places WORK EXPERIENCE before PROJECTS, whereas Java role places PROJECTS before WORK EXPERIENCE."""
    # 1. QA role (is_testing_role = True)
    tailored_qa = validate_and_sanitize_tailored(master_resume_data, master_resume_data, "qa", job=sample_job_qa)
    pdf_qa = tmp_path / "reorder_qa.pdf"
    generate_resume_pdf(tailored_qa, str(pdf_qa), job=sample_job_qa)
    text_qa = pypdf.PdfReader(str(pdf_qa)).pages[0].extract_text()
    pos_exp_qa = text_qa.find("WORK EXPERIENCE")
    pos_proj_qa = text_qa.find("TECHNICAL PROJECTS")
    assert pos_exp_qa != -1 and pos_proj_qa != -1
    assert pos_exp_qa < pos_proj_qa, "For testing roles, WORK EXPERIENCE must appear before TECHNICAL PROJECTS"

    # 2. Non-QA role (is_testing_role = False)
    tailored_java = validate_and_sanitize_tailored(master_resume_data, master_resume_data, "java", job=sample_job_java)
    pdf_java = tmp_path / "reorder_java.pdf"
    generate_resume_pdf(tailored_java, str(pdf_java), job=sample_job_java)
    text_java = pypdf.PdfReader(str(pdf_java)).pages[0].extract_text()
    pos_exp_java = text_java.find("WORK EXPERIENCE")
    pos_proj_java = text_java.find("TECHNICAL PROJECTS")
    assert pos_exp_java != -1 and pos_proj_java != -1
    assert pos_proj_java < pos_exp_java, "For non-testing roles, TECHNICAL PROJECTS must appear before WORK EXPERIENCE"
