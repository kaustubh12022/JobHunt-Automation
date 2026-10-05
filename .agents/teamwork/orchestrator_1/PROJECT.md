# Project: Regex Filter Audit & Rewrite (Phases 2-7)

## Architecture
- Input: `regex_audit/master_raw_dataset_2026-09-29.jsonl` (1,137 jobs)
- Layer 1 Filter: Pandas pre-filter logic from `src/scraper.py` (empty desc, freshness >72h, location bounds, `matches_senior_title`, `requires_3_plus_years`, deduplication)
- Layer 2 Filter: Scorer regex filter logic from `src/scorer.py` (`matches_senior_title`, `matches_out_of_scope_role`, `requires_3_plus_years`, `is_relevant_jd`)
- Evaluation & Ground Truth: Multi-agent evaluation against candidate profile rubric (Fresher 0-2 yrs, target locations: Pune/Mumbai/Bangalore/Remote/WFH/Hybrid/Pan-India, target domains: Java/Spring, Python/Django/Flask, QA/Automation, .NET/C#, Full Stack, MERN, AI/ML/LLM; exclude out-of-scope stacks and senior/3+ yrs)
- Rewrite: `regex_audit/scorer_v2.py` with expanded DOMAIN_ANCHORS (MERN & AI/LLM), TECH_TOOLS, and refined regex rules without touching `src/scorer.py` or `src/scraper.py`.
- Retesting: `regex_audit/run_retest.py` verifying >= 95.0% accuracy vs ground truth and 0 regressions on valid jobs.

## Code Layout
- `regex_audit/master_raw_dataset_2026-09-29.jsonl` (Read-only source dataset)
- `src/scraper.py` (Read-only baseline)
- `src/scorer.py` (Read-only baseline)
- `regex_audit/filter_results/`:
  - `layer1_pandas_pass.jsonl`
  - `layer1_pandas_fail.jsonl`
  - `layer2_regex_pass.jsonl`
  - `layer2_regex_fail.jsonl`
- `regex_audit/evaluation/`:
  - `ground_truth.jsonl`
  - `false_positives.jsonl`
  - `false_negatives.jsonl`
- `regex_audit/audit_report.md`
- `regex_audit/scorer_v2.py`
- `regex_audit/run_retest.py`
- `regex_audit/retest/`:
  - `v2_pass.jsonl`
  - `v2_fail.jsonl`
  - `comparison_report.md`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Master Dataset Replay (Layer 1) | Replay 1,137 jobs through Pandas pre-filter rules deterministically | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Master Dataset Replay (Layer 2) | Replay Layer 1 survivors through Scorer regex rules deterministically | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Filter Results Artifacts | Generate layer1_pandas_pass/fail.jsonl and layer2_regex_pass/fail.jsonl with rejection reasons | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Multi-Agent Profile Evaluation | Evaluate all 1,137 jobs against Candidate Profile Rubric (including MERN, AI/LLM) | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Ground Truth Generation | Create ground_truth.jsonl with 1,137 entries with expected_outcome and confidence | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Discrepancy Attribution | Generate false_positives.jsonl & false_negatives.jsonl with specific root causes and pattern details | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Dynamic Regex Audit Report | Comprehensive root-cause analysis at regex_audit/audit_report.md with before/after diffs | M3 | ORIGINAL_REQUEST §R3 |
| 8 | Rewritten Deterministic Scorer | Implement regex_audit/scorer_v2.py with MERN, AI/LLM anchors, tools, and refined regex | M4 | ORIGINAL_REQUEST §R4 |
| 9 | Preserved Baselines | Ensure src/scorer.py and src/scraper.py remain completely untouched | M1-M5 | ORIGINAL_REQUEST AC |
| 10 | Deterministic Retest Runner | Implement regex_audit/run_retest.py executing 1,137 jobs through scorer_v2.py | M5 | ORIGINAL_REQUEST §R5 |
| 11 | Accuracy Benchmark | Achieve >= 95.0% match rate vs ground_truth.jsonl | M5 | ORIGINAL_REQUEST AC |
| 12 | Zero Regression Guarantee | Ensure zero regressions on legitimate entry-level target domain jobs | M5 | ORIGINAL_REQUEST AC |
| 13 | Retest Comparison Report | Output regex_audit/retest/comparison_report.md with complete metrics and residual analysis | M5 | ORIGINAL_REQUEST §R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 0 | Survey & Scope Mapping | Map dataset structure, baseline filter implementations, schemas | none | DONE |
| 1 | Two-Layer Filter Replay | Run Layer 1 & Layer 2 replays on 1,137 jobs; write filter_results/*.jsonl | M0 | DONE |
| 2 | Ground-Truth Dataset Creation | Multi-agent evaluation of 1,137 jobs against candidate rubric; output ground_truth.jsonl, false_positives.jsonl, false_negatives.jsonl | M1 | DONE |
| 3 | Dynamic Regex Audit Report | Produce regex_audit/audit_report.md with pattern breakdown, statistics, diff proposals | M2 | DONE |
| 4 | Deterministic Regex Rewrite | Implement regex_audit/scorer_v2.py with updated anchors/tools/regex | M3 | IN_PROGRESS |
| 5 | Retesting & Verification | Implement run_retest.py, achieve >=95% accuracy & 0 regressions, produce comparison_report.md | M4 | PLANNED |

## Interface Contracts
### Filter Replay Contract
- Input: `regex_audit/master_raw_dataset_2026-09-29.jsonl`
- Records: 1,137 JSON lines
- Replay outputs:
  - `layer1_pandas_pass.jsonl`: list of jobs passing layer 1
  - `layer1_pandas_fail.jsonl`: list of jobs failing layer 1 with `filter_layer="pandas"`, `rejection_reason`, `rejection_detail`, `matched_pattern`
  - `layer2_regex_pass.jsonl`: list of jobs passing layer 2
  - `layer2_regex_fail.jsonl`: list of jobs failing layer 2 with `filter_layer="regex"`, `rejection_reason`, `rejection_detail`, `matched_pattern`

### Ground Truth Contract
- File: `regex_audit/evaluation/ground_truth.jsonl`
- Count: Exactly 1,137 JSON lines
- Fields: `job_index` (int), `title` (str), `company` (str), `expected_outcome` ("PASS"|"FAIL"), `actual_outcome_layer1` ("PASS"|"FAIL"), `actual_outcome_layer2` ("PASS"|"FAIL"), `is_correct` (bool), `flag_type` (null|"false_positive"|"false_negative"), `confidence` ("high"|"medium"|"low"), `notes` (str)

### Scorer V2 Interface Contract
- File: `regex_audit/scorer_v2.py`
- Must provide clean, deterministic standalone functions matching or superseding `src/scorer.py`:
  - `matches_senior_title(title: str, description: str = "") -> bool`
  - `requires_3_plus_years(text: str) -> bool`
  - `matches_out_of_scope_role(title: str, description: str = "") -> bool`
  - `is_relevant_jd(description: str, title: str = "") -> bool`
- Must be 100% deterministic with no network or LLM dependencies.
