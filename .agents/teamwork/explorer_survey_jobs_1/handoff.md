# Handoff Report: Survey of Real Production Jobs & Scoring Audit Architecture

**Agent:** `explorer_survey_jobs_1`  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_jobs_1`  
**Recipient:** `parent` (`7cb7199f-c2a4-46e3-be86-1c86a84aa546`)  
**Date:** 2026-09-29  
**Handoff Type:** Hard (Task complete)

---

## 1. Observation

1. **Surviving Production Jobs Location & Line Counts**:
   - `regex_audit/filter_results/layer1_pandas_pass.jsonl`: Contains exactly **73 lines/records**.
   - `regex_audit/filter_results/layer1_pandas_fail.jsonl`: Contains **1,064 lines/records**.
   - `regex_audit/filter_results/layer2_regex_pass.jsonl`: Contains exactly **58 lines/records**.
   - `regex_audit/filter_results/layer2_regex_fail.jsonl`: Contains **15 lines/records**.
   - `regex_audit/evaluation/ground_truth.jsonl`: Contains **1,137 lines/records** (60 PASS, 1,077 FAIL).
   - `regex_audit/evaluation/false_positives.jsonl`: Contains **8 records**.
   - `regex_audit/evaluation/false_negatives.jsonl`: Contains **10 records**.
   - Verbatim check tool output:
     ```
     layer1_pass: 73
     layer1_fail: 1064
     layer2_pass: 58
     layer2_fail: 15
     ground_truth: 1137
     false_positives: 8
     false_negatives: 10
     ```

2. **Description Field Asymmetry**:
   - In `regex_audit/filter_results/layer1_pandas_pass.jsonl`, all 73 records contain:
     `['job_index', 'id', 'title', 'company', 'location', 'description', 'url', 'source', 'job_type', 'date_posted', 'is_remote', 'scraped_at', 'filter_layer', 'status']`.
     The `description` field is 100% present and non-empty (lengths range from 419 to 11,878 chars, mean 3,256 chars).
   - In `regex_audit/filter_results/layer2_regex_pass.jsonl`, records contain:
     `['job_index', 'id', 'title', 'company', 'location', 'url', 'filter_layer', 'status', 'matched_anchors', 'matched_tools']`.
     `description` is **completely absent** across all 58 records.

3. **Master Raw Datasets**:
   - `regex_audit/master_raw_dataset_2026-09-29.jsonl`: 6,407,800 bytes, exactly 1,137 JSON lines.
   - `regex_audit/master_raw_dataset_2026-09-29.json`: 6,761,410 bytes, exactly 1,137 JSON array objects.
   - Keys: `['job_index', 'id', 'title', 'company', 'location', 'description', 'url', 'source', 'job_type', 'date_posted', 'is_remote', 'raw_metadata', 'scraped_at']`.
   - Complete integrity: 1,137 titles, companies, descriptions, and URLs are non-null.

4. **Directory Structure of `scoring_audit/`**:
   - `os.path.exists("scoring_audit")` returns `False`. The directory has not yet been initialized.
   - Target subdirectories required per `SCORING_AUDIT_PLAN.md`: `scoring_audit/scores/`, `scoring_audit/analysis/`.

5. **Environment & API Keys**:
   - `.env` contains:
     - `GEMINI_API_KEY`: Present
     - `GROQ_API_KEY`: Present
     - `GROK_API_KEY`: Present
     - `DEEPSEEK_API_KEY`: Absent (strictly forbidden)
   - Python environment verification:
     - `google.genai` is installed.
     - `openai` is installed (capable of connecting to Groq via `base_url="https://api.groq.com/openai/v1"`).

6. **Scoring Prompt Baseline**:
   - `src/prompts/scoring_prompt.txt` specifies candidate target domains 1 through 5 (Java, Automation Tester, .NET, Full Stack Python/JS, Software Tester). Target Domain 6 (MERN Stack) and Target Domain 7 (AI/ML/LLM/Agentic AI) are omitted.

---

## 2. Logic Chain

1. **Reconciliation of "~73 Jobs"**:
   - Observation 1 shows `layer1_pandas_pass.jsonl` contains 73 records.
   - `SCORING_AUDIT_PLAN.md` lines 116 and 165 state: "For 300 synthetic + 73 real × 2 providers each = 746 total API calls" and "~73 × 2 = 146 API calls".
   - Because $300 \times 2 + 73 \times 2 = 746$, the calculation specifically depends on 73 real jobs, which matches the exact count of Layer 1 survivors.
   - However, the baseline Layer 2 filter dropped 15 of these 73 jobs (Observation 1), leaving 58 jobs in `layer2_regex_pass.jsonl`.
   - Therefore, the "~73 surviving jobs" referenced in the plan refers to the Layer 1 survivors dataset.

2. **Necessity of Schema Join for Downstream Scoring**:
   - Observation 2 demonstrates that `layer2_regex_pass.jsonl` does NOT store `description`.
   - LLM scoring prompts (Observation 6) require the full text of the job description to evaluate skill overlap, missing skills, and domain relevance.
   - Therefore, any downstream worker scoring the production jobs must either:
     a) Load `regex_audit/filter_results/layer1_pandas_pass.jsonl` directly (73 jobs with full descriptions), OR
     b) Filter `layer1_pandas_pass.jsonl` against the `job_index`es in `layer2_regex_pass.jsonl` to obtain the 58 Layer 2 survivors with full descriptions.

3. **Infrastructure Readiness**:
   - Observation 4 shows `scoring_audit/` does not exist yet.
   - Observation 5 confirms `google.genai` and `openai` are installed, and `GEMINI_API_KEY` and `GROQ_API_KEY` are present in `.env`.
   - Therefore, downstream workers can implement `scoring_audit/ai_engine_v2.py` without requiring package installation or credential creation.

---

## 3. Caveats

1. **Candidate Target Roles**: While 58 jobs passed Layer 2 regex filtering, 4 of the 15 jobs dropped in Layer 2 (Jobs #84, #220, #246, #722) are legitimate in-scope entry roles that were erroneously dropped due to regex deficiencies (False Negatives). Scoring all 73 Layer 1 jobs will allow the AI engine to evaluate these valid opportunities as well.
2. **Rate Limits**: Gemini free tier allows 15 RPM (min 4.0s delay between calls). Groq allows 30 RPM (min 2.0s delay between calls). Total time to score 73 real jobs across both providers is ~3-5 minutes.
3. **DeepSeek Ban**: DeepSeek API is completely unconfigured and must not be called or referenced in any fallback logic.

---

## 4. Conclusion

1. **Surviving Production Jobs**:
   - Located at: `regex_audit/filter_results/layer1_pandas_pass.jsonl` (73 jobs, all complete with `description`).
   - If restricted to Layer 2 baseline survivors: 58 jobs, obtained by matching `job_index` from `regex_audit/filter_results/layer2_regex_pass.jsonl` back to `layer1_pandas_pass.jsonl`.
2. **Master Dataset**:
   - `regex_audit/master_raw_dataset_2026-09-29.jsonl` is intact with 1,137 valid jobs (6.11 MB).
3. **Scoring Audit Setup**:
   - `scoring_audit/` is ready to be initialized with `scoring_audit/scores/` and `scoring_audit/analysis/`.
4. **Code Execution Path**:
   - Both `google.genai` and `openai` are present and ready for Gemini and Groq multi-provider integration.

---

## 5. Verification Method

To independently verify the observations and conclusions:

1. **Verify Line Counts & Schema Integrity**:
   ```powershell
   python -c "
   import json
   for path in ['regex_audit/filter_results/layer1_pandas_pass.jsonl', 'regex_audit/filter_results/layer2_regex_pass.jsonl', 'regex_audit/filter_results/layer2_regex_fail.jsonl']:
       with open(path, 'r', encoding='utf-8') as f:
           lines = [json.loads(line) for line in f]
       has_desc = all('description' in x for x in lines)
       print(path, '-> count:', len(lines), '| has description:', has_desc)
   "
   ```
   *Expected Output*:
   - `layer1_pandas_pass.jsonl -> count: 73 | has description: True`
   - `layer2_regex_pass.jsonl -> count: 58 | has description: False`
   - `layer2_regex_fail.jsonl -> count: 15 | has description: False`

2. **Verify Environment Keys & SDKs**:
   ```powershell
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('GEMINI:', bool(os.getenv('GEMINI_API_KEY')), 'GROQ:', bool(os.getenv('GROQ_API_KEY')), 'DEEPSEEK:', bool(os.getenv('DEEPSEEK_API_KEY'))); import google.genai, openai; print('SDKs: google.genai and openai loaded successfully')"
   ```
   *Expected Output*:
   - `GEMINI: True GROQ: True DEEPSEEK: False`
   - `SDKs: google.genai and openai loaded successfully`

3. **Inspect Generated Report**:
   - File: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_jobs_1\report.md`
