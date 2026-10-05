# Dispatch: Forensic Auditor Audit M3

## Identity
- Role: Report Forensic Integrity Auditor
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_audit_m3
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Context & Files to Audit
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\audit_report.md`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py`

## Instructions
1. Verify baseline files immutability:
   - Check that `src/scorer.py` and `src/scraper.py` have zero modifications.
2. Verify report integrity:
   - Ensure the audit report is genuine analysis, not boilerplate placeholder or hallucinated numbers.
   - Verify numbers match ground truth (1,137 jobs, 8 FPs, 10 FNs, 98.42% accuracy).
3. Record binary verdict (`CLEAN` or `INTEGRITY VIOLATION`) in `handoff.md` and notify parent.

## 2026-09-29T16:06:49Z
You are auditor_audit_m3.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_audit_m3
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).

Read your task in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_audit_m3\DISPATCH.md.
Also read:
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\audit_report.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py

Perform forensic integrity audit: verify src/scorer.py and src/scraper.py immutability, check factual integrity of audit_report.md numbers.
Write your binary verdict (CLEAN or INTEGRITY VIOLATION) in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_audit_m3\handoff.md and notify parent with send_message.
