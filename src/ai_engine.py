"""
AutoApply AI Engine — DeepSeek via OpenAI SDK.

Supports two calling modes:
  - Scoring:  thinking DISABLED (fast, cheap)
  - Tailoring: thinking ENABLED  (deep reasoning, hyper-tailored)

Master resume is pinned as the system prompt to trigger DeepSeek's
$0.0028/1M prompt caching rate.
"""
import json
import asyncio
import random
from openai import OpenAI, AsyncOpenAI, RateLimitError
from src.config_loader import load_config, load_resume
from src.logger import logger


def _get_client() -> tuple[OpenAI, str]:
    """Create a synchronous OpenAI client pointed at the DeepSeek API."""
    config = load_config()
    client = OpenAI(
        api_key=config['ai']['api_key'],
        base_url="https://api.deepseek.com"
    )
    model = config['ai'].get('model', 'deepseek-v4-flash')
    return client, model


_ASYNC_CLIENT = None
_MODEL = None
_MASTER_RESUME = None

def _get_async_client() -> tuple[AsyncOpenAI, str]:
    """Get or create a cached asynchronous OpenAI client."""
    global _ASYNC_CLIENT, _MODEL
    if _ASYNC_CLIENT is None:
        config = load_config()
        _ASYNC_CLIENT = AsyncOpenAI(
            api_key=config['ai']['api_key'],
            base_url="https://api.deepseek.com"
        )
        _MODEL = config['ai'].get('model', 'deepseek-v4-flash')
    return _ASYNC_CLIENT, _MODEL

def _get_master_resume() -> dict:
    """Get or load the cached master resume."""
    global _MASTER_RESUME
    if _MASTER_RESUME is None:
        _MASTER_RESUME = load_resume()
    return _MASTER_RESUME


