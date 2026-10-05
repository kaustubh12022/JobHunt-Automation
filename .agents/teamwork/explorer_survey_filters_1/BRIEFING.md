# BRIEFING — 2026-09-29T15:13:00Z

## Mission
Investigate and document the existing two-layer regex and rule filtering architecture in src/scraper.py and src/scorer.py, and detail how to deterministically replay both layers on raw job data without LLMs.

## 🔒 My Identity
- Archetype: explorer
- Roles: Existing Filter Architecture Explorer
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1
- Original parent: 5eb201de-9def-4d9e-9362-a784693de631
- Milestone: Filter Architecture Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / do NOT modify production code
- Do NOT modify src/scraper.py or src/scorer.py
- Deliver findings in handoff.md following 5-component protocol
- Send completion message to parent via send_message

## Current Parent
- Conversation ID: 5eb201de-9def-4d9e-9362-a784693de631
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/scraper.py` (lines 56-206, 209-356, 360-585): Layer 1 `apply_pandas_filter`, location aliases, remote patterns, URL normalization, deduplication.
  - `src/scorer.py` (lines 47-97, 114-188, 191-301, 310-356): Layer 2 regex filtering, `matches_senior_title`, `matches_out_of_scope_role`, `requires_3_plus_years`, `is_relevant_jd`, `DOMAIN_ANCHORS`, `TECH_TOOLS`.
  - `config.yaml`: Search terms, locations (Pune, Mumbai, Bangalore), hours_old (72).
  - `regex_audit/master_raw_dataset_2026-09-29.jsonl`: 1,137 raw scraped jobs.
  - `context/SCRAPING_AND_REGEX_TESTING.md` & `regex_audit_plan.md`: Replay architecture and schemas.
- **Key findings**:
  - Layer 1 executes 6 sequential filters in Pandas: empty desc (0 dropped), freshness (>72h cutoff, 74 dropped; preserves NaN date_posted), location regex + remote (16 dropped), `matches_senior_title` (516 dropped), `requires_3_plus_years` (356 dropped), two-stage deduplication (102 dropped: URL first, then clean title + known company). Layer 1 yields exactly 73 survivors.
  - Layer 2 executes 4 synchronous checks on Layer 1 survivors: `matches_senior_title` (0 dropped, redundant), `matches_out_of_scope_role` (12 dropped), `requires_3_plus_years` (0 dropped, redundant), `is_relevant_jd` (3 dropped). Layer 2 yields exactly 58 survivors.
  - Discovered critical root causes: `is_relevant_jd` ignores title for domain anchors; does substring matching without word boundaries; lacks MERN / AI / ML / Node / Express / MongoDB anchors; markdown escaping (`full\-stack`) defeats exact anchor match `'full stack'`; `OUT_OF_SCOPE_STACK_PATTERN` aggressively checks entire JD description, rejecting legitimate roles that mention out-of-scope tools in passing (e.g. Capgemini Java/Kotlin or Scoutit QA with Salesforce).
  - Deterministic replay requires fixing the reference cutoff time to the dataset scrape timestamp (`2026-09-29T14:05:55Z`) rather than dynamic `pd.Timestamp.now()`.
- **Unexplored areas**: None. All components in scope have been fully analyzed and verified with empirical code execution.

## Key Decisions Made
- Confirmed exact sequential ordering of filters in Layer 1 and Layer 2.
- Empirically simulated Layer 1 and Layer 2 against the exact 1,137 raw jobs dataset to verify numbers and failure reasons.
- Documenting complete specifications and step-by-step replay architecture for the Phase 2 replay engineer.

## Artifact Index
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1\handoff.md — Complete 5-component analysis and handoff report.
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_filters_1\progress.md — Execution heartbeat and progress tracking.

