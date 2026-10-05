# Ground Truth Evaluation Dataset Validation — Handoff Report

**Role**: challenger_gt_1 (Ground Truth Challenger & Empirical Stress Tester)  
**Parent**: orchestrator_1 (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Verdict**: **APPROVE**  
**Timestamp**: 2026-09-29T15:53:00Z  

---

## 1. Observation

### 1.1 Automated Test Execution
- Executed command: `python -m pytest regex_audit/test_ground_truth.py`
- Result verbatim:
  ```
  ============================= test session starts =============================
  platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
  rootdir: C:\Users\kalek\Desktop\Projects\Job_Hunt
  plugins: anyio-4.15.0, platformdirs-4.12.1
  collected 6 items

  regex_audit\test_ground_truth.py ......                                  [100%]

  ============================== 6 passed in 0.19s ==============================
  ```
- All 6 test suites passed:
  1. `test_file_existence_and_counts`: GT=1137, FP=8, FN=10.
  2. `test_ground_truth_schema_and_indexing`: 0..1136 sequential, TP=50, TN=1069, FP=8, FN=10.
  3. `test_false_positives_dataset`: exact index set `{336, 456, 510, 513, 563, 752, 796, 1038}`.
  4. `test_false_negatives_dataset`: exact index set `{18, 84, 119, 169, 220, 246, 466, 687, 722, 1027}`.
  5. `test_fidelity_against_raw_and_replay`: 100% field fidelity against raw dataset and filter replay.
  6. `test_code_immutability`: zero diff on `src/scorer.py`.

### 1.2 Dataset Dimensions & Line Counts
- `regex_audit/master_raw_dataset_2026-09-29.jsonl`: exactly 1,137 non-empty JSON lines.
- `regex_audit/evaluation/ground_truth.jsonl`: exactly 1,137 non-empty JSON lines.
- `regex_audit/evaluation/false_positives.jsonl`: exactly 8 non-empty JSON lines.
- `regex_audit/evaluation/false_negatives.jsonl`: exactly 10 non-empty JSON lines.
- `regex_audit/filter_results/layer1_pandas_pass.jsonl`: 73 lines.
- `regex_audit/filter_results/layer1_pandas_fail.jsonl`: 1,064 lines (Sum = 1,137).
- `regex_audit/filter_results/layer2_regex_pass.jsonl`: 58 lines.
- `regex_audit/filter_results/layer2_regex_fail.jsonl`: 15 lines (Sum = 73).

### 1.3 1:1 Join and Field Fidelity Check
- Ran programmatic comparison between `master_raw_dataset_2026-09-29.jsonl` and `ground_truth.jsonl` for every index $i \in [0, 1136]$:
  - Exact match count on `id`: 1,137 / 1,137 (100.0%).
  - Exact match count on `title`: 1,137 / 1,137 (100.0%).
  - Exact match count on `company`: 1,137 / 1,137 (100.0%).
  - Exact match count on `location`: 1,137 / 1,137 (100.0%).
  - Exact match count on `job_index`: 1,137 / 1,137 (100.0%).
  - Field mismatches detected: **0**.

### 1.4 Partition and Confusion Matrix Verification
- `TP` (True Positives, `expected_outcome == PASS` and `actual_outcome_layer2 == PASS`): 50 records.
- `TN` (True Negatives, `expected_outcome == FAIL` and `actual_outcome_layer2 == FAIL`): 1,069 records.
- `FP` (False Positives, `expected_outcome == FAIL` and `actual_outcome_layer2 == PASS`): 8 records.
- `FN` (False Negatives, `expected_outcome == PASS` and `actual_outcome_layer2 == FAIL`): 10 records.
- Sum: $50 + 1069 + 8 + 10 = 1,137$ records.
- Invariants verified:
  - `is_correct == (expected_outcome == actual_outcome_layer2)` on all 1,137 rows.
  - `flag_type == "false_positive"` on exactly indices `[336, 456, 510, 513, 563, 752, 796, 1038]`.
  - `flag_type == "false_negative"` on exactly indices `[18, 84, 119, 169, 220, 246, 466, 687, 722, 1027]`.
  - `flag_type is null` on all other 1,119 rows (`is_correct == True`).

### 1.5 Semantic Audit of Flagged Items
- **False Positives (8 jobs)**:
  1. Job 336 (`Advanced Engineer Quality` @ Albertsons): Senior engineering tier requiring mentoring/hiring.
  2. Job 456 (`Quality Engineer` @ Accenture): Career Level 7 / Quality Engineering Manager coaching team.
  3. Job 510 (`Java Software Engineer` @ Wissen Technology): Required Experience: 2-5 yrs (escaped markdown `2\-5`).
  4. Job 513 (`Technical Consultant (Java Developer)` @ Infios): At least 5 years experience (word numeral 'five years').
  5. Job 563 (`IN_Associate_Saviynt _GCC_Advisory_Bangalore` @ PwC): Years of Experience required: 4.
  6. Job 752 (`Product Definition Analyst 3` @ Amadeus): BA/PO role with grade tier 3, not SWE/QA.
  7. Job 796 (`Software Engineer, AVP` @ NatWest): Associate Vice President executive management role.
  8. Job 1038 (`Fullstack Python Engineer` @ Azuga): At least 3 years React experience (stripped by prefix pattern).
- **False Negatives (10 jobs)**:
  1. Job 18 (`Associate - QA Automation` @ DAVIES): 'ten years' in company growth history.
  2. Job 84 (`Java or Kotlin & React.js Developer` @ Capgemini): 'kotlin' as optional JVM backend alternative.
  3. Job 119 (`ASP.Net MVC Developer` @ Domex): '(27 to 40 Yrs)' candidate age requirement, exp is 1-2 yrs.
  4. Job 169 (`Software Engineer - AI & Product` @ Datastraw): 'Tech Lead' is progression pathway suffix.
  5. Job 220 (`Full Stack Developer Intern` @ nan): Pune intern role; 'flutter' was minor optional mention.
  6. Job 246 (`Full Stack Developer` @ nan): Valid MERN role dropped due to missing MERN anchors.
  7. Job 466 (`Associate - QA Automation` @ DAVIES): 'ten years' in company growth history.
  8. Job 687 (`ASP.Net MVC Developer` @ Domex): '(27 to 40 Yrs)' candidate age requirement, exp is 1-2 yrs.
  9. Job 722 (`Quality Assurance Engineer` @ Scoutit): 'Salesforce' listed under Good to Have in QA role.
  10. Job 1027 (`Software Engineer – Full Stack (.NET/React)` @ DYMATRIX): 'With over 20 years of experience, DYMATRIX is...' company history.

### 1.6 Immutability of Production Code
- `git diff --stat src/scorer.py` produced 0 lines of output.
- `git diff --stat src/scraper.py` produced 0 lines of output.

---

## 2. Logic Chain

1. **Record Completeness & Schema Compliance**:
   - `ground_truth.jsonl` contains exactly 1,137 records with strictly contiguous indices 0 to 1136 ($N=1137$).
   - Every single line parses cleanly with `json.loads` without syntax errors or unescaped characters.
   - All expected keys (`job_index`, `id`, `title`, `company`, `location`, `expected_outcome`, `actual_outcome_layer1`, `actual_outcome_layer2`, `is_correct`, `flag_type`, `confidence`, `target_domain`, `notes`) are present on all records.

2. **1:1 Alignment with Master Raw Dataset**:
   - A row-by-row join between `master_raw_dataset_2026-09-29.jsonl` and `ground_truth.jsonl` demonstrates identical UUID `id`, `title`, `company`, and `location` for all 1,137 indices.
   - There are zero dropped, duplicated, or drifted records.

3. **Replay Flow Consistency**:
   - The Layer 1 replay results ($73 \text{ pass} + 1,064 \text{ fail} = 1,137$) and Layer 2 replay results ($58 \text{ pass} + 15 \text{ fail} = 73$) form a strict mathematical hierarchy ($\text{L2 Pass} \subset \text{L1 Pass}$).
   - The `actual_outcome_layer1` and `actual_outcome_layer2` columns in `ground_truth.jsonl` mirror the replay artifacts with 100% fidelity.

4. **Adversarial Integrity of Flags**:
   - The 8 False Positives and 10 False Negatives have been cross-checked against raw JD text, confirming legitimate failure modes and root causes.
   - An adversarial scan of the 1,069 True Negatives revealed 0 unaccounted entry-level developer or QA positions.
   - Inspection of all 50 True Positives confirmed zero senior titles, zero out-of-scope stacks, and valid entry-level constraints.

---

## 3. Caveats

- **Target Domain on Job 1035**: Record 1035 (`Forward Deployed Engineer - India` at Cursor) has `target_domain: null`. The record is nonetheless fully valid (`expected_outcome: PASS`, `confidence: high`, clear notes stating "Valid AI Forward Deployed Engineer role at Cursor (Python, TypeScript, AI workflows) in Bengaluru/Mumbai"), and conforms to schema definitions.
- **Out of Scope**: This evaluation was strictly an audit of the ground truth dataset and test harness. No implementation code or ground truth records were altered.

---

## 4. Conclusion

**Verdict: APPROVE**

The ground truth dataset (`regex_audit/evaluation/ground_truth.jsonl`), false positive registry (`false_positives.jsonl`), and false negative registry (`false_negatives.jsonl`) meet all quantitative and qualitative criteria:
- Complete 1,137 / 1,137 record coverage.
- Exact 1:1 join with the master raw dataset.
- Exact index alignment across all artifact files.
- Thorough and accurate root-cause documentation for all 18 flagged discrepancies.
- Complete immutability of production source files (`src/scorer.py`, `src/scraper.py`).

Phase 3 & 4 deliverables are verified and ready for downstream Phase 5 (Regex Audit Report) and Phase 6/7 (Scorer v2 rewrite).

---

## 5. Verification Method

To independently verify these conclusions:

```powershell
# 1. Run official automated test suite
python -m pytest regex_audit/test_ground_truth.py

# 2. Check line counts
(Get-Content regex_audit/evaluation/ground_truth.jsonl | Measure-Object).Count
(Get-Content regex_audit/evaluation/false_positives.jsonl | Measure-Object).Count
(Get-Content regex_audit/evaluation/false_negatives.jsonl | Measure-Object).Count

# 3. Check git diff for production immutability
git diff --stat src/scorer.py src/scraper.py
```
