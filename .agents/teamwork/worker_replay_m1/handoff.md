# Handoff Report: Deterministic Two-Layer Filter Replay (Phase 2)

**Author:** `worker_replay_m1`  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_replay_m1`  
**Target Audience:** `orchestrator_1` (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Date:** 2026-09-29  
**Status:** Hard Handoff (Phase 2 Implementation Complete)

---

## 1. Observation

1. **Dataset Invariance & Verification**:
   - Master dataset `regex_audit/master_raw_dataset_2026-09-29.jsonl` contains exactly 1,137 raw job postings.
   - Pinned reference timestamp `2026-09-29T14:05:55Z` was used to establish the 72-hour freshness cutoff (`2026-09-26T14:05:55Z`), ensuring 100% reproducible execution over time.
   - 295 records with `date_posted == "nan"` were correctly preserved as fresh/undated per `src/scraper.py:241-250`.

2. **Replay Script Implementation**:
   - Implemented `regex_audit/run_filter_replay.py` without external network access or AI/LLM API calls.
   - Replicated Layer 1 (Pandas Pre-Filter) matching `src/scraper.py:209-354`:
     - Empty description check
     - Freshness check (>72h cutoff relative to pinned scrape time)
     - Location check (target cities `['pune', 'mumbai', 'bangalore']` with aliases and remote bypass if `is_remote == True`)
     - `matches_senior_title`
     - `requires_3_plus_years`
     - Deduplication: Pass A on `normalized_url`; Pass B on `(clean_title, clean_company)`
   - Replicated Layer 2 (Scorer Regex Filter) matching `src/scorer.py:337-352` on Layer 1 survivors:
     - `matches_senior_title`
     - `matches_out_of_scope_role`
     - `requires_3_plus_years`
     - `is_relevant_jd`

3. **Execution Output & Verification**:
   Running `python regex_audit/run_filter_replay.py` produced:
   ```text
   ======================================================================
     TWO-LAYER FILTER REPLAY HARNESS
     Dataset: C:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\master_raw_dataset_2026-09-29.jsonl
     Pinned Scrape Time: 2026-09-29T14:05:55+00:00
     Cutoff Time: 2026-09-26T14:05:55+00:00 (72h freshness)
   ======================================================================
   [Dataset] Loaded 1137 jobs from master raw dataset
   [Layer 1] Pass survivors: 73
   [Layer 1] Dropped records: 1064
   [Layer 2] Pass survivors: 58
   [Layer 2] Dropped records: 15
   [Artifacts] Successfully wrote all 4 JSONL filter results files.
   ======================================================================
     VERIFICATION COMPLETE: 100% ACCOUNTING IDENTITY CONFIRMED
     Total Raw:       1137
     Layer 1 Pass:    73
     Layer 1 Fail:    1064  (Pass + Fail = 1137)
     Layer 2 Pass:    58
     Layer 2 Fail:    15   (Pass + Fail = 73)
   ======================================================================
   ```

4. **Detailed Rejection Breakdown**:
   - **Layer 1 Rejections (1,064 total)**:
     - `senior_title`: 516
     - `experience_3_plus`: 356
     - `duplicate_url`: 97
     - `stale`: 74
     - `location_mismatch`: 16
     - `duplicate_company_title`: 5
     - `empty_description`: 0
   - **Layer 2 Rejections (15 total)**:
     - `out_of_scope_stack`: 12
     - `irrelevant_jd`: 3
     - `senior_title`: 0
     - `experience_3_plus`: 0

5. **Code Immutability Check**:
   - `src/scorer.py`: Git clean, 0 diffs.
   - Neither `src/scraper.py` nor `src/scorer.py` were modified by this worker.

---

## 2. Logic Chain

1. **Partitioning and Conservation of Records**:
   - From Observation 1 & 3, the input comprises exactly $N = 1,137$ raw jobs indexed from $0$ to $1,136$.
   - Layer 1 partitions the 1,137 jobs into survivors ($73$) and rejections ($1,064$). The index union is strictly $\{0 \dots 1136\}$ and the intersection is $\emptyset$.
   - Layer 2 operates solely on the 73 survivors of Layer 1, partitioning them into final passes ($58$) and final rejections ($15$). The index union is strictly the set of 73 Layer 1 survivor indices and the intersection is $\emptyset$.
   - Therefore, the accounting identity holds at 100% precision:
     $$\text{Total Raw} = 1137 = 73 + 1064$$
     $$\text{Layer 1 Pass} = 73 = 58 + 15$$

2. **Deduplication Dependency & Reproducibility**:
   - URL and company/title deduplication evaluate rows sequentially with `keep='first'`.
   - By reading `master_raw_dataset_2026-09-29.jsonl` in its canonical row order (0..1136), deduplication produces identical drops regardless of execution environment.
   - Pinned reference time `2026-09-29T14:05:55Z` ensures that the 72h freshness filter remains immutable across future runs.

3. **Schema Compliance**:
   - Every record in `layer1_pandas_pass.jsonl` contains the 14 required fields: `job_index`, `id`, `title`, `company`, `location`, `description`, `url`, `source`, `job_type`, `date_posted`, `is_remote`, `scraped_at`, `filter_layer`, `status`.
   - Every record in `layer1_pandas_fail.jsonl` and `layer2_regex_fail.jsonl` contains the 8 required fields: `job_index`, `id`, `title`, `company`, `filter_layer`, `rejection_reason`, `rejection_detail`, `matched_pattern`.
   - Every record in `layer2_regex_pass.jsonl` contains the 10 required fields: `job_index`, `id`, `title`, `company`, `location`, `url`, `filter_layer`, `status`, `matched_anchors`, `matched_tools`.

---

## 3. Caveats

1. **Layer 2 Downstream Nature**:
   Layer 2 only evaluated the 73 jobs that passed Layer 1. As noted in earlier surveys, many false negatives (such as MERN jobs) were dropped in Layer 1 by `senior_title` or `experience_3_plus` before reaching Layer 2, while the 3 `irrelevant_jd` drops in Layer 2 (e.g. Capgemini Software Engineer and MERN Developer) illustrate the known deficiencies in `DOMAIN_ANCHORS` and `TECH_TOOLS`.
2. **Deduplication Classification**:
   102 jobs dropped during Layer 1 deduplication (97 URL duplicates, 5 Title+Company duplicates) are marked with `duplicate_url` and `duplicate_company_title`. Their intrinsic profile suitability will be evaluated independently in Phase 3/4 Ground Truth compilation.
3. **Immutability of Baseline Code**:
   No changes were made to `src/scraper.py` or `src/scorer.py`. All filter replay logic is encapsulated within `regex_audit/run_filter_replay.py`.

---

## 4. Conclusion

Phase 2 (Two-Layer Filter Replay) is complete and verified:
1. `regex_audit/run_filter_replay.py` is implemented, deterministic, self-contained, and uses zero AI/LLM calls.
2. The four JSONL artifacts have been generated and validated in `regex_audit/filter_results/`:
   - `layer1_pandas_pass.jsonl` (73 records)
   - `layer1_pandas_fail.jsonl` (1,064 records)
   - `layer2_regex_pass.jsonl` (58 records)
   - `layer2_regex_fail.jsonl` (15 records)
3. 100% accounting identity across all 1,137 jobs is confirmed with zero record collisions or omissions.
4. Downstream agents (evaluator workers for Ground Truth generation and audit engineers) can proceed immediately using these verified artifacts.

---

## 5. Verification Method

To independently verify the replay execution and accounting identity, execute the following PowerShell command from the repository root:

```powershell
python -c @"
import json
from pathlib import Path
from collections import Counter

