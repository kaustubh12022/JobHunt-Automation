"""
Milestone 4: Role-Lens Tailoring, Zero-Hallucination Guardrails, and JD Requirement Coverage Test Suite.
Verifies:
1. Deterministic Role-Lens Detection ('qa', 'java', 'dotnet', 'fullstack')
2. JD Boilerplate Stripping & Token Reduction (~64%)
3. DeepSeek Reasoner Parameter Handling (no temperature/response_format) & Reasoning Tokens Telemetry
4. Python-level Zero-Hallucination Guardrail (Pruning Fabricated Skills, Locking Immutables)
5. Preservation of All 3 Verified Candidate Projects with Role-Weighted Reordering
6. Mathematical JD Requirement Coverage >= 95% of Applicable Candidate Skills (M ∩ J)
"""
import pytest
import asyncio
import copy
import re
from unittest.mock import patch, MagicMock, AsyncMock

from src.models import Job
from src.config_loader import load_resume
from src.scorer import strip_boilerplate
from src.resume_tailor import (
    detect_role_lens,
    validate_and_sanitize_tailored,
    get_applicable_candidate_skills,
    calculate_jd_requirement_coverage,
    tailor_resume_async,
    is_valid_candidate_skill,
    _normalize_skill
)
from src.ai_engine import call_ai_tailoring_async, TokenUsage, runtime_settings


# =====================================================================
# 1. Role-Lens Detection Tests
# =====================================================================

def test_m4_detect_role_lens_qa_by_title_and_flag():
    """QA lens detected via job title keywords and is_testing_role flag."""
    job1 = Job(title="QA Automation Engineer", company="TestCorp", location="Pune", description="Java testing", url="http://ex.com")
    assert detect_role_lens(job1) == "qa"

    job2 = Job(title="Software Test Engineer Trainee", company="QAInc", location="Mumbai", description="Testing apps", url="http://ex.com")
    assert detect_role_lens(job2) == "qa"

    job3 = Job(title="SDET Fresher", company="AutoQA", location="Bangalore", description="Write test cases", url="http://ex.com")
    assert detect_role_lens(job3) == "qa"

    job4 = Job(title="Quality Assurance Analyst", company="ITSol", location="Pune", description="Manual test", url="http://ex.com")
    assert detect_role_lens(job4) == "qa"

    job5 = Job(title="Graduate Trainee", company="TCS", location="Pune", description="Any work", url="http://ex.com")
    job5.is_testing_role = True
    assert detect_role_lens(job5) == "qa"


def test_m4_detect_role_lens_qa_by_description_content():
    """QA lens detected for generic title when JD strongly features testing keywords."""
    job = Job(
        title="Associate Software Engineer",
        company="Wipro",
        location="Pune",
        description="Responsible for test automation using Selenium and Postman. Write test cases, defect reporting, manual testing fundamentals, and pytest execution.",
        url="http://ex.com"
    )
    assert detect_role_lens(job) == "qa"


def test_m4_detect_role_lens_java_by_title():
    """Java lens detected via Java job title keywords."""
    job1 = Job(title="Java Developer", company="Tech Mahindra", location="Pune", description="Core Java, Spring Boot", url="http://ex.com")
    assert detect_role_lens(job1) == "java"

    job2 = Job(title="Junior Backend Java Engineer", company="FinTech", location="Mumbai", description="REST APIs, SQL", url="http://ex.com")
    assert detect_role_lens(job2) == "java"

    job3 = Job(title="Spring Boot Developer Trainee", company="CloudSys", location="Bangalore", description="Microservices, JDBC", url="http://ex.com")
    assert detect_role_lens(job3) == "java"


def test_m4_detect_role_lens_java_by_content():
    """Java lens detected for generic title when JD strongly features Java stack."""
    job = Job(
        title="Software Engineer Trainee",
        company="Infosys",
        location="Pune",
        description="Work on backend systems with Java, Spring Boot, JDBC, Hibernate, MySQL, Maven, and REST APIs.",
        url="http://ex.com"
    )
    assert detect_role_lens(job) == "java"


