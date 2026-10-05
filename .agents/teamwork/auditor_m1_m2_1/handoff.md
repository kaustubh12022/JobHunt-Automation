# Forensic Audit Handoff Report: Milestones M1 & M2 Integrity Verification

**Auditor**: Forensic Auditor (`auditor_m1_m2_1`)  
**Target**: Milestone M1 (Synthetic Benchmark Dataset) & Milestone M2 (Dual-Provider Scoring Engine)  
**Recipient**: Parent Orchestrator (`7cb7199f-c2a4-46e3-be86-1c86a84aa546`)  
**Date**: 2026-09-29  
**Final Verdict**: `CLEAN`

---

## Forensic Audit Report

**Work Product**: `scoring_audit/synthetic_jds.json`, `scoring_audit/generate_synthetic_jds.py`, `scoring_audit/ai_engine_v2.py`, `scoring_audit/test_engine_v2.py`, baseline files `src/ai_engine.py`, `src/scorer.py`  
**Profile**: General Project (Development Mode / Integrity Mode)  
**Verdict**: **CLEAN**

### Phase Results
- **Check 1: DeepSeek Zero-Call & Zero-Reference**: PASS — Zero outbound network calls, Zero SDK calls, `.env` contains no `DEEPSEEK_API_KEY`, and explicit provider guard blocks all case variations of `deepseek` with `ValueError`.
- **Check 2: Synthetic Dataset Authenticity & Schema**: PASS — Exactly 300 unique job descriptions across 15 categories (20 each) with valid ground-truth score ranges, test flags, and 0 false missing skills against candidate resume.
- **Check 3: Dual-Provider Engine Authenticity & Anti-Facade**: PASS — Live empirical execution with Gemini (`gemini-3.5-flash-lite`) and Groq (`qwen/qwen3.8-27b`) confirmed non-mocked, content-aware dynamic responses (Chef role scored 0, Java developer scored 90/92, QA role correctly flagged `is_testing_role=True`).
- **Check 4: Rate Limiting & Resilience Architecture**: PASS — Async token-bucket pacing verified (Gemini <= 15 RPM / min 4.0s interval; Groq <= 20 RPM / min 3.5s interval), exponential backoff with jitter implemented.
- **Check 5: Baseline Preservation**: PASS — Baseline production files `src/ai_engine.py` and `src/scorer.py` are completely untouched (`git diff` is empty, 0 lines changed).
- **Check 6: Independent Test Suite Execution**: PASS — `pytest scoring_audit/generate_synthetic_jds.py` (4/4 passed) and `pytest scoring_audit/test_engine_v2.py` (7/7 passed).

---

## 1. Observation

1. **DeepSeek Zero-Call & Guard Verification**:
   - `scoring_audit/ai_engine_v2.py` lines 386-388:
     ```python
     prov = (provider or "").strip().lower()
     if "deepseek" in prov:
         raise ValueError("DeepSeek is strictly forbidden in this pipeline.")
     ```
   - Validated against adversarial variations: `['deepseek', 'DeepSeek', 'DEEPSEEK', 'deepseek-chat', 'deepseek-reasoner', 'deepseek-v4', '  deepseek  ']`. Every variation raised verbatim `ValueError: DeepSeek is strictly forbidden in this pipeline.`.
   - Verified that `.env` does not contain `DEEPSEEK_API_KEY`.
   - Grep search confirmed zero outbound DeepSeek API endpoints (`api.deepseek.com`) in `scoring_audit/`.

2. **Synthetic Dataset Structure & Non-Repetition**:
   - `scoring_audit/synthetic_jds.json` contains exactly 300 records with contiguous IDs `SYNTH_001` through `SYNTH_300`.
   - Total categories: 15, with exactly 20 records per category.
   - All 300 job descriptions are unique (300 distinct strings; min length 166 characters for sparse postings, max length 2,510 characters for comprehensive enterprise postings).
   - Candidate known skills check: 0 false missing skills detected against `data_folder/plain_text_resume.yaml`. Candidate technologies (Java, Python, Docker, Kubernetes, MongoDB, Selenium, Postman, pytest, Azure) are never marked as missing skills.

