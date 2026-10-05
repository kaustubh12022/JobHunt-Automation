"""
Instahyre Scraper for AutoApply Pipeline.
Targeted at premium tech companies, fast-growing startups, and high-paying developer roles in India.
Uses stealth Playwright browser session to interface directly with Instahyre's internal API.
Zero proxies needed, fast, resilient, and structured JSON output.
"""

import re
import uuid
import urllib.parse
from playwright.sync_api import sync_playwright
import pandas as pd
from bs4 import BeautifulSoup
from src.logger import logger
from src.models import Job

def clean_html(html_str: str) -> str:
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def scrape_instahyre(search_terms: list[str], locations: list[str] = None, job_type: str = "fulltime", max_results_per_query: int = 15, hours_old: int = 48) -> list[Job]:
    """
    Scrape Instahyre jobs using Playwright authenticated context session to access job_search API.
    """
    jobs = []
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            logger.debug("Initializing Instahyre session...")
            page.goto("https://www.instahyre.com/search-jobs/", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning(f"Failed to initialize Instahyre session: {e}")
            browser.close()
            return []

        for term in search_terms:
            # Map location query
            loc_param = ""
            if locations:
                loc_param = "&jobLocations=" + urllib.parse.quote_plus(",".join(locations))

            query_url = f"https://www.instahyre.com/api/v1/job_search?skills={urllib.parse.quote_plus(term)}{loc_param}&offset=0"
            logger.debug(f"Instahyre API query: {query_url}")

            try:
                res = page.evaluate(f"""async () => {{
                    try {{
                        const resp = await fetch('{query_url}');
                        if (!resp.ok) return {{ status: resp.status, objects: [] }};
                        const data = await resp.json();
                        return {{ status: 200, objects: data.objects || [] }};
                    }} catch (e) {{
                        return {{ status: 500, error: e.toString(), objects: [] }};
                    }}
                }}""")
            except Exception as e:
                logger.warning(f"Error evaluating Instahyre fetch for '{term}': {e}")
                continue

            objects = res.get("objects", [])
            for obj in objects[:max_results_per_query]:
                job_id = obj.get("id")
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = obj.get("candidate_title") or obj.get("title") or term
                employer = obj.get("employer") or {}
                company = employer.get("company_name", "Unknown")
                company_note = employer.get("instahyre_note", "")

                loc_val = obj.get("locations") or "India"
                if isinstance(loc_val, list):
                    location_str = ", ".join(loc_val)
                else:
                    location_str = str(loc_val)

                public_url = obj.get("public_url") or f"https://www.instahyre.com/job-{job_id}"
                keywords = obj.get("keywords") or []
                keyword_str = ", ".join(keywords) if keywords else ""

                # Construct description
                desc_parts = [
                    f"{title} at {company} ({location_str})",
                    company_note,
                    f"Required Skills / Keywords: {keyword_str}" if keyword_str else ""
                ]
                description = "\n\n".join(p for p in desc_parts if p).strip()

                # Parse date if available in payload
                raw_date = obj.get("reviewed_at") or obj.get("created_at")
                posted_dt = None
                if raw_date:
                    try:
                        parsed_dt = pd.to_datetime(raw_date, utc=True)
                        if pd.notna(parsed_dt):
                            posted_dt = parsed_dt
                    except Exception:
                        pass

                job_obj = Job(
                    id=str(uuid.uuid4()),
                    title=title,
                    company=company,
                    location=location_str,
                    description=description,
                    url=public_url,
                    source="instahyre",
                    job_type=job_type,
                    apply_type="easy_apply",
                    date_posted=posted_dt,
                    is_remote="remote" in location_str.lower() or "work from home" in location_str.lower()
                )
                jobs.append(job_obj)

        browser.close()

    logger.info(f"✅ Instahyre Scraper found {len(jobs)} jobs")
    return jobs
