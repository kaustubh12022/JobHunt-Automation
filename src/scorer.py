"""
AutoApply Scorer — Hyper-Optimized Token Saving.

Architecture Rules:
- Zero-token keyword relevance filter: drops irrelevant JDs before API call
- Boilerplate stripping: regex strips "About Us", "Benefits", "EEO" sections before API call
- Micro-JSON output: AI returns ONLY {match_score, missing_skills}
- Uses call_ai_scoring() with thinking DISABLED
- Master resume is cached in the system prompt (handled by ai_engine)
"""
import json
import re
from src.logger import logger
from src.models import Job
from src.ai_engine import call_ai_scoring_async


# ── Boilerplate stripping regex patterns ──
BOILERPLATE_PATTERNS = [
    r'(?i)(?:^|\n)\s*(?:about\s+(?:us|the\s+company|our\s+company)).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:company\s+(?:overview|description|profile)).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:benefits|perks|what\s+we\s+offer|compensation|what\s+you.*?get).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:equal\s+opportunity|diversity|eeo|we\s+are\s+an?\s+equal).*',
    r'(?i)(?:^|\n)\s*(?:disclaimer|note\s*:?\s*this).*',
    r'(?i)(?:^|\n)\s*(?:life\s+at|why\s+join\s+us|our\s+culture|covid).*?(?=\n\s*(?:[A-Z]|\Z))',
]

# ── Zero-Token Keyword Relevance Filter ──
# A JD must contain at least 2 of these keywords to be sent to AI.
# This prevents wasting tokens on completely irrelevant jobs.
CORE_STACK_KEYWORDS = [
    'java', 'python', 'sql', 'selenium', 'postman', 'junit', 'pytest',
    'automation', 'qa', '.net', 'c#', 'asp.net', 'spring', 'jdbc',
    'rest api', 'backend', 'testing', 'test case', 'api testing',
    'html', 'css', 'javascript', 'full stack', 'software engineer',
    'developer', 'agile', 'git', 'mysql', 'mongodb', 'docker',
]
MIN_KEYWORD_MATCHES = 2


def strip_boilerplate(description: str) -> str:
    """
    Aggressively strip HR boilerplate from a job description to reduce token cost.
    Targets: About Us, Benefits, EEO statements, company overviews.
    """
    cleaned = description
    for pattern in BOILERPLATE_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
    # Collapse excessive whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else description  # Fallback to original if stripped too aggressively


def is_relevant_jd(description: str) -> bool:
    """
    Zero-token relevance check: ensures the JD contains at least
    MIN_KEYWORD_MATCHES of the candidate's core stack keywords.
    Returns True if the JD is worth sending to AI.
    """
    desc_lower = description.lower()
    matches = sum(1 for kw in CORE_STACK_KEYWORDS if kw in desc_lower)
    return matches >= MIN_KEYWORD_MATCHES


import asyncio

def score_jobs(jobs: list[Job], test_mode=False) -> list[Job]:
    """
    Scores jobs using DeepSeek with thinking DISABLED.
    Uses asyncio to process all API calls concurrently.
    """
    # Filter irrelevant jobs synchronously first
    relevant_jobs = []
    skipped_irrelevant = 0
    total = len(jobs)
    
    for job in jobs:
        if not is_relevant_jd(job.description):
            skipped_irrelevant += 1
            continue
        relevant_jobs.append(job)
        
    logger.info(f"🧠 Starting AI scoring for {len(relevant_jobs)} relevant jobs concurrently (skipped {skipped_irrelevant})...")

    # The async scoring logic for a single job
    async def process_job(idx: int, job: Job):
        stripped_desc = strip_boilerplate(job.description)
        user_prompt = (
            f"Score this candidate against the following job:\n\n"
            f"Job Title: {job.title}\n"
            f"Company: {job.company}\n"
            f"Location: {job.location}\n\n"
            f"Job Description:\n{stripped_desc}"
        )

        try:
            from src.ai_engine import call_ai_scoring_async
            response_text = await call_ai_scoring_async(user_prompt)

            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                logger.warning(f"   ⚠️ Could not parse JSON for {job.company}.")
                return None

            result = json.loads(response_text[start_idx:end_idx])

            job.score = result.get("match_score", result.get("score", 0))
            job.missing_skills = result.get("missing_skills", [])
            
            # Phase 2 JD Compression: store extracted requirements on the job object
            job.extracted_requirements = result.get("extracted_requirements", "")
            job.is_testing_role = result.get("is_testing_role", False)

            logger.debug(f"   → [{idx+1}/{len(relevant_jobs)}] Score: {job.score}% | QA: {job.is_testing_role} | Missing: {', '.join(job.missing_skills[:3])}...")
            return job

        except Exception as e:
            logger.error(f"   ❌ Error scoring job {job.company}: {e}")
            return None

    # Run all jobs concurrently
    async def run_all():
        tasks = [process_job(i, job) for i, job in enumerate(relevant_jobs)]
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(run_all())
    
    scored_jobs = [j for j in results if j is not None and not isinstance(j, Exception)]

    # Sort by score descending
    scored_jobs.sort(key=lambda j: j.score or 0, reverse=True)

    logger.info(f"📊 Scoring Summary: {len(scored_jobs)} scored, {skipped_irrelevant} skipped (irrelevant)")

    if test_mode:
        return scored_jobs

    # Filter 50%+
    filtered = [j for j in scored_jobs if j.score and j.score >= 50]
    logger.info(f"✅ Scoring complete. {len(filtered)} jobs scored 50% or above.")

    return filtered