# Forensic Audit Report: Ground Truth Generation & Baseline Immutability

**Work Product**: `regex_audit/compile_ground_truth.py`, `regex_audit/evaluation/` (`ground_truth.jsonl`, `false_positives.jsonl`, `false_negatives.jsonl`), `src/scorer.py`, `src/scraper.py`  
**Profile**: General Project (Development Mode per ORIGINAL_REQUEST.md)  
**Auditor**: `auditor_gt_1`  
**Parent**: `orchestrator_1` (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Verdict**: **CLEAN**

---

## Forensic Audit Summary

### Phase Results
- **Check 1 (Production Code Immutability)**: **PASS** — `src/scorer.py` has 0 git diffs (completely untouched). `src/scraper.py` uncommitted changes predate evaluation tasks (dating back to Phase 1 data collection, last write `2026-09-29T14:04:35Z` UTC).
- **Check 2 (Static Code & Network Lockdown Analysis)**: **PASS** — `regex_audit/compile_ground_truth.py` uses only Python standard library; zero network/socket calls, zero LLM calls; executes successfully under monkey-patched network lockdown with 0 socket attempts.
- **Check 3 (Accounting & Partition Completeness)**: **PASS** — Exactly 1,137 records indexed 0..1136 sequentially; disjoint batch union from `evaluator_worker_1` (0..378), `evaluator_worker_2` (379..757), and `evaluator_worker_3` (758..1136); 0 gaps, 0 duplicates.
- **Check 4 (Filter Replay Alignment)**: **PASS** — `actual_outcome_layer1` and `actual_outcome_layer2` match 100% with `regex_audit/filter_results/` replay outputs (L1 Pass: 73, Fail: 1064; L2 Pass: 58, Fail: 15).
- **Check 5 (Candidate Rubric Ground Truth Derivation)**: **PASS** — All 8 False Positives (`[336, 456, 510, 513, 563, 752, 796, 1038]`) and all 10 False Negatives (`[18, 84, 119, 169, 220, 246, 466, 687, 722, 1027]`) are genuine discrepancies with verified root causes against raw JD text. All 50 True Positives are legitimate entry-level target domain roles.
- **Check 6 (Deterministic Reproduction & SHA256 Integrity)**: **PASS** — Re-running `compile_ground_truth.py` reproduces byte-for-byte identical output files matching published SHA256 hashes.
- **Check 7 (Test Suite Execution)**: **PASS** — `python -m pytest regex_audit/test_ground_truth.py` executed with 6/6 tests passing in 0.16s.

---

## 1. Observation

1. **Baseline Immutability Observation (`src/scorer.py` and `src/scraper.py`)**:
   - Running `git diff --stat src/scorer.py`:
     ```text
     (Exit code 0, 0 lines output)
     ```
   - Running `Get-Item src/scraper.py, src/scorer.py | Select-Object Name, LastWriteTime, Length`:
     ```text
     Name       LastWriteTime       Length
     ----       -------------       ------
     scraper.py 29-09-2026 19:34:35  26909
     scorer.py  12-09-2026 22:11:15  23304
     ```
   - `src/scorer.py` is entirely untouched since 12-09-2026.
   - `src/scraper.py` was modified prior to Phase 2/3/4 tasks (at 19:34:35 local / 14:04:35 UTC) during Phase 1 master scraping to register raw job callbacks (`get_last_raw_jobs`). It was untouched during Ground Truth compilation.

2. **Static AST Analysis & Network Lockdown (`regex_audit/compile_ground_truth.py`)**:
   - Module imports: `sys`, `os`, `json`, `pathlib.Path`, `typing.Dict, List, Any, Optional`.
   - Zero networking or LLM dependencies (`requests`, `urllib`, `httpx`, `aiohttp`, `openai`, `google-genai`).
   - Under monkeypatched network lockdown (`socket.socket.connect`, `socket.create_connection`, `socket.getaddrinfo` raising `RuntimeError`), `compile_evaluation_datasets()` ran to completion with zero socket exceptions.

3. **Ground Truth Accounting & Classification Counts (`regex_audit/evaluation/`)**:
   - Master raw dataset: 1,137 records (`regex_audit/master_raw_dataset_2026-09-29.jsonl`).
   - `regex_audit/evaluation/ground_truth.jsonl`: Exactly 1,137 records.
     - Strictly sequential indices from 0 to 1136 with zero duplicates and zero gaps.
     - True Positives (TP): 50
     - True Negatives (TN): 1,069
     - False Positives (FP): 8
     - False Negatives (FN): 10
     - Total PASS expected: 60 ($50 + 10 = 60$)
     - Total FAIL expected: 1,077 ($1069 + 8 = 1077$)
     - Total records: $60 + 1077 = 1137$
     - Baseline pipeline accuracy: $\frac{50 + 1069}{1137} = 98.42\%$
   - `regex_audit/evaluation/false_positives.jsonl`: Exactly 8 records.
     - Indices: `[336, 456, 510, 513, 563, 752, 796, 1038]`
   - `regex_audit/evaluation/false_negatives.jsonl`: Exactly 10 records.
     - Indices: `[18, 84, 119, 169, 220, 246, 466, 687, 722, 1027]`

4. **Semantic Ground Truth Verification Against Candidate Profile Rubric**:
   - **8 False Positives Verified**:
     - `336` (Albertsons): Advanced Engineer Quality (requires mentoring junior engineers, hiring, performance engineering — senior IC).
     - `456` (Accenture): Quality Engineer (Career Level 7, Quality Engineering Manager coaching senior engineers and client management).
     - `510` (Wissen): Java Software Engineer ("Required Experience: 2-5", upper bound 5 years exceeds candidate ceiling).
     - `513` (Infios): Technical Consultant ("At least five years of experience", word-form numeral bypassed regex).
     - `563` (PwC): Saviynt Advisory ("Years of Experience required:\n\n 4", multiline format bypassed regex).
     - `752` (Amadeus): Product Definition Analyst 3 (Level 3 airline business/product analyst, not SWE/QA).
     - `796` (NatWest): Software Engineer, AVP (Associate Vice President senior executive level).
     - `1038` (Azuga): Fullstack Python Engineer ("* At least 3 years of experience working with React", qualification line stripped by third_party_prefixes).
   - **10 False Negatives Verified**:
     - `18` & `466` (DAVIES): Associate - QA Automation (Cypress, Selenium, API testing; rejected on company history "ten years").
     - `84` (Capgemini): Java or Kotlin & React.js Developer (Full stack Java/React; rejected on "kotlin" alternative backend language).
     - `119` & `687` (Domex): ASP.Net MVC Developer (Entry level 1-2 yrs, fresher internship compulsory; rejected on applicant age "(27 to 40 Yrs)").
     - `169` (Datastraw): Software Engineer - AI & Product (1-3 yrs experience, React/Supabase/LLM/RAG; rejected on "lead" in "| Fast-Track to Tech Lead").
     - `220` (PopPop Labs): Full Stack Developer Intern (Pune Camp, React/Node/Python/RAG; rejected on peripheral mention of "Flutter").
     - `246` (COMMANDO): Full Stack Developer (React/Node/MongoDB; rejected for missing domain anchor because DOMAIN_ANCHORS omitted React/Node/MERN).
     - `722` (Scoutit): Quality Assurance Engineer (QA testing web apps/APIs/LLMs; rejected on "Salesforce" listed under "Good to Have").
     - `1027` (DYMATRIX): Software Engineer – Full Stack (.NET/React) (unspecified experience; rejected on company history "With over 20 years of experience, DYMATRIX is...").
   - **50 True Positives Verified**: All 50 belong to target domains (Java backend, Python backend, QA automation/testing, .NET/C#, MERN, AI/ML, Full Stack SWE) located in target locations (MH, KA, Remote).

5. **Empirical Determinism & SHA256 Checksums**:
   Re-running `regex_audit/compile_ground_truth.py` regenerated all three deliverable files with identical SHA256 checksums:
   - `ground_truth.jsonl`: `0ff51e159c9058aaede4b268b17b73b40c5570f2106e64512d21f0f40252c80d`
   - `false_positives.jsonl`: `983ad3da97402a2b8e13de0e2b4ac35171519c743a35108f5418c24263752047`
   - `false_negatives.jsonl`: `6b8f2853c3b88de58d8b0bbf160022f1598a34383f976ec7d2dba5707ba3c23f`

6. **Pytest Verification**:
   Running `python -m pytest regex_audit/test_ground_truth.py`:
   ```text
   ============================= test session starts =============================
   collected 6 items
   regex_audit\test_ground_truth.py ......                                  [100%]
   ============================== 6 passed in 0.16s ==============================
   ```

---

## 2. Logic Chain

1. From Observation 1, `src/scorer.py` has zero modifications against git HEAD, and `src/scraper.py` was not modified during this evaluation milestone, satisfying the baseline immutability constraint.
2. From Observation 2, `regex_audit/compile_ground_truth.py` operates completely offline without network, external API, or LLM calls.
3. From Observation 3, the ground truth dataset completely covers the master dataset ($N=1,137$) sequentially ($0..1136$) without gaps or duplicates, and the classification subsets (50 TP, 1,069 TN, 8 FP, 10 FN) form an exact disjoint partition of all 1,137 jobs.
4. From Observation 4, independent verification of each discrepancy confirms that every single False Positive and False Negative is genuinely classified according to the candidate profile rubric in `ORIGINAL_REQUEST.md`, proving that classifications are authentic evaluations and not facade/fabricated placeholders.
5. From Observation 5 and 6, the compilation script reproduces identical files byte-for-byte under network lockdown, and all 6 automated test assertions pass cleanly.
6. Therefore, the ground truth generation pipeline satisfies all requirements of Development Mode integrity forensics.

---

## 3. Caveats

- `src/scraper.py` has uncommitted modifications dating back to Phase 1 data collection (`2026-09-29T14:04:35Z` UTC / `19:34:35` local), which added `get_last_raw_jobs()` to capture raw scraped jobs for the master dataset. It was verified that no modifications occurred during Phases 2, 3, or 4.
- No other caveats.

---

## 4. Conclusion

**Verdict: CLEAN**

The ground truth dataset generation, `compile_ground_truth.py`, and the evaluation artifacts in `regex_audit/evaluation/` are genuine, authentic, mathematically consistent, deterministic, and free of any integrity violations, facade implementations, or network dependencies. Baseline files remain preserved. The milestone is certified for downstream regex audit report generation (Phase 5) and scorer rewrite (Phase 6).

---

## 5. Verification Method

To independently reproduce the forensic audit:

1. **Verify baseline file immutability**:
   ```powershell
   git diff src/scorer.py
   # Expected: Clean (0 lines)
   ```

2. **Execute independent forensic audit suite**:
   ```powershell
   python .agents/teamwork/auditor_gt_1/forensic_audit_suite.py
   # Expected: ALL 7 CHECKS PASSED EMPIRICALLY. VERDICT: CLEAN
   ```

3. **Run official test suite**:
   ```powershell
   python -m pytest regex_audit/test_ground_truth.py
   # Expected: 6 passed in ~0.20s
   ```
