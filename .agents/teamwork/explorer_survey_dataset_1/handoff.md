# Master Raw Dataset Survey & Integrity Audit Report

**Investigator:** `explorer_survey_dataset_1`  
**Working Directory:** `c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\explorer_survey_dataset_1`  
**Dataset Targets:**
- `regex_audit/master_raw_dataset_2026-09-29.jsonl` (6.11 MB, 6,407,800 bytes)
- `regex_audit/master_raw_dataset_2026-09-29.json` (6.45 MB, 6,761,410 bytes)

---

## 1. Observation

### 1.1 Line Count & File Integrity
Execution of programmatic verification against both dataset files yielded the following output:
```text
JSONL total lines read: 1137
JSONL successfully parsed records: 1137
JSONL errors: []
JSON parsed records count: 1137
JSON is list: True
Matching records between JSONL and JSON: 1137/1137
```
- **Line Count:** Exactly 1,137 lines in `.jsonl`.
- **JSON Object Count:** Exactly 1,137 items in `.json` root list.
- **Record Parity:** Every record in `master_raw_dataset_2026-09-29.jsonl` is 100% byte-for-byte and key-for-key identical to the corresponding item in `master_raw_dataset_2026-09-29.json`.
- **Indexing & IDs:**
  - `job_index`: Strictly contiguous integers from `0` to `1136` (`min=0, max=1136, unique=1137`).
  - `id`: Exactly 1,137 globally unique UUID strings (e.g., `22652da2-8b05-40f0-8f13-feb0f142ed94`).

### 1.2 Schema & Field Verification
Across all 1,137 records, exactly 13 top-level keys exist. There are 0 missing keys and 0 null values at the top-level schema:

| Field Name | Type | Presence | Nulls | Empty Strings | Description / Value Domain |
|---|---|---|---|---|---|
| `job_index` | `int` | 1137/1137 (100%) | 0 | 0 | Deterministic sequential index (0 to 1136) |
| `id` | `str` | 1137/1137 (100%) | 0 | 0 | UUIDv4 string identifier |
| `title` | `str` | 1137/1137 (100%) | 0 | 0 | Raw scraped job title (450 unique titles) |
| `company` | `str` | 1137/1137 (100%) | 0 | 0 | Company name |
| `location` | `str` | 1137/1137 (100%) | 0 | 0 | City/State/Country string (7 distinct values) |
| `description` | `str` | 1137/1137 (100%) | 0 | 0 | Cleaned text description (min 229 chars, max 14,320 chars) |
| `url` | `str` | 1137/1137 (100%) | 0 | 0 | Direct application or listing URL |
| `source` | `str` | 1137/1137 (100%) | 0 | 0 | Platform origin (`'indeed'` or `'linkedin'`) |
| `job_type` | `str` | 1137/1137 (100%) | 0 | 0 | Employment type (`'fulltime'` or `'internship'`) |
| `date_posted` | `str` | 1137/1137 (100%) | 0 | 0 | Date string or `'nan'` (295 LinkedIn records) |
| `is_remote` | `bool` | 1137/1137 (100%) | 0 | N/A | Boolean flag (`True` or `False`) |
| `raw_metadata` | `dict` | 1137/1137 (100%) | 0 | N/A | Sub-dictionary containing 33 raw scraper attributes |
| `scraped_at` | `str` | 1137/1137 (100%) | 0 | 0 | ISO-8601 UTC timestamp with microsecond precision |

### 1.3 Nested `raw_metadata` Attributes
Every record contains `raw_metadata` with exactly 33 attributes:
`['id', 'site', 'job_url', 'job_url_direct', 'title', 'company', 'location', 'date_posted', 'job_type', 'salary_source', 'interval', 'min_amount', 'max_amount', 'currency', 'is_remote', 'job_level', 'job_function', 'listing_type', 'emails', 'company_industry', 'company_url', 'company_logo', 'company_url_direct', 'company_addresses', 'company_num_employees', 'company_revenue', 'company_description', 'skills', 'experience_range', 'company_rating', 'company_reviews_count', 'vacancy_count', 'work_from_home_type']`.

