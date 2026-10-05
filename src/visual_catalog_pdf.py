"""
visual_catalog_pdf.py — Simple, clean 3-column table PDF catalog of tailored resume jobs:
  Column 1: Company Name
  Column 2: Job Role
  Column 3: Direct Apply Link (clickable)
"""

import re
from pathlib import Path
from datetime import date
from playwright.sync_api import sync_playwright
from src.logger import logger


def generate_visual_catalog_pdf(jobs_data: list, output_dir: Path) -> str:
    """
    Generate Resume_Created_Jobs.pdf — a clean, simple 3-column table PDF:
    Columns: Company Name | Job Role | Direct Apply Link
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "Resume_Created_Jobs.pdf"

    if not jobs_data:
        logger.warning("No jobs data provided for visual catalog PDF.")
        return ""

    today_str = date.today().strftime("%B %d, %Y")

    has_resume_links = any(bool(j.get('supabase_resume_url') or j.get('resume_url')) for j in jobs_data)
    th_resume = '<th class="col-resume-th">Supabase Resume Link</th>' if has_resume_links else ''
    page_orientation = "A4 landscape" if has_resume_links else "A4 portrait"

    # Group jobs by platform -> apply_type
    grouped = {}
    for job in jobs_data:
        plat = str(job.get('platform') or 'General').strip().capitalize()
        # Clean workday prefixes if any
        if plat.lower().startswith('workday'):
            plat = 'Workday'
        atype = str(job.get('apply_type') or 'easy_apply').strip().lower()
        if plat not in grouped:
            grouped[plat] = {'easy_apply': [], 'company_site': []}
        if atype == 'company_site':
            grouped[plat]['company_site'].append(job)
        else:
            grouped[plat]['easy_apply'].append(job)

    sections_html = []
    global_idx = 1

    def render_table_rows(jobs_subset):
        nonlocal global_idx
        t_rows = []
        for job in jobs_subset:
            comp = job.get('company') or 'Company'
            role = job.get('role') or job.get('title') or 'Software Engineer'
            apply_url = job.get('apply_link') or job.get('url') or ''
            resume_url = job.get('supabase_resume_url') or job.get('resume_url') or ''

            if apply_url.startswith("mailto:"):
                display_email = apply_url.replace("mailto:", "").split("?")[0]
                apply_html = f'''
                    <div class="action-cell">
                        <a href="{apply_url}" class="apply-link email-btn">✉️ Send Email ({display_email})</a>
                    </div>
                '''
            elif apply_url.startswith("http://") or apply_url.startswith("https://"):
                short_url = re.sub(r'^https?://(www\.)?', '', apply_url).split('?')[0]
                if len(short_url) > 42:
                    short_url = short_url[:39] + "..."
                apply_html = f'''
                    <div class="action-cell">
                        <a href="{apply_url}" class="apply-link" target="_blank">Apply Now &rarr;</a>
                        <span class="url-text"><a href="{apply_url}" class="raw-url" target="_blank">{short_url}</a></span>
                    </div>
                '''
            else:
                apply_html = f'''
                    <div class="action-cell">
                        <span class="referral-badge">📌 {apply_url or "Direct Submission"}</span>
                    </div>
                '''

            # For Easy Apply roles, no resume is generated or required (per protocol)
            atype = str(job.get('apply_type') or 'easy_apply').strip().lower()
            if atype == 'easy_apply':
                resume_html = '''
                    <div class="action-cell">
                        <span class="easy-pill" style="font-size: 9.5px; background: #eff6ff; border: 1px solid #bfdbfe; padding: 3px 6px; border-radius: 4px; display: inline-block;">
                            ⚡ In-Platform Apply (No Resume Required)
                        </span>
                    </div>
                '''
            elif resume_url.startswith("http://") or resume_url.startswith("https://"):
                short_res = re.sub(r'^https?://(www\.)?', '', resume_url).split('?')[0]
                filename_match = re.search(r'[^/]+$', short_res)
                res_label = filename_match.group(0) if filename_match else short_res
                if len(res_label) > 35:
                    res_label = res_label[:32] + "..."
                resume_html = f'''
                    <div class="action-cell">
                        <a href="{resume_url}" class="apply-link resume-btn" target="_blank">📄 View Resume &rarr;</a>
                        <span class="url-text"><a href="{resume_url}" class="raw-url" target="_blank">{res_label}</a></span>
                    </div>
                '''
            else:
                resume_html = '<span style="color: #94a3b8; font-size: 10px;">Pending / Direct Portal</span>'

            if has_resume_links:
                t_rows.append(f"""
                <tr>
                    <td class="col-num">{global_idx}</td>
                    <td class="col-company"><strong>{comp}</strong></td>
                    <td class="col-role">{role}</td>
                    <td class="col-link">{apply_html}</td>
                    <td class="col-resume">{resume_html}</td>
                </tr>
                """)
            else:
                t_rows.append(f"""
                <tr>
                    <td class="col-num">{global_idx}</td>
                    <td class="col-company"><strong>{comp}</strong></td>
                    <td class="col-role">{role}</td>
                    <td class="col-link">{apply_html}</td>
                </tr>
                """)
            global_idx += 1
        return "\n".join(t_rows)

    for platform_name, types_dict in grouped.items():
        total_plat_jobs = len(types_dict['easy_apply']) + len(types_dict['company_site'])
        if total_plat_jobs == 0:
            continue

        plat_header_html = f"""
        <div class="platform-block">
            <div class="platform-title-bar">
                <span class="platform-badge">🏢 {platform_name.upper()}</span>
                <span class="platform-meta">{total_plat_jobs} role{'s' if total_plat_jobs > 1 else ''} found</span>
            </div>
        """

        # Easy Apply Sub-section
        easy_jobs = types_dict['easy_apply']
        if easy_jobs:
            plat_header_html += f"""
            <div class="category-header easy-header">
                <span class="cat-pill easy-pill">⚡ Easy Apply (1-Click Application)</span>
                <span class="cat-count">{len(easy_jobs)} jobs</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th class="col-num-th">#</th>
                        <th class="col-comp-th">Company Name</th>
                        <th class="col-role-th">Role</th>
                        <th class="col-link-th">Direct Apply Link</th>
                        {th_resume}
                    </tr>
                </thead>
                <tbody>
                    {render_table_rows(easy_jobs)}
                </tbody>
            </table>
            """

        # Company Site Sub-section
        comp_jobs = types_dict['company_site']
        if comp_jobs:
            plat_header_html += f"""
            <div class="category-header company-header">
                <span class="cat-pill company-pill">🌐 Company Site (Direct ATS Portal)</span>
                <span class="cat-count">{len(comp_jobs)} jobs</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th class="col-num-th">#</th>
                        <th class="col-comp-th">Company Name</th>
                        <th class="col-role-th">Role</th>
                        <th class="col-link-th">Direct Apply Link</th>
                        {th_resume}
                    </tr>
                </thead>
                <tbody>
                    {render_table_rows(comp_jobs)}
                </tbody>
            </table>
            """

        plat_header_html += "</div>"
        sections_html.append(plat_header_html)

    body_content_html = "\n".join(sections_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    @page {{
        size: {page_orientation};
        margin: 12mm 15mm;
    }}
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #0f172a;
        background: #ffffff;
        font-size: 11px;
        line-height: 1.4;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}
    .header {{
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 2px solid #0f172a;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }}
    .title-block h1 {{
        font-size: 18px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
        margin-bottom: 3px;
    }}
    .title-block p {{
        font-size: 11px;
        color: #64748b;
    }}
    .meta-block {{
        text-align: right;
        font-size: 10.5px;
        color: #475569;
    }}
    .meta-block strong {{
        color: #0f172a;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 6px;
        table-layout: fixed;
    }}
    thead {{
        display: table-header-group;
    }}
    thead th {{
        background-color: #0f172a;
        color: #ffffff;
        text-align: left;
        padding: 9px 12px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        border: 1px solid #0f172a;
    }}
    thead th.col-num-th {{
        width: 4%;
        text-align: center;
    }}
    thead th.col-comp-th {{
        width: 20%;
    }}
    thead th.col-role-th {{
        width: 24%;
    }}
    thead th.col-link-th {{
        width: 26%;
    }}
    thead th.col-resume-th {{
        width: 26%;
    }}
    tbody tr {{
        border-bottom: 1px solid #e2e8f0;
        page-break-inside: avoid;
    }}
    tbody tr:nth-child(even) {{
        background-color: #f8fafc;
    }}
    tbody td {{
        padding: 9px 12px;
        vertical-align: middle;
        border: 1px solid #e2e8f0;
        word-wrap: break-word;
    }}
    .col-num {{
        text-align: center;
        font-weight: 600;
        color: #64748b;
        font-size: 10.5px;
    }}
    .col-company {{
        font-size: 11.5px;
        color: #0f172a;
    }}
    .col-role {{
        font-size: 11px;
        color: #334155;
        font-weight: 500;
    }}
    .col-link, .col-resume {{
        font-size: 10.5px;
    }}
    .action-cell {{
        display: flex;
        flex-direction: column;
        gap: 3px;
    }}
    .apply-link {{
        display: inline-block;
        background-color: #1e40af;
        color: #ffffff !important;
        text-decoration: none !important;
        font-weight: 700;
        font-size: 10px;
        padding: 4px 10px;
        border-radius: 4px;
        width: fit-content;
        letter-spacing: 0.01em;
    }}
    .resume-btn {{
        background-color: #0f766e !important;
    }}
    .email-btn {{
        background-color: #047857;
    }}
    .url-text {{
        font-size: 9px;
        color: #64748b;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 220px;
    }}
    .raw-url {{
        color: #64748b !important;
        text-decoration: none !important;
    }}
    .referral-badge {{
        font-size: 10.5px;
        font-weight: 600;
        color: #b45309;
        background-color: #fef3c7;
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
    }}
    .platform-block {{
        margin-top: 14px;
        margin-bottom: 20px;
    }}
    .platform-title-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0f172a;
        color: #ffffff;
        padding: 8px 14px;
        border-radius: 6px 6px 0 0;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.05em;
        page-break-after: avoid;
        break-after: avoid;
    }}
    .platform-badge {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .platform-meta {{
        font-size: 11px;
        color: #94a3b8;
        font-weight: 500;
    }}
    .category-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 12px;
        font-size: 11px;
        font-weight: 700;
        border-left: 4px solid #3b82f6;
        border-right: 1px solid #e2e8f0;
        margin-top: 4px;
        page-break-after: avoid;
        break-after: avoid;
    }}
    .easy-header {{
        background: #eff6ff;
        border-left-color: #2563eb;
    }}
    .company-header {{
        background: #f8fafc;
        border-left-color: #64748b;
    }}
    .cat-pill {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10.5px;
    }}
    .easy-pill {{
        color: #1d4ed8;
        font-weight: 700;
    }}
    .company-pill {{
        color: #334155;
        font-weight: 700;
    }}
    .cat-count {{
        font-size: 10px;
        color: #64748b;
        font-weight: 600;
    }}
    .footer {{
        margin-top: 20px;
        text-align: center;
        font-size: 10px;
        color: #94a3b8;
        border-top: 1px solid #e2e8f0;
        padding-top: 10px;
    }}
</style>
</head>
<body>

<div class="header">
    <div class="title-block">
        <h1>📋 Job Applications &amp; Tailored Resumes</h1>
        <p>Categorized by Platform and Application Type (⚡ Easy Apply vs 🌐 Company Site)</p>
    </div>
    <div class="meta-block">
        <div><strong>Candidate:</strong> Kaustubh Kale</div>
        <div><strong>Date:</strong> {today_str}</div>
        <div><strong>Total Roles:</strong> {len(jobs_data)}</div>
    </div>
</div>

{body_content_html}

<div class="footer">
    Antigravity JobHunt Automation • Click any link to open employer application or view tailored resume
</div>

</body>
</html>
"""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content)
            page.pdf(
                path=str(pdf_path),
                format="A4",
                landscape=has_resume_links,
                print_background=True,
                margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"}
            )
            browser.close()
        logger.info(f"📄 Table PDF generated successfully: {pdf_path}")
        return str(pdf_path)
    except Exception as e:
        logger.error(f"Failed to generate table PDF: {e}")
        return ""
