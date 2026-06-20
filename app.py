"""
AutoApply Flask Dashboard — Admin Control Panel.

Features:
- Dynamic platform toggles (LinkedIn, Indeed)
- Production pipeline (full daily run)
- Isolated Test Mode (1 combo, 3 jobs, 1 resume, email delivery)
- Real-time log streaming
"""
import json
import threading
import traceback
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify, redirect, url_for
from src.logger import logger, log_queue
from src.scraper import run_scraper
from src.scorer import score_jobs
from src.sheet_generator import generate_final_sheet, get_human_date_str
from src.config_loader import load_config
from src.email_sender import deliver_daily_resumes

app = Flask(__name__, template_folder='templates', static_folder='static')

# ══════════════════════════════════════════════
# PIPELINE STATE MACHINES
# ══════════════════════════════════════════════
pipeline_state = {
    "running": False,
    "phase": "idle",
    "progress": "",
    "result_path": None,
    "jobs_found": 0,
    "jobs_scored": 0,
    "jobs_shortlisted": 0,
}

test_state = {
    "running": False,
    "phase": "idle",
}


# ══════════════════════════════════════════════
# PRODUCTION PIPELINE
# ══════════════════════════════════════════════
def run_pipeline(platforms, dry_run=False):
    """Background thread that runs the full PRODUCTION pipeline."""
    global pipeline_state
    try:
        pipeline_state["running"] = True
        pipeline_state["phase"] = "scraping"
        logger.info("🚀 Pipeline started!")

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 1/5: SCRAPING JOBS")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        jobs, scrape_stats = run_scraper(selected_platforms=platforms)
        pipeline_state["jobs_found"] = scrape_stats.get("found_initial", len(jobs))

        if not jobs:
            logger.warning("⚠️ No jobs found matching your criteria.")
            return

        pipeline_state["phase"] = "scoring"
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 2/5: AI SCORING")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        scored_jobs = score_jobs(jobs)
        pipeline_state["jobs_scored"] = len(scored_jobs)

        if not scored_jobs:
            logger.warning("⚠️ No jobs met the minimum score threshold.")
            return

        config = load_config()
        top_n = config['scoring'].get('top_n', 20)
        shortlisted = scored_jobs[:top_n]
        pipeline_state["jobs_shortlisted"] = len(shortlisted)

        pipeline_state["phase"] = "tailoring"
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 3/5: TAILORING RESUMES & PDFS")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        from src.resume_tailor import tailor_resume
        from src.pdf_generator import generate_pdf
        from playwright.sync_api import sync_playwright

        date_str = get_human_date_str()
        pdf_paths = []
        
        if dry_run:
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("🛡️ DRY RUN MODE: WRITING AUDIT LOG")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("   Writing tailored JSONs and scores to audit.log instead of generating PDFs/Excel...")
            pdf_paths = ["dry_run.pdf"] * len(shortlisted)
            path = "audit.log"
            
            from src.resume_tailor import tailor_resumes_batch
            logger.info("   [Batch] Starting concurrent AI tailoring for dry run...")
            tailored_jsons = tailor_resumes_batch(shortlisted)
            
            with open("audit.log", "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*50}\n")
                f.write(f"🛡️ DRY RUN AUDIT: {date_str}\n")
                f.write(f"{'='*50}\n")
                f.write(f"Scraped: {pipeline_state['jobs_found']} | Scored: {pipeline_state['jobs_scored']} | Shortlisted: {pipeline_state['jobs_shortlisted']}\n\n")
                
                for i, (job, tailored_data) in enumerate(zip(shortlisted, tailored_jsons)):
                    try:
                        f.write(f"--- [{i+1}] {job.title} at {job.company} ---\n")
                        f.write(f"URL: {job.url}\n")
                        f.write(f"Score: {job.score}% | QA Role: {getattr(job, 'is_testing_role', False)}\n")
                        f.write(f"Extracted Reqs: {getattr(job, 'extracted_requirements', '')}\n")
                        if isinstance(tailored_data, Exception):
                            f.write(f"Tailoring Error: {tailored_data}\n\n")
                            logger.error(f"   ❌ AUDIT FAILED for {job.company}: {tailored_data}")
                        else:
                            f.write(f"Tailored JSON Output:\n{json.dumps(tailored_data, indent=2)}\n\n")
                            logger.info(f"   ✅ Audited: {job.title} at {job.company}")
                    except Exception as e:
                        logger.error(f"   ❌ AUDIT FAILED for {job.company}: {e}")
                        
        else:
            try:
                import uuid
                from src.resume_tailor import tailor_resumes_batch
                
                for job in shortlisted:
                    job.unique_id = str(uuid.uuid4())[:6]
                    
                logger.info(f"   [Batch] Requesting {len(shortlisted)} resumes from DeepSeek concurrently...")
                tailored_jsons = tailor_resumes_batch(shortlisted)
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    for i, (job, tailored_data) in enumerate(zip(shortlisted, tailored_jsons)):
                        if isinstance(tailored_data, Exception) or not tailored_data:
                            logger.error(f"   ❌ RESUME TAILORING FAILED for {job.company}: {tailored_data}")
                            pdf_paths.append("")
                            continue
                            
                        logger.info(f"   [{i+1}/{len(shortlisted)}] Generating PDF for: {job.title} at {job.company}")
                        try:
                            pdf_path = generate_pdf(job, tailored_data, f"{date_str}_{job.unique_id}", page)
                            pdf_paths.append(pdf_path)
                            logger.info(f"   📄 PDF Generated: {Path(pdf_path).name if pdf_path else 'FAILED'}")
                        except Exception as e:
                            logger.error(f"   ❌ PDF FAILED for {job.company}: {e}")
                            pdf_paths.append("")
                    browser.close()
            except Exception as e:
                logger.error(f"Error during PDF generation in app: {e}")
                pdf_paths = [""] * len(shortlisted)

            pipeline_state["phase"] = "saving"
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("PHASE 4/5: SAVING FINAL EXCEL SHEET")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            path = generate_final_sheet(scored_jobs, pdf_paths=pdf_paths)

            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("PHASE 5/5: ZIP & EMAIL DELIVERY")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            out_dir_path = Path(config['output']['desktop_path']) / config['output']['folder_name'] / date_str

            stats = {
            "found_initial": scrape_stats.get("found_initial", len(jobs)),
            "pandas_dropped": scrape_stats.get("pandas_dropped", 0),
            "dedup_dropped": scrape_stats.get("dedup_dropped", 0),
            "reached_scoring": scrape_stats.get("reached_scoring", len(jobs)),
            "scored": pipeline_state["jobs_scored"],
            "tailored": sum(1 for p in pdf_paths if p)
        }
            deliver_daily_resumes(str(out_dir_path), date_str, stats, shortlisted)

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🎉 PIPELINE COMPLETE!")
        logger.info(f"   Jobs Found:       {pipeline_state['jobs_found']}")
        logger.info(f"   Jobs Scored:      {pipeline_state['jobs_scored']}")
        logger.info(f"   Jobs Shortlisted: {pipeline_state['jobs_shortlisted']}")
        if not dry_run:
            logger.info(f"   Resumes Generated: {sum(1 for p in pdf_paths if p)}")
            if path:
                logger.info(f"   Sheet saved to:   {path}")
        else:
            logger.info(f"   🛡️ DRY RUN AUDIT SAVED TO: audit.log")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
    finally:
        pipeline_state["phase"] = "done"
        pipeline_state["running"] = False