Key observations inside `raw_metadata`:
- `experience_range`: `None` across 1,137 / 1,137 records (100%). Scraper did not populate structured experience ranges from cards.
- `job_level`:
  - `None`: 657 records (100% of Indeed jobs).
  - `'mid-senior level'`: 337 records (LinkedIn).
  - `'not applicable'`: 67 records (LinkedIn).
  - `'entry level'`: 49 records (LinkedIn).
  - `'associate'`: 24 records (LinkedIn).

### 1.4 Critical Edge Cases & Anomalies
1. **String `'nan'` in `date_posted`:**
   - In `regex_audit/run_master_scrape.py` line 38: `date_posted_str = str(date_posted_val)`.
   - When JobSpy returned float `NaN`, `str(float('nan'))` evaluated to the string `'nan'`.
   - Result: Exactly 295 records (all from LinkedIn) contain `date_posted: "nan"`. This is NOT python `None` or `null`.
2. **`"Unknown"` in `location`:**
   - Exactly 19 records (all from LinkedIn) have `location: "Unknown"`.
   - 18 of these have `is_remote: False`.
   - 1 of these (Index 536, TCS `Java Backend Developer`) has `is_remote: True`.
3. **Console Encoding on Windows (`cp1252`):**
   - Printing descriptions directly to standard Windows stdout failed with:
     ```text
     UnicodeEncodeError: 'charmap' codec can't encode character '\u25cf' in position 126: character maps to <undefined>
     ```
   - Job descriptions contain bullet points (`\u25cf` `●`), em dashes, and unicode symbols.
4. **Duplicate Scrapes Across Queries:**
   - 1,137 total raw rows, but only 552 unique URLs and 528 unique `(title, company)` pairs.
   - Example duplicate: `https://in.indeed.com/viewjob?jk=4bf536d7e4af847e` appears 6 times because the raw scrape queried across multiple search terms (`"QA Automation"`, `"Java Developer"`, etc.).
   - This duplication is expected in raw scrape outputs and will be handled by Layer 1 deduplication.

### 1.5 Summary Statistics & Distributions

#### Platform Breakdown
- **indeed**: 657 jobs (57.78%)
- **linkedin**: 480 jobs (42.22%)
- **Total**: 1,137 jobs (100.0%)

#### Employment Type (`job_type`) Breakdown
- **fulltime**: 809 jobs (71.15%)
  - Indeed: 329 jobs
  - LinkedIn: 480 jobs
- **internship**: 328 jobs (28.85%)
  - Indeed: 328 jobs
  - LinkedIn: 0 jobs

#### Work Arrangement (`is_remote`) Breakdown
- **On-site / In-person (`is_remote=False`)**: 989 jobs (86.98%)
  - Indeed: 555 jobs
  - LinkedIn: 434 jobs
- **Remote / WFH (`is_remote=True`)**: 148 jobs (13.02%)
  - Indeed: 102 jobs
  - LinkedIn: 46 jobs

#### Location Breakdown (7 Distinct Values)
| Location String | Source | Count | % of Dataset | Notes |
|---|---|---|---|---|
| `MH, IN` | Indeed | 418 | 36.76% | Maharashtra, India (Pune, Mumbai, etc.) |
| `Bengaluru, Karnataka, India` | LinkedIn | 405 | 35.62% | Bangalore Urban |
| `KA, IN` | Indeed | 239 | 21.02% | Karnataka, India (Bangalore, etc.) |
| `Bengaluru East, Karnataka, India` | LinkedIn | 36 | 3.17% | Sub-region of Bangalore |
| `Unknown` | LinkedIn | 19 | 1.67% | 1 remote (`is_remote=True`), 18 non-remote |
| `Bangalore Urban, Karnataka, India` | LinkedIn | 17 | 1.50% | Sub-region of Bangalore |
| `Bengaluru North, Karnataka, India` | LinkedIn | 3 | 0.26% | Sub-region of Bangalore |
| **Total** | | **1,137** | **100.0%** | |

