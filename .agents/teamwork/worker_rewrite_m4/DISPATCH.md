# Dispatch: Worker Rewrite M4

## Identity
- Role: Scorer V2 Implementation Worker
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_rewrite_m4
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Files to Read
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\audit_report.md` (Full diff specifications & regex proposals)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_audit_m3\handoff.md` (Reviewer advisories for V2)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_positives.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\evaluation\false_negatives.jsonl`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py` (READ-ONLY baseline)
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py` (READ-ONLY baseline)

## Deliverables & Tasks
1. Implement `regex_audit/scorer_v2.py`:
   - Define expanded `DOMAIN_ANCHORS` (including MERN: `mern`, `mern stack`, `react`, `node`, `nodejs`, `node.js`, `express`, `expressjs`, `express.js`, `mongodb`, and AI/LLM: `ai`, `ml`, `machine learning`, `llm`, `agentic`, `genai`, `generative ai`, `rag`, `langchain`, `deep learning`).
   - Define expanded `TECH_TOOLS` (including `express`, `mongodb`, `node`, `nodejs`, `node.js`, `fastapi`, `langchain`, `rag`, `agentic`, `llm`).
   - Implement `matches_senior_title(title: str, description: str = "") -> bool` with:
     - `\bavp\b` added to senior titles.
     - Terminal senior digit matching `\b[2-9]$` (after stripping whitespace).
     - "Advanced Engineer" pattern.
     - Negative lookbehind/protection for career path suffixes (e.g., "Fast-Track to Tech Lead", "Path to Lead").
   - Implement `requires_3_plus_years(text: str) -> bool` with:
     - Company boilerplate protection ("with over \d+ years", "over ten years", "20 years of experience").
     - Age range exclusion `\(\d{2}\s*to\s*\d{2}\s*yrs\)`.
     - Preserving Steps 3, 5, 6, 7 from baseline logic.
     - Refining third-party prefix regex to avoid swallowing candidate experience requirements like "working with React".
   - Implement `matches_out_of_scope_role(title: str, description: str = "") -> bool`:
     - Strictly check title for out-of-scope roles.
     - For description, check for primary/required stack without falsely rejecting core roles mentioning Kotlin, Flutter, or Salesforce secondarily.
   - Implement `is_relevant_jd(description: str, title: str = "") -> bool`:
     - Unescape markdown hyphens (`full\-stack` -> `full-stack`).
     - Check `DOMAIN_ANCHORS` across combined title and description.
     - Check `TECH_TOOLS` and ensure role is not out of scope.
2. Create unit test suite `regex_audit/test_scorer_v2.py`:
   - Test all 8 False Positives to confirm they now FAIL.
   - Test all 10 False Negatives to confirm they now PASS.
   - Test sample baseline True Positives (e.g. Jobs 0, 77, etc.) to confirm zero regressions.
3. Ensure `src/scorer.py` and `src/scraper.py` remain untouched.
4. Write `handoff.md` in your working directory and notify parent.

## 2026-09-29T16:14:00Z
You are worker_rewrite_m4.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_rewrite_m4
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Read your task in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_rewrite_m4\DISPATCH.md.
Also read:
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\regex_audit\audit_report.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_audit_m3\handoff.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py (READ-ONLY)
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py (READ-ONLY)

Implement regex_audit/scorer_v2.py with the clean, deterministic standalone functions and expanded anchor/tool sets.
Create and run unit test suite regex_audit/test_scorer_v2.py (testing the 18 discrepancy jobs and baseline true positives).
Write your completion report in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_rewrite_m4\handoff.md and notify parent with send_message.

