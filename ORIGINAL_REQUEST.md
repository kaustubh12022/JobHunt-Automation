# Original User Request

## Initial Request — 2026-09-06T07:26:08Z

# Teamwork Project Prompt — Draft

> Status: Step 9 — Ready for launch — awaiting user approval.
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team

Completely audit, overhaul, and test the JobHunt-Automation pipeline to ensure high-quality job filtering, accurate AI scoring, and generation of highly tailored, 1-page ATS-friendly resumes at minimal AI cost.

Working directory: c:\Users\kalek\Desktop\Job_Hunt
Integrity mode: development

## Requirements

### R1. Pipeline Reliability & UI
- Ensure the pipeline completes without manual intervention.
- Add a **small-batch testing mode** for fast iteration without running the full 1-hour scraping cycle.
- Fix any broken flows, errors, or inconsistencies in the UI. All critical UI controls must be functional.

### R2. Scraping & Filtering Quality
- **Scraping**: Ensure no duplicates, correct platform attribution, and preserved JDs/URLs across a test set of 200+ jobs.
- **Filtering**: Optimize Pandas/Regex filters for recall first (do not drop relevant jobs), then precision (reject senior/irrelevant jobs).

### R3. AI Scoring
- Verify the scoring logic correctly distinguishes job relevance (Highly relevant to Irrelevant/Senior).
- Ensure the model selected in the UI is actually the one called by the API.

