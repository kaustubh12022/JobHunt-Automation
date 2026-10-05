#!/usr/bin/env python3
"""
Compile Ground Truth Dataset, False Positives, and False Negatives.

This script aggregates the evaluated job batches from evaluator_worker_1,
evaluator_worker_2, and evaluator_worker_3 along with Layer 1 and Layer 2
filter results to produce the authoritative ground truth dataset:
1. regex_audit/evaluation/ground_truth.jsonl (1,137 records, indexed 0..1136)
2. regex_audit/evaluation/false_positives.jsonl (8 flagged false positive jobs)
3. regex_audit/evaluation/false_negatives.jsonl (10 flagged false negative jobs)
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGEX_AUDIT_DIR = PROJECT_ROOT / "regex_audit"
EVALUATION_DIR = REGEX_AUDIT_DIR / "evaluation"
FILTER_RESULTS_DIR = REGEX_AUDIT_DIR / "filter_results"

RAW_DATASET_PATH = REGEX_AUDIT_DIR / "master_raw_dataset_2026-09-29.jsonl"
L1_PASS_PATH = FILTER_RESULTS_DIR / "layer1_pandas_pass.jsonl"
L1_FAIL_PATH = FILTER_RESULTS_DIR / "layer1_pandas_fail.jsonl"
L2_PASS_PATH = FILTER_RESULTS_DIR / "layer2_regex_pass.jsonl"
L2_FAIL_PATH = FILTER_RESULTS_DIR / "layer2_regex_fail.jsonl"

BATCH_EVAL_PATHS = [
    PROJECT_ROOT / ".agents" / "teamwork" / "evaluator_worker_1" / "batch_eval_1.jsonl",
    PROJECT_ROOT / ".agents" / "teamwork" / "evaluator_worker_2" / "batch_eval_2.jsonl",
    PROJECT_ROOT / ".agents" / "teamwork" / "evaluator_worker_3" / "batch_eval_3.jsonl",
]

OUTPUT_GROUND_TRUTH_PATH = EVALUATION_DIR / "ground_truth.jsonl"
OUTPUT_FALSE_POSITIVES_PATH = EVALUATION_DIR / "false_positives.jsonl"
OUTPUT_FALSE_NEGATIVES_PATH = EVALUATION_DIR / "false_negatives.jsonl"

# Filter failure / rejection metadata mapping for false positives and false negatives
FP_METADATA: Dict[int, Dict[str, str]] = {
    336: {
        "reason": "Title 'Advanced Engineer Quality' hides senior engineering tier requiring mentoring junior engineers, participating in hiring, and enterprise performance engineering exceeding entry-level profile.",
        "which_filter_failed": "matches_senior_title",
        "root_cause": "matches_senior_title lacks 'advanced' prefix in title filter and requires_3_plus_years lacks detection for mentoring/hiring requirements without explicit numeric year thresholds.",
        "specific_pattern_issue": r"\badvanced\b in job title representing senior engineering tier.",
    },
    456: {
        "reason": "Title 'Quality Engineer' hides Career Level 7 / Quality Engineering Manager leadership role coaching senior engineers and managing QE teams.",
        "which_filter_failed": "matches_senior_title",
        "root_cause": "matches_senior_title only checks job title string, failing to detect leadership/managerial seniority specified in JD body (Career Level 7, Quality Engineering Manager).",
        "specific_pattern_issue": "Missing check for senior/managerial career level in description headers ('Career Level [7-9]', 'Engineering Manager').",
    },
    510: {
        "reason": "Requires 2-5 years experience ('Required Experience: 2-5'), which exceeds candidate bracket (upper bound 5 >= 4).",
        "which_filter_failed": "requires_3_plus_years",
        "root_cause": "requires_3_plus_years regex requires number followed by 'years', missing standalone range format 'Required Experience: 2-5', and only checks lower bound >= 3.",
        "specific_pattern_issue": r"Regex lacks pattern for 'Required Experience:\s*\d+\s*-\s*\d+' and fails to check upper bound >= 4 when lower bound is 2.",
    },
    513: {
        "reason": "Requires 'At least five years of experience working with OMS or distributed commerce systems', exceeding entry-level threshold.",
        "which_filter_failed": "requires_3_plus_years",
        "root_cause": "requires_3_plus_years only matches digit-based experience numbers (\\d+), failing to match word-form numbers like 'five years'.",
        "specific_pattern_issue": "Missing word-form numerals (three, four, five, six, seven, eight, nine, ten) in experience regex.",
    },
    563: {
        "reason": "Requires 4 years experience ('Years of Experience required:\\n\\n 4'), exceeding entry-level threshold.",
        "which_filter_failed": "requires_3_plus_years",
        "root_cause": "requires_3_plus_years regex expects number followed by 'years', missing multi-line key-value format 'Years of Experience required:\\s*\\d+'.",
        "specific_pattern_issue": r"Missing regex for 'Years of Experience required:\s*\d+'.",
    },
    752: {
        "reason": "Product Definition Analyst 3 is a Level 3 Senior Business/Product Analyst role, not a software development or QA automation engineering role.",
        "which_filter_failed": "matches_senior_title / is_relevant_jd",
        "root_cause": "matches_senior_title missed digit grade tier '3' at the end of the title; is_relevant_jd falsely matched on generic tools ('python', 'sql', 'mongodb', 'test case') in a BA/PO role.",
        "specific_pattern_issue": r"Missing pattern for terminal digit seniority tiers in title ('\b[2-9]$') and insufficient domain anchoring to distinguish BA from SWE/QA.",
    },
    796: {
        "reason": "Senior management executive role at Associate Vice President level ('We're offering this role at associate vice president level'). Title contains 'AVP'.",
        "which_filter_failed": "matches_senior_title",
        "root_cause": "matches_senior_title in src/scorer.py failed to recognize executive/senior grade acronym 'AVP' (Associate Vice President) in job title.",
        "specific_pattern_issue": r"matches_senior_title lacks regex boundary match for r'\bavp\b' and 'associate vice president'",
    },
    1038: {
        "reason": "Strictly requires 'At least 3 years of experience working with React.' Exceeds entry-level 0-2 / 1-3 years experience ceiling.",
        "which_filter_failed": "requires_3_plus_years",
        "root_cause": "requires_3_plus_years incorrectly stripped qualification sentence '* At least 3 years of experience working with React' because third_party_prefixes over-eagerly matched '(?:work|working)\\s+(?:with|alongside|beside|among)', treating candidate skill experience as company/colleague description.",
        "specific_pattern_issue": r"requires_3_plus_years third_party_prefixes pattern r'(?:work|working)\s+(?:with|alongside|beside|among)' falsely stripped candidate qualification sentence containing 'working with <tech>'",
    },
}

FN_METADATA: Dict[int, Dict[str, str]] = {
    18: {
        "reason": "Valid Associate QA Automation role (Cypress, Selenium, Cucumber, API testing, MH). Rejected because requires_3_plus_years matched company growth history ('ten years' in 'Over the past ten years Davies has grown...').",
        "which_filter_rejected": "requires_3_plus_years",
        "rejection_layer": "layer1_pandas",
        "root_cause": "requires_3_plus_years matched company growth history ('Over the past ten years Davies has grown its annual revenues') as candidate experience, failing to filter boilerplate/company history.",
        "specific_pattern_issue": "Word-based experience pattern matching 'ten years' in company description paragraph ('Over the past ten years Davies has grown...').",
    },
    84: {
        "reason": "Valid Java/Spring Boot + React.js Full Stack developer role in MH. Rejected because matches_out_of_scope_role matched 'kotlin' when Kotlin was mentioned only as an alternative JVM backend language alongside Java.",
        "which_filter_rejected": "matches_out_of_scope_role",
        "rejection_layer": "layer2_regex",
        "root_cause": "Over-eager out-of-scope regex matching 'kotlin' when used as an alternative JVM backend language alongside Java/Spring Boot and React in a full-stack web developer role.",
        "specific_pattern_issue": r"\bkotlin\b in OUT_OF_SCOPE_STACK_PATTERN matching alternative JVM backend language in full-stack Java/React JD.",
    },
    119: {
        "reason": "Valid ASP.Net MVC Developer role in Worli Mumbai requiring Fresher/1-2 years experience. Rejected because requires_3_plus_years matched candidate age bracket '(27 to 40 Yrs)' as work experience.",
        "which_filter_rejected": "requires_3_plus_years",
        "rejection_layer": "layer1_pandas",
        "root_cause": "requires_3_plus_years matched candidate age bracket '(27 to 40 Yrs)' as work experience, ignoring that the actual requirement is 'Fresher/Experienced Graduates with 1 to 2 years experience'.",
        "specific_pattern_issue": r"\b(?:\d+)\s*(?:to|-)\s*(?:\d+)\s*yrs\b matching candidate age qualification instead of job experience.",
    },
    169: {
        "reason": "Valid entry-level Software Engineer - AI & Product role (1-3 yrs experience preserved, Mumbai Hybrid, React+Supabase+LLMs/RAG). Rejected because matches_senior_title matched 'lead' in career progression suffix '| Fast-Track to Tech Lead'.",
        "which_filter_rejected": "matches_senior_title",
        "rejection_layer": "layer1_pandas",
        "root_cause": "matches_senior_title matched word boundary on 'lead' in career path suffix 'Fast-Track to Tech Lead', ignoring that the actual role is 'Software Engineer - AI & Product' with 1-3 years experience.",
        "specific_pattern_issue": r"\blead\b matching career path / growth subtitle 'Fast-Track to Tech Lead' in an entry-level 1-3 years SWE role.",
    },
    220: {
        "reason": "Valid Full Stack Developer Internship in Pune Camp (React, Node, Express, Python, PostgreSQL, LLMs/RAG). Rejected because matches_out_of_scope_role matched peripheral 'flutter' listed as an optional frontend skill.",
        "which_filter_rejected": "matches_out_of_scope_role",
        "rejection_layer": "layer2_regex",
        "root_cause": "Over-eager regex search for out-of-scope technologies across the full description, rejecting a comprehensive Full Stack Developer Internship in Pune (React, Node, Express, Python, RAG) due to a peripheral mention of Flutter.",
        "specific_pattern_issue": r"\bflutter\b in OUT_OF_SCOPE_STACK_PATTERN matching peripheral mobile option in full-stack JD.",
    },
    246: {
        "reason": "Valid entry-level MERN/Full Stack Developer role in MH (React.js, Node.js, MongoDB, Next.js, Go). Rejected because is_relevant_jd reported missing domain anchor since DOMAIN_ANCHORS lacks MERN/React/Node terms.",
        "which_filter_rejected": "is_relevant_jd",
        "rejection_layer": "layer2_regex",
        "root_cause": "DOMAIN_ANCHORS lacks MERN / React / Node / Express terms, causing a valid entry-level full-stack React/Node/MongoDB developer job to be rejected as irrelevant.",
        "specific_pattern_issue": "Missing 'react', 'node', 'nodejs', 'mern' in DOMAIN_ANCHORS.",
    },
    466: {
        "reason": "Legitimate Associate QA Automation role (Cypress, Selenium, Cucumber, CI/CD) in MH, IN. Candidate experience unspecified. Rejected because requires_3_plus_years matched company growth history ('ten years').",
        "which_filter_rejected": "requires_3_plus_years",
        "rejection_layer": "layer1_pandas",
        "root_cause": "Word-based experience regex matched company revenue growth history ('Over the past ten years Davies has grown its annual revenues more than 20-fold'), not candidate experience requirement.",
        "specific_pattern_issue": "requires_3_plus_years failed to exclude company history phrases ('over the past \\w+ years', 'years Davies has grown').",
    },
    687: {
        "reason": "Legitimate entry-level ASP.NET MVC Developer role in Mumbai with 1-2 years experience / fresher internship compulsory. Rejected because requires_3_plus_years matched candidate age bracket '(27 to 40 Yrs)'.",
        "which_filter_rejected": "requires_3_plus_years",
        "rejection_layer": "layer1_pandas",
        "root_cause": "Regex interpreted candidate age range in title '(27 to 40 Yrs)' as work experience requirement, ignoring subsequent explicit requirement 'with 1 to 2 years experience'.",
        "specific_pattern_issue": "requires_3_plus_years regex incorrectly matched age specification '(27 to 40 Yrs)' in title/opening.",
    },
    722: {
        "reason": "Legitimate entry-level QA Engineer role in Bengaluru testing web apps, APIs, Postman, AI/LLMs. Rejected because matches_out_of_scope_role matched 'Salesforce' listed under Good to Have.",
        "which_filter_rejected": "matches_out_of_scope_role",
        "rejection_layer": "layer2_regex",
        "root_cause": "matches_out_of_scope_role searches entire description for \\bsalesforce\\b, falsely rejecting core QA roles where Salesforce is merely listed as good-to-have or third-party application tested.",
        "specific_pattern_issue": "matches_out_of_scope_role lacks scope limiting (should check title or primary requirement, not optional/good-to-have mentions in description).",
    },
    1027: {
        "reason": "Valid entry-level Full Stack role (.NET/React/TypeScript/AI coding) in Bengaluru with no candidate experience requirement. Rejected because requires_3_plus_years matched company history sentence ('With over 20 years of experience, DYMATRIX is...').",
        "which_filter_rejected": "requires_3_plus_years",
        "rejection_layer": "layer1_pandas",
        "root_cause": "requires_3_plus_years in Layer 1 failed to identify 'With over 20 years of experience, DYMATRIX is...' as company background text, mistakenly attributing 20 years to candidate experience.",
        "specific_pattern_issue": r"requires_3_plus_years third_party_prefixes lacks pattern for company background clause r'\bwith\s+(?:over|more\s+than)\s+\d+\s+years\s+of\s+experience\b'",
    },
}


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSONL records from file."""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line_str = line.strip()
            if line_str:
                try:
                    records.append(json.loads(line_str))
                except json.JSONDecodeError as err:
                    raise ValueError(f"Invalid JSON at {file_path}:{line_no}: {err}") from err
    return records


