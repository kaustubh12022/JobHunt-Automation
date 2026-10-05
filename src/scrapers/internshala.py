"""
Internshala Scraper for AutoApply Pipeline.
Targeted at college freshers, software internships, and graduate developer roles in India.
Zero proxies needed, fast direct HTTP with resilient parsing.
"""

import re
import uuid
import urllib.request
import urllib.parse
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def clean_term_for_slug(term: str) -> str:
    """Convert search term to Internshala URL slug."""
    slug = re.sub(r'[^a-zA-Z0-9\s]', '', term).strip().lower()
    return re.sub(r'\s+', '-', slug)

def fetch_internshala_detail(job_url: str) -> str:
    """Fetch full job description from Internshala detail page."""
    if not job_url:
        return ""
    try:
        req = urllib.request.Request(job_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8, context=_SSL_CTX) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        desc_el = soup.select_one(".text-container, .internship_details, #job_description")
        if desc_el:
            return desc_el.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.debug(f"Internshala detail fetch failed for {job_url}: {e}")
    return ""

def scrape_internshala(search_terms: list[str], locations: list[str], job_type: str = "fulltime", max_results_per_query: int = 15, fetch_details: bool = True, hours_old: int = 48) -> list[Job]:
    """
    Scrape Internshala jobs or internships with strict freshness verification.
    """
    jobs = []
    seen_urls = set()
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours_old) if hours_old is not None else None
    
    base_prefix = "jobs" if job_type == "fulltime" else "internships"
    
    for term in search_terms:
        term_slug = clean_term_for_slug(term)
        for loc in locations:
            loc_slug = clean_term_for_slug(loc)
            url = f"https://internshala.com/{base_prefix}/{term_slug}-jobs-in-{loc_slug}/" if job_type == "fulltime" else f"https://internshala.com/{base_prefix}/{term_slug}-internship-in-{loc_slug}/"
            
            logger.debug(f"Internshala checking: {url}")
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
            except urllib.error.HTTPError as he:
                if he.code == 404:
                    # Fallback to broader keyword URL
                    fallback_url = f"https://internshala.com/{base_prefix}/keywords-{term_slug}/"
                    try:
                        req = urllib.request.Request(fallback_url, headers=HEADERS)
                        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                            html = resp.read().decode('utf-8', errors='ignore')
                    except Exception:
                        continue
                else:
                    logger.warning(f"Internshala HTTP error {he.code} for {url}")
                    continue
            except Exception as e:
                logger.warning(f"Internshala error for {url}: {e}")
                continue

            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select(".individual_internship")
            
            for c in cards[:max_results_per_query]:
                link_el = c.select_one("a.job-title-href, a[href*='/job/detail/'], a[href*='/internship/detail/'], a.view_detail_button")
                if not link_el or 'href' not in link_el.attrs:
                    continue
                raw_href = link_el['href']
                job_url = f"https://internshala.com{raw_href}" if raw_href.startswith('/') else raw_href
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                title_el = c.select_one(".job-internship-name, .profile, h3")
                comp_el = c.select_one(".company-name, .company_name")
                loc_el = c.select_one(".row-1-item.locations, .locations a, #location_names")

                title = title_el.get_text(strip=True) if title_el else term
                company = comp_el.get_text(strip=True) if comp_el else "Unknown"
                # Strip 'Actively hiring' banner
                company = re.sub(r'Actively hiring.*', '', company).strip()
                location = loc_el.get_text(strip=True) if loc_el else loc

                # Parse relative posted date from tags and card text
                posted_dt = None
                status_nodes = c.select(".status-success, .status-info, .status-inactive, .status_container, .status, .posted-by")
                card_text = " ".join([el.get_text(strip=True) for el in status_nodes] + [c.get_text(separator=" ", strip=True)])

                hour_match = re.search(r'(?i)\b(?:just\s+now|few\s+hours?\s+ago|today|\d+\s*hour[s]?\s+ago)\b', card_text)
                day_match = re.search(r'(?i)\b(\d+)\+?\s*day[s]?\s+ago\b', card_text)
                week_match = re.search(r'(?i)\b(\d+)\+?\s*week[s]?\s+ago\b', card_text)
                month_match = re.search(r'(?i)\b(\d+)\+?\s*month[s]?\s+ago\b', card_text)

                if hour_match:
                    posted_dt = pd.Timestamp.now(tz="UTC")
                elif day_match:
                    days = int(day_match.group(1))
                    posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
                elif week_match:
                    weeks = int(week_match.group(1))
                    posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=weeks * 7)
                elif month_match:
                    months = int(month_match.group(1))
                    posted_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=months * 30)
                else:
                    # Check 10-digit UNIX epoch at the end of the URL
                    epoch_match = re.search(r'(\d{10})$', raw_href.strip())
                    if epoch_match:
                        try:
                            epoch_val = int(epoch_match.group(1))
                            if 1700000000 <= epoch_val <= 2000000000:
                                posted_dt = pd.to_datetime(epoch_val, unit="s", utc=True)
                        except Exception:
                            pass

                # Strictly enforce freshness cutoff
                if cutoff is not None:
                    if posted_dt is None:
                        logger.debug(f"Dropping Internshala job with unverified date: {title}")
                        continue
                    if posted_dt < cutoff:
                        logger.debug(f"Dropping stale Internshala job ({title}): posted {posted_dt}, cutoff {cutoff}")
                        continue
                elif posted_dt is None:
                    posted_dt = pd.Timestamp.now(tz="UTC")

                # Description
                description = ""
                if fetch_details:
                    description = fetch_internshala_detail(job_url)
                if not description:
                    # Fallback to snippet from card
                    other_details = [div.get_text(strip=True) for div in c.select(".item_body")]
                    description = f"{title} at {company} in {location}. Details: {' | '.join(other_details)}"

                # Clean and normalize job_url
                clean_url = job_url.split('?')[0].strip()

                job_obj = Job(
                    id=str(uuid.uuid4()),
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    url=clean_url,
                    source="internshala",
                    job_type=job_type,
                    apply_type="easy_apply",
                    date_posted=posted_dt,
                    is_remote="remote" in location.lower() or "home" in location.lower()
                )
                jobs.append(job_obj)

    logger.info(f"✅ Internshala Scraper found {len(jobs)} fresh jobs")
    return jobs
