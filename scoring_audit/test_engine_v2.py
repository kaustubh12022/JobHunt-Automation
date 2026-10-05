"""
Comprehensive Verification Suite for Dual-Provider AI Scoring Engine v2.

Tests:
1. DeepSeek Zero-Call Guard (strictly raises ValueError)
2. Unsupported provider rejection
3. Schema normalization & backwards compatibility (fit_score <-> match_score, reasoning <-> reason)
4. Markdown code fence JSON extraction
5. Prompt formatting & candidate resume injection
6. AsyncRateLimiter pacing and minimum interval enforcement
7. Gemini live call verification (gemini-3.5-flash-lite)
8. Groq live call verification (qwen/qwen3.8-27b)
"""

import asyncio
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from scoring_audit.ai_engine_v2 import (
    AsyncRateLimiter,
    DualProviderScoringEngine,
    ScoringResult,
    extract_json_str,
    format_scoring_prompt,
    load_master_resume,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Guard & Security Tests
# ─────────────────────────────────────────────────────────────────────────────


def _run_async(coro):
    """Helper to run an async coroutine synchronously in pytest and CLI."""
    return asyncio.run(coro)


async def _async_test_deepseek_guard():
    """Verify that any DeepSeek call attempt is immediately blocked with ValueError."""
    print("\n[Test 1] Testing DeepSeek Zero-Call Guard...")
    engine = DualProviderScoringEngine()

    forbidden_providers = [
        "deepseek",
        "DeepSeek",
        "DEEPSEEK",
        "deepseek-chat",
        "deepseek-reasoner",
        " deepseek ",
    ]

    for p in forbidden_providers:
        try:
            engine._validate_provider(p)
            assert False, f"Expected ValueError for provider '{p}', but none was raised!"
        except ValueError as e:
            assert "DeepSeek is strictly forbidden" in str(e), (
                f"Unexpected error message: {e}"
            )
            print(f"  [PASS] Successfully blocked forbidden provider: '{p}' -> {e}")

    # Also test via score_job
    try:
        await engine.score_job(jd_text="test jd", provider="deepseek")
        assert False, "Expected ValueError when calling score_job with deepseek"
    except ValueError as e:
        assert "DeepSeek is strictly forbidden" in str(e)
        print("  [PASS] score_job(provider='deepseek') successfully raised ValueError")


def test_deepseek_guard():
    _run_async(_async_test_deepseek_guard())


def test_unsupported_provider():
    """Verify that unrecognized providers raise ValueError."""
    print("\n[Test 2] Testing Unsupported Provider Guard...")
    engine = DualProviderScoringEngine()
    for p in ["anthropic", "claude-3-opus", "openai", "cohere", ""]:
        try:
            engine._validate_provider(p)
            assert False, f"Expected ValueError for unsupported provider '{p}'"
        except ValueError as e:
            assert "Supported providers are 'gemini' and 'groq'" in str(e)
    print("  [PASS] All unsupported providers correctly rejected.")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Schema Normalization & Parsing Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_schema_and_compatibility():
    """Verify Pydantic ScoringResult normalization and legacy compatibility."""
    print("\n[Test 3] Testing ScoringResult Schema & Compatibility...")

    # Case A: Standard v2 creation
    res1 = ScoringResult(
        fit_score=88,
        is_testing_role=False,
        missing_skills=["Docker", "Kubernetes"],
        reasoning="Strong match on Java backend and Spring Boot.",
    )
    assert res1.fit_score == 88
    assert res1.match_score == 88, "match_score property should equal fit_score"
    assert res1.reason == res1.reasoning, "reason property should equal reasoning"
    assert res1.is_testing_role is False
    assert len(res1.missing_skills) == 2
    print("  [PASS] Standard v2 ScoringResult valid, compatibility properties verified.")

    # Case B: Legacy v1 dictionary (match_score, reason)
    v1_dict = {
        "match_score": 75,
        "reason": "Good match for junior QA automation role.",
        "is_testing_role": True,
        "missing_skills": ["Cypress"],
    }
    res2 = ScoringResult.model_validate(v1_dict)
    assert res2.fit_score == 75, "Legacy match_score should normalize to fit_score"
    assert res2.reasoning == "Good match for junior QA automation role."
    assert res2.match_score == 75
    assert res2.reason == "Good match for junior QA automation role."
    assert res2.is_testing_role is True
    print("  [PASS] Legacy v1 dict correctly normalized into v2 ScoringResult.")

    # Case C: JSON markdown code block extraction
    raw_markdown = (
        "Here is the result:\n```json\n"
        '{\n  "fit_score": 92,\n  "is_testing_role": true,\n'
        '  "missing_skills": ["Appium"],\n'
        '  "reasoning": "Excellent fit for automation testing."\n}\n'
        "```\nThank you!"
    )
    extracted = extract_json_str(raw_markdown)
    res3 = ScoringResult.model_validate_json(extracted)
    assert res3.fit_score == 92
    assert res3.is_testing_role is True
    assert res3.missing_skills == ["Appium"]
    print("  [PASS] Markdown code fence extraction and parsing verified.")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Prompt Formatting & Resume Injection Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_prompt_formatting():
    """Verify prompt formatting and master resume injection."""
    print("\n[Test 4] Testing Prompt Formatting & Resume Injection...")
    resume = load_master_resume()
    assert "personal_information" in resume
    assert resume["personal_information"].get("name") == "Kaustubh"
    assert resume["personal_information"].get("surname") == "Kale"
    print(f"  [PASS] Master resume loaded successfully: {resume['personal_information']['name']} {resume['personal_information']['surname']}")

    test_jd = "Senior React Developer with 5 years experience in GraphQL."
    formatted = format_scoring_prompt(jd_text=test_jd)
    assert "Kaustubh" in formatted, "Candidate name should be present in formatted prompt"
    assert "Kale" in formatted, "Candidate surname should be present in formatted prompt"
    assert test_jd in formatted, "Job description should be present in formatted prompt"
    print("  [PASS] Prompt template formatted with cached resume and JD successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Rate Limiter Pacing Tests
# ─────────────────────────────────────────────────────────────────────────────


async def _async_test_rate_limiter_pacing():
    """Verify that AsyncRateLimiter enforces minimum intervals between calls."""
    print("\n[Test 5] Testing AsyncRateLimiter Pacing...")
    # Test with a small interval for test speed
    test_min_interval = 0.3
    limiter = AsyncRateLimiter(rpm=60, min_interval=test_min_interval)

    t0 = time.perf_counter()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.perf_counter() - t0

    assert elapsed >= (test_min_interval * 0.95), (
        f"Expected at least {test_min_interval}s delay between calls, but got {elapsed:.3f}s"
    )
    print(f"  [PASS] RateLimiter enforced pacing: 2 calls took {elapsed:.3f}s (min {test_min_interval}s).")

    # Verify default engine rate limiters satisfy project specifications
    engine = DualProviderScoringEngine()
    assert engine.gemini_limiter.rpm <= 15.0, "Gemini RPM must be <= 15"
    assert engine.gemini_limiter.min_interval >= 4.0, "Gemini min interval must be >= 4.0s"
    assert engine.groq_limiter.rpm <= 20.0, "Groq RPM must be <= 20"
    assert engine.groq_limiter.min_interval >= 3.0, "Groq min interval must be >= 3.0s"
    print(
        f"  [PASS] Engine rate limiters correctly configured: "
        f"Gemini RPM={engine.gemini_limiter.rpm} (interval={engine.gemini_limiter.min_interval}s) | "
        f"Groq RPM={engine.groq_limiter.rpm} (interval={engine.groq_limiter.min_interval}s)"
    )


def test_rate_limiter_pacing():
    _run_async(_async_test_rate_limiter_pacing())


# ─────────────────────────────────────────────────────────────────────────────
# 5. Gemini Live API Call Test
# ─────────────────────────────────────────────────────────────────────────────


async def _async_test_gemini_live_scoring():
    """Verify live Gemini API scoring with gemini-3.5-flash-lite."""
    print("\n[Test 6] Testing Gemini Live Scoring (gemini-3.5-flash-lite)...")
    engine = DualProviderScoringEngine()

    test_jd = (
        "Job Title: Junior Java Backend Developer\n"
        "Company: Apex Global Technologies\n"
        "Location: Pune, India\n"
        "Experience: 0-1 years / Fresher\n"
        "Requirements: Strong core Java, Spring Boot, REST APIs, SQL/JDBC, Git. Good problem solving skills."
    )

    t0 = time.perf_counter()
    result = await engine.score_job(jd_text=test_jd, provider="gemini")
    duration = time.perf_counter() - t0

    print(f"  [PASS] Gemini response received in {duration:.2f}s:")
    print(f"    - Provider: {result.provider} (model: {result.model})")
    print(f"    - Fit Score: {result.fit_score}/100 (match_score: {result.match_score})")
    print(f"    - Is Testing Role: {result.is_testing_role}")
    print(f"    - Missing Skills: {result.missing_skills}")
    print(f"    - Reasoning: {result.reasoning}")

    assert isinstance(result, ScoringResult)
    assert 0 <= result.fit_score <= 100, f"Invalid fit_score: {result.fit_score}"
    assert isinstance(result.is_testing_role, bool)
    assert isinstance(result.missing_skills, list)
    assert isinstance(result.reasoning, str) and len(result.reasoning) > 10
    assert result.match_score == result.fit_score
    assert result.reason == result.reasoning
    assert result.provider == "gemini"
    print("  [PASS] Gemini live verification passed with all assertions satisfied.")


def test_gemini_live_scoring():
    _run_async(_async_test_gemini_live_scoring())


# ─────────────────────────────────────────────────────────────────────────────
# 6. Groq Live API Call Test
# ─────────────────────────────────────────────────────────────────────────────


async def _async_test_groq_live_scoring():
    """Verify live Groq API scoring with qwen/qwen3.8-27b."""
    print("\n[Test 7] Testing Groq Live Scoring (qwen/qwen3.8-27b)...")
    engine = DualProviderScoringEngine()

    test_jd = (
        "Job Title: QA Automation Tester / SDET Intern\n"
        "Company: CloudQA Solutions\n"
        "Location: Pune, India\n"
        "Experience: 0-1 years\n"
        "Requirements: Hands-on automation testing with Selenium WebDriver, Python or Java, pytest, Postman for API testing. Test case execution and defect reporting."
    )

    t0 = time.perf_counter()
    result = await engine.score_job(jd_text=test_jd, provider="groq")
    duration = time.perf_counter() - t0

    print(f"  [PASS] Groq response received in {duration:.2f}s:")
    print(f"    - Provider: {result.provider} (model: {result.model})")
    print(f"    - Fit Score: {result.fit_score}/100 (match_score: {result.match_score})")
    print(f"    - Is Testing Role: {result.is_testing_role}")
    print(f"    - Missing Skills: {result.missing_skills}")
    print(f"    - Reasoning: {result.reasoning}")
    if hasattr(result, "tokens_used") and result.tokens_used:
        print(f"    - Tokens Used: {result.tokens_used}")

    assert isinstance(result, ScoringResult)
    assert 0 <= result.fit_score <= 100, f"Invalid fit_score: {result.fit_score}"
    assert result.is_testing_role is True, (
        f"Expected is_testing_role=True for QA Automation role, got {result.is_testing_role}"
    )
    assert isinstance(result.missing_skills, list)
    assert isinstance(result.reasoning, str) and len(result.reasoning) > 10
    assert result.match_score == result.fit_score
    assert result.reason == result.reasoning
    assert result.provider == "groq"
    print("  [PASS] Groq live verification passed with all assertions satisfied.")
    await engine.close()


def test_groq_live_scoring():
    _run_async(_async_test_groq_live_scoring())


# ─────────────────────────────────────────────────────────────────────────────
# Main Verification Runner
# ─────────────────────────────────────────────────────────────────────────────


def run_all_tests():
    print("=" * 70)
    print("STARTING DUAL-PROVIDER SCORING ENGINE V2 VERIFICATION SUITE")
    print("=" * 70)

    # Unit & logic tests
    test_deepseek_guard()
    test_unsupported_provider()
    test_schema_and_compatibility()
    test_prompt_formatting()
    test_rate_limiter_pacing()

    # Live API integration tests
    test_gemini_live_scoring()
    test_groq_live_scoring()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! (7/7)")
    print("=" * 70)


def main():
    try:
        run_all_tests()
    except Exception as e:
        print(f"\n[FAIL] TEST SUITE FAILED: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
