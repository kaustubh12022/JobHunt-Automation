import os
from supabase import create_client, Client
from dotenv import load_dotenv
from collections import Counter
import json

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

runs = supabase.table('pipeline_runs').select('*').order('started_at', desc=True).limit(5).execute()
print("Recent Pipeline Runs:")
for r in runs.data:
    print(f"ID: {r['id']}, Date: {r['started_at']}, Scraped: {r['jobs_scraped']}, Filtered: {r['jobs_filtered']}, Scored: {r['jobs_scored']}, Resumes: {r['resumes_generated']}")

if runs.data:
    latest_run_id = runs.data[0]['id']
    print(f"\nAnalyzing latest run: {latest_run_id}")
    
    jobs = supabase.table('tracked_jobs').select('*').eq('run_id', latest_run_id).execute()
    print(f"Total jobs saved for this run: {len(jobs.data)}")
    
    scored_jobs = [j for j in jobs.data if j.get('score') is not None]
    print(f"Jobs with scores: {len(scored_jobs)}")
    
    resume_jobs = [j for j in jobs.data if j.get('tailored_resume') is not None]
    print(f"Jobs with tailored resume (JSON): {len(resume_jobs)}")
    
    print("\nSample of jobs that passed regex filter (i.e. saved to tracked_jobs):")
    for j in jobs.data[:3]:
        print(f"- {j['title']} at {j['company']} (Source: {j['source']})")
        
    print("\nSample of jobs with tailored JSON:")
    for j in resume_jobs[:2]:
        print(f"- {j['title']} at {j['company']} (Score: {j['score']})")
        if j['tailored_resume']:
            print("  Tailored JSON keys:", list(j['tailored_resume'].keys()))
