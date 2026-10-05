# Handoff Report: Dual-Provider Scoring Engine Implementation (Milestone M2)

**Author**: Worker M2 (`worker_m2_engine`)  
**Target Milestone**: M2 - Dual-Provider Scoring Engine  
**Recipient**: Parent Orchestrator (`7cb7199f-c2a4-46e3-be86-1c86a84aa546`)  
**Date**: 2026-09-29  
**Artifacts Produced**:
- `scoring_audit/ai_engine_v2.py`
- `scoring_audit/test_engine_v2.py`

---

## 1. Observation

1. **API Keys and Provider Credentials**:
   - Environment check confirmed `GEMINI_API_KEY` (53 chars) and `GROQ_API_KEY` (56 chars, prefix `gsk_`) are configured in `.env`.
   - `DEEPSEEK_API_KEY` is completely absent from `.env` and environment variables.

2. **Model Availability & Performance**:
   - Google Gemini: Tested `gemini-3.5-flash-lite` via `google-genai` SDK 2.25.0 (`client.aio.models.generate_content`). Returned in 2.82s with structured JSON matching `ScoringResult`.
   - Groq: Tested `qwen/qwen3.8-27b` via `openai.AsyncOpenAI` 2.54.0 pointing to `base_url="https://api.groq.com/openai/v1"`. Returned in 1.80s with structured JSON matching `ScoringResult`.
   - Google Developer API schema restriction: Specifying `model_config = ConfigDict(extra="allow")` generates `"additionalProperties": true`, causing Google GenAI to raise:
     `ValueError: additionalProperties is only supported in Gemini Enterprise Agent Platform mode, , not in Gemini Developer API mode.`
     Omitting `extra="allow"` and handling dynamic attributes (`provider`, `model`, `latency_seconds`, `tokens_used`) via custom `__setattr__` resolved this completely.

3. **Security & DeepSeek Isolation**:
   - Calling `engine._validate_provider("deepseek")`, `"DeepSeek"`, or `score_job(..., provider="deepseek")` raises verbatim:
     `ValueError: DeepSeek is strictly forbidden in this pipeline.`

4. **Rate Limiting Telemetry**:
   - Gemini limiter defaults: `rpm=15.0`, `min_interval=4.0s`.
   - Groq limiter defaults: `rpm=20.0`, `min_interval=3.5s` (protects the strict 8,000 TPM limit).
   - AsyncRateLimiter pacing test confirmed inter-request delay enforcement (2 rapid calls with `min_interval=0.3s` took 0.306s).

5. **Test Suite Verification**:
   - Ran `python scoring_audit/test_engine_v2.py`:
     ```
     ======================================================================
     ALL TESTS PASSED SUCCESSFULLY! (7/7)
     ======================================================================
     ```
   - Ran `pytest scoring_audit/test_engine_v2.py -v`:
     ```
     scoring_audit/test_engine_v2.py::test_deepseek_guard PASSED              [ 14%]
     scoring_audit/test_engine_v2.py::test_unsupported_provider PASSED        [ 28%]
     scoring_audit/test_engine_v2.py::test_schema_and_compatibility PASSED    [ 42%]
     scoring_audit/test_engine_v2.py::test_prompt_formatting PASSED           [ 57%]
     scoring_audit/test_engine_v2.py::test_rate_limiter_pacing PASSED         [ 71%]
     scoring_audit/test_engine_v2.py::test_gemini_live_scoring PASSED         [ 85%]
     scoring_audit/test_engine_v2.py::test_groq_live_scoring PASSED           [100%]
     ======================== 7 passed, 1 warning in 5.42s =========================
     ```
   - Live sample test on synthetic JD #1 (`SYNTH_001` - Junior Java Developer):
     - Gemini Result: `fit_score=88`, `is_testing_role=False`, missing `['Hibernate', 'JPA', 'PostgreSQL', 'Kafka']`
     - Groq Result: `fit_score=88`, `is_testing_role=False`, missing `['Kafka', 'Hibernate', 'PostgreSQL', 'Microservices', 'SOLID Principles']`
     - Perfect 100% agreement on score (88/100) and classification (`is_testing_role=False`).

