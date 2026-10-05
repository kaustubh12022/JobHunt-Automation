# Handoff Report: AI Scoring Engine & Prompt Architecture Survey

**Agent**: `explorer_survey_ai_1`  
**Working Directory**: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1`  
**Parent Agent**: `parent` (`7cb7199f-c2a4-46e3-be86-1c86a84aa546`)  
**Type**: Hard Handoff (Investigation Complete)

---

## 1. Observation

### 1.1 `src/ai_engine.py` Observations
- **DeepSeek Hardcoding**:
  - `src/ai_engine.py:121-125`: `client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY", config['ai']['api_key']), base_url="https://api.deepseek.com")`
  - `src/ai_engine.py:136-140`: `client = AsyncOpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY", config['ai']['api_key']), base_url="https://api.deepseek.com")`
  - `src/ai_engine.py:22-27`: `runtime_settings = {"scoring_model": "deepseek-chat", "scoring_thinking": False, "tailoring_model": "deepseek-chat", "tailoring_thinking": True}`
  - `src/ai_engine.py:30-40`: `calculate_deepseek_cost()` computes cache hit ($0.07/1M) and cache miss ($0.27/1M) costs specific to DeepSeek.
- **Concurrency & Rate Limiting**:
  - `src/scorer.py:488-493`: `tasks.append(process_job(i, job)); rest_results = await asyncio.gather(*tasks, return_exceptions=True)`.
  - `src/ai_engine.py` contains zero rate limiting (no RPM / TPM pacing).
- **Prompt Injection & Serialization**:
  - `src/ai_engine.py:151-155`: `_get_prompt(filename, master_resume)` reads `src/prompts/{filename}` and replaces `"{master_resume_json}"` with `json.dumps(master_resume, indent=2)`.
  - `src/ai_engine.py:143-148`: `_get_master_resume()` calls `load_resume()` from `src/config_loader.py`.

### 1.2 `src/prompts/scoring_prompt.txt` Observations
- **Target Role Omissions**:
  - `src/prompts/scoring_prompt.txt:7-14`:
    ```
    === CANDIDATE TARGET ROLES ===
    The candidate is targeting these specific domains:
    1. Java Backend Developer (Spring, JDBC, REST APIs, SQL)
    2. Automation Tester / QA Automation (Selenium, JUnit, Postman, pytest, Test Case Design)
    3. .NET / C# Developer (candidate has Azure Fundamentals cert and OOP foundation)
    4. Software Engineer / Full Stack Developer (Python, JavaScript, HTML/CSS)
    5. Software Tester / QA Engineer (Manual + Automated Testing)
    ```
    MERN Stack (React, Express, MongoDB, Node.js) and AI/ML/LLM are completely absent.
- **Score Calibration & Compression**:
  - `src/prompts/scoring_prompt.txt:17-21`:
    - "If the core domain matches, assign a solid score (50+)."
    - "If the JD asks for Automation Testing... or Java Backend, score HIGH (70-90)"
    - "If the JD asks for .NET/C#, score MODERATE (60-75)"
    - "ONLY output match_score: 0 if the JD explicitly states 3+ years... or complete mismatch"
- **Missing Skills Hallucination Trigger**:
  - `src/prompts/scoring_prompt.txt:18`: "The candidate is a FRESHER. Do NOT heavily penalize them for lacking secondary/advanced tools (like AWS, Docker, Kubernetes, Kafka, CI/CD, JIRA)."
  - In `data_folder/plain_text_resume.yaml:107-108`, `Docker` and `Kubernetes` are listed under `skills.Tools & Platforms`.

