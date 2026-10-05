# Dispatch: Forensic Auditor Rewrite M4

## Identity
- Role: Scorer V2 Forensic Integrity Auditor
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_rewrite_m4
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Context & Files to Audit
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\scorer_v2.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py`

## Instructions
Execute forensic checks:
1. Static code analysis of `regex_audit/scorer_v2.py`:
   - Verify absence of hardcoded job IDs, company lookups, title-specific cheats, or artificial if/else branches tied to dataset indices.
   - Verify zero network/API calls (no LLM, no external requests).
2. Baselines immutability check:
   - Verify `src/scorer.py` and `src/scraper.py` are strictly untouched.
3. Verify that all logic in `scorer_v2.py` is genuine, generalized, and reusable regex filtering.
4. Record binary verdict (`CLEAN` or `INTEGRITY VIOLATION`) in `handoff.md` and notify parent.

## 2026-09-29T16:42:45Z
You are auditor_rewrite_m4.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_rewrite_m4
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).

Read your task in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_rewrite_m4\DISPATCH.md.
Also read:
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\scorer_v2.py
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py

Conduct forensic integrity audit: static AST analysis for hardcoded answers or index cheats, verify zero network/LLM dependencies, and verify immutability of src/scorer.py and src/scraper.py.
Write your binary verdict (CLEAN or INTEGRITY VIOLATION) in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\auditor_rewrite_m4\handoff.md and notify parent with send_message.
