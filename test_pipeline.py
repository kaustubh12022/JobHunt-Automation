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
    
    # 4. Check for missing skills false positives
    skills = job.missing_skills
    if skills:
        resume_text_lower = json.dumps(tailored).lower()
        for skill in skills:
            if skill.lower() in resume_text_lower:
                logger.warning(f"   [Warn] Missing skill '{skill}' was actually found in the tailored resume.")
                errors.append(f"False Positive Missing Skill: '{skill}' is actually present.")

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

def run_fast_test(skip_scraper=True):
    """Executes a fast test pipeline testing Pandas filters and AI Scoring (max 100 jobs)."""
    logger.info("🧪 [TEST PIPELINE] Starting rigorous validation pipeline...")
    
    if skip_scraper:
        logger.info("   [1/5] Skipping Scraper... Using predefined mock jobs.")
        jobs = [
            Job(
                title="QA Automation Engineer",
                company="MockTech QA",
                location="Pune",
                description="We are looking for a QA Automation Engineer. Requirements: Selenium, Java, Postman, API Testing, JUnit, Cucumber. Minimum 1 year experience.",
                url="https://example.com/job1",
                source="linkedin"
            ),
            Job(
                title="Java Backend Developer",
                company="MockCorp Backend",
                location="Remote",
                description="Looking for a Java Backend Dev. Core skills: Java, Spring Boot, REST APIs, SQL, Microservices. Great opportunity for freshers.",
                url="https://example.com/job2",
                source="indeed"
            ),
            Job(
                title="Frontend Developer",
                company="Mock UI",
                location="Mumbai",
                description="We need a React developer. Skills: HTML, CSS, JavaScript, React, Redux.",
                url="https://example.com/job3",
                source="linkedin"
            )
        ]
    else:
        logger.info("   [1/5] Scraping up to 100 jobs and applying Pandas filters...")
        jobs, stats = run_scraper(test_mode=True)
        
        if not jobs:
            logger.error("❌ Failed to scrape test jobs or they were all filtered out. Aborting test.")
            return
            
        logger.info(f"   ✅ Pre-filter passed {len(jobs)} jobs. Moving to AI Scoring...")
    
    logger.info("   [2/5] Scoring jobs concurrently...")
    jobs = score_jobs(jobs, test_mode=True)
    
    # Sort and take top 3
    jobs.sort(key=lambda j: j.score, reverse=True)
    top_jobs = jobs[:3]
    
    logger.info(f"   [3/5] Tailoring resumes for top {len(top_jobs)} jobs...")
    tailored_jsons = tailor_resumes_batch(top_jobs)
    
    logger.info("   [4/5] Validating JSON Output & Generating PDFs...")
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
        
    logger.info("\n   [5/5] Validating Final PDF Layouts & Database Logging...")
    
    import glob
    test_pdfs = glob.glob(str(Path("C:/Users/kalek/OneDrive/Desktop/AutoApply_Output/test_output") / "*.pdf"))
    if not test_pdfs:
        # Fallback to current dir if not in Desktop output
        test_pdfs = glob.glob(str(out_dir / "*.pdf"))
    
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

    # Database Validation
    try:
        from src.db import save_pipeline_results
        import datetime
        pipeline_state = {
            "mode": "test_pipeline",
            "scan": {"total_found": 3},
            "filter": {"after": 3},
            "score": {"scored": len(jobs), "shortlisted": len(top_jobs)},
            "platforms": ["mock_linkedin", "mock_indeed"],
            "started_at": datetime.datetime.now().isoformat()
        }
        
        # Get absolute paths for the db save
        abs_pdf_paths = [str((out_dir / f"test_resume_{i}.pdf").absolute()) for i in range(len(top_jobs))]
        save_pipeline_results(pipeline_state, top_jobs, abs_pdf_paths)
        logger.info("   ✅ Database logging passed successfully.")
    except Exception as e:
        logger.error(f"   ❌ Database logging crashed: {e}")
        all_passed = False
                
    logger.info("\n==============================================")
    if all_passed:
        logger.info("🎉 TEST PIPELINE COMPLETED SUCCESSFULLY! All validations passed.")
    else:
        logger.error("❌ TEST PIPELINE FAILED! Please review the errors above.")
    logger.info("==============================================\n")

if __name__ == "__main__":
    run_fast_test()
