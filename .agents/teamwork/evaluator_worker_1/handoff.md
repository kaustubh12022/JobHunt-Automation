# Evaluator Worker 1: Handoff Report (Batch 0..378)

**Agent:** evaluator_worker_1  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_1`  
**Parent Agent:** orchestrator_1 (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Date:** 2026-09-29  
**Assigned Scope:** Job indices 0 to 378 (379 jobs total)  
**Deliverable File:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_1\batch_eval_1.jsonl`  

---

## 1. Observation

Direct observations from the raw dataset, Layer 1/2 filter outputs, and candidate rubric:

1. **Batch Population Accounting**:
   - Master dataset total: 1,137 jobs (`regex_audit/master_raw_dataset_2026-09-29.jsonl`).
   - Assigned batch: indices 0 to 378 (exactly 379 records).
   - Baseline Layer 1 results for batch 1:
     - `layer1_pandas_pass.jsonl`: 36 jobs survived Layer 1.
     - `layer1_pandas_fail.jsonl`: 343 jobs dropped at Layer 1 (`senior_title`: 172, `experience_3_plus`: 119, `stale`: 23, `duplicate_url`: 23, `duplicate_company_title`: 5, `location_mismatch`: 1).
   - Baseline Layer 2 results for batch 1:
     - `layer2_regex_pass.jsonl`: 24 jobs passed Layer 2.
     - `layer2_regex_fail.jsonl`: 12 jobs dropped at Layer 2 (`out_of_scope_stack`: 9, `irrelevant_jd`: 3).

2. **Identified Discrepancies**:
   - **False Positive (1 job)**:
     - **Job 336** (`Albertsons Companies India`, `"Advanced Engineer Quality [T500-29735]"`):
       - Title has `"Advanced Engineer"`, which bypassed `matches_senior_title` because `"advanced"` was not in `SENIOR_TITLE_PATTERN`.
       - JD requires: `"Uphold quality standards and mentor junior team members on testing practices and engineering excellence"`, `"Performance Engineering, Capacity Planning, Workload Modeling... Kubernetes"`, and `"contribute to hiring activities"`.
       - Passed Layer 1 and Layer 2 despite being a senior IC role exceeding candidate fresher profile.
   - **False Negatives (6 jobs)**:
     - **Job 18** (`DAVIES`, `"Associate - QA Automation"`):
       - Legitimate Associate QA Automation role (Cypress, Selenium, Cucumber, API testing, MH/Mumbai/Pune).
       - Rejected in Layer 1 by `requires_3_plus_years` on pattern `\b(?:ten)\s*years\b` which matched company growth text in boilerplate: `"Over the past ten years Davies has grown its annual revenues more than 20-fold"`.
     - **Job 84** (`Capgemini`, `"Java or Kotlin & React.js Developer"`):
       - Full Stack Java/Spring Boot + React.js web developer role with unspecified experience in MH.
       - Rejected in Layer 2 by `matches_out_of_scope_role` matching `\bkotlin\b` when Kotlin was merely listed as an alternative backend JVM language to Java.
     - **Job 119** (`Domex Business Information Pvt Ltd`, `"ASP.Net MVC Developer"`):
       - Legitimate entry-level .NET developer role in Worli, Mumbai requiring `"Fresher/Experienced Graduates with 1 to 2 years experience in ASP.net, MVC, MS SQL Server"`.
       - Rejected in Layer 1 by `requires_3_plus_years` because it matched the applicant age bracket `"(27 to 40 Yrs)"` as work experience (`(lo=27, hi=40)`).
     - **Job 169** (`Datastraw Technologies Pvt Ltd`, `"Software Engineer - AI & Product | Fast-Track to Tech Lead"`):
       - Legitimate entry-level SWE role in Mumbai (Hybrid) requiring `"1-3 years of experience"` (preserved per rubric) working on React, PostgreSQL, Supabase, LLMs, and RAG.
       - Rejected in Layer 1 by `matches_senior_title` matching `\blead\b` inside the career progression suffix `"| Fast-Track to Tech Lead"`.
     - **Job 220** (`PopPop Labs`, `"Full Stack Developer Intern"`):
       - Legitimate Full Stack Developer Internship in Pune Camp working with React, Next.js, Node.js, Express.js, Python, PostgreSQL, and LLM/RAG APIs.
       - Rejected in Layer 2 by `matches_out_of_scope_role` matching peripheral `"Flutter / Dart"` listed under optional frontend technologies.
     - **Job 246** (`COMMANDO`, `"Full Stack Developer"`):
       - Legitimate entry-level Full Stack role in MH working with React.js, Next.js, Node.js, and MongoDB.
       - Rejected in Layer 2 by `is_relevant_jd` for `missing_domain_anchor` because `DOMAIN_ANCHORS` omitted `"react"`, `"node"`, `"nodejs"`, and `"mern"`.

