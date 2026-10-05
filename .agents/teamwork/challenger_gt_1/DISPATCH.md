# Dispatch: Challenger GT 1

## Identity
- Role: Ground Truth Challenger & Empirical Stress Tester
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\challenger_gt_1
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Context & Files to Test
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\ground_truth.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_positives.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_negatives.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\master_raw_dataset_2026-09-29.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\test_ground_truth.py`

## Instructions
1. Run automated tests (`python -m pytest regex_audit/test_ground_truth.py`).
2. Empirically verify 1:1 join between `master_raw_dataset_2026-09-29.jsonl` and `ground_truth.jsonl`:
   - Check that `title`, `company`, `job_index` match exactly on all 1,137 records.
   - Verify that `false_positives` indices match `[row['job_index'] for row in ground_truth if row['flag_type'] == 'false_positive']`.
   - Verify that `false_negatives` indices match `[row['job_index'] for row in ground_truth if row['flag_type'] == 'false_negative']`.
3. Check for any corrupted JSON lines or malformed fields.
4. Record verdict (`APPROVE` or `CHALLENGE_FAILED`) in `handoff.md` and notify parent.

## 2026-09-29T15:49:37Z
You are challenger_gt_1.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\challenger_gt_1
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).

Read your task in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\challenger_gt_1\DISPATCH.md.
Also read:
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\ground_truth.jsonl
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_positives.jsonl
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_negatives.jsonl
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\master_raw_dataset_2026-09-29.jsonl
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\test_ground_truth.py

Run test_ground_truth.py, verify 1:1 join with raw dataset, check integrity of all 1,137 records.
Write your verdict (APPROVE or CHALLENGE_FAILED) in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\challenger_gt_1\handoff.md and notify parent with send_message.
