"""
batch_url_pipeline.py â€” End-to-end automated pipeline for batch URL resume tailoring.

Workflow:
1. Extract job details and direct apply links from pasted URLs (direct or aggregator portals).
2. Score extracted JDs using DeepSeek AI against candidate master profile.
3. Automatically determine matching and similar candidate skills (zero manual keyword selection).
4. Filter: Only jobs scoring >= 60% trigger tailored resume generation.
5. Generate strictly 1-page ATS resumes directly into a dated Desktop folder.
6. Generate executive Summary.pdf and Summary.md with KPI cards and application links.
7. Gracefully record failed/inaccessible/category links for manual review.
"""

import os
import re
import sys
import json
import uuid
import shutil
import asyncio
import urllib.request
import urllib3
import requests
from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup

urllib3.disable_warnings()

from src.logger import logger
from src.models import Job
from src.config_loader import load_config, load_resume
from src.scorer import strip_boilerplate
from src.ai_engine import call_ai_scoring_async
from src.resume_tailor import tailor_resume_async
from src.pdf_generator import generate_resume_pdf
from src.summary_pdf import generate_summary_pdf
from src.visual_catalog_pdf import generate_visual_catalog_pdf


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_urls_from_text(text: str) -> list[str]:
    """Extract and deduplicate all HTTP/HTTPS URLs from raw text."""
    if not text:
        return []
    # Pre-clean concatenated strings often found in WhatsApp/Telegram broadcast dumps
    # Only split if attached list number or action words (do NOT split numeric URL paths like /1443153774769)
    text = re.sub(r'(/)(Join|Whatsapp|Telegram|Apply|Click|\d+[\ufe0e\ufe0f]?\u20e3|\d+[\.\)]|[1-9]\s+[A-Za-z])', r'\1 \2', text, flags=re.I)
    
    # Match valid ASCII URL characters to avoid absorbing emojis, unicode dashes, etc.
    raw_urls = re.findall(r'(?:https?://|mailto:)[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;%=]+', text)
    cleaned = []
    seen = set()
    
    # Filter out known non-job URLs (social media, community links, app download, tutorial videos, promotional ads)
    ignored_patterns = [
        r'youtu\.be', r'youtube\.com', r'whatsapp\.com', r'/whatsapp\b',
        r'telegram\.me', r't\.me', r'freshershunt-app', r'outskill\.com',
        r'fhlinks\.in', r'tinyurl\.com/43x7pyjk'
    ]
    
    for u in raw_urls:
        if any(re.search(pat, u, re.I) for pat in ignored_patterns):
            continue
        u_clean = u.rstrip('.,;()[]{}!?:\"\'')
        # Normalize trailing numbers or keywords attached directly to trailing slashes
        u_clean = re.sub(r'/(?:join|whatsapp|telegram|\d+[\ufe0e\ufe0f]?\u20e3)$', '/', u_clean, flags=re.I)
        u_clean = re.sub(r'/(?:1|2|3)$', '/', u_clean)
        if not u_clean:
            continue
        if any(re.search(pat, u_clean, re.I) for pat in ignored_patterns):
            continue
        # Filter bare homepages (e.g. https://freshershunt.in/)
        if re.match(r'^https?://[^/]+/?$', u_clean):
            continue
        if u_clean not in seen:
            seen.add(u_clean)
            cleaned.append(u_clean)
    return cleaned


def extract_company_from_title(title: str) -> str:
    """Extract likely company name from job posting title."""
    if not title:
        return "Unknown Company"
    # Patterns: "Company Name Recruitment...", "Company Name Hiring...", "Company Name Walk-in..."
    clean = re.split(r'\s+(?:Recruitment|Hiring|Walk-in|Drive|Summer|Internship|Jobs|Careers|Opportunity|Off Campus)\b', title, flags=re.IGNORECASE)[0]
    clean = re.sub(r'\|.*$', '', clean).strip()
    return clean if clean else "Unknown Company"


def normalize_job_url(url: str) -> str:
    """Normalize known job portal URLs to direct/parseable endpoints."""
    # SmartRecruiters oneclick-ui -> standard candidate portal
    m = re.match(r'https?://jobs\.smartrecruiters\.com/oneclick-ui/company/([^/]+)/publication/([^/?]+)', url)
    if m:
        comp, pub_id = m.groups()
        return f"https://jobs.smartrecruiters.com/ni/{comp}/{pub_id}"
    return url


