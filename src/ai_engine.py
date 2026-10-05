"""
AutoApply AI Engine — Production DeepSeek AI Engine via OpenAI SDK.

Supports:
  - Scoring: DeepSeek-V3 (deepseek-chat) with thinking disabled by default (fast, cheap).
  - Tailoring: DeepSeek-V3 / DeepSeek-Reasoner with thinking enabled by default (deep reasoning, hyper-tailored).

Features:
  - Master resume pinned as system prompt for DeepSeek prompt caching ($0.07 / 1M tokens).
  - Full telemetry tracking with TokenUsage and calculate_deepseek_cost.
  - Multi-attempt exponential backoff retry.
  - Dynamic runtime_settings overrides (used by dashboard and test suite).
  - Safe client lifecycle management.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

from src.config_loader import load_config, load_resume
from src.logger import logger

load_dotenv()

# ── Runtime AI Settings (overridden by dashboard UI and tests) ──
runtime_settings: Dict[str, Any] = {
    "provider": "deepseek",
    "scoring_model": "deepseek-chat",
    "scoring_thinking": False,
    "tailoring_model": "deepseek-chat",
    "tailoring_thinking": True,
}


def calculate_deepseek_cost(
    model: str, cached_tokens: int, miss_tokens: int, completion_tokens: int
) -> float:
    """
    Calculate USD cost per API call using official DeepSeek pricing tiers:
    - deepseek-chat: Cache Hit: $0.07 / 1M, Cache Miss: $0.27 / 1M, Output: $1.10 / 1M
    - deepseek-reasoner: Cache Hit: $0.14 / 1M, Cache Miss: $0.55 / 1M, Output: $2.19 / 1M
    """
    if "reasoner" in (model or "").lower() or "r1" in (model or "").lower():
        cost = (
            (cached_tokens * 0.14 / 1_000_000)
            + (miss_tokens * 0.55 / 1_000_000)
            + (completion_tokens * 2.19 / 1_000_000)
        )
    else:
        cost = (
            (cached_tokens * 0.07 / 1_000_000)
            + (miss_tokens * 0.27 / 1_000_000)
            + (completion_tokens * 1.10 / 1_000_000)
        )
    return round(cost, 8)


class TokenUsage(dict):
    """
    Token and cost telemetry dictionary with arithmetic and comparison support
    for backwards compatibility with integer operations.
    """

    def __int__(self):
        return int(self.get("total_tokens", 0))

    def __add__(self, other):
        return int(self.get("total_tokens", 0)) + int(other)

    def __radd__(self, other):
        return int(other) + int(self.get("total_tokens", 0))

    def __sub__(self, other):
        return int(self.get("total_tokens", 0)) - int(other)

    def __rsub__(self, other):
        return int(other) - int(self.get("total_tokens", 0))

    def __float__(self):
        return float(self.get("total_tokens", 0))

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return self.get("total_tokens", 0) == other
        return super().__eq__(other)

    def __ne__(self, other):
        if isinstance(other, (int, float)):
            return self.get("total_tokens", 0) != other
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.get("total_tokens", 0) < other
        if isinstance(other, TokenUsage):
            return self.get("total_tokens", 0) < other.get("total_tokens", 0)
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, (int, float)):
            return self.get("total_tokens", 0) <= other
        if isinstance(other, TokenUsage):
            return self.get("total_tokens", 0) <= other.get("total_tokens", 0)
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, (int, float)):
            return self.get("total_tokens", 0) > other
        if isinstance(other, TokenUsage):
            return self.get("total_tokens", 0) > other.get("total_tokens", 0)
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return self.get("total_tokens", 0) >= other
        if isinstance(other, TokenUsage):
            return self.get("total_tokens", 0) >= other.get("total_tokens", 0)
        return NotImplemented

    def __mul__(self, other):
        return int(self) * other

    def __rmul__(self, other):
        return other * int(self)

    def __truediv__(self, other):
        return int(self) / other

    def __floordiv__(self, other):
        return int(self) // other


def _get_api_key() -> str:
    """Fetch DeepSeek API key from environment or config."""
    config = load_config()
    api_key = os.environ.get("DEEPSEEK_API_KEY") or config.get("ai", {}).get("api_key", "")
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY is not set in environment or config.yaml."
        )
    return api_key


def _get_client() -> tuple[OpenAI, str]:
    """Create a synchronous OpenAI client pointed at the DeepSeek API."""
    config = load_config()
    api_key = _get_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )
    model = (
        runtime_settings.get("scoring_model")
        or config.get("ai", {}).get("scoring_model")
        or config.get("ai", {}).get("model", "deepseek-chat")
    )
    return client, model


def _get_async_client() -> tuple[AsyncOpenAI, str]:
    """Create a new asynchronous OpenAI client for DeepSeek API."""
    config = load_config()
    api_key = _get_api_key()
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )
    model = (
        runtime_settings.get("scoring_model")
        or config.get("ai", {}).get("scoring_model")
        or config.get("ai", {}).get("model", "deepseek-chat")
    )
    return client, model


_MASTER_RESUME: Optional[dict] = None


def _get_master_resume() -> dict:
    """Get or load the cached master resume."""
    global _MASTER_RESUME
    if _MASTER_RESUME is None:
        _MASTER_RESUME = load_resume()
    return _MASTER_RESUME


def _get_prompt(filename: str, master_resume: dict) -> str:
    """Load prompt file and inject serialized master resume context."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content.replace("{master_resume_json}", json.dumps(master_resume, indent=2))