### R4. Resume Tailoring & ATS Compatibility
- Generate extremely well-matched, visually aesthetic, single-page resumes.
- Use a **best-fit role lens** (e.g., analyze general experience through the specific job's lens). Place relevant skills naturally; do not blindly keyword stuff.
- 0 fabricated qualifications (no hallucinations).
- Resumes must be 100% machine-readable (ATS-friendly) and exactly 1 page.

### R5. Token & Cost Efficiency
- Track every AI call (model, input/output/cached tokens, cost, stage).
- Eliminate all unnecessary AI calls.
- Use the cheapest model capable of achieving the quality required. Target a 30% AI cost reduction per successful resume vs the baseline.

### R6. Summary Artifact
- Create a beginner-friendly summary/walkthrough file explaining all changes, test results, cost improvements, UI updates, and subagents used.

## Acceptance Criteria

### Measurable Success Criteria
- [ ] **Pipeline reliability**: ≥ 95%
- [ ] **Scraping data integrity**: ≥ 98%
- [ ] **Relevant-job recall**: ≥ 98%
- [ ] **Senior/irrelevant rejection**: ≥ 90–95%
- [ ] **AI scoring agreement**: ≥ 90% (vs manual evaluation)
- [ ] **JD requirement coverage**: ≥ 95%
- [ ] **Resume hallucinations**: 0
- [ ] **Machine-readable resumes**: 100%
- [ ] **One-page resumes**: 100%
- [ ] **Visual QA pass**: 100%
- [ ] **Critical UI controls**: 100% functional
- [ ] **Unnecessary AI calls**: 0
- [ ] **AI cost reduction**: ≥ 30% vs baseline
- [ ] **End-to-end successful runs**: ≥ 95%

## 2026-09-06T08:17:16Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Multi-agent execution of JobHunt-Automation overhaul and verification
> Requested team: Full team

Audit, debug, overhaul, and verify the end-to-end JobHunt-Automation system for a single user (Indian fresher candidate) to achieve reliable 1-click job hunting: scraping, recall-first regex/pandas filtering, DeepSeek scoring, role-lens resume tailoring, 1-page ATS PDF generation, and Supabase integration at minimal token cost.

Working directory: c:\Users\kalek\Desktop\Job_Hunt
Integrity mode: development

## Credentials & Configuration Context
- **DeepSeek API Key**: `YOUR_DEEPSEEK_API_KEY`
  - Scoring Model: `deepseek-chat`
  - Resume Tailoring Model: `deepseek-reasoner`
- **Supabase Project**:
  - Project ID: `hysfjbecwcljddszcjui`
  - Project URL: `https://hysfjbecwcljddszcjui.supabase.co`
  - Publishable Key: `sb_publishable_UwSom1GLyDkoTDha4ykc-w__AO0LPaI`
- **Target Candidate Profile**: Fresher / Entry-level candidate in India (locations: Pune, Mumbai, Bangalore; terms: QA Automation, Java Developer, .NET Developer, Software Engineer, Backend Developer, Full Stack Developer).

---

## Requirements

### R1. Pipeline Reliability, Test Mode & Bug Fixes
- Fix all run-blocking bugs across the codebase:
  - Update invalid DeepSeek model names (e.g., replace deprecated/invalid names with `deepseek-chat` for scoring and `deepseek-reasoner` for tailoring).
  - Fix Windows dependency and runtime issues (e.g., numpy compilation/ABI issues, path issues, `.bat` script paths).
  - Broaden job freshness filter from 24 hours to 72 hours so valid opportunities aren't dropped.
  - Adjust default AI score threshold from 70 to 60 to prevent over-filtering.
  - Replace or fix non-functional scraper platforms in India (e.g., replace ZipRecruiter with Glassdoor if supported in JobSpy, or handle gracefully).
- Implement a dedicated **small-batch testing mode**:
  - Allows rapid end-to-end iteration (< 2 minutes) with a small, representative sample of jobs without running the full 1-hour scraping cycle.
- Ensure the pipeline can be safely rerun, handles failures with clear error messages, and achieves ≥ 95% run completion rate.

### R2. Scraping & Pre-AI Filtering Quality
- **Scraping Integrity**:
  - Audit and fix scraping pipeline across all enabled sources (LinkedIn, Indeed, Glassdoor/others).
  - Eliminate duplicate job entries, preserve complete job descriptions, and preserve valid apply URLs.
- **Recall-First Regex / Pandas Filtering**:
  - Prioritize **recall (≥ 98%)** so genuine fresher/entry-level jobs are never dropped.
  - Accurately filter out senior/lead/staff/manager positions and out-of-scope roles with target rejection of 90–95%.
  - Audit false positives and false negatives against a representative dataset of 200+ jobs.

### R3. AI Scoring Accuracy & Token Efficiency
- Verify that AI Scoring accurately distinguishes job relevance (highly relevant vs. borderline vs. irrelevant vs. senior).
- Ensure the model requested in configuration/UI matches the API call executed.
- Enforce strict token and cost optimization:
  - Cache prompt prefixes where applicable.
  - Do not send redundant JD text or unnecessary tokens.
  - Eliminate AI calls on jobs that should have been eliminated during pre-AI filtering.
  - Log model, input tokens, cached tokens, output tokens, cost, and pipeline stage for every call.

### R4. Role-Lens Resume Tailoring & Zero Hallucinations
- Implement a **best-fit role lens** tailoring mechanism:
  - Tailor the candidate's existing background (e.g., Full Stack / MEAN) to highlight genuinely applicable skills and projects for the specific target role (e.g., Data Science, QA Automation, Backend).
  - Place relevant skills naturally within project and experience bullet points rather than superficial keyword stuffing.
  - Keep strong, relevant projects and experience rather than arbitrarily stripping them down.
- **Strict Anti-Hallucination Guardrail**:
  - Exactly 0 fabricated skills, certifications, degrees, or experiences. Every claim must stem from the master profile.
  - ≥ 95% of genuinely applicable JD requirements present in master profile must be reflected in the final resume.

### R5. 1-Page ATS-Friendly Resume PDF Generation
- Redesign the resume template to a modern, clean sans-serif layout with subtle blue accent styling.
- Ensure 100% ATS machine-readability (extractable, parseable text, standard headings, correct reading order, no embedded text images).
- Enforce a strict **single-page constraint** without CSS `transform: scale()` or hacky shrinking that degrades ATS parsing or visual hierarchy.
- Ensure 100% visual QA pass: clean margins, no overflowing text, no awkward page breaks or clipped sections.

### R6. Supabase Integration & UI Audit
- Configure and test Supabase connection using the provided project credentials. Store processed jobs, tailored resumes, and metadata.
- Audit the web UI (Streamlit / Flask / HTML):
  - Ensure every button, input, toggle, and trigger operates without unhandled exceptions.
  - Provide clear loading states, progress feedback, and error reporting.

### R7. Comprehensive Verification & Beginner-Friendly Final Summary
- Build automated test/verification scripts:
  - Verify regex recall/precision on 200+ job dataset.
  - Verify ATS readability and single-page constraint on generated PDFs.
  - Verify token usage and cost reduction (target ≥ 30% savings vs baseline).
  - Verify zero-hallucination compliance.
- Produce a clear, beginner-friendly summary and walkthrough document detailing:
  - What was originally broken.
  - What changes were made and why.
  - Verification results and metrics achieved.
  - Step-by-step instructions on running both test mode and the full 1-click production pipeline.
  - Roles and discoveries of subagents involved.

---

## Acceptance Criteria

### Pipeline & Filtering
- [ ] Pipeline runs end-to-end with 1 click without manual intervention (≥ 95% reliability across repeated runs).
- [ ] Small-batch test mode executes end-to-end in < 2 minutes.
- [ ] Scraping data integrity ≥ 98% (no duplicates, preserved JDs, valid URLs).
- [ ] Pre-AI regex/pandas filter achieves ≥ 98% recall for relevant fresher jobs and 90–95% rejection of senior/out-of-scope roles.

### AI Scoring & Tailoring
- [ ] AI scoring reflects true relevance with ≥ 90% manual evaluation agreement.
- [ ] 0 fabricated qualifications or experiences in generated resumes (100% truthful).
- [ ] ≥ 95% coverage of genuinely applicable JD requirements using the best-fit role lens.
- [ ] DeepSeek model parameters, endpoints, and token counts are correctly configured (`deepseek-chat` for scoring, `deepseek-reasoner` for tailoring).
- [ ] ≥ 30% reduction in AI cost per successful resume compared to unoptimized baseline, with 0 unnecessary AI calls.

### Resume PDF & ATS
- [ ] 100% of generated resumes extract clean, structured plain text with standard section headers.
- [ ] 100% of generated resumes fit exactly on 1 page without CSS scale hacks or visual overflow.
- [ ] 100% pass on visual design audit (modern typography, blue accents, clean whitespace).

### Storage & UI
- [ ] Supabase database connection and schema successfully store jobs and tailored resumes.
- [ ] 100% of critical UI buttons and controls functional with appropriate status feedback.
- [ ] Beginner-friendly final walkthrough artifact completed with detailed before/after explanations.

## Follow-up — 2026-09-06T14:07:06Z

just 1 thing for testing try to use original data like for real world testing and try to use less api calls for testing

## Follow-up — 2026-09-06T14:09:14Z

USER CLARIFICATION: The user specifically means to minimize **DeepSeek API calls** (the job scoring and reasoner tailoring calls) during the test suites to save money/cost. Ensure that your automated tests use real-world data but minimize hitting the live DeepSeek API, e.g., by testing the core logic locally or aggressively caching the test responses.
## Follow-up — 2026-09-06T15:01:24Z

USER COMMAND: Skip Milestone 7 entirely. Do not run the final E2E test or Victory Audit. Immediately generate the final summary documentation artifact (detailing all agents used, their tasks, and the exact code changes made). Once the document is generated, gracefully terminate your execution. The user wants to manually run the pipeline.

## Follow-up — 2026-09-29T15:01:02Z

Audit and rewrite the regex filtering pipeline for the AutoApply job hunting system using the existing 1,137-job master raw dataset. Replay existing filter layers, identify all false positives and false negatives against the candidate profile, generate a ground-truth dataset, rewrite the filter logic in regex_audit/scorer_v2.py, and verify >=95% accuracy against ground truth.

Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt
Integrity mode: development

CRITICAL DIRECTIVE: DO NOT re-scrape or re-generate the raw dataset. The complete 1,137-job raw dataset has already been successfully scraped, verified, and stored at regex_audit/master_raw_dataset_2026-09-29.jsonl (and regex_audit/master_raw_dataset_2026-09-29.json). Load and use this existing dataset directly for all tasks.

## Candidate Profile & Domain Scope
- Candidate: Kaustubh Kale (Fresher, BE IT 2026, Pune, India)
- Target Domains (Valid Passes):
  1. Java / Spring / Backend Development
  2. Python / Django / Flask / Backend
  3. QA / Testing / Automation (Selenium, JUnit, Postman, pytest)
  4. .NET / C# / ASP.NET
  5. Full Stack / Software Engineering (general)
  6. MERN Stack (React, Express, MongoDB, Node.js)
  7. AI / ML / LLM / Agentic AI
- Valid Locations: Pune, Mumbai, Bangalore, or Remote / Hybrid / WFH / Pan-India
- Experience Requirement: 0-2 years, fresher, graduate, or unspecified (drop if strictly requires 3+ years)

---

## Requirements

### R1. Replay Existing Two-Layer Filtering
Replay the 1,137 raw jobs from regex_audit/master_raw_dataset_2026-09-29.jsonl through the existing filters without any AI/LLM scoring:
- Layer 1 (Pandas Pre-Filter): Empty description, freshness (>72h), location bounds, senior title (matches_senior_title), experience (requires_3_plus_years), and cross-platform deduplication.
- Layer 2 (Scorer Regex Filter): Senior titles, out-of-scope stacks (matches_out_of_scope_role), high experience, and domain relevance (is_relevant_jd).
Record the exact pass/fail decision and matching pattern for each job into:
- regex_audit/filter_results/layer1_pandas_pass.jsonl & layer1_pandas_fail.jsonl
- regex_audit/filter_results/layer2_regex_pass.jsonl & layer2_regex_fail.jsonl

### R2. Systematic Evaluation & Ground-Truth Dataset Creation
Evaluate all 1,137 jobs against the candidate profile and target domains:
- Identify False Positives: Jobs that passed regex filters but are senior, out-of-domain, or non-technical.
- Identify False Negatives: Jobs that should have passed based on profile (including MERN and AI/LLM) but were rejected by existing filters.
- Generate a unified regex_audit/evaluation/ground_truth.jsonl containing the expected outcome (PASS or FAIL) for every single job with confidence and reasoning.

### R3. Regex Filter Root-Cause Audit
Analyze the specific regex patterns and keyword lists responsible for false positives and false negatives:
- Analyze DOMAIN_ANCHORS and TECH_TOOLS deficiencies (e.g. missing MERN/AI terms).
- Analyze matches_senior_title and requires_3_plus_years boundary and false-rejection cases.
- Produce an actionable markdown audit report at regex_audit/audit_report.md detailing exact before/after regex modifications.

### R4. Deterministic Filter Rewrite (scorer_v2.py)
Implement the cleaned and enhanced regex filter logic in regex_audit/scorer_v2.py without modifying the original src/scorer.py or using any LLM:
- Update domain anchor and tech tool sets to recognize MERN and AI/LLM roles.
- Fix regex pattern edge cases for experience and senior title detection.
- Provide clean, deterministic standalone functions matching the existing filter interface.

### R5. Retesting & Objective Verification Against Ground Truth
Execute the entire 1,137-job raw dataset through regex_audit/scorer_v2.py:
- Programmatically compare new regex outputs against regex_audit/evaluation/ground_truth.jsonl.
- Verify that overall accuracy meets or exceeds the 95% threshold.
- Output detailed pass/fail artifacts in regex_audit/retest/ and a comprehensive comparison report in regex_audit/retest/comparison_report.md.

---

## Acceptance Criteria

### Execution & Artifacts
- [ ] Layer 1 and Layer 2 replay files exist and account for all 1,137 records.
- [ ] regex_audit/evaluation/ground_truth.jsonl contains exactly 1,137 verified entries with expected outcomes.
- [ ] regex_audit/evaluation/false_positives.jsonl and false_negatives.jsonl contain specific root causes and pattern details for every flagged job.
- [ ] regex_audit/audit_report.md thoroughly documents pattern deficiencies and proposed fixes.
- [ ] regex_audit/scorer_v2.py is fully implemented, syntactically valid, and operates 100% deterministically without external LLM calls.
- [ ] Original files (src/scorer.py, src/scraper.py) remain untouched.

### Quantitative Quality Bar
- [ ] Retest script runs deterministically across all 1,137 jobs.
- [ ] New regex filter output achieves >= 95.0% agreement with ground_truth.jsonl.
- [ ] Zero regressions on legitimate entry-level target domain jobs that originally passed.
- [ ] regex_audit/retest/comparison_report.md contains exact metrics: total jobs, match rate, false positives resolved, false negatives resolved, and detailed analysis of any remaining edge cases.

## Follow-up — 2026-09-29T15:09:21Z

Execute the complete Regex Filter Audit & Rewrite plan (Phases 2 through 7) as specified in `SCRAPING_AND_REGEX_TESTING.md` and `regex_audit_plan.md`, using the captured raw dataset of 1,137 jobs.

Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt
Integrity mode: development

## Reference Material
- Master Plan: `c:\Users\kalek\Desktop\Projects\Job_Hunt\context\SCRAPING_AND_REGEX_TESTING.md`
- Implementation Plan: `C:\Users\kalek\.gemini\antigravity\brain\0d78065d-672a-4019-8e92-63a175ebef44\regex_audit_plan.md`
- Master Raw Dataset (Phase 1 complete): `regex_audit/master_raw_dataset_2026-09-29.jsonl` (1,137 jobs)
- Original Scorer: `src/scorer.py` (Must remain untouched)
- Original Scraper: `src/scraper.py` (Must remain untouched)

## Requirements

### R1. Two-Layer Filter Replay (Phase 2)
Replay both filtering layers deterministically on all 1,137 raw jobs from `regex_audit/master_raw_dataset_2026-09-29.jsonl`.
- **Layer 1 (Pandas Pre-filter):** Evaluate empty descriptions, freshness (>72h), location regex, `matches_senior_title()`, `requires_3_plus_years()`, and deduplication. Output `regex_audit/filter_results/layer1_pandas_pass.jsonl` and `layer1_pandas_fail.jsonl` with structured rejection reasons.
- **Layer 2 (Scorer Regex Filter):** Replay on Layer 1 survivors using `matches_senior_title()`, `matches_out_of_scope_role()`, `requires_3_plus_years()`, and `is_relevant_jd()`. Output `regex_audit/filter_results/layer2_regex_pass.jsonl` and `layer2_regex_fail.jsonl`.
- Complete stop after Layer 2: No LLM/AI scoring or resume generation.

### R2. Multi-Agent Ground-Truth Evaluation (Phases 3 & 4)
Evaluate each of the 1,137 jobs against the locked Candidate Profile Rubric:
- Fresher / 0-2 yrs experience, target locations (Pune, Mumbai, Bangalore, Remote/WFH/Hybrid/Pan-India), valid target domains (Java/Spring, Python/Django/Flask, QA/Automation/Testing, .NET/C#, Full Stack, Software Engineering, MERN stack [React/Express/Node/MongoDB], AI/ML/LLM/Agentic AI).
- Exclude out-of-scope stacks (PHP, Ruby, iOS, Android, Flutter, React Native, Salesforce, SAP, Drupal, Magento, WordPress) and senior roles / 3+ years experience.
- Flag all discrepancies into `regex_audit/evaluation/false_positives.jsonl` and `regex_audit/evaluation/false_negatives.jsonl`.
- Compile all 1,137 evaluations into `regex_audit/evaluation/ground_truth.jsonl` matching the defined JSONL schema.

### R3. Dynamic Regex Audit Report (Phase 5)
Conduct a deep-dive root cause analysis on all flagged issues:
- Identify patterns causing false positives (e.g., regex boundary issues, missing exclusions) and false negatives (e.g., missing MERN / AI keywords in `DOMAIN_ANCHORS` and `TECH_TOOLS`).
- Generate `regex_audit/audit_report.md` detailing summary statistics, pattern-level breakdowns, before/after diff proposals, and affected job counts.

### R4. Deterministic Regex Rewrite & Retesting (Phases 6 & 7)
Implement fixed deterministic regex filters in `regex_audit/scorer_v2.py`:
- Incorporate expanded `DOMAIN_ANCHORS` (MERN, AI/LLM), `TECH_TOOLS` (express, mongodb, node, etc.), and refined title/experience regex patterns. Keep `src/scorer.py` and `src/scraper.py` untouched.
- Create and execute `regex_audit/run_retest.py` to replay the 1,137 jobs through `scorer_v2.py` and compare against `ground_truth.jsonl`.
- Generate `regex_audit/retest/comparison_report.md` with pass/fail metrics.

## Acceptance Criteria

### Filter Replay & Preservation
- [ ] Exactly 1,137 jobs from `regex_audit/master_raw_dataset_2026-09-29.jsonl` are replayed through Layer 1 and Layer 2.
- [ ] `regex_audit/filter_results/` contains `layer1_pandas_pass.jsonl`, `layer1_pandas_fail.jsonl`, `layer2_regex_pass.jsonl`, and `layer2_regex_fail.jsonl` adhering to schema.
- [ ] No changes are made to `src/scorer.py` or `src/scraper.py`.

### Ground Truth Integrity
- [ ] `regex_audit/evaluation/ground_truth.jsonl` contains exactly 1,137 valid JSON lines with `expected_outcome` ('PASS' or 'FAIL').
- [ ] `false_positives.jsonl` and `false_negatives.jsonl` contain specific filter attribution and root cause details for every discrepancy.

### Audit & Rewrite
- [ ] `regex_audit/audit_report.md` provides root-cause analysis and proposed regex diffs.
- [ ] `regex_audit/scorer_v2.py` is created with updated `DOMAIN_ANCHORS` (including MERN and AI/LLM), `TECH_TOOLS`, and refined experience/title filters.

### Retest Verification
- [ ] Retest script `regex_audit/run_retest.py` runs deterministically without network or AI API dependencies.
- [ ] Retest match rate between `scorer_v2.py` and `ground_truth.jsonl` achieves ≥ 95.0%.
- [ ] Zero regressions introduced on previously correct baseline decisions.
- [ ] `regex_audit/retest/comparison_report.md` is generated detailing all metrics, fixes, and residual edge cases.

## Follow-up — 2026-09-29T16:37:31Z

Execute an end-to-end AI Scoring Phase Audit and Multi-Provider Fix for the job hunting automation pipeline using Gemini and Groq APIs, strictly excluding DeepSeek. Generate synthetic test datasets, audit scoring accuracy, cross-validate provider agreement, engineer an optimized scoring prompt v2, re-score, and integrate multi-provider support into production.

Working directory: C:\Users\kalek\Desktop\Projects\Job_Hunt
Integrity mode: development

## Requirements

### R1. Synthetic Benchmark Dataset Generation
Generate a diverse, realistic dataset of 300 synthetic job descriptions across 15 distinct categories (20 JDs each, covering target domains like Java/Spring, QA/Automation, MERN, AI/ML/LLM, as well as traps, sparse, and out-of-scope roles) with pre-determined ground-truth expected score ranges and classification flags, saved to `scoring_audit/synthetic_jds.json`.

### R2. Dual-Provider Scoring Engine (Gemini & Groq Only)
Implement `scoring_audit/ai_engine_v2.py` supporting Gemini (`gemini-2.0-flash` or current free tier) and Groq (`llama-3.3-70b-versatile` or Groq fast models) using API keys from `.env`. Strictly forbid any calls or fallbacks to DeepSeek. Enforce client-side rate limiters (Gemini <= 15 RPM, Groq <= 30 RPM), exponential retries, and strict JSON response schema extraction.

### R3. Dual-Provider Baseline Scoring Execution
Execute scoring with the baseline prompt `src/prompts/scoring_prompt.txt` across:
1. All 300 synthetic benchmark JDs independently via both Gemini and Groq.
2. The ~73 real production jobs surviving regex filtering from `regex_audit/` or master dataset.
Persist structured scoring logs to `scoring_audit/scores/`.

### R4. Cross-Validation & Deficiencies Analysis
Conduct a forensic audit comparing provider scores against synthetic ground-truth ranges and between providers (Gemini vs. Groq ±10 point threshold). Audit `missing_skills` accuracy against the candidate's resume and `is_testing_role` classification. Produce comprehensive Markdown audit reports in `scoring_audit/analysis/`.

### R5. Prompt Optimization (v2) & Benchmark Verification
Engineer `scoring_audit/scoring_prompt_v2.txt` to fix identified failure modes (specifically under-scoring of MERN stack and AI/ML/LLM roles, score compression, and false missing skills). Re-score the entire synthetic and real job datasets with v2, generating a comparative metrics report proving measurable accuracy improvements.

### R6. Production Multi-Provider Integration
Update `src/ai_engine.py` and `config.yaml` to support configurable provider selection (`gemini` or `groq`) with rate limiting and automated fallback, while keeping original baseline files backed up and strictly avoiding any DeepSeek API calls.

## Acceptance Criteria

### API Security & Compliance
- [ ] Strictly zero calls made to DeepSeek API; only Gemini and Groq API keys are utilized.
- [ ] Rate limits are strictly respected without encountering unhandled 429 quota exhaustion.

### Scoring Accuracy & Consistency
- [ ] Synthetic category accuracy with prompt v2 reaches >= 90% of scores within expected ground-truth ranges.
- [ ] Cross-provider agreement between Gemini and Groq is >= 80% within a ±10 point threshold.
- [ ] `is_testing_role` classification accuracy is >= 95% on synthetic benchmark test cases.
- [ ] `missing_skills` accuracy is >= 85% (flagged skills are genuinely missing from candidate profile).

### Deliverables & Artifacts
- [ ] 300 synthetic JDs saved in `scoring_audit/synthetic_jds.json`.
- [ ] Raw score logs saved in `scoring_audit/scores/` for synthetic and real jobs across both providers (v1 and v2).
- [ ] Audit reports produced in `scoring_audit/analysis/` detailing discrepancy attribution and v1 vs v2 improvements.
- [ ] Optimized prompt saved at `scoring_audit/scoring_prompt_v2.txt`.
- [ ] Production engine `src/ai_engine.py` updated with multi-provider support and verified with automated tests.

