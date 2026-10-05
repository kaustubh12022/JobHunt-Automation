# Dispatch: Worker Audit M3

## Identity
- Role: Regex Audit Report Author
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_audit_m3
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Files to Read
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_positives.jsonl` (8 records)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_negatives.jsonl` (10 records)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\ground_truth.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py` (READ-ONLY baseline)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py` (READ-ONLY baseline)

## Deliverables & Tasks
1. Conduct an in-depth root cause analysis for all 18 discrepancy jobs:
   - 8 False Positives: [336, 456, 510, 513, 563, 752, 796, 1038]
   - 10 False Negatives: [18, 84, 119, 169, 220, 246, 466, 687, 722, 1027]
2. Author `regex_audit/audit_report.md`:
   - Executive Summary & Overall Pipeline Performance (1,137 jobs, baseline accuracy 98.42%, 8 FPs, 10 FNs).
   - Pattern-Level Breakdown by Filter Component:
     - `DOMAIN_ANCHORS` & `TECH_TOOLS` (MERN & AI/LLM omissions, title evaluation in `is_relevant_jd`).
     - `matches_senior_title()` (`\bavp\b`, title qualifiers, career path suffixes like "Fast-Track to Tech Lead", "Advanced Engineer").
     - `requires_3_plus_years()` (handling company boilerplate like "ten years", "20 years of experience", age ranges like "(27 to 40 Yrs)", prefix regex over-eagerness).
     - `matches_out_of_scope_role()` (handling secondary/optional mentions of Kotlin, Flutter, Salesforce in descriptions).
   - Concrete Before / After Regex Diff Proposals for each component.
   - Affected Job Counts and projected impact for every proposed modification.
   - Risk Assessment and Guardrails against regressions.
3. Write `handoff.md` in your working directory and notify parent.

## 2026-09-29T15:56:37Z
You are worker_audit_m3.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_audit_m3
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).
Tasks:
Write the comprehensive root-cause analysis report in c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\audit_report.md detailing summary statistics, pattern-level breakdowns, concrete before/after regex diff proposals, and affected job counts.
Write your handoff report in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_audit_m3\handoff.md and notify parent with send_message.

