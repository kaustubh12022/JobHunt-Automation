# Reviewer & Adversarial Critic Report: Ground Truth & Evaluation Datasets

**Reviewer Agent**: `reviewer_gt_1`  
**Roles**: Reviewer, Adversarial Critic  
**Working Directory**: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_gt_1`  
**Parent Agent**: `orchestrator_1` (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Date**: 2026-09-29T15:55:00Z  
**Verdict**: **APPROVE**  

---

## Review Summary

**Verdict**: **APPROVE**

The ground truth dataset (`regex_audit/evaluation/ground_truth.jsonl`), false positive registry (`false_positives.jsonl`), false negative registry (`false_negatives.jsonl`), compiler script (`compile_ground_truth.py`), and test suite (`test_ground_truth.py`) have been independently audited, stress-tested, and verified. 
- All line counts, index ranges, and schema interfaces match specifications exactly.
- All 18 flagged discrepancies (8 False Positives and 10 False Negatives) have been cross-checked directly against the raw job descriptions and confirm authentic, verifiable rubric violations or omissions.
- Zero integrity violations were detected: no hardcoded facade implementations, no fabricated results, and no shortcuts.
- Production scoring code (`src/scorer.py`) remains completely untouched (0 git diffs).

---

## 1. Observation

### 1.1 Line Counts and Index Ordering
Direct inspection of files in `regex_audit/evaluation/`:
- `ground_truth.jsonl`: Exactly 1,137 non-empty lines.
- `false_positives.jsonl`: Exactly 8 non-empty lines.
- `false_negatives.jsonl`: Exactly 10 non-empty lines.
- Index sequentiality verification command:
  ```python
  indices = [json.loads(l)['job_index'] for l in open('regex_audit/evaluation/ground_truth.jsonl', encoding='utf-8')]
  assert indices == list(range(1137))
  ```
  Result: 1,137 indices strictly contiguous from 0 to 1136 with zero duplicates and zero gaps.

### 1.2 Schema Conformance
Every line across all three JSONL files was validated against the TypeScript interfaces defined in `spec_miner_survey_1/handoff.md` Section 3.2:
- `ground_truth.jsonl`: All 1,137 records contain `{job_index, id, title, company, location, expected_outcome, actual_outcome_layer1, actual_outcome_layer2, is_correct, flag_type, confidence, target_domain, notes}`. Field types, nullability, and enum constraints (`PASS`/`FAIL`, `high`/`medium`/`low`, `false_positive`/`false_negative`/`null`) hold on 100% of records.
- `false_positives.jsonl`: All 8 records contain `{job_index, id, title, company, actual_decision, expected_decision, issue_type, reason, which_filter_failed, root_cause, specific_pattern_issue}`.
- `false_negatives.jsonl`: All 10 records contain `{job_index, id, title, company, actual_decision, expected_decision, issue_type, reason, which_filter_rejected, rejection_layer, root_cause, specific_pattern_issue}`.

### 1.3 Confusion Matrix & Accounting Invariants
- `TP` (`expected_outcome == PASS` and `actual_outcome_layer2 == PASS`): 50
- `TN` (`expected_outcome == FAIL` and `actual_outcome_layer2 == FAIL`): 1,069
- `FP` (`expected_outcome == FAIL` and `actual_outcome_layer2 == PASS`): 8
- `FN` (`expected_outcome == PASS` and `actual_outcome_layer2 == FAIL`): 10
- Sum: $50 + 1069 + 8 + 10 = 1,137$
- Replay concordance:
  - Baseline Layer 2 pass count: $50 + 8 = 58$ (`regex_audit/filter_results/layer2_regex_pass.jsonl` contains exactly 58 lines).
  - Baseline Layer 2 fail count: $1069 + 10 = 1,079$ ($1137 - 58 = 1079$).
  - Baseline pipeline accuracy against ground truth: $\frac{50 + 1069}{1137} = 98.42\%$.

### 1.4 Verbatim Verification of the 18 Flagged Cases
Each flagged job was verified against the corresponding record in `regex_audit/master_raw_dataset_2026-09-29.jsonl`:

#### False Positives (8 jobs):
1. **Job 336** (`Advanced Engineer Quality`, Albertsons): Description explicitly requires: `* Uphold quality standards and mentor junior team members on testing practices and engineering excellence` and `* Contribute to hiring activities, team collaboration, and knowledge sharing`. Senior IC role missed by title filter.
2. **Job 456** (`Quality Engineer`, Accenture): Description header states: `Career Level 7 | Test Architecture •Automation • GenAI• Agentic Testing... We are looking for a hands-on Quality Engineering Manager to lead engineering teams... coaching senior engineers`. Senior managerial level disguised by generic title.
3. **Job 510** (`Java Software Engineer`, Wissen): Description states: `Required Experience: 2-5`. Lower bound 2, upper bound 5 (violates rubric ceiling of 0-2 / 1-3 years).
4. **Job 513** (`Technical Consultant (Java Developer)`, Infios): Description states: `* At least five years of experience working with OMS or distributed commerce systems`. Word-form number bypassed regex.
5. **Job 563** (`IN_Associate_Saviynt _GCC_Advisory_Bangalore`, PwC): Description states: `Years of Experience required:\n\n 4`. Multiline format bypassed regex.
6. **Job 752** (`Product Definition Analyst 3`, Amadeus): Non-developer airline functional business analysis role; terminal tier `3` missed by title regex.
7. **Job 796** (`Software Engineer, AVP`, NatWest): Description states: `We're offering this role at associate vice president level`. Executive acronym `AVP` missed by title filter.
8. **Job 1038** (`Fullstack Python Engineer`, Azuga): Description states: `* At least 3 years of experience working with React`. Over-eager third-party prefix regex mistakenly stripped candidate qualification sentence.

