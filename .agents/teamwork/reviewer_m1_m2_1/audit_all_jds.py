import json
import sys
import re

with open("scoring_audit/synthetic_jds.json", "r", encoding="utf-8") as f:
    jds = json.load(f)

print(f"Loaded {len(jds)} JDs.")

# Check IDs
ids = [j["id"] for j in jds]
expected_ids = [f"SYNTH_{i:03d}" for i in range(1, 301)]
assert ids == expected_ids, "IDs do not match expected sequence SYNTH_001..SYNTH_300"
print("[PASS] IDs sequence SYNTH_001..SYNTH_300 exact match.")

# Check length of descriptions
desc_lens = [len(j["description"]) for j in jds]
min_len = min(desc_lens)
max_len = max(desc_lens)
avg_len = sum(desc_lens) / len(desc_lens)
print(f"[INFO] Description lengths: min={min_len}, max={max_len}, avg={avg_len:.1f}")

# Check sparse vs rich
sparse_jds = [j for j in jds if j["category"] == "Sparse_Job_Description"]
rich_jds = [j for j in jds if j["category"] != "Sparse_Job_Description"]

print(f"[INFO] Sparse JDs count: {len(sparse_jds)}, min_len={min(len(j['description']) for j in sparse_jds)}, max_len={max(len(j['description']) for j in sparse_jds)}")
print(f"[INFO] Rich JDs count: {len(rich_jds)}, min_len={min(len(j['description']) for j in rich_jds)}, max_len={max(len(j['description']) for j in rich_jds)}")

# Check fields non-empty
for i, j in enumerate(jds):
    assert j["title"].strip(), f"Empty title in JD {j['id']}"
    assert j["company"].strip(), f"Empty company in JD {j['id']}"
    assert j["location"].strip(), f"Empty location in JD {j['id']}"
    assert j["experience_required"].strip(), f"Empty experience in JD {j['id']}"
    assert j["description"].strip(), f"Empty description in JD {j['id']}"
    gt = j["ground_truth"]
    assert 0 <= gt["expected_min_score"] <= gt["expected_max_score"] <= 100, f"Score error in {j['id']}"
    assert isinstance(gt["is_testing_role"], bool), f"is_testing_role type error in {j['id']}"
    assert isinstance(gt["acceptable_pass"], bool), f"acceptable_pass type error in {j['id']}"
    assert isinstance(gt["expected_missing_skills"], list), f"expected_missing_skills type error in {j['id']}"

print("[PASS] All 300 records have non-empty valid fields and ground truth.")
