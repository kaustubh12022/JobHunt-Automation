# Project: AI Scoring Phase Audit & Multi-Provider Architecture

## Architecture
- **Pipeline Role**: The AI Scoring subsystem evaluates jobs passing regex filtering against the candidate profile (`data_folder/plain_text_resume.yaml`), outputting a match score (0-100), reasoning, missing skills, and testing role classification.
- **Provider Layer**: Dual-provider architecture supporting Google Gemini (`gemini-3.5-flash-lite` via `google-genai` 2.25.0) and Groq (`qwen/qwen3.8-27b` via `openai` 2.54.0 compatible endpoint). Strictly zero DeepSeek calls or credentials.
- **Throttling & Resilience**: Async token-bucket rate limiting (Gemini <= 15 RPM, Groq <= 20 RPM / 8k TPM), exponential backoff with jitter on 429/503.
- **Schema & Normalization**: Pydantic `ScoringResult` model (`fit_score`, `is_testing_role`, `missing_skills`, `reasoning`), backwards-compatible properties `match_score` and `reason`.
- **Prompt Architecture**: Prompt v1 (`src/prompts/scoring_prompt.txt`) baseline audited; Prompt v2 (`scoring_audit/scoring_prompt_v2.txt`) adds MERN, AI/ML/LLM, fixes Docker/K8s hallucination, and provides a multi-tier calibration rubric.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Synthetic Benchmark Dataset | 300 synthetic JDs across 15 categories (20 each) with ground truth score ranges, test flags, and missing skills in `scoring_audit/synthetic_jds.json` | M1 | Survey / ORIGINAL_REQUEST R1 |
| 2 | Dual-Provider Scoring Engine | Standalone `scoring_audit/ai_engine_v2.py` with Gemini & Groq async clients, rate limiters, backoff, and JSON extraction | M2 | Survey / ORIGINAL_REQUEST R2 |
| 3 | DeepSeek Zero-Call Guard | Strict isolation from DeepSeek API, raising ValueError if attempted | M2 | Survey / ORIGINAL_REQUEST R2 |
| 4 | Baseline Scoring (Prompt v1) | Score 300 synthetic JDs and 73 surviving real jobs via Gemini & Groq, saving logs to `scoring_audit/scores/` | M3 | Survey / ORIGINAL_REQUEST R3 |
| 5 | Cross-Validation & Deficiencies Audit | Audit accuracy vs GT ranges, provider agreement (±10 pts), is_testing_role, missing_skills, generate reports in `scoring_audit/analysis/` | M4 | Survey / ORIGINAL_REQUEST R4 |
| 6 | Scoring Prompt v2 Engineering | Add MERN & AI/ML to target roles, fix false missing skills (Docker/K8s), calibrate tiered score ranges in `scoring_audit/scoring_prompt_v2.txt` | M5 | Survey / ORIGINAL_REQUEST R5 |
| 7 | Benchmark Re-scoring & Verification | Re-score synthetic and real jobs with v2 on both providers, verify >=90% GT accuracy, >=80% agreement, produce comparison report | M5 | Survey / ORIGINAL_REQUEST R5 |
| 8 | Production Multi-Provider Integration | Update `src/ai_engine.py` and `config.yaml` with backup, configurable providers, rate limiting, and zero DeepSeek | M6 | Survey / ORIGINAL_REQUEST R6 |
| 9 | Production Test Verification | Verify test suites (`tests/test_ai_engine.py` or new provider tests) pass cleanly without regressions | M6 | Survey / ORIGINAL_REQUEST R6 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Synthetic Benchmark Dataset Generation | Generate 300 JDs across 15 categories to `scoring_audit/synthetic_jds.json` | none | PLANNED |
| M2 | Dual-Provider Scoring Engine | Implement `scoring_audit/ai_engine_v2.py` (Gemini & Groq, rate limiters, backoff, schema) | none | PLANNED |
| M3 | Dual-Provider Baseline Scoring Execution | Execute baseline scoring (Prompt v1) on 300 synthetic + 73 real jobs for both providers | M1, M2 | PLANNED |
| M4 | Cross-Validation & Deficiencies Analysis | Audit baseline scores, provider agreement, missing_skills, is_testing_role, generate reports | M3 | PLANNED |
| M5 | Prompt Optimization (v2) & Retest Verification | Create prompt v2, re-score, verify >=90% accuracy bar, generate comparison reports | M4 | PLANNED |
| M6 | Production Multi-Provider Integration | Update `src/ai_engine.py`, `config.yaml`, back up baselines, verify all tests pass | M5 | PLANNED |

## Interface Contracts
### Synthetic Dataset Format (`scoring_audit/synthetic_jds.json`)
```json
[
  {
    "id": "SYNTH_001",
    "category": "Java_Spring_Backend",
    "title": "Junior Java Developer",
    "company": "TechCorp",
    "experience_required": "0-1 years",
    "description": "...",
    "ground_truth": {
      "expected_min_score": 80,
      "expected_max_score": 95,
      "is_testing_role": false,
      "expected_missing_skills": [],
      "acceptable_pass": true
    }
  }
]
```

### Scoring Engine Interface (`scoring_audit/ai_engine_v2.py`)
```python
class ScoringResult(BaseModel):
    fit_score: int
    is_testing_role: bool
    missing_skills: list[str]
    reasoning: str

    @property
    def match_score(self) -> int: return self.fit_score
    @property
    def reason(self) -> str: return self.reasoning

class DualProviderScoringEngine:
    async def score_job(self, jd_text: str, provider: str = "gemini", prompt_path: str = None) -> ScoringResult:
        ...
```

## Code Layout
- `scoring_audit/`: Root directory for audit artifacts
  - `synthetic_jds.json`: 300 synthetic benchmark job descriptions
  - `ai_engine_v2.py`: Dual-provider async scoring engine (Gemini & Groq)
  - `scoring_prompt_v2.txt`: Optimized scoring prompt v2
  - `scores/`: Raw score logs (JSONL/JSON) for Gemini and Groq, v1 and v2
  - `analysis/`: Cross-validation, discrepancy audit, and comparison reports
- `src/ai_engine.py`: Production AI engine updated for multi-provider support
- `config.yaml`: Production configuration with provider selection
- `tests/`: Automated unit and integration tests