#### False Negatives (10 jobs):
1. **Job 18** (`Associate - QA Automation`, Davies): Associate QA role rejected on company history `Over the past ten years Davies has grown its annual revenues more than 20-fold`.
2. **Job 84** (`Java or Kotlin & React.js Developer`, Capgemini): Full-stack Java+React role rejected because `OUT_OF_SCOPE_STACK_PATTERN` matched `kotlin` mentioned as alternative JVM backend language.
3. **Job 119** (`ASP.Net MVC Developer`, Domex): Entry-level 1-2 years ASP.NET role rejected because `requires_3_plus_years` matched candidate age qualification `(27 to 40 Yrs)`.
4. **Job 169** (`Software Engineer - AI & Product | Fast-Track to Tech Lead`, Datastraw): Entry-level AI & Product role (1-3 yrs experience) rejected on growth pathway subtitle `Fast-Track to Tech Lead`.
5. **Job 220** (`Full Stack Developer Intern`, PopPop Labs): Pune intern role (React, Node, Express, Python, RAG) rejected on peripheral mention of optional `Flutter`.
6. **Job 246** (`Full Stack Developer`, COMMANDO): Entry-level MERN/React/Node/MongoDB developer rejected as irrelevant because `DOMAIN_ANCHORS` omitted React/Node/MERN.
7. **Job 466** (`Associate - QA Automation`, Davies): Associate QA role rejected on company history `ten years`.
8. **Job 687** (`ASP.Net MVC Developer`, Domex): Entry-level 1-2 years ASP.NET role rejected on candidate age qualification `(27 to 40 Yrs)`.
9. **Job 722** (`Quality Assurance Engineer`, Scoutit): Entry-level QA role rejected because `matches_out_of_scope_role` matched `Salesforce` listed under "Good to Have".
10. **Job 1027** (`Software Engineer – Full Stack (.NET/React)`, DYMATRIX): Entry-level .NET/React SWE rejected on company history `With over 20 years of experience, DYMATRIX is...`.

### 1.5 Audit of All 50 True Positives
All 50 True Positive jobs were inspected for title, company, location, domain, and experience:
- All 50 belong to target domains: Java Backend (9), Full Stack SWE (13), QA Automation/Testing (14), .NET/C# (6), Python Backend (4), MERN Stack (1), AI/ML (3).
- All 50 are located in valid target regions: MH (Mumbai/Pune), KA (Bengaluru), or Remote.
- None have senior titles or require 3+ years experience.

### 1.6 Production Code Immutability
- Command: `git diff --stat src/scorer.py`
  Result: 0 diff lines (completely untouched).
- `compile_ground_truth.py` does not modify any source code files.

### 1.7 Automated Test Execution
- Command: `python -m pytest regex_audit/test_ground_truth.py`
  Result: 6 passed in 0.19s.

---

## 2. Logic Chain