3. **Authentic, Non-Facade Dual-Provider Execution**:
   - Tested live scoring independently against Gemini (`gemini-3.5-flash-lite`) and Groq (`qwen/qwen3.8-27b`) with three diverse role archetypes:
     * Irrelevant French Chef JD: Gemini score `0` (Reasoning: *"Complete domain mismatch between software engineering profile..."*), Groq score `0` (Reasoning: *"Complete mismatch between software engineering skills and culinary..."*).
     * Junior Java Backend JD: Gemini score `90` (`is_testing_role=False`), Groq score `92` (`is_testing_role=False`).
     * QA Automation Tester JD: Gemini score `85` (`is_testing_role=True`), Groq score `95` (`is_testing_role=True`).
   - Latencies recorded were authentic LLM round-trip network times (>2.0s per request).

4. **Baseline File Preservation**:
   - `git diff src/ai_engine.py src/scorer.py` produced 0 output lines.
   - `git status --porcelain src/ai_engine.py src/scorer.py` is empty.
   - Neither file was altered, corrupted, or deleted during M1 or M2.

5. **Test Suite Execution**:
   - `pytest scoring_audit/generate_synthetic_jds.py -v`: 4/4 passed in 0.04s.
   - `pytest scoring_audit/test_engine_v2.py -v`: 7/7 passed in 19.05s.
   - Standalone CLI `python scoring_audit/generate_synthetic_jds.py --verify`: All validation checks passed.
   - Standalone CLI `python scoring_audit/test_engine_v2.py`: All 7 verification checks passed.

---

## 2. Logic Chain

1. **Step 1 (Zero DeepSeek Enforcement)**: The user's prompt and ORIGINAL_REQUEST.md strictly mandate zero DeepSeek calls. Direct inspection of `ai_engine_v2.py` line 387 showed that `_validate_provider` executes prior to any network initialization, immediately raising a `ValueError`. Testing multiple case-variations confirmed this guard cannot be bypassed by formatting quirks. No DeepSeek keys or endpoints exist in `scoring_audit/`.
2. **Step 2 (Authenticity & Anti-Facade)**: Facade implementations typically return fixed constants or mock strings. To stress-test authenticity, an independent dynamic execution was executed sending extreme JD variations (Executive Chef vs Junior Java vs QA Automation). Both Gemini and Groq returned context-specific reasonings and scores varying from 0 to 95, proving real, dynamic, and non-hardcoded LLM execution.
3. **Step 3 (Synthetic Ground Truth Integrity)**: To prevent self-certifying tests or bogus datasets, `synthetic_jds.json` was audited for uniqueness and resume-grounded skill verification. All 300 entries are unique, across 15 balanced categories, with zero candidate known skills falsely identified as missing.
4. **Step 4 (Baseline Safety)**: `git diff` confirms that production baseline files `src/ai_engine.py` and `src/scorer.py` remain identical to HEAD, preserving production stability while audit engineering occurs in `scoring_audit/`.

---

## 3. Caveats

1. **Informational Warning on Gemini AFC**: During Gemini async execution, `google-genai` emits an informational library notice regarding automatic function calling in `AsyncModels.generate_content`. This is an upstream SDK notice and does not impact output validity or execution codes.
2. **Milestone M3-M6 Scope**: Baseline prompt execution (M3), cross-validation analysis (M4), prompt v2 engineering (M5), and production integration (M6) are downstream milestones that have not yet run; this audit strictly certifies the foundations established in M1 and M2.

---

## 4. Conclusion

The deliverables for Milestones M1 and M2 pass all forensic integrity checks under Development Mode.
- **DeepSeek Zero-Call**: Fully verified and enforced.
- **Authenticity**: 100% genuine Gemini and Groq execution with dynamic parsing.
- **Anti-Cheating**: 0 hardcoded test results, 0 facade modules, 0 fabricated logs.
- **Baseline Preservation**: 100% untouched.

**Verdict: CLEAN**

---

## 5. Verification Method

1. Verify DeepSeek zero-call guard:
   ```powershell
   python -c "from scoring_audit.ai_engine_v2 import DualProviderScoringEngine; DualProviderScoringEngine()._validate_provider('deepseek')"
   ```
   *Expected*: Raises `ValueError: DeepSeek is strictly forbidden in this pipeline.`

2. Verify synthetic dataset structure and resume skill sanity:
   ```powershell
   pytest scoring_audit/generate_synthetic_jds.py -v
   ```
   *Expected*: 4 passed in <0.2s.

3. Verify dual-provider engine and live Gemini/Groq execution:
   ```powershell
   pytest scoring_audit/test_engine_v2.py -v
   ```
   *Expected*: 7 passed in ~19s.

4. Verify untouched baseline files:
   ```powershell
   git status --porcelain src/ai_engine.py src/scorer.py
   ```
   *Expected*: Empty output.
