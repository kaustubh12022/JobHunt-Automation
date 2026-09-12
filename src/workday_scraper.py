"""
Workday Scraper Interface Wrapper.
Re-exports scrape_workday and helpers from src.scrapers.workday for interface compliance.
"""
from src.scrapers.workday import (
    scrape_workday,
    strip_html,
    workday_search,
    workday_detail,
)

__all__ = [
    "scrape_workday",
    "strip_html",
    "workday_search",
    "workday_detail",
]
