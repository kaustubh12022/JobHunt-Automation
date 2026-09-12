import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from dotenv import load_dotenv
from src.ai_engine import call_ai_scoring_async, calculate_deepseek_cost
from src.scorer import strip_boilerplate

load_dotenv()

async def live_demo():
    print("================================================================")
    print("LIVE VERIFICATION: DEEPSEEK-CHAT PROMPT CACHING & COST TELEMETRY")
    print("================================================================")

    jd1 = """
    Company: Persistent Systems
    Title: Junior QA Automation Engineer
    Location: Pune, India
    Description: We are seeking an entry level QA Automation Engineer.
    Responsibilities: Automate test scripts using Selenium and Python.
    Execute API test suites with Postman. Work with relational databases using SQL.
    Qualifications: Bachelor degree in Computer Science. 0-1 year experience.
    Knowledge of Selenium, Python, SQL, and Git.
    """
    
    jd2 = """
    Company: LTIMindtree
    Title: Java Backend Developer - Fresher
    Location: Bangalore, India
    Description: Looking for entry-level Java Developer.
    Responsibilities: Design microservices using Java and Spring Boot.
    Develop REST APIs and write database queries with JDBC.
    Qualifications: 0-1 year or fresher with strong Java, OOP, SQL foundation.
    """

    prompt1 = f"Score this candidate against the following job:\n\n{strip_boilerplate(jd1)}"
    prompt2 = f"Score this candidate against the following job:\n\n{strip_boilerplate(jd2)}"

    print("\n[1] Firing Call 1 (Warming DeepSeek prompt prefix cache)...")
    content1, stats1 = await call_ai_scoring_async(prompt1)
    print(f"Call 1 JSON Output:\n{content1}")
    print(f"Call 1 Telemetry: Total: {stats1['total_tokens']} | Prompt: {stats1['prompt_tokens']} (Hit: {stats1['prompt_cache_hit_tokens']}, Miss: {stats1['prompt_cache_miss_tokens']}) | Completion: {stats1['completion_tokens']} | Cost: ${stats1['cost_usd']:.6f}")

    print("\n[2] Firing Call 2 (Consecutive call with identical static system prompt)...")
    content2, stats2 = await call_ai_scoring_async(prompt2)
    print(f"Call 2 JSON Output:\n{content2}")
    print(f"Call 2 Telemetry: Total: {stats2['total_tokens']} | Prompt: {stats2['prompt_tokens']} (Hit: {stats2['prompt_cache_hit_tokens']}, Miss: {stats2['prompt_cache_miss_tokens']}) | Completion: {stats2['completion_tokens']} | Cost: ${stats2['cost_usd']:.6f}")

    hit_tokens = stats2["prompt_cache_hit_tokens"]
    total_prompt = stats2["prompt_tokens"]
    hit_rate = (hit_tokens / total_prompt) * 100 if total_prompt > 0 else 0
    print(f"\n[3] Empirical Cache Hit Rate on Call 2: {hit_rate:.2f}% (Requirement: >= 70%)")
    assert hit_rate >= 70.0, f"Cache hit rate below 70%: {hit_rate}"

    # Unoptimized baseline comparison
    unoptimized_cost_call2 = (total_prompt * 0.27 / 1_000_000) + (stats2["completion_tokens"] * 1.10 / 1_000_000)
    actual_cost_call2 = stats2["cost_usd"]
    cost_reduction = ((unoptimized_cost_call2 - actual_cost_call2) / unoptimized_cost_call2) * 100
    print(f"[4] Cost Comparison for Call 2:")
    print(f"    - Unoptimized Baseline Cost: ${unoptimized_cost_call2:.6f}")
    print(f"    - Actual Optimized Cost:     ${actual_cost_call2:.6f}")
    print(f"    - Direct Invocations Savings: {cost_reduction:.2f}% (Requirement: >= 30%)")
    assert cost_reduction >= 30.0, f"Cost reduction below 30%: {cost_reduction}"
    print("\n>>> LIVE VERIFICATION PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    asyncio.run(live_demo())
