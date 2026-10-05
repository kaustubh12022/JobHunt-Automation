# Scraping & Regex Testing — Master Plan

> **Status:** PLANNED — Awaiting user approval to begin execution.  
> **Created:** 2026-09-29  
> **Scope:** Scraping → Raw Data Preservation → Regex Filtering → Ground-Truth Creation → Regex Audit → Regex Rewrite → Retesting  
> **Out of Scope:** AI scoring, LLM, resume generation, database/Supabase, frontend

---

## Design Decisions (Locked)

| Decision | Choice |
|---|---|
| Storage format | JSONL (one JSON object per line) |
| Audit directory | `regex_audit/` at project root |
| Data source | Fresh production scrape (~40-45 min) |
| Filter tracking | Two layers separately (Pandas pre-filter + Scorer regex filter) |
| Agent strategy | Multi-agent parallel (5-10 agents, batches of 300-500 jobs) |
| Evaluation standard | Strict profile match |
| Domain expansion | MERN + AI/LLM/Agentic AI added to valid pass criteria |
| Sparse JD handling | Flag as regex issue if title clearly indicates relevance |
| Audit panel | Dynamic — sized based on actual results |
| Success criteria | ≥95% match against ground-truth |
| File strategy | New `scorer_v2.py` created; originals untouched |
| Anchor/keyword updates | Yes — DOMAIN_ANCHORS and TECH_TOOLS updated in scorer_v2.py |

---

## Candidate Profile (Evaluation Rubric)

- **Name:** Kaustubh Kale
- **Experience:** Fresher (1-month Java Developer internship)
- **Education:** B.E. Information Technology (2022-2026)
- **Location:** Pune, India (open to Mumbai, Bangalore, Remote)

### Valid Target Domains (a job should PASS if it matches any)
1. Java / Spring / Backend Development
2. Python / Django / Flask / Backend
3. QA / Testing / Automation (Selenium, JUnit, Postman, pytest)
4. .NET / C# / ASP.NET
5. Full Stack (any combo of frontend + backend candidate knows)
6. Software Engineering (general)
7. **MERN stack (React, Express, MongoDB, Node.js)** ← ADDED
8. **AI / ML / LLM / Agentic AI** ← ADDED

### Core Skills
Java, Python, SQL, C#, JavaScript, TypeScript, HTML, CSS, React, Next.js, Node.js, Spring Core, JDBC, REST APIs, Pandas, Asyncio, JUnit, Postman, Selenium, pytest, Docker, Kubernetes, MongoDB, MySQL, Git, Agile/Scrum

### PASS Criteria (ALL must be true)
1. Entry-level / junior / fresher / associate / graduate / trainee / 0-2 years / unspecified experience
2. Matches one of the valid target domains above
3. Not exclusively an out-of-scope stack (PHP, Ruby, iOS/Swift, Android/Kotlin, Flutter, React Native, Salesforce, SAP, Drupal, Magento, WordPress)
4. In Pune, Mumbai, Bangalore, or Remote/Hybrid/WFH/Pan-India

### FAIL Criteria (ANY makes it fail)
1. Senior / Lead / Manager / Principal / Director / Architect / Staff / Expert title (without junior/entry qualifier)
2. Requires 3+ years of direct candidate experience
3. Exclusively uses an out-of-scope tech stack
4. Non-technical role (HR, Sales, Marketing, Finance, Legal)
5. Location outside India or non-target Indian city with no remote option

---

## 7-Phase Execution Plan

### Phase 1: Fresh Scrape + Raw Data Capture (~40-45 min)
- Run `run_scraper()` with production settings
- 8 search terms × 3 locations × 2 job types
- Save EVERY raw job to `regex_audit/raw_dataset_YYYY-MM-DD.jsonl` BEFORE any filtering
- Scraper NOT modified — wrapped in an audit harness

### Phase 2: Two-Layer Filter Replay (~2 min)
- Replay Pandas pre-filter on raw dataset, record every decision
- Replay Scorer regex filter on Layer 1 survivors, record every decision
- Output 4 files: `layer1_pandas_pass.jsonl`, `layer1_pandas_fail.jsonl`, `layer2_regex_pass.jsonl`, `layer2_regex_fail.jsonl`
- Pipeline STOPS — no AI scoring

### Phase 3: Multi-Agent Evaluation (~15-30 min)
- 5-10 parallel evaluator agents, each processing 300-500 jobs
- Each agent evaluates every job against the candidate profile rubric above
- Flags false positives (passed but shouldn't have) and false negatives (failed but shouldn't have)
- Output: `false_positives.jsonl`, `false_negatives.jsonl`

### Phase 4: Ground-Truth Creation (~2 min)
- Merge evaluator findings into `ground_truth.jsonl`
- Every job gets an expected outcome (PASS or FAIL)
- Jobs not flagged = assumed correct

### Phase 5: Dynamic Regex Audit (~10-15 min)
- Agent panel (sized dynamically) analyzes flagged issues
- Root cause analysis per regex pattern
- Fix proposals with before/after examples
- Output: `audit_report.md`

