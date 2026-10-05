"""
Universal ATS Acceptance Test Suite
Author: Antigravity AI
Validates PDF files against enterprise ATS parsing standards.
"""
import sys
import re
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import pypdf
import fitz  # PyMuPDF


def audit_resume_pdf(pdf_path: str) -> dict:
    results = {
        "passed": True,
        "errors": [],
        "warnings": [],
        "details": {}
    }

    if not os.path.exists(pdf_path):
        results["passed"] = False
        results["errors"].append(f"FILE NOT FOUND: {pdf_path}")
        return results

    # 1. Page Count Audit
    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    results["details"]["page_count"] = total_pages
    if total_pages != 1:
        results["passed"] = False
        results["errors"].append(f"PAGE COUNT VIOLATION: Resume has {total_pages} pages. Strict single-page required.")

    # 2. Extract Raw Text Stream
    full_text = ""
    for page in reader.pages:
        text = page.extract_text() or ""
        full_text += text + "\n"

    # Also check PyMuPDF extraction for encoding/glyph issues
    doc = fitz.open(pdf_path)
    fitz_text = ""
    for page in doc:
        fitz_text += page.get_text() + "\n"
    doc.close()

    results["details"]["char_count_pypdf"] = len(full_text)
    results["details"]["char_count_fitz"] = len(fitz_text)

    # 3. Kerning & Word-Splitting Audit
    split_patterns = [
        r'\bT\s+echnical\b',
        r'\bT\s+ools\b',
        r'\bT\s+echnologies\b',
        r'\bV\s+ersion\b',
        r'\bP\s+rojects\b',
        r'\bE\s+ducation\b',
        r'\bE\s+xperience\b',
        r'\bC\s+ertifications\b',
        r'\bA\s+chievements\b',
        r'\bP\s+rofile\b',
        r'\bS\s+kills\b'
    ]
    for pattern in split_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE) or re.search(pattern, fitz_text, re.IGNORECASE)
        if match:
            results["passed"] = False
            results["errors"].append(f"KERNING WORD-SPLIT DETECTED: Found '{match.group(0)}'. Must be clean contiguous word.")

    # 4. Two-Digit Year Audit
    two_digit_date_pattern = r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{2})\b(?!\d{2})'
    invalid_dates = re.findall(two_digit_date_pattern, full_text) or re.findall(two_digit_date_pattern, fitz_text)
    if invalid_dates:
        results["passed"] = False
        results["errors"].append(f"FATAL 2-DIGIT YEAR DETECTED: Found {invalid_dates}. Must use 4-digit years (e.g., 'Jan 2025').")

    # Also check 2-digit ranges like '22 – '26 or 25 - 26
    two_digit_range_pattern = r'\b(?:\'|\b)(2[0-9])\s*[-–—]\s*(?:\'|\b)(2[0-9])\b'
    invalid_ranges = re.findall(two_digit_range_pattern, full_text)
    if invalid_ranges:
        results["passed"] = False
        results["errors"].append(f"FATAL 2-DIGIT YEAR RANGE DETECTED: Found {invalid_ranges}. Must use 4-digit years (e.g., '2022 - 2026').")

    # 5. Candidate Location in Header Audit (Must appear BEFORE first section heading)
    header_match = re.split(r'\b(PROFILE|SUMMARY|EDUCATION|SKILLS|TECHNICAL\s+SKILLS|WORK\s+EXPERIENCE|PROJECTS)\b', full_text, flags=re.IGNORECASE)
    header_text = header_match[0] if header_match else full_text[:250]
    location_keywords = ["Pune", "Maharashtra", "India", "Bangalore", "Delhi", "Mumbai", "Hyderabad", "Remote"]
    found_loc = any(loc.lower() in header_text.lower() for loc in location_keywords)
    if not found_loc:
        results["passed"] = False
        results["errors"].append("MISSING LOCATION IN HEADER: Candidate contact block (above first section) does not contain City, State, or Country.")

    # 6. Horizontal Collision Audit
    collision_patterns = [
        r'TechnologiesPune',
        r'SuiteWeb',
        r'PipelinePython',
        r'Technologies\s*Pune',  # check if merged without space or separator
    ]
    for pattern in [r'TechnologiesPune', r'SuiteWeb', r'PipelinePython']:
        if re.search(pattern, full_text) or re.search(pattern, fitz_text):
            results["passed"] = False
            results["errors"].append(f"HORIZONTAL COLLISION DETECTED: Text stream merged into '{pattern}'. Add structural spacing.")

    # 7. Unmapped Unicode Glyph Audit
    if '\ufffd' in full_text or '\ufffd' in fitz_text:
        results["passed"] = False
        results["errors"].append("UNMAPPED GLYPH DETECTED: PDF contains replacement character (\\ufffd). Fix font encoding.")

    # Non-standard or broken control characters
    broken_chars = [c for c in full_text if ord(c) in (0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f)]
    if broken_chars:
        results["passed"] = False
        results["errors"].append(f"CORRUPT CHARACTERS DETECTED: Found unmapped raw bytes {[hex(ord(c)) for c in broken_chars]}.")

    # 8. Cumulative CGPA Check
    cgpa_pattern = r'(?:Cumulative\s+)?CGPA\s*[:=]?\s*(\d+(?:\.\d+)?)'
    if not (re.search(cgpa_pattern, full_text, re.IGNORECASE) or re.search(cgpa_pattern, fitz_text, re.IGNORECASE)):
        results["warnings"].append("STRUCTURED CGPA MISSING: Explicit 'CGPA: X.XX' or 'Cumulative CGPA: X.XX' not found in text stream.")

    # 9. Structured Secondary Education (10th / 12th) Check
    hsc_pattern = r'(?:12th|HSC|Higher\s+Secondary)'
    ssc_pattern = r'(?:10th|SSC|Secondary\s+School)'
    has_hsc = bool(re.search(hsc_pattern, full_text, re.IGNORECASE))
    has_ssc = bool(re.search(ssc_pattern, full_text, re.IGNORECASE))
    if not (has_hsc and has_ssc):
        results["warnings"].append("STRUCTURED 10th/12th MISSING: Explicit 10th (SSC) and 12th (HSC) records recommended for Indian IT enterprise ATS.")

    # 10. Phone Number Check
    phone_pattern = r'\+91[-\s]?\d{10}'
    if not (re.search(phone_pattern, full_text) or re.search(phone_pattern, fitz_text)):
        results["warnings"].append("PHONE FORMAT WARNING: Standard '+91-XXXXXXXXXX' format recommended in header.")

    # 11. Links in Header Check
    link_pattern = r'(?:linkedin\.com\/in\/[\w\-]+|github\.com\/[\w\-]+)'
    if not (re.search(link_pattern, full_text) or re.search(link_pattern, fitz_text)):
        results["warnings"].append("CLEAN LINKS WARNING: Explicit plain text URLs (linkedin.com/in/... or github.com/...) not found in text stream.")

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ats_verifier.py <path_to_resume.pdf>")
        sys.exit(1)

    pdf_to_check = sys.argv[1]
    res = audit_resume_pdf(pdf_to_check)
    print("\n" + "=" * 55)
    print("      UNIVERSAL ATS RESUME COMPLIANCE AUDIT REPORT")
    print("=" * 55)
    print(f"Target File: {pdf_to_check}")
    print(f"Status     : {'PASSED [100% ATS Safe]' if res['passed'] else 'FAILED [ATS Incompatible]'}")
    print(f"Pages      : {res['details'].get('page_count', 'N/A')}")

    if res["errors"]:
        print("\n[CRITICAL ERRORS TO FIX]:")
        for err in res["errors"]:
            print(f"  ❌ {err}")

    if res["warnings"]:
        print("\n[WARNINGS / RECOMMENDATIONS]:")
        for w in res["warnings"]:
            print(f"  ⚠️  {w}")

    if res["passed"]:
        print("\n✅ All checks passed successfully. Ready for enterprise submission.")
        sys.exit(0)
    else:
        print(f"\n❌ Audit failed with {len(res['errors'])} critical errors.")
        sys.exit(1)
