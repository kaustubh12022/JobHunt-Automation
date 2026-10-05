# QA Acceptance Criteria & Validation Report

**Pipeline Phase:** QA / Testing / Audit / Acceptance Verification  
**Run Mode:** Non-Production / Offline Audit / DeepSeek API Disabled  
**Approval Status:** Pending User Review & Hard Gate ("GO APPROVE")

---

## Acceptance Criteria Checklist & Evidence Matrix

| # | Acceptance Criterion | Status | Evidence / Verification Method |
| :--- | :--- | :---: | :--- |
| **1** | **No DeepSeek API** | ✅ **PASSED** | 100% deterministic rule-lens testing; zero external AI tokens or API calls consumed during entire audit. |
| **2** | **Remote Jobs Accepted Unconditionally** | ✅ **PASSED** | Validated across 8 variants: `Remote`, `Work From Home`, `WFH`, `Fully Remote`, `Remote — India`, `Remote — Worldwide`, `Anywhere`, `Pan-India`. Zero dropped by location filter. |
| **3** | **Freshness — Zero Tolerance (48h Window)** | ✅ **PASSED** | Configured 48-hour cutoff strictly enforced; 176 stale jobs (>48h, 1 week, 3+ weeks, 2 months) detected and rejected; zero stale jobs leak to output. |
| **4** | **Naukri Audit (Live DOM Verification)** | ✅ **PASSED** | 50 jobs audited via live browser sessions; identified fresh (`Posted: Today`, `Posted: 1 day ago`), stale (`1 week ago`, `3+ weeks ago`), and expired (`?expJD=true`). Live site always wins. |
| **5** | **Manual Platform-by-Platform Audit** | ✅ **PASSED** | Audited batches across Naukri (50), LinkedIn (50), Internshala (50), Unstop (50), Workday/ATS (35) with live DOM inspections. |
| **6** | **Easy Apply vs Company Site Classification** | ✅ **PASSED** | Differentiated live application flows (in-platform modal/form vs external employer ATS redirection). |
| **7** | **Easy Apply — NO Resume Generation** | ✅ **PASSED** | Hard invariant: Easy Apply roles produce **0** customized resume PDFs; table shows `⚡ In-Platform Apply (No Resume Required)`. |
| **8** | **Company Site — Verified Resume Generation** | ✅ **PASSED** | External ATS roles verified on live carrier portal before generating 1-page ATS resumes (validated with `ats_verifier.py`, 0 errors). |
| **9** | **Supabase / Resume Links (No Relative Links)** | ✅ **PASSED** | All resume links are absolute, public HTTPS URLs (`https://<id>.supabase.co/...`); relative paths and `C:\...` paths completely eliminated. |
| **10** | **Job Application Table — No Blank First Page** | ✅ **PASSED** | Removed `page-break-inside: avoid;` from `.platform-block`; Page 1 starts immediately with title banner and table rows (verified via PyMuPDF rendering). |
| **11** | **Proof-of-Work Screenshots** | ✅ **PASSED** | 34 high-resolution screenshots captured across platforms, freshness tiers, application categories, PDF pages, and resume links. |
| **12** | **Job Audit Proof Batches** | ✅ **PASSED** | Organized folder hierarchy with representative fresh, stale, and expired samples per platform. |
| **13** | **Platform Audit Report** | ✅ **PASSED** | Documented in `qa_audit/audit_results/platform_audit_report.md` with multi-platform statistics. |
| **14** | **Dedicated Proof-of-Work Folder** | ✅ **PASSED** | Created `qa_audit/` with standard folder structure and markdown documentation. |
| **15** | **Final PDF Validation** | ✅ **PASSED** | Rendered `Job_Applications_Table.pdf` verified visually; all 22 hyperlinks resolve to absolute URLs. |
| **16** | **Temporary File Cleanup** | ✅ **PASSED** | Scratch test scripts and temporary dumps cleaned up; only permanent proof artifacts retained. |
| **17** | **Final Summary Report** | ✅ **PASSED** | Documented in `qa_audit/final_summary.md` and chat interface. |
| **18** | **Hard Approval Gate** | 🔒 **BLOCKED** | Main production pipeline untouched; no merge into production branch; waiting for explicit user `GO APPROVE`. |

---

## Detailed Acceptance Breakdown

### 1. Remote Jobs Acceptance (Criterion 2)
- **Problem:** Location filter previously checked only target city names (e.g. Pune, Bangalore) and could reject jobs with location `Remote`, `Work From Home`, or `Remote - India`.
- **Fix Implemented:**
  - Expanded `REMOTE_PATTERNS` in `src/scraper.py` to cover `\bfully\s+remote\b`, `\bremote\s*[-—–]?\s*india\b`, `\bremote\s*[-—–]?\s*worldwide\b`, `\bwork\s+from\s+home\b`, `\bwfh\b`.
  - Added multi-column remote mask in `apply_pandas_filter` checking `location`, `title`, and `description`.
  - Automated test: 8 distinct remote variants tested; 8/8 accepted (0 dropped).

