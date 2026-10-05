"""
Integration tests for src/ai_engine.py DeepSeek engine.
Validates:
1. DeepSeek scoring and schema compatibility.
2. TokenUsage arithmetic and compatibility.
3. Accurate DeepSeek cost calculation.
4. Prompt caching and telemetry logging.
"""

import asyncio
import json
import pytest
from src import ai_engine
from src.ai_engine import TokenUsage, call_ai_scoring_async, calculate_deepseek_cost


def run_async(coro):
    return asyncio.run(coro)


def test_token_usage_arithmetic():
    """Verify TokenUsage backward compatibility with integer addition and comparisons."""
    tu = TokenUsage({"total_tokens": 1500, "cost_usd": 0.001})
    assert int(tu) == 1500
    assert tu + 100 == 1600
    assert 100 + tu == 1600
    assert tu - 500 == 1000
    assert tu == 1500
    assert tu > 1000
    assert tu < 2000


def test_deepseek_cost_calculation():
    """Verify DeepSeek pricing calculations for chat and reasoner models."""
    # deepseek-chat: $0.07/M hit, $0.27/M miss, $1.10/M output
    cost_chat = calculate_deepseek_cost("deepseek-chat", cached_tokens=1_000_000, miss_tokens=1_000_000, completion_tokens=1_000_000)
    assert round(cost_chat, 2) == 1.44  # 0.07 + 0.27 + 1.10

    # deepseek-reasoner: $0.14/M hit, $0.55/M miss, $2.19/M output
    cost_reasoner = calculate_deepseek_cost("deepseek-reasoner", cached_tokens=1_000_000, miss_tokens=1_000_000, completion_tokens=1_000_000)
    assert round(cost_reasoner, 2) == 2.88  # 0.14 + 0.55 + 2.19


def test_live_deepseek_scoring():
    """Verify live DeepSeek scoring produces valid JSON, correct schema, and positive telemetry."""
    content, stats = run_async(
        call_ai_scoring_async(
            "Company: TechCorp\nTitle: Junior Java Developer\nRequirements: Java, Spring Boot, SQL, REST APIs."
        )
    )
    assert isinstance(content, str)
    data = json.loads(content)
    assert "fit_score" in data or "match_score" in data
    score = data.get("fit_score", data.get("match_score"))
    assert 70 <= score <= 100
    assert stats["model"] == "deepseek-chat"
    assert stats["total_tokens"] > 0
    assert stats["cost_usd"] > 0.0


def test_live_deepseek_qa_role_detection():
    """Verify live DeepSeek correctly flags is_testing_role for QA positions."""
    content, stats = run_async(
        call_ai_scoring_async(
            "Company: QA Labs\nTitle: QA Automation Engineer Intern\nRequirements: Selenium, pytest, Python, Postman."
        )
    )
    assert isinstance(content, str)
    data = json.loads(content)
    assert data.get("is_testing_role") is True
    assert stats["model"] == "deepseek-chat"
