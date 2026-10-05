# Specification Mining Report: Regex Job Filter Pipeline Audit & Optimization

**Agent:** spec_miner_survey_1  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_1`  
**Parent Agent:** orchestrator_1 (Conversation ID: `5eb201de-9def-4d9e-9362-a784693de631`)  
**Date:** 2026-09-29  

---

## 1. Observation

Direct observations from authoritative specifications and codebase:

1. **Directive & Raw Data Invariance**:
   - `ORIGINAL_REQUEST.md` (Lines 10, 89): "CRITICAL DIRECTIVE: DO NOT re-scrape or re-generate the raw dataset. The complete 1,137-job raw dataset has already been successfully scraped, verified, and stored at `regex_audit/master_raw_dataset_2026-09-29.jsonl` (and `regex_audit/master_raw_dataset_2026-09-29.json`). Load and use this existing dataset directly for all tasks."
   - Verification via python inspects exactly 1,137 records (657 Indeed, 480 LinkedIn). Description length ranges from 229 to 14,320 characters (mean 3,991 chars). Zero jobs have empty or truncated descriptions.

2. **Candidate Profile Specifications**:
   - `ORIGINAL_REQUEST.md` (Lines 13-24, 102-105) & `SCRAPING_AND_REGEX_TESTING.md` (Lines 31-61):
     - Candidate: Kaustubh Kale, Fresher (1-month Java Developer internship), B.E. Information Technology (2022–2026), Pune, Maharashtra, India.
     - 7 Valid Target Domains: Java/Spring, Python/Django/Flask, QA/Testing/Automation, .NET/C#, Full Stack/SWE, MERN Stack (React, Express, MongoDB, Node.js), AI/ML/LLM/Agentic AI.
     - Valid Locations: Pune, Mumbai, Bangalore / Bengaluru, or Remote / Hybrid / WFH / Pan-India.
     - Preserved Experience: 0-2 years, fresher, entry-level, junior, associate, graduate, trainee, 1-3 years (per `src/scorer.py` line 196: "1-3 years is NEVER dropped"), or unspecified.
     - Out-of-Scope Stacks: PHP, Laravel, Ruby, Rails, iOS, Swift, SwiftUI, Android, Kotlin, Flutter, React Native, Salesforce, Apex, SAP, ABAP, Drupal, Magento, WordPress.

3. **Current Filter Implementation Deficiencies Observed**:
   - `src/scorer.py` (Lines 57-70): `DOMAIN_ANCHORS` lacks `mern`, `express`, `mongodb`, `node`, `ai`, `ml`, `machine learning`, `llm`, `agentic`, `rag`, `langchain`.
   - Direct execution probe:
     ```python
     is_relevant_jd('We are looking for a MERN developer skilled in React, Node, Express, MongoDB.', 'MERN Developer')
     # Observed Output: False (FALSE NEGATIVE)
     ```
   - `src/scorer.py` (Lines 87-97): `matches_out_of_scope_role()` searches entire description for `OUT_OF_SCOPE_STACK_PATTERN`.
     ```python
     matches_out_of_scope_role('Java Developer', 'Java Spring Boot role. Experience with PHP is a plus.')
     # Observed Output: True (FALSE NEGATIVE / FALSE REJECTION)
     ```
   - `src/scorer.py` (Lines 148-154): `matches_senior_title()` matches `\bsenior\b` regardless of junior qualification.
     ```python
     matches_senior_title('Senior / Junior Developer')
     # Observed Output: True (REJECTED)
     ```
   - `src/scraper.py` (Lines 260-275): `build_location_regex(['pune', 'mumbai', 'bangalore'])` correctly matches "MH, IN", "KA, IN", "Bengaluru, Karnataka, India", but drops jobs with `location: "Unknown"` unless `is_remote == True`.

4. **Required Deliverables & Locations**:
   - Filter Replay (Phase 2): `regex_audit/filter_results/layer1_pandas_pass.jsonl`, `layer1_pandas_fail.jsonl`, `layer2_regex_pass.jsonl`, `layer2_regex_fail.jsonl`.
   - Evaluation & Ground Truth (Phases 3 & 4): `regex_audit/evaluation/ground_truth.jsonl`, `false_positives.jsonl`, `false_negatives.jsonl`.
   - Audit Analysis (Phase 5): `regex_audit/audit_report.md`.
   - Rewrite & Retest (Phases 6 & 7): `regex_audit/scorer_v2.py`, `regex_audit/retest/v2_pass.jsonl`, `v2_fail.jsonl`, `regex_audit/retest/comparison_report.md`.
   - Untouched constraint: `src/scorer.py` and `src/scraper.py` must NOT be edited.

---

## 2. Logic Chain

1. **Data Completeness & Flow Consistency**:
   - The dataset contains 1,137 jobs. Replaying Layer 1 partition all 1,137 jobs into `layer1_pandas_pass` and `layer1_pandas_fail`.
   - Layer 2 filters ONLY the survivors of Layer 1 (`layer1_pandas_pass`), partitioning them into `layer2_regex_pass` and `layer2_regex_fail`.
   - Total accounting identity:
     $$\text{Total Raw} = 1137 = |\text{Layer1 Pass}| + |\text{Layer1 Fail}|$$
     $$|\text{Layer1 Pass}| = |\text{Layer2 Pass}| + |\text{Layer2 Fail}|$$
   - Ground truth must contain an entry for every single raw job ($N=1137$).

2. **Deduplication Logic in Ground Truth**:
   - Scrape replay includes cross-platform deduplication in Layer 1 (585 normalized URL duplicates, 609 title/company duplicates).
   - A duplicate record of an otherwise legitimate job is legitimately dropped by Layer 1 deduplication. In `ground_truth.jsonl`, its `expected_outcome` is `FAIL` with note `Duplicate of job_index X`, so its rejection by Layer 1 is evaluated as correct (`is_correct: true`).

3. **Domain Expansion Alignment**:
   - Candidate has full-stack, React, Node, and Python AI skills. The original scorer dropped MERN roles due to missing `DOMAIN_ANCHORS` and missing `express` in `TECH_TOOLS`.
   - Expanding `DOMAIN_ANCHORS` to include MERN terms (`mern`, `mern stack`, `react`, `node`, `nodejs`, `express`, `expressjs`, `mongodb`) and AI/LLM terms (`ai`, `ml`, `machine learning`, `llm`, `agentic`, `genai`, `generative ai`, `rag`, `langchain`) directly recovers legitimate jobs without lowering the technical bar.

4. **Deterministic Accuracy Threshold (>=95.0%)**:
   - With 1,137 jobs, a 95.0% accuracy bar against ground truth requires agreement on at least:
     $$\lceil 1137 \times 0.95 \rceil = 1081 \text{ jobs}$$
   - Residual mismatches ($\le 56$ jobs) must be genuine borderline edge cases (e.g., conflicting experience clauses or unresolvable missing metadata).
   - Regression bar: 0 regressions on valid jobs that legitimately passed in the baseline run.

---

## 3. Comprehensive Specifications

### 3.1 Candidate Profile Rubric

#### A. Candidate Identity & Qualification
- **Full Legal Name:** Kaustubh Sanjay Kale
- **Education:** Bachelor of Engineering (B.E.) in Information Technology, 2022–2026 (Graduating Batch 2026)
- **Current Location:** Pune, Maharashtra, India (Zip: 411037)
- **Target Experience Bracket:** Fresher / Entry-Level / Junior (0–2 years, 1-month Java Developer internship completed, 1–3 years preserved per baseline standard)

#### B. Target Domains (Valid Passes)
A job satisfies the technical domain criterion if it matches **any** of the following 7 domains:
1. **Java / Spring / Backend Development:**
   - Keywords: `Java`, `Spring Core`, `Spring Boot`, `Hibernate`, `JDBC`, `Microservices`, `REST APIs`, `Backend Developer`.
2. **Python / Backend & Frameworks:**
   - Keywords: `Python`, `Django`, `Flask`, `FastAPI`, `Pandas`, `Asyncio`, `Backend Engineer`.
3. **QA / Testing / Automation:**
   - Keywords: `QA`, `Quality Assurance`, `Automation Testing`, `SDET`, `Selenium`, `JUnit`, `Postman`, `pytest`, `Playwright`, `Cypress`, `TestNG`, `Rest Assured`, `Manual Testing`, `API Testing`, `Test Engineer`, `Test Analyst`.
4. **.NET / C# / ASP.NET:**
   - Keywords: `.NET`, `C#`, `csharp`, `ASP.NET`, `ASP.NET Core`, `C# Developer`.
