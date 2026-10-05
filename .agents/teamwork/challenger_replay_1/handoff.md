# Handoff Report: Challenger Replay Verification

**Milestone**: Phase 2 — Two-Layer Filter Replay Verification  
**Agent**: challenger_replay_1  
**Verdict**: **`APPROVE`**

---

## 1. Observation

Direct empirical evidence was gathered across the raw dataset and all four replay output files:

1. **Master Raw Dataset** (`regex_audit/master_raw_dataset_2026-09-29.jsonl`):
   - Record count: Exactly 1,137 records.
   - Indices: Monotonically increasing from 0 through 1136, with 0 missing indices and 0 duplicates.
   - All records are valid JSON conforming to the Job schema.

2. **Layer 1 Artifacts** (`regex_audit/filter_results/`):
   - `layer1_pandas_pass.jsonl`: 73 records.
   - `layer1_pandas_fail.jsonl`: 1,064 records.
   - Total accounting: `73 + 1,064 = 1,137`.
   - Intersection between pass and fail index sets: `len(pass_indices & fail_indices) == 0`.
   - Union of pass and fail index sets: Exactly matches `set(range(1137))` (`0..1136`).
   - L1 Rejection reasons observed:
     - `senior_title`: 516
     - `experience_3_plus`: 356
     - `duplicate_url`: 97
     - `stale`: 74
     - `location_mismatch`: 16
     - `duplicate_company_title`: 5
     - Total: 1,064

3. **Layer 2 Artifacts** (`regex_audit/filter_results/`):
   - `layer2_regex_pass.jsonl`: 58 records.
   - `layer2_regex_fail.jsonl`: 15 records.
   - Total accounting: `58 + 15 = 73`.
   - Intersection between L2 pass and fail index sets: `len(l2_pass & l2_fail) == 0`.
   - Union of L2 pass and fail index sets: Exactly equals the L1 pass index set (`union_l2 == l1_pass_set`).
   - Leaked records (in L2 but not in L1 pass): Exactly 0.
   - Dropped records (in L1 pass but missing from L2): Exactly 0.
   - L2 Rejection reasons observed:
     - `out_of_scope_stack`: 12
     - `irrelevant_jd`: 3
     - Total: 15

4. **Determinism and Cryptographic Integrity**:
   Pre-execution SHA-256 hashes:
   - `layer1_pandas_pass.jsonl`: `28083702f890e92c9444f72c705b360d18f531ecc180772ac4fce6f03f6f78af`
   - `layer1_pandas_fail.jsonl`: `3f45339fc900823fb2216b868f487bf7bf2acf5c60d1eafc5cde6449e2bd1efd`
   - `layer2_regex_pass.jsonl`: `ca6a284d06483dacf77435d9bb6518f62bfe1703cb1e5ab07178c615bc295b8e`
   - `layer2_regex_fail.jsonl`: `aaf0e2a5f4204ea35951b13c3cba42a973682aea4283ab045e4ff11b374e41a7`

   Executed tool command: `python regex_audit/run_filter_replay.py`.
   Exit code: `0`.
   Post-execution SHA-256 hashes matched the pre-execution hashes byte-for-byte across all four files.

5. **Code Integrity**:
   - `src/scorer.py` remains untouched.
   - Zero external LLM or AI calls were made.

---

## 2. Logic Chain

1. **Partition Integrity**:
   - Observation: `|L1_Pass| = 73`, `|L1_Fail| = 1064`, and `L1_Pass ∩ L1_Fail = ∅`.
   - Observation: `L1_Pass ∪ L1_Fail = {0, 1, ..., 1136}`.
   - Deduction: Layer 1 cleanly and disjointly partitions the master dataset without record loss, ghost jobs, or double counting.

2. **Origin Tracing Integrity**:
   - Observation: `|L2_Pass| = 58`, `|L2_Fail| = 15`, and `L2_Pass ∩ L2_Fail = ∅`.
   - Observation: `(L2_Pass ∪ L2_Fail) = L1_Pass`.
   - Observation: Every attribute (`id`, `title`, `company`, `location`, `url`) in L2 records matches the corresponding L1 pass record.
   - Deduction: Layer 2 processes strictly and exclusively the output of Layer 1. No jobs bypass Layer 1, and no survivors of Layer 1 are dropped unexamined.

3. **Determinism Verification**:
   - Observation: `PINNED_SCRAPE_TIME` (`2026-09-29T14:05:55Z`) pins the freshness evaluation time.
   - Observation: The SHA-256 hash comparison after executing `python regex_audit/run_filter_replay.py` yielded exact matches across all four generated files.
   - Deduction: The replay harness is 100% deterministic, state-independent, and reproducible.

---

## 3. Caveats

- **Scope Boundary**: This verification tested structural integrity, index completeness, origin tracing, and execution determinism. It did not evaluate whether the baseline regex filters made correct recruitment decisions (e.g. false positives/false negatives against the candidate profile), which is the explicit mission of Phase 3 (ground truth generation).
- **Time Pinning**: Freshness relies on the pinned scrape timestamp (`2026-09-29T14:05:55Z`) embedded in `run_filter_replay.py` to avoid runtime drift against `CUTOFF_TIME`.

---

## 4. Conclusion

**Verdict: `APPROVE`**

The Two-Layer Filter Replay implementation and resulting artifacts satisfy all requirements under R1 of `ORIGINAL_REQUEST.md`:
- Exactly 1,137 jobs replayed.
- Disjoint 0..1136 partition verified.
- Origin tracing from Layer 1 to Layer 2 100% verified.
- Byte-for-byte replay determinism empirically confirmed.
- Implementation files `src/scorer.py` and `src/scraper.py` remain preserved.

The pipeline is verified and ready for Phase 3 (Ground-Truth Evaluation).

---

## 5. Verification Method

To independently verify these findings, run the following commands in powershell:

```powershell
# 1. Re-run replay harness
python regex_audit/run_filter_replay.py

# 2. Verify SHA-256 hashes match:
python -c "
import hashlib
from pathlib import Path
expected = {
    'layer1_pandas_pass.jsonl': '28083702f890e92c9444f72c705b360d18f531ecc180772ac4fce6f03f6f78af',
    'layer1_pandas_fail.jsonl': '3f45339fc900823fb2216b868f487bf7bf2acf5c60d1eafc5cde6449e2bd1efd',
    'layer2_regex_pass.jsonl': 'ca6a284d06483dacf77435d9bb6518f62bfe1703cb1e5ab07178c615bc295b8e',
    'layer2_regex_fail.jsonl': 'aaf0e2a5f4204ea35951b13c3cba42a973682aea4283ab045e4ff11b374e41a7',
}
for name, exp_h in expected.items():
    act_h = hashlib.sha256(Path('regex_audit/filter_results/' + name).read_bytes()).hexdigest()
    assert act_h == exp_h, f'Hash mismatch on {name}'
print('All hashes verified byte-for-byte!')
"
```
