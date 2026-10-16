"""
consultancy_veto.py — Deduplication and Consultancy/Spam Repost Veto Filtering Engine.

Responsible for Pillar 2:
- Protects freshers from fee-charging placement scams, training traps, non-IT bait-and-switch roles,
  and mass repost spam.
- Enforces strict zero-token pre-veto: drops junk before any AI token or resume generation is invoked.
- Multi-tier deduplication:
    1. Canonical clean URL matching (strips UTM, tracking tokens, session IDs)
    2. Normalized (company, clean_title, city) hashing
    3. Multi-city repost agency flood detection
"""

import re
import hashlib
import urllib.parse
from typing import Dict, Any, List, Tuple, Optional, Set
from src.logger import logger
from src.models import Job

# ── 1. FEE TRAP & SCAM PATTERNS ──
FEE_TRAP_PATTERNS = [
    (re.compile(r'(?i)\bregistration\s+(?:fee|charges?|amount|cost)\b'), "Registration Fee Required"),
    (re.compile(r'(?i)\bplacement\s+(?:charges?|fee|cost|amount)\b'), "Placement Charges"),
    (re.compile(r'(?i)\b(?:security|laptop|asset|equipment)\s+deposit\b'), "Security Deposit Required"),
    (re.compile(r'(?i)\btraining\s+(?:fee|charges?|cost|amount)\b'), "Training Fee Charged"),
    (re.compile(r'(?i)\bpay\s+after\s+placement(?:\s*\(pap\))?\b'), "Pay After Placement Trap"),
    (re.compile(r'(?i)\b(?:candidate|applicant|student|fresher)s?\s+(?:has\s+to|must|needs?\s+to|is\s+required\s+to|will\s+have\s+to|should)\s+(?:pay|deposit|transfer|bear)\b'), "Payment Requested from Candidate"),
    (re.compile(r'(?i)\brefundable\s+(?:deposit|amount|security)\b'), "Refundable Deposit Scheme"),
    (re.compile(r'(?i)\b100%\s+placement\s+guarantee\s+with\s+(?:training|course|fees?)\b'), "Placement Guarantee Course Trap"),
    (re.compile(r'(?i)\b(?:processing|documentation|interview|assessment|exam|test|selection|onboarding|offer\s+letter|verification|application|badge)\s+(?:charges?|fees?|cost|amount)\b'), "Fee Trap (Exam/Interview/Processing Charges)"),
    (re.compile(r'(?i)\bpay\s+(?:[\u20b9]|rs\.?|inr)\s*\d+'), "Direct Upfront Payment Required"),
    (re.compile(r'(?i)\btraining\s+(?:and|&)\s+placement\s+(?:program\s+)?with\s+(?:nominal\s+)?fees?\b'), "Training & Placement Fee Trap"),
    (re.compile(r'(?i)\bupfront\s+(?:charges?|fee|payment|amount)\b'), "Upfront Payment Trap"),
    (re.compile(r'(?i)\bbond\s+amount\s+(?:to\s+be\s+paid|required)\b'), "Upfront Bond Payment"),
]

def normalize_spaced_adversarial_text(text: str) -> str:
    """Collapses spaced-out adversarial text like 'r e g i s t r a t i o n   c h a r g e s' into 'registration charges'."""
    if not text:
        return ""
    # Collapse single-character spaces: 'r e g i s t r a t i o n' -> 'registration'
    collapsed = re.sub(r'(?<=\b[a-zA-Z])\s(?=[a-zA-Z]\b)', '', text)
    return re.sub(r'\s+', ' ', collapsed).strip()

# ── 2. FAKE CONSULTANCY & THIRD-PARTY AGGREGATOR PATTERNS ──
CONSULTANCY_PATTERNS = [
    (re.compile(r'(?i)\bhiring\s+on\s+behalf\s+of\s+(?:our\s+)?(?:top\s+)?(?:tier-?1\s+)?client\b'), "Third-Party Proxy Hiring"),
    (re.compile(r'(?i)\bclient\s+location\s+deputed\b'), "Third-Party Deputation"),
    (re.compile(r'(?i)\bthird[- ]?party\s+payroll\b'), "Third-Party Payroll Staffing"),
    (re.compile(r'(?i)\bcontract\s+to\s+hire\s+via\s+consultancy\b'), "Consultancy Proxy Staffing"),
    (re.compile(r'(?i)\bconfidential\s+client\s+hiring\b'), "Unrevealed Client Consultancy"),
]

