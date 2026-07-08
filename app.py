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
import os
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_from_directory, send_file
from src.logger import logger, log_queue
from src.scraper import run_scraper
from src.scorer import score_jobs
from src.config_loader import load_config, get_human_date_str
from src.db import save_pipeline_results
from datetime import datetime

app = Flask(__name__, static_folder='frontend/dist')

# ══════════════════════════════════════════════
# PIPELINE STATE MACHINES
# ══════════════════════════════════════════════
stop_event = threading.Event()

pipeline_state = {
    "running": False,
    "mode": "idle",           # idle | prod | test
    "phase": "idle",          # idle | scanning | filtering | scoring | tailoring | saving | done | error
    "status_text": "",
    "scan": {
        "total_found": 0,
        "current_platform": "",
        "current_city": "",
        "current_term": "",
        "combos_done": 0,
        "combos_total": 0,
        "live_jobs": []
    },
    "filter": {
        "before": 0,
        "after": 0,
        "dropped": { "empty": 0, "stale": 0, "location": 0, "senior": 0, "experience": 0, "duplicate": 0 },
        "dropped_jobs": []
    },
    "score": {
        "total": 0,
        "scored": 0,
        "avg_score": 0,
        "above_threshold": 0,
        "shortlisted": 0,
        "live_scores": []
    },
    "tailor": {
        "total": 0,
        "completed": 0,
        "failed": 0,
        "current_company": "",
        "results": []
    },
    "result": {
        "resumes_generated": 0,
        "output_dir": "",
    },
    "error": None,
}

test_state = pipeline_state.copy()

import re

def extract_number(text):
    match = re.search(r'\d+', text)
    return int(match.group()) if match else 0

def pipeline_log_interceptor(message):
    """Parses log messages to update pipeline_state for the dashboard."""
    text = message.record["message"]
    text_lower = text.lower()
    
    # Just basic matching for Phase 1, we can improve later if needed
    pipeline_state["status_text"] = text
    if "scraping" in text_lower and "linkedin" in text_lower:
        pipeline_state["scan"]["current_platform"] = "linkedin"
    elif "scraping" in text_lower and "indeed" in text_lower:
        pipeline_state["scan"]["current_platform"] = "indeed"
    elif "jobs found" in text_lower or ("found" in text_lower and "jobs" in text_lower):
        if "raw jobs" not in text_lower and "pre-filter" not in text_lower:
            pipeline_state["scan"]["total_found"] += extract_number(text)
    elif "pre-filter" in text_lower:
        pipeline_state["phase"] = "filtering"

# Add the interceptor to Loguru
logger.add(pipeline_log_interceptor, format="{message}")



# ══════════════════════════════════════════════
# EVENT CALLBACKS
# ══════════════════════════════════════════════
def on_cycle_start(cycle_data):
    pipeline_state["scan"]["live_jobs"] = []
    if isinstance(cycle_data, dict):
        pipeline_state["scan"]["current_params"] = cycle_data
        pipeline_state["status_text"] = f"Scraping {cycle_data.get('term', '')} in {cycle_data.get('loc', '')}..."
    else:
        pipeline_state["status_text"] = str(cycle_data)

def on_job_scraped(job_dict):
    # Just append since we clear it every cycle
    pipeline_state["scan"]["live_jobs"].append(job_dict)

def on_job_dropped(title, company, reason):
    if len(pipeline_state["filter"]["dropped_jobs"]) < 100:
        pipeline_state["filter"]["dropped_jobs"].insert(0, {"title": str(title), "company": str(company), "reason": str(reason)})

def on_score_start(job_id, title, company):
    pipeline_state["score"]["live_scores"].insert(0, {"id": job_id, "title": str(title), "company": str(company), "status": "scoring", "score": None})

def on_score_complete(job_id, score, reason=""):
    for item in pipeline_state["score"]["live_scores"]:
        if item["id"] == job_id:
            item["score"] = score
            item["reason"] = reason
            item["status"] = "done"
            break

callbacks = {
    "on_cycle_start": on_cycle_start,
    "on_job_scraped": on_job_scraped,
    "on_job_dropped": on_job_dropped,
    "on_score_start": on_score_start,
    "on_score_complete": on_score_complete
}

