"""
Challenger 1 Adversarial Stress Test Suite for Milestone 4.
Empirically stress-tests zero-hallucination guardrails, immutability locking,
project retention, and boilerplate stripping against adversarial payloads.
"""
import pytest
import re
from src.models import Job
from src.config_loader import load_resume
from src.scorer import strip_boilerplate
from src.resume_tailor import (
    validate_and_sanitize_tailored,
    is_valid_candidate_skill,
    detect_role_lens,
    get_applicable_candidate_skills,
    calculate_jd_requirement_coverage,
    _normalize_skill
)


# =====================================================================
# 1. Zero-Hallucination & Skill Guardrail Stress Tests
# =====================================================================

def test_adversarial_zero_hallucination_prunes_all_fake_skills(master_resume, zero_hallucination_validator):
    """
    Stress-tests skill sanitizer against a hostile payload of fabricated technologies
    specified in DISPATCH.md: AWS, Docker, K8s, Ruby, Go, SAP, plus additional cloud/devops stacks.
    """
    adversarial_payload = {
        "profile_summary": "Fabricated summary claiming extensive cloud and systems mastery.",
        "skills": [
            "AWS",
            "Docker",
            "Kubernetes",
            "Ruby",
            "Go",
            "SAP",
            "SAP ABAP",
            "Terraform",
            "PHP",
            "COBOL",
            "Rust",
            "Java",
            "Python",
            "Selenium",
            "SQL"
        ]
    }

    sanitized = validate_and_sanitize_tailored(adversarial_payload, master_resume, role_lens="qa")
    skills = sanitized["skills"]

    # Explicitly verify fabricated skills from dispatch are pruned
    assert "AWS" not in skills, "AWS must be pruned"
    assert "Docker" not in skills, "Docker must be pruned"
    assert "Kubernetes" not in skills, "Kubernetes must be pruned"
    assert "Ruby" not in skills, "Ruby must be pruned"
    assert "SAP" not in skills, "SAP must be pruned"
    assert "SAP ABAP" not in skills, "SAP ABAP must be pruned"
    assert "Terraform" not in skills, "Terraform must be pruned"
    assert "PHP" not in skills, "PHP must be pruned"
    assert "COBOL" not in skills, "COBOL must be pruned"

    # Authentic skills should remain
    assert "Java" in skills
    assert "Python" in skills
    assert "Selenium" in skills
    assert "SQL" in skills

    # CRITICAL CHALLENGE: Check if 'Go' (specified in prompt) was pruned or leaked!
    # If 'Go' matched 'Data Structures & Algorithms' via unanchored substring, this fails:
    assert not any(s == "Data Structures & Algorithms" for s in skills if "Data Structures & Algorithms" not in adversarial_payload["skills"]), (
        "VULNERABILITY DETECTED: 'Go' was erroneously accepted as valid skill 'Data Structures & Algorithms'!"
    )


def test_adversarial_substring_skill_injection_vulnerability(master_resume):
    """
    Directly tests whether short skill names (Go, R, ML, CI, DB, OS) trigger false positive
    substring matches against the candidate's master skill vocabulary.
    """
    # Go matches 'alGOrithms' in 'data structures & algorithms'
    valid_go, canonical_go = is_valid_candidate_skill("Go", master_resume)
    assert not valid_go, f"VULNERABILITY: Fabricated skill 'Go' was marked valid as {canonical_go!r}!"

    # R matches 'azuRe' in 'c# (basics via azure)'
    valid_r, canonical_r = is_valid_candidate_skill("R", master_resume)
    assert not valid_r, f"VULNERABILITY: Fabricated skill 'R' was marked valid as {canonical_r!r}!"

    # ML matches 'htML'
    valid_ml, canonical_ml = is_valid_candidate_skill("ML", master_resume)
    assert not valid_ml, f"VULNERABILITY: Fabricated skill 'ML' was marked valid as {canonical_ml!r}!"


# =====================================================================
# 2. Immutability Stress Tests: Education, Employer, and Role
# =====================================================================

def test_adversarial_locks_education_credentials(master_resume):
    """
    Stress-tests tampering of education with elite universities, fake GPA, and altered graduation.
    """
    tampered = {
        "education_details": [
            {
                "institution": "Harvard University",
                "education_level": "Master of Science in Computer Science",
                "final_evaluation_grade": "4.0 GPA",
                "year_of_completion": "2024"
            },
            {
                "institution": "Massachusetts Institute of Technology (MIT)",
                "education_level": "Ph.D. in Artificial Intelligence",
                "final_evaluation_grade": "Summa Cum Laude",
                "year_of_completion": "2020"
            }
        ]
    }
    sanitized = validate_and_sanitize_tailored(tampered, master_resume, role_lens="java")
    edu = sanitized["education_details"]

    assert len(edu) == 1, "Must retain candidate's single authentic education record"
    assert edu[0]["institution"] == "SKNSITS, Lonavala"
    assert edu[0]["education_level"] == "Bachelors of Engineering in Information Technology"
    assert edu[0]["final_evaluation_grade"] == "7.70 CGPA"
    assert edu[0]["year_of_completion"] == "2026"


