import sys
import json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(r"c:\Users\kalek\Desktop\Projects\Job_Hunt")
with open(ROOT / "regex_audit" / "master_raw_dataset_2026-09-29.jsonl", "r", encoding="utf-8") as f:
    raw_jobs = {r["job_index"]: r for r in (json.loads(line) for line in f if line.strip())}

fp_indices = [336, 456, 510, 513, 563, 752, 796, 1038]
fn_indices = [18, 84, 119, 169, 220, 246, 466, 687, 722, 1027]

print("==================== FALSE POSITIVES (EXPECTED FAIL, BASELINE PASSED) ====================")
for idx in fp_indices:
    r = raw_jobs[idx]
    print(f"\n--- Job {idx} ---")
    print(f"Title: {r['title']}")
    print(f"Company: {r['company']}")
    print(f"Location: {r['location']}")
    print(f"Description snippet (first 600 chars):")
    print(r['description'][:600].replace('\n', ' '))

print("\n\n==================== FALSE NEGATIVES (EXPECTED PASS, BASELINE FAILED) ====================")
for idx in fn_indices:
    r = raw_jobs[idx]
    print(f"\n--- Job {idx} ---")
    print(f"Title: {r['title']}")
    print(f"Company: {r['company']}")
    print(f"Location: {r['location']}")
    print(f"Description snippet (first 600 chars):")
    print(r['description'][:600].replace('\n', ' '))
