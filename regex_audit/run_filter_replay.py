"""
Deterministic Two-Layer Filter Replay Harness
Replays all 1,137 jobs from regex_audit/master_raw_dataset_2026-09-29.jsonl
through Layer 1 (Pandas Pre-Filter) and Layer 2 (Scorer Regex Filter).

Zero AI/LLM calls.
Pure deterministic execution.
Verifies 100% accounting identity across all records.
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import pandas as pd

# Enforce UTF-8 encoding across Windows console & I/O
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Setup project root for local module imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper import build_location_regex, normalize_url
from src.scorer import (
    matches_senior_title,
    requires_3_plus_years,
    matches_out_of_scope_role,
    is_relevant_jd,
    OUT_OF_SCOPE_STACK_PATTERN,
    DOMAIN_ANCHORS,
    TECH_TOOLS
)

# Reference constants
DATASET_PATH = PROJECT_ROOT / "regex_audit" / "master_raw_dataset_2026-09-29.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "regex_audit" / "filter_results"

L1_PASS_PATH = OUTPUT_DIR / "layer1_pandas_pass.jsonl"
L1_FAIL_PATH = OUTPUT_DIR / "layer1_pandas_fail.jsonl"
L2_PASS_PATH = OUTPUT_DIR / "layer2_regex_pass.jsonl"
L2_FAIL_PATH = OUTPUT_DIR / "layer2_regex_fail.jsonl"

# Pinned collection timestamp to ensure 100% reproducible freshness evaluation
PINNED_SCRAPE_TIME = pd.Timestamp("2026-09-29T14:05:55Z")
HOURS_OLD = 72
CUTOFF_TIME = PINNED_SCRAPE_TIME - pd.Timedelta(hours=HOURS_OLD)

# Target search locations matching production configuration
TARGET_LOCATIONS = ["pune", "mumbai", "bangalore"]

# Patterns replicated from src.scorer for detailed attribution
SENIOR_KEYWORDS_PATTERN = (
    r'\b(?:senior|lead|manager|principal|director|head|vp|president|experienced|'
    r'architect|staff|expert|ii|iii|iv|v|vi|vii|viii|level\s*[2-9]|l[2-9])\b|\bsr[\.,\s]|\bsr$'
)
RANGE_TITLE_PAT = r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?\.?|yoe)'
SINGLE_TITLE_PAT = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?|yoe)'
WORDS_TO_NUM_TITLE = {
    'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
    'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
}
WORDS_LIST_TITLE = '|'.join(WORDS_TO_NUM_TITLE.keys())
WORD_TITLE_PAT = fr'\b({WORDS_LIST_TITLE})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b'

THIRD_PARTY_PREFIXES = (
    r'(?:our|the)\s+team\s+(?:has|have|with|of)',
    r'(?:work|working)\s+(?:with|alongside|beside|among)',
    r'(?:join|joining)\s+(?:a\s+)?team\s+(?:of|with)',
    r'(?:founded|established|started|operating|running)\s+(?:in|since|for|with)',
    r'(?:we\s+have|company\s+has|firm\s+has)\s+(?:over|more\s+than|been)',
    r'(?:our\s+company|our\s+firm|our\s+organisation)\s+(?:has|have)',
    r'colleagues?\s+(?:with|who\s+have)',
    r'mentors?\s+(?:with|who\s+have)',
    r'mentorship\s+from',
    r'(?:learn|learning)\s+from',
    r'(?:combined|collective|total)\s+experience',
    r'(?:history|heritage|industry)\s+(?:of|spanning)',
    r'(?:team|group|pool)\s+of\s+(?:engineers?|developers?|professionals?)\s+with',
    r'(?:senior\s+)?engineers?\s+(?:who\s+have|with\s+over)',
    r'in\s+\d{4}\s+with\s+\d+\s+years',
)

WORDS_TO_NUM_ALL = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12
}


def _tok_to_val(tok: str) -> int:
    tok_clean = tok.lower().strip()
    if tok_clean.isdigit():
        return int(tok_clean)
    return WORDS_TO_NUM_ALL.get(tok_clean, 0)


NUM_TOKENS = r'(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'
RANGE_SEP = r'(?:[-\u2013\u2014]|to|till|and)'
RANGE_PATTERN_EXP = fr'\b({NUM_TOKENS})\s*(?:\([^\)]+\)\s*)?{RANGE_SEP}\s*({NUM_TOKENS})\s*(?:\([^\)]+\)\s*)?(?:\+|or more|plus)?\s*(?:years?|yrs?\.?|yoe)\b'
PLUS_PATTERN_EXP = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than|plus)\s*(?:years?|yrs?\.?|yoe)'
MIN_PATTERN_EXP = r'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?\.?)?'
SINGLE_EXP_PATTERN = r'(?<![-\u2013\d])\b(\d+)\s*(?:years?|yrs?\.?)\s*(?:of\s+)?(?:experience|exp|hands[- ]on|relevant|background|industry|work)?'
YRS_PATTERN_EXP = r'(?<![-\u2013\d])\b(\d+)\s+yrs?\b'
WORD_PATTERN_EXP = fr'\b({WORDS_LIST_TITLE})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b'


def explain_senior_title(title: str) -> Tuple[str, Optional[str]]:
    """Determine the exact pattern and detail string for a rejected senior title."""
    if not title:
        return "Empty job title", None
    tl = title.lower()

    m = re.search(SENIOR_KEYWORDS_PATTERN, tl)
    if m:
        return f"Senior title keyword detected: '{m.group(0)}' in '{title}'", SENIOR_KEYWORDS_PATTERN

    for m in re.finditer(RANGE_TITLE_PAT, tl):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return f"Senior experience range '{m.group(0)}' detected in title '{title}'", RANGE_TITLE_PAT

    for m in re.finditer(SINGLE_TITLE_PAT, tl):
        num = int(m.group(1))
        has_plus = bool(re.search(r'\+|or more|more than|plus', m.group(0)))
        if has_plus and num >= 3:
            return f"Senior experience requirement '{m.group(0)}' detected in title '{title}'", SINGLE_TITLE_PAT
        if num >= 3 and not re.search(r'\b[012]\s*[-\u2013to]+\s*' + str(num), tl):
            return f"Senior experience requirement '{m.group(0)}' detected in title '{title}'", SINGLE_TITLE_PAT

    for m in re.finditer(WORD_TITLE_PAT, tl):
        if WORDS_TO_NUM_TITLE.get(m.group(1), 0) >= 3:
            preceding = tl[:m.start()]
            if not re.search(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014)\s*$', preceding):
                return f"Word-based senior experience requirement '{m.group(0)}' detected in title '{title}'", WORD_TITLE_PAT

    return "Senior title detected", None


def explain_experience_3_plus(desc: str) -> Tuple[str, Optional[str]]:
    """Determine the exact pattern and detail string for a rejected 3+ years experience JD."""
    if not isinstance(desc, str):
        return "Empty job description", None
    desc_lower = desc.lower().replace('\\', '')
    sentences = re.split(r'(?<=[.!?\n])\s*', desc_lower)
    candidate_sentences = [
        sent for sent in sentences
        if not any(re.search(pat, sent) for pat in THIRD_PARTY_PREFIXES)
    ]
    candidate_text = ' '.join(candidate_sentences)

    for m in re.finditer(RANGE_PATTERN_EXP, candidate_text):
        lo, hi = _tok_to_val(m.group(1)), _tok_to_val(m.group(2))
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return f"Experience range '{m.group(0)}' (lo={lo}, hi={hi}) requires 3+ years", RANGE_PATTERN_EXP

    candidate_noranges = re.sub(RANGE_PATTERN_EXP, ' ', candidate_text)

    for m in re.finditer(PLUS_PATTERN_EXP, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return f"Plus experience requirement '{m.group(0)}' requires 3+ years", PLUS_PATTERN_EXP

    for m in re.finditer(MIN_PATTERN_EXP, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return f"Minimum experience requirement '{m.group(0)}' requires 3+ years", MIN_PATTERN_EXP

    for m in re.finditer(SINGLE_EXP_PATTERN, candidate_noranges):
        num = int(m.group(1))
        if re.search(r'degree|bachelor|diploma|bond|agreement|contract|commitment|lock-in|warranty|course', candidate_text[max(0, m.start()-20):min(len(candidate_text), m.end()+20)]):
            continue
        if 3 <= num <= 25:
            return f"Single experience requirement '{m.group(0)}' requires 3+ years", SINGLE_EXP_PATTERN

    for m in re.finditer(YRS_PATTERN_EXP, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return f"Experience shorthand '{m.group(0)}' requires 3+ years", YRS_PATTERN_EXP

    for m in re.finditer(WORD_PATTERN_EXP, candidate_noranges):
        matched_word = m.group(1)
        if WORDS_TO_NUM_TITLE.get(matched_word, 0) >= 3:
            preceding = candidate_noranges[:m.start()]
            if re.search(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014|till|and|or)\s*$', preceding):
                continue
            return f"Word-based experience requirement '{m.group(0)}' requires 3+ years", WORD_PATTERN_EXP

    return "High experience required (3+ years)", None


def explain_out_of_scope(title: str, desc: str) -> Tuple[str, str]:
    """Identify matching out-of-scope technology tokens in title or description."""
    m_title = OUT_OF_SCOPE_STACK_PATTERN.search(title) if title else None
    if m_title:
        token = m_title.group(0)
        return f"Out-of-scope stack '{token}' detected in title: '{title}'", OUT_OF_SCOPE_STACK_PATTERN.pattern

    m_desc = OUT_OF_SCOPE_STACK_PATTERN.search(desc) if desc else None
    if m_desc:
        token = m_desc.group(0)
        return f"Out-of-scope stack '{token}' detected in description", OUT_OF_SCOPE_STACK_PATTERN.pattern

    return "Out-of-scope stack detected", OUT_OF_SCOPE_STACK_PATTERN.pattern


def explain_irrelevant_jd(desc: str, title: str) -> Tuple[str, str]:
    """Identify missing anchors or tools in irrelevant job descriptions."""
    desc_lower = desc.lower() if desc else ""
    matched_anchors = [kw for kw in DOMAIN_ANCHORS if kw in desc_lower]
    matched_tools = [kw for kw in TECH_TOOLS if kw in desc_lower]

    if not matched_anchors and not matched_tools:
        return "Missing both domain anchor and tech tool keywords in description", "missing_anchor_and_tool"
    elif not matched_anchors:
        return f"Missing domain anchor keyword in description (found tools: {matched_tools[:5]})", "missing_domain_anchor"
    elif not matched_tools:
        return f"Missing tech tool keyword in description (found anchors: {matched_anchors[:5]})", "missing_tech_tool"

    return "Relevance threshold not satisfied", "relevance_check_failed"


def run_filter_replay():
    print("=" * 70)
    print("  TWO-LAYER FILTER REPLAY HARNESS")
    print(f"  Dataset: {DATASET_PATH}")
    print(f"  Pinned Scrape Time: {PINNED_SCRAPE_TIME.isoformat()}")
    print(f"  Cutoff Time: {CUTOFF_TIME.isoformat()} ({HOURS_OLD}h freshness)")
    print("=" * 70)

    # 1. Load dataset
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        raw_jobs = [json.loads(line) for line in f]

    total_raw = len(raw_jobs)
    print(f"[Dataset] Loaded {total_raw} jobs from master raw dataset")
    assert total_raw == 1137, f"Expected 1137 jobs, found {total_raw}"

    # Build location matcher
    loc_pattern = build_location_regex(TARGET_LOCATIONS)
    loc_re = re.compile(loc_pattern, re.IGNORECASE)

    # Containers for Layer 1
    l1_fail_records: List[Dict[str, Any]] = []
    l1_pass_survivors: List[Dict[str, Any]] = []

    # Sequential execution of Layer 1 passes
    # Pass 1: Empty description
    pass_p1: List[Dict[str, Any]] = []
    for r in raw_jobs:
        desc = r.get("description")
        if not desc or not isinstance(desc, str) or not desc.strip():
            l1_fail_records.append({
                "job_index": r["job_index"],
                "id": r["id"],
                "title": r.get("title", ""),
                "company": r.get("company", ""),
                "filter_layer": "pandas",
                "rejection_reason": "empty_description",
                "rejection_detail": "Job description is empty or whitespace-only",
                "matched_pattern": None
            })
        else:
            pass_p1.append(r)

    # Pass 2: Freshness check (>72h cutoff relative to pinned scrape time)
    pass_p2: List[Dict[str, Any]] = []
    for r in pass_p1:
        dp = r.get("date_posted")
        clean_dp = None if dp == "nan" else dp
        dt = pd.to_datetime(clean_dp, errors="coerce", utc=True)
        if pd.notna(dt) and dt < CUTOFF_TIME:
            l1_fail_records.append({
                "job_index": r["job_index"],
                "id": r["id"],
                "title": r.get("title", ""),
                "company": r.get("company", ""),
                "filter_layer": "pandas",
                "rejection_reason": "stale",
                "rejection_detail": f"Date posted '{dp}' is older than {HOURS_OLD}h cutoff ({CUTOFF_TIME.isoformat()})",
                "matched_pattern": f"date_posted < {CUTOFF_TIME.isoformat()}"
            })
        else:
            pass_p2.append(r)

    # Pass 3: Location check (target cities with aliases OR remote)
    pass_p3: List[Dict[str, Any]] = []
    for r in pass_p2:
        loc = str(r.get("location", ""))
        is_remote = bool(r.get("is_remote", False))
        if loc_re.search(loc) or is_remote:
            pass_p3.append(r)
        else:
            l1_fail_records.append({
                "job_index": r["job_index"],
                "id": r["id"],
                "title": r.get("title", ""),
                "company": r.get("company", ""),
                "filter_layer": "pandas",
                "rejection_reason": "location_mismatch",
                "rejection_detail": f"Location '{loc}' does not match target cities (Pune, Mumbai, Bangalore) or remote",
                "matched_pattern": loc_pattern
            })

    # Pass 4: Senior title check
    pass_p4: List[Dict[str, Any]] = []
    for r in pass_p3:
        t = str(r.get("title", ""))
        if matches_senior_title(t):
            detail, pat = explain_senior_title(t)
            l1_fail_records.append({
                "job_index": r["job_index"],
                "id": r["id"],
                "title": r.get("title", ""),
                "company": r.get("company", ""),
                "filter_layer": "pandas",
                "rejection_reason": "senior_title",
                "rejection_detail": detail,
                "matched_pattern": pat
            })
        else:
            pass_p4.append(r)

    # Pass 5: Experience 3+ check
    pass_p5: List[Dict[str, Any]] = []
    for r in pass_p4:
        d = str(r.get("description", ""))
        if requires_3_plus_years(d):
            detail, pat = explain_experience_3_plus(d)
            l1_fail_records.append({
                "job_index": r["job_index"],
                "id": r["id"],
                "title": r.get("title", ""),
                "company": r.get("company", ""),
                "filter_layer": "pandas",
                "rejection_reason": "experience_3_plus",
                "rejection_detail": detail,
                "matched_pattern": pat
            })
        else:
            pass_p5.append(r)

    # Pass 6a: Deduplication by normalized URL
    pass_p6a: List[Dict[str, Any]] = []
    seen_urls = set()
    for r in pass_p5:
        raw_url = r.get("url", "")
        norm_url = normalize_url(raw_url)
        r["_normalized_url"] = norm_url
        if norm_url and norm_url.strip():
            if norm_url in seen_urls:
                l1_fail_records.append({
                    "job_index": r["job_index"],
                    "id": r["id"],
                    "title": r.get("title", ""),
                    "company": r.get("company", ""),
                    "filter_layer": "pandas",
                    "rejection_reason": "duplicate_url",
                    "rejection_detail": f"Duplicate of earlier job with normalized URL: {norm_url}",
                    "matched_pattern": f"normalized_url: {norm_url}"
                })
                continue
            seen_urls.add(norm_url)
        pass_p6a.append(r)

    # Pass 6b: Deduplication by (clean_title, company) for known companies
    pass_p6b: List[Dict[str, Any]] = []
    unknown_companies = {'', 'unknown', 'none', 'nan', 'null', 'n/a'}
    seen_company_title = set()
    for r in pass_p6a:
        comp_str = str(r.get("company", "")).strip().lower()
        title_str = str(r.get("title", "")).strip().lower()
        if comp_str and comp_str not in unknown_companies:
            pair = (title_str, comp_str)
            if pair in seen_company_title:
                l1_fail_records.append({
                    "job_index": r["job_index"],
                    "id": r["id"],
                    "title": r.get("title", ""),
                    "company": r.get("company", ""),
                    "filter_layer": "pandas",
                    "rejection_reason": "duplicate_company_title",
                    "rejection_detail": f"Duplicate of earlier job with title '{title_str}' and company '{comp_str}'",
                    "matched_pattern": f"title: {title_str} | company: {comp_str}"
                })
                continue
            seen_company_title.add(pair)
        pass_p6b.append(r)

    # Build Layer 1 Pass records
    for r in pass_p6b:
        dp = r.get("date_posted")
        l1_pass_survivors.append({
            "job_index": r["job_index"],
            "id": r["id"],
            "title": r["title"],
            "company": r["company"],
            "location": r["location"],
            "description": r["description"],
            "url": r["url"],
            "source": r["source"],
            "job_type": r.get("job_type", "fulltime"),
            "date_posted": None if dp == "nan" else dp,
            "is_remote": bool(r.get("is_remote", False)),
            "scraped_at": r["scraped_at"],
            "filter_layer": "pandas",
            "status": "PASS"
        })

    # Sort outputs by job_index for deterministic joining and inspection
    l1_pass_survivors.sort(key=lambda x: x["job_index"])
    l1_fail_records.sort(key=lambda x: x["job_index"])

    print(f"[Layer 1] Pass survivors: {len(l1_pass_survivors)}")
    print(f"[Layer 1] Dropped records: {len(l1_fail_records)}")
    assert len(l1_pass_survivors) + len(l1_fail_records) == total_raw, (
        f"Layer 1 accounting mismatch: {len(l1_pass_survivors)} + {len(l1_fail_records)} != {total_raw}"
    )

    # -------------------------------------------------------------
    # Layer 2: Scorer Regex Filter (executed on Layer 1 survivors)
    # -------------------------------------------------------------
    l2_pass_records: List[Dict[str, Any]] = []
    l2_fail_records: List[Dict[str, Any]] = []

    for job in l1_pass_survivors:
        title = job.get("title", "")
        desc = job.get("description", "")

        # 1. Senior title check
        if matches_senior_title(title):
            detail, pat = explain_senior_title(title)
            l2_fail_records.append({
                "job_index": job["job_index"],
                "id": job["id"],
                "title": title,
                "company": job["company"],
                "filter_layer": "regex",
                "rejection_reason": "senior_title",
                "rejection_detail": detail,
                "matched_pattern": pat
            })
            continue

        # 2. Out of scope stack check
        if matches_out_of_scope_role(title, desc):
            detail, pat = explain_out_of_scope(title, desc)
            l2_fail_records.append({
                "job_index": job["job_index"],
                "id": job["id"],
                "title": title,
                "company": job["company"],
                "filter_layer": "regex",
                "rejection_reason": "out_of_scope_stack",
                "rejection_detail": detail,
                "matched_pattern": pat
            })
            continue

        # 3. Experience 3+ check
        if requires_3_plus_years(desc):
            detail, pat = explain_experience_3_plus(desc)
            l2_fail_records.append({
                "job_index": job["job_index"],
                "id": job["id"],
                "title": title,
                "company": job["company"],
                "filter_layer": "regex",
                "rejection_reason": "experience_3_plus",
                "rejection_detail": detail,
                "matched_pattern": pat
            })
            continue

        # 4. Domain relevance check
        if not is_relevant_jd(desc, title):
            detail, pat = explain_irrelevant_jd(desc, title)
            l2_fail_records.append({
                "job_index": job["job_index"],
                "id": job["id"],
                "title": title,
                "company": job["company"],
                "filter_layer": "regex",
                "rejection_reason": "irrelevant_jd",
                "rejection_detail": detail,
                "matched_pattern": pat
            })
            continue

        # Survived Layer 2
        desc_lower = desc.lower()
        matched_anchors = [kw for kw in DOMAIN_ANCHORS if kw in desc_lower]
        matched_tools = [kw for kw in TECH_TOOLS if kw in desc_lower]

        l2_pass_records.append({
            "job_index": job["job_index"],
            "id": job["id"],
            "title": title,
            "company": job["company"],
            "location": job["location"],
            "url": job["url"],
            "filter_layer": "regex",
            "status": "PASS",
            "matched_anchors": matched_anchors,
            "matched_tools": matched_tools
        })

    # Sort outputs by job_index
    l2_pass_records.sort(key=lambda x: x["job_index"])
    l2_fail_records.sort(key=lambda x: x["job_index"])

    print(f"[Layer 2] Pass survivors: {len(l2_pass_records)}")
    print(f"[Layer 2] Dropped records: {len(l2_fail_records)}")
    assert len(l2_pass_records) + len(l2_fail_records) == len(l1_pass_survivors), (
        f"Layer 2 accounting mismatch: {len(l2_pass_records)} + {len(l2_fail_records)} != {len(l1_pass_survivors)}"
    )

    # -------------------------------------------------------------
    # Write JSONL Output Files
    # -------------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(L1_PASS_PATH, "w", encoding="utf-8") as f:
        for rec in l1_pass_survivors:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(L1_FAIL_PATH, "w", encoding="utf-8") as f:
        for rec in l1_fail_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(L2_PASS_PATH, "w", encoding="utf-8") as f:
        for rec in l2_pass_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(L2_FAIL_PATH, "w", encoding="utf-8") as f:
        for rec in l2_fail_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("[Artifacts] Successfully wrote all 4 JSONL filter results files.")

    # -------------------------------------------------------------
    # Comprehensive Accounting & Schema Integrity Verification
    # -------------------------------------------------------------
    l1_pass_indices = {r["job_index"] for r in l1_pass_survivors}
    l1_fail_indices = {r["job_index"] for r in l1_fail_records}
    all_raw_indices = set(range(total_raw))

    assert l1_pass_indices | l1_fail_indices == all_raw_indices, "Layer 1 index coverage is not complete"
    assert len(l1_pass_indices & l1_fail_indices) == 0, "Layer 1 pass/fail index collision detected"

    l2_pass_indices = {r["job_index"] for r in l2_pass_records}
    l2_fail_indices = {r["job_index"] for r in l2_fail_records}

    assert l2_pass_indices | l2_fail_indices == l1_pass_indices, "Layer 2 index coverage is not complete across L1 survivors"
    assert len(l2_pass_indices & l2_fail_indices) == 0, "Layer 2 pass/fail index collision detected"

    # Schema field presence verification
    l1_pass_req_keys = {
        "job_index", "id", "title", "company", "location", "description",
        "url", "source", "job_type", "date_posted", "is_remote", "scraped_at",
        "filter_layer", "status"
    }
    for rec in l1_pass_survivors:
        assert set(rec.keys()) == l1_pass_req_keys, f"Invalid keys in L1 pass: {set(rec.keys())}"

    l1_fail_req_keys = {
        "job_index", "id", "title", "company", "filter_layer",
        "rejection_reason", "rejection_detail", "matched_pattern"
    }
    for rec in l1_fail_records:
        assert set(rec.keys()) == l1_fail_req_keys, f"Invalid keys in L1 fail: {set(rec.keys())}"
        assert rec["rejection_reason"] in {
            "empty_description", "stale", "location_mismatch",
            "senior_title", "experience_3_plus", "duplicate_url",
            "duplicate_company_title"
        }

    l2_pass_req_keys = {
        "job_index", "id", "title", "company", "location", "url",
        "filter_layer", "status", "matched_anchors", "matched_tools"
    }
    for rec in l2_pass_records:
        assert set(rec.keys()) == l2_pass_req_keys, f"Invalid keys in L2 pass: {set(rec.keys())}"

    l2_fail_req_keys = {
        "job_index", "id", "title", "company", "filter_layer",
        "rejection_reason", "rejection_detail", "matched_pattern"
    }
    for rec in l2_fail_records:
        assert set(rec.keys()) == l2_fail_req_keys, f"Invalid keys in L2 fail: {set(rec.keys())}"
        assert rec["rejection_reason"] in {
            "senior_title", "out_of_scope_stack", "experience_3_plus", "irrelevant_jd"
        }

    print("=" * 70)
    print("  VERIFICATION COMPLETE: 100% ACCOUNTING IDENTITY CONFIRMED")
    print(f"  Total Raw:       {total_raw}")
    print(f"  Layer 1 Pass:    {len(l1_pass_survivors)}")
    print(f"  Layer 1 Fail:    {len(l1_fail_records)}  (Pass + Fail = {len(l1_pass_survivors) + len(l1_fail_records)})")
    print(f"  Layer 2 Pass:    {len(l2_pass_records)}")
    print(f"  Layer 2 Fail:    {len(l2_fail_records)}   (Pass + Fail = {len(l2_pass_records) + len(l2_fail_records)})")
    print("=" * 70)


if __name__ == "__main__":
    run_filter_replay()
