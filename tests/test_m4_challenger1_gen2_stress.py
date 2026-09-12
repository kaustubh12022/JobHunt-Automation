"""
Adversarial Stress Test Suite - Milestone 4 Challenger 1 Gen 2
Stress-testing all 4 remediated vulnerabilities plus boundary cases.
"""
import pytest
import re
from src.resume_tailor import (
    load_resume,
    is_valid_candidate_skill,
    validate_and_sanitize_tailored,
    detect_role_lens,
    get_applicable_candidate_skills,
    calculate_jd_requirement_coverage,
    CANONICAL_MASTER_PROJECTS,
    _normalize_skill,
)
from src.scorer import strip_boilerplate, matches_out_of_scope_role
from src.models import Job


@pytest.fixture
def master_resume():
    return load_resume()


# ── Area 1: Substring Skill Matching & False Positives ──

def test_stress_fabricated_short_and_substring_skills(master_resume):
    """
    Exhaustively test short and substring skills to ensure zero false positives.
    """
    fabricated_skills = [
        "Go", "golang", "R", "ML", "AI", "CI", "CD", "OS", "UI", "UX", "C",
        "PHP", "Ruby", "Rust", "Swift", "Dart", "Perl", "Vue", "Angular",
        "React", "Docker", "Kubernetes", "AWS", "GCP", "Salesforce", "SAP",
        "Spring Boot 3", "Ruby on Rails", "Node", "Express", "Hadoop", "Spark",
        "PyTorch", "TensorFlow", "Keras", "Scikit-Learn", "Algos", "rithms",
        "script", "end", "dev", "net core"
    ]
    for skill in fabricated_skills:
        valid, canonical = is_valid_candidate_skill(skill, master_resume)
        assert not valid, f"Adversarial breach: Fabricated skill '{skill}' accepted as '{canonical}'"


def test_stress_authentic_skills_preserved(master_resume):
    """
    Ensure all authentic candidate skills (including punctuation and short names) are accepted.
    """
    authentic_skills = [
        "Java", "Python", "SQL", "C#", ".NET", "HTML", "CSS", "Git",
        "Maven", "Postman", "Selenium", "JUnit", "pytest", "DBMS",
        "OOP", "DSA", "REST APIs", "Asyncio", "Pandas",
        "Manual Testing Fundamentals", "Test Case Design", "MySQL"
    ]
    for skill in authentic_skills:
        valid, canonical = is_valid_candidate_skill(skill, master_resume)
        assert valid, f"Authentic skill '{skill}' was falsely rejected!"


def test_stress_alias_normalization(master_resume):
    """
    Test edge cases in skill alias variations.
    """
    alias_tests = [
        ("csharp", "C#"),
        ("dotnet", "C#"),
        ("dsa", "DSA"),
        ("oop", "OOP"),
        ("object oriented programming", "OOP"),
        ("dbms", "DBMS"),
        ("mysql", "MySQL"),
        ("html5", "HTML"),
        ("css3", "CSS"),
        ("rest api", "REST APIs"),
        ("restful apis", "REST APIs"),
    ]
    for input_skill, expected_canonical in alias_tests:
        valid, canonical = is_valid_candidate_skill(input_skill, master_resume)
        assert valid, f"Alias '{input_skill}' failed to match!"
        if input_skill == "dsa":
            assert canonical in ["DSA", "Data Structures & Algorithms"]
        else:
            assert canonical.lower() == expected_canonical.lower(), (
                f"Alias '{input_skill}' returned '{canonical}', expected '{expected_canonical}'"
            )


# ── Area 2: Experience Position Sanitization ──

@pytest.mark.parametrize("hostile_position", [
    "Staff Engineer, 5 yrs",
    "Senior Software Engineer",
    "Lead Developer",
    "Principal QA Architect",
    "Engineering Manager",
    "Technical Director",
    "Chief Architect",
    "Software Engineer (3+ yrs experience)",
    "Backend Developer, 4 years",
    "Vice President of Engineering",
    "Full Stack Lead",
    "Senior Intern",
    "Staff Intern",
    "Manager Trainee"
])
def test_stress_experience_senior_and_duration_sanitization(master_resume, hostile_position):
    """
    Verify all senior titles, duration claims, and manager variations are reverted to authentic title.
    """
    tampered = {
        "experience_details": [
            {
                "position": hostile_position,
                "company": "Hostile Corp",
                "employment_period": "2020 - 2026",
                "location": "New York, NY"
            }
        ]
    }
    sanitized = validate_and_sanitize_tailored(tampered, master_resume, role_lens="java")
    exp = sanitized["experience_details"][0]

    assert exp["position"] == "Java Developer Intern", (
        f"Hostile position '{hostile_position}' was not sanitized! Got '{exp['position']}'"
    )
    assert exp["company"] == "CWIPedia Technologies"
    assert exp["employment_period"] == "Jan 25 - Feb 25"
    assert exp["location"] == "Pune, India"


def test_stress_experience_valid_intern_variants(master_resume):
    """
    Verify valid entry-level variants (intern, trainee, fresher) without senior keywords are allowed.
    """
    valid_variants = [
        "Software Engineering Intern",
        "QA Automation Intern",
        "Graduate Trainee",
        "Java Trainee",
        "Software Fresher"
    ]
    for var in valid_variants:
        tampered = {
            "experience_details": [
                {
                    "position": var,
                    "company": "CWIPedia Technologies"
                }
            ]
        }
        sanitized = validate_and_sanitize_tailored(tampered, master_resume, role_lens="qa")
        exp = sanitized["experience_details"][0]
        assert exp["position"] == var, f"Valid variant '{var}' was improperly reset to '{exp['position']}'"


