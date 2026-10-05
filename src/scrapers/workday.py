import json
import logging
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import yaml
from pathlib import Path
import pandas as pd
from src.logger import logger
from src.models import Job
import uuid

# -- HTML stripper -----------------------------------------------------------
class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        elif tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        elif tag in ("p", "div", "li", "tr"):
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[^\S\n]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

def strip_html(html: str) -> str:
    if not html:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


# -- HTTP Helpers -------------------------------------------------------------
def _urlopen(req, timeout=10):
    return urllib.request.urlopen(req, timeout=timeout)

def workday_search(employer: dict, search_text: str, limit: int = 20, offset: int = 0) -> dict:
    limit = min(int(limit), 20)
    url = f"{employer['base_url']}/wday/cxs/{employer['tenant']}/{employer['site_id']}/jobs"
    payload = json.dumps({
        "appliedFacets": {},
        "limit": limit,
        "offset": offset,
        "searchText": search_text,
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    with _urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def workday_detail(employer: dict, external_path: str) -> dict:
    url = f"{employer['base_url']}/wday/cxs/{employer['tenant']}/{employer['site_id']}{external_path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    with _urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


INDIA_LOCATION_KEYWORDS = [
    "india", "pune", "mumbai", "bangalore", "bengaluru", "hyderabad",
    "delhi", "noida", "gurgaon", "gurugram", "chennai", "remote", "hybrid", "location"
]

def _is_viable_location(loc_str: str) -> bool:
    if not loc_str:
        return True  # If location is unknown/empty, fetch detail to be safe
    loc_lower = loc_str.lower()
    return any(k in loc_lower for k in INDIA_LOCATION_KEYWORDS)


def _process_employer(employer_key: str, employer: dict, queries: list[str], max_results_per_query: int = 20, hours_old: int = 48) -> list[Job]:
    jobs_found = []
    seen_paths = set()  # Deduplicate across queries for the same employer
    candidate_postings = []
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours_old) if hours_old is not None else None

    for search_text in queries:
        try:
            data = workday_search(employer, search_text, limit=max_results_per_query, offset=0)
            postings = data.get("jobPostings", [])
            for j in postings:
                external_path = j.get("externalPath", "")
                if not external_path or external_path in seen_paths:
                    continue
                seen_paths.add(external_path)

                loc = j.get("locationsText", "")
                if not _is_viable_location(loc):
                    continue  # Skip clearly overseas roles

                candidate_postings.append(j)

        except urllib.error.HTTPError as e:
            if e.code == 422:
                logger.warning(f"Skipping Workday {employer['name']} for query '{search_text}': HTTP 422")
            elif e.code == 429:
                logger.warning(f"Rate limited by Workday {employer['name']}, stopping queries for this employer")
                break
            else:
                logger.error(f"HTTP {e.code} scraping Workday employer {employer['name']} for query '{search_text}': {e}")
        except Exception as e:
            logger.warning(f"Error searching Workday employer {employer['name']} for query '{search_text}': {e}")

    # Fetch details for viable candidates concurrently
    def fetch_job_detail(j):
        external_path = j.get("externalPath", "")
        loc = j.get("locationsText", "")
        title = j.get("title", "")
        try:
            detail = workday_detail(employer, external_path)
            info = detail.get("jobPostingInfo", {})
            raw_desc = info.get("jobDescription", "")
            description = strip_html(raw_desc)
            apply_url = info.get("externalUrl", "")
            if not apply_url:
                apply_url = f"{employer['base_url']}/{employer['site_id']}{external_path}"
            if not description:
                return None

            # Parse postedOn accurately
            posted_on = str(info.get("postedOn") or "").strip().lower()
            posted_dt = None
            if posted_on:
                if any(k in posted_on for k in ["today", "just", "hour"]):
                    posted_dt = pd.Timestamp.now(tz="UTC")
                elif "yesterday" in posted_on:
                    posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=1)
                else:
                    day_match = re.search(r'(\d+)\+?\s*day', posted_on)
                    week_match = re.search(r'(\d+)\+?\s*week', posted_on)
                    month_match = re.search(r'(\d+)\+?\s*month', posted_on)
                    if day_match:
                        posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=int(day_match.group(1)))
                    elif week_match:
                        posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=int(week_match.group(1)) * 7)
                    elif month_match:
                        posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=int(month_match.group(1)) * 30)

            # Enforce freshness cutoff
            if cutoff is not None:
                if posted_dt is None:
                    logger.debug(f"Dropping Workday job with unverified date '{title}' at {employer['name']}")
                    return None
                if posted_dt < cutoff:
                    logger.debug(f"Dropping stale Workday job '{title}' at {employer['name']} ({posted_on})")
                    return None
            elif posted_dt is None:
                posted_dt = pd.Timestamp.now(tz="UTC")

            return Job(
                id=str(uuid.uuid4()),
                title=title,
                company=employer["name"],
                location=loc or "India",
                description=description,
                url=apply_url,
                source=f"workday-{employer_key}",
                apply_type="company_site",
                date_posted=posted_dt
            )
        except Exception as detail_err:
            logger.debug(f"Skipping job detail for '{title}' at {employer['name']}: {detail_err}")
            return None

    if candidate_postings:
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = pool.map(fetch_job_detail, candidate_postings)
            for jb in results:
                if jb:
                    jobs_found.append(jb)

    return jobs_found


def scrape_workday(queries: list[str], test_mode: bool = False, max_results_per_query: int = 20, hours_old: int = 48) -> list[Job]:
    """Main entry point for Workday discovery with strict freshness cutoff"""
    yaml_path = Path(__file__).parent / "employers.yaml"
    if not yaml_path.exists():
        logger.warning(f"Workday configuration not found at {yaml_path}")
        return []
        
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            employers = data.get("employers", {})
    except Exception as e:
        logger.error(f"Failed to load Workday employers: {e}")
        return []
        
    if not employers:
        return []
        
    employer_keys = list(employers.keys())
    
    if test_mode:
        logger.info("🧪 TEST MODE (Workday): Scraping 1 employer only.")
        employer_keys = employer_keys[:1]
        
    logger.info(f"🌐 Starting Workday Scrape for {len(employer_keys)} employers (≤{hours_old}h)...")
    all_jobs = []
    
    # Run with a 6-worker pool for high throughput
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_process_employer, key, employers[key], queries, max_results_per_query, hours_old): key for key in employer_keys}
        for future in as_completed(futures):
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Workday employer extraction failed: {e}")
                
    logger.info(f"✅ Workday Scraper finished. Found {len(all_jobs)} fresh jobs.")
    return all_jobs
