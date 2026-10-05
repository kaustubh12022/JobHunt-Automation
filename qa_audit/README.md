# QA Audit & Acceptance Verification Directory

This directory contains the complete verification artifacts, platform-by-platform live audits, proof-of-work screenshots, and acceptance criteria reports for the Job Pipeline.

---

## Directory Navigation

- **[`final_summary.md`](final_summary.md):** Executive summary of changes made, testing metrics, and proof locations.
- **[`acceptance_criteria.md`](acceptance_criteria.md):** Detailed checklist and verification matrix for all 18 acceptance criteria.
- **[`audit_results/`](audit_results/):**
  - [`platform_audit_report.md`](audit_results/platform_audit_report.md): Platform-by-platform statistics table (Checked, Fresh, Stale, Expired, Broken, Classification).
  - [`detailed_audit_log.json`](audit_results/detailed_audit_log.json): Raw machine-readable audit telemetry.
- **[`screenshots/`](screenshots/):** High-resolution captures from live browser inspections:
  - [`naukri/`](screenshots/naukri/): Fresh today, 1-day, 1-week stale, 3-week stale, and expired (`?expJD=true`).
  - [`linkedin/`](screenshots/linkedin/): Fresh 1-hour easy apply, fresh 39-min company site, closed 2-months.
  - [`internshala/`](screenshots/internshala/): Fresh few hours in-platform apply.
  - [`unstop/`](screenshots/unstop/): Fresh updated today registration.
  - [`other_platforms/`](screenshots/other_platforms/): Cisco Workday ATS (fresh vs stale), Hirist portal.
- **[`freshness/`](freshness/):** Evidence grouped by freshness classification (`fresh/`, `stale/`, `expired/`).
- **[`application_type/`](application_type/):** Evidence grouped by application category (`easy_apply/`, `company_site/`).
- **[`pdf_validation/`](pdf_validation/):**
  - Generated 3-column & 4-column Job Applications Table PDF: [`Resume_Created_Jobs.pdf`](pdf_validation/Resume_Created_Jobs.pdf).
  - Rendered Page 1 proof confirming table starts on Page 1 (no blank page): [`table_pdf_page_1_verified.png`](pdf_validation/table_pdf_page_1_verified.png).
  - Rendered Page 2 proof: [`table_pdf_page_2_verified.png`](pdf_validation/table_pdf_page_2_verified.png).
  - ATS-compliant 1-page resume generated for Company Site: [`Cisco_Full_Stack_Software_Engineer_ATS_Verified.pdf`](pdf_validation/Cisco_Full_Stack_Software_Engineer_ATS_Verified.pdf).
- **[`resume_links/`](resume_links/):** Proof confirming all embedded links are valid, resolvable HTTP/HTTPS URLs with zero relative or local filesystem links.

---

## Protocol Verification Status
- **DeepSeek API:** Zero API calls made.
- **Remote Jobs:** 100% accepted across all variants.
- **Freshness Window:** 48 hours strictly enforced. Zero stale jobs permitted.
- **Easy Apply:** 0 resumes generated.
- **Company Site:** Resumes generated & verified for ATS compliance.
- **Approval Gate:** **HOLD** (Awaiting explicit user `GO APPROVE`).
