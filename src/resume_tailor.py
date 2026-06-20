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


async def tailor_resume_async(job: Job) -> dict:
    """
    Calls DeepSeek with thinking ENABLED to generate a Delta JSON,
    then merges it with the master resume's static fields.
    """
    master_resume = load_resume()

    # Fallback if Phase 2 compression failed or wasn't run
    reqs = getattr(job, "extracted_requirements", None)
    if not reqs:
        reqs = "Requires deep technical analysis based on the JD."

    # Send the compressed JD requirements instead of the full 1000-word JD
    user_prompt = (
        f"Job Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n\n"
        f"Core Requirements:\n{reqs}"
    )

    try:
        response_text = await call_ai_tailoring_async(user_prompt)

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

        if "skills" in delta:
            tailored["skills"] = delta["skills"]

        if "experience_details" in delta:
            tailored["experience_details"] = delta["experience_details"]
        elif "experience" in delta:
            tailored["experience"] = delta["experience"]

        if "projects" in delta:
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
    tasks = [tailor_resume_async(job) for job in jobs]
    return await asyncio.gather(*tasks, return_exceptions=True)

def tailor_resumes_batch(jobs: list[Job]) -> list[dict]:
    import asyncio
    return asyncio.run(tailor_resumes_batch_async(jobs))