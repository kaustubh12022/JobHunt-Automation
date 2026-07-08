import pytest
from unittest.mock import patch, MagicMock
from src.models import Job

# --- Mock Data ---
@pytest.fixture
def mock_jobs():
    return [
        Job(title="Java Dev", company="Tech Corp", location="Remote", description="We need a Java Backend Developer with Spring and SQL skills.", url="http://example.com/1"),
        Job(title="Accountant", company="Finance LLC", location="NYC", description="Looking for a CPA with 5 years of audit experience.", url="http://example.com/2"),
        Job(title="QA Tester", company="QA Inc", location="SF", description="Looking for an Automation Tester with Selenium and Python.", url="http://example.com/3")
    ]

# --- 1. Scorer Component Tests ---
@patch('src.scorer.call_ai_scoring_async')
def test_scorer_relevance_filtering(mock_ai, mock_jobs):
    from src.scorer import is_relevant_jd, score_jobs
    
    # Test relevance logic directly
    assert is_relevant_jd(mock_jobs[0].description) == True # Java, SQL
    assert is_relevant_jd(mock_jobs[1].description) == False # None
    assert is_relevant_jd(mock_jobs[2].description) == True # Automation, Selenium, Python
    
    # AI response mock
    async def mock_async_response(*args, **kwargs):
        return '{"match_score": 85, "missing_skills": [], "extracted_requirements": "Java, Spring", "is_testing_role": false}', 150
        
    mock_ai.side_effect = mock_async_response
    
    # The Accountant job should be skipped entirely
    scored = score_jobs(mock_jobs, test_mode=True)
    assert len(scored) == 2 # Only 2 jobs passed relevance check
    assert scored[0].score == 85

# --- 2. Boilerplate Stripper Tests ---
def test_strip_boilerplate():
    from src.scorer import strip_boilerplate
    raw_jd = "About Us: We are a fast growing startup.\n\nRequired Skills: Java, Spring Boot.\n\nBenefits: 401k, Health Insurance.\n\nEEO Statement: We are an equal opportunity employer."
    stripped = strip_boilerplate(raw_jd)
    
    assert "Required Skills: Java, Spring Boot." in stripped
    assert "About Us" not in stripped
    assert "Benefits" not in stripped
    assert "EEO Statement" not in stripped

# --- 3. Date Util Tests ---
def test_human_date_str():
    from src.config_loader import get_human_date_str
    from datetime import datetime
    
    date_str = get_human_date_str()
    expected = datetime.now().strftime('%Y-%m-%d')
    assert date_str == expected
