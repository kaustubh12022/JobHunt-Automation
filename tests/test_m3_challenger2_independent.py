"""
Milestone 3 Challenger 2 Gen 2 Independent Adversarial Verification Suite.

Adversarially challenges:
1. Zero wasted AI calls on ALL out-of-scope tech stacks:
   - PHP, Laravel, Ruby, Ruby on Rails, iOS, Swift, SwiftUI, Android, Kotlin, Flutter, React Native, Salesforce, Apex, SAP, ABAP, Drupal, Magento, WordPress.
   - Tested on both Title-level mentions and JD-level mentions with generic titles.
   - Verified that valid fresher target roles (Java, QA, .NET, Full Stack) are NOT blocked.
2. Slicing resilience and token telemetry accounting:
   - ScoredJobList slicing preserves all_scored_jobs across arbitrary slices ([:3], [:1], [1:4], [::2]).
   - save_pipeline_results captures all 1,500 tokens from 10 scored jobs when only 1 is shortlisted.
   - Fallbacks (pipeline_state['all_scored_jobs'] and get_last_scored_jobs()) successfully capture all 1,500 tokens when plain list is passed.
3. Score coercion and threshold resilience:
   - String scores ("85", "85.5", "90"), missing keys, None, and corrupt string values ("invalid", "NaN").
   - Cached JD score coercion with string values.
   - Strict threshold 60 application across both test and production modes.
4. TokenUsage dunder arithmetic & relational invariants.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.models import Job
from src.ai_engine import TokenUsage
from src.scorer import (
    score_jobs,
    is_relevant_jd,
    matches_out_of_scope_role,
    ScoredJobList,
    get_last_scored_jobs,
)
from src.db import save_pipeline_results


# ==============================================================================
# SECTION 1: Exhaustive Out-of-Scope Stacks Zero Wasted Calls Challenge
# ==============================================================================

OUT_OF_SCOPE_TEST_CASES = [
    # (title, description, stack_name)
    ("PHP Developer", "Develop web services with PHP and MySQL. Write unit test cases and integrate REST APIs. Git repository.", "PHP"),
    ("Junior Laravel Developer", "Backend development in Laravel framework. Design MySQL schemas. Write automated tests.", "Laravel"),
    ("Ruby Developer", "Maintain Ruby backend services. Write unit tests with RSpec. Work with PostgreSQL and Git.", "Ruby"),
    ("Ruby on Rails Engineer", "Develop web features using Ruby on Rails. RESTful API integration. Automated testing.", "Ruby on Rails"),
    ("iOS Developer", "Build iOS apps in Swift and UIKit. Write automated tests with XCTest. Integrate REST APIs.", "iOS"),
    ("Swift Developer", "Develop mobile client in Swift. Unit testing and Git version control. RESTful APIs.", "Swift"),
    ("SwiftUI Engineer", "Mobile UI in SwiftUI and Swift. Work with REST endpoints and SQLite database.", "SwiftUI"),
    ("Android Developer", "Build Android applications using Java and Android SDK. Write JUnit test cases. SQLite database.", "Android"),
    ("Kotlin Mobile Developer", "Develop mobile apps using Kotlin and Android Jetpack. Unit testing with JUnit and mockito.", "Kotlin"),
    ("Flutter Developer", "Cross-platform mobile apps in Flutter and Dart. Unit tests and REST API integration.", "Flutter"),
    ("React Native Developer", "Cross-platform apps in React Native. Automated unit tests with Jest. REST APIs.", "React Native"),
    ("Salesforce Developer", "Develop Salesforce CRM solutions, Apex classes, and Visualforce pages. Database SOQL.", "Salesforce"),
    ("Apex Developer", "Write Apex triggers, batch classes, and unit tests in Salesforce environment.", "Apex"),
    ("SAP Consultant", "Configure SAP ERP modules. Database queries and interface testing.", "SAP"),
    ("SAP ABAP Developer", "Develop ABAP reports, interfaces, and database tables. Testing and debugging.", "SAP ABAP"),
    ("WordPress Developer", "Custom WordPress theme and plugin development using PHP and MySQL. API integration.", "WordPress"),
    ("Drupal Developer", "Drupal CMS configuration, PHP modules, and MySQL database management.", "Drupal"),
    ("Magento Developer", "E-commerce store customization in Magento 2 and PHP. Database optimization and testing.", "Magento"),
    # Generic title, but out-of-scope stack in JD:
    ("Junior Software Engineer", "Develop mobile applications using Flutter and Dart. Write automated tests.", "Flutter (JD only)"),
    ("Associate Developer", "Join our mobile team developing native Android apps with Kotlin and SQLite.", "Android Kotlin (JD only)"),
    ("Software Engineer Trainee", "Build iOS applications using Swift and Xcode. Unit testing with XCTest.", "iOS Swift (JD only)"),
    ("Backend Developer Trainee", "Maintain backend microservices in Ruby on Rails. MySQL database and REST APIs.", "Ruby on Rails (JD only)"),
    ("Junior Application Developer", "Custom CRM development using Salesforce Apex triggers and Lightning components.", "Salesforce (JD only)"),
    ("Web Developer", "Maintain e-commerce website built on WordPress and WooCommerce using PHP and MySQL.", "WordPress (JD only)"),
]


@pytest.mark.parametrize("title,description,stack_name", OUT_OF_SCOPE_TEST_CASES)
def test_adversarial_exhaustive_outofscope_stacks_zero_ai_calls(title, description, stack_name):
    """
    Adversarially verify that every out-of-scope technology stack is intercepted
    and results in EXACTLY ZERO AI calls.
    """
    job = Job(
        title=title,
        company=f"TestCo-{stack_name}",
        location="Pune",
        description=description,
        url=f"http://test-{stack_name.lower().replace(' ', '-')}.com"
    )

    ai_calls = []
    async def mock_ai(prompt):
        ai_calls.append(prompt)
        return json.dumps({"match_score": 10, "missing_skills": ["Java"]}), 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None):
        results = score_jobs([job])

    assert len(ai_calls) == 0, f"LEAK DETECTED for {stack_name}! AI scoring was invoked {len(ai_calls)} times for '{title}'"
    assert len(results) == 0, f"Expected 0 results for out-of-scope {stack_name}, got {len(results)}"


def test_adversarial_target_fresher_roles_not_blocked():
    """
    Adversarially verify that genuine fresher target roles are NOT accidentally dropped
    by the out-of-scope or relevance filters (Recall preservation).
    """
    target_jobs = [
        Job(
            title="Junior QA Automation Engineer",
            company="QACo",
            location="Pune",
            description="Automated testing using Selenium, Python, and pytest. Write test cases and validate REST APIs using Postman. SQL database.",
            url="http://qa1.com"
        ),
        Job(
            title="Java Developer Trainee",
            company="JavaCo",
            location="Pune",
            description="Develop backend services using Java, Spring Boot, and REST APIs. Work with MySQL database and Git.",
            url="http://java1.com"
        ),
        Job(
            title="Associate .NET Developer",
            company="DotNetCo",
            location="Pune",
            description="Build web applications using C#, ASP.NET Core, and SQL Server. Write unit tests and participate in Agile sprints.",
            url="http://dotnet1.com"
        ),
        Job(
            title="Software Engineer - Fresher",
            company="FreshCo",
            location="Pune",
            description="Entry-level software engineer with strong foundations in Python, OOPs concepts, SQL databases, and REST APIs.",
            url="http://fresh1.com"
        ),
        Job(
            title="SDET Trainee",
            company="SDETCo",
            location="Pune",
            description="Software Development Engineer in Test. Test automation with Postman, JUnit, Selenium, and CI/CD pipelines.",
            url="http://sdet1.com"
        ),
    ]

    ai_calls = []
    async def mock_ai(prompt):
        ai_calls.append(prompt)
        return json.dumps({"match_score": 85, "missing_skills": []}), 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None):
        results = score_jobs(target_jobs)

    assert len(ai_calls) == 5, f"False negative rejection! Expected 5 AI calls for valid target roles, got {len(ai_calls)}"
    assert len(results) == 5, f"Expected all 5 valid target roles to be scored and returned, got {len(results)}"


# ==============================================================================
# SECTION 2: Slicing Resilience & 1,500 Token Telemetry Accounting Challenge
# ==============================================================================

def test_adversarial_slicing_resilience_multi_level_and_stepped():
    """
    Adversarially verify that ScoredJobList retains all_scored_jobs across:
    - Normal slicing: [:3]
    - Sub-slicing: [:3][:1]
    - Middle slicing: [2:6]
    - Stepped slicing: [::2]
    """
    raw_jobs = [Job(title=f"Job {i}", company=f"C{i}", location="Pune", description="QA", url=f"http://job{i}.com", score=90 - i) for i in range(10)]
    slist = ScoredJobList(raw_jobs, all_scored_jobs=raw_jobs)

    # Level 1 slice
    s1 = slist[:5]
    assert isinstance(s1, ScoredJobList)
    assert len(s1) == 5
    assert len(s1.all_scored_jobs) == 10

    # Level 2 sub-slice
    s2 = s1[:2]
    assert isinstance(s2, ScoredJobList)
    assert len(s2) == 2
    assert len(s2.all_scored_jobs) == 10

    # Middle slice
    s3 = slist[3:7]
    assert isinstance(s3, ScoredJobList)
    assert len(s3) == 4
    assert len(s3.all_scored_jobs) == 10

    # Stepped slice
    s4 = slist[::2]
    assert isinstance(s4, ScoredJobList)
    assert len(s4) == 5
    assert len(s4.all_scored_jobs) == 10


def test_adversarial_save_pipeline_results_captures_all_1500_tokens_when_sliced():
    """
    Verify save_pipeline_results captures all 1,500 tokens when scored_jobs is sliced
    down to 1 job (shortlisted[:1]), matching the exact flow in run.py / app.py test_mode.
    """
    scored_pool = []
    for i in range(10):
        j = Job(
            title=f"QA Engineer {i}",
            company=f"Company {i}",
            location="Pune",
            description="Selenium",
            url=f"http://job{i}.com",
            score=85 if i < 3 else 45
        )
        j.tokens_used = 150
        j.cost_usd = 0.0001
        j.token_usage = {
            "prompt_tokens": 100,
            "prompt_cache_hit_tokens": 80,
            "prompt_cache_miss_tokens": 20,
            "completion_tokens": 50,
        }
        scored_pool.append(j)

    # score_jobs produces ScoredJobList with 10 all_scored_jobs and top 3 filtered
    scored_jobs = ScoredJobList(scored_pool[:3], all_scored_jobs=scored_pool)

    # Simulation of run.py test_mode:
    top_n = 3
    shortlisted = scored_jobs[:top_n]
    tailor_targets = shortlisted[:1]  # Sliced down to single job

    assert len(tailor_targets) == 1
    assert hasattr(tailor_targets, "all_scored_jobs")
    assert len(tailor_targets.all_scored_jobs) == 10

    captured_payloads = []
    def fake_insert(payload):
        captured_payloads.append(dict(payload))
        m = MagicMock()
        m.execute.return_value.data = [{"id": "run-test-1500"}]
        return m

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.side_effect = fake_insert

    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 10},
        "filter": {"after": 10},
        "score": {"scored": 10, "shortlisted": 1},
        "all_scored_jobs": getattr(scored_jobs, "all_scored_jobs", scored_jobs),
    }

    with patch("src.db.supabase", mock_sb):
        save_pipeline_results(pipeline_state, tailor_targets, ["resume1.pdf"])

    assert len(captured_payloads) >= 1
    payload = captured_payloads[0]

    # Verification of all 1,500 tokens
    assert payload["tokens_used"] == 1500, f"Token leak! Expected 1500 tokens, got {payload['tokens_used']}"
    assert payload["ai_metrics"]["total_tokens"] == 1500
    assert payload["ai_metrics"]["input_tokens"] == 1000
    assert payload["ai_metrics"]["cached_tokens"] == 800
    assert payload["ai_metrics"]["miss_tokens"] == 200
    assert payload["ai_metrics"]["output_tokens"] == 500
    assert payload["ai_metrics"]["jobs_scored_count"] == 10
    assert payload["ai_metrics"]["jobs_shortlisted_count"] == 1
    assert payload["ai_metrics"]["total_cost_usd"] == pytest.approx(0.001, rel=1e-4)


def test_adversarial_db_fallback_to_last_scored_when_plain_list_and_no_pipeline_state():
    """
    Adversarially verify that even if a caller passes a plain python list with no all_scored_jobs
    and empty pipeline_state, save_pipeline_results falls back to get_last_scored_jobs()
    and correctly recovers the full 1,500 tokens.
    """
    scored_pool = []
    for i in range(10):
        j = Job(
            title=f"QA Dev {i}",
            company=f"Company {i}",
            location="Pune",
            description="Selenium",
            url=f"http://job{i}.com",
            score=85 if i < 2 else 40
        )
        j.tokens_used = 150
        j.cost_usd = 0.0001
        j.token_usage = {"prompt_tokens": 100, "completion_tokens": 50}
        scored_pool.append(j)

    plain_list = list(scored_pool[:2])  # Standard Python list (strips all_scored_jobs)

    captured_payloads = []
    def fake_insert(payload):
        captured_payloads.append(dict(payload))
        m = MagicMock()
        m.execute.return_value.data = [{"id": "run-fallback"}]
        return m

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.side_effect = fake_insert

    with patch("src.db.supabase", mock_sb), \
         patch("src.scorer.get_last_scored_jobs", return_value=scored_pool):
        # Passed with empty pipeline_state and plain list:
        save_pipeline_results({}, plain_list, ["pdf1.pdf", "pdf2.pdf"])

    assert len(captured_payloads) >= 1
    payload = captured_payloads[0]
    assert payload["tokens_used"] == 1500, f"Fallback failed! Expected 1500 tokens, got {payload['tokens_used']}"
    assert payload["ai_metrics"]["jobs_scored_count"] == 10


# ==============================================================================
# SECTION 3: Defensive Score Coercion & Threshold Filter Challenge
# ==============================================================================

COERCION_TEST_CASES = [
    # (raw_json_str, expected_score, should_pass_60_threshold)
    ('{"match_score": "85", "missing_skills": []}', 85, True),
    ('{"match_score": "85.7", "missing_skills": []}', 85, True),
    ('{"match_score": "60", "missing_skills": []}', 60, True),
    ('{"match_score": "59.9", "missing_skills": []}', 59, False),
    ('{"match_score": "0", "missing_skills": []}', 0, False),
    ('{"match_score": "NaN", "missing_skills": []}', 0, False),
    ('{"match_score": "N/A", "missing_skills": []}', 0, False),
    ('{"score": "75", "missing_skills": []}', 75, True),
    ('{"missing_skills": []}', 0, False),
    ('{"match_score": null, "missing_skills": []}', 0, False),
]


@pytest.mark.parametrize("raw_json_str,expected_score,should_pass", COERCION_TEST_CASES)
def test_adversarial_score_coercion_and_threshold_resilience(raw_json_str, expected_score, should_pass):
    """
    Adversarially verify that score_jobs handles diverse string representations,
    corrupted score formats, and missing keys without raising TypeError or crashing,
    and applies min_score (60) correctly.
    """
    job = Job(title="QA Trainee", company="Co", location="Pune", description="Selenium and Python testing", url="http://c.com")

    async def mock_ai(p):
        return raw_json_str, 150

    with patch("src.scorer.call_ai_scoring_async", side_effect=mock_ai), \
         patch("src.db.get_cached_jd_score", return_value=None), \
         patch("src.db.save_jd_cache", return_value=None):
        scored = score_jobs([job])

    if should_pass:
        assert len(scored) == 1
        assert scored[0].score == expected_score
    else:
        assert len(scored) == 0, f"Score {expected_score} should have been filtered out (< 60)"


def test_adversarial_cached_score_coercion_string_handling():
    """Verify cached JD score with string score (e.g. '92') is coerced safely without crash."""
    job = Job(title="QA Trainee", company="Co", location="Pune", description="Selenium and Python testing", url="http://cached.com")

    cached_entry = {
        "score": "92",
        "missing_skills": ["Docker"],
        "extracted_requirements": "Testing|||REASON|||Good match",
        "is_testing_role": True,
    }

    with patch("src.db.get_cached_jd_score", return_value=cached_entry):
        scored = score_jobs([job])

    assert len(scored) == 1
    assert scored[0].score == 92
    assert isinstance(scored[0].score, int)


# ==============================================================================
# SECTION 4: TokenUsage Dunder Arithmetic & Relational Invariants
# ==============================================================================

def test_adversarial_token_usage_full_dunder_suite():
    """Verify TokenUsage dunder operators work bidirectionally with int, float, and self."""
    t = TokenUsage({
        "prompt_tokens": 1000,
        "prompt_cache_hit_tokens": 800,
        "prompt_cache_miss_tokens": 200,
        "completion_tokens": 500,
        "total_tokens": 1500,
        "cost_usd": 0.0005,
    })

    # Equality & Inequality
    assert t == 1500
    assert 1500 == t
    assert t != 1000
    assert 1000 != t
    assert not (t == 1000)
    assert not (t != 1500)

    # Relational
    assert t > 1000
    assert t >= 1500
    assert t < 2000
    assert t <= 1500
    assert 1000 < t
    assert 2000 > t

    # Multiplication
    assert t * 2 == 3000
    assert 3 * t == 4500

    # Division
    assert t / 2 == 750.0
    assert t // 2 == 750

    # Addition & Subtraction
    assert t + 500 == 2000
    assert 500 + t == 2000
    assert t - 500 == 1000
    assert 2000 - t == 500

    # Inter-TokenUsage operations
    t_other = TokenUsage({"total_tokens": 500})
    assert t > t_other
    assert t_other < t
    assert t != t_other
    assert t + t_other == 2000
