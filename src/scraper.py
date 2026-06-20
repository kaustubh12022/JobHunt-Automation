"""
AutoApply Scraper — Combinatorial Matrix + Pandas Pre-Filter Layer.

Architecture Rules:
- Boolean search queries for entry-level targeting
- Full page pulls (results_wanted=20 per combo)
- Anti-ban delays: time.sleep(random.uniform(5, 12))
- Pandas Pre-Filter: drop senior titles, null descriptions, misaligned locations
- Deduplication by job_url
- Full raw JD preserved in the Job object (never truncated)
"""
import time
import random
import re
import pandas as pd
from jobspy import scrape_jobs
from src.logger import logger
from src.models import Job
from src.config_loader import load_config


# ── Regex for senior-level title filtering is embedded in the run_scraper directly ──


def clean_html(desc: str) -> str:
    """Strip HTML tags from a description string."""
    if not desc:
        return ""
    desc = re.sub(r'<[^>]+>', '', str(desc))
    desc = re.sub(r'\s+', ' ', desc)
    return desc.strip()


def run_scraper(selected_platforms=None, test_mode=False) -> list[Job]:
    """
    Scrapes jobs using the Combinatorial Matrix strategy.
    
    Production: Runs all (search_term × location × job_type) combos.
    Test Mode:  Runs 1 combo with 5 results max.
    """
    config = load_config()
    search_cfg = config.get('search', {})

    search_terms = search_cfg.get('search_terms', ['"Java Developer" AND (Intern OR Fresher)'])
    locations = search_cfg.get('locations', ["Pune"])
    job_types = search_cfg.get('job_types', ["fulltime", "internship"])
    proxies = search_cfg.get('proxies', [])

    platforms = selected_platforms if selected_platforms else search_cfg.get('platforms', ["linkedin", "indeed"])

    # Build the combinatorial matrix
    combinations = [
        (term, loc, jt)
        for term in search_terms
        for loc in locations
        for jt in job_types
    ]

    if test_mode:
        logger.info("🧪 TEST MODE: Scraping up to 5 combinations with 20 results each (max 100)")
        combinations = combinations[:5]
        results_wanted = 20
    else:
        results_wanted = search_cfg.get('results_wanted', 20)

    total_combos = len(combinations)
    all_dfs = []

    platform_totals = {}
    for idx, (term, loc, jt) in enumerate(combinations):
        logger.info(f"[{idx+1}/{total_combos}] 🔍 Scraping '{term}' in '{loc}' (type={jt}) from {', '.join(platforms)}...")
        
        # Skip linkedin for internships
        effective_platforms = platforms.copy()
        if jt == "internship" and "linkedin" in effective_platforms:
            effective_platforms.remove("linkedin")
            
        if not effective_platforms:
            logger.info("   ℹ️ No valid platforms for this combination. Skipping.")
            continue

        try:
            scrape_kwargs = dict(
                site_name=effective_platforms,
                search_term=term,
                location=loc,
                job_type=jt,
                results_wanted=results_wanted,
                hours_old=search_cfg.get('hours_old', 24),
                country_indeed=search_cfg.get('country_indeed', 'India'),
                linkedin_fetch_description=True,
            )
            if proxies:
                scrape_kwargs['proxies'] = proxies

            jobs_df = scrape_jobs(**scrape_kwargs)

            if not jobs_df.empty:
                for platform in effective_platforms:
                    count = len(jobs_df[jobs_df['site'] == platform])
                    if count > 0:
                        logger.info(f"   ✅ {platform.capitalize()}: {count} jobs found")
                        platform_totals[platform] = platform_totals.get(platform, 0) + count
                all_dfs.append(jobs_df)
            else:
                logger.info("   ℹ️ No jobs found for this combination.")

        except Exception as e:
            logger.error(f"   ❌ Error scraping combo '{term}' + '{loc}': {e}")

        # Anti-ban delay (skip after last combo)
        if idx < total_combos - 1:
            delay = random.uniform(5.0, 12.0)
            logger.info(f"⏳ Waiting {delay:.1f}s before next search...")
            time.sleep(delay)

    if not all_dfs:
        logger.warning("⚠️ No jobs found matching your criteria.")
        return [], {}

    for p in platforms:
        total = platform_totals.get(p, 0)
        if total == 0:
            logger.warning(f"⚠️ {p.capitalize()} returned 0 jobs across all combos — possible IP block or site issue")
        else:
            logger.info(f"   📊 {p.capitalize()}: {total} total raw jobs")

    # ── Merge all DataFrames ──
    combined_df = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"📊 Raw jobs scraped (before filtering): {len(combined_df)}")

    # ══════════════════════════════════════════════
    # PANDAS PRE-FILTER LAYER (Zero-Token Cost)
    # ══════════════════════════════════════════════
    before_count = len(combined_df)

    # 1. Drop null/empty descriptions
    combined_df = combined_df.dropna(subset=['description'])
    combined_df = combined_df[combined_df['description'].str.strip().astype(bool)]

    # 2. Recency Safety Net (Hard filter > 24h)
    if 'date_posted' in combined_df.columns:
        combined_df['date_posted'] = pd.to_datetime(combined_df['date_posted'], errors='coerce')
        cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=search_cfg.get('hours_old', 24))
        # Ensure timezone info matches
        if combined_df['date_posted'].dt.tz is None:
            combined_df['date_posted'] = combined_df['date_posted'].dt.tz_localize('UTC')
        stale_mask = combined_df['date_posted'] < cutoff
        stale_count = stale_mask.sum()
        if stale_count > 0:
            logger.info(f"   🕐 Dropped {stale_count} stale jobs (older than {search_cfg.get('hours_old', 24)}h)")
        combined_df = combined_df[~stale_mask | combined_df['date_posted'].isna()]

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
        combined_df = combined_df[loc_mask]

    # 4. Anti-Senior Title Filter
    if 'title' in combined_df.columns:
        senior_mask = combined_df['title'].str.contains(r'senior|sr[\.\s]|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert', case=False, na=False, regex=True)
        dropped_df = combined_df[senior_mask]
        dropped_senior = len(dropped_df)
        combined_df = combined_df[~senior_mask]
        if dropped_senior > 0:
            logger.info(f"   🚫 Dropped {dropped_senior} senior-level jobs (title filter)")
            for title in dropped_df['title']:
                logger.info(f"      - Dropped title: {title}")

    # 4.5 Experience Level Filter (Zero-Token Rule)
    if 'description' in combined_df.columns:
        def requires_3_plus_years(desc):
            if not isinstance(desc, str): return False
            desc_lower = desc.lower()
            
            # Catch digit-based experience: "3+ years", "3-5 yrs", "3 to 5 years", "3+ yrs"
            digit_pattern = r'\b(\d+)\s*(?:\+|to|-|and)?\s*(?:\d+)?\s*(?:years?|yrs?)'
            for m in re.findall(digit_pattern, desc_lower):
                try:
                    if 3 <= int(m) <= 25:
                        return True
                except: pass
                
            # Catch word-based experience: "three years", "five+ yrs"
            words = ['three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']
            word_pattern = fr'\b({"|".join(words)})\s*(?:\+|to|-|and)?\s*(?:\w+)?\s*(?:years?|yrs?)'
            if re.search(word_pattern, desc_lower):
                return True
                
            return False
            
        exp_mask = combined_df['description'].apply(requires_3_plus_years)
        dropped_exp = exp_mask.sum()
        if dropped_exp > 0:
            logger.info(f"   🚫 Dropped {dropped_exp} jobs requiring 3+ years of experience")
        combined_df = combined_df[~exp_mask]

    # 5. Deduplicate (Job URL + Fallback to Title/Company)
    before_dedup = len(combined_df)
    url_col = 'job_url' if 'job_url' in combined_df.columns else 'url'
    if url_col in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=[url_col], keep='first')
        
    if 'title' in combined_df.columns and 'company' in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=['title', 'company'], keep='first')

    dropped_dedup = before_dedup - len(combined_df)
    if dropped_dedup > 0:
        logger.info(f"   🔄 Dropped {dropped_dedup} duplicate jobs (cross-platform overlap)")

    after_count = len(combined_df)
    logger.info(f"🧹 Pre-filter: {before_count} → {after_count} jobs ({before_count - after_count} dropped)")


    # ── Convert to Job models ──
    final_jobs = []
    for _, row in combined_df.iterrows():
        desc = clean_html(row.get("description", ""))
        if not desc:
            continue

        job = Job(
            title=str(row.get("title", "Unknown Title")),
            company=str(row.get("company", "Unknown Company")),
            location=str(row.get("location", "Unknown Location")),
            description=desc,  # Full raw JD preserved (never truncated)
            url=str(row.get("job_url", row.get("url", ""))),
            source=str(row.get("site", "Unknown"))
        )
        final_jobs.append(job)

    if test_mode:
        final_jobs = final_jobs[:20]

    stats = {
        "found_initial": before_count,
        "pandas_dropped": before_count - after_count - dropped_dedup,
        "dedup_dropped": dropped_dedup,
        "reached_scoring": after_count
    }

    logger.info(f"✅ Returning {len(final_jobs)} job listings with cleaned descriptions.")
    return final_jobs, stats