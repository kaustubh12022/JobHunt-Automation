# Milestone 1 Review & Adversarial Audit Report: Two-Layer Filter Replay

**Reviewer / Adversarial Critic:** `reviewer_replay_1`  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_replay_1`  
**Parent Agent:** `orchestrator_1` (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Date:** 2026-09-29  
**Verdict:** **APPROVE**  

---

## Review Summary

**Verdict**: **APPROVE**  
The Phase 2 / Milestone 1 filter replay implementation and resulting artifacts satisfy all requirements, pass all integrity and adversarial stress checks, strictly adhere to target schemas, and achieve 100% accounting identity across the 1,137 raw jobs.

---

## 1. Quality Review Report

### Findings
- **Critical Findings**: None. No integrity violations, facade implementations, or hardcoded shortcuts detected.
- **Major Findings**: None. Code fidelity against `src/scraper.py` and `src/scorer.py` is exact.
- **Minor / Observational Finding 1**:
  - *Location*: `src/scraper.py`
  - *Context*: `git status` shows uncommitted changes in `src/scraper.py`.
  - *Observation*: Timestamp inspection reveals `src/scraper.py` was last modified on `2026-09-29 19:34:35 IST`, prior to the dispatch of Milestone 1 (`2026-09-29 20:39:21 IST`). The diff consists strictly of raw job logging/callbacks (`_LAST_RAW_JOBS`) added during Phase 1 raw data collection. Worker `worker_replay_m1` did not touch or modify `src/scraper.py`. `src/scorer.py` remains 100% pristine (0 diffs, last modified `2026-09-12 22:11:15 IST`).
  - *Verdict Impact*: Acceptable. No changes were made by the replay worker.

### Verified Claims
| Claim | Verification Method | Result |
|---|---|---|
| Master dataset contains 1,137 jobs | Direct JSON parse & line count of `master_raw_dataset_2026-09-29.jsonl` | **PASS** (1,137 records) |
| Layer 1 Pass count == 73 | Line count & JSON parse of `layer1_pandas_pass.jsonl` | **PASS** (73 records) |
| Layer 1 Fail count == 1,064 | Line count & JSON parse of `layer1_pandas_fail.jsonl` | **PASS** (1,064 records) |
| Layer 2 Pass count == 58 | Line count & JSON parse of `layer2_regex_pass.jsonl` | **PASS** (58 records) |
| Layer 2 Fail count == 15 | Line count & JSON parse of `layer2_regex_fail.jsonl` | **PASS** (15 records) |
| Complete Accounting Identity | Set partition: $L1_{pass} \cup L1_{fail} = \{0 \dots 1136\}$, $L1_{pass} \cap L1_{fail} = \emptyset$, $L2_{pass} \cup L2_{fail} = L1_{pass}$, $L2_{pass} \cap L2_{fail} = \emptyset$ | **PASS** (100% partition) |
| Schema Conformance | Strict key and type validation on all 1,137 records across 4 files against `spec_miner_survey_1` specifications | **PASS** (All fields valid) |
| Code Fidelity (Layer 1) | Mocked `apply_pandas_filter` with pinned scrape time against `Job` objects | **PASS** (Exact 73 identical jobs) |
| Code Fidelity (Layer 2) | Executed `src.scorer` filter functions directly on 73 survivors | **PASS** (Exact 58 pass, 15 fail) |
| Deterministic Idempotence | Re-ran `run_filter_replay.py` and compared SHA-256 hashes of generated files | **PASS** (100% bit-for-bit identical) |
| Integrity & Anti-Cheat | AST inspection & regex scan for hardcoded counts/indices in `run_filter_replay.py` | **PASS** (Zero hardcoding) |

### Coverage Gaps
- None. All 1,137 jobs in the dataset are fully accounted for with zero omissions.

### Unverified Items
- None.

---

## 2. Adversarial Challenge Report

**Overall Risk Assessment**: **LOW**

### Challenges & Stress Tests

#### Challenge 1: Temporal / Freshness Sliding Window Drift
- **Assumption Challenged**: Freshness filter (`hours_old=72`) evaluates deterministically across future test runs.
- **Attack Scenario**: In production, `apply_pandas_filter` computes `cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=hours_old)`. If replay evaluated `pd.Timestamp.now()`, re-running the script tomorrow would drop additional jobs that were fresh on the scrape date (2026-09-29), causing the pass count to decay over time.
- **Stress Test**: Inspected date distribution in raw dataset: 479 jobs from 2026-09-29, 265 from 2026-09-28, 295 undated ("nan"). Verified `run_filter_replay.py` pins `PINNED_SCRAPE_TIME = pd.Timestamp("2026-09-29T14:05:55Z")` and sets `CUTOFF_TIME = PINNED_SCRAPE_TIME - pd.Timedelta(hours=72)`.
- **Blast Radius**: If unpinned, 744 fresh jobs would progressively fail as stale.
- **Result**: **PASS** (Mitigation verified; 100% temporal invariance guaranteed).

#### Challenge 2: Sequential Deduplication Permutation Sensitivity
- **Assumption Challenged**: Deduplication with `keep='first'` produces stable results regardless of data ingestion order.
- **Attack Scenario**: If jobs were loaded out of index order or via unordered sets/dicts, a different instance of a duplicated URL or company/title pair might be retained or dropped.
- **Stress Test**: Verified that `run_filter_replay.py` processes raw jobs strictly in indexed row order `0..1136` and sorts all output lists by `job_index` prior to serialization.
- **Result**: **PASS** (Deterministic ordering guaranteed).

#### Challenge 3: Short-Circuit Attribution Ordering
- **Assumption Challenged**: In Layer 1 and Layer 2, jobs meeting multiple failure criteria (e.g. senior title AND 3+ years experience) are attributed to the correct filter stage.
- **Attack Scenario**: If Layer 1 evaluated experience before senior title, the failure counts per category would deviate from the production pipeline in `src/scraper.py`.
- **Stress Test**: Compared execution sequence in `run_filter_replay.py` against `src/scraper.py:236-328`:
  1. Empty description
  2. Freshness (>72h)
  3. Location regex
  4. Senior title
  5. Experience 3+ years
  6. Deduplication (URL, then company+title)
  Both implementations match in order and drop counts: `senior_title` (516), `experience_3_plus` (356), `duplicate_url` (97), `stale` (74), `location_mismatch` (16), `duplicate_company_title` (5), `empty_description` (0).
- **Result**: **PASS** (Exact architectural alignment).

---

## 3. 5-Component Handoff Report

### 3.1 Observation
1. **File Locations & Output Sizes**:
   - `regex_audit/run_filter_replay.py` (25,858 bytes, 612 lines)
   - `regex_audit/filter_results/layer1_pandas_pass.jsonl` (73 lines, SHA-256: `28083702f890e92c9444f72c705b360d18f531ecc180772ac4fce6f03f6f78af`)
   - `regex_audit/filter_results/layer1_pandas_fail.jsonl` (1,064 lines, SHA-256: `3f45339fc900823fb2216b868f487bf7bf2acf5c60d1eafc5cde6449e2bd1efd`)
   - `regex_audit/filter_results/layer2_regex_pass.jsonl` (58 lines, SHA-256: `ca6a284d06483dacf77435d9bb6518f62bfe1703cb1e5ab07178c615bc295b8e`)
   - `regex_audit/filter_results/layer2_regex_fail.jsonl` (15 lines, SHA-256: `aaf0e2a5f4204ea35951b13c3cba42a973682aea4283ab045e4ff11b374e41a7`)

2. **Replay Re-Execution Output**:
   Running `python regex_audit/run_filter_replay.py` completed with exit code 0:
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

3. **Hash Matching**:
   Re-running the script produced output files with SHA-256 hashes matching the originals character-for-character.

4. **Layer 2 Rejections Breakdown (15 jobs)**:
   - `out_of_scope_stack`: 12 jobs (e.g. Flutter Developer [78, 244], Java or Kotlin & React [84], WordPress/Shopify [164], React Native [175], Full Stack with Laravel in description [178], PHP CodeIgniter [198], Full Stack with Flutter in description [220], App Dev Intern with Flutter [223], QA with Salesforce in description [722], Associate Salesforce QA [736], Application Eng with PHP in description [1075]).
   - `irrelevant_jd`: 3 jobs (Capgemini Software Engineer [155], Full Stack Developer with missing domain anchor [246], C++ Developer Mobileum [263]).

5. **Code Immutability**:
   - `src/scorer.py`: Git status clean, 0 diffs.
   - `src/scraper.py`: Pre-existing modifications from 19:34:35 IST untouched by Milestone 1.

### 3.2 Logic Chain
1. *From Observation 1 & 2*: Exactly 1,137 raw jobs are ingested from `master_raw_dataset_2026-09-29.jsonl`.
2. *From Observation 2*: Layer 1 categorizes 73 jobs as PASS and 1,064 jobs as FAIL. The sum is exactly $73 + 1064 = 1137$. The index sets are disjoint and their union is $\{0 \dots 1136\}$.
3. *From Observation 2 & 4*: Layer 2 evaluates only the 73 Layer 1 survivors, passing 58 and dropping 15. The sum is exactly $58 + 15 = 73$. The index sets are disjoint and their union is strictly the Layer 1 pass index set.
4. *From Observation 1 & Quality Review*: Every record in each of the four JSONL files contains exactly the required fields with matching types according to `spec_miner_survey_1/handoff.md`.
5. *From Observation 3 & Adversarial Review*: Independent execution of `apply_pandas_filter` and `src.scorer` functions confirms that `run_filter_replay.py` does not alter or fake the underlying business logic.
6. *Conclusion*: Milestone 1 is verified with high rigor, free of integrity violations, and ready for Phase 3/4 Ground Truth evaluation.

### 3.3 Caveats
- Layer 1 deduplication drops 102 jobs as duplicate URLs or company/title pairs. As identified in the specifications, their rejection by Layer 1 is technically correct for the scraping pipeline, but their intrinsic JD content will be independently analyzed during Ground Truth compilation.
- No other caveats.

### 3.4 Conclusion
`worker_replay_m1` has executed Milestone 1 flawlessly. The accounting identities, schemas, and code fidelity are fully verified. Verdict is **APPROVE**. Downstream evaluation and ground-truth tasks can proceed immediately using `regex_audit/filter_results/`.

### 3.5 Verification Method
To independently verify this verdict, run the following command from the workspace root:

```powershell
python -c @"
import json
from pathlib import Path

