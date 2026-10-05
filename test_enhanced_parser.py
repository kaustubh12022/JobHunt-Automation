import re
import json
import ssl
import urllib.request
import requests
import urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def normalize_url(url: str) -> str:
    """Normalize known job portal URLs to direct/parseable endpoints."""
    # SmartRecruiters oneclick-ui
    m = re.match(r'https?://jobs\.smartrecruiters\.com/oneclick-ui/company/([^/]+)/publication/([^/?]+)', url)
    if m:
        comp, pub_id = m.groups()
        return f"https://jobs.smartrecruiters.com/ni/{comp}/{pub_id}"
    return url

def fetch_smartrecruiters_api(url: str) -> dict:
    """Try fetching SmartRecruiters jobs via public API if applicable."""
    # Pattern: https://jobs.smartrecruiters.com/Company/12345-job-title
    m = re.search(r'jobs\.smartrecruiters\.com/([^/]+)/(\d+)', url)
    if m:
        comp, post_id = m.groups()
        api_url = f"https://api.smartrecruiters.com/v1/companies/{comp}/postings/{post_id}"
        try:
            r = requests.get(api_url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                title = data.get("name", "")
                company = data.get("company", {}).get("name", comp)
                sections = data.get("jobAd", {}).get("sections", {})
                desc_parts = []
                for s_key in ["companyDescription", "jobDescription", "qualifications", "additionalInformation"]:
                    sec = sections.get(s_key, {})
                    if sec.get("text"):
                        soup = BeautifulSoup(sec["text"], "html.parser")
                        desc_parts.append(f"{sec.get('title', s_key)}:\n{soup.get_text(separator=' ', strip=True)}")
                
                desc = "\n\n".join(desc_parts)
                if len(desc) > 150:
                    return {
                        "success": True,
                        "title": title,
                        "company": company,
                        "description": desc,
                        "direct_apply_link": url,
                        "method": "SmartRecruiters API"
                    }
        except Exception:
            pass
    return None

def fetch_with_requests(url: str) -> dict:
    """Fetch using requests with SSL verify=False and standard headers."""
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Check for standard JD containers
            content_div = (
                soup.find('div', class_=re.compile(r'entry-content|job-description|jd-content|description|content-area|job-sections|job-detail', re.I))
                or soup.find('section', class_=re.compile(r'job-sections|job-description|details', re.I))
                or soup.find('article')
            )
            if content_div:
                for u in content_div.find_all(['script', 'style', 'nav', 'form']):
                    u.decompose()
                desc = content_div.get_text(separator='\n', strip=True)
                desc = re.sub(r'\n{3,}', '\n\n', desc).strip()
                if len(desc) >= 150:
                    title_tag = soup.find('h1') or soup.find('title')
                    title = title_tag.get_text(strip=True) if title_tag else ""
                    return {
                        "success": True,
                        "title": title,
                        "description": desc,
                        "direct_apply_link": url,
                        "method": "requests (SSL unverified)"
                    }
    except Exception:
        pass
    return None

def fetch_with_playwright(url: str, pw_context) -> dict:
    """Dynamic headless browser fallback for SPAs (Accenture, Medpace, etc.)."""
    try:
        page = pw_context.new_page()
        resp = page.goto(url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(2500) # Allow client-side hydration
        
        # Extract title
        title = page.title()
        
        # Try finding common job description selectors first
        desc = ""
        for sel in [
            '[class*="job-description"]', '[class*="jobDescription"]', 
            '[class*="jd-content"]', '[class*="job-detail"]',
            '[class*="posting-requirements"]', 'article', 'main'
        ]:
            loc = page.locator(sel).first
            if loc.count() > 0:
                txt = loc.inner_text().strip()
                if len(txt) > len(desc):
                    desc = txt
        
        # Fallback to body inner_text if selectors don't yield enough
        if len(desc) < 200:
            body_text = page.inner_text('body').strip()
            # Clean header/footer lines if needed
            desc = re.sub(r'\n{3,}', '\n\n', body_text)
            
        page.close()
        
        if len(desc) >= 150:
            return {
                "success": True,
                "title": title,
                "description": desc,
                "direct_apply_link": url,
                "method": "Playwright Dynamic Browser"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": False, "error": "Extracted text < 150 chars"}

urls = [
    ("Abstrabit", "https://jobs.smartrecruiters.com/AbstrabitTechnologiesPvtLtd/744000150286364-software-engineering-intern"),
    ("Sutherland", "https://jobs.smartrecruiters.com/oneclick-ui/company/Sutherland/publication/819e73fb-c999-4f9d-9519-87b604afbc88?dcr_ci=Sutherland"),
    ("Accenture AI/ML", "https://www.accenture.com/in-en/careers/jobdetails?id=AIOC-S01665345_en"),
    ("Medpace", "https://careers.medpace.com/jobs/11927"),
    ("Siemens", "https://jobs.siemens.com/en_US/externaljobs/JobDetail/522234?source=LinkedIn&ste_sid=79c323052472f2293e8f2f81f536b2f3"),
    ("Xproguard", "https://xproguard.com/careers/ios-engineer"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=HEADERS["User-Agent"],
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 800}
    )
    
    for label, raw_url in urls:
        url = normalize_url(raw_url)
        print(f"\n==========================================")
        print(f"Testing: {label} ({url})")
        
        # 1. SmartRecruiters API
        res = fetch_smartrecruiters_api(url)
        if not res:
            # 2. Fast requests
            res = fetch_with_requests(url)
        if not res or not res.get("success"):
            # 3. Playwright Dynamic
            res = fetch_with_playwright(url, context)
            
        print(f"Result: Success={res.get('success')} | Method={res.get('method')}")
        print(f"Title: {res.get('title')[:60] if res.get('title') else 'N/A'}")
        print(f"Desc Len: {len(res.get('description', ''))}")
        if res.get('description'):
            print(f"Snippet: {res['description'][:150].replace('\n', ' ')}...")
            
    browser.close()