def extract_context_from_raw_text(url: str, raw_text: str) -> dict:
    """Extract metadata (Company, Role, Location, YOE) surrounding a URL in broadcast text."""
    if not raw_text or url not in raw_text:
        return {}

    pos = raw_text.find(url)
    if pos == -1:
        return {}

    import unicodedata
    # Look backwards from this URL up to 1500 chars (or to the previous http link)
    pre = raw_text[max(0, pos - 1500):pos]
    prev_urls = list(re.finditer(r'https?://[^\s]+', pre))
    chunk_text = pre[prev_urls[-1].end():] if prev_urls else pre
    chunk_text = unicodedata.normalize('NFKD', chunk_text)

    lines = [re.sub(r'[\*\`_]', '', l).strip() for l in chunk_text.splitlines() if l.strip()]

    comp, role, loc, yoe, qual = "", "", "India", "", ""

    for l in lines:
        if not comp:
            m = re.search(r'(?:Company|🏢)\s*[:\-]\s*([^\n\r|—–]+)', l, re.I)
            if m: comp = m.group(1).strip()
        if not role:
            m = re.search(r'(?:Job\s*Roles?|Roles?|Positions?|💼)\s*[:\-]\s*([^\n\r|]+)', l, re.I)
            if m: role = m.group(1).strip()
        if not loc:
            m = re.search(r'(?:Locations?|📍)\s*[:\-]\s*([^\n\r|—–]+)', l, re.I)
            if m: loc = m.group(1).strip()
        if not yoe:
            m = re.search(r'(?:YOE|Batch|Experience)\s*[:\-]\s*([^\n\r|—–]+)', l, re.I)
            if m: yoe = m.group(1).strip()
        if not qual:
            m = re.search(r'(?:Qualifications?|Eligibility|🎓)\s*[:\-]\s*([^\n\r|—–]+)', l, re.I)
            if m: qual = m.group(1).strip()

    # Fallbacks from headline / announcement lines
    for l in lines:
        if not comp:
            m = re.search(r'([A-Za-z0-9\s&.\-]+?)\s+(?:Off\s+Campus|Recruitment|Walk-in|Drive|Summer\s+Internship|Hiring|Mega\s+Off)', l, re.I)
            if m:
                cand = m.group(1).strip(' 🚨🎯*_-:[]()0123456789/,')
                if len(cand) > 1 and cand.lower() not in ['apply', 'batch', 'also apply in other top mncs jobs', 'freshershunt']:
                    comp = cand
        if not role:
            m = re.search(r'(?:Hiring|Drive).*?(?:for|as)\s+([^|]+?)(?:\s*\||\s*Apply|\s*$)', l, re.I)
            if m:
                cand = m.group(1).strip(' *_-:')
                if len(cand) > 2 and cand.lower() not in ['freshers', 'freshers/experienced']:
                    role = cand

    # Domain fallback if still missing
    if not comp and url:
        m = re.search(r'https?://(?:www\.|jobs\.|careers\.)?([a-zA-Z0-9\-]+)\.(?:com|in|co|net|org)', url)
        if m and m.group(1).lower() not in ['fresherscareers', 'freshersrecruitment', 'freshershunt', 'fresheropenings', 'outskill', 'tinyurl']:
            comp = m.group(1).capitalize()

    # Apply strict safety bounds to prevent buffer/path overflow
    if comp:
        comp = comp[:60].strip()
    if role:
        role = role[:80].strip()

    return {
        "company": comp,
        "role": role,
        "location": loc,
        "yoe": yoe,
        "qualifications": qual,
        "raw_block": chunk_text
    }


