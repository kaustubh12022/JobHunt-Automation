# Dispatch: Explorer Survey Filters 1

## Identity
- Role: Existing Filter Architecture Explorer
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1
- Parent: orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631)

## Task Description
Investigate the existing filtering architecture in `src/scraper.py` and `src/scorer.py` (DO NOT modify them):
1. Document Layer 1 (Pandas Pre-Filter) in `src/scraper.py`:
   - Empty description check
   - Freshness check (>72h cutoff logic)
   - Location regex and remote logic
   - `matches_senior_title()` call in scraper
   - `requires_3_plus_years()` call in scraper
   - Deduplication logic (URL + company/title)
2. Document Layer 2 (Scorer Regex Filter) in `src/scorer.py`:
   - `matches_senior_title()` definition and regex patterns
   - `matches_out_of_scope_role()` definition and `OUT_OF_SCOPE_STACK_PATTERN`
   - `requires_3_plus_years()` definition, patterns, and exception rules
   - `is_relevant_jd()`, `DOMAIN_ANCHORS`, and `TECH_TOOLS`
3. Detail how a deterministic replay script should execute these two layers sequentially on `regex_audit/master_raw_dataset_2026-09-29.jsonl` without AI/LLM calls.

## Authoritative Files to Read
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py`
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py`

## Output
Write `handoff.md` in your working directory with the complete filter architecture analysis and send a completion message back.

## 2026-09-29T15:12:38Z
You are explorer_survey_filters_1.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1
Your parent is orchestrator_1 (Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631).

Read your task in c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1\DISPATCH.md.
Also read:
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scraper.py
- c:\Users\kalek\Desktop\Projects\Job_Hunt\src\scorer.py

Investigate the existing filtering architecture in src/scraper.py and src/scorer.py (DO NOT modify them):
1. Document Layer 1 (Pandas Pre-Filter) in src/scraper.py:
   - Empty description check
   - Freshness check (>72h cutoff logic)
   - Location regex and remote logic
   - matches_senior_title() call in scraper
   - requires_3_plus_years() call in scraper
   - Deduplication logic (URL + company/title)
2. Document Layer 2 (Scorer Regex Filter) in src/scorer.py:
   - matches_senior_title() definition and regex patterns
   - matches_out_of_scope_role() definition and OUT_OF_SCOPE_STACK_PATTERN
   - requires_3_plus_years() definition, patterns, and exception rules
   - is_relevant_jd(), DOMAIN_ANCHORS, and TECH_TOOLS
3. Detail how a deterministic replay script should execute these two layers sequentially on regex_audit/master_raw_dataset_2026-09-29.jsonl without AI/LLM calls.

Write your full findings to c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1\handoff.md following the Handoff Protocol.
When done, send a message to your parent with send_message.

