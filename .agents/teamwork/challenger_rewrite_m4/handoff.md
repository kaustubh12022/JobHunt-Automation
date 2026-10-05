# Empirical Challenger Stress Report & Handoff (Milestone 4)

**Author:** `challenger_rewrite_m4`  
**Roles:** Critic, Specialist  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\challenger_rewrite_m4`  
**Parent Agent:** `orchestrator_1` (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Target:** `regex_audit/scorer_v2.py`  
**Test Suites:** `regex_audit/test_scorer_v2.py`, `regex_audit/test_challenger_m4.py`  
**Date:** 2026-09-29T16:51:00Z  
**Verdict:** **`APPROVE`**

---

## Challenge Summary

**Overall Risk Assessment:** **LOW**  
The deterministic filter rewrite in `regex_audit/scorer_v2.py` is empirically robust, mathematically consistent with the ground-truth specification, completely free of AI/LLM API calls, and preserves 100% baseline immutability (`src/scorer.py` has 0 diffs). It achieves **99.82% overall pipeline accuracy** (1,135 / 1,137 jobs matching `ground_truth.jsonl`), **100.0% accuracy on Layer 1 survivors** (73 / 73), eliminates all 8 False Positives, rescues all 10 False Negatives, and introduces **zero regressions** across the 50 baseline True Positives. 

Two minor adversarial edge cases (non-string type vulnerability in `matches_out_of_scope_role`/`is_relevant_jd`, and boilerplate-only fallback behavior in `strip_boilerplate`) along with a latency optimization recommendation for raw un-prefiltered inputs are documented below with concrete mitigations. None of these impact the production pipeline where inputs are pre-validated strings and Layer 2 processes only Layer 1 survivors in **0.33 seconds** (< 2.0s budget).

---

## 1. Observation

All stress tests, benchmarks, and regression checks were executed empirically in Python 3.13.15 on Windows 11 using `regex_audit/test_scorer_v2.py` and `regex_audit/test_challenger_m4.py`.

### 1.1 Automated Test Suite Execution
- **Command:** `python -m pytest regex_audit/test_scorer_v2.py -v`
- **Output:**
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
  ============================= 23 passed in 0.58s ==============================
  ```

### 1.2 Quantitative Ground Truth Agreement
Executing Two-Layer replay with Scorer V2 against `regex_audit/evaluation/ground_truth.jsonl`:
- **Total Master Raw Dataset Records:** 1,137 jobs.
- **Agreement:** 1,135 / 1,137 (**99.82%**), exceeding the required >= 95.0% threshold.
- **Discrepancies:** Exactly 2 jobs (Job 466 and Job 687).
  - Ground truth notes indicate Job 466 is an identical duplicate of Job 18 (Davies), and Job 687 is an identical duplicate of Job 119 (Domex).
  - In isolated single-job evaluation, 10/10 False Negatives pass (100.0%).
  - In sequential dataset evaluation, Layer 1 Pass 6b correctly drops the duplicate second posting, leaving 58 valid passing survivors.
- **Layer 1 Survivors Agreement:** 73 / 73 (**100.0%**), exactly 0 discrepancies on all jobs entering Layer 2.
- **Baseline True Positives:** 50 / 50 (**100.0%**), zero regressions detected.
- **Baseline False Positives:** 8 / 8 (**100.0%**), all 8 fail as expected.
- **Baseline False Negatives:** 10 / 10 (**100.0%**), all 10 pass as expected.

### 1.3 Throughput & Latency Benchmarks
- **Production Layer 1 Survivors (73 jobs):**
  - Time: **0.3325 seconds** (~4.55 ms/job). Well under the 2.0-second requirement.
- **Full 1,137 Un-prefiltered Jobs (`score_jobs` synchronous filter):**
  - Time: **3.1787 seconds** (~2.79 ms/job).
  - Profiling individual functions on full 1,137 un-prefiltered jobs:
    - `matches_senior_title`: **0.0706s** (instantaneous)
    - `requires_3_plus_years`: **3.8042s** (sentence splitting + 18 uncompiled regex searches per sentence)
    - `matches_out_of_scope_role`: **1.9163s**
    - `is_relevant_jd`: **1.6912s**
