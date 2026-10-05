# Task Assignment: Explorer Survey AI & Prompts

- Working Directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1
- Project Root: c:\Users\kalek\Desktop\Projects\Job_Hunt
- Request: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md (specifically ## Follow-up — 2026-09-29T16:37:31Z)

## Objective
Investigate the existing AI scoring engine, prompt architecture, candidate profile/resume, and project configuration.

## Scope of Investigation
1. Examine `src/ai_engine.py` (or related scoring files in `src/`):
   - What is the current scoring pipeline, model selection, prompt loading, response parsing, and error handling?
   - How are DeepSeek / other providers currently referenced or implemented?
2. Examine `src/prompts/scoring_prompt.txt` (and any other prompts in `src/prompts/`):
   - How are score, missing_skills, is_testing_role, and candidate skills instructed?
   - What are the scoring criteria, weights, and rubric?
   - Look for reasons why MERN stack and AI/ML/LLM roles may be under-scored or experience score compression.
3. Examine candidate profile / resume data:
   - Check `config/profile.json`, `config.yaml`, and any resume text/markdown files.
   - Identify candidate skills (languages, frameworks, tools, education, experience, target domains).
4. Identify existing test files for ai_engine (e.g. `tests/test_ai_engine.py` or similar).

## Output
Produce a detailed Markdown report at:
`c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1\report.md`
Also produce `handoff.md` with your structured summary, observation, logic chain, and conclusion.
Use `send_message` to report completion.

## 2026-09-29T16:40:18Z
Read c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md and c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1\DISPATCH.md.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_ai_1.
Examine src/ai_engine.py, src/prompts/scoring_prompt.txt, config/profile.json, config.yaml, resume data, and existing tests.
Produce report.md and handoff.md in your working directory and report completion via send_message.
