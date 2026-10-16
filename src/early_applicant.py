"""
early_applicant.py — Early-Applicant Detection (<20 Applicants Rule) & Fast Polling Engine.

Responsible for Pillar 1:
- In Indian fresher tech hiring (Naukri, LinkedIn, Indeed), applications submitted
  when applicant count is < 20 have a 5-10x higher review and interview rate.
- Extracts applicant counts and early-applicant badges from job descriptions, cards, and metadata.
- Classifies jobs into 4 Priority Tiers:
    * TIER_1_IMMEDIATE: < 10 applicants or < 2 hours old (Ultra-Fresh)
    * TIER_2_EARLY: < 20 applicants or < 6 hours old (Early Applicant Rule)
    * TIER_3_STANDARD: 20–50 applicants or < 24 hours old
    * TIER_4_SATURATED: > 50 applicants
- Provides FastPollingEngine for scheduled, rapid monitoring of fresh job streams.
"""

import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable
import pandas as pd

from src.logger import logger
from src.models import Job

# Regex patterns for detecting applicant counts across LinkedIn, Naukri, Indeed
APPLICANT_PATTERNS = [
    (re.compile(r'(?i)be\s+(?:one\s+of\s+|among\s+)?(?:the\s+)?first\s+(\d+)\s+applicants?'), True),
    (re.compile(r'(?i)(?:fewer|less)\s+than\s+(\d+)\s+applicants?'), True),
    (re.compile(r'(?i)under\s+(\d+)\s+applicants?'), True),
    (re.compile(r'(?i)<\s*(\d+)\s+applicants?'), True),
    (re.compile(r'(?i)first\s+(\d+)\s+applicants?'), True),
    (re.compile(r'(?i)applicants?\s*:\s*(\d+)'), False),
    (re.compile(r'(?i)applied\s*:\s*(\d+)'), False),
    (re.compile(r'(?i)(?:0\s*-\s*|1\s*-\s*)?(\d+)\s+applicants?'), False),
    (re.compile(r'(?i)(?:0\s*-\s*|1\s*-\s*)?(\d+)\s+candidates?\s+applied'), False),
    (re.compile(r'(?i)>?\s*(\d+)\s+(?:people|candidates?)\s+(?:have\s+)?applied'), False),
    (re.compile(r'(?i)applied\s+by\s+(\d+)\s+(?:candidates?|applicants?|people)'), False),
    (re.compile(r'(?i)\b(\d+)\s+applied\b'), False),
    (re.compile(r'(?i)over\s+(\d+)\s+applicants?'), False),
]

EARLY_BADGE_PATTERNS = [
    re.compile(r'(?i)\bearly\s+applicant\b'),
    re.compile(r'(?i)\bbe\s+an\s+early\s+applicant\b'),
    re.compile(r'(?i)\burgently\s+hiring\b'),
    re.compile(r'(?i)\bjust\s+posted\b'),
    re.compile(r'(?i)\bposted\s+today\b'),
]


