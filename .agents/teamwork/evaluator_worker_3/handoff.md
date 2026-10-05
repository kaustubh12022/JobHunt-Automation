# Handoff Report: Evaluator Worker 3 (Batch 758..1136)

**Agent:** evaluator_worker_3  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_3`  
**Parent Agent:** orchestrator_1 (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Scope:** Jobs `job_index` 758 to 1136 inclusive (379 jobs total)  
**Deliverable:** `batch_eval_3.jsonl`  
**Date:** 2026-09-29  

---

## 1. Observation

1. **Dataset Accounting in Batch 3 (758..1136)**:
   - Total raw jobs evaluated: exactly 379 records.
   - Master raw dataset inspected: `regex_audit/master_raw_dataset_2026-09-29.jsonl` lines 758 to 1136.
   - Layer 1 (`regex_audit/filter_results/layer1_pandas_pass.jsonl` & `fail`):
     * Layer 1 Pass: 15 jobs (`[796, 821, 830, 833, 910, 911, 1018, 1020, 1021, 1035, 1038, 1048, 1051, 1052, 1075]`)
     * Layer 1 Fail: 364 jobs
       - `senior_title`: 174 jobs
       - `experience_3_plus`: 114 jobs
       - `duplicate_url`: 49 jobs
       - `stale`: 21 jobs
       - `location_mismatch`: 6 jobs
   - Layer 2 (`regex_audit/filter_results/layer2_regex_pass.jsonl` & `fail`):
     * Layer 2 Pass: 14 jobs (`[796, 821, 830, 833, 910, 911, 1018, 1020, 1021, 1035, 1038, 1048, 1051, 1052]`)
     * Layer 2 Fail: 1 job (`1075: Specialist - Cloud & Application Engineering` dropped due to `out_of_scope_stack: 'PHP'`)

2. **Observed Discrepancies**:
   - **False Positive 1 (Job 796)**:
     * Title: `Software Engineer, AVP` | Company: `NatWest Group` | Location: `Bengaluru, Karnataka, India`
     * Actual Layer 2: `PASS`
     * Expected: `FAIL`
     * Observation: JD states verbatim: *"We're offering this role at associate vice president level"* and *"build a wide network of stakeholders of varying levels of seniority... using your extensive experience to engineer software"*. `matches_senior_title` checked `\b(senior|sr|lead|principal|architect|director|head|vp|chief|manager|mgr|fellow|expert)\b` and failed to match `AVP` (Associate Vice President).
   - **False Positive 2 (Job 1038)**:
     * Title: `Fullstack Python Engineer` | Company: `Azuga, Inc.` | Location: `Bangalore Urban, Karnataka, India`
     * Actual Layer 2: `PASS`
     * Expected: `FAIL`
     * Observation: JD states verbatim under Minimum Qualifications: `* At least 3 years of experience working with React.` This exceeds the entry-level 0-2 / 1-3 year ceiling. `requires_3_plus_years()` in `src/scorer.py` returned `False` because `third_party_prefixes` matched `(?:work|working)\s+(?:with|alongside|beside|among)` on `"working with React"`, erroneously stripping the candidate qualification requirement as third-party text.
   - **False Negative 1 (Job 1027)**:
     * Title: `Software Engineer – Full Stack (.NET/React) (all genders)` | Company: `DYMATRIX` | Location: `Bengaluru, Karnataka, India`
     * Actual Layer 1 / 2: `FAIL` (Layer 1 rejected with `Single experience requirement '20 years of experience' requires 3+ years`)
     * Expected: `PASS`
     * Observation: The job is a valid entry-level Full Stack role (.NET / React / TypeScript / AI tools) in Bengaluru with **zero** candidate experience required. Under "About Us", the JD states: *"With over 20 years of experience, DYMATRIX is the leading German software, solution and service provider..."*. `requires_3_plus_years()` lacked a safeguard pattern for `\bwith\s+(?:over|more\s+than)\s+\d+\s+years\s+of\s+experience\b`, treating the company's 20 years of business experience as a candidate requirement.

3. **Confirmed True Positives (12 jobs)**:
   - Job 821: `Software Engineer` | Cisco (Bachelors + 2 yrs or Masters + 0 yrs, Python/Go, Bengaluru)
   - Job 830: `Full Stack Engineer - Java, Python, Angular or React or Next Js` | Optum India (Java, Python, React, 2+ yrs preserved, Bengaluru)
   - Job 833: `Intermediate Software Engineer` | Q2 (Python, SQL, 2+ yrs preserved, Bengaluru)
   - Job 910: `AI Engineer - Python full-stack/backend engineering capability` | Tavant (Python, FastAPI, LangChain, LLM APIs, RAG, React, Bengaluru)
   - Job 911: `Z2_Python Developer` | NTT DATA North America (Python backend microservices, remote eligible, Bangalore Urban)
   - Job 1018: `.Net full stack Developer` | Infosys (C#, .NET Core, Angular/React, 2-3 yrs preserved, Bengaluru)
   - Job 1020: `Full Stack Developer - Entry Level` | Ucanly (entry level full stack developer, Bengaluru)
   - Job 1021: `Java Full Stack Engineer` | ITC Infotech (Java, React, AWS, Bengaluru/Pune Hybrid)
   - Job 1035: `Forward Deployed Engineer - India` | Cursor (Python, TypeScript, AI workflows, Bengaluru/Mumbai)
   - Job 1048: `Full stack Developer` | QualityAI (Python, FastAPI, React, Angular, AWS, Bengaluru)
   - Job 1051: `Java Full Stack Developer` | C5i (Java, Spring Boot, Microservices, Angular, MongoDB, Bengaluru)
   - Job 1052: `Full Stack Developer with expertise in Develop & Maintain web applications using .NET technologies .` | CGI (C#, .NET, Angular/React, Bengaluru)

4. **Confirmed True Negatives (364 jobs)**:
   - Layer 2 True Negative: Job 1075 (`Specialist - Cloud & Application Engineering` at Bristlecone: core role is PHP Developer, correctly dropped by out-of-scope filter).
   - Layer 1 True Negatives (363 jobs):
     * 174 senior titles: all titles contain un-demoted senior indicators (`Senior`, `Lead`, `Manager`, `Director`, `Staff`, `Architect`, `Vice President`, `II`, `III`, `L3`).
     * 113 experience 3+ drops: verified candidate requirements >= 3 years (or ranges like 2-4, 2-5, 3-5, 5-8 yrs).
     * 49 duplicate URLs: verified redundant scrapes of earlier jobs, correctly dropped per deduplication specs.
     * 21 stale jobs: verified timestamps < 2026-09-26T14:05:55Z.
     * 6 location mismatches: non-target Indian or Unknown locations without remote (817, 825, 827, 1040, 1059, 1066).

---

## 2. Logic Chain

1. **Step 1: Strict Verification Against Locked Candidate Rubric**:
   - Every job is evaluated against the 7 target domains (Java/Spring, Python/Backend, QA/Testing/Automation, .NET/C#, Full Stack/SWE, MERN Stack, AI/ML/LLM), target locations (Pune, Mumbai, Bangalore, Remote/WFH/Hybrid/Pan-India), and 0-2 / 1-3 years experience boundary.
   - Deduplication drops (49 jobs) and stale drops (21 jobs) are evaluated as `expected_outcome: "FAIL"` with `is_correct: True` because they represent expired or duplicate postings appropriately handled by Layer 1.

2. **Step 2: Cross-Referencing Actual vs Expected Decision**:
   - `is_correct = (expected_outcome == actual_outcome_layer2)`
   - Where actual = PASS and expected = FAIL $\implies$ `flag_type = "false_positive"` (Jobs 796, 1038).
   - Where actual = FAIL and expected = PASS $\implies$ `flag_type = "false_negative"` (Job 1027).
   - Where actual == expected $\implies$ `flag_type = null` (376 jobs, 99.21% agreement).

3. **Step 3: Root Cause Isolation**:
   - For Job 796, `matches_senior_title()` omitted `\bavp\b` and `associate vice president`.
   - For Job 1038, `requires_3_plus_years()` regex `(?:work|working)\s+(?:with|alongside|beside|among)` over-stripped `"working with React"`, bypassing the 3-year threshold.
   - For Job 1027, `requires_3_plus_years()` lacked a company background prefix pattern for `"With over X years of experience, <Company>..."`.

---

## 3. Caveats

- **No caveats.** Every single one of the 379 jobs in batch 3 was individually evaluated, verified, and cross-checked against Layer 1 and Layer 2 outputs.

---

## 4. Conclusion

- **Dataset Metrics**:
  * Total jobs evaluated: 379 (`job_index` 758 to 1136)
  * Expected PASS: 13 jobs (3.43%)
  * Expected FAIL: 366 jobs (96.57%)
  * Baseline Pipeline Correct Decisions: 376 (99.21%)
  * False Positives: 2 jobs (0.53%) — Jobs 796, 1038
  * False Negatives: 1 job (0.26%) — Job 1027
- **Deliverable**: Generated `batch_eval_3.jsonl` adhering to schema and specification contracts with 100% data integrity and no missing records.

---

## 5. Verification Method

To independently verify this evaluation:
1. Run the automated schema and integrity validator:
   ```powershell
   python .agents/teamwork/evaluator_worker_3/validate_batch_eval_3.py
   ```
   *Expected output*: `ALL ASSERTIONS PASSED! File batch_eval_3.jsonl is 100% valid and verified.`
2. Verify line count and continuity:
   ```powershell
   python -c "import json; lines = [json.loads(l) for l in open('.agents/teamwork/evaluator_worker_3/batch_eval_3.jsonl', encoding='utf-8')]; assert len(lines) == 379; assert [l['job_index'] for l in lines] == list(range(758, 1137)); print('Count and index verified!')"
   ```
3. Inspect discrepancies:
   ```powershell
   python -c "import json; lines = [json.loads(l) for l in open('.agents/teamwork/evaluator_worker_3/batch_eval_3.jsonl', encoding='utf-8')]; fps = [l['job_index'] for l in lines if l['flag_type'] == 'false_positive']; fns = [l['job_index'] for l in lines if l['flag_type'] == 'false_negative']; print('FPs:', fps); print('FNs:', fns)"
   ```
   *Expected output*: `FPs: [796, 1038] | FNs: [1027]`
