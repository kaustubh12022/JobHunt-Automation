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

from src.logger import logger
from src.models import Job
from src.config_loader import load_config
from src.scrapers.workday import scrape_workday
from src.scrapers.jsonld import scrape_jsonld


def clean_html(desc: str) -> str:
    """Strip HTML tags from a description string."""
    if not desc:
        return ""
    desc = re.sub(r'<[^>]+>', '', str(desc))
    desc = re.sub(r'\s+', ' ', desc)
    return desc.strip()


def apply_pandas_filter(jobs: list[Job], locations: list[str], callbacks=None, test_mode=False) -> list[Job]:
    """Applies the strict 24-hour freshness, location, and anti-senior filters."""
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
            "date_posted": getattr(j, "date_posted", pd.Timestamp.now(tz="UTC")), # Default to now for api scrapers if missing
            "is_remote": getattr(j, "is_remote", False)
        })
    
    combined_df = pd.DataFrame(data)
    before_count = len(combined_df)
    
    # 1. Drop null/empty descriptions
    combined_df = combined_df.dropna(subset=['description'])
    combined_df = combined_df[combined_df['description'].str.strip().astype(bool)]

    # 2. Recency Safety Net (Hard filter: STRICTLY 24h only)
    if 'date_posted' in combined_df.columns:
        combined_df['date_posted'] = pd.to_datetime(combined_df['date_posted'], errors='coerce', utc=True)
        no_date_mask = combined_df['date_posted'].isna()
        combined_df = combined_df[~no_date_mask]
        
        # Hard 24-hour cutoff
        cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=24)
        stale_mask = combined_df['date_posted'] < cutoff
        
        stale_count = stale_mask.sum()
        if stale_count > 0:
            logger.info(f"   [Stale] Dropped {stale_count} stale jobs (older than 24h)")
            if callbacks and "on_job_dropped" in callbacks:
                for _, row in combined_df[stale_mask].iterrows():
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Stale (older than 24h)")
        combined_df = combined_df[~stale_mask]

    # 3. Location Filter (Target cities OR Remote)
    if 'location' in combined_df.columns and locations:
        location_pattern = '|'.join(re.escape(loc) for loc in locations)
        is_remote_mask = pd.Series(False, index=combined_df.index)
        if 'is_remote' in combined_df.columns:
            is_remote_mask = combined_df['is_remote'] == True
            
        loc_mask = combined_df['location'].str.contains(location_pattern, case=False, na=False) | is_remote_mask
        dropped_loc = (~loc_mask).sum()
        if dropped_loc > 0:
            logger.info(f"   [Location] Dropped {dropped_loc} jobs with mismatched locations (not in target cities or remote)")
            if callbacks and "on_job_dropped" in callbacks:
                for _, row in combined_df[~loc_mask].iterrows():
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Location mismatch")
        combined_df = combined_df[loc_mask]

    # 4. Anti-Senior Title Filter & Experience Filter
    # NOTE: This runs in BOTH test mode and production. Filtering junk jobs in test
    # mode is essential to avoid wasting AI tokens.
    if 'title' in combined_df.columns:
        senior_mask = combined_df['title'].str.contains(
            r'senior|sr[\.,\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert',
            case=False, na=False, regex=True
        )
        dropped_df = combined_df[senior_mask]
        dropped_senior = len(dropped_df)
        combined_df = combined_df[~senior_mask]
        if dropped_senior > 0:
            logger.info(f"   [Senior] Dropped {dropped_senior} senior-level jobs (title filter)")
            for _, row in dropped_df.iterrows():
                if callbacks and "on_job_dropped" in callbacks:
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Senior title detected")

    if 'description' in combined_df.columns:
        def requires_3_plus_years(desc):
            """
            Returns True if the JD requires 3+ years of CANDIDATE experience.

            Key safeguards:
            - Strips sentences that mention "our team has X years", "work with engineers 
              who have X years", etc. — these are team/company experience, not candidate requirements.
            - Checks UPPER bound of ranges: "2-5 years" -> upper=5 -> FILTER.
            - Handles "3 or more years", "more than 3 years".
            - Handles "(2-5 years)" and "2 - 5 years" (spaced ranges).
            - Never filters purely on 0-2 year ranges or non-candidate context.
            """
            if not isinstance(desc, str): return False
            desc_lower = desc.lower().replace('\\', '')

            # ── Step 1: Remove sentences about COMPANY/TEAM experience ──
            # These phrases indicate the experience belongs to others, not the candidate.
            # We strip the whole sentence before running numeric checks.
            third_party_prefixes = (
                r'(?:our|the)\s+team\s+(?:has|have|with|of)',
                r'(?:work|working)\s+(?:with|alongside|beside|among)',
                r'(?:join|joining)\s+(?:a\s+)?team\s+(?:of|with)',
                r'(?:founded|established|started|operating|running)\s+(?:in|since|for)',
                r'(?:we\s+have|company\s+has|firm\s+has)\s+(?:over|more\s+than|been)',
                r'(?:our\s+company|our\s+firm|our\s+organisation)\s+(?:has|have)',
                r'colleagues?\s+(?:with|who\s+have)',
                r'mentors?\s+(?:with|who\s+have)',
                r'mentorship\s+from',
                r'(?:learn|learning)\s+from',
                r'(?:combined|collective|total)\s+experience',
                r'(?:history|heritage|industry)\s+(?:of|spanning)',
                # Only strip "team of engineers with X years" - NOT bare "developer with X"
                r'(?:team|group|pool)\s+of\s+(?:engineers?|developers?|professionals?)\s+with',
                r'(?:senior\s+)?engineers?\s+(?:who\s+have|with\s+over)',
            )
            # Split into sentences and strip those matching third-party patterns
            sentences = re.split(r'(?<=[.!?\n])\s*', desc_lower)
            candidate_sentences = []
            for sent in sentences:
                is_third_party = any(re.search(pat, sent) for pat in third_party_prefixes)
                if not is_third_party:
                    candidate_sentences.append(sent)
            
            candidate_text = ' '.join(candidate_sentences)

            # ── Step 2: Apply numeric checks on candidate_text only ──

            # Pattern 1: Range (X-Y years) -> check UPPER bound
            # Catches: "2-5 years", "2 to 5 years", "2 - 5 years", "(2-5 years)"
            range_pattern = r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?\.?)'
            for m in re.finditer(range_pattern, candidate_text):
                lo, hi = int(m.group(1)), int(m.group(2))
                if hi >= 3:
                    return True

            # Pattern 2: Single number + "years", with optional "or more"/"+"
            # Catches: "3 years", "5+ years", "3 or more years", "more than 3 years"
            single_pattern = r'(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?)'
            for m in re.finditer(single_pattern, candidate_text):
                num = int(m.group(1))
                if 3 <= num <= 25:
                    return True

            # Pattern 3: "minimum/at least X years"
            min_pattern = r'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?\.?)?'
            for m in re.finditer(min_pattern, candidate_text):
                num = int(m.group(1))
                if 3 <= num <= 25:
                    return True

            # Pattern 4: "X yrs" shorthand
            yrs_pattern = r'\b(\d+)\s+yrs?\b'
            for m in re.finditer(yrs_pattern, candidate_text):
                num = int(m.group(1))
                if 3 <= num <= 25:
                    return True

            # Pattern 5: Word-based ("three to five years")
            words_to_num = {
                'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
                'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
            }
            words_list = '|'.join(words_to_num.keys())
            word_pattern = fr'\b({words_list})\s*(?:to|-|or more)?\s*(?:\w+\s+)?years?\b'
            for m in re.finditer(word_pattern, candidate_text):
                if words_to_num.get(m.group(1), 0) >= 3:
                    return True

            return False

        # Filter experience for ALL jobs (both fulltime and internship)
        # Internships requiring 3+ years of experience are mislabeled or senior roles and should be dropped.
        exp_mask = combined_df['description'].apply(requires_3_plus_years).astype(bool)
        
        dropped_exp = exp_mask.sum()
        if dropped_exp > 0:
            logger.info(f"   [Experience] Dropped {dropped_exp} jobs requiring 3+ years of experience")
            if callbacks and "on_job_dropped" in callbacks:
                for _, row in combined_df[exp_mask].iterrows():
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "High experience required")
        combined_df = combined_df[~exp_mask]

    # 5. Deduplicate (Job URL + Fallback to Title/Company)
    before_dedup = len(combined_df)
    url_col = 'url'
    if url_col in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=[url_col], keep='first')
        
    if 'title' in combined_df.columns and 'company' in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=['title', 'company'], keep='first')

    dropped_dedup = before_dedup - len(combined_df)
    if dropped_dedup > 0:
        logger.info(f"   [Duplicate] Dropped {dropped_dedup} duplicate jobs (cross-platform overlap)")

    after_count = len(combined_df)
    logger.info(f"   [Filter] Pre-filter: {before_count} → {after_count} jobs ({before_count - after_count} dropped)")
    
    # Convert back to Job objects
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
        # Preserve original date_posted if needed, but not part of model right now
        filtered_jobs.append(job)
        
    return filtered_jobs


