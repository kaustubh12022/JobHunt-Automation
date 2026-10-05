import json
import hashlib
from pathlib import Path

ROOT = Path(r"c:\Users\kalek\Desktop\Projects\Job_Hunt")

print("--- Inspecting Evaluator Worker Batches ---")
for b in [1, 2, 3]:
    p = ROOT / f".agents/teamwork/evaluator_worker_{b}/batch_eval_{b}.jsonl"
    with open(p, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    fps = [x for x in records if x.get("flag_type") == "false_positive"]
    fns = [x for x in records if x.get("flag_type") == "false_negative"]
    passes = [x for x in records if x.get("expected_outcome") == "PASS"]
    fails = [x for x in records if x.get("expected_outcome") == "FAIL"]
    min_idx = min(x["job_index"] for x in records)
    max_idx = max(x["job_index"] for x in records)
    print(f"Worker {b}: {len(records)} records, range=[{min_idx}..{max_idx}], PASS={len(passes)}, FAIL={len(fails)}, FP={len(fps)}, FN={len(fns)}")

print("\n--- Inspecting Compiled Files in regex_audit/evaluation ---")
for fname in ["ground_truth.jsonl", "false_positives.jsonl", "false_negatives.jsonl"]:
    p = ROOT / "regex_audit" / "evaluation" / fname
    data = p.read_bytes()
    lines = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    sha = hashlib.sha256(data).hexdigest()
    print(f"{fname}: {len(lines)} records, size={len(data)} bytes, sha256={sha}")

print("\n--- Testing Network Lockdown & Deterministic Compilation ---")
import socket
import subprocess

def no_net(*args, **kwargs):
    raise RuntimeError("ILLEGAL NETWORK ACCESS ATTEMPTED!")

socket.socket.connect = no_net
socket.create_connection = no_net
socket.getaddrinfo = no_net

# Import and run compile_evaluation_datasets under network lockdown
import importlib.util
spec = importlib.util.spec_from_file_location("compile_gt", str(ROOT / "regex_audit" / "compile_ground_truth.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.compile_evaluation_datasets()
print("Compilation executed successfully under strict network lockdown!")

print("\n--- Re-verifying SHA256 Checksums after Re-compilation ---")
expected_shas = {
    "ground_truth.jsonl": "0ff51e159c9058aaede4b268b17b73b40c5570f2106e64512d21f0f40252c80d",
    "false_positives.jsonl": "983ad3da97402a2b8e13de0e2b4ac35171519c743a35108f5418c24263752047",
    "false_negatives.jsonl": "6b8f2853c3b88de58d8b0bbf160022f1598a34383f976ec7d2dba5707ba3c23f"
}

all_match = True
for fname, exp_sha in expected_shas.items():
    p = ROOT / "regex_audit" / "evaluation" / fname
    actual_sha = hashlib.sha256(p.read_bytes()).hexdigest()
    match = (actual_sha == exp_sha)
    if not match: all_match = False
    print(f"{fname}: {'MATCH' if match else 'MISMATCH'} ({actual_sha})")

if all_match:
    print("ALL CHECKSUMS MATCH EXACTLY. Output is 100% deterministic.")
else:
    print("WARNING: Checksum mismatch detected!")

