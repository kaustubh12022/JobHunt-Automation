# Survey Report: Real Production Jobs, Schemas & Scoring Audit Architecture

**Agent:** `explorer_survey_jobs_1`  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_jobs_1`  
**Date:** 2026-09-29  
**Target Milestone:** AI Scoring Phase Audit & Multi-Provider Fix (Phases 1–7)

---

## 1. Executive Summary

A comprehensive investigation was conducted across `regex_audit/`, `master_raw_dataset_2026-09-29.jsonl`, filter result artifacts, evaluation ground truths, and the project root to prepare the foundation for the AI Scoring Audit.

### Core Discoveries:
1. **The ~73 Surviving Production Jobs Identified**:
   - The reference to **"~73 jobs"** in `ORIGINAL_REQUEST.md` (line 158) and `SCORING_AUDIT_PLAN.md` (lines 14, 116, 165, 168) corresponds exactly to the **73 jobs that passed Layer 1 (Pandas Pre-Filter)** located at `regex_audit/filter_results/layer1_pandas_pass.jsonl`.
   - **Crucial Schema Finding**: `layer1_pandas_pass.jsonl` contains the **full job description** (`description`) for all 73 records.
   - Conversely, `regex_audit/filter_results/layer2_regex_pass.jsonl` contains **58 jobs**, but **omits the `description` field** to minimize file size.
   - For downstream AI scoring, scoring engines **must receive job descriptions**. Therefore, loading `layer1_pandas_pass.jsonl` directly (or joining `layer2_regex_pass.jsonl` with `layer1_pandas_pass.jsonl` or `master_raw_dataset_2026-09-29.jsonl`) is mandatory.
2. **Master Raw Dataset Integrity**:
   - `regex_audit/master_raw_dataset_2026-09-29.jsonl` (6.41 MB) and `regex_audit/master_raw_dataset_2026-09-29.json` (6.76 MB) both contain **exactly 1,137 raw scraped jobs** with 100% field completeness for title, company, description, url, and source.
3. **Status of `scoring_audit/` Directory**:
   - `scoring_audit/` **does not exist yet**. It must be created with subdirectories `scoring_audit/scores/` and `scoring_audit/analysis/`.
4. **API & Dependency Readiness**:
   - `GEMINI_API_KEY`, `GROQ_API_KEY`, and `GROK_API_KEY` are **active and present** in `.env`.
   - `DEEPSEEK_API_KEY` is **absent** and strictly excluded from all scoring audit operations.
   - Python environment already has `google.genai` (v0.1.1+ official Google GenAI SDK) and `openai` (v1.0+ OpenAI-compatible client for Groq) installed.

---

## 2. Pipeline Attrition & Surviving Jobs Accounting

The table below reconciles the numbers across all stages of the filtering pipeline:

| Dataset / Stage | File Location | Record Count | Description Included? | Notes |
|---|---|:---:|:---:|---|
| **Master Raw Scrape** | `regex_audit/master_raw_dataset_2026-09-29.jsonl` | **1,137** | ✅ Yes | Complete raw capture from Indeed (657) & LinkedIn (480) |
| **Layer 1 Pass (Pandas)** | `regex_audit/filter_results/layer1_pandas_pass.jsonl` | **73** | ✅ Yes | Filtered for freshness, location, senior title, exp >3 yrs |
| **Layer 1 Fail (Pandas)** | `regex_audit/filter_results/layer1_pandas_fail.jsonl` | **1,064** | ❌ No | Dropped by Layer 1 with structured rejection reasons |
| **Layer 2 Pass (Baseline Scorer)** | `regex_audit/filter_results/layer2_regex_pass.jsonl` | **58** | ❌ No | Filtered Layer 1 survivors with baseline `src/scorer.py` |
| **Layer 2 Fail (Baseline Scorer)** | `regex_audit/filter_results/layer2_regex_fail.jsonl` | **15** | ❌ No | 12 out-of-scope stacks, 3 irrelevant JDs |
| **Layer 2 Pass (Scorer V2)** | Evaluated via `regex_audit/scorer_v2.py` | **54** | ✅ Yes (from L1) | Re-evaluated with expanded MERN & AI/LLM domain rules |
| **Ground Truth PASS** | `regex_audit/evaluation/ground_truth.jsonl` | **60** | ❌ No | 60 true entry-level target domain positions (10 FN + 50 TP) |
| **Ground Truth FAIL** | `regex_audit/evaluation/ground_truth.jsonl` | **1,077** | ❌ No | Out-of-scope, senior, non-technical, duplicate, or stale |

### Clarification on the "~73 Production Jobs":
In `SCORING_AUDIT_PLAN.md` (line 116):
> `"For 300 synthetic + 73 real × 2 providers each = 746 total API calls"`
> `"Phase 4: Score Real Production Jobs (~73 × 2 = 146 API calls)"`

- The calculation `73 × 2 = 146` API calls demonstrates that the plan specifically budgeted for the **73 Layer 1 survivors**.
- Alternatively, if the team elects to score only the **58 baseline Layer 2 survivors**, the call volume is `58 × 2 = 116` API calls (232 calls across v1 and v2 prompts).
- **Recommendation**: Provide downstream scripts with the capability to score all **73 Layer 1 survivors** (flagging the 15 Layer 2 baseline drops for visibility), or strictly the **58 baseline Layer 2 survivors**.

---

## 3. Detailed Schema Analysis

### 3.1 `regex_audit/filter_results/layer1_pandas_pass.jsonl` (73 records)
Each line is a self-contained JSON object containing full metadata and the JD body:

```json
{
  "job_index": 1,
  "id": "988ac687-fbc2-4606-b2c8-a1c10ac4b75c",
  "title": "Software Tester",
  "company": "Moksha Softlabs",
  "location": "MH, IN",
  "description": "Full cleaned job description text...",
  "url": "https://in.indeed.com/viewjob?jk=2010e3a161bb52b7",
  "source": "indeed",
  "job_type": "fulltime",
  "date_posted": "2026-09-29",
  "is_remote": false,
  "scraped_at": "2026-09-29T14:05:55.776118+00:00",
  "filter_layer": "layer1_pandas",
  "status": "PASS"
}
```

#### Field Specifications:
- `job_index` (int, 0–1136): Persistent index matching master raw dataset.
- `id` (str UUID): Unique job UUID.
- `title` (str): Cleaned job posting title.
- `company` (str): Company name.
- `location` (str): Standardized location string (e.g., `MH, IN`, `Bengaluru, Karnataka, India`).
- `description` (str): Full text of the job description. (Length stats: Min: 419, Max: 11,878, Avg: 3,256 characters).
- `url` (str): Target application or posting URL.
- `source` (str): `"indeed"` (27 jobs) or `"linkedin"` (46 jobs).
- `job_type` (str): `"fulltime"` (46 jobs) or `"internship"` (27 jobs).
- `date_posted` (str or null): Date string if extracted by scraper.
- `is_remote` (bool): `false` (66 jobs) or `true` (7 jobs).
- `scraped_at` (str ISO): Timestamp of collection.
- `filter_layer` (str): `"layer1_pandas"`.
- `status` (str): `"PASS"`.

---

### 3.2 `regex_audit/filter_results/layer2_regex_pass.jsonl` (58 records)
```json
{
  "job_index": 1,
  "id": "988ac687-fbc2-4606-b2c8-a1c10ac4b75c",
  "title": "Software Tester",
  "company": "Moksha Softlabs",
  "location": "MH, IN",
  "url": "https://in.indeed.com/viewjob?jk=2010e3a161bb52b7",
  "filter_layer": "layer2_regex",
  "status": "PASS",
  "matched_anchors": ["qa", "tester"],
  "matched_tools": ["test", "qa"]
}
```
- **Notice**: Lacks `description`.
- `matched_anchors` (List[str]): Anchors identified by `src/scorer.py` (e.g. `java`, `automation`, `python`, `qa`).
- `matched_tools` (List[str]): Tools identified by `src/scorer.py` (e.g. `test`, `api`, `git`, `sql`).

---

### 3.3 `regex_audit/filter_results/layer2_regex_fail.jsonl` (15 records)
```json
{
  "job_index": 78,
  "id": "4b7b3b4d-0db2-4d22-ab78-c0b784fa0772",
  "title": "Flutter Developer",
  "company": "Baynine Ventures",
  "filter_layer": "layer2_regex",
  "rejection_reason": "out_of_scope_stack",
  "rejection_detail": "Matched out-of-scope technology pattern in title or description",
  "matched_pattern": "flutter"
}
```
- 12 dropped due to `out_of_scope_stack` (Flutter, React Native, WordPress, PHP, Kotlin, Salesforce).
- 3 dropped due to `irrelevant_jd` (C++ Developer, Software Engineer without anchors).

---

### 3.4 `regex_audit/master_raw_dataset_2026-09-29.jsonl` (1,137 records)
File size: 6,407,800 bytes (6.11 MB).
```json
{
  "job_index": 0,
  "id": "22652da2-8b05-40f0-8f13-feb0f142ed94",
  "title": "Lead QA Engineer",
  "company": "Siemens Energy",
  "location": "MH, IN",
  "description": "### **How to contribute to our vision**...",
  "url": "https://in.indeed.com/viewjob?jk=4bf536d7e4af847e",
  "source": "indeed",
  "job_type": "internship",
  "date_posted": "2026-09-29",
  "is_remote": false,
  "raw_metadata": { "id": "in-4bf536d7e4af847e", "site": "indeed", ... },
  "scraped_at": "2026-09-29T14:05:55.571339+00:00"
}
```

---

## 4. `scoring_audit/` Directory & Architecture Survey

### 4.1 Current Status
- `scoring_audit/` **does not exist** in the workspace.
- Needs to be initialized with proper subdirectory hierarchy.

### 4.2 Required Directory Structure
```
scoring_audit/
├── synthetic_jds.json                    # 300 synthetic benchmark JDs (15 categories × 20)
├── ai_engine_v2.py                       # Dual-provider scoring engine (Gemini + Groq)
├── run_scoring_audit.py                  # Main audit orchestrator script
├── scoring_prompt_v2.txt                 # Optimized prompt with MERN, AI/LLM, calibrated ranges
├── scores/
│   ├── synthetic_gemini_scores.jsonl     # Gemini scores for 300 synthetic JDs (baseline prompt)
│   ├── synthetic_groq_scores.jsonl       # Groq scores for 300 synthetic JDs (baseline prompt)
│   ├── real_gemini_scores.jsonl          # Gemini scores for real jobs (baseline prompt)
│   ├── real_groq_scores.jsonl            # Groq scores for real jobs (baseline prompt)
│   ├── v2_synthetic_gemini_scores.jsonl  # Gemini scores with v2 prompt
│   ├── v2_synthetic_groq_scores.jsonl    # Groq scores with v2 prompt
│   ├── v2_real_gemini_scores.jsonl       # Gemini real jobs with v2 prompt
│   └── v2_real_groq_scores.jsonl         # Groq real jobs with v2 prompt
└── analysis/
    ├── synthetic_analysis_report.md
    ├── real_jobs_analysis_report.md
    ├── cross_validation_report.md
    ├── scoring_prompt_deficiencies.md
    └── v1_vs_v2_comparison.md
