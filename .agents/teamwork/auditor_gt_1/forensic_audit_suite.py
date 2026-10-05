import sys
import json
import hashlib
import socket
import subprocess
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\kalek\Desktop\Projects\Job_Hunt")
EVAL_DIR = PROJECT_ROOT / "regex_audit" / "evaluation"
GT_PATH = EVAL_DIR / "ground_truth.jsonl"
FP_PATH = EVAL_DIR / "false_positives.jsonl"
FN_PATH = EVAL_DIR / "false_negatives.jsonl"
RAW_PATH = PROJECT_ROOT / "regex_audit" / "master_raw_dataset_2026-09-29.jsonl"
L1_PASS = PROJECT_ROOT / "regex_audit" / "filter_results" / "layer1_pandas_pass.jsonl"
L1_FAIL = PROJECT_ROOT / "regex_audit" / "filter_results" / "layer1_pandas_fail.jsonl"
L2_PASS = PROJECT_ROOT / "regex_audit" / "filter_results" / "layer2_regex_pass.jsonl"
L2_FAIL = PROJECT_ROOT / "regex_audit" / "filter_results" / "layer2_regex_fail.jsonl"

def run_forensic_checks():
    print("=" * 80)
    print("  EXHAUSTIVE FORENSIC AUDIT SUITE - AUDITOR_GT_1")
    print("=" * 80)
    
    # Check 1: Baseline file immutability
    print("[Check 1] Baseline Immutability Check...")
    diff_scorer = subprocess.run(["git", "diff", "--stat", "src/scorer.py"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert diff_scorer.stdout.strip() == "", f"VIOLATION: src/scorer.py has diff: {diff_scorer.stdout}"
    print("  PASS: src/scorer.py git diff is 0 lines (completely untouched).")
    
    # Check 2: Load raw dataset
    print("[Check 2] Master Raw Dataset Verification...")
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw_jobs = [json.loads(line) for line in f if line.strip()]
    assert len(raw_jobs) == 1137, f"Expected 1137 raw jobs, got {len(raw_jobs)}"
    raw_by_idx = {r["job_index"]: r for r in raw_jobs}
    print(f"  PASS: Loaded {len(raw_jobs)} raw jobs from master dataset.")

    # Check 3: Load filter replay outputs
    print("[Check 3] Filter Replay Accounting Verification...")
    l1_pass_set = {json.loads(l)["job_index"] for l in open(L1_PASS, encoding="utf-8") if l.strip()}
    l1_fail_set = {json.loads(l)["job_index"] for l in open(L1_FAIL, encoding="utf-8") if l.strip()}
    l2_pass_set = {json.loads(l)["job_index"] for l in open(L2_PASS, encoding="utf-8") if l.strip()}
    l2_fail_set = {json.loads(l)["job_index"] for l in open(L2_FAIL, encoding="utf-8") if l.strip()}

    assert len(l1_pass_set) == 73, f"Expected 73 L1 pass, got {len(l1_pass_set)}"
    assert len(l1_fail_set) == 1064, f"Expected 1064 L1 fail, got {len(l1_fail_set)}"
    assert l1_pass_set.isdisjoint(l1_fail_set), "VIOLATION: L1 pass and fail sets overlap!"
    assert (l1_pass_set | l1_fail_set) == set(range(1137)), "VIOLATION: L1 does not partition 0..1136!"

    assert len(l2_pass_set) == 58, f"Expected 58 L2 pass, got {len(l2_pass_set)}"
    assert len(l2_fail_set) == 15, f"Expected 15 L2 fail, got {len(l2_fail_set)}"
    assert l2_pass_set.isdisjoint(l2_fail_set), "VIOLATION: L2 pass and fail sets overlap!"
    assert (l2_pass_set | l2_fail_set) == l1_pass_set, "VIOLATION: L2 does not partition L1 survivors!"
    print(f"  PASS: Filter replay sets are strictly disjoint and complete (L1: 73+1064=1137, L2: 58+15=73).")

    # Check 4: Ground Truth Schema, Integrity, and Logic
    print("[Check 4] Ground Truth Dataset Verification...")
    with open(GT_PATH, "r", encoding="utf-8") as f:
        gt_jobs = [json.loads(line) for line in f if line.strip()]
    assert len(gt_jobs) == 1137, f"Expected 1137 GT jobs, got {len(gt_jobs)}"

    gt_keys = {
        "job_index", "id", "title", "company", "location", "expected_outcome",
        "actual_outcome_layer1", "actual_outcome_layer2", "is_correct",
        "flag_type", "confidence", "target_domain", "notes"
    }

    tp_indices = []
    tn_indices = []
    fp_indices = []
    fn_indices = []

    for i, r in enumerate(gt_jobs):
        assert r["job_index"] == i, f"Index mismatch at row {i}: job_index={r['job_index']}"
        raw = raw_by_idx[i]
        assert r["id"] == raw["id"], f"ID mismatch at {i}"
        assert r["title"] == raw["title"], f"Title mismatch at {i}"
        assert r["company"] == raw["company"], f"Company mismatch at {i}"
        assert r["location"] == raw["location"], f"Location mismatch at {i}"

        # Replay alignment
        exp_l1 = "PASS" if i in l1_pass_set else "FAIL"
        exp_l2 = "PASS" if i in l2_pass_set else "FAIL"
        assert r["actual_outcome_layer1"] == exp_l1, f"L1 outcome mismatch at {i}"
        assert r["actual_outcome_layer2"] == exp_l2, f"L2 outcome mismatch at {i}"

        # Correctness logic
        expected = r["expected_outcome"]
        actual_l2 = r["actual_outcome_layer2"]
        is_corr = (expected == actual_l2)
        assert r["is_correct"] == is_corr, f"is_correct mismatch at {i}"

        flag = r["flag_type"]
        if expected == "PASS" and actual_l2 == "PASS":
            assert flag is None, f"TP row {i} has non-None flag_type {flag}"
            tp_indices.append(i)
        elif expected == "FAIL" and actual_l2 == "FAIL":
            assert flag is None, f"TN row {i} has non-None flag_type {flag}"
            tn_indices.append(i)
        elif expected == "FAIL" and actual_l2 == "PASS":
            assert flag == "false_positive", f"FP row {i} has incorrect flag_type {flag}"
            fp_indices.append(i)
        elif expected == "PASS" and actual_l2 == "FAIL":
            assert flag == "false_negative", f"FN row {i} has incorrect flag_type {flag}"
            fn_indices.append(i)

    assert len(tp_indices) == 50, f"Expected 50 TP, got {len(tp_indices)}"
    assert len(tn_indices) == 1069, f"Expected 1069 TN, got {len(tn_indices)}"
    assert len(fp_indices) == 8, f"Expected 8 FP, got {len(fp_indices)}"
    assert len(fn_indices) == 10, f"Expected 10 FN, got {len(fn_indices)}"
    print(f"  PASS: Ground truth breakdown confirmed: TP=50, TN=1069, FP=8, FN=10.")

    # Check 5: False Positives Dataset
    print("[Check 5] False Positives Dataset Verification...")
    with open(FP_PATH, "r", encoding="utf-8") as f:
        fp_file = [json.loads(line) for line in f if line.strip()]
    assert len(fp_file) == 8, f"Expected 8 FP, got {len(fp_file)}"
    assert [r["job_index"] for r in fp_file] == fp_indices, f"FP indices mismatch: {[r['job_index'] for r in fp_file]} != {fp_indices}"
    for r in fp_file:
        assert r["actual_decision"] == "PASS"
        assert r["expected_decision"] == "FAIL"
        assert r["issue_type"] == "false_positive"
        for k in ["reason", "which_filter_failed", "root_cause", "specific_pattern_issue"]:
            assert k in r and len(r[k].strip()) > 0, f"FP record {r['job_index']} missing/empty {k}"
    print(f"  PASS: 8 FP records verified with indices {fp_indices}.")

    # Check 6: False Negatives Dataset
    print("[Check 6] False Negatives Dataset Verification...")
    with open(FN_PATH, "r", encoding="utf-8") as f:
        fn_file = [json.loads(line) for line in f if line.strip()]
    assert len(fn_file) == 10, f"Expected 10 FN, got {len(fn_file)}"
    assert [r["job_index"] for r in fn_file] == fn_indices, f"FN indices mismatch: {[r['job_index'] for r in fn_file]} != {fn_indices}"
    for r in fn_file:
        assert r["actual_decision"] == "FAIL"
        assert r["expected_decision"] == "PASS"
        assert r["issue_type"] == "false_negative"
        assert r["rejection_layer"] in ("layer1_pandas", "layer2_regex")
        for k in ["reason", "which_filter_rejected", "root_cause", "specific_pattern_issue"]:
            assert k in r and len(r[k].strip()) > 0, f"FN record {r['job_index']} missing/empty {k}"
    print(f"  PASS: 10 FN records verified with indices {fn_indices}.")

    # Check 7: Network Lockdown & Deterministic Reproduction
    print("[Check 7] Network Lockdown & Deterministic Compilation Check...")
    def no_net(*args, **kwargs):
        raise RuntimeError("NETWORK ATTEMPT DETECTED!")
    socket.socket.connect = no_net
    socket.create_connection = no_net
    socket.getaddrinfo = no_net

    import importlib.util
    spec = importlib.util.spec_from_file_location("compile_gt", str(PROJECT_ROOT / "regex_audit" / "compile_ground_truth.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.compile_evaluation_datasets()

    shas = {
        "ground_truth.jsonl": hashlib.sha256(GT_PATH.read_bytes()).hexdigest(),
        "false_positives.jsonl": hashlib.sha256(FP_PATH.read_bytes()).hexdigest(),
        "false_negatives.jsonl": hashlib.sha256(FN_PATH.read_bytes()).hexdigest(),
    }
    expected_shas = {
        "ground_truth.jsonl": "0ff51e159c9058aaede4b268b17b73b40c5570f2106e64512d21f0f40252c80d",
        "false_positives.jsonl": "983ad3da97402a2b8e13de0e2b4ac35171519c743a35108f5418c24263752047",
        "false_negatives.jsonl": "6b8f2853c3b88de58d8b0bbf160022f1598a34383f976ec7d2dba5707ba3c23f"
    }
    for fname, exp_sha in expected_shas.items():
        assert shas[fname] == exp_sha, f"SHA256 mismatch for {fname}: got {shas[fname]} vs expected {exp_sha}"
        print(f"  SHA256 MATCH for {fname}: {shas[fname]}")
    print("  PASS: Output is 100% byte-for-byte deterministic under network lockdown.")

    print("=" * 80)
    print("  FORENSIC AUDIT RESULT: ALL 7 CHECKS PASSED EMPIRICALLY.")
    print("  VERDICT: CLEAN")
    print("=" * 80)

if __name__ == "__main__":
    run_forensic_checks()
