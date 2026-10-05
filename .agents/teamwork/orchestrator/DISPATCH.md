# Dispatch Instructions

## 2026-09-29T15:02:00Z

You are the Project Orchestrator for the project located at c:\Users\kalek\Desktop\Projects\Job_Hunt.
Your working directory is c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator.
The authoritative user request is recorded at c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md.

Read ORIGINAL_REQUEST.md carefully and orchestrate the team to fulfill all requirements (R1 through R5) and acceptance criteria:
- R1: Replay existing two-layer filtering on the 1,137 jobs in regex_audit/master_raw_dataset_2026-09-29.jsonl and record pass/fail in regex_audit/filter_results/.
- R2: Systematic evaluation against candidate profile & target domains; produce regex_audit/evaluation/ground_truth.jsonl (1,137 entries), false_positives.jsonl, and false_negatives.jsonl.
- R3: Root-cause audit report at regex_audit/audit_report.md.
- R4: Deterministic filter rewrite in regex_audit/scorer_v2.py (keep src/scorer.py and src/scraper.py untouched).
- R5: Retesting and objective verification against ground truth (>=95.0% accuracy), producing artifacts in regex_audit/retest/ and comprehensive report at regex_audit/retest/comparison_report.md.

CRITICAL DIRECTIVE: DO NOT re-scrape or re-generate the raw dataset. Use regex_audit/master_raw_dataset_2026-09-29.jsonl directly.
Maintain your BRIEFING.md and progress.md in your working directory. Notify me when completion is claimed.
