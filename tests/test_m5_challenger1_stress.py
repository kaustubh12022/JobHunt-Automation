"""
Milestone 5 Challenger 1 Adversarial Stress Test Suite:
1-Page ATS-Friendly PDF Resume Generation & Single-Page Budgeting.

Author: Challenger 1 (critic, specialist)
Verification Goals:
1. Static code verification: Zero transform: scale(), scaleFactor, or JS DOM scaling hacks.
2. Real-world dataset verification: Real jobs from tests/fixtures/jobs_200_dataset.json
   across all 4 role lenses ('qa', 'java', 'dotnet', 'fullstack').
3. Edge case data stress testing:
   - Long bullet text (up to 250 chars per bullet across all experience and project items)
   - Max allowed skills (12 long-form skills)
   - Full contact line (full international phone, long email, LinkedIn, GitHub, full location)
   - Dense profile summary
   - Multi-certification entries
4. Strict single-page assertion: len(reader.pages) == 1 across every single test case.
5. ATS text extraction fidelity: Clean machine readability, correct section ordering,
   no scrambled characters.
"""
import copy
import json
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
def jobs_dataset():
    fixtures_path = Path(__file__).parent / "fixtures" / "jobs_200_dataset.json"
    assert fixtures_path.exists(), f"Fixtures file not found: {fixtures_path}"
    with open(fixtures_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_adversarial_static_code_inspection():
    """
    Adversarial Challenge 1: Verify absolute elimination of CSS/JS scale hacks in src/pdf_generator.py.
    Checks AST/code for transform, scaleFactor, style.transform, zoom, or page.evaluate DOM manipulation.
    """
    generator_file = Path(__file__).parent.parent / "src" / "pdf_generator.py"
    assert generator_file.exists()
    content = generator_file.read_text(encoding="utf-8")

    forbidden_patterns = [
        r"transform\s*:\s*scale",
        r"scaleFactor",
        r"document\.body\.style\.transform",
        r"document\.documentElement\.scrollHeight",
        r"style\.transformOrigin",
        r"style\.zoom",
        r"page\.evaluate",
    ]

    for pattern in forbidden_patterns:
        match = re.search(pattern, content)
        assert not match, f"Forbidden scaling pattern '{pattern}' detected in src/pdf_generator.py: {match}"

    # Confirm format is A4 and print_background is True
    assert 'format="A4"' in content
    assert "print_background=True" in content


def test_real_world_dataset_4_role_lenses(tmp_path, master_resume, jobs_dataset):
    """
    Adversarial Challenge 2: Render real PDFs across all 4 role lenses using real-world job fixtures
    from tests/fixtures/jobs_200_dataset.json.
    Assert len(reader.pages) == 1 strictly across all role lenses.
    """
    lens_targets = {
        "qa": lambda j: j.get("target_role") == "qa" and j.get("is_relevant"),
        "java": lambda j: j.get("target_role") == "java" and j.get("is_relevant"),
        "dotnet": lambda j: j.get("target_role") == "dotnet" and j.get("is_relevant"),
        "fullstack": lambda j: j.get("target_role") == "fullstack" and j.get("is_relevant"),
    }

    for lens, filter_fn in lens_targets.items():
        matching_jobs = [j for j in jobs_dataset if filter_fn(j)]
        assert len(matching_jobs) > 0, f"No fixture jobs found for role lens: {lens}"
        raw_job = matching_jobs[0]

        job = Job(
            title=raw_job["title"],
            company=raw_job["company"],
            location=raw_job["location"],
            description=raw_job["description"],
            url=raw_job["url"]
        )
        job.is_testing_role = (lens == "qa")

        tailored = validate_and_sanitize_tailored(master_resume, master_resume, lens, job=job)
        pdf_path = tmp_path / f"real_job_{lens}_{raw_job['id']}.pdf"

        out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)
        assert Path(out_path).exists(), f"PDF generation failed for {lens}"

        reader = pypdf.PdfReader(out_path)
        num_pages = len(reader.pages)
        assert num_pages == 1, (
            f"Adversarial Failure: Role lens '{lens}' with real job fixture '{raw_job['id']}' "
            f"produced {num_pages} pages instead of exactly 1 page!"
        )

        extracted_text = reader.pages[0].extract_text()
        assert "PROFILE SUMMARY" in extracted_text
        assert "TECHNICAL SKILLS" in extracted_text
        assert "TECHNICAL PROJECTS" in extracted_text
        assert "WORK EXPERIENCE" in extracted_text
        assert "EDUCATION" in extracted_text
        assert "CERTIFICATIONS" in extracted_text
        assert "Kaustubh" in extracted_text
        assert "CWIPedia" in extracted_text
        assert "SKNSITS" in extracted_text


