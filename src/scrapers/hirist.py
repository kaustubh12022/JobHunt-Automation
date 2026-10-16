"""
Hirist Scraper for AutoApply Pipeline.
Targeted at tech developers, software engineers, and technology startups in India.
Direct REST API: fast, resilient, zero proxy needed, structured JSON output.
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
from src.config_loader import load_config

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.hirist.tech/"
}

def clean_html(html_str: str) -> str:
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def fetch_hirist_detail(job_id: int or str) -> str:
    """Fetch full job description for a job ID from Hirist detail API."""
    if not job_id:
        return ""
    try:
        url = f"https://gladiator.hirist.tech/job/detail?jobcode={job_id}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            intro = data.get('data', {}).get('introText') or ""
            return clean_html(intro)
    except Exception as e:
        logger.debug(f"Hirist detail fetch failed for {job_id}: {e}")
    return ""

def scrape_hirist(search_terms: list[str], locations: list[str] = None, job_type: str = "fulltime", max_results_per_query: int = 15, fetch_details: bool = True, hours_old: int = 48, max_experience_years: int = None) -> list[Job]:
    """
    Scrape Hirist tech developer jobs via Gladiator REST API.
    Enforces native 'posting' freshness parameter and in-scraper timestamp cutoff.
    """
    config = load_config()
    if max_experience_years is None:
        max_experience_years = config.get('search', {}).get('max_experience_years', 0)
    
    jobs = []
    seen_ids = set()
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours_old) if hours_old is not None else None

    # Map hours_old to Hirist native 'posting' API parameter
    # 1 = Last 24 hours, 2 = Last 48 hours, 3 = Last 72 hours, 7 = Last 7 days
    if hours_old is not None:
        if hours_old <= 24:
            posting_param = 1
        elif hours_old <= 48:
            posting_param = 2
        elif hours_old <= 72:
            posting_param = 3
        else:
            posting_param = 7
    else:
        posting_param = 2

    for term in search_terms:
        encoded_term = urllib.parse.quote_plus(term)
        url = f"https://gladiator.hirist.tech/job/search?query={encoded_term}&page=0&posting={posting_param}&size={max_results_per_query}"

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"Hirist API error for query '{term}': {e}")
            continue

        raw_jobs = data.get("data", [])
        if not raw_jobs:
            continue

        for r in raw_jobs:
            job_id = r.get("id")
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            title = r.get("title", term)
            
            # Company
            company_data = r.get("companyData") or {}
            company = company_data.get("companyName") or r.get("createdByAlias") or "Unknown"

            # Locations
            loc_list = r.get("location") or []
            loc_names = [l.get("name") for l in loc_list if isinstance(l, dict) and l.get("name")]
            location_str = ", ".join(loc_names) if loc_names else "India"

            # URL
            job_url = r.get("jobDetailUrl") or f"https://www.hirist.tech/j/{job_id}"

            # Experience check (favor fresher / junior 0-3 years)
            min_exp = r.get("min", 0)
            max_exp = r.get("max", 0)
            
            # Hard filter at scraper level for non-fresher jobs
            if min_exp is not None and min_exp > max_experience_years:
                logger.debug(f"Dropping non-fresher Hirist job ({title}): min_exp={min_exp}")
                continue

            # Date parsing from createdTimeMs epoch
            created_ms = r.get("createdTimeMs") or r.get("createdTime")
            if not created_ms:
                logger.debug(f"Dropping Hirist job without timestamp: {title}")
                continue
            try:
                posted_dt = pd.to_datetime(created_ms, unit="ms", utc=True)
                if pd.isna(posted_dt) or (cutoff is not None and posted_dt < cutoff):
                    logger.debug(f"Dropping stale Hirist job ({title}): posted {posted_dt}, cutoff {cutoff}")
                    continue
            except Exception:
                continue

            # Description
            description = ""
            if fetch_details:
                description = fetch_hirist_detail(job_id)
            if not description:
                tags = [t.get("name") for t in (r.get("tags") or []) if isinstance(t, dict)]
                tag_str = ", ".join(tags) if tags else ""
                description = f"{title} at {company} in {location_str}. Experience: {min_exp}-{max_exp} yrs. Skills: {tag_str}"

            # Check if external URL or native 1-click apply
            ext_apply = r.get("applyUrl")
            apply_type = "company_site" if ext_apply and str(ext_apply).strip().startswith("http") else "easy_apply"

            job_obj = Job(
                id=str(uuid.uuid4()),
                title=title,
                company=company,
                location=location_str,
                description=description,
                url=job_url,
                source="hirist",
                job_type=job_type,
                apply_type=apply_type,
                date_posted=posted_dt,
                is_remote=bool(r.get("workFromHome", False)) or "remote" in location_str.lower(),
                min_experience=min_exp,
                max_experience=max_exp
            )
            jobs.append(job_obj)

    logger.info(f"✅ Hirist Scraper found {len(jobs)} fresh jobs")
    return jobs
