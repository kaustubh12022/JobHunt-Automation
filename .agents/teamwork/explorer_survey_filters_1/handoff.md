# Handoff Report: Existing Filter Architecture Survey (Layer 1 & Layer 2)

**Author:** explorer_survey_filters_1  
**Target Audience:** orchestrator_1, developer_replay_1, and subsequent audit/rewrite agents  
**Date:** 2026-09-29  
**Status:** Hard Handoff (Investigation Complete)

---

## 1. Observation

Direct code observations from `src/scraper.py`, `src/scorer.py`, `config.yaml`, and empirical execution against `regex_audit/master_raw_dataset_2026-09-29.jsonl`.

### 1.1 Layer 1: Pandas Pre-Filter Architecture (`src/scraper.py`)

The pre-filter is implemented in `apply_pandas_filter(jobs: list[Job], locations: list[str], callbacks=None, test_mode=False, hours_old: int = None) -> list[Job]` spanning lines 209 to 354 of `src/scraper.py`. It converts incoming `Job` objects into a `pandas.DataFrame` (`combined_df`) and applies six discrete filtering passes sequentially.

#### 1.1.1 Empty Description Check
* **File & Lines:** `src/scraper.py:236-238`
* **Source Code:**
  ```python
  # 1. Drop null/empty descriptions
  combined_df = combined_df.dropna(subset=['description'])
  combined_df = combined_df[combined_df['description'].str.strip().astype(bool)]
  ```
* **Mechanism:** Drops any row where `description` is `NaN`/null, then strips whitespace and drops rows evaluating to an empty string.

#### 1.1.2 Freshness Check (>72h Cutoff Logic)
* **File & Lines:** `src/scraper.py:242-258`
* **Source Code:**
  ```python
  if 'date_posted' in combined_df.columns:
      combined_df['date_posted'] = pd.to_datetime(combined_df['date_posted'], errors='coerce', utc=True)
      if hours_old is None:
          config = load_config()
          hours_old = config.get('search', {}).get('hours_old', 72)
      cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=hours_old)

      # Only drop if date is parseable AND older than cutoff
      stale_mask = combined_df['date_posted'].notna() & (combined_df['date_posted'] < cutoff)

      stale_count = stale_mask.sum()
      if stale_count > 0:
          logger.info(f"   [Stale] Dropped {stale_count} stale jobs (older than {hours_old}h)")
          if callbacks and "on_job_dropped" in callbacks:
              for _, row in combined_df[stale_mask].iterrows():
                  callbacks["on_job_dropped"](row.get("title"), row.get("company"), f"Stale (older than {hours_old}h)")
      combined_df = combined_df[~stale_mask]
  ```
* **Critical Mechanism:**
  - `date_posted` is coerced to UTC datetime via `pd.to_datetime(..., errors='coerce', utc=True)`.
  - **Preservation Rule:** Jobs with unparseable or missing (`NaT`/`NaN`) `date_posted` evaluate `stale_mask` as `False` and are **retained**. Only rows with a valid datetime strictly earlier than `cutoff` are dropped.
  - Cutoff evaluates dynamically against current time `pd.Timestamp.now(tz='UTC')`.