def run_scraper(selected_platforms=None, selected_job_types=None, test_mode=False, callbacks=None) -> list[Job]:
    """
    Scrapes jobs from all sources, handling Full-Time and Internship blocks separately.
    """
    config = load_config()
    search_cfg = config.get('search', {})

    search_terms = search_cfg.get('search_terms', ['"Java Developer"'])
    locations = search_cfg.get('locations', ["Pune"])
    job_types = selected_job_types if selected_job_types is not None else search_cfg.get('job_types', ["fulltime", "internship"])
    proxies = search_cfg.get('proxies', [])
    hours_old = search_cfg.get('hours_old', 24)

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
        jobspy_plats = [p for p in platforms if p not in ["workday", "jsonld"]]
        if jt == "internship" and "linkedin" in jobspy_plats:
            jobspy_plats = [p for p in jobspy_plats if p != "linkedin"]
        if jobspy_plats:
            combos = len(search_terms)  # One call per term (locations batched)
            if test_mode:
                combos = 1
            global_total_cycles += combos
    
    for jt in job_types:
        logger.info(f"   [Start] Starting collection block for Job Type: {jt.upper()}")
        
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
                                desc = clean_html(row.get("description", ""))
                                if not desc: continue
                                job = Job(
                                    id=str(uuid.uuid4()),
                                    title=str(row.get("title", "Unknown")),
                                    company=str(row.get("company", "Unknown")),
                                    location=str(row.get("location", "Unknown")),
                                    description=desc,
                                    url=str(row.get("job_url", row.get("url", ""))),
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
                        logger.info(f"   [{'/'.join(per_loc_sites):10s}] | {term} | {individual_loc} | {results_wanted_per_loc} results")
                        do_scrape(per_loc_sites, individual_loc, results_wanted_per_loc)
                
                if not test_mode:
                    delay = random.uniform(2.0, 5.0)
                    if callbacks and "on_cycle_start" in callbacks:
                        callbacks["on_cycle_start"]({
                            "wait_time": int(delay),
                            "message": f"⏳ Waiting {int(delay)}s before next term..."
                        })
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
                wd_jobs = scrape_workday(queries=workday_queries, test_mode=test_mode, max_results_per_query=results_wanted)
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
    filtered_jobs = apply_pandas_filter(all_raw_jobs, locations, callbacks=callbacks, test_mode=test_mode)
    
    stats = {
        "found_initial": len(all_raw_jobs),
        "pandas_dropped": len(all_raw_jobs) - len(filtered_jobs),
        "dedup_dropped": 0, # Included in pandas_dropped
        "reached_scoring": len(filtered_jobs)
    }

    logger.info(f"   [Done] Scraper pipeline finished. Returning {len(filtered_jobs)} viable jobs.")
    return filtered_jobs, stats