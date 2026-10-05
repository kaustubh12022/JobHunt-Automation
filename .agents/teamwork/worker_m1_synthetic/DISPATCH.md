# Task Assignment: Worker M1 - Synthetic Benchmark Dataset Generation

- Working Directory: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m1_synthetic
- Project Root: c:\Users\kalek\Desktop\Projects\Job_Hunt
- Request: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md (specifically ## Follow-up — 2026-09-29T16:37:31Z, Requirement R1)
- Scope Document: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\orchestrator_3\PROJECT.md

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You exclusively own:
- `scoring_audit/generate_synthetic_jds.py` (generation script)
- `scoring_audit/synthetic_jds.json` (benchmark dataset output)
Do NOT modify files owned by other agents or production source code.

## Requirements
1. Generate exactly 300 diverse, realistic synthetic job descriptions across 15 distinct categories (exactly 20 JDs per category):
   - Category 1: `Java_Spring_Backend` (entry level, 0-2 yrs, expected 80-95, is_testing: false)
   - Category 2: `QA_Automation_Testing` (Selenium, JUnit, Postman, pytest, 0-2 yrs, expected 80-95, is_testing: true)
   - Category 3: `MERN_Stack` (React, Node.js, Express, MongoDB, 0-2 yrs, expected 75-90, is_testing: false)
   - Category 4: `AI_ML_LLM` (Python, LLM integration, prompt engineering, 0-2 yrs, expected 75-88, is_testing: false)
   - Category 5: `Python_Backend` (Django/Flask/FastAPI/REST, 0-2 yrs, expected 75-90, is_testing: false)
   - Category 6: `DotNet_CSharp` (C#, .NET, Azure, OOP, SQL, 0-2 yrs, expected 60-75, is_testing: false)
   - Category 7: `FullStack_SWE` (JavaScript, React/Node/Python/Java, 0-2 yrs, expected 70-85, is_testing: false)
   - Category 8: `Manual_QA_Testing` (Test cases, JIRA, manual testing, 0-2 yrs, expected 65-80, is_testing: true)
   - Category 9: `Senior_Java_Lead` (3-8+ yrs, Lead/Architect, expected 0-25, is_testing: false) - Trap: senior
   - Category 10: `Senior_QA_Lead` (5+ yrs, QA Lead/Manager, expected 0-25, is_testing: true) - Trap: senior QA
   - Category 11: `Mobile_Dev_OutOfScope` (iOS, Swift, Android, Kotlin, Flutter, expected 0-20, is_testing: false) - Out of scope
   - Category 12: `Legacy_OutOfScope` (PHP, Ruby on Rails, Salesforce, SAP, expected 0-20, is_testing: false) - Out of scope
   - Category 13: `DevOps_Cloud_Infra` (heavy AWS, Terraform, Kubernetes cluster admin, expected 30-55, is_testing: false) - Edge: partial match
   - Category 14: `Sparse_Job_Description` (minimal 1-2 sentence JD, 0-2 yrs, expected 40-60, is_testing: false) - Edge: sparse
   - Category 15: `Non_Technical_Role` (Sales, Marketing, HR, Finance, expected 0-10, is_testing: false) - Irrelevant
2. Ground-Truth Data Structure per Job:
   ```json
   {
     "id": "SYNTH_001",
     "category": "Java_Spring_Backend",
     "title": "Junior Java Developer",
     "company": "Enterprise Tech Solutions",
     "location": "Pune, India",
     "experience_required": "0-1 years",
     "description": "Full realistic job description text...",
     "ground_truth": {
       "expected_min_score": 80,
       "expected_max_score": 95,
       "is_testing_role": false,
       "expected_missing_skills": ["Kafka"],
       "acceptable_pass": true
     }
   }
   ```
3. Run the generation script and verify `scoring_audit/synthetic_jds.json`:
   - Valid JSON containing exactly 300 records.
   - All 15 categories present with exactly 20 records each.
   - All fields present and non-empty.
   - Ground-truth score ranges and flags logically sound against candidate profile (`data_folder/plain_text_resume.yaml`).
4. Output your handoff to `handoff.md` and report completion via `send_message`.

## 2026-09-29T16:48:13Z
Read c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\ORIGINAL_REQUEST.md and c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m1_synthetic\DISPATCH.md.
Your working directory is: c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\worker_m1_synthetic.
Implement scoring_audit/generate_synthetic_jds.py, generate scoring_audit/synthetic_jds.json (300 JDs across 15 categories, 20 each, with ground truth ranges, test flags, missing skills), verify JSON validity and distribution, write handoff.md, and send_message to parent upon completion.