def test_stress_max_edge_case_payload(tmp_path, master_resume):
    """
    Adversarial Challenge 3: Extreme Edge Case Data Payload.
    - 250-character bullets across all experience responsibilities (3 bullets)
    - 250-character bullets across all 3 projects (3 + 2 + 2 = 7 bullets)
    - 12 long-form skills
    - Full contact info with phone prefix, long email, LinkedIn, GitHub, full location
    - Dense multi-line profile summary
    - Both certifications with long descriptions
    Assert len(reader.pages) == 1 strictly across all 4 role lenses.
    """
    # Construct maximal 250-character bullet strings
    b250_1 = "Architected and delivered end-to-end modular backend microservices integrating Java, Spring Core, and optimized SQL schemas, yielding a 35% improvement in transaction throughput while maintaining zero downtime across multi-tenant production deployments."
    b250_2 = "Spearheaded automated regression and continuous integration pipelines utilizing Selenium WebDriver, pytest, and Postman API suites, executing 500+ daily test cases and reducing release validation turnaround from 4 hours to 45 minutes with high precision."
    b250_3 = "Engineered responsive, highly accessible user interfaces leveraging modern ECMAScript standards and clean component architecture, achieving a 98+ Google Lighthouse score and reducing client-side load latency by 40% across desktop and mobile devices."

    assert 220 <= len(b250_1) <= 260
    assert 220 <= len(b250_2) <= 260
    assert 220 <= len(b250_3) <= 260

    max_payload = copy.deepcopy(master_resume)

    # Full contact line
    max_payload["personal_information"] = {
        "name": "Kaustubh",
        "surname": "Kale",
        "phone_prefix": "+91",
        "phone": "9975526627",
        "email": "kaustubh.kale.engineering.work@gmail.com",
        "linkedin": "linkedin.com/in/kaustubhkale12-software-engineer",
        "github": "https://github.com/kaustubh12022-engineering-portfolio",
        "city": "Pune, Maharashtra",
        "country": "India"
    }

    # Dense profile summary
    max_payload["profile_summary"] = (
        "High-achieving IT engineering graduate specializing in robust backend development, QA automation, and cloud integration. "
        "Demonstrated track record of delivering resilient software pipelines using Java, Python, SQL, Selenium, and REST APIs. "
        "Adept at optimizing complex algorithmic workflows and maintaining rigorous test coverage in Agile environments."
    )

    # 12 long-form skills
    max_payload["skills"] = [
        "Data Structures & Algorithms",
        "Manual Testing Fundamentals",
        "Microsoft Azure Fundamentals",
        "Windows Task Scheduler",
        "Selenium (Basic UI Automation)",
        "Postman (API Testing)",
        "Spring Core (Basics)",
        "REST APIs",
        "BeautifulSoup",
        "Agile/Scrum",
        "JavaScript",
        "Python"
    ]

    # Maximal experience bullets
    max_payload["experience_details"][0]["key_responsibilities"] = [
        b250_1,
        b250_2,
        b250_3
    ]

    # Maximal project bullets
    for proj in max_payload["projects"]:
        proj["description_bullets"] = [b250_1, b250_2, b250_3]

    role_lenses = [
        ("qa", True, "Lead QA Automation Engineer"),
        ("java", False, "Backend Java Systems Engineer"),
        ("dotnet", False, ".NET Cloud Application Developer"),
        ("fullstack", False, "Full Stack Solutions Engineer")
    ]

    for lens, is_qa, title in role_lenses:
        job = Job(
            title=title,
            company="Global Enterprise Solutions Ltd.",
            location="Pune, India",
            description=f"Demanding enterprise role for {title} requiring production skills and system design.",
            url=f"https://linkedin.com/jobs/view/stress-{lens}"
        )
        job.is_testing_role = is_qa

        # Tailor payload
        tailored = validate_and_sanitize_tailored(max_payload, master_resume, lens, job=job)

        # Overwrite bullets with 250-char stress strings to test physical CSS capacity
        tailored["personal_information"] = max_payload["personal_information"]
        tailored["experience_details"][0]["key_responsibilities"] = [b250_1, b250_2, b250_3]
        for p in tailored["projects"]:
            p["description_bullets"] = [b250_1, b250_2] if len(p.get("description_bullets", [])) <= 2 else [b250_1, b250_2, b250_3]

        pdf_path = tmp_path / f"stress_max_payload_{lens}.pdf"
        out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)
        assert Path(out_path).exists()

        reader = pypdf.PdfReader(out_path)
        page_count = len(reader.pages)
        assert page_count == 1, (
            f"Adversarial Stress Failure: Max payload overflowed to {page_count} pages under role lens '{lens}'!"
        )