#### 1.1.3 Location Regex and Remote Logic
* **File & Lines:** `src/scraper.py:126-206, 260-275`
* **Source Code:**
  ```python
  LOCATION_ALIASES = {
      "pune": [r"\bpune\b", r"\bmaharashtra\b", r"\bmh\b", r"\bin-mh\b", r"\bmh,\s*in\b"],
      "mumbai": [r"\bmumbai\b", r"\bbombay\b", r"\bnavi\s+mumbai\b", r"\bthane\b", r"\bmaharashtra\b", r"\bmh\b", r"\bin-mh\b", r"\bmh,\s*in\b"],
      "bangalore": [r"\bbangalore\b", r"\bbengaluru\b", r"\bkarnataka\b", r"\bka\b", r"\bin-ka\b", r"\bka,\s*in\b"],
      "bengaluru": [r"\bbangalore\b", r"\bbengaluru\b", r"\bkarnataka\b", r"\bka\b", r"\bin-ka\b", r"\bka,\s*in\b"],
      "delhi": [r"\bdelhi\b", r"\bnew\s+delhi\b", r"\bncr\b", r"\bnoida\b", r"\bgurgaon\b", r"\bgurugram\b"],
      "hyderabad": [r"\bhyderabad\b", r"\btelangana\b", r"\bts\b"],
      "chennai": [r"\bchennai\b", r"\btamil\s*nadu\b", r"\btn\b"],
  }

  REMOTE_PATTERNS = [
      r"\bremote\b", r"\bhybrid\b", r"\bwork\s+from\s+home\b",
      r"\bwfh\b", r"\banywhere\b", r"\bpan[- ]?india\b",
  ]

  def build_location_regex(locations: list[str]) -> str:
      patterns = list(REMOTE_PATTERNS)
      for loc in locations:
          loc_clean = loc.strip().lower()
          if loc_clean in LOCATION_ALIASES:
              patterns.extend(LOCATION_ALIASES[loc_clean])
          else:
              matched = False
              for k, aliases in LOCATION_ALIASES.items():
                  if k in loc_clean:
                      patterns.extend(aliases)
                      matched = True
              if not matched:
                  patterns.append(r"\b" + re.escape(loc_clean) + r"\b")
      unique_patterns = list(dict.fromkeys(patterns))
      return "|".join(f"(?:{p})" for p in unique_patterns)
  ```
  Filtering mask in `apply_pandas_filter`:
  ```python
  loc_mask = combined_df['location'].astype(str).str.contains(location_pattern, case=False, na=False) | is_remote_mask
  ```
* **Mechanism:** Checks if `location` matches target cities or state/regional abbreviations (e.g., `mh`, `in-mh`, `ka`), or any remote alias, OR if `is_remote == True`. If both are false, dropped as `"Location mismatch"`.

#### 1.1.4 `matches_senior_title()` Call in Scraper
* **File & Lines:** `src/scraper.py:276-287`
* **Source Code:**
  ```python
  if 'title' in combined_df.columns:
      senior_mask = combined_df['title'].apply(matches_senior_title).astype(bool)
      dropped_df = combined_df[senior_mask]
      dropped_senior = len(dropped_df)
      combined_df = combined_df[~senior_mask]
      if dropped_senior > 0:
          logger.info(f"   [Senior] Dropped {dropped_senior} senior-level jobs (title filter)")
          for _, row in dropped_df.iterrows():
              if callbacks and "on_job_dropped" in callbacks:
                  callbacks["on_job_dropped"](row.get("title"), row.get("company"), "Senior title detected")
  ```
* **Mechanism:** Imports `matches_senior_title` from `src.scorer` and maps it across the `title` column. Any matching row is discarded.

#### 1.1.5 `requires_3_plus_years()` Call in Scraper
* **File & Lines:** `src/scraper.py:288-298`
* **Source Code:**
  ```python
  if 'description' in combined_df.columns:
      exp_mask = combined_df['description'].apply(requires_3_plus_years).astype(bool)
      dropped_exp = exp_mask.sum()
      if dropped_exp > 0:
          logger.info(f"   [Experience] Dropped {dropped_exp} jobs requiring 3+ years of experience")
          if callbacks and "on_job_dropped" in callbacks:
              for _, row in combined_df[exp_mask].iterrows():
                  callbacks["on_job_dropped"](row.get("title"), row.get("company"), "High experience required")
      combined_df = combined_df[~exp_mask]
  ```
* **Mechanism:** Imports `requires_3_plus_years` from `src.scorer` and applies it across the `description` column. Rows requiring 3+ years candidate experience are discarded.

