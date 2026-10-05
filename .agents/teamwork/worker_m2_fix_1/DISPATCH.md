# Task Assignment: Worker M2 Fix - Engine Remediation & Hardening

- Working Directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m2_fix_1
- Project Root: c:\Users\kalek\Desktop\Projects\Job_Hunt
- Request: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md (specifically ## Follow-up — 2026-09-29T16:37:31Z, R2)
- Scope Document: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3\PROJECT.md
- Reviewer 2 Feedback: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_m1_m2_2\handoff.md`
- Challenger 2 Feedback: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\challenger_m1_m2_2\handoff.md`
- Adversarial Test Suite: `tests/test_m1_m2_challenger2_ai_engine.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You exclusively own:
- `scoring_audit/ai_engine_v2.py`
- `scoring_audit/test_engine_v2.py`

## Concrete Remediation Tasks
1. **JSON Extraction Robustness (`extract_json_str`)**:
   - Fix regex and parsing to support markdown fences accompanied by leading/trailing text and braces.
   - Greedily extract the JSON substring and validate parsing without crashing on commentary containing `{...}`.
2. **Groq 429 Retry-After Handling & Pacing**:
   - When encountering HTTP 429 on Groq or Gemini, parse the `retry-after` header or extract `Please try again in X.Xs` from the error message.
   - Sleep for the exact required duration + 1.0s buffer rather than burning premature static retries.
   - Set Groq rate limiter default minimum interval to 4.0s (<= 15 RPM) to protect the 7k-8k TPM ceiling.
3. **Schema Resilience**:
   - In `ScoringResult`:
     - Default `is_testing_role: bool = False`.
     - Clamp `fit_score` to `[0, 100]` in a validator so scores like 105 or -5 are safely clamped to 100 or 0 instead of raising `ValidationError`.
     - Add explicit optional metadata fields:
       `provider: Optional[str] = None`
       `model: Optional[str] = None`
       `latency_seconds: Optional[float] = None`
       `tokens_used: Optional[dict] = None`
       so that `.model_dump()` captures complete audit telemetry.
4. **DeepSeek Model Guard**:
   - In `_validate_provider`, ensure that if `model` is provided, `model.lower()` does not contain `"deepseek"` (blocks Groq DeepSeek distill models like `deepseek-r1-distill-llama-70b`).
5. **Transient Formatting Retry**:
   - Treat `JSONDecodeError` and `ValidationError` as retryable (up to 2 retry attempts) with a short delay before aborting.
6. **Verification Requirements**:
   - Run `pytest tests/test_m1_m2_challenger2_ai_engine.py -v` -> verify all 27 tests PASS.
   - Run `pytest scoring_audit/test_engine_v2.py -v` -> verify all 7 tests PASS.
   - Document all changes and test outputs in `handoff.md` and report completion via `send_message`.

## 2026-09-29T17:04:11Z
Read c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md and c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m2_fix_1\DISPATCH.md.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m2_fix_1.
Apply all 5 concrete remediations to scoring_audit/ai_engine_v2.py (JSON extraction robustness, Groq 429 retry-after wait, schema resilience with score clamping & metadata fields, DeepSeek model guard, and transient parse retry).
Run pytest tests/test_m1_m2_challenger2_ai_engine.py -v and pytest scoring_audit/test_engine_v2.py -v to verify 100% pass, write handoff.md, and send_message to parent upon completion.