def test_m4_detect_role_lens_dotnet_by_title_and_content():
    """.NET lens detected via C# / .NET title or description."""
    job1 = Job(title=".NET Developer", company="Hexaware", location="Pune", description="C#, ASP.NET Core, SQL Server", url="http://ex.com")
    assert detect_role_lens(job1) == "dotnet"

    job2 = Job(title="C# Software Engineer", company="LTI", location="Mumbai", description="Azure, C#, Web APIs", url="http://ex.com")
    assert detect_role_lens(job2) == "dotnet"

    job3 = Job(
        title="Graduate Engineer Trainee",
        company="Mindtree",
        location="Bangalore",
        description="Develop applications using C#, .NET framework, ASP.NET, Entity Framework, Azure cloud services, and SQL Server.",
        url="http://ex.com"
    )
    assert detect_role_lens(job3) == "dotnet"


def test_m4_detect_role_lens_fullstack_and_fallback():
    """Full Stack lens detected for full stack titles and acts as robust fallback."""
    job1 = Job(title="Full Stack Developer", company="Startup", location="Pune", description="JavaScript, Python, React", url="http://ex.com")
    assert detect_role_lens(job1) == "fullstack"

    job2 = Job(title="Web Developer Intern", company="Agency", location="Mumbai", description="HTML, CSS, JavaScript, Web APIs", url="http://ex.com")
    assert detect_role_lens(job2) == "fullstack"

    job3 = Job(title="Software Engineer", company="Generic", location="Bangalore", description="General problem solving and coding.", url="http://ex.com")
    assert detect_role_lens(job3) == "fullstack"

    assert detect_role_lens(None) == "fullstack"


# =====================================================================
# 2. JD Boilerplate Stripping & Token Reduction
# =====================================================================

def test_m4_strip_boilerplate_token_reduction():
    """Boilerplate stripper achieves >= 50% length reduction on noisy JDs while preserving tech terms."""
    noisy_jd = """
About Us:
We are a global Fortune 500 company transforming digital services. Our Pune center is world-class.
Company Overview:
Founded in 2005, we have 50,000+ employees across 20 countries.

Job Description:
We are seeking an entry-level QA Automation Engineer to join our quality engineering team.
Requirements:
- Hands-on experience with Java and Python
- UI automation using Selenium WebDriver
- API testing using Postman
- Knowledge of SQL and relational databases
- Familiarity with Git, GitHub, and agile development workflows

Benefits:
- Competitive compensation and performance bonuses
- Comprehensive medical, dental, and vision insurance
- 401(k) matching and generous paid time off
- On-site gym, cafeteria, and wellness programs

Equal Opportunity Employer:
We are an equal opportunity employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, sexual orientation, gender identity, national origin, or protected veteran status.

Disclaimer:
This job posting is subject to background verification checks.
"""
    stripped = strip_boilerplate(noisy_jd)
    assert len(stripped) < len(noisy_jd) * 0.50, f"Expected >= 50% reduction, got {len(stripped)}/{len(noisy_jd)}"

    # Core tech terms MUST be preserved
    assert "Selenium" in stripped
    assert "Postman" in stripped
    assert "Java" in stripped
    assert "Python" in stripped
    assert "SQL" in stripped

    # Boilerplate MUST be removed
    assert "About Us:" not in stripped
    assert "Comprehensive medical" not in stripped
    assert "Equal Opportunity Employer:" not in stripped
    assert "401(k)" not in stripped


# =====================================================================
# 3. DeepSeek Reasoner API Parameter Handling & Thinking Tokens
# =====================================================================

