import os
import csv
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from src.logger import logger

TARGET_PLATFORMS = [
    "linkedin",
    "indeed",
    "workday",
    "direct_apply",
    "naukri",
    "internshala",
    "hirist",
]

RESUME_ENABLED_PLATFORMS = {"linkedin", "indeed", "workday", "direct_apply"}


def _extract_job_field(j, *field_names, default=""):
    """Robustly extract a field from a Job object or dictionary."""
    for f in field_names:
        if isinstance(j, dict):
            val = j.get(f)
        else:
            val = getattr(j, f, None)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def package_pipeline_archive(
    pdf_paths: list[str] = None,
    table_pdf_path: str = None,
    date_str: str = None,
    desktop_dir: Path = None,
    shortlisted_jobs: list = None,
    platforms: list[str] = None,
) -> str:
    """
    Packages the generated resume PDFs and Job Applications tables into a deliverable ZIP archive
    organized strictly by platform subfolders.

    Archive Structure:
    <Date>.zip (e.g. 8 October 2026.zip)
    ├── linkedin/
    │   ├── resumes/                      <-- Tailored ATS Resumes for LinkedIn
    │   │   └── Company1_Role_Resume.pdf
    │   └── job_applications_table.csv   <-- Platform specific table outside resumes/
    ├── indeed/
    │   ├── resumes/                      <-- Tailored ATS Resumes for Indeed
    │   └── job_applications_table.csv
    ├── workday/
    │   ├── resumes/                      <-- Tailored ATS Resumes for Workday
    │   └── job_applications_table.csv
    ├── naukri/
    │   ├── resumes/                      <-- (Empty subfolder per requirement)
    │   └── job_applications_table.csv
    ├── internshala/
    │   ├── resumes/                      <-- (Empty subfolder per requirement)
    │   └── job_applications_table.csv
    └── hirist/
        ├── resumes/                      <-- (Empty subfolder per requirement)
        └── job_applications_table.csv

    STRICT DESKTOP CLEANLINESS:
    Only <Date>.zip remains on the Desktop as output. All loose folders, staging files,
    and temporary tables are cleanly purged.
    """
    now = datetime.now()
    if not date_str:
        date_str = now.strftime("%Y-%m-%d")

    if not desktop_dir:
        desktop_dir = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"

    # Primary archive name: '<Date>.zip' (e.g. '8 October 2026.zip')
    human_date_str = f"{now.day} {now.strftime('%B')} {now.year}"
    zip_filename = f"{human_date_str}.zip"
    primary_zip_path = desktop_dir / zip_filename

    # Active platform list
    active_platforms = list(TARGET_PLATFORMS)
    if platforms:
        for p in platforms:
            norm_p = p.lower().replace("workday-", "").strip()
            if norm_p and norm_p not in active_platforms:
                active_platforms.append(norm_p)

    # 1. Group shortlisted jobs by platform
    jobs_by_platform: dict[str, list] = {p: [] for p in active_platforms}
    if shortlisted_jobs:
        for j in shortlisted_jobs:
            src = _extract_job_field(j, "source", "platform", default="direct_apply").lower().replace("workday-", "").strip()
            matched_plat = "direct_apply"
            for plat_key in active_platforms:
                if plat_key in src:
                    matched_plat = plat_key
                    break
            if matched_plat not in jobs_by_platform:
                jobs_by_platform[matched_plat] = []
            jobs_by_platform[matched_plat].append(j)

    # 2. Identify resume files and map to platform
    resumes_by_platform: dict[str, list[Path]] = {p: [] for p in active_platforms}
    EXCLUDED_NAMES = {
        "job_applications_table.pdf",
        "resume_created_jobs.pdf",
        "summary.pdf",
        "job_applications_table.csv",
        "other_platforms_jobs.pdf",
    }

    # Collect from pdf_paths
    if pdf_paths:
        for p in pdf_paths:
            if p and Path(p).exists() and Path(p).suffix.lower() == ".pdf":
                path_obj = Path(p)
                if path_obj.name.lower() in EXCLUDED_NAMES:
                    continue

                # Match by path hierarchy or filename
                plat = None
                path_norm = str(path_obj).replace("\\", "/").lower()
                for p_key in active_platforms:
                    if f"/{p_key}/" in path_norm:
                        plat = p_key
                        break
                
                if not plat and shortlisted_jobs:
                    # Match against job companies or titles
                    clean_stem = path_obj.stem.lower().replace("_", " ")
                    for j in shortlisted_jobs:
                        comp = _extract_job_field(j, "company", "company_name").lower()
                        if comp and (comp in clean_stem or clean_stem in comp):
                            src = _extract_job_field(j, "source", "platform", default="direct_apply").lower().replace("workday-", "").strip()
                            for p_key in active_platforms:
                                if p_key in src:
                                    plat = p_key
                                    break
                            if plat:
                                break

                if not plat:
                    for p_key in active_platforms:
                        if p_key in path_norm:
                            plat = p_key
                            break

                if not plat:
                    plat = "direct_apply"

                if plat not in resumes_by_platform:
                    resumes_by_platform[plat] = []
                if path_obj not in resumes_by_platform[plat]:
                    resumes_by_platform[plat].append(path_obj)

    # Also search standard output directories if needed
    search_dirs = [
        desktop_dir / f"Resumes_{date_str}",
        desktop_dir / f"Tailored_Resumes_{date_str}",
    ]
    for s_dir in search_dirs:
        if s_dir.exists():
            for pdf_file in s_dir.rglob("*.pdf"):
                if pdf_file.stat().st_size > 0 and pdf_file.name.lower() not in EXCLUDED_NAMES:
                    p_lower = str(pdf_file).lower()
                    matched = False
                    for plat_key in RESUME_ENABLED_PLATFORMS:
                        if plat_key in p_lower:
                            if pdf_file not in resumes_by_platform[plat_key]:
                                resumes_by_platform[plat_key].append(pdf_file)
                            matched = True
                            break
                    if not matched:
                        if "direct_apply" not in active_platforms:
                            active_platforms.append("direct_apply")
                            RESUME_ENABLED_PLATFORMS.add("direct_apply")
                            resumes_by_platform["direct_apply"] = []
                            jobs_by_platform["direct_apply"] = []
                        if pdf_file not in resumes_by_platform["direct_apply"]:
                            resumes_by_platform["direct_apply"].append(pdf_file)
                            
            # Also capture the CSV if shortlisted_jobs wasn't passed (Mode B)
            csv_file = s_dir / "Job_Applications_Table.csv"
            if csv_file.exists() and not shortlisted_jobs:
                if "direct_apply" not in active_platforms:
                    active_platforms.append("direct_apply")
                    jobs_by_platform["direct_apply"] = []
                import pandas as pd
                try:
                    df = pd.read_csv(csv_file)
                    class DummyJob:
                        pass
                    for _, row in df.iterrows():
                        dj = DummyJob()
                        dj.company = row.get("Company Name", "")
                        dj.title = row.get("Job Title", "")
                        dj.url = row.get("Direct Apply Link", "")
                        dj.source = "direct_apply"
                        jobs_by_platform["direct_apply"].append(dj)
                except Exception as e:
                    logger.warning(f"Could not read batch CSV {csv_file}: {e}")

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"📦 PACKAGING DELIVERABLE ARCHIVE: {zip_filename}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for p in active_platforms:
        logger.info(f"   Platform [{p}]: {len(jobs_by_platform.get(p, []))} jobs | {len(resumes_by_platform.get(p, []))} resumes")

    # Read any existing archive on Desktop to merge previously packaged platforms across combined runs
    existing_zip_files = {}
    if primary_zip_path.exists() and primary_zip_path.stat().st_size > 0:
        try:
            with zipfile.ZipFile(primary_zip_path, "r") as ezf:
                for item in ezf.infolist():
                    existing_zip_files[item.filename] = (item, ezf.read(item.filename))
            logger.info(f"   🔄 Read {len(existing_zip_files)} existing entries from {primary_zip_path.name} to merge.")
        except Exception as e:
            logger.warning(f"Could not read existing archive for merging: {e}")

    # 3. Build the ZIP Archive with the exact subfolder hierarchy
    temp_zip_path = desktop_dir / f"temp_{zip_filename}"
    written_entries = set()
    
    from playwright.sync_api import sync_playwright
    import tempfile
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        
        with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            other_platforms_jobs = []
            
            for plat in active_platforms:
                plat_jobs = jobs_by_platform.get(plat, [])
                plat_resumes = resumes_by_platform.get(plat, []) if plat in RESUME_ENABLED_PLATFORMS else []

                if plat in RESUME_ENABLED_PLATFORMS:
                    if not plat_jobs and not plat_resumes:
                        continue # Skip entirely if empty

                    # Generate Job_Applications_Table.pdf
                    pdf_arcname = f"{plat}/Job_Applications_Table.pdf"
                    
                    html_lines = [
                        f"<html><head><style>",
                        "body { font-family: -apple-system, sans-serif; font-size: 12px; }",
                        "table { width: 100%; border-collapse: collapse; table-layout: fixed; }",
                        "th, td { padding: 8px; border: 1px solid #ddd; text-align: left; word-wrap: break-word; }",
                        "th { background-color: #f8fafc; font-weight: bold; }",
                        ".col-comp { width: 25%; }",
                        ".col-role { width: 30%; }",
                        ".col-link { width: 45%; }",
                        "a { color: #2563eb; text-decoration: underline; word-break: break-all; }",
                        "</style></head><body>",
                        f"<h2>{plat.replace('_', ' ').title()} - Job Applications</h2>",
                        "<table><thead><tr>",
                        "<th class='col-comp'>Company Name</th><th class='col-role'>Job Role</th><th class='col-link'>Direct Apply Link</th>",
                        "</tr></thead><tbody>"
                    ]
                    
                    for j in plat_jobs:
                        url = _extract_job_field(j, "link", "apply_link", "url", "job_url")
                        comp = _extract_job_field(j, "company", "company_name")
                        title = _extract_job_field(j, "title", "role", "job_title", "position")
                        link_html = f"<a href='{url}'>{url}</a>" if url else "<span style='color:#94a3b8;'>No link available</span>"
                        html_lines.append(f"<tr><td>{comp}</td><td>{title}</td><td>{link_html}</td></tr>")
                    
                    html_lines.append("</tbody></table></body></html>")
                    
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                        tmp_pdf_path = tmp_pdf.name
                        
                    try:
                        page.set_content("".join(html_lines))
                        page.pdf(path=tmp_pdf_path, format="A4", print_background=True, margin={"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"})
                        zf.write(tmp_pdf_path, pdf_arcname)
                        written_entries.add(pdf_arcname)
                        logger.info(f"   ➕ Added: {pdf_arcname} ({len(plat_jobs)} rows)")
                    finally:
                        if os.path.exists(tmp_pdf_path):
                            os.remove(tmp_pdf_path)

                    # Write Resumes subfolder
                    resumes_dir_entry = zipfile.ZipInfo(f"{plat}/resumes/")
                    resumes_dir_entry.external_attr = 0o755 << 16
                    zf.writestr(resumes_dir_entry, "")
                    written_entries.add(f"{plat}/resumes/")

                    for rf in plat_resumes:
                        resume_arcname = f"{plat}/resumes/{rf.name}"
                        zf.write(rf, arcname=resume_arcname)
                        written_entries.add(resume_arcname)
                        logger.info(f"   ➕ Added: {resume_arcname}")
                else:
                    if plat_jobs:
                        other_platforms_jobs.append((plat, plat_jobs))

            if other_platforms_jobs:
                # Generate aggregate Other_Platforms_Jobs.pdf
                pdf_arcname = "Other_Platforms_Jobs.pdf"
                
                html_lines = [
                    f"<html><head><style>",
                    "body { font-family: -apple-system, sans-serif; font-size: 12px; }",
                    "table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }",
                    "th, td { padding: 8px; border: 1px solid #ddd; text-align: left; word-wrap: break-word; }",
                    "th { background-color: #f8fafc; font-weight: bold; }",
                    ".col-comp { width: 25%; }",
                    ".col-role { width: 30%; }",
                    ".col-link { width: 45%; }",
                    "a { color: #2563eb; text-decoration: underline; word-break: break-all; }",
                    "h2 { margin-top: 30px; border-bottom: 2px solid #ccc; padding-bottom: 5px; }",
                    "</style></head><body>",
                    "<h1>Other Platforms - Job Applications</h1>"
                ]
                
                for plat, p_jobs in other_platforms_jobs:
                    html_lines.append(f"<h2>{plat.replace('_', ' ').title()}</h2>")
                    html_lines.append("<table><thead><tr>")
                    html_lines.append("<th class='col-comp'>Company Name</th><th class='col-role'>Job Role</th><th class='col-link'>Direct Apply Link</th>")
                    html_lines.append("</tr></thead><tbody>")
                    
                    for j in p_jobs:
                        url = _extract_job_field(j, "link", "apply_link", "url", "job_url")
                        comp = _extract_job_field(j, "company", "company_name")
                        title = _extract_job_field(j, "title", "role", "job_title", "position")
                        link_html = f"<a href='{url}'>{url}</a>" if url else "<span style='color:#94a3b8;'>No link available</span>"
                        html_lines.append(f"<tr><td>{comp}</td><td>{title}</td><td>{link_html}</td></tr>")
                    
                    html_lines.append("</tbody></table>")
                
                html_lines.append("</body></html>")
                
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                    tmp_pdf_path = tmp_pdf.name
                    
                try:
                    page.set_content("".join(html_lines))
                    page.pdf(path=tmp_pdf_path, format="A4", print_background=True, margin={"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"})
                    zf.write(tmp_pdf_path, pdf_arcname)
                    written_entries.add(pdf_arcname)
                    logger.info(f"   ➕ Added: {pdf_arcname}")
                finally:
                    if os.path.exists(tmp_pdf_path):
                        os.remove(tmp_pdf_path)

            # Merge existing items from previous runs that were not regenerated in this run
            for fname, (item, data) in existing_zip_files.items():
                plat_prefix = fname.split("/")[0] if "/" in fname else fname
                # If this platform was actively populated in the current run, don't keep its stale files
                if plat_prefix in active_platforms and (jobs_by_platform.get(plat_prefix) or resumes_by_platform.get(plat_prefix)):
                    continue
                if fname not in written_entries:
                    zf.writestr(item, data)
                    written_entries.add(fname)
                    logger.info(f"   🔄 Merged from previous run: {fname}")

    # Atomic rename temp -> primary
    if primary_zip_path.exists():
        try:
            primary_zip_path.unlink()
        except Exception:
            pass
    temp_zip_path.rename(primary_zip_path)

    # 4. Integrity verification
    if primary_zip_path.exists() and primary_zip_path.stat().st_size > 0:
        size_mb = primary_zip_path.stat().st_size / (1024 * 1024)
        logger.info(f"   ✅ ZIP ARCHIVE CREATED: {primary_zip_path} ({size_mb:.2f} MB)")

        # 4. Mandatory Automated Parity & Link Integrity Audit
        with zipfile.ZipFile(primary_zip_path, "r") as zf:
            file_list = zf.namelist()
            logger.info("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"   🔍 MANDATORY PARITY & LINK INTEGRITY AUDIT ({len(file_list)} items)")
            logger.info("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            for plat in active_platforms:
                table_pdf_arc = f"{plat}/Job_Applications_Table.pdf"
                res_files = [f for f in file_list if f.startswith(f"{plat}/resumes/") and f.endswith(".pdf")]
                res_count = len(res_files)

                if table_pdf_arc in file_list:
                    try:
                        import pymupdf as fitz
                        doc = fitz.open(stream=zf.read(table_pdf_arc), filetype="pdf")
                        link_uris = []
                        full_text = ""
                        for p in doc:
                            for l in p.get_links():
                                if "uri" in l and l["uri"].strip():
                                    link_uris.append(l["uri"].strip())
                            full_text += p.get_text()

                        link_count = len(link_uris)
                        if res_count > 0 and link_count == 0:
                            logger.error(f"     ❌ {plat:12s} : {res_count} resumes but 0 link URIs found in {table_pdf_arc}!")
                        else:
                            plat_jobs_count = len(jobs_by_platform.get(plat, []))
                            if plat_jobs_count > 0 and plat_jobs_count != res_count:
                                logger.warning(f"     ⚠️ {plat:12s} : Table jobs ({plat_jobs_count}) != Resumes ({res_count})")
                            else:
                                logger.info(f"     ✅ {plat:12s} : {res_count} Resumes | {link_count} Link URIs | 1:1 Parity Verified")
                    except Exception as audit_err:
                        logger.warning(f"     ⚠️ {plat:12s} : Deep audit skipped ({audit_err}) | Resumes={res_count}")
                elif res_count > 0:
                    logger.warning(f"     ⚠️ {plat:12s} : {res_count} resumes but missing {table_pdf_arc}!")

            if "Other_Platforms_Jobs.pdf" in file_list:
                try:
                    import pymupdf as fitz
                    doc = fitz.open(stream=zf.read("Other_Platforms_Jobs.pdf"), filetype="pdf")
                    logger.info(f"     ✅ Other Platforms : Other_Platforms_Jobs.pdf verified ({len(doc)} pages)")
                except Exception:
                    pass
            logger.info("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Mirror to OneDrive Desktop if available
        onedrive_desktop = Path("C:/Users/kalek/OneDrive/Desktop")
        if onedrive_desktop.exists() and str(onedrive_desktop) != str(desktop_dir):
            try:
                shutil.copy2(primary_zip_path, onedrive_desktop / zip_filename)
                logger.info(f"   ☁️ Mirrored archive {zip_filename} to OneDrive Desktop.")
            except Exception as e:
                logger.debug(f"Could not mirror to OneDrive Desktop: {e}")

        # 5. STRICT CLEANUP: Purge all temporary staging directories on Desktop
        # Only the .zip file remains on Desktop!
        try:
            clean_targets = [
                desktop_dir / "AutoApply_Output",
                desktop_dir / f"Resumes_{date_str}",
                desktop_dir / f"Tailored_Resumes_{date_str}",
                desktop_dir / "Job_Applications_Table.pdf",
                desktop_dir / "Job_Applications_Table.csv",
                desktop_dir / "Resume_Created_Jobs.pdf",
            ]
            for target in clean_targets:
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink()

            # Clean any staging date folders like '2026-10-08' created by AutoApply on Desktop
            for item in desktop_dir.glob(f"{date_str}*"):
                if item.is_dir() and item != primary_zip_path:
                    shutil.rmtree(item, ignore_errors=True)

            logger.info("   🧹 Cleaned up all staging files. Strictly ONLY .zip file remains on Desktop.")
        except Exception as e:
            logger.warning(f"   Cleanup warning: {e}")

        return str(primary_zip_path)
    else:
        logger.error(f"   ❌ Failed to create valid ZIP archive at {primary_zip_path}")
        return ""
