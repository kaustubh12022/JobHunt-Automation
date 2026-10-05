# Handoff Report: Empirical Adversarial Challenge of Dual-Provider Scoring Engine (M1/M2)

**Author**: Empirical Challenger 2 (`challenger_m1_m2_2`)  
**Target Milestone**: M1 / M2 - Dual-Provider Scoring Engine & Dataset Robustness  
**Recipient**: Parent Orchestrator (`7cb7199f-c2a4-46e3-be86-1c86a84aa546`)  
**Verdict**: **REQUEST_CHANGES**  
**Date**: 2026-09-29  
**Artifacts Produced**:
- `tests/test_m1_m2_challenger2_ai_engine.py` (Comprehensive 27-test empirical adversarial test suite)
- `.agents/teamwork/challenger_m1_m2_2/handoff.md` (This report)

---

## 1. Observation

A 27-test empirical adversarial battery was executed directly against `scoring_audit/ai_engine_v2.py` via pytest:

### Observation 1.1: Markdown Fenced JSON Extraction Defect on Trailing Commentary with Braces
In `scoring_audit/ai_engine_v2.py`, lines 212–217:
```python
if cleaned.startswith("```"):
    fence_match = re.match(
        r"^```(?:json)?\s*\n?([\s\S]*?)\n?```$", cleaned, re.IGNORECASE
    )
    if fence_match:
        cleaned = fence_match.group(1).strip()
```
And lines 227–235:
```python
start_idx = cleaned.find("{")
end_idx = cleaned.rfind("}")
if start_idx != -1 and end_idx > start_idx:
    candidate = cleaned[start_idx : end_idx + 1]
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        pass
```
When an LLM generates a fenced JSON block followed by any explanatory notes containing curly braces (e.g. `"```json\n{...}\n```\nNote: check {skill_tags}."`), `test_trailing_commentary_with_braces` in `tests/test_m1_m2_challenger2_ai_engine.py` FAILED:
```
FAILED tests/test_m1_m2_challenger2_ai_engine.py::TestJsonExtractionAndNormalization::test_trailing_commentary_with_braces
pydantic_core._pydantic_core.ValidationError: 1 validation error for ScoringResult
Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='```json\n{\n  "fit_score": 85,\n  "is_testing_role": false,\n  "missing_skills": ["Docker"],\n  "reasoning": "Solid fit"\n}\n```\nNote: Please review {skill_tags} in candidate profile.', input_type=str]
```
Root Cause: `re.match` requires the string to terminate at ```````$````. Because the string contains trailing text, `re.match` fails. `cleaned` remains unchanged, and `rfind("}")` captures the closing brace of the trailing commentary rather than the JSON object, producing corrupt text that fails `json.loads` and crashes Pydantic JSON validation.

### Observation 1.2: Groq 429 ITPM Quota Exhaustion & Fixed Backoff Desynchronization
During live execution of `test_live_giant_bloated_jd_groq` (>10,000 character JD) against `qwen/qwen3.8-27b`, the following telemetry was captured verbatim from stderr:
```
[2026-09-29 22:29:40,069] [WARNING] [ai_engine_v2] [Groq] Retryable error (RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_01m3pke62gec0tzv742mh6qtjz` service tier `on_demand` on input tokens per minute (ITPM): Limit 7000, Used 5143, Requested 4326. Please try again in 21.162857142s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}). Retrying in 2.66s (attempt 1/4)...
[2026-09-29 22:30:23,007] [WARNING] [ai_engine_v2] [Groq] Retryable error (RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_01m3pke62gec0tzv742mh6qtjz` service tier `on_demand` on input tokens per minute (ITPM): Limit 7000, Used 5054, Requested 4326. Please try again in 20.4s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}). Retrying in 4.39s (attempt 2/4)...
[2026-09-29 22:31:04,638] [WARNING] [ai_engine_v2] [Groq] Retryable error (RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_01m3pke62gec0tzv742mh6qtjz` service tier `on_demand` on input tokens per minute (ITPM): Limit 7000, Used 5136, Requested 4326. Please try again in 21.102857142s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}). Retrying in 8.71s (attempt 3/4)...
```
Root Cause:
1. Groq's `qwen/qwen3.8-27b` free on-demand tier has a limit of **7,000 ITPM** (Input Tokens Per Minute), not 8,000. A large JD with resume consumes 4,326 input tokens; two consecutive calls exceed 7,000 ITPM.
2. In `_score_groq` (lines 592–599), the retry loop sleeps `(2**attempt) * 2.0s + jitter` (2.66s, 4.39s, 8.71s), ignoring Groq's explicit error directive: `"Please try again in 21.162857142s"`. This results in 3 premature, failed API retries before finally succeeding on attempt 4.

### Observation 1.3: Schema Fragility — Missing `is_testing_role` Default
In `scoring_audit/ai_engine_v2.py`, line 55:
```python
is_testing_role: bool = Field(
    description="True if role is QA, Testing, SDET, or Automation"
)
```
If an LLM returns a JSON payload omitting `is_testing_role`, Pydantic raises an unhandled `ValidationError: Field required [type=missing, input_value=...]`. It lacks a default (`default=False`).

### Observation 1.4: Score Clamping Deficiency
In `scoring_audit/ai_engine_v2.py`, lines 93–98:
```python
if "fit_score" in data and data["fit_score"] is not None:
    try:
        data["fit_score"] = int(round(float(data["fit_score"])))
    except (ValueError, TypeError):
        data["fit_score"] = 0