def test_m4_call_ai_tailoring_reasoner_parameters():
    """call_ai_tailoring_async omits temperature & response_format for reasoner and captures reasoning_tokens."""
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"profile_summary": "Tailored summary.", "tailored_skills": ["Java", "SQL"]}\n```'
    mock_response.choices = [mock_choice]

    mock_usage = MagicMock()
    mock_usage.total_tokens = 600
    mock_usage.prompt_tokens = 300
    mock_usage.prompt_cache_hit_tokens = 200
    mock_usage.prompt_cache_miss_tokens = 100
    mock_usage.completion_tokens = 300
    mock_details = MagicMock()
    mock_details.reasoning_tokens = 180
    mock_usage.completion_tokens_details = mock_details
    mock_response.usage = mock_usage

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    async def run_test():
        with patch('src.ai_engine._get_async_client', return_value=(mock_client, "test-key")), \
             patch.dict(runtime_settings, {"tailoring_model": "deepseek-reasoner", "tailoring_thinking": True}):

            content, stats = await call_ai_tailoring_async("Test Prompt")

            # Verify kwargs sent to client
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "deepseek-reasoner"
            assert "temperature" not in call_kwargs, "temperature must be omitted for deepseek-reasoner"
            assert "response_format" not in call_kwargs, "response_format must be omitted for deepseek-reasoner"
            assert "extra_body" not in call_kwargs, "Anthropic extra_body thinking must not be passed to deepseek-reasoner"

            # Verify reasoning tokens telemetry
            assert stats["reasoning_tokens"] == 180
            assert stats["completion_tokens"] == 300
            assert stats["prompt_cache_hit_tokens"] == 200
            assert stats["model"] == "deepseek-reasoner"
            assert stats["stage"] == "tailoring"

            # Verify defensive brace matching cleaned markdown code fences
            assert content.startswith("{")
            assert content.endswith("}")

    asyncio.run(run_test())


# =====================================================================
# 4. Python-Level Zero-Hallucination Sanitizer Tests
# =====================================================================

def test_m4_zero_hallucination_prunes_fabricated_skills(master_resume, zero_hallucination_validator):
    """Sanitizer strictly prunes skills not present in candidate master profile."""
    untrusted_llm_delta = {
        "profile_summary": "Passionate engineer.",
        "tailored_skills": [
            "Java",
            "Python",
            "Kubernetes Cluster Management",
            "AWS Certified Solutions Architect",
            "Selenium",
            "Docker Containerization",
            "Postman",
            "SAP ABAP Enterprise",
            "PHP Laravel",
            "SQL",
            "Git"
        ]
    }

    sanitized = validate_and_sanitize_tailored(
        tailored_data=untrusted_llm_delta,
        master_resume=master_resume,
        role_lens="qa"
    )

    output_skills = sanitized["skills"]

    # Fabricated skills must be pruned
    assert "Kubernetes Cluster Management" not in output_skills
    assert "AWS Certified Solutions Architect" not in output_skills
    assert "Docker Containerization" not in output_skills
    assert "SAP ABAP Enterprise" not in output_skills
    assert "PHP Laravel" not in output_skills

    # Genuine skills must be kept
    assert "Java" in output_skills
    assert "Python" in output_skills
    assert "Selenium" in output_skills
    assert "Postman" in output_skills
    assert "SQL" in output_skills
    assert "Git" in output_skills

    # Must pass test suite zero_hallucination_validator fixture with 0 violations
    is_valid, violations = zero_hallucination_validator(sanitized)
    assert is_valid, f"Expected 0 violations, got: {violations}"


def test_m4_zero_hallucination_locks_education_and_employer(master_resume, zero_hallucination_validator):
    """Sanitizer resets tampered education, personal info, and employer to master profile values."""
    tampered_data = {
        "personal_information": {
            "name": "Fake Candidate",
            "email": "fake.hacker@darkweb.org",
            "phone": "0000000000"
        },
        "education_details": [
            {
                "education_level": "Ph.D. in Artificial Intelligence",
                "institution": "Stanford University",
                "final_evaluation_grade": "4.0 GPA",
                "year_of_completion": "2030"
            }
        ],
        "experience_details": [
            {
                "company": "Google LLC",
                "position": "Principal Architect",
                "employment_period": "2020 - Present"
            }
        ]
    }

    sanitized = validate_and_sanitize_tailored(
        tailored_data=tampered_data,
        master_resume=master_resume,
        role_lens="java"
    )

    # Education MUST be locked
    edu = sanitized["education_details"][0]
    assert edu["institution"] == "SKNSITS, Lonavala"
    assert edu["education_level"] == "Bachelors of Engineering in Information Technology"
    assert edu["final_evaluation_grade"] == "7.70 CGPA"
    assert edu["year_of_completion"] == "2026"

    # Employer MUST be locked to CWIPedia Technologies
    exp = sanitized["experience_details"][0]
    assert exp["company"] == "CWIPedia Technologies"
    assert exp["employment_period"] == "Jan 25 - Feb 25"
    assert exp["location"] == "Pune, India"

    # Personal info MUST be locked
    assert sanitized["personal_information"]["name"] == "Kaustubh"
    assert sanitized["personal_information"]["email"] == "kaustubh.kale.work@gmail.com"

    is_valid, violations = zero_hallucination_validator(sanitized)
    assert is_valid, f"Violations: {violations}"


def test_m4_canonical_alias_matching(master_resume, zero_hallucination_validator):
    """Common skill aliases ('Core Java', 'Selenium WebDriver', 'RESTful API', 'pytest testing') are recognized."""
    raw_delta = {
        "skills": ["Core Java", "Selenium WebDriver", "RESTful API", "pytest testing", "C#", "Azure"]
    }
    sanitized = validate_and_sanitize_tailored(raw_delta, master_resume, role_lens="qa")

    is_valid, violations = zero_hallucination_validator(sanitized)
    assert is_valid, f"Canonical aliases failed validator: {violations}"
    assert len(sanitized["skills"]) >= 4


def test_m4_empty_skills_fallback(master_resume, zero_hallucination_validator):
    """Empty or completely invalid skills delta falls back to role-relevant master skills."""
    empty_delta = {"skills": []}
    sanitized = validate_and_sanitize_tailored(empty_delta, master_resume, role_lens="qa")
    assert len(sanitized["skills"]) >= 8
    assert "Selenium" in sanitized["skills"]

    is_valid, violations = zero_hallucination_validator(sanitized)
    assert is_valid, f"Fallback skills failed validator: {violations}"


# =====================================================================
# 5. Retention of All 3 Verified Projects & Role Reordering
# =====================================================================

def test_m4_retains_all_3_verified_projects(master_resume):
    """All 3 verified candidate projects (SmartApply, CampFlow, Neon-Pulse) are retained with bullet budgeting."""
    delta = {
        "projects": [
            {
                "name": "SmartApply: AI-Driven Job Automation Pipeline",
                "description_bullets": ["Engineered scraping pipeline.", "Integrated prompt caching."]
            },
            {
                "name": "Crypto Currency Blockchain Trader",
                "description_bullets": ["Built smart contracts."]
            }
        ]
    }

    sanitized = validate_and_sanitize_tailored(delta, master_resume, role_lens="qa")
    projects = sanitized["projects"]

    assert len(projects) == 3, f"Expected 3 projects, got {len(projects)}"
    project_names = [p["name"].lower() for p in projects]

    assert any("smartapply" in n for n in project_names)
    assert any("campflow" in n for n in project_names)
    assert any("neon-pulse" in n or "neon" in n for n in project_names)
    assert not any("crypto" in n for n in project_names), "Fabricated project must be pruned"

    assert len(projects[0]["description_bullets"]) == 3
    assert len(projects[1]["description_bullets"]) == 2
    assert len(projects[2]["description_bullets"]) in [1, 2]


def test_m4_project_role_weighted_reordering(master_resume):
    """Fullstack lens prioritizes CampFlow (#1), while QA/Java/DotNet lenses prioritize SmartApply (#1)."""
    qa_sanitized = validate_and_sanitize_tailored({}, master_resume, role_lens="qa")
    assert "smartapply" in qa_sanitized["projects"][0]["name"].lower()

    java_sanitized = validate_and_sanitize_tailored({}, master_resume, role_lens="java")
    assert "smartapply" in java_sanitized["projects"][0]["name"].lower()

    dotnet_sanitized = validate_and_sanitize_tailored({}, master_resume, role_lens="dotnet")
    assert "smartapply" in dotnet_sanitized["projects"][0]["name"].lower()

    fs_sanitized = validate_and_sanitize_tailored({}, master_resume, role_lens="fullstack")
    assert "campflow" in fs_sanitized["projects"][0]["name"].lower()


# =====================================================================
# 6. Mathematical Coverage: >= 95% Applicable Candidate Skills (M ∩ J)
# =====================================================================

def test_m4_coverage_qa_role_with_auto_injection(master_resume):
    """Auto-injects missing candidate applicable skills to achieve >= 95% coverage on QA job."""
    job = Job(
        title="QA Automation Engineer Trainee",
        company="Barclays",
        location="Pune",
        description="Seeking candidate with Python, Selenium, Postman, SQL, Git, and pytest testing skills. Knowledge of JIRA and Docker is a plus.",
        url="http://ex.com"
    )
    job.extracted_requirements = "Selenium, Python, Postman, pytest, SQL, Git"
    job.is_testing_role = True

    applicable = get_applicable_candidate_skills(job, master_resume)
    assert "Selenium" in applicable
    assert "Postman" in applicable
    assert "pytest" in applicable
    assert "SQL" in applicable
    assert "Git" in applicable
    assert "Docker" not in applicable, "Non-candidate skills must not be in M ∩ J"
    assert "JIRA" not in applicable

    incomplete_delta = {
        "skills": ["Python", "Selenium"]
    }

    sanitized = validate_and_sanitize_tailored(incomplete_delta, master_resume, role_lens="qa", job=job)
    cov_pct, matched, all_app = calculate_jd_requirement_coverage(sanitized, job, master_resume)

    assert cov_pct >= 95.0, f"Expected >= 95% coverage, got {cov_pct:.1f}% ({len(matched)}/{len(all_app)})"
    assert set(matched) == set(all_app)
    assert len(sanitized["skills"]) <= 12, "Must not exceed 12 skills for single-page ATS budget"


def test_m4_coverage_java_role(master_resume):
    """Java backend job achieves >= 95% coverage of applicable candidate skills."""
    job = Job(
        title="Junior Java Developer",
        company="Persistent Systems",
        location="Pune",
        description="Requires Java, Spring Boot, JDBC, SQL, REST APIs, Maven. Kubernetes and AWS preferred.",
        url="http://ex.com"
    )
    job.extracted_requirements = "Java, Spring Boot, JDBC, SQL, REST APIs, Maven"

    sanitized = validate_and_sanitize_tailored({"skills": ["Java"]}, master_resume, role_lens="java", job=job)
    cov_pct, matched, all_app = calculate_jd_requirement_coverage(sanitized, job, master_resume)

    assert cov_pct >= 95.0, f"Expected >= 95% coverage, got {cov_pct:.1f}%"
    assert "Java" in matched
    assert "SQL" in matched
    assert "Spring Core" in matched or "Spring" in matched or "JDBC" in matched


def test_m4_coverage_dotnet_role(master_resume):
    """DotNet job achieves >= 95% coverage of applicable candidate skills (C#, SQL, Azure)."""
    job = Job(
        title=".NET Developer Fresher",
        company="Cognizant",
        location="Mumbai",
        description="Entry level role requiring C#, .NET fundamentals, SQL Server, and Microsoft Azure cloud.",
        url="http://ex.com"
    )
    job.extracted_requirements = "C#, .NET, SQL, Azure"

    sanitized = validate_and_sanitize_tailored({"skills": []}, master_resume, role_lens="dotnet", job=job)
    cov_pct, matched, all_app = calculate_jd_requirement_coverage(sanitized, job, master_resume)

    assert cov_pct >= 95.0, f"Expected >= 95% coverage, got {cov_pct:.1f}%"
    assert "C#" in matched
    assert "SQL" in matched


def test_m4_coverage_zero_applicable_skills_edge_case(master_resume):
    """Job with completely unrelated skills (e.g. Go, Rust, Cobol) returns 100% coverage without crashing."""
    job = Job(
        title="Rust Kernel Engineer",
        company="Systems Co",
        location="Bangalore",
        description="Must have 5 years Rust, C++, Linux kernel internals, FPGA design.",
        url="http://ex.com"
    )
    job.extracted_requirements = "Rust, C++, FPGA"

    sanitized = validate_and_sanitize_tailored({}, master_resume, role_lens="fullstack", job=job)
    cov_pct, matched, all_app = calculate_jd_requirement_coverage(sanitized, job, master_resume)

    assert cov_pct == 100.0
    assert len(all_app) == 0



# =====================================================================
# 7. End-to-End Async Tailoring Pipeline Test (Mocked Network)
# =====================================================================

def test_m4_e2e_tailor_resume_async_integration(sample_fresher_qa_job, master_resume, zero_hallucination_validator):
    """Full pipeline tailor_resume_async() produces role-lens reframed, sanitized resume with 0 hallucinations."""
    mock_ai_json = '''{
        "profile_summary": "Goal-oriented IT graduate with solid foundation in QA automation, Selenium, Postman, and pytest.",
        "tailored_skills": ["Selenium", "Postman", "pytest", "Python", "Java", "SQL", "Git", "AWS Lambda"],
        "tailored_experience": [
            {
                "position": "QA Automation Intern",
                "company": "CWIPedia Technologies",
                "key_responsibilities": [
                    "Automated API test suites using Postman and Python, reducing regression cycles by 30%.",
                    "Engineered modular UI test scripts with Selenium WebDriver for core product workflows.",
                    "Executed automated unit tests with JUnit and collaborated in Agile sprint stand-ups."
                ]
            }
        ],
        "tailored_projects": [
            {
                "name": "SmartApply: AI-Driven Job Automation Pipeline",
                "description_bullets": [
                    "Engineered Python and Pandas data extraction pipeline for automated job scraping.",
                    "Built JSON-based scoring and verification workflows for candidate evaluation.",
                    "Designed automated PDF generation with WeasyPrint and Windows Task Scheduler."
                ]
            },
            {
                "name": "CampFlow: Hospitality Automation & Booking Suite",
                "description_bullets": [
                    "Automated booking workflows for 5+ business owners with role-specific dashboards.",
                    "Conducted end-to-end user acceptance testing across Vercel deployed interfaces."
                ]
            }
        ]
    }'''

    async def run_test():
        with patch('src.resume_tailor.call_ai_tailoring_async', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (mock_ai_json, TokenUsage({"total_tokens": 450, "cost_usd": 0.001}))

            result = await tailor_resume_async(sample_fresher_qa_job)

            # 1. AWS Lambda was hallucinated by LLM -> MUST BE PRUNED
            assert "AWS Lambda" not in result["skills"]

            # 2. CampFlow was in delta, SmartApply was in delta, Neon-Pulse was omitted -> ALL 3 MUST BE PRESENT
            assert len(result["projects"]) == 3
            proj_names = [p["name"].lower() for p in result["projects"]]
            assert any("smartapply" in n for n in proj_names)
            assert any("campflow" in n for n in proj_names)
            assert any("neon" in n for n in proj_names)

            # 3. Static fields locked
            assert result["education_details"][0]["institution"] == "SKNSITS, Lonavala"
            assert result["experience_details"][0]["company"] == "CWIPedia Technologies"

            # 4. Zero-hallucination check passes 100%
            is_valid, violations = zero_hallucination_validator(result)
            assert is_valid, f"Tailored resume failed zero-hallucination check: {violations}"

    asyncio.run(run_test())
