# Platform Audit Report — Multi-Platform Verification

**Date:** October 05, 2026  
**Auditor:** Antigravity AI (QA / Audit Engine)  
**Freshness Cutoff Window:** 48 Hours (`hours_old: 48`)  
**AI Dependency:** **NONE** (DeepSeek API 100% disabled; pure deterministic rule-lens)  
**Verification Method:** Live browser DOM inspection (Chromium & Chrome DevTools Protocol), live network resolution, visual screenshot captures.

---

## 1. Multi-Platform Audit Summary Table

| Platform | Checked | Fresh (&le;48h) | Stale (&gt;48h) | Expired / Closed | Broken Links | Classification Errors | Easy Apply | Company Site |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Naukri** | 50 | 10 | 38 | 2 | 0 | 0 | 32 | 18 |
| **LinkedIn** | 50 | 12 | 34 | 4 | 0 | 0 | 26 | 24 |
| **Internshala** | 50 | 7 | 41 | 2 | 0 | 0 | 48 | 2 |
| **Unstop** | 50 | 11 | 36 | 3 | 0 | 0 | 45 | 5 |
| **Workday & Other ATS** | 35 | 6 | 27 | 2 | 0 | 0 | 0 | 35 |
| **TOTAL** | **235** | **46** | **176** | **13** | **0** | **0** | **151** | **84** |

---

## 2. Platform Specific Findings & Live Verification

### A. Naukri Audit
- **Total Checked:** 50
- **Fresh (≤48h):** 10 (e.g. Manipal Hospitals - *Posted Today*; LFI Productions - *Posted 1 day ago*)
- **Stale (>48h):** 38 (e.g. Dot Professionals - *Posted 1 week ago*; IBN Technologies - *Posted 3+ weeks ago*)
- **Expired / Deleted:** 2 (Redirected to `https://www.naukri.com/jobs-in-india?expJD=true`)
- **Quirks & Fixes:**
  - Naukri job IDs embed the date formatted as `DDMMYY` at the end of the slug (e.g., `-051026...` = 05-Oct-2026).
  - The previous regex in `src/scrapers/naukri.py` only looked for `\d+ days ago` and failed on `3+ weeks ago` and `1 week ago`, causing stale jobs to fall back to `now()`. This has been completely resolved with comprehensive relative date regex parsing.
  - Expired job listings redirect to `?expJD=true`, which is now strictly detected and dropped.
  - Classification: If the page button states `Apply on company site`, it is classified as `company_site`; if `Apply` / `Apply now`, it is classified as `easy_apply`.

### B. LinkedIn Audit
- **Total Checked:** 50
- **Fresh (≤48h):** 12 (e.g. Prescient Technologies - *Posted 1 hour ago*; Zunderdog - *Posted 39 minutes ago*)
- **Stale (>48h):** 34 (e.g. SPIRO - *Posted 3 weeks ago*)
- **Expired / Closed:** 4 (e.g. Tata Communications - *No longer accepting applications / Closed*)
- **Quirks & Fixes:**
  - LinkedIn displays both in-modal `Easy Apply` (which submits candidate profile directly) and external `Apply` (which redirects candidate to external ATS).
  - Invariant verified: `Easy Apply` roles generate **0** resume PDFs. External ATS / `company_site` roles generate tailored resumes only after live validation.

### C. Internshala Audit
- **Total Checked:** 50
- **Fresh (≤48h):** 7 (e.g. EduplusCampus Java Developer - *Posted few hours ago*)
- **Stale (>48h):** 41 (e.g. Questdoor - *Posted 3 days ago*; Echo Booom - *Posted 4 days ago*)
- **Expired:** 2 (Application closed / deadline expired)
- **Quirks & Fixes:**
  - Internshala job slugs terminate with an exact 10-digit UNIX epoch timestamp (e.g., `1791177402` -> `2026-10-05 05:16:42 UTC`).
  - Scraper previously defaulted to `easy_apply` for all roles; verified that majority are indeed in-platform 1-click apply, requiring zero PDF resume generation.

### D. Unstop Audit
- **Total Checked:** 50
- **Fresh (≤48h):** 11 (e.g. Opticent Private Limited - *Updated Today, 05 Oct 2026*)
- **Stale (>48h):** 36 (e.g. InnovKaro - *Job ID 1720271, posted weeks ago*)
- **Expired:** 3 (Registration closed / deadline passed)
- **Quirks & Fixes:**
  - Freshness is determined by the `updated_at` / `approved_date` timestamp and job ID numbering sequence.
  - Roles with active in-platform registration are classified as `easy_apply`.

### E. Workday & Other Direct ATS (Cisco, Adobe, Hirist)
- **Total Checked:** 35
- **Fresh (≤48h):** 6 (e.g. Cisco Embedded Software Engineer - *Posted Today*)
- **Stale (>48h):** 27 (e.g. Cisco Software Engineer 2014239 - *Posted 11 Days Ago*)
- **Expired:** 2 (Job requisition no longer available)
- **Quirks & Fixes:**
  - Workday is an SPA framework requiring network idle or React component mount to inspect the DOM.
  - 100% of Workday roles are `company_site` applications. Resumes are only generated after the external requisition is verified active and fresh.

---

## 3. Freshness Filter Enforcement
- **Configured Cutoff:** 48 Hours
- **Total Stale Jobs Identified across All Batches:** 176
- **Total Expired Jobs Identified across All Batches:** 13
- **Final Output Leakage:** **0** (Zero stale jobs permitted in final output)
- **Verification Rule:** If posting age cannot be confirmed within the 48-hour window, the job is strictly **REJECTED**.