---

## 2. Logic Chain

1. **Baseline Replay Accuracy vs. Profile Rubric**:
   - Out of 379 jobs evaluated in batch 1:
     - 23 baseline passes are confirmed True Positives (valid entry-level roles in Java, Python, QA, Full Stack, MERN, AI/ML in Pune/Mumbai/Bengaluru).
     - 1 baseline pass is a False Positive (Job 336, senior/mentoring role).
     - 349 baseline rejections are confirmed True Negatives (senior titles, >=3 yrs exp, stale postings >72h, cross-platform duplicates, out-of-scope stacks).
     - 6 baseline rejections are False Negatives (valid entry-level roles across QA, Java/Kotlin, .NET, AI/Product, MERN intern, MERN full-stack).
   - Expected outcomes:
     - **PASS**: 29 jobs (23 TP + 6 FN)
     - **FAIL**: 350 jobs (349 TN + 1 FP)
   - Baseline pipeline accuracy:
     $$\text{Accuracy} = \frac{23 + 349}{379} = \frac{372}{379} \approx 98.15\%$$

2. **Root Cause Categorization for Filter Rewrite**:
   - **Company Boilerplate / History**: `requires_3_plus_years` must ignore text sections containing `"About [Company]"`, `"our company"`, `"past X years"`.
   - **Age Qualification Pattern**: `requires_3_plus_years` must distinguish applicant age brackets (e.g. `"27 to 40 Yrs"`) from job experience requirements.
   - **Title Progression Suffixes**: `matches_senior_title` should avoid triggering on growth/progression suffixes (e.g. `"Fast-Track to Tech Lead"` or `"path to Lead"`).
   - **Peripheral Tech Matches**: `matches_out_of_scope_role` should not reject web full-stack roles when mobile or JVM alternatives (Kotlin, Flutter) appear peripherally or as optional skills.
   - **Domain Anchor Coverage**: `DOMAIN_ANCHORS` must include MERN and modern web stack tokens (`mern`, `react`, `node`, `nodejs`, `express`, `mongodb`).

---

## 3. Caveats

1. **Job 353 (Infotel French Description)**:
   - Job 353 (`Testeur Automaticien (H/F)`) is located in Bengaluru East and specifies QA Automation with Selenium, Python, and 2 years minimum experience. Although the description is written entirely in French, the candidate rubric does not have an explicit language disqualifier. It has been marked `PASS` with `confidence: "medium"` based strictly on technical domain, experience, and location fit.
2. **Duplicate Records**:
   - 28 duplicate records (23 URL duplicates and 5 title/company duplicates) in batch 1 were marked `FAIL` with explicit attribution to Layer 1 deduplication. This ensures that cross-platform scrape duplicates are never evaluated as false rejections.

---

## 4. Conclusion

- Batch 1 evaluation (indices 0..378) is 100% complete and fully verified.
- `batch_eval_1.jsonl` contains exactly 379 records matching the required schema with all fields populated:
  - Total PASS: 29
  - Total FAIL: 350
  - Total False Positives: 1 (Job 336)
  - Total False Negatives: 6 (Jobs 18, 84, 119, 169, 220, 246)
  - Baseline Agreement Rate: 98.15% (372/379)
- All 7 discrepancies have detailed `notes`, `root_cause`, and `specific_pattern_issue` strings ready for compilation into `ground_truth.jsonl` and `regex_audit/audit_report.md`.

---

## 5. Verification Method

To independently verify `batch_eval_1.jsonl`:

```powershell
python -X utf8 -c "
import json
path = r'.agents/teamwork/evaluator_worker_1/batch_eval_1.jsonl'
records = [json.loads(l) for l in open(path, encoding='utf-8')]
print('Total records:', len(records))
assert len(records) == 379
pass_count = sum(1 for r in records if r['expected_outcome'] == 'PASS')
fail_count = sum(1 for r in records if r['expected_outcome'] == 'FAIL')
fp_count = sum(1 for r in records if r['flag_type'] == 'false_positive')
fn_count = sum(1 for r in records if r['flag_type'] == 'false_negative')
correct_count = sum(1 for r in records if r['is_correct'])
print(f'PASS: {pass_count}, FAIL: {fail_count}, FP: {fp_count}, FN: {fn_count}, Correct: {correct_count}')
assert pass_count == 29
assert fail_count == 350
assert fp_count == 1
assert fn_count == 6
assert correct_count == 372
for i, r in enumerate(records):
    assert r['job_index'] == i
    assert r['expected_outcome'] in ('PASS', 'FAIL')
    if not r['is_correct']:
        assert r['root_cause'] and r['specific_pattern_issue']
print('ALL VERIFICATION CHECKS PASSED!')
"
```
