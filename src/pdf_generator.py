import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from src.config_loader import load_config, load_resume
from src.logger import logger
from src.models import Job


def generate_pdf(job: Job, tailored_resume: dict, date_str: str, page) -> str:
    """
    Generate a PDF resume from the tailored resume dict using Playwright.
    
    Filename format: CompanyName_CandidateName_Resume.pdf
    """
    config = load_config()
    # Organize into categorized sub-folders: <platform>/<apply_type>/
    platform = (getattr(job, "source", None) or "general").lower().replace("workday-", "")
    apply_type = (getattr(job, "apply_type", None) or "easy_apply").lower()

    out_dir_path = Path(config['output']['desktop_path']) / config['output']['folder_name'] / date_str / platform / apply_type
    out_dir_path.mkdir(parents=True, exist_ok=True)

    import re
    # Build filename: JobTitle_CompanyName.pdf
    safe_title = "".join([c if c.isalnum() else "_" for c in job.title]).strip("_")
    safe_company = "".join([c if c.isalnum() else "_" for c in job.company]).strip("_")
    
    # Remove duplicate underscores
    safe_title = re.sub(r'_+', '_', safe_title)
    safe_company = re.sub(r'_+', '_', safe_company)
    
    pdf_filename = f"{safe_title}_{safe_company}.pdf"
    pdf_path = out_dir_path / pdf_filename

    # Jinja2 setup
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("resume_template.html")

    # Generate HTML from template + tailored data + job data
    html_out = template.render(resume=tailored_resume, job=job)

    # Convert HTML → PDF using the shared Playwright Page object
    try:
        page.set_content(html_out)
        
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"}  # Margins handled by CSS
        )
            
        logger.info(f"   ✅ Saved: {platform}/{apply_type}/{pdf_filename}")

        # Local workspace output mirror
        try:
            import shutil
            local_dir = Path(__file__).parent.parent / "output" / "resumes" / platform / apply_type
            local_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(pdf_path), str(local_dir / pdf_filename))
        except Exception:
            pass

        # Mirror to alternate desktop if both local Desktop and OneDrive Desktop exist
        try:
            import shutil
            alt_base = Path("C:/Users/kalek/OneDrive/Desktop") if "OneDrive" not in str(out_dir_path) else Path("C:/Users/kalek/Desktop")
            if alt_base.exists():
                alt_dir = alt_base / config['output']['folder_name'] / date_str / platform / apply_type
                alt_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(pdf_path), str(alt_dir / pdf_filename))
        except Exception:
            pass

        # Universal ATS Acceptance Audit
        try:
            from ats_verifier import audit_resume_pdf
            audit_result = audit_resume_pdf(str(pdf_path))
            if not audit_result["passed"]:
                logger.error(f"   ❌ ATS Compliance Violations in {pdf_filename}: {audit_result['errors']}")
            else:
                logger.info(f"   🛡️ ATS Audit Verified [100% ATS Safe]: {pdf_filename}")
        except Exception as ae:
            logger.warning(f"   ⚠️ ATS Audit skipped: {ae}")

        return str(pdf_path)
    except Exception as e:
        logger.error(f"   ❌ Error generating PDF for {job.company}: {e}")
        return ""


def generate_resume_pdf(tailored_resume: dict, output_path: str, job: Job = None) -> str:
    """
    Generate a 1-page ATS-friendly PDF resume directly to output_path.
    Creates its own Playwright browser session for standalone execution.
    Automatically audits output using Universal ATS Acceptance Suite.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("resume_template.html")

    html_out = template.render(resume=tailored_resume, job=job)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.set_content(html_out)
                page.pdf(
                    path=str(out_file),
                    format="A4",
                    print_background=True,
                    margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"}
                )
                logger.info(f"   ✅ Saved: {out_file.name}")

                # Universal ATS Acceptance Audit
                try:
                    from ats_verifier import audit_resume_pdf
                    audit_result = audit_resume_pdf(str(out_file))
                    if not audit_result["passed"]:
                        logger.error(f"   ❌ ATS Compliance Violations in {out_file.name}: {audit_result['errors']}")
                    else:
                        logger.info(f"   🛡️ ATS Audit Verified [100% ATS Safe]: {out_file.name}")
                except Exception as ae:
                    logger.warning(f"   ⚠️ ATS Audit skipped: {ae}")

                return str(out_file)
            finally:
                browser.close()
    except Exception as e:
        logger.error(f"   ❌ Error generating standalone PDF: {e}")
        return ""