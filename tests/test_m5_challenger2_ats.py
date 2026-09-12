"""
Milestone 5 Challenger 2 Adversarial Test Suite:
ATS Machine Readability & PDF Plain-Text Extraction Verification.

Author: Challenger 2 (critic, specialist)
Verification Goals:
1. Dual-Engine Extraction Fidelity:
   Both `pypdf` and `pdfplumber` extract 100% parseable, structured text.
2. Standalone ATS Headings:
   All 6 standard uppercase headings (PROFILE SUMMARY, TECHNICAL SKILLS,
   WORK EXPERIENCE, TECHNICAL PROJECTS, EDUCATION, CERTIFICATIONS) appear
   as clean, isolated lines without text interleaving or concatenation.
3. Top-to-Bottom Sequential Layout Order:
   Monotonically descending vertical coordinates (y-order) for headers and sections.
   Flexbox right-aligned items (dates, CGPA) stay aligned with left titles without drifting.
4. Candidate Credential Extraction:
   Verifies Name, Email, Phone, LinkedIn, Location, CWIPedia Technologies,
   SKNSITS, 7.70 CGPA, SmartApply, CampFlow, Neon-Pulse, Azure, and Google certs.
   Tests optional GitHub link inclusion in header.
5. Ligature & Encoding Purity:
   Confirms zero Unicode ligatures (\ufb00-\ufb06), zero null bytes (\x00),
   zero replacement characters (\ufffd), and clean whitespace tokenization.
6. Real-World Job Fixtures Batch:
   Batch verification across 10 diverse real-world jobs from `tests/fixtures/jobs_200_dataset.json`
   spanning QA, Java, .NET, and Fullstack.
"""
import copy
import json
import re
from pathlib import Path
import pytest
import pypdf
import pdfplumber

from src.models import Job
from src.config_loader import load_resume
from src.resume_tailor import validate_and_sanitize_tailored
from src.pdf_generator import generate_resume_pdf

STANDARD_ATS_HEADINGS = [
    "PROFILE SUMMARY",
    "TECHNICAL SKILLS",
    "WORK EXPERIENCE",
    "TECHNICAL PROJECTS",
    "EDUCATION",
    "CERTIFICATIONS",
]


@pytest.fixture(scope="module")
def master_resume():
    return load_resume()


@pytest.fixture(scope="module")
def real_jobs_dataset():
    fixtures_path = Path(__file__).parent / "fixtures" / "jobs_200_dataset.json"
    assert fixtures_path.exists(), f"Fixtures file not found: {fixtures_path}"
    with open(fixtures_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_dual_engine_ats_heading_isolation(tmp_path, master_resume):
    """
    Challenge 1: Verify all 6 ATS headings are extracted as clean, standalone lines
    by both pypdf and pdfplumber, preventing heading/content concatenation.
    """
    job = Job(
        title="QA Automation Engineer",
        company="Infosys",
        location="Pune, India",
        description="Selenium, Python, JUnit, Postman automation.",
        url="https://example.com/qa1"
    )
    job.is_testing_role = True

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "qa", job=job)
    pdf_path = tmp_path / "test_heading_isolation.pdf"
    generate_resume_pdf(tailored, str(pdf_path), job=job)

    # 1. pypdf verification
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 1, "PDF must be strictly 1 page"
    pypdf_lines = [line.strip() for line in reader.pages[0].extract_text().splitlines() if line.strip()]

    for heading in STANDARD_ATS_HEADINGS:
        assert heading in pypdf_lines, (
            f"Heading '{heading}' is not a standalone line in pypdf extraction. "
            f"Found lines containing heading: {[l for l in pypdf_lines if heading in l]}"
        )

    # 2. pdfplumber verification
    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) == 1, "PDF must be strictly 1 page"
        plumber_lines = [line.strip() for line in pdf.pages[0].extract_text().splitlines() if line.strip()]

        for heading in STANDARD_ATS_HEADINGS:
            assert heading in plumber_lines, (
                f"Heading '{heading}' is not a standalone line in pdfplumber extraction. "
                f"Found lines containing heading: {[l for l in plumber_lines if heading in l]}"
            )


