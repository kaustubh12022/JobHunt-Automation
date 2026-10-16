"""
Foundit (Monster India) Scraper for AutoApply Pipeline.
Targeted at tech developer and software engineering roles in India.
Direct REST API with resilient parsing and optional detail fetching.
Zero proxies needed, structured JSON output.
"""

import re
import uuid
import urllib.request
import urllib.parse
import json
import ssl
import html
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
    "Referer": "https://www.foundit.in/",
    "x-site-context": "monster_india"
}

DETAIL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://www.foundit.in/",
    "x-site-context": "monster_india"
}


def clean_html(desc: str) -> str:
    """Clean and strip HTML tags from a string while preserving readable structure."""
    if not desc:
        return ""
    desc_str = re.sub(r'(?i)<br\s*/?>', '\n', desc)
    desc_str = re.sub(r'(?i)<li[^>]*>', '\n- ', desc_str)
    desc_str = re.sub(r'(?i)</?(?:p|div|li|tr|h[1-6]|blockquote|section|article)[^>]*>', '\n', desc_str)
    desc_str = re.sub(r'<[^>]+>', '', desc_str)
    desc_str = html.unescape(desc_str)
    desc_str = re.sub(r'[^\S\r\n]+', ' ', desc_str)
    desc_str = re.sub(r'\n\s*\n\s*\n+', '\n\n', desc_str)
    return desc_str.strip()


def fetch_foundit_detail(job_id: str) -> str:
    """Fetch full job description from Foundit seeker detail page."""
    if not job_id:
        return ""
    try:
        url = f"https://www.foundit.in/seeker/job-details?id={job_id}"
        req = urllib.request.Request(url, headers=DETAIL_HEADERS)
        with urllib.request.urlopen(req, timeout=6, context=_SSL_CTX) as resp:
            page = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(page, 'html.parser')
        for s in soup.find_all('script', type='application/ld+json'):
            if s.string and '"description"' in s.string:
                try:
                    data = json.loads(s.string)
                    raw_desc = data.get('description', '')
                    if raw_desc:
                        return clean_html(raw_desc)
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Foundit detail fetch failed for {job_id}: {e}")
    return ""


def parse_relative_posted_time(posted_str: str) -> pd.Timestamp:
    """Parse relative time string (e.g. '10 minutes ago', '2 hours ago', '1 day ago')."""
    if not posted_str:
        return None
    s = str(posted_str).lower().strip()
    now = pd.Timestamp.now(tz="UTC")
    if "just now" in s or "minute" in s or "today" in s:
        return now
    m_hour = re.search(r'(\d+)\s+hour', s)
    if m_hour:
        return now - pd.Timedelta(hours=int(m_hour.group(1)))
    if "an hour ago" in s:
        return now - pd.Timedelta(hours=1)
    m_day = re.search(r'(\d+)\s+day', s)
    if m_day:
        return now - pd.Timedelta(days=int(m_day.group(1)))
    m_week = re.search(r'(\d+)\s+week', s)
    if m_week:
        return now - pd.Timedelta(days=int(m_week.group(1)) * 7)
    m_month = re.search(r'(\d+)\s+month', s)
    if m_month:
        return now - pd.Timedelta(days=int(m_month.group(1)) * 30)
    return None


def scrape_foundit(
    search_terms: list[str],
    locations: list[str] = None,
    job_type: str = "fulltime",
    max_results_per_query: int = 15,
    fetch_details: bool = True,
    hours_old: int = 48
) -> list[Job]:
    """
    Scrape Foundit (Monster India) jobs using the middleware/jobsearch API.
    Sorts by freshness (sort=2) and filters stale jobs.
    """
    config = load_config()
    max_experience_years = config.get('search', {}).get('max_experience_years', 0)
    
    jobs = []
    seen_ids = set()
    locations = locations or ["Pune"]
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours_old) if hours_old is not None else None

    for term in search_terms:
        for loc in locations:
            query_enc = urllib.parse.quote_plus(term)
            loc_enc = urllib.parse.quote_plus(loc)
            # sort=2 is Freshness on Foundit
            url = f"https://www.foundit.in/middleware/jobsearch?query={query_enc}&locations={loc_enc}&limit={max_results_per_query}&sort=2"

            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                    payload = json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"Foundit search failed for '{term}' in '{loc}': {e}")
                continue

            raw_jobs = payload.get("jobSearchResponse", {}).get("data", [])
            for rj in raw_jobs:
                job_id = str(rj.get("id") or rj.get("jobId") or "")
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = str(rj.get("title") or "Unknown").strip()
                company = str(rj.get("companyName") or "Unknown").strip()
                job_loc = str(rj.get("locations") or loc).strip()
                
                min_exp = rj.get("minimumExperience", {}).get("years", 0)
                max_exp = rj.get("maximumExperience", {}).get("years", 0)
                
                # Hard filter at scraper level for non-fresher jobs
                if min_exp is not None and min_exp > max_experience_years:
                    logger.debug(f"Dropping non-fresher Foundit job ({title}): min_exp={min_exp}")
                    continue

                # Parse post date
                posted_dt = None
                created_at = rj.get("createdAt") or rj.get("freshness")
                if created_at and isinstance(created_at, (int, float)):
                    try:
                        posted_dt = pd.to_datetime(created_at, unit="ms", utc=True)
                    except Exception:
                        posted_dt = None

                if posted_dt is None:
                    posted_dt = parse_relative_posted_time(rj.get("postedBy"))

                if cutoff is not None:
                    if posted_dt is not None and posted_dt < cutoff:
                        logger.debug(f"Dropping stale Foundit job ({title} at {company}): posted {posted_dt}")
                        continue
                    if posted_dt is None and hours_old <= 48:
                        # If date cannot be determined and fresh window required, skip
                        continue
                elif posted_dt is None:
                    posted_dt = pd.Timestamp.now(tz="UTC")

                # URL
                apply_url = rj.get("applyUrl")
                jd_url = rj.get("jdUrl") or rj.get("seoJdUrl") or f"/job/{job_id}"
                final_url = apply_url if (apply_url and apply_url.startswith("http")) else f"https://www.foundit.in{jd_url}"

                # Description
                description = ""
                if fetch_details:
                    description = fetch_foundit_detail(job_id)

                skills = rj.get("skills", "")
                exp_summary = f"{min_exp}-{max_exp} years" if max_exp else f"{min_exp}+ years"

                if not description:
                    desc_parts = [
                        f"{title} at {company} ({job_loc})",
                        f"Experience Required: {exp_summary}",
                        f"Required Skills: {skills}" if skills else "",
                        f"Role Overview: {title} position in {job_loc} seeking technical proficiencies in {skills}." if skills else ""
                    ]
                    description = "\n\n".join(p for p in desc_parts if p).strip()
                elif skills and skills not in description:
                    description = f"{description}\n\nKey Skills: {skills}"

                # Determine apply_type
                is_quick = bool(rj.get("quickApplyJob") or rj.get("quickJob"))
                apply_type = "easy_apply" if is_quick else "company_site"

                is_remote = "remote" in job_loc.lower() or "hybrid" in job_loc.lower()

                job = Job(
                    id=str(uuid.uuid4()),
                    title=title,
                    company=company,
                    location=job_loc,
                    description=description,
                    url=final_url,
                    source="foundit",
                    job_type=job_type,
                    apply_type=apply_type,
                    date_posted=posted_dt,
                    is_remote=is_remote,
                    min_experience=min_exp,
                    max_experience=max_exp
                )
                jobs.append(job)

    logger.info(f"   [Foundit] Discovered {len(jobs)} jobs across queries.")
    return jobs