### Phase 6: Regex Rewrite (~10 min)
- Create `regex_audit/scorer_v2.py` with fixed patterns
- Updated DOMAIN_ANCHORS (MERN/AI/LLM keywords added)
- Updated TECH_TOOLS (express, mongodb, node, etc.)
- Fixed edge cases in matches_senior_title, requires_3_plus_years, is_relevant_jd
- Original `src/scorer.py` UNTOUCHED

### Phase 7: Retesting Against Ground-Truth (~2 min)
- Run same raw dataset through scorer_v2.py
- Compare new outcomes vs. ground-truth
- Target: ≥95% match rate
- Output: `comparison_report.md`

---

## Directory Structure

```
regex_audit/
├── run_audit_scrape.py          # Script to run the fresh scrape
├── raw_dataset_YYYY-MM-DD.jsonl # ALL scraped jobs (2,000–3,000)
├── filter_results/
│   ├── layer1_pandas_pass.jsonl
│   ├── layer1_pandas_fail.jsonl
│   ├── layer2_regex_pass.jsonl
│   └── layer2_regex_fail.jsonl
├── evaluation/
│   ├── false_positives.jsonl
│   ├── false_negatives.jsonl
│   └── ground_truth.jsonl
├── audit_report.md
├── retest/
│   ├── v2_pass.jsonl
│   ├── v2_fail.jsonl
│   └── comparison_report.md
└── scorer_v2.py
```

---

## JSONL Schemas

### Raw Dataset Record
```json
{
  "job_index": 0,
  "id": "uuid",
  "title": "Junior Java Developer",
  "company": "TCS",
  "location": "Pune, Maharashtra, India",
  "description": "Full cleaned JD text...",
  "url": "https://...",
  "source": "linkedin",
  "job_type": "fulltime",
  "date_posted": "2026-09-28T10:00:00+00:00",
  "is_remote": false,
  "scraped_at": "2026-09-29T19:30:00+05:30"
}
```

### Filter Decision Record
```json
{
  "job_index": 42,
  "title": "Senior Java Architect",
  "company": "Infosys",
  "filter_layer": "pandas|regex",
  "rejection_reason": "senior_title|experience|out_of_scope|irrelevant_jd|location|stale|empty_desc|duplicate",
  "rejection_detail": "Human-readable explanation",
  "matched_pattern": "The exact regex pattern that triggered"
}
```

### False Positive / False Negative Record
```json
{
  "job_index": 77,
  "title": "...",
  "company": "...",
  "actual_decision": "PASS|FAIL",
  "expected_decision": "PASS|FAIL",
  "issue_type": "false_positive|false_negative",
  "reason": "Why the decision was wrong",
  "which_filter_failed": "Which filter function is responsible",
  "rejection_layer": "layer1_pandas|layer2_regex",
  "root_cause": "Root cause analysis",
  "specific_pattern_issue": "The exact pattern/keyword causing the problem"
}
```

### Ground Truth Record
```json
{
  "job_index": 0,
  "title": "...",
  "company": "...",
  "expected_outcome": "PASS|FAIL",
  "actual_outcome_layer1": "PASS|FAIL",
  "actual_outcome_layer2": "PASS|FAIL",
  "is_correct": true,
  "flag_type": null,
  "confidence": "high|medium|low",
  "notes": ""
}
```

---

## Current Regex Filter Architecture (Before Changes)

### Filters in `src/scorer.py`
- `DOMAIN_ANCHORS`: java, python, qa, selenium, automation, .net, c#, csharp, asp.net, spring, full stack, fullstack, sdet, quality assurance, postman, pytest, junit, playwright, cypress, tester, manual testing, automation testing, software testing, api testing, test automation, test case, test cases, test suite, test plan, test engineer
- `TECH_TOOLS`: spring, sql, pytest, postman, junit, rest api, api, react, javascript, html, css, mysql, mongodb, docker, git, jdbc, azure, c#, java, python, selenium, automation, database, oops, oop, microservices, django, flask, node, test, qa
- `OUT_OF_SCOPE_STACK_PATTERN`: php, laravel, ruby, rails, ios, swift, swiftui, android, kotlin, flutter, react native, salesforce, apex, sap, abap, drupal, magento, wordpress
- `matches_senior_title()`: senior, lead, manager, principal, director, head, vp, president, experienced, architect, staff, expert, ii-viii, level 2-9, L2-9, sr., plus experience range checks
- `requires_3_plus_years()`: Complex multi-step regex scanning for 3+ year requirements with safeguards for third-party/team experience
- `is_relevant_jd()`: Requires 1 domain anchor AND 1 tech tool, rejects out-of-scope stacks

### Filters in `src/scraper.py` (Pandas layer)
- Empty description drop
- Freshness (>72h cutoff)
- Location regex (LOCATION_ALIASES + REMOTE_PATTERNS)
- `matches_senior_title()` (same function from scorer)
- `requires_3_plus_years()` (same function from scorer)
- Deduplication (URL + company/title)

---

## Estimated Timeline
| Step | Duration |
|---|---|
| Create audit scripts | ~5 min |
| Fresh scrape | ~40-45 min |
| Filter replay | ~2 min |
| Multi-agent evaluation | ~15-30 min |
| Ground-truth generation | ~2 min |
| Dynamic audit | ~10-15 min |
| Regex rewrite | ~10 min |
| Retest + report | ~2 min |
| **Total** | **~90-120 min** |
