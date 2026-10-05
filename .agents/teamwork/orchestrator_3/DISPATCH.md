# Orchestrator Dispatch

- Working Directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3
- Project Root: c:\Users\kalek\Desktop\Projects\Job_Hunt
- Request: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
- Scope: AI Scoring Phase Audit and Multi-Provider Fix (Gemini and Groq only, strictly excluding DeepSeek)

## 2026-09-29T16:38:58Z
You are the Project Orchestrator for the JobHunt-Automation system.

Your working directory is:
c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3

The project root is:
c:\Users\kalek\Desktop\Projects\Job_Hunt

Read the authoritative user request at:
c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md
specifically the section under:
## Follow-up — 2026-09-29T16:37:31Z

Mission:
Execute an end-to-end AI Scoring Phase Audit and Multi-Provider Fix for the job hunting automation pipeline using Gemini and Groq APIs, strictly excluding DeepSeek. Generate synthetic test datasets, audit scoring accuracy, cross-validate provider agreement, engineer an optimized scoring prompt v2, re-score, and integrate multi-provider support into production.

Requirements:
- R1. Synthetic Benchmark Dataset Generation (300 JDs across 15 categories, 20 JDs each, saved to scoring_audit/synthetic_jds.json)
- R2. Dual-Provider Scoring Engine (Gemini & Groq Only in scoring_audit/ai_engine_v2.py, strictly zero DeepSeek calls, rate limiters Gemini <= 15 RPM, Groq <= 30 RPM, exponential backoff, JSON schema extraction)
- R3. Dual-Provider Baseline Scoring Execution (score synthetic and real jobs with v1 prompt, persist to scoring_audit/scores/)
- R4. Cross-Validation & Deficiencies Analysis (audit accuracy, provider agreement ±10 pts, missing_skills, is_testing_role, markdown reports in scoring_audit/analysis/)
- R5. Prompt Optimization (v2) & Benchmark Verification (scoring_audit/scoring_prompt_v2.txt fixing MERN, AI/ML under-scoring, score compression, re-score and produce comparative metrics)
- R6. Production Multi-Provider Integration (update src/ai_engine.py, config.yaml, tests, backing up original baseline files, strictly no DeepSeek)

Maintain BRIEFING.md and progress.md in your working directory.
Dispatch specialists as appropriate.
When finished and verified, send a message to the sentinel reporting completion.

## 2026-09-30T07:03:26Z
Server restart has completed and fresh daily quota is available. Please resume execution from the current state (Milestone 2 remediation / Gate 1 re-evaluation and proceed to Milestone 3). Continue driving the project milestones.
