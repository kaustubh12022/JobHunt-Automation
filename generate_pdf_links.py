import os
from pathlib import Path
from src.db import supabase
from playwright.sync_api import sync_playwright

def main():
    if not supabase:
        print("Supabase client not initialized.")
        return

    # Let's get the latest run_id from pipeline_runs
    res = supabase.table("pipeline_runs").select("id").order("id", desc=True).limit(1).execute()
    if not res.data:
        print("No pipeline runs found.")
        return
    
    run_id = res.data[0]["id"]
    print(f"Found latest run: {run_id}")
    
    # Get jobs for this run_id
    jobs_res = supabase.table("tracked_jobs").select("title, company, url").eq("run_id", run_id).execute()
    jobs = jobs_res.data
    
    if not jobs:
        print("No jobs found for the latest run.")
        return
    
    print(f"Found {len(jobs)} jobs. Generating PDF...")
    
    # Generate HTML
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
            .col-company { width: 25%; }
            .col-title { width: 35%; }
            .col-link { width: 40%; }
        </style>
    </head>
    <body>
        <h1>Latest Pipeline Jobs</h1>
        <table>
            <thead>
                <tr>
                    <th class="col-company">Company Name</th>
                    <th class="col-title">Job Name</th>
                    <th class="col-link">Specific Apply Link</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for job in jobs:
        title = job.get("title", "N/A")
        company = job.get("company", "N/A")
        url = job.get("url", "#")
        html_content += f"""
                <tr>
                    <td>{company}</td>
                    <td>{title}</td>
                    <td><a href="{url}">{url}</a></td>
                </tr>
        """
        
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    # Save PDF
    desktop_path = os.path.join(os.environ["USERPROFILE"], "Desktop", "Job_Links.pdf")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        page.pdf(
            path=desktop_path,
            format="A4",
            print_background=True,
            margin={"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"}
        )
        browser.close()
        
    print(f"PDF successfully generated at {desktop_path}")

if __name__ == "__main__":
    main()
