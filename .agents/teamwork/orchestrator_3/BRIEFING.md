# BRIEFING — 2026-09-29T16:38:58Z

## Mission
Execute an end-to-end AI Scoring Phase Audit and Multi-Provider Fix for the job hunting automation pipeline using Gemini and Groq APIs, strictly excluding DeepSeek.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3
- Original parent: parent
- Original parent conversation ID: c3c46219-7270-4163-842c-0af56ab35b81

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: c:\Users\kalek\Desktop\Projects\Job_Hunt\PROJECT.md
1. **Decompose**: Decompose into Survey + 6 Milestones (M1: Synthetic Benchmark Dataset Generation, M2: Dual-Provider Scoring Engine, M3: Dual-Provider Baseline Scoring Execution, M4: Cross-Validation & Deficiencies Analysis, M5: Prompt Optimization v2 & Benchmark Verification, M6: Production Multi-Provider Integration)
2. **Dispatch & Execute**:
   - Survey: Spawn 3 Explorers in parallel to survey codebase, existing prompts, scoring engine, config, and available real jobs.
   - For each milestone: Direct iteration loop (Explorer -> Worker -> Reviewers -> Challengers -> Auditor -> Gate) or delegated sub-orchestrator.
3. **On failure**:
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: At 16 spawns, write handoff.md, spawn successor
- **Work items**:
  1. Survey & Initial Project Mapping [done]
  2. M1: Synthetic Benchmark Dataset Generation [in-progress]
  3. M2: Dual-Provider Scoring Engine [in-progress]
  4. M3: Dual-Provider Baseline Scoring Execution [pending]
  5. M4: Cross-Validation & Deficiencies Analysis [pending]
  6. M5: Prompt Optimization v2 & Benchmark Verification [pending]
  7. M6: Production Multi-Provider Integration [pending]
- **Current phase**: 1 (M1 & M2 Execution)
- **Current focus**: Milestone 1 (Synthetic JDs) & Milestone 2 (Dual-Provider Engine)

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers for technical investigation.
- You MAY use file-editing tools ONLY for metadata/state files (.md) in your .agents/teamwork/ folder.
- Strictly zero DeepSeek API calls; strictly use Gemini and Groq APIs only.
- Strict rate limiting: Gemini <= 15 RPM, Groq <= 20 RPM (8k TPM bound), exponential backoff, JSON schema extraction.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh.

## Current Parent
- Conversation ID: c3c46219-7270-4163-842c-0af56ab35b81
- Updated: not yet

## Key Decisions Made
- Initialized Project Orchestrator for AI Scoring Phase Audit and Multi-Provider Fix.
- Survey completed: 73 surviving real jobs identified in `regex_audit/filter_results/layer1_pandas_pass.jsonl`; models identified as `gemini-3.5-flash-lite` (Gemini) and `qwen/qwen3.8-27b` (Groq).
- DeepSeek strictly absent and prohibited. Rate limits mapped: Gemini 15 RPM, Groq 15-20 RPM (8k TPM limit).

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| explorer_survey_ai_1 | teamwork_preview_explorer | Survey AI engine & prompts | completed | 96b641fa-c7b7-4247-9fb1-efa60b291cbd |
| explorer_survey_jobs_1 | teamwork_preview_explorer | Survey jobs dataset & regex | completed | 56a62aee-2794-4ecf-b62d-d431656e977a |
| spec_miner_survey_api_1 | teamwork_preview_spec_miner | Survey APIs, keys & packages | completed | 224b5954-7948-4fc6-a391-cc3fd35289f9 |
| worker_m1_synthetic | teamwork_preview_worker | Generate 300 synthetic benchmark JDs | completed | 355d45de-818b-44da-83ed-480a5ea49baf |
| worker_m2_engine | teamwork_preview_worker | Dual-provider engine (Gemini & Groq) | completed | c047b5ab-ca21-4bd6-8eee-e11866d070cd |
| reviewer_m1_m2_1 | teamwork_preview_reviewer | Dataset & Schema Review | completed | c0308596-8fea-40ff-83bb-4c2cfc3ab7b7 |
| reviewer_m1_m2_2 | teamwork_preview_reviewer | Engine Architecture Review | completed | 08bea35f-ba9f-44de-8f7e-12f88e2dd94e |
| challenger_m1_m2_1 | teamwork_preview_challenger | Rate Limit Pacing Challenger | completed | 3aa03209-7a30-4c09-80e7-c034c28f6193 |
| challenger_m1_m2_2 | teamwork_preview_challenger | Schema & Live Call Challenger | completed | ebe4f988-30e1-4b94-b4a2-88745f876da5 |
| auditor_m1_m2_1 | teamwork_preview_auditor | Forensic Integrity Auditor | completed | d9193087-ac84-4dd8-b1dd-c6ca363e2ba7 |
| worker_m2_fix_1 | teamwork_preview_worker | Engine Remediation & Hardening | in-progress | 5cf2b4ad-c80f-48d9-8cc2-59df82a86106 |

## Succession Status
- Succession required: no
- Spawn count: 11 / 16
- Pending subagents: 5cf2b4ad-c80f-48d9-8cc2-59df82a86106
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 7cb7199f-c2a4-46e3-be86-1c86a84aa546/task-169
- Safety timer: none

## Artifact Index
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md — User request specification
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3\DISPATCH.md — Task assignment
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3\progress.md — Progress log & liveness