def test_top_to_bottom_vertical_flow_and_no_column_scrambling(tmp_path, master_resume):
    """
    Challenge 2: Verify strict monotonic top-to-bottom reading order.
    Ensures flexbox headers (position vs date, project vs tech stack) do not scramble
    or interleave with subsequent bullet points.
    """
    job = Job(
        title="Java Backend Engineer",
        company="Persistent Systems",
        location="Pune, India",
        description="Core Java, Spring Boot, JDBC, SQL microservices.",
        url="https://example.com/java1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "java", job=job)
    pdf_path = tmp_path / "test_reading_order.pdf"
    generate_resume_pdf(tailored, str(pdf_path), job=job)

    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        assert len(words) >= 200, f"Expected at least 200 words, got {len(words)}"

        # Verify page dimensions correspond to standard A4 (approx 595 x 842 pt)
        assert 590 <= page.width <= 600, f"Unexpected page width: {page.width}"
        assert 835 <= page.height <= 850, f"Unexpected page height: {page.height}"

        # Track the top y-coordinate of each heading
        heading_y_coords = {}
        for heading in STANDARD_ATS_HEADINGS:
            # Match heading words in order
            h_words = heading.split()
            for i in range(len(words) - len(h_words) + 1):
                window = [w['text'].upper() for w in words[i:i + len(h_words)]]
                if window == h_words:
                    heading_y_coords[heading] = words[i]['top']
                    break

        assert len(heading_y_coords) == 6, (
            f"Not all headings found in pdfplumber word list. Found: {list(heading_y_coords.keys())}"
        )

        # In non-testing role (Java), order should be:
        # PROFILE SUMMARY -> TECHNICAL SKILLS -> TECHNICAL PROJECTS -> WORK EXPERIENCE -> EDUCATION -> CERTIFICATIONS
        expected_seq = [
            "PROFILE SUMMARY",
            "TECHNICAL SKILLS",
            "TECHNICAL PROJECTS",
            "WORK EXPERIENCE",
            "EDUCATION",
            "CERTIFICATIONS",
        ]
        y_values = [heading_y_coords[h] for h in expected_seq]
        for idx in range(len(y_values) - 1):
            assert y_values[idx] < y_values[idx + 1], (
                f"Heading ordering violated: {expected_seq[idx]} (y={y_values[idx]}) "
                f"is not above {expected_seq[idx+1]} (y={y_values[idx+1]})"
            )

        # Inspect date / right-aligned items
        # "Jan 25 - Feb 25" should have approximately same vertical top as "Java Developer Intern"
        intern_word = next((w for w in words if w['text'] == "Intern"), None)
        date_word = next((w for w in words if w['text'] == "Jan"), None)
        assert intern_word is not None, "'Intern' word not found"
        assert date_word is not None, "'Jan' word not found"
        assert abs(intern_word['top'] - date_word['top']) < 8.0, (
            f"Date 'Jan' (top={date_word['top']}) drifted vertically from job title 'Intern' (top={intern_word['top']})"
        )


def test_candidate_credentials_extraction_fidelity(tmp_path, master_resume):
    """
    Challenge 3: Adversarially check all core candidate credentials in extracted text:
    Name, Email, Phone, LinkedIn, Location, CWIPedia, SKNSITS, 7.70 CGPA,
    SmartApply, CampFlow, Neon-Pulse, and test optional GitHub inclusion.
    """
    master_with_gh = copy.deepcopy(master_resume)
    master_with_gh["personal_information"]["github"] = "https://github.com/kaustubhkale12"

    job = Job(
        title="Full Stack Developer",
        company="Tech Mahindra",
        location="Pune, India",
        description="Full stack developer with Python, JavaScript, and SQL.",
        url="https://example.com/fs1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(master_with_gh, master_with_gh, "fullstack", job=job)
    pdf_path = tmp_path / "test_credentials.pdf"
    generate_resume_pdf(tailored, str(pdf_path), job=job)

    reader = pypdf.PdfReader(str(pdf_path))
    extracted = reader.pages[0].extract_text()

    required_credentials = [
        ("Candidate Name", "Kaustubh Kale"),
        ("Phone Number", "9975526627"),
        ("Email Address", "kaustubh.kale.work@gmail.com"),
        ("LinkedIn URL", "linkedin.com/in/kaustubhkale12"),
        ("GitHub Link", "GitHub"),
        ("Candidate Location", "Pune, India"),
        ("Experience Employer", "CWIPedia Technologies"),
        ("Experience Position", "Java Developer Intern"),
        ("Experience Dates", "Jan 25 - Feb 25"),
        ("Education Institution", "SKNSITS, Lonavala"),
        ("Degree Level", "Bachelors of Engineering in Information Technology"),
        ("Graduation Year", "2026"),
        ("Evaluation Grade", "7.70 CGPA"),
        ("Project 1", "SmartApply: AI-Driven Job Automation Pipeline"),
        ("Project 2", "CampFlow: Hospitality Automation & Booking Suite"),
        ("Project 3", "Neon-Pulse – Pattern Recognition & Logic Engine"),
        ("Certification 1", "Microsoft Azure Fundamentals"),
        ("Certification 2", "Cybersecurity - Google (Coursera)"),
    ]

    for label, cred in required_credentials:
        assert cred in extracted, f"Required credential '{label}' ('{cred}') missing from extracted PDF text!"


def test_ligature_encoding_and_tokenization_integrity(tmp_path, master_resume):
    """
    Challenge 4: Check for corrupted ligatures (fi, fl, ff), control characters,
    null bytes, and verify clean word tokenization.
    """
    job = Job(
        title=".NET C# Developer",
        company="Capgemini",
        location="Pune, India",
        description="C#, .NET Core, SQL Server, Azure.",
        url="https://example.com/dotnet1"
    )
    job.is_testing_role = False

    tailored = validate_and_sanitize_tailored(master_resume, master_resume, "dotnet", job=job)
    pdf_path = tmp_path / "test_ligatures.pdf"
    generate_resume_pdf(tailored, str(pdf_path), job=job)

    reader = pypdf.PdfReader(str(pdf_path))
    text = reader.pages[0].extract_text()

    # 1. Unicode Ligature check (U+FB00 to U+FB06)
    # If ligatures like 'fi' or 'fl' are rendered as single private/presentation glyphs,
    # ATS regex search for words like 'Final', 'CampFlow', 'filtering' will fail.
    unicode_ligatures = [
        ('\ufb00', 'ff'),
        ('\ufb01', 'fi'),
        ('\ufb02', 'fl'),
        ('\ufb03', 'ffi'),
        ('\ufb04', 'ffl'),
        ('\ufb05', 'ft'),
        ('\ufb06', 'st'),
    ]
    for char, name in unicode_ligatures:
        assert char not in text, f"Corrupted Unicode ligature '{name}' (\\u{ord(char):04x}) detected in PDF text!"

    # 2. Critical keywords containing ligature candidates (fi, fl, ff) must be present as pure ASCII
    for word in ["Graduate", "CampFlow", "filtering"]:
        assert word in text, f"Keyword '{word}' was not found as clean text, possibly damaged by font ligature!"
    assert re.search(r'\bPROFILE\b', text), "Section heading 'PROFILE' was not found cleanly!"

    # 3. Control chars and null bytes
    assert "\x00" not in text, "Null byte found in PDF text layer"
    assert "\ufffd" not in text, "Unicode replacement character (mojibake) found in PDF text layer"
    assert "â€" not in text, "UTF-8 mojibake sequence found in PDF text layer"

    # 4. Tokenization integrity (words are properly space-separated)
    assert not re.search(r'JavaDeveloperIntern', text), "Missing space between words in job title"
    assert not re.search(r'CWIPediaTechnologies', text), "Missing space in employer name"
    assert not re.search(r'7\.70CGPA', text), "Missing space between grade and CGPA unit"
    assert re.search(r'7\.70\s+CGPA', text), "Grade '7.70 CGPA' must have proper whitespace separation"


def test_batch_real_world_fixtures_200_dataset(tmp_path, master_resume, real_jobs_dataset):
    """
    Challenge 5: Batch test across 10 diverse real-world jobs from tests/fixtures/jobs_200_dataset.json.
    Covers QA, Java, .NET, and Fullstack.
    Verifies for each:
    - len(pages) == 1 strictly
    - All 6 ATS headings are extracted cleanly
    - Candidate name, employer CWIPedia, SKNSITS are present
    """
    target_role_samples = {
        "qa": 3,
        "java": 3,
        "dotnet": 2,
        "fullstack": 2,
    }

    tested_count = 0
    for role, count in target_role_samples.items():
        matching = [
            j for j in real_jobs_dataset
            if j.get("target_role") == role and j.get("is_relevant")
        ][:count]
        assert len(matching) == count, f"Could not find {count} jobs for role '{role}' in dataset"

        for raw_job in matching:
            job = Job(
                title=raw_job["title"],
                company=raw_job["company"],
                location=raw_job["location"],
                description=raw_job["description"],
                url=raw_job["url"]
            )
            job.is_testing_role = (role == "qa")

            tailored = validate_and_sanitize_tailored(master_resume, master_resume, role, job=job)
            pdf_path = tmp_path / f"batch_{raw_job['id']}.pdf"

            out = generate_resume_pdf(tailored, str(pdf_path), job=job)
            assert Path(out).exists(), f"Failed to generate PDF for job {raw_job['id']}"

            # Verify with pypdf
            reader = pypdf.PdfReader(out)
            assert len(reader.pages) == 1, (
                f"Batch job {raw_job['id']} ({role}) rendered {len(reader.pages)} pages instead of 1 page!"
            )

            text = reader.pages[0].extract_text()

            # Verify headings
            for h in STANDARD_ATS_HEADINGS:
                assert h in text, f"Heading '{h}' missing in batch job {raw_job['id']}"

            # Verify credentials
            assert "Kaustubh" in text
            assert "CWIPedia" in text
            assert "SKNSITS" in text
            assert "7.70 CGPA" in text

            # Dynamic reordering check
            pos_exp = text.find("WORK EXPERIENCE")
            pos_proj = text.find("TECHNICAL PROJECTS")
            if role == "qa":
                assert pos_exp < pos_proj, f"QA job {raw_job['id']} failed section reordering (exp before proj)"
            else:
                assert pos_proj < pos_exp, f"Non-QA job {raw_job['id']} failed section reordering (proj before exp)"

            tested_count += 1

    assert tested_count == 10, f"Expected to test 10 batch jobs, tested {tested_count}"
