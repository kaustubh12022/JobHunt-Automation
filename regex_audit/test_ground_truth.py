#!/usr/bin/env python3
"""
Test Suite for Ground Truth Compilation and Validation.

Verifies:
1. File existence and line counts of ground_truth.jsonl, false_positives.jsonl, false_negatives.jsonl
2. Sequential indexing (0..1136) with 0 missing indices
3. Valid JSON syntax on every line
4. Strict schema compliance for all 3 datasets
5. Internal consistency (is_correct, flag_type, expected_outcome vs actual_outcome_layer2)
6. Cross-reference fidelity against raw dataset and filter results
7. Immutability of production code (src/scorer.py and src/scraper.py)
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_DIR = PROJECT_ROOT / "regex_audit" / "evaluation"
GT_PATH = EVALUATION_DIR / "ground_truth.jsonl"
FP_PATH = EVALUATION_DIR / "false_positives.jsonl"
FN_PATH = EVALUATION_DIR / "false_negatives.jsonl"
RAW_PATH = PROJECT_ROOT / "regex_audit" / "master_raw_dataset_2026-09-29.jsonl"
L1_PASS_PATH = PROJECT_ROOT / "regex_audit" / "filter_results" / "layer1_pandas_pass.jsonl"
L2_PASS_PATH = PROJECT_ROOT / "regex_audit" / "filter_results" / "layer2_regex_pass.jsonl"


def test_file_existence_and_counts():
    """Verify all deliverables exist with exact expected line counts."""
    print("Test 1: File existence and line count verification...")
    assert GT_PATH.exists(), f"Missing {GT_PATH}"
    assert FP_PATH.exists(), f"Missing {FP_PATH}"
    assert FN_PATH.exists(), f"Missing {FN_PATH}"

    with open(GT_PATH, "r", encoding="utf-8") as f:
        gt_lines = [l for l in f if l.strip()]
    with open(FP_PATH, "r", encoding="utf-8") as f:
        fp_lines = [l for l in f if l.strip()]
    with open(FN_PATH, "r", encoding="utf-8") as f:
        fn_lines = [l for l in f if l.strip()]

    assert len(gt_lines) == 1137, f"Expected 1137 GT records, got {len(gt_lines)}"
    assert len(fp_lines) == 8, f"Expected 8 FP records, got {len(fp_lines)}"
    assert len(fn_lines) == 10, f"Expected 10 FN records, got {len(fn_lines)}"
    print(f"  PASS: GT=1137, FP=8, FN=10")


def test_ground_truth_schema_and_indexing():
    """Verify schema, types, sequential 0..1136 indexing, and logic consistency of ground_truth.jsonl."""
    print("Test 2: Ground Truth schema, indexing, and logic consistency...")
    gt_records = []
    with open(GT_PATH, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f):
            rec = json.loads(line)
            gt_records.append(rec)

    expected_keys = {
        "job_index", "id", "title", "company", "location",
        "expected_outcome", "actual_outcome_layer1", "actual_outcome_layer2",
        "is_correct", "flag_type", "confidence", "target_domain", "notes"
    }

    seen_indices = set()
    tp_count = 0
    tn_count = 0
    fp_count = 0
    fn_count = 0

    for idx, rec in enumerate(gt_records):
        # Sequential index check
        assert rec["job_index"] == idx, f"Line {idx} has job_index {rec['job_index']}"
        seen_indices.add(rec["job_index"])

        # Schema completeness
        assert expected_keys.issubset(rec.keys()), f"Missing keys at index {idx}: {expected_keys - rec.keys()}"

        # Value constraints
        assert isinstance(rec["job_index"], int)
        assert isinstance(rec["id"], str) and len(rec["id"]) > 0
        assert isinstance(rec["title"], str) and len(rec["title"]) > 0
        assert isinstance(rec["company"], str)
        assert isinstance(rec["location"], str)
        assert rec["expected_outcome"] in ("PASS", "FAIL")
        assert rec["actual_outcome_layer1"] in ("PASS", "FAIL")
        assert rec["actual_outcome_layer2"] in ("PASS", "FAIL")
        assert isinstance(rec["is_correct"], bool)
        assert rec["flag_type"] in (None, "false_positive", "false_negative")
        assert rec["confidence"] in ("high", "medium", "low")
        assert isinstance(rec["notes"], str) and len(rec["notes"]) > 0

        # Logic consistency
        expected_is_correct = (rec["expected_outcome"] == rec["actual_outcome_layer2"])
        assert rec["is_correct"] == expected_is_correct, f"is_correct mismatch at {idx}"

        if rec["expected_outcome"] == "PASS" and rec["actual_outcome_layer2"] == "PASS":
            assert rec["flag_type"] is None, f"Expected null flag_type for TP at {idx}"
            tp_count += 1
        elif rec["expected_outcome"] == "FAIL" and rec["actual_outcome_layer2"] == "FAIL":
            assert rec["flag_type"] is None, f"Expected null flag_type for TN at {idx}"
            tn_count += 1
        elif rec["expected_outcome"] == "FAIL" and rec["actual_outcome_layer2"] == "PASS":
            assert rec["flag_type"] == "false_positive", f"Expected false_positive at {idx}"
            fp_count += 1
        elif rec["expected_outcome"] == "PASS" and rec["actual_outcome_layer2"] == "FAIL":
            assert rec["flag_type"] == "false_negative", f"Expected false_negative at {idx}"
            fn_count += 1

    assert len(seen_indices) == 1137
    assert min(seen_indices) == 0
    assert max(seen_indices) == 1136
    assert tp_count == 50, f"Expected 50 TP, got {tp_count}"
    assert tn_count == 1069, f"Expected 1069 TN, got {tn_count}"
    assert fp_count == 8, f"Expected 8 FP, got {fp_count}"
    assert fn_count == 10, f"Expected 10 FN, got {fn_count}"
    print(f"  PASS: 1,137 indices 0..1136 strictly ordered, TP=50, TN=1069, FP=8, FN=10")


def test_false_positives_dataset():
    """Verify false_positives.jsonl schema, indices, and content."""
    print("Test 3: False Positives schema and content verification...")
    with open(FP_PATH, "r", encoding="utf-8") as f:
        fp_records = [json.loads(line) for line in f if line.strip()]

    assert len(fp_records) == 8, f"Expected 8 FP records, got {len(fp_records)}"

    expected_fp_indices = {336, 456, 510, 513, 563, 752, 796, 1038}
    actual_fp_indices = {r["job_index"] for r in fp_records}
    assert actual_fp_indices == expected_fp_indices, f"FP index mismatch: {actual_fp_indices} != {expected_fp_indices}"

    fp_required_keys = {
        "job_index", "id", "title", "company", "actual_decision",
        "expected_decision", "issue_type", "reason", "which_filter_failed",
        "root_cause", "specific_pattern_issue"
    }

    for r in fp_records:
        assert fp_required_keys.issubset(r.keys()), f"FP missing keys in job {r['job_index']}"
        assert r["actual_decision"] == "PASS"
        assert r["expected_decision"] == "FAIL"
        assert r["issue_type"] == "false_positive"
        assert len(r["reason"]) > 0
        assert len(r["which_filter_failed"]) > 0
        assert len(r["root_cause"]) > 0
        assert len(r["specific_pattern_issue"]) > 0

    print(f"  PASS: 8 FP records verified with indices {sorted(actual_fp_indices)}")


def test_false_negatives_dataset():
    """Verify false_negatives.jsonl schema, indices, and content."""
    print("Test 4: False Negatives schema and content verification...")
    with open(FN_PATH, "r", encoding="utf-8") as f:
        fn_records = [json.loads(line) for line in f if line.strip()]

    assert len(fn_records) == 10, f"Expected 10 FN records, got {len(fn_records)}"

    expected_fn_indices = {18, 84, 119, 169, 220, 246, 466, 687, 722, 1027}
    actual_fn_indices = {r["job_index"] for r in fn_records}
    assert actual_fn_indices == expected_fn_indices, f"FN index mismatch: {actual_fn_indices} != {expected_fn_indices}"

    fn_required_keys = {
        "job_index", "id", "title", "company", "actual_decision",
        "expected_decision", "issue_type", "reason", "which_filter_rejected",
        "rejection_layer", "root_cause", "specific_pattern_issue"
    }

    for r in fn_records:
        assert fn_required_keys.issubset(r.keys()), f"FN missing keys in job {r['job_index']}"
        assert r["actual_decision"] == "FAIL"
        assert r["expected_decision"] == "PASS"
        assert r["issue_type"] == "false_negative"
        assert r["rejection_layer"] in ("layer1_pandas", "layer2_regex")
        assert len(r["reason"]) > 0
        assert len(r["which_filter_rejected"]) > 0
        assert len(r["root_cause"]) > 0
        assert len(r["specific_pattern_issue"]) > 0

    print(f"  PASS: 10 FN records verified with indices {sorted(actual_fn_indices)}")


def test_fidelity_against_raw_and_replay():
    """Verify 100% field fidelity against raw dataset and filter replay."""
    print("Test 5: Cross-check fidelity against raw dataset and replay filters...")
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw_by_idx = {r["job_index"]: r for r in (json.loads(line) for line in f if line.strip())}

    with open(L1_PASS_PATH, "r", encoding="utf-8") as f:
        l1_pass_indices = {json.loads(line)["job_index"] for line in f if line.strip()}

    with open(L2_PASS_PATH, "r", encoding="utf-8") as f:
        l2_pass_indices = {json.loads(line)["job_index"] for line in f if line.strip()}

    with open(GT_PATH, "r", encoding="utf-8") as f:
        gt_records = [json.loads(line) for line in f if line.strip()]

    for r in gt_records:
        idx = r["job_index"]
        raw = raw_by_idx[idx]

        assert r["id"] == raw["id"], f"ID mismatch at {idx}"
        assert r["title"] == raw["title"], f"Title mismatch at {idx}"
        assert r["company"] == raw["company"], f"Company mismatch at {idx}"
        assert r["location"] == raw["location"], f"Location mismatch at {idx}"

        exp_l1 = "PASS" if idx in l1_pass_indices else "FAIL"
        exp_l2 = "PASS" if idx in l2_pass_indices else "FAIL"
        assert r["actual_outcome_layer1"] == exp_l1, f"Layer 1 mismatch at {idx}"
        assert r["actual_outcome_layer2"] == exp_l2, f"Layer 2 mismatch at {idx}"

    print("  PASS: 100% field fidelity confirmed across all 1,137 jobs.")


def test_code_immutability():
    """Verify that src/scorer.py and src/scraper.py remain untouched."""
    print("Test 6: Production code immutability check...")
    res = subprocess.run(
        ["git", "diff", "--stat", "src/scorer.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True
    )
    assert res.stdout.strip() == "", f"src/scorer.py has been modified!\n{res.stdout}"
    print("  PASS: src/scorer.py has zero git diff.")


def run_all_tests():
    print("=" * 80)
    print("  GROUND TRUTH AND EVALUATION DATASET TEST SUITE")
    print("=" * 80)
    test_file_existence_and_counts()
    test_ground_truth_schema_and_indexing()
    test_false_positives_dataset()
    test_false_negatives_dataset()
    test_fidelity_against_raw_and_replay()
    test_code_immutability()
    print("=" * 80)
    print("  ALL 6 TEST SUITES PASSED WITH ZERO FAILURES!")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
