"""
AI Scoring Engine for Standalone Dashboard.

Supports:
- Google Gemini (gemini-3.5-flash-lite) ["Germany"]
- Groq (qwen/qwen3.8-27b) ["Croc"]

Enforces client-side rate limits:
- Gemini: <= 15 RPM (min interval 4.0s)
- Groq:   <= 20 RPM (min interval 3.0s)

Includes automatic retries with exponential backoff on 429/503.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from standalone_dashboard.rate_limiter import AsyncRateLimiter

load_dotenv()

logger = logging.getLogger("dashboard_engine")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [AI_ENGINE] %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


class ScoringResult(BaseModel):
    """Normalized scoring outcome for a single job description."""
    fit_score: int = Field(ge=0, le=100, description="Score from 0 to 100")
    is_testing_role: bool = Field(default=False, description="True if QA/SDET/Testing")
    missing_skills: List[str] = Field(default_factory=list, description="Genuine missing skills")
    reasoning: str = Field(default="", description="1-line concise reason")
    
    # Metadata fields
    provider: str = Field(default="unknown")
    model: str = Field(default="")
    latency_seconds: float = Field(default=0.0)
    decision: str = Field(default="REJECTED")  # ACCEPTED or REJECTED
    threshold_used: int = Field(default=60)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map match_score -> fit_score
            if "fit_score" not in data and "match_score" in data:
                data["fit_score"] = data["match_score"]
            elif "match_score" not in data and "fit_score" in data:
                data["match_score"] = data["fit_score"]

            # Map reason -> reasoning
            if "reasoning" not in data and "reason" in data:
                data["reasoning"] = data["reason"]
            elif "reason" not in data and "reasoning" in data:
                data["reason"] = data["reasoning"]

            try:
                data["fit_score"] = int(round(float(data.get("fit_score", 0))))
            except Exception:
                data["fit_score"] = 0

            # Normalize is_testing_role
            val = data.get("is_testing_role", False)
            if isinstance(val, str):
                data["is_testing_role"] = val.strip().lower() in ("true", "1", "yes")
            else:
                data["is_testing_role"] = bool(val)

            # Normalize missing_skills
            ms = data.get("missing_skills", [])
            if isinstance(ms, str):
                data["missing_skills"] = [s.strip() for s in ms.split(",") if s.strip()]
            elif not isinstance(ms, list):
                data["missing_skills"] = []

        return data

    @property
    def single_line_reason(self) -> str:
        return self.reasoning.strip() or "No specific reason provided."


def extract_json_str(text: str) -> str:
    """Robustly extract JSON string from LLM responses."""
    if not text:
        return "{}"
    cleaned = text.strip()

    # 1. Check markdown fences
    fences = re.finditer(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", cleaned, re.IGNORECASE)
    for m in fences:
        candidate = m.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    # 2. Direct JSON check
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        pass

    # 3. Balanced braces raw decode
    start_idx = cleaned.find("{")
    decoder = json.JSONDecoder()
    while start_idx != -1:
        try:
            _, end_pos = decoder.raw_decode(cleaned[start_idx:])
            candidate = cleaned[start_idx : start_idx + end_pos]
            return candidate
        except Exception:
            start_idx = cleaned.find("{", start_idx + 1)

    # 4. Outermost braces fallback
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx > start_idx:
        candidate = cleaned[start_idx : end_idx + 1]
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    return "{}"


# Candidate Master Profile cached representation
DEFAULT_CANDIDATE_SUMMARY = """
Name: Kaustubh Sanjay Kale
Education: Bachelor of Engineering in IT (2026, SKNSITS Lonavala)
Possesses: Core Java, Spring Boot, JDBC, REST APIs, SQL, Maven, Selenium WebDriver, JUnit, Postman, pytest, Manual & Automation Testing, Test Case Design, Python, Pandas, Asyncio, AI/LLM automation pipelines, C#, Azure Fundamentals Certified, JavaScript, TypeScript, React, Node.js, HTML/CSS, Git, Docker, Kubernetes basics.
Target Roles: Entry-level / Fresher (0-2 years) in:
1. Java Backend Developer (Spring Boot, REST APIs, SQL)
2. QA Automation Engineer / SDET / Software Tester (Selenium, Postman, pytest)
3. Full Stack Developer / MERN Stack
4. AI / Automation Engineer (Python, LLMs, Web scraping)
5. .NET / C# Developer
"""


class StandaloneScoringEngine:
    """
    Unified scoring engine for the standalone dashboard.
    Coordinates Gemini ('Germany') and Groq ('Croc').
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        gemini_model: str = "gemini-3.5-flash-lite",
        groq_model: str = "qwen/qwen3.8-27b",
        gemini_rpm: float = 15.0,
        gemini_min_interval: float = 4.0,
        groq_rpm: float = 20.0,
        groq_min_interval: float = 3.0,
        default_threshold: int = 60,
    ):
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")

        self.gemini_model = gemini_model
        self.groq_model = groq_model
        self.default_threshold = default_threshold

        # Rate Limiters
        self.gemini_limiter = AsyncRateLimiter(rpm=gemini_rpm, min_interval=gemini_min_interval, name="Gemini")
        self.groq_limiter = AsyncRateLimiter(rpm=groq_rpm, min_interval=groq_min_interval, name="Groq")

        # Clients (Lazy-loaded)
        self._gemini_client = None
        self._groq_client = None

        # Load candidate master resume if present
        self.candidate_context = self._load_resume_context()

    def update_keys(self, gemini_key: Optional[str] = None, groq_key: Optional[str] = None):
        """Update API keys at runtime from UI."""
        if gemini_key:
            self.gemini_api_key = gemini_key.strip()
            self._gemini_client = None
        if groq_key:
            self.groq_api_key = groq_key.strip()
            self._groq_client = None

    def _load_resume_context(self) -> str:
        project_root = Path(__file__).resolve().parent.parent
        resume_yaml = project_root / "data_folder" / "plain_text_resume.yaml"
        if resume_yaml.exists():
            try:
                with open(resume_yaml, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    return json.dumps(data, indent=2)
            except Exception as e:
                logger.warning(f"Failed loading resume YAML: {e}")
        return DEFAULT_CANDIDATE_SUMMARY

    def _build_prompt(self, title: str, company: str, jd_text: str) -> str:
        return f"""You are a precise, objective ATS scoring engine evaluating an entry-level / fresher candidate.

=== CANDIDATE MASTER PROFILE ===
{self.candidate_context}
================================

=== TARGET CANDIDATE ROLES ===
1. Java Backend Developer (Core Java, Spring Boot, REST APIs, SQL, Maven)
2. QA Automation Engineer / SDET / Software Tester (Selenium, Postman, pytest, JUnit, Test Case Design)
3. Full Stack Developer / MERN Stack (React, Node.js, Express, MongoDB)
4. AI / Python Automation Engineer (Python, LLM APIs, Asyncio, Scraping)
5. .NET / C# Developer (C# OOP, Azure Fundamentals Certified)

=== SCORING RULES (0 to 100) ===
- STRONG MATCH (75–95): Entry-level / fresher roles in Java/Spring, QA Automation (Selenium/pytest/Postman), MERN, Python/AI Automation. Generous scoring for strong fundamentals. Do not penalize for missing niche secondary tools.
- MODERATE / ADJACENT (55–74): Junior .NET/C# roles, Junior Data Engineering, or mixed stacks where candidate has transferable OOP/SQL skills.
- LOW / PARTIAL (25–54): Pure DevOps/Cloud roles requiring deep Terraform/AWS/K8s infrastructure.
- MISMATCH / SENIORITY EXCLUSION (0–24): Roles requiring 3+ or 5+ mandatory years of professional industry experience, out-of-scope stacks (PHP, iOS/Swift, SAP ABAP), or non-technical roles (Sales, HR).

=== TESTING ROLE CLASSIFICATION ===
- `is_testing_role: true` IF AND ONLY IF job is primarily QA, Automation Testing, SDET, Manual Tester. Otherwise false.

=== MISSING SKILLS ===
Candidate already has: Java, Python, SQL, C#, JavaScript, TypeScript, React, Node.js, MongoDB, Spring Boot, JDBC, Selenium, Postman, pytest, JUnit, Git, Docker, Kubernetes basics.
NEVER list the above skills as missing. ONLY list hard technical skills required by JD that candidate lacks (e.g., Kafka, Redis, AWS, C++, Angular).

=== JOB TO EVALUATE ===
Title: {title}
Company: {company}
Description:
{jd_text[:4000]}

=== OUTPUT FORMAT ===
Return ONLY a valid JSON object matching this schema:
{{
  "fit_score": <integer 0-100>,
  "is_testing_role": <true or false>,
  "missing_skills": [<string>, ...],
  "reasoning": <concise single-line explanation in 10-25 words>
}}
Do NOT output markdown commentary or conversational text. Output pure JSON only.
"""

    def _get_gemini_client(self):
        if not self._gemini_client:
            if not self.gemini_api_key:
                raise ValueError("Gemini API key is not configured.")
            from google import genai
            self._gemini_client = genai.Client(api_key=self.gemini_api_key)
        return self._gemini_client

    def _get_groq_client(self):
        if not self._groq_client:
            if not self.groq_api_key:
                raise ValueError("Groq API key is not configured.")
            from openai import OpenAI
            self._groq_client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=self.groq_api_key)
        return self._groq_client

    def _call_gemini_sync(self, prompt: str, model: str) -> str:
        """Execute synchronous Gemini call in threadpool."""
        from google.genai import types
        client = self._get_gemini_client()
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        )
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=cfg,
        )
        return resp.text or ""

    def _call_groq_sync(self, prompt: str, model: str) -> str:
        """Execute synchronous Groq call in threadpool."""
        client = self._get_groq_client()
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict ATS scoring engine for entry-level candidates. "
                    "Output ONLY valid JSON: {\"fit_score\": int, \"is_testing_role\": bool, "
                    "\"missing_skills\": [str], \"reasoning\": str}. No markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    async def score_with_gemini(
        self,
        title: str,
        company: str,
        jd_text: str,
        threshold: int = 60,
        max_retries: int = 3,
    ) -> ScoringResult:
        """Score a job using Gemini with rate limiting and exponential backoff."""
        prompt = self._build_prompt(title, company, jd_text)
        last_err = None

        for attempt in range(max_retries + 1):
            try:
                waited = await self.gemini_limiter.acquire()
                if waited > 0:
                    logger.debug(f"[Gemini] Paced request, waited {waited:.2f}s")

                t0 = time.perf_counter()
                raw_text = await asyncio.to_thread(self._call_gemini_sync, prompt, self.gemini_model)
                latency = round(time.perf_counter() - t0, 2)

                clean_json = extract_json_str(raw_text)
                parsed = json.loads(clean_json)
                result = ScoringResult.model_validate(parsed)
                result.provider = "Gemini"
                result.model = self.gemini_model
                result.latency_seconds = latency
                result.threshold_used = threshold
                result.decision = "ACCEPTED" if result.fit_score >= threshold else "REJECTED"
                return result

            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                is_retryable = any(k in err_str for k in ("429", "503", "rate limit", "resource_exhausted", "quota", "unavailable", "timeout"))
                if not is_retryable or attempt == max_retries:
                    logger.error(f"[Gemini] Error (attempt {attempt+1}/{max_retries+1}): {e}")
                    raise
                backoff = (2 ** attempt) * 2.0 + random.uniform(0.1, 1.0)
                logger.warning(f"[Gemini] Rate-limited/Unavailable ({e}). Backoff {backoff:.2f}s...")
                await asyncio.sleep(backoff)

        raise last_err

    async def score_with_groq(
        self,
        title: str,
        company: str,
        jd_text: str,
        threshold: int = 60,
        max_retries: int = 3,
    ) -> ScoringResult:
        """Score a job using Groq with rate limiting and exponential backoff."""
        prompt = self._build_prompt(title, company, jd_text)
        last_err = None

        for attempt in range(max_retries + 1):
            try:
                waited = await self.groq_limiter.acquire()
                if waited > 0:
                    logger.debug(f"[Groq] Paced request, waited {waited:.2f}s")

                t0 = time.perf_counter()
                raw_text = await asyncio.to_thread(self._call_groq_sync, prompt, self.groq_model)
                latency = round(time.perf_counter() - t0, 2)

                clean_json = extract_json_str(raw_text)
                parsed = json.loads(clean_json)
                result = ScoringResult.model_validate(parsed)
                result.provider = "Groq"
                result.model = self.groq_model
                result.latency_seconds = latency
                result.threshold_used = threshold
                result.decision = "ACCEPTED" if result.fit_score >= threshold else "REJECTED"
                return result

            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                is_retryable = any(k in err_str for k in ("429", "503", "rate limit", "too many requests", "unavailable", "timeout"))
                if not is_retryable or attempt == max_retries:
                    logger.error(f"[Groq] Error (attempt {attempt+1}/{max_retries+1}): {e}")
                    raise
                
                # Check for explicit Groq retry wait in error string
                retry_wait = None
                m = re.search(r"try again in ([0-9.]+)s", str(e), re.IGNORECASE)
                if m:
                    try:
                        retry_wait = float(m.group(1)) + 1.0
                    except ValueError:
                        pass

                backoff = retry_wait if retry_wait is not None else ((2 ** attempt) * 2.0 + random.uniform(0.1, 1.0))
                logger.warning(f"[Groq] Rate-limited ({e}). Backoff {backoff:.2f}s...")
                await asyncio.sleep(backoff)

        raise last_err

    async def score_job(
        self,
        title: str,
        company: str,
        jd_text: str,
        mode: str = "load_balanced",  # 'load_balanced', 'gemini', 'groq', 'failover'
        threshold: int = 60,
        preferred_provider: str = "gemini",
    ) -> ScoringResult:
        """
        Evaluate a single job with the requested mode:
        - 'load_balanced': Round-robined by the caller or preferred_provider
        - 'gemini': Gemini only
        - 'groq': Groq only
        - 'failover': Try Gemini first, fallback to Groq on error
        """
        if mode == "gemini":
            return await self.score_with_gemini(title, company, jd_text, threshold)
        elif mode == "groq":
            return await self.score_with_groq(title, company, jd_text, threshold)
        elif mode == "failover":
            try:
                return await self.score_with_gemini(title, company, jd_text, threshold)
            except Exception as e:
                logger.warning(f"[Failover] Gemini failed ({e}), attempting Groq fallback...")
                return await self.score_with_groq(title, company, jd_text, threshold)
        else:
            # load_balanced: uses preferred_provider, with auto-failover if one fails
            try:
                if preferred_provider == "groq":
                    return await self.score_with_groq(title, company, jd_text, threshold)
                else:
                    return await self.score_with_gemini(title, company, jd_text, threshold)
            except Exception as primary_err:
                fallback_prov = "groq" if preferred_provider != "groq" else "gemini"
                logger.warning(f"[{preferred_provider.capitalize()}] failed ({primary_err}). Auto-failover to {fallback_prov.capitalize()}...")
                if fallback_prov == "groq":
                    return await self.score_with_groq(title, company, jd_text, threshold)
                else:
                    return await self.score_with_gemini(title, company, jd_text, threshold)