#### Date Posted Breakdown
| `date_posted` Value | Platform Breakdown | Count | Freshness Status (<72h from 2026-09-29) |
|---|---|---|---|
| `2026-09-29` | Indeed: 479, LinkedIn: 0 | 479 | Fresh (<24h) |
| `nan` (string) | LinkedIn: 295, Indeed: 0 | 295 | Undated / Preserved Freshness |
| `2026-09-28` | Indeed: 136, LinkedIn: 129 | 265 | Fresh (<48h) |
| `2026-09-26` | Indeed: 6, LinkedIn: 32 | 38 | Fresh (~72h boundary) |
| `2026-09-27` | Indeed: 0, LinkedIn: 24 | 24 | Fresh (<48h) |
| `2026-09-10` | Indeed: 8, LinkedIn: 0 | 8 | Stale (>72h) |
| `2026-08-12` | Indeed: 6, LinkedIn: 0 | 6 | Stale (>72h) |
| `2026-09-22` | Indeed: 4, LinkedIn: 0 | 4 | Stale (>72h) |
| `2026-08-05` | Indeed: 4, LinkedIn: 0 | 4 | Stale (>72h) |
| `2026-09-15` | Indeed: 2, LinkedIn: 0 | 2 | Stale (>72h) |
| Other dates (<= 2 each) | Indeed: 12 | 12 | Stale (>72h) |

#### Description Metrics
- Character length: Min = 229, Max = 14,320, Mean = 3,991.8, Median ≈ 3,400.
- Word count: Min = 24, Max = 2,023, Mean = 550.2.
- 0 records have empty descriptions; 0 records have <100 characters.

#### Job Title Semantic Clusters (Top Keyword Overlaps)
| Semantic Cluster | Keywords / Patterns | Jobs Matching | % of Dataset |
|---|---|---|---|
| **General Software Engineering** | Software Engineer, Developer, SDE, Associate Engineer | 848 | 74.6% |
| **QA / Testing / SDET** | QA, SDET, Tester, Testing, Quality, Automation Tester | 273 | 24.0% |
| **Java / Spring / Backend** | Java, Spring, Springboot, Backend | 262 | 23.0% |
| **Full Stack / Web Dev** | Full Stack, Frontend, React, Angular, Node, MERN, MEAN | 252 | 22.2% |
| **Out-of-Scope / Mobile / Niche** | Oracle Apex, JD Edwards, Salesforce, PHP, SAP, Flutter | 98 | 8.6% |
| **AI / ML / Data / LLM** | AI, ML, Machine Learning, Data, NLP, LLM, Computer Vision | 65 | 5.7% |
| **Python / Django / Flask** | Python, Django, Flask, FastAPI | 44 | 3.9% |
| **.NET / C#** | .NET, C#, Dotnet, ASP.NET | 14 | 1.2% |
| **Internship / Trainee Titles** | Intern, Internship, Trainee (in title string) | 8 | 0.7% |

*Note: Individual job titles frequently span multiple clusters (e.g., "Full Stack Developer (Java + React)" matches General Software Engineering, Java/Backend, and Full Stack).*

---

## 2. Logic Chain

1. **Observation 1.1 establishes** that `regex_audit/master_raw_dataset_2026-09-29.jsonl` and `.json` each contain exactly 1,137 records with zero parse failures, zero missing lines, and 100% 1:1 identity.
   - *Inference:* The raw dataset captured during Phase 1 is intact, stable, and ready for ingestion without any re-scraping.

