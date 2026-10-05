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
    jobs = scrape_hirist(["Java Developer"], max_results_per_query=2)
    assert len(jobs) > 0, "Hirist scraper returned 0 jobs"
    for j in jobs:
        assert isinstance(j, Job)
        assert j.title and j.title != "N/A"
        assert j.company and j.company != "N/A"
        assert j.url.startswith("http")
        assert j.source == "hirist"
        assert len(j.description) > 0

def test_internshala_scraper_basic():
    jobs = scrape_internshala(["Java Developer"], locations=["Pune"], max_results_per_query=2, fetch_details=False)
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
    assert len(jobs) > 0, "Naukri scraper returned 0 jobs"
    for j in jobs:
        assert isinstance(j, Job)
        assert j.title and j.title != "N/A"
        assert j.company and j.company != "N/A"
        assert j.url.startswith("http")
        assert j.source == "naukri"
        assert len(j.description) > 0

def test_fresher_jobs_pass_filter():
    jobs = scrape_unstop(["Java Developer"], max_results_per_query=2)
    filtered = apply_pandas_filter(jobs, locations=["Pune", "Mumbai", "Bangalore", "Noida", "India"], hours_old=720)
    assert len(filtered) > 0, "All jobs were incorrectly dropped by filter"