#### 1.1.6 Deduplication Logic (URL + Company/Title)
* **File & Lines:** `src/scraper.py:56-96, 299-333`
* **Source Code:**
  ```python
  # 6a. Normalize URLs and deduplicate by normalized URL
  if 'url' in combined_df.columns:
      combined_df['normalized_url'] = combined_df['url'].apply(normalize_url)
      has_url_mask = combined_df['normalized_url'].astype(str).str.strip().astype(bool)
      with_url = combined_df[has_url_mask].drop_duplicates(subset=['normalized_url'], keep='first')
      without_url = combined_df[~has_url_mask]
      combined_df = pd.concat([with_url, without_url], ignore_index=True)

  # 6b. Deduplicate by (clean_title, company) ONLY when company is known
  if 'title' in combined_df.columns and 'company' in combined_df.columns:
      unknown_companies = {'', 'unknown', 'none', 'nan', 'null', 'n/a'}
      is_unknown = (
          combined_df['company'].isna() |
          combined_df['company'].fillna('').astype(str).str.strip().str.lower().isin(unknown_companies)
      )
      is_known_company = ~is_unknown

      known_df = combined_df[is_known_company].copy()
      unknown_df = combined_df[~is_unknown].copy()

      known_df['clean_title_dedup'] = known_df['title'].astype(str).str.strip().str.lower()
      known_df['clean_company_dedup'] = known_df['company'].astype(str).str.strip().str.lower()
      known_deduped = known_df.drop_duplicates(subset=['clean_title_dedup', 'clean_company_dedup'], keep='first')

      combined_df = pd.concat([known_deduped, unknown_df], ignore_index=True)
      combined_df = combined_df.drop(columns=['clean_title_dedup', 'clean_company_dedup', 'normalized_url'], errors='ignore')
  ```
* **URL Normalization Function (`normalize_url`, L63-96):**
  - Strips tracking parameters: `TRACKING_PARAMS = {'refid', 'trackingid', 'tracking_id', 'trk', 'trkcampaign', 'midtoken', 'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid', '_ga', '_gl'}` and any parameter starting with `utm_`.
  - Removes trailing slashes and fragments (`#...`).
  - Preserves functional query params (e.g. `jk` for Indeed).
* **Two-Pass Deduplication Rule:**
  - Pass A: Drops duplicates on `normalized_url` (keeping `first`). Empty/missing URLs are bypassed.
  - Pass B: For rows where `company` is NOT in `{'', 'unknown', 'none', 'nan', 'null', 'n/a'}`, normalizes `title` and `company` to lowercase stripped strings and deduplicates (keeping `first`). Rows with unknown companies are never dropped against each other in Pass B.

---

### 1.2 Layer 2: Scorer Regex Filter Architecture (`src/scorer.py`)

Layer 2 is invoked inside `score_jobs(jobs: list[Job], ...)` at `src/scorer.py:337-352`:
```python
# 2. Filter irrelevant and senior jobs synchronously first (zero wasted AI calls)
relevant_jobs = []
skipped_irrelevant = 0

for job in fresh_jobs:
    if (
        matches_senior_title(job.title)
        or matches_out_of_scope_role(job.title, job.description)
        or requires_3_plus_years(job.description)
        or not is_relevant_jd(job.description, job.title)
    ):
        skipped_irrelevant += 1
        continue
    relevant_jobs.append(job)
```

#### 1.2.1 `matches_senior_title(title: str)`
* **File & Lines:** `src/scorer.py:137-188`
* **Logic & Patterns:**
  1. **Senior Keywords Pattern (`L148-153`):**
     ```python
     senior_keywords_pattern = (
         r'\b(?:senior|lead|manager|principal|director|head|vp|president|experienced|'
         r'architect|staff|expert|ii|iii|iv|v|vi|vii|viii|level\s*[2-9]|l[2-9])\b|\bsr[\.,\s]|\bsr$'
     )
     ```
     Matches:
     - Explicit seniority titles (`senior`, `lead`, `principal`, `architect`, etc.).
     - Roman numerals (`ii` through `viii`, e.g. `Software Engineer II`).
     - Level indicators (`level 2-9`, `l2-9`).
     - Prefix abbreviations: `sr.`, `sr,`, `sr `, or string ending with `sr`.
  2. **Experience Ranges in Title (`L157-161`):**
     ```python
     range_title_pat = r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?\.?|yoe)'
     # lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5 -> return True
     ```
     Preserves `0-2`, `0-3`, `1-3`, `2-3`. Drops `2-4`, `3-5`, `5-10`, etc.
  3. **Single Number Experience in Title (`L164-171`):**
     ```python
     single_title_pat = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?|yoe)'
     ```
     Drops if `has_plus and num >= 3`, or if `num >= 3` and not preceded by `0-`, `1-`, or `2-`.
  4. **Word-Based Experience in Title (`L174-187`):**
     Maps `three` through `twelve` to 3..12. If number >= 3 and not preceded by `zero/one/two/0/1/2 to/-`, returns `True`.

