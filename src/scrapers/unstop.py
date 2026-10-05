"""
Unstop Scraper for AutoApply Pipeline.
Targeted at tech opportunities, fresher roles, and engineering hiring challenges in India.
Direct public REST API: fast, zero proxy needed, structured JSON output.
"""

import re
import uuid
import urllib.request
import urllib.parse
import json
import ssl
from bs4 import BeautifulSoup
import pandas as pd
from src.logger import logger
from src.models import Job

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def clean_html(html_str: str) -> str:
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def scrape_unstop(search_terms: list[str], locations: list[str] = None, job_type: str = "fulltime", max_results_per_query: int = 20, hours_old: int = None) -> list[Job]:
    """
    Scrape Unstop developer jobs or internships via public REST API.
    Strictly verifies approved_date against hours_old cutoff when provided.
    """
    jobs = []
    seen_ids = set()
    opp_type = "jobs" if job_type == "fulltime" else "internships"
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours_old) if hours_old is not None else None
    
    for term in search_terms:
        encoded_term = urllib.parse.quote_plus(term)
        url = f"https://unstop.com/api/public/opportunity/search-result?opportunity={opp_type}&searchTerm={encoded_term}&per_page={max_results_per_query}"
        
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"Unstop API error for query '{term}': {e}")
            continue

        data_field = data.get("data", {})
        postings = data_field.get("data", []) if isinstance(data_field, dict) else []
        
        for p in postings:
            job_id = p.get("id")
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            title = p.get("title", term)
            
            # Parse date_posted strictly from approved_date / start_date (NOT updated_at which changes on system edits)
            raw_date = p.get("approved_date") or p.get("start_date")
            if not raw_date:
                logger.debug(f"Dropping Unstop job without approved date: {title}")
                continue
            try:
                parsed_dt = pd.to_datetime(raw_date, utc=True)
                if pd.isna(parsed_dt) or (cutoff is not None and parsed_dt < cutoff):
                    logger.debug(f"Dropping stale Unstop job ({title}): approved {parsed_dt}, cutoff {cutoff}")
                    continue
                posted_dt = parsed_dt
            except Exception:
                continue

            # Extract company
            org = p.get("organisation")
            if isinstance(org, dict):
                company = org.get("name") or org.get("title") or "Unknown"
            elif isinstance(org, str):
                company = org
            else:
                company = "Unknown"

            # Extract location
            loc_parts = []
            locs = p.get("locations") or []
            if isinstance(locs, list):
                for l in locs:
                    if isinstance(l, dict):
                        city = l.get("city")
                        if city:
                            loc_parts.append(city)
            location_str = ", ".join(loc_parts) if loc_parts else "India"

            # URL
            public_path = p.get("public_url") or ""
            if public_path.startswith("http"):
                job_url = public_path
            elif public_path:
                job_url = f"https://unstop.com/{public_path.lstrip('/')}"
            else:
                job_url = f"https://unstop.com/jobs/{job_id}"

            # Extract full description
            desc_parts = []
            details_html = p.get("details") or ""
            if details_html:
                desc_parts.append(clean_html(details_html))

            job_detail = p.get("jobDetail") or {}
            if isinstance(job_detail, dict):
                reqs = job_detail.get("requirements")
                if reqs:
                    desc_parts.append(clean_html(str(reqs)))
                resps = job_detail.get("responsibilities")
                if resps:
                    desc_parts.append(clean_html(str(resps)))

            skills = p.get("required_skills") or []
            if skills and isinstance(skills, list):
                desc_parts.append(f"Required Skills: {', '.join(str(s) for s in skills)}")

            description = "\n\n".join(desc_parts).strip()
            if not description:
                description = f"{title} at {company} in {location_str}"

            # Check if external URL or native in-platform application
            ext_url = p.get("register_url") or p.get("apply_url") or p.get("website")
            apply_type = "company_site" if ext_url and str(ext_url).strip().startswith("http") else "easy_apply"

            job_obj = Job(
                id=str(uuid.uuid4()),
                title=title,
                company=company,
                location=location_str,
                description=description,
                url=job_url,
                source="unstop",
                job_type=job_type,
                apply_type=apply_type,
                date_posted=posted_dt,
                is_remote="remote" in location_str.lower() or "virtual" in location_str.lower()
            )
            jobs.append(job_obj)

    logger.info(f"✅ Unstop Scraper found {len(jobs)} fresh jobs")
    return jobs
