from src.db import supabase
res = supabase.table('applications').select('id, status, error_code, error_message, tracked_jobs(company)').execute()
for a in res.data:
    if a['status'] in ('failed', 'needs_review'):
        print(f"{a['status']:15} | {a.get('error_code') or ''} | {a['tracked_jobs']['company']:30} | {str(a.get('error_message'))[:50]}")
