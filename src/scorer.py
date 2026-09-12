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
async def call_ai_scoring_async(*args, **kwargs):
    """Delegate to src.ai_engine.call_ai_scoring_async dynamically to support patching either module."""
    import src.ai_engine as _ai
    return await _ai.call_ai_scoring_async(*args, **kwargs)


class ScoredJobList(list):
    """
    List of filtered/shortlisted jobs that retains all scored jobs
    for full token and cost telemetry accounting.
    """
    def __init__(self, iterable=(), all_scored_jobs=None):
        super().__init__(iterable)
        self.all_scored_jobs = all_scored_jobs if all_scored_jobs is not None else []

    def __getitem__(self, item):
        res = super().__getitem__(item)
        if isinstance(item, slice):
            return ScoredJobList(res, all_scored_jobs=self.all_scored_jobs)
        return res


_LAST_SCORED_JOBS: list[Job] = []


def get_last_scored_jobs() -> list[Job]:
    """Retrieve the complete list of jobs scored during the most recent run."""
    global _LAST_SCORED_JOBS
    return list(_LAST_SCORED_JOBS)


# ── Boilerplate stripping regex patterns ──
BOILERPLATE_PATTERNS = [
    r'(?i)(?:^|\n)\s*(?:about\s+(?:us|the\s+company|our\s+company)).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:company\s+(?:overview|description|profile)).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:benefits|perks|what\s+we\s+offer|compensation|what\s+you.*?get).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:equal\s+opportunity|diversity|eeo|we\s+are\s+an?\s+equal).*?(?=(?:\n\s*(?:technical\s+requirements|requirements|responsibilities|qualifications|skills|job\s+description|[A-Z][A-Za-z0-9\s/]+:))|\Z)',
    r'(?i)(?:^|\n)\s*(?:disclaimer|note\s*:?\s*this).*?(?=(?:\n\s*(?:technical\s+requirements|requirements|responsibilities|qualifications|skills|job\s+description|[A-Z][A-Za-z0-9\s/]+:))|\Z)',
    r'(?i)(?:^|\n)\s*(?:life\s+at|why\s+join\s+us|our\s+culture|covid).*?(?=\n\s*(?:[A-Z]|\Z))',
]

# ── Zero-Token Domain-Anchored Keyword Relevance Filter ──
DOMAIN_ANCHORS = [
    'java', 'python', 'qa', 'selenium', 'automation',
    '.net', 'c#', 'csharp', 'asp.net', 'spring', 'full stack', 'fullstack',
    'sdet', 'quality assurance', 'postman', 'pytest', 'junit',
    'playwright', 'cypress', 'tester', 'manual testing', 'automation testing',
    'software testing', 'api testing', 'test automation', 'test case', 'test cases',
    'test suite', 'test plan', 'test engineer'
]
TECH_TOOLS = [
    'spring', 'sql', 'pytest', 'postman', 'junit', 'rest api', 'api', 'react',
    'javascript', 'html', 'css', 'mysql', 'mongodb', 'docker', 'git', 'jdbc',
    'azure', 'c#', 'java', 'python', 'selenium', 'automation', 'database',
    'oops', 'oop', 'microservices', 'django', 'flask', 'node', 'test', 'qa'
]

CORE_STACK_KEYWORDS = [
    'java', 'python', 'sql', 'selenium', 'postman', 'junit', 'pytest',
    'automation', 'qa', '.net', 'c#', 'asp.net', 'spring', 'jdbc',
    'rest api', 'backend', 'testing', 'test case', 'api testing',
    'html', 'css', 'javascript', 'full stack', 'software engineer',
    'developer', 'agile', 'git', 'mysql', 'mongodb', 'docker',
]
MIN_KEYWORD_MATCHES = 2

OUT_OF_SCOPE_STACK_PATTERN = re.compile(
    r'\b(?:php|laravel|ruby|rails|ios|swift|swiftui|android|kotlin|flutter|react\s+native|salesforce|apex|sap|abap|drupal|magento|wordpress)\b',
    re.IGNORECASE
)


