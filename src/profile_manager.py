"""
profile_manager.py — Local Profile and Credential Persistence Engine.

Responsible for Pillar 4:
- Reads the master resume from Desktop (plain_text_resume.yaml or Resume_Dev_Updated.pdf).
- Normalizes and synchronizes credentials and profile data into config/profile.json and Desktop/profile.json.
- Validates profile completeness, ATS compliance (4-digit years, +91 phone, structured CGPA, 10th/12th),
  and persists local credentials and EEO data for autonomous job-application workflows.
"""

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from src.logger import logger

DEFAULT_DESKTOP_PATH = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"
PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_DIR / "config"
PROFILE_JSON_PATH = CONFIG_DIR / "profile.json"
DATA_FOLDER = PROJECT_DIR / "data_folder"


def find_desktop_resume_path(custom_path: Optional[str] = None) -> Path:
    """Locates the plain text resume YAML or PDF file on Desktop with safe fallbacks."""
    if custom_path and os.path.exists(custom_path):
        return Path(custom_path)

    candidates = [
        DEFAULT_DESKTOP_PATH / "plain_text_resume.yaml",
        DEFAULT_DESKTOP_PATH / "Resume_Dev_Updated.pdf",
        DEFAULT_DESKTOP_PATH / "apply bot" / "data_folder" / "plain_text_resume.yaml",
        DATA_FOLDER / "plain_text_resume.yaml",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c

    # Fallback to project data folder
    return DATA_FOLDER / "plain_text_resume.yaml"


def extract_resume_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Extracts candidate resume text and structured sections from a PDF file using pypdf."""
    import pypdf
    logger.info(f"📄 Extracting resume data from PDF: {pdf_path}")
    reader = pypdf.PdfReader(str(pdf_path))
    full_text = "\n".join([page.extract_text() or "" for page in reader.pages])

    # Load baseline master yaml structure if present for clean merging
    base_data = {}
    master_yaml = DATA_FOLDER / "plain_text_resume.yaml"
    if master_yaml.exists():
        try:
            with open(master_yaml, "r", encoding="utf-8") as f:
                base_data = yaml.safe_load(f) or {}
        except Exception:
            pass

    # Extract or verify key fields from PDF text
    personal = base_data.get("personal_information", {})
    if not personal.get("phone"):
        m_phone = re.search(r'\+91[- ]?\d{10}', full_text)
        if m_phone:
            personal["phone"] = m_phone.group(0)
    if not personal.get("email"):
        m_email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text)
        if m_email:
            personal["email"] = m_email.group(0)
    if not personal.get("linkedin"):
        m_li = re.search(r'linkedin\.com/in/[\w\-]+', full_text)
        if m_li:
            personal["linkedin"] = m_li.group(0)
    if not personal.get("github"):
        m_gh = re.search(r'github\.com/[\w\-]+', full_text)
        if m_gh:
            personal["github"] = m_gh.group(0)

    base_data["personal_information"] = personal
    base_data["raw_pdf_text"] = full_text
    return base_data


def load_desktop_resume_yaml(custom_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads and parses the master resume file (YAML or PDF) from the Desktop."""
    path = find_desktop_resume_path(custom_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found at: {path}")

    logger.info(f"📄 Loading master resume from: {path}")
    if path.suffix.lower() == ".pdf":
        return extract_resume_from_pdf(path)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def validate_profile_ats_invariants(profile: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates the generated profile data against ATS and Golden Standard rules:
    - 4-digit years (never 2-digit years like '25)
    - Standard contact block (+91-9975526627, Pune, Maharashtra, India)
    - Valid structured education with CGPA 7.51 / 10.0 and 10th/12th
    - Valid work experience and project history without hallucination
    """
    errors: List[str] = []

    # 1. Contact validation
    contact = profile.get("contact", {})
    phone = contact.get("phone", "")
    if not re.search(r"\+91[- ]?9975526627", phone):
        errors.append(f"Phone must be '+91-9975526627', got '{phone}'")

    location = contact.get("location", "")
    if "Pune" not in location:
        errors.append(f"Location must include 'Pune', got '{location}'")

    # 2. Year format checks in education and experience
    two_digit_pattern = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*'?\d{2}\b(?!\d{2})")
    
    for edu in profile.get("education", []):
        dates = edu.get("dates", "")
        if "'" in dates or re.search(r"\b\d{2}\s*-\s*\d{2}\b", dates):
            errors.append(f"Education dates must use 4-digit years: '{dates}'")
        score = edu.get("score", "")
        if "7.51" not in score:
            errors.append(f"Expected CGPA 7.51 in score, got '{score}'")

    for exp in profile.get("experience", []):
        dates = exp.get("dates", "")
        if re.search(r"\b[A-Za-z]{3}\s+\d{2}\b", dates):
            errors.append(f"Experience dates must use 4-digit years (e.g., 'Jan 2025'): '{dates}'")

    # 3. Minimum project presence
    projects = profile.get("projects", [])
    if len(projects) < 3:
        errors.append(f"Profile must contain at least 3 verified projects, found {len(projects)}")

    # 4. Verified skills
    skills = profile.get("skills", [])
    if len(skills) < 15:
        errors.append(f"Profile skills list is unusually short ({len(skills)} skills)")

    return (len(errors) == 0, errors)


def build_profile_from_resume(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a complete, normalized profile dictionary combining resume YAML data
    and verified EEO/demographic application answers.
    """
    personal = resume_data.get("personal_information", {})
    full_name = f"{personal.get('name', 'Kaustubh')} {personal.get('surname', 'Kale')}".strip()

    contact = {
        "location": personal.get("address", "Pune, Maharashtra, India"),
        "phone": personal.get("phone", "+91-9975526627"),
        "email": personal.get("email", "kaustubh.kale.work@gmail.com"),
        "linkedin": personal.get("linkedin", "linkedin.com/in/kaustubhkale12"),
        "github": personal.get("github", "github.com/kaustubhkale12")
    }

    # Education normalization
    education_raw = resume_data.get("education_details", [])
    education_clean = []
    for edu in education_raw:
        education_clean.append({
            "institution": edu.get("institution", "SKNSITS, Lonavala (Savitribai Phule Pune University)"),
            "location": edu.get("location", "Pune, India"),
            "degree": edu.get("education_level", "Bachelor of Engineering in Information Technology"),
            "dates": edu.get("dates", "2022 - 2026"),
            "score": edu.get("final_evaluation_grade", "Cumulative CGPA: 7.51 / 10.0"),
            "secondary_education": edu.get("secondary_education", [
                "12th (HSC): 82.33% | Maharashtra Board (2022)",
                "10th (SSC): 88.00% | Maharashtra Board (2020)"
            ])
        })

    # Experience normalization
    experience_raw = resume_data.get("experience_details", [])
    experience_clean = []
    for exp in experience_raw:
        bullets = []
        responsibilities = exp.get("key_responsibilities", [])
        if isinstance(responsibilities, list):
            for r in responsibilities:
                if isinstance(r, dict):
                    bullets.extend(list(r.values()))
                elif isinstance(r, str):
                    bullets.append(r)
        experience_clean.append({
            "company": exp.get("company", "CWIPedia Technologies"),
            "location": exp.get("location", "Pune, India"),
            "role": exp.get("position", "Java Developer Intern"),
            "dates": exp.get("dates", exp.get("employment_period", "Jan 2025 - Feb 2025")),
            "bullets": bullets
        })

    # Projects normalization
    projects_raw = resume_data.get("projects", [])
    projects_clean = []
    for proj in projects_raw:
        bullets = proj.get("description_bullets", [])
        desc = proj.get("description", " ".join(bullets) if bullets else "")
        projects_clean.append({
            "name": proj.get("name", ""),
            "tech_stack": proj.get("tech_stack", ""),
            "link": proj.get("link", "github.com/kaustubhkale12"),
            "description_bullets": bullets,
            "description": desc
        })

    # Certifications & Achievements
    certs_raw = resume_data.get("certifications", [])
    certs_clean = [c.get("name", "") if isinstance(c, dict) else str(c) for c in certs_raw if c]

    achieve_raw = resume_data.get("achievements", [])
    achieve_clean = []
    for a in achieve_raw:
        if isinstance(a, dict):
            name = a.get("name", "")
            desc = a.get("description", "")
            achieve_clean.append(f"{name}: {desc}" if desc else name)
        else:
            achieve_clean.append(str(a))

    # Structured skills definition
    structured_skills = {
        "Core Languages": [
            "Java", "Python", "SQL", "JavaScript", "TypeScript", "HTML", "CSS"
        ],
        "Java & Backend": [
            "Spring Boot", "Spring Core", "Hibernate/JPA", "REST APIs", "JDBC",
            "MySQL", "SQLite", "JWT Auth", "DB Schema Design", "MVC Architecture", "JSON"
        ],
        "MERN & Frontend": [
            "React", "Next.js", "Node.js", "Express", "MongoDB", "Mongoose",
            "State Management (Context/Redux)", "Tailwind CSS", "Vite"
        ],
        "Applied AI & Automation": [
            "Generative AI", "DeepSeek API", "LLM API Integration", "RAG & Vector Search",
            "MCP & Tool Calling", "LangChain", "Structured JSON Schema", "Prompt Engineering",
            "FastAPI", "AsyncIO Pipelines", "n8n AI Agents", "Telemetry & Logging"
        ],
        "CS Fundamentals": [
            "Data Structures & Algorithms", "OOP", "DBMS", "Problem-Solving"
        ],
        "Cloud/DevOps/Tools": [
            "Microsoft Azure Fundamentals", "Git", "GitHub", "Postman", "VS Code",
            "IntelliJ IDEA", "Maven", "Spring Tool Suite (STS)", "Agile/Scrum",
            "Linux/Bash", "Vercel & Render", "Cursor IDE & GitHub Copilot"
        ]
    }

    # Flat unique skills list
    raw_skills = resume_data.get("skills", [])
    flat_skills = list(dict.fromkeys(raw_skills)) if raw_skills else []
    for cat_list in structured_skills.values():
        for sk in cat_list:
            if sk not in flat_skills:
                flat_skills.append(sk)

    # Demographic / EEO AutoApply Answers
    eeo_answers = {
        "legal_full_name": "Kaustubh Sanjay Kale",
        "legal_first_name": "Kaustubh",
        "legal_middle_name": "Sanjay",
        "legal_last_name": "Kale",
        "gender": "Male",
        "transgender": "No",
        "sexual_orientation": "Straight / Heterosexual",
        "ethnicity": "Asian Indian",
        "disability": "No",
        "reasonable_adjustments": "No / None",
        "nationality": "Indian",
        "country_of_birth": "India",
        "citizenship": "India",
        "authorized_to_work_in_india": True,
        "requires_visa_sponsorship": False,
        "languages": ["English", "Hindi", "Marathi"],
        "preferred_language": "English",
        "address_line_1": "B-Wing, C-Building, 4th floor, C54, Suyog Aditya Residency",
        "address_line_2": "Bibawewadi",
        "full_address": "B-Wing, C-Building, 4th floor, C54, Suyog Aditya Residency, Bibawewadi, Pune 411037",
        "city": "Pune",
        "state": "Maharashtra",
        "country": "India",
        "zip_code": "411037"
    }

    profile = {
        "name": full_name,
        "contact": contact,
        "profile_summary": resume_data.get("profile_summary", ""),
        "education": education_clean,
        "experience": experience_clean,
        "projects": projects_clean,
        "achievements": achieve_clean,
        "certifications": certs_clean,
        "skills": flat_skills,
        "skills_structured": structured_skills,
        "target_roles": [
            "Java Developer",
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "AI / GenAI Developer"
        ],
        "eeo_answers": eeo_answers
    }

    return profile


def sync_profile_from_desktop(
    custom_resume_path: Optional[str] = None,
    save_to_desktop: bool = True
) -> Dict[str, Any]:
    """
    Full synchronization workflow:
    1. Reads Desktop plain_text_resume.yaml
    2. Builds normalized profile dictionary
    3. Validates against ATS standards
    4. Writes to config/profile.json and Desktop/profile.json
    5. Returns sync report
    """
    resume_path = find_desktop_resume_path(custom_resume_path)
    resume_data = load_desktop_resume_yaml(str(resume_path))
    profile = build_profile_from_resume(resume_data)

    valid, errors = validate_profile_ats_invariants(profile)
    if not valid:
        logger.warning(f"⚠️ Profile ATS validation warnings: {errors}")

    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4)
    logger.info(f"✅ Master profile synchronized to: {PROFILE_JSON_PATH}")

    desktop_profile_path = DEFAULT_DESKTOP_PATH / "profile.json"
    if save_to_desktop and DEFAULT_DESKTOP_PATH.exists():
        try:
            with open(desktop_profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=4)
            logger.info(f"✅ Desktop profile mirror updated: {desktop_profile_path}")
        except Exception as e:
            logger.warning(f"Could not write desktop profile mirror: {e}")

    return {
        "success": True,
        "source_resume": str(resume_path),
        "target_profile": str(PROFILE_JSON_PATH),
        "desktop_mirror": str(desktop_profile_path) if save_to_desktop else None,
        "skills_count": len(profile.get("skills", [])),
        "projects_count": len(profile.get("projects", [])),
        "ats_valid": valid,
        "validation_errors": errors
    }


def get_profile() -> Dict[str, Any]:
    """Retrieves current profile from config/profile.json, syncing if missing."""
    if not PROFILE_JSON_PATH.exists():
        logger.info("config/profile.json missing. Running automatic sync from Desktop resume...")
        sync_profile_from_desktop()
    with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    result = sync_profile_from_desktop()
    print("\n" + "=" * 50)
    print("      PROFILE SYNCHRONIZATION AUDIT REPORT")
    print("=" * 50)
    print(f"Source Resume  : {result['source_resume']}")
    print(f"Target Profile : {result['target_profile']}")
    print(f"Skills Total   : {result['skills_count']}")
    print(f"Projects Total : {result['projects_count']}")
    print(f"ATS Valid      : {'YES' if result['ats_valid'] else 'WARNINGS'}")
    if result["validation_errors"]:
        for e in result["validation_errors"]:
            print(f"  ⚠️ {e}")
    print("=" * 50)
