"""
Milestone 5 Forensic Auditor Independent Verification & Stress Test Suite.
Authored by: Forensic Auditor (teamwork_preview_auditor_m5_1)
Mission:
1. Forensic verification of no transform: scale() or hidden DOM shrinkage hacks.
2. Forensic AST analysis of src/pdf_generator.py to verify real Playwright logic (no facades/mocks).
3. DOM-level verification in headless browser runtime (computed transform == 'none', zoom == '1').
4. Empirical verification using original candidate data (plain_text_resume.yaml) and real-world job fixtures (jobs_200_dataset.json).
5. ATS readability and strict 1-page compliance across diverse roles.
"""
import ast
import json
from pathlib import Path
import pytest
import pypdf
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from src.models import Job
from src.config_loader import load_resume
from src.resume_tailor import validate_and_sanitize_tailored, detect_role_lens
from src.pdf_generator import generate_resume_pdf


@pytest.fixture(scope="module")
def candidate_data():
    return load_resume()


@pytest.fixture(scope="module")
def jobs_200_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "jobs_200_dataset.json"
    assert fixture_path.exists(), f"Fixture not found at {fixture_path}"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_forensic_no_transform_scale_anywhere():
    """Forensic Check 1: Ensure no transform: scale, scaleFactor, or zoom hacks in generator or template."""
    pdf_gen_path = Path(__file__).parent.parent / "src" / "pdf_generator.py"
    template_path = Path(__file__).parent.parent / "templates" / "resume_template.html"

    pdf_code = pdf_gen_path.read_text(encoding="utf-8")
    template_code = template_path.read_text(encoding="utf-8")

    # Check for transform: scale in src/pdf_generator.py
    assert "transform" not in pdf_code, "Found 'transform' in src/pdf_generator.py"
    assert "scaleFactor" not in pdf_code, "Found 'scaleFactor' in src/pdf_generator.py"
    assert "document.body.style" not in pdf_code, "Found DOM style manipulation in src/pdf_generator.py"
    assert "evaluate(" not in pdf_code, "Found page.evaluate in src/pdf_generator.py"

    # Check template for CSS transforms or scaling hacks
    assert "transform: scale" not in template_code, "Found 'transform: scale' in template"
    assert "zoom:" not in template_code, "Found 'zoom:' CSS property in template"
    assert "transform-origin" not in template_code, "Found 'transform-origin' in template"


def test_forensic_ast_no_facade_in_pdf_generator():
    """Forensic Check 2: AST analysis of src/pdf_generator.py confirms authentic Playwright execution."""
    pdf_gen_path = Path(__file__).parent.parent / "src" / "pdf_generator.py"
    tree = ast.parse(pdf_gen_path.read_text(encoding="utf-8"))

    func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert "generate_pdf" in func_names, "generate_pdf must exist in src/pdf_generator.py"
    assert "generate_resume_pdf" in func_names, "generate_resume_pdf must exist in src/pdf_generator.py"

    # Ensure functions are not facades (no simple 'return constant' or 'pass')
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("generate_pdf", "generate_resume_pdf"):
            calls = [c.func.attr for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)]
            assert "pdf" in calls, f"Function {node.name} does not call page.pdf!"
            assert "set_content" in calls, f"Function {node.name} does not call page.set_content!"


def test_forensic_dom_runtime_metrics(candidate_data):
    """Forensic Check 3: Launch Playwright and verify computed DOM styles, zero scale, and scrollHeight."""
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("resume_template.html")
    html_content = template.render(resume=candidate_data, job=None)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)

        metrics = page.evaluate("""() => {
            const bodyStyle = window.getComputedStyle(document.body);
            return {
                transform: bodyStyle.transform,
                zoom: bodyStyle.zoom,
                scrollHeight: document.documentElement.scrollHeight,
                bodyScrollHeight: document.body.scrollHeight,
                bodyHeight: bodyStyle.height,
                fontFamily: bodyStyle.fontFamily
            };
        }""")
        browser.close()

    # Computed transform must be strictly 'none'
    assert metrics["transform"] == "none", f"Body transform is not 'none': {metrics['transform']}"
    # Zoom must be '1' or 'normal'
    assert metrics["zoom"] in ("1", "normal", ""), f"Body zoom is not 1: {metrics['zoom']}"
    # Font family must contain Inter or sans-serif
    assert "Inter" in metrics["fontFamily"] or "sans-serif" in metrics["fontFamily"]
    # scrollHeight must fit comfortably within A4 height (1122.5px at 96 DPI)
    # Target printable height is ~1045px
    assert metrics["scrollHeight"] <= 1045, (
        f"Rendered scrollHeight {metrics['scrollHeight']}px exceeds safe A4 printable height of 1045px!"
    )


