import os
import shutil
import zipfile
from pathlib import Path
from src.db import supabase, resolve_local_pdf_path
from playwright.sync_api import sync_playwright

def main():
    if not supabase:
        print("Supabase client not initialized.")
        return

    res = supabase.table("pipeline_runs").select("id").order("id", desc=True).limit(1).execute()
    if not res.data:
        print("No pipeline runs found.")
        return
    
    run_id = res.data[0]["id"]
    
    jobs_res = supabase.table("tracked_jobs").select("id, title, company, url, pdf_filename").eq("run_id", run_id).execute()
    jobs = jobs_res.data
    
    desktop_dir = Path(os.environ["USERPROFILE"]) / "Desktop"
    bundle_dir = desktop_dir / "Job_Resumes"
    bundle_dir.mkdir(exist_ok=True)
    
    resumes_dir = bundle_dir / "Resumes"
    resumes_dir.mkdir(exist_ok=True)
    
    html_content = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { text-align: center; color: #333; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; word-wrap: break-word; }
            th { background-color: #f4f4f4; color: #333; font-weight: bold; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .col-company { width: 20%; }
            .col-title { width: 30%; }
            .col-link { width: 25%; }
            .col-resume { width: 25%; }
            .btn { display: inline-block; padding: 6px 12px; margin: 2px; background-color: #0066cc; color: white; text-decoration: none; border-radius: 4px; font-size: 12px; }
            .btn:hover { background-color: #005bb5; text-decoration: none; color: white; }
        </style>
    </head>
    <body>
        <h1>Latest Pipeline Jobs & Resumes</h1>
        <table>
            <thead>
                <tr>
                    <th class="col-company">Company Name</th>
                    <th class="col-title">Job Name</th>
                    <th class="col-link">Apply Link</th>
                    <th class="col-resume">Resume</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for job in jobs:
        title = job.get("title", "N/A")
        company = job.get("company", "N/A")
        url = job.get("url", "#")
        pdf_url = job.get("pdf_filename", "")
        
        safe_company = "".join(c if c.isalnum() else "_" for c in company)
        safe_title = "".join(c if c.isalnum() else "_" for c in title)
        local_filename = f"{safe_company}_{safe_title}_Resume.pdf"
        
        local_path = resolve_local_pdf_path(job["id"])
        if local_path and os.path.exists(local_path):
            shutil.copy(local_path, resumes_dir / local_filename)
        
        resume_links = ""
        if pdf_url and pdf_url.startswith("http"):
            resume_links = f'<a href="{pdf_url}" target="_blank" class="btn">View / Download</a>'
        else:
            resume_links = "Not available online"
            
        html_content += f"""
                <tr>
                    <td>{company}</td>
                    <td>{title}</td>
                    <td><a href="{url}" target="_blank">Job Link</a></td>
                    <td>{resume_links}</td>
                </tr>
        """
        
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    summary_pdf_path = bundle_dir / "Job_Summary.pdf"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        page.pdf(
            path=str(summary_pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"}
        )
        browser.close()
        
    zip_path = desktop_dir / "Job_Application_Bundle.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(bundle_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(desktop_dir)
                zipf.write(file_path, arcname)
                
    print(f"ZIP_PATH={zip_path}")

if __name__ == "__main__":
    main()
