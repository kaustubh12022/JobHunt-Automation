# Technical Survey & Forensic Audit Report: AI Scoring Engine & Prompt Architecture

**Date**: 2026-09-29  
**Investigator**: Explorer Survey AI (`explorer_survey_ai_1`)  
**Scope**: Codebase audit of `src/ai_engine.py`, `src/prompts/scoring_prompt.txt`, candidate profile & resume data, project configuration, and automated test suites in preparation for the Multi-Provider AI Scoring Audit (Gemini & Groq).

---

## 1. Executive Summary

This investigation conducted a granular, code-level survey of the AI scoring subsystem in the JobHunt-Automation repository. The objective is to establish the baseline architectural state, diagnose root causes of known scoring failures (specifically MERN stack and AI/ML/LLM under-scoring, score compression, and false missing skills), audit candidate profile data, and evaluate testing/SDK dependencies for migrating to Gemini and Groq while strictly eliminating DeepSeek.

### Key Findings
1. **Hardcoded DeepSeek Infrastructure in `src/ai_engine.py`**: The scoring engine is exclusively coupled to DeepSeek (`https://api.deepseek.com`, `deepseek-chat`, and prefix caching cost calculations). It lacks any client-side rate limiting (essential for Gemini's 15 RPM and Groq's 30 RPM free tiers) and relies on unthrottled concurrent requests via `asyncio.gather()`.
2. **Critical Prompt Omissions in `src/prompts/scoring_prompt.txt`**: The baseline prompt completely omits MERN Stack and AI/ML/LLM roles from `=== CANDIDATE TARGET ROLES ===` and provides scoring calibration rules only for Java/QA (70-90) and .NET (60-75). Consequently, MERN and AI/ML/LLM roles fall back to ambiguous 50+ guidance and suffer severe under-scoring and score compression.
3. **Prompt Hallucination Trigger for Missing Skills**: Line 18 of `scoring_prompt.txt` erroneously states that entry-level candidates lack tools "(like AWS, Docker, Kubernetes, Kafka, CI/CD, JIRA)", directly causing LLMs to hallucinate Docker and Kubernetes as `missing_skills` even though both are explicitly present in the candidate's master resume.
4. **Canonical Candidate Profile Location**: `config/profile.json` does not exist on disk. The single source of truth for the candidate's resume and technical background is `data_folder/plain_text_resume.yaml`, with configuration in `config.yaml` and EEO/application answers in system rules.
5. **SDK & API Key Readiness**: In `.env`, `GEMINI_API_KEY` and `GROQ_API_KEY` (along with `GROK_API_KEY` pointing to the same `gsk_` key) are populated. In the Python 3.13 virtual environment, `openai==2.54.0` and `google.genai` are installed and ready. Groq is fully supported via OpenAI SDK client compatibility (`base_url="https://api.groq.com/openai/v1"`). Existing Milestone 3 unit tests (17 tests in `tests/test_m3_scoring_telemetry.py` and 60 tests in adversarial suites) pass completely.

---

## 2. Examination of `src/ai_engine.py` & Scoring Pipeline

### 2.1 Call Chain & Execution Flow
The AI scoring workflow spans `src/scorer.py` and `src/ai_engine.py`:
1. **Entry Point (`src/scorer.py:311`)**: `score_jobs(jobs: list[Job], test_mode=False, callbacks=None, stop_event=None)` receives jobs passing Phase 1 scraping.
2. **Deterministic Pre-Filters (`src/scorer.py:322-351`)**:
   - Freshness filter: skips jobs older than `hours_old` (default 72h).
   - Zero-token regex pre-filters: `matches_senior_title()`, `matches_out_of_scope_role()`, `requires_3_plus_years()`, and `is_relevant_jd()`.
