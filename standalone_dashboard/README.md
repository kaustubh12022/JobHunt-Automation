# AutoApply Standalone Job Evaluator & Dashboard

A high-throughput, standalone ATS evaluation dashboard completely decoupled from the main backend.

---

## 🌟 Key Capabilities

1. **Completely Independent**:
   - Zero dependencies on the main pipeline, scrapers, Supabase, or email handlers.
   - Runs on its own dedicated port (`http://localhost:5050`) via FastAPI and Uvicorn.

2. **Dual-Provider AI Engine**:
   - **Google Gemini** (`gemini-3.5-flash-lite`) ["Germany" testing]
   - **Groq** (`qwen/qwen3.8-27b`) ["Croc"]
   - API keys are pre-loaded from `.env` (`GEMINI_API_KEY` and `GROQ_API_KEY`) and can also be adjusted via the UI.

3. **Strict Client-Side Rate Limiting & Backoff**:
   - Gemini: `<= 15 RPM` (min 4.0s interval)
   - Groq: `<= 20 RPM` (min 3.0s interval)
   - Built-in sliding window rate limiter with exponential backoff and jitter on 429/503 responses.

4. **Multi-Mode Dispatch**:
   - **Smart Load-Balancing (Default)**: Alternates jobs between Gemini and Groq in parallel, maximizing throughput without exceeding individual rate limits.
   - **Gemini Only**: Routes all jobs to Gemini.
   - **Groq Only**: Routes all jobs to Groq.
   - **Failover**: Sends primary requests to Gemini; automatically falls back to Groq if rate-limited or unavailable.

5. **Real-Time Terminal & UI Logs**:
   - Live stdout terminal logging with single-line decision reasons:
     ```text
     [ACCEPTED] (Gemini | Score: 85/100) Infosys - Java Backend Developer | Reason: Strong match for Core Java and Spring Boot.
     [REJECTED] (Groq | Score: 20/100) Siemens Energy - Lead QA Engineer | Reason: Requires 8+ years experience and senior QA leadership.
     ```
   - Real-time Server-Sent Events (SSE) streaming logs directly into an interactive web terminal.

6. **Interactive Summary & Table Views**:
   - **Summary Cards**: Total Uploaded, Processed %, Selected (Accepted) %, Non-Selected (Rejected) %, Engine distribution, Average Score and Latency.
   - **Tab Navigation**:
     - **All Jobs**: Complete dataset view.
     - **Selected / Accepted**: Jobs scoring `>= threshold` (default 60).
     - **Non-Selected / Rejected**: Jobs scoring `< threshold`.
   - **Live Search**: Instant keyword filtering by Title, Company, Missing Skills, or Reason.
   - **Export**: 1-click download of Selected, Rejected, or All jobs as CSV or JSON.

---

## 🚀 Quick Start

### Option 1: Command Line
```powershell
python run_dashboard.py
```

### Option 2: Windows Batch File
Double-click `run_dashboard.bat`.

Once launched, open your browser at:
👉 **[http://localhost:5050](http://localhost:5050)**

---

## 📁 How to Use

1. **Upload Dataset**:
   - Drag & drop any raw JSON file (e.g. `master_raw_dataset_2026-09-29.json` or custom scraped job lists).
   - Alternatively, pick an existing dataset from the "choose existing" dropdown.
2. **Configure Settings**:
   - Choose your engine mode (e.g. *Smart Load-Balancing*).
   - Adjust the acceptance threshold (default: 60/100).
   - Select a batch limit (e.g. All jobs, or first 10 for a smoke test).
3. **Start Evaluation**:
   - Click **Start Evaluation**.
   - Watch the live terminal console and progress bar update in real time.
4. **Filter & Export**:
   - Switch between **All Jobs**, **Selected / Accepted**, and **Non-Selected / Rejected** tabs.
   - Click the eye icon on any job to view the full description and missing skill tags.
   - Click **Export** to save CSV or JSON reports.
