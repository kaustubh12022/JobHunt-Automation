# Task Assignment: Worker M2 - Dual-Provider Scoring Engine Implementation

- Working Directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m2_engine
- Project Root: c:\Users\kalek\Desktop\Projects\Job_Hunt
- Request: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md (specifically ## Follow-up — 2026-09-29T16:37:31Z, Requirement R2)
- Scope Document: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3\PROJECT.md
- Reference Findings: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1\report.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You exclusively own:
- `scoring_audit/ai_engine_v2.py` (engine implementation)
- `scoring_audit/test_engine_v2.py` (engine verification script)
Do NOT modify production source files (`src/ai_engine.py`, `src/scorer.py`) or files owned by other agents.

## Requirements
1. Implement `scoring_audit/ai_engine_v2.py`:
   - Dual-Provider Support:
     - `gemini`: Uses `google-genai` 2.25.0 (`from google import genai; from google.genai import types`). Default model: `gemini-3.5-flash-lite`. Reads `GEMINI_API_KEY` from environment / `.env`.
     - `groq`: Uses `openai` 2.54.0 (`from openai import AsyncOpenAI`). Base URL: `https://api.groq.com/openai/v1`. Default model: `qwen/qwen3.8-27b`. Reads `GROQ_API_KEY` from environment / `.env`.
   - Zero DeepSeek Rule:
     - Strictly forbid any DeepSeek calls. If `provider="deepseek"` is passed, immediately raise `ValueError("DeepSeek is strictly forbidden in this pipeline.")`.
   - Client-Side Rate Limiting:
     - Gemini Rate Limiter: Enforce <= 15 RPM (min 4.0s delay between requests).
     - Groq Rate Limiter: Enforce <= 20 RPM (min 3.5s delay to strictly stay within the 8,000 TPM limit).
     - Rate limiters must be async-safe (e.g. using `asyncio.Lock` and timestamp queues).
   - Retry & Exponential Backoff:
     - Implement exponential backoff on HTTP 429 and 503 errors (3 to 5 attempts, jitter).
   - Schema & Extraction:
     - Pydantic model `ScoringResult`:
       ```python
       class ScoringResult(BaseModel):
           fit_score: int = Field(ge=0, le=100)
           is_testing_role: bool
           missing_skills: list[str] = Field(default_factory=list)
           reasoning: str

           @property
           def match_score(self) -> int: return self.fit_score
           @property
           def reason(self) -> str: return self.reasoning
       ```
     - For Gemini: Use `types.GenerateContentConfig(response_mime_type="application/json", response_schema=ScoringResult)`.
     - For Groq: Use `response_format={"type": "json_object"}`. Strip any markdown fences ` ```json ... ``` ` and parse JSON.
   - Master Resume & Prompt Injection:
     - Helper method `format_scoring_prompt(prompt_template_path: str, jd_text: str) -> str`:
       Loads candidate resume from `data_folder/plain_text_resume.yaml` and injects `{master_resume_json}` and `{job_description}` (or appends JD to user prompt).
2. Create and run `scoring_audit/test_engine_v2.py`:
   - Test Gemini live call on a test JD -> verify valid `ScoringResult`.
   - Test Groq live call on a test JD -> verify valid `ScoringResult`.
   - Test DeepSeek guard -> verify `ValueError` raised.
   - Test rate limiter delay -> verify pacing is respected.
3. Output your handoff to `handoff.md` and report completion via `send_message`.

## 2026-09-29T16:48:13Z
User Request:
Read c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md and c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m2_engine\DISPATCH.md.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m2_engine.
Implement scoring_audit/ai_engine_v2.py (Gemini gemini-3.5-flash-lite, Groq qwen/qwen3.8-27b, strict zero DeepSeek guard, rate limiting <=15 RPM Gemini, <=20 RPM Groq, backoff, Pydantic schema), write and run scoring_audit/test_engine_v2.py to verify both providers, write handoff.md, and send_message to parent upon completion.
