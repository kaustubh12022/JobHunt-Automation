# BRIEFING — 2026-09-29T16:45:00Z

## Mission
Investigate the existing AI scoring engine, prompt architecture, candidate profile/resume, and project configuration to support the multi-provider AI scoring audit.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1
- Original parent: 7cb7199f-c2a4-46e3-be86-1c86a84aa546
- Milestone: AI Scoring Phase Audit Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strictly zero calls to DeepSeek API
- Write only to working directory .agents/teamwork/explorer_survey_ai_1/
- Produce report.md and handoff.md, then send_message to parent

## Current Parent
- Conversation ID: 7cb7199f-c2a4-46e3-be86-1c86a84aa546
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/ai_engine.py`: Examined client instantiation, model selection, runtime_settings, prompt loading, response parsing, retry loop, DeepSeek hardcoding, and cost telemetry.
  - `src/scorer.py`: Analyzed pre-filtering, boilerplate stripping, cache check, and `score_jobs` async execution.
  - `src/prompts/scoring_prompt.txt`: Analyzed target domains, scoring rubric, schema, root causes of MERN and AI under-scoring, and false missing skills.
  - `src/prompts/tailoring_prompt.txt`: Examined Phase 4 resume tailoring prompt.
  - `config.yaml`: Examined AI settings, search terms, and scoring thresholds.
  - `data_folder/plain_text_resume.yaml`: Extracted full candidate skills, education, experience, and projects.
  - `requirements.txt`: Checked SDKs (openai 2.54.0, google.genai installed; groq package not installed, OpenAI client for Groq available).
  - `.env`: Confirmed GEMINI_API_KEY and GROQ_API_KEY/GROK_API_KEY present; DEEPSEEK_API_KEY disabled.
  - `tests/`: Tested test_m3_scoring_telemetry.py (17 passed) and adversarial m3 suites (60 passed).
- **Key findings**:
  - `src/ai_engine.py` is hardcoded to DeepSeek with zero rate limiting; requires client-side rate limiters (Gemini <=15 RPM, Groq <=30 RPM).
  - `src/prompts/scoring_prompt.txt` completely omits MERN Stack and AI/ML/LLM from target roles, causing severe under-scoring; scoring rules lack fine-grained calibration tiers causing score compression; false missing skills result from prompt claiming candidate lacks secondary tools like Docker/Kubernetes when candidate resume explicitly contains them.
  - Candidate canonical resume is in `data_folder/plain_text_resume.yaml` (`config/profile.json` does not exist on disk).
  - Environment has `openai` (v2.54.0) and `google.genai` installed; Groq API can be called via `AsyncOpenAI(base_url="https://api.groq.com/openai/v1")` and Gemini via `google.genai.Client`.
- **Unexplored areas**: None within scope.

## Key Decisions Made
- Fully analyzed all 4 scope items and verified dependencies and test compatibility.
- Ready to write `report.md` and `handoff.md`.

## Artifact Index
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1\BRIEFING.md — Persistent state
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1\progress.md — Liveness heartbeat
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1\report.md — Detailed survey report
- c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1\handoff.md — 5-component handoff report
