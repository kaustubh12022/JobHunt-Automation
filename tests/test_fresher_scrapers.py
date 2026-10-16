"""
test_fresher_scrapers.py — Automated test suite for multi-platform fresher job scrapers.
Validates:
- Internshala, Unstop, Hirist, Naukri, and Instahyre scraper modules
- Verification that real jobs are returned with title, company, location, URL, description
- Handoff into apply_pandas_filter
"""

import pytest
from src.models import Job
from src.scrapers.internshala import scrape_internshala
from src.scrapers.unstop import scrape_unstop
from src.scrapers.hirist import scrape_hirist
from src.scrapers.naukri import scrape_naukri
from src.scrapers.instahyre import scrape_instahyre
from src.scraper import apply_pandas_filter

def test_unstop_scraper_basic():
    jobs = scrape_unstop(["Java Developer"], max_results_per_query=2)
    assert len(jobs) > 0, "Unstop scraper returned 0 jobs"
    for j in jobs:
        assert isinstance(j, Job)
        assert j.title and j.title != "N/A"
        assert j.company and j.company != "N/A"
        assert j.url.startswith("http")
        assert j.source == "unstop"
        assert len(j.description) > 0

def test_hirist_scraper_basic():
    jobs = scrape_hirist(["Java Developer"], max_results_per_query=2, max_experience_years=5, hours_old=720)
    assert len(jobs) > 0, "Hirist scraper returned 0 jobs"
    for j in jobs:
        assert isinstance(j, Job)
        assert j.title and j.title != "N/A"
        assert j.company and j.company != "N/A"
        assert j.url.startswith("http")
        assert j.source == "hirist"
        assert len(j.description) > 0

def test_internshala_scraper_basic():
    jobs = scrape_internshala(["Java Developer"], locations=["Pune", "India"], max_results_per_query=2, fetch_details=False, hours_old=720)
    assert len(jobs) > 0, "Internshala scraper returned 0 jobs"
    for j in jobs:
        assert isinstance(j, Job)
        assert j.title and j.title != "N/A"
        assert j.company and j.company != "N/A"
        assert j.url.startswith("http")
        assert j.source == "internshala"
        assert len(j.description) > 0

def test_naukri_scraper_basic():
    jobs = scrape_naukri(["Java Developer"], locations=["Pune"], max_results_per_query=2)
    if not jobs:
        pytest.skip("Naukri scraper returned 0 jobs (upstream Jina AI reader blocked or rate-limited)")
    assert len(jobs) > 0, "Naukri scraper returned 0 jobs"
    for j in jobs:
        assert isinstance(j, Job)
        assert j.title and j.title != "N/A"
        assert j.company and j.company != "N/A"
        assert j.url.startswith("http")
        assert j.source == "naukri"
        assert len(j.description) > 0

def test_naukri_markdown_parser_deterministic():
    from src.scrapers.naukri import parse_naukri_markdown
    sample_md = """
## [Junior Java Developer](https://www.naukri.com/job-listings-010126000001)
[Triton Technologies](https://www.naukri.com/triton-technologies-careers-12345)
* 0-1 Yrs Pune
* Java, Spring Boot, MySQL, REST APIs
We are hiring freshers with strong Java fundamentals and basic Spring Boot experience.
Posted 2 hours ago
"""
    jobs = parse_naukri_markdown(sample_md, default_loc="Pune", hours_old=720, max_experience_years=2)
    assert len(jobs) > 0
    j = jobs[0]
    assert j.title == "Junior Java Developer"
    assert "Triton" in j.company
    assert j.source == "naukri"
    assert j.min_experience == 0

def test_foundit_scraper_basic():
    from src.scrapers.foundit import scrape_foundit
    jobs = scrape_foundit(["Software Engineer"], locations=["Pune", "Bangalore"], max_results_per_query=2, hours_old=168)
    assert len(jobs) > 0, "Foundit scraper returned 0 jobs"
    for j in jobs:
        assert isinstance(j, Job)
        assert j.title and j.title != "N/A"
        assert j.company and j.company != "N/A"
        assert j.url.startswith("http")
        assert j.source == "foundit"
        assert len(j.description) > 0

def test_fresher_jobs_pass_filter():
    jobs = scrape_unstop(["Java Developer"], max_results_per_query=2)
    filtered = apply_pandas_filter(jobs, locations=["Pune", "Mumbai", "Bangalore", "Noida", "India"], hours_old=720)
    assert len(filtered) > 0, "All jobs were incorrectly dropped by filter"