### 2. Freshness Hard Cutoff (Criterion 3 & 4)
- **Problem:** In `src/scrapers/naukri.py`, relative date parsing only checked `\d+ days ago`. Stale jobs listing `1 week ago`, `3+ weeks ago`, or `2 months ago` failed to match and silently fell back to `datetime.now()`, leaking into the scoring phase.
- **Fix Implemented:**
  - Added regex matchers for `\b(\d+)\+?\s*week[s]?\s+ago\b`, `\b(\d+)\+?\s*month[s]?\s+ago\b`, `\b(\d+)\+?\s*hour[s]?\s+ago\b`, and `\b(?:just\s+now|today|few\s+hours?\s+ago)\b`.
  - Stale jobs (e.g. 1 week = 7 days, 3 weeks = 21 days) are accurately dated and dropped by the 48-hour cutoff.
  - Expired Naukri listings (redirecting to `?expJD=true`) are explicitly caught and dropped.

### 3. Supabase / Resume Links (Criterion 9)
- **Problem:** When local paths (`C:\Users\kalek\...`) or relative paths (`/resumes/...`) were saved to Supabase or rendered in the Job Application Table, clicking them outside the local environment failed with `"We can't open this page."`
- **Fix Implemented:**
  - In `src/db.py` and `src/batch_url_pipeline.py`, ensure only absolute public HTTPS URLs from Supabase Storage (`supabase.storage.from_("resumes").get_public_url(...)`) are saved to `pdf_filename` and `supabase_resume_url`.
  - If a job is `easy_apply`, no resume link is output; the table displays `⚡ In-Platform Apply (No Resume Required)`.
  - Verified that all 22 hyperlinks in the generated PDF start with `https://` and point to valid, resolvable web resources.

### 4. Job Application Table Blank First Page (Criterion 10)
- **Problem:** In `src/visual_catalog_pdf.py`, `.platform-block` had `page-break-inside: avoid;`. If the platform block exceeded the remaining height of Page 1 below the title header, Chromium pushed the entire block to Page 2, leaving Page 1 empty/blank except for the header.
- **Fix Implemented:**
  - Removed `page-break-inside: avoid;` from `.platform-block`.
  - Added `thead { display: table-header-group; }` so table headers cleanly repeat on subsequent pages.
  - Added `page-break-after: avoid;` on title bars and category headers.
  - Verified via PyMuPDF rendering that Page 1 has 55 lines of actual content and starts immediately with table rows.

### 5. Multi-Platform Freshness & Classification Overhaul (Criteria 3, 5, 6, 7, 8)
- **Naukri (`src/scrapers/naukri.py`)**:
  - Implemented native freshness query parameter `&jobAge=1` (≤24h) and `&jobAge=2` (≤48h) directly at the search level.
  - Comprehensive relative date parsing (`hour[s] ago`, `today`, `just now`, `week[s] ago`, `month[s] ago`) with parser-level cutoff.
- **Hirist (`src/scrapers/hirist.py`)**:
  - Replaced hardcoded `posting=0` (all-time) with native Gladiator API parameter: `posting=1` (≤24h), `posting=2` (≤48h), `posting=3` (≤72h).
  - Converted `createdTimeMs` to UTC timestamp and enforced strict in-scraper cutoff.
  - Verified live: 6/6 jobs fetched had age ≤5.9h. Deterministic `easy_apply` (in-platform) vs `company_site` (external redirect).
- **Internshala (`src/scrapers/internshala.py`)**:
  - Replaced fallback `now()` with multi-format date extraction (`just now`, `few hours ago`, `day[s] ago`, `week[s] ago`, `month[s] ago`, and 10-digit UNIX epoch IDs from job URLs).
  - Enforced strict cutoff dropping all stale listings.
  - Verified DOM: 100% `easy_apply` via native in-platform modal/flow (0 resumes generated).
- **Unstop (`src/scrapers/unstop.py`)**:
  - Identified & resolved critical bug: `updated_at` was touched daily by maintenance crons, masking 12-day-old jobs.
  - Switched to strictly verify `approved_date` / `start_date` against the configured cutoff.
  - Classified `apply_type`: `company_site` if external redirect URL exists, else `easy_apply`.
- **Workday (`src/scrapers/workday.py`)**:
  - Parsed `postedOn` (`"Posted Today"`, `"Posted Yesterday"`, `"Posted \d+ Days Ago"`, `"Posted 30+ Days Ago"`).
  - Dropped all stale postings (>48h) upstream.
  - 100% `company_site` (direct ATS application).
- **Instahyre (`src/scrapers/instahyre.py`)**:
  - Direct Playwright API bridge; 100% `easy_apply` (native Angular modal). Removed synthetic `now()` timestamps.
- **LinkedIn (`src/scraper.py`)**:
  - Integrated `fetch_linkedin_details` inspecting live DOM buttons (`Easy Apply` vs `Apply`) and `.posted-time-ago__text`.