- **Prototype Optimization with Single Precompiled Regex:**
  - Combining the 18 third-party prefixes into a single pre-compiled pattern `re.compile('|'.join(...))` reduced `requires_3_plus_years` execution time across all 1,137 jobs from 3.8042s down to **1.3560s** (a 64.3% speedup).

### 1.4 Catastrophic Backtracking (ReDoS) Fuzzing
Massive adversarial payloads were tested against all regex patterns in `scorer_v2.py`:
- 100KB Boilerplate repetition: `strip_boilerplate` took **0.0031s**, `requires_3_plus_years` took **0.0152s**.
- 500KB Dash/Number repetition: `requires_3_plus_years` took **0.0480s**.
- 1MB Text body: `requires_3_plus_years` took **0.5663s**, linear O(N) scaling, zero hangs, zero recursion depth errors.
- Unclosed markdown backticks (500 chars), deeply nested parentheses (`(` * 200), null bytes (`\x00`), and zero-width spaces (`\u200b` * 100) all returned cleanly without exceptions.

### 1.5 Adversarial Edge Case Vulnerabilities Identified
1. **Type Coercion Issue**: In `matches_out_of_scope_role` (lines 109, 118) and `is_relevant_jd` (line 369), the code uses `title.lower() if title else ""`. When an integer (e.g. `12345`) or non-string object is passed, it triggers `AttributeError: 'int' object has no attribute 'lower'`. (In contrast, `matches_senior_title` and `requires_3_plus_years` guard with `isinstance(..., str)`).
2. **`strip_boilerplate` Idiom Defect**: At line 399 of `scorer_v2.py`:
   ```python
   return cleaned if cleaned else description
   ```
   When `description` consists entirely of boilerplate or whitespace, `cleaned.strip()` evaluates to `""` (falsy). The fallback expression `cleaned if cleaned else description` returns the original unstripped text rather than `""`.

### 1.6 Production Baseline Immutability
- `git diff src/scorer.py` yields zero lines.
- `src/scorer.py` remains 100% untouched.

---

## 2. Logic Chain

1. **Accuracy Criteria Evaluation (Obs 1.1, 1.2)**: `ORIGINAL_REQUEST.md` R5 mandates >= 95.0% agreement against `ground_truth.jsonl` and zero regressions on baseline true positives. Direct execution of the full two-layer pipeline achieves 99.82% agreement (1,135/1,137). On the 73 jobs reaching Layer 2, accuracy is 100.0%. All 50 baseline True Positives pass without regressions.
2. **Discrepancy Remediation (Obs 1.1, 1.2)**: All 8 baseline False Positives are confirmed to evaluate to FAIL, and all 10 baseline False Negatives are confirmed to evaluate to PASS.
3. **Execution Latency Evaluation (Obs 1.3)**: In the actual production workflow, Layer 2 executes exclusively on Layer 1 survivors (73 jobs). This takes 0.33 seconds, well under the 2.0-second latency ceiling. On raw un-prefiltered jobs, `score_jobs` takes 3.18 seconds, which is safely non-blocking and can be further accelerated via pattern precompilation.
4. **ReDoS Resilience Evaluation (Obs 1.4)**: Extreme payloads up to 1MB demonstrate linear scaling and total resistance to polynomial/exponential catastrophic backtracking.
5. **Adversarial Safety Evaluation (Obs 1.5)**: Non-string type crashes in `matches_out_of_scope_role` and `is_relevant_jd` are low-risk in production because upstream scraping/pandas pipelines strictly supply string fields (`str(row['title'])`). The `strip_boilerplate` fallback anomaly does not affect filter decisions because filtering does not rely on `strip_boilerplate`.
6. **Integrity & Immutability (Obs 1.6)**: Baseline `src/scorer.py` is completely untouched. Zero LLM or external API dependencies exist in `scorer_v2.py`.

---

## 3. Challenges & Mitigations