#### 1.2.2 `matches_out_of_scope_role(title, description)` and `OUT_OF_SCOPE_STACK_PATTERN`
* **File & Lines:** `src/scorer.py:81-97`
* **Source Code:**
  ```python
  OUT_OF_SCOPE_STACK_PATTERN = re.compile(
      r'\b(?:php|laravel|ruby|rails|ios|swift|swiftui|android|kotlin|flutter|react\s+native|salesforce|apex|sap|abap|drupal|magento|wordpress)\b',
      re.IGNORECASE
  )

  def matches_out_of_scope_role(title: str = "", description: str = "") -> bool:
      if title and OUT_OF_SCOPE_STACK_PATTERN.search(title):
          return True
      if description and OUT_OF_SCOPE_STACK_PATTERN.search(description):
          return True
      return False
  ```
* **Mechanism:** Word-boundary match (`\b`) against 17 prohibited technologies across both `title` and `description`.
* **Important Behavior:** Checks the **entire body** of `description`. If a company mentions an out-of-scope technology as an integration point, minor dependency, or secondary asset (e.g. "QA testing an app with Salesforce integrations" or "Java or Kotlin backend"), the job is dropped immediately.

#### 1.2.3 `requires_3_plus_years(desc: str)`
* **File & Lines:** `src/scorer.py:191-301`
* **Logic & Execution Pipeline:**
  - **Step 1: Third-Party & Company Experience Stripping (`L204-227`):**
    Splits description by sentence punctuation/newlines (`(?<=[.!?\n])\s*`). Discards any sentence matching any of 15 prefixes:
    `'(?:our|the)\s+team\s+(?:has|have|with|of)'`, `'(?:work|working)\s+(?:with|alongside|beside|among)'`, `'(?:join|joining)\s+(?:a\s+)?team\s+(?:of|with)'`, `'(?:founded|established|started|operating|running)\s+(?:in|since|for|with)'`, `'(?:we\s+have|company\s+has|firm\s+has)\s+(?:over|more\s+than|been)'`, `'(?:our\s+company|our\s+firm|our\s+organisation)\s+(?:has|have)'`, `'colleagues?\s+(?:with|who\s+have)'`, `'mentors?\s+(?:with|who\s+have)'`, `'mentorship\s+from'`, `'(?:learn|learning)\s+from'`, `'(?:combined|collective|total)\s+experience'`, `'(?:history|heritage|industry)\s+(?:of|spanning)'`, `'(?:team|group|pool)\s+of\s+(?:engineers?|developers?|professionals?)\s+with'`, `'(?:senior\s+)?engineers?\s+(?:who\s+have|with\s+over)'`, `'in\s+\d{4}\s+with\s+\d+\s+years'`.
    Remaining sentences are joined into `candidate_text`.
  - **Step 2: Experience Range Checking (`L229-253`):**
    Matches `({num_tokens})\s*(?:\([^\)]+\)\s*)?{range_sep}\s*({num_tokens})\s*(?:\([^\)]+\)\s*)?(?:\+|or more|plus)?\s*(?:years?|yrs?\.?|yoe)\b`.
    Rule: `if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5: return True`.
    Then all ranges are replaced with `' '` via `re.sub(range_pattern, ' ', candidate_text)` to prevent matching the trailing digit in subsequent single-number checks.
  - **Step 3: Plus Patterns (`L254-260`):**
    `r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than|plus)\s*(?:years?|yrs?\.?|yoe)'` -> drops if `3 <= num <= 25`.
  - **Step 4: Minimum Requirement (`L261-267`):**
    `r'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?\.?)?'` -> drops if `3 <= num <= 25`.
  - **Step 5: Contextual Experience Pattern with Negative Lookahead Window (`L268-277`):**
    `r'(?<![-\u2013\d])\b(\d+)\s*(?:years?|yrs?\.?)\s*(?:of\s+)?(?:experience|exp|hands[- ]on|relevant|background|industry|work)?'`
    **Exclusion Rule:** Inspects a `[-20, +20]` character slice around match for keywords: `degree|bachelor|diploma|bond|agreement|contract|commitment|lock-in|warranty|course`. If found, ignores the match; otherwise drops if `3 <= num <= 25`.
  - **Step 6: Abbreviated Shorthand (`L278-284`):**
    `r'(?<![-\u2013\d])\b(\d+)\s+yrs?\b'` -> drops if `3 <= num <= 25`.
  - **Step 7: Word-Based Experience (`L285-299`):**
    Scans for words `three` through `twelve`. If word >= 3 and preceding text does not contain `zero/one/two/0/1/2`, returns `True`.