3. **Caching Layer (`src/scorer.py:368-400`)**: Queries SQLite via `get_cached_jd_score(norm_url)`. On cache hit, assigns score, missing skills, and requirements with 0 API tokens and $0.00 cost.
4. **Boilerplate Stripping (`src/scorer.py:401-408`)**: Aggressively strips "About Us", "Benefits", "EEO", and company profiles using `strip_boilerplate()` to reduce prompt tokens.
5. **Async Delegation (`src/scorer.py:15-18`)**: Calls `call_ai_scoring_async(user_prompt)` which imports and delegates to `src.ai_engine.call_ai_scoring_async()`.
6. **Concurrent Dispatch with Cache Warming (`src/scorer.py:470-496`)**:
   - First job runs sequentially to "warm" the prompt prefix cache on DeepSeek.
   - Subsequent jobs run concurrently using `asyncio.gather(*tasks)`.
7. **Post-Scoring Filter (`src/scorer.py:512-515`)**: Discards jobs with `job.score < min_score` (default 60 from `config.yaml`).

### 2.2 Model Selection & Runtime Settings
In `src/ai_engine.py`:
- Lines 21–27 define global `runtime_settings`:
  ```python
  runtime_settings = {
      "scoring_model": "deepseek-chat",
      "scoring_thinking": False,
      "tailoring_model": "deepseek-chat",
      "tailoring_thinking": True,
  }
  ```
- Lines 118–126 (`_get_client`) and 133–141 (`_get_async_client`) load configuration:
  ```python
  client = AsyncOpenAI(
      api_key=os.environ.get("DEEPSEEK_API_KEY", config['ai']['api_key']),
      base_url="https://api.deepseek.com"
  )
  model = config['ai'].get('scoring_model', config['ai'].get('model', 'deepseek-chat'))
  ```
- In `call_ai_scoring_async` (lines 166–185), `scoring_model` is read from `runtime_settings` (default `"deepseek-chat"`) and `scoring_thinking` is checked. `temperature` is fixed at `0.3`, and `response_format={"type": "json_object"}` is passed.

### 2.3 Prompt Loading & Context Injection
In `src/ai_engine.py:151-155`:
```python
def _get_prompt(filename: str, master_resume: dict) -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content.replace("{master_resume_json}", json.dumps(master_resume, indent=2))
```
`_get_master_resume()` (lines 143–148) memoizes `load_resume()` from `src/config_loader.py`, which parses `data_folder/plain_text_resume.yaml`. The JSON-serialized resume is injected into the system prompt.

### 2.4 Response Parsing & Error Handling
In `src/ai_engine.py:223-234`:
```python
content = response.choices[0].message.content
if content:
    try:
        json.loads(content)
    except json.JSONDecodeError:
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            extracted = content[start_idx:end_idx]
            json.loads(extracted)
            content = extracted
```
In `src/scorer.py:425-445`, `result = json.loads(response_text[start_idx:end_idx])` extracts:
- `raw_score = result.get("match_score", result.get("score", 0))`
- `missing_skills = result.get("missing_skills", [])`
- `reasons = result.get("reason", "")`
- `job_summary = result.get("job_summary", "")`
- `extracted_requirements = result.get("extracted_requirements", "")`
- `is_testing_role = result.get("is_testing_role", False)`

Retry logic in `src/ai_engine.py:186-242`:
- 3 attempts with exponential backoff: `delay = (2 ** attempt) * 2 + random.uniform(0, 1)`.
- If the 3rd attempt fails, it raises the exception.
- Client is closed in `finally: await client.close()`.

### 2.5 DeepSeek Coupling & Deficiencies for Multi-Provider
1. **Hardcoded DeepSeek Base URL & Cost Math**:
   - `_get_client` and `_get_async_client` hardcode `base_url="https://api.deepseek.com"`.
   - `calculate_deepseek_cost` assumes DeepSeek's $0.07/$0.27 cache hit/miss and $1.10 completion pricing.
   - `TokenUsage` object expects DeepSeek-specific token fields (`prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`).
