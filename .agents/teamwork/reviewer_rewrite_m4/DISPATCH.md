# Dispatch: Reviewer Rewrite M4

## Identity
- Role: Scorer V2 Code Reviewer
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_rewrite_m4
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Context & Files to Review
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\scorer_v2.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\test_scorer_v2.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\audit_report.md`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py` (Verify untouched)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py` (Verify untouched)

## Instructions
1. Review `regex_audit/scorer_v2.py`:
   - Verify code quality, deterministic behavior, and interface conformity:
     - `matches_senior_title(title: str, description: str = "") -> bool`
     - `requires_3_plus_years(text: str) -> bool`
     - `matches_out_of_scope_role(title: str, description: str = "") -> bool`
     - `is_relevant_jd(description: str, title: str = "") -> bool`
   - Verify expanded `DOMAIN_ANCHORS` (MERN, AI/LLM) and `TECH_TOOLS`.
   - Verify zero external network or LLM dependencies.
2. Verify `test_scorer_v2.py` execution.
3. Verify `src/scorer.py` and `src/scraper.py` remain untouched.
4. Record verdict (`APPROVE` or `REQUEST_CHANGES`) in `handoff.md` and notify parent.

## 2026-09-29T16:42:45Z
You are reviewer_rewrite_m4.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_rewrite_m4
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).

Read your task in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_rewrite_m4\DISPATCH.md.
Also read:
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\scorer_v2.py
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\test_scorer_v2.py
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py (verify untouched)
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py (verify untouched)

Review code quality, deterministic interface compliance, and test suite execution.
Write your verdict (APPROVE or REQUEST_CHANGES) in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_rewrite_m4\handoff.md and notify parent with send_message.
