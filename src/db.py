import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
from src.logger import logger
from src.models import Job
from datetime import datetime

# Load environment variables
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
# Use service role key if available for backend tasks bypassing RLS, fallback to anon key
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_KEY"))
if url and key:
    supabase: Client = create_client(url, key)
else:
    supabase = None

def get_cached_jd_score(url: str):
    if not supabase: return None
    res = supabase.table("jd_cache").select("*").eq("url", url).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    return None

def save_jd_cache(url: str, score: int, missing_skills: list, extracted_requirements: str, is_testing_role: bool):
    if not supabase: return
    supabase.table("jd_cache").upsert({
        "url": url,
        "score": score,
        "missing_skills": missing_skills,
        "extracted_requirements": extracted_requirements,
        "is_testing_role": is_testing_role
    }).execute()

def cleanup_old_pdfs():
    """Automatically deletes PDFs older than 30 days if status is generated, rejected, or custom."""
    if not supabase: return
    try:
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
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

def save_pipeline_results(pipeline_state, shortlisted_jobs, pdf_paths):
    """Push pipeline results to Supabase. Replaces sheet_generator + email_sender."""
    if not supabase:
        print("Warning: Supabase credentials not found. Results will not be saved to DB.")
        return
        
    total_tokens = sum(getattr(j, "tokens_used", 0) for j in shortlisted_jobs)
    
    # 1. Record the pipeline run
    run = supabase.table("pipeline_runs").insert({
        "mode": pipeline_state["mode"],
        "jobs_scraped": pipeline_state["scan"]["total_found"],
        "jobs_filtered": pipeline_state["filter"]["after"],
        "jobs_scored": pipeline_state["score"]["scored"],
        "jobs_shortlisted": pipeline_state["score"]["shortlisted"],
        "resumes_generated": sum(1 for p in pdf_paths if p),
        "tokens_used": total_tokens
    }).execute()
    
    run_id = run.data[0]["id"]
    
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
        
        supabase.table("applications").insert({
            "job_id": job_record.data[0]["id"],
            "status": "generated",
        }).execute()
        
    # Trigger cleanup
    cleanup_old_pdfs()

def save_manual_job(job: Job, pdf_path: str):
    """Saves a manually tailored job to the tracker database."""
    if not supabase: return
    
    # 1. Create a "manual" pipeline run to group these
    run = supabase.table("pipeline_runs").insert({
        "mode": "manual",
        "jobs_scraped": 0,
        "jobs_filtered": 0,
        "jobs_scored": 1,
        "jobs_shortlisted": 1,
        "resumes_generated": 1 if pdf_path else 0,
        "completed_at": datetime.utcnow().isoformat()
    }).execute()
    
    run_id = run.data[0]["id"]
    stored_pdf_url = pdf_path
    
    if pdf_path and os.path.exists(pdf_path):
        filename = Path(pdf_path).name
        try:
            with open(pdf_path, 'rb') as f:
                supabase.storage.from_("resumes").upload(filename, f.read())
            public_url = supabase.storage.from_("resumes").get_public_url(filename)
        except Exception as e:
            logger.error(f"Failed to upload {filename} to Supabase: {e}")
            
    # 2. Insert the tracked job
    job_record = supabase.table("tracked_jobs").insert({
        "id": job.id,
        "run_id": run_id,
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
    supabase.table("applications").insert({
        "job_id": job_record.data[0]["id"],
        "status": "generated",
    }).execute()

def delete_pipeline_run(run_id: str):
    """Manually cascade delete a pipeline run and return the PDF paths that need local deletion."""
    if not supabase: return []
    
    # 1. Get all jobs for this run
    jobs = supabase.table("tracked_jobs").select("id, pdf_filename").eq("run_id", run_id).execute().data
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
    apps = supabase.table("applications").select("id").in_("job_id", job_ids).execute().data
    app_ids = [a["id"] for a in apps]
    
    # 3. Delete status history
    if app_ids:
        supabase.table("status_history").delete().in_("application_id", app_ids).execute()
        
    # 4. Delete applications
    if job_ids:
        supabase.table("applications").delete().in_("job_id", job_ids).execute()
        
    # 5. Delete tracked jobs
    supabase.table("tracked_jobs").delete().eq("run_id", run_id).execute()
    
    # 6. Delete pipeline run
    supabase.table("pipeline_runs").delete().eq("id", run_id).execute()
    
    return pdf_paths

def get_job_pdf_path(job_id: str):
    if not supabase: return None
    res = supabase.table("tracked_jobs").select("pdf_filename").eq("id", job_id).execute()
    if res.data and len(res.data) > 0:
        return res.data[0].get("pdf_filename")
    return None

def delete_application(app_id: str):
    """Deletes an application, its history, its associated tracked job, and returns the PDF path for local deletion."""
    if not supabase: return None
    
    # Get the application to find the job_id
    app_res = supabase.table("applications").select("job_id").eq("id", app_id).execute()
    if not app_res.data:
        return None
        
    job_id = app_res.data[0]["job_id"]
    
    # Get the job to find the pdf path
    job_res = supabase.table("tracked_jobs").select("pdf_filename").eq("id", job_id).execute()
    pdf_path = None
    if job_res.data:
        pdf_path = job_res.data[0].get("pdf_filename")
        if pdf_path and "resumes/" in pdf_path:
            filename = pdf_path.split("resumes/")[-1]
            try:
                supabase.storage.from_("resumes").remove([filename])
            except:
                pass

    # Delete history, then app, then job
    supabase.table("status_history").delete().eq("application_id", app_id).execute()
    supabase.table("applications").delete().eq("id", app_id).execute()
    supabase.table("tracked_jobs").delete().eq("id", job_id).execute()
    
    return pdf_path

