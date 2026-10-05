# Task Assignment: Spec Miner Survey APIs & Dependencies

- Working Directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1
- Project Root: c:\Users\kalek\Desktop\Projects\Job_Hunt
- Request: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md (specifically ## Follow-up — 2026-09-29T16:37:31Z)

## Objective
Investigate API credentials, installed Python packages, provider API specifications (Gemini & Groq), rate limit parameters, and model specifications.

## Scope of Investigation
1. Examine environment variables and `.env`:
   - Check if GEMINI_API_KEY (or GOOGLE_API_KEY) and GROQ_API_KEY exist in `.env` or system environment.
   - NOTE: DO NOT print or reveal secret keys in reports. Only report boolean presence/absence and key format/prefix if helpful.
   - Confirm DEEPSEEK_API_KEY status (must be strictly excluded/forbidden from scoring).
2. Examine installed Python packages in the current environment:
   - Check if `google-genai`, `google-generativeai`, `groq`, `pydantic`, `tenacity`, `asyncio`, etc. are installed.
   - Check which versions are installed.
3. Spec Requirements for R2 Dual-Provider Scoring Engine:
   - Gemini: target model `gemini-2.0-flash` (or current free tier), rate limit <= 15 RPM.
   - Groq: target model `llama-3.3-70b-versatile` (or Groq fast models), rate limit <= 30 RPM.
   - Exponential backoff strategy on 429/503.
   - Strict JSON schema extraction (handling markdown fences ```json ... ```, schema validation).
   - Expected JSON schema fields: `fit_score`, `is_testing_role`, `missing_skills`, `reasoning`.

## Output
Produce a detailed Markdown report at:
`c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1\report.md`
Also produce `handoff.md` with your structured summary, observation, logic chain, and conclusion.
Use `send_message` to report completion.

## 2026-09-29T16:40:18Z
Read c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md and c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1\DISPATCH.md.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\spec_miner_survey_api_1.
Investigate .env for GEMINI_API_KEY / GROQ_API_KEY presence (never output secrets), installed Python packages (groq, google-genai, etc.), rate limiting specs, model specifications, JSON schema extraction.
Produce report.md and handoff.md in your working directory and report completion via send_message.

