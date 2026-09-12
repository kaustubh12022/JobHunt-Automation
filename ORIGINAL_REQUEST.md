# Original User Request

## Initial Request — 2026-09-06T07:26:08Z

# Teamwork Project Prompt — Draft

> Status: Step 9 — Ready for launch — awaiting user approval.
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team

Completely audit, overhaul, and test the JobHunt-Automation pipeline to ensure high-quality job filtering, accurate AI scoring, and generation of highly tailored, 1-page ATS-friendly resumes at minimal AI cost.

Working directory: c:\Users\kalek\Desktop\Job_Hunt
Integrity mode: development

## Requirements

### R1. Pipeline Reliability & UI
- Ensure the pipeline completes without manual intervention.
- Add a **small-batch testing mode** for fast iteration without running the full 1-hour scraping cycle.
- Fix any broken flows, errors, or inconsistencies in the UI. All critical UI controls must be functional.

### R2. Scraping & Filtering Quality
- **Scraping**: Ensure no duplicates, correct platform attribution, and preserved JDs/URLs across a test set of 200+ jobs.
- **Filtering**: Optimize Pandas/Regex filters for recall first (do not drop relevant jobs), then precision (reject senior/irrelevant jobs).

### R3. AI Scoring
- Verify the scoring logic correctly distinguishes job relevance (Highly relevant to Irrelevant/Senior).
- Ensure the model selected in the UI is actually the one called by the API.

