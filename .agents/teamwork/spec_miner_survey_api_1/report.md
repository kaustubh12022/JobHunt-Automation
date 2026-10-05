# API & Dependency Specification Mining Survey Report

**Author**: Specification Miner Agent (`spec_miner_survey_api_1`)  
**Target Milestone**: AI Scoring Phase Audit & Multi-Provider Architecture (M1 Survey)  
**Date**: 2026-09-29  
**Working Directory**: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1`  
**Authoritative Sources**: Project `.env`, Python 3.13 Runtime Environment, Official Google GenAI SDK & Documentation, Groq OpenAI-Compatible REST API, Existing Scorer Codebase (`src/scorer.py`, `src/ai_engine.py`, `src/prompts/scoring_prompt.txt`).

---

## Executive Summary

This investigation surveys API credentials, runtime dependencies, model specifications, rate limiting parameters, error recovery mechanics, and JSON schema extraction for implementing the dual-provider scoring engine (`Gemini` and `Groq`) in `scoring_audit/ai_engine_v2.py`.

### Key Discoveries & Status:
1. **Credentials**:
   - `GEMINI_API_KEY`: Present in `.env` (53 characters, validated against Google GenAI API).
   - `GROQ_API_KEY`: Present in `.env` (56 characters, validated against Groq API).
   - `DEEPSEEK_API_KEY`: **ABSENT** from `.env` and environment variables. DeepSeek is strictly forbidden and completely isolated from the scoring pipeline.
   - Secret integrity: Zero raw secrets exposed; all keys verified via prefix/length introspection.

2. **Package Ecosystem**:
   - `google-genai` **2.25.0** is installed (Google's latest official SDK). Legacy `google-generativeai` is NOT installed.
   - `groq` standalone package is NOT installed, but `openai` **2.54.0** is installed and natively interfaces with Groq via `base_url="https://api.groq.com/openai/v1"`.
   - `pydantic` **2.13.5** and `tenacity` **9.1.4** are installed and ideal for schema enforcement and rate-limit backoff.

3. **Active Model Availability**:
   - **Gemini**: `gemini-2.0-flash`, `gemini-2.5-flash`, and `gemini-2.5-flash-lite` have been decommissioned / restricted by Google (HTTP 404). Active and responsive models verified in the runtime environment are **`gemini-3.5-flash-lite`** (recommended primary), **`gemini-flash-lite-latest`**, and **`gemini-flash-latest`** (subject to intermittent 503 demand spikes).
   - **Groq**: `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` return HTTP 404 (`model_not_found` for this tier), while legacy `llama3-70b-8192` is decommissioned (HTTP 400). The active, high-performance models verified via live API calls are **`qwen/qwen3.8-27b`** (recommended primary fast model), **`openai/gpt-oss-120b`**, and **`openai/gpt-oss-20b`**.

4. **Rate Limit Bounds**:
   - **Gemini Free Tier**: Strict client-side pacing at **<= 15 RPM** (minimum 4.0s delay between requests). Free tier daily quota is 1,500 RPD.
   - **Groq Free Tier**: While request limits allow up to 30 RPM, empirical header telemetry reveals a strict token ceiling of **`x-ratelimit-limit-tokens: 8000` TPM** (8k tokens/minute). Pacing at **15–20 RPM** (3.0s–4.0s delay) is required to prevent 429 token-quota exhaustion on multi-turn/batched prompts.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Auth & Env | `.env` Credential Loader | Loads `GEMINI_API_KEY`, `GROQ_API_KEY`, and ignores nonexistent keys | `.env` file | In-memory key mapping | Silent ignore or KeyError if accessed via `os.environ` without `.env` load | `dotenv.load_dotenv()` |
| 2 | Auth & Env | DeepSeek Strict Isolation | Complete exclusion of DeepSeek credentials and endpoints | Pipeline config | Zero outbound DeepSeek traffic | Assertion/RuntimeError if `deepseek` provider requested | Code review & `.env` inspection |
| 3 | SDK Client | Google GenAI Async Client | Modern async client interface for Gemini content generation | `api_key`, `model` | `genai.Client().aio.models.generate_content()` | `google.genai.errors.ClientError` (404/429), `ServerError` (503) | `google-genai` 2.25.0 inspect |
| 4 | SDK Client | Groq OpenAI Async Client | OpenAI SDK configured with Groq base URL and auth headers | `api_key`, `base_url="https://api.groq.com/openai/v1"` | `AsyncOpenAI.chat.completions.create()` | `openai.NotFoundError` (404), `openai.RateLimitError` (429) | `openai` 2.54.0 live test |
| 5 | Models | Gemini Active Models | Verified models available on Google GenAI developer tier | Model ID string | Valid completion response | 404 if legacy model (`gemini-2.0-flash`), 503 if high demand | Live API probe |
| 6 | Models | Groq Active Models | Verified models available on Groq platform | Model ID string | Valid completion response | 404 if `llama-3.3-70b-versatile`, 400 if decommissioned | Live API probe & `models.list()` |
| 7 | Rate Limiting | Gemini RPM Throttler | Client-side rate limiter enforcing <= 15 RPM | Delay generator / timestamp queue | Enforced delay (>= 4.0s) | Prevents 429 RESOURCE_EXHAUSTED | Gemini API documentation & telemetry |
| 8 | Rate Limiting | Groq TPM/RPM Throttler | Client-side rate limiter enforcing 8,000 TPM limit (15-20 RPM) | Delay generator / timestamp queue | Enforced delay (>= 3.5s) | Prevents 429 rate limit errors | Groq HTTP response headers |
| 9 | Structured Output | Gemini Native JSON Schema | Direct Pydantic schema validation using `response_schema` | `types.GenerateContentConfig(response_schema=ScoringResult)` | Guaranteed JSON matching Pydantic model | `ValidationError` on parse fail | `google-genai` live test |
| 10 | Structured Output | Groq JSON Object Mode | Server-side JSON enforcement with markdown fallback parsing | `response_format={"type": "json_object"}` | Valid JSON string in `content` | Substring fallback search `{...}` | `openai` live test on Groq |
| 11 | Resilience | Exponential Backoff & Jitter | Retry failed requests on transient network or rate-limit codes | Attempt index, status code | Sleep duration (base * 2^attempt + jitter) | Raises after max attempts (5) | `tenacity` 9.1.4 / custom loop |
| 12 | Compatibility | Bi-directional Schema Mapping | Maps between legacy `match_score`/`reason` and v2 `fit_score`/`reasoning` | Parsed JSON dict | Normalized dict with all required keys | Defaults missing keys safely | `src/scorer.py` code audit |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Gemini Model Selection | `model="gemini-2.0-flash"` | `ClientError: 404 NOT_FOUND. 'This model models/gemini-2.0-flash is no longer available. Please update your code to use models/gemini-3.8-flash...'` |
| 2 | Gemini Model Selection | `model="gemini-2.5-flash"` | `ClientError: 404 NOT_FOUND. 'This model models/gemini-2.5-flash is no longer available to new users...'` |
| 3 | Gemini Model Availability | `model="gemini-3.5-flash"` or `"gemini-flash-latest"` | Intermittent `ServerError: 503 UNAVAILABLE. 'This model is currently experiencing high demand. Spikes in demand are usually temporary...'` |
| 4 | Gemini Stable Model | `model="gemini-3.5-flash-lite"` | Immediate `200 OK` with valid structured JSON output and low latency. |
| 5 | Groq Model Selection | `model="llama-3.3-70b-versatile"` | `NotFoundError: Error code: 404 - {'error': {'message': 'The model llama-3.3-70b-versatile does not exist or you do not have access to it.'}}` |
| 6 | Groq Model Selection | `model="llama3-70b-8192"` | `BadRequestError: Error code: 400 - {'error': {'message': 'The model llama3-70b-8192 has been decommissioned and is no longer supported.'}}` |
| 7 | Groq Stable Model | `model="qwen/qwen3.8-27b"` | Immediate `200 OK` with valid JSON adhering to all requested keys (`fit_score`, `is_testing_role`, `missing_skills`, `reasoning`). |
| 8 | Groq Token Limit | Concurrency > 2 or > 20 RPM | `x-ratelimit-limit-tokens` is only 8,000 TPM. Rapid consecutive calls deplete quota and return HTTP 429. |
| 9 | Groq Response Formatting | System prompt without explicit JSON keywords | Model may include conversational preamble or markdown fences unless `response_format={"type": "json_object"}` is supplied. |
| 10 | Gemini Response Format | Prompt requesting schema without `response_mime_type="application/json"` | Model wraps output in ` ```json ... ``` ` markdown blocks. Native config eliminates fences. |

---

## Detailed Technical Specifications

### 1. Environment & Credentials Architecture

```
Project Root (.env)
├── GEMINI_API_KEY      -> [53 chars, valid Google GenAI key]
├── GROQ_API_KEY        -> [56 chars, valid Groq key, prefix gsk_]
├── GROK_API_KEY        -> [Identical to GROQ_API_KEY]
├── DEEPSEEK_API_KEY    -> [NOT PRESENT - strictly forbidden]
```

- **Environment Loading**:
  Scripts must execute `from dotenv import load_dotenv; load_dotenv()` before initializing clients.
- **Provider Guards**:
  The dual-provider engine must validate `provider in ("gemini", "groq")` and raise an explicit `ValueError` if any caller attempts to pass `deepseek`.

### 2. Runtime Dependencies & Package Verification

| Package | Version Installed | Usage in Dual-Provider Engine |
|---------|-------------------|-------------------------------|
| `google-genai` | **2.25.0** | Primary SDK for Gemini API calls via `genai.Client` and `client.aio.models.generate_content`. |
| `openai` | **2.54.0** | OpenAI-compatible SDK for Groq API calls via `AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=...)`. |
| `pydantic` | **2.13.5** | Defines `ScoringResult` model and executes strict runtime schema validation. |
| `tenacity` | **9.1.4** | Provides decorators for retry with exponential backoff on HTTP 429 and 503. |
| `python-dotenv`| **1.2.2** | Loads environment variables from `.env`. |
| `httpx` | **0.28.1** | Underlying async HTTP client for both SDKs. |

### 3. Model Specifications & Recommendations

#### Gemini Provider
- **Decommissioned / Restricted**:
  - `gemini-2.0-flash` (HTTP 404)
  - `gemini-2.5-flash` (HTTP 404)
  - `gemini-2.5-flash-lite` (HTTP 404)
- **Active & Tested**:
  - `gemini-3.5-flash-lite`: **RECOMMENDED PRIMARY**. High throughput, zero 503 errors during test bursts, native JSON schema support.
  - `gemini-flash-lite-latest`: Responsive, stable alternative.
  - `gemini-flash-latest`: Responsive, but subject to 503 demand spikes.
- **Configuration**:
  ```python
  from google import genai
  from google.genai import types

  client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
  config = types.GenerateContentConfig(
      response_mime_type="application/json",
      response_schema=ScoringResult,
      temperature=0.2
  )
  response = await client.aio.models.generate_content(
      model="gemini-3.5-flash-lite",
      contents=prompt,
      config=config
  )
  ```

#### Groq Provider
- **Decommissioned / Inaccessible**:
  - `llama-3.3-70b-versatile` (HTTP 404: `model_not_found`)
  - `llama-3.1-8b-instant` (HTTP 404: `model_not_found`)
  - `llama3-70b-8192` (HTTP 400: `model_decommissioned`)
- **Active & Tested**:
  - `qwen/qwen3.8-27b`: **RECOMMENDED PRIMARY**. 27B parameter dense model, high inference speed, 100% JSON compliance, superior domain reasoning.
  - `openai/gpt-oss-120b`: Strong alternative for larger context and complex scoring.
  - `openai/gpt-oss-20b`: Fast lightweight option.
- **Configuration**:
  ```python
  from openai import AsyncOpenAI

  client = AsyncOpenAI(
      base_url="https://api.groq.com/openai/v1",
      api_key=os.getenv("GROQ_API_KEY")
  )
  response = await client.chat.completions.create(
      model="qwen/qwen3.8-27b",
      messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt}
      ],
      response_format={"type": "json_object"},
      temperature=0.2
  )
  ```

### 4. Rate Limiting & Backoff Specifications

#### Gemini Throttling:
- **Target**: <= 15 RPM.
- **Interval Delay**: Minimum `4.0 seconds` between requests.
- **Retry Handling**: Retry on `google.genai.errors.ServerError` (HTTP 503) and `ClientError` with code 429.
- **Backoff Formula**: `sleep = (2 ** attempt) * 2.0 + random.uniform(0.1, 1.0)`.

#### Groq Throttling:
- **Target**: <= 20 RPM (enforcing the **8,000 TPM** limit).
- **Interval Delay**: Minimum `3.5 – 4.0 seconds` between requests.
- **Retry Handling**: Retry on `openai.RateLimitError` (HTTP 429) and `openai.APIConnectionError`.
- **Telemetry Inspection**: If `x-ratelimit-reset-tokens` is returned in headers, respect that pause duration.

### 5. Unified JSON Schema Extraction Contract

```python
from pydantic import BaseModel, Field