2. **Absence of Rate Limiting**:
   - `score_jobs()` dispatches all relevant jobs simultaneously via `asyncio.gather(*tasks)`.
   - While DeepSeek Tier 2/3 handles higher concurrency, Gemini free tier allows max 15 RPM (1 req / 4.0s) and Groq free tier allows max 30 RPM (1 req / 2.0s). Unthrottled calls will immediately fail with HTTP 429.
3. **No Provider Abstraction or Fallback**:
   - No mechanism exists to route between Gemini, Groq, or local mock providers.
   - No dynamic failover if one provider encounters rate limits or service outages.

---

## 3. Examination of Prompt Architecture (`src/prompts/scoring_prompt.txt`)

### 3.1 Content Breakdown
`src/prompts/scoring_prompt.txt` consists of 35 lines structured into 4 sections:
1. **Candidate Master Resume Injection** (lines 3–5): `{master_resume_json}`.
2. **Candidate Target Roles** (lines 7–14):
   - Java Backend Developer (Spring, JDBC, REST APIs, SQL)
   - Automation Tester / QA Automation (Selenium, JUnit, Postman, pytest, Test Case Design)
   - .NET / C# Developer (candidate has Azure Fundamentals cert and OOP foundation)
   - Software Engineer / Full Stack Developer (Python, JavaScript, HTML/CSS)
   - Software Tester / QA Engineer (Manual + Automated Testing)
3. **Scoring Rules** (lines 15–21):
   - Score 0-100 based on core match.
   - "If the core domain matches, assign a solid score (50+)".
   - Fresher rule: "Do NOT heavily penalize them for lacking secondary/advanced tools (like AWS, Docker, Kubernetes, Kafka, CI/CD, JIRA)".
   - Explicit targets: Automation Testing / Java Backend -> HIGH (70-90); .NET/C# -> MODERATE (60-75).
   - Drop rule: "ONLY output match_score: 0 if 3+ years experience or complete language mismatch (e.g. C++, Ruby)".
4. **JSON Schema Specification & Constraints** (lines 23–34):
   - Returns JSON with `match_score`, `reason` (10-12 words), `job_summary`, `missing_skills` (top 5), `extracted_requirements`, `is_testing_role`.

### 3.2 Root Causes of Scoring Deficiencies

#### A. Under-Scoring of MERN Stack Roles
- **Omission from Target Roles**: `=== CANDIDATE TARGET ROLES ===` omits MERN Stack, React Developer, Node.js Developer, or MongoDB.
- **Missing Domain Rubric**: The rubric only provides guidance for Java/QA (70-90) and .NET (60-75). MERN roles fall into the generic "50+" guideline.
- **Fresher Job Title Bias**: The candidate's resume lists "Java Developer Intern" under professional experience. Because MERN is not listed as a target role, LLMs judge MERN JDs as having a mismatched job history, penalizing them down to 40–55 (below the 60 cutoff).
- **Reality**: The candidate possesses extensive modern web experience: React, Next.js, Node.js, Mongoose, MongoDB, JavaScript, TypeScript, and HTML/CSS, with full-stack projects (CampFlow, Neon-Pulse).

#### B. Under-Scoring of AI / ML / LLM Roles
- **Omission from Target Roles**: AI/ML/LLM/Agentic AI is completely absent from target roles.
- **Rubric Blindspot**: No scoring bracket exists for AI or LLM roles.
- **Failure to Recognize Project Depth**: The candidate built SmartApply, featuring LLM integration (prompt engineering, prompt caching, token cost optimization, multi-dimensional scoring). Without explicit instructions, LLMs evaluate AI roles against an entry-level candidate having only a Java internship, assigning low scores (30–50).