2. **Observation 1.2 & 1.3 establish** that all 1,137 records possess an identical top-level schema of 13 keys with zero null or empty string fields, and an identical `raw_metadata` structure of 33 keys.
   - *Inference:* Downstream consumers do not need defensive `KeyError` try-catch blocks for top-level keys (`job_index`, `id`, `title`, `company`, `location`, `description`, `url`, `source`, `job_type`, `date_posted`, `is_remote`, `raw_metadata`, `scraped_at`).

3. **Observation 1.4(1) establishes** that 295 records from LinkedIn have `date_posted == "nan"` as a string.
   - *Inference:* Standard Python checks like `if record['date_posted'] is None:` will evaluate to `False`. When passing this string into pandas, `pd.to_datetime('nan', errors='coerce', utc=True)` converts it to `pd.NaT`.
   - *Impact on Layer 1:* In `src/scraper.py` line 250, the freshness filter is `stale_mask = combined_df['date_posted'].notna() & (combined_df['date_posted'] < cutoff)`. Because `notna()` is `False` for `NaT`, undated LinkedIn records are intentionally preserved and NOT rejected as stale. Downstream replay scripts must preserve this exact logic.

4. **Observation 1.4(2) establishes** that 19 LinkedIn records have `location == "Unknown"`, of which 1 record (`idx=536`) has `is_remote == True`.
   - *Inference:* In `src/scraper.py` line 267, `loc_mask = combined_df['location'].str.contains(...) | is_remote_mask`. Because `is_remote` is `True` for `idx=536`, it passes Layer 1 location filtering. The remaining 18 records have `is_remote == False` and will be dropped by Layer 1 location filtering unless their titles/descriptions qualify elsewhere.

5. **Observation 1.4(3) establishes** that Windows default console encoding `cp1252` throws `UnicodeEncodeError` when printing raw description strings containing bullets (`\u25cf`).
   - *Inference:* All ingestion and test scripts running on Windows must enforce UTF-8 (`sys.stdout.reconfigure(encoding='utf-8')` and `open(..., encoding='utf-8')`).

6. **Observation 1.4(4) establishes** that 552 unique URLs exist across the 1,137 rows due to multi-query scraping.
   - *Inference:*
     - In **Phase 2 (Layer 1 Replay)**: Step 6 of `apply_pandas_filter()` will drop multi-query duplicate rows (`dropped_dedup`), leaving deduplicated survivors for Layer 2.
     - In **Phases 3 & 4 (Ground Truth Creation)**: As required by `ORIGINAL_REQUEST.md`, `ground_truth.jsonl` must contain **all 1,137 records** (1:1 mapping by `job_index` and `id`), providing an explicit assessment for every captured job.

---

## 3. Caveats

1. **No External Live Validation:** This survey strictly analyzes the static raw dataset stored on disk (`master_raw_dataset_2026-09-29.jsonl` and `.json`) and the local code paths (`src/scraper.py`, `src/scorer.py`). Live network URLs were not pinged to maintain deterministic read-only isolation.
2. **Ground Truth Scope vs Filter Dedup:** Deduplication occurs at step 6 of Layer 1 filtering in `src/scraper.py`. Duplicate records share the same URL and description, so their intrinsic ground-truth suitability (PASS vs FAIL) will be identical, but in replay filtering, subsequent duplicates are dropped under the reason `"Duplicate job (cross-platform overlap)"`. Downstream evaluation scripts must clearly distinguish between a job failing candidate criteria vs being dropped as a duplicate.
3. **No Code Modifications Made:** Per the explorer archetype constraints, zero modifications have been made to repository code (`src/` or `regex_audit/`).

---

## 4. Conclusion

1. **Dataset Verified:** `regex_audit/master_raw_dataset_2026-09-29.jsonl` and `.json` are completely intact, syntax-valid, and contain exactly 1,137 records.
2. **Schema Uniformity:** 100% of records have the complete 13-field top-level schema.
3. **Ingestion Safety:** All workers can safely ingest the dataset using standard JSON/JSONL parsers provided they handle UTF-8 encoding and string `"nan"` dates properly.

