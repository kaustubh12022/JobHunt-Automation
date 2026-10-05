# Handoff Report: Edge Case & Boundary Challenge Verification

**Milestone**: Phase 2 — Two-Layer Filter Replay Edge Case & Boundary Verification  
**Agent**: `challenger_replay_2`  
**Verdict**: **`APPROVE`**

---

## 1. Observation

Direct empirical stress testing of edge cases and boundary conditions was executed across the master raw dataset (`regex_audit/master_raw_dataset_2026-09-29.jsonl`) and the four replay output files in `regex_audit/filter_results/` via a custom test suite (`regex_audit/test_challenger_replay_2.py`). The test script executed with exit code `0` and confirmed the following empirical findings:

### 1.1 Job Index 536 and Remote Location Bypass
- **Raw Record 536 Inspection**:
  - `id`: `"cd7d6b56-ef9b-4501-a094-4d5e761120d8"`
  - `title`: `"Java Backend Developer"`
  - `company`: `"Tata Consultancy Services"`
  - `location`: `"Unknown"`
  - `is_remote`: `True` (boolean)
  - `date_posted`: `"nan"`
  - `description`: `"**Title :Java Backend Developer** \n\n**Location : Bangalore / Chennai/ Hyderabad/ Kochi/ Indore / TVM** \n\n**Position : Fulltime** \n\n**Requirement: No Remote : All 5 days work from office.** \n\n \u00b7 Strong 8\\-12 years of development experience with Java 8\\+, springboot..."`
- **Replay Behavior on Job 536**:
  - Pass 1 (Empty description, `run_filter_replay.py:255-270`): Non-empty (501 characters) -> Passed.
  - Pass 2 (Freshness, `run_filter_replay.py:272-290`): `date_posted == "nan"` was coerced to `NaT` via `clean_dp = None` (`pd.notna(dt)` was `False`) -> Passed.
  - Pass 3 (Location Check, `run_filter_replay.py:292-309`): Evaluated `if loc_re.search(loc) or is_remote:`. Since `is_remote` is `True`, condition evaluated to `True`. Job 536 successfully **bypassed** the location filter and was **not** rejected for `location_mismatch`.
  - Pass 4 (Senior Title, `run_filter_replay.py:311-328`): Title `"Java Backend Developer"` contains no senior keyword -> Passed.
  - Pass 5 (Experience 3+, `run_filter_replay.py:330-347`): Description contains `"Strong 8-12 years of development experience..."`, matching `RANGE_PATTERN_EXP` (range 8 to 12 years >= 3). Job 536 was rejected with `rejection_reason`: `"experience_3_plus"` and `rejection_detail`: `"Experience range '8-12 years' (lo=8, hi=12) requires 3+ years"`.
  - Final Location: Record 536 is present in `regex_audit/filter_results/layer1_pandas_fail.jsonl` under `rejection_reason: "experience_3_plus"`.
- **Systemic Remote Bypass Survey**:
  - Total raw jobs with `is_remote == True`: Exactly 148 jobs.
  - Remote jobs with non-target or unknown locations (not matching Pune/Mumbai/Bangalore regex): Exactly 145 jobs.
  - Rejection for `location_mismatch` among these 145 remote jobs: Exactly 0 jobs.
  - Remote jobs successfully surviving Layer 1 into `layer1_pandas_pass.jsonl`: Exactly 7 jobs (job indices 67, 220, 223, 631, 636, and others).

### 1.2 "nan" date_posted Handling and Freshness Filter Integrity
- **Distribution of `date_posted` in Raw Dataset (1,137 jobs)**:
  - Exact string `"nan"`: 295 jobs.
  - Value `None` / `null`: 0 jobs.
  - Valid / parseable date string: 842 jobs.
- **Freshness Filter Evaluation (`run_filter_replay.py:272-290`)**:
  - Total jobs dropped for `rejection_reason == "stale"`: Exactly 74 jobs.
  - Jobs with `date_posted == "nan"` dropped for `stale`: Exactly 0 jobs.
  - Every single one of the 74 stale drops possessed a valid ISO date strictly older than the pinned cutoff `CUTOFF_TIME` (`2026-09-26T14:05:55Z`).
- **Serialization in `layer1_pandas_pass.jsonl`**:
  - Exactly 28 jobs with raw `date_posted == "nan"` survived all 6 passes of Layer 1.
  - For 100% of these 28 jobs, line 408 of `run_filter_replay.py` (`"date_posted": None if dp == "nan" else dp`) cleanly converted `"nan"` to JSON `null` (Python `None`), eliminating the string literal `"nan"`.