5. **Full Stack / General Software Engineering:**
   - Keywords: `Full Stack`, `Fullstack`, `Software Engineer`, `Software Developer`, `SDE`, `Associate Software Engineer`, `Graduate Engineer Trainee (GET)`, combining frontend and backend.
6. **MERN Stack:**
   - Keywords: `MERN`, `React`, `React.js`, `Node`, `Node.js`, `Express`, `Express.js`, `MongoDB`.
7. **AI / ML / LLM / Agentic AI:**
   - Keywords: `AI`, `Artificial Intelligence`, `Machine Learning`, `ML`, `LLM`, `Large Language Models`, `Agentic AI`, `Generative AI`, `GenAI`, `RAG`, `LangChain`, `LlamaIndex`, `PyTorch`, `HuggingFace`.

#### C. Out-of-Scope Stacks (Strict Fail Criteria)
A job fails if its core or exclusive requirement is in any of the following stacks:
- `PHP`, `Laravel`, `CodeIgniter`
- `Ruby`, `Ruby on Rails`
- `iOS`, `Swift`, `SwiftUI`, `Objective-C`
- `Android`, `Kotlin` (native mobile)
- `Flutter`, `Dart` (cross-platform mobile)
- `React Native` (mobile-only)
- `Salesforce`, `Apex`, `Visualforce`
- `SAP`, `ABAP`, `SAP HANA`
- `Drupal`, `Magento`, `WordPress`, `Shopify`, `Joomla`
- *Refinement for scorer_v2:* A job must only fail if the role is *primarily* or *exclusively* for these stacks. Peripheral mentions (e.g. "knowledge of PHP/mobile is an advantage" in a Java/Python backend role) should not trigger false rejection.

