# Forensic Audit Handoff Report: Filter Replay Pipeline

**Work Product**: `regex_audit/run_filter_replay.py` and `regex_audit/filter_results/`  
**Profile**: General Project (Development Mode per ORIGINAL_REQUEST.md)  
**Verdict**: **CLEAN**

---

## 1. Observation

1. **Static AST Analysis & Network Inspection (`regex_audit/run_filter_replay.py`)**:
   - AST module inspection confirmed imports are restricted strictly to:
     `['sys', 'os', 'json', 're', 'pathlib.Path', 'typing.Optional', 'pandas', 'src.scraper.build_location_regex', 'src.scorer.matches_senior_title']`.
   - Zero networking, HTTP client, or LLM libraries (`requests`, `urllib.request`, `httpx`, `aiohttp`, `openai`, `anthropic`, `google-genai`) are imported or called.
   - Network lockdown test: `socket.socket.connect`, `socket.create_connection`, and `socket.getaddrinfo` were monkeypatched to immediately raise `RuntimeError("NETWORK ATTEMPT DETECTED!")`. The replay script executed end-to-end to completion with 0 exceptions, confirming zero network socket activity.

2. **Source Code Immutability (`src/scorer.py` and `src/scraper.py`)**:
   - `src/scorer.py`: Git diff is completely empty (`git diff src/scorer.py` returned code 0 with 0 lines). Timestamp on disk is `2026-09-12T16:41:15Z` (unaltered since weeks prior).
   - `src/scraper.py`: Last write timestamp is `2026-09-29T14:04:35Z` (modified during Phase 1 raw data collection for raw job callbacks). Zero modifications occurred during Phase 2 (started after 15:09Z).

3. **Replay Accounting & Integrity Identity**:
   - Total raw dataset records: 1,137 (`regex_audit/master_raw_dataset_2026-09-29.jsonl`).
   - Layer 1 outputs (`layer1_pandas_pass.jsonl` + `layer1_pandas_fail.jsonl`):
     - Pass survivors: 73
     - Dropped records: 1,064
     - Accounting identity: $73 + 1064 = 1137$ ($100\%$ accounted for, disjoint sets, full union).
   - Layer 2 outputs (`layer2_regex_pass.jsonl` + `layer2_regex_fail.jsonl`):
     - Pass survivors: 58
     - Dropped records: 15
     - Accounting identity: $58 + 15 = 73$ ($100\%$ accounted for across Layer 1 survivors, disjoint sets, full union).

4. **Deterministic Reproducibility & SHA256 Checksums**:
   Executing `python regex_audit/run_filter_replay.py` regenerated the exact outputs byte-for-byte with identical SHA256 checksums:
   - `layer1_pandas_pass.jsonl`: `28083702f890e92c9444f72c705b360d18f531ecc180772ac4fce6f03f6f78af`
   - `layer1_pandas_fail.jsonl`: `3f45339fc900823fb2216b868f487bf7bf2acf5c60d1eafc5cde6449e2bd1efd`
   - `layer2_regex_pass.jsonl`: `ca6a284d06483dacf77435d9bb6518f62bfe1703cb1e5ab07178c615bc295b8e`
   - `layer2_regex_fail.jsonl`: `aaf0e2a5f4204ea35951b13c3cba42a973682aea4283ab045e4ff11b374e41a7`

5. **Independent Re-computation Verification**:
   - Direct execution of `src.scorer` functions (`matches_senior_title`, `matches_out_of_scope_role`, `requires_3_plus_years`, `is_relevant_jd`) on all 73 Layer 1 survivors yielded 0 mismatches against `layer2_regex_pass.jsonl` and `layer2_regex_fail.jsonl`.
   - Independent re-implementation of Layer 1 pipeline evaluated against all 1,137 jobs yielded 0 mismatches in pass/fail decisions and rejection reasons against `layer1_pandas_pass.jsonl` and `layer1_pandas_fail.jsonl`.

---

## 2. Logic Chain

1. From Observation 1, the script contains no network/LLM dependencies and does not initiate socket connections during execution, satisfying the strict offline/deterministic requirement.
2. From Observation 2, `src/scorer.py` is entirely untouched (`git diff` clean), and `src/scraper.py` was not modified during this phase, satisfying the immutability constraint.
3. From Observation 3, the accounting identities $73 + 1064 = 1137$ and $58 + 15 = 73$ hold with 0 overlaps, satisfying complete dataset preservation without record dropping or synthetic record generation.
4. From Observation 4, re-running the replay pipeline reproduces byte-for-byte identical output files, proving that results are not pre-populated stubs or arbitrary non-deterministic outputs.
5. From Observation 5, independent evaluation using the actual functions in `src/scorer.py` and `src/scraper.py` replicates all decisions with 0 mismatches, proving that the outputs are genuine executions of the filtering logic rather than facade implementations or hardcoded lookup tables.
6. Therefore, the replay implementation meets all criteria for Development mode integrity.

---

## 3. Caveats

- `src/scraper.py` has uncommitted modifications dating back to Phase 1 (`2026-09-29T14:04:35Z`), which added `get_last_raw_jobs()` and raw job callbacks to enable the master dataset scrape. This was required for Phase 1 data collection and was not touched during Phase 2.
- No other caveats.

---

## 4. Conclusion

**Verdict: CLEAN**

The Phase 2 replay implementation in `regex_audit/run_filter_replay.py` and the artifacts in `regex_audit/filter_results/` are fully verified, genuine, deterministic, and free of any integrity violations, facade implementations, or network dependencies.

---

## 5. Verification Method

To independently reproduce the audit verification:

```bash
# 1. Verify file immutability
git diff src/scorer.py

# 2. Execute replay with network lockdown
python -c "
import socket
from regex_audit.run_filter_replay import run_filter_replay
def no_net(*a, **kw): raise RuntimeError('NETWORK DETECTED')
socket.socket.connect = no_net
socket.create_connection = no_net
socket.getaddrinfo = no_net
run_filter_replay()
print('Clean offline execution verified.')
"

# 3. Verify SHA256 checksums
python -c "
import hashlib
from pathlib import Path
d = Path('regex_audit/filter_results')
for f in ['layer1_pandas_pass.jsonl', 'layer1_pandas_fail.jsonl', 'layer2_regex_pass.jsonl', 'layer2_regex_fail.jsonl']:
    print(f, hashlib.sha256((d / f).read_bytes()).hexdigest())
"
```
