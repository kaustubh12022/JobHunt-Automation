# Dispatch: Worker GT Builder

## Identity
- Role: Ground Truth Compiler & Validator Worker
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_gt_builder
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Files to Read
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_1\handoff.md` (Schemas for ground_truth, false_positives, false_negatives)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_1\batch_eval_1.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_2\batch_eval_2.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_3\batch_eval_3.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\filter_results\layer1_pandas_pass.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\filter_results\layer2_regex_pass.jsonl`

## Deliverables & Tasks
1. Create `regex_audit/compile_ground_truth.py`.
2. Execute the script to compile and write:
   - `regex_audit/evaluation/ground_truth.jsonl`: Exactly 1,137 lines, indexed 0..1136 sequentially.
     Schema: `job_index`, `title`, `company`, `expected_outcome` ("PASS"|"FAIL"), `actual_outcome_layer1` ("PASS"|"FAIL"), `actual_outcome_layer2` ("PASS"|"FAIL"), `is_correct` (bool), `flag_type` (null|"false_positive"|"false_negative"), `confidence` ("high"|"medium"|"low"), `notes` (str).
   - `regex_audit/evaluation/false_positives.jsonl`: Exactly 8 records.
     Schema: `job_index`, `title`, `company`, `actual_decision`, `expected_decision`, `issue_type`, `reason`, `which_filter_failed`, `root_cause`, `specific_pattern_issue`.
   - `regex_audit/evaluation/false_negatives.jsonl`: Exactly 10 records.
     Schema: `job_index`, `title`, `company`, `actual_decision`, `expected_decision`, `issue_type`, `reason`, `which_filter_rejected`, `rejection_layer`, `root_cause`, `specific_pattern_issue`.
3. Verify that all 1,137 indices are present, valid JSON on every line, and 100% schema compliant.
4. Ensure `src/scraper.py` and `src/scorer.py` remain untouched.


## 2026-09-29T15:43:28Z
You are worker_gt_builder.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_gt_builder
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).
Compile and generate:
1. regex_audit/evaluation/ground_truth.jsonl (exactly 1,137 records, indexed 0..1136 sequentially)
2. regex_audit/evaluation/false_positives.jsonl (the 8 flagged false positive jobs)
3. regex_audit/evaluation/false_negatives.jsonl (the 10 flagged false negative jobs)
Verify 100% schema compliance, valid JSON on every line, and 0 missing indices.
Write your handoff report in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_gt_builder\handoff.md and notify parent with send_message.