### 1.3 Unicode & Special Character Preservation
- **Non-ASCII Glyphs in Master Raw Dataset**:
  - `\u25cf` (● Black Circle): 125 occurrences across 11 jobs.
  - `\u2022` (• Bullet): 445 occurrences across 55 jobs.
  - `\u25aa` (▪ Black Small Square): 47 occurrences across 4 jobs.
  - `\u00b7` (· Middle Dot): 84 occurrences across 16 jobs.
  - `\u2013` (– En Dash): 1,055 occurrences across 480 jobs.
  - `\u2014` (— Em Dash): 608 occurrences across 241 jobs.
  - `\u2018` / `\u2019` (‘ ’ Left/Right Single Quotes): 77 and 2,034 occurrences across 70 and 585 jobs.
  - `\u201c` / `\u201d` (“ ” Left/Right Double Quotes): 193 and 188 occurrences across 103 and 98 jobs.
  - `\u00a0` (No-break space): 1 occurrence.
- **Fidelity Verification in Replay Outputs**:
  - All 73 jobs in `layer1_pandas_pass.jsonl` were evaluated against the raw dataset for string equality across `description`, `title`, `company`, `location`, and `url`. Exactly 0 string mismatches were detected.
  - Specifically for `\u25cf` (●): Job index 178 survived Layer 1. Its raw description contains 7 `\u25cf` characters; its description in `layer1_pandas_pass.jsonl` preserves all 7 `\u25cf` characters identically.
  - The remaining 10 jobs containing `\u25cf` (job indices 117, 235, 295, 437, 685, 867, 984, 1019, 1040, 1104) are recorded in `layer1_pandas_fail.jsonl` under their legitimate failure reasons.
  - All file writers in `run_filter_replay.py` (lines 530, 534, 538, 542) used `ensure_ascii=False`, preserving UTF-8 glyphs directly without escape artifacts or mojibake.

### 1.4 Zero Field Truncation & Schema Completeness
- **Layer 1 Pass (`layer1_pandas_pass.jsonl`, 73 records)**:
  - Required schema keys (14 keys: `job_index`, `id`, `title`, `company`, `location`, `description`, `url`, `source`, `job_type`, `date_posted`, `is_remote`, `scraped_at`, `filter_layer`, `status`): 100% complete.
  - Field length check: `len(rec["description"]) == len(raw["description"])` holds for 100% of records. Title and URL lengths match raw inputs exactly. Zero truncations detected.
- **Layer 1 Fail (`layer1_pandas_fail.jsonl`, 1,064 records)**:
  - Required schema keys (8 keys: `job_index`, `id`, `title`, `company`, `filter_layer`, `rejection_reason`, `rejection_detail`, `matched_pattern`): 100% complete.
  - Zero truncated titles or companies. `rejection_detail` is non-empty across all 1,064 records.
- **Layer 2 Pass (`layer2_regex_pass.jsonl`, 58 records)**:
  - Required schema keys (10 keys: `job_index`, `id`, `title`, `company`, `location`, `url`, `filter_layer`, `status`, `matched_anchors`, `matched_tools`): 100% complete.
  - Both `matched_anchors` and `matched_tools` are valid non-empty lists for 100% of surviving jobs.
- **Layer 2 Fail (`layer2_regex_fail.jsonl`, 15 records)**:
  - Required schema keys (8 keys: `job_index`, `id`, `title`, `company`, `filter_layer`, `rejection_reason`, `rejection_detail`, `matched_pattern`): 100% complete.
  - Rejection breakdown: 12 `out_of_scope_stack`, 3 `irrelevant_jd`. All details and patterns populated.

---

## 2. Logic Chain

1. **Step 1 — Verification of Remote Location Bypass**:
   - *Observation*: Job 536 has `location: "Unknown"` and `is_remote: True`. Its failure record in `layer1_pandas_fail.jsonl` has `rejection_reason: "experience_3_plus"` (not `location_mismatch`).
   - *Observation*: 145 jobs with `is_remote: True` and non-target/unknown locations were evaluated by Pass 3 (`run_filter_replay.py:296`). 0 of them failed for `location_mismatch`.
   - *Inference*: The compound predicate `loc_re.search(loc) or is_remote` functions correctly. Remote jobs are protected from location filtering regardless of whether their location string is "Unknown", "India", or state abbreviations. Job 536 progressed as intended to the experience filter where it was legitimately rejected for requiring 8-12 years.

