from src.db import supabase

res = supabase.table('applications').select('id, status, tracked_jobs(title, company, url)').execute()
for a in res.data:
    tj = a.get('tracked_jobs', {})
    url = tj.get('url', '')[:60]
    company = tj.get('company', '')
    status = a.get('status', '')
    print(f"{status:15} | {company:30} | {url}")
