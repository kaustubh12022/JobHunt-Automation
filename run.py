import sys
import traceback
from loguru import logger
from src.scraper import run_scraper
from src.scorer import score_jobs
from src.sheet_generator import generate_final_sheet, get_human_date_str
from src.pdf_generator import generate_pdf
from src.resume_tailor import tailor_resume
from src.email_sender import deliver_daily_resumes
from src.config_loader import load_config
from pathlib import Path

import argparse

# Fix Windows console emoji encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Run Headless AutoApply Pipeline")
    parser.add_argument("--test", action="store_true", help="Run in test mode (fast scrape, 1 combo, minimal scoring)")
    parser.add_argument("--dry-run", action="store_true", help="Run without generating PDFs or sending emails, logging to audit.log")
    args = parser.parse_args()
    test_mode = args.test
    dry_run = args.dry_run

    logger.info("🚀 Starting Headless AutoApply Pipeline..." + (" [TEST MODE]" if test_mode else "") + (" [DRY RUN]" if dry_run else ""))
    platforms = ["linkedin", "indeed"]
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 1/5: SCRAPING JOBS")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        jobs, scrape_stats = run_scraper(selected_platforms=platforms, test_mode=test_mode)
        if not jobs:
            logger.warning("⚠️ No jobs found matching your criteria. Exiting.")
            return
    except Exception as e:
        logger.error(f"❌ SCRAPING FAILED: {type(e).__name__} - {e}")
        logger.error(f"💡 Hint: Check internet connection, JobSpy API limits, or site blocks.")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return
        
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 2/5: AI SCORING")
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
    top_n = config['scoring'].get('top_n', 20)
    shortlisted = scored_jobs[:top_n]
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PHASE 3/5: TAILORING RESUMES & PDFS")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    from src.resume_tailor import tailor_resumes_batch
    from playwright.sync_api import sync_playwright
    
    date_str = get_human_date_str()
    pdf_paths = []
    
    logger.info(f"   🧠 Firing {len(shortlisted)} tailoring requests to DeepSeek concurrently...")
    
    try:
        # Generate all tailored JSONs in parallel (~3 seconds total)
        tailored_jsons = tailor_resumes_batch(shortlisted)
        
        if dry_run:
            import json
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("🛡️ DRY RUN MODE: WRITING AUDIT LOG")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            pdf_paths = ["dry_run.pdf"] * len(shortlisted)
            path = "audit.log"
            with open("audit.log", "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*50}\n")
                f.write(f"🛡️ DRY RUN AUDIT: {date_str}\n")
                f.write(f"{'='*50}\n")
                
                for i, (job, tailored_data) in enumerate(zip(shortlisted, tailored_jsons)):
                    if isinstance(tailored_data, Exception):
                        logger.error(f"   ❌ FATAL TAILORING ERROR for {job.company}: {tailored_data}")
                        continue
                    f.write(f"--- [{i+1}] {job.title} at {job.company} ---\n")
                    f.write(f"URL: {job.url}\n")
                    f.write(f"Score: {job.score}% | QA Role: {getattr(job, 'is_testing_role', False)}\n")
                    f.write(f"Extracted Reqs: {getattr(job, 'extracted_requirements', '')}\n")
                    f.write(f"Tailored JSON Output:\n{json.dumps(tailored_data, indent=2)}\n\n")
                    logger.info(f"   ✅ Audited: {job.title} at {job.company}")
        else:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                import uuid
                for i, (job, tailored_data) in enumerate(zip(shortlisted, tailored_jsons)):
                    if isinstance(tailored_data, Exception):
                        logger.error(f"   ❌ FATAL TAILORING ERROR for {job.company}: {tailored_data}")
                        pdf_paths.append("")
                        continue
                        
                    logger.info(f"   [{i+1}/{len(shortlisted)}] Generating PDF for: {job.title} at {job.company}")
                    try:
                        short_id = str(uuid.uuid4())[:6]
                        job.unique_id = short_id
                        pdf_path = generate_pdf(job, tailored_data, f"{date_str}_{short_id}", page)
                        pdf_paths.append(pdf_path)
                    except Exception as e:
                        logger.error(f"   ❌ PDF GENERATION FAILED for {job.company}: {type(e).__name__} - {e}")
                        logger.error(f"   📋 Traceback: {traceback.format_exc()}")
                        pdf_paths.append("")
                        
                browser.close()
                
    except Exception as e:
        logger.error(f"   ❌ BATCH TAILORING FAILED: {type(e).__name__} - {e}")
        logger.error(f"   📋 Traceback: {traceback.format_exc()}")
        pdf_paths = [""] * len(shortlisted)
            
    if not dry_run:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 4/5: SAVING FINAL EXCEL SHEET")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        try:
            path = generate_final_sheet(scored_jobs, pdf_paths=pdf_paths, test_mode=test_mode)
        except Exception as e:
            logger.error(f"❌ EXCEL GENERATION FAILED: {type(e).__name__} - {e}")
            logger.error(f"💡 Hint: Check if the Excel file is open elsewhere or if Pandas/openpyxl crashed.")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return
        
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 5/5: ZIP & EMAIL DELIVERY")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        try:
            out_dir_path = Path(config['output']['desktop_path']) / config['output']['folder_name'] / date_str
            
            stats = {
                "found_initial": scrape_stats.get("found_initial", len(jobs)),
                "pandas_dropped": scrape_stats.get("pandas_dropped", 0),
                "dedup_dropped": scrape_stats.get("dedup_dropped", 0),
                "reached_scoring": scrape_stats.get("reached_scoring", len(jobs)),
                "scored": len(scored_jobs),
                "tailored": sum(1 for p in pdf_paths if p)
            }
            deliver_daily_resumes(str(out_dir_path), date_str, stats, shortlisted)
        except Exception as e:
            logger.error(f"❌ EMAIL DELIVERY FAILED: {type(e).__name__} - {e}")
            logger.error(f"💡 Hint: Check SMTP settings, App Password, or ZIP file permissions.")
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
            logger.info(f"   Sheet saved to:   {path}")
    else:
        logger.info(f"   🛡️ DRY RUN AUDIT SAVED TO: audit.log")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    main()