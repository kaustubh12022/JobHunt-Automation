"""
Naukri Scraper for AutoApply Pipeline.
Targeted at India's #1 job portal for software engineering and fresher tech roles.
Uses Jina AI reader bridge to reliably bypass Akamai anti-bot protection.
Zero proxies needed, fast, deterministic markdown parsing.
"""

import re
import uuid
import urllib.request
import urllib.parse
import ssl
import pandas as pd
from src.logger import logger
from src.models import Job
from src.config_loader import load_config

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/plain, text/markdown, */*"
}

def clean_term_for_slug(term: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9\s]', '', term).strip().lower()
    return re.sub(r'\s+', '-', slug)

def parse_experience_from_url(url: str) -> tuple[int, int] | None:
    """Extract (min_exp, max_exp) from Naukri URL slug like '6-to-11-years'."""
    m = re.search(r'(\d+)-to-(\d+)-years?', url)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None

def parse_naukri_markdown(md_text: str, default_loc: str = "India", job_type: str = "fulltime", hours_old: int = 48, max_experience_years: int = 0) -> list[Job]:
    """
    Parse Jina-rendered Naukri markdown into structured Job objects.
    Enforces freshness cutoff at parser level so stale jobs never enter pipeline.
    """
    jobs = []
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours_old) if hours_old is not None else None

    # Split by job listing headers
    # Format: ## [Title](URL "Title")
    pattern = re.compile(
        r'##\s+\[(?P<title>[^\]]+)\]\((?P<url>https://www\.naukri\.com/job-listings-[^\s\)]+)(?:\s+"[^"]*")?\)'
        r'(?P<body>.*?)(?=(?:##\s+\[|$))',
        re.DOTALL
    )

    for m in pattern.finditer(md_text):
        title = m.group("title").strip()
        raw_url = m.group("url").strip()
        body = m.group("body")

        # Extract Company: first markdown link after title, e.g. [Infosys](https://www.naukri.com/infosys...)
        company = "Unknown"
        comp_match = re.search(r'\[(?P<comp>[^\]]+)\]\(https://www\.naukri\.com/[^/]+-careers-[^\)]+\)', body)
        if comp_match:
            company = comp_match.group("comp").strip()
        else:
            # Fallback company check
            comp_match2 = re.search(r'\[(?P<comp>[A-Za-z0-9\s\.\,&-]+)\]\(https://www\.naukri\.com/[^\)]+\)', body)
            if comp_match2:
                company = comp_match2.group("comp").strip()

        # Extract experience & location
        # Format usually: "0-1 Yrs Pune, Mumbai" or "0-2 Yrs Bengaluru"
        exp_loc_match = re.search(r'(?P<exp>\d+(?:-\d+)?\s+Yrs?)\s+(?P<loc>[^\n\r]+)', body)
        location = default_loc
        
        min_exp, max_exp = None, None
        
        if exp_loc_match:
            loc_candidate = exp_loc_match.group("loc").strip()
            # Clean ratings or garbage if attached
            loc_candidate = re.sub(r'\[.*?\]\(.*?\)', '', loc_candidate).strip()
            if loc_candidate:
                location = loc_candidate
            
            # Extract min_exp and max_exp from body text
            exp_str = exp_loc_match.group("exp")
            exp_nums = re.findall(r'\d+', exp_str)
            if len(exp_nums) >= 2:
                min_exp, max_exp = int(exp_nums[0]), int(exp_nums[1])
            elif len(exp_nums) == 1:
                min_exp = int(exp_nums[0])
                
        # URL parsing takes precedence as it's more reliable
        url_exp = parse_experience_from_url(raw_url)
        if url_exp:
            min_exp, max_exp = url_exp
            
        # Hard filter at scraper level for non-fresher jobs
        if min_exp is not None and min_exp > max_experience_years:
            logger.debug(f"Dropping non-fresher Naukri job ({title}): min_exp={min_exp}")
            continue

        # Extract description snippet & bulleted skills
        # Extract bullet skills: * Skill
        skills = re.findall(r'\*\s+([^\n\r]+)', body)
        skill_str = ", ".join(s.strip() for s in skills if s.strip())

        # Clean snippet
        snippet_lines = []
        for line in body.split("\n"):
            line_str = line.strip()
            if line_str and not line_str.startswith("![") and not line_str.startswith("[") and not line_str.startswith("*") and "Reviews" not in line_str and "Yrs" not in line_str and "save" not in line_str.lower() and "ago" not in line_str.lower():
                snippet_lines.append(line_str)
        snippet = " ".join(snippet_lines[:3])

        desc_parts = [
            f"{title} at {company} ({location})",
            snippet,
            f"Key Skills: {skill_str}" if skill_str else ""
        ]
        description = "\n\n".join(p for p in desc_parts if p).strip()

        # Relative date parsing from body
        posted_dt = None
        hour_match = re.search(r'(?i)\b(\d+)\+?\s*hour[s]?\s+ago\b', body)
        just_now_match = re.search(r'(?i)\b(?:just\s+now|today|few\s+hours?\s+ago)\b', body)
        date_match = re.search(r'(?i)\b(\d+)\+?\s*day[s]?\s+ago\b', body)
        week_match = re.search(r'(?i)\b(\d+)\+?\s*week[s]?\s+ago\b', body)
        month_match = re.search(r'(?i)\b(\d+)\+?\s*month[s]?\s+ago\b', body)

        if hour_match:
            hours = int(hour_match.group(1))
            posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
        elif just_now_match:
            posted_dt = pd.Timestamp.now(tz="UTC")
        elif date_match:
            days = int(date_match.group(1))
            posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
        elif week_match:
            weeks = int(week_match.group(1))
            posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=weeks * 7)
        elif month_match:
            months = int(month_match.group(1))
            posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=months * 30)

        # Drop stale jobs immediately right at parse level (Zero Stale Jobs Invariant)
        if cutoff is not None:
            if posted_dt is not None and posted_dt < cutoff:
                logger.debug(f"Dropping stale Naukri job ({title}): posted {posted_dt}, older than {hours_old}h")
                continue
            if posted_dt is None:
                logger.debug(f"Dropping Naukri job with unverified date ({title})")
                continue
        elif posted_dt is None:
            posted_dt = pd.Timestamp.now(tz="UTC")

        # Check apply_type
        apply_type = "company_site" if any(k in body.lower() for k in ["company site", "apply on company", "external site", "redirect"]) else "easy_apply"

        clean_url = raw_url.split('?')[0].strip()

        job_obj = Job(
            id=str(uuid.uuid4()),
            title=title,
            company=company,
            location=location,
            description=description,
            url=clean_url,
            source="naukri",
            job_type=job_type,
            apply_type=apply_type,
            date_posted=posted_dt,
            is_remote="remote" in location.lower() or "hybrid" in location.lower(),
            min_experience=min_exp,
            max_experience=max_exp
        )
        jobs.append(job_obj)

    return jobs

def scrape_naukri(search_terms: list[str], locations: list[str] = None, job_type: str = "fulltime", max_results_per_query: int = 15, hours_old: int = 48) -> list[Job]:
    """
    Scrape Naukri fresher developer jobs using Jina AI Reader bridge.
    Applies &jobAge query parameter to ensure upstream search only fetches fresh jobs.
    """
    config = load_config()
    max_experience_years = config.get('search', {}).get('max_experience_years', 0)
    
    jobs = []
    seen_urls = set()
    locations = locations or ["Pune"]

    # Map hours_old to Naukri's native jobAge query parameter
    if hours_old <= 24:
        job_age_param = 1
    elif hours_old <= 48:
        job_age_param = 2
    elif hours_old <= 72:
        job_age_param = 3
    else:
        job_age_param = max(1, hours_old // 24)

    for term in search_terms:
        term_slug = clean_term_for_slug(term)
        for loc in locations:
            loc_slug = clean_term_for_slug(loc)
            target_url = f"https://www.naukri.com/{term_slug}-jobs-in-{loc_slug}?experience=0&jobAge={job_age_param}"
            jina_url = f"https://r.jina.ai/{target_url}"
            logger.debug(f"Naukri via Jina: {target_url}")

            md_text = ""
            try:
                req = urllib.request.Request(jina_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                    md_text = resp.read().decode('utf-8', errors='ignore')
            except Exception as e:
                logger.warning(f"Failed to fetch Naukri page via Jina ({target_url}): {e}")

            parsed_jobs = parse_naukri_markdown(md_text, default_loc=loc, job_type=job_type, hours_old=hours_old, max_experience_years=max_experience_years) if md_text else []
            
            # Fallback 1: Try without ?experience=0 if 0 jobs found
            if not parsed_jobs:
                fallback_url = f"https://www.naukri.com/{term_slug}-jobs-in-{loc_slug}?jobAge={job_age_param}"
                try:
                    req = urllib.request.Request(f"https://r.jina.ai/{fallback_url}", headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                        fb_text = resp.read().decode('utf-8', errors='ignore')
                    parsed_jobs = parse_naukri_markdown(fb_text, default_loc=loc, job_type=job_type, hours_old=hours_old, max_experience_years=max_experience_years)
                except Exception:
                    pass

            # Fallback 2: Try national/broader keyword if still 0
            if not parsed_jobs:
                fallback_url2 = f"https://www.naukri.com/{term_slug}-jobs?experience=0&jobAge={job_age_param}"
                try:
                    req = urllib.request.Request(f"https://r.jina.ai/{fallback_url2}", headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                        fb_text2 = resp.read().decode('utf-8', errors='ignore')
                    parsed_jobs = parse_naukri_markdown(fb_text2, default_loc=loc, job_type=job_type, hours_old=hours_old, max_experience_years=max_experience_years)
                except Exception:
                    pass

            # Fallback 3: National broad search with jobAge
            if not parsed_jobs:
                fallback_url3 = f"https://www.naukri.com/{term_slug}-jobs?jobAge={job_age_param}"
                try:
                    req = urllib.request.Request(f"https://r.jina.ai/{fallback_url3}", headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                        fb_text3 = resp.read().decode('utf-8', errors='ignore')
                    parsed_jobs = parse_naukri_markdown(fb_text3, default_loc=loc, job_type=job_type, hours_old=hours_old, max_experience_years=max_experience_years)
                except Exception:
                    pass

            for j in parsed_jobs[:max_results_per_query]:
                if j.url in seen_urls:
                    continue
                seen_urls.add(j.url)
                jobs.append(j)

    logger.info(f"✅ Naukri Scraper found {len(jobs)} fresh jobs")
    return jobs
