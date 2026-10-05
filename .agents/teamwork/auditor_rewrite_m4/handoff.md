# Forensic Audit Handoff Report: Milestone 4 Scorer V2 Implementation

**Work Product**: `regex_audit/scorer_v2.py`, `src/scorer.py`, `src/scraper.py`  
**Profile**: General Project (Development Mode per `ORIGINAL_REQUEST.md`)  
**Auditor**: `auditor_rewrite_m4`  
**Parent**: `orchestrator_1` (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Date**: 2026-09-29T16:48:00Z  
**Verdict**: **CLEAN**

---

## Forensic Audit Summary

### Phase Results
- **Check 1 (Static AST Code Analysis for Cheats & Hardcoding)**: **PASS** — Complete AST traversal confirmed zero hardcoded job IDs (e.g. 336, 456, 510, etc.), zero dataset indices/row numbers, zero company name lookups in executable code, zero full-title exact match branches, and zero artificial if/else branching. The sole occurrence of the word "accenture" is within a docstring comment (`line 156`), with the underlying code executing a generalized career-level regex (`r'\bcareer\s+level\s+[1-7]\b.*?(?:manager|leadership|lead\s+engineering)'`).
- **Check 2 (Network & LLM Zero-Dependency Verification)**: **PASS** — AST traversal of imports and calls confirmed strictly zero network/API dependencies. No imports of `requests`, `urllib`, `httpx`, `aiohttp`, `socket`, `openai`, `google.generativeai`, `groq`, `anthropic`, or `langchain`. Only Python standard libraries (`re`, `json`, `typing`), local utility modules (`src.config_loader`, `src.scraper`), and `pandas` are imported.
- **Check 3 (Production Baseline Immutability)**: **PASS** — `src/scorer.py` is 100% clean and unmodified (`git diff HEAD src/scorer.py` yields zero lines; last write time remains `2026-09-12T16:41:15Z` UTC). `src/scraper.py` was untouched during Milestone 4 (last write timestamp remains `2026-09-29T14:04:35Z` UTC from Phase 1 data collection).
- **Check 4 (Authentic & Generalized Regex Logic)**: **PASS** — All filters (`matches_senior_title`, `requires_3_plus_years`, `matches_out_of_scope_role`, `is_relevant_jd`) implement authentic, generalized, reusable regex patterns and boundary checks.
- **Check 5 (Empirical Test Suite Execution)**: **PASS** — `pytest -v regex_audit/test_scorer_v2.py` executed with **23 passed in 0.55s**.
- **Check 6 (Discrepancy Resolution & Zero Regressions)**: **PASS** — Verified all 8 baseline False Positives evaluate to FAIL (100.0%), all 10 baseline False Negatives evaluate to PASS (100.0%), and all 50 baseline True Positives continue to PASS with zero regressions (100.0%).

---

## 1. Observation

1. **Static AST Analysis of `regex_audit/scorer_v2.py`**:
   Executing AST inspection across the full module:
   ```python
   # Script: AST walk for imports, constant strings, numbers, attribute accesses, and function calls
   ```
   Direct output:
   - **Imports**: `['json', 're', 'typing', 'src.scraper', 'pandas', 'src.config_loader']` (zero network/LLM packages).
   - **Found Companies in Strings**: The only match across all discrepancy companies (`azuga`, `albertsons`, `accenture`, `wissen`, `infios`, `pwc`, `amadeus`, `natwest`, `dymatrix`, `domex`, `datastraw`, `davies`, `poppop`, `commando`, `scoutit`, `capgemini`) was:
     ```text
     [('accenture', "\n    Returns True if job title indicates a senior/lead/managerial role or\n    explicitly requires >= 3 years of experience in the title.\n    Preserves genuine entry-level, junior, associate, graduate, trainee, and 0-2 / 1-3 year jobs.\n\n    V2 Enhancements:\n    - Masks career progression suffixes (e.g. 'Fast-Track to Tech Lead').\n    - Recognizes AVP, Associate Vice President, and Advanced Engineer tiers.\n    - Matches terminal senior digit tiers (e.g. 'Analyst 3', 'Engineer 2').\n    - Checks description header for disguised managerial career levels (Accenture Level 7).\n    ", 147)]
     ```
     The code implementation itself at line 209 uses:
     ```python
     re.search(r'\bcareer\s+level\s+[1-7]\b.*?(?:manager|leadership|lead\s+engineering)', first_1000, re.DOTALL)
     ```
     which is a generalized pattern matching any company's career levels 1-7.
   - **Found Job IDs in String Constants**: `[]` (None).
   - **Found Numeric Job IDs in AST Constants**: `[]` (None).
   - **All Numeric Constants in Code**: `[False, True, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 25, 72, 1000]`.
     - `2`: `MIN_KEYWORD_MATCHES`, short abbreviation length boundary (`len(kw) <= 2`), tier regex `level\s*[2-9]`.
     - `3-12`: Numerical mapping dictionary `words_to_num_all` (`'three': 3` ... `'twelve': 12`).
     - `20`: Word context window for degree exclusion `m.start()-20`.
     - `25`: Age boundary filter (`lo >= 25 or hi >= 25`) to ignore candidate age specifications.
     - `72`: Default freshness cutoff (`hours_old = 72`).
     - `1000`: Header character slice (`description[:1000]`).
   - **Attribute Accesses**: `['DOTALL', 'I', 'IGNORECASE', 'Timedelta', 'Timestamp', '__getitem__', '__init__', 'all_scored_jobs', 'append', 'compile', 'end', 'escape', 'finditer', 'get', 'group', 'isdigit', 'join', 'keys', 'lower', 'notna', 'now', 'replace', 'search', 'split', 'start', 'strip', 'sub', 'super', 'to_datetime']` — strictly standard library and pandas methods; zero access to `job.id`, `job.company`, `job.url`, etc.
   - **`getattr` Invocations**:
     - Line 452: `getattr(job, 'date_posted', None)`
     - Line 468: `getattr(job, 'title', '')`
     - Line 469: `getattr(job, 'description', '')`
   - **Subscript Keys**: `[]` (no dictionary literal lookups by job ID or index).

2. **Baseline File Immutability (`src/scorer.py` and `src/scraper.py`)**:
   - Running `git diff HEAD src/scorer.py`:
     ```text
     (Exit code 0, 0 lines output)
     ```
   - Running file timestamp query:
     ```text
     Name         LastWriteTime
     ----         -------------
     scorer.py    12-09-2026 22:11:15 (UTC: 2026-09-12T16:41:15Z)
     scraper.py   29-09-2026 19:34:35 (UTC: 2026-09-29T14:04:35Z)
     scorer_v2.py 29-09-2026 22:09:59 (UTC: 2026-09-29T16:39:59Z)
     ```
   - `src/scorer.py` is pristine with 0 modifications.
   - `src/scraper.py` has uncommitted modifications dating exclusively to Phase 1 data collection (`2026-09-29T14:04:35Z` UTC) for raw job telemetry collection. It was completely untouched during Milestone 4.

3. **Empirical Unit Test Execution (`regex_audit/test_scorer_v2.py`)**:
   - Command: `pytest -v regex_audit/test_scorer_v2.py`
     ```text
     ============================= test session starts =============================
     platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
     rootdir: C:\Users\kalek\Desktop\Projects\Job_Hunt
     collected 23 items

     regex_audit/test_scorer_v2.py::TestFalsePositives::test_all_8_false_positives_fail PASSED [  4%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_1038_azuga_candidate_skill_experience PASSED [  8%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_336_albertsons_advanced_engineer PASSED [ 13%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_456_accenture_career_level_7 PASSED [ 17%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_510_wissen_experience_range PASSED [ 21%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_513_infios_word_numeral_experience PASSED [ 26%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_563_pwc_multiline_experience PASSED [ 30%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_752_amadeus_terminal_digit PASSED [ 34%]
     regex_audit/test_scorer_v2.py::TestFalsePositives::test_fp_job_796_natwest_avp PASSED [ 39%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_all_10_false_negatives_pass PASSED [ 43%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_1027_dymatrix_company_heritage PASSED [ 47%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_119_and_687_domex_age_bracket PASSED [ 52%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_169_datastraw_fast_track_lead PASSED [ 56%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_18_and_466_davies_company_growth PASSED [ 60%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_220_poppop_fullstack_flutter PASSED [ 65%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_246_commando_mern_markdown PASSED [ 69%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_722_scoutit_qa_salesforce PASSED [ 73%]
     regex_audit/test_scorer_v2.py::TestFalseNegatives::test_fn_job_84_capgemini_jvm_kotlin PASSED [ 78%]
     regex_audit/test_scorer_v2.py::TestBaselineTruePositives::test_all_50_baseline_true_positives_pass PASSED [ 82%]
     regex_audit/test_scorer_v2.py::TestStandaloneFunctionUnits::test_is_relevant_jd_anchors_and_tools PASSED [ 86%]
     regex_audit/test_scorer_v2.py::TestStandaloneFunctionUnits::test_matches_out_of_scope_role_scoping PASSED [ 91%]
     regex_audit/test_scorer_v2.py::TestStandaloneFunctionUnits::test_requires_3_plus_years_boundaries PASSED [ 95%]
     regex_audit/test_scorer_v2.py::TestStandaloneFunctionUnits::test_senior_title_boundaries PASSED [100%]

     ============================= 23 passed in 0.55s ==============================
     ```

4. **Independent Discrepancy & Regression Verification**:
   Running isolated verification script on all 18 discrepancy jobs directly from raw text:
   ```text
   TESTING 8 FALSE POSITIVES IN SCORER V2:
   Job 336: passed=False
   Job 456: passed=False
   Job 510: passed=False
   Job 513: passed=False
   Job 563: passed=False
   Job 752: passed=False
   Job 796: passed=False
   Job 1038: passed=False

   TESTING 10 FALSE NEGATIVES IN SCORER V2:
   Job 18: passed=True
   Job 84: passed=True
   Job 119: passed=True
   Job 169: passed=True
   Job 220: passed=True
   Job 246: passed=True
   Job 466: passed=True
   Job 687: passed=True
   Job 722: passed=True
   Job 1027: passed=True
   ```
   Combined Pipeline Accuracy (Layer 1 + Scorer V2 vs Ground Truth across all 1,137 jobs):
   - **Matches**: 1,131 / 1,137 (**99.47%**)
   - Substantially exceeds the **95.0%** threshold.

---

## 2. Logic Chain

1. **Baseline Immutability**: `git diff HEAD src/scorer.py` produced 0 output, proving `src/scorer.py` has had zero lines altered. `src/scraper.py` retains its modification timestamp from Phase 1 data collection (`14:04:35Z`), confirming Milestone 4 made zero edits to either baseline production file (Obs 2).
2. **Authenticity of Implementation**: AST parsing demonstrated that `regex_audit/scorer_v2.py` does not contain any lookup tables, hardcoded job IDs, row index mappings, or company checks. All logic consists of generalized regular expressions, string parsing, and boundary evaluations (Obs 1).
3. **Absence of Prohibited Patterns**:
   - Zero hardcoded test results: No hardcoded booleans or conditional results tied to specific test inputs.
   - Zero facade implementations: Functions perform genuine string cleaning, sentence segmentation, regex compilation, and range evaluation.
   - Zero network delegation: Zero HTTP or LLM API calls; execution is 100% local and deterministic (Obs 1).
4. **Empirical Correctness**: The 23 unit tests in `regex_audit/test_scorer_v2.py` pass without errors or warnings. Direct verification of the 18 discrepancy jobs confirmed 8/8 False Positives are rejected and 10/10 False Negatives are accepted, with 50/50 baseline True Positives preserved (Obs 3, 4).
5. **Conclusion**: The deliverable `regex_audit/scorer_v2.py` is certified as an authentic, high-integrity, deterministic implementation.

---

## 3. Caveats

1. **Pre-existing Phase 1 Changes in `src/scraper.py`**:
   `src/scraper.py` contains uncommitted changes dating back to Phase 1 data collection (`2026-09-29T14:04:35Z` UTC) that introduced `get_last_raw_jobs()` and raw job callbacks to collect the 1,137 raw jobs. No modifications were made during Milestone 4.
2. **Challenger Adversarial Fuzzing Observations**:
   In adversarial stress testing conducted by challenger agent (`test_challenger_m4.py`), non-string types passed to `matches_out_of_scope_role` or `is_relevant_jd` (such as integer `12345`) raise `AttributeError` because `.lower()` is called on truthy values without checking `isinstance(val, str)`. This is a defensive programming consideration for untyped environments rather than an integrity violation; in normal production, titles and descriptions are strings.
3. **No caveats** regarding forensic integrity, cheating, or hardcoding.

---

## 4. Conclusion

**Verdict: CLEAN**

`regex_audit/scorer_v2.py` satisfies all forensic integrity criteria under Development Mode.
- Zero hardcoded answers, job IDs, or index cheats.
- Zero network or LLM dependencies.
- `src/scorer.py` and `src/scraper.py` remain strictly preserved.
- All filter logic is genuine, generalized, and reusable regex.
- All 18 discrepancy jobs are resolved (100.0%) and baseline True Positives have 0 regressions.

Milestone 4 is certified **CLEAN**.

---

## 5. Verification Method

To independently reproduce this forensic audit:

1. **Verify Baseline Immutability**:
   ```powershell
   git diff HEAD src/scorer.py
   powershell -Command "Get-Item src\scorer.py, src\scraper.py | Select-Object Name, LastWriteTime"
   ```

2. **Verify AST and Absense of Cheats**:
   ```powershell
   python -c "import ast; tree = ast.parse(open('regex_audit/scorer_v2.py').read()); print([n.name for n in ast.walk(tree) if isinstance(n, ast.Import)])"
   ```

3. **Run Scorer V2 Unit Test Suite**:
   ```powershell
   pytest -v regex_audit/test_scorer_v2.py
   ```

4. **Verify Direct Discrepancy Resolution**:
   ```powershell
   python -c "import json, regex_audit.scorer_v2 as s; ds = [json.loads(l) for l in open('regex_audit/master_raw_dataset_2026-09-29.jsonl', encoding='utf-8') if l.strip()]; print('FP (all False):', [not s.matches_senior_title(ds[i]['title'], ds[i]['description']) and not s.requires_3_plus_years(ds[i]['description']) and not s.matches_out_of_scope_role(ds[i]['title'], ds[i]['description']) and s.is_relevant_jd(ds[i]['description'], ds[i]['title']) for i in [336, 456, 510, 513, 563, 752, 796, 1038]]); print('FN (all True):', [not s.matches_senior_title(ds[i]['title'], ds[i]['description']) and not s.requires_3_plus_years(ds[i]['description']) and not s.matches_out_of_scope_role(ds[i]['title'], ds[i]['description']) and s.is_relevant_jd(ds[i]['description'], ds[i]['title']) for i in [18, 84, 119, 169, 220, 246, 466, 687, 722, 1027]])"
   ```
