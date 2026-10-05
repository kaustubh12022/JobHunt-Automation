# Dispatch: Reviewer GT 1

## Identity
- Role: Ground Truth Reviewer
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_gt_1
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Context & Files to Review
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_1\handoff.md` (Ground truth schema specifications)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\ground_truth.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_positives.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_negatives.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\compile_ground_truth.py`

## Instructions
1. Verify line count: exactly 1,137 lines in `ground_truth.jsonl` (indices 0..1136 strictly sequential).
2. Verify line counts: exactly 8 entries in `false_positives.jsonl` and 10 entries in `false_negatives.jsonl`.
3. Check schema adherence of every JSON line.
4. Verify that the 18 flagged jobs have sensible and accurate candidate rubric justifications.
5. Record verdict (`APPROVE` or `REQUEST_CHANGES`) in `handoff.md` and notify parent.

## 2026-09-29T15:49:37Z
You are reviewer_gt_1.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_gt_1
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).

Read your task in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_gt_1\DISPATCH.md.
Also read:
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_1\handoff.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\ground_truth.jsonl
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_positives.jsonl
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_negatives.jsonl
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\compile_ground_truth.py

Verify line counts, schemas, and candidate profile rubric evaluations.
Write your verdict (APPROVE or REQUEST_CHANGES) in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_gt_1\handoff.md and notify parent with send_message.
