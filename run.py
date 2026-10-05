import sys
import os
import json
import time
import shutil
import traceback
from datetime import datetime
from pathlib import Path
import argparse

# Fix Windows console emoji encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from src.logger import logger
from src.scraper import run_scraper
from src.scorer import score_jobs
from src.config_loader import get_human_date_str, load_config
from src.pdf_generator import generate_pdf
from src.visual_catalog_pdf import generate_visual_catalog_pdf

PROGRESS_FILE = Path(__file__).parent / "pipeline_progress.json"

def update_progress(data: dict):
    try:
        data["updated_at"] = datetime.now().isoformat()
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to update progress file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run Headless AutoApply Pipeline with Off-Peak Rate Scheduling")
    parser.add_argument("--test-mode", "--test", action="store_true", dest="test_mode", help="Run in test mode (fast scrape, 1 combo, minimal scoring)")
    parser.add_argument("--dry-run", action="store_true", help="Run without generating PDFs or sending emails, logging to audit.log")
    parser.add_argument("--no-wait-offpeak", action="store_true", help="Do not wait for 3:31 PM off-peak window")
    parser.add_argument("--target-time", default="15:31", help="Target time in HH:MM (IST) to start AI calls for 50% off-peak rate")
    parser.add_argument("--no-tailor", action="store_true", help="Skip resume tailoring")
    parser.add_argument("--no-table-pdf", action="store_true", help="Skip final table PDF generation")
    parser.add_argument("--hours-old", type=int, default=None, help="Recency cutoff in hours (e.g. 24, 36, 48, 72)")
    parser.add_argument("--platforms", type=str, default=None, help="Comma-separated platforms to scrape (e.g. linkedin,indeed,workday)")
    parser.add_argument("--strict-3-col", action="store_true", help="Force strictly 3 columns in the Job Applications Table (Company, Role, Apply Link)")
    parser.add_argument("--zero-ai", action="store_true", help="Run 100% deterministic pipeline without calling DeepSeek AI (zero token cost, instant)")
    args = parser.parse_args()
    
    start_time = datetime.now()
    config = load_config()
    test_mode = args.test_mode or config.get('test_mode', {}).get('enabled', False)
    dry_run = args.dry_run
    use_ai = not args.zero_ai
    wait_offpeak = (not args.no_wait_offpeak) and use_ai
    should_tailor = not args.no_tailor
    generate_table = not args.no_table_pdf

    progress = {
        "phase": "initializing",
        "status_text": "Initializing pipeline...",
        "start_time": start_time.isoformat(),
        "jobs_scraped": 0,
        "current_cycle": "Starting...",
        "offpeak_active": False,
        "jobs_scored": 0,
        "jobs_shortlisted": 0,
        "resumes_generated": 0,
        "table_pdf_path": "",
        "zip_path": "",
        "complete": False
    }
    update_progress(progress)

    logger.info("🚀 Starting Headless AutoApply Pipeline..." + (" [TEST MODE]" if test_mode else "") + (" [DRY RUN]" if dry_run else ""))
    
    # Ensure freshness from config is respected during pipeline runs
    import pandas as pd
    import src.scraper as scraper_module
    hours_old = args.hours_old if args.hours_old is not None else config.get('search', {}).get('hours_old', 36)
    orig_apply_pandas_filter = scraper_module.apply_pandas_filter

    def m1_apply_pandas_filter(jobs, locations, callbacks=None, test_mode=False, **kwargs):
        now = pd.Timestamp.now(tz='UTC')
        cutoff = now - pd.Timedelta(hours=kwargs.get('hours_old', hours_old))
        saved_dates = {}
        for j in jobs:
            dp = getattr(j, 'date_posted', None)
            if dp is not None:
                try:
                    dt = pd.to_datetime(dp, errors='coerce', utc=True)
                    if pd.notna(dt) and dt >= cutoff:
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

        filtered = orig_apply_pandas_filter(jobs, locations, callbacks=callbacks, test_mode=test_mode, **kwargs)
        for j in filtered:
            if j.id in saved_dates:
                j.date_posted = saved_dates[j.id]

        if test_mode and not filtered and jobs:
            logger.info("🧪 TEST MODE: Scraped sample had 0 filter passes; passing top available scraped jobs for pipeline verification.")
            for j in jobs:
                if j.id in saved_dates and saved_dates[j.id] is not None:
                    j.date_posted = saved_dates[j.id]
            filtered = [j for j in jobs if j.description and j.description.strip()][:3]
            for f in filtered:
                f.title = "Junior QA Automation Engineer"
                f.description = "Looking for a QA engineer with Python, Java, Selenium, API testing."
                f.date_posted = pd.Timestamp.now(tz='UTC')

        return filtered

    scraper_module.apply_pandas_filter = m1_apply_pandas_filter

    if args.platforms:
        platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    elif test_mode:
        platforms = config.get('test_mode', {}).get('platforms', ["internshala", "unstop", "hirist", "naukri"])
    else:
        platforms = config.get('search', {}).get('platforms', ["naukri", "instahyre", "internshala", "unstop", "hirist", "workday", "linkedin", "indeed"])

    if test_mode:
        orig_load_config = scraper_module.load_config
        def test_mode_load_config():
            cfg = orig_load_config()
            cfg['search']['search_terms'] = cfg.get('test_mode', {}).get('search_terms', ["Junior Java Developer"])
            cfg['search']['locations'] = cfg.get('test_mode', {}).get('locations', ["Pune"])
            cfg['search']['platforms'] = platforms
            cfg['search']['results_wanted'] = cfg.get('test_mode', {}).get('results_wanted', 5)
            return cfg
        scraper_module.load_config = test_mode_load_config
    
    # Set up live callbacks for scraping progress
    scraped_counter = {"count": 0}
    def on_cycle_start(cycle_data):
        label = cycle_data.get("cycle_label", "")
        progress["phase"] = "scraping"
        progress["current_cycle"] = label
        progress["status_text"] = f"Scraping: {label} (Found {scraped_counter['count']} raw jobs)"
        update_progress(progress)

    def on_job_scraped(job_data):
        scraped_counter["count"] += 1
        progress["jobs_scraped"] = scraped_counter["count"]
        progress["status_text"] = f"Scraping active: {scraped_counter['count']} jobs discovered ({job_data.get('company', '')} - {job_data.get('title', '')})"
        update_progress(progress)

    callbacks = {
        "on_cycle_start": on_cycle_start,
        "on_job_scraped": on_job_scraped,
    }

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 1/4: SCRAPING JOBS")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        jobs, scrape_stats = run_scraper(
            selected_platforms=platforms, 
            selected_job_types=["fulltime"] if test_mode else None, 
            test_mode=test_mode,
            callbacks=callbacks,
            hours_old=hours_old
        )
        if not jobs:
            logger.warning("⚠️ No jobs found matching your criteria. Exiting.")
            progress["phase"] = "done"
            progress["status_text"] = "No jobs found matching criteria."
            update_progress(progress)
            return
    except Exception as e:
        logger.error(f"❌ SCRAPING FAILED: {type(e).__name__} - {e}")
        logger.error(f"💡 Hint: Check internet connection, JobSpy API limits, or site blocks.")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        progress["phase"] = "error"
        progress["status_text"] = f"Scraping failed: {e}"
        update_progress(progress)
        return

    logger.info(f"✅ Scraping completed! Viable jobs after filters: {len(jobs)}")
    progress["jobs_scraped"] = len(jobs)
    progress["status_text"] = f"Scraping complete ({len(jobs)} viable jobs)."
    update_progress(progress)

    # ── OFF-PEAK TIME CHECK & WAIT ──
    if wait_offpeak:
        try:
            t_parts = [int(p) for p in args.target_time.split(":")]
            target_hour = t_parts[0]
            target_minute = t_parts[1]
        except Exception:
            target_hour, target_minute = 15, 31

        now = datetime.now()
        target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if now < target_dt:
            wait_seconds = int((target_dt - now).total_seconds())
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"🕒 OFF-PEAK WAIT: Current time is {now.strftime('%H:%M:%S')} IST.")
            logger.info(f"   Target off-peak discount window: {target_hour:02d}:{target_minute:02d} IST (10:01 UTC).")
            logger.info(f"   Waiting {wait_seconds} seconds to lock in DeepSeek 50% half rates...")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            while datetime.now() < target_dt:
                cur = datetime.now()
                rem = int((target_dt - cur).total_seconds())
                if rem <= 0:
                    break
                progress["phase"] = "waiting_offpeak"
                progress["status_text"] = f"Scraping finished ({len(jobs)} jobs). Waiting for 15:31 IST 50% discount ({rem}s left)..."
                progress["remaining_wait_seconds"] = rem
                update_progress(progress)
                time.sleep(min(10, rem))

            logger.info("🎯 TARGET TIME REACHED! DeepSeek 50% off-peak pricing is now ACTIVE!")
        else:
            logger.info(f"🎯 Current time ({now.strftime('%H:%M:%S')} IST) is already >= {target_hour:02d}:{target_minute:02d} IST.")
            logger.info("   DeepSeek 50% off-peak pricing is ALREADY ACTIVE!")

    progress["offpeak_active"] = True
    progress["phase"] = "scoring"
    progress["status_text"] = "Running AI Scoring with DeepSeek (50% off-peak rate)..."
    update_progress(progress)

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 2/4: AI SCORING")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        scored_jobs = score_jobs(jobs, test_mode=test_mode, use_ai=use_ai)
        if not scored_jobs:
            logger.warning("⚠️ No jobs met the minimum score threshold. Exiting.")
            progress["phase"] = "done"
            progress["status_text"] = "No jobs met minimum score threshold."
            update_progress(progress)
            return
    except Exception as e:
        logger.error(f"❌ SCORING FAILED: {type(e).__name__} - {e}")
        logger.error(f"💡 Hint: Check AI Provider API Key, limits, or connection.")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        progress["phase"] = "error"
        progress["status_text"] = f"Scoring failed: {e}"
        update_progress(progress)
        return
        
    config = load_config()
    min_score = config.get('scoring', {}).get('minimum_score', 60)
    shortlisted = [j for j in scored_jobs if j.score >= min_score]
    
    progress["jobs_scored"] = len(scored_jobs)
    progress["jobs_shortlisted"] = len(shortlisted)
    update_progress(progress)

    logger.info(f"📊 Scoring finished: {len(scored_jobs)} scored, {len(shortlisted)} shortlisted (>= {min_score}%).")

    # ── PHASE 3: RESUME TAILORING & PDF GENERATION ──
    pdf_paths = [""] * len(shortlisted)
    if should_tailor and shortlisted and not dry_run:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"PHASE 3/4: TAILORING RESUMES & PDFS ({len(shortlisted)} shortlisted jobs)")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        progress["phase"] = "tailoring"
        progress["status_text"] = f"Tailoring {len(shortlisted)} resumes concurrently with DeepSeek..."
        update_progress(progress)

        try:
            from src.resume_tailor import tailor_resumes_batch
            from playwright.sync_api import sync_playwright

            logger.info(f"   [Batch] Tailoring {len(shortlisted)} resumes ({'AI' if use_ai else 'Deterministic Rule-Lens'})...")
            tailored_jsons = tailor_resumes_batch(shortlisted, use_ai=use_ai)
            date_str = get_human_date_str()

            generated_paths = []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                for i, (job, tailored_data) in enumerate(zip(shortlisted, tailored_jsons)):
                    apply_type = (getattr(job, "apply_type", None) or "easy_apply").lower()
                    if apply_type == "easy_apply":
                        logger.info(f"   [{i+1}/{len(shortlisted)}] ⚡ Easy Apply role ({job.company}): No resume generation per protocol.")
                        generated_paths.append("")
                        continue

                    if isinstance(tailored_data, Exception) or not tailored_data:
                        logger.error(f"   ❌ RESUME TAILORING FAILED for {job.company}: {tailored_data}")
                        generated_paths.append("")
                        continue

                    logger.info(f"   [{i+1}/{len(shortlisted)}] Rendering PDF for: {job.title} at {job.company}")
                    try:
                        pdf_path = generate_pdf(job, tailored_data, date_str, page)
                        generated_paths.append(pdf_path)
                        job.tailored_resume = tailored_data
                    except Exception as e:
                        logger.error(f"   ❌ PDF FAILED for {job.company}: {e}")
                        generated_paths.append("")
                        
                    progress["resumes_generated"] = sum(1 for p in generated_paths if p)
                    progress["status_text"] = f"Generated {progress['resumes_generated']}/{len(shortlisted)} resumes..."
                    update_progress(progress)

                browser.close()
            pdf_paths = generated_paths
        except Exception as e:
            logger.error(f"Error during resume tailoring and PDF generation: {e}")
            logger.error(traceback.format_exc())
            pdf_paths = [""] * len(shortlisted)
    else:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 3/4: TAILORING SKIPPED (--no-tailor or dry-run)")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ── PHASE 4: SAVING TO DATABASE & SUPABASE STORAGE ──
    path = ""
    if not dry_run:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 4/4: SAVING TO DATABASE & STORAGE")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        progress["phase"] = "saving"
        progress["status_text"] = "Saving results and uploading PDFs to Supabase..."
        update_progress(progress)

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
                shortlisted,
                pdf_paths,
                all_scored_jobs=getattr(scored_jobs, "all_scored_jobs", scored_jobs),
            )
            path = "Database (Supabase)"
            logger.info("   ✅ All records and resume PDFs successfully synced to Supabase.")
        except Exception as e:
            logger.error(f"❌ DATABASE SAVE FAILED: {type(e).__name__} - {e}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")

    # ── PHASE 5: GENERATE 4-COLUMN SUMMARY TABLE PDF ──
    table_pdf_path = ""
    if generate_table and shortlisted:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("GENERATING FINAL 4-COLUMN TABLE PDF")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        progress["phase"] = "generating_table_pdf"
        progress["status_text"] = "Generating summary table PDF..."
        update_progress(progress)

        try:
            from src.db import supabase
            catalog_jobs = []
            for job, pdf_path in zip(shortlisted, pdf_paths):
                supabase_url = ""
                platform = (getattr(job, "source", None) or "general").lower().replace("workday-", "")
                apply_type = (getattr(job, "apply_type", None) or "easy_apply").lower()
                if not args.strict_3_col and pdf_path and os.path.exists(pdf_path):
                    filename = Path(pdf_path).name
                    storage_path = f"{platform}/{apply_type}/{filename}"
                    if supabase:
                        try:
                            supabase_url = supabase.storage.from_("resumes").get_public_url(storage_path)
                        except Exception:
                            supabase_url = ""
                catalog_jobs.append({
                    "company": job.company,
                    "role": job.title,
                    "apply_link": getattr(job, "url", ""),
                    "supabase_resume_url": supabase_url,
                    "platform": platform,
                    "apply_type": apply_type
                })

            desktop_dir = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"
            out_pdf = generate_visual_catalog_pdf(catalog_jobs, desktop_dir)
            if out_pdf and os.path.exists(out_pdf):
                # Also save a dedicated copy named Job_Applications_Table.pdf on Desktop
                table_pdf_path = str(desktop_dir / "Job_Applications_Table.pdf")
                shutil.copy(out_pdf, table_pdf_path)
                logger.info(f"   ✅ Saved Table PDF: {table_pdf_path}")
                progress["table_pdf_path"] = table_pdf_path

            # Also generate a clean categorized CSV table
            try:
                import csv
                csv_path = desktop_dir / "Job_Applications_Table.csv"
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Platform", "Application Type", "Company Name", "Job Title", "Direct Apply Link", "Resume PDF Link"])
                    for j in catalog_jobs:
                        writer.writerow([
                            j.get("platform", "general").capitalize(),
                            "Easy Apply" if j.get("apply_type") == "easy_apply" else "Company Site",
                            j.get("company", ""),
                            j.get("role", ""),
                            j.get("apply_link", ""),
                            j.get("supabase_resume_url", "")
                        ])
                logger.info(f"   ✅ Saved Categorized Table CSV: {csv_path}")
            except Exception as ce:
                logger.warning(f"Could not generate Table CSV: {ce}")
        except Exception as e:
            logger.error(f"❌ Table PDF Generation failed: {e}")
            logger.error(traceback.format_exc())

    # ── PHASE 6: PACKAGE DELIVERABLE ZIP ARCHIVE ──
    zip_archive_path = ""
    if shortlisted:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PACKAGING FINAL DELIVERABLE ZIP ARCHIVE")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        progress["phase"] = "packaging_zip"
        progress["status_text"] = "Packaging deliverable ZIP archive..."
        update_progress(progress)

        try:
            from src.archive_packager import package_pipeline_archive
            desktop_dir = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"
            zip_archive_path = package_pipeline_archive(
                pdf_paths=pdf_paths,
                table_pdf_path=table_pdf_path,
                desktop_dir=desktop_dir,
            )
            if zip_archive_path:
                progress["zip_path"] = zip_archive_path
                logger.info(f"   ✅ Saved Deliverable ZIP: {zip_archive_path}")
        except Exception as ze:
            logger.error(f"❌ ZIP Archive Packaging failed: {ze}")
            logger.error(traceback.format_exc())

    elapsed = int((datetime.now() - start_time).total_seconds())
    progress["phase"] = "done"
    progress["complete"] = True
    progress["elapsed_seconds"] = elapsed
    progress["status_text"] = f"Pipeline complete in {elapsed // 60}m {elapsed % 60}s!"
    update_progress(progress)

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"🎉 PIPELINE COMPLETE IN {elapsed // 60}m {elapsed % 60}s!")
    logger.info(f"   Jobs Found:        {len(jobs)}")
    logger.info(f"   Jobs Scored:       {len(scored_jobs)}")
    logger.info(f"   Jobs Shortlisted:  {len(shortlisted)}")
    logger.info(f"   Resumes Generated: {sum(1 for p in pdf_paths if p)}")
    if table_pdf_path:
        logger.info(f"   Table PDF:         {table_pdf_path}")
    if zip_archive_path:
        logger.info(f"   Deliverable ZIP:   {zip_archive_path}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    main()