output_dir = Path('regex_audit/filter_results')
files = {
    'l1_pass': output_dir / 'layer1_pandas_pass.jsonl',
    'l1_fail': output_dir / 'layer1_pandas_fail.jsonl',
    'l2_pass': output_dir / 'layer2_regex_pass.jsonl',
    'l2_fail': output_dir / 'layer2_regex_fail.jsonl'
}

data = {}
for k, p in files.items():
    assert p.exists(), f'{p} does not exist'
    with open(p, 'r', encoding='utf-8') as f:
        lines = [json.loads(line) for line in f if line.strip()]
    data[k] = lines
    print(f'{k}: {len(lines)} records')

assert len(data['l1_pass']) == 73, 'L1 pass count mismatch'
assert len(data['l1_fail']) == 1064, 'L1 fail count mismatch'
assert len(data['l2_pass']) == 58, 'L2 pass count mismatch'
assert len(data['l2_fail']) == 15, 'L2 fail count mismatch'

# Exact index partitioning
l1_pass_idx = [r['job_index'] for r in data['l1_pass']]
l1_fail_idx = [r['job_index'] for r in data['l1_fail']]
l2_pass_idx = [r['job_index'] for r in data['l2_pass']]
l2_fail_idx = [r['job_index'] for r in data['l2_fail']]

assert sorted(l1_pass_idx + l1_fail_idx) == list(range(1137)), 'L1 accounting failed'
assert sorted(l2_pass_idx + l2_fail_idx) == sorted(l1_pass_idx), 'L2 accounting failed'

print('L1 Fail breakdown:', Counter([r['rejection_reason'] for r in data['l1_fail']]))
print('L2 Fail breakdown:', Counter([r['rejection_reason'] for r in data['l2_fail']]))
print('INDEPENDENT VERIFICATION SUCCESSFUL: All 1,137 jobs verified!')
"@
```

**Invalidation Conditions:**
- Any discrepancy in record count ($73, 1064, 58, 15$).
- Any missing or duplicate `job_index` in the union of pass and fail sets.
- Any modification to `src/scraper.py` or `src/scorer.py`.