#### 1.2.4 `is_relevant_jd(description, title)`, `DOMAIN_ANCHORS`, and `TECH_TOOLS`
* **File & Lines:** `src/scorer.py:57-70, 114-135`
* **Source Code:**
  ```python
  DOMAIN_ANCHORS = [
      'java', 'python', 'qa', 'selenium', 'automation',
      '.net', 'c#', 'csharp', 'asp.net', 'spring', 'full stack', 'fullstack',
      'sdet', 'quality assurance', 'postman', 'pytest', 'junit',
      'playwright', 'cypress', 'tester', 'manual testing', 'automation testing',
      'software testing', 'api testing', 'test automation', 'test case', 'test cases',
      'test suite', 'test plan', 'test engineer'
  ]
  TECH_TOOLS = [
      'spring', 'sql', 'pytest', 'postman', 'junit', 'rest api', 'api', 'react',
      'javascript', 'html', 'css', 'mysql', 'mongodb', 'docker', 'git', 'jdbc',
      'azure', 'c#', 'java', 'python', 'selenium', 'automation', 'database',
      'oops', 'oop', 'microservices', 'django', 'flask', 'node', 'test', 'qa'
  ]

  def is_relevant_jd(description: str, title: str = "") -> bool:
      if not description or not isinstance(description, str):
          return False
      desc_lower = description.lower()

      # Reject out-of-scope stacks immediately
      if OUT_OF_SCOPE_STACK_PATTERN.search(desc_lower):
          return False
      if title and OUT_OF_SCOPE_STACK_PATTERN.search(title):
          return False

      has_anchor = any(kw in desc_lower for kw in DOMAIN_ANCHORS)
      has_tool = any(kw in desc_lower for kw in TECH_TOOLS)
      return has_anchor and has_tool
  ```
* **Critical Architectural Deficiencies Observed:**
  1. **Title Ignored for Domain Anchors:** `has_anchor` only inspects `desc_lower`. If a job title is `"Full Stack Developer"` or `"Java Developer"`, but the JD description itself uses variant phrasing, the title is ignored for relevance qualification!
  2. **Substring Matching without Word Boundaries:** Checks `kw in desc_lower`. While this works for phrases, short tokens like `'qa'`, `'api'`, and `'node'` can match inside ordinary words (e.g. `'rapid'` contains `'api'`, `'fastest'` contains `'test'`).
  3. **Missing Critical Target Domains:** `DOMAIN_ANCHORS` does NOT contain:
     - MERN stack anchors: `'mern'`, `'express'`, `'mongodb'`, `'node.js'`, `'nodejs'`, `'react'`
     - AI / ML anchors: `'ai'`, `'ml'`, `'machine learning'`, `'llm'`, `'genai'`, `'generative ai'`, `'deep learning'`, `'nlp'`, `'agentic'`
     - General software engineering terms: `'software engineering'`, `'software engineer'`, `'backend'`
  4. **Markdown Escaping Fracture:** Many scraped JDs contain markdown escaped hyphens, e.g. `full\-stack`. Because `DOMAIN_ANCHORS` checks `'full stack'` and `'fullstack'`, the string `'full\-stack'` fails substring matching!

---

### 1.3 Empirical Simulation Results on `master_raw_dataset_2026-09-29.jsonl`

A dry-run python script executing the exact filtering code across all 1,137 jobs produced the following deterministic numbers:

```
Total Master Raw Jobs Loaded: 1,137

=== Layer 1: Pandas Pre-Filter ===
  [Empty Description]:     0 dropped
  [Stale (>72h)]:         74 dropped
  [Location Mismatch]:    16 dropped
  [Senior Title]:        516 dropped
  [Experience 3+ Years]: 356 dropped
  [Duplicate (URL/Title)]: 102 dropped
  ---------------------------------
  Total Layer 1 Dropped: 1,064 jobs
  Layer 1 Pass (Survivors): 73 jobs (Accounting: 1,064 + 73 = 1,137)

=== Layer 2: Scorer Regex Filter (executed on 73 Layer 1 survivors) ===
  [Senior Title Re-check]:  0 dropped (already eliminated in L1)
  [Out of Scope Role]:     12 dropped (PHP, Flutter, Salesforce, Kotlin, etc.)
  [Experience Re-check]:    0 dropped (already eliminated in L1)
  [Irrelevant JD]:          3 dropped (Capgemini Software Engineer, BTPL C++, nan Full Stack)
  ---------------------------------
  Total Layer 2 Dropped:  15 jobs
  Layer 2 Pass (Survivors): 58 jobs (Accounting: 15 + 58 = 73)
```