def matches_out_of_scope_role(title: str = "", description: str = "") -> bool:
    """
    Returns True if the title or description indicates an out-of-scope technology stack
    (e.g., PHP, Ruby on Rails, iOS, Android, Flutter, React Native, Salesforce, SAP).
    These should never be sent to AI scoring for our target fresher profile.
    """
    if title and OUT_OF_SCOPE_STACK_PATTERN.search(title):
        return True
    if description and OUT_OF_SCOPE_STACK_PATTERN.search(description):
        return True
    return False


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


def is_relevant_jd(description: str, title: str = "") -> bool:
    """
    Zero-token relevance check: ensures the JD contains at least
    1 core domain anchor and at least 1 technology tool/qualifier,
    and does not belong to an out-of-scope technology stack.
    Prevents wasting AI tokens on completely irrelevant or out-of-scope roles.
    """
    if not description or not isinstance(description, str):
        return False
    desc_lower = description.lower()

    # Reject out-of-scope stacks immediately
    if OUT_OF_SCOPE_STACK_PATTERN.search(desc_lower):
        return False
    if title and OUT_OF_SCOPE_STACK_PATTERN.search(title):
        return False

    has_anchor = any(kw in desc_lower for kw in DOMAIN_ANCHORS)
    has_tool = any(kw in desc_lower for kw in TECH_TOOLS)
    return has_anchor and has_tool



def matches_senior_title(title: str) -> bool:
    """
    Returns True if job title indicates a senior/lead/managerial role or
    explicitly requires >= 3 years of experience in the title.
    Preserves genuine entry-level, junior, associate, graduate, trainee, and 0-2 / 1-3 year jobs.
    """
    if not title or not isinstance(title, str):
        return False
    title_lower = title.lower()

    # 1. Senior role keywords with appropriate boundaries (including Roman numerals II-VIII, Level 2-9, L2-9)
    senior_keywords_pattern = (
        r'\b(?:senior|lead|manager|principal|director|head|vp|president|experienced|'
        r'architect|staff|expert|ii|iii|iv|v|vi|vii|viii|level\s*[2-9]|l[2-9])\b|\bsr[\.,\s]|\bsr$'
    )
    if re.search(senior_keywords_pattern, title_lower):
        return True

    # 2. Explicit experience ranges in title: e.g. "3-5 years", "3 to 5 yrs", "4-10 yrs"
    # Preserves entry-level ranges like "0-2 years", "0-3 yrs", "1-3 years"
    range_title_pat = r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(range_title_pat, title_lower):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # 3. Explicit single experience requirements in title: e.g. "5+ years", "5+yrs", "3+ yoe", "3-6 years"
    single_title_pat = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(single_title_pat, title_lower):
        num = int(m.group(1))
        has_plus = bool(re.search(r'\+|or more|more than|plus', m.group(0)))
        if has_plus and num >= 3:
            return True
        if num >= 3 and not re.search(r'\b[012]\s*[-\u2013to]+\s*' + str(num), title_lower):
            return True

    # 4. Word-based experience in title (e.g. "three to five years")
    words_to_num = {
        'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
        'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
    }
    words_list = '|'.join(words_to_num.keys())
    word_title_pat = fr'\b({words_list})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b'
    for m in re.finditer(word_title_pat, title_lower):
        matched_word = m.group(1)
        if words_to_num.get(matched_word, 0) >= 3:
            preceding = title_lower[:m.start()]
            if re.search(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014)\s*$', preceding):
                continue
            return True

    return False