output_dir = Path('regex_audit/filter_results')
with open(output_dir / 'layer1_pandas_pass.jsonl', 'r', encoding='utf-8') as f:
    l1_pass = [json.loads(line) for line in f]
with open(output_dir / 'layer1_pandas_fail.jsonl', 'r', encoding='utf-8') as f:
    l1_fail = [json.loads(line) for line in f]
with open(output_dir / 'layer2_regex_pass.jsonl', 'r', encoding='utf-8') as f:
    l2_pass = [json.loads(line) for line in f]
with open(output_dir / 'layer2_regex_fail.jsonl', 'r', encoding='utf-8') as f:
    l2_fail = [json.loads(line) for line in f]

assert len(l1_pass) == 73
assert len(l1_fail) == 1064
assert len(l2_pass) == 58
assert len(l2_fail) == 15

s_l1_pass = set(r['job_index'] for r in l1_pass)
s_l1_fail = set(r['job_index'] for r in l1_fail)
s_l2_pass = set(r['job_index'] for r in l2_pass)
s_l2_fail = set(r['job_index'] for r in l2_fail)

assert s_l1_pass | s_l1_fail == set(range(1137))
assert len(s_l1_pass & s_l1_fail) == 0
assert s_l2_pass | s_l2_fail == s_l1_pass
assert len(s_l2_pass & s_l2_fail) == 0

print('ALL VERIFICATIONS PASSED!')
"@
```

**Invalidation Conditions:**
- Any change in line counts ($73, 1064, 58, 15$).
- Any missing or extraneous fields in the 4 JSONL schemas.
- Non-empty intersection between pass and fail sets.