#### C. Score Compression & Coarse Clustering
- **Narrow Calibration Targets**: The prompt specifies only two score bands: HIGH (70-90) and MODERATE (60-75).
- **Lack of Multi-Tier Rubric**: There is no graded guidance for:
  - 90–98: Exceptional match (core stack + verified project alignment)
  - 80–89: Strong match (fresher-appropriate core stack)
  - 70–79: Good match (core languages match, partial framework match)
  - 60–69: Moderate/transferable match (.NET with OOP/Azure, general SWE)
  - 40–59: Weak match (adjacent domain, heavy secondary requirements)
  - 0–20: Explicit senior (3+ yrs) or forbidden tech stack (PHP, Ruby, iOS)
- Consequently, models compress 80% of all relevant scores into the 68–76 range.

#### D. False `missing_skills` Reporting
- **Self-Defeating Prompt Text (Line 18)**:
  `"...lacking secondary/advanced tools (like AWS, Docker, Kubernetes, Kafka, CI/CD, JIRA)..."`
  LLMs interpret this prompt parenthetical as factual context that the candidate lacks Docker and Kubernetes. However, the candidate's resume explicitly includes:
  `skills.Tools & Platforms: Docker, Kubernetes, MongoDB, Git, GitHub...`
  As a result, models routinely report Docker and Kubernetes as missing skills!
- **Lack of Canonical Normalization**: Synonyms such as "PostgreSQL" vs "SQL/MySQL", "Express" vs "Node.js", or "RESTful APIs" vs "REST APIs" are often reported as missing because the prompt lacks fuzzy or semantic equivalence instructions.

#### E. Strict Word-Count Constraint Failures
- Line 25 enforces: `"reason": a concise explanation in EXACTLY 10 to 12 words. Do not exceed 12 words under any circumstance.`
- LLMs frequently struggle with exact word-count constraints, resulting in truncated sentences, awkward phrasing, or schema formatting bugs when the model attempts to force a 10-12 word string.

---

## 4. Examination of Candidate Profile & Resume Data

### 4.1 Profile Location & Discrepancy Note
- `config/profile.json` referenced in earlier prompt instructions does **not exist** in the repository.
- The single authoritative master resume is located at:  
  `c:\Users\kalek\Desktop\Projects\Job_Hunt\data_folder\plain_text_resume.yaml`
- System-wide search settings and thresholds are located at:  
  `c:\Users\kalek\Desktop\Projects\Job_Hunt\config.yaml`
- Candidate demographic and EEO form filling rules are documented in:  
  `C:\Users\kalek\.gemini\config\rules\autoapply-profile-rule.md`

### 4.2 Candidate Technical Inventory (Kaustubh Kale)

| Category | Candidate Master Resume Contents |
|----------|----------------------------------|
| **Education** | B.E. in Information Technology (2022–2026), SKNSITS Lonavala, 7.70 CGPA |
| **Professional Experience** | Java Developer Intern, CWIPedia Technologies (Jan 2025 – Feb 2025, Pune) — Backend components, Java, SQL, JDBC, REST APIs, responsive UI |
| **Core Languages** | Java, Python, SQL, C# (Basics via Azure cert), JavaScript, TypeScript, HTML, CSS |
| **Frameworks & Libraries** | React, Next.js, Node.js, Vite, Mongoose, Spring Core (Basics), JDBC, REST APIs, JSON, MVC Architecture, Pandas, Asyncio, Jinja2, BeautifulSoup, Regex |
| **Testing Tools** | JUnit (Unit Testing), Postman (API Testing), Selenium (UI Automation), pytest (Python Testing), Manual Testing Fundamentals, Test Case Design |
| **Databases & Cloud** | MongoDB, MySQL, Microsoft Azure (Fundamentals Certified AZ-900), Docker, Kubernetes |
| **Key Projects** | 1. **SmartApply**: AI-Driven Job Automation Pipeline (Python, Pandas, DeepSeek API, Jinja2, WeasyPrint, BeautifulSoup)<br>2. **CampFlow**: Hospitality Automation Suite (Web Automation, Vercel)<br>3. **Neon-Pulse**: Pattern Recognition Engine (Vanilla JavaScript, CSS3) |
| **Certifications** | Microsoft Azure Fundamentals, Cybersecurity - Google (Coursera) |
| **Locations & Availability** | Pune (Current), Mumbai, Bangalore; Open to Remote/Hybrid/In-Person/Relocation |