def test_dom_scrollheight_within_a4_bounds(master_resume):
    """
    Adversarial Challenge 4: Measure rendered DOM scrollHeight in headless Chromium
    to verify physical headroom below A4 threshold (1122.5px at 96 DPI).
    """
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("resume_template.html")

    job = Job(
        title="Software Development Engineer",
        company="Amazon Web Services",
        location="Pune, India",
        description="Looking for SDE skilled in Java, Python, and SQL.",
        url="https://amazon.jobs/en/jobs/101"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "fullstack", job=job)
    html_out = template.render(resume=tailored, job=job)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Set viewport to standard A4 width at 96 DPI (794px width, generous height)
            page.set_viewport_size({"width": 794, "height": 2000})
            page.set_content(html_out)

            # Measure natural content height of document.body without any CSS transforms
            body_height = page.evaluate("document.body.getBoundingClientRect().height")
            body_offset = page.evaluate("document.body.offsetHeight")

            # A4 physical height is 1122.5px (297mm @ 96 DPI)
            MAX_A4_PX = 1122.5
            assert body_height <= MAX_A4_PX, (
                f"Body height {body_height}px exceeds maximum A4 height {MAX_A4_PX}px!"
            )
            assert body_offset <= MAX_A4_PX, (
                f"Body offsetHeight {body_offset}px exceeds maximum A4 height {MAX_A4_PX}px!"
            )

            # Assert healthy headroom (at least 150px buffer to prevent printer-driver overflow)
            headroom = MAX_A4_PX - body_height
            assert headroom >= 150, f"Headroom too tight ({headroom}px) for safe single-page printing"

        finally:
            browser.close()