# ══════════════════════════════════════════════
# PRODUCTION PIPELINE
# ══════════════════════════════════════════════
def run_pipeline(platforms, dry_run=False, test_mode=False):
    """Background thread that runs the full pipeline for both PROD and TEST modes."""
    global pipeline_state
    try:
        pipeline_state["running"] = True
        pipeline_state["mode"] = "test" if test_mode else "prod"
        pipeline_state["phase"] = "scanning"
        pipeline_state["scan"]["live_jobs"] = []
        pipeline_state["scan"]["total_found"] = 0
        pipeline_state["filter"]["dropped_jobs"] = []
        pipeline_state["score"]["live_scores"] = []
        pipeline_state["tailor"]["results"] = []
        
        mode_label = " [TEST MODE]" if test_mode else ""
        logger.info(f"🚀 Pipeline started!{mode_label}")

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 1/5: SCRAPING JOBS")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        jobs, scrape_stats = run_scraper(selected_platforms=platforms, test_mode=test_mode, callbacks=callbacks)
        pipeline_state["scan"]["total_found"] = scrape_stats.get("found_initial", len(jobs))
        pipeline_state["filter"]["after"] = scrape_stats.get("reached_scoring", len(jobs))

        if not jobs:
            logger.warning("⚠️ No jobs found matching your criteria.")
            return

        if stop_event.is_set(): return

        pipeline_state["phase"] = "scoring"
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 2/5: AI SCORING")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        if test_mode:
            logger.info("🧪 TEST MODE: Limiting to 5 jobs for scoring")
            jobs = jobs[:5]
            
        scored_jobs = score_jobs(jobs, test_mode=test_mode, callbacks=callbacks)
        pipeline_state["score"]["scored"] = len(scored_jobs)

        if not scored_jobs:
            logger.warning("⚠️ No jobs met the minimum score threshold.")
            return

        if stop_event.is_set(): return

        config = load_config()
        top_n = 1 if test_mode else config['scoring'].get('top_n', 20)
        shortlisted = scored_jobs[:top_n]
        pipeline_state["score"]["shortlisted"] = len(shortlisted)

        pipeline_state["phase"] = "tailoring"
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 3/5: TAILORING RESUMES & PDFS")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        from src.resume_tailor import tailor_resume
        from src.pdf_generator import generate_pdf
        from playwright.sync_api import sync_playwright

        time_format = datetime.now().strftime('%d%b-%H-%M').lower()
        date_str = f"test/{time_format}" if test_mode else f"main pipeline/{time_format}"
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
                f.write(f"Scraped: {pipeline_state['scan']['total_found']} | Scored: {pipeline_state['score']['scored']} | Shortlisted: {pipeline_state['score']['shortlisted']}\n\n")
                
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
                from src.resume_tailor import tailor_resumes_batch
                
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
                            # Pass date_str as the directory, unique_id can be added to filename in pdf_generator if needed,
                            # but right now pdf_generator uses date_str strictly as the directory name.
                            pdf_path = generate_pdf(job, tailored_data, date_str, page)
                            pdf_paths.append(pdf_path)
                            pipeline_state["tailor"]["results"].append({
                                "id": job.id,
                                "title": job.title,
                                "company": job.company,
                                "pdf_path": pdf_path
                            })
                            logger.info(f"   📄 PDF Generated: {Path(pdf_path).name if pdf_path else 'FAILED'}")
                        except Exception as e:
                            logger.error(f"   ❌ PDF FAILED for {job.company}: {e}")
                            pdf_paths.append("")
                    browser.close()
            except Exception as e:
                logger.error(f"Error during PDF generation in app: {e}")
                pdf_paths = [""] * len(shortlisted)

            if stop_event.is_set(): return

            pipeline_state["phase"] = "saving"
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("PHASE 4/4: SAVE TO DATABASE")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            save_pipeline_results(pipeline_state, shortlisted, pdf_paths)
            path = "Database (Supabase)"

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🎉 PIPELINE COMPLETE!")
        logger.info(f"   Jobs Found:       {pipeline_state['scan']['total_found']}")
        logger.info(f"   Jobs Scored:      {pipeline_state['score']['scored']}")
        logger.info(f"   Jobs Shortlisted: {pipeline_state['score']['shortlisted']}")
        if not dry_run:
            logger.info(f"   Resumes Generated: {sum(1 for p in pdf_paths if p)}")
            logger.info(f"   Results saved to:  {path}")
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
# FLASK ROUTES
# ══════════════════════════════════════════════
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    print(f"DEBUG: serve_react called with path: {path}")
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/start', methods=['POST'])
def start_pipeline():
    if pipeline_state["running"]:
        return jsonify({"error": "A pipeline is already running"}), 400
    
    # Read platform selections from frontend toggles
    data = request.get_json(silent=True) or {}
    platforms = data.get('platforms', ["linkedin", "indeed"])
    dry_run = data.get('dry_run', False)
    
    stop_event.clear()
    thread = threading.Thread(target=run_pipeline, args=(platforms, dry_run))
    thread.daemon = True
    thread.start()
    return jsonify({"message": "Started successfully"})


@app.route('/api/test-start', methods=['POST'])
def start_test_pipeline():
    if pipeline_state["running"]:
        return jsonify({"error": "A pipeline is already running"}), 400
    
    # Read platform selections from frontend toggles
    data = request.get_json(silent=True) or {}
    platforms = data.get('platforms', ["linkedin", "indeed"])
    
    stop_event.clear()
    thread = threading.Thread(target=run_pipeline, args=(platforms, False, True))
    thread.daemon = True
    thread.start()
    return jsonify({"message": "Test pipeline started"})


@app.route('/api/stop', methods=['POST'])
def stop_pipeline():
    stop_event.set()
    pipeline_state["running"] = False
    pipeline_state["phase"] = "idle"
    pipeline_state["status_text"] = "Aborted by user."
    return jsonify({"message": "Pipeline aborted."})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(pipeline_state)