```

### 4.3 Providers, SDKs & Rate Limits

| Feature | Provider A: Google Gemini | Provider B: Groq | Notes |
|---|---|---|---|
| **API Key Variable** | `GEMINI_API_KEY` (Present in `.env`) | `GROQ_API_KEY` (Present in `.env`) | DeepSeek strictly excluded |
| **Model** | `gemini-2.0-flash` | `llama-3.3-70b-versatile` | Free tier models |
| **Rate Limit** | 15 RPM (min 4.0s delay between calls) | 30 RPM (min 2.0s delay between calls) | Combined throughput: 45 RPM |
| **Python SDK** | `google.genai` (Installed) | `openai` client with `base_url="https://api.groq.com/openai/v1"` (Installed) | No extra pip install needed |
| **Output Format** | Strict JSON object mode | Strict JSON mode | Exactly 6 keys required |

### 4.4 Deficiencies in Existing Baseline Prompt (`src/prompts/scoring_prompt.txt`)
Inspection of `src/prompts/scoring_prompt.txt` reveals why prompt v2 is necessary:
1. **Target Domains 6 & 7 Missing**: Only Java, QA, .NET, Full Stack (Python/JS), and Software Tester are defined. MERN Stack (React/Node/Express/Mongo) and AI/ML/LLM/Agentic AI are completely missing, leading to score suppression on legitimate modern stack jobs.
2. **Missing Skills False Positives**: Does not enforce robust case-insensitive and synonym cross-checking against the Master Resume (`data_folder/plain_text_resume.yaml`).
3. **Calibrated Score Anchors**: Lacks explicit scoring guidance for internship vs full-time tiering.

---

## 5. Exact Loading Specifications for Real Production Jobs

### 5.1 Python Helper to Load Real Production Jobs (Recommended)

To load the **73 Layer 1 surviving jobs** (which include full descriptions):

```python
import json
from pathlib import Path
from typing import List, Dict, Any

