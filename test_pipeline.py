import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import re
import json
from pathlib import Path
from jobspy import scrape_jobs
from pypdf import PdfReader
from src.logger import logger
from src.models import Job
from src.scraper import clean_html
from src.ai_engine import call_ai_scoring_async
from src.resume_tailor import tailor_resumes_batch
from src.pdf_generator import generate_pdf
from playwright.sync_api import sync_playwright
import asyncio


def validate_resume_json(job: Job, tailored: dict) -> list[str]:
    """Validates the generated JSON resume against ATS and Layout rules."""
    errors = []
    
    # 1. Company Name Tailoring
    # 1. Company Name Tailoring
    target_company = job.company.lower()
    first_word = target_company.split()[0] if ' ' in target_company else target_company
    
    # Check if target company was mentioned anywhere in the resume
    resume_text_lower = json.dumps(tailored).lower()
    if target_company not in resume_text_lower and first_word not in resume_text_lower:
        errors.append(f"Company name '{job.company}' (or '{first_word}') not found anywhere in the tailored resume.")

    # 2. Bullet Point Action Verbs & Length
    action_verbs = ['developed', 'engineered', 'architected', 'spearheaded', 'orchestrated', 
                    'implemented', 'designed', 'created', 'built', 'led', 'managed', 'optimized',
                    'automated', 'tested', 'executed', 'integrated', 'streamlined', 'reduced', 'increased',
                    'collaborated', 'resolved', 'maintained', 'performed', 'wrote', 'configured', 'deployed']
    
    for exp in tailored.get('experience_details', []):
        for resp in exp.get('key_responsibilities', []):
            if isinstance(resp, dict):
                bullet = list(resp.values())[0]
            else:
                bullet = resp
            
            words = str(bullet).split()
            if len(words) > 30:
                errors.append(f"Bullet point too long ({len(words)} words): '{bullet[:40]}...'")
            
            if words:
                first_word = words[0].lower().strip(',')
                if first_word not in action_verbs and not first_word.endswith('ed'):
                    # It's a soft check, but we flag it
                    logger.warning(f"   [Warn] Bullet might not start with action verb: '{first_word}' in '{bullet[:30]}'")

    # 3. ATS Keyword Coverage
    reqs = getattr(job, 'extracted_requirements', '').lower()
    if reqs:
        req_words = set(re.findall(r'\b[a-z]{3,}\b', reqs))
        
        resume_text = json.dumps(tailored).lower()
        resume_words = set(re.findall(r'\b[a-z]{3,}\b', resume_text))
        
        overlap = req_words.intersection(resume_words)
        if len(req_words) > 0:
            coverage = len(overlap) / len(req_words)
            if coverage < 0.20: # 20% literal word overlap is expected at minimum for tech skills
                errors.append(f"Low ATS Keyword Coverage: {coverage:.0%} overlap with requirements.")
            else:
                logger.info(f"   ✅ ATS Coverage good: {coverage:.0%}")
    
    return errors


def validate_pdf(pdf_path: str) -> list[str]:
    """Validates the generated PDF file."""
    errors = []
    try:
        reader = PdfReader(pdf_path)
        pages = len(reader.pages)
        if pages > 1:
            errors.append(f"PDF is {pages} pages long. MUST be exactly 1 page.")
        else:
            logger.info(f"   ✅ PDF is exactly 1 page.")
            
        # Check text extraction
        text = reader.pages[0].extract_text()
        if not text or len(text) < 100:
            errors.append("PDF appears to be empty or unreadable.")
            
    except Exception as e:
        errors.append(f"Failed to read PDF: {e}")
        
    return errors


from src.scraper import run_scraper
from src.scorer import score_jobs

def run_fast_test():
    """Executes a fast test pipeline testing Pandas filters and AI Scoring (max 100 jobs)."""
    logger.info("🧪 [TEST PIPELINE] Starting rigorous validation pipeline...")
    
    logger.info("   [1/4] Scraping up to 100 jobs and applying Pandas filters...")
    # This will scrape 1 combo up to 100 results and apply pandas pre-filtering
    jobs, stats = run_scraper(test_mode=True)
    
    if not jobs:
        logger.error("❌ Failed to scrape test jobs or they were all filtered out. Aborting test.")
        return
        
    logger.info(f"   ✅ Pre-filter passed {len(jobs)} jobs. Moving to AI Scoring...")
    
    logger.info("   [2/4] Scoring jobs concurrently...")
    jobs = asyncio.run(score_jobs(jobs))
    
    # Sort and take top 3
    jobs.sort(key=lambda j: j.score, reverse=True)
    top_jobs = jobs[:3]
    
    logger.info(f"   [3/4] Tailoring resumes for top {len(top_jobs)} jobs...")
    tailored_jsons = tailor_resumes_batch(top_jobs)
    
    logger.info("   [4/4] Validating JSON Output & Generating PDFs...")
    all_passed = True
    
    out_dir = Path("test_output")
    out_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for i, (job, tailored) in enumerate(zip(top_jobs, tailored_jsons)):
            logger.info(f"\n--- Validating Job: {job.title} at {job.company} ---")
            
            if isinstance(tailored, Exception):
                logger.error(f"   ❌ AI Generation Failed: {tailored}")
                all_passed = False
                continue
                
            json_errors = validate_resume_json(job, tailored)
            if json_errors:
                all_passed = False
                for err in json_errors:
                    logger.error(f"   ❌ JSON Error: {err}")
            else:
                logger.info("   ✅ JSON Structure & ATS rules passed.")
                
            pdf_path = out_dir / f"test_resume_{i}.pdf"
            try:
                generate_pdf(job, tailored, "test_output", page)
            except Exception as e:
                logger.error(f"   ❌ PDF Generation crashed: {e}")
                all_passed = False
                continue
                
        browser.close()
        
    logger.info("\n   [5/5] Validating Final PDF Layouts...")
    
    import glob
    test_pdfs = glob.glob(str(Path("C:/Users/kalek/OneDrive/Desktop/AutoApply_Output/test_output/*.pdf")))
    
    if not test_pdfs:
        logger.error("   ❌ No PDFs were found to validate!")
        all_passed = False
        
    for pdf_path in test_pdfs:
        logger.info(f"Checking {Path(pdf_path).name}...")
        pdf_errors = validate_pdf(pdf_path)
        if pdf_errors:
            all_passed = False
            for err in pdf_errors:
                logger.error(f"   ❌ PDF Error: {err}")
                
    logger.info("\n==============================================")
    if all_passed:
        logger.info("🎉 TEST PIPELINE COMPLETED SUCCESSFULLY! All validations passed.")
    else:
        logger.error("❌ TEST PIPELINE FAILED! Please review the errors above.")
    logger.info("==============================================\n")

if __name__ == "__main__":
    run_fast_test()