### 1.3 Candidate Profile & Configuration Observations
- **Profile Files**:
  - `config/profile.json` does not exist on disk (`view_file` returned file not found).
  - `data_folder/plain_text_resume.yaml:1-141` contains the complete master resume (Kaustubh Kale, BE IT 2026, 7.70 CGPA, Java, Python, SQL, C#, JS, TS, React, Next.js, Node.js, Mongoose, MongoDB, Docker, Kubernetes, Selenium, JUnit, Postman, pytest, SmartApply, CampFlow, Neon-Pulse).
  - `config.yaml:6-13` specifies:
    ```yaml
    ai:
      provider: "deepseek"
      scoring_model: "deepseek-chat"
      tailoring_model: "deepseek-chat"
      model: "deepseek-chat"
      api_key: ""
      temperature: 0.3
    ```
- **Environment & Keys**:
  - `.env` contains active `GEMINI_API_KEY` and `GROQ_API_KEY` (`gsk_...`). `DEEPSEEK_API_KEY` is commented out.
  - Python packages verified: `openai==2.54.0` (installed), `google.genai` (installed).

### 1.4 Test Suite Observations
- Executed `pytest tests/test_m3_scoring_telemetry.py -q`: 17 passed in 4.69s.
- Executed `pytest tests/test_adversarial_m3_stress.py tests/test_m3_challenger2_adversarial.py tests/test_m3_challenger2_independent.py -q`: 60 passed in 4.13s.

---

## 2. Logic Chain

1. **Premise 1**: `src/ai_engine.py` calls `https://api.deepseek.com` and has `runtime_settings` defaulting to `deepseek-chat` (Observation 1.1).
2. **Premise 2**: In `.env`, `DEEPSEEK_API_KEY` is disabled, while `GEMINI_API_KEY` and `GROQ_API_KEY` are provided. The prompt directive strictly prohibits calling DeepSeek (Observation 1.3).
3. **Inference 1**: The scoring audit cannot execute against `src/ai_engine.py` as currently implemented. A standalone multi-provider engine `scoring_audit/ai_engine_v2.py` must be built that routes requests to Gemini (`gemini-2.0-flash`) and Groq (`llama-3.3-70b-versatile`) while keeping `src/ai_engine.py` untouched until Phase 7 production integration.
4. **Premise 3**: Gemini free tier enforces 15 RPM (1 req / 4.0s) and Groq free tier enforces 30 RPM (1 req / 2.0s). `src/scorer.py` currently fires all tasks concurrently via `asyncio.gather(*tasks)` (Observation 1.1).
5. **Inference 2**: `scoring_audit/ai_engine_v2.py` must incorporate explicit asynchronous rate limiting (token bucket or sliding interval: min 4.1s for Gemini, min 2.1s for Groq) to prevent unhandled HTTP 429 quota exhaustion during the 600 synthetic and ~73 real job scoring runs.
6. **Premise 4**: In `src/prompts/scoring_prompt.txt`, MERN Stack and AI/ML/LLM are omitted from target roles and scoring brackets (Observation 1.2), yet the candidate possesses extensive MERN and AI/LLM experience (Observation 1.3).
7. **Inference 3**: When evaluated by LLMs with the baseline prompt, MERN and AI jobs fall into the generic "50+" guideline or get penalized because the candidate's formal job title is "Java Developer Intern", explaining the severe under-scoring and score compression.
8. **Premise 5**: Line 18 of `scoring_prompt.txt` states candidate lacks tools "(like AWS, Docker, Kubernetes...)", whereas candidate's resume explicitly lists Docker and Kubernetes (Observation 1.2, 1.3).
9. **Inference 4**: Models hallucinate Docker and Kubernetes as `missing_skills` because the system prompt itself primes the LLM to believe the candidate lacks them.
10. **Inference 5**: `scoring_audit/scoring_prompt_v2.txt` must explicitly include all 7 target domains (including MERN and AI/ML/LLM), define a granular 6-tier rubric (90-98, 75-89, 60-74, 35-59, 0-20), remove Docker/Kubernetes from the lack list, and relax reason length to 8-15 words.

---

## 3. Caveats

- **Grok Model vs Groq Endpoint**: The project plan (`SCORING_AUDIT_PLAN.md`) references "Grok" in places, but `.env` provides `GROQ_API_KEY` with a `gsk_` prefix (Groq SDK key). The implementation must use Groq (`https://api.groq.com/openai/v1`) with fast models like `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`.
- **Existing Live Test Scripts**: `tests/test_live_m3_scoring.py` and `tests/test_live_multi_call_stability.py` are DeepSeek-specific integration scripts. They should remain unmodified during the audit and only updated if live tests are migrated to multi-provider in Phase 7.
- **No `config/profile.json`**: Any reference to `config/profile.json` in user prompts or documentation should map to `data_folder/plain_text_resume.yaml` and `config.yaml`.

---

## 4. Conclusion

The existing codebase, prompt architecture, and candidate profile have been thoroughly cataloged and analyzed. All prerequisites for generating the 300 synthetic JDs, constructing `scoring_audit/ai_engine_v2.py`, executing baseline dual-provider scoring, and creating `scoring_prompt_v2.txt` are clearly understood and documented in `report.md`.

---

## 5. Verification Method

To independently verify the facts and findings of this survey:

1. **Verify Python packages and API keys**:
   ```powershell
   python -c "import openai, google.genai; print('OpenAI:', openai.__version__, '| Google GenAI: OK')"
   ```
2. **Verify test suite baseline**:
   ```powershell
   pytest tests/test_m3_scoring_telemetry.py -q
   ```
3. **Verify absence of `config/profile.json` and presence of master resume**:
   ```powershell
   Test-Path "config/profile.json"  # Returns False
   Test-Path "data_folder/plain_text_resume.yaml"  # Returns True
   ```
4. **Inspect generated report**:
   View `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1\report.md`.