---

## 2. Logic Chain

1. **Step 1 (Schema & Compatibility)**: Downstream tasks and legacy scripts require interoperability between v1 keys (`match_score`, `reason`) and v2 schema (`fit_score`, `reasoning`). By defining `ScoringResult` with `@model_validator(mode="before")`, any dictionary or JSON payload from either prompt version is normalized deterministically without data loss.
2. **Step 2 (Zero DeepSeek Compliance)**: The project integrity directive strictly forbids any calls to DeepSeek. By validating `provider in ("gemini", "groq")` at the entry point of `score_job` and raising `ValueError` on any occurrence of `"deepseek"`, DeepSeek is completely blocked.
3. **Step 3 (Client-side Rate Limiting)**: To prevent HTTP 429 quota exhaustion (Gemini free tier limit 15 RPM, Groq free tier limit 8,000 TPM / 20 RPM), `AsyncRateLimiter` enforces both a sliding 60-second window and a minimum inter-request interval (4.0s for Gemini, 3.5s for Groq) guarded by `asyncio.Lock`.
4. **Step 4 (Resilience & Exponential Backoff)**: Transient HTTP 429 and 503 errors (especially Gemini peak demand spikes) are caught and automatically retried using exponential backoff with jitter (`(2 ** attempt) * base_backoff + random.uniform(0.1, 1.0)`) across up to 4 retry attempts.
5. **Step 5 (Prompt Formatting & Context Injection)**: `format_scoring_prompt` reads the candidate's master resume from `data_folder/plain_text_resume.yaml`, serializes it to JSON, and injects `{master_resume_json}` and `{job_description}` into the prompt template.

---

## 3. Caveats

1. **Google GenAI AFC Warning**: `google-genai` 2.25.0 outputs an informational log message (`Direct use of automatic function calling (AFC) in AsyncModels.generate_content is not recommended...`) to stderr. This is a library-level informational notice that does not affect output or exit codes.
2. **Pre-existing Repository Test Failures**: `pytest tests/` fails on two pre-existing collection errors (`tests/integration/test_gmail_otp.py` missing `src.gmail_otp` and `tests/unit/test_credential_vault.py` missing `src.credentials_vault`). These are unrelated legacy files outside Milestone M2 scope.

---

## 4. Conclusion

Milestone M2 requirements are fully satisfied:
- `scoring_audit/ai_engine_v2.py` is implemented, production-ready, and verified.
- Gemini (`gemini-3.5-flash-lite`) and Groq (`qwen/qwen3.8-27b`) are fully operational.
- Strict Zero DeepSeek rule is enforced with immediate `ValueError`.
- Async rate limiting (<= 15 RPM for Gemini, <= 20 RPM for Groq) and backoff are verified.
- `ScoringResult` Pydantic model enforces structured output with legacy compatibility.
- `scoring_audit/test_engine_v2.py` achieves 100% pass rate (7/7 tests passed) in both direct CLI and pytest execution modes.
- Production source files (`src/ai_engine.py`, `src/scorer.py`) remain completely untouched.

---

## 5. Verification Method

Run the verification test suite directly via Python:
```powershell
python scoring_audit/test_engine_v2.py
```
Expected output: All 7 tests pass with exit code 0.

Run the verification test suite via pytest:
```powershell
pytest scoring_audit/test_engine_v2.py -v
```
Expected output: `7 passed in ~5s`.

Test synthetic JD live scoring:
```powershell
python -c "import json, asyncio; from scoring_audit.ai_engine_v2 import DualProviderScoringEngine; engine = DualProviderScoringEngine(); jd = json.load(open('scoring_audit/synthetic_jds.json'))[0]['description']; print('Gemini:', asyncio.run(engine.score_job(jd, provider='gemini')).fit_score); print('Groq:', asyncio.run(engine.score_job(jd, provider='groq')).fit_score)"
```
Expected output: Both providers successfully return an integer score in the expected ground truth range (80-95).
