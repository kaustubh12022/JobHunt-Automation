import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\kalek\Desktop\Projects\Job_Hunt")
DATASET_PATH = PROJECT_ROOT / "regex_audit" / "master_raw_dataset_2026-09-29.jsonl"
RESULTS_DIR = PROJECT_ROOT / "regex_audit" / "filter_results"

L1_PASS_PATH = RESULTS_DIR / "layer1_pandas_pass.jsonl"
L1_FAIL_PATH = RESULTS_DIR / "layer1_pandas_fail.jsonl"
L2_PASS_PATH = RESULTS_DIR / "layer2_regex_pass.jsonl"
L2_FAIL_PATH = RESULTS_DIR / "layer2_regex_fail.jsonl"

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                records.append(json.loads(line_str))
    return records

def run_edge_case_tests():
    print("=" * 80)
    print("  CHALLENGER REPLAY 2: EDGE CASE & BOUNDARY STRESS TESTS")
    print("=" * 80)

    # Load all files
    raw_jobs = load_jsonl(DATASET_PATH)
    l1_pass = load_jsonl(L1_PASS_PATH)
    l1_fail = load_jsonl(L1_FAIL_PATH)
    l2_pass = load_jsonl(L2_PASS_PATH)
    l2_fail = load_jsonl(L2_FAIL_PATH)

    print(f"Loaded records:")
    print(f"  Raw:     {len(raw_jobs)}")
    print(f"  L1 Pass: {len(l1_pass)}")
    print(f"  L1 Fail: {len(l1_fail)}")
    print(f"  L2 Pass: {len(l2_pass)}")
    print(f"  L2 Fail: {len(l2_fail)}")

    raw_by_idx = {r["job_index"]: r for r in raw_jobs}
    l1_pass_by_idx = {r["job_index"]: r for r in l1_pass}
    l1_fail_by_idx = {r["job_index"]: r for r in l1_fail}
    l2_pass_by_idx = {r["job_index"]: r for r in l2_pass}
    l2_fail_by_idx = {r["job_index"]: r for r in l2_fail}

    # =========================================================================
    # TEST 1: job_index 536 and Remote Location Bypass
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 1: JOB 536 AND REMOTE LOCATION BYPASS")
    print("-" * 80)

    job536 = raw_by_idx[536]
    print(f"Job 536 Raw Data:")
    print(f"  Title:       {job536.get('title')}")
    print(f"  Company:     {job536.get('company')}")
    print(f"  Location:    {job536.get('location')}")
    print(f"  is_remote:   {job536.get('is_remote')} (type: {type(job536.get('is_remote'))})")
    print(f"  date_posted: {job536.get('date_posted')}")

    # Check where job 536 landed
    assert 536 not in l1_pass_by_idx, "Job 536 should not be in L1 pass"
    assert 536 in l1_fail_by_idx, "Job 536 must be in L1 fail"

    rec536 = l1_fail_by_idx[536]
    print(f"\nJob 536 L1 Fail Record:")
    print(f"  Filter Layer:     {rec536.get('filter_layer')}")
    print(f"  Rejection Reason: {rec536.get('rejection_reason')}")
    print(f"  Rejection Detail: {rec536.get('rejection_detail')}")

    # CRITICAL CHECK: Did job 536 bypass location check?
    # If location check had failed it, rejection_reason would be 'location_mismatch'
    # But because is_remote=True, it bypassed Pass 3 (location) and Pass 4 (senior_title)
    # and was rejected at Pass 5 (experience_3_plus) because JD requires 8-12 years.
    assert rec536.get("rejection_reason") != "location_mismatch", (
        f"FAILURE: Job 536 was rejected for location_mismatch! Expected remote bypass."
    )
    assert rec536.get("rejection_reason") == "experience_3_plus", (
        f"FAILURE: Job 536 expected rejection for experience_3_plus, got {rec536.get('rejection_reason')}"
    )
    print("  => CONFIRMED: Job 536 successfully bypassed location filter due to is_remote=True!")
    print("  => CONFIRMED: Job 536 was legitimately rejected at Pass 5 for experience_3_plus (8-12 years).")

    # Survey all jobs with is_remote=True
    remote_jobs = [j for j in raw_jobs if bool(j.get("is_remote", False))]
    print(f"\nTotal raw jobs with is_remote=True: {len(remote_jobs)}")

    # Check how many remote jobs had non-target locations
    target_locations = ["pune", "mumbai", "bangalore"]
    loc_pattern = r'\b(?:' + '|'.join(target_locations) + r')\b'
    loc_re = re.compile(loc_pattern, re.IGNORECASE)

    remote_non_target_loc = [
        j for j in remote_jobs
        if not loc_re.search(str(j.get("location", "")))
    ]
    print(f"Remote jobs with non-target/unknown locations: {len(remote_non_target_loc)}")

    # Verify that NONE of these remote jobs failed with location_mismatch
    for r_job in remote_non_target_loc:
        idx = r_job["job_index"]
        if idx in l1_fail_by_idx:
            fail_rec = l1_fail_by_idx[idx]
            assert fail_rec["rejection_reason"] != "location_mismatch", (
                f"FAILURE: Remote job {idx} with location '{r_job.get('location')}' "
                f"was rejected for location_mismatch! Remote bypass failed."
            )
    print("  => CONFIRMED: 100% of remote jobs with non-target locations bypassed location_mismatch!")

    # Check if any remote jobs survived into L1 pass
    remote_in_l1_pass = [j for j in l1_pass if j.get("is_remote") is True]
    print(f"Remote jobs surviving into L1 Pass: {len(remote_in_l1_pass)}")
    for j in remote_in_l1_pass[:5]:
        print(f"  - job_index={j['job_index']}: {j['title']} at {j['company']} (loc: {j['location']})")

    # =========================================================================
    # TEST 2: "nan" date_posted Handling & Freshness Check Integrity
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 2: 'nan' date_posted HANDLING & FRESHNESS INTEGRITY")
    print("-" * 80)

    # Inspect all date_posted values across raw dataset
    raw_date_types = {}
    nan_date_jobs = []
    none_date_jobs = []
    valid_date_jobs = []

    for j in raw_jobs:
        dp = j.get("date_posted")
        if dp == "nan":
            nan_date_jobs.append(j)
        elif dp is None:
            none_date_jobs.append(j)
        else:
            valid_date_jobs.append(j)

    print(f"Raw dataset date_posted distribution:")
    print(f"  Exact string 'nan': {len(nan_date_jobs)}")
    print(f"  None / null:        {len(none_date_jobs)}")
    print(f"  Valid / other date: {len(valid_date_jobs)}")

    # Check if ANY "nan" or None date job was rejected as "stale"
    stale_rejections = [r for r in l1_fail if r.get("rejection_reason") == "stale"]
    print(f"Total L1 stale rejections: {len(stale_rejections)}")

    for r in stale_rejections:
        idx = r["job_index"]
        raw_dp = raw_by_idx[idx].get("date_posted")
        assert raw_dp != "nan" and raw_dp is not None, (
            f"FAILURE: Job {idx} with date_posted='{raw_dp}' was rejected as stale!"
        )
    print("  => CONFIRMED: Zero jobs with 'nan' or None date_posted were rejected as stale!")

    # Check how "nan" date jobs were serialized into L1 pass
    nan_in_l1_pass = [j for j in l1_pass if raw_by_idx[j["job_index"]].get("date_posted") == "nan"]
    print(f"Jobs with raw date_posted='nan' that survived into L1 Pass: {len(nan_in_l1_pass)}")
    for j in nan_in_l1_pass:
        # In run_filter_replay.py: "date_posted": None if dp == "nan" else dp
        assert j["date_posted"] is None, (
            f"FAILURE: Job {j['job_index']} date_posted in L1 pass was not converted to None! Value: {j['date_posted']}"
        )
    print("  => CONFIRMED: In L1 pass, all raw 'nan' dates were cleanly normalized to None (null in JSON).")

    # Check all stale rejections against pinned cutoff time
    PINNED_SCRAPE_TIME = pd.Timestamp("2026-09-29T14:05:55Z")
    CUTOFF_TIME = PINNED_SCRAPE_TIME - pd.Timedelta(hours=72)
    print(f"Verifying all {len(stale_rejections)} stale jobs against cutoff ({CUTOFF_TIME.isoformat()}):")
    for r in stale_rejections:
        idx = r["job_index"]
        raw_dp = raw_by_idx[idx].get("date_posted")
        dt = pd.to_datetime(raw_dp, errors="coerce", utc=True)
        assert pd.notna(dt), f"Job {idx} marked stale but date could not be parsed: {raw_dp}"
        assert dt < CUTOFF_TIME, f"Job {idx} marked stale but {dt} >= cutoff {CUTOFF_TIME}"
    print("  => CONFIRMED: 100% of stale rejections strictly satisfy dt < CUTOFF_TIME.")

    # =========================================================================
    # TEST 3: Unicode & Character Preservation (Bullets, Dashes, Quotes, Symbols)
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 3: UNICODE PRESERVATION (BULLETS, DASHES, QUOTES, SYMBOLS)")
    print("-" * 80)

    # Search for bullet characters across raw jobs
    bullet_chars = {
        "\u25cf": "Black Circle (\\u25cf ●)",
        "\u2022": "Bullet (\\u2022 •)",
        "\u25aa": "Black Small Square (\\u25aa ▪)",
        "\u25b6": "Black Right-Pointing Triangle (\\u25b6 ▶)",
        "\u00b7": "Middle Dot (\\u00b7 ·)",
        "\u2013": "En Dash (\\u2013 –)",
        "\u2014": "Em Dash (\\u2014 —)",
        "\u2018": "Left Single Quote (\\u2018 ‘)",
        "\u2019": "Right Single Quote (\\u2019 ’)",
        "\u201c": "Left Double Quote (\\u201c “)",
        "\u201d": "Right Double Quote (\\u201d ”)",
        "\u2265": "Greater-than or equal to (\\u2265 ≥)",
        "\u00a0": "No-break space (\\u00a0)",
    }

    bullet_counts_raw = {k: 0 for k in bullet_chars}
    jobs_with_char = {k: [] for k in bullet_chars}

    for j in raw_jobs:
        combined_text = (j.get("title", "") or "") + " " + (j.get("description", "") or "")
        for ch in bullet_chars:
            if ch in combined_text:
                bullet_counts_raw[ch] += combined_text.count(ch)
                jobs_with_char[ch].append(j["job_index"])

    print("Unicode characters found in master raw dataset:")
    for ch, name in bullet_chars.items():
        if bullet_counts_raw[ch] > 0:
            print(f"  {name:42s}: {bullet_counts_raw[ch]:5d} occurrences across {len(jobs_with_char[ch]):3d} jobs")

    # Specifically check \u25cf
    u25cf_jobs = jobs_with_char["\u25cf"]
    print(f"\nJobs with \\u25cf (●): {len(u25cf_jobs)} jobs: {u25cf_jobs}")

    # For each job in L1 pass, verify character-for-character fidelity of description and title
    print("\nVerifying 100% exact text fidelity between raw and L1 pass records:")
    mismatches = []
    unicode_preservation_checks = 0

    for l1_rec in l1_pass:
        idx = l1_rec["job_index"]
        raw_rec = raw_by_idx[idx]

        # Check title
        if l1_rec["title"] != raw_rec["title"]:
            mismatches.append((idx, "title", len(raw_rec["title"]), len(l1_rec["title"])))

        # Check description
        if l1_rec["description"] != raw_rec["description"]:
            mismatches.append((idx, "description", len(raw_rec["description"]), len(l1_rec["description"])))

        # Check company
        if l1_rec["company"] != raw_rec["company"]:
            mismatches.append((idx, "company", len(raw_rec["company"]), len(l1_rec["company"])))

        # Check location
        if l1_rec["location"] != raw_rec["location"]:
            mismatches.append((idx, "location", len(raw_rec["location"]), len(l1_rec["location"])))

        # Check url
        if l1_rec["url"] != raw_rec["url"]:
            mismatches.append((idx, "url", len(raw_rec["url"]), len(l1_rec["url"])))

        # Check unicode preservation in description
        for ch in bullet_chars:
            if ch in raw_rec["description"]:
                assert ch in l1_rec["description"], (
                    f"FAILURE: Unicode char {bullet_chars[ch]} lost in L1 pass job {idx}!"
                )
                assert raw_rec["description"].count(ch) == l1_rec["description"].count(ch), (
                    f"FAILURE: Unicode char {bullet_chars[ch]} count mismatch in job {idx}!"
                )
                unicode_preservation_checks += 1

    assert len(mismatches) == 0, f"Text mismatches between raw and L1 pass: {mismatches}"
    print(f"  => PASS: Checked all {len(l1_pass)} L1 pass jobs — 0 mismatches!")
    print(f"  => PASS: Verified {unicode_preservation_checks} Unicode character occurrences in L1 pass.")

    # Check \u25cf in particular jobs across all files
    for idx in u25cf_jobs:
        raw_desc = raw_by_idx[idx]["description"]
        raw_count = raw_desc.count("\u25cf")
        if idx in l1_pass_by_idx:
            l1_desc = l1_pass_by_idx[idx]["description"]
            assert "\u25cf" in l1_desc, f"Job {idx} lost \\u25cf in L1 pass!"
            assert l1_desc.count("\u25cf") == raw_count
            print(f"  - Job {idx} in L1 Pass: \\u25cf preserved ({raw_count} times).")
        else:
            # It's in L1 fail
            l1_f = l1_fail_by_idx[idx]
            print(f"  - Job {idx} in L1 Fail ({l1_f['rejection_reason']}): raw has \\u25cf ({raw_count} times).")

    # =========================================================================
    # TEST 4: Zero Field Truncation & Schema Completeness
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 4: ZERO FIELD TRUNCATION & SCHEMA COMPLETENESS")
    print("-" * 80)

    # 1. Check L1 Pass Schema and length preservation
    l1_pass_keys = {
        "job_index", "id", "title", "company", "location", "description",
        "url", "source", "job_type", "date_posted", "is_remote", "scraped_at",
        "filter_layer", "status"
    }
    for r in l1_pass:
        idx = r["job_index"]
        raw_r = raw_by_idx[idx]
        assert set(r.keys()) == l1_pass_keys, f"L1 pass keys mismatch at job {idx}"

        # Exact length match
        assert len(r["description"]) == len(raw_r["description"]), (
            f"Description truncation in job {idx}! Raw len: {len(raw_r['description'])}, L1 len: {len(r['description'])}"
        )
        assert len(r["title"]) == len(raw_r["title"]), f"Title truncation in job {idx}"
        assert len(r["url"]) == len(raw_r["url"]), f"URL truncation in job {idx}"

    print(f"  => L1 Pass ({len(l1_pass)} records): Exact length match on all string fields, 0 truncations.")

    # 2. Check L1 Fail Schema
    l1_fail_keys = {
        "job_index", "id", "title", "company", "filter_layer",
        "rejection_reason", "rejection_detail", "matched_pattern"
    }
    for r in l1_fail:
        idx = r["job_index"]
        raw_r = raw_by_idx[idx]
        assert set(r.keys()) == l1_fail_keys, f"L1 fail keys mismatch at job {idx}"
        assert len(r["title"]) == len(raw_r["title"]), f"Title truncation in L1 fail job {idx}"
        assert r["company"] == raw_r["company"], f"Company mismatch in L1 fail job {idx}"
        assert r["rejection_reason"] in {
            "empty_description", "stale", "location_mismatch",
            "senior_title", "experience_3_plus", "duplicate_url",
            "duplicate_company_title"
        }, f"Invalid rejection_reason '{r['rejection_reason']}' in job {idx}"
        assert len(r["rejection_detail"]) > 0, f"Empty rejection_detail in job {idx}"

    print(f"  => L1 Fail ({len(l1_fail)} records): Schema complete, reasons valid, 0 truncations.")

    # 3. Check L2 Pass Schema
    l2_pass_keys = {
        "job_index", "id", "title", "company", "location", "url",
        "filter_layer", "status", "matched_anchors", "matched_tools"
    }
    for r in l2_pass:
        idx = r["job_index"]
        raw_r = raw_by_idx[idx]
        assert set(r.keys()) == l2_pass_keys, f"L2 pass keys mismatch at job {idx}"
        assert r["status"] == "PASS"
        assert r["filter_layer"] == "regex"
        assert isinstance(r["matched_anchors"], list) and len(r["matched_anchors"]) > 0, (
            f"Job {idx} in L2 pass has empty matched_anchors!"
        )
        assert isinstance(r["matched_tools"], list) and len(r["matched_tools"]) > 0, (
            f"Job {idx} in L2 pass has empty matched_tools!"
        )
        assert len(r["title"]) == len(raw_r["title"]), f"Title truncation in L2 pass job {idx}"
        assert len(r["url"]) == len(raw_r["url"]), f"URL truncation in L2 pass job {idx}"

    print(f"  => L2 Pass ({len(l2_pass)} records): Schema complete, matched_anchors and matched_tools non-empty, 0 truncations.")

    # 4. Check L2 Fail Schema
    l2_fail_keys = {
        "job_index", "id", "title", "company", "filter_layer",
        "rejection_reason", "rejection_detail", "matched_pattern"
    }
    for r in l2_fail:
        idx = r["job_index"]
        raw_r = raw_by_idx[idx]
        assert set(r.keys()) == l2_fail_keys, f"L2 fail keys mismatch at job {idx}"
        assert r["filter_layer"] == "regex"
        assert r["rejection_reason"] in {
            "senior_title", "out_of_scope_stack", "experience_3_plus", "irrelevant_jd"
        }, f"Invalid rejection_reason '{r['rejection_reason']}' in L2 fail job {idx}"
        assert len(r["title"]) == len(raw_r["title"]), f"Title truncation in L2 fail job {idx}"
        assert len(r["rejection_detail"]) > 0, f"Empty rejection_detail in L2 fail job {idx}"

    print(f"  => L2 Fail ({len(l2_fail)} records): Schema complete, rejection_details non-empty, 0 truncations.")

    # =========================================================================
    # TEST 5: Comprehensive Boundary Survey
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 5: COMPREHENSIVE BOUNDARY & EDGE-CASE SURVEY")
    print("-" * 80)

    # Empty descriptions
    empty_desc_jobs = [j for j in raw_jobs if not j.get("description") or not j["description"].strip()]
    print(f"Jobs with empty/whitespace description: {len(empty_desc_jobs)}")
    for j in empty_desc_jobs:
        idx = j["job_index"]
        assert idx in l1_fail_by_idx
        assert l1_fail_by_idx[idx]["rejection_reason"] == "empty_description"
    print("  => CONFIRMED: 100% of empty description jobs rejected at Pass 1 with empty_description.")

    # Deduplication checks
    dup_url_rejections = [r for r in l1_fail if r.get("rejection_reason") == "duplicate_url"]
    dup_comp_title_rejections = [r for r in l1_fail if r.get("rejection_reason") == "duplicate_company_title"]
    print(f"Duplicate URL rejections: {len(dup_url_rejections)}")
    print(f"Duplicate (company, title) rejections: {len(dup_comp_title_rejections)}")

    # Check that in L1 pass there are NO duplicate URLs
    l1_pass_urls = [r["url"] for r in l1_pass if r.get("url")]
    assert len(l1_pass_urls) == len(set(l1_pass_urls)), "Duplicate URLs found in L1 Pass!"
    print("  => CONFIRMED: 0 duplicate URLs exist in L1 Pass.")

    # Check accounting sums
    assert len(l1_pass) + len(l1_fail) == 1137
    assert len(l2_pass) + len(l2_fail) == len(l1_pass)
    print(f"  => CONFIRMED: Exact accounting identity holds: 1137 = {len(l1_pass)} (L1 Pass) + {len(l1_fail)} (L1 Fail); {len(l1_pass)} = {len(l2_pass)} (L2 Pass) + {len(l2_fail)} (L2 Fail).")

    print("\n" + "=" * 80)
    print("  ALL EMPIRICAL EDGE-CASE STRESS TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_edge_case_tests()
