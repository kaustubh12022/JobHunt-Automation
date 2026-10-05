import json
import re
from pathlib import Path

# Load data
with open("regex_audit/master_raw_dataset_2026-09-29.jsonl", "r", encoding="utf-8") as f:
    raw_jobs = [json.loads(line) for line in f]

with open("regex_audit/evaluation/false_positives.jsonl", "r", encoding="utf-8") as f:
    fps = [json.loads(line) for line in f]

with open("regex_audit/evaluation/false_negatives.jsonl", "r", encoding="utf-8") as f:
    fns = [json.loads(line) for line in f]

print("--- Checking 8 False Positives ---")
for fp in fps:
    idx = fp["job_index"]
    job = raw_jobs[idx]
    print(f"FP {idx}: {job['title']} @ {job['company']}")
    assert fp["actual_decision"] == "PASS"
    assert fp["expected_decision"] == "FAIL"

print("\n--- Checking 10 False Negatives ---")
for fn in fns:
    idx = fn["job_index"]
    job = raw_jobs[idx]
    print(f"FN {idx}: {job['title']} @ {job['company']}")
    assert fn["actual_decision"] == "FAIL"
    assert fn["expected_decision"] == "PASS"

# Let's test the proposed regex patterns from audit_report.md
# 1. Progression pattern: fast-track to tech lead
prog_pattern = r'\b(?:fast[- ]track|path(?:way)?|aspiring|journey|road)\s+to\s+(?:tech\s+)?lead\b'
t169 = raw_jobs[169]['title'].lower()
assert re.search(prog_pattern, t169), f"Progression pattern failed on job 169: {t169}"
print("\nJob 169 progression pattern: MATCHED")

# 2. Senior keywords: avp, advanced, [2-9]$
senior_kw = r'\b(?:senior|lead|manager|principal|director|head|vp|president|experienced|architect|staff|expert|ii|iii|iv|v|vi|vii|viii|level\s*[2-9]|l[2-9]|avp|associate\s+vice\s+president|advanced)\b|\bsr[\.,\s]|\bsr$|\b[2-9]$'
t336 = raw_jobs[336]['title'].lower()
t752 = raw_jobs[752]['title'].lower()
t796 = raw_jobs[796]['title'].lower()

assert re.search(senior_kw, t336), f"Senior kw failed on job 336: {t336}"
assert re.search(senior_kw, t752), f"Senior kw failed on job 752: {t752}"
assert re.search(senior_kw, t796), f"Senior kw failed on job 796: {t796}"
print("Jobs 336, 752, 796 senior kw patterns: MATCHED")

# 3. Header check for job 456
d456 = raw_jobs[456]['description'][:1000].lower()
header_check = bool(re.search(r'\bcareer\s+level\s+[1-7]\b.*?(?:manager|leadership|lead\s+engineering)', d456, re.DOTALL) or re.search(r'\b(?:engineering\s+manager|quality\s+engineering\s+manager)\b', d456))
assert header_check, f"Header check failed on job 456"
print("Job 456 header check: MATCHED")

# 4. Experience patterns:
# Job 510: 'Required Experience: 2-5'
d510 = raw_jobs[510]['description'].lower()
kv_range = re.search(r'(?:required|work|total)?\s*experience\s*:\s*(\d+)\s*[-\u2013to]+\s*(\d+)', d510)
assert kv_range and int(kv_range.group(1)) == 2 and int(kv_range.group(2)) == 5
print("Job 510 KV range (2-5): MATCHED")

# Job 513: 'At least five years'
d513 = raw_jobs[513]['description'].lower()
num_tokens = r'(?:[0-9]+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)'
min_p = fr'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?({num_tokens})\s*(?:years?|yrs?\.?)?'
m513 = re.search(min_p, d513)
assert m513 and m513.group(1) == 'five'
print("Job 513 word numeral ('five'): MATCHED")

# Job 563: 'Years of Experience required:\n\n 4'
d563 = raw_jobs[563]['description'].lower()
m563 = re.search(r'years\s+of\s+experience\s+required\s*:\s*(\d+)', d563)
assert m563 and int(m563.group(1)) == 4
print("Job 563 multi-line KV ('4'): MATCHED")

# Job 1038: React experience not stripped
d1038 = raw_jobs[1038]['description'].lower()
assert "3 years of experience working with react" in d1038
print("Job 1038 react experience requirement present in raw text")

print("\n>>> ALL DETAILED DISCREPANCY & PROPOSED REGEX CHECKS PASSED! <<<")
