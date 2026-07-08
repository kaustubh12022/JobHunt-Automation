"""
AutoApply Resume Tailor — Delta Output with Thinking Enabled.

Architecture Rules:
- Uses call_ai_tailoring() with thinking ENABLED (deep reasoning)
- Reads full JD from local Phase 1 Job object (no re-fetching)
- AI outputs a Delta JSON (only modified sections)
- Python merges delta with static master resume data
"""
import json
import copy
import re
from src.logger import logger
from src.models import Job
from src.ai_engine import call_ai_tailoring_async
from src.config_loader import load_resume


async def tailor_resume_async(job: Job, selected_skills: list[str] = None) -> dict:
    """
    Calls DeepSeek with thinking ENABLED to generate a Delta JSON,
    then merges it with the master resume's static fields.
    """
    master_resume = load_resume()

    # Pass the full raw job description + Phase 2 signals
    user_prompt = (
        f"Job Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n\n"
        f"=== PHASE 2 PRIORITY SIGNALS ===\n"
        f"Score: {job.score}%\n"
        f"Core Match Areas: {getattr(job, 'extracted_requirements', 'N/A')}\n"
        f"Missing Skills: {', '.join(getattr(job, 'missing_skills', []))}\n"
        f"Is Testing Role: {getattr(job, 'is_testing_role', False)}\n\n"
    )
    
    if selected_skills:
        user_prompt += (
            f"=== ADDITIONAL CONFIRMED SKILLS ===\n"
            f"The candidate has confirmed they also possess: [{', '.join(selected_skills)}]\n"
            f"You MUST naturally weave these skills into the resume — in bullet points,\n"
            f"project descriptions, and the skills list. They should appear organic,\n"
            f"not forced. Present them in the most impactful context possible.\n\n"
        )
        
    user_prompt += (
        f"=== COMPLETE JOB DESCRIPTION ===\n"
        f"{job.description}"
    )

    try:
        response_text, tokens = await call_ai_tailoring_async(user_prompt)
        job.tokens_used = getattr(job, 'tokens_used', 0) + tokens

        # Robust Markdown stripping
        cleaned_text = response_text
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()
        
        # Fallback substring extraction if DeepSeek put text before/after JSON
        start_idx = cleaned_text.find('{')
        end_idx = cleaned_text.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            cleaned_text = cleaned_text[start_idx:end_idx]

        try:
            delta = json.loads(cleaned_text)
        except json.JSONDecodeError as je:
            logger.warning(f"   ⚠️ Could not parse Delta JSON for {job.company}: {je}")
            return master_resume

        # ── Merge delta into a copy of master resume ──
        tailored = copy.deepcopy(master_resume)

        if "profile_summary" in delta:
            tailored["profile_summary"] = delta["profile_summary"]
        elif "professional_summary" in delta:
            tailored["professional_summary"] = delta["professional_summary"]

        if "tailored_skills" in delta:
            tailored["skills"] = delta["tailored_skills"]
        elif "skills" in delta:
            tailored["skills"] = delta["skills"]

        if "tailored_experience" in delta:
            tailored["experience_details"] = delta["tailored_experience"]
        elif "experience_details" in delta:
            tailored["experience_details"] = delta["experience_details"]
        elif "experience" in delta:
            tailored["experience_details"] = delta["experience"]

        if "tailored_projects" in delta:
            tailored["projects"] = delta["tailored_projects"]
        elif "projects" in delta:
            tailored["projects"] = delta["projects"]

        return tailored

    except Exception as e:
        logger.error(f"   ❌ Error tailoring resume for {job.company}: {e}")
        return master_resume


def tailor_resume(job: Job) -> dict:
    import asyncio
    return asyncio.run(tailor_resume_async(job))

async def tailor_resumes_batch_async(jobs: list[Job]) -> list[dict]:
    import asyncio
    if not jobs:
        return []
        
    # Cache Warming: Process first job sequentially to populate DeepSeek's prefix cache
    first_result = await tailor_resume_async(jobs[0])
    
    if len(jobs) > 1:
        tasks = [tailor_resume_async(job) for job in jobs[1:]]
        rest_results = await asyncio.gather(*tasks, return_exceptions=True)
        return [first_result] + list(rest_results)
        
    return [first_result]

def tailor_resumes_batch(jobs: list[Job]) -> list[dict]:
    import asyncio
    return asyncio.run(tailor_resumes_batch_async(jobs))
def tailor_resume_with_skills(job: Job, selected_skills: list[str]) -> str:
    import asyncio
    import os
    import datetime
    import shutil
    from playwright.sync_api import sync_playwright
    from src.pdf_generator import generate_pdf
    
    tailored_resume = asyncio.run(tailor_resume_async(job, selected_skills))
    job.tailored_resume = tailored_resume
    
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    pdf_path = ''
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            pdf_path = generate_pdf(job, tailored_resume, date_str, page)
        finally:
            browser.close()
            
    if pdf_path and os.path.exists(pdf_path):
        manual_dir = os.path.join(os.getcwd(), 'output', 'manual')
        if not os.path.exists(manual_dir):
            os.makedirs(manual_dir)
        filename = os.path.basename(pdf_path)
        dest_path = os.path.join(manual_dir, filename)
        shutil.copy2(pdf_path, dest_path)
        return dest_path
        
    return ''