### 4.3 Domain Alignment Matrix

| # | Target Domain | Candidate Resume Evidence | Baseline Prompt Status | Recommended Prompt v2 Calibration |
|---|---------------|---------------------------|------------------------|-----------------------------------|
| 1 | **Java / Spring Backend** | Java, Spring Core (Basics), JDBC, REST APIs, SQL, MySQL, Internship | Explicitly included (70-90) | Keep HIGH (80–95 for core match) |
| 2 | **Python Backend (Django/Flask)** | Python, Pandas, Asyncio, REST APIs, SmartApply backend | Mentioned as generic SWE | Explicitly include Python/APIs (75–90) |
| 3 | **QA / Automation Testing** | Selenium, JUnit, Postman, pytest, Test Case Design | Explicitly included (70-90) | Keep HIGH (80–95 for QA/SDET) |
| 4 | **.NET / C# Developer** | C# (Basics), Azure cert, OOP, SQL, DBMS | Explicitly included (60-75) | Calibrate MODERATE (60–75) |
| 5 | **General SWE / Full Stack** | JS, TS, HTML, CSS, React, Python, Java | Explicitly included (50+) | Calibrate GOOD (70–85) |
| 6 | **MERN Stack** | React, Next.js, Node.js, Mongoose, MongoDB, JS/TS, CampFlow | **OMITTED (Critical Defect)** | Add to Target Roles; Calibrate HIGH (75–90) |
| 7 | **AI / ML / LLM / Agentic AI** | Python, Prompt Engineering, LLM Integration, SmartApply AI Pipeline | **OMITTED (Critical Defect)** | Add to Target Roles; Calibrate HIGH (75–88 for entry-level AI/LLM) |

---

## 5. Test Suite & Dependency Audit

### 5.1 Test Suite Verification
The repository contains 36 test files in `tests/`. Key tests evaluating AI scoring and telemetry:
- `tests/test_m3_scoring_telemetry.py` (564 lines):
  - `test_m3_scoring_model_runtime_defaults`: Checks `runtime_settings["scoring_model"] == "deepseek-chat"`.
  - `test_m3_call_ai_scoring_passes_json_object_mode`: Verifies JSON mode call structure.
  - `test_m3_scoring_json_error_recovery`: Tests extraction of markdown-wrapped or embedded JSON.
  - `test_m3_scoring_prompt_prefix_structure`: Tests presence of rubric sections, target roles, and token length >= 1024.
  - `test_m3_zero_senior_or_irrelevant_jobs_reach_ai`: Asserts pre-filter rejects senior/irrelevant JDs before API.
  - All 17 tests **PASSED** when executed via `pytest`.
- `tests/test_adversarial_m3_stress.py` & `tests/test_m3_challenger2_*.py`:
  - 60 tests covering flaky responses, score coercion, TokenUsage arithmetic.
  - All 60 tests **PASSED**.
- `tests/test_live_m3_scoring.py` & `tests/test_live_multi_call_stability.py`:
  - Live scripts designed for DeepSeek prompt caching verification. These must NOT be executed with DeepSeek per strict user constraints.

### 5.2 Python Environment & Provider SDK Status
- **Python Version**: Python 3.13.2 (Windows x64).
- **Installed Packages**:
  - `openai==2.54.0`: Pre-installed and verified. Supports Groq directly via `AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)`.
  - `google.genai`: Pre-installed and verified via `import google.genai`.
  - `groq`: Not installed, but redundant since `openai` provides 100% native OpenAI-compatible integration with Groq endpoints.
  - `pydantic`, `pyyaml`, `pandas`, `beautifulsoup4`, `jinja2`, `loguru`: Pre-installed and verified.