async def call_ai_scoring_async(user_prompt: str) -> str:
    """
    Call DeepSeek for job scoring concurrently.
    - Thinking mode: DISABLED (maximum speed, minimum tokens)
    - System prompt: master resume pinned at top for prompt caching
    """
    client, model = _get_async_client()
    master_resume = _get_master_resume()
    
    system_prompt = (
        "You are a precise ATS scoring engine for an entry-level/fresher candidate.\n\n"
        "=== CANDIDATE MASTER RESUME (CACHED CONTEXT) ===\n"
        f"{json.dumps(master_resume, indent=2)}\n"
        "=================================================\n\n"
        "=== CANDIDATE TARGET ROLES ===\n"
        "The candidate is targeting these specific domains:\n"
        "1. Java Backend Developer (Spring, JDBC, REST APIs, SQL)\n"
        "2. Automation Tester / QA Automation (Selenium, JUnit, Postman, pytest, Test Case Design)\n"
        "3. .NET / C# Developer (candidate has Azure Fundamentals cert and OOP foundation)\n"
        "4. Software Engineer / Full Stack Developer (Python, JavaScript, HTML/CSS)\n"
        "5. Software Tester / QA Engineer (Manual + Automated Testing)\n\n"
        "=== SCORING RULES (FLEXIBLE & BROAD) ===\n"
        "- Score 0-100 based on how well the candidate's core skills match the primary JD requirements.\n"
        "- Be flexible and practical. We do NOT need a perfect 100% keyword match. If the core domain matches, assign a solid score (50+).\n"
        "- The candidate is a FRESHER. Do NOT heavily penalize them for lacking secondary/advanced tools (like AWS, Docker, Kubernetes, Kafka, CI/CD, JIRA). It is completely acceptable for an entry-level candidate to lack these.\n"
        "- If the JD asks for Automation Testing (Selenium/Postman/pytest) or Java Backend, score HIGH (70-90) as these are strong core matches.\n"
        "- If the JD asks for .NET/C#, score MODERATE (50-70).\n"
        "- ONLY output match_score: 0 if the JD explicitly states 3+ years of mandatory experience, OR if the core language is a complete mismatch (e.g., purely C++ or Ruby).\n\n"
        "Return ONLY a raw JSON object with exactly four keys:\n"
        '- "match_score": integer 0-100\n'
        '- "missing_skills": array of top 5 skills the candidate LACKS for this specific role. missing_skills must only contain hard technical tools (e.g., "Kafka"), not soft skills.\n'
        '- "extracted_requirements": a concise comma-separated string of the core technical stack and domain requirements extracted from the JD.\n'
        '- "is_testing_role": boolean (true if the job is primarily a QA, Testing, SDET, or Automation role, false otherwise).\n\n'
        "CRITICAL RULES:\n"
        "- Do NOT copy-paste any text from the job description.\n"
        "- Do NOT add any explanation, markdown, or code blocks.\n"
        "- Return ONLY the raw JSON object."
    )
    
    try:
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            extra_body={"thinking": {"type": "disabled"}}
        )
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                if attempt == 2:
                    raise
                delay = (2 ** attempt) * 2 + random.uniform(0, 1)
                logger.warning(f"   ⚠️ API Error during scoring ({type(e).__name__}). Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"DeepSeek Scoring API Error: {e}")
        raise


async def call_ai_tailoring_async(user_prompt: str) -> str:
    """
    Call DeepSeek for resume tailoring concurrently.
    - Thinking mode: ENABLED (deep reasoning for hyper-tailored output)
    - System prompt: master resume pinned at top for prompt caching
    """
    client, model = _get_async_client()
    master_resume = _get_master_resume()
    
    system_prompt = (
        "You are an elite, human-level Executive Resume Writer.\n\n"
        "=== MASTER RESUME CONTEXT ===\n"
        f"{json.dumps(master_resume, indent=2)}\n"
        "=============================\n\n"
        "Your task is to DYNAMICALLY ASSEMBLE and REFRAME a highly tailored 1-page resume JSON.\n"
        "Do not simply tweak words. You must prune irrelevant data and surgically reframe the candidate's experience.\n\n"
        "=== THE REFRAMING 'LENS' RULES ===\n"
        "1. Analyze the 'Core Requirements' and 'Job Title' passed in the user message below to determine the Target Role Lens.\n"
        "   - If the Lens is QA/Testing: Focus heavily on validation, edge-case handling, bug lifecycle, and automation frameworks. You MUST extract and emphasize ANY testing or automation logic present in the original projects. If a project is purely development, reframe it to describe the architectural choices that made it testable, or the manual/automated validations performed to ensure 100% accuracy and zero-lag performance.\n"
        "   - If the Lens is Backend/Java: Focus heavily on API architecture, database optimization, scalability, and data logic.\n"
        "2. EXPERIENCE: You MUST include the candidate's 'Java Developer Intern' experience. Rewrite its bullet points entirely through the Target Role Lens.\n"
        "3. PROJECTS: Select ONLY the top 2 projects from the Master Resume that best fit this Lens. Drop all others. Rewrite the project descriptions entirely through this Lens.\n\n"
        "=== STRICT MATHEMATICAL CONSTRAINTS ===\n"
        "1. PROJECTS: Output exactly 2 projects.\n"
        "2. BULLET POINTS: Output exactly 3 bullet points per Project, and exactly 3 bullet points for the Internship Experience. Maximum 20 words per bullet point.\n"
        "3. SUMMARY: The Professional Summary must be exactly two sentences.\n"
        "4. KEYWORD DENSITY: You must inject the top 3 technical requirements from the JD into at least one Experience bullet point, one Project bullet point, and the Professional Summary.\n\n"
        "=== NEGATIVE PROMPTING (WHAT NOT TO DO) ===\n"
        "- Do NOT use weak filler verbs like 'Worked on', 'Responsible for', or 'Assisted in'. Every single bullet must start with a powerful action verb (e.g., Engineered, Validated, Orchestrated, Architected).\n"
        "- Do NOT hallucinate skills or experience the candidate does not have. Only use data present in the Master Resume.\n"
        "- Do NOT wrap your output in markdown formatting. DO NOT output ```json or ``` at the beginning or end. Output RAW JSON text ONLY.\n\n"
        "=== REQUIRED JSON SCHEMA ===\n"
        "You must return a raw JSON object matching EXACTLY this structure and keys:\n"
        "{\n"
        '  "profile_summary": "Your 2-sentence summary here...",\n'
        '  "skills": ["Skill1", "Skill2", "Skill3"],\n'
        '  "experience_details": [\n'
        "    {\n"
        '      "position": "Java Developer Intern",\n'
        '      "company": "CWIPedia Technologies",\n'
        '      "employment_period": "Jan 25 - Feb 25",\n'
        '      "location": "Pune, India",\n'
        '      "industry": "Software Engineering",\n'
        '      "key_responsibilities": [\n'
        '        {"responsibility_1": "Action verb bullet point 1..."},\n'
        '        {"responsibility_2": "Action verb bullet point 2..."},\n'
        '        {"responsibility_3": "Action verb bullet point 3..."}\n'
        "      ]\n"
        "    }\n"
        "  ],\n"
        '  "projects": [\n'
        "    {\n"
        '      "name": "Project 1 Name",\n'
        '      "description": "Action verb bullet 1. Action verb bullet 2. Action verb bullet 3.",\n'
        '      "tech_stack": "Tech Stack string"\n'
        "    },\n"
        "    {\n"
        '      "name": "Project 2 Name",\n'
        '      "description": "Action verb bullet 1. Action verb bullet 2. Action verb bullet 3.",\n'
        '      "tech_stack": "Tech Stack string"\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    
    try:
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            extra_body={"thinking": {"type": "enabled"}}
        )
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                if attempt == 2:
                    raise
                delay = (2 ** attempt) * 3 + random.uniform(0, 1)
                logger.warning(f"   ⚠️ API Error during tailoring ({type(e).__name__}). Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"DeepSeek Tailoring API Error: {e}")
        raise
