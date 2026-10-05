"""
Standalone FastAPI Web Server for Job Evaluation Dashboard.

Completely independent of the main backend (no Flask, no Supabase, no scraper imports).
Provides:
- File upload for raw dataset JSON
- 1-click loading of existing datasets in data_folder/
- Dual-provider concurrent or load-balanced execution (Gemini + Groq)
- Real-time Server-Sent Events (SSE) log & status streaming
- Instant table filtering (All, Selected/Accepted, Non-Selected/Rejected)
- Summary metrics and CSV/JSON export
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Fix Windows stdout encoding for UTF-8 terminal logs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from standalone_dashboard.engine import StandaloneScoringEngine, ScoringResult

load_dotenv()

# Logger setup
logger = logging.getLogger("dashboard_server")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

app = FastAPI(title="AutoApply Standalone Evaluation Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# In-Memory State
# ─────────────────────────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self.current_filename: str = ""
        self.is_running: bool = False
        self.stop_requested: bool = False
        self.task: Optional[asyncio.Task] = None
        self.engine: StandaloneScoringEngine = StandaloneScoringEngine()
        
        # Statistics
        self.threshold: int = 60
        self.mode: str = "load_balanced"  # load_balanced, gemini, groq, failover
        self.processed_count: int = 0
        self.accepted_count: int = 0
        self.rejected_count: int = 0
        self.gemini_count: int = 0
        self.groq_count: int = 0
        self.total_latency: float = 0.0
        self.total_score: float = 0.0
        
        # Logs
        self.logs: List[Dict[str, Any]] = []
        self.subscribers: List[asyncio.Queue] = []
        self.lock = asyncio.Lock()

    def reset_stats(self):
        self.processed_count = 0
        self.accepted_count = 0
        self.rejected_count = 0
        self.gemini_count = 0
        self.groq_count = 0
        self.total_latency = 0.0
        self.total_score = 0.0

    async def broadcast_log(self, text: str, level: str = "INFO", category: str = "general"):
        """Print log to terminal console and broadcast via SSE to UI."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "time": timestamp,
            "text": text,
            "level": level,
            "category": category,
        }
        self.logs.append(entry)
        if len(self.logs) > 1000:
            self.logs = self.logs[-800:]

        # Terminal Log Output
        print(f"[{timestamp}] [{level.upper()}] {text}", flush=True)

        # Broadcast SSE event
        msg = json.dumps({"type": "log", "data": entry})
        dead = []
        for q in self.subscribers:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for d in dead:
            if d in self.subscribers:
                self.subscribers.remove(d)

    async def broadcast_update(self, job_update: Optional[Dict[str, Any]] = None):
        """Broadcast status update and optional individual job result."""
        status_data = self.get_summary()
        payload = {"type": "update", "summary": status_data}
        if job_update:
            payload["job"] = job_update

        msg = json.dumps(payload)
        dead = []
        for q in self.subscribers:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for d in dead:
            if d in self.subscribers:
                self.subscribers.remove(d)

    def get_summary(self) -> Dict[str, Any]:
        avg_score = round(self.total_score / self.processed_count, 1) if self.processed_count > 0 else 0
        avg_latency = round(self.total_latency / self.processed_count, 2) if self.processed_count > 0 else 0
        return {
            "is_running": self.is_running,
            "current_filename": self.current_filename,
            "total_jobs": len(self.jobs),
            "processed": self.processed_count,
            "accepted": self.accepted_count,
            "rejected": self.rejected_count,
            "gemini_count": self.gemini_count,
            "groq_count": self.groq_count,
            "avg_score": avg_score,
            "avg_latency": avg_latency,
            "threshold": self.threshold,
            "mode": self.mode,
        }


state = AppState()

# Mount static and template dirs
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Parse Dataset JSON
# ─────────────────────────────────────────────────────────────────────────────

