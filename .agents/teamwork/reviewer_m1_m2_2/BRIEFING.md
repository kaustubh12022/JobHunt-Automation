# BRIEFING — 2026-09-29T17:05:00Z

## Mission
Review scoring_audit/ai_engine_v2.py architecture, rate limiting (Gemini <=15 RPM, Groq <=20 RPM / 8k TPM), exponential backoff, prompt injection, and DeepSeek guard with adversarial stress-testing.

## 🔒 My Identity
- Archetype: reviewer_critic
- Roles: reviewer, critic
- Working directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_m1_m2_2
- Original parent: 7cb7199f-c2a4-46e3-be86-1c86a84aa546
- Milestone: M2 (Dual-Provider Scoring Engine)
- Instance: 2 of 2

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Strictly zero calls made to DeepSeek API; enforce DeepSeek guard
- Verify client-side rate limiters (Gemini <=15 RPM, Groq <=20 RPM to respect 8k TPM)
- Verify concurrency safety, exponential backoff with jitter on 429/503
- Check for prompt injection vulnerabilities and schema extraction resilience
- Actively check for integrity violations (hardcoding, facades, shortcuts, fake logs)

## Current Parent
- Conversation ID: 7cb7199f-c2a4-46e3-be86-1c86a84aa546
- Updated: 2026-09-29T17:05:00Z

## Review Scope
- **Files to review**: `scoring_audit/ai_engine_v2.py`, `scoring_audit/test_engine_v2.py`, `src/prompts/scoring_prompt.txt`, `data_folder/plain_text_resume.yaml`
- **Interface contracts**: `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3\PROJECT.md`
- **Review criteria**: correctness, thread/async concurrency safety, rate limit compliance, exponential backoff, resilience, security/prompt injection, integrity violations

## Key Decisions Made
- Executed `test_engine_v2.py` (7/7 unit & live API tests passed).
- Executed adversarial prompt injection test with system override commands; verified models did not succumb.
- Discovered Groq 7,000 ITPM limit 429 error during empirical test and identified that backoff ignores `Please try again in 20.2s` server header.
- Discovered DeepSeek model name bypass on Groq (`groq_model="deepseek-r1-distill-llama-70b"`).
- Discovered `ScoringResult.model_dump()` strips metadata (`provider`, `model`, `latency_seconds`).
- Discovered `_is_retryable_error` excludes `ValidationError` and `JSONDecodeError`.
- Determined verdict: `REQUEST_CHANGES` to fix major resilience and guard gaps prior to Milestone 3 batch execution.

## Artifact Index
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_m1_m2_2\BRIEFING.md` — Situational awareness
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_m1_m2_2\progress.md` — Liveness & progress tracking
- `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\reviewer_m1_m2_2\handoff.md` — Complete 5-component handoff report

## Review Checklist
- **Items reviewed**: `scoring_audit/ai_engine_v2.py`, `scoring_audit/test_engine_v2.py`, live API endpoints (Gemini, Groq)
- **Verdict**: REQUEST_CHANGES
- **Unverified claims**: All claims independently verified with live code and stress tests

## Attack Surface
- **Hypotheses tested**:
  1. Integrity violation check: Negative (implementation is genuine, live calls work).
  2. Prompt injection bypass: Tested with executive system override; passed (models scored 0 on mismatch).
  3. Groq 8k TPM limit under continuous calls: FAILED (empirical 429 caught; 7,000 ITPM exceeded, backoff interval 2.5s < 20.2s required wait).
  4. DeepSeek guard model parameter bypass: FAILED (provider guard only checks `provider`, allows `deepseek-*` model string on Groq).
  5. Telemetry serialization: FAILED (`model_dump()` strips dynamic attributes `provider`, `latency_seconds`).
  6. Transient parse error resilience: FAILED (`_is_retryable_error` rejects `ValidationError`/`JSONDecodeError`).
- **Vulnerabilities found**: 4 Major findings, 2 Minor findings documented in `handoff.md`.
- **Untested angles**: Extreme token inputs (>100k tokens), long duration connection dropouts.