def test_forensic_real_jobs_empirical_single_page(tmp_path, candidate_data, jobs_200_fixture):
    """Forensic Check 4: Test real candidate data against real-world jobs from 200-job dataset across multiple roles."""
    # Filter representative jobs across different roles
    selected_jobs = []
    seen_roles = set()
    for j_data in jobs_200_fixture:
        role = j_data.get("target_role")
        if role and role not in seen_roles:
            seen_roles.add(role)
            selected_jobs.append(j_data)
        if len(selected_jobs) >= 6:
            break

    assert len(selected_jobs) >= 4, f"Need at least 4 distinct roles, found {len(selected_jobs)}"

    for job_dict in selected_jobs:
        job = Job(
            title=job_dict["title"],
            company=job_dict["company"],
            location=job_dict.get("location", "Pune"),
            description=job_dict.get("description", ""),
            url=job_dict.get("url", "https://example.com/job")
        )
        role_lens = detect_role_lens(job)
        job.is_testing_role = (role_lens == "qa")

        tailored = validate_and_sanitize_tailored(candidate_data, candidate_data, role_lens, job=job)
        pdf_path = tmp_path / f"resume_{job_dict['id']}.pdf"

        # Generate real PDF
        out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)
        assert Path(out_path).exists(), f"PDF for {job_dict['id']} was not created"

        # Verify page count with pypdf
        reader = pypdf.PdfReader(out_path)
        assert len(reader.pages) == 1, (
            f"Job '{job.title}' ({role_lens}) produced {len(reader.pages)} pages instead of strictly 1 page!"
        )

        # Verify page dimensions (standard A4: 595.276 x 841.89 points)
        page_box = reader.pages[0].mediabox
        width, height = float(page_box.width), float(page_box.height)
        assert abs(width - 595.28) < 1.0, f"Unexpected page width: {width}"
        assert abs(height - 841.89) < 1.0, f"Unexpected page height: {height}"


def test_forensic_ats_plain_text_content(tmp_path, candidate_data, jobs_200_fixture):
    """Forensic Check 5: Verify 100% extractable ATS plain-text integrity and section order."""
    qa_job_dict = next(j for j in jobs_200_fixture if j.get("target_role") == "qa")
    job = Job(
        title=qa_job_dict["title"],
        company=qa_job_dict["company"],
        location=qa_job_dict["location"],
        description=qa_job_dict["description"],
        url=qa_job_dict["url"]
    )
    job.is_testing_role = True

    tailored = validate_and_sanitize_tailored(candidate_data, candidate_data, "qa", job=job)
    pdf_path = tmp_path / "forensic_qa_resume.pdf"
    generate_resume_pdf(tailored, str(pdf_path), job=job)

    reader = pypdf.PdfReader(str(pdf_path))
    text = reader.pages[0].extract_text()

    # ATS Headings
    headings = ["PROFILE SUMMARY", "TECHNICAL SKILLS", "WORK EXPERIENCE", "TECHNICAL PROJECTS", "EDUCATION", "CERTIFICATIONS"]
    for h in headings:
        assert h in text, f"Missing heading: {h}"

    # Personal Information
    assert "Kaustubh" in text
    assert "Kale" in text
    assert "kaustubh.kale.work@gmail.com" in text
    assert "9975526627" in text

    # Experience, Projects, Education, Certifications
    assert "CWIPedia Technologies" in text
    assert "SKNSITS" in text
    assert "SmartApply" in text
    assert "CampFlow" in text
    assert "Neon-Pulse" in text
    assert "Microsoft Azure Fundamentals" in text

    # Role order: for QA, WORK EXPERIENCE comes before TECHNICAL PROJECTS
    idx_exp = text.find("WORK EXPERIENCE")
    idx_proj = text.find("TECHNICAL PROJECTS")
    assert idx_exp < idx_proj, "For QA role, WORK EXPERIENCE must appear before TECHNICAL PROJECTS"


def test_forensic_adversarial_stress_layout_and_sanitization(tmp_path, candidate_data):
    """Adversarial stress test: Long strings, special characters, and boundary conditions."""
    import copy
    ad_data = copy.deepcopy(candidate_data)

    # 1. Stress: Max candidate skills (14 skills)
    ad_data["skills"] = [
        "Python", "Java", "C#", "SQL", "Selenium WebDriver", "Postman",
        "Jira", "Git", "GitHub Actions", "Docker", "Linux", "REST APIs", "Agile/Scrum", "DSA"
    ]

    # 2. Stress: Adversarial special characters in job title and company
    job = Job(
        title='Sr. QA / "Lead" <Automation> & SDET Tester (Pune/Remote) #101 *NEW*',
        company='Persistent Systems & Co. / "Solutions" <Ltd>',
        location='Pune / Mumbai / Bengaluru, Maharashtra, India',
        description='Adversarial JD with long strings & <tags> & "quotes"',
        url='https://example.com/job/101?query=test&param="val"'
    )
    job.is_testing_role = True

    tailored = validate_and_sanitize_tailored(ad_data, ad_data, "qa", job=job)
    pdf_path = tmp_path / "adversarial_stress.pdf"

    # Must generate successfully without throwing exception
    out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)
    assert Path(out_path).exists(), "Adversarial PDF generation failed to produce file"

    reader = pypdf.PdfReader(out_path)
    # Check single-page budgeting under full 14-skill load
    assert len(reader.pages) == 1, f"Adversarial layout overflowed to {len(reader.pages)} pages"

    text = reader.pages[0].extract_text()
    assert "Selenium WebDriver" in text
    # Milestone 4 & 5 content budgeting caps skills at 12 to guarantee 1 page
    assert "REST APIs" in text
    assert len(reader.pages) == 1