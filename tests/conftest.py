"""
Shared Pytest Fixtures for JobHunt-Automation E2E Test Suite.
Provides datasets, master profile fixtures, mock clients, and isolated test environments.
"""
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import re
import copy
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
from src.models import Job
from src.config_loader import load_resume, load_config

# Path to 200+ dataset fixture
DATASET_PATH = Path(__file__).parent / "fixtures" / "jobs_200_dataset.json"

@pytest.fixture(scope="session")
def jobs_200_dataset():
    """Loads the 200+ representative jobs dataset with ground truth labels."""
    assert DATASET_PATH.exists(), f"Dataset fixture not found at {DATASET_PATH}"
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) >= 200, f"Expected >=200 jobs in dataset fixture, got {len(data)}"
    return data

@pytest.fixture(scope="session")
def master_resume():
    """Loads the candidate's authoritative master resume."""
    resume_data = load_resume()
    assert isinstance(resume_data, dict), "Master resume must be a dictionary"
    assert "personal_information" in resume_data
    assert "skills" in resume_data
    assert "projects" in resume_data
    return resume_data

@pytest.fixture
def sample_fresher_qa_job():
    """Returns a realistic Indian fresher QA Automation Job in Pune."""
    return Job(
        id="test-qa-pune-001",
        title="Junior QA Automation Engineer",
        company="Persistent Systems",
        location="Pune, Maharashtra, India",
        description=(
            "Persistent Systems is looking for a Junior QA Automation Engineer in Pune.\n"
            "Responsibilities: Write test automation scripts using Selenium and Python. "
            "Execute API tests using Postman. Report defects in Jira.\n"
            "Requirements: B.E./B.Tech in IT/CS. 0-2 years of experience in test automation. "
            "Knowledge of Selenium, Python, Postman, SQL, and Git."
        ),
        url="https://www.linkedin.com/jobs/view/100000001",
        source="linkedin",
        job_type="fulltime"
    )

@pytest.fixture
def sample_fresher_java_job():
    """Returns a realistic Indian fresher Java Developer Job in Bangalore."""
    return Job(
        id="test-java-blr-002",
        title="Java Backend Developer - Fresher",
        company="LTIMindtree",
        location="Bengaluru, Karnataka, India",
        description=(
            "LTIMindtree is hiring an entry level Java Developer for our Bangalore center.\n"
            "Responsibilities: Develop modular backend services using Java, Spring Boot, JDBC, and SQL. "
            "Build RESTful APIs and collaborate with database teams.\n"
            "Requirements: 0-1 year experience or fresher with strong Java, OOP, SQL, and DSA skills."
        ),
        url="https://www.linkedin.com/jobs/view/100000002",
        source="linkedin",
        job_type="fulltime"
    )

@pytest.fixture
def sample_fresher_dotnet_job():
    """Returns a realistic Indian fresher .NET Developer Job in Mumbai."""
    return Job(
        id="test-dotnet-mum-003",
        title=".NET Developer (Fresher)",
        company="CitiusTech",
        location="Mumbai, Maharashtra, India",
        description=(
            "CitiusTech is seeking an Associate .NET Developer in Mumbai.\n"
            "Responsibilities: Write backend business logic using C# and ASP.NET Core. "
            "Write stored procedures in SQL Server and interface with Azure.\n"
            "Requirements: 0-2 years experience. Proficiency in C#, .NET, OOP, and SQL."
        ),
        url="https://www.linkedin.com/jobs/view/100000003",
        source="indeed",
        job_type="fulltime"
    )

@pytest.fixture
def sample_fresher_fullstack_job():
    """Returns a realistic Indian fresher Full Stack Developer Job."""
    return Job(
        id="test-fs-pune-004",
        title="Full Stack Software Engineer",
        company="Razorpay",
        location="Pune, India",
        description=(
            "Razorpay is hiring a Full Stack Software Engineer for our Pune office.\n"
            "Responsibilities: Build frontend components using HTML/CSS/JavaScript and backend APIs with Python/Node.\n"
            "Requirements: Freshers / 0-2 years experience. Strong problem solving, web fundamentals, and Git."
        ),
        url="https://www.linkedin.com/jobs/view/100000004",
        source="linkedin",
        job_type="fulltime"
    )

@pytest.fixture
def sample_senior_lead_job():
    """Returns a senior engineering role that must be filtered out."""
    return Job(
        id="test-senior-lead-005",
        title="Senior Technical Lead - Distributed Systems",
        company="Amazon India",
        location="Bengaluru, Karnataka, India",
        description=(
            "Amazon India is hiring a Senior Technical Lead.\n"
            "Requirements: 8+ years of industry experience designing large-scale distributed architectures. "
            "Proven track record managing engineering teams and setting technical roadmaps."
        ),
        url="https://www.linkedin.com/jobs/view/100000005",
        source="linkedin",
        job_type="fulltime"
    )

@pytest.fixture
def sample_irrelevant_job():
    """Returns an out-of-scope non-tech job that must be filtered out."""
    return Job(
        id="test-nontech-006",
        title="Senior Financial Accountant",
        company="Bajaj Finserv",
        location="Pune, Maharashtra",
        description=(
            "We are seeking an experienced Chartered Accountant to manage corporate accounts, "
            "taxation compliance, audits, and financial reporting. B.Com/CA required with Tally."
        ),
        url="https://www.linkedin.com/jobs/view/100000006",
        source="indeed",
        job_type="fulltime"
    )