---

## 2. Logic Chain

From the observations above, we establish the step-by-step reasoning leading to the deterministic replay design and filter audit findings:

1. **Sequential Hierarchy:** In production, Layer 1 runs first during the scraping cycle (`src/scraper.py:575`), and Layer 2 runs subsequently when `score_jobs()` is invoked (`src/scorer.py:343`). Therefore, Layer 2 is **strictly downstream** of Layer 1. Layer 2 never operates on the 1,137 raw jobs directly; it operates solely on the 73 jobs that survived Layer 1.
2. **Redundancy Between Layers:** Observations in 1.1.4, 1.1.5 vs 1.2.1, 1.2.3 reveal that `matches_senior_title()` and `requires_3_plus_years()` are executed in BOTH Layer 1 and Layer 2 using the exact same underlying functions. In our empirical test, zero jobs failed `matches_senior_title` or `requires_3_plus_years` in Layer 2 because Layer 1 had already pruned them.
3. **Primary Functions of Layer 2:** Layer 2 uniquely contributes two functional gates not present in Layer 1:
   - `matches_out_of_scope_role()` (checking 17 prohibited tech tokens)
   - `is_relevant_jd()` (ensuring at least 1 domain anchor and 1 tech tool)
4. **Determinism and Reference Time Sensitivity:** In Observation 1.1.2, `apply_pandas_filter` calculates `cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=hours_old)`.
   - In `master_raw_dataset_2026-09-29.jsonl`, all jobs were scraped at `2026-09-29T14:05:55Z`.
   - If a replay script relies on dynamic system time (`now()`), executing the replay days later would cause `cutoff` to shift forward, artificially marking fresh jobs as stale and corrupting reproducibility.
   - **Deduction:** The replay script MUST pin the reference timestamp to the dataset's collection timestamp (`2026-09-29T14:05:55Z` or max `scraped_at`).
5. **Deduplication Dependency on Row Ordering:** Observation 1.1.6 demonstrates that URL and `(title, company)` deduplication use `keep='first'`. Therefore, preserving the exact sequential index (`job_index` 0 to 1136) is mandatory to ensure identical deduplication decisions.
6. **False Negative Root Causes in Layer 2:**
   - As observed in Section 1.2.4, `TITLE: Full Stack Developer` requiring React, Node, MongoDB, Next.js was dropped with `irrelevant_jd` because `DOMAIN_ANCHORS` lacks MERN/Node keywords, the title was ignored, and markdown escaping `full\-stack` evaded `'full stack'`.
   - `TITLE: Software Engineer` at Capgemini was dropped because generic software engineering terms are not recognized by `DOMAIN_ANCHORS` and `TECH_TOOLS`.
   - `TITLE: Java or Kotlin & React.js Developer` at Capgemini was dropped by `matches_out_of_scope_role` because `'kotlin'` triggered `OUT_OF_SCOPE_STACK_PATTERN`, even though Java and React are core candidate target skills.

---

## 3. Caveats

1. **Scope of Replay:** The filter replay is purely deterministic regex and logic testing. AI scoring (DeepSeek), prompt token caching, resume tailoring, and Supabase database writes are strictly out of scope and will not be invoked.
2. **Missing `date_posted` Handling:** 295 records in `master_raw_dataset_2026-09-29.jsonl` have `null`/`NaN` date posted. Per `src/scraper.py:250`, these are intentionally preserved as fresh. The replay script must adhere strictly to this behavior.
3. **Cross-Platform Deduplication Order:** Because deduplication occurs in two distinct passes (first on `normalized_url`, then on `(clean_title, clean_company)`), the order of operations in `apply_pandas_filter` must be replicated identically.
4. **Callbacks Interface:** Production `apply_pandas_filter` invokes `callbacks["on_job_dropped"]` for only 4 out of 6 rejection categories and omits pattern details. The replay script must implement its own granular auditing harness to capture full metadata and regex matches for every dropped job.

