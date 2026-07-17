import os
import json
import asyncio
import time
import random
from dotenv import load_dotenv
import google.generativeai as genai
import pandas as pd
from unittest.mock import patch
from src.scraper import run_scraper, apply_pandas_filter

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def evaluate_job(title, company, description, job_type):
    prompt = f"""
    You are an expert HR recruiter auditing a job description.
    Job Title: {title}
    Company: {company}
    Job Type: {job_type}
    Description:
    {description}

    Task: Determine if this job is TRULY RELEVANT for a fresher (0-2 years experience).
    - If it's an internship, it is relevant unless it specifically asks for advanced degrees (e.g. PhD) or lots of prior full-time experience.
    - If the job description explicitly requires 3 or more years of candidate experience, it is IRRELEVANT.
    - If the job title indicates it's a senior, lead, manager, director, or principal role, it is IRRELEVANT.
    - If the job is suitable for someone with 0, 1, or 2 years of experience, it is RELEVANT.
    - Note: Some jobs may say "our team has 10 years of experience" - this does not mean the candidate needs it. Do not be confused by this.

    Return ONLY a JSON object with this exact structure, nothing else:
    {{
        "is_relevant": true or false,
        "reason": "Brief explanation of why"
    }}
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        return data["is_relevant"], data["reason"]
    except Exception as e:
        print(f"Error evaluating job {title}: {e}")
        return None, str(e)

def scrape_raw_jobs():
    original_apply = apply_pandas_filter
    
    def dummy_filter(jobs, locations, callbacks=None, test_mode=False):
        return jobs
        
    with patch('src.scraper.apply_pandas_filter', side_effect=dummy_filter):
        # We want more jobs than test mode typically gives.
        jobs, _ = run_scraper(selected_platforms=["linkedin", "indeed"], selected_job_types=["fulltime", "internship"], test_mode=False)
    return jobs, original_apply

def run_cycle(cycle_num):
    print(f"\n=== Starting Cycle {cycle_num} ===")
    
    # Check if we already scraped raw jobs to save time/API calls
    import pickle
    cache_file = f"raw_jobs_cycle_{cycle_num}.pkl"
    original_filter_fn = apply_pandas_filter
    if os.path.exists(cache_file):
        print("Loading cached raw jobs...")
        with open(cache_file, "rb") as f:
            raw_jobs = pickle.load(f)
    else:
        print("Scraping raw jobs...")
        raw_jobs, original_filter_fn = scrape_raw_jobs()
        with open(cache_file, "wb") as f:
            pickle.dump(raw_jobs, f)
            
    print(f"Scraped {len(raw_jobs)} raw jobs.")
    if not raw_jobs:
        return
        
    from src.config_loader import load_config
    config = load_config()
    locations = config.get('search', {}).get('locations', ["Pune"])
    
    # 1. Apply the original (or current) pandas filter
    print("Applying pandas regex filter...")
    passed_jobs = original_filter_fn(raw_jobs, locations)
    passed_ids = {j.id for j in passed_jobs}
    
    rejected_jobs = [j for j in raw_jobs if j.id not in passed_ids]
    
    print(f"Filter PASSED: {len(passed_jobs)} | Filter REJECTED: {len(rejected_jobs)}")
    
    # Respecting Gemini API Free Tier Limit: 15 Requests Per Minute
    # We will evaluate a maximum of 30 randomly sampled jobs for PASSED and 30 for REJECTED
    # and we will sleep for 4.1 seconds between API calls to stay under 15 RPM.
    eval_passed = random.sample(passed_jobs, min(30, len(passed_jobs)))
    eval_rejected = random.sample(rejected_jobs, min(30, len(rejected_jobs)))
    
    false_positives = []
    false_negatives = []
    
    print("\n--- Evaluating PASSED jobs (Looking for False Positives) ---")
    for i, j in enumerate(eval_passed):
        print(f"[{i+1}/{len(eval_passed)}] Evaluating PASSED: {j.title[:40]} at {j.company[:20]}", end='\r')
        is_relevant, reason = evaluate_job(j.title, j.company, j.description, getattr(j, 'job_type', 'fulltime'))
        if is_relevant is False:
            false_positives.append((j, reason))
        time.sleep(4.1)
    print()
        
    print("\n--- Evaluating REJECTED jobs (Looking for False Negatives) ---")
    for i, j in enumerate(eval_rejected):
        print(f"[{i+1}/{len(eval_rejected)}] Evaluating REJECTED: {j.title[:40]} at {j.company[:20]}", end='\r')
        drop_reason = []
        def cb(title, company, r): drop_reason.append(r)
        original_filter_fn([j], locations, callbacks={"on_job_dropped": cb})
        dr = drop_reason[0] if drop_reason else "Unknown/Dupe/Location/Stale"
        
        if "Stale" in dr or "Location" in dr or "Duplicate" in dr:
            continue
            
        is_relevant, reason = evaluate_job(j.title, j.company, j.description, getattr(j, 'job_type', 'fulltime'))
        if is_relevant is True:
            false_negatives.append((j, dr, reason))
        time.sleep(4.1)
    print()
    
    report = {
        "cycle": cycle_num,
        "metrics": {
            "total_scraped": len(raw_jobs),
            "total_passed": len(passed_jobs),
            "total_rejected": len(rejected_jobs),
            "false_positives": len(false_positives),
            "false_negatives": len(false_negatives)
        },
        "false_positives": [{"title": j.title, "company": j.company, "description": j.description, "job_type": getattr(j, 'job_type', 'fulltime'), "reason": r} for j, r in false_positives],
        "false_negatives": [{"title": j.title, "company": j.company, "description": j.description, "job_type": getattr(j, 'job_type', 'fulltime'), "filter_reason": dr, "ai_reason": r} for j, dr, r in false_negatives]
    }
    
    out_file = f"audit_report_cycle_{cycle_num}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"\n=== Cycle {cycle_num} Complete ===")
    print(f"False Positives (Passed filter but AI says IRRELEVANT): {len(false_positives)}")
    for j, r in false_positives[:3]: print(f"  - {j.title} | {r}")
    
    print(f"\nFalse Negatives (Rejected filter but AI says RELEVANT): {len(false_negatives)}")
    for j, dr, r in false_negatives[:3]: print(f"  - {j.title} | Filtered because: {dr} | {r}")
    
    print(f"\nFull report saved to {out_file}")

if __name__ == "__main__":
    import sys
    c = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_cycle(c)
