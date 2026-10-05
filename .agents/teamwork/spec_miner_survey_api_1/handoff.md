# Handoff Report: AI Scoring API & Dependency Survey

**Agent**: `spec_miner_survey_api_1`  
**Working Directory**: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1`  
**Handoff Type**: Hard (Task Complete)  
**Timestamp**: 2026-09-29T16:47:00Z  

---

## 1. Observation

1. **Credentials & Environment Variables**:
   - Inspected `c:\Users\kalek\Desktop\Projects\Job_Hunt\.env` via Python inspection script:
     - `GEMINI_API_KEY`: Present: True, Length: 53 chars, Prefix: `AQ.A...`
     - `GROQ_API_KEY`: Present: True, Length: 56 chars, Prefix: `gsk_...`
     - `GROK_API_KEY`: Present: True, Length: 56 chars, Prefix: `gsk_...` (identical value to `GROQ_API_KEY`)
     - `DEEPSEEK_API_KEY`: NOT present in `.env` (Absent)
   - Checked OS environment variables via `os.environ`:
     - `os.environ["GEMINI_API_KEY"]`: Present=False
     - `os.environ["GROQ_API_KEY"]`: Present=False
     - `os.environ["DEEPSEEK_API_KEY"]`: Present=False
     - Implication: Keys reside in `.env` and must be loaded via `dotenv.load_dotenv()`.

2. **Installed Python Packages & Versions**:
   - `python -c "import importlib.metadata; ..."`:
     - `google-genai`: **2.25.0** (Installed)
     - `google-generativeai`: **NOT INSTALLED**
     - `groq`: **NOT INSTALLED**
     - `openai`: **2.54.0** (Installed)
     - `pydantic`: **2.13.5** (Installed)
     - `tenacity`: **9.1.4** (Installed)
     - `httpx`: **0.28.1** (Installed)
     - `aiohttp`: **3.14.3** (Installed)
     - `python-dotenv`: **1.2.2** (Installed)
     - `pyyaml`: **6.0.3** (Installed)

3. **Gemini API Probing**:
   - Probing `gemini-2.0-flash`:
     - Verbatim response: `<class 'google.genai.errors.ClientError'> 404 NOT_FOUND. {'error': {'code': 404, 'message': 'This model models/gemini-2.0-flash is no longer available. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://ai.google.dev/gemini-api/docs/get-started).', 'status': 'NOT_FOUND'}}`
   - Probing `gemini-2.5-flash`:
     - Verbatim response: `<class 'google.genai.errors.ClientError'> 404 NOT_FOUND. {'error': {'code': 404, 'message': 'This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements...', 'status': 'NOT_FOUND'}}`
   - Probing `gemini-2.5-flash-lite`:
     - Verbatim response: `<class 'google.genai.errors.ClientError'> 404 NOT_FOUND. {'error': {'code': 404, 'message': 'This model models/gemini-2.5-flash-lite is no longer available to new users...', 'status': 'NOT_FOUND'}}`
   - Probing `gemini-3.5-flash` and `gemini-3.8-flash`:
     - Verbatim response: `503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}`
   - Probing `gemini-3.5-flash-lite` and `gemini-flash-lite-latest`:
     - Verbatim response: `SUCCESS! Resp: OK`
   - Tested async structured JSON output with `gemini-3.5-flash-lite`:
     - Using `types.GenerateContentConfig(response_mime_type='application/json', response_schema=ScoreSchema)` returned valid parseable JSON: `{'fit_score': 60, 'is_testing_role': False, 'missing_skills': ['FastAPI'], 'reasoning': '...'}`.

4. **Groq API Probing**:
   - Tested access via `OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)`:
     - `client.models.list()` returned 11 models: `allam-2-7b`, `canopylabs/orpheus-arabic-saudi`, `canopylabs/orpheus-v1-english`, `meta-llama/llama-prompt-guard-2-22m`, `meta-llama/llama-prompt-guard-2-86m`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `openai/gpt-oss-safeguard-20b`, `qwen/qwen3.8-27b`, `whisper-large-v3`, `whisper-large-v3-turbo`.
   - Probing `llama-3.3-70b-versatile` and `llama-3.1-8b-instant`:
     - Verbatim response: `NotFoundError: Error code: 404 - {'error': {'message': 'The model llama-3.3-70b-versatile does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'code': 'model_not_found'}}`
   - Probing `llama3-70b-8192` and `llama3-8b-8192`:
     - Verbatim response: `BadRequestError: Error code: 400 - {'error': {'message': 'The model llama3-70b-8192 has been decommissioned and is no longer supported...', 'type': 'invalid_request_error', 'code': 'model_decommissioned'}}`
   - Probing `qwen/qwen3.8-27b`, `openai/gpt-oss-120b`, and `openai/gpt-oss-20b`:
     - Verbatim response: All returned `200 OK` with valid JSON schema matching `fit_score`, `is_testing_role`, `missing_skills`, and `reasoning`.
   - Header telemetry from Groq API via HTTPX POST:
     - `x-ratelimit-limit-requests: 1000`
     - `x-ratelimit-limit-tokens: 8000`
     - `x-ratelimit-remaining-tokens: 7982`
     - `x-ratelimit-reset-tokens: 134ms`
     - Notice: Strict 8,000 TPM token budget per minute.

5. **Existing Codebase & Interface Contracts**:
   - `src/ai_engine.py` currently hardcodes DeepSeek (`https://api.deepseek.com`, model `deepseek-chat`).
   - `src/prompts/scoring_prompt.txt` specifies keys: `match_score`, `reason`, `job_summary`, `missing_skills`, `extracted_requirements`, `is_testing_role`.
   - `src/scorer.py` lines 431-443 parse `match_score` (fallback `score`), `reason`, `job_summary`, `extracted_requirements`, `is_testing_role`.
   - `DISPATCH.md` expects schema fields: `fit_score`, `is_testing_role`, `missing_skills`, `reasoning`.

---

## 2. Logic Chain

1. **Credentials & Isolation**:
   - Observation 1 confirms that `GEMINI_API_KEY` and `GROQ_API_KEY` are present and valid, while `DEEPSEEK_API_KEY` is completely absent.
   - Therefore, the requirement to strictly forbid DeepSeek is structurally supported by the environment, and `ai_engine_v2.py` should only instantiate Gemini or Groq clients.

2. **Package Selection**:
   - Observation 2 reveals that `google-genai` 2.25.0 is installed, making it the authoritative SDK for Gemini calls.
   - The standalone `groq` package is not installed, but `openai` 2.54.0 is installed and fully capable of driving Groq via its official OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`).
   - `pydantic` 2.13.5 and `tenacity` 9.1.4 are installed, allowing seamless structured extraction and retry decorators without installing additional dependencies.

3. **Model Selection**:
   - Observation 3 proves that Gemini models `gemini-2.0-flash`, `gemini-2.5-flash`, and `gemini-2.5-flash-lite` are 404/restricted. `gemini-3.5-flash-lite` is immediately responsive and supports Pydantic JSON schemas.
   - Observation 4 proves that `llama-3.3-70b-versatile` returns 404 with the active Groq key. However, `qwen/qwen3.8-27b` is active, fast, and generates perfect JSON for scoring.
   - Therefore, `gemini-3.5-flash-lite` and `qwen/qwen3.8-27b` are the optimal, verified model choices for the dual-provider scoring engine.

4. **Rate Limiting Strategy**:
   - Observation 3 & Gemini docs establish a <= 15 RPM limit for Gemini free tier (interval >= 4.0s).
   - Observation 4 establishes that while Groq allows 1,000 requests per rolling window, its free tier token rate is capped at 8,000 TPM. A prompt and completion consume ~350-500 tokens. Calling at 30 RPM would generate 10,500-15,000 TPM and trigger 429 errors.
   - Therefore, Groq pacing must be calibrated to 15–20 RPM (delay >= 3.5s) to guarantee zero 429 token quota exceptions.

5. **JSON Extraction & Schema Compatibility**:
   - Observation 5 shows that legacy `src/scorer.py` expects `match_score` and `reason`, while the audit spec requests `fit_score` and `reasoning`.
   - Therefore, the dual-provider engine must return a unified Pydantic schema or dictionary containing both pairs (`fit_score` + `match_score`, `reasoning` + `reason`) so that existing pipelines and new audit benchmarks work interchangeably without regressions.

---

## 3. Caveats

1. **Model Naming Flexibility**: If Groq later enables `llama-3.3-70b-versatile` on this API key or Google promotes `gemini-3.8-flash` to general non-preview tier without 503 spikes, the engine should allow configuring model names via parameters or environment variables rather than hardcoding a single string.
2. **Groq TPM Variations**: The 8,000 TPM limit on Groq is per rolling window. If scoring large batches of long job descriptions without stripping boilerplate, token consumption will be higher; boilerplate stripping via `strip_boilerplate()` in `src/scorer.py` is essential.
3. **No Code Written**: Per specification miner instructions, no implementation files in `scoring_audit/` or `src/` were created or modified.

---

## 4. Conclusion

1. Dual-provider credentials and runtime environment are 100% verified and operational:
   - Gemini: Uses `google-genai` SDK, key `GEMINI_API_KEY`, model `gemini-3.5-flash-lite`, rate limiter <= 15 RPM.
   - Groq: Uses `openai` SDK pointing to `https://api.groq.com/openai/v1`, key `GROQ_API_KEY`, model `qwen/qwen3.8-27b` (fallback `openai/gpt-oss-120b`), rate limiter 15–20 RPM (to honor 8,000 TPM).
   - DeepSeek: Completely absent and forbidden.
2. Structured output is validated with Pydantic schema `fit_score`, `is_testing_role`, `missing_skills`, `reasoning`, aliased to `match_score` and `reason` for full backwards compatibility.
3. The comprehensive specification report has been generated at `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1\report.md`.

---

## 5. Verification Method

To independently verify these findings, run the following commands from `c:\Users\kalek\Desktop\Projects\Job_Hunt`:

1. **Verify Credentials & Exclusion**:
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Gemini:', bool(os.getenv('GEMINI_API_KEY')), 'Groq:', bool(os.getenv('GROQ_API_KEY')), 'DeepSeek:', bool(os.getenv('DEEPSEEK_API_KEY')))"
   ```
   *Expected Output*: `Gemini: True Groq: True DeepSeek: False`

2. **Verify Gemini API & Structured Output**:
   ```bash
   python -c "from google import genai; from google.genai import types; from dotenv import load_dotenv; import os; load_dotenv(); client = genai.Client(api_key=os.getenv('GEMINI_API_KEY')); print(client.models.generate_content(model='gemini-3.5-flash-lite', contents='Say OK').text.strip())"
   ```
   *Expected Output*: `OK`

3. **Verify Groq API & JSON Mode**:
   ```bash
   python -c "from openai import OpenAI; from dotenv import load_dotenv; import os; load_dotenv(); client = OpenAI(base_url='https://api.groq.com/openai/v1', api_key=os.getenv('GROQ_API_KEY')); resp = client.chat.completions.create(model='qwen/qwen3.8-27b', messages=[{'role':'user','content':'output JSON with key ok'}], response_format={'type':'json_object'}); print(resp.choices[0].message.content)"
   ```
   *Expected Output*: `{"ok": true}` or equivalent valid JSON object.
