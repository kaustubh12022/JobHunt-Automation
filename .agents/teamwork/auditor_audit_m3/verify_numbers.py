import json
from pathlib import Path

BASE_DIR = Path("regex_audit")

# 1. Master raw dataset
with open(BASE_DIR / "master_raw_dataset_2026-09-29.jsonl", "r", encoding="utf-8") as f:
    raw_jobs = [json.loads(line) for line in f]
print(f"1. Raw jobs count: {len(raw_jobs)}")

# 2. Filter replay results
with open(BASE_DIR / "filter_results" / "layer1_pandas_pass.jsonl", "r", encoding="utf-8") as f:
    l1_pass = [json.loads(line) for line in f]
with open(BASE_DIR / "filter_results" / "layer1_pandas_fail.jsonl", "r", encoding="utf-8") as f:
    l1_fail = [json.loads(line) for line in f]
with open(BASE_DIR / "filter_results" / "layer2_regex_pass.jsonl", "r", encoding="utf-8") as f:
    l2_pass = [json.loads(line) for line in f]
with open(BASE_DIR / "filter_results" / "layer2_regex_fail.jsonl", "r", encoding="utf-8") as f:
    l2_fail = [json.loads(line) for line in f]

print(f"2. Layer 1 pass: {len(l1_pass)}, fail: {len(l1_fail)}, sum: {len(l1_pass) + len(l1_fail)}")
print(f"   Layer 2 pass: {len(l2_pass)}, fail: {len(l2_fail)}, sum: {len(l2_pass) + len(l2_fail)}")

# 3. Ground truth
with open(BASE_DIR / "evaluation" / "ground_truth.jsonl", "r", encoding="utf-8") as f:
    gt = [json.loads(line) for line in f]
print(f"3. Ground truth total: {len(gt)}")
gt_pass = [x for x in gt if x["expected_outcome"] == "PASS"]
gt_fail = [x for x in gt if x["expected_outcome"] == "FAIL"]
print(f"   Expected PASS: {len(gt_pass)}, Expected FAIL: {len(gt_fail)}")

# 4. FP and FN
with open(BASE_DIR / "evaluation" / "false_positives.jsonl", "r", encoding="utf-8") as f:
    fps = [json.loads(line) for line in f]
with open(BASE_DIR / "evaluation" / "false_negatives.jsonl", "r", encoding="utf-8") as f:
    fns = [json.loads(line) for line in f]

fp_indices = [x["job_index"] for x in fps]
fn_indices = [x["job_index"] for x in fns]
print(f"4. FP count: {len(fps)}, indices: {fp_indices}")
print(f"   FN count: {len(fns)}, indices: {fn_indices}")

# 5. Confusion matrix calculation
l2_pass_ids = {x["id"] for x in l2_pass}
tp = [x for x in gt if x["expected_outcome"] == "PASS" and x["id"] in l2_pass_ids]
fn = [x for x in gt if x["expected_outcome"] == "PASS" and x["id"] not in l2_pass_ids]
fp = [x for x in gt if x["expected_outcome"] == "FAIL" and x["id"] in l2_pass_ids]
tn = [x for x in gt if x["expected_outcome"] == "FAIL" and x["id"] not in l2_pass_ids]

print(f"5. Confusion Matrix: TP={len(tp)}, FN={len(fn)}, FP={len(fp)}, TN={len(tn)}")
acc = (len(tp) + len(tn)) / len(gt) * 100
prec = len(tp) / (len(tp) + len(fp)) * 100
rec = len(tp) / (len(tp) + len(fn)) * 100
spec = len(tn) / (len(tn) + len(fp)) * 100
f1 = 2 * (prec * rec) / (prec + rec)

print(f"   Overall Accuracy: {acc:.4f}% ({acc:.2f}%)")
print(f"   Precision: {prec:.4f}% ({prec:.2f}%)")
print(f"   Recall: {rec:.4f}% ({rec:.2f}%)")
print(f"   Specificity: {spec:.4f}% ({spec:.2f}%)")
print(f"   F1-Score: {f1:.4f}% ({f1:.2f}%)")
print(f"   Discrepancy count: {len(fp) + len(fn)}")

# 6. Verify job details for FPs and FNs in audit_report.md
expected_fp_indices = [336, 456, 510, 513, 563, 752, 796, 1038]
expected_fn_indices = [18, 84, 119, 169, 220, 246, 466, 687, 722, 1027]

assert fp_indices == expected_fp_indices, f"FP mismatch: {fp_indices} != {expected_fp_indices}"
assert fn_indices == expected_fn_indices, f"FN mismatch: {fn_indices} != {expected_fn_indices}"
assert len(tp) == 50, f"TP mismatch: {len(tp)} != 50"
assert len(tn) == 1069, f"TN mismatch: {len(tn)} != 1069"
assert len(fp) == 8, f"FP mismatch: {len(fp)} != 8"
assert len(fn) == 10, f"FN mismatch: {len(fn)} != 10"
assert round(acc, 2) == 98.42, f"Accuracy mismatch: {acc}"
assert round(prec, 2) == 86.21, f"Precision mismatch: {prec}"
assert round(rec, 2) == 83.33, f"Recall mismatch: {rec}"
assert round(spec, 2) == 99.26, f"Specificity mismatch: {spec}"
assert round(f1, 2) == 84.75, f"F1 mismatch: {f1}"
print("\n>>> ALL EMPIRICAL NUMBER ASSERTIONS PASSED PERFECTLY! <<<")