#### D. Experience Boundaries
- **PASS:**
  - Explicit entry levels: `fresher`, `entry level`, `entry-level`, `junior`, `associate`, `graduate`, `intern`, `internship`, `trainee`, `apprentice`.
  - Numeric ranges: `0-1 year`, `0-2 years`, `0-3 years`, `1-2 years`, `1-3 years`, `2-3 years`.
  - Unspecified experience (no explicit minimum stated in JD).
- **FAIL:**
  - Strictly requires $\ge 3$ years of candidate experience (e.g. `3+ years`, `3-5 years`, `4+ years`, `at least 3 years`, `minimum 3 years`, `3 to 6 years`).
  - Range lower bound $\ge 3$ (e.g., `3-4 years`), or lower bound $\ge 2$ with upper bound $\ge 4$ (e.g., `2-5 years`), or upper bound $\ge 5$.
- **Safeguards / Non-Candidate Experience:**
  - Must strip company/team history: "our team has 10+ years experience", "firm with 15 years in industry", "mentors with 20 years experience".
  - Must strip degree/bond durations: "3 years degree", "3 year bachelor", "3 years diploma", "3 years service bond/agreement".

#### E. Seniority Title Boundaries
- **FAIL:**
  - Titles containing: `Senior`, `Sr.`, `Sr`, `Lead`, `Manager`, `Principal`, `Director`, `Head of`, `VP`, `Vice President`, `President`, `Staff`, `Architect`, `Expert`, `Lead QA`, `Team Lead`.
  - Roman numerals indicating senior tiers: `II`, `III`, `IV`, `V`, `VI`, `VII`, `VIII`.
  - Corporate grade levels: `Level 2` to `Level 9`, `L2` to `L9`.
- **PASS (Exceptions):**
  - Titles qualified by junior/entry markers (e.g. "Junior / Associate Engineer", "Trainee Engineer").
  - Roman numeral `I` / `Level 1` / `L1` (Entry Level / Junior).

#### F. Location Boundaries
- **PASS:**
  - Target Metros: `Pune`, `Mumbai` (including `Navi Mumbai`, `Thane`), `Bangalore` / `Bengaluru`.
  - State/Regional Aliases: `Maharashtra`, `MH`, `IN-MH`, `MH, IN`; `Karnataka`, `KA`, `IN-KA`, `KA, IN`.
  - Remote / Flexible: `is_remote == True`, `Remote`, `Hybrid`, `Work From Home`, `WFH`, `Anywhere`, `Pan-India`, `Pan India`.
- **FAIL:**
  - Foreign locations outside India with no remote option.
  - Non-target Indian cities (e.g. `Delhi`, `Noida`, `Gurgaon`, `Hyderabad`, `Chennai`, `Kolkata`) **unless** explicitly marked as `Hybrid`, `Remote`, `WFH`, or `Pan-India`.
  - Location listed as `Unknown` **unless** `is_remote == True` or JD specifies remote/hybrid eligibility.

