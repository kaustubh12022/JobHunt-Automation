import json
import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")
from scoring_audit.ai_engine_v2 import (
    ScoringResult,
    extract_json_str,
    DualProviderScoringEngine,
    AsyncRateLimiter
)

def test_extract_json_str_robustness():
    # Case 1: Standard markdown
    t1 = '```json\n{"fit_score": 80, "is_testing_role": false, "missing_skills": [], "reasoning": "good"}\n```'
    assert json.loads(extract_json_str(t1))['fit_score'] == 80

    # Case 2: Preamble and postamble with fences
    t2 = 'Here is the JSON evaluation:\n```json\n{"fit_score": 90, "is_testing_role": true, "missing_skills": ["Cypress"], "reasoning": "excellent"}\n```\nHope this helps!'
    parsed2 = json.loads(extract_json_str(t2))
    assert parsed2['fit_score'] == 90
    assert parsed2['is_testing_role'] is True

    # Case 3: Raw JSON without code fence but with surrounding text
    t3 = 'I analyzed the resume. {"fit_score": 70, "is_testing_role": false, "missing_skills": [], "reasoning": "ok"} Let me know if you need anything else.'
    parsed3 = json.loads(extract_json_str(t3))
    assert parsed3['fit_score'] == 70

    # Case 4: Empty string
    assert extract_json_str('') == '{}'

    # Case 5: Nested braces in strings
    t5 = '{"fit_score": 85, "is_testing_role": false, "missing_skills": [], "reasoning": "Candidate knows {A} and {B} well."}'
    parsed5 = json.loads(extract_json_str(t5))
    assert parsed5['reasoning'] == "Candidate knows {A} and {B} well."

def test_scoring_result_adversarial_types():
    # Null / None missing_skills
    r1 = ScoringResult.model_validate({"fit_score": 50, "reasoning": "ok", "is_testing_role": False, "missing_skills": None})
    assert r1.missing_skills == []

    # Non-list, non-string missing_skills (e.g. dict or int)
    r2 = ScoringResult.model_validate({"fit_score": 50, "reasoning": "ok", "is_testing_role": False, "missing_skills": 123})
    assert r2.missing_skills == []

    # String bool variants
    for val in ["true", "True", "TRUE", "yes", "1"]:
        r = ScoringResult.model_validate({"fit_score": 50, "reasoning": "ok", "is_testing_role": val})
        assert r.is_testing_role is True

    for val in ["false", "False", "FALSE", "no", "0", "anything_else"]:
        r = ScoringResult.model_validate({"fit_score": 50, "reasoning": "ok", "is_testing_role": val})
        assert r.is_testing_role is False

    # Out of range scores
    with pytest.raises(ValidationError):
        ScoringResult.model_validate({"fit_score": -1, "reasoning": "ok", "is_testing_role": False})

    with pytest.raises(ValidationError):
        ScoringResult.model_validate({"fit_score": 101, "reasoning": "ok", "is_testing_role": False})

def test_deepseek_guard_variants():
    engine = DualProviderScoringEngine()
    test_cases = [
        "deepseek",
        "DeepSeek",
        "DEEPSEEK",
        "deepseek-chat",
        "deepseek-reasoner",
        "deepseek-v3",
        "deepseek_r1",
        "api.deepseek.com",
    ]
    for tc in test_cases:
        with pytest.raises(ValueError) as exc:
            engine._validate_provider(tc)
        assert "DeepSeek is strictly forbidden" in str(exc.value)

if __name__ == "__main__":
    test_extract_json_str_robustness()
    test_scoring_result_adversarial_types()
    test_deepseek_guard_variants()
    print("ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")
