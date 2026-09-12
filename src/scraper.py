"""
AutoApply Scraper — Unified Pipeline.

Architecture Rules:
- Scrape Jobs from JobSpy, Workday, and JSON-LD.
- Full-Time and Internship jobs processed in separate blocks.
- Pandas Pre-Filter: strict 24-hour freshness, location bounds, anti-senior filter.
- Deduplication by job_url.
- Full raw JD preserved in the Job object.
"""
import time
import random
import re
import pandas as pd
import uuid
import time
from jobspy import scrape_jobs

def _scrape_with_retry(kwargs: dict, max_retries: int = 3, backoff: float = 5.0):
    """Call scrape_jobs with retry on transient failures."""
    for attempt in range(max_retries + 1):
        try:
            return scrape_jobs(**kwargs)
        except Exception as e:
            err = str(e).lower()
            transient = any(k in err for k in ("timeout", "429", "proxy", "connection", "reset", "refused", "error encountered"))
            if transient and attempt < max_retries:
                wait = backoff * (attempt + 1)
                logger.warning(f"Retry {attempt + 1}/{max_retries} for {kwargs.get('site_name')} in {wait}s: {e}")
                time.sleep(wait)
            else:
                logger.error(f"JobSpy Error for {kwargs.get('site_name')}: {e}")
                import pandas as pd
                return pd.DataFrame()

import html
import urllib.parse

from src.logger import logger
from src.models import Job
from src.config_loader import load_config
from src.scrapers.workday import scrape_workday
from src.scrapers.jsonld import scrape_jsonld
from src.scorer import is_relevant_jd, matches_senior_title, requires_3_plus_years


TRACKING_PARAMS = {
    'refid', 'trackingid', 'tracking_id', 'trk', 'trkcampaign',
    'midtoken', 'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid',
    '_ga', '_gl'
}


def normalize_url(url: str) -> str:
    """
    Normalizes a job URL for deduplication and storage:
    - Strips tracking query parameters (utm_*, refId, trackingId, trk, etc.)
    - Removes trailing slashes
    - Preserves functional query parameters like 'jk' on Indeed.
    """
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return url
        # Filter query params
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_pairs = [
            (k, v) for k, v in query_pairs
            if not k.lower().startswith('utm_') and k.lower() not in TRACKING_PARAMS
        ]
        new_query = urllib.parse.urlencode(filtered_pairs)
        path = parsed.path.rstrip('/')
        normalized = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            path,
            parsed.params,
            new_query,
            ''  # strip fragment
        ))
        return normalized
    except Exception:
        return url


def clean_html(desc: str) -> str:
    """
    Clean and strip HTML tags from a job description string while preserving
    newlines, paragraphs, and list formatting.
    """
    if not desc:
        return ""
    desc_str = str(desc)

    # Replace break and list tags with newlines / bullet points
    desc_str = re.sub(r'(?i)<br\s*/?>', '\n', desc_str)
    desc_str = re.sub(r'(?i)<li[^>]*>', '\n- ', desc_str)
    desc_str = re.sub(r'(?i)</?(?:p|div|li|tr|h[1-6]|blockquote|section|article)[^>]*>', '\n', desc_str)

    # Remove remaining HTML tags
    desc_str = re.sub(r'<[^>]+>', '', desc_str)

    # Unescape HTML entities (e.g. &amp;, &lt;, &nbsp;)
    desc_str = html.unescape(desc_str)

    # Normalize horizontal whitespace (spaces, tabs) to single spaces per line
    desc_str = re.sub(r'[^\S\r\n]+', ' ', desc_str)
    # Normalize excessive newlines (keep at most 2 consecutive newlines)
    desc_str = re.sub(r'\n\s*\n\s*\n+', '\n\n', desc_str)

    return desc_str.strip()


LOCATION_ALIASES = {
    "pune": [
        r"\bpune\b",
        r"\bmaharashtra\b",
        r"\bmh\b",
        r"\bin-mh\b",
        r"\bmh,\s*in\b",
    ],
    "mumbai": [
        r"\bmumbai\b",
        r"\bbombay\b",
        r"\bnavi\s+mumbai\b",
        r"\bthane\b",
        r"\bmaharashtra\b",
        r"\bmh\b",
        r"\bin-mh\b",
        r"\bmh,\s*in\b",
    ],
    "bangalore": [
        r"\bbangalore\b",
        r"\bbengaluru\b",
        r"\bkarnataka\b",
        r"\bka\b",
        r"\bin-ka\b",
        r"\bka,\s*in\b",
    ],
    "bengaluru": [
        r"\bbangalore\b",
        r"\bbengaluru\b",
        r"\bkarnataka\b",
        r"\bka\b",
        r"\bin-ka\b",
        r"\bka,\s*in\b",
    ],
    "delhi": [
        r"\bdelhi\b",
        r"\bnew\s+delhi\b",
        r"\bncr\b",
        r"\bnoida\b",
        r"\bgurgaon\b",
        r"\bgurugram\b",
    ],
    "hyderabad": [
        r"\bhyderabad\b",
        r"\btelangana\b",
        r"\bts\b",
    ],
    "chennai": [
        r"\bchennai\b",
        r"\btamil\s*nadu\b",
        r"\btn\b",
    ],
}