# ── Area 3: Project tech_stack Anchoring ──

def test_stress_project_tech_stack_strictly_immutable(master_resume):
    """
    Verify project tech_stack is completely locked to canonical metadata regardless of LLM injection.
    """
    tampered = {
        "projects": [
            {
                "name": "SmartApply: AI-Driven Job Automation Pipeline",
                "tech_stack": "AWS Cloud, Kubernetes, Terraform, Go, GraphQL, React",
                "link": "https://fake-link.com",
                "description_bullets": ["Bullet 1", "Bullet 2"]
            },
            {
                "name": "CampFlow: Camp Management Platform",
                "tech_stack": "C++, Unreal Engine, Solidity, Blockchain",
                "link": "https://crypto-camp.xyz",
                "description_bullets": ["Bullet 1", "Bullet 2"]
            },
            {
                "name": "Neon-Pulse: Real-Time Event Dashboard",
                "tech_stack": "Ruby, Rails, Kafka, Spark, Redis, BigQuery",
                "link": "https://neon-fake.io",
                "description_bullets": ["Bullet 1", "Bullet 2"]
            }
        ]
    }
    sanitized = validate_and_sanitize_tailored(tampered, master_resume, role_lens="fullstack")

    for proj in sanitized["projects"]:
        matched_key = None
        for key, meta in CANONICAL_MASTER_PROJECTS.items():
            if meta["name"] == proj["name"]:
                matched_key = key
                break
        assert matched_key is not None, f"Unknown project name: {proj['name']}"
        expected_meta = CANONICAL_MASTER_PROJECTS[matched_key]

        # Tech stack MUST exactly match canonical metadata
        assert proj["tech_stack"] == expected_meta["tech_stack"], (
            f"Tech stack was compromised! Got '{proj['tech_stack']}', expected '{expected_meta['tech_stack']}'"
        )
        assert proj["link"] == expected_meta["tech_stack"], (
            f"Project link was compromised! Got '{proj['link']}', expected '{expected_meta['tech_stack']}'"
        )
        # Verify no hostile keywords leaked
        for forbidden in ["AWS", "Kubernetes", "Terraform", "Solidity", "Blockchain", "Ruby", "Rails"]:
            assert forbidden not in proj["tech_stack"], f"Forbidden token '{forbidden}' leaked in tech_stack!"


# ── Area 4: Boilerplate Stripping Over-matching ──

def test_stress_strip_boilerplate_preserves_various_headers():
    """
    Test strip_boilerplate against tricky headers and note/disclaimer placements.
    """
    cases = [
        # Note before Technical Requirements
        (
            "About Us:\nWe are an amazing startup.\n\nNote: This is a fast-paced role.\n\nTechnical Requirements:\n- Java 17\n- Spring Boot\n- MySQL\n",
            ["Java 17", "Spring Boot", "MySQL"]
        ),
        # Equal opportunity before Responsibilities
        (
            "Equal Opportunity Employer:\nWe celebrate diversity.\n\nResponsibilities:\n- Develop automation scripts using Selenium and Python\n- Build test suites in pytest\n",
            ["Selenium", "Python", "pytest"]
        ),
        # Disclaimer before Qualifications
        (
            "Disclaimer: Candidate must be eligible to work in India.\n\nQualifications:\n- B.E. / B.Tech in IT/CS\n- Proficiency in SQL and Git\n",
            ["SQL", "Git"]
        ),
        # Note: This followed by standard CamelCase header with colon
        (
            "Note: This role is based in Pune.\n\nKey Skills Required:\n- C# and .NET Core\n- REST APIs and Azure\n",
            ["C#", ".NET Core", "REST APIs", "Azure"]
        ),
        # Benefits followed by Skills
        (
            "What We Offer:\n- Health insurance\n- 401k match\n\nSkills:\n- Postman\n- Manual Testing Fundamentals\n",
            ["Postman", "Manual Testing Fundamentals"]
        ),
    ]

    for dirty_text, expected_preserved in cases:
        stripped = strip_boilerplate(dirty_text)
        for req in expected_preserved:
            assert req in stripped, f"Boilerplate stripping erroneously removed '{req}' from JD!"


# ── Area 5: Java & JavaScript Co-occurrence & Requirement Coverage ──

def test_stress_java_and_javascript_cooccurrence(master_resume):
    """
    Verify that in a Full Stack JD requiring both Java and JavaScript,
    neither skill is dropped and both are recognized as applicable.
    """
    job = Job(
        title="Full Stack Java & JavaScript Developer",
        company="Tech Innovators",
        location="Pune",
        description="Looking for a developer with strong Java and Spring Core, plus frontend skills in JavaScript and HTML/CSS.",
        url="https://example.com/job1"
    )
    applicable = get_applicable_candidate_skills(job, master_resume)
    assert "Java" in applicable, "Java was dropped in co-occurrence with JavaScript!"
    assert "JavaScript" in applicable, "JavaScript was not recognized!"

    # Calculate coverage
    tailored = {
        "skills": ["Java", "JavaScript", "Spring Core", "HTML", "CSS", "SQL", "Git"]
    }
    cov, cov_skills, missing = calculate_jd_requirement_coverage(tailored, job, master_resume)
    assert "Java" in cov_skills
    assert "JavaScript" in cov_skills
    assert cov >= 80.0