def write_jsonl(file_path: Path, records: List[Dict[str, Any]]) -> None:
    """Write records to JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def compile_evaluation_datasets() -> None:
    """Compile ground_truth, false_positives, and false_negatives."""
    print("=" * 80)
    print("  COMPILING GROUND TRUTH, FALSE POSITIVES, AND FALSE NEGATIVES")
    print("=" * 80)

    # 1. Load raw dataset
    print(f"Loading raw dataset from {RAW_DATASET_PATH}...")
    raw_records = load_jsonl(RAW_DATASET_PATH)
    assert len(raw_records) == 1137, f"Expected 1137 raw records, got {len(raw_records)}"
    raw_by_idx = {r["job_index"]: r for r in raw_records}
    print(f"  Loaded {len(raw_records)} raw records.")

    # 2. Load filter replay results
    print(f"Loading Layer 1 & Layer 2 filter results...")
    l1_pass = {r["job_index"]: r for r in load_jsonl(L1_PASS_PATH)}
    l1_fail = {r["job_index"]: r for r in load_jsonl(L1_FAIL_PATH)}
    l2_pass = {r["job_index"]: r for r in load_jsonl(L2_PASS_PATH)}
    l2_fail = {r["job_index"]: r for r in load_jsonl(L2_FAIL_PATH)}

    assert len(l1_pass) + len(l1_fail) == 1137, "Layer 1 accounting mismatch!"
    assert len(l2_pass) + len(l2_fail) == len(l1_pass), "Layer 2 accounting mismatch!"
    print(f"  Layer 1 Pass: {len(l1_pass)}, Fail: {len(l1_fail)}")
    print(f"  Layer 2 Pass: {len(l2_pass)}, Fail: {len(l2_fail)}")

    # 3. Load all three batch evaluations
    eval_records_by_idx: Dict[int, Dict[str, Any]] = {}
    for batch_idx, batch_path in enumerate(BATCH_EVAL_PATHS, 1):
        print(f"Loading batch evaluation {batch_idx} from {batch_path}...")
        batch_records = load_jsonl(batch_path)
        print(f"  Batch {batch_idx}: {len(batch_records)} records")
        for r in batch_records:
            idx = r["job_index"]
            assert idx not in eval_records_by_idx, f"Duplicate job_index {idx} across batches!"
            eval_records_by_idx[idx] = r

    assert len(eval_records_by_idx) == 1137, f"Expected 1137 evaluated records, got {len(eval_records_by_idx)}"

    # 4. Construct Ground Truth dataset (0..1136 sequentially)
    ground_truth_records: List[Dict[str, Any]] = []
    fp_records: List[Dict[str, Any]] = []
    fn_records: List[Dict[str, Any]] = []

    for idx in range(1137):
        assert idx in eval_records_by_idx, f"Missing job_index {idx} in evaluation batches!"
        eval_rec = eval_records_by_idx[idx]
        raw_rec = raw_by_idx[idx]

        # Verify layer pass/fail consistency
        actual_l1 = "PASS" if idx in l1_pass else "FAIL"
        actual_l2 = "PASS" if idx in l2_pass else "FAIL"
        assert eval_rec["actual_outcome_layer1"] == actual_l1, f"Mismatch in actual_outcome_layer1 at job {idx}"
        assert eval_rec["actual_outcome_layer2"] == actual_l2, f"Mismatch in actual_outcome_layer2 at job {idx}"

        expected_outcome = eval_rec["expected_outcome"]
        flag_type = eval_rec.get("flag_type")
        is_correct = (expected_outcome == actual_l2)
        assert eval_rec["is_correct"] == is_correct, f"Mismatch in is_correct at job {idx}"

        # Build GroundTruthRecord adhering strictly to schema
        gt_rec = {
            "job_index": idx,
            "id": raw_rec["id"],
            "title": raw_rec["title"],
            "company": raw_rec["company"],
            "location": raw_rec["location"],
            "expected_outcome": expected_outcome,
            "actual_outcome_layer1": actual_l1,
            "actual_outcome_layer2": actual_l2,
            "is_correct": is_correct,
            "flag_type": flag_type,
            "confidence": eval_rec.get("confidence", "high"),
            "target_domain": eval_rec.get("target_domain"),
            "notes": eval_rec.get("notes", ""),
        }
        ground_truth_records.append(gt_rec)

        # Handle False Positives
        if flag_type == "false_positive":
            assert idx in FP_METADATA, f"Unregistered FP job_index {idx}!"
            meta = FP_METADATA[idx]
            fp_rec = {
                "job_index": idx,
                "id": raw_rec["id"],
                "title": raw_rec["title"],
                "company": raw_rec["company"],
                "actual_decision": "PASS",
                "expected_decision": "FAIL",
                "issue_type": "false_positive",
                "reason": meta["reason"],
                "which_filter_failed": meta["which_filter_failed"],
                "root_cause": meta["root_cause"],
                "specific_pattern_issue": meta["specific_pattern_issue"],
            }
            fp_records.append(fp_rec)

        # Handle False Negatives
        elif flag_type == "false_negative":
            assert idx in FN_METADATA, f"Unregistered FN job_index {idx}!"
            meta = FN_METADATA[idx]
            fn_rec = {
                "job_index": idx,
                "id": raw_rec["id"],
                "title": raw_rec["title"],
                "company": raw_rec["company"],
                "actual_decision": "FAIL",
                "expected_decision": "PASS",
                "issue_type": "false_negative",
                "reason": meta["reason"],
                "which_filter_rejected": meta["which_filter_rejected"],
                "rejection_layer": meta["rejection_layer"],
                "root_cause": meta["root_cause"],
                "specific_pattern_issue": meta["specific_pattern_issue"],
            }
            fn_records.append(fn_rec)

    # 5. Verify counts
    assert len(ground_truth_records) == 1137, f"Expected 1137 ground truth records, got {len(ground_truth_records)}"
    assert len(fp_records) == 8, f"Expected 8 false positive records, got {len(fp_records)}"
    assert len(fn_records) == 10, f"Expected 10 false negative records, got {len(fn_records)}"

    # 6. Write output files
    print(f"\nWriting {len(ground_truth_records)} records to {OUTPUT_GROUND_TRUTH_PATH}...")
    write_jsonl(OUTPUT_GROUND_TRUTH_PATH, ground_truth_records)

    print(f"Writing {len(fp_records)} records to {OUTPUT_FALSE_POSITIVES_PATH}...")
    write_jsonl(OUTPUT_FALSE_POSITIVES_PATH, fp_records)

    print(f"Writing {len(fn_records)} records to {OUTPUT_FALSE_NEGATIVES_PATH}...")
    write_jsonl(OUTPUT_FALSE_NEGATIVES_PATH, fn_records)

    # 7. Print summary statistics
    tp_count = sum(1 for r in ground_truth_records if r["expected_outcome"] == "PASS" and r["actual_outcome_layer2"] == "PASS")
    tn_count = sum(1 for r in ground_truth_records if r["expected_outcome"] == "FAIL" and r["actual_outcome_layer2"] == "FAIL")
    fp_count = len(fp_records)
    fn_count = len(fn_records)

    print("\n" + "=" * 80)
    print("  COMPILATION & VERIFICATION COMPLETE")
    print("=" * 80)
    print(f"  Total Master Jobs:     {len(ground_truth_records)}")
    print(f"  True Positives (TP):   {tp_count} (Pass expected & baseline passed)")
    print(f"  True Negatives (TN):   {tn_count} (Fail expected & baseline rejected)")
    print(f"  False Positives (FP):  {fp_count} (Fail expected & baseline passed)")
    print(f"  False Negatives (FN):  {fn_count} (Pass expected & baseline rejected)")
    print(f"  Baseline Accuracy:     {(tp_count + tn_count) / len(ground_truth_records) * 100:.2f}%")
    print(f"  Total Expected PASS:   {tp_count + fn_count}")
    print(f"  Total Expected FAIL:   {tn_count + fp_count}")
    print("=" * 80)


if __name__ == "__main__":
    compile_evaluation_datasets()