- **Environment API Keys (`.env`)**:
  - `GEMINI_API_KEY`: Present (`AQ.Ab8...`).
  - `GROQ_API_KEY` / `GROK_API_KEY`: Present (`gsk_XmHA...`).
  - `DEEPSEEK_API_KEY`: Commented out (`# DEEPSEEK_API_KEY=...`).
  - **Compliance**: Zero DeepSeek calls required or permitted.

---

## 6. Architecture & Implementation Blueprint

### 6.1 Requirements for `scoring_audit/ai_engine_v2.py`
To satisfy the dual-provider requirements without regressions:
1. **Strict Provider Routing**:
   - Provider `gemini`: Uses `google.genai.Client` with model `gemini-2.0-flash`.
   - Provider `groq`: Uses `AsyncOpenAI` with `base_url="https://api.groq.com/openai/v1"` and model `llama-3.3-70b-versatile` (or `llama-3.1-8b-instant`).
   - Zero fallback to DeepSeek.
2. **Client-Side Rate Limiting**:
   - Implement asynchronous token-bucket or sliding-window rate limiters:
     - Gemini: strictly <= 15 requests per minute (minimum interval: 4.1 seconds between calls).
     - Groq: strictly <= 30 requests per minute (minimum interval: 2.1 seconds between calls).
3. **Robust JSON Extraction**:
   - Both Gemini and Groq support structured JSON responses. Add regex fallback to parse `{...}` even if wrapped in markdown codeblocks.
4. **Normalized Telemetry Tracking**:
   - Return normalized token metrics: `prompt_tokens`, `completion_tokens`, `total_tokens`, `response_time_ms`, `cost_usd` ($0.00 for free tier).

### 6.2 Requirements for `scoring_audit/scoring_prompt_v2.txt`
1. **Add Full 7 Target Domains**:
   - Domain 1: Java / Spring / Backend Development
   - Domain 2: Python / Django / Flask / Backend
   - Domain 3: QA / Automation / Testing (Selenium, JUnit, Postman, pytest)
   - Domain 4: .NET / C# / ASP.NET (Azure Fundamentals, OOP)
   - Domain 5: Full Stack / General Software Engineering
   - Domain 6: MERN Stack (React, Express, MongoDB, Node.js)
   - Domain 7: AI / ML / LLM / Agentic AI (Python, LLM integration, prompt engineering)
2. **Granular Calibration Tiers**:
   - 88–98: Direct match on core language/framework + relevant project/internship.
   - 75–87: Strong match on entry-level stack (MERN, Java, QA, Python AI).
   - 60–74: Moderate/transferable match (.NET, adjacent tech, general SWE).
   - 35–55: Partial/weak match (heavy specialized tech like cloud/DevOps where candidate only has basics).
   - 0–20: Out of scope (PHP, Ruby, iOS/Swift, Android/Kotlin) or strict 3+ years experience.
3. **Fix Missing Skills Prompting**:
   - Remove the misleading statement that the candidate lacks Docker and Kubernetes.
   - Clarify that if a tool appears anywhere in the resume (including Docker, Kubernetes, MongoDB, Git), it is NOT missing.
   - Add synonym awareness (e.g., PostgreSQL matches SQL/MySQL, Express matches Node.js).
4. **Relaxed Reason Formatting**:
   - Change "EXACTLY 10 to 12 words" to "a concise explanation in 8 to 15 words" to prevent truncation and parsing syntax errors.

---

## 7. Conclusion

The technical investigation confirms that the AI scoring subsystem is fully understood and primed for the audit and rewrite:
- `src/ai_engine.py` and `src/scorer.py` provide a clean separation of concerns, making the creation of `scoring_audit/ai_engine_v2.py` straightforward.
- All dependencies (`google.genai`, `openai`) and API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) are verified and functional.
- The deficiencies of `scoring_prompt.txt` have been isolated with root-cause certainty.
- The ground truth dataset (`regex_audit/evaluation/ground_truth.jsonl`) and master raw dataset provide the exact reference points needed for validation.
