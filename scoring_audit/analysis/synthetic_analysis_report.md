# Synthetic Benchmark Scoring Analysis Report (V1)

**Total Benchmark JDs Evaluated**: 300 (Gemini: 300, Groq: 60, Both: 60)

## Overall Performance Summary

| Metric | Gemini | Groq | Target Threshold |
|---|:---:|:---:|:---:|
| **Category Accuracy (In-Range)** | **69.7%** | **88.3%** | $\ge 90.0\%$ |
| **Testing Role Classification** | **100.0%** | **100.0%** | $\ge 95.0\%$ |
| **Missing Skills Genuine Accuracy** | **96.8%** | **98.5%** | $\ge 85.0\%$ |
| **Over-Scoring Rate** | 30.3% | 11.7% | Low |
| **Under-Scoring Rate** | 0.0% | 0.0% | Low |
| **Cross-Provider Agreement ($\pm 10$)** | \multicolumn{2}{c|}{100.0%} | $\ge 80.0\%$ |

## Category-by-Category Accuracy

| Category | Expected | Gemini Acc | Groq Acc | Provider Agreement | Avg Gemini | Avg Groq |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `AI_ML_LLM` | 75-88 | 0.0% (0/20) | 0.0% (0/20) | 0.0% (0/20) | 91.3 | 0.0 |
| `DevOps_Cloud_Infra` | 30-55 | 95.0% (19/20) | 0.0% (0/20) | 0.0% (0/20) | 44.3 | 0.0 |
| `DotNet_CSharp` | 60-75 | 95.0% (19/20) | 0.0% (0/20) | 0.0% (0/20) | 74.3 | 0.0 |
| `FullStack_SWE` | 70-85 | 0.0% (0/20) | 0.0% (0/20) | 0.0% (0/20) | 91.2 | 0.0 |
| `Java_Spring_Backend` | 80-95 | 100.0% (20/20) | 100.0% (20/20) | 100.0% (20/20) | 88.8 | 91.6 |
| `Legacy_OutOfScope` | 0-20 | 100.0% (20/20) | 0.0% (0/20) | 0.0% (0/20) | 15.0 | 0.0 |
| `MERN_Stack` | 75-90 | 100.0% (20/20) | 65.0% (13/20) | 100.0% (20/20) | 88.5 | 88.2 |
| `Manual_QA_Testing` | 65-80 | 0.0% (0/20) | 0.0% (0/20) | 0.0% (0/20) | 91.0 | 0.0 |
| `Mobile_Dev_OutOfScope` | 0-20 | 80.0% (16/20) | 0.0% (0/20) | 0.0% (0/20) | 19.2 | 0.0 |
| `Non_Technical_Role` | 0-10 | 75.0% (15/20) | 0.0% (0/20) | 0.0% (0/20) | 11.2 | 0.0 |
| `Python_Backend` | 75-90 | 100.0% (20/20) | 0.0% (0/20) | 0.0% (0/20) | 87.1 | 0.0 |
| `QA_Automation_Testing` | 80-95 | 100.0% (20/20) | 100.0% (20/20) | 100.0% (20/20) | 92.5 | 92.0 |
| `Senior_Java_Lead` | 0-25 | 100.0% (20/20) | 0.0% (0/20) | 0.0% (0/20) | 10.5 | 0.0 |
| `Senior_QA_Lead` | 0-25 | 100.0% (20/20) | 0.0% (0/20) | 0.0% (0/20) | 10.2 | 0.0 |
| `Sparse_Job_Description` | 40-60 | 0.0% (0/20) | 0.0% (0/20) | 0.0% (0/20) | 87.7 | 0.0 |