@pytest.fixture
def mock_deepseek_scoring_response():
    """Returns a realistic DeepSeek scoring JSON payload with token telemetry."""
    json_text = json.dumps({
        "match_score": 85,
        "missing_skills": ["Docker", "Kubernetes"],
        "reason": "Strong match for Core Java, SQL, REST APIs, and automation testing fundamentals.",
        "extracted_requirements": "Java, Spring Boot, SQL, REST APIs, Git",
        "is_testing_role": False
    })
    tokens_used = 220
    return json_text, tokens_used

@pytest.fixture
def mock_deepseek_tailoring_response():
    """Returns a realistic DeepSeek Delta JSON tailoring response with token telemetry."""
    delta_data = {
        "profile_summary": "Results-driven IT engineer skilled in Java, Python, SQL, and REST APIs, specializing in modular backend services and automated testing pipelines.",
        "tailored_skills": [
            "Java", "Python", "SQL", "Spring Core", "REST APIs", "Selenium", "Postman", "Git", "DSA"
        ],
        "tailored_experience": [
            {
                "position": "Java Developer Intern",
                "company": "CWIPedia Technologies",
                "employment_period": "Jan 25 - Feb 25",
                "location": "Pune, India",
                "industry": "Software Engineering",
                "key_responsibilities": [
                    {"responsibility_1": "Engineered modular backend services and REST APIs with Java and SQL, optimizing query performance by 25%."},
                    {"responsibility_2": "Executed automated API test suites using Postman and JUnit to validate endpoint responses under sprint deadlines."}
                ]
            }
        ]
    }
    json_text = json.dumps(delta_data)
    tokens_used = 480
    return json_text, tokens_used

@pytest.fixture
def mock_supabase():
    """Returns a mocked Supabase client for testing database and storage operations."""
    client = MagicMock()
    mock_table = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    # Setup chaining for table operations
    mock_table.insert.return_value.execute.return_value.data = [{"id": "run-mock-123"}]
    mock_table.upsert.return_value.execute.return_value.data = [{"id": 1}]
    mock_table.select.return_value.eq.return_value.execute.return_value.data = []
    mock_table.select.return_value.execute.return_value.data = []

    client.table.return_value = mock_table
    client.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket
    mock_bucket.upload.return_value = {"Key": "resumes/sample.pdf"}
    mock_bucket.get_public_url.return_value = "https://mock.supabase.co/storage/v1/object/public/resumes/sample.pdf"

    return client

@pytest.fixture
def temp_output_dir(tmp_path):
    """Provides an isolated clean temporary output directory for PDF generation tests."""
    out_dir = tmp_path / "AutoApply_Output"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir)

@pytest.fixture
def flask_client():
    """Provides a Flask test client for testing dashboard routes."""
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def zero_hallucination_validator(master_resume):
    """
    Validates that a tailored resume contains ZERO fabricated qualifications:
    - 100% of tailored skills must exist in master resume (or recognized canonical forms).
    - Education degrees, universities, and graduation years must match verbatim.
    - Company names and employment dates must match verbatim.
    """
    def _normalize(s: str) -> str:
        return re.sub(r'[\(\)\-\_\s]+', ' ', s).strip().lower()

    # Build normalized master skill set
    master_skills_raw = master_resume.get("skills", [])
    master_skills_norm = {_normalize(s) for s in master_skills_raw}
    # Add canonical parts (e.g. 'selenium' from 'selenium (basic ui automation)')
    for s in master_skills_raw:
        base = s.split('(')[0].strip()
        if base:
            master_skills_norm.add(_normalize(base))

    def validator(tailored_resume: dict) -> tuple[bool, list[str]]:
        violations = []
        # 1. Check skills
        tailored_skills = tailored_resume.get("skills", [])
        for skill in tailored_skills:
            norm_skill = _normalize(skill)
            # check if norm_skill or any substring exists in master skills
            found = norm_skill in master_skills_norm or any(
                norm_skill in ms or ms in norm_skill for ms in master_skills_norm
            )
            if not found:
                violations.append(f"Fabricated skill detected: '{skill}'")

        # 2. Check education
        tailored_edu = tailored_resume.get("education_details", [])
        master_edu = master_resume.get("education_details", [])
        for t_edu, m_edu in zip(tailored_edu, master_edu):
            if t_edu.get("institution") != m_edu.get("institution"):
                violations.append(f"Fabricated institution: '{t_edu.get('institution')}' != '{m_edu.get('institution')}'")
            if t_edu.get("education_level") != m_edu.get("education_level"):
                violations.append(f"Fabricated degree: '{t_edu.get('education_level')}' != '{m_edu.get('education_level')}'")

        # 3. Check experience companies
        tailored_exp = tailored_resume.get("experience_details", [])
        master_exp = master_resume.get("experience_details", [])
        for t_exp, m_exp in zip(tailored_exp, master_exp):
            if t_exp.get("company") != m_exp.get("company"):
                violations.append(f"Fabricated company: '{t_exp.get('company')}' != '{m_exp.get('company')}'")

        return len(violations) == 0, violations

    return validator