def extract_json_str(text: str) -> str:
    """Robust extraction of JSON substring from model output."""
    if not text:
        return "{}"
    cleaned = text.strip()

    # Strip markdown codeblocks
    if "```" in cleaned:
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if code_block:
            cleaned = code_block.group(1).strip()

    # Balanced raw decode
    start_idx = cleaned.find("{")
    decoder = json.JSONDecoder()
    while start_idx != -1:
        try:
            _, end_pos = decoder.raw_decode(cleaned[start_idx:])
            return cleaned[start_idx : start_idx + end_pos]
        except json.JSONDecodeError:
            start_idx = cleaned.find("{", start_idx + 1)

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        cand = cleaned[first_brace : last_brace + 1]
        try:
            json.loads(cand)
            return cand
        except json.JSONDecodeError:
            pass

    return cleaned


async def call_ai_scoring_async(user_prompt: str) -> tuple[str, TokenUsage]:
    """
    Call DeepSeek for job scoring concurrently.
    Returns (response_text, token_usage_dict)
    """
    client, _ = _get_async_client()
    master_resume = _get_master_resume()

    scoring_model = runtime_settings.get("scoring_model", "deepseek-chat")
    scoring_thinking = runtime_settings.get("scoring_thinking", False)
    thinking_type = "enabled" if scoring_thinking else "disabled"

    system_prompt = _get_prompt("scoring_prompt.txt", master_resume)
    logger.debug(f"   🧠 Scoring: model={scoring_model}, thinking={thinking_type}")

    try:
        kwargs: Dict[str, Any] = dict(
            model=scoring_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        if scoring_thinking:
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                usage = response.usage
                if usage:
                    total = getattr(usage, "total_tokens", 0) or 0
                    cache_hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
                    cache_miss = getattr(usage, "prompt_cache_miss_tokens", 0) or 0
                    completion = getattr(usage, "completion_tokens", 0) or 0
                    prompt = getattr(usage, "prompt_tokens", 0) or 0
                    if prompt > 0 and cache_hit == 0 and cache_miss == 0:
                        cache_miss = prompt
                    elif cache_miss == 0 and prompt > cache_hit:
                        cache_miss = prompt - cache_hit
                    if total == 0:
                        total = prompt + completion
                    cost = calculate_deepseek_cost(
                        scoring_model, cache_hit, cache_miss, completion
                    )
                    logger.debug(
                        f"   📊 Scoring Tokens — Total: {total} | "
                        f"Prompt: {prompt} (cached: {cache_hit}, miss: {cache_miss}) | "
                        f"Completion: {completion} | Cost: ${cost:.6f}"
                    )
                else:
                    total = cache_hit = cache_miss = completion = prompt = 0
                    cost = 0.0

                token_stats = TokenUsage(
                    {
                        "prompt_tokens": prompt,
                        "prompt_cache_hit_tokens": cache_hit,
                        "prompt_cache_miss_tokens": cache_miss,
                        "completion_tokens": completion,
                        "total_tokens": total,
                        "cost_usd": cost,
                        "model": scoring_model,
                        "stage": "scoring",
                    }
                )

                content = response.choices[0].message.content or ""
                clean_content = extract_json_str(content)
                return clean_content, token_stats

            except Exception as e:
                if attempt == 2:
                    raise
                delay = (2**attempt) * 2 + random.uniform(0, 1)
                logger.warning(
                    f"   ⚠️ API Error during scoring ({type(e).__name__}). Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"DeepSeek Scoring API Error: {e}")
        raise
    finally:
        await client.close()


async def call_ai_tailoring_async(user_prompt: str) -> tuple[str, TokenUsage]:
    """
    Call DeepSeek for resume tailoring concurrently.
    Returns (response_text, token_usage_dict)
    """
    client, _ = _get_async_client()
    master_resume = _get_master_resume()

    tailoring_model = runtime_settings.get("tailoring_model", "deepseek-chat")
    tailoring_thinking = runtime_settings.get("tailoring_thinking", True)
    thinking_type = "enabled" if tailoring_thinking else "disabled"

    system_prompt = _get_prompt("tailoring_prompt.txt", master_resume)
    logger.debug(f"   🧠 Tailoring: model={tailoring_model}, thinking={thinking_type}")

    try:
        is_reasoner = (
            "reasoner" in (tailoring_model or "").lower()
            or "r1" in (tailoring_model or "").lower()
        )
        kwargs: Dict[str, Any] = dict(
            model=tailoring_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if not is_reasoner:
            kwargs["temperature"] = 0.3
            kwargs["response_format"] = {"type": "json_object"}
            if tailoring_thinking:
                kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            else:
                kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                usage = response.usage
                reasoning_tokens = 0
                if usage:
                    total = getattr(usage, "total_tokens", 0) or 0
                    cache_hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
                    cache_miss = getattr(usage, "prompt_cache_miss_tokens", 0) or 0
                    completion = getattr(usage, "completion_tokens", 0) or 0
                    prompt = getattr(usage, "prompt_tokens", 0) or 0
                    details = getattr(usage, "completion_tokens_details", None)
                    if details:
                        if isinstance(details, dict):
                            reasoning_tokens = details.get("reasoning_tokens", 0) or 0
                        else:
                            reasoning_tokens = getattr(details, "reasoning_tokens", 0) or 0
                    if prompt > 0 and cache_hit == 0 and cache_miss == 0:
                        cache_miss = prompt
                    elif cache_miss == 0 and prompt > cache_hit:
                        cache_miss = prompt - cache_hit
                    if total == 0:
                        total = prompt + completion
                    cost = calculate_deepseek_cost(
                        tailoring_model, cache_hit, cache_miss, completion
                    )
                    logger.debug(
                        f"   📊 Tailoring Tokens — Total: {total} | "
                        f"Prompt: {prompt} (cached: {cache_hit}, miss: {cache_miss}) | "
                        f"Completion: {completion} (reasoning: {reasoning_tokens}) | Cost: ${cost:.6f}"
                    )
                else:
                    total = cache_hit = cache_miss = completion = prompt = reasoning_tokens = 0
                    cost = 0.0

                token_stats = TokenUsage(
                    {
                        "prompt_tokens": prompt,
                        "prompt_cache_hit_tokens": cache_hit,
                        "prompt_cache_miss_tokens": cache_miss,
                        "completion_tokens": completion,
                        "reasoning_tokens": reasoning_tokens,
                        "total_tokens": total,
                        "cost_usd": cost,
                        "model": tailoring_model,
                        "stage": "tailoring",
                    }
                )

                content = response.choices[0].message.content or ""
                clean_content = extract_json_str(content)
                return clean_content, token_stats

            except Exception as e:
                if attempt == 2:
                    raise
                delay = (2**attempt) * 3 + random.uniform(0, 1)
                logger.warning(
                    f"   ⚠️ API Error during tailoring ({type(e).__name__}). Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"DeepSeek Tailoring API Error: {e}")
        raise
    finally:
        await client.close()


def call_ai_scoring(user_prompt: str) -> tuple[str, TokenUsage]:
    """Synchronous wrapper for call_ai_scoring_async."""
    return asyncio.run(call_ai_scoring_async(user_prompt))


def call_ai_tailoring(user_prompt: str) -> tuple[str, TokenUsage]:
    """Synchronous wrapper for call_ai_tailoring_async."""
    return asyncio.run(call_ai_tailoring_async(user_prompt))