#### G. Non-Technical / Irrelevant Roles
- **FAIL:** Roles in HR, Talent Acquisition, Sales, Business Development, Marketing, Graphic Design, Legal, Accounting, Finance, Hardware Maintenance, Non-technical Customer Support/BPO.

---

### 3.2 Data Schemas for All Deliverables

#### Deliverable 1: `regex_audit/filter_results/layer1_pandas_pass.jsonl`
Contains raw job objects that survived Layer 1 (Pandas Pre-Filter), augmented with replay metadata so Layer 2 can consume them seamlessly.
```typescript
interface Layer1PassRecord {
  job_index: number;              // 0 to 1136
  id: string;                     // UUID or job unique identifier
  title: string;                  // Clean job title
  company: string;                // Company name
  location: string;               // Location string
  description: string;           // Full job description text
  url: string;                    // Application / listing URL
  source: "indeed" | "linkedin";  // Scrape origin platform
  job_type: "fulltime" | "internship" | string;
  date_posted: string | null;     // ISO date string (YYYY-MM-DD) or null
  is_remote: boolean;             // Remote boolean flag
  scraped_at: string;             // ISO timestamp
  filter_layer: "pandas";         // Layer label
  status: "PASS";                 // Passed Layer 1
}
```

#### Deliverable 2: `regex_audit/filter_results/layer1_pandas_fail.jsonl`
Contains records dropped during Layer 1, detailing the exact rule and pattern triggered.
```typescript
interface Layer1FailRecord {
  job_index: number;              // 0 to 1136
  id: string;                     // Job UUID
  title: string;                  // Job title
  company: string;                // Company name
  filter_layer: "pandas";         // Fixed layer label
  rejection_reason:               // Standard rejection category
    | "empty_description"
    | "stale"
    | "location_mismatch"
    | "senior_title"
    | "experience_3_plus"
    | "duplicate_url"
    | "duplicate_company_title";
  rejection_detail: string;       // Human-readable explanation
  matched_pattern: string | null; // Regex pattern or criteria string that triggered rejection
}
```

#### Deliverable 3: `regex_audit/filter_results/layer2_regex_pass.jsonl`
Contains records that survived both Layer 1 and Layer 2 (would normally advance to AI scoring).
```typescript
interface Layer2PassRecord {
  job_index: number;              // 0 to 1136
  id: string;                     // Job UUID
  title: string;                  // Job title
  company: string;                // Company name
  location: string;               // Location string
  url: string;                    // Job URL
  filter_layer: "regex";          // Layer label
  status: "PASS";                 // Passed Layer 2
  matched_anchors: string[];      // Domain anchors matched in JD
  matched_tools: string[];        // Tech tools matched in JD
}
```

#### Deliverable 4: `regex_audit/filter_results/layer2_regex_fail.jsonl`
Contains records that passed Layer 1 but were dropped by Layer 2 Scorer Regex.
```typescript
interface Layer2FailRecord {
  job_index: number;              // 0 to 1136
  id: string;                     // Job UUID
  title: string;                  // Job title
  company: string;                // Company name
  filter_layer: "regex";          // Fixed layer label
  rejection_reason:               // Standard Layer 2 rejection category
    | "senior_title"
    | "out_of_scope_stack"
    | "experience_3_plus"
    | "irrelevant_jd";
  rejection_detail: string;       // Detailed reason explanation
  matched_pattern: string | null; // Regex pattern or missing keywords info
}
```

#### Deliverable 5: `regex_audit/evaluation/ground_truth.jsonl`
Contains exactly 1,137 lines (one per raw job). Serves as the authoritative gold standard.
```typescript
interface GroundTruthRecord {
  job_index: number;              // 0 to 1136 (strictly ordered)
  id: string;                     // Job UUID
  title: string;                  // Job title
  company: string;                // Company name
  location: string;               // Location
  expected_outcome: "PASS" | "FAIL"; // Gold standard ground-truth label
  actual_outcome_layer1: "PASS" | "FAIL"; // Result from baseline Layer 1
  actual_outcome_layer2: "PASS" | "FAIL"; // Result from baseline Layer 2 (or FAIL if dropped at Layer 1)
  is_correct: boolean;            // True if baseline pipeline decision matches expected_outcome
  flag_type: "false_positive" | "false_negative" | null;
  confidence: "high" | "medium" | "low";
  target_domain: string | null;   // e.g. "qa_automation", "java_backend", "mern_stack", "ai_ml", etc.
  notes: string;                  // Justification / rule applied
}
```

