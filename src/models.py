from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Job:
    title: str
    company: str
    location: str
    description: str          # Full cleaned description from Phase 1
    url: str
    source: str = ""          # Which platform (LinkedIn, Indeed, etc.)
    score: Optional[int] = None
    missing_skills: Optional[List[str]] = None   # Skills candidate LACKS for this role
    reasons: Optional[str] = None