import time
@app.route('/api/stream')
def stream_status():
    def event_stream():
        last_state = None
        while True:
            current_state = json.dumps(pipeline_state)
            if current_state != last_state:
                yield f"data: {current_state}\n\n"
                last_state = current_state
            time.sleep(0.5)
            
    return Response(event_stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    })

@app.route('/api/runs/<run_id>', methods=['DELETE'])
def api_delete_run(run_id):
    from src.db import delete_pipeline_run
    try:
        pdf_paths = delete_pipeline_run(run_id)
        # delete local files
        deleted_count = 0
        for path_str in pdf_paths:
            if path_str:
                p = Path(path_str)
                if p.exists():
                    p.unlink()
                    deleted_count += 1
        return jsonify({"message": f"Run deleted. {deleted_count} local PDFs removed."})
    except Exception as e:
        logger.error(f"Error deleting run: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/resume/<job_id>', methods=['GET'])
def api_get_resume(job_id):
    from src.db import get_job_pdf_path
    try:
        # Prevent Supabase 22P02 error for legacy 8-char unique_ids
        if len(job_id) < 36:
            return jsonify({"error": "Resume not found (Legacy ID format no longer supported)."}), 404
            
        pdf_path = get_job_pdf_path(job_id)
        
        # If it's a running pipeline, it might be in the in-memory state
        if not pdf_path:
            for item in pipeline_state.get("tailor", {}).get("results", []):
                if item["id"] == job_id:
                    pdf_path = item.get("pdf_path")
                    break
                    
        if not pdf_path:
            return jsonify({"error": "Resume not found in DB or has been cleaned up."}), 404
            
        if pdf_path.startswith("http"):
            # It's a Supabase URL! Let's bypass the 504 Gateway Timeout by finding it locally.
            filename = pdf_path.split("/")[-1]
            found_local = None
            
            config = load_config()
            output_dir = os.path.join(config['output']['desktop_path'], config['output']['folder_name'])
            search_dirs = [os.path.join(output_dir, "main pipeline"), os.path.join(output_dir, "test")]
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    for root, dirs, files in os.walk(search_dir):
                        if filename in files:
                            found_local = os.path.join(root, filename)
                            break
                    if found_local:
                        break
            
            if found_local:
                return send_file(found_local, mimetype='application/pdf')
            else:
                # Fallback to redirect if not found locally
                return redirect(pdf_path)
            
        if os.path.exists(pdf_path):
            return send_file(pdf_path, mimetype='application/pdf')
            
        return jsonify({"error": "Resume not found or local file deleted"}), 404
    except Exception as e:
        logger.error(f"Error fetching resume: {e}")
        return jsonify({"error": str(e)}), 500



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


from src.models import Job
from uuid import uuid4

@app.route('/api/manual-tailor/score', methods=['POST'])
def manual_tailor_score():
    data = request.get_json()
    job_description = data.get('job_description', '')
    job_title = data.get('job_title', 'Unknown Role')
    company = data.get('company', 'Unknown Company')
    
    job = Job(title=job_title, company=company, location='Remote',
              description=job_description, url='', id=str(uuid4()))
    
    # Run scoring in test_mode to ensure it returns even if score < 50
    scored_jobs = score_jobs([job], test_mode=True)
    if not scored_jobs:
        return jsonify({"error": "Failed to score job"}), 500
        
    scored_job = scored_jobs[0]
    return jsonify({
        "score": scored_job.score,
        "reason": scored_job.reasons,
        "missing_skills": scored_job.missing_skills,
        "extracted_requirements": scored_job.extracted_requirements,
        "is_testing_role": scored_job.is_testing_role
    })

@app.route('/api/manual-tailor/generate', methods=['POST'])
def manual_tailor_generate():
    data = request.get_json()
    
    job = Job(
        title=data.get('job_title', 'Unknown Role'),
        company=data.get('company', 'Unknown Company'),
        location='Remote',
        description=data.get('job_description', ''),
        url='',
        id=str(uuid4()),
        score=data.get('score', 0),
        missing_skills=data.get('missing_skills', []),
        extracted_requirements=data.get('extracted_requirements', ''),
        is_testing_role=data.get('is_testing_role', False)
    )
    
    selected_skills = data.get('selected_skills', [])
    
    from src.resume_tailor import tailor_resume_with_skills
    pdf_path = tailor_resume_with_skills(job, selected_skills)
    
    if not pdf_path:
        return jsonify({"error": "Failed to generate resume"}), 500
        
    filename = os.path.basename(pdf_path)
    return jsonify({"pdf_url": f"/api/resume/manual/{filename}"})

@app.route('/api/resume/manual/<filename>', methods=['GET'])
def get_manual_resume(filename):
    manual_dir = os.path.join(os.getcwd(), "output", "manual")
    if not os.path.exists(manual_dir):
        os.makedirs(manual_dir)
    return send_from_directory(manual_dir, filename)

if __name__ == '__main__':
    logger.info("🌐 Starting AutoApply Dashboard on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)