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
            logger.info(f"   🕐 Dropped {stale_count} stale jobs (older than 24h)")
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
            logger.info(f"   📍 Dropped {dropped_loc} jobs with mismatched locations (not in target cities or remote)")
            if callbacks and "on_job_dropped" in callbacks:
                for _, row in combined_df[~loc_mask].iterrows():
                    callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Location mismatch")
        combined_df = combined_df[loc_mask]

    # 4. Anti-Senior Title Filter & Experience Filter
    if not test_mode:
        if 'title' in combined_df.columns:
            senior_mask = combined_df['title'].str.contains(r'senior|sr[\.\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert', case=False, na=False, regex=True)
            dropped_df = combined_df[senior_mask]
            dropped_senior = len(dropped_df)
            combined_df = combined_df[~senior_mask]
            if dropped_senior > 0:
                logger.info(f"   🚫 Dropped {dropped_senior} senior-level jobs (title filter)")
                for _, row in dropped_df.iterrows():
                    if callbacks and "on_job_dropped" in callbacks:
                        callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Senior title detected")
    
        if 'description' in combined_df.columns:
            def requires_3_plus_years(desc):
                if not isinstance(desc, str): return False
                desc_lower = desc.lower()
                digit_pattern = r'\b(\d+)\s*(?:\+|to|-|and)?\s*(?:\d+)?\s*(?:years?|yrs?)'
                for m in re.findall(digit_pattern, desc_lower):
                    try:
                        if 3 <= int(m) <= 25:
                            return True
                    except: pass
                words = ['three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']
                word_pattern = fr'\b({"|".join(words)})\s*(?:\+|to|-|and)?\s*(?:\w+)?\s*(?:years?|yrs?)'
                if re.search(word_pattern, desc_lower):
                    return True
                return False
                
            # Filter experience only for fulltime jobs, bypass for internships
            fulltime_mask = combined_df['job_type'] == 'fulltime'
            exp_mask = pd.Series(False, index=combined_df.index)
            exp_mask[fulltime_mask] = combined_df.loc[fulltime_mask, 'description'].apply(requires_3_plus_years)
            
            dropped_exp = exp_mask.sum()
            if dropped_exp > 0:
                logger.info(f"   🚫 Dropped {dropped_exp} fulltime jobs requiring 3+ years of experience")
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
        logger.info(f"   🔄 Dropped {dropped_dedup} duplicate jobs (cross-platform overlap)")

    after_count = len(combined_df)
    logger.info(f"🧹 Pre-filter: {before_count} → {after_count} jobs ({before_count - after_count} dropped)")
    
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
    job_types = selected_job_types if selected_job_types else search_cfg.get('job_types', ["fulltime", "internship"])
    proxies = search_cfg.get('proxies', [])
    hours_old = search_cfg.get('hours_old', 24)

    platforms = selected_platforms if selected_platforms else search_cfg.get('platforms', ["linkedin", "indeed"])
    
    results_wanted = 5 if test_mode else search_cfg.get('results_wanted', 20)
    
    all_raw_jobs = []
    
    for jt in job_types:
        logger.info(f"🚀 Starting collection block for Job Type: {jt.upper()}")
        
        # 1. JobSpy Module
        jobspy_platforms = [p for p in platforms if p not in ["workday", "jsonld"]]
        if jt == "internship" and "linkedin" in jobspy_platforms:
            jobspy_platforms.remove("linkedin")
            
        combinations = [(term, loc) for term in search_terms for loc in locations]
        if test_mode:
            random.shuffle(combinations)
            combinations = combinations[:1]
            
        for term, loc in combinations:
            cycle_label = f"JobSpy: {term} in {loc} ({jt})"
            
            if callbacks and "on_cycle_start" in callbacks:
                callbacks["on_cycle_start"]({"cycle_label": cycle_label, "platforms": jobspy_platforms, "jt": jt, "term": term, "loc": loc})
                
            # Pass all platforms directly to do_scrape
            jobspy_sites = [p for p in jobspy_platforms]
            
            def do_scrape(site_list, scrape_loc):
                if not site_list: return
                try:
                    df = _scrape_with_retry({
                        "site_name": site_list,
                        "search_term": term,
                        "location": scrape_loc,
                        "job_type": jt,
                        "results_wanted": results_wanted,
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
                            # Attach date_posted for filtering
                            job.date_posted = row.get("date_posted")
                            job.is_remote = row.get("is_remote", False)
                            all_raw_jobs.append(job)
                            
                            if callbacks and "on_job_scraped" in callbacks:
                                callbacks["on_job_scraped"]({"title": job.title, "company": job.company, "platform": job.source, "cycle": cycle_label})
                except Exception as e:
                    logger.error(f"❌ Error scraping JobSpy {site_list} for '{term}': {e}")
                    if callbacks and "on_error" in callbacks:
                        callbacks["on_error"](str(e))
                        
            # Run all JobSpy platforms together
            do_scrape(jobspy_sites, loc)
            
            if not test_mode:
                time.sleep(random.uniform(5.0, 12.0))
                
        # 2. Workday Module
        if not selected_platforms or "workday" in selected_platforms:
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
                logger.error(f"❌ Error scraping Workday: {e}")
                if callbacks and "on_error" in callbacks:
                    callbacks["on_error"](str(e))
                    
        # 3. JSON-LD Module
        if not selected_platforms or "jsonld" in selected_platforms:
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
                logger.error(f"❌ Error scraping JSON-LD: {e}")
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

    logger.info(f"✅ Scraper pipeline finished. Returning {len(filtered_jobs)} viable jobs.")
    return filtered_jobs, stats