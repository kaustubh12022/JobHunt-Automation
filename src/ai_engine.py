"""
AutoApply AI Engine — DeepSeek via OpenAI SDK.

Supports two calling modes:
  - Scoring:  thinking DISABLED by default (fast, cheap)
  - Tailoring: thinking ENABLED by default (deep reasoning, hyper-tailored)

Model and thinking mode can be overridden at runtime via `runtime_settings`.

Master resume is pinned as the system prompt to trigger DeepSeek's
$0.0028/1M prompt caching rate.
"""
import json
import os
import asyncio
import random
from openai import OpenAI, AsyncOpenAI, RateLimitError
from src.config_loader import load_config, load_resume
from src.logger import logger

# ── Runtime AI Settings (overridden by dashboard UI) ──
runtime_settings = {
    "scoring_model": "deepseek-v4-flash",
    "scoring_thinking": False,
    "tailoring_model": "deepseek-v4-pro",
    "tailoring_thinking": True,
}


def _get_client() -> tuple[OpenAI, str]:
    """Create a synchronous OpenAI client pointed at the DeepSeek API."""
    config = load_config()
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY", config['ai']['api_key']),
        base_url="https://api.deepseek.com"
    )
    model = config['ai'].get('model', 'deepseek-v4-flash')
    return client, model


_ASYNC_CLIENT = None
_MODEL = None
_MASTER_RESUME = None

def _get_async_client() -> tuple[AsyncOpenAI, str]:
    """Create a new asynchronous OpenAI client for the current event loop."""
    config = load_config()
    client = AsyncOpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY", config['ai']['api_key']),
        base_url="https://api.deepseek.com"
    )
    model = config['ai'].get('model', 'deepseek-v4-flash')
    return client, model

def _get_master_resume() -> dict:
    """Get or load the cached master resume."""
    global _MASTER_RESUME
    if _MASTER_RESUME is None:
        _MASTER_RESUME = load_resume()
    return _MASTER_RESUME


def _get_prompt(filename: str, master_resume: dict) -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content.replace("{master_resume_json}", json.dumps(master_resume, indent=2))

async def call_ai_scoring_async(user_prompt: str) -> tuple[str, int]:
    """
    Call DeepSeek for job scoring concurrently.
    Returns (response_text, tokens_used)
    """
    client, _ = _get_async_client()
    master_resume = _get_master_resume()
    
    # Use runtime settings for model and thinking mode
    scoring_model = runtime_settings.get("scoring_model", "deepseek-v4-flash")
    scoring_thinking = runtime_settings.get("scoring_thinking", False)
    thinking_type = "enabled" if scoring_thinking else "disabled"
    
    system_prompt = _get_prompt("scoring_prompt.txt", master_resume)
    logger.debug(f"   🧠 Scoring: model={scoring_model}, thinking={thinking_type}")
    
    try:
        kwargs = dict(
            model=scoring_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            extra_body={"thinking": {"type": thinking_type}}
        )
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                usage = response.usage
                if usage:
                    total = usage.total_tokens
                    cache_hit = getattr(usage, 'prompt_cache_hit_tokens', 0)
                    cache_miss = getattr(usage, 'prompt_cache_miss_tokens', 0)
                    completion = getattr(usage, 'completion_tokens', 0)
                    prompt = getattr(usage, 'prompt_tokens', 0)
                    logger.debug(
                        f"   📊 Scoring Tokens — Total: {total} | "
                        f"Prompt: {prompt} (cached: {cache_hit}, miss: {cache_miss}) | "
                        f"Completion: {completion}"
                    )
                    tokens = total
                else:
                    tokens = 0
                return response.choices[0].message.content, tokens
            except Exception as e:
                if attempt == 2:
                    raise
                delay = (2 ** attempt) * 2 + random.uniform(0, 1)
                logger.warning(f"   ⚠️ API Error during scoring ({type(e).__name__}). Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"DeepSeek Scoring API Error: {e}")
        raise
    finally:
        await client.close()


async def call_ai_tailoring_async(user_prompt: str) -> tuple[str, int]:
    """
    Call DeepSeek for resume tailoring concurrently.
    Returns (response_text, tokens_used)
    """
    client, _ = _get_async_client()
    master_resume = _get_master_resume()
    
    # Use runtime settings for model and thinking mode
    tailoring_model = runtime_settings.get("tailoring_model", "deepseek-v4-pro")
    tailoring_thinking = runtime_settings.get("tailoring_thinking", True)
    thinking_type = "enabled" if tailoring_thinking else "disabled"
    
    system_prompt = _get_prompt("tailoring_prompt.txt", master_resume)
    logger.debug(f"   🧠 Tailoring: model={tailoring_model}, thinking={thinking_type}")
    
    try:
        kwargs = dict(
            model=tailoring_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": thinking_type}}
        )
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                usage = response.usage
                if usage:
                    total = usage.total_tokens
                    cache_hit = getattr(usage, 'prompt_cache_hit_tokens', 0)
                    cache_miss = getattr(usage, 'prompt_cache_miss_tokens', 0)
                    completion = getattr(usage, 'completion_tokens', 0)
                    prompt = getattr(usage, 'prompt_tokens', 0)
                    logger.debug(
                        f"   📊 Tailoring Tokens — Total: {total} | "
                        f"Prompt: {prompt} (cached: {cache_hit}, miss: {cache_miss}) | "
                        f"Completion: {completion}"
                    )
                    tokens = total
                else:
                    tokens = 0
                return response.choices[0].message.content, tokens
            except Exception as e:
                if attempt == 2:
                    raise
                delay = (2 ** attempt) * 3 + random.uniform(0, 1)
                logger.warning(f"   ⚠️ API Error during tailoring ({type(e).__name__}). Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"DeepSeek Tailoring API Error: {e}")
        raise
    finally:
        await client.close()
