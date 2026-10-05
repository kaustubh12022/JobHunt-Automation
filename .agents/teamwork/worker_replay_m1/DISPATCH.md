# Dispatch: Worker Replay M1

## Identity
- Role: Implementation Worker (Filter Replay)
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_replay_m1
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Files to Read
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY: read first)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_1\handoff.md` (Deliverable schemas)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1\handoff.md` (Detailed filter logic & replay blueprint)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_dataset_1\handoff.md` (Dataset nuances & schema)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py` (READ-ONLY baseline)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py` (READ-ONLY baseline)

## Deliverables & Tasks
1. Create `regex_audit/run_filter_replay.py`.
   - Read all 1,137 jobs from `regex_audit/master_raw_dataset_2026-09-29.jsonl` (ensure UTF-8 encoding).
   - Implement Layer 1 (Pandas Pre-Filter) matching `src/scraper.py:209-354`:
     - Empty description check
     - Freshness check (>72h cutoff relative to pinned scrape time `2026-09-29T14:05:55Z`; parseable string "nan" treated as NaT/fresh)
     - Location check (target cities `['pune', 'mumbai', 'bangalore']` with aliases and remote bypass if `is_remote == True`)
     - `matches_senior_title`
     - `requires_3_plus_years`
     - Deduplication (Pass A: normalized URL; Pass B: clean title + company)
   - Save to:
     - `regex_audit/filter_results/layer1_pandas_pass.jsonl`
     - `regex_audit/filter_results/layer1_pandas_fail.jsonl`
   - Implement Layer 2 (Scorer Regex Filter) matching `src/scorer.py:337-352` on Layer 1 survivors:
     - `matches_senior_title`
     - `matches_out_of_scope_role`
     - `requires_3_plus_years`
     - `is_relevant_jd`
   - Save to:
     - `regex_audit/filter_results/layer2_regex_pass.jsonl`
     - `regex_audit/filter_results/layer2_regex_fail.jsonl`
2. Run `python regex_audit/run_filter_replay.py`.
3. Verify accounting identity:
   - Total Raw: exactly 1,137
   - Layer 1 Pass + Layer 1 Fail == 1,137
   - Layer 2 Pass + Layer 2 Fail == Layer 1 Pass
   - Schema correctness for each rejection record: `job_index`, `title`, `company`, `filter_layer`, `rejection_reason`, `rejection_detail`, `matched_pattern`.
4. Ensure `src/scraper.py` and `src/scorer.py` remain untouched.
5. Write `handoff.md` in your working directory and notify parent.

## 2026-09-29T15:18:35Z
Received dispatch from orchestrator_1:
- Implement regex_audit/run_filter_replay.py and execute it to generate the 4 JSONL files in regex_audit/filter_results/
- Ensure 100% accounting identity across all 1,137 jobs. Zero AI/LLM calls.
- Write completion report in handoff.md and notify parent with send_message.