# ── 3. NON-TECH BAIT-AND-SWITCH ROLES ──
NON_TECH_PATTERNS = [
    (re.compile(r'(?i)\b(?:telecalling|telecaller|tele-sales|telesales)\b'), "Non-Tech Telecalling Role"),
    (re.compile(r'(?i)\b(?:bpo|voice\s+process|non-voice\s+process|call\s+center)\b'), "BPO/Call Center Role"),
    (re.compile(r'(?i)\b(?:data\s+entry\s+operator|back\s+office\s+executive)\b'), "Data Entry / Back Office Role"),
    (re.compile(r'(?i)\b(?:field\s+sales|door\s+to\s+door|direct\s+marketing)\b'), "Field Sales Disguised as Tech"),
    (re.compile(r'(?i)\bcustomer\s+(?:support|care)\s+executive\b'), "Customer Care Executive"),
]

# Known predatory or spam consultancy keywords in company names
BLACKLIST_COMPANY_PATTERNS = [
    re.compile(r'(?i)\bplacement\s+(?:consultant|services?|solution|hub)\b'),
    re.compile(r'(?i)\bhr\s+(?:consultancy|consultants?|solutions?)\b'),
    re.compile(r'(?i)\bstaffing\s+(?:solutions?|hub|enterprises?)\b'),
    re.compile(r'(?i)\brecruitment\s+partners?\b'),
    re.compile(r'(?i)\bcareerstacks?\b'),
    re.compile(r'(?i)\bhirecraft\s+consulting\b'),
    re.compile(r'(?i)\bglobal\s+talent\s+recruiters\b'),
]


def normalize_url_for_dedup(url: str) -> str:
    """Strips tracking query params, session IDs, UTM tags, and trailing slashes."""
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if not parsed.netloc:
            return url.strip().lower()

        # Retain only non-tracking query parameters
        ignored_keys = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'refid', 'trackingid', 'tracking_id', 'trk', 'trkcampaign',
            'midtoken', 'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid',
            '_ga', '_gl', 'src', 'origin'
        }
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in query_pairs if k.lower() not in ignored_keys]
        new_query = urllib.parse.urlencode(filtered)
        clean_path = parsed.path.rstrip('/')

        normalized = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            '',
            new_query,
            ''
        ))
        return normalized
    except Exception:
        return url.strip().lower()


def compute_job_fingerprint(title: str, company: str, location: str = "") -> str:
    """Computes a canonical alphanumeric fingerprint for semantic deduplication."""
    t = re.sub(r'[^a-z0-9]', '', (title or "").lower())
    c = re.sub(r'[^a-z0-9]', '', (company or "").lower())
    loc = re.sub(r'[^a-z0-9]', '', (location or "").lower())
    raw = f"{c}_{t}_{loc}" if loc else f"{c}_{t}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def compute_description_hash(desc: str) -> str:
    """Computes a normalized text hash for identifying identical reposted job descriptions."""
    # Collapse all whitespace and strip non-alphanumeric
    cleaned = re.sub(r'[^a-z0-9]', '', (desc or "").lower())
    # Take first 1000 characters for robust agency repost detection
    return hashlib.sha256(cleaned[:1000].encode('utf-8')).hexdigest()