### R4. Resume Tailoring & ATS Compatibility
- Generate extremely well-matched, visually aesthetic, single-page resumes.
- Use a **best-fit role lens** (e.g., analyze general experience through the specific job's lens). Place relevant skills naturally; do not blindly keyword stuff.
- 0 fabricated qualifications (no hallucinations).
- Resumes must be 100% machine-readable (ATS-friendly) and exactly 1 page.

### R5. Token & Cost Efficiency
- Track every AI call (model, input/output/cached tokens, cost, stage).
- Eliminate all unnecessary AI calls.
- Use the cheapest model capable of achieving the quality required. Target a 30% AI cost reduction per successful resume vs the baseline.

### R6. Summary Artifact
- Create a beginner-friendly summary/walkthrough file explaining all changes, test results, cost improvements, UI updates, and subagents used.

## Acceptance Criteria

### Measurable Success Criteria
- [ ] **Pipeline reliability**: ≥ 95%
- [ ] **Scraping data integrity**: ≥ 98%
- [ ] **Relevant-job recall**: ≥ 98%
- [ ] **Senior/irrelevant rejection**: ≥ 90–95%
- [ ] **AI scoring agreement**: ≥ 90% (vs manual evaluation)
- [ ] **JD requirement coverage**: ≥ 95%
- [ ] **Resume hallucinations**: 0
- [ ] **Machine-readable resumes**: 100%
- [ ] **One-page resumes**: 100%
- [ ] **Visual QA pass**: 100%
- [ ] **Critical UI controls**: 100% functional
- [ ] **Unnecessary AI calls**: 0
- [ ] **AI cost reduction**: ≥ 30% vs baseline
- [ ] **End-to-end successful runs**: ≥ 95%

## 2026-09-06T08:17:16Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Multi-agent execution of JobHunt-Automation overhaul and verification
> Requested team: Full team

Audit, debug, overhaul, and verify the end-to-end JobHunt-Automation system for a single user (Indian fresher candidate) to achieve reliable 1-click job hunting: scraping, recall-first regex/pandas filtering, DeepSeek scoring, role-lens resume tailoring, 1-page ATS PDF generation, and Supabase integration at minimal token cost.

Working directory: c:\Users\kalek\Desktop\Job_Hunt
Integrity mode: development

## Credentials & Configuration Context
- **DeepSeek API Key**: `YOUR_DEEPSEEK_API_KEY`
  - Scoring Model: `deepseek-chat`
  - Resume Tailoring Model: `deepseek-reasoner`
- **Supabase Project**:
  - Project ID: `hysfjbecwcljddszcjui`
  - Project URL: `https://hysfjbecwcljddszcjui.supabase.co`
  - Publishable Key: `sb_publishable_UwSom1GLyDkoTDha4ykc-w__AO0LPaI`
- **Target Candidate Profile**: Fresher / Entry-level candidate in India (locations: Pune, Mumbai, Bangalore; terms: QA Automation, Java Developer, .NET Developer, Software Engineer, Backend Developer, Full Stack Developer).

---

## Requirements

### R1. Pipeline Reliability, Test Mode & Bug Fixes
- Fix all run-blocking bugs across the codebase:
  - Update invalid DeepSeek model names (e.g., replace deprecated/invalid names with `deepseek-chat` for scoring and `deepseek-reasoner` for tailoring).
  - Fix Windows dependency and runtime issues (e.g., numpy compilation/ABI issues, path issues, `.bat` script paths).
  - Broaden job freshness filter from 24 hours to 72 hours so valid opportunities aren't dropped.
  - Adjust default AI score threshold from 70 to 60 to prevent over-filtering.
  - Replace or fix non-functional scraper platforms in India (e.g., replace ZipRecruiter with Glassdoor if supported in JobSpy, or handle gracefully).
- Implement a dedicated **small-batch testing mode**:
  - Allows rapid end-to-end iteration (< 2 minutes) with a small, representative sample of jobs without running the full 1-hour scraping cycle.
- Ensure the pipeline can be safely rerun, handles failures with clear error messages, and achieves ≥ 95% run completion rate.

### R2. Scraping & Pre-AI Filtering Quality
- **Scraping Integrity**:
  - Audit and fix scraping pipeline across all enabled sources (LinkedIn, Indeed, Glassdoor/others).
  - Eliminate duplicate job entries, preserve complete job descriptions, and preserve valid apply URLs.
- **Recall-First Regex / Pandas Filtering**:
  - Prioritize **recall (≥ 98%)** so genuine fresher/entry-level jobs are never dropped.
  - Accurately filter out senior/lead/staff/manager positions and out-of-scope roles with target rejection of 90–95%.
  - Audit false positives and false negatives against a representative dataset of 200+ jobs.

### R3. AI Scoring Accuracy & Token Efficiency
- Verify that AI Scoring accurately distinguishes job relevance (highly relevant vs. borderline vs. irrelevant vs. senior).
- Ensure the model requested in configuration/UI matches the API call executed.
- Enforce strict token and cost optimization:
  - Cache prompt prefixes where applicable.
  - Do not send redundant JD text or unnecessary tokens.
  - Eliminate AI calls on jobs that should have been eliminated during pre-AI filtering.
  - Log model, input tokens, cached tokens, output tokens, cost, and pipeline stage for every call.

### R4. Role-Lens Resume Tailoring & Zero Hallucinations
- Implement a **best-fit role lens** tailoring mechanism:
  - Tailor the candidate's existing background (e.g., Full Stack / MEAN) to highlight genuinely applicable skills and projects for the specific target role (e.g., Data Science, QA Automation, Backend).
  - Place relevant skills naturally within project and experience bullet points rather than superficial keyword stuffing.
  - Keep strong, relevant projects and experience rather than arbitrarily stripping them down.
- **Strict Anti-Hallucination Guardrail**:
  - Exactly 0 fabricated skills, certifications, degrees, or experiences. Every claim must stem from the master profile.
  - ≥ 95% of genuinely applicable JD requirements present in master profile must be reflected in the final resume.

### R5. 1-Page ATS-Friendly Resume PDF Generation
- Redesign the resume template to a modern, clean sans-serif layout with subtle blue accent styling.
- Ensure 100% ATS machine-readability (extractable, parseable text, standard headings, correct reading order, no embedded text images).
- Enforce a strict **single-page constraint** without CSS `transform: scale()` or hacky shrinking that degrades ATS parsing or visual hierarchy.
- Ensure 100% visual QA pass: clean margins, no overflowing text, no awkward page breaks or clipped sections.

### R6. Supabase Integration & UI Audit
- Configure and test Supabase connection using the provided project credentials. Store processed jobs, tailored resumes, and metadata.
- Audit the web UI (Streamlit / Flask / HTML):
  - Ensure every button, input, toggle, and trigger operates without unhandled exceptions.
  - Provide clear loading states, progress feedback, and error reporting.

### R7. Comprehensive Verification & Beginner-Friendly Final Summary
- Build automated test/verification scripts:
  - Verify regex recall/precision on 200+ job dataset.
  - Verify ATS readability and single-page constraint on generated PDFs.
  - Verify token usage and cost reduction (target ≥ 30% savings vs baseline).
  - Verify zero-hallucination compliance.
- Produce a clear, beginner-friendly summary and walkthrough document detailing:
  - What was originally broken.
  - What changes were made and why.
  - Verification results and metrics achieved.
  - Step-by-step instructions on running both test mode and the full 1-click production pipeline.
  - Roles and discoveries of subagents involved.

---

## Acceptance Criteria

### Pipeline & Filtering
- [ ] Pipeline runs end-to-end with 1 click without manual intervention (≥ 95% reliability across repeated runs).
- [ ] Small-batch test mode executes end-to-end in < 2 minutes.
- [ ] Scraping data integrity ≥ 98% (no duplicates, preserved JDs, valid URLs).
- [ ] Pre-AI regex/pandas filter achieves ≥ 98% recall for relevant fresher jobs and 90–95% rejection of senior/out-of-scope roles.

### AI Scoring & Tailoring
- [ ] AI scoring reflects true relevance with ≥ 90% manual evaluation agreement.
- [ ] 0 fabricated qualifications or experiences in generated resumes (100% truthful).
- [ ] ≥ 95% coverage of genuinely applicable JD requirements using the best-fit role lens.
- [ ] DeepSeek model parameters, endpoints, and token counts are correctly configured (`deepseek-chat` for scoring, `deepseek-reasoner` for tailoring).
- [ ] ≥ 30% reduction in AI cost per successful resume compared to unoptimized baseline, with 0 unnecessary AI calls.

### Resume PDF & ATS
- [ ] 100% of generated resumes extract clean, structured plain text with standard section headers.
- [ ] 100% of generated resumes fit exactly on 1 page without CSS scale hacks or visual overflow.
- [ ] 100% pass on visual design audit (modern typography, blue accents, clean whitespace).

### Storage & UI
- [ ] Supabase database connection and schema successfully store jobs and tailored resumes.
- [ ] 100% of critical UI buttons and controls functional with appropriate status feedback.
- [ ] Beginner-friendly final walkthrough artifact completed with detailed before/after explanations.

## Follow-up — 2026-09-06T14:07:06Z

just 1 thing for testing try to use original data like for real world testing and try to use less api calls for testing

## Follow-up — 2026-09-06T14:09:14Z

USER CLARIFICATION: The user specifically means to minimize **DeepSeek API calls** (the job scoring and reasoner tailoring calls) during the test suites to save money/cost. Ensure that your automated tests use real-world data but minimize hitting the live DeepSeek API, e.g., by testing the core logic locally or aggressively caching the test responses.
## Follow-up — 2026-09-06T15:01:24Z

USER COMMAND: Skip Milestone 7 entirely. Do not run the final E2E test or Victory Audit. Immediately generate the final summary documentation artifact (detailing all agents used, their tasks, and the exact code changes made). Once the document is generated, gracefully terminate your execution. The user wants to manually run the pipeline.
