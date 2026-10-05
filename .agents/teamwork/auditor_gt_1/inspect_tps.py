import sys
import json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(r"c:\Users\kalek\Desktop\Projects\Job_Hunt")
with open(ROOT / "regex_audit" / "evaluation" / "ground_truth.jsonl", "r", encoding="utf-8") as f:
    gt = [json.loads(l) for l in f if l.strip()]

tps = [r for r in gt if r["expected_outcome"] == "PASS" and r["actual_outcome_layer2"] == "PASS"]
print(f"Total True Positives: {len(tps)}")
print("Index | Title | Company | Location | Domain")
print("-" * 80)
for r in tps:
    print(f"{r['job_index']:4d} | {r['title'][:30]:30s} | {r['company'][:20]:20s} | {r['location'][:20]:20s} | {r['target_domain']}")