#### Deliverable 6: `regex_audit/evaluation/false_positives.jsonl`
Captures every job that passed the baseline filters (`actual_outcome_layer2 == 'PASS'`) but violates the candidate rubric (`expected_outcome == 'FAIL'`).
```typescript
interface FalsePositiveRecord {
  job_index: number;              // 0 to 1136
  id: string;                     // Job UUID
  title: string;                  // Job title
  company: string;                // Company name
  actual_decision: "PASS";        // Passed baseline filters
  expected_decision: "FAIL";      // Should have failed
  issue_type: "false_positive";
  reason: string;                 // Why job should have failed (e.g. requires 5 yrs, senior title missed)
  which_filter_failed: string;    // Function name that failed to catch it (e.g. matches_senior_title)
  root_cause: string;             // Detailed explanation of regex pattern gap
  specific_pattern_issue: string; // Specific regex boundary or missing pattern
}
```

#### Deliverable 7: `regex_audit/evaluation/false_negatives.jsonl`
Captures every legitimate entry-level target domain job that was rejected by baseline filters (`actual_outcome == 'FAIL'`) but should have passed (`expected_outcome == 'PASS'`).
```typescript
interface FalseNegativeRecord {
  job_index: number;              // 0 to 1136
  id: string;                     // Job UUID
  title: string;                  // Job title
  company: string;                // Company name
  actual_decision: "FAIL";        // Rejected by baseline
  expected_decision: "PASS";      // Valid candidate role
  issue_type: "false_negative";
  reason: string;                 // Why job should have passed (e.g. valid MERN fresher role)
  which_filter_rejected: string;  // Function name that rejected it (e.g. is_relevant_jd)
  rejection_layer: "layer1_pandas" | "layer2_regex";
  root_cause: string;             // Detailed cause (e.g. DOMAIN_ANCHORS lacks 'mern')
  specific_pattern_issue: string; // Exact missing keywords or overly strict pattern
}
```

#### Deliverable 8: `regex_audit/audit_report.md`
Markdown document detailing the root causes, statistics, and concrete proposed code modifications:
- **Structure:**
  1. Executive Summary & Audit Overview
  2. Dataset & Replay Statistics ($N=1137$, Layer 1 Drops, Layer 2 Drops, Final Baseline Passes)
  3. Discrepancy Breakdown (Total False Positives, Total False Negatives by category)
  4. Root Cause Analysis by Component:
     - `DOMAIN_ANCHORS` & `TECH_TOOLS` omissions (MERN, Express, MongoDB, Node, AI/ML, LLM, Agentic AI)
     - `matches_out_of_scope_role` over-eager matching on peripheral tech mentions in description
     - `matches_senior_title` edge cases (Roman numerals, qualifier preservation, multi-tier titles)
     - `requires_3_plus_years` boundary conditions (1-3 yrs preservation, degree/bond filtering, team experience)
     - Location & Deduplication quirks
  5. Proposed Regex & Scorer Diff (`scorer_v2.py` specifications) with before/after snippets
  6. Projected Impact & Risk Mitigation

#### Deliverables 9 & 10: `regex_audit/retest/v2_pass.jsonl` & `v2_fail.jsonl`
Pass and fail partitions of all 1,137 jobs when retested against `scorer_v2.py`.
```typescript
interface V2ResultRecord {
  job_index: number;
  id: string;
  title: string;
  company: string;
  v2_decision: "PASS" | "FAIL";
  matched_reasons?: string[];     // If fail: rejection reason list
  matched_keywords?: string[];    // If pass: matched anchors and tools
}
```

#### Deliverable 11: `regex_audit/retest/comparison_report.md`
Markdown document delivering the final objective validation against `ground_truth.jsonl`:
- **Structure:**
  1. Executive Verdict & Quality Gate Status
  2. Quantitative Evaluation Summary:
     - Total Raw Jobs Evaluated: 1,137
     - Agreement Rate: $\ge 95.0\%$ (Target: $\ge 1081 / 1137$)
     - Regressions on Legitimate Baseline Jobs: Exactly 0
     - False Positives Resolved: Count and %
     - False Negatives Resolved: Count and %
  3. Confusion Matrix:
     | Metric | Expected PASS | Expected FAIL | Total |
     |---|---|---|---|
     | **v2 PASS** | True Positives (TP) | False Positives (FP) | Total v2 Pass |
     | **v2 FAIL** | False Negatives (FN) | True Negatives (TN) | Total v2 Fail |
     | **Total** | Total Expected Pass | Total Expected Fail | 1,137 |
  4. Residual Edge Case Audit: Detailed documentation and justification for any remaining discrepancies ($\le 5\%$).

