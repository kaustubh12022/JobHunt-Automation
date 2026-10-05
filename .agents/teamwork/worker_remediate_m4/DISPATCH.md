# Dispatch: Worker Remediate M4

## Identity
- Role: Scorer V2 Remediation Worker
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_remediate_m4
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Files to Read
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\scorer_v2.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_rewrite_m4\handoff.md` (Contains exact code fixes)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\challenger_rewrite_m4\handoff.md`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\test_scorer_v2.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py` (READ-ONLY baseline)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py` (READ-ONLY baseline)

## Required Remediation in `regex_audit/scorer_v2.py`
1. **Type Guards for Non-String Inputs**:
   In `matches_out_of_scope_role`, `is_relevant_jd`, `matches_senior_title`, and `requires_3_plus_years`, ensure inputs are safely guarded:
   ```python
   if not isinstance(title, str):
       title = "" if title is None or pd.isna(title) else str(title)
   if not isinstance(description, str):
       description = "" if description is None or pd.isna(description) else str(description)
   ```
2. **Case Normalization in `_match_keyword`**:
   Ensure `_match_keyword(kw: str, text: str)` converts both to lowercase or uses `re.IGNORECASE` so uppercase tokens like `"AI"` or `"ML"` match correctly.
3. **Pre-Compiled Third-Party Patterns**:
   Pre-compile the third-party prefix pattern at module level:
   ```python
   THIRD_PARTY_PATTERN = re.compile(
       r'\b(?:' + '|'.join(THIRD_PARTY_EXPERIENCE_PREFIXES) + r')\s*(?:(?:about|around|over|more than|approximately)\s*)?\d+(?:\s*[-–]\s*\d+)?\+?\s*(?:years?|yrs?)\b',
       re.IGNORECASE
   )
   ```
   and replace sequential iteration with a single regex substitution.
4. **Verification**:
   Run `pytest regex_audit/test_scorer_v2.py` and `pytest regex_audit/test_challenger_m4.py`.
5. Keep `src/scorer.py` and `src/scraper.py` untouched.
6. Write `handoff.md` in your working directory and notify parent.

## 2026-09-29T16:50:01Z
Apply the 3 requested improvements to regex_audit/scorer_v2.py (type guards on non-string inputs, case normalization in _match_keyword, pre-compiled third-party regex pattern).
Run pytest regex_audit/test_scorer_v2.py and verify all tests pass.
Write your completion report in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_remediate_m4\handoff.md and notify parent with send_message.

