# BRIEFING — 2026-09-29T16:55:00Z

## Mission
Implement dual-provider async scoring engine in scoring_audit/ai_engine_v2.py and verification suite in scoring_audit/test_engine_v2.py for Gemini and Groq with rate limiting, exponential backoff, Pydantic schema validation, and strict zero DeepSeek guard.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m2_engine
- Original parent: 7cb7199f-c2a4-46e3-be86-1c86a84aa546
- Milestone: M2 - Dual-Provider Scoring Engine

## 🔒 Key Constraints
- DO NOT CHEAT: Genuine implementation only, no mock/hardcoded responses, real state and real API calls.
- Write Ownership: Exclusively own `scoring_audit/ai_engine_v2.py` and `scoring_audit/test_engine_v2.py`. Do NOT edit `src/ai_engine.py`, `src/scorer.py`, or files of other agents.
- Zero DeepSeek: Strictly forbid any DeepSeek calls or keys. If provider="deepseek" is passed, immediately raise ValueError.
- Models: Gemini `gemini-3.5-flash-lite` via `google-genai` 2.25.0, Groq `qwen/qwen3.8-27b` via `openai` 2.54.0 (`base_url="https://api.groq.com/openai/v1"`).
- Rate Limiting: Gemini <= 15 RPM (>=4.0s delay), Groq <= 20 RPM (>=3.5s delay). Async-safe with lock and timestamps.
- Exponential Backoff: Retry on 429 and 503 with exponential delay and jitter (3-5 attempts).
- Schema: Pydantic `ScoringResult` (`fit_score: int [0,100]`, `is_testing_role: bool`, `missing_skills: list[str]`, `reasoning: str`), backwards-compatible properties `match_score` and `reason`.

## Current Parent
- Conversation ID: 7cb7199f-c2a4-46e3-be86-1c86a84aa546
- Updated: 2026-09-29T16:55:00Z

## Task Summary
- **What to build**: DualProviderScoringEngine in `scoring_audit/ai_engine_v2.py` and test script in `scoring_audit/test_engine_v2.py`.
- **Success criteria**: Live tests pass for both Gemini and Groq, DeepSeek guard raises ValueError, rate limiter enforces pacing, structured ScoringResult returned.
- **Interface contracts**: PROJECT.md Milestone M2 and DISPATCH.md.
- **Code layout**: `scoring_audit/` directory.

## Change Tracker
- **Files modified**:
  - `scoring_audit/ai_engine_v2.py`: Implemented `DualProviderScoringEngine`, `AsyncRateLimiter`, `ScoringResult`, prompt injection, and retry backoff.
  - `scoring_audit/test_engine_v2.py`: Comprehensive test suite with 7 verification tests for pytest and standalone execution.
- **Build status**: Pass (7/7 tests passed in both standalone and pytest modes).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: PASS (7/7 tests passed in 5.42s).
- **Lint status**: Clean (`py_compile` exited 0).
- **Tests added/modified**: 7 tests covering DeepSeek guard, unsupported provider rejection, schema normalization, prompt formatting, rate limiter pacing, Gemini live API call, Groq live API call.

## Loaded Skills
- None specified in dispatch.

## Key Decisions Made
- Used `google.genai` SDK 2.25.0 with `types.GenerateContentConfig(response_mime_type="application/json", response_schema=ScoringResult)` for Gemini.
- Used `openai.AsyncOpenAI` with `base_url="https://api.groq.com/openai/v1"` and `response_format={"type": "json_object"}` for Groq.
- Avoided `ConfigDict(extra="allow")` on `ScoringResult` to prevent `"additionalProperties"` from breaking Google GenAI developer API mode, while allowing dynamic Python attributes (`provider`, `model`, `latency_seconds`) via custom `__setattr__`.
- Designed synchronous pytest-compatible wrappers around async tests so both `pytest` and direct python execution work seamlessly.

## Artifact Index
- `scoring_audit/ai_engine_v2.py` — Engine implementation
- `scoring_audit/test_engine_v2.py` — Engine verification test script
- `handoff.md` — Handoff report for parent
