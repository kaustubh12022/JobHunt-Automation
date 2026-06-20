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
    out_dir_path = Path(config['output']['desktop_path']) / config['output']['folder_name'] / date_str
    out_dir_path.mkdir(parents=True, exist_ok=True)

    # Get candidate name from master resume for filename
    master = load_resume()
    candidate_name = master.get('personal_information', {}).get('name', 'Candidate')
    candidate_surname = master.get('personal_information', {}).get('surname', '')
    full_name = f"{candidate_name}_{candidate_surname}" if candidate_surname else candidate_name

    # Build filename: CompanyName_CandidateName_Resume.pdf
    safe_company = "".join([c if c.isalnum() else "_" for c in job.company]).strip("_")
    safe_name = "".join([c if c.isalnum() else "_" for c in full_name]).strip("_")
    pdf_filename = f"{safe_company}_{safe_name}_Resume.pdf"
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
        
        # Inject JavaScript to dynamically scale content to fit 1 page (A4 = 1122px height approx)
        page.evaluate("""
            const A4_HEIGHT_PX = 1100; // slightly under A4 to be safe
            let scrollHeight = document.documentElement.scrollHeight;
            if (scrollHeight > A4_HEIGHT_PX) {
                let scaleFactor = A4_HEIGHT_PX / scrollHeight;
                // Cap scaling at 0.85 to preserve readability
                if (scaleFactor < 0.80) scaleFactor = 0.80; 
                document.body.style.transform = `scale(${scaleFactor})`;
                document.body.style.transformOrigin = 'top left';
                document.body.style.width = `${100 / scaleFactor}%`;
            }
        """)

        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"} # Margins handled by CSS
        )
            
        logger.info(f"   ✅ Saved: {pdf_filename}")
        return str(pdf_path)
    except Exception as e:
        logger.error(f"   ❌ Error generating PDF for {job.company}: {e}")
        return ""