REMOTE_PATTERNS = [
    r"\bremote\b",
    r"\bhybrid\b",
    r"\bwork\s+from\s+home\b",
    r"\bwfh\b",
    r"\banywhere\b",
    r"\bpan[- ]?india\b",
]


def build_location_regex(locations: list[str]) -> str:
    """Build a comprehensive regex pattern covering target cities, regional aliases, and remote options."""
    patterns = list(REMOTE_PATTERNS)
    for loc in locations:
        loc_clean = loc.strip().lower()
        if loc_clean in LOCATION_ALIASES:
            patterns.extend(LOCATION_ALIASES[loc_clean])
        else:
            matched = False
            for k, aliases in LOCATION_ALIASES.items():
                if k in loc_clean:
                    patterns.extend(aliases)
                    matched = True
            if not matched:
                patterns.append(r"\b" + re.escape(loc_clean) + r"\b")
    unique_patterns = list(dict.fromkeys(patterns))
    return "|".join(f"(?:{p})" for p in unique_patterns)


def apply_pandas_filter(jobs: list[Job], locations: list[str], callbacks=None, test_mode=False, hours_old: int = None) -> list[Job]:
    """
    Applies recall-first freshness, location regional aliases, anti-senior,
    experience, and robust deduplication filters.
    """
    if not jobs:
        return []

    # Convert list of Job objects to DataFrame for filtering
    data = []
    for j in jobs:
        data.append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "description": j.description,
            "url": j.url,
            "source": j.source,
            "job_type": getattr(j, "job_type", "fulltime"),
            "date_posted": getattr(j, "date_posted", None),
            "is_remote": getattr(j, "is_remote", False)
        })

    combined_df = pd.DataFrame(data)
    before_count = len(combined_df)

    # 1. Drop null/empty descriptions
    combined_df = combined_df.dropna(subset=['description'])
    combined_df = combined_df[combined_df['description'].str.strip().astype(bool)]

    # 2. Freshness Safety Net: respect configured hours_old (default 72h)
    # CRITICAL: Keep jobs with missing/NaN date_posted (do NOT drop them)
    if 'date_posted' in combined_df.columns:
        combined_df['date_posted'] = pd.to_datetime(combined_df['date_posted'], errors='coerce', utc=True)
        if hours_old is None:
            config = load_config()
            hours_old = config.get('search', {}).get('hours_old', 72)
        cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=hours_old)

        # Only drop if date is parseable AND older than cutoff
        stale_mask = combined_df['date_posted'].notna() & (combined_df['date_posted'] < cutoff)

        stale_count = stale_mask.sum()
        if stale_count > 0:
            logger.info(f"   [Stale] Dropped {stale_count} stale jobs (older than {hours_old}h)")
            if callbacks and "on_job_dropped" in callbacks:
                for _, row in combined_df[stale_mask].iterrows():
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), f"Stale (older than {hours_old}h)")
        combined_df = combined_df[~stale_mask]

    # 3. Location Filter: Target cities with comprehensive Indian regional aliases OR Remote/Hybrid
    if 'location' in combined_df.columns and locations:
        location_pattern = build_location_regex(locations)
        is_remote_mask = pd.Series(False, index=combined_df.index)
        if 'is_remote' in combined_df.columns:
            is_remote_mask = combined_df['is_remote'] == True

        loc_mask = combined_df['location'].astype(str).str.contains(location_pattern, case=False, na=False) | is_remote_mask
        dropped_loc = (~loc_mask).sum()
        if dropped_loc > 0:
            logger.info(f"   [Location] Dropped {dropped_loc} jobs with mismatched locations (not in target cities or remote)")
            if callbacks and "on_job_dropped" in callbacks:
                for _, row in combined_df[~loc_mask].iterrows():
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Location mismatch")
        combined_df = combined_df[loc_mask]

    # 4. Anti-Senior Title Filter (with explicit title experience checking)
    if 'title' in combined_df.columns:
        senior_mask = combined_df['title'].apply(matches_senior_title).astype(bool)
        dropped_df = combined_df[senior_mask]
        dropped_senior = len(dropped_df)
        combined_df = combined_df[~senior_mask]
        if dropped_senior > 0:
            logger.info(f"   [Senior] Dropped {dropped_senior} senior-level jobs (title filter)")
            for _, row in dropped_df.iterrows():
                if callbacks and "on_job_dropped" in callbacks:
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Senior title detected")

    # 5. Candidate Experience Filter (0-2 / 1-3 years preserved; 3+ years rejected)
    if 'description' in combined_df.columns:
        exp_mask = combined_df['description'].apply(requires_3_plus_years).astype(bool)
        dropped_exp = exp_mask.sum()
        if dropped_exp > 0:
            logger.info(f"   [Experience] Dropped {dropped_exp} jobs requiring 3+ years of experience")
            if callbacks and "on_job_dropped" in callbacks:
                for _, row in combined_df[exp_mask].iterrows():
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "High experience required")
        combined_df = combined_df[~exp_mask]

    # 6. Robust Deduplication (Job URL + Known Company/Title)
    before_dedup = len(combined_df)

    # 6a. Normalize URLs and deduplicate by normalized URL
    if 'url' in combined_df.columns:
        combined_df['normalized_url'] = combined_df['url'].apply(normalize_url)
        has_url_mask = combined_df['normalized_url'].astype(str).str.strip().astype(bool)
        with_url = combined_df[has_url_mask].drop_duplicates(subset=['normalized_url'], keep='first')
        without_url = combined_df[~has_url_mask]
        combined_df = pd.concat([with_url, without_url], ignore_index=True)

    # 6b. Deduplicate by (clean_title, company) ONLY when company is known
    # Prevents dropping unique jobs with "Unknown" or empty company names
    if 'title' in combined_df.columns and 'company' in combined_df.columns:
        unknown_companies = {'', 'unknown', 'none', 'nan', 'null', 'n/a'}
        is_unknown = (
            combined_df['company'].isna() |
            combined_df['company'].fillna('').astype(str).str.strip().str.lower().isin(unknown_companies)
        )
        is_known_company = ~is_unknown

        known_df = combined_df[is_known_company].copy()
        unknown_df = combined_df[~is_known_company].copy()

        known_df['clean_title_dedup'] = known_df['title'].astype(str).str.strip().str.lower()
        known_df['clean_company_dedup'] = known_df['company'].astype(str).str.strip().str.lower()
        known_deduped = known_df.drop_duplicates(subset=['clean_title_dedup', 'clean_company_dedup'], keep='first')

        combined_df = pd.concat([known_deduped, unknown_df], ignore_index=True)
        combined_df = combined_df.drop(columns=['clean_title_dedup', 'clean_company_dedup', 'normalized_url'], errors='ignore')

    dropped_dedup = before_dedup - len(combined_df)
    if dropped_dedup > 0:
        logger.info(f"   [Duplicate] Dropped {dropped_dedup} duplicate jobs (cross-platform overlap)")

    after_count = len(combined_df)
    logger.info(f"   [Filter] Pre-filter: {before_count} → {after_count} jobs ({before_count - after_count} dropped)")

    # Convert back to Job objects, preserving date_posted and is_remote
    filtered_jobs = []
    for _, row in combined_df.iterrows():
        job = Job(
            id=str(row.get("id")),
            title=str(row.get("title")),
            company=str(row.get("company")),
            location=str(row.get("location")),
            description=str(row.get("description")),
            url=str(row.get("url")),
            source=str(row.get("source")),
            job_type=str(row.get("job_type"))
        )
        job.date_posted = row.get("date_posted")
        job.is_remote = row.get("is_remote", False)
        filtered_jobs.append(job)

    return filtered_jobs