def test_adversarial_locks_employer_and_role(master_resume):
    """
    Stress-tests tampering of employer and position:
    Fabricated payload claims 'Staff Engineer, 5 yrs' at 'Google LLC'.
    Immutability must restore authentic employer ('CWIPedia Technologies')
    AND prevent senior role hallucinations ('Staff Engineer, 5 yrs').
    """
    tampered = {
        "experience_details": [
            {
                "company": "Google LLC",
                "position": "Staff Engineer, 5 yrs",
                "employment_period": "2019 - 2024 (5 years)",
                "location": "Mountain View, CA"
            }
        ]
    }
    sanitized = validate_and_sanitize_tailored(tampered, master_resume, role_lens="qa")
    exp = sanitized["experience_details"][0]

    assert exp["company"] == "CWIPedia Technologies"
    assert exp["employment_period"] == "Jan 25 - Feb 25"
    assert exp["location"] == "Pune, India"

    # CRITICAL CHALLENGE: Check if 'Staff Engineer, 5 yrs' leaked into position!
    assert "Staff Engineer" not in exp["position"] and "5 yrs" not in exp["position"], (
        f"VULNERABILITY DETECTED: Fabricated role 'Staff Engineer, 5 yrs' leaked through sanitization into experience position: {exp['position']!r}!"
    )


def test_adversarial_project_tech_stack_hallucination(master_resume):
    """
    Stress-tests whether fabricated skills injected in project 'tech_stack' leak into output.
    """
    tampered = {
        "projects": [
            {
                "name": "SmartApply: AI-Driven Job Automation Pipeline",
                "tech_stack": "AWS, Kubernetes, Docker, SAP, Ruby",
                "description_bullets": ["Bullet 1", "Bullet 2", "Bullet 3"]
            }
        ]
    }
    sanitized = validate_and_sanitize_tailored(tampered, master_resume, role_lens="qa")
    proj = sanitized["projects"][0]

    # Verify no fabricated technologies survive in the project's tech stack / link
    assert "AWS" not in proj["tech_stack"] and "Kubernetes" not in proj["tech_stack"], (
        f"VULNERABILITY DETECTED: Fabricated tech stack leaked into project header: {proj['tech_stack']!r}!"
    )


# =====================================================================
# 3. Project Retention & Excessive Bullets Stress Tests
# =====================================================================

def test_adversarial_project_omission_and_excess_bullets(master_resume):
    """
    Verifies that:
    1. All 3 verified projects are retained when LLM drops projects (0 or 1 project returned).
    2. Excessive bullet counts (e.g. 10 bullets per project) are strictly budgeted (<= 3, 2, 2).
    """
    # Test 1: Empty projects payload
    empty_payload = {"projects": []}
    sanitized_empty = validate_and_sanitize_tailored(empty_payload, master_resume, role_lens="qa")
    assert len(sanitized_empty["projects"]) == 3
    assert [len(p["description_bullets"]) for p in sanitized_empty["projects"]] == [3, 2, 2]

    # Test 2: Massive bullet flood (10 bullets per project, 10 bullets in experience)
    flood_payload = {
        "experience_details": [
            {
                "position": "Intern",
                "key_responsibilities": [f"Responsibility bullet {i}" for i in range(10)]
            }
        ],
        "projects": [
            {"name": "SmartApply", "description_bullets": [f"SmartApply bullet {i}" for i in range(10)]},
            {"name": "CampFlow", "description_bullets": [f"CampFlow bullet {i}" for i in range(10)]},
            {"name": "Neon-Pulse", "description_bullets": [f"Neon-Pulse bullet {i}" for i in range(10)]}
        ]
    }
    sanitized_flood = validate_and_sanitize_tailored(flood_payload, master_resume, role_lens="fullstack")

    # Projects must be budgeted to 3, 2, 2
    proj_bullet_counts = [len(p["description_bullets"]) for p in sanitized_flood["projects"]]
    assert proj_bullet_counts == [3, 2, 2], f"Expected [3, 2, 2], got {proj_bullet_counts}"

    # Experience must be budgeted to <= 3
    exp_bullet_count = len(sanitized_flood["experience_details"][0]["key_responsibilities"])
    assert exp_bullet_count <= 3, f"Expected <= 3 experience bullets, got {exp_bullet_count}"


# =====================================================================
# 4. Boilerplate Stripping Stress Tests with Dirty JDs
# =====================================================================

def test_adversarial_strip_boilerplate_preserves_requirements():
    """
    Tests whether strip_boilerplate inadvertently destroys technical requirements
    when common prelude phrases like 'Note: This' or 'Diversity:' appear before requirements.
    """
    dirty_jd = (
        "Job Title: QA Automation Engineer\n"
        "Location: Pune, India\n"
        "Note: This is an immediate hiring requisition for entry-level candidates.\n\n"
        "Technical Requirements:\n"
        "- Experience in Selenium WebDriver and Python\n"
        "- Knowledge of Postman API testing and SQL\n"
        "- Strong problem solving and Git skills\n"
    )

    stripped = strip_boilerplate(dirty_jd)

    assert "Selenium" in stripped, "VULNERABILITY DETECTED: 'Note: This' caused entire requirements section to be wiped out!"
    assert "Postman" in stripped
    assert "SQL" in stripped