def load_real_production_jobs(
    filepath: str = "regex_audit/filter_results/layer1_pandas_pass.jsonl"
) -> List[Dict[str, Any]]:
    """
    Loads the 73 real production jobs that survived Layer 1 filtering.
    Every record contains 'title', 'company', 'location', 'description', and 'url'.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.resolve()}")
    
    jobs = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if line_str:
                job = json.loads(line_str)
                assert "description" in job and job["description"], f"Missing description on line {line_num}"
                jobs.append(job)
    return jobs
```

### 5.2 Python Helper to Load Specifically the 58 Layer 2 Survivors (With Descriptions)

If the downstream executor requires strictly the **58 jobs that survived baseline Layer 2 regex filtering**:

```python
import json
from pathlib import Path
from typing import List, Dict, Any

def load_layer2_survivors_with_descriptions(
    l1_pass_path: str = "regex_audit/filter_results/layer1_pandas_pass.jsonl",
    l2_pass_path: str = "regex_audit/filter_results/layer2_regex_pass.jsonl"
) -> List[Dict[str, Any]]:
    """
    Loads the 58 jobs that survived Layer 2 regex filtering,
    re-attaching full descriptions from Layer 1.
    """
    with open(l2_pass_path, "r", encoding="utf-8") as f:
        l2_indices = {json.loads(line)["job_index"] for line in f if line.strip()}
    
    survivors = []
    with open(l1_pass_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                job = json.loads(line)
                if job["job_index"] in l2_indices:
                    survivors.append(job)
    return survivors  # Exactly 58 jobs with full descriptions
```

---

## 6. Recommendations for Downstream Implementation

1. **Dataset Selection for R3 Baseline Scoring**:
   - The team can score all **73 jobs** from `layer1_pandas_pass.jsonl`.
   - By scoring all 73, we evaluate how AI judges the 58 jobs that passed Layer 2 **as well as** the 15 jobs dropped by Layer 2 (e.g. Job #84 Capgemini Java/Kotlin/React, Job #220 PopPop Full Stack Intern, Job #246 COMMANDO Full Stack). This provides end-to-end visibility into whether regex rejections match AI judgment.
2. **Setup of `scoring_audit/`**:
   - The orchestrator or builder agent should immediately create `scoring_audit/`, `scoring_audit/scores/`, and `scoring_audit/analysis/`.
3. **Dual Provider Engine Design**:
   - In `scoring_audit/ai_engine_v2.py`, implement an asynchronous token bucket or interval-based rate limiter (Gemini: 4.0s minimum interval, Groq: 2.0s minimum interval).
   - Use `google.genai.Client(api_key=...)` for Gemini (`gemini-2.0-flash`).
   - Use `openai.OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")` for Groq (`llama-3.3-70b-versatile`).
