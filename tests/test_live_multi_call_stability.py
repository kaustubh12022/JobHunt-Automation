import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from src.ai_engine import call_ai_scoring_async, calculate_deepseek_cost
from src.scorer import strip_boilerplate

load_dotenv()

async def live_multi_call_test():
    print("=================================================================")
    print("LIVE EMPIRICAL STABILITY: MULTI-CALL DEEPSEEK CACHE HIT EVALUATION")
    print("=================================================================")

    jobs = [
        ("Persistent Systems", "Junior QA Automation Engineer", "Automate test scripts using Selenium and Python. Execute API test suites with Postman. SQL and Git."),
        ("LTIMindtree", "Java Backend Developer - Fresher", "Design microservices using Java and Spring Boot. Develop REST APIs and write database queries with JDBC."),
        ("Wipro", ".NET Developer Trainee", "Entry level .NET developer with C#, ASP.NET, SQL Server, and Azure fundamentals.")
    ]

    telemetry_records = []

    for i, (company, title, desc) in enumerate(jobs, 1):
        prompt = f"Score this candidate against the following job:\n\nCompany: {company}\nTitle: {title}\nDescription: {desc}"
        print(f"\n[{i}] Firing Live Call {i} ({company} - {title})...")
        content, stats = await call_ai_scoring_async(prompt)
        prompt_tokens = stats["prompt_tokens"]
        hit_tokens = stats["prompt_cache_hit_tokens"]
        miss_tokens = stats["prompt_cache_miss_tokens"]
        comp_tokens = stats["completion_tokens"]
        cost = stats["cost_usd"]
        hit_rate = (hit_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0.0
        
        # Unoptimized baseline cost
        unopt_cost = (prompt_tokens * 0.27 / 1_000_000) + (comp_tokens * 1.10 / 1_000_000)
        savings = ((unopt_cost - cost) / unopt_cost * 100) if unopt_cost > 0 else 0.0

        print(f"    - Total: {stats['total_tokens']} | Prompt: {prompt_tokens} (Hit: {hit_tokens}, Miss: {miss_tokens}) | Comp: {comp_tokens}")
        print(f"    - Cache Hit Rate: {hit_rate:.2f}%")
        print(f"    - Cost: ${cost:.6f} (Baseline: ${unopt_cost:.6f}, Savings: {savings:.2f}%)")

        telemetry_records.append({
            "call": i,
            "hit_rate": hit_rate,
            "savings": savings,
            "stats": stats
        })

    print("\n=================================================================")
    print("MULTI-CALL EMPIRICAL SUMMARY:")
    for r in telemetry_records:
        print(f"Call {r['call']}: Cache Hit Rate = {r['hit_rate']:.2f}%, Cost Savings = {r['savings']:.2f}%")

    call2_hit = telemetry_records[1]["hit_rate"]
    call3_hit = telemetry_records[2]["hit_rate"]
    call2_savings = telemetry_records[1]["savings"]
    call3_savings = telemetry_records[2]["savings"]

    assert call2_hit >= 70.0, f"Call 2 hit rate {call2_hit:.2f}% < 70%"
    assert call3_hit >= 70.0, f"Call 3 hit rate {call3_hit:.2f}% < 70%"
    assert call2_savings >= 30.0, f"Call 2 savings {call2_savings:.2f}% < 30%"
    assert call3_savings >= 30.0, f"Call 3 savings {call3_savings:.2f}% < 30%"

    print("\n>>> ALL MULTI-CALL LIVE VERIFICATION ASSERTIONS PASSED! <<<")

if __name__ == "__main__":
    asyncio.run(live_multi_call_test())
