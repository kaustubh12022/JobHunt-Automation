from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Job:
    title: str
    company: str
    location: str
    description: str          # Full cleaned description from Phase 1
    url: str
    id: Optional[str] = None
    source: str = ""          # Which platform (LinkedIn, Indeed, Workday, etc.)
    job_type: str = "fulltime" # fulltime or internship
    score: Optional[int] = None
    missing_skills: Optional[List[str]] = None   # Skills candidate LACKS for this role
    reasons: Optional[str] = None
    job_summary: Optional[str] = None
    extracted_requirements: Optional[str] = None
    is_testing_role: Optional[bool] = None
    unique_id: Optional[str] = None
    tailored_resume: Optional[dict] = None
    user_selected_skills: Optional[List[str]] = None
    tokens_used: int = 0