---

## 5. Actionable Guidance & Ingestion Protocols

### 5.1 Safe Ingestion Template for Downstream Workers
Subsequent worker scripts (Layer 1 replay, Layer 2 replay, Ground Truth evaluators, Retest scripts) should use this boilerplate:

```python
import sys
import json
from pathlib import Path
import pandas as pd

# 1. Enforce UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 2. Ingest JSONL line-by-line
dataset_path = Path("regex_audit/master_raw_dataset_2026-09-29.jsonl")
records = []
with open(dataset_path, "r", encoding="utf-8") as f:
    for line in f:
        line_str = line.strip()
        if line_str:
            records.append(json.loads(line_str))

assert len(records) == 1137, f"Expected 1137 records, got {len(records)}"

# 3. Clean date_posted for pandas processing
for r in records:
    # Convert string "nan" to None so pandas parses it cleanly to pd.NaT
    if r.get("date_posted") == "nan":
        r["date_posted"] = None
```

### 5.2 Key Mapping Rules for Evaluator Subagents
1. **Always retain `job_index` (0..1136) and `id` (UUID):** Every output file (`layer1_pandas_pass.jsonl`, `layer1_pandas_fail.jsonl`, `layer2_regex_pass.jsonl`, `layer2_regex_fail.jsonl`, `ground_truth.jsonl`) must preserve `job_index` and `id` as the primary key pair to allow deterministic joining and validation.
2. **Date Freshness Handling:**
   - Evaluators and replay filters must treat `date_posted == "nan"` (or `None`) as **fresh** (do not drop). This matches `src/scraper.py` line 241.
   - Jobs with parseable dates older than 72 hours (e.g., 2026-09-10, 2026-08-12) should be flagged as stale if evaluated against the 72-hour freshness window.
3. **Location Handling:**
   - 19 records have `location == "Unknown"`.
   - If `is_remote == True` (e.g. `idx=536`), the job bypasses location rejection.
   - If `is_remote == False`, check if the description explicitly mentions Pune/Mumbai/Bangalore/Remote/WFH before final candidate pass/fail classification.
4. **Duplicate Handling:**
   - `ground_truth.jsonl` requires all 1,137 entries. If a job is duplicate of another, evaluate its intrinsic suitability (e.g. PASS if it matches candidate profile, FAIL if senior/out-of-scope), while Layer 1 replay records whether it was dropped by deduplication.

---

## 6. Verification Method

To independently verify all claims made in this report, run the following command from the repository root:

```powershell
python -c @"
import json
from collections import Counter

jsonl_path = 'regex_audit/master_raw_dataset_2026-09-29.jsonl'
json_path = 'regex_audit/master_raw_dataset_2026-09-29.json'

with open(jsonl_path, 'r', encoding='utf-8') as f:
    jsonl_data = [json.loads(line) for line in f]

with open(json_path, 'r', encoding='utf-8') as f:
    json_data = json.load(f)

assert len(jsonl_data) == 1137, f'JSONL count mismatch: {len(jsonl_data)}'
assert len(json_data) == 1137, f'JSON count mismatch: {len(json_data)}'
assert jsonl_data == json_data, 'JSONL and JSON content mismatch'

expected_keys = {'job_index', 'id', 'title', 'company', 'location', 'description', 'url', 'source', 'job_type', 'date_posted', 'is_remote', 'raw_metadata', 'scraped_at'}
for idx, r in enumerate(jsonl_data):
    assert set(r.keys()) == expected_keys, f'Key mismatch at index {idx}'
    assert r['job_index'] == idx, f'Index sequence mismatch at {idx}'

print('VERIFICATION SUCCESSFUL: 1,137 records verified with 100% schema match.')
"@
```

**Invalidation Conditions:**
- If the command fails with an `AssertionError`, line count is not 1,137 or record parity is compromised.
- If any line raises `json.JSONDecodeError`, file corruption has occurred.
