# AutoApply — Master Project Documentation

> **Single Source of Truth** · Last Updated: July 8, 2026 (Revised)  
> This document is the definitive reference for understanding, maintaining, and extending the AutoApply project.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Overall Architecture](#2-overall-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Complete Pipeline Workflow](#4-complete-pipeline-workflow)
5. [Component Deep Dives](#5-component-deep-dives)
   - 5.1 [Scraper Component](#51-scraper-component)
   - 5.2 [Pandas Filtering Component](#52-pandas-filtering-component)
   - 5.3 [Regex Filtering Component](#53-regex-filtering-component)
   - 5.4 [AI Scoring Component](#54-ai-scoring-component)
   - 5.5 [AI Reasoning & Resume Tailoring Component](#55-ai-reasoning--resume-tailoring-component)
   - 5.6 [Resume Generation (HTML Rendering) Component](#56-resume-generation-html-rendering-component)
   - 5.7 [PDF Generation Component](#57-pdf-generation-component)
   - 5.8 [Database Component](#58-database-component)
   - 5.9 [Sheet Generator Component](#59-sheet-generator-component)
   - 5.10 [Email Sender Component](#510-email-sender-component)
   - 5.11 [Dashboard Component (Frontend)](#511-dashboard-component-frontend)
   - 5.12 [Application Tracker Component](#512-application-tracker-component)
   - 5.13 [Test Engine Component](#513-test-engine-component)
6. [Pipeline Orchestration](#6-pipeline-orchestration)
7. [Data Flow Between Components](#7-data-flow-between-components)
8. [Database Schema](#8-database-schema)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Configuration System](#10-configuration-system)
11. [External APIs and Services](#11-external-apis-and-services)
12. [Folder Structure](#12-folder-structure)
13. [Error Handling Strategy](#13-error-handling-strategy)
14. [Logging Architecture](#14-logging-architecture)
15. [Testing Strategy](#15-testing-strategy)
16. [Execution Modes](#16-execution-modes)
17. [Legacy / Inherited Code](#17-legacy--inherited-code)
18. [Current Limitations](#18-current-limitations)
19. [Inconsistencies Found](#19-inconsistencies-found)
20. [Future Roadmap](#20-future-roadmap)
21. [Suggestions and Recommendations](#21-suggestions-and-recommendations)

---

## 1. Project Overview

**AutoApply** is an AI-powered job application automation pipeline designed for an entry-level/fresher candidate (currently configured for Kaustubh Kale). The system automates the complete job hunting workflow:

1. **Scrapes** hundreds of job postings from LinkedIn and Indeed daily
2. **Filters** irrelevant jobs using zero-cost Pandas and Regex rules
3. **Scores** remaining jobs against the candidate's resume using AI (DeepSeek LLM)
4. **Tailors** custom resumes for the top-scoring jobs using AI deep reasoning
5. **Generates** ATS-compliant PDF resumes from tailored data
6. **Persists** results to a Supabase PostgreSQL database
7. **Outputs** a formatted Excel tracker sheet
8. **Emails** daily ZIP packages of resumes and the tracker
9. **Displays** a real-time React dashboard showing pipeline progress
10. **Tracks** applications through a Kanban-style board
11. **Simulates** pipeline stages via a Modular Test Lab to save AI tokens

The project has **two execution interfaces**:
- **Headless CLI** (`run.py`) — designed for Windows Task Scheduler automation
- **Web Dashboard** (`app.py`) — Flask backend serving a React SPA for interactive control

### Key Design Principles
- **Token Optimization**: Multi-layer filtering eliminates jobs *before* they reach the expensive AI API, reducing token costs by ~80%
- **Concurrent Processing**: All AI calls (scoring + tailoring) use `asyncio.gather()` for massive parallelism
- **Prompt Caching**: The master resume is pinned as the system prompt to trigger DeepSeek's discounted prompt caching rate ($0.0028/1M tokens)
- **Delta Output**: AI returns only modified resume sections, not the full document, saving output tokens
- **Single-Page Resume**: All generated resumes are constrained to exactly one A4 page via CSS + JS scaling

---

## 2. Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                              │
│  ┌──────────────┐    ┌─────────────────────────────────────────┐   │
│  │  CLI (run.py) │    │  Web Dashboard (app.py + React SPA)    │   │
│  │  Task         │    │  ┌───────────┐  ┌──────────────────┐   │   │
│  │  Scheduler    │    │  │ Dashboard  │  │ Application      │   │   │
│  │  / Manual     │    │  │ (Pipeline) │  │ Tracker (Kanban) │   │   │
│  └──────┬───────┘    │  └─────┬─────┘  └───────┬──────────┘   │   │
│         │            │        │                  │              │   │
│         │            └────────┼──────────────────┼──────────────┘   │
└─────────┼─────────────────────┼──────────────────┼──────────────────┘
          │                     │                  │
          ▼                     ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND PIPELINE                               │
│                                                                     │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │
│  │ Scraper │→ │ Pandas   │→ │ AI      │→ │ Resume  │→ │ PDF    │ │
│  │ (JobSpy)│  │ Filter   │  │ Scorer  │  │ Tailor  │  │ Gen    │ │
│  └─────────┘  └──────────┘  └────┬────┘  └────┬────┘  └───┬────┘ │
│                                   │            │            │      │
│                              ┌────┴────────────┴────────────┴───┐  │
│                              │         DeepSeek LLM API         │  │
│                              │      (OpenAI-compatible SDK)     │  │
│                              └──────────────────────────────────┘  │
│                                                                     │
│  ┌──────────┐  ┌─────────────┐  ┌────────────┐                    │
│  │ Supabase │  │ Excel Sheet │  │ Email      │                    │
│  │ Database │  │ Generator   │  │ (SMTP/ZIP) │                    │
│  └──────────┘  └─────────────┘  └────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Architecture Pattern
- **Monolithic Python backend** with modular source files
- **Flask** serves the built React SPA from `frontend/dist/`
- **Server-Sent Events (SSE)** for real-time pipeline status to the dashboard
- **Supabase** (hosted PostgreSQL) for persistent data storage
- **Direct Supabase JS client** in the frontend for Tracker reads/writes (bypasses Flask)

---

## 3. Technology Stack

### Backend (Python)
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.x | Core runtime |
| Flask | ≥3.0.0 | Web server, API endpoints, static file serving |
| python-jobspy | ≥1.1.48 | Multi-platform job scraping (LinkedIn, Indeed) |
| OpenAI SDK | ≥1.30.0 | AI API client (pointed at DeepSeek endpoint) |
| Pandas | ≥2.2.0 | DataFrame-based job filtering and transformation |
| Playwright | ≥1.44.0 | Headless Chromium for HTML→PDF rendering |
| Jinja2 | ≥3.1.3 | HTML resume template engine |
| openpyxl | ≥3.1.2 | Excel file generation and styling |
| PyYAML | ≥6.0.1 | YAML config and resume parsing |
| Loguru | ≥0.7.2 | Structured logging with queue-based dashboard streaming |
| Supabase Python | latest | PostgreSQL database client |
| python-dotenv | latest | Environment variable loading |
| BeautifulSoup4 | ≥4.12.0 | HTML parsing (imported but minimally used in active pipeline) |

### Frontend (React)
| Technology | Version | Purpose |
|---|---|---|
| React | 19.2.7 | UI component framework |
| Vite | 8.1.0 | Build tool and dev server |
| React Router DOM | 7.18.0 | Client-side routing |
| Framer Motion | 12.42.0 | Animations and transitions |
| Lucide React | 1.22.0 | Icon library |
| Supabase JS | 2.108.2 | Direct database client for Tracker |
| React CountUp | 6.5.3 | Animated number counters |

### External Services
| Service | Purpose |
|---|---|
| DeepSeek API | LLM for job scoring and resume tailoring |
| Supabase | Hosted PostgreSQL database + REST API |
| Gmail SMTP | Daily email delivery of results |
| LinkedIn / Indeed | Job posting data sources (via JobSpy) |

### DevOps
| Tool | Purpose |
|---|---|
| GitHub Actions | CI pipeline (install + pytest) |
| Windows Task Scheduler | Automated daily pipeline execution |
| `run_autoapply.bat` | Batch script: runs pipeline then suspends PC |

---

## 4. Complete Pipeline Workflow

### Step-by-Step Execution Flow

```
START
  │
  ├─ [1] SCRAPING (scraper.py)
  │    ├─ Load config.yaml (search terms, locations, job types, platforms)
  │    ├─ Build combinatorial matrix: terms × locations × job_types
  │    ├─ For each combination:
  │    │    ├─ Call JobSpy API (linkedin + indeed)
  │    │    ├─ Collect raw DataFrames
  │    │    ├─ Anti-ban delay: random 5-12 seconds
  │    │    └─ Fire on_cycle_start / on_job_scraped callbacks
  │    ├─ Merge all DataFrames
  │    │
  │    ├─ [PANDAS PRE-FILTER] (Zero-Token Cost)
  │    │    ├─ Drop null/empty descriptions
  │    │    ├─ Drop stale jobs (>72h old)
  │    │    ├─ Drop location mismatches (not in target cities, not remote)
  │    │    ├─ Drop senior-level titles (regex: senior, lead, director, etc.)
  │    │    ├─ Drop 3+ years experience requirements (regex in descriptions)
  │    │    └─ Deduplicate by job_url + (title, company)
  │    │
  │    ├─ Convert DataFrame rows → Job dataclass objects
  │    ├─ Clean HTML from descriptions
  │    └─ Return (List[Job], scrape_stats)
  │
  ├─ [2] AI SCORING (scorer.py)
  │    ├─ Zero-Token Keyword Relevance Filter
  │    │    └─ Drop JDs with <2 matches against CORE_STACK_KEYWORDS
  │    ├─ Supabase JD Cache Check
  │    │    └─ If JD URL was already scored previously, pull score from cache to save tokens
  │    ├─ For each relevant job (CONCURRENT via asyncio.gather):
  │    │    ├─ Strip boilerplate sections (About Us, Benefits, EEO)
  │    │    ├─ Build user prompt with job title, company, location, stripped JD
  │    │    ├─ Call DeepSeek API (thinking: DISABLED, fast mode)
  │    │    │    System prompt = master resume (pinned for caching)
  │    │    ├─ Parse JSON response → {match_score, missing_skills, extracted_requirements, is_testing_role}
  │    │    ├─ Attach score + metadata to Job object
  │    │    └─ Fire on_score_start / on_score_complete callbacks
  │    ├─ Sort jobs by score descending
  │    ├─ Filter: keep only jobs with score ≥ 50%
  │    └─ Return List[Job] (scored, sorted)
  │
  ├─ [3] SHORTLISTING
  │    └─ Take top_n jobs (default 20) from scored list
  │
  ├─ [4] RESUME TAILORING (resume_tailor.py)
  │    ├─ For each shortlisted job (CONCURRENT via asyncio.gather):
  │    │    ├─ Load master resume YAML
  │    │    ├─ Build user prompt with job title + compressed requirements
  │    │    │   (uses extracted_requirements from Phase 2, NOT the full JD)
  │    │    ├─ Call DeepSeek API (thinking: ENABLED, deep reasoning)
  │    │    │    System prompt = master resume + "Reframing Lens" rules
  │    │    ├─ Parse Delta JSON response
  │    │    ├─ Merge delta into master resume copy (deepcopy + overlay)
  │    │    └─ Return tailored_resume dict
  │    └─ Return List[dict] (tailored resume JSONs)
  │
  ├─ [5] PDF GENERATION (pdf_generator.py)
  │    ├─ Launch Playwright headless Chromium (single browser, reused page)
  │    ├─ For each (job, tailored_resume):
  │    │    ├─ Render Jinja2 template with resume + job data
  │    │    │    Dynamic section reordering: Experience↔Projects based on is_testing_role
  │    │    ├─ Inject JavaScript to auto-scale content to fit 1 A4 page
  │    │    ├─ Call page.pdf() to generate PDF
  │    │    └─ Save as: {Company}_{CandidateName}_Resume.pdf
  │    └─ Return List[str] (PDF file paths)
  │
  ├─ [6] PERSISTENCE
  │    ├─ Save to Supabase (db.py → save_pipeline_results)
  │    │    ├─ Insert pipeline_runs record (stats)
  │    │    ├─ Insert tracked_jobs records (one per shortlisted job)
  │    │    └─ Insert applications records (status: "generated")
  │    └─ Generate Excel sheet (sheet_generator.py)
  │         ├─ Build DataFrame with Rank, Score, Company, Title, etc.
  │         ├─ Style with openpyxl (headers, conditional fills, hyperlinks)
  │         └─ Save as: AutoApply_Jobs_{date}.xlsx
  │
  ├─ [7] EMAIL DELIVERY (CLI mode only)
  │    ├─ ZIP the output folder (PDFs + Excel)
  │    ├─ Compose HTML email with stats table + shortlisted jobs
  │    ├─ Attach ZIP file
  │    └─ Send via Gmail SMTP (port 587, STARTTLS)
  │
  └─ DONE
```

### Data Handoff Between Phases

| From | To | Data Passed |
|---|---|---|
| Scraper | Scorer | `List[Job]` with full cleaned descriptions |
| Scorer | Shortlister | `List[Job]` with `.score`, `.missing_skills`, `.extracted_requirements`, `.is_testing_role` |
| Shortlister | Tailor | Top N `List[Job]` objects |
| Tailor | PDF Generator | `List[dict]` (tailored resume JSONs, parallel with job list) |
| PDF Generator | DB/Sheet/Email | `List[str]` (PDF file paths) |

---

## 5. Component Deep Dives

### 5.1 Scraper Component

| Attribute | Detail |
|---|---|
| **Purpose** | Aggregates job postings from multiple platforms using a combinatorial search matrix |
| **File** | `src/scraper.py` (277 lines) |
| **Dependencies** | `python-jobspy`, `pandas`, `re`, `src.models.Job`, `src.config_loader` |
| **Inputs** | `config.yaml` (search terms, locations, job types, platforms), `selected_platforms` param, `test_mode` flag |
| **Outputs** | `(List[Job], dict)` — cleaned job objects + scraping statistics |

**Internal Workflow:**
1. Loads configuration from `config.yaml`
2. Constructs a combinatorial matrix: `search_terms × locations × job_types`
   - Production: All combos (e.g., 8 terms × 3 cities × 2 types = 48 combos)
   - Test mode: First 5 combos only, 20 results each
3. For each combo, calls `jobspy.scrape_jobs()` with appropriate parameters
4. Applies anti-ban delays (`random.uniform(5.0, 12.0)` seconds) between combos
5. Skips LinkedIn for internship job types (LinkedIn doesn't support this filter well)
6. Merges all result DataFrames and applies the Pandas Pre-Filter Layer
7. Converts filtered DataFrame rows to `Job` dataclass instances
8. Returns jobs + statistics dict

**Key Design Decisions:**
- Full job descriptions are preserved (never truncated) — this is critical for downstream AI accuracy
- HTML tags are stripped from descriptions via `clean_html()`
- LinkedIn descriptions are explicitly fetched (`linkedin_fetch_description=True`)

---

### 5.2 Pandas Filtering Component

| Attribute | Detail |
|---|---|
| **Purpose** | Eliminates obviously irrelevant jobs at zero token cost before AI processing |
| **Location** | Embedded within `src/scraper.py` (lines 146–246) |
| **Technologies** | `pandas`, `re` |
| **Inputs** | Raw merged DataFrame from all scraping combos |
| **Outputs** | Filtered DataFrame |

**Five-Layer Filter Stack:**

1. **Null/Empty Description Drop** — Removes rows with missing or blank job descriptions
2. **Recency Filter** — Drops jobs older than the configured `hours_old` threshold (default: 72h). Handles timezone-aware comparison.
3. **Location Filter** — Keeps only jobs matching target cities (Pune, Mumbai, Bangalore) OR flagged as remote
4. **Anti-Senior Title Filter** — Regex drops titles containing: `senior, sr., lead, manager, principal, director, head, vp, president, experienced, architect, staff, expert`
5. **Experience Level Filter** — Regex scans job descriptions for experience requirements of 3+ years (both digit-based like "3+ years" and word-based like "three years")
6. **Deduplication** — First by `job_url`, then by `(title, company)` composite key

**Callbacks:** For each dropped job, fires `on_job_dropped(title, company, reason)` to update the dashboard's filter view in real time.

---

### 5.3 Regex Filtering Component

| Attribute | Detail |
|---|---|
| **Purpose** | Provides zero-cost text pattern matching for both pre-filter (titles/descriptions) and boilerplate stripping |
| **Location** | `src/scraper.py` (title regex, experience regex), `src/scorer.py` (boilerplate stripping, keyword matching) |
| **Technology** | Python `re` module |

**Regex Patterns Used:**

| Pattern | Location | Purpose |
|---|---|---|
| `senior\|sr[\.\s]\|lead\|manager\|principal\|...` | `scraper.py:189` | Drop senior-level job titles |
| `\b(\d+)\s*(?:\+\|to\|-\|and)?...(?:years?\|yrs?)` | `scraper.py:207` | Detect 3+ years experience requirements |
| `(?i)(?:about\s+(?:us\|the\s+company))...` | `scorer.py:20-26` | Strip HR boilerplate sections from JDs |

---

### 5.4 AI Scoring Component

| Attribute | Detail |
|---|---|
| **Purpose** | Evaluates job-candidate fit using AI, producing a 0-100 match score and metadata |
| **Files** | `src/scorer.py` (155 lines), `src/ai_engine.py` (lines 53-114) |
| **Dependencies** | `openai` (AsyncOpenAI), `asyncio`, `json`, `re` |
| **Inputs** | `List[Job]` with full cleaned descriptions |
| **Outputs** | `List[Job]` enriched with `.score`, `.missing_skills`, `.extracted_requirements`, `.is_testing_role` |

**Internal Workflow:**
1. **Zero-Token Keyword Filter**: Each JD must contain ≥2 of `CORE_STACK_KEYWORDS` (Java, Python, SQL, Selenium, etc.) to proceed. Completely irrelevant JDs are silently dropped.
2. **JD Caching System**: Checks Supabase `jd_cache` table by URL. If the job was scored in a previous run, the cached score, missing skills, and extracted requirements are loaded instantly (zero token cost).
3. **Boilerplate Stripping**: Regex removes "About Us", "Benefits", "EEO" and similar sections from descriptions to reduce token count.
4. **Concurrent API Calls**: Uncached, relevant jobs are scored concurrently using `asyncio.gather()`.
4. **AI Call**: `call_ai_scoring_async()` sends the stripped JD to DeepSeek with:
   - **Thinking mode: DISABLED** (fast, cheap)
   - **System prompt**: Full master resume JSON (pinned for prompt caching)
   - **Temperature**: 0.3
   - **Retry logic**: 3 attempts with exponential backoff
5. **Response Parsing**: Extracts raw JSON from AI response (`{match_score, missing_skills, extracted_requirements, is_testing_role}`)
6. **Score Assignment**: Attaches all parsed fields to the `Job` object
7. **Threshold Filter**: In production mode, drops all jobs with score < 50

**AI Scoring Rules (embedded in system prompt):**
- Flexible fresher-friendly scoring — doesn't penalize for lacking AWS/Docker/K8s
- Java Backend / QA Automation → scored HIGH (70-90)
- .NET/C# → scored MODERATE (50-70)
- Score 0 only if 3+ years mandatory OR complete language mismatch

---

### 5.5 AI Reasoning & Resume Tailoring Component

| Attribute | Detail |
|---|---|
| **Purpose** | Uses deep AI reasoning to generate a hyper-tailored resume for each shortlisted job |
| **Files** | `src/resume_tailor.py` (101 lines), `src/ai_engine.py` (lines 117-205) |
| **Dependencies** | `openai` (AsyncOpenAI), `asyncio`, `json`, `copy` |
| **Inputs** | `List[Job]` (shortlisted, with `.extracted_requirements`), master resume YAML |
| **Outputs** | `List[dict]` — tailored resume JSON objects |

**Internal Workflow:**
1. Loads the master resume from `data_folder/plain_text_resume.yaml`
2. Uses the **compressed requirements** (`job.extracted_requirements`) from Phase 2 instead of the full JD — this is a key token-saving optimization
3. Calls `call_ai_tailoring_async()` with:
   - **Thinking mode: ENABLED** (deep reasoning for quality output)
   - **Temperature**: 0.3
   - **Retry logic**: 3 attempts with exponential backoff (longer delays than scoring)
4. AI applies a "Reframing Lens" — dynamically adapts the resume based on whether the target role is QA/Testing or Backend/Java
5. AI returns a **Delta JSON** containing only modified sections: `profile_summary`, `skills`, `experience_details`, `projects`
6. Delta is merged into a `deepcopy()` of the master resume
7. All jobs are processed concurrently via `tailor_resumes_batch()` using `asyncio.gather()`

**AI Tailoring Rules (embedded in system prompt):**
- Zero hallucination: Never invents fake experience
- Exactly 2 projects, 3 bullets each (max 20 words per bullet)
- Professional summary: exactly 2 sentences
- Keyword density injection: top 3 JD keywords must appear in summary, experience, and projects
- No weak verbs: "Worked on" → "Engineered", "Responsible for" → "Orchestrated"

---

### 5.6 Resume Generation (HTML Rendering) Component

| Attribute | Detail |
|---|---|
| **Purpose** | Transforms tailored resume JSON into ATS-compliant HTML using Jinja2 templates |
| **File** | `templates/resume_template.html` (279 lines) |
| **Technologies** | Jinja2, HTML5, CSS |
| **Inputs** | `resume` (tailored dict), `job` (Job object with `.is_testing_role`) |
| **Outputs** | Rendered HTML string |

**Key Features:**
- **ATS-Compliant Design**: Times New Roman font, clean sections, no fancy graphics
- **Dynamic Section Reordering**: If `job.is_testing_role == True`, Experience comes before Projects; otherwise Projects first — maximizes relevance visibility
- **Flexible Data Handling**: Supports both dict-style responsibilities (`{responsibility_1: "..."}`) and string arrays
- **Jinja2 Macros**: `render_experience()` and `render_projects()` are defined as macros for reuse and conditional ordering
- **Contact Bar**: Dynamically constructs a `|`-separated contact line from available fields (phone, email, LinkedIn, GitHub)

---

### 5.7 PDF Generation Component

| Attribute | Detail |
|---|---|
| **Purpose** | Converts rendered HTML resumes to single-page A4 PDF files |
| **File** | `src/pdf_generator.py` (69 lines) |
| **Dependencies** | Playwright (headless Chromium), Jinja2, `src.config_loader` |
| **Inputs** | `Job` object, tailored resume dict, date string, Playwright `page` object |
| **Outputs** | PDF file path string |

**Internal Workflow:**
1. Creates output directory: `{desktop_path}/AutoApply_Output/{date_str}/`
2. Builds filename: `{Company}_{CandidateName}_Resume.pdf`
3. Renders HTML using Jinja2 template + tailored resume data + job data
4. Sets HTML content on the Playwright page
5. Injects JavaScript to auto-scale content:
   - Measures `scrollHeight`
   - If content exceeds 1100px (≈A4 height), applies CSS `transform: scale()`
   - Minimum scale factor: 0.80 (preserves readability)
6. Calls `page.pdf()` with zero margins (margins handled by CSS)
7. Returns the file path

**Performance Optimization:** A single Playwright browser and page object are reused across all PDFs — only launched once per pipeline run.

---

### 5.8 Database Component

| Attribute | Detail |
|---|---|
| **Purpose** | Persists pipeline results and application tracking data to Supabase PostgreSQL |
| **Files** | `src/db.py` (92 lines), `setup_db.py` (80 lines), `setup_supabase.sql` (63 lines) |
| **Dependencies** | `supabase` Python SDK, `psycopg2` (for initial setup), `python-dotenv` |
| **Inputs** | `pipeline_state` dict, `List[Job]`, `List[str]` (PDF paths) |
| **Outputs** | Database records (pipeline_runs, tracked_jobs, applications) |

**Functions:**
- `save_pipeline_results()` — Inserts a pipeline run record, uploads generated PDFs to Supabase Storage, inserts each shortlisted job with full metadata (source, requirements, tailored resume), and creates an application record (status: "generated").
- `delete_pipeline_run()` — Cascade-deletes a run: status_history → applications → tracked_jobs → pipeline_runs. Deletes associated PDFs from Supabase Storage.
- `get_job_pdf_path()` — Retrieves the PDF path/URL for a tracked job.
- `cleanup_old_pdfs()` — Background auto-cleanup function that removes PDFs older than 30 days if the status is "generated", "rejected", or "custom".
- **Caching Functions**: `get_cached_jd_score()` and `save_jd_cache()` manage the `jd_cache` table to prevent re-scoring duplicate jobs.
- **Sampling Functions**: `sample_raw_jobs()`, `sample_scored_jobs()`, and `sample_tailored_jobs()` provide database records for the Test Engine.

**Connection:** Uses Supabase REST API via the `supabase` Python SDK, configured through `.env` environment variables (`SUPABASE_URL`, `SUPABASE_KEY`).

---

### 5.9 Sheet Generator Component

| Attribute | Detail |
|---|---|
| **Purpose** | Creates a professionally formatted Excel spreadsheet of scored and shortlisted jobs |
| **File** | `src/sheet_generator.py` (142 lines) |
| **Dependencies** | `pandas`, `openpyxl` |
| **Inputs** | `List[Job]` (scored), `List[str]` (PDF paths), `test_mode` flag |
| **Outputs** | Excel file path string |

**Features:**
- Dark header row with white bold text
- Color-coded scores: green (≥80), yellow (≥50)
- Clickable hyperlinks for job URLs ("🔗 Apply Now") and resume files ("📄 Open Resume")
- Auto-adjusted column widths
- Frozen panes (header row + first 3 columns)
- Full description columns set to 80-char width to prevent vertical stretching

---

### 5.10 Email Sender Component

| Attribute | Detail |
|---|---|
| **Purpose** | ZIPs daily output and emails it to the user via Gmail SMTP |
| **File** | `src/email_sender.py` (140 lines) |
| **Dependencies** | `smtplib`, `shutil`, `email.mime.*` |
| **Inputs** | Output folder path, date string, stats dict, shortlisted jobs |
| **Outputs** | Email sent via SMTP; ZIP file preserved on Desktop |

**Internal Workflow:**
1. Checks if email is enabled and credentials are valid
2. Creates a ZIP archive of the output folder on the Desktop
3. Composes an HTML email with:
   - Scraping & filtering statistics table
   - AI processing statistics
   - Table of final shortlisted jobs with color-coded scores
4. Attaches the ZIP file
5. Sends via Gmail SMTP (port 587, STARTTLS before login)
6. On failure, preserves the ZIP file and logs the error

---

### 5.11 Dashboard Component (Frontend)

| Attribute | Detail |
|---|---|
| **Purpose** | Provides a real-time visual control panel for the pipeline with live status updates |
| **File** | `frontend/src/pages/Dashboard.jsx` (416 lines) |
| **Technologies** | React, Framer Motion, Lucide Icons, SSE |

**Sub-Views (phase-driven rendering):**

| Phase | Component | What it shows |
|---|---|---|
| `idle` | `IdleView` | Platform toggles (LinkedIn/Indeed), test mode toggle, Start button |
| `scanning` | `ScanView` | Live job table streaming in real-time, total count, current cycle |
| `filtering` | `FilterView` | Dropped jobs table with reasons (Senior title, Stale, Location, etc.) |
| `scoring` | `ScoreView` | Live scoring table with spinner → checkmark + score, color-coded |
| `tailoring` | `TailorView` | Shortlisted jobs being processed, resume generation status |
| `saving` | `SavingView` | Database persistence indicator |
| `done` | `CompleteView` | Summary stats (scraped/filtered/approved/resumes) + "View Tracker" button |
| `test-lab` | `TestLab` | Separate interface for granular, modular testing of pipeline stages |

**Real-Time Updates:** Uses Server-Sent Events (SSE) via `/api/stream` endpoint. The backend polls `pipeline_state` every 500ms and emits changes.

**Controls:**
- Start Pipeline (with platform selection and test mode)
- Abort Pipeline (sends `/api/stop`)

---

### 5.12 Application Tracker Component

| Attribute | Detail |
|---|---|
| **Purpose** | Kanban-style board for tracking job application statuses post-pipeline |
| **Files** | `frontend/src/pages/Tracker.jsx`, `frontend/src/components/tracker/` (4 components) |
| **Technologies** | React, Supabase JS client, HTML5 Drag & Drop |

**Sub-Components:**

| Component | Purpose |
|---|---|
| `Tracker.jsx` | Page wrapper — fetches runs, applications; handles filtering and status changes |
| `KanbanBoard.jsx` | Renders 7 status columns; supports drag-and-drop between columns |
| `ApplicationCard.jsx` | Individual job card with title, company, score, status dropdown |
| `FilterBar.jsx` | Search input for filtering by job title or company |
| `JobDetailModal.jsx` | Detailed modal: score, source, missing skills, personal notes, resume download |

**Kanban Columns:** `Generated` → `Applied` → `Shortlisted` → `Interview` → `Offer` → `Accepted` / `Rejected`

**Key Features:**
- **Pipeline Run Selector**: Dropdown to filter applications by specific pipeline run
- **Delete Run**: Removes a pipeline run from DB + deletes local PDF files
- **Status Change**: Optimistic UI update + Supabase persist + status_history logging
- **Personal Notes**: Editable notes per application (persisted to Supabase)
- **Resume Viewer**: In-browser PDF viewing and download via Flask `/api/resume/<job_id>`
- **Direct Supabase Connection**: The Tracker reads/writes directly to Supabase via the JS client (does NOT go through Flask)

---

### 5.13 Test Engine Component

| Attribute | Detail |
|---|---|
| **Purpose** | Provides modular execution of individual pipeline stages with database sampling to bypass full runs and save AI tokens |
| **File** | `src/test_engine.py` |
| **Dependencies** | `src.db`, `src.scraper`, `src.scorer`, `src.resume_tailor`, `src.pdf_generator` |
| **Inputs** | Selected stages (scrape, score, tailor, render), sampling counts |
| **Outputs** | Stage-specific results dict |

**Features:**
- **Granular Execution**: Can run just scoring, just tailoring, or just rendering.
- **Database Sampling**: Instead of scraping new jobs, it samples previously scraped/scored jobs from Supabase.
- **Token Efficiency**: Allows rapid testing of AI prompt changes without running the full expensive pipeline.

---

## 6. Pipeline Orchestration

### Two Orchestrators

#### CLI Orchestrator (`run.py` — 180 lines)
- Entry point: `python run.py [--test] [--dry-run]`
- 5-phase linear pipeline: Scrape → Score → Tailor+PDF → Excel → Email
- No dashboard, no database saving
- Designed for Windows Task Scheduler with `run_autoapply.bat`
- `--dry-run` mode writes an audit log instead of generating PDFs/emails

#### Web Orchestrator (`app.py` — 615 lines)
- Entry point: `python app.py` → Flask on port 5000
- Contains **two pipeline functions**:
  - `run_pipeline()` — Production mode (full run with DB save)
  - `run_test_pipeline()` — Test mode (5 combos, 3 resumes, DB save, no email)
- Pipelines run in **daemon threads** so Flask remains responsive
- Pipeline state is tracked in a global `pipeline_state` dict, polled by SSE
- **Callbacks system**: Dashboard registers event handlers (`on_cycle_start`, `on_job_scraped`, `on_job_dropped`, `on_score_start`, `on_score_complete`) that update `pipeline_state` in real-time
- `stop_event` (threading.Event) allows user-initiated pipeline abort

### Flask API Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Serve React SPA (catch-all) |
| `/api/start` | POST | Start production pipeline |
| `/api/test-start` | POST | Start test pipeline |
| `/api/stop` | POST | Abort running pipeline |
| `/api/status` | GET | Get current `pipeline_state` |
| `/api/stream` | GET | SSE endpoint for real-time state |
| `/api/logs` | GET | Dequeue log messages |
| `/api/config` | GET | Return current config.yaml |
| `/api/runs/<run_id>` | DELETE | Delete a pipeline run + local files |
| `/api/resume/<job_id>` | GET | Serve a generated PDF |
| `/edit_profile` | GET/POST | YAML resume editor (server-rendered HTML) |

---

## 7. Data Flow Between Components

```
config.yaml ──────────────────────────────────────────────────────────────┐
data_folder/plain_text_resume.yaml ─────────────────────┐                │
.env (SUPABASE_URL, SUPABASE_KEY) ──────────────────────┼───────────┐    │
frontend/.env (VITE_SUPABASE_URL, VITE_SUPABASE_KEY) ──┐│           │    │
                                                        ││           │    │
                                                        ││           ▼    ▼
                                                        ││    ┌────────────────┐
    ┌──────────────┐                                    ││    │ config_loader  │
    │   JobSpy API │                                    ││    │ load_config()  │
    └──────┬───────┘                                    ││    │ load_resume()  │
           │ raw DataFrames                             ││    └───────┬────────┘
           ▼                                            ││            │
    ┌──────────────┐   List[Job]   ┌────────────────┐  ││            │
    │   scraper.py │──────────────▶│   scorer.py    │  ││            │
    │ (+ Pandas    │               │ (keyword filter│  ││            │
    │  filters)    │               │  + async AI)   │  ││            │
    └──────────────┘               └───────┬────────┘  ││            │
                                           │ scored    ││            │
                                           │ List[Job] ││            │
                                           ▼           ││            │
                                    ┌──────────────┐   ││            │
                                    │ Top N = 20   │   ││            │
                                    │ Shortlister  │   ││            │
                                    └──────┬───────┘   ││            │
                                           │           ││            │
                                           ▼           ▼│            │
                                    ┌────────────────────┘            │
                                    │  resume_tailor.py               │
                                    │  (uses master resume ◄──────────┘
                                    │   + extracted_requirements)
                                    └──────┬─────────────┐
                                           │ List[dict]  │
                                           ▼             │
                                    ┌──────────────┐     │
                                    │pdf_generator │     │
                                    │ (Playwright) │     │
                                    └──────┬───────┘     │
                                           │ List[str]   │
                                           │ (PDF paths) │
                                           ▼             │
                            ┌──────────────┼─────────────┘
                            │              │
                    ┌───────▼───┐  ┌───────▼──────┐  ┌──────────────┐
                    │  db.py    │  │sheet_generator│  │email_sender  │
                    │ (Supabase)│  │ (.xlsx)       │  │ (SMTP+ZIP)   │
                    └───────────┘  └──────────────┘  └──────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │ React Dashboard  │
               │ (SSE + Supabase) │
               └──────────────────┘
```

---

## 8. Database Schema

Four tables in Supabase PostgreSQL (RLS disabled for backend access):

### `pipeline_runs`
| Column | Type | Description |
|---|---|---|
| id | UUID (PK) | Auto-generated |
| mode | TEXT | `prod` / `test` / `dry_run` |
| jobs_scraped | INT | Total raw jobs found |
| jobs_filtered | INT | Jobs after pandas filtering |
| jobs_scored | INT | Jobs successfully scored by AI |
| jobs_shortlisted | INT | Jobs selected for resume generation |
| resumes_generated | INT | PDFs successfully created |
| scrape_stats | JSONB | Full statistics breakdown |
| platforms | TEXT[] | e.g., `['linkedin', 'indeed']` |
| started_at | TIMESTAMPTZ | Run start time |
| completed_at | TIMESTAMPTZ | Run completion time |

### `jd_cache`
| Column | Type | Description |
|---|---|---|
| url | TEXT (PK) | Job posting URL |
| score | INT | AI match score (0-100) |
| missing_skills | TEXT[] | Skills candidate lacks |
| extracted_requirements | TEXT | Compressed JD requirements |
| is_testing_role | BOOLEAN | Whether job is QA/Testing |
| updated_at | TIMESTAMPTZ | Last update time |

### `tracked_jobs`
| Column | Type | Description |
|---|---|---|
| id | UUID (PK) | Auto-generated |
| run_id | UUID (FK → pipeline_runs) | Parent run |
| title | TEXT | Job title |
| company | TEXT | Company name |
| location | TEXT | Job location |
| url | TEXT | Job posting URL |
| source | TEXT | `linkedin` / `indeed` |
| score | INT | AI match score (0-100) |
| missing_skills | TEXT[] | Skills candidate lacks |
| extracted_requirements | TEXT | Compressed JD requirements |
| is_testing_role | BOOLEAN | Whether job is QA/Testing |
| tailored_resume | JSONB | Full tailored resume JSON |
| pdf_filename | TEXT | Supabase Storage public URL (or local fallback) |
| created_at | TIMESTAMPTZ | Record creation time |

### `applications`
| Column | Type | Description |
|---|---|---|
| id | UUID (PK) | Auto-generated |
| job_id | UUID (FK → tracked_jobs) | Associated job |
| status | TEXT | `generated` / `applied` / `shortlisted` / `interview` / `offer_received` / `accepted` / `rejected` / `custom` |
| custom_status | TEXT | User-defined status |
| notes | TEXT | Personal notes |
| applied_at | TIMESTAMPTZ | When user marked as applied |
| updated_at / created_at | TIMESTAMPTZ | Timestamps |

### `status_history`
| Column | Type | Description |
|---|---|---|
| id | UUID (PK) | Auto-generated |
| application_id | UUID (FK → applications) | Parent application |
| old_status | TEXT | Previous status |
| new_status | TEXT | New status |
| notes | TEXT | Change notes |
| changed_at | TIMESTAMPTZ | When status changed |

---

## 9. Frontend Architecture

```
frontend/
├── .env                    # Supabase credentials (VITE_ prefixed)
├── index.html              # HTML shell
├── package.json            # React 19, Vite 8, Framer Motion, etc.
├── vite.config.js          # Dev proxy: /api → localhost:5000
├── dist/                   # Production build (served by Flask)
└── src/
    ├── main.jsx            # React entry point
    ├── App.jsx             # BrowserRouter + Layout + Routes
    ├── App.css             # Vite boilerplate styles
    ├── index.css           # Design system (Apple-inspired glassmorphism)
    ├── lib/
    │   └── supabase.js     # Supabase client initialization
    ├── pages/
    │   ├── Dashboard.jsx   # Pipeline control panel (SSE-driven)
    │   ├── Tracker.jsx     # Application tracking (Supabase-driven)
    │   └── TestLab.jsx     # Modular testing interface
    └── components/
        ├── tracker/
        │   ├── KanbanBoard.jsx     # 7-column drag-and-drop board
        │   ├── ApplicationCard.jsx # Job card with status dropdown
        │   ├── FilterBar.jsx       # Search input
        │   └── JobDetailModal.jsx  # Full job detail + notes + resume
        ├── pipeline/               # (empty, reserved)
        └── ui/                     # (empty, reserved)
```

### Routing
| Path | Component |
|---|---|
| `/` | `Dashboard` |
| `/tracker` | `Tracker` |
| `/test-lab` | `TestLab` |

### Design System (index.css)
- **Aesthetic**: Apple-inspired light glassmorphism
- **Colors**: Apple system colors (Blue #007aff, Green #34c759, Orange #ff9500, Red #ff3b30)
- **Typography**: Inter (UI), JetBrains Mono (code)
- **Background**: Radial gradient mesh (`hsla(210)` + `hsla(190)` + `hsla(240)`)
- **Panels**: Frosted glass with `backdrop-filter: blur(20px) saturate(180%)`
- **Animations**: Framer Motion for page transitions and list item entrances

### Data Flow
- **Dashboard**: Reads pipeline state from Flask `/api/stream` (SSE) and `/api/status` (REST)
- **Tracker**: Reads/writes directly to Supabase via the JS client (`@supabase/supabase-js`); uses Flask only for `/api/runs/<id>` (delete) and `/api/resume/<id>` (PDF serving)

---

## 10. Configuration System

### Primary Config: `config.yaml`
Central configuration file loaded by `src/config_loader.py` via `load_config()`.

| Section | Key | Description | Default |
|---|---|---|---|
| `ai` | `provider` | AI provider name | `deepseek` |
| `ai` | `model` | Model identifier | `deepseek-v4-flash` |
| `ai` | `api_key` | API key | (set in file) |
| `ai` | `temperature` | Generation temperature | `0.3` |
| `search` | `platforms` | Job search platforms | `[linkedin, indeed]` |
| `search` | `search_terms` | Job search queries | (8 terms configured) |
| `search` | `locations` | Target cities | `[Pune, Mumbai, Bangalore]` |
| `search` | `hours_old` | Max job age (hours) | `72` |
| `search` | `results_wanted` | Results per combo | `20` |
| `search` | `job_types` | Job type filter | `[internship, fulltime]` |
| `search` | `country_indeed` | Indeed country | `India` |
| `search` | `proxies` | Proxy list | `[]` |
| `scoring` | `minimum_score` | AI score threshold | `50` |
| `scoring` | `top_n` | Max shortlisted jobs | `20` |
| `output` | `desktop_path` | Output base directory | `C:/Users/kalek/OneDrive/Desktop` |
| `output` | `folder_name` | Output folder name | `AutoApply_Output` |
| `email` | `enabled` | Enable email delivery | `true` |
| `email` | `sender` / `recipient` | Email addresses | (configured) |
| `email` | `app_password` | Gmail app password | (configured) |
| `resume` | `style` | Resume template style | `ats_clean` |
| `resume` | `max_pages` | Max resume pages | `1` |

### Master Resume: `data_folder/plain_text_resume.yaml`
Loaded by `load_resume()`. Contains:
- `personal_information` (name, contact, LinkedIn)
- `profile_summary`
- `education_details`
- `experience_details` (with key_responsibilities)
- `projects` (with descriptions)
- `achievements`
- `certifications`
- `skills` (categorized: Core Languages, Frameworks, Testing Tools, etc.)
- `languages`
- `work_preferences`
- `target_roles`

### Environment Variables
| File | Variable | Purpose |
|---|---|---|
| `.env` | `SUPABASE_URL` | Supabase project URL |
| `.env` | `SUPABASE_KEY` | Supabase anonymous key |
| `frontend/.env` | `VITE_SUPABASE_URL` | Same (Vite-prefixed) |
| `frontend/.env` | `VITE_SUPABASE_KEY` | Same (Vite-prefixed) |

### Secondary Config: `config.py`
Legacy config from the inherited AIHawk codebase. Sets:
- `LOG_LEVEL = 'ERROR'`
- `LLM_MODEL_TYPE = 'openai'`
- `LLM_MODEL = 'gpt-4o-mini'`
- `JOB_SUITABILITY_SCORE = 7`

> **Note**: This file is NOT used by the active pipeline. It's referenced only by legacy modules. See [Legacy Code](#17-legacy--inherited-code).

---

## 11. External APIs and Services

### DeepSeek LLM API
- **Endpoint**: `https://api.deepseek.com`
- **SDK**: OpenAI Python SDK (compatible API)
- **Model**: `deepseek-v4-flash`
- **Two Modes**:
  - Scoring: `thinking: disabled` (fast, cheap)
  - Tailoring: `thinking: enabled` (deep reasoning)
- **Prompt Caching**: Master resume pinned as system prompt for $0.0028/1M token rate
- **Rate Limiting**: Handled with exponential backoff (3 retries)

### JobSpy (python-jobspy)
- **Purpose**: Multi-platform job scraping
- **Platforms**: LinkedIn, Indeed
- **Parameters**: search_term, location, job_type, results_wanted, hours_old, country_indeed
- **LinkedIn**: `linkedin_fetch_description=True` (fetches full JDs)
- **Anti-Ban**: 5-12 second random delays between requests

### Supabase
- **URL**: `https://hysfjbecwcljddszcjui.supabase.co`
- **Usage**: REST API via Python SDK (backend) and JS SDK (frontend)
- **RLS**: Disabled on all tables for unrestricted backend access
- **Auth**: Anonymous key (no user authentication implemented)

### Gmail SMTP
- **Server**: `smtp.gmail.com:587`
- **Auth**: App Password (16-char)
- **Protocol**: STARTTLS before login (mandatory)
- **Used only in CLI mode** (`run.py`); not used in web dashboard mode

---

## 12. Folder Structure

```
AutoApply/
├── .env                          # Supabase credentials
├── .gitignore                    # Git ignore rules
├── .github/
│   ├── CODE_OF_CONDUCT.md        # Open source code of conduct
│   ├── CONTRIBUTING.md           # Contribution guidelines
│   ├── FUNDING.yml               # Sponsorship info
│   ├── ISSUE_TEMPLATE/           # Bug, docs, enhancement templates
│   └── workflows/
│       ├── ci.yml                # Python CI (install + pytest)
│       └── stale.yml             # Auto-close stale issues
│
├── app.py                        # 🔑 Flask web dashboard + pipeline orchestrator
├── run.py                        # 🔑 CLI headless pipeline orchestrator
├── config.yaml                   # 🔑 Primary project configuration
├── requirements.txt              # Python dependencies
├── setup_db.py                   # One-time database schema setup (psycopg2)
├── setup_supabase.sql            # Raw SQL for Supabase schema
├── run_autoapply.bat             # Windows batch: run pipeline → sleep PC
│
├── data_folder/                  # 🔑 User-specific data
│   ├── plain_text_resume.yaml    # Master resume (source of truth)
│   ├── work_preferences.yaml     # Legacy work preferences
│   └── secrets.yaml              # Legacy secrets placeholder
│
├── data_folder_example/          # Example data for new users
│   ├── plain_text_resume.yaml    # Sample resume (Liam Murphy)
│   ├── resume_liam_murphy.txt    # Plain text resume
│   ├── work_preferences.yaml     # Sample preferences
│   └── secrets.yaml              # Sample secrets
│
├── assets/
│   ├── AIHawk.png                # Legacy project logo
│   ├── laboro.png                # Legacy branding
│   └── resume_schema.yaml        # Resume data schema reference
│
├── templates/
│   ├── resume_template.html      # 🔑 Jinja2 ATS resume template
│   ├── dashboard.html            # ⚠️ Legacy server-rendered dashboard
│   └── edit_profile.html         # Server-rendered YAML editor
│
├── src/
│   ├── __init__.py               # Package marker
│   ├── scraper.py                # 🔑 Job scraping + Pandas pre-filter
│   ├── scorer.py                 # 🔑 AI job scoring (async)
│   ├── ai_engine.py              # 🔑 DeepSeek API wrapper (scoring + tailoring)
│   ├── resume_tailor.py          # 🔑 AI resume tailoring (async)
│   ├── pdf_generator.py          # 🔑 Playwright HTML→PDF converter
│   ├── sheet_generator.py        # Excel output with openpyxl styling
│   ├── email_sender.py           # Gmail SMTP ZIP delivery
│   ├── db.py                     # 🔑 Supabase CRUD operations
│   ├── config_loader.py          # YAML config + resume loader
│   ├── logger.py                 # 🔑 Loguru + queue sink for dashboard
│   ├── models.py                 # 🔑 Job dataclass (active pipeline)
│   └── test_engine.py            # 🔑 Modular testing and DB sampling engine
│
├── _archive/                     # ⚠️ Archived legacy code from AIHawk
│   ├── config.py
│   ├── job.py
│   ├── job_application_saver.py
│   ├── logging.py
│   ├── libs/
│   ├── prompts/
│   ├── resume_schemas/
│   └── utils/
│
├── frontend/
│   ├── .env                      # Supabase credentials (VITE_ prefix)
│   ├── package.json              # React 19, Vite 8
│   ├── vite.config.js            # Dev proxy /api → :5000
│   ├── index.html                # HTML shell
│   ├── dist/                     # Production build
│   └── src/
│       ├── main.jsx              # React mount point
│       ├── App.jsx               # Router + Layout
│       ├── App.css               # Vite boilerplate
│       ├── index.css             # 🔑 Design system (glassmorphism)
│       ├── lib/
│       │   └── supabase.js       # Supabase JS client
│       ├── pages/
│       │   ├── Dashboard.jsx     # 🔑 Pipeline control panel
│       │   ├── Tracker.jsx       # 🔑 Kanban application tracker
│       │   └── TestLab.jsx       # 🔑 Modular testing interface
│       ├── components/
│       │   ├── tracker/          # Tracker sub-components
│       │   ├── pipeline/         # (empty, reserved)
│       │   └── ui/               # (empty, reserved)
│       ├── canvas/               # (empty, reserved)
│       └── assets/               # (empty, reserved)
│
├── test_output/                  # Empty directory for test PDF output
├── test_pipeline.py              # Integration test with JSON + PDF validation
├── test_async.py                 # Async concurrency test for AI calls
├── test_json.py                  # JSON extraction test
├── tests/                        # Additional testing components
│   ├── test_components.py
│   └── test_phase3_upgrade.py
│
├── CONTRIBUTING.md               # Contribution guidelines
├── LICENSE                       # GPL-3.0 License
└── README.md                     # Basic project readme
```

> **Key**: 🔑 = Active core file, ⚠️ = Legacy/inherited code (not used by active pipeline)

---

## 13. Error Handling Strategy

### Pipeline-Level Error Handling
Each pipeline phase is wrapped in a try/except block that:
1. Logs the error type, message, and full traceback
2. Provides a "Hint" suggesting common fixes
3. Returns early (stops the pipeline) on critical failures
4. Continues to the next item on per-job failures (PDF generation, tailoring)

### AI API Error Handling
- **Retry Logic**: 3 attempts with exponential backoff
  - Scoring: `(2^attempt × 2 + random) seconds`
  - Tailoring: `(2^attempt × 3 + random) seconds`
- **JSON Parsing Fallback**: If AI response isn't valid JSON, uses `find('{')` / `rfind('}')` to extract the JSON substring
- **Markdown Stripping**: Handles AI responses wrapped in ` ```json ``` ` code blocks
- **Graceful Degradation**: If tailoring fails for a job, falls back to the unmodified master resume

### Database Error Handling
- If Supabase credentials are missing, prints a warning and continues (results simply aren't persisted)
- Cascade delete has ordered cleanup: status_history → applications → tracked_jobs → pipeline_runs

### Email Error Handling
- Network errors, SMTP auth errors, and general exceptions are all caught individually
- ZIP file is always preserved on Desktop as a fallback

### Frontend Error Handling
- Dashboard: Shows error banner if backend connection fails
- Tracker: Logs Supabase errors to console; reverts optimistic UI updates on failure

---

## 14. Logging Architecture

### Active Logging System (`src/logger.py`)
Uses **Loguru** with two sinks:

1. **Console Sink**: `sys.stdout` with timestamp formatting (`YYYY-MM-DD HH:mm:ss`)
2. **Queue Sink**: Custom `QueueSink` class pushes formatted log messages to a `queue.Queue` for real-time streaming to the Flask dashboard

### Dashboard Log Streaming
1. Backend: `pipeline_log_interceptor()` in `app.py` parses log messages to update `pipeline_state`
2. Frontend: SSE endpoint (`/api/stream`) emits `pipeline_state` as JSON every 500ms
3. Frontend: Alternative polling endpoint (`/api/logs`) dequeues from `log_queue`

### Legacy Logging System (`src/logging.py`)
Inherited from AIHawk. Features:
- Optional file logging (`log/app.log`) with rotation and compression
- Optional console logging to stderr
- Selenium-specific logging (`log/selenium.log`)
- Controlled by `config.py` settings (`LOG_LEVEL`, `LOG_TO_FILE`, `LOG_TO_CONSOLE`)

> **Note**: Both logging systems coexist. The active pipeline uses `src/logger.py`; legacy modules import from `src/logging.py`. They do NOT conflict because they use separate Loguru instances.

---

## 15. Testing Strategy

### Test Files

| File | Purpose | Status |
|---|---|---|
| `test_pipeline.py` | Full integration test: scrape → score → tailor → validate JSON → generate PDF → validate PDF | Manual execution |
| `test_async.py` | Verifies concurrent AI API calls work correctly with `asyncio.gather()` | Manual execution |
| `test_json.py` | Tests JSON extraction from markdown-wrapped AI responses | Manual execution |
| `tests/*` | Contains specific testing scripts (`test_components.py`, `test_phase3_upgrade.py`) | Manual execution |
| `app.py` (test mode) | Test pipeline via web dashboard (3 resumes, DB save, no email) | Via UI |
| `run.py --test` | Test pipeline via CLI (1 combo, no email) | Via CLI |
| `test_engine.py` | Modular testing via database sampling to test specific stages (Scraping, Scoring, Tailoring, Rendering) without full execution | Via UI `/test-lab` |

### Validation in `test_pipeline.py`
- **JSON Validation**: Checks company name appears in resume, bullet points start with action verbs, bullets ≤30 words, ATS keyword coverage ≥20%
- **PDF Validation**: Checks PDF is exactly 1 page, text is extractable and non-trivial (>100 chars)

### CI Pipeline (`.github/workflows/ci.yml`)
- Triggered on push and PR
- Runs on Ubuntu with Python 3.x
- Installs requirements and runs `pytest`

> **Limitation**: No unit tests exist. The CI pipeline will find no test files matching pytest conventions (files must be named `test_*.py` or `*_test.py` and use pytest functions/classes).

---

## 16. Execution Modes

### Production Mode (CLI)
```bash
python run.py
```
- Full combinatorial search matrix (all combos)
- All platforms enabled
- 50% minimum score threshold
- Top 20 shortlisted
- PDFs + Excel + Email delivery

### Production Mode (Web)
Via Dashboard → Start Pipeline
- Same as CLI but with:
  - Platform selection from UI toggles
  - Real-time SSE status updates
  - Supabase database persistence
  - No email delivery (replaced by DB save)

### Test Mode (CLI)
```bash
python run.py --test
```
- First 5 search combos, 20 results each (max 100 jobs)
- All jobs scored (no threshold filter)
- Top 3 shortlisted for tailoring

### Test Mode (Web)
Via Dashboard → Enable "Test Mode" toggle → Start Pipeline
- Same limits as CLI test mode
- 3 resumes generated
- Saved to DB for Tracker viewing
- No email delivery

### Modular Test Lab
Via Dashboard → Test Lab Tab (`/test-lab`)
- Granular execution of any combination of stages (Scrape, Score, Tailor, Render).
- **Database Sampling**: Randomly samples past `tracked_jobs` to bypass scraping/scoring and save AI tokens.
- **Dynamic Options**: Allows customizing how many jobs to sample/process per stage.
- Shows detailed short results for manual testing.


### Dry Run Mode (CLI)
```bash
python run.py --dry-run
```
- Full scraping and scoring
- Writes audit log instead of generating PDFs
- No Excel, no email
- Used for validating the pipeline without producing output

### Dry Run Mode (Web)
Via `/api/start` with `dry_run: true` in POST body
- Same as CLI dry run but with dashboard feedback

### Scheduled Mode
```
run_autoapply.bat → Task Scheduler
```
1. Navigates to project directory
2. Runs `python run.py`
3. Suspends PC after completion

---

## 17. Legacy / Inherited Code

The project was forked from or inspired by the **AIHawk** (formerly "Auto Jobs Applier") project. Several files remain from the original codebase but are **NOT used** by the active AutoApply pipeline:

| File | Original Purpose | Why It's Legacy |
|---|---|---|
| `config.py` | LLM config (OpenAI, Ollama) | Replaced by `config.yaml` |
| `src/job.py` | Job dataclass (with role, apply_method) | Replaced by `src/models.py` |
| `src/jobContext.py` | Job + Application context | Not used |
| `src/job_application_saver.py` | Save applications to local directories | Replaced by Supabase DB |
| `src/logging.py` | Configurable logging with Selenium support | Replaced by `src/logger.py` |
| `src/utils/constants.py` | String constants for LLM, etc. | Only imported by `config.py` |
| `src/utils/chrome_utils.py` | Selenium Chrome setup + HTML→PDF | Replaced by Playwright |
| `src/resume_schemas/` | Structured resume/profile dataclasses | Not used by pipeline |
| `src/libs/llm_manager.py` | Multi-provider LLM manager (~28KB) | Replaced by `ai_engine.py` |
| `src/libs/resume_and_cover_builder/` | Full resume/cover letter generation system | Replaced by `resume_tailor.py` + `pdf_generator.py` |
| `src/prompts/*.txt` | External prompt templates | Prompts now embedded in `ai_engine.py` |
| `templates/dashboard.html` | Server-rendered dashboard | Replaced by React SPA |
| `data_folder/work_preferences.yaml` | Work preference config | Not used by active pipeline |
| `data_folder/secrets.yaml` | API key storage | Replaced by `config.yaml` + `.env` |
| `assets/AIHawk.png` | Original project branding | Not referenced |
| `assets/laboro.png` | Branding image | Not referenced |
| `assets/resume_schema.yaml` | Resume schema definition | Reference only |

**Impact**: These files increase the project's apparent complexity but do not affect runtime behavior. They could be safely moved to an `_archive/` directory or deleted.

---

## 18. Current Limitations

### Technical Limitations
1. **No Authentication**: The web dashboard and API endpoints have zero authentication. Anyone with network access can start/stop the pipeline and view data.
2. **Single User**: The system is hardcoded for one candidate (resume, config, scoring rules).
3. **No Rate Limiting**: No protection against rapid API calls to DeepSeek or Supabase.
4. **Browser Dependency**: Playwright requires Chromium to be installed (`playwright install`). PDF generation fails without it.
5. **Windows-Specific**: `run_autoapply.bat` and `sys.stdout.reconfigure(encoding='utf-8')` are Windows-specific. The batch script hardcodes a Windows path.
6. **No Concurrent Pipeline Runs**: Only one pipeline can run at a time (enforced by `pipeline_state["running"]` check).
7. **In-Memory State**: Pipeline state is stored in a Python dict. If Flask restarts, all in-progress state is lost.

### AI/Data Limitations
10. **Hardcoded Scoring Rules**: The AI system prompt contains hardcoded target roles and scoring biases specific to one candidate.
11. **Keyword List Maintenance**: `CORE_STACK_KEYWORDS` must be manually updated if the candidate's target roles change.
12. **No JD Caching**: If the same job appears in multiple runs, it's re-scored every time.
13. **DeepSeek Dependency**: The entire AI pipeline depends on a single provider. No fallback model.
14. **Regex Limitations**: Experience detection regex can produce false positives (e.g., "3 years of company history").

### Frontend Limitations
15. **No Mobile Optimization**: The Kanban board uses fixed-width columns that don't adapt well to mobile screens.
16. **No Offline Support**: No PWA capabilities, no service worker.
17. **No Real-Time Tracker Updates**: The Tracker page doesn't auto-refresh when a pipeline completes.
18. **Empty Component Directories**: `pipeline/`, `ui/`, `canvas/`, `assets/` in the frontend are empty placeholders.

---

## 19. Inconsistencies Found

### Code vs. Schema Inconsistencies

1. **Prompt Files vs. Embedded Prompts**: `_archive/prompts/scoring_prompt.txt` and `resume_tailor_prompt.txt` exist as external files but are **NOT used** — the actual prompts are hardcoded directly in `src/ai_engine.py` (lines 62-89 and 126-179). The external files represent an older architecture.

2. **`config.py` vs. `config.yaml`**: Two configuration systems existed. Legacy `config.py` is now in `_archive/`. The active pipeline uses `config.yaml` with `provider: deepseek` and `model: deepseek-v4-flash`.

3. **`resume` config section unused**: `config.yaml` defines `resume.style` and `resume.max_pages` but these values are never read by any code. The resume style is hardcoded in the Jinja2 template, and max pages is enforced by CSS/JS scaling.

4. **`offer_received` vs. `offer` status mismatch**: The DB schema defines status `offer_received` but the Kanban board uses `offer` as the column ID. The `KanbanBoard.jsx` has a workaround: `app.status === 'offer_received' && statusId === 'offer'`.

8. **`get_human_date_str()` defined twice**: Once in `src/sheet_generator.py` (returns "8 July" format) and once in `app.py` (returns "2026-07-08" format). They serve different purposes but share the same function name.

9. **`score_jobs` is sync but calls async**: `scorer.py` defines `score_jobs()` as a regular function that internally uses `asyncio.run()`. In `test_pipeline.py:116`, it's called with `asyncio.run(score_jobs(jobs))` — this would fail because `asyncio.run()` can't be nested. This is likely a stale test file.

10. **Batch script path mismatch**: `run_autoapply.bat` references `cd "C:\Users\kalek\OneDrive\Desktop\AutoApply"` but the actual project path is `C:\Users\kalek\OneDrive\Desktop\Projects\AutoApply`.

---

## 20. Future Roadmap

Based on the codebase structure, empty directories, and architecture patterns, the following areas are likely planned or would be natural extensions:

1. **Cloud Deployment**: Move from local Windows machine to a cloud-hosted solution (e.g., AWS Lambda, Google Cloud Run) for 24/7 scheduling
2. **Mobile/PWA**: The `canvas/` directory and responsive CSS suggest PWA capabilities were planned
3. **Multi-User Support**: Add authentication (Supabase Auth) and per-user configs
4. **Additional Platforms**: Extend JobSpy integration to Glassdoor, Naukri, etc.
5. **Auto-Apply**: The project name "AutoApply" suggests automated job application submission (not yet implemented — currently only generates resumes)
6. **Cover Letter Generation**: The legacy `cover_letter_prompt/` directory and `resume_facade.py` contain cover letter infrastructure
7. **AI Model Fallback**: Support multiple AI providers (OpenAI GPT-4o, Claude, Gemini) as fallbacks
8. **Pipeline Analytics Dashboard**: Historical charts, cost tracking, conversion rates
9. **Resume A/B Testing**: Generate multiple resume variants per job and track which get callbacks

---

## 21. Suggestions and Recommendations

### High Priority

1. **🔐 Add Authentication**: The web dashboard is completely open. Add Supabase Auth with at minimum a password-protected login.

2. **🔧 Fix `run_autoapply.bat` Path**: Update the `cd` path to match the actual project location.

### Medium Priority

3. **🔄 Remove Duplicate Functions**: Consolidate `get_human_date_str()` into `config_loader.py` or a shared utilities module.

4. **📊 Use `resume` Config Section**: Wire `config.yaml`'s `resume.style` and `resume.max_pages` to actually control resume generation behavior.

5. **🧪 Add Real Unit Tests**: Create pytest-compatible test files for each component (scraper, scorer, tailor, PDF generator). Mock external API calls.

6. **📱 Mobile Responsive Kanban**: Make the tracker Kanban board responsive with vertical stacking on mobile.

### Low Priority

7. **🔀 Unify Status Names**: Change the Kanban column from `offer` to `offer_received` (or vice versa) to eliminate the workaround in `KanbanBoard.jsx`.

8. **📄 Externalize AI Prompts**: Move the hardcoded AI prompts from `ai_engine.py` to the `_archive/prompts/` directory or a new `src/prompts/` directory as YAML or text files.

9. **🌐 Cross-Platform Compatibility**: Replace Windows-specific `sys.stdout.reconfigure()` with a cross-platform solution and make file paths OS-agnostic.

10. **📈 Pipeline Cost Tracking**: Track DeepSeek API token usage per run and display cumulative costs on the dashboard.

11. **🔔 Real-Time Tracker Refresh**: Add a Supabase Realtime subscription in `Tracker.jsx` so the page auto-updates when a pipeline run completes.

---

> **This document was generated by deep analysis of every file in the AutoApply codebase.**  
> **For questions or updates, modify this file directly and commit to version control.**
