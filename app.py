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
import time
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
from src.db import save_pipeline_results, supabase
from src.ai_engine import runtime_settings
from datetime import datetime, timezone
from flask_cors import CORS

app = Flask(__name__, static_folder='frontend/dist')
CORS(app)

# ══════════════════════════════════════════════
# SUPABASE REALTIME SYNCER
# ══════════════════════════════════════════════
last_synced_state = None
def sync_state_to_supabase():
    global last_synced_state
    while True:
        time.sleep(2)
        if not supabase: continue
        current_state = json.dumps(pipeline_state, default=str)
        if current_state != last_synced_state:
            try:
                supabase.table("live_pipeline").upsert({
                    "id": 1,
                    "phase": pipeline_state["phase"],
                    "running": pipeline_state["running"],
                    "mode": pipeline_state["mode"],
                    "status_text": pipeline_state["status_text"],
                    "scan_data": pipeline_state["scan"],
                    "score_data": pipeline_state["score"],
                    "tailor_data": pipeline_state["tailor"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                last_synced_state = current_state
            except Exception as e:
                logger.error(f"Live sync failed: {e}")

threading.Thread(target=sync_state_to_supabase, daemon=True).start()


# ══════════════════════════════════════════════
# PIPELINE STATE MACHINES
# ══════════════════════════════════════════════
stop_event = threading.Event()
resume_generation_event = threading.Event()
pipeline_lock = threading.Lock()
pending_pipeline_data = {}

pipeline_state = {
    "running": False,
    "mode": "idle",           # idle | prod | test
    "phase": "idle",          # idle | scanning | filtering | scoring | review | tailoring | saving | done | error
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
    "shortlisted_jobs": [],
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

def get_single_sentence_summary(job):
    """Derives a concise single-sentence summary explaining what the job is."""
    # 1. Direct explicit job_summary if present
    job_summary = getattr(job, 'job_summary', None)
    if job_summary and isinstance(job_summary, str) and job_summary.strip():
        s = job_summary.strip()
        return s if s.endswith(('.', '!', '?')) else s + '.'

    title = getattr(job, 'title', 'Role') or 'Role'
    company = getattr(job, 'company', 'Company') or 'Company'
    reqs = getattr(job, 'extracted_requirements', '') or ''
    if '|||REASON|||' in reqs:
        reqs = reqs.split('|||REASON|||')[0].strip()

    # 2. Check if description has an introductory role sentence
    desc = getattr(job, 'description', '') or ''
    if desc:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', desc) if s.strip()]
        for sent in sentences:
            sent_clean = ' '.join(sent.split())
            if 20 <= len(sent_clean) <= 180:
                sent_lower = sent_clean.lower()
                if any(kw in sent_lower for kw in ['looking for', 'seeking', 'responsible for', 'role is', 'position is', 'you will', 'engineer to', 'developer to', 'team is looking', 'join our']):
                    return sent_clean if sent_clean.endswith(('.', '!', '?')) else sent_clean + '.'

    # 3. If extracted requirements exist, synthesize role explanation
    if reqs:
        return f"{title} role at {company} requiring {reqs}."

    # 4. If reasons is present and not merely score evaluation, use it if needed
    reasons = getattr(job, 'reasons', None)
    if reasons:
        r_str = str(reasons[0]).strip() if isinstance(reasons, list) and reasons else str(reasons).strip()
        if r_str and len(r_str) > 10 and not any(neg in r_str.lower() for neg in ['lacks', 'score', 'missing', 'penalty', 'threshold']):
            return r_str if r_str.endswith(('.', '!', '?')) else r_str + '.'

    return f"{title} position at {company}."

def extract_number(text):
    match = re.search(r'\d+', text)
    return int(match.group()) if match else 0

def pipeline_log_interceptor(message):
    """Parses log messages to update pipeline_state for the dashboard.
    
    NOTE: total_found is ONLY incremented by the on_job_scraped callback.
    The log interceptor must NOT touch total_found — doing so caused a
    triple-counting bug where log messages like 'Found 200 jobs' added
    their number on top of the per-job callback increments.
    """
    text = message.record["message"]
    text_lower = text.lower()
    
    pipeline_state["status_text"] = text
    if "scraping" in text_lower and "linkedin" in text_lower:
        pipeline_state["scan"]["current_platform"] = "linkedin"
    elif "scraping" in text_lower and "indeed" in text_lower:
        pipeline_state["scan"]["current_platform"] = "indeed"
    elif "pre-filter" in text_lower:
        pipeline_state["phase"] = "filtering"

# Add the interceptor to Loguru
logger.add(pipeline_log_interceptor, format="{message}")



# ══════════════════════════════════════════════
# EVENT CALLBACKS
# ══════════════════════════════════════════════
def on_cycle_start(cycle_data):
    if stop_event.is_set():
        return
    if isinstance(cycle_data, dict):
        if "wait_time" in cycle_data:
            pipeline_state["status_text"] = cycle_data["message"]
            pipeline_state["scan"]["is_waiting"] = True
            pipeline_state["scan"]["wait_time"] = cycle_data["wait_time"]
            logger.info(f"Wait Delay: {cycle_data['wait_time']}s")
        else:
            pipeline_state["scan"]["current_params"] = cycle_data
            pipeline_state["status_text"] = f"Scraping {cycle_data.get('term', '')} in {cycle_data.get('loc', '')}..."
            pipeline_state["scan"]["is_waiting"] = False
            logger.info(f"--- UI CYCLE UPDATED TO: {cycle_data.get('current_cycle')} ---")
    else:
        pipeline_state["status_text"] = str(cycle_data)
        pipeline_state["scan"]["is_waiting"] = False

def on_job_scraped(job_dict):
    if stop_event.is_set():
        return
    pipeline_state["scan"]["total_found"] += 1
    pipeline_state["scan"]["live_jobs"].insert(0, job_dict)
    if len(pipeline_state["scan"]["live_jobs"]) > 100:
        pipeline_state["scan"]["live_jobs"].pop()

def on_job_dropped(title, company, reason):
    if stop_event.is_set():
        return
    if len(pipeline_state["filter"]["dropped_jobs"]) < 100:
        pipeline_state["filter"]["dropped_jobs"].insert(0, {"title": str(title), "company": str(company), "reason": str(reason)})

def on_score_start(job_id, title, company):
    if stop_event.is_set():
        return
    pipeline_state["score"]["live_scores"].insert(0, {"id": job_id, "title": str(title), "company": str(company), "status": "scoring", "score": None})

def on_score_complete(job_id, score, reason=""):
    if stop_event.is_set():
        return
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
def run_pipeline(platforms, job_types=None, dry_run=False, test_mode=False):
    """Background thread that runs the full pipeline for both PROD and TEST modes."""
    global pipeline_state
    try:
        pipeline_state["running"] = True
        pipeline_state["mode"] = "test" if test_mode else "prod"
        pipeline_state["phase"] = "scanning"
        pipeline_state["scan"]["current_params"] = None
        pipeline_state["scan"]["live_jobs"] = []
        pipeline_state["scan"]["total_found"] = 0
        pipeline_state["filter"]["dropped_jobs"] = []
        pipeline_state["score"]["live_scores"] = []
        pipeline_state["tailor"]["results"] = []
        
        mode_label = " [TEST MODE]" if test_mode else ""
        logger.info(f"🚀 Pipeline started!{mode_label}")

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 1/4: SCRAPING JOBS")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        jobs, scrape_stats = run_scraper(selected_platforms=platforms, selected_job_types=job_types, test_mode=test_mode, callbacks=callbacks, stop_event=stop_event)
        # NOTE: Do NOT overwrite total_found here — the on_job_scraped callback
        # is the single source of truth and has been incrementing it live.
        # Overwriting caused the UI counter to jump erratically.
        pipeline_state["filter"]["after"] = scrape_stats.get("reached_scoring", len(jobs))

        if stop_event.is_set():
            logger.info("🛑 Pipeline aborted during scraping phase.")
            return

        if not jobs:
            logger.warning("⚠️ No jobs found matching your criteria.")
            with pipeline_lock:
                pipeline_state["running"] = False
                pipeline_state["phase"] = "done"
            return

        pipeline_state["phase"] = "scoring"
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("PHASE 2/4: AI SCORING")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        if test_mode:
            logger.info("🧪 TEST MODE: Scoring all jobs, but limiting resumes to 3.")
            
        scored_jobs = score_jobs(jobs, test_mode=test_mode, callbacks=callbacks, stop_event=stop_event)

        if stop_event.is_set():
            logger.info("🛑 Pipeline aborted during scoring phase.")
            return

        pipeline_state["score"]["scored"] = len(scored_jobs)
        raw_scored = getattr(scored_jobs, "all_scored_jobs", scored_jobs) or []
        pipeline_state["all_scored_jobs"] = [
            {
                "id": getattr(j, "id", ""),
                "title": getattr(j, "title", ""),
                "company": getattr(j, "company", ""),
                "location": getattr(j, "location", ""),
                "score": getattr(j, "score", 0),
                "reasons": getattr(j, "reasons", []),
                "summary": get_single_sentence_summary(j),
                "missing_skills": getattr(j, "missing_skills", []),
                "extracted_requirements": getattr(j, "extracted_requirements", ""),
                "is_testing_role": getattr(j, "is_testing_role", False),
                "tokens_used": getattr(j, "tokens_used", 0),
                "cost_usd": getattr(j, "cost_usd", 0.0),
                "token_usage": getattr(j, "token_usage", {}) or {},
            }
            if not isinstance(j, dict) else j
            for j in raw_scored
        ]

        if not scored_jobs:
            logger.warning("⚠️ No jobs met the minimum score threshold.")
            with pipeline_lock:
                pipeline_state["running"] = False
                pipeline_state["phase"] = "done"
            return

        time_format = datetime.now().strftime('%d%b-%H-%M').lower()
        date_str = f"test/{time_format}" if test_mode else f"main pipeline/{time_format}"

        if test_mode:
            shortlisted = scored_jobs[:3]
            logger.info("🧪 TEST MODE: Shortlisted top 3 jobs for review.")
        else:
            shortlisted = scored_jobs
            logger.info(f"Shortlisted all {len(shortlisted)} jobs that passed the threshold for review.")
            
        pipeline_state["score"]["shortlisted"] = len(shortlisted)

        # ── INTERACTIVE REVIEW PHASE ──
        # Pause execution so user can review shortlisted jobs & select missing skills to embed
        resume_generation_event.clear()
        with pipeline_lock:
            pending_pipeline_data.clear()
            pending_pipeline_data["shortlisted"] = shortlisted
            pending_pipeline_data["date_str"] = date_str
            pending_pipeline_data["dry_run"] = dry_run
            pending_pipeline_data["test_mode"] = test_mode
            pending_pipeline_data["scored_jobs"] = scored_jobs
            pending_pipeline_data["user_selections"] = None

            pipeline_state["shortlisted_jobs"] = [
                {
                    "id": getattr(j, "id", ""),
                    "title": getattr(j, "title", ""),
                    "company": getattr(j, "company", ""),
                    "location": getattr(j, "location", ""),
                    "score": getattr(j, "score", 0),
                    "reasons": getattr(j, "reasons", []),
                    "summary": get_single_sentence_summary(j),
                    "missing_skills": list(getattr(j, "missing_skills", []) or []),
                    "extracted_requirements": getattr(j, "extracted_requirements", "") or "",
                    "is_testing_role": getattr(j, "is_testing_role", False),
                    "url": getattr(j, "url", "") or "",
                }
                for j in shortlisted
            ]
            pipeline_state["phase"] = "review"
            pipeline_state["status_text"] = f"Scoring complete. {len(shortlisted)} jobs shortlisted for review."

        logger.info(f"⏸️ Pipeline paused: Waiting for user to review {len(shortlisted)} shortlisted jobs...")
        resume_generation_event.wait()

        if stop_event.is_set():
            logger.info("🛑 Pipeline aborted during review phase.")
            return

        # Apply user selections
        user_selections = pending_pipeline_data.get("user_selections")
        if user_selections is not None:
            selected_map = {
                str(item["id"]).strip(): [str(s).strip() for s in item.get("selected_skills", []) if str(s).strip()]
                for item in user_selections if isinstance(item, dict) and "id" in item
            }
            shortlisted = [j for j in shortlisted if str(getattr(j, "id", "")).strip() in selected_map]
            for j in shortlisted:
                j.user_selected_skills = selected_map.get(str(getattr(j, "id", "")).strip(), [])

        if not shortlisted:
            logger.warning("⚠️ No jobs selected for resume generation.")
            with pipeline_lock:
                pipeline_state["running"] = False
                pipeline_state["phase"] = "done"
                pipeline_state["status_text"] = "No jobs selected for resume generation."
                pipeline_state["shortlisted_jobs"] = []
            return

        pipeline_state["score"]["shortlisted"] = len(shortlisted)
        pipeline_state["phase"] = "tailoring"
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"PHASE 3/4: TAILORING RESUMES & PDFS ({len(shortlisted)} jobs selected)")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        from src.resume_tailor import tailor_resume
        from src.pdf_generator import generate_pdf
        from playwright.sync_api import sync_playwright

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
            tailored_jsons = tailor_resumes_batch(shortlisted, stop_event=stop_event)
            
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
                tailored_jsons = tailor_resumes_batch(shortlisted, stop_event=stop_event)
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    for i, (job, tailored_data) in enumerate(zip(shortlisted, tailored_jsons)):
                        if stop_event.is_set():
                            logger.info("🛑 PDF generation aborted.")
                            break
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

            save_pipeline_results(
                pipeline_state,
                shortlisted,
                pdf_paths,
                all_scored_jobs=getattr(scored_jobs, "all_scored_jobs", scored_jobs),
            )
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
        with pipeline_lock:
            if stop_event.is_set():
                pipeline_state["phase"] = "idle"
                pipeline_state["running"] = False
                pipeline_state["status_text"] = "Aborted by user."
                pipeline_state["shortlisted_jobs"] = []
            else:
                pipeline_state["phase"] = "done"
                pipeline_state["running"] = False


# ══════════════════════════════════════════════
# FLASK ROUTES
# ══════════════════════════════════════════════
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    target_path = os.path.join(app.static_folder, path) if path else os.path.join(app.static_folder, 'index.html')
    if path != "" and os.path.exists(target_path):
        return send_from_directory(app.static_folder, path)
    else:
        index_file = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_file):
            return send_from_directory(app.static_folder, 'index.html')
        return "Frontend dist not built. Please run npm run build in frontend/", 404


@app.route('/api/start', methods=['POST'])
def start_pipeline():
    raw_data = request.get_json(silent=True)
    if raw_data is not None and not isinstance(raw_data, dict):
        return jsonify({"error": "Invalid JSON payload, expected an object"}), 400
    data = raw_data or {}

    with pipeline_lock:
        if pipeline_state["running"]:
            return jsonify({"error": "A pipeline is already running"}), 400
        pipeline_state["running"] = True
        pipeline_state["mode"] = "prod"

    platforms = data.get('platforms', ["linkedin", "indeed"])
    job_types = data.get('job_types', ["fulltime", "internship"])
    dry_run = data.get('dry_run', False)

    try:
        # Apply AI model settings from frontend
        _apply_ai_settings(data)
        stop_event.clear()
        resume_generation_event.clear()
        pending_pipeline_data.clear()
        pipeline_state["shortlisted_jobs"] = []
        thread = threading.Thread(target=run_pipeline, args=(platforms, job_types, dry_run, False))
        thread.daemon = True
        thread.start()
    except Exception as e:
        with pipeline_lock:
            pipeline_state["running"] = False
            pipeline_state["mode"] = "idle"
        logger.error(f"Failed to start pipeline: {e}")
        return jsonify({"error": f"Failed to start pipeline: {e}"}), 500

    return jsonify({"message": "Started successfully"})


@app.route('/api/test-start', methods=['POST'])
def start_test_pipeline():
    raw_data = request.get_json(silent=True)
    if raw_data is not None and not isinstance(raw_data, dict):
        return jsonify({"error": "Invalid JSON payload, expected an object"}), 400
    data = raw_data or {}

    with pipeline_lock:
        if pipeline_state["running"]:
            return jsonify({"error": "A pipeline is already running"}), 400
        pipeline_state["running"] = True
        pipeline_state["mode"] = "test"

    platforms = data.get('platforms', ["linkedin", "indeed"])
    job_types = data.get('job_types', ["fulltime", "internship"])

    try:
        # Apply AI model settings from frontend
        _apply_ai_settings(data)
        stop_event.clear()
        resume_generation_event.clear()
        pending_pipeline_data.clear()
        pipeline_state["shortlisted_jobs"] = []
        thread = threading.Thread(target=run_pipeline, args=(platforms, job_types, False, True))
        thread.daemon = True
        thread.start()
    except Exception as e:
        with pipeline_lock:
            pipeline_state["running"] = False
            pipeline_state["mode"] = "idle"
        logger.error(f"Failed to start test pipeline: {e}")
        return jsonify({"error": f"Failed to start test pipeline: {e}"}), 500

    return jsonify({"message": "Test pipeline started"})


@app.route('/api/stop', methods=['POST'])
def stop_pipeline():
    with pipeline_lock:
        stop_event.set()
        resume_generation_event.set()
        pipeline_state["running"] = False
        pipeline_state["phase"] = "idle"
        pipeline_state["status_text"] = "Aborted by user."
        pipeline_state["shortlisted_jobs"] = []
        pending_pipeline_data.clear()
    return jsonify({"message": "Pipeline aborted."})


@app.route('/api/generate-resumes', methods=['POST'])
def api_generate_resumes():
    if request.is_json and request.data.strip():
        raw_data = request.get_json(silent=True)
        if raw_data is None:
            return jsonify({"error": "Invalid JSON payload"}), 400
    else:
        raw_data = request.get_json(silent=True)

    if raw_data is not None and not isinstance(raw_data, dict):
        return jsonify({"error": "Invalid JSON payload, expected an object"}), 400
    data = raw_data or {}
    if "selected_jobs" in data and not isinstance(data["selected_jobs"], list):
        return jsonify({"error": "selected_jobs must be a list"}), 400
    selected_jobs = data.get("selected_jobs", [])

    with pipeline_lock:
        if pipeline_state.get("phase") != "review":
            return jsonify({"error": "Pipeline is not in review phase"}), 400
        pending_pipeline_data["user_selections"] = selected_jobs
        pipeline_state["phase"] = "tailoring"
        pipeline_state["status_text"] = "Tailoring resumes with your selected skills..."
        resume_generation_event.set()

    return jsonify({"message": "Resume generation started", "count": len(selected_jobs)})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(pipeline_state)

import time
@app.route('/api/stream')
def stream_status():
    def event_stream():
        last_state = None
        while True:
            current_state = json.dumps(pipeline_state, default=str)
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

@app.route('/api/applications/<app_id>', methods=['DELETE'])
def delete_app_endpoint(app_id):
    from src.db import delete_application
    try:
        pdf_path = delete_application(app_id)
        if pdf_path:
            p = Path(pdf_path)
            if p.exists():
                p.unlink()
        return jsonify({"message": "Application deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting application: {e}")
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
        try:
            logs.append(log_queue.get_nowait())
        except Exception:
            break
    return jsonify(logs)


@app.route('/api/config', methods=['GET'])
def get_config_api():
    config = load_config()
    return jsonify(config)


def _apply_ai_settings(data: dict):
    """Apply AI model/thinking settings from frontend request to runtime_settings."""
    if not isinstance(data, dict):
        return
    if 'scoring_model' in data:
        runtime_settings['scoring_model'] = data['scoring_model']
    if 'scoring_thinking' in data:
        runtime_settings['scoring_thinking'] = bool(data['scoring_thinking'])
    if 'tailoring_model' in data:
        runtime_settings['tailoring_model'] = data['tailoring_model']
    if 'tailoring_thinking' in data:
        runtime_settings['tailoring_thinking'] = bool(data['tailoring_thinking'])
    logger.info(
        f"\u2699\ufe0f AI Settings: "
        f"Scoring=[{runtime_settings['scoring_model']}, thinking={'ON' if runtime_settings['scoring_thinking'] else 'OFF'}] | "
        f"Tailoring=[{runtime_settings['tailoring_model']}, thinking={'ON' if runtime_settings['tailoring_thinking'] else 'OFF'}]"
    )


@app.route('/api/ai-settings', methods=['GET'])
def get_ai_settings():
    """Return current AI runtime settings for the frontend."""
    return jsonify(runtime_settings)


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

@app.route('/api/pending-tailors', methods=['GET'])
def get_pending_tailors():
    if not supabase: return jsonify([])
    try:
        # Get tracked jobs with empty or null pdf_filename
        res = supabase.table('tracked_jobs').select('*').or_('pdf_filename.eq."",pdf_filename.is.null').order('score', desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/manual-tailor/score', methods=['POST'])
def manual_tailor_score():
    raw_data = request.get_json(silent=True)
    if raw_data is not None and not isinstance(raw_data, dict):
        return jsonify({"error": "Invalid JSON payload, expected an object"}), 400
    data = raw_data or {}
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
    raw_data = request.get_json(silent=True)
    if raw_data is not None and not isinstance(raw_data, dict):
        return jsonify({"error": "Invalid JSON payload, expected an object"}), 400
    data = raw_data or {}
    
    job = Job(
        title=data.get('job_title', 'Unknown Role'),
        company=data.get('company', 'Unknown Company'),
        location='Remote',
        description=data.get('job_description', ''),
        url=data.get('url', ''),
        id=data.get('id') or str(uuid4()),
        score=data.get('score', 0),
        missing_skills=data.get('missing_skills', []),
        extracted_requirements=data.get('extracted_requirements', ''),
        is_testing_role=data.get('is_testing_role', False)
    )
    job.run_id = data.get('run_id')
    
    selected_skills = data.get('selected_skills', [])
    
    from src.resume_tailor import tailor_resume_with_skills
    pdf_path = tailor_resume_with_skills(job, selected_skills)
    
    if not pdf_path:
        return jsonify({"error": "Failed to generate resume"}), 500
        
    from src.db import save_manual_job
    save_manual_job(job, pdf_path)
    
    filename = os.path.basename(pdf_path)
    return jsonify({"pdf_url": f"/api/resume/manual/{filename}"})

@app.route('/api/manual-tailor/generate-batch', methods=['POST'])
def manual_tailor_generate_batch():
    raw_data = request.get_json(silent=True)
    if raw_data is not None and not isinstance(raw_data, dict):
        return jsonify({"error": "Invalid JSON payload, expected an object"}), 400
    data = raw_data or {}
    
    jobs_data = data.get('jobs', [])
    if not jobs_data:
        return jsonify({"error": "No jobs provided for batch generation"}), 400
        
    jobs_to_process = []
    selected_skills_list = []
    
    for j_data in jobs_data:
        job = Job(
            title=j_data.get('job_title', 'Unknown Role'),
            company=j_data.get('company', 'Unknown Company'),
            location='Remote',
            description=j_data.get('job_description', ''),
            url=j_data.get('url', ''),
            id=j_data.get('id') or str(uuid4()),
            score=j_data.get('score', 0),
            missing_skills=j_data.get('missing_skills', []),
            extracted_requirements=j_data.get('extracted_requirements', ''),
            is_testing_role=j_data.get('is_testing_role', False)
        )
        jobs_to_process.append(job)
        selected_skills_list.append(j_data.get('selected_skills', []))
        
    from src.resume_tailor import tailor_resume_with_skills
    pdf_paths = []
    generated_results = []
    
    for job, skills in zip(jobs_to_process, selected_skills_list):
        try:
            pdf_path = tailor_resume_with_skills(job, skills)
            pdf_paths.append(pdf_path)
            
            if pdf_path:
                filename = os.path.basename(pdf_path)
                generated_results.append({
                    "id": job.id,
                    "pdf_url": f"/api/resume/manual/{filename}"
                })
            else:
                generated_results.append({
                    "id": job.id,
                    "error": "Failed to generate resume"
                })
        except Exception as e:
            logger.error(f"Error generating resume for {job.id}: {e}")
            pdf_paths.append("")
            generated_results.append({"id": job.id, "error": str(e)})
            
    # Save the entire batch to Supabase under one pipeline run
    from src.db import save_manual_jobs_batch
    save_manual_jobs_batch(jobs_to_process, pdf_paths)
    
    return jsonify({"results": generated_results})

@app.route('/api/resume/manual/<filename>', methods=['GET'])
def get_manual_resume(filename):
    manual_dir = os.path.join(os.getcwd(), "output", "manual")
    if not os.path.exists(manual_dir):
        os.makedirs(manual_dir)
    return send_from_directory(manual_dir, filename)


if __name__ == '__main__':
    logger.info("🌐 Starting AutoApply Dashboard on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)