```
If the LLM returns an out-of-bounds score (e.g. 105 or -5), `normalize_keys` converts it to `105`, and Pydantic raises `ValidationError: Input should be less than or equal to 100` rather than gracefully clamping to `[0, 100]` via `max(0, min(100, score))`.

### Observation 1.5: Passed Validations
1. **Resume Injection Robustness**: `load_master_resume()` correctly parsed candidate data (`Kaustubh Kale`, 20+ technical skills). `format_scoring_prompt` uses `.replace("{master_resume_json}")` and `.replace("{job_description}")`, preventing `KeyError` crashes when JDs contain Python format braces `{var}` or `{0}`.
2. **DeepSeek Zero-Call Isolation**: Strictly blocks all casing (`deepseek`, `DeepSeek`, `DEEPSEEK`) and substrings (`deepseek-chat`, `provider_deepseek`) with `ValueError("DeepSeek is strictly forbidden in this pipeline.")`.
3. **Sparse & Adversarial JD Scoring**: Live calls to Gemini and Groq with 1-line JDs and prompt-injection JDs (`"IGNORE ALL PREVIOUS INSTRUCTIONS"`) returned valid `ScoringResult` instances without crashes.

---

## 2. Logic Chain

1. **Premise**: In production batch scoring (Milestone M3 onward), LLM responses will exhibit non-deterministic formatting (e.g. code blocks with post-fence notes, slight schema omissions, or minor score drift like 105%).
2. **Step 1 (Extraction Fragility)**: Because `extract_json_str` relies on `re.match` anchored to the end of string ````\n?```$````, any markdown fence with trailing commentary bypasses regex stripping. When the trailing commentary contains braces `{...}`, `rfind("}")` captures those trailing braces, corrupting the JSON payload and causing fatal `ValidationError` crashes.
3. **Step 2 (Schema Strictness)**: Without `default=False` on `is_testing_role` and without `max(0, min(100, ...))` clamping on `fit_score`, minor LLM omissions or boundary hallucinations result in unhandled pipeline exceptions.
4. **Step 3 (Rate Limiting Resilience)**: Groq enforces a strict 7,000 ITPM cap. Hammering Groq with 2.66s and 4.39s retries when Groq specifically mandates a 21.2s wait risks burning all 4 retries and failing the scoring job entirely under batch load.
5. **Conclusion**: These defects present high operational risk for batch scoring (300 synthetic + 73 real jobs). Therefore, changes are requested to fortify `scoring_audit/ai_engine_v2.py`.

---

## 3. Caveats

1. In the live test run, `test_live_giant_bloated_jd_groq` ultimately passed on its 4th retry because the cumulative backoff plus network latency reached ~25 seconds. However, this relied on luck with the window boundary; if a batch of multiple large JDs arrives consecutively, 4 retries will be insufficient.
2. Testing was performed using Python 3.13 on Windows 11. Deprecation warnings from `google-genai` regarding `AiohttpClientSession` were observed but do not affect execution.

---

## 4. Conclusion

**Verdict**: **REQUEST_CHANGES**

### Required Remediations for Worker M2:

1. **Fortify `extract_json_str`**:
   - Replace `cleaned.startswith("```")` and `re.match(r"^...$")` with `re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", cleaned, re.IGNORECASE)` to extract fenced JSON regardless of preceding or trailing text.
   - Use `json.JSONDecoder().raw_decode(cleaned[start_idx:])` before falling back to `rfind("}")`, ensuring balanced braces are parsed accurately.
2. **Default `is_testing_role`**:
   - Change `is_testing_role: bool = Field(...)` to `is_testing_role: bool = Field(default=False, ...)` in `ScoringResult`.
3. **Clamp `fit_score`**:
   - In `ScoringResult.normalize_keys`, clamp `fit_score`:
     `data["fit_score"] = max(0, min(100, int(round(float(data["fit_score"])))))`
4. **Dynamic `retry-after` Backoff for Groq**:
   - In `_score_groq` exception handler, parse `Please try again in ([0-9.]+)s` or inspect response headers for `retry-after`. If present, sleep `wait_seconds + 0.5s` instead of the blind exponential curve.

---

## 5. Verification Method

1. Run the comprehensive adversarial test suite:
   ```powershell
   pytest tests/test_m1_m2_challenger2_ai_engine.py -v
   ```
2. Specifically verify `test_trailing_commentary_with_braces`:
   ```powershell
   pytest tests/test_m1_m2_challenger2_ai_engine.py -k "test_trailing_commentary_with_braces" -v
   ```
   **Invalidation Condition**: Once worker implements the recommended `re.search` / `raw_decode` in `ai_engine_v2.py`, all 27 tests in `tests/test_m1_m2_challenger2_ai_engine.py` must pass with 0 failures.