def run_scraper(selected_platforms=None, selected_job_types=None, test_mode=False, callbacks=None, stop_event=None) -> list[Job]:
    """
    Scrapes jobs from all sources, handling Full-Time and Internship blocks separately.
    """
    config = load_config()
    search_cfg = config.get('search', {})

    search_terms = search_cfg.get('search_terms', ['"Java Developer"'])
    locations = search_cfg.get('locations', ["Pune"])
    job_types = selected_job_types if selected_job_types is not None else search_cfg.get('job_types', ["fulltime", "internship"])
    proxies = search_cfg.get('proxies', [])
    hours_old = search_cfg.get('hours_old', 72)

    platforms = selected_platforms if selected_platforms is not None else search_cfg.get('platforms', ["linkedin", "indeed"])
    
    results_wanted_per_loc = 5 if test_mode else search_cfg.get('results_wanted', 20)
    # Scale results_wanted by number of locations because all locations are batched into
    # a single JobSpy call. This preserves the same total coverage as the old
    # per-location calls (results_per_loc × n_locations = effective session limit).
    results_wanted_batched = results_wanted_per_loc * len(locations)
    
    all_raw_jobs = []
    
    # Pre-calculate total cycles across ALL job types for accurate progress tracking
    # Locations are now batched per term (1 call per term, not 1 call per term×location)
    # This prevents the cycle counter from resetting when the second job type starts
    global_cycle_counter = 0
    global_total_cycles = 0
    batched_location = ", ".join(locations)  # e.g. "Pune, Mumbai, Bangalore"
    logger.info(f"📊 Session limit: {results_wanted_per_loc}/loc × {len(locations)} locs = {results_wanted_batched} results per batched call")
    for jt in job_types:
        if stop_event and stop_event.is_set():
            break
        jobspy_plats = [p for p in platforms if p not in ["workday", "jsonld"]]
        if jt == "internship" and "linkedin" in jobspy_plats:
            jobspy_plats.remove("linkedin")
        if jobspy_plats:
            global_total_cycles += len(search_terms) if not test_mode else 1
        if "workday" in platforms:
            global_total_cycles += 1
        if "jsonld" in platforms:
            global_total_cycles += 1
    
    for jt in job_types:
        if stop_event and stop_event.is_set():
            logger.info("🛑 Scraper cancelled by stop_event.")
            break
        logger.info(f"⚡ Processing Job Category: {jt.upper()}")
        
        # 1. JobSpy Module
        jobspy_platforms = [p for p in platforms if p not in ["workday", "jsonld"]]
        if jt == "internship" and "linkedin" in jobspy_platforms:
            jobspy_platforms.remove("linkedin")
            
        if jobspy_platforms:
            # Locations are batched for platforms that support it; others get per-location calls.
            # LinkedIn: supports comma-separated multi-location → 1 call per term (batched)
            # Indeed / others: single-location only → inner loop per location, no inter-loc delay
            MULTI_LOC_PLATFORMS = {"linkedin"}  # Platforms confirmed to support multi-location
            multi_loc_sites = [p for p in jobspy_platforms if p in MULTI_LOC_PLATFORMS]
            per_loc_sites   = [p for p in jobspy_platforms if p not in MULTI_LOC_PLATFORMS]

            combinations = list(search_terms) if not test_mode else [random.choice(search_terms)]
                
            for i, term in enumerate(combinations, 1):
                if stop_event and stop_event.is_set():
                    break
                global_cycle_counter += 1
                cycle_label = f"Cycle {global_cycle_counter}/{global_total_cycles}: JobSpy - {term} ({jt})"
                
                if callbacks and "on_cycle_start" in callbacks:
                    callbacks["on_cycle_start"]({
                        "cycle_label": cycle_label, 
                        "platforms": jobspy_platforms, 
                        "jt": jt, 
                        "term": term, 
                        "loc": batched_location,
                        "current_cycle": global_cycle_counter,
                        "total_cycles": global_total_cycles
                    })
                    
                def do_scrape(site_list, scrape_loc, results_per_call):
                    """Fire one JobSpy call and collect results into all_raw_jobs."""
                    if not site_list: return
                    if stop_event and stop_event.is_set(): return
                    try:
                        df = _scrape_with_retry({
                            "site_name": site_list,
                            "search_term": term,
                            "location": scrape_loc,
                            "job_type": jt,
                            "results_wanted": results_per_call,
                            "hours_old": hours_old,
                            "country_indeed": search_cfg.get('country_indeed', 'India'),
                            "linkedin_fetch_description": True,
                            "proxies": proxies if proxies else None
                        })
                        if not df.empty:
                            for _, row in df.iterrows():
                                if stop_event and stop_event.is_set(): break
                                desc = clean_html(row.get("description", ""))
                                if not desc: continue
                                raw_url = str(row.get("job_url", row.get("url", "")))
                                job = Job(
                                    id=str(uuid.uuid4()),
                                    title=str(row.get("title", "Unknown")),
                                    company=str(row.get("company", "Unknown")),
                                    location=str(row.get("location", "Unknown")),
                                    description=desc,
                                    url=normalize_url(raw_url) if raw_url else "",
                                    source=str(row.get("site", "jobspy")),
                                    job_type=jt
                                )
                                job.date_posted = row.get("date_posted")
                                job.is_remote = row.get("is_remote", False)
                                all_raw_jobs.append(job)
                                if callbacks and "on_job_scraped" in callbacks:
                                    callbacks["on_job_scraped"]({"title": job.title, "company": job.company, "platform": job.source, "cycle": cycle_label})
                    except Exception as e:
                        logger.error(f"   [Error] Error scraping JobSpy {site_list} for '{term}' in '{scrape_loc}': {e}")
                        if callbacks and "on_error" in callbacks:
                            callbacks["on_error"](str(e))

                # ── LinkedIn: one batched call (all locations in one string) ──
                if multi_loc_sites:
                    logger.info(f"   [LinkedIn] | {term} | [{batched_location}] | {results_wanted_batched} results")
                    do_scrape(multi_loc_sites, batched_location, results_wanted_batched)

                # ── Indeed / others: one call per location (no inter-location delay) ──
                if per_loc_sites:
                    for individual_loc in locations:
                        if stop_event and stop_event.is_set(): break
                        logger.info(f"   [{'/'.join(per_loc_sites):10s}] | {term} | {individual_loc} | {results_wanted_per_loc} results")
                        do_scrape(per_loc_sites, individual_loc, results_wanted_per_loc)
                
                if not test_mode:
                    delay = random.uniform(2.0, 5.0)
                    if callbacks and "on_cycle_start" in callbacks:
                        callbacks["on_cycle_start"]({
                            "wait_time": int(delay),
                            "message": f"⏳ Waiting {int(delay)}s before next term..."
                        })
                    if stop_event:
                        if stop_event.wait(delay):
                            break
                    else:
                        time.sleep(delay)
                
        # 2. Workday Module
        if "workday" in platforms:
            cycle_label = f"Workday API ({jt})"
            if callbacks and "on_cycle_start" in callbacks:
                callbacks["on_cycle_start"]({"cycle_label": cycle_label, "platforms": ["workday"], "jt": jt, "term": "All Configured", "loc": "All Configured"})
                
            workday_queries = search_terms
            if jt == "internship":
                workday_queries = [f"{q} intern" for q in search_terms] + ["intern", "internship"]
                
            try:
                wd_jobs = scrape_workday(queries=workday_queries, test_mode=test_mode, max_results_per_query=results_wanted_per_loc)
                for w_job in wd_jobs:
                    w_job.job_type = jt
                    w_job.date_posted = pd.Timestamp.now(tz="UTC") # Workday API may not provide exact date in simple JSON, assume fresh
                    all_raw_jobs.append(w_job)
                    if callbacks and "on_job_scraped" in callbacks:
                        callbacks["on_job_scraped"]({"title": w_job.title, "company": w_job.company, "platform": w_job.source, "cycle": cycle_label})
            except Exception as e:
                logger.error(f"   [Error] Error scraping Workday: {e}")
                if callbacks and "on_error" in callbacks:
                    callbacks["on_error"](str(e))
                    
        # 3. JSON-LD Module
        if "jsonld" in platforms:
            cycle_label = f"JSON-LD ({jt})"
            if callbacks and "on_cycle_start" in callbacks:
                callbacks["on_cycle_start"]({"cycle_label": cycle_label, "platforms": ["jsonld"], "jt": jt, "term": "JSON-LD Search", "loc": "All Configured"})
            try:
                jld_jobs = scrape_jsonld(test_mode=test_mode)
                for j_job in jld_jobs:
                    j_job.job_type = jt
                    j_job.date_posted = pd.Timestamp.now(tz="UTC")
                    all_raw_jobs.append(j_job)
                    if callbacks and "on_job_scraped" in callbacks:
                        callbacks["on_job_scraped"]({"title": j_job.title, "company": j_job.company, "platform": j_job.source, "cycle": cycle_label})
            except Exception as e:
                logger.error(f"   [Error] Error scraping JSON-LD: {e}")
                if callbacks and "on_error" in callbacks:
                    callbacks["on_error"](str(e))

    # Finally, apply the strict Pandas filters
    filtered_jobs = apply_pandas_filter(all_raw_jobs, locations, callbacks=callbacks, test_mode=test_mode, hours_old=hours_old)
    
    stats = {
        "found_initial": len(all_raw_jobs),
        "pandas_dropped": len(all_raw_jobs) - len(filtered_jobs),
        "dedup_dropped": 0, # Included in pandas_dropped
        "reached_scoring": len(filtered_jobs)
    }

    logger.info(f"   [Done] Scraper pipeline finished. Returning {len(filtered_jobs)} viable jobs.")
    return filtered_jobs, stats