class ScoringResult(BaseModel):
    fit_score: int = Field(ge=0, le=100, description="Match score between 0 and 100")
    is_testing_role: bool = Field(description="True if role is QA, Testing, SDET, or Automation")
    missing_skills: list[str] = Field(default_factory=list, description="Top genuine technical missing skills")
    reasoning: str = Field(description="Concise justification of score and skill alignment")

    # Compatibility properties for legacy scorer pipeline
    @property
    def match_score(self) -> int:
        return self.fit_score

    @property
    def reason(self) -> str:
        return self.reasoning
```

#### Robust Parsing Strategy:
1. **Gemini**: Directly parse `response.text` via `ScoringResult.model_validate_json(response.text)`.
2. **Groq**: Extract `resp.choices[0].message.content`. Strip markdown code fences ` ```json ... ``` ` if present. If direct `model_validate_json()` fails due to leading/trailing text, locate substring from the first `{` to the last `}` and re-validate.
3. **Data Normalization**: Return both `fit_score` and `match_score`, `reasoning` and `reason` in the returned dictionary/object so all downstream modules (`scorer.py`, `ai_engine.py`, audit scripts) operate without regression.

---

## Recommended Next Steps for Implementation Team

1. **Implement `scoring_audit/ai_engine_v2.py`**:
   - Provide an async engine class supporting `provider="gemini"` (default model: `gemini-3.5-flash-lite`) and `provider="groq"` (default model: `qwen/qwen3.8-27b`).
   - Implement `RateLimiter` instances per provider (Gemini 15 RPM, Groq 15–20 RPM).
   - Enforce Pydantic schema validation with automatic fence stripping.
2. **Generate Synthetic Dataset (`scoring_audit/synthetic_jds.json`)**:
   - 300 synthetic JDs across 15 categories (20 each).
3. **Execute Baseline Scoring (R3)**:
   - Run dual scoring on synthetic dataset and surviving real jobs with prompt v1.
4. **Prompt Optimization (v2)**:
   - Tune prompt for MERN and AI/ML/LLM roles to resolve false negatives and score compression.
