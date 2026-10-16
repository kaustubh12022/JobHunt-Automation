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
    apply_type: str = "company_site" # easy_apply or company_site
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
    cost_usd: float = 0.0
    token_usage: dict = field(default_factory=dict)
    date_posted: Optional[object] = None
    is_remote: Optional[bool] = False
    min_experience: Optional[int] = None   # Minimum years required (0 = fresher-eligible, None = unknown)
    max_experience: Optional[int] = None   # Maximum years in range
    raw_metadata: Optional[dict] = None
    applicant_count: Optional[int] = None
    is_early_applicant: Optional[bool] = None
    early_priority_tier: Optional[str] = None  # "TIER_1_IMMEDIATE", "TIER_2_EARLY", "TIER_3_NORMAL", "TIER_4_SATURATED"
    is_consultancy_spam: Optional[bool] = None
    veto_reason: Optional[str] = None
    application_status: Optional[str] = "DISCOVERED"
    submission_proof: Optional[dict] = None
