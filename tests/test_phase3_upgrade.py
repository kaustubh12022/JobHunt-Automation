import pytest
import os
import json
from unittest.mock import patch, MagicMock
from src.models import Job

def test_tailoring_prompt_no_hardcoded_values():
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "prompts", "tailoring_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    assert "Java Developer Intern" not in prompt
    assert "CWIPedia Technologies" not in prompt

def test_scoring_prompt_has_crosscheck():
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "prompts", "scoring_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    assert "cross-check it against ALL sections" in prompt