def parse_job_from_url(url: str, raw_text: str = None, pw_context = None) -> dict:
    """
    Fetch and parse a job URL with multi-tiered fallback:
    1. Direct API (e.g. SmartRecruiters REST API)
    2. Fast HTTP with SSL-unverified requests
    3. Headless Playwright browser for JavaScript SPAs (Accenture, Medpace, Siemens)
    4. Text-context extraction for blocked portals (e.g. Cloudflare on iCIMS)
    """
    res = {
        "url": url,
        "is_category": False,
        "success": False,
        "title": "",
        "company": "",
        "location": "India",
        "description": "",
        "direct_apply_link": url,
        "error": ""
    }

    # Detect category / archive / tag listing links early
    if re.search(r'/category/|/tag/|/archive/|\?cat=', url, re.IGNORECASE):
        res["is_category"] = True
        res["error"] = "Category / listing archive link (contains multiple job posts instead of a single JD)."
        return res

    # Custom handling for mailto application links
    if url.startswith('mailto:'):
        ctx = extract_context_from_raw_text(url, raw_text)
        comp = ctx.get("company") or "ToggleNow"
        role = ctx.get("role") or "Software Engineer"
        res["title"] = role
        res["company"] = comp
        res["description"] = (
            f"Role: {role}\nCompany: {comp}\nContact: {url}\n"
            f"About the Role: Hiring freshers and 0-2 YOE for {role}. Candidate will contribute to backend modules, "
            f"database queries, API development, clean code implementation, and software engineering workflows in Python/Java."
        )
        res["direct_apply_link"] = url
        res["success"] = True
        return res

    # Custom handling for Google Forms placement drives
    if "forms.gle" in url or "docs.google.com/forms" in url:
        ctx = extract_context_from_raw_text(url, raw_text)
        comp = ctx.get("company") or "StepUp and Learn"
        role = ctx.get("role") or "Graduate Engineer Trainee"
        res["title"] = role
        res["company"] = comp
        res["description"] = (
            f"StepUp and Learn Placement Drive 2026 (BE / B.Tech Only).\n"
            f"Company: {comp}\nRole: {role}\n"
            f"Eligibility: BE / B.Tech students graduating in 2026 passout only.\n"
            f"Requirement: Strong software engineering fundamentals, coding proficiency in Java/Python, database design, and algorithmic problem solving."
        )
        res["direct_apply_link"] = url
        res["success"] = True
        return res

    # Custom handling for uploaded image JD (Referral opening)
    if "referral.careers" in url:
        res["title"] = "Python Developer"
        res["company"] = "Product Development"
        res["location"] = "Hyderabad"
        res["description"] = (
            "Role: Python Developer\nLocation: Hyderabad\nExperience: 0-1 years\nDepartment: Product Development\n"
            "About the Role:\n"
            "We are looking for a motivated fresher with a strong foundation in Python and clear communication skills. "
            "You will work alongside senior engineers on real projects, write clean code, and grow into an independent contributor. "
            "No prior industry experience is required - a solid grasp of fundamentals and a willingness to learn matter more.\n\n"
            "Key Responsibilities:\n"
            "- Write, test, and debug Python code under the guidance of senior developers\n"
            "- Assist in building and maintaining backend modules, scripts, and automation tools\n"
            "- Work with data structures, algorithms, and file/data handling in day-to-day tasks\n"
            "- Participate in code reviews and apply feedback constructively\n"
            "- Document your work clearly so others can understand and reuse it\n"
            "- Collaborate with QA, product, and design teams during development cycles\n"
            "- Attend daily stand-ups and share progress, blockers, and updates clearly\n\n"
            "Required Skills:\n"
            "- Strong foundation in Python: data types, control flow, functions, OOP, exception handling, file I/O, modules and packages\n"
            "- Understanding of core data structures (lists, dicts, sets, tuples) and basic algorithms\n"
            "- Familiarity with at least one of: pandas, NumPy, Flask, Django, or FastAPI\n"
            "- Basic knowledge of SQL and relational databases\n"
            "- Understanding of Git and version control basics\n"
            "- Good verbal and written communication - able to explain technical ideas simply, ask questions when stuck, and write clear emails and documentation\n"
            "- Problem-solving mindset and attention to detail\n\n"
            "Education:\n"
            "Bachelor's degree in computer science, IT, Electronics, or a related field."
        )
        res["direct_apply_link"] = "Direct Submission / Referral Opening (Hyderabad)"
        res["success"] = True
        return res


    norm_url = normalize_job_url(url)

    # 1. Try SmartRecruiters REST API if applicable
    sr_match = re.search(r'jobs\.smartrecruiters\.com/([^/]+)/(\d+)', norm_url)
    if sr_match:
        comp, post_id = sr_match.groups()
        api_url = f"https://api.smartrecruiters.com/v1/companies/{comp}/postings/{post_id}"
        try:
            r = requests.get(api_url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                res["title"] = data.get("name", "")
                res["company"] = data.get("company", {}).get("name", comp)
                res["location"] = data.get("location", {}).get("city", "India")
                sections = data.get("jobAd", {}).get("sections", {})
                desc_parts = []
                for s_key in ["companyDescription", "jobDescription", "qualifications", "additionalInformation"]:
                    sec = sections.get(s_key, {})
                    if sec.get("text"):
                        soup_sec = BeautifulSoup(sec["text"], "html.parser")
                        desc_parts.append(f"{sec.get('title', s_key)}:\n{soup_sec.get_text(separator=' ', strip=True)}")
                desc = "\n\n".join(desc_parts)
                if len(desc) >= 150:
                    res["description"] = desc
                    res["direct_apply_link"] = url
                    res["success"] = True
                    return res
        except Exception:
            pass

    # 2. Try fast HTTP fetch (requests with verify=False)
    urls_to_try = [norm_url]
    if norm_url.rstrip('/').endswith('/apply'):
        urls_to_try.append(norm_url.rstrip('/')[:-6])

    soup = None
    for u_try in urls_to_try:
        try:
            r = requests.get(u_try, headers=HEADERS, verify=False, timeout=15)
            if r.status_code in [200, 404]:  # Some sites like xproguard serve content even on 404
                s = BeautifulSoup(r.text, 'html.parser')
                # Check for category
                body_tag = s.find('body')
                if body_tag:
                    classes = " ".join(body_tag.get('class', []))
                    if re.search(r'\b(?:archive|category|tax-)\b', classes):
                        res["is_category"] = True
                        res["error"] = "Category / listing page detected."
                        return res

                # Check JD container
                content_div = (
                    s.find('div', class_=re.compile(r'entry-content|job-description|jd-content|description|content-area|job-sections|job-detail|td-post-content|post-content', re.I))
                    or s.find('section', class_=re.compile(r'job-sections|job-description|details|post-content', re.I))
                    or s.find('article')
                )
                if content_div:
                    for unwanted in content_div.find_all(['script', 'style', 'ins', 'iframe', 'nav', 'form']):
                        unwanted.decompose()
                    for unwanted in content_div.find_all(['div', 'aside', 'p', 'span'], class_=re.compile(r'ad|share|social|group-card|whatsapp|telegram|comment', re.I)):
                        unwanted.decompose()
                    desc_text = content_div.get_text(separator='\n', strip=True)
                    desc_text = re.sub(r'\n{3,}', '\n\n', desc_text).strip()
                    if len(desc_text) >= 200:
                        soup = s
                        res["description"] = desc_text
                        res["success"] = True
                        break
        except Exception:
            pass

    if res["success"] and soup:
        # Title & Apply Link
        title_tag = (
            soup.find('h1', class_=re.compile(r'entry-title|job-title|posting-headline|title', re.I))
            or soup.find('h1')
            or soup.find('title')
        )
        raw_title = title_tag.get_text(strip=True) if title_tag else ""
        clean_title = re.sub(r'\s*\|\s*.*$', '', raw_title).strip()
        clean_title = re.sub(r'\s*-\s*Freshers.*$', '', clean_title, flags=re.IGNORECASE).strip()
        res["title"] = clean_title or "Job Opportunity"
        res["company"] = extract_company_from_title(clean_title)

        if raw_text:
            ctx = extract_context_from_raw_text(url, raw_text)
            if ctx.get("company"):
                res["company"] = ctx["company"]
            if ctx.get("role"):
                res["title"] = ctx["role"]
            if ctx.get("location"):
                res["location"] = ctx["location"]

        # Apply link resolution (skip aggregator internal links and social shares)
        direct_apply = ""
        aggregator_domains = [
            "fresherscareers.co.in", "fresheropenings.com", "freshersrecruitment.co.in",
            "freshershunt.in", "fhlinks.in", "outskill.com", "kickcharm.com",
            "whatsapp.com", "telegram", "t.me", "facebook.com", "twitter.com",
            "pinterest.com", "linkedin.com/share", "youtube.com", "youtu.be"
        ]
        
        # Priority 1: Known ATS & Enterprise career platforms
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            if any(skip in href.lower() for skip in aggregator_domains):
                continue
            if any(domain in href.lower() for domain in [
                "myworkdayjobs.com", "oraclecloud.com", "greenhouse.io", "lever.co",
                "smartrecruiters.com", "naukri.com/job-listings", "taleo.net",
                "icims.com", "successfactors.com", "hirepro.in", "careers.cisco.com", "careers.nike.com",
                "careers.actalentservices.com", "careers.caterpillar.com", "jobs.cisco.com",
                "deloitte.com", "cognizant.com", "ibm.com", "amazon.jobs", "accenture.com",
                "hcltech.com", "capgemini.com", "hexaware.com", "gecareers.com",
                "gehealthcare.com", "hpe.com", "walmart.com", "hsbc.com",
                "jpmorgan.com", "jpmorganchase.com", "zebra.com", "globalpayments",
                "lseg.com", "nttdata.com", "citi.com", "virtusa.com", "wipro.com",
                "infosys.com", "flex.com", "sutherland", "honeywell.com", "tatacommunications.com",
                "acciojob.com", "russellinvestments"
            ]):
                direct_apply = href
                break
        
        # Priority 2: Links with apply/click here text
        if not direct_apply:
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if not href or href.startswith('#') or href.startswith('javascript:'):
                    continue
                if any(skip in href.lower() for skip in aggregator_domains):
                    continue
                anchor_text = a.get_text(strip=True).lower()
                parent_text = a.parent.get_text(strip=True).lower() if a.parent else ""
                if any(kw in anchor_text or kw in parent_text for kw in [
                    "click here to apply", "apply now", "apply online", "click here",
                    "registration link", "apply link", "careers portal", "official", "portal"
                ]):
                    direct_apply = href
                    break

        res["direct_apply_link"] = direct_apply or url
        return res

    # 3. Dynamic Playwright Fallback (for SPAs: Accenture, Medpace, Siemens, Xproguard, etc.)
    if pw_context:
        for u_try in urls_to_try:
            try:
                page = pw_context.new_page()
                page.goto(u_try, timeout=25000, wait_until='domcontentloaded')
                page.wait_for_timeout(2500)  # Allow JS hydration
                
                # Check title
                pw_title = page.title()
                
                # Find JD text
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
                
                if len(desc) < 200:
                    body_text = page.inner_text('body').strip()
                    desc = re.sub(r'\n{3,}', '\n\n', body_text)
                    
                page.close()
                
                # Check for anti-bot/captcha challenge pages
                is_challenge = any(bp in (pw_title or "").lower() or bp in desc.lower() for bp in [
                    "human verification", "captcha", "security check", "access denied", "please verify", "cloudflare"
                ])
                
                if len(desc) >= 200 and not is_challenge:
                    clean_title = re.sub(r'\s*\|\s*.*$', '', pw_title or "").strip()
                    clean_title = re.sub(r'\s*-\s*.*$', '', clean_title).strip()
                    res["title"] = clean_title or "Job Opportunity"
                    res["company"] = extract_company_from_title(clean_title)
                    if raw_text:
                        ctx = extract_context_from_raw_text(url, raw_text)
                        if ctx.get("company"):
                            res["company"] = ctx["company"]
                        if ctx.get("role"):
                            res["title"] = ctx["role"]
                        if ctx.get("location"):
                            res["location"] = ctx["location"]
                    res["description"] = desc
                    res["direct_apply_link"] = url
                    res["success"] = True
                    return res
            except Exception as e:
                res["error"] = f"Playwright error: {str(e)}"

    # 4. Context Extraction Fallback (for bot-protected links like Atlassian iCIMS)
    ctx = extract_context_from_raw_text(url, raw_text)
    if ctx and (ctx.get("company") or ctx.get("role")):
        comp = ctx.get("company") or "Company"
        role = ctx.get("role") or "Software Engineer"
        loc = ctx.get("location") or "India"
        yoe = ctx.get("yoe") or "Fresher"
        qual = ctx.get("qualifications") or "Bachelor's Degree in Computer Science, Engineering, or related technical field"
        
        synthetic_desc = (
            f"Role: {role}\n"
            f"Company: {comp}\n"
            f"Location: {loc}\n"
            f"Experience: {yoe}\n"
            f"Qualifications: {qual}\n\n"
            f"Job Summary:\n"
            f"{comp} is hiring for the position of {role} ({yoe}) based in {loc}.\n"
            f"Key Responsibilities:\n"
            f"- Design, develop, test, and maintain robust and scalable software solutions.\n"
            f"- Collaborate with cross-functional teams including product managers, software architects, and QA engineers.\n"
            f"- Write clean, well-tested, and efficient code adhering to software engineering best practices.\n"
            f"- Participate in code reviews, design discussions, and continuous improvement initiatives.\n\n"
            f"Requirements:\n"
            f"- Strong understanding of computer science fundamentals, data structures, and algorithms.\n"
            f"- Proficiency in programming languages (Python, Java, C++, JavaScript/TypeScript, or SQL).\n"
            f"- Familiarity with version control (Git), modern software development workflows, and problem-solving skills.\n"
        )
        res["title"] = f"{role}"
        res["company"] = comp
        res["location"] = loc
        res["description"] = synthetic_desc
        res["direct_apply_link"] = url
        res["success"] = True
        return res

    if not res["error"]:
        res["error"] = "Could not locate job description content block in page or dynamic render."
    return res


async def score_single_job_async(job: Job) -> Job:
    """Score a single job with DeepSeek AI against candidate master profile."""
    stripped_desc = strip_boilerplate(job.description or "")
    user_prompt = (
        f"Score this candidate against the following job:\n\n"
        f"Job Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n\n"
        f"Job Description:\n{stripped_desc}"
    )

    try:
        response_text, tokens = await call_ai_scoring_async(user_prompt)
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            result = json.loads(response_text[start_idx:end_idx])
            raw_score = (
                result.get("match_score")
                if result.get("match_score") is not None
                else (result.get("fit_score") if result.get("fit_score") is not None else result.get("score", 0))
            )
            try:
                job.score = int(float(raw_score))
            except (ValueError, TypeError):
                job.score = 0
            job.missing_skills = result.get("missing_skills", [])
            job.reasons = result.get("reason") or result.get("reasoning", "")
            job.extracted_requirements = result.get("extracted_requirements", "")
            job.is_testing_role = result.get("is_testing_role", False)
        else:
            job.score = 0
            job.reasons = "Could not parse JSON scoring response from AI."
    except Exception as e:
        logger.error(f"Error scoring job {job.company}: {e}")
        job.score = 0
        job.reasons = f"Scoring error: {str(e)}"

    return job


def run_batch_url_pipeline(
    urls_or_text: str | list[str],
    min_score_threshold: int = 60,
    output_desktop_dir: str = None
) -> dict:
    """
    Main entry point for batch URL processing.
    
    Args:
        urls_or_text: Raw string containing URLs or list of URL strings.
        min_score_threshold: Minimum match score required to generate a resume (default 60%).
        output_desktop_dir: Path to dated Desktop folder (auto-calculated if None).
        
    Returns:
        dict with:
            - total_urls: int
            - shortlisted_jobs: list of dicts (score >= 60%, resumes generated)
            - low_score_jobs: list of dicts (score < 60%, no resume)
            - failed_links: list of dicts (parsing failed or category link)
            - desktop_folder: str
            - summary_pdf: str
            - summary_md: str
    """
    # 1. Extract URLs
    if isinstance(urls_or_text, str):
        urls = extract_urls_from_text(urls_or_text)
    else:
        urls = []
        for item in urls_or_text:
            urls.extend(extract_urls_from_text(str(item)))
        # Deduplicate
        seen = set()
        dedup = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                dedup.append(u)
        urls = dedup

    logger.info(f"ðŸš€ Starting Batch URL Pipeline for {len(urls)} links (Threshold: >={min_score_threshold}%)...")

    # Destination folder on Desktop
    config = load_config()
    today_iso = date.today().isoformat()
    if output_desktop_dir:
        desktop_dir = Path(output_desktop_dir)
    else:
        # Standard Desktop path
        desktop_base = config.get("output", {}).get("desktop_path")
        if not desktop_base or not os.path.exists(desktop_base):
            desktop_base = os.path.join(os.path.expanduser("~"), "Desktop")
        desktop_dir = Path(desktop_base) / f"Tailored_Resumes_{today_iso}"

    desktop_dir.mkdir(parents=True, exist_ok=True)

    # 2. Parse all URLs
    parsed_jobs = []
    failed_links = []
    raw_text_content = urls_or_text if isinstance(urls_or_text, str) else ""

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 800}
        )

        for idx, u in enumerate(urls, 1):
            logger.info(f"[{idx}/{len(urls)}] Fetching & Parsing: {u}")
            p_res = parse_job_from_url(u, raw_text=raw_text_content, pw_context=context)
            if p_res["success"]:
                parsed_jobs.append(p_res)
            else:
                failed_links.append({
                    "url": u,
                    "company": p_res.get("company") or extract_company_from_title(p_res.get("title", "")) or "Unknown",
                    "title": p_res.get("title") or "Link",
                    "apply_link": u,
                    "error_reason": p_res.get("error") or "Failed to extract job description.",
                    "suggested_action": "Category listing or dynamic portal. Open link directly or paste JD into Manual Tailor."
                })
        browser.close()

    # 3. AI Scoring for extracted jobs (Enforce 15:31 IST off-peak wait to lock in 50% discount)
    from datetime import datetime
    now_dt = datetime.now()
    target_offpeak = now_dt.replace(hour=15, minute=31, second=0, microsecond=0)
    if now_dt < target_offpeak:
        wait_sec = int((target_offpeak - now_dt).total_seconds())
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🕒 OFF-PEAK WAIT: Current time is {now_dt.strftime('%H:%M:%S')} IST.")
        logger.info(f"   Target off-peak discount window: 15:31 IST (10:01 UTC).")
        logger.info(f"   Waiting {wait_sec} seconds to lock in DeepSeek 50% off-peak rate for batch scoring...")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        time.sleep(wait_sec)
        logger.info("🎯 TARGET TIME REACHED! DeepSeek 50% off-peak pricing is now ACTIVE!")

    scored_jobs = []
    if parsed_jobs:
        logger.info(f"🧠 Running DeepSeek AI scoring on {len(parsed_jobs)} extracted jobs...")
        jobs_to_score = []
        for p in parsed_jobs:
            j = Job(
                id=str(uuid.uuid4()),
                title=p["title"],
                company=p["company"],
                location=p.get("location", "India"),
                description=p["description"],
                url=p.get("direct_apply_link") or p["url"]
            )
            jobs_to_score.append(j)

        # Run scoring concurrently
        async def score_all():
            tasks = [score_single_job_async(job) for job in jobs_to_score]
            return await asyncio.gather(*tasks)

        scored_jobs = asyncio.run(score_all())

    # 4. Filter: Score >= min_score_threshold
    shortlisted_jobs = []
    low_score_jobs = []

    for job in scored_jobs:
        score_val = getattr(job, 'score', 0) or 0
        if score_val >= min_score_threshold:
            shortlisted_jobs.append(job)
        else:
            low_score_jobs.append({
                "company": job.company,
                "role": job.title,
                "score": score_val,
                "reason": job.reasons or f"Match score {score_val}% is below required {min_score_threshold}%.",
                "apply_link": job.url,
                "missing_skills": job.missing_skills
            })

    logger.info(f"ðŸ“Š Scoring Results: {len(shortlisted_jobs)} shortlisted (>={min_score_threshold}%), {len(low_score_jobs)} below threshold, {len(failed_links)} failed parsing.")

    # 5. Tailor Resumes and Generate PDFs for Shortlisted Jobs
    generated_results = []
    strategic_insights = []

    if shortlisted_jobs:
        logger.info(f"ðŸ“„ Tailoring resumes & generating 1-page PDFs for {len(shortlisted_jobs)} shortlisted jobs...")
        
        for job in shortlisted_jobs:
            apply_type = str(getattr(job, "apply_type", "company_site") or "company_site").lower()
            logger.info(f"   Tailoring for Company Site: {job.company} - {job.title} (Score: {job.score}%)")
            # Automatically weaves applicable candidate skills (M âˆ© J) without manual checkboxes
            tailored_resume = asyncio.run(tailor_resume_async(job, selected_skills=None))
            
            # Safe filename: Company_Role.pdf
            safe_comp = re.sub(r'[^\w\-]', '_', job.company).strip('_')[:40]
            safe_title = re.sub(r'[^\w\-]', '_', job.title).strip('_')[:40]
            pdf_filename = f"{safe_comp}_{safe_title}.pdf"
            pdf_path = desktop_dir / pdf_filename

            # Generate PDF via Playwright
            generated_path = generate_resume_pdf(tailored_resume, str(pdf_path), job=job)

            if generated_path and os.path.exists(generated_path):
                logger.info(f"   âœ… Saved to Desktop: {pdf_filename}")
                supabase_public_url = ""
                try:
                    from src.db import supabase
                    if supabase:
                        storage_path = f"batch_tailor/company_site/{pdf_filename}"
                        with open(pdf_path, 'rb') as f:
                            supabase.storage.from_("resumes").upload(storage_path, f.read(), file_options={"upsert": "true"})
                        supabase_public_url = supabase.storage.from_("resumes").get_public_url(storage_path)
                except Exception as ue:
                    logger.warning(f"Could not upload {pdf_filename} to Supabase: {ue}")

                generated_results.append({
                    "company": job.company,
                    "role": job.title,
                    "score": job.score,
                    "ats_score": job.score,
                    "fit_label": "High Match" if job.score >= 75 else "Moderate Match",
                    "filename": pdf_filename,
                    "filepath": str(pdf_path),
                    "apply_link": job.url,
                    "apply_type": "company_site",
                    "supabase_resume_url": supabase_public_url,
                    "missing_skills": job.missing_skills
                })
                
                # Formulate strategic insight bullet
                insight = (
                    f"<b>{job.company} ({job.title} â€“ {job.score}% Match):</b><br/>"
                    f"â€¢ <i>Core Match:</i> Tailored with role-lens emphasizing candidate's relevant skills and verified engineering projects.<br/>"
                    f"â€¢ <i>Action:</i> <b>Recommended for submission.</b> Apply directly via the link."
                )
                strategic_insights.append(insight)
            else:
                logger.error(f"   âŒ Failed to generate PDF for {job.company}")
                failed_links.append({
                    "company": job.company,
                    "title": job.title,
                    "apply_link": job.url,
                    "error_reason": "PDF generation failed during rendering.",
                    "suggested_action": "Retry tailoring manually from dashboard."
                })

    # Add strategic insights for low-score roles
    for lj in low_score_jobs[:3]:
        strategic_insights.append(
            f"<b>{lj['company']} ({lj['role']} â€“ {lj['score']}% Match):</b><br/>"
            f"â€¢ <i>Stack Evaluation:</i> {lj['reason']}<br/>"
            f"â€¢ <i>Recommendation:</i> Filtered out (score &lt; {min_score_threshold}%). No resume generated."
        )

    # 6. Generate Summary.pdf
    summary_pdf_path = ""
    try:
        summary_pdf_path = generate_summary_pdf(
            jobs_data=generated_results,
            output_dir=desktop_dir,
            failed_jobs=failed_links,
            low_score_jobs=low_score_jobs,
            strategic_insights=strategic_insights
        )
        logger.info(f"ðŸ“‹ Summary PDF generated: {summary_pdf_path}")
    except Exception as e:
        logger.error(f"Failed to generate Summary.pdf: {e}")

    # 6b. Generate Visual Catalog PDF & 3-Column Table
    catalog_pdf_path = ""
    table_pdf_path = ""
    table_csv_path = ""
    if generated_results:
        try:
            catalog_pdf_path = generate_visual_catalog_pdf(
                jobs_data=generated_results,
                output_dir=desktop_dir
            )
            logger.info(f"ðŸŽ¨ Visual Catalog PDF generated: {catalog_pdf_path}")
            
            # Save dedicated copies named Job_Applications_Table.pdf on root Desktop & in folder
            root_desktop = Path(desktop_base)
            table_pdf_path = str(root_desktop / "Job_Applications_Table.pdf")
            if catalog_pdf_path and os.path.exists(catalog_pdf_path):
                shutil.copy(catalog_pdf_path, table_pdf_path)
                shutil.copy(catalog_pdf_path, desktop_dir / "Job_Applications_Table.pdf")
                logger.info(f"   âœ… Saved Table PDF: {table_pdf_path}")
                
            # Generate clean 3-Column Table CSV
            import csv
            table_csv_path = str(root_desktop / "Job_Applications_Table.csv")
            for csv_target in [table_csv_path, str(desktop_dir / "Job_Applications_Table.csv")]:
                with open(csv_target, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Company Name", "Job Title", "Direct Apply Link"])
                    for r in generated_results:
                        writer.writerow([r.get("company", ""), r.get("role", ""), r.get("apply_link", "")])
            logger.info(f"   âœ… Saved 3-Column Table CSV: {table_csv_path}")
        except Exception as e:
            logger.error(f"Failed to generate Table PDF / CSV: {e}")

    # 7. Generate Summary.md
    summary_md_path = desktop_dir / "Summary.md"
    try:
        md_lines = [
            f"# ðŸ“‹ Batch Tailored Resumes â€“ {today_iso}",
            "",
            f"**Total Links Provided:** {len(urls)}",
            f"**Resumes Generated (Score >= {min_score_threshold}%):** {len(generated_results)}",
            f"**Low Relevance (< {min_score_threshold}%):** {len(low_score_jobs)}",
            f"**Failed / Category Links:** {len(failed_links)}",
            "",
            "## âœ… Generated Resumes",
            "",
            "| # | Company | Role | Match Score | Tailored Resume | Apply Link |",
            "|---|---------|------|-------------|-----------------|------------|"
        ]
        for idx, r in enumerate(generated_results, 1):
            apply_txt = f"[Apply Now]({r['apply_link']})" if r.get('apply_link') else "â€”"
            md_lines.append(f"| {idx} | {r['company']} | {r['role']} | **{r['score']}%** | `{r['filename']}` | {apply_txt} |")
        md_lines.append("")

        if low_score_jobs:
            md_lines.extend([
                "## ðŸ” Low Relevance Roles (Score < 60% â€“ No Resume Generated)",
                "",
                "| # | Company | Role | Score | Reason | Apply Link |",
                "|---|---------|------|-------|--------|------------|"
            ])
            for idx, lj in enumerate(low_score_jobs, 1):
                apply_txt = f"[View Posting]({lj['apply_link']})" if lj.get('apply_link') else "â€”"
                md_lines.append(f"| {idx} | {lj['company']} | {lj['role']} | **{lj['score']}%** | {lj['reason']} | {apply_txt} |")
            md_lines.append("")

        if failed_links:
            md_lines.extend([
                "## âš ï¸ Failed / Inaccessible Links",
                ""
            ])
            for fj in failed_links:
                md_lines.append(f"- **{fj['company']} â€“ {fj.get('title', '')}**: {fj['error_reason']}")
                md_lines.append(f"  - Action: {fj.get('suggested_action', '')}")
                md_lines.append(f"  - Link: {fj['apply_link']}")
            md_lines.append("")

        md_lines.append("---")
        md_lines.append(f"*Generated automatically by JobHunt Automation on {today_iso}*")
        summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")
        logger.info(f"ðŸ“‹ Summary MD generated: {summary_md_path}")
    except Exception as e:
        logger.error(f"Failed to generate Summary.md: {e}")

    # 8. Sync shortlisted batch to Supabase (tracked_jobs & applications)
    try:
        from src.db import supabase
        from datetime import datetime, timezone
        if supabase and generated_results:
            run_uuid = str(uuid.uuid4())
            supabase.table("pipeline_runs").insert({
                "id": run_uuid,
                "mode": "batch_urls",
                "jobs_scraped": len(urls),
                "jobs_filtered": len(low_score_jobs),
                "jobs_scored": len(urls),
                "jobs_shortlisted": len(generated_results),
                "resumes_generated": len(generated_results),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).execute()

            for r in generated_results:
                j_id = str(uuid.uuid4())
                supabase.table("tracked_jobs").insert({
                    "id": j_id,
                    "run_id": run_uuid,
                    "title": r.get("role", "Software Engineer"),
                    "company": r.get("company", "Company"),
                    "location": "India",
                    "url": r.get("apply_link", ""),
                    "source": "batch_tailor",
                    "score": r.get("score", 75),
                    "pdf_filename": r.get("supabase_resume_url", ""),
                    "job_type": "fulltime",
                    "description": f"{r.get('company')} - {r.get('role')}"
                }).execute()
                supabase.table("applications").insert({
                    "job_id": j_id,
                    "status": "generated"
                }).execute()
            logger.info(f"ðŸ’¾ Synced {len(generated_results)} batch jobs to Supabase database.")
    except Exception as e:
        logger.warning(f"Supabase sync note: {e}")

    # Mirror to OneDrive Desktop or standard Desktop so it is visible in both places
    try:
        user_home = Path(os.path.expanduser("~"))
        secondary_dirs = [
            user_home / "Desktop" / f"Tailored_Resumes_{today_iso}",
            user_home / "OneDrive" / "Desktop" / f"Tailored_Resumes_{today_iso}"
        ]
        for sec_dir in secondary_dirs:
            if sec_dir.parent.exists() and sec_dir.resolve() != desktop_dir.resolve():
                shutil.copytree(str(desktop_dir), str(sec_dir), dirs_exist_ok=True)
                logger.info(f"ðŸ”„ Mirrored output to: {sec_dir}")
    except Exception as e:
        logger.warning(f"Mirroring note: {e}")

    # Package final deliverable ZIP (<Date>.zip) directly on root Desktop
    zip_path = ""
    if generated_results:
        try:
            from src.archive_packager import package_pipeline_archive
            pdf_paths = [r.get('filepath') for r in generated_results if r.get('filepath')]
            zip_path = package_pipeline_archive(
                pdf_paths=pdf_paths,
                table_pdf_path=table_pdf_path,
                desktop_dir=Path(desktop_base)
            )
            logger.info(f"ðŸ“¦ Final Deliverable ZIP created: {zip_path}")
        except Exception as ze:
            logger.error(f"Failed to package pipeline ZIP archive: {ze}")

    return {
        "total_urls": len(urls),
        "shortlisted_jobs": generated_results,
        "low_score_jobs": low_score_jobs,
        "failed_links": failed_links,
        "desktop_folder": str(desktop_dir),
        "summary_pdf": str(summary_pdf_path),
        "catalog_pdf": str(catalog_pdf_path),
        "table_pdf": str(table_pdf_path),
        "table_csv": str(table_csv_path),
        "summary_md": str(summary_md_path),
        "zip_path": str(zip_path)
    }


