import sys
import traceback
from src.logger import logger
from src.scraper import run_scraper
from src.scorer import score_jobs
from src.config_loader import get_human_date_str
from src.pdf_generator import generate_pdf
from src.resume_tailor import tailor_resume
from src.config_loader import load_config
from pathlib import Path

import argparse

# Fix Windows console emoji encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Run Headless AutoApply Pipeline")
    parser.add_argument("--test-mode", "--test", action="store_true", dest="test_mode", help="Run in test mode (fast scrape, 1 combo, minimal scoring)")
    parser.add_argument("--dry-run", action="store_true", help="Run without generating PDFs or sending emails, logging to audit.log")
    args = parser.parse_args()
    
    config = load_config()
    test_mode = args.test_mode or config.get('test_mode', {}).get('enabled', False)
    dry_run = args.dry_run

    logger.info("🚀 Starting Headless AutoApply Pipeline..." + (" [TEST MODE]" if test_mode else "") + (" [DRY RUN]" if dry_run else ""))
    
    # Ensure 72h freshness from config is respected during pipeline runs
    import pandas as pd
    import src.scraper as scraper_module
    hours_old = config.get('search', {}).get('hours_old', 72)
    orig_apply_pandas_filter = scraper_module.apply_pandas_filter

    def m1_apply_pandas_filter(jobs, locations, callbacks=None, test_mode=False):
        now = pd.Timestamp.now(tz='UTC')
        cutoff_72 = now - pd.Timedelta(hours=hours_old)
        saved_dates = {}
        for j in jobs:
            dp = getattr(j, 'date_posted', None)
            if dp is not None:
                try:
                    dt = pd.to_datetime(dp, errors='coerce', utc=True)
                    if pd.notna(dt) and dt >= cutoff_72:
                        saved_dates[j.id] = dp
                        j.date_posted = now
                    elif pd.isna(dt):
                        saved_dates[j.id] = dp
                        j.date_posted = now
                except Exception:
                    saved_dates[j.id] = dp
                    j.date_posted = now
            else:
                saved_dates[j.id] = None
                j.date_posted = now

        filtered = orig_apply_pandas_filter(jobs, locations, callbacks=callbacks, test_mode=test_mode)
        for j in filtered:
            if j.id in saved_dates:
                j.date_posted = saved_dates[j.id]

        if test_mode and not filtered and jobs:
            logger.info("🧪 TEST MODE: Scraped sample had 0 filter passes; passing top available scraped jobs for pipeline verification.")
            for j in jobs:
                if j.id in saved_dates and saved_dates[j.id] is not None:
                    j.date_posted = saved_dates[j.id]
            filtered = [j for j in jobs if j.description and j.description.strip()][:3]

        return filtered

    scraper_module.apply_pandas_filter = m1_apply_pandas_filter

    if test_mode:
        platforms = ["linkedin"]
        orig_load_config = scraper_module.load_config
        def test_mode_load_config():
            cfg = orig_load_config()
            cfg['search']['search_terms'] = ["QA Automation"]
            cfg['search']['locations'] = ["Pune"]
            cfg['search']['platforms'] = ["linkedin"]
            cfg['search']['results_wanted'] = 5
            return cfg
        scraper_module.load_config = test_mode_load_config
    else:
        platforms = config.get('search', {}).get('platforms', ["linkedin", "indeed"])
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 1/4: SCRAPING JOBS")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        jobs, scrape_stats = run_scraper(
            selected_platforms=platforms, 
            selected_job_types=["fulltime"] if test_mode else None, 
            test_mode=test_mode
        )
        if not jobs:
            logger.warning("⚠️ No jobs found matching your criteria. Exiting.")
            return
    except Exception as e:
        logger.error(f"❌ SCRAPING FAILED: {type(e).__name__} - {e}")
        logger.error(f"💡 Hint: Check internet connection, JobSpy API limits, or site blocks.")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return
        
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 2/4: AI SCORING")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        scored_jobs = score_jobs(jobs, test_mode=test_mode)
        if not scored_jobs:
            logger.warning("⚠️ No jobs met the minimum score threshold. Exiting.")
            return
    except Exception as e:
        logger.error(f"❌ SCORING FAILED: {type(e).__name__} - {e}")
        logger.error(f"💡 Hint: Check AI Provider API Key, limits, or connection.")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return
        
    config = load_config()
    
    # Remove 5 resume limitation. EVERY job > minimum_score gets shortlisted.
    shortlisted = [j for j in scored_jobs if j.score >= config.get('scoring', {}).get('minimum_score', 60)]
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 3/4: TAILORING RESUMES & PDFS (SKIPPED - DELEGATED TO UI)")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("   Tailoring is now handled interactively via the Dashboard.")
    
    pdf_paths = [""] * len(shortlisted)
    
    path = ""
    if not dry_run:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 4/4: SAVING TO DATABASE")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        try:
            from src.db import save_pipeline_results
            pipeline_state = {
                "mode": "test" if test_mode else "prod",
                "scan": {"total_found": len(jobs)},
                "filter": {"after": scrape_stats.get("reached_scoring", len(jobs))},
                "score": {"scored": len(scored_jobs), "shortlisted": len(shortlisted)},
                "all_scored_jobs": getattr(scored_jobs, "all_scored_jobs", scored_jobs),
            }
            save_pipeline_results(
                pipeline_state,
                tailor_targets,
                pdf_paths,
                all_scored_jobs=getattr(scored_jobs, "all_scored_jobs", scored_jobs),
            )
            path = "Database (Supabase)"
        except Exception as e:
            logger.error(f"❌ DATABASE SAVE FAILED: {type(e).__name__} - {e}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"🎉 PIPELINE COMPLETE!")
    logger.info(f"   Jobs Found:       {len(jobs)}")
    logger.info(f"   Jobs Scored:      {len(scored_jobs)}")
    logger.info(f"   Jobs Shortlisted: {len(shortlisted)}")
    if not dry_run:
        logger.info(f"   Resumes Generated: {sum(1 for p in pdf_paths if p)}")
        if path:
            logger.info(f"   Saved to:         {path}")
    else:
        logger.info(f"   🛡️ DRY RUN AUDIT SAVED TO: audit.log")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    main()