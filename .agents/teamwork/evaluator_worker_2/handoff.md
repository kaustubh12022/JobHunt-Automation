# Handoff Report: Profile Rubric Evaluation (Batch 379..757)

**Author:** `evaluator_worker_2`  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_2`  
**Parent Agent:** `orchestrator_1` (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Date:** 2026-09-29  
**Status:** Hard Handoff (Batch 2 Complete)  

---

## 1. Observation

1. **Assigned Scope & Input Files**:
   - Total records evaluated: 379 jobs (`job_index` 379 to 757 inclusive) loaded from `regex_audit/master_raw_dataset_2026-09-29.jsonl`.
   - Baseline replay results inspected:
     - `regex_audit/filter_results/layer1_pandas_pass.jsonl` (22 jobs in batch 2: [384, 387, 456, 505, 510, 513, 531, 540, 545, 563, 631, 634, 636, 663, 665, 672, 709, 712, 722, 736, 747, 752]).
     - `regex_audit/filter_results/layer1_pandas_fail.jsonl` (357 jobs in batch 2: senior_title=170, experience_3_plus=123, stale=30, duplicate_url=25, location_mismatch=9).
     - `regex_audit/filter_results/layer2_regex_pass.jsonl` (20 jobs in batch 2: all except 722 and 736).
     - `regex_audit/filter_results/layer2_regex_fail.jsonl` (2 jobs in batch 2: 722 and 736).

2. **Identified False Positives (5 jobs)**:
   - **Job 456**: `Quality Engineer @ Accenture in India` (`id`: `6c71c4c8-47bc-4993-9c87-9bc95dc5ebc8`).
     - Passed baseline Layer 1 and Layer 2.
     - Verbatim excerpt from JD:
       > `*Career Level 7 | Test Architecture •Automation • GenAI• Agentic Testing*`  
       > `We are looking for a hands-on Quality Engineering Manager to lead engineering teams delivering high-quality, reliable, AI-augmented applications across complex, cloud-native environments. This is a leadership role for a mature practitioner who is equally comfortable architecting a test strategy, coaching senior engineers...`
     - Failure reason: Career Level 7 Quality Engineering Manager leadership role coaching senior engineers. `matches_senior_title` only inspected the title string (`Quality Engineer`), missing senior managerial level in the JD header.
   - **Job 510**: `Java Software Engineer @ Wissen Technology` (`id`: `bcebcfce-ca2d-45a7-bc40-27f999971ebf`).
     - Passed baseline Layer 1 and Layer 2.
     - Verbatim excerpt from JD:
       > `Required Experience: 2-5`
     - Failure reason: Requires 2-5 years experience (upper bound 5 $\ge$ 4). `requires_3_plus_years` failed because the word "years" was absent after the range and lower bound was 2.
   - **Job 513**: `Technical Consultant (Java Developer) @ Infios` (`id`: `7ea6a635-4299-4d69-a178-57c2a7927c4f`).
     - Passed baseline Layer 1 and Layer 2.
     - Verbatim excerpt from JD:
       > `* At least five years of experience working with OMS or distributed commerce systems.`
     - Failure reason: Requires $\ge 5$ years experience. `requires_3_plus_years` failed because regex only checked numeric digits (`\d+`) and missed word numeral "five".
   - **Job 563**: `IN_Associate_Saviynt _GCC_Advisory_Bangalore @ PwC India` (`id`: `5a8fa8a1-77ec-448a-a430-671239c089f2`).
     - Passed baseline Layer 1 and Layer 2.
     - Verbatim excerpt from JD:
       > `Years of Experience required:`  
       > `4`
     - Failure reason: Requires 4 years experience. `requires_3_plus_years` missed multi-line key-value syntax where "Years of Experience required:" preceded the digit 4.
   - **Job 752**: `Product Definition Analyst 3 @ Amadeus` (`id`: `2643a7a9-d3db-4cb8-8c10-ca811fc7b9aa`).
     - Passed baseline Layer 1 and Layer 2.
     - Verbatim excerpt from JD:
       > `Product Definition Analyst 3 ... Analyse business requirements written by airline customers ... Write documentation for product specifications or functional studies ...`
     - Failure reason: Non-target domain (Business/Product Analyst role, not SWE/QA) and Grade 3 senior tier. `matches_senior_title` missed terminal digit '3', while `is_relevant_jd` matched generic keywords (`python`, `sql`, `mongodb`, `test case`).

3. **Identified False Negatives (3 jobs)**:
   - **Job 466**: `Associate - QA Automation @ DAVIES` (`id`: `fa4f1d6b-734f-4a30-8041-aa6b2c6dc67b`).
     - Location: `MH, IN` (target metro Pune/Mumbai).
     - Stack: Cypress Cloud, Selenium WebDriver, Cucumber, Jest, K6, JMeter, BrowserStack, GitHub CI/CD pipelines (QA Automation).
     - Experience: Associate level, candidate experience unspecified.
     - Rejected at Layer 1: `rejection_reason`: `experience_3_plus`, detail: `Word-based experience requirement 'ten years' requires 3+ years`.
     - Verbatim excerpt from JD:
       > `Over the past ten years Davies has grown its annual revenues more than 20-fold, investing heavily in research & development...`
     - Failure reason: Rejection was triggered by company revenue growth history ("ten years"), not candidate experience.
   - **Job 687**: `ASP.Net MVC Developer @ Domex Business Information Pvt Ltd` (`id`: `3134375b-007a-426b-80fc-efd372e2cf5b`).
     - Location: `Worli, Mumbai, MH, IN`.
     - Stack: ASP.NET MVC, MS SQL Server (.NET stack, target domain 4).
     - Experience & Salary:
       > `ASP.Net MVC Developers (27 to 40 Yrs) required by Worli (South Mumbai) based Pvt. Ltd. company engaged in online/ e-commerce activity. Fresher/Experienced Graduates with 1 to 2 years experience in ASP.net, MVC, MS SQL Server. Previous experience in software development and good coding logic essential. Fresher internship is compulsory. ... Salary: 20,000 - 30,000 per month`
     - Rejected at Layer 1: `rejection_reason`: `experience_3_plus`, detail: `Experience range '27 to 40 yrs' (lo=27, hi=40) requires 3+ years`.
     - Failure reason: Regex parsed candidate age requirement `(27 to 40 Yrs)` as work experience, ignoring explicit 1-2 years experience / fresher internship requirement.
   - **Job 722**: `Quality Assurance Engineer @ Scoutit` (`id`: `96d7cd1b-f51d-4e44-9ee1-ddd39e8015e4`).
     - Location: `Bengaluru, Karnataka, India`.
     - Stack: Functional, regression, exploratory testing, Postman, APIs, exposure to AI products / LLM evaluation. Candidate experience unspecified.
     - Passed Layer 1; rejected at Layer 2: `rejection_reason`: `out_of_scope_stack`, detail: `Out-of-scope stack 'Salesforce' detected in description`.
     - Verbatim excerpt from JD:
       > `Good to Have: ... Experience testing products such as Salesforce, NetSuite, Canva, Power BI, DocuSign, or similar enterprise applications.`
     - Failure reason: Core QA role. `matches_out_of_scope_role` executed unanchored regex search across entire description for `\bsalesforce\b`, falsely triggering on an optional third-party application example.

4. **True Positives (15 jobs)**:
   - Jobs: 384, 387, 505, 531, 540, 545, 631, 634, 636, 663, 665, 672, 709, 712, 747.
   - All 15 passed Layer 1 and Layer 2, and are legitimate entry-level/preserved target domain roles.

5. **True Negatives (356 jobs)**:
   - 170 senior title drops in Layer 1 (all verified senior / lead / manager / principal / architect / L3 / II / III).
   - 121 experience 3+ drops in Layer 1 (all verified $\ge 3$ years candidate requirement).
   - 30 stale drops in Layer 1 (>72h cutoff relative to pinned scrape time).
   - 25 duplicate URL drops in Layer 1.
   - 9 location mismatch drops in Layer 1 (Unknown location without remote).
   - 1 Layer 2 rejection: Job 736 (`Associate Salesforce Quality Assurance Engineer - Automation @ ANSR` $\rightarrow$ core Salesforce QA role).

---

## 2. Logic Chain

1. **Partitioning and Conservation**:
   - Total batch raw jobs: $757 - 379 + 1 = 379$.
   - Baseline results:
     $$\text{Total Batch 2} = 379 = 22 \text{ (Layer 1 Pass)} + 357 \text{ (Layer 1 Fail)}$$
     $$22 \text{ (Layer 1 Pass)} = 20 \text{ (Layer 2 Pass)} + 2 \text{ (Layer 2 Fail)}$$
   - Ground truth classification:
     $$\text{Total Expected PASS} = 15 \text{ (True Positives)} + 3 \text{ (False Negatives)} = 18$$
     $$\text{Total Expected FAIL} = 356 \text{ (True Negatives)} + 5 \text{ (False Positives)} = 361$$
     $$\text{Total Records} = 18 + 361 = 379$$

2. **False Positive Deduction**:
   - Each of the 20 Layer 2 survivors was checked against Candidate Profile Rubric §3.1.
   - Jobs 456, 510, 513, 563, and 752 violated explicit rubric rules (Career Level 7 Manager, 2-5 yrs exp, 5 yrs exp, 4 yrs exp, and Level 3 BA role respectively).
   - Thus, they are classified as `expected_outcome: FAIL` with `flag_type: false_positive`.

3. **False Negative Deduction**:
   - Every single rejection in Layer 1 (357 jobs) and Layer 2 (2 jobs) was inspected.
   - Non-technical, stale, and duplicate drops were legitimately rejected.
   - In `experience_3_plus`:
     - Job 466 matched company tenure, not candidate experience.
     - Job 687 matched candidate age, while candidate experience was 1-2 years.
   - In `out_of_scope_stack`:
     - Job 722 is a generic QA Engineer role where Salesforce was an optional tool tested, not the core engineering stack.
   - All three jobs satisfy the target domain, target location, and experience criteria, and are therefore classified as `expected_outcome: PASS` with `flag_type: false_negative`.

4. **Overall Baseline Accuracy on Batch 2**:
   $$\text{Baseline Accuracy} = \frac{\text{True Positives (15)} + \text{True Negatives (356)}}{379} = \frac{371}{379} = 97.89\%$$

---

## 3. Caveats

1. **Duplicate URL Retention**:
   - 25 jobs in batch 2 were dropped by Layer 1 deduplication (`duplicate_url`). Per the architecture specification in `spec_miner_survey_1/handoff.md`, duplicate copies of otherwise valid postings are marked as `expected_outcome: FAIL` with explanatory notes linking to their original jobs, since duplicate drops are desired and correct pipeline behavior.
2. **Freshness Cutoff (72h)**:
   - 30 jobs in batch 2 posted prior to `2026-09-26T14:05:55Z` were rejected as stale by Layer 1. These are marked as `expected_outcome: FAIL` because freshness filtering is an intended operational requirement.
3. No other caveats.

---

## 4. Conclusion

- Batch 2 evaluation (`job_index` 379 to 757) is complete and fully verified.
- Deliverable `batch_eval_2.jsonl` contains exactly 379 JSON lines with strictly contiguous indices 379..757.
- Key findings for `scorer_v2.py` optimization:
  1. Add company history and tenure stripping to `requires_3_plus_years` (e.g. `over the past \w+ years`, `revenue`).
  2. Differentiate candidate age brackets from experience ranges (e.g. `\(\d+ to \d+ Yrs\)` in titles/summaries).
  3. Scope `matches_out_of_scope_role` to title or require primary stack weighting, avoiding rejections from "good to have" mentions in the description.
  4. Expand `requires_3_plus_years` to capture word-form numerals (`five years`), multi-line key-value patterns (`Years of Experience required:\s*\d+`), and upper bounds $\ge 4$ on 2-5 year ranges (`Required Experience: 2-5`).
  5. Check JD header for senior leadership/career level markers (`Career Level [7-9]`, `Engineering Manager`) when title is ambiguous (`Quality Engineer`).

---

## 5. Verification Method

1. **Verify Line Count and Schema Integrity**:
   ```powershell
   python -c "
   import json
   path = '.agents/teamwork/evaluator_worker_2/batch_eval_2.jsonl'
   required_keys = ['job_index', 'title', 'company', 'expected_outcome', 'actual_outcome_layer1', 'actual_outcome_layer2', 'is_correct', 'flag_type', 'confidence', 'notes', 'root_cause', 'specific_pattern_issue']
   indices = []
   with open(path, 'r', encoding='utf-8') as f:
       for line in f:
           obj = json.loads(line)
           for k in required_keys: assert k in obj
           indices.append(obj['job_index'])
   assert len(indices) == 379
   assert indices == list(range(379, 758))
   print('Verification Passed: 379 records contiguous and complete.')
   "
   ```

2. **Verify Breakdown and Counts**:
   ```powershell
   python -c "
   import json
   from collections import Counter
   path = '.agents/teamwork/evaluator_worker_2/batch_eval_2.jsonl'
   counts = Counter()
   with open(path, 'r', encoding='utf-8') as f:
       for line in f:
           obj = json.loads(line)
           counts[(obj['expected_outcome'], obj['actual_outcome_layer2'], obj['flag_type'])] += 1
   print('Breakdown:', counts)
   "
   ```