def requires_3_plus_years(desc: str) -> bool:
    """
    Returns True if the JD requires 3+ years of CANDIDATE experience.
    Safeguards:
    - Strips third-party/company/team experience sentences.
    - Preserves 0-1, 0-2, 0-3, 1-2, 1-3 year jobs (1-3 years is NEVER dropped).
    - Checks upper bounds only when lower bound indicates non-entry level (lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5).
    - Checks single number requirements with '+' or candidate experience context.
    """
    if not isinstance(desc, str):
        return False
    desc_lower = desc.lower().replace('\\', '')

    # Step 1: Strip third-party / company / team experience sentences
    third_party_prefixes = (
        r'(?:our|the)\s+team\s+(?:has|have|with|of)',
        r'(?:work|working)\s+(?:with|alongside|beside|among)',
        r'(?:join|joining)\s+(?:a\s+)?team\s+(?:of|with)',
        r'(?:founded|established|started|operating|running)\s+(?:in|since|for|with)',
        r'(?:we\s+have|company\s+has|firm\s+has)\s+(?:over|more\s+than|been)',
        r'(?:our\s+company|our\s+firm|our\s+organisation)\s+(?:has|have)',
        r'colleagues?\s+(?:with|who\s+have)',
        r'mentors?\s+(?:with|who\s+have)',
        r'mentorship\s+from',
        r'(?:learn|learning)\s+from',
        r'(?:combined|collective|total)\s+experience',
        r'(?:history|heritage|industry)\s+(?:of|spanning)',
        r'(?:team|group|pool)\s+of\s+(?:engineers?|developers?|professionals?)\s+with',
        r'(?:senior\s+)?engineers?\s+(?:who\s+have|with\s+over)',
        r'in\s+\d{4}\s+with\s+\d+\s+years',
    )
    sentences = re.split(r'(?<=[.!?\n])\s*', desc_lower)
    candidate_sentences = [
        sent for sent in sentences
        if not any(re.search(pat, sent) for pat in third_party_prefixes)
    ]
    candidate_text = ' '.join(candidate_sentences)

    # Step 2: Experience range check (X-Y years, digits or words)
    words_to_num_all = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12
    }
    def _tok_to_val(tok: str) -> int:
        tok_clean = tok.lower().strip()
        if tok_clean.isdigit():
            return int(tok_clean)
        return words_to_num_all.get(tok_clean, 0)

    num_tokens = r'(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'
    range_sep = r'(?:[-\u2013\u2014]|to|till|and)'
    range_pattern = fr'\b({num_tokens})\s*(?:\([^\)]+\)\s*)?{range_sep}\s*({num_tokens})\s*(?:\([^\)]+\)\s*)?(?:\+|or more|plus)?\s*(?:years?|yrs?\.?|yoe)\b'
    for m in re.finditer(range_pattern, candidate_text):
        lo, hi = _tok_to_val(m.group(1)), _tok_to_val(m.group(2))
        # Keep 0-1, 0-2, 0-3, 1-2, 1-3, 2-3
        # Drop if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # Strip ranges before checking single numbers so second number (e.g. 3 in 1-3 or 'three' in 'one to three') is not re-matched
    candidate_noranges = re.sub(range_pattern, ' ', candidate_text)

    # Step 3: Single number + '+' or 'or more' (e.g. 3+ years, 5+ yrs)
    plus_pattern = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than|plus)\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(plus_pattern, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return True

    # Step 4: 'minimum/at least X years'
    min_pattern = r'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?\.?)?'
    for m in re.finditer(min_pattern, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return True

    # Step 5: Single number with candidate experience context
    single_exp_pattern = r'(?<![-\u2013\d])\b(\d+)\s*(?:years?|yrs?\.?)\s*(?:of\s+)?(?:experience|exp|hands[- ]on|relevant|background|industry|work)?'
    for m in re.finditer(single_exp_pattern, candidate_noranges):
        num = int(m.group(1))
        # Avoid false positives like degree duration '3 years degree', '3 years bond'
        if re.search(r'degree|bachelor|diploma|bond|agreement|contract|commitment|lock-in|warranty|course', candidate_text[max(0, m.start()-20):min(len(candidate_text), m.end()+20)]):
            continue
        if 3 <= num <= 25:
            return True

    # Step 6: 'X yrs' shorthand
    yrs_pattern = r'(?<![-\u2013\d])\b(\d+)\s+yrs?\b'
    for m in re.finditer(yrs_pattern, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return True

    # Step 7: Word-based ('three to five years')
    words_to_num = {
        'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
        'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
    }
    words_list = '|'.join(words_to_num.keys())
    word_pattern = fr'\b({words_list})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b'
    for m in re.finditer(word_pattern, candidate_noranges):
        matched_word = m.group(1)
        if words_to_num.get(matched_word, 0) >= 3:
            preceding = candidate_noranges[:m.start()]
            if re.search(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014|till|and|or)\s*$', preceding):
                continue
            return True

    return False


def apply_pandas_filter(*args, **kwargs):
    """Convenience delegate for apply_pandas_filter to ensure interface contract compliance."""
    from src.scraper import apply_pandas_filter as _apf
    return _apf(*args, **kwargs)


import asyncio

def score_jobs(jobs: list[Job], test_mode=False, callbacks=None, stop_event=None) -> list[Job]:
    """
    Scores jobs using DeepSeek with thinking DISABLED.
    Uses asyncio to process all API calls concurrently.
    """
    from src.config_loader import load_config
    import pandas as pd
    config = load_config()
    hours_old = config.get('search', {}).get('hours_old', 72)
    cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=hours_old)

    # 1. Freshness filter respecting configured hours_old (default 72h)
    fresh_jobs = []
    skipped_stale = 0
    for job in jobs:
        date_posted = getattr(job, 'date_posted', None)
        if date_posted is not None:
            try:
                dt = pd.to_datetime(date_posted, errors='coerce', utc=True)
                if pd.notna(dt) and dt < cutoff:
                    skipped_stale += 1
                    continue
            except Exception:
                pass
        fresh_jobs.append(job)

    # 2. Filter irrelevant and senior jobs synchronously first (zero wasted AI calls)
    relevant_jobs = []
    skipped_irrelevant = 0
    total = len(jobs)
    
    for job in fresh_jobs:
        if (
            matches_senior_title(job.title)
            or matches_out_of_scope_role(job.title, job.description)
            or requires_3_plus_years(job.description)
            or not is_relevant_jd(job.description, job.title)
        ):
            skipped_irrelevant += 1
            continue
        relevant_jobs.append(job)

    if test_mode:
        # Small-batch test mode: limit to scoring top 3 relevant jobs
        relevant_jobs = relevant_jobs[:3]
        
    logger.info(f"🧠 Starting AI scoring for {len(relevant_jobs)} relevant jobs concurrently (skipped {skipped_irrelevant} irrelevant, {skipped_stale} stale)...")

    # The async scoring logic for a single job
    async def process_job(idx: int, job: Job):
        if stop_event and stop_event.is_set():
            return None
        job_id = job.id
        if callbacks and "on_score_start" in callbacks:
            callbacks["on_score_start"](job_id, job.title, job.company)

        # Check JD Cache First (skip for manual tailor requests with no URL)
        has_url = bool(job.url and job.url.strip())
        norm_url = job.url.split('?')[0].strip() if has_url else ""
        try:
            from src.db import get_cached_jd_score, save_jd_cache
            if has_url:
                cached = get_cached_jd_score(norm_url)
                if cached:
                    raw_cached_score = cached.get('score', 0)
                    try:
                        job.score = int(float(raw_cached_score))
                    except (ValueError, TypeError):
                        job.score = 0
                    job.missing_skills = cached.get('missing_skills', [])
                    
                    raw_req = cached.get('extracted_requirements', '')
                    if '|||REASON|||' in raw_req:
                        req_parts = raw_req.split('|||REASON|||')
                        job.extracted_requirements = req_parts[0]
                        job.reasons = req_parts[1]
                    else:
                        job.extracted_requirements = raw_req
                        job.reasons = ""
                        
                    job.is_testing_role = cached.get('is_testing_role', False)
                    job.tokens_used = 0
                    job.cost_usd = 0.0
                    logger.debug(f"   -> [{idx+1}/{len(relevant_jobs)}] (CACHED) Score: {job.score}%")
                    if callbacks and "on_score_complete" in callbacks:
                        callbacks["on_score_complete"](job_id, job.score, job.reasons)
                    return job
        except Exception as ce:
            logger.debug(f"Cache check failed: {ce}")

        stripped_desc = strip_boilerplate(job.description)
        user_prompt = (
            f"Score this candidate against the following job:\n\n"
            f"Job Title: {job.title}\n"
            f"Company: {job.company}\n"
            f"Location: {job.location}\n\n"
            f"Job Description:\n{stripped_desc}"
        )

        try:
            response_text, tokens = await call_ai_scoring_async(user_prompt)
            if stop_event and stop_event.is_set():
                return None

            if isinstance(tokens, dict):
                tokens_count = tokens.get("total_tokens", 0)
                cost = tokens.get("cost_usd", 0.0)
                job.tokens_used = getattr(job, 'tokens_used', 0) + tokens_count
                job.cost_usd = getattr(job, 'cost_usd', 0.0) + cost
                job.token_usage = dict(tokens)
            elif isinstance(tokens, (int, float)):
                job.tokens_used = getattr(job, 'tokens_used', 0) + int(tokens)
                job.cost_usd = getattr(job, 'cost_usd', 0.0)

            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                logger.warning(f"   ⚠️ Could not parse JSON for {job.company}.")
                return None

            result = json.loads(response_text[start_idx:end_idx])
            raw_score = result.get("match_score", result.get("score", 0))
            try:
                job.score = int(float(raw_score))
            except (ValueError, TypeError):
                job.score = 0
            job.missing_skills = result.get("missing_skills", [])
            job.reasons = result.get("reason", "")
            job.job_summary = result.get("job_summary", "")
            
            # Phase 2 JD Compression: store extracted requirements on the job object
            job.extracted_requirements = result.get("extracted_requirements", "")
            job.is_testing_role = result.get("is_testing_role", False)
            
            if stop_event and stop_event.is_set():
                return None

            # Save to Cache with normalized URL (skip for manual tailor requests with no URL)
            if has_url:
                try:
                    combined_req = f"{job.extracted_requirements}|||REASON|||{job.reasons}"
                    save_jd_cache(norm_url, job.score, job.missing_skills, combined_req, job.is_testing_role)
                except Exception as ce:
                    logger.debug(f"Save to cache failed: {ce}")

            logger.debug(f"   -> [{idx+1}/{len(relevant_jobs)}] Score: {job.score}% | QA: {job.is_testing_role} | Missing: {', '.join(job.missing_skills[:3])}...")
            
            if callbacks and "on_score_complete" in callbacks:
                if not (stop_event and stop_event.is_set()):
                    callbacks["on_score_complete"](job_id, job.score, job.reasons)
                
            return job

        except Exception as e:
            logger.error(f"   ❌ Error scoring job {job.company}: {e}")
            if callbacks and "on_score_complete" in callbacks:
                callbacks["on_score_complete"](job_id, 0, "")
            return None

    # Run all jobs concurrently with Cache Warming
    async def run_all():
        if not relevant_jobs:
            return []
            
        results = []
        cache_warmed = False
        tasks = []
        
        for i, job in enumerate(relevant_jobs):
            if stop_event and stop_event.is_set():
                break
            if not cache_warmed:
                res = await process_job(i, job)
                results.append(res)
                # If tokens_used > 0, it hit the DeepSeek API and the prompt cache is now warm
                if res and getattr(res, 'tokens_used', 0) > 0:
                    cache_warmed = True
            else:
                tasks.append(process_job(i, job))
                
        if tasks:
            rest_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(rest_results)
            
        return results

    results = asyncio.run(run_all())
    
    scored_jobs = [j for j in results if j is not None and not isinstance(j, Exception)]

    # Sort by score descending
    scored_jobs.sort(key=lambda j: j.score or 0, reverse=True)

    global _LAST_SCORED_JOBS
    _LAST_SCORED_JOBS = list(scored_jobs)

    logger.info(f"📊 Scoring Summary: {len(scored_jobs)} scored, {skipped_irrelevant} skipped (irrelevant)")

    # Filter by minimum score (default threshold: 60)
    from src.config_loader import load_config
    config = load_config()
    min_score = config.get('scoring', {}).get('minimum_score', 60)

    filtered = [j for j in scored_jobs if j.score is not None and j.score >= min_score]
    logger.info(f"✅ Scoring complete. {len(filtered)} jobs scored {min_score}% or above.")

    if test_mode:
        return ScoredJobList(filtered[:3], all_scored_jobs=scored_jobs)

    return ScoredJobList(filtered, all_scored_jobs=scored_jobs)