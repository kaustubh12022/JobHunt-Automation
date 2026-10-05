# Dispatch: Evaluator Worker 1 (Batch 0..378)

## Identity
- Role: Profile Rubric Evaluator (Batch 1)
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_1
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Files to Read
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_1\handoff.md` (Candidate rubric specifications)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\master_raw_dataset_2026-09-29.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\filter_results\layer1_pandas_pass.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\filter_results\layer2_regex_pass.jsonl`

## Assigned Scope
Evaluate jobs with `job_index` from 0 to 378 (inclusive, 379 jobs total).

## Rubric Rules
1. PASS Criteria:
   - Target domain: Java/Spring, Python/Backend, QA/Testing/Automation, .NET/C#, Full Stack/SWE, MERN Stack (React, Express, MongoDB, Node.js), AI/ML/LLM/Agentic AI.
   - Location: Pune, Mumbai, Bangalore, or Remote/WFH/Hybrid/Pan-India.
   - Experience: 0-2 yrs, fresher, graduate, trainee, associate, 1-3 yrs (NEVER dropped), or unspecified.
   - NOT exclusively an out-of-scope stack (PHP, Ruby, iOS, Android, Flutter, React Native, Salesforce, SAP, Drupal, Magento, WordPress).
2. FAIL Criteria:
   - Senior / Lead / Manager / Principal / Director / Architect / Staff / Expert title (without junior qualification).
   - Requires 3+ years candidate experience.
   - Exclusively out-of-scope stack.
   - Non-technical role.
   - Outside India or non-target city without remote.
3. Compare expected outcome against actual Layer 1 and Layer 2 outcomes:
   - False Positive: passed Layer 2 (`layer2_regex_pass.jsonl`), but expected outcome is FAIL.
   - False Negative: expected outcome is PASS, but rejected in Layer 1 or Layer 2.

## Deliverable
Write `batch_eval_1.jsonl` in your working directory with entries containing:
`job_index`, `title`, `company`, `expected_outcome` ("PASS"|"FAIL"), `actual_outcome_layer1`, `actual_outcome_layer2`, `is_correct`, `flag_type` (null|"false_positive"|"false_negative"), `confidence` ("high"|"medium"|"low"), `notes`, `root_cause`, `specific_pattern_issue`.
Write `handoff.md` and send completion message to parent.