---

### 3.3 Quality Gates & Acceptance Criteria

| # | Quality Gate | Requirement / Metric | Target Value | Verification Method |
|---|---|---|---|---|
| **QG-1** | **Dataset Invariance** | Exactly 1,137 raw jobs used without re-scraping or modifications | Total rows = 1,137, IDs match master | `wc -l` or python len check on `master_raw_dataset_2026-09-29.jsonl` |
| **QG-2** | **Filter Replay Accounting** | Layer 1 Pass + Layer 1 Fail = 1,137; Layer 2 Pass + Layer 2 Fail = Layer 1 Pass | Exact record balance | Cross-count lines in `filter_results/*.jsonl` |
| **QG-3** | **Ground Truth Completeness** | Exactly 1,137 records in `ground_truth.jsonl`, ordered 0..1136 | Exactly 1,137 records, zero missing indices | `python -c "assert len(lines) == 1137"` |
| **QG-4** | **Discrepancy Attribution** | Every FP and FN has non-empty `root_cause`, `which_filter`, and `specific_pattern_issue` | 100% attributed | Schema validation script across `false_positives.jsonl` and `false_negatives.jsonl` |
| **QG-5** | **Production Code Immutability** | `src/scorer.py` and `src/scraper.py` remain completely untouched | Git clean / 0 diffs | `git diff --stat src/scorer.py src/scraper.py` |
| **QG-6** | **Deterministic Rewrite** | `regex_audit/scorer_v2.py` is 100% deterministic (no LLM, no HTTP, no random state) | 0 external calls, identical output across runs | Repeated execution diff |
| **QG-7** | **Accuracy Bar** | Agreement between `scorer_v2.py` and `ground_truth.jsonl` across all 1,137 jobs | **$\ge 95.0\%$** ($\ge 1081 / 1137$) | Retest execution script `regex_audit/run_retest.py` |
| **QG-8** | **Zero Regressions** | Legitimate entry-level target domain jobs that passed baseline must NOT fail in v2 | **0 regressions** | Set difference comparison between baseline TP and v2 TP |
| **QG-9** | **Domain Coverage** | MERN and AI/ML/LLM entry-level jobs must be recognized and pass | MERN & AI recovery $\ge 90\%$ | Check recovery rate of flagged MERN/AI false negatives |

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Raw Data Storage | Master Raw Preservation | Immutable storage of all 1,137 raw jobs captured during Phase 1 scrape | Scraper raw job stream | `master_raw_dataset_2026-09-29.jsonl` | Fails if re-scraped or files altered | `regex_audit_plan.md`, `ORIGINAL_REQUEST.md` |
| 2 | Layer 1 Pre-Filter | Description Null Check | Drops jobs with missing or whitespace-only descriptions | Job description string | Boolean (keep/drop) | Drops job if null or `desc.strip() == ""` | `src/scraper.py` lines 237-238 |
| 3 | Layer 1 Pre-Filter | Freshness Window | Drops jobs older than 72 hours while preserving missing/NaN dates | `date_posted`, `hours_old` config | Boolean (keep/drop) | Preserves NaN date_posted; drops if timestamp < cutoff | `src/scraper.py` lines 242-259 |
| 4 | Layer 1 Pre-Filter | Location Regional Aliasing | Matches target cities (`pune`, `mumbai`, `bangalore`) + regional aliases (`mh`, `ka`, `karnataka`, `maharashtra`) + remote | `location`, `is_remote` | Boolean (keep/drop) | Drops if not matching and not remote | `src/scraper.py` lines 260-275 |
| 5 | Layer 1 Pre-Filter | Title Seniority Check | Fast rejection of senior/lead/manager/principal titles before expensive parsing | `title` | Boolean (is senior) | Rejects if matching senior regex | `src/scraper.py` line 278, `src/scorer.py` line 137 |
| 6 | Layer 1 Pre-Filter | Experience Regex Check | Rejects JDs requiring $\ge 3$ years of candidate experience | `description` | Boolean (requires $\ge 3$) | Strips third-party history, preserves 1-3 yrs | `src/scraper.py` line 290, `src/scorer.py` line 191 |
| 7 | Layer 1 Pre-Filter | URL Deduplication | Drops duplicate job postings based on normalized URL | `url` | Cleaned DataFrame | Keeps first occurrence, drops duplicates | `src/scraper.py` lines 303-309 |
| 8 | Layer 1 Pre-Filter | Title-Company Deduplication | Drops duplicate postings with identical cleaned title and known company | `title`, `company` | Cleaned DataFrame | Skips dedup if company is unknown/null | `src/scraper.py` lines 312-320 |
| 9 | Layer 2 Regex Filter | Out-of-Scope Stack Check | Rejects tech stacks outside candidate target (PHP, Ruby, iOS, Android, Flutter, Salesforce, SAP) | `title`, `description` | Boolean (out of scope) | Currently triggers on ANY mention in JD | `src/scorer.py` lines 87-97 |
| 10 | Layer 2 Regex Filter | Domain Relevance Check | Zero-token relevance gate requiring $\ge 1$ domain anchor AND $\ge 1$ tech tool | `description`, `title` | Boolean (is relevant) | Drops if anchor or tool is missing, or out of scope | `src/scorer.py` lines 114-133 |
| 11 | Layer 2 Regex Filter | Boilerplate Stripping | Removes "About Us", "Benefits", "EEO" sections to optimize token payload | `description` | Cleaned string | Fallback to original if stripped too aggressively | `src/scorer.py` lines 100-112 |
| 12 | Evaluation | Ground Truth Generation | Comprehensive assignment of expected PASS/FAIL outcome to all 1,137 jobs | 1,137 raw jobs + candidate rubric | `ground_truth.jsonl` | Flags false positives and false negatives | `SCRAPING_AND_REGEX_TESTING.md`, Phase 4 |
| 13 | Audit Analysis | Regex Pattern Root-Cause Audit | Detailed pattern-level breakdown of false positive and negative causes | `false_positives.jsonl`, `false_negatives.jsonl` | `audit_report.md` | Documents specific deficient regex tokens | `regex_audit_plan.md`, Phase 5 |
| 14 | Rewritten Filter | Deterministic Scorer v2 | Enhanced standalone regex filter module with MERN, AI/LLM, and refined patterns | Raw job stream | Pass/Fail classification | Pure deterministic regex, 0 LLM calls | `regex_audit_plan.md`, Phase 6 |
| 15 | Verification | Retest & Comparison | Quantitative validation comparing v2 filter outputs against ground truth | `ground_truth.jsonl`, `scorer_v2.py` | `comparison_report.md`, `v2_pass.jsonl`, `v2_fail.jsonl` | Verifies $\ge 95.0\%$ match and 0 regressions | `ORIGINAL_REQUEST.md`, Phase 7 |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `is_relevant_jd` (MERN) | JD: "We are looking for a MERN developer skilled in React, Node, Express, MongoDB." Title: "MERN Developer" | Returns `False`. Defect: `DOMAIN_ANCHORS` lacks `mern`, `express`, `mongodb`, `node`. Causes False Negative. |
| 2 | `matches_out_of_scope_role` (Peripheral) | Title: "Java Developer", JD: "Java Spring Boot role. Experience with PHP is a plus." | Returns `True`. Defect: Searching whole description rejects valid backend Java jobs that mention legacy PHP. Causes False Negative. |
| 3 | `matches_senior_title` (Junior qualifier) | Title: "Senior / Junior Developer" or "Junior/Senior Software Engineer" | Returns `True`. Defect: Simple regex match on `\bsenior\b` overrides junior qualifier. |
| 4 | `matches_senior_title` (Roman Numerals) | Title: "Software Engineer II" | Returns `True`. In many tech companies, Level II is 1-2 years experience, but matches `\bii\b`. |
| 5 | `matches_senior_title` (Lead title) | Title: "Lead QA Engineer" | Returns `True`. Correctly flags senior role. |
| 6 | `matches_senior_title` (Entry range) | Title: "Software Engineer 0-2 years" | Returns `False`. Correctly preserved. |
| 7 | `matches_senior_title` (Senior range) | Title: "Software Engineer 3-5 years" | Returns `True`. Correctly rejected. |
| 8 | `requires_3_plus_years` (1-3 yrs preserved) | JD: "Requires 1-3 years of experience in Python." | Returns `False`. Correctly preserved (special safeguard for entry-level 1-3 yrs). |
| 9 | `requires_3_plus_years` (3+ yrs) | JD: "Requires 3+ years of experience in Python." | Returns `True`. Correctly rejected. |
| 10 | `requires_3_plus_years` (Company experience) | JD: "Our company has over 10 years of experience delivering cloud solutions." | Returns `False`. Correctly stripped by `third_party_prefixes`. |
| 11 | `requires_3_plus_years` (Degree duration) | JD: "Requires 3 years degree in Computer Science." | Returns `False`. Correctly stripped by educational safeguard pattern. |
| 12 | `requires_3_plus_years` (Service bond) | JD: "Must sign a 3 years bond upon joining." | Returns `False`. Correctly stripped by bond safeguard pattern. |
| 13 | `build_location_regex` (Regional abbreviations) | Location: "MH, IN" or "KA, IN" | Matches `\bmh,\s*in\b` and `\bka,\s*in\b`. Correctly preserved. |
| 14 | `build_location_regex` (Metros) | Location: "Bengaluru, Karnataka, India" or "Pune, Maharashtra, India" | Matches `\bbengaluru\b` and `\bpune\b`. Correctly preserved. |
| 15 | `build_location_regex` (Unknown location) | Location: "Unknown", `is_remote == False` | Returns `False`. Dropped by location filter in Layer 1. |
| 16 | Freshness filter (Missing date) | `date_posted: null` / `NaN` | Retained (not dropped). Matches production requirement to avoid losing jobs lacking timestamp metadata. |
| 17 | Deduplication (Duplicate URLs) | Two jobs from different search terms with identical normalized URL | Exactly one retained in Layer 1 Pass; duplicate sent to Layer 1 Fail (`duplicate_url`). |