def is_consultancy_or_spam(job: Job) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Evaluates whether a job is a consultancy fee-trap, scam, or misleading non-tech role.
    Returns: (is_vetoed: bool, veto_reason: str or None, matched_pattern: str or None)
    """
    text_corpus = f"{job.title} {job.company} {job.description}"

    # 1. Company Name Veto
    company_name = job.company or ""
    for pat in BLACKLIST_COMPANY_PATTERNS:
        m = pat.search(company_name)
        if m:
            return (True, "Blacklisted Staffing Consultancy", m.group(0))

    # 2. Fee Trap Veto (Absolute zero-tolerance, including spaced-out adversarial text)
    norm_corpus = normalize_spaced_adversarial_text(text_corpus)
    for pat, reason in FEE_TRAP_PATTERNS:
        m = pat.search(text_corpus) or pat.search(norm_corpus)
        if m:
            return (True, f"Fee Trap: {reason}", m.group(0))

    # 3. Non-Tech Role Veto in Title
    for pat, reason in NON_TECH_PATTERNS:
        m = pat.search(job.title)
        if m:
            return (True, f"Non-Technical Role: {reason}", m.group(0))

    # 4. Third-Party Proxy Consultancy in Description
    for pat, reason in CONSULTANCY_PATTERNS:
        m = pat.search(job.description or "")
        if m:
            return (True, f"Consultancy Trap: {reason}", m.group(0))

    return (False, None, None)


def deduplicate_and_veto_reposts(
    jobs: List[Job],
    existing_seen_urls: Optional[Set[str]] = None,
    existing_seen_fingerprints: Optional[Set[str]] = None
) -> Tuple[List[Job], List[Job], Dict[str, Any]]:
    """
    Comprehensive deduplication and spam repost veto filter.
    Returns: (valid_jobs, vetoed_jobs, telemetry_report)
    """
    seen_urls: Set[str] = set(existing_seen_urls) if existing_seen_urls else set()
    seen_fingerprints: Set[str] = set(existing_seen_fingerprints) if existing_seen_fingerprints else set()
    seen_desc_hashes: Dict[str, int] = {}

    valid_jobs: List[Job] = []
    vetoed_jobs: List[Job] = []

    if isinstance(jobs, tuple):
        jobs = jobs[0]
    cleaned_jobs: List[Job] = []
    if isinstance(jobs, list):
        for item in jobs:
            if isinstance(item, list):
                cleaned_jobs.extend([x for x in item if isinstance(x, Job)])
            elif isinstance(item, Job):
                cleaned_jobs.append(item)
    jobs = cleaned_jobs

    metrics = {
        "total_incoming": len(jobs),
        "passed_valid": 0,
        "vetoed_total": 0,
        "vetoed_fee_traps": 0,
        "vetoed_consultancies": 0,
        "vetoed_non_tech": 0,
        "vetoed_duplicate_urls": 0,
        "vetoed_duplicate_fingerprints": 0,
        "vetoed_repost_spam": 0
    }

    for j in jobs:
        # A. URL Deduplication
        norm_url = normalize_url_for_dedup(j.url)
        if norm_url and norm_url in seen_urls:
            j.is_consultancy_spam = True
            j.veto_reason = "Duplicate URL across portals"
            j.application_status = "VETOED_SPAM"
            vetoed_jobs.append(j)
            metrics["vetoed_total"] += 1
            metrics["vetoed_duplicate_urls"] += 1
            continue

        # B. Consultancy / Spam Veto
        is_vetoed, reason, matched = is_consultancy_or_spam(j)
        if is_vetoed:
            j.is_consultancy_spam = True
            j.veto_reason = f"{reason} (matched: '{matched}')"
            j.application_status = "VETOED_SPAM"
            vetoed_jobs.append(j)
            metrics["vetoed_total"] += 1
            if "Fee Trap" in reason:
                metrics["vetoed_fee_traps"] += 1
            elif "Non-Technical" in reason:
                metrics["vetoed_non_tech"] += 1
            else:
                metrics["vetoed_consultancies"] += 1
            continue

        # C. Semantic Fingerprint Deduplication (Company + Title)
        fp = compute_job_fingerprint(j.title, j.company, j.location)
        # Only deduplicate when company name is known and meaningful
        unknown_company = (j.company or "").strip().lower() in {'', 'unknown', 'none', 'nan', 'null'}
        if not unknown_company and fp in seen_fingerprints:
            j.is_consultancy_spam = True
            j.veto_reason = f"Duplicate posting by {j.company} for {j.title}"
            j.application_status = "VETOED_SPAM"
            vetoed_jobs.append(j)
            metrics["vetoed_total"] += 1
            metrics["vetoed_duplicate_fingerprints"] += 1
            continue

        # D. Identical Description Cross-City Repost Flood Detection
        desc_hash = compute_description_hash(j.description)
        if desc_hash:
            seen_desc_hashes[desc_hash] = seen_desc_hashes.get(desc_hash, 0) + 1
            if seen_desc_hashes[desc_hash] > 2:
                # Same exact description flooded across >2 postings
                j.is_consultancy_spam = True
                j.veto_reason = "Multi-city mass repost spam (identical JD flood)"
                j.application_status = "VETOED_SPAM"
                vetoed_jobs.append(j)
                metrics["vetoed_total"] += 1
                metrics["vetoed_repost_spam"] += 1
                continue

        # Survived all checks: Record as valid
        if norm_url:
            seen_urls.add(norm_url)
        if not unknown_company:
            seen_fingerprints.add(fp)

        j.is_consultancy_spam = False
        j.veto_reason = None
        j.application_status = "DISCOVERED"
        valid_jobs.append(j)
        metrics["passed_valid"] += 1

    logger.info(
        f"🛡️ Consultancy & Repost Veto Audit: {metrics['total_incoming']} scanned → "
        f"{metrics['passed_valid']} valid, {metrics['vetoed_total']} vetoed "
        f"({metrics['vetoed_fee_traps']} fee traps, {metrics['vetoed_consultancies']} consultancies, "
        f"{metrics['vetoed_non_tech']} non-tech, {metrics['vetoed_repost_spam'] + metrics['vetoed_duplicate_fingerprints']} duplicates)"
    )

    return valid_jobs, vetoed_jobs, metrics
