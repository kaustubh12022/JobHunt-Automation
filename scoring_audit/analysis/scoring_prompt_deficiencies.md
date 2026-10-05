# Scoring Prompt V1 Deficiencies & Root Cause Analysis

## Identified Failure Modes in `scoring_prompt.txt`

### 1. Missing Target Domains: MERN Stack & AI/ML/LLM
- **Root Cause**: `scoring_prompt.txt` only explicitly listed 5 target domains (Java, QA, .NET/C#, General SWE, Tester). It completely omitted **MERN Stack** (React, Express, Node.js, MongoDB) and **AI/ML/LLM Agentic Roles** (Python, Agents, LLM APIs).
- **Impact**: In benchmark categories C05 (MERN) and C06 (AI/ML), models penalized the candidate because the prompt did not acknowledge these as core target roles.

### 2. Hallucinated Missing Skills
- **Root Cause**: Models frequently listed 'Docker', 'Kubernetes', 'Git', or 'SQL' under `missing_skills` despite these being explicitly listed in `plain_text_resume.yaml`.
- **Fix for V2**: Include an explicit negative constraint: `DO NOT list skills already present in the resume under missing_skills` and enforce strict deduplication.

### 3. DeepSeek Legacy Key Removal & Standard Schema
- **Root Cause**: Baseline prompt was designed for DeepSeek and relied on legacy fields (`job_summary`, `extracted_requirements`).
- **Fix for V2**: Standardize cleanly on `fit_score`, `is_testing_role`, `missing_skills`, and `reasoning`.
