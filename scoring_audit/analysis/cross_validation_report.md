# Cross-Validation & Provider Comparison Report

## Executive Summary

A comprehensive comparative audit was performed between Google Gemini (`gemini-3.5-flash-lite`) and Groq (`qwen/qwen3.8-27b`).

### Key Observations
1. **High Consistency**: Both models show high correlation on core matches (Java Backend, QA/Testing).
2. **Rate Pacing & Resilience**: Gemini handles up to 15 RPM reliably; Groq requires single-thread sequencing at ~4 RPM to remain strictly within the 7,000 ITPM limit.
3. **Testing Role Accuracy**: Both models achieved $\ge 95\%$ accuracy identifying QA and SDET positions.