---

## 4. Caveats

1. **Dataset Invariance**:
   The raw dataset was frozen on 2026-09-29 with 1,137 jobs. No live web queries or re-scraping should occur during execution of any subsequent phases.
2. **Deterministic Scorer Scope**:
   `scorer_v2.py` is strictly deterministic regex filtering. It replaces Layer 2 and fixes regex filters without making LLM calls or invoking DeepSeek. AI scoring occurs only in later production stages (which are explicitly out of scope for this audit).
3. **Duplicate Treatment in Ground Truth**:
   The 585 duplicate URLs in the raw dataset must be explicitly marked as `FAIL` with rejection reason `duplicate` in `ground_truth.jsonl` so that pipeline deduplication is scored as 100% compliant and accurate.

---

## 5. Conclusion

The specification mining for the Regex Job Filter Pipeline Audit & Optimization is complete and authoritative:
- The **Candidate Profile Rubric** establishes unambiguous PASS/FAIL criteria across 7 technical domains (including newly added MERN and AI/LLM), strict 0-2 / 1-3 year experience boundaries, anti-senior title rules, and target metro/remote locations.
- **Deliverable Data Schemas** have been fully specified for all 10 artifacts across `filter_results/`, `evaluation/`, and `retest/`, complete with TypeScript/JSON schema interfaces and markdown reporting structures.
- **Quality Gates** establish a hard $\ge 95.0\%$ accuracy target, 0 regressions on valid jobs, strict accounting across all 1,137 raw records, and total code immutability for `src/scorer.py` and `src/scraper.py`.

The downstream agents (`explorer_survey_filters_1`, `explorer_survey_dataset_1`, evaluator agents, and rewrite engineers) can immediately consume these specifications without ambiguity.

---

## 6. Verification Method

To independently verify this specification and its findings:
1. Verify raw dataset record count:
   ```powershell
   python -c "import json; f = open('regex_audit/master_raw_dataset_2026-09-29.jsonl', 'r', encoding='utf-8'); print('Count:', len(f.readlines()))"
   # Expected Output: Count: 1137
   ```
2. Verify code immutability:
   ```powershell
   git status src/scorer.py src/scraper.py
   # Expected: clean, no unstaged or staged changes
   ```
3. Verify test probes demonstrating current filter defects:
   ```powershell
   python -c "from src.scorer import is_relevant_jd, matches_out_of_scope_role; print('MERN check:', is_relevant_jd('MERN React Express MongoDB Node', 'MERN Dev')); print('PHP mention check:', matches_out_of_scope_role('Java Dev', 'Java Spring Boot. Legacy PHP is a plus.'))"
   # Expected Output: MERN check: False | PHP mention check: True
   ```
