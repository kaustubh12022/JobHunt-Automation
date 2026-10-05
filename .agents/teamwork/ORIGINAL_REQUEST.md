# Original User Request

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