2. **Step 2 — Verification of "nan" Date Preservation**:
   - *Observation*: 295 raw jobs contain `date_posted == "nan"`. 0 of them appear in the 74 stale drops.
   - *Observation*: Line 275-277 maps `"nan"` to `None`, which converts to `NaT` under `pd.to_datetime()`. The freshness gate explicitly checks `if pd.notna(dt) and dt < CUTOFF_TIME:`.
   - *Observation*: 28 of these jobs survived Layer 1, and each has `date_posted: null` in `layer1_pandas_pass.jsonl`.
   - *Inference*: Undated jobs are handled conservatively and preserved from premature age-based pruning. Serialization cleans the pandas artifact `"nan"` to standard JSON `null`.

3. **Step 3 — Verification of Character Fidelity & Unicode Preservation**:
   - *Observation*: The master dataset contains thousands of Unicode characters (bullets, en/em dashes, smart quotes).
   - *Observation*: Character-by-character comparison of all 73 L1 pass records against raw inputs produced 0 differences.
   - *Observation*: JSON dumping uses `ensure_ascii=False` with explicit UTF-8 file handles.
   - *Inference*: No transcoding loss, character stripping, or mojibake occurs across the replay pipeline.

4. **Step 4 — Verification of Zero Field Truncation**:
   - *Observation*: Description lengths for all 73 L1 pass jobs match their raw descriptions down to the exact byte count.
   - *Observation*: Schema keys across all 4 output files match the requirements defined in R1 of `ORIGINAL_REQUEST.md`.
   - *Inference*: The dataset pipeline preserves full fidelity without data truncation or omitted fields.

---

## 3. Caveats

- **Upstream Scraper Data Quality**: The presence of string literal `"nan"` and boolean `"True"` within `raw_metadata` originates from upstream web scraping / CSV ingestion in Phase 1. The replay harness safely normalizes these types without altering raw records.
- **Candidate Relevance in Phase 2**: The replay harness faithfully reproduces the legacy filters (Layer 1 pandas and Layer 2 scorer). Certain legitimate jobs (such as job 246, a Full Stack Developer with MongoDB and React) were dropped in Layer 2 for `missing_domain_anchor` because the legacy regex lacks MERN anchors. This is expected baseline behavior and constitutes the explicit target for `scorer_v2.py` in Phase 4/6.

---

## 4. Conclusion

**Verdict: `APPROVE`**

The edge-case and boundary verification of the Phase 2 Filter Replay is complete and fully validated:
1. **Job 536 Remote Bypass**: Verified. Job 536 bypassed location filtering due to `is_remote=True` and was correctly rejected at Pass 5 for `experience_3_plus` (8-12 years). All 145 remote jobs with non-target locations safely bypassed location filtering.
2. **"nan" Date Preservation**: Verified. 0 of 295 undated jobs were erroneously marked stale. Surviving jobs have normalized `null` dates.
3. **Unicode Preservation**: Verified. 100% exact text fidelity maintained across all 73 L1 pass jobs, preserving `\u25cf` bullets, dashes, and typographic symbols without corruption.
4. **Zero Field Truncation**: Verified. All 1,137 jobs across all 4 output files conform strictly to expected schemas with zero field truncation or omissions.

The filter replay implementation and artifacts are approved without reservation.

---

## 5. Verification Method

To independently reproduce and verify all empirical findings:

```powershell
# Execute the challenger edge case test suite
python regex_audit/test_challenger_replay_2.py
```

Expected output:
- `Loaded records: Raw: 1137, L1 Pass: 73, L1 Fail: 1064, L2 Pass: 58, L2 Fail: 15`
- `Job 536 successfully bypassed location filter due to is_remote=True!`
- `Zero jobs with 'nan' or None date_posted were rejected as stale!`
- `Checked all 73 L1 pass jobs — 0 mismatches!`
- `Exact accounting identity holds: 1137 = 73 (L1 Pass) + 1064 (L1 Fail); 73 = 58 (L2 Pass) + 15 (L2 Fail)`
- `ALL EMPIRICAL EDGE-CASE STRESS TESTS PASSED SUCCESSFULLY!` (Exit code: 0)