1. From Observation 1.1, `ground_truth.jsonl` contains all 1,137 jobs with continuous indices 0..1136, satisfying the complete coverage requirement without missing or duplicate rows.
2. From Observation 1.2, all fields, types, and values adhere to the data schemas established in `spec_miner_survey_1/handoff.md`.
3. From Observation 1.3, the confusion matrix elements ($50 + 1069 + 8 + 10 = 1137$) and replay counts ($50 + 8 = 58$ L2 passes) maintain strict mathematical consistency with the replayed filter artifacts.
4. From Observation 1.4, every single one of the 8 False Positives and 10 False Negatives was verified against the verbatim raw text. The justifications correctly apply the candidate profile rubric rules regarding experience boundaries, senior titles, out-of-scope technologies, and domain anchors.
5. From Observation 1.5, independent audit of all 50 True Positives verified zero false inclusions.
6. From Observation 1.6 and 1.7, production code is immutable, the compilation is deterministic, and all 6 test suites pass cleanly.
7. Therefore, the ground truth dataset and evaluation artifacts are mathematically sound, semantically accurate, and ready for use in subsequent phases.

---

## 3. Caveats & Adversarial Findings

1. **Duplicate Pairs Among False Negatives (Job 18/466 and Job 119/687)**:
   - Job 18 and Job 466 share the identical URL (`https://in.indeed.com/viewjob?jk=b56691592fc0e64f`).
   - Job 119 and Job 687 share the identical URL (`https://in.indeed.com/viewjob?jk=f3804a1110bfda36`).
   - In the baseline run, both 466 and 687 were rejected at `requires_3_plus_years` (Step 5) *before* Layer 1 deduplication (Step 6) could evaluate them.
   - At the individual filter level, classifying both 466 and 687 as False Negatives of `requires_3_plus_years` is accurate because the experience regex failed on them.
   - *Adversarial note for Phase 6/7:* If `run_retest.py` evaluates the entire Layer 1 pipeline including deduplication, Job 466 and Job 687 will be dropped as duplicates by Step 6 deduplication once `requires_3_plus_years` is fixed. When evaluating `scorer_v2.py` standalone at the scorer function level, both 466 and 687 will evaluate to `PASS`, matching `ground_truth.jsonl`. This distinction must be preserved during retest harness construction.
2. **Job 1035 Target Domain (`Forward Deployed Engineer - India` at Cursor)**:
   - Field `target_domain` is `null`, which is valid under `target_domain: string | null`. The notes clearly document it as an AI Forward Deployed Engineer role (Python, TypeScript, AI workflows).
3. **Immutability Scope**:
   - `src/scorer.py` has 0 git diffs and is pristine. `src/scraper.py` has pre-existing uncommitted modifications from Phase 1 data collection (`2026-09-29T14:04:35Z` UTC) which were untouched during evaluation.

---

## 4. Conclusion

**Verdict: APPROVE**

The work product delivered by `worker_gt_builder` and the evaluator agents satisfies all requirements and quality gates:
1. `regex_audit/evaluation/ground_truth.jsonl`: 1,137 records, indexed 0..1136 sequentially, 100% schema compliance.
2. `regex_audit/evaluation/false_positives.jsonl`: 8 authentic False Positives with accurate root causes and regex pattern issues.
3. `regex_audit/evaluation/false_negatives.jsonl`: 10 authentic False Negatives with accurate root causes, rejection layers, and regex pattern issues.
4. `regex_audit/compile_ground_truth.py`: Fully deterministic, offline, and reproducible.
5. All 6 automated test suites in `regex_audit/test_ground_truth.py` pass.

The ground truth dataset is officially approved. The orchestrator may proceed to Phase 5 (Regex Audit Report) and Phase 6/7 (Scorer v2 rewrite).

---

## 5. Verification Method

To independently verify this review:

1. **Run Ground Truth Test Suite**:
   ```powershell
   python -m pytest regex_audit/test_ground_truth.py
   # Expected: 6 passed in ~0.20s
   ```

2. **Verify Line Counts & Sequential Indices**:
   ```powershell
   python -c "import json; gt = [json.loads(l) for l in open('regex_audit/evaluation/ground_truth.jsonl', encoding='utf-8')]; fp = [json.loads(l) for l in open('regex_audit/evaluation/false_positives.jsonl', encoding='utf-8')]; fn = [json.loads(l) for l in open('regex_audit/evaluation/false_negatives.jsonl', encoding='utf-8')]; assert len(gt) == 1137; assert len(fp) == 8; assert len(fn) == 10; assert [r['job_index'] for r in gt] == list(range(1137)); print('All counts and indices verified successfully!')"
   ```

3. **Verify Production Scorer Immutability**:
   ```powershell
   git diff src/scorer.py
   # Expected: Clean (0 diffs)
   ```
