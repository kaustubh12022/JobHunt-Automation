import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from src.logger import logger


def package_pipeline_archive(
    pdf_paths: list[str] = None,
    table_pdf_path: str = None,
    date_str: str = None,
    desktop_dir: Path = None,
) -> str:
    """
    Packages the generated resume PDFs and Job_Applications_Table.pdf into a deliverable ZIP archive.

    Archive Structure:
    ├── Job_Applications_Table.pdf (root)
    └── resumes/
        ├── Company1_Role_Resume.pdf
        └── ...
    
    Saves to local Desktop and automatically mirrors to OneDrive Desktop if available.
    """
    now = datetime.now()
    if not date_str:
        date_str = now.strftime("%Y-%m-%d")

    if not desktop_dir:
        desktop_dir = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"

    # Primary archive name: '<Date>.zip' (e.g. '4 October.zip')
    human_day_month_str = f"{now.day} {now.strftime('%B')}"
    zip_filename = f"{human_day_month_str}.zip"
    primary_zip_path = desktop_dir / zip_filename

    # Identify Table PDF & CSV
    candidate_tables = [
        Path(table_pdf_path) if table_pdf_path else None,
        desktop_dir / "Job_Applications_Table.pdf",
        desktop_dir / "Resume_Created_Jobs.pdf",
        Path("C:/Users/kalek/OneDrive/Desktop/Job_Applications_Table.pdf"),
        Path("C:/Users/kalek/OneDrive/Desktop/Resume_Created_Jobs.pdf"),
    ]
    resolved_table_pdf = None
    for cand in candidate_tables:
        if cand and cand.exists() and cand.stat().st_size > 0:
            resolved_table_pdf = cand
            break

    candidate_csvs = [
        desktop_dir / "Job_Applications_Table.csv",
        Path("C:/Users/kalek/OneDrive/Desktop/Job_Applications_Table.csv"),
    ]
    resolved_table_csv = None
    for cand_c in candidate_csvs:
        if cand_c and cand_c.exists() and cand_c.stat().st_size > 0:
            resolved_table_csv = cand_c
            break

    # Identify resume files
    resumes_map: dict[str, Path] = {}
    EXCLUDED_NAMES = {
        "job_applications_table.pdf",
        "resume_created_jobs.pdf",
        "summary.pdf",
        "job_applications_table.csv",
    }

    # 1. From provided pdf_paths
    if pdf_paths:
        for p in pdf_paths:
            if p and Path(p).exists() and Path(p).suffix.lower() == ".pdf":
                path_obj = Path(p)
                if path_obj.name.lower() not in EXCLUDED_NAMES:
                    resumes_map[path_obj.name] = path_obj

    # 2. From standard output directories only if pdf_paths was empty
    if not resumes_map:
        search_dirs = [
            desktop_dir / "AutoApply_Output" / date_str,
            desktop_dir / f"Resumes_{date_str}",
            desktop_dir / f"Tailored_Resumes_{date_str}",
            Path("C:/Users/kalek/OneDrive/Desktop/AutoApply_Output") / date_str,
            Path("C:/Users/kalek/OneDrive/Desktop") / f"Tailored_Resumes_{date_str}",
        ]
        for s_dir in search_dirs:
            if s_dir.exists():
                for pdf_file in s_dir.rglob("*.pdf"):
                    if pdf_file.stat().st_size > 0 and pdf_file.name.lower() not in EXCLUDED_NAMES:
                        resumes_map[pdf_file.name] = pdf_file

    resume_files = sorted(list(resumes_map.values()), key=lambda x: x.name)

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"📦 PACKAGING PIPELINE ARCHIVE: {zip_filename}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"   Table PDF: {resolved_table_pdf if resolved_table_pdf else 'NOT FOUND'}")
    logger.info(f"   Table CSV: {resolved_table_csv if resolved_table_csv else 'NOT FOUND'}")
    logger.info(f"   Resumes Found: {len(resume_files)}")

    # Build the ZIP
    with zipfile.ZipFile(primary_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Add Job_Applications_Table.pdf at the root
        if resolved_table_pdf and resolved_table_pdf.exists():
            zf.write(resolved_table_pdf, arcname="Job_Applications_Table.pdf")
            logger.info("   ➕ Added: Job_Applications_Table.pdf (root)")
        else:
            logger.warning("   ⚠️ Warning: Job_Applications_Table.pdf was not found for archive root.")

        # Add Job_Applications_Table.csv at the root if available
        if resolved_table_csv and resolved_table_csv.exists():
            zf.write(resolved_table_csv, arcname="Job_Applications_Table.csv")
            logger.info("   ➕ Added: Job_Applications_Table.csv (root)")

        # Add resumes categorized by platform and apply_type subfolders
        for rf in resume_files:
            parent_name = rf.parent.name.lower()
            grandparent_name = rf.parent.parent.name.lower()
            if parent_name in ["easy_apply", "company_site"]:
                arcname = f"resumes/{grandparent_name}/{parent_name}/{rf.name}"
            else:
                arcname = f"resumes/{rf.name}"
            zf.write(rf, arcname=arcname)
        logger.info(f"   ➕ Added {len(resume_files)} resumes to categorized 'resumes/' subfolders.")

    # Integrity verification
    if primary_zip_path.exists() and primary_zip_path.stat().st_size > 0:
        size_mb = primary_zip_path.stat().st_size / (1024 * 1024)
        logger.info(f"   ✅ ZIP ARCHIVE CREATED: {primary_zip_path} ({size_mb:.2f} MB)")

        # Verify contents
        with zipfile.ZipFile(primary_zip_path, "r") as zf:
            file_list = zf.namelist()
            has_table = "Job_Applications_Table.pdf" in file_list
            resumes_count = sum(1 for f in file_list if (f.startswith("resumes/") or f.startswith("resume/")) and f.endswith(".pdf"))
            logger.info(f"   Archive Verification: Total {len(file_list)} items:")
            logger.info(f"     - Root Job_Applications_Table.pdf: {'YES' if has_table else 'NO'}")
            logger.info(f"     - Resumes in 'resumes/' folder: {resumes_count}")

        # Mirror to OneDrive Desktop if exists
        onedrive_desktop = Path("C:/Users/kalek/OneDrive/Desktop")
        if onedrive_desktop.exists() and str(onedrive_desktop) != str(desktop_dir):
            try:
                shutil.copy2(primary_zip_path, onedrive_desktop / zip_filename)
                logger.info(f"   ☁️ Mirrored archive {zip_filename} to OneDrive Desktop.")
            except Exception as e:
                logger.debug(f"Could not mirror to OneDrive Desktop: {e}")

        return str(primary_zip_path)
    else:
        logger.error(f"   ❌ Failed to create valid ZIP archive at {primary_zip_path}")
        return ""
