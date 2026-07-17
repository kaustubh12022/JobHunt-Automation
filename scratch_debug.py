import sys
import re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('.')
from src.scraper import _scrape_with_retry, clean_html, apply_pandas_filter
from src.scorer import score_jobs
from src.models import Job
import uuid
import pandas as pd

print('Scraping Jobs for debugging...')
df = _scrape_with_retry({
    'site_name': ['linkedin'],
    'search_term': 'Java Developer',
    'location': 'Pune',
    'job_type': 'fulltime',
    'results_wanted': 15,
    'hours_old': 72,
    'country_indeed': 'India',
    'linkedin_fetch_description': True
})

raw_jobs = []
if not df.empty:
    for _, row in df.iterrows():
        desc = clean_html(row.get('description', ''))
        if not desc: continue
        job = Job(
            id=str(uuid.uuid4()),
            title=str(row.get('title', 'Unknown')),
            company=str(row.get('company', 'Unknown')),
            location=str(row.get('location', 'Unknown')),
            description=desc,
            url=str(row.get('job_url', row.get('url', ''))),
            source=str(row.get('site', 'jobspy')),
            job_type='fulltime'
        )
        job.date_posted = pd.Timestamp.now(tz='UTC')
        raw_jobs.append(job)

print(f'Raw jobs fetched: {len(raw_jobs)}')

# Let's apply our filter just to see what IT drops, and then what it keeps.
# Wait, we want to see what LEAKS, so we apply the filter, and then score what survived.
survived_jobs = apply_pandas_filter(raw_jobs, ['Pune'], test_mode=False)

print(f'Jobs surviving the filter: {len(survived_jobs)}')

if not survived_jobs:
    print("No jobs survived. We can't find leaks if nothing survives.")
    sys.exit(0)

print('Scoring surviving jobs to find leaks...')
scored_jobs = score_jobs(survived_jobs, test_mode=True)

for job in scored_jobs:
    reason_lower = job.reasons.lower()
    if 'year' in reason_lower or 'fresher' in reason_lower:
        print(f'\n--- {job.title} at {job.company} ---')
        print(f'AI Reason: {job.reasons}')
        
        # Extract snippets around 'year' or 'yr'
        desc_lower = job.description.lower()
        print("Snippets:")
        for match in re.finditer(r'.{0,40}years?.{0,40}', desc_lower):
            print(f'  "{match.group(0).strip()}"')
