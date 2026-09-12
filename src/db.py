import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
from src.logger import logger
from src.models import Job
from datetime import datetime, timezone, timedelta

# Load environment variables
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
# Use service role key if available for backend tasks bypassing RLS, fallback to anon key
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_KEY"))
supabase: Client | None = None
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        logger.warning(f"Could not initialize Supabase client: {e}")
        supabase = None


def get_cached_jd_score(url: str):
    if not supabase: return None
    try:
        res = supabase.table("jd_cache").select("*").eq("url", url).execute()
        if res and hasattr(res, "data") and res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as e:
        logger.warning(f"Failed to query jd_cache from Supabase: {e}")
    return None

def save_jd_cache(url: str, score: int, missing_skills: list, extracted_requirements: str, is_testing_role: bool):
    if not supabase: return
    try:
        supabase.table("jd_cache").upsert({
            "url": url,
            "score": score,
            "missing_skills": missing_skills,
            "extracted_requirements": extracted_requirements,
            "is_testing_role": is_testing_role
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to save to jd_cache in Supabase: {e}")

def cleanup_old_pdfs():
    """Automatically deletes PDFs older than 30 days if status is generated, rejected, or custom."""
    if not supabase: return
    try:
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        # Query applications older than 30 days
        apps_res = supabase.table("applications").select("job_id").in_("status", ["generated", "rejected", "custom"]).lt("created_at", thirty_days_ago).execute()
        job_ids = [app["job_id"] for app in apps_res.data]
        
        if not job_ids:
            return
            
        jobs_res = supabase.table("tracked_jobs").select("id, pdf_filename").in_("id", job_ids).execute()
        files_to_remove = []
        for job in jobs_res.data:
            pdf_url = job.get("pdf_filename")
            if pdf_url and "resumes/" in pdf_url:
                # Extract filename from url
                filename = pdf_url.split("resumes/")[-1]
                files_to_remove.append(filename)
                
        if files_to_remove:
            supabase.storage.from_("resumes").remove(files_to_remove)
            
        # NULL the pdf_filename in the database
        for job in jobs_res.data:
            supabase.table("tracked_jobs").update({"pdf_filename": None}).eq("id", job["id"]).execute()
            
        logger.info(f"🧹 Cleaned up {len(files_to_remove)} old PDFs from Supabase Storage.")
    except Exception as e:
        logger.error(f"Error during PDF cleanup: {e}")

def save_pipeline_results(pipeline_state, shortlisted_jobs, pdf_paths, all_scored_jobs=None):
    """Push pipeline results to Supabase with comprehensive token and cost telemetry across all scored jobs."""
    if not supabase:
        print("Warning: Supabase credentials not found. Results will not be saved to DB.")
        return
        
    # Resolve all_scored_jobs across possible sources
    if all_scored_jobs is None:
        all_scored_jobs = getattr(shortlisted_jobs, "all_scored_jobs", None)
    if all_scored_jobs is None and pipeline_state:
        all_scored_jobs = pipeline_state.get("all_scored_jobs")

    def _job_key(j):
        return getattr(j, "id", None) or (getattr(j, "title", None), getattr(j, "company", None), getattr(j, "url", None)) or id(j)

    # Fallback to get_last_scored_jobs() from src.scorer if all_scored_jobs is missing or has fewer jobs than shortlisted
    if not all_scored_jobs or (shortlisted_jobs and len(all_scored_jobs) <= len(shortlisted_jobs)):
        try:
            from src.scorer import get_last_scored_jobs
            last_scored = get_last_scored_jobs()
            if last_scored and (not all_scored_jobs or len(last_scored) > len(all_scored_jobs)):
                if shortlisted_jobs:
                    last_keys = {_job_key(j) for j in last_scored}
                    short_keys = {_job_key(j) for j in shortlisted_jobs}
                    if short_keys.issubset(last_keys):
                        all_scored_jobs = last_scored
                else:
                    all_scored_jobs = last_scored
        except Exception:
            pass

    if not all_scored_jobs:
        all_scored_jobs = shortlisted_jobs

    # Map all jobs to avoid double counting and ensure ALL scored jobs are included
    # Key on j.id (with fallback to metadata tuple or memory pointer) instead of raw id(j)
    tracked_map = {_job_key(j): j for j in (all_scored_jobs or [])}
    for j in shortlisted_jobs:
        key = _job_key(j)
        tracked_map[key] = j
    all_jobs_tracked = list(tracked_map.values())

    total_tokens = sum(int(getattr(j, "tokens_used", 0) or 0) for j in all_jobs_tracked)
    total_cost = sum(float(getattr(j, "cost_usd", 0.0) or 0.0) for j in all_jobs_tracked)

    total_prompt_tokens = sum(int((getattr(j, "token_usage", None) or {}).get("prompt_tokens", 0) or 0) for j in all_jobs_tracked)
    total_cached_tokens = sum(int((getattr(j, "token_usage", None) or {}).get("prompt_cache_hit_tokens", 0) or 0) for j in all_jobs_tracked)
    total_miss_tokens = sum(int((getattr(j, "token_usage", None) or {}).get("prompt_cache_miss_tokens", 0) or 0) for j in all_jobs_tracked)
    total_completion_tokens = sum(int((getattr(j, "token_usage", None) or {}).get("completion_tokens", 0) or 0) for j in all_jobs_tracked)

    cache_hit_rate = round(total_cached_tokens / total_prompt_tokens, 4) if total_prompt_tokens > 0 else 0.0

    ai_metrics = {
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "input_tokens": total_prompt_tokens,
        "cached_tokens": total_cached_tokens,
        "miss_tokens": total_miss_tokens,
        "output_tokens": total_completion_tokens,
        "cache_hit_rate": cache_hit_rate,
        "jobs_scored_count": len(all_jobs_tracked),
        "jobs_shortlisted_count": len(shortlisted_jobs),
        "resumes_generated": sum(1 for p in pdf_paths if p),
    }

    # 1. Record the pipeline run
    run_payload = {
        "mode": pipeline_state.get("mode", "prod"),
        "jobs_scraped": pipeline_state.get("scan", {}).get("total_found", 0),
        "jobs_filtered": pipeline_state.get("filter", {}).get("after", 0),
        "jobs_scored": pipeline_state.get("score", {}).get("scored", len(all_jobs_tracked)),
        "jobs_shortlisted": pipeline_state.get("score", {}).get("shortlisted", len(shortlisted_jobs)),
        "resumes_generated": sum(1 for p in pdf_paths if p),
        "tokens_used": total_tokens,
        "ai_metrics": ai_metrics,
    }

    try:
        try:
            run = supabase.table("pipeline_runs").insert(run_payload).execute()
        except Exception as e:
            err_msg = str(e)
            if "ai_metrics" in err_msg or "PGRST204" in err_msg:
                # Fallback if ai_metrics column is not yet in Supabase schema cache
                run_payload.pop("ai_metrics", None)
                existing_stats = pipeline_state.get("scrape_stats", {}) or {}
                run_payload["scrape_stats"] = {**existing_stats, "ai_metrics": ai_metrics}
                run = supabase.table("pipeline_runs").insert(run_payload).execute()
            else:
                raise
        run_id = run.data[0]["id"] if (run and getattr(run, "data", None)) else None
    except Exception as e:
        logger.error(f"Failed to record pipeline_run in Supabase: {e}")
        return

    # 2. Insert each shortlisted job + auto-create application
    for job, pdf_path in zip(shortlisted_jobs, pdf_paths):
        stored_pdf_url = pdf_path
        
        # Upload to Supabase Storage if pdf exists
        if pdf_path and os.path.exists(pdf_path):
            filename = Path(pdf_path).name
            try:
                with open(pdf_path, 'rb') as f:
                    supabase.storage.from_("resumes").upload(filename, f.read())
                # Get public url
                public_url = supabase.storage.from_("resumes").get_public_url(filename)
                # stored_pdf_url = public_url # Keep local path to avoid 504 Gateway Timeouts
            except Exception as e:
                logger.error(f"Failed to upload {filename} to Supabase: {e}")
                # Fallback to local path if upload fails
        
        try:
            job_record = supabase.table("tracked_jobs").insert({
                "id": job.id,
                "run_id": run_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "description": getattr(job, 'description', ''),
                "source": getattr(job, 'source', None),
                "job_type": getattr(job, 'job_type', 'fulltime'),
                "score": job.score,
                "missing_skills": getattr(job, 'missing_skills', []),
                "extracted_requirements": getattr(job, 'extracted_requirements', None),
                "is_testing_role": getattr(job, 'is_testing_role', None),
                "tailored_resume": getattr(job, 'tailored_resume', None),
                "pdf_filename": stored_pdf_url,
            }).execute()
            
            job_db_id = job_record.data[0]["id"] if (job_record and getattr(job_record, "data", None)) else job.id
            supabase.table("applications").insert({
                "job_id": job_db_id,
                "status": "generated",
            }).execute()
        except Exception as e:
            logger.error(f"Failed to record job {getattr(job, 'id', '')} in Supabase: {e}")
        
    # Trigger cleanup
    try:
        cleanup_old_pdfs()
    except Exception as e:
        logger.warning(f"Error during cleanup_old_pdfs: {e}")

def save_manual_job(job: Job, pdf_path: str):
    """Saves a manually tailored job to the tracker database."""
    if not supabase: return
    
    try:
        # 1. Create a "manual" pipeline run to group these
        run = supabase.table("pipeline_runs").insert({
            "mode": "manual",
            "jobs_scraped": 0,
            "jobs_filtered": 0,
            "jobs_scored": 1,
            "jobs_shortlisted": 1,
            "resumes_generated": 1 if pdf_path else 0,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        run_id = run.data[0]["id"] if (run and getattr(run, "data", None)) else None
        stored_pdf_url = pdf_path
        
        if pdf_path and os.path.exists(pdf_path):
            filename = Path(pdf_path).name
            try:
                with open(pdf_path, 'rb') as f:
                    supabase.storage.from_("resumes").upload(filename, f.read())
                public_url = supabase.storage.from_("resumes").get_public_url(filename)
            except Exception as e:
                logger.error(f"Failed to upload {filename} to Supabase: {e}")
                
        # 2. Upsert the tracked job
        job_record = supabase.table("tracked_jobs").upsert({
            "id": job.id,
            "run_id": getattr(job, 'run_id', run_id) or run_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": getattr(job, 'url', ''),
            "description": getattr(job, 'description', ''),
            "source": "manual",
            "job_type": getattr(job, 'job_type', 'fulltime'),
            "score": getattr(job, 'score', 0),
            "missing_skills": getattr(job, 'missing_skills', []),
            "extracted_requirements": getattr(job, 'extracted_requirements', None),
            "is_testing_role": getattr(job, 'is_testing_role', None),
            "tailored_resume": getattr(job, 'tailored_resume', None),
            "pdf_filename": stored_pdf_url,
        }).execute()
        
        # 3. Create application entry
        job_db_id = job_record.data[0]["id"] if (job_record and getattr(job_record, "data", None)) else job.id
        supabase.table("applications").insert({
            "job_id": job_db_id,
            "status": "generated",
        }).execute()
    except Exception as e:
        logger.error(f"Failed to save manual job to Supabase: {e}")

def delete_pipeline_run(run_id: str):
    """Manually cascade delete a pipeline run and return the PDF paths that need local deletion."""
    if not supabase: return []
    try:
        # 1. Get all jobs for this run
        jobs_res = supabase.table("tracked_jobs").select("id, pdf_filename").eq("run_id", run_id).execute()
        jobs = jobs_res.data if (jobs_res and getattr(jobs_res, "data", None)) else []
        if not jobs:
            # Just delete the run
            supabase.table("pipeline_runs").delete().eq("id", run_id).execute()
            return []
            
        job_ids = [j["id"] for j in jobs]
        pdf_paths = [j["pdf_filename"] for j in jobs if j.get("pdf_filename")]
        
        files_to_remove = []
        for pdf_url in pdf_paths:
            if pdf_url and "resumes/" in pdf_url:
                filename = pdf_url.split("resumes/")[-1]
                files_to_remove.append(filename)
                
        if files_to_remove:
            try:
                supabase.storage.from_("resumes").remove(files_to_remove)
            except Exception as e:
                logger.error(f"Error removing files from storage: {e}")
                
        # 2. Get applications for these jobs
        apps_res = supabase.table("applications").select("id").in_("job_id", job_ids).execute()
        apps = apps_res.data if (apps_res and getattr(apps_res, "data", None)) else []
        app_ids = [a["id"] for a in apps]
        
        # 3. Delete status history and apply logs
        if app_ids:
            try:
                supabase.table("apply_logs").delete().in_("application_id", app_ids).execute()
            except Exception:
                pass
            try:
                supabase.table("status_history").delete().in_("application_id", app_ids).execute()
            except Exception:
                pass
            
        # 4. Delete applications
        if job_ids:
            supabase.table("applications").delete().in_("job_id", job_ids).execute()
            
        # 5. Delete tracked jobs
        supabase.table("tracked_jobs").delete().eq("run_id", run_id).execute()
        
        # 6. Delete pipeline run
        supabase.table("pipeline_runs").delete().eq("id", run_id).execute()
        
        return pdf_paths
    except Exception as e:
        logger.error(f"Error deleting pipeline run {run_id}: {e}")
        return []

def get_job_pdf_path(job_id: str):
    if not supabase: return None
    try:
        res = supabase.table("tracked_jobs").select("pdf_filename").eq("id", job_id).execute()
        if res and getattr(res, "data", None) and len(res.data) > 0:
            return res.data[0].get("pdf_filename")
    except Exception as e:
        logger.error(f"Error getting PDF path from Supabase for {job_id}: {e}")
    return None

def resolve_local_pdf_path(job_id: str) -> str:
    """
    Returns a verified LOCAL filesystem path to the job's PDF.
    If the DB stores a Supabase URL, searches the output directory for the file.
    Returns empty string if not found locally.
    """
    import os
    pdf_path = get_job_pdf_path(job_id)
    if not pdf_path:
        return ""
    
    # Case 1: It's already a local path and exists
    if not pdf_path.startswith("http") and os.path.exists(pdf_path):
        return pdf_path
    
    # Case 2: It's a Supabase URL — extract filename and search locally
    if pdf_path.startswith("http"):
        filename = pdf_path.split("/")[-1]
    else:
        filename = os.path.basename(pdf_path)
    
    # Search in the output directories
    from src.config_loader import load_config
    config = load_config()
    output_dir = os.path.join(config['output']['desktop_path'], config['output']['folder_name'])
    
    search_dirs = [
        os.path.join(output_dir, "main pipeline"),
        os.path.join(output_dir, "test"),
        os.path.join(os.getcwd(), "output", "manual"),
    ]
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for root, dirs, files in os.walk(search_dir):
                if filename in files:
                    return os.path.join(root, filename)
    
    return ""

def get_job_by_id(job_id: str):
    if not supabase: return None
    try:
        res = supabase.table("tracked_jobs").select("*").eq("id", job_id).execute()
        if res and getattr(res, "data", None) and len(res.data) > 0:
            # Convert dictionary to Job dataclass
            data = res.data[0]
            return Job(
                id=data.get("id"),
                title=data.get("title"),
                company=data.get("company"),
                location=data.get("location"),
                description=data.get("description"),
                url=data.get("url"),
                source=data.get("source"),
                job_type=data.get("job_type"),
                score=data.get("score"),
                missing_skills=data.get("missing_skills"),
                extracted_requirements=data.get("extracted_requirements"),
                is_testing_role=data.get("is_testing_role"),
                tailored_resume=data.get("tailored_resume")
            )
    except Exception as e:
        logger.error(f"Error getting job {job_id} from Supabase: {e}")
    return None

def delete_application(app_id: str):
    """Deletes an application, its history, its associated tracked job, and returns the PDF path for local deletion."""
    if not supabase: return None
    try:
        # Get the application to find the job_id
        app_res = supabase.table("applications").select("job_id").eq("id", app_id).execute()
        if not app_res or not getattr(app_res, "data", None) or not app_res.data:
            return None
            
        job_id = app_res.data[0]["job_id"]
        
        # Get the job to find the pdf path
        job_res = supabase.table("tracked_jobs").select("pdf_filename").eq("id", job_id).execute()
        pdf_path = None
        if job_res and getattr(job_res, "data", None) and job_res.data:
            pdf_path = job_res.data[0].get("pdf_filename")
            if pdf_path and "resumes/" in pdf_path:
                filename = pdf_path.split("resumes/")[-1]
                try:
                    supabase.storage.from_("resumes").remove([filename])
                except Exception:
                    pass

        # Delete history, apply logs, then app, then job
        try:
            supabase.table("status_history").delete().eq("application_id", app_id).execute()
        except Exception:
            pass
        try:
            supabase.table("apply_logs").delete().eq("application_id", app_id).execute()
        except Exception:
            pass
        supabase.table("applications").delete().eq("id", app_id).execute()
        supabase.table("tracked_jobs").delete().eq("id", job_id).execute()
        
        return pdf_path
    except Exception as e:
        logger.error(f"Error deleting application {app_id}: {e}")
        return None