### [Medium] Challenge 1: Type Safety on Non-String Inputs
- **Assumption Challenged:** Function arguments are always `str` or `None`.
- **Attack Scenario:** A caller or broken scraper passes an integer job ID or dict into `matches_out_of_scope_role(12345, 12345)` or `is_relevant_jd("desc", 12345)`.
- **Blast Radius:** Unhandled `AttributeError: 'int' object has no attribute 'lower'` halts batch execution.
- **Mitigation:** Update lines 109, 118, 369 to add explicit string guards:
  ```python
  title_clean = title.lower() if isinstance(title, str) else ""
  desc_lower = description.lower() if isinstance(description, str) else ""
  ```

### [Low] Challenge 2: Boilerplate Stripping Fallback Defect
- **Assumption Challenged:** `strip_boilerplate` returns stripped text or empty string when everything is stripped.
- **Attack Scenario:** A job description consisting exclusively of "About Us..." boilerplate is passed to `strip_boilerplate`.
- **Blast Radius:** Returns the unstripped boilerplate unchanged instead of empty string, wasting LLM tokens if used downstream for resume generation.
- **Mitigation:** Change line 399 in `strip_boilerplate`:
  ```python
  return cleaned  # Return cleaned string directly, not fallback to description
  ```

### [Low] Challenge 3: Uncompiled Regex Loop in `requires_3_plus_years`
- **Assumption Challenged:** Calling `re.search` on 18 raw strings per sentence is fast enough for bulk processing.
- **Attack Scenario:** Processing batches of 10,000+ jobs without Layer 1 pre-filtering takes > 30 seconds.
- **Blast Radius:** Increased CPU time on large datasets.
- **Mitigation:** Precompile the 18 third-party prefixes into a single module-level regex `COMBINED_THIRD_PARTY_PATTERN = re.compile('|'.join(THIRD_PARTY_PATTERNS))`, which cuts execution time by 64.3%.

---

## 4. Caveats

- **Deduplication Accounting in Pipeline**: Jobs 466 and 687 differ between ground truth expected outcome ('PASS') and two-layer pipeline outcome ('FAIL') solely because they are duplicate postings of earlier jobs (Job 18 and Job 119) and are legitimately dropped by Layer 1 deduplication. In standalone execution, both evaluate to PASS.
- **Review-Only Constraint Maintained**: Per agent instructions, the implementation code in `regex_audit/scorer_v2.py` was NOT modified by this agent. The vulnerabilities identified in Section 3 are submitted as findings/recommendations.

---

## 5. Conclusion

**Verdict: `APPROVE`**

`regex_audit/scorer_v2.py` satisfies all quantitative acceptance criteria specified in `ORIGINAL_REQUEST.md` and `DISPATCH.md`:
1. **Accuracy**: 99.82% overall two-layer agreement (1,135/1,137) and 100.0% Layer 1 survivor agreement (73/73), far surpassing the >= 95.0% threshold.
2. **Zero Regressions**: 50/50 baseline True Positives continue to pass without a single regression.
3. **Discrepancy Fixes**: All 8 False Positives fail and all 10 False Negatives pass.
4. **Latency**: Production flow (Layer 1 survivors) processes in 0.33 seconds (< 2.0s budget).
5. **ReDoS Resilience**: Verified linear performance across 100KB, 500KB, and 1MB payloads.
6. **Code Safety**: 100% deterministic local Python standard library regex; zero external network or LLM API calls; `src/scorer.py` remains completely untouched.

---

## 6. Verification Method

To independently reproduce all empirical findings:

1. **Run the Official Unit Test Suite:**
   ```powershell
   python -m pytest regex_audit/test_scorer_v2.py -v
   ```
   *Expected: 23 passed in < 1.0s.*

2. **Run the Challenger Empirical Stress Suite:**
   ```powershell
   python -m pytest regex_audit/test_challenger_m4.py -v
   ```
   *Expected: 10 passed in ~4.3s.*

3. **Verify Baseline Immutability:**
   ```powershell
   git diff src/scorer.py
   ```
   *Expected: Zero lines output.*
