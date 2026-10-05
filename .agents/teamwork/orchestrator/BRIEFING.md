# BRIEFING — 2026-09-29T15:02:30Z

## Mission
Orchestrate audit and rewrite of regex filtering pipeline for AutoApply job hunting system to achieve >=95% accuracy against 1,137-job ground truth.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator
- Original parent: parent
- Original parent conversation ID: 7d3c5750-af7d-466b-bf1b-1f6bc67a5263

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: c:\Users\kalek\Desktop\Projects\Job_Hunt\PROJECT.md
1. **Decompose**: Decompose into survey, M1 (Filter Replay), M2 (Ground Truth & Eval), M3 (Root Cause Audit), M4 (Filter Rewrite scorer_v2.py), M5 (Retesting & Verification).
2. **Dispatch & Execute**:
   - Survey: Spawn 3 Explorers in parallel to survey codebase, existing filtering, dataset, and requirements.
   - Decompose milestones, create PROJECT.md.
   - Delegate milestones to workers/subagents following the Explorer -> Worker -> Reviewer -> Challenger -> Auditor cycle.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (last resort)
4. **Succession**: At 16 spawns, write handoff.md, cancel crons, spawn successor.
- **Work items**:
  1. Survey & Plan [in-progress]
  2. M1: Replay Existing Two-Layer Filtering [pending]
  3. M2: Systematic Evaluation & Ground-Truth Dataset [pending]
  4. M3: Regex Filter Root-Cause Audit [pending]
  5. M4: Deterministic Filter Rewrite (scorer_v2.py) [pending]
  6. M5: Retest & Objective Verification Against Ground Truth [pending]
- **Current phase**: 0 (Survey & Planning)
- **Current focus**: Survey phase (map scope with explorers)

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers for technical investigation.
- You MAY use file-editing tools ONLY for metadata/state files (.md) in your .agents/teamwork/ folder.
- CRITICAL DIRECTIVE: DO NOT re-scrape or re-generate the raw dataset. Use regex_audit/master_raw_dataset_2026-09-29.jsonl directly.
- Keep src/scorer.py and src/scraper.py untouched.
- Retest accuracy >= 95.0% against ground_truth.jsonl.
- Always include path to ORIGINAL_REQUEST.md in subagent dispatches.
- Binary veto on Forensic Audit failure.

## Current Parent
- Conversation ID: 7d3c5750-af7d-466b-bf1b-1f6bc67a5263
- Updated: not yet

## Key Decisions Made
- Project pattern selected for multi-milestone data science/engineering pipeline audit and rewrite.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|

## Succession Status
- Succession required: no
- Spawn count: 0 / 16
- Pending subagents: none
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: not started
- Safety timer: none

## Artifact Index
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md — Authoritative User Request
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator\DISPATCH.md — Orchestrator Dispatch Log