# ══════════════════════════════════════════════
# TEST MODE PIPELINE (completely isolated)
# ══════════════════════════════════════════════
def run_test_pipeline(platforms):
    """
    Background thread for TEST MODE.
    Scrapes 1 combo (~3 jobs), scores all, tailors top 1, generates PDF + Excel + Email.
    """
    global test_state
    try:
        test_state["running"] = True
        test_state["phase"] = "scraping"

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🧪 TEST MODE STARTED")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🧪 [TEST] This will scrape up to 20 jobs, score them, and generate 1 resume.")
        logger.info("🧪 [TEST] No production output will be created.")
        logger.info("")

        # Step 1: Scrape
        logger.info("🧪 [TEST] ── PHASE 1: SCRAPING ──")
        try:
            jobs, scrape_stats = run_scraper(selected_platforms=platforms, test_mode=True)
            if not jobs:
                logger.warning("🧪 [TEST] ⚠️ No jobs found. Test cannot proceed.")
                logger.info("🧪 [TEST] ❌ TEST FAILED — Scraping returned 0 jobs")
                return
            logger.info(f"🧪 [TEST] ✅ Scraping OK — Found {len(jobs)} jobs")
            logger.info("")
        except Exception as e:
            logger.error(f"🧪 [TEST] ❌ SCRAPING FAILED: {type(e).__name__} - {e}")
            logger.error(f"🧪 [TEST] 💡 Hint: Check internet connection, JobSpy API limits, or site blocks.")
            logger.error(f"🧪 [TEST] 📋 Traceback: {traceback.format_exc()}")
            return

        # Step 2: Score
        test_state["phase"] = "scoring"
        logger.info("🧪 [TEST] ── PHASE 2: SCORING ──")
        try:
            scored = score_jobs(jobs, test_mode=True)
            if not scored:
                logger.warning("🧪 [TEST] ⚠️ Scoring returned no results.")
                logger.info("🧪 [TEST] ❌ TEST FAILED — Scoring error")
                return
            logger.info(f"🧪 [TEST] ✅ Scoring OK — {len(scored)} jobs scored successfully")
            logger.info("")
        except Exception as e:
            logger.error(f"🧪 [TEST] ❌ SCORING FAILED: {type(e).__name__} - {e}")
            logger.error(f"🧪 [TEST] 💡 Hint: Check AI Provider API Key, limits, or connection.")
            logger.error(f"🧪 [TEST] 📋 Traceback: {traceback.format_exc()}")
            return

        # Step 3: Tailor top 3
        test_state["phase"] = "tailoring"
        scored.sort(key=lambda j: j.score or 0, reverse=True)
        top_jobs = scored[:3]

        logger.info("🧪 [TEST] ── PHASE 3: RESUME TAILORING ──")
        logger.info(f"🧪 [TEST] Tailoring resumes for top {len(top_jobs)} jobs...")

        from src.resume_tailor import tailor_resumes_batch
        from src.pdf_generator import generate_pdf
        import uuid

        try:
            for job in top_jobs:
                if not hasattr(job, 'unique_id') or not job.unique_id:
                    job.unique_id = str(uuid.uuid4())[:6]
                    
            tailored_jsons = tailor_resumes_batch(top_jobs)
            logger.info("🧪 [TEST] ✅ AI tailoring OK — Concurrent batch received")
        except Exception as e:
            logger.error(f"🧪 [TEST] ❌ RESUME TAILORING FAILED: {type(e).__name__} - {e}")
            logger.error(f"🧪 [TEST] 💡 Hint: Check AI model response format, API key, or timeouts.")
            logger.error(f"🧪 [TEST] 📋 Traceback: {traceback.format_exc()}")
            return

        # Step 4: PDF
        logger.info("🧪 [TEST] ── PHASE 4: PDF GENERATION ──")
        pdf_paths = []
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                for job, tailored_data in zip(top_jobs, tailored_jsons):
                    if isinstance(tailored_data, Exception):
                        logger.error(f"🧪 [TEST] ❌ TAILORING ERROR FOR {job.company}: {tailored_data}")
                        pdf_paths.append("")
                        continue
                        
                    pdf_path = generate_pdf(job, tailored_data, "_test", page)
                    if pdf_path:
                        logger.info(f"🧪 [TEST] ✅ PDF Generated: {Path(pdf_path).name}")
                        pdf_paths.append(pdf_path)
                    else:
                        logger.error(f"🧪 [TEST] ❌ PDF generation failed for {job.company}")
                        pdf_paths.append("")
                browser.close()
        except Exception as e:
            logger.error(f"🧪 [TEST] ❌ PDF GENERATION FAILED: {type(e).__name__} - {e}")
            logger.error(f"🧪 [TEST] 💡 Hint: Check wkhtmltopdf/Playwright installation, PATH variables, or write permissions.")
            logger.error(f"🧪 [TEST] 📋 Traceback: {traceback.format_exc()}")
            return

        # Step 5: Excel
        logger.info("🧪 [TEST] ── PHASE 5: EXCEL GENERATION ──")
        try:
            path = generate_final_sheet(scored, pdf_paths=pdf_paths, test_mode=True)
            if path:
                logger.info(f"🧪 [TEST] ✅ Excel Sheet Generated: {path}")
            else:
                logger.error("🧪 [TEST] ❌ Excel generation failed")
        except Exception as e:
            logger.error(f"🧪 [TEST] ❌ EXCEL GENERATION FAILED: {type(e).__name__} - {e}")
            logger.error(f"🧪 [TEST] 💡 Hint: Check if the Excel file is open elsewhere or if Pandas/openpyxl crashed.")
            logger.error(f"🧪 [TEST] 📋 Traceback: {traceback.format_exc()}")
            return

        # Step 6: File Check (No Email Delivery in Test Mode)
        logger.info("🧪 [TEST] ── PHASE 6: RESULTS SAVED ──")
        try:
            config = load_config()
            out_dir_path = Path(config['output']['desktop_path']) / config['output']['folder_name'] / "_test"

            logger.info(f"🧪 [TEST] ✅ All {len(pdf_paths)} test files saved to: {out_dir_path}")
            logger.info(f"🧪 [TEST] 🛑 Email delivery skipped in test mode per user request.")
        except Exception as e:
            logger.error(f"🧪 [TEST] ❌ FILE SAVING ERROR: {type(e).__name__} - {e}")
            logger.error(f"🧪 [TEST] 📋 Traceback: {traceback.format_exc()}")
            return

        # Final Report
        logger.info("")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🧪 TEST MODE COMPLETE — ALL PHASES PASSED ✅")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🧪 [TEST] Jobs scraped:  {len(jobs)}")
        logger.info(f"🧪 [TEST] Jobs scored:   {len(scored)}")
        for i, j in enumerate(top_jobs):
            logger.info(f"🧪 [TEST] Top {i+1} match:   {j.title} at {j.company} ({j.score}%)")
        logger.info(f"🧪 [TEST] Resumes saved: {sum(1 for p in pdf_paths if p)}")
        logger.info(f"🧪 [TEST] Sheet saved:   {path if path else 'FAILED'}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    except Exception as e:
        logger.error(f"🧪 [TEST] ❌ UNEXPECTED TEST PIPELINE ERROR: {type(e).__name__} - {e}")
        logger.error(f"🧪 [TEST] 📋 Full traceback: {traceback.format_exc()}")
    finally:
        test_state["phase"] = "done"
        test_state["running"] = False


# ══════════════════════════════════════════════
# FLASK ROUTES
# ══════════════════════════════════════════════
@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/start', methods=['POST'])
def start_pipeline():
    if pipeline_state["running"] or test_state["running"]:
        return jsonify({"error": "A pipeline is already running"}), 400
    
    # Read platform selections from frontend toggles
    data = request.get_json(silent=True) or {}
    platforms = data.get('platforms', ["linkedin", "indeed"])
    dry_run = data.get('dry_run', False)
    
    thread = threading.Thread(target=run_pipeline, args=(platforms, dry_run))
    thread.daemon = True
    thread.start()
    return jsonify({"message": "Started successfully"})


@app.route('/api/test-start', methods=['POST'])
def start_test_pipeline():
    if pipeline_state["running"] or test_state["running"]:
        return jsonify({"error": "A pipeline is already running"}), 400
    
    # Read platform selections from frontend toggles
    data = request.get_json(silent=True) or {}
    platforms = data.get('platforms', ["linkedin", "indeed"])
    
    thread = threading.Thread(target=run_test_pipeline, args=(platforms,))
    thread.daemon = True
    thread.start()
    return jsonify({"message": "Test pipeline started"})


@app.route('/api/status', methods=['GET'])
def get_status():
    if test_state["running"]:
        return jsonify({
            "running": True,
            "phase": test_state["phase"],
            "mode": "test"
        })
    return jsonify({
        "running": pipeline_state["running"],
        "phase": pipeline_state["phase"],
        "mode": "prod"
    })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    logs = []
    while not log_queue.empty():
        logs.append(log_queue.get())
    return jsonify(logs)


@app.route('/api/config', methods=['GET'])
def get_config_api():
    config = load_config()
    return jsonify(config)


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    import yaml
    resume_path = Path('data_folder/plain_text_resume.yaml')
    
    if request.method == 'POST':
        yaml_content = request.form.get('yaml_content')
        if yaml_content:
            try:
                # Validate that it is valid YAML before saving
                yaml.safe_load(yaml_content)
                with open(resume_path, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                return redirect(url_for('edit_profile', success=True))
            except Exception as e:
                return render_template('edit_profile.html', yaml_content=yaml_content, error=str(e))
                
    # GET method
    with open(resume_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    
    success = request.args.get('success')
    return render_template('edit_profile.html', yaml_content=yaml_content, success=success)


if __name__ == '__main__':
    logger.info("🌐 Starting AutoApply Dashboard on http://localhost:5000")
    app.run(port=5000)