---

## 4. Conclusion

1. The filtering architecture consists of two cleanly separated layers:
   - **Layer 1 (Pandas Pre-Filter):** 6-step pipeline (Empty desc -> 72h Freshness -> Location/Remote -> Senior Title -> Experience 3+ -> Deduplication). Prunes 1,137 jobs down to 73 survivors (1,064 dropped).
   - **Layer 2 (Scorer Regex Filter):** 4-step pipeline (Senior Title -> Out-of-Scope Role -> Experience 3+ -> Relevance Check). Prunes 73 survivors down to 58 final jobs (15 dropped).
2. The deterministic replay script can be constructed as a zero-dependency, zero-LLM python script (`regex_audit/run_replay.py`) that reads `regex_audit/master_raw_dataset_2026-09-29.jsonl`, pins the reference time to `2026-09-29T14:05:55Z`, and writes the 4 required JSONL files:
   - `regex_audit/filter_results/layer1_pandas_pass.jsonl` (73 records)
   - `regex_audit/filter_results/layer1_pandas_fail.jsonl` (1,064 records)
   - `regex_audit/filter_results/layer2_regex_pass.jsonl` (58 records)
   - `regex_audit/filter_results/layer2_regex_fail.jsonl` (15 records)
3. Key areas identified for the Phase 5 audit and Phase 6 rewrite (`scorer_v2.py`):
   - Expand `DOMAIN_ANCHORS` and `TECH_TOOLS` to include MERN (Node, Express, MongoDB, React) and AI/ML/LLM keywords.
   - Normalize markdown escapes (`full\-stack` -> `full-stack`) prior to keyword matching.
   - Allow `is_relevant_jd()` to consider job `title` when evaluating domain anchors.
   - Refine `OUT_OF_SCOPE_STACK_PATTERN` so that secondary or optional mentions in descriptions do not discard valid target roles.

---

## 5. Verification Method

### 5.1 Independent Replay Verification Command
Run the following PowerShell command in the project root to independently verify the filter numbers and logic against `regex_audit/master_raw_dataset_2026-09-29.jsonl`:

```powershell
python -c "
import json
import pandas as pd
from src.scraper import apply_pandas_filter
from src.scorer import matches_senior_title, requires_3_plus_years, matches_out_of_scope_role, is_relevant_jd
from src.models import Job

jobs = []
with open('regex_audit/master_raw_dataset_2026-09-29.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        j = Job(id=d['id'], title=d['title'], company=d['company'], location=d['location'], description=d['description'], url=d['url'], source=d['source'], job_type=d['job_type'])
        j.date_posted = d.get('date_posted')
        j.is_remote = d.get('is_remote', False)
        jobs.append(j)

l1_survivors = apply_pandas_filter(jobs, ['Pune', 'Mumbai', 'Bangalore'], hours_old=72)
assert len(l1_survivors) == 73, f'Expected 73 L1 survivors, got {len(l1_survivors)}'

l2_survivors = []
for j in l1_survivors:
    if not (matches_senior_title(j.title) or matches_out_of_scope_role(j.title, j.description) or requires_3_plus_years(j.description) or not is_relevant_jd(j.description, j.title)):
        l2_survivors.append(j)

assert len(l2_survivors) == 58, f'Expected 58 L2 survivors, got {len(l2_survivors)}'
print('VERIFICATION SUCCESSFUL: 1137 -> L1 (73) -> L2 (58)')
"
```

### 5.2 Files to Inspect
- `src/scraper.py` (lines 56-96, 126-206, 209-354)
- `src/scorer.py` (lines 56-97, 114-188, 191-301, 337-352)
- `regex_audit/master_raw_dataset_2026-09-29.jsonl`

### 5.3 Invalidation Conditions
This survey and its replay blueprint will be invalidated if:
1. `src/scraper.py` or `src/scorer.py` is modified before replay execution.
2. The reference cutoff timestamp is computed dynamically using a date significantly past `2026-09-29`, shifting stale job thresholds.
3. The dataset `regex_audit/master_raw_dataset_2026-09-29.jsonl` is regenerated or modified.