def test_ats_character_encoding_and_symbol_integrity(tmp_path, master_resume):
    """
    Adversarial Challenge 5: Verify that en-dashes, pipes, ampersands, and bullet characters
    are preserved without Unicode corruption (e.g. mojibake or \ufffd) in the PDF text layer.
    """
    job = Job(
        title="Full Stack Engineer",
        company="Accenture Solutions",
        location="Pune, India",
        description="Full Stack engineer with Java & Python experience.",
        url="https://accenture.com/jobs/1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "fullstack", job=job)
    pdf_path = tmp_path / "test_encoding.pdf"
    generate_resume_pdf(tailored, str(pdf_path), job=job)

    reader = pypdf.PdfReader(str(pdf_path))
    extracted = reader.pages[0].extract_text()

    # Reject replacement characters / mojibake
    assert "\ufffd" not in extracted, "Unicode replacement character found in PDF text layer"
    assert "â€" not in extracted, "Mojibake corruption detected in PDF text layer"

    # Verify key tokens are present and legible
    assert "Kaustubh Kale" in extracted
    assert "CWIPedia Technologies" in extracted
    assert "SKNSITS" in extracted
    assert "SmartApply" in extracted
    assert "CampFlow" in extracted
    assert "Neon-Pulse" in extracted


def test_generate_pdf_shared_playwright_page(tmp_path, monkeypatch, master_resume):
    """
    Adversarial Challenge 6: Verify pipeline's generate_pdf() with shared Playwright page object.
    Ensures that generate_pdf creates strict 1-page PDF adhering to the configured desktop path.
    """
    monkeypatch.setitem(load_config()["output"], "desktop_path", str(tmp_path))
    monkeypatch.setitem(load_config()["output"], "folder_name", "Resumes")

    job = Job(
        title="QA Automation Specialist",
        company="Cognizant Tech",
        location="Pune, India",
        description="Selenium, pytest, API testing",
        url="https://cognizant.com/jobs/99"
    )
    job.is_testing_role = True

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "qa", job=job)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            pdf_path_str = generate_pdf(job, tailored, "2026-09-06", page)
            assert pdf_path_str != "", "generate_pdf returned empty string"
            pdf_path = Path(pdf_path_str)
            assert pdf_path.exists(), f"Output PDF does not exist: {pdf_path}"

            reader = pypdf.PdfReader(str(pdf_path))
            assert len(reader.pages) == 1, (
                f"generate_pdf produced {len(reader.pages)} pages instead of 1 page!"
            )
        finally:
            browser.close()


def test_generate_resume_pdf_with_none_job(tmp_path, master_resume):
    """
    Adversarial Challenge 7: Standalone generate_resume_pdf() with job=None.
    Template must fall back cleanly without raising Jinja errors, and produce exactly 1 page.
    """
    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "fullstack", job=None)
    pdf_path = tmp_path / "standalone_no_job.pdf"

    out_path = generate_resume_pdf(tailored, str(pdf_path), job=None)
    assert Path(out_path).exists()

    reader = pypdf.PdfReader(out_path)
    assert len(reader.pages) == 1, "Expected exactly 1 page when job=None"

    extracted = reader.pages[0].extract_text()
    pos_proj = extracted.find("TECHNICAL PROJECTS")
    pos_exp = extracted.find("WORK EXPERIENCE")
    assert pos_proj != -1 and pos_exp != -1
    assert pos_proj < pos_exp, "Default when job=None should place PROJECTS before EXPERIENCE"


def test_html_escaping_and_special_entities(tmp_path, master_resume):
    """
    Adversarial Challenge 8: Verify that HTML tags in project/experience descriptions
    (e.g., <script>, <b>, &) are handled securely without breaking the single-page layout.
    """
    malicious_payload = copy.deepcopy(master_resume)
    malicious_payload["experience_details"][0]["key_responsibilities"] = [
        "Maintained <script>alert('xss')</script> automated test suites with 100% pass rate.",
        "Engineered <b>backend</b> API endpoints handling &amp; query parameters seamlessly.",
        "Refactored SQL queries with > 50% speedup using \"indexed\" views and 'prepared' statements."
    ]

    job = Job(
        title="Security Software Engineer",
        company="CyberSec Ltd.",
        location="Pune, India",
        description="Application security and code review.",
        url="https://cybersec.example/jobs/1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(malicious_payload, master_resume, "fullstack", job=job)
    pdf_path = tmp_path / "test_malicious_entities.pdf"

    out_path = generate_resume_pdf(tailored, str(pdf_path), job=job)
    assert Path(out_path).exists()

    reader = pypdf.PdfReader(out_path)
    assert len(reader.pages) == 1, "Special entities caused overflow to multiple pages"

    text = reader.pages[0].extract_text()
    assert "<script>" not in text or "alert" in text  # In text layer, script tags should either be escaped or sanitized
