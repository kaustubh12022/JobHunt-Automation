"""
Adversarial Stress-Testing Suite by Challenger 2 for Milestone 4.
Covers:
1. Ambiguous, conflicting, and edge-case role titles and contents in detect_role_lens.
2. Realistic JDs for QA, Java, .NET, Fullstack with candidate-known and candidate-unknown skills.
3. Verification of >= 95% requirement coverage on M n J and strict exclusion of J \ M.
4. Edge cases: M n J = 0, empty titles, None attributes, high-skill count JDs.
5. DeepSeek reasoner parameter safety: temperature and response_format omission, casing, and reasoning token extraction.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import Job
from src.config_loader import load_resume
from src.resume_tailor import (
    detect_role_lens,
    get_applicable_candidate_skills,
    calculate_jd_requirement_coverage,
    validate_and_sanitize_tailored,
    is_valid_candidate_skill,
    _normalize_skill
)
from src.ai_engine import call_ai_tailoring_async, TokenUsage, runtime_settings


# ==============================================================================
# SECTION 1: Adversarial Role-Lens Classification
# ==============================================================================

@pytest.mark.parametrize("title,desc,reqs,is_testing,expected_lens", [
    # Conflicting Title: Both Fullstack and QA
    ("Fullstack Java QA Engineer", "Write tests and web code", "", False, "qa"),
    # Conflicting Title: Both Python and .NET
    ("Python .NET Developer", "C# backend and python scripts", "", False, "dotnet"),
    # Conflicting Title: Both Java and .NET
    ("Java / .NET Software Engineer", "Build enterprise apps", "", False, "dotnet"),
    # Title says Java, but is_testing_role flag is explicitly set
    ("Java Backend Developer", "Java Spring Boot", "", True, "qa"),
    # Obscure / Empty / Special characters
    ("", "Looking for Selenium, Postman, pytest test engineer", "", False, "qa"),
    (None, "Java, Spring Boot, JDBC, Maven, MySQL developer", "", False, "java"),
    ("?? 12345 !@#$%^&*()", "ASP.NET Core, C#, Azure, SQL Server", "", False, "dotnet"),
    ("Happiness Coordinator", "No technical content here at all", "", False, "fullstack"),
    # Generic title, conflicting content
    ("Graduate Engineer Trainee", "Selenium Postman test case vs Java Spring Boot", "", False, "qa"),
    # Generic title with equal content keyword tie (QA=1, .NET=1, Java=1, Fullstack=1)
    ("Software Engineer Trainee", "Selenium C# Java JavaScript", "", False, "qa"),
])
def test_detect_role_lens_adversarial_titles(title, desc, reqs, is_testing, expected_lens):
    job = Job(
        title=title,
        company="Adversarial Corp",
        location="Pune",
        description=desc,
        url="http://example.com",
        extracted_requirements=reqs,
        is_testing_role=is_testing
    )
    result = detect_role_lens(job)
    assert result == expected_lens, f"Failed for title='{title}': expected {expected_lens}, got {result}"


def test_detect_role_lens_none_job_safe():
    """Confirms detect_role_lens handles None without crashing."""
    assert detect_role_lens(None) == "fullstack"


# ==============================================================================
# SECTION 2: Realistic JDs & Coverage on M n J (QA, Java, .NET, Fullstack)
# ==============================================================================

def test_coverage_and_isolation_qa_realistic():
    """
    Realistic QA Automation JD:
    Candidate known (M n J): Selenium, Postman, pytest, JUnit, Python, SQL, Git, Agile/Scrum
    Candidate unknown (J \\ M): Appium, Cypress, Robot Framework, Jenkins, TestNG, JIRA, Karate
    """
    resume = load_resume()
    jd_desc = """
    Role: QA Automation Engineer Fresher
    Required Skills:
    - Strong knowledge of Selenium WebDriver, Postman API testing, pytest, and JUnit.
    - Scripting skills in Python and SQL for database validation.
    - Version control with Git and experience in Agile/Scrum sprints.
    - Bonus: Appium mobile automation, Cypress, Robot Framework, Jenkins CI/CD, TestNG, JIRA, and Karate.
    """
    job = Job(title="QA Automation Engineer", company="QASolutions", location="Pune", description=jd_desc, url="http://ex.com")
    
    app_skills = get_applicable_candidate_skills(job, resume)
    unknown_skills = ["Appium", "Cypress", "Robot Framework", "Jenkins", "TestNG", "JIRA", "Karate"]
    for u in unknown_skills:
        assert not any(_normalize_skill(u) == _normalize_skill(a) for a in app_skills), f"{u} must not be in M n J"

    llm_output = {
        "skills": ["Cypress", "Jenkins", "Appium", "Selenium", "Postman", "AWS", "Docker"],
        "projects": [{"name": "SmartApply", "description_bullets": ["Bullet 1", "Bullet 2"]}]
    }
    sanitized = validate_and_sanitize_tailored(llm_output, resume, "qa", job=job)
    
    for u in unknown_skills + ["AWS", "Docker"]:
        assert not any(_normalize_skill(u) == _normalize_skill(s) for s in sanitized["skills"]), f"{u} leaked into resume!"

    coverage, matched, total_app = calculate_jd_requirement_coverage(sanitized, job, resume)
    assert coverage >= 95.0, f"QA Coverage was {coverage}%, expected >= 95%"


def test_coverage_and_isolation_java_realistic():
    """
    Realistic Java Developer JD:
    Candidate known (M n J): Java, Spring Core, JDBC, SQL, REST APIs, OOP, DBMS, Maven, Git, Agile/Scrum
    Candidate unknown (J \\ M): Spring Cloud, Microservices, Kafka, Redis, Docker, Kubernetes, AWS, GraphQL
    """
    resume = load_resume()
    jd_desc = """
    Role: Junior Java Backend Developer
    We are seeking a Junior Java Developer proficient in Core Java, Spring Boot / Spring Core, JDBC, SQL, and REST APIs.
    Must understand OOP principles, DBMS concepts, Maven build management, Git, and Agile/Scrum methodologies.
    Preferred: Spring Cloud, Kafka event streaming, Redis caching, Docker, Kubernetes, AWS ECS, and GraphQL.
    """
    job = Job(title="Junior Java Developer", company="FinTech Corp", location="Mumbai", description=jd_desc, url="http://ex.com")
    
    app_skills = get_applicable_candidate_skills(job, resume)
    unknown_skills = ["Spring Cloud", "Kafka", "Redis", "Docker", "Kubernetes", "AWS", "GraphQL"]
    for u in unknown_skills:
        assert not any(_normalize_skill(u) == _normalize_skill(a) for a in app_skills), f"{u} must not be in M n J"

    llm_output = {
        "skills": ["Java", "Spring Core", "Kafka", "Redis", "Docker", "AWS"],
        "projects": []
    }
    sanitized = validate_and_sanitize_tailored(llm_output, resume, "java", job=job)
    
    for u in unknown_skills:
        assert not any(_normalize_skill(u) == _normalize_skill(s) for s in sanitized["skills"]), f"{u} leaked into resume!"

    coverage, matched, total_app = calculate_jd_requirement_coverage(sanitized, job, resume)
    assert coverage >= 95.0, f"Java Coverage was {coverage}%, expected >= 95%"


def test_coverage_and_isolation_dotnet_realistic():
    """
    Realistic .NET / C# Developer JD:
    Candidate known (M n J): C#, SQL, REST APIs, Azure, OOP, DBMS, Git, Agile/Scrum
    Candidate unknown (J \\ M): Blazor, Entity Framework, LINQ, WPF, WCF, RabbitMQ
    """
    resume = load_resume()
    jd_desc = """
    Role: C# .NET Software Engineer
    Requirements:
    - Hands-on with C# and Microsoft Azure cloud services.
    - Strong database skills with SQL, DBMS, and developing REST APIs.
    - Fundamental OOP knowledge, Git version control, and Agile/Scrum experience.
    - Nice to have: Blazor, Entity Framework, LINQ, WPF desktop apps, WCF services, and RabbitMQ.
    """
    job = Job(title="C# .NET Software Engineer", company="CloudNet", location="Bangalore", description=jd_desc, url="http://ex.com")
    
    app_skills = get_applicable_candidate_skills(job, resume)
    unknown_skills = ["Blazor", "Entity Framework", "LINQ", "WPF", "WCF", "RabbitMQ"]
    for u in unknown_skills:
        assert not any(_normalize_skill(u) == _normalize_skill(a) for a in app_skills), f"{u} must not be in M n J"

    llm_output = {
        "skills": ["C#", "Blazor", "Entity Framework", "RabbitMQ", "SQL"],
        "projects": []
    }
    sanitized = validate_and_sanitize_tailored(llm_output, resume, "dotnet", job=job)
    
    for u in unknown_skills:
        assert not any(_normalize_skill(u) == _normalize_skill(s) for s in sanitized["skills"]), f"{u} leaked into resume!"

    coverage, matched, total_app = calculate_jd_requirement_coverage(sanitized, job, resume)
    assert coverage >= 95.0, f".NET Coverage was {coverage}%, expected >= 95%"


def test_coverage_and_isolation_fullstack_realistic():
    """
    Realistic Full Stack / Web Developer JD:
    Candidate known (M n J): JavaScript, TypeScript, HTML, CSS, REST APIs, SQL, Git, Python, Pandas, Asyncio
    Candidate unknown (J \\ M): React, Angular, Vue, Node, Express, MongoDB, Next.js
    """
    resume = load_resume()
    jd_desc = """
    Role: Associate Full Stack Developer
    Looking for freshers proficient in JavaScript, TypeScript, HTML, CSS, REST APIs, and SQL.
    Scripting with Python, Pandas for data processing, Asyncio, and Git.
    Nice to have: React, Angular, Vue.js, Node.js, Express, MongoDB, Next.js, and Tailwind CSS.
    """
    job = Job(title="Full Stack Developer", company="WebCraft", location="Pune", description=jd_desc, url="http://ex.com")
    
    app_skills = get_applicable_candidate_skills(job, resume)
    unknown_skills = ["React", "Angular", "Vue", "Node", "Express", "MongoDB", "Next.js"]
    for u in unknown_skills:
        assert not any(_normalize_skill(u) == _normalize_skill(a) for a in app_skills), f"{u} must not be in M n J"

    llm_output = {
        "skills": ["React", "Node", "MongoDB", "JavaScript", "HTML"],
        "projects": []
    }
    sanitized = validate_and_sanitize_tailored(llm_output, resume, "fullstack", job=job)
    
    for u in unknown_skills:
        assert not any(_normalize_skill(u) == _normalize_skill(s) for s in sanitized["skills"]), f"{u} leaked into resume!"

    coverage, matched, total_app = calculate_jd_requirement_coverage(sanitized, job, resume)
    assert coverage >= 95.0, f"Fullstack Coverage was {coverage}%, expected >= 95%"


# ==============================================================================
# SECTION 3: Edge Cases: Zero Common Skills (M n J = Ø) and High-Overlap JDs
# ==============================================================================

def test_coverage_zero_overlap_edge_case():
    """
    When candidate has zero common skills with JD (e.g. Embedded C / Rust / Firmware),
    coverage should cleanly return 100.0% without division by zero.
    """
    resume = load_resume()
    jd_desc = "Firmware engineer needed for microcontrollers using Rust, Assembly, RTOS, Verilog, FPGA, PCB layout."
    job = Job(title="Embedded Firmware Engineer", company="HardwareCo", location="Pune", description=jd_desc, url="http://ex.com")
    
    app_skills = get_applicable_candidate_skills(job, resume)
    assert len(app_skills) == 0, f"Expected 0 applicable skills, got {app_skills}"

    sanitized = validate_and_sanitize_tailored({}, resume, "fullstack", job=job)
    coverage, matched, all_app = calculate_jd_requirement_coverage(sanitized, job, resume)
    assert coverage == 100.0
    assert matched == []
    assert all_app == []


def test_coverage_high_overlap_saturation():
    """
    Stress-test what happens if a JD requires MORE than 12 applicable skills.
    Because single-page resume caps skills at 12, what is the resulting coverage?
    """
    resume = load_resume()
    jd_desc = """
    Requirements:
    Java, Python, C#, JavaScript, TypeScript, HTML, CSS, SQL, Spring Core, JDBC,
    REST APIs, Selenium, Postman, pytest, JUnit, Git, Azure, Maven, Agile
    """
    job = Job(title="Software Engineer", company="MegaCorp", location="Pune", description=jd_desc, url="http://ex.com")
    app_skills = get_applicable_candidate_skills(job, resume)
    assert len(app_skills) >= 15, f"Expected >= 15 applicable skills, got {len(app_skills)}"

    sanitized = validate_and_sanitize_tailored({}, resume, "fullstack", job=job)
    assert len(sanitized["skills"]) == 12

    coverage, matched, all_app = calculate_jd_requirement_coverage(sanitized, job, resume)
    expected_ratio = round((len(matched) / len(app_skills)) * 100.0, 2)
    assert coverage == expected_ratio


# ==============================================================================
# SECTION 4: DeepSeek Reasoner Parameter Safety & Telemetry
# ==============================================================================

@pytest.mark.parametrize("model_name,should_omit_params", [
    ("deepseek-reasoner", True),
    ("deepseek-reasoner-v2", True),
    ("DeepSeek-Reasoner", True),
    ("DEEPSEEK-REASONER", True),
    ("deepseek-chat", False),
    ("deepseek-chat-v3", False),
])
def test_reasoner_parameter_safety_matrix(model_name, should_omit_params):
    """
    Ensures that for all variations of deepseek-reasoner:
    - temperature is NOT passed
    - response_format is NOT passed
    - extra_body is NOT passed
    While for chat models:
    - temperature IS passed
    - response_format IS passed
    """
    async def run():
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"skills": ["Java", "SQL"], "profile_summary": "Test summary"}'))
        ]
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 500
        mock_usage.prompt_cache_hit_tokens = 200
        mock_usage.prompt_cache_miss_tokens = 300
        mock_usage.completion_tokens = 150
        mock_usage.total_tokens = 650
        mock_usage.completion_tokens_details = {"reasoning_tokens": 85}
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()

        with patch("src.ai_engine._get_async_client", return_value=(mock_client, "dummy_key")):
            with patch.dict(runtime_settings, {"tailoring_model": model_name, "tailoring_thinking": True}):
                content, token_usage = await call_ai_tailoring_async("Test user prompt")
                
                call_kwargs = mock_client.chat.completions.create.call_args[1]
                if should_omit_params:
                    assert "temperature" not in call_kwargs, f"temperature leaked into {model_name} kwargs!"
                    assert "response_format" not in call_kwargs, f"response_format leaked into {model_name} kwargs!"
                    assert "extra_body" not in call_kwargs, f"extra_body leaked into {model_name} kwargs!"
                else:
                    assert "temperature" in call_kwargs, f"temperature missing for chat model {model_name}"
                    assert "response_format" in call_kwargs, f"response_format missing for chat model {model_name}"

                assert token_usage["reasoning_tokens"] == 85
                assert token_usage["model"] == model_name

    asyncio.run(run())


def test_reasoner_object_details_reasoning_tokens():
    """Verify reasoning_tokens extracted when completion_tokens_details is an object rather than dict."""
    async def run():
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"skills": ["Python"]}'))]
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.prompt_cache_hit_tokens = 0
        mock_usage.prompt_cache_miss_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        
        class Details:
            reasoning_tokens = 42
        mock_usage.completion_tokens_details = Details()
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()

        with patch("src.ai_engine._get_async_client", return_value=(mock_client, "dummy_key")):
            with patch.dict(runtime_settings, {"tailoring_model": "deepseek-reasoner"}):
                content, token_usage = await call_ai_tailoring_async("Prompt")
                assert token_usage["reasoning_tokens"] == 42

    asyncio.run(run())


def test_reasoner_content_thought_tag_and_fence_stripping():
    """
    DeepSeek Reasoner may emit thought chains or markdown fences before the JSON payload:
    <thought>Let's think step by step...</thought>
    ```json
    {"skills": ["Java", "Python"]}
    ```
    Confirm brace matching properly isolates valid JSON payload.
    """
    async def run():
        raw_payload = (
            "<thought>\n"
            "Candidate is a fresher in IT.\n"
            "Need to tailor for QA.\n"
            "</thought>\n"
            "```json\n"
            "{\"skills\": [\"Selenium\", \"Postman\"], \"profile_summary\": \"Solid QA engineer\"}\n"
            "```\n"
            "Hope this helps!"
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=raw_payload))]
        mock_response.usage = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()

        with patch("src.ai_engine._get_async_client", return_value=(mock_client, "dummy_key")):
            with patch.dict(runtime_settings, {"tailoring_model": "deepseek-reasoner"}):
                content, token_usage = await call_ai_tailoring_async("Prompt")
                import json
                parsed = json.loads(content)
                assert "skills" in parsed
                assert parsed["skills"] == ["Selenium", "Postman"]
                assert parsed["profile_summary"] == "Solid QA engineer"

    asyncio.run(run())