def extract_applicant_count_and_tier(
    text: str,
    raw_metadata: Optional[Dict[str, Any]] = None,
    date_posted: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Extracts applicant count, early-applicant status, and priority tier
    from textual snippets or metadata dictionaries.
    """
    applicant_count: Optional[int] = None
    explicit_early_badge = False

    # Check raw metadata first if available
    if raw_metadata and isinstance(raw_metadata, dict):
        for k in ("num_applicants", "applicants", "applicant_count", "applications"):
            if k in raw_metadata and raw_metadata[k] is not None:
                try:
                    val = raw_metadata[k]
                    if isinstance(val, (int, float)):
                        applicant_count = int(val)
                        break
                    elif isinstance(val, str):
                        m = re.search(r'(\d+)', val)
                        if m:
                            applicant_count = int(m.group(1))
                            break
                except Exception:
                    pass

    # Scan text for explicit count patterns
    if text and isinstance(text, str):
        for pattern, is_explicit_early in APPLICANT_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    found_count = int(m.group(1))
                    if applicant_count is None:
                        applicant_count = found_count
                    if is_explicit_early:
                        explicit_early_badge = True
                    break
                except Exception:
                    pass

        # Scan for early badge indicators
        for badge_pat in EARLY_BADGE_PATTERNS:
            if badge_pat.search(text):
                explicit_early_badge = True
                break

    # Calculate hours old if date_posted is provided
    hours_old: Optional[float] = None
    if date_posted is not None:
        try:
            if isinstance(date_posted, pd.Timestamp):
                ts = date_posted
            else:
                ts = pd.to_datetime(date_posted, errors='coerce', utc=True)
            if pd.notna(ts):
                now = pd.Timestamp.now(tz=timezone.utc)
                diff = now - ts
                hours_old = max(0.0, diff.total_seconds() / 3600.0)
        except Exception:
            pass

    # Tier Classification Logic (<20 Applicants Rule & Early Badge Prioritization)
    tier: str
    priority_score_boost: int
    is_early_applicant: bool

    if explicit_early_badge:
        # Explicit early applicant badge (e.g. "be one of the first 25 applicants" or "early applicant badge")
        if (applicant_count is not None and applicant_count <= 10) or (hours_old is not None and hours_old <= 2.0):
            tier = "TIER_1_IMMEDIATE"
            priority_score_boost = 25
            is_early_applicant = True
        else:
            tier = "TIER_2_EARLY"
            priority_score_boost = 15
            is_early_applicant = True
    elif applicant_count is not None:
        if applicant_count < 10 or (hours_old is not None and hours_old <= 2.0):
            tier = "TIER_1_IMMEDIATE"
            priority_score_boost = 25
            is_early_applicant = True
        elif applicant_count < 20 or (hours_old is not None and hours_old <= 6.0):
            tier = "TIER_2_EARLY"
            priority_score_boost = 15
            is_early_applicant = True
        elif applicant_count <= 50:
            tier = "TIER_3_STANDARD"
            priority_score_boost = 0
            is_early_applicant = False
        else:
            tier = "TIER_4_SATURATED"
            priority_score_boost = -10
            is_early_applicant = False
    elif (hours_old is not None and hours_old <= 3.0):
        tier = "TIER_1_IMMEDIATE" if (hours_old is not None and hours_old <= 1.5) else "TIER_2_EARLY"
        priority_score_boost = 20
        is_early_applicant = True
        applicant_count = 10  # conservative estimated applicant count
    elif hours_old is not None and hours_old <= 12.0:
        tier = "TIER_2_EARLY"
        priority_score_boost = 10
        is_early_applicant = True
    elif hours_old is not None and hours_old <= 24.0:
        tier = "TIER_3_STANDARD"
        priority_score_boost = 0
        is_early_applicant = False
    else:
        tier = "TIER_3_STANDARD"
        priority_score_boost = 0
        is_early_applicant = False

    return {
        "applicant_count": applicant_count,
        "is_early_applicant": is_early_applicant,
        "early_priority_tier": tier,
        "priority_score_boost": priority_score_boost,
        "hours_old": round(hours_old, 1) if hours_old is not None else None,
        "explicit_early_badge": explicit_early_badge
    }


def evaluate_job_early_applicant(job: Job) -> Job:
    """Evaluates and annotates a Job object with early applicant metrics and tier."""
    metrics = extract_applicant_count_and_tier(
        text=f"{job.title} {job.description}",
        raw_metadata=getattr(job, "raw_metadata", None),
        date_posted=getattr(job, "date_posted", None)
    )

    job.applicant_count = metrics["applicant_count"]
    job.is_early_applicant = metrics["is_early_applicant"]
    job.early_priority_tier = metrics["early_priority_tier"]

    # Preserve base_score to guarantee idempotency across repeated evaluations
    if job.score is not None:
        if not hasattr(job, "base_score") or getattr(job, "base_score", None) is None:
            raw_meta = getattr(job, "raw_metadata", None) or {}
            base = raw_meta.get("base_score", job.score)
            setattr(job, "base_score", base)
            if isinstance(getattr(job, "raw_metadata", None), dict):
                job.raw_metadata["base_score"] = base

        base_score = getattr(job, "base_score", job.score)
        if metrics["priority_score_boost"] != 0:
            job.score = min(100, max(0, base_score + metrics["priority_score_boost"]))
        else:
            job.score = base_score

    return job


def filter_early_applicants(
    jobs: Any,
    max_applicants: int = 20,
    max_hours: float = 24.0
) -> Tuple[List[Job], List[Job]]:
    """
    Separates jobs into early applicants (meeting the <20 rule or high freshness)
    vs saturated/older postings.
    """
    if isinstance(jobs, tuple):
        jobs = jobs[0]
    flat_jobs: List[Job] = []
    if isinstance(jobs, list):
        for item in jobs:
            if isinstance(item, list):
                flat_jobs.extend([x for x in item if isinstance(x, Job)])
            elif isinstance(item, Job):
                flat_jobs.append(item)
    jobs = flat_jobs

    early_pool: List[Job] = []
    other_pool: List[Job] = []

    for j in jobs:
        evaluate_job_early_applicant(j)
        count = j.applicant_count
        tier = j.early_priority_tier

        # Qualifies if explicitly early, tier 1/2, or count < max_applicants
        if j.is_early_applicant or tier in ("TIER_1_IMMEDIATE", "TIER_2_EARLY"):
            early_pool.append(j)
        elif count is not None and count < max_applicants:
            early_pool.append(j)
        else:
            other_pool.append(j)

    return early_pool, other_pool


class FastPollingEngine:
    """
    High-frequency polling loop for monitoring new job postings
    and triggering early-applicant alerts.
    """
    def __init__(
        self,
        poll_interval_seconds: int = 900,  # 15 minutes default
        max_applicants_rule: int = 20,
        on_early_applicant_found: Optional[Callable[[Job], None]] = None
    ):
        self.poll_interval = poll_interval_seconds
        self.max_applicants = max_applicants_rule
        self.on_early_found = on_early_applicant_found
        self.seen_urls: set = set()
        self.is_running = False

    def mark_seen(self, url: str):
        if url:
            self.seen_urls.add(url.strip().lower())

    def process_incoming_jobs(self, jobs: Any) -> List[Job]:
        """Filters new unseen jobs and detects those meeting the early applicant rule."""
        if isinstance(jobs, tuple):
            jobs = jobs[0]
        flat_jobs: List[Job] = []
        if isinstance(jobs, list):
            for item in jobs:
                if isinstance(item, list):
                    flat_jobs.extend([x for x in item if isinstance(x, Job)])
                elif isinstance(item, Job):
                    flat_jobs.append(item)
        jobs = flat_jobs

        brand_new_jobs: List[Job] = []
        for j in jobs:
            clean_url = (j.url or "").strip().lower()
            if clean_url and clean_url in self.seen_urls:
                continue
            if clean_url:
                self.seen_urls.add(clean_url)

            evaluate_job_early_applicant(j)
            brand_new_jobs.append(j)

            if j.is_early_applicant and self.on_early_found:
                try:
                    self.on_early_found(j)
                except Exception as e:
                    logger.error(f"Error in early applicant callback: {e}")

        early_jobs = [j for j in brand_new_jobs if j.is_early_applicant]
        logger.info(
            f"⚡ Fast Poller Processed {len(jobs)} jobs: "
            f"{len(brand_new_jobs)} new, {len(early_jobs)} early-applicant (<{self.max_applicants})"
        )
        return brand_new_jobs