def normalize_jobs_data(raw_data: Any) -> List[Dict[str, Any]]:
    """Convert various JSON formats into a standardized list of jobs."""
    raw_list = []
    if isinstance(raw_data, list):
        raw_list = raw_data
    elif isinstance(raw_data, dict):
        for key in ["jobs", "data", "results", "items", "dataset"]:
            if key in raw_data and isinstance(raw_data[key], list):
                raw_list = raw_data[key]
                break
        if not raw_list:
            # Map of objects
            raw_list = list(raw_data.values())

    standardized = []
    for idx, item in enumerate(raw_list):
        if not isinstance(item, dict):
            continue

        job_id = str(item.get("id") or item.get("job_id") or item.get("job_index") or f"job_{idx+1}")
        title = str(item.get("title") or item.get("role") or item.get("job_title") or "Unknown Title").strip()
        company = str(item.get("company") or item.get("company_name") or "Unknown Company").strip()
        location = str(item.get("location") or "Not Specified").strip()
        description = str(item.get("description") or item.get("job_description") or item.get("jd") or "").strip()
        url = str(item.get("job_url") or item.get("url") or item.get("link") or "").strip()

        standardized.append({
            "id": job_id,
            "index": idx + 1,
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "url": url,
            "status": "pending",  # pending, scored, failed
            "decision": None,    # ACCEPTED, REJECTED
            "fit_score": None,
            "is_testing_role": None,
            "missing_skills": [],
            "reasoning": "",
            "single_line_log": "",
            "provider": None,
            "model": None,
            "latency_seconds": None,
            "scored_at": None,
        })

    return standardized


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = TEMPLATES_DIR / "index.html"
    if not html_file.exists():
        return HTMLResponse("<h1>Dashboard template not found.</h1>", status_code=500)
    with open(html_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/config")
async def get_config():
    """Return configured providers and status."""
    has_gemini = bool(state.engine.gemini_api_key)
    has_groq = bool(state.engine.groq_api_key)
    return {
        "gemini": {
            "configured": has_gemini,
            "model": state.engine.gemini_model,
            "rpm_limit": state.engine.gemini_limiter.rpm,
            "key_preview": f"••••{state.engine.gemini_api_key[-6:]}" if has_gemini else "",
        },
        "groq": {
            "configured": has_groq,
            "model": state.engine.groq_model,
            "rpm_limit": state.engine.groq_limiter.rpm,
            "key_preview": f"••••{state.engine.groq_api_key[-6:]}" if has_groq else "",
        },
        "default_threshold": state.threshold,
    }


@app.post("/api/update_keys")
async def update_keys(data: Dict[str, str]):
    """Update API keys from the UI if user wants to change them."""
    gemini_key = data.get("gemini_key", "").strip()
    groq_key = data.get("groq_key", "").strip()
    state.engine.update_keys(gemini_key=gemini_key or None, groq_key=groq_key or None)
    await state.broadcast_log("API keys updated from dashboard.", level="INFO")
    return {"status": "success", "message": "Keys updated successfully"}


@app.get("/api/available_datasets")
async def list_available_datasets():
    """List JSON datasets available in the workspace for 1-click loading."""
    datasets = []
    # Check data_folder
    data_dir = PROJECT_ROOT / "data_folder"
    if data_dir.exists():
        for p in data_dir.glob("*.json"):
            size_mb = round(p.stat().st_size / (1024 * 1024), 2)
            datasets.append({
                "name": p.name,
                "path": str(p),
                "size_mb": size_mb,
                "source": "data_folder"
            })
    # Check scoring_audit
    audit_dir = PROJECT_ROOT / "scoring_audit"
    if audit_dir.exists():
        for p in audit_dir.glob("*.json"):
            size_mb = round(p.stat().st_size / (1024 * 1024), 2)
            datasets.append({
                "name": p.name,
                "path": str(p),
                "size_mb": size_mb,
                "source": "scoring_audit"
            })
    return {"datasets": datasets}


@app.post("/api/load_dataset")
async def load_dataset(data: Dict[str, str]):
    """Load a dataset from workspace path."""
    if state.is_running:
        raise HTTPException(status_code=400, detail="Cannot load new dataset while evaluation is running.")

    file_path = data.get("path")
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Dataset file not found.")

    target = Path(file_path)
    try:
        with open(target, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse JSON: {e}")

    normalized = normalize_jobs_data(raw_data)
    state.jobs = normalized
    state.current_filename = target.name
    state.reset_stats()

    await state.broadcast_log(f"Loaded dataset '{target.name}' with {len(normalized)} jobs.", level="INFO")
    await state.broadcast_update()

    return {
        "status": "success",
        "filename": target.name,
        "total_jobs": len(normalized),
        "jobs": normalized[:15],  # initial sample preview
    }


@app.post("/api/upload")
async def upload_json(file: UploadFile = File(...)):
    """Upload a raw JSON dataset file."""
    if state.is_running:
        raise HTTPException(status_code=400, detail="Cannot upload while evaluation is running.")

    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed.")

    try:
        content = await file.read()
        raw_data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")

    normalized = normalize_jobs_data(raw_data)
    if not normalized:
        raise HTTPException(status_code=400, detail="No valid job descriptions could be parsed from this JSON.")

    state.jobs = normalized
    state.current_filename = file.filename
    state.reset_stats()

    await state.broadcast_log(f"Uploaded and parsed '{file.filename}' ({len(normalized)} jobs).", level="INFO")
    await state.broadcast_update()

    return {
        "status": "success",
        "filename": file.filename,
        "total_jobs": len(normalized),
        "jobs": normalized[:15],
    }


class StartEvaluationRequest(BaseModel):
    mode: str = "load_balanced"  # load_balanced, gemini, groq, failover
    threshold: int = 60
    limit: Optional[int] = None  # None for all, or integer for batch limit


async def run_evaluation_worker():
    """
    Background worker that iterates through jobs and evaluates them.
    Respects rate limits and logs every acceptance/rejection to terminal and UI.
    """
    state.is_running = True
    state.stop_requested = False
    
    total = len(state.jobs)
    mode = state.mode
    threshold = state.threshold

    await state.broadcast_log(
        f"🚀 Starting evaluation on {total} jobs | Mode: {mode.upper()} | Threshold: {threshold}/100",
        level="INFO"
    )

    # Provider alternator for load_balanced mode
    provider_toggle = 0

    for idx, job in enumerate(state.jobs):
        if state.stop_requested:
            await state.broadcast_log("⏹️ Evaluation stopped by user.", level="WARN")
            break

        if job["status"] == "scored":
            continue

        job["status"] = "processing"
        await state.broadcast_update()

        title = job.get("title", "Unknown Title")
        company = job.get("company", "Unknown Company")
        jd_text = job.get("description", "")

        # Determine preferred provider for this job
        if mode == "load_balanced":
            preferred = "gemini" if provider_toggle % 2 == 0 else "groq"
            provider_toggle += 1
        elif mode == "gemini":
            preferred = "gemini"
        elif mode == "groq":
            preferred = "groq"
        else:
            preferred = "gemini"

        try:
            res: ScoringResult = await state.engine.score_job(
                title=title,
                company=company,
                jd_text=jd_text,
                mode=mode,
                threshold=threshold,
                preferred_provider=preferred,
            )

            # Update job record
            job["status"] = "scored"
            job["decision"] = res.decision
            job["fit_score"] = res.fit_score
            job["is_testing_role"] = res.is_testing_role
            job["missing_skills"] = res.missing_skills
            job["reasoning"] = res.reasoning
            job["provider"] = res.provider
            job["model"] = res.model
            job["latency_seconds"] = res.latency_seconds
            job["scored_at"] = datetime.now(timezone.utc).isoformat()

            # Update statistics
            state.processed_count += 1
            state.total_latency += res.latency_seconds
            state.total_score += res.fit_score
            if res.decision == "ACCEPTED":
                state.accepted_count += 1
            else:
                state.rejected_count += 1

            if res.provider.lower() == "gemini":
                state.gemini_count += 1
            else:
                state.groq_count += 1

            # Format the single-line reason log cleanly as requested
            log_line = f"({res.provider} | Score: {res.fit_score}/100) {company} - {title} | Reason: {res.reasoning}"
            job["single_line_log"] = f"[{res.decision}] {log_line}"

            level = "ACCEPTED" if res.decision == "ACCEPTED" else "REJECTED"
            await state.broadcast_log(f"[{level}] {log_line}", level=level, category=res.decision.lower())
            await state.broadcast_update(job_update=job)

        except Exception as e:
            logger.error(f"Failed to score job {job['id']}: {e}")
            job["status"] = "failed"
            job["reasoning"] = f"Evaluation error: {str(e)[:100]}"
            await state.broadcast_log(f"[ERROR] Failed {company} - {title}: {e}", level="ERROR")
            await state.broadcast_update(job_update=job)

    state.is_running = False
    await state.broadcast_log(
        f"✅ Finished! Processed {state.processed_count}/{total} | Selected: {state.accepted_count} | Rejected: {state.rejected_count}",
        level="INFO"
    )
    await state.broadcast_update()


@app.post("/api/start")
async def start_evaluation(req: StartEvaluationRequest):
    """Start job evaluation process."""
    if state.is_running:
        raise HTTPException(status_code=400, detail="Evaluation is already in progress.")

    if not state.jobs:
        raise HTTPException(status_code=400, detail="No jobs uploaded. Please upload a dataset first.")

    state.mode = req.mode
    state.threshold = req.threshold

    if req.limit and req.limit > 0:
        state.jobs = state.jobs[: req.limit]

    state.task = asyncio.create_task(run_evaluation_worker())
    return {"status": "success", "message": "Evaluation started."}


@app.post("/api/stop")
async def stop_evaluation():
    """Cancel or stop current evaluation run."""
    if not state.is_running:
        return {"status": "info", "message": "Evaluation is not currently running."}

    state.stop_requested = True
    return {"status": "success", "message": "Stopping evaluation..."}


@app.post("/api/clear")
async def clear_data():
    """Clear all loaded jobs and results."""
    if state.is_running:
        raise HTTPException(status_code=400, detail="Cannot clear while running. Stop first.")

    state.jobs = []
    state.current_filename = ""
    state.reset_stats()
    state.logs = []
    await state.broadcast_log("Dashboard cleared.", level="INFO")
    await state.broadcast_update()
    return {"status": "success", "message": "Data cleared."}


@app.get("/api/status")
async def get_status():
    """Get current status, summary stats, and full job list."""
    return {
        "summary": state.get_summary(),
        "jobs": state.jobs,
        "logs": state.logs[-100:],  # return recent logs
    }


@app.get("/api/events")
async def events():
    """SSE streaming endpoint for live logs and real-time UI updates."""
    queue = asyncio.Queue()
    state.subscribers.append(queue)

    async def event_generator():
        # First send initial summary
        init_msg = json.dumps({"type": "init", "summary": state.get_summary()})
        yield f"data: {init_msg}\n\n"

        try:
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in state.subscribers:
                state.subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/export")
async def export_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    filter_by: str = Query("all", pattern="^(all|selected|rejected)$"),
):
    """Export scored jobs to CSV or JSON."""
    jobs_to_export = state.jobs
    if filter_by == "selected":
        jobs_to_export = [j for j in state.jobs if j.get("decision") == "ACCEPTED"]
    elif filter_by == "rejected":
        jobs_to_export = [j for j in state.jobs if j.get("decision") == "REJECTED"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jobs_scored_{filter_by}_{timestamp}.{format}"

    if format == "json":
        content = json.dumps(jobs_to_export, indent=2, ensure_ascii=False)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Title", "Company", "Location", "Decision",
            "Score", "Testing Role", "Missing Skills", "Reasoning",
            "Provider", "Model", "Latency (s)", "Job URL"
        ])
        for j in jobs_to_export:
            writer.writerow([
                j.get("id"),
                j.get("title"),
                j.get("company"),
                j.get("location"),
                j.get("decision"),
                j.get("fit_score"),
                j.get("is_testing_role"),
                ", ".join(j.get("missing_skills", [])),
                j.get("reasoning"),
                j.get("provider"),
                j.get("model"),
                j.get("latency_seconds"),
                j.get("url"),
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
