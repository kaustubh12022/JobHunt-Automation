"""
Standalone Job Evaluation Dashboard Launcher.

Runs on http://localhost:5050 completely independent of the main backend.
"""

import os
import sys
import webbrowser
import uvicorn
from pathlib import Path

# Fix Windows console encoding for UTF-8 logs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    port = int(os.environ.get("DASHBOARD_PORT", 5050))
    host = os.environ.get("DASHBOARD_HOST", "127.0.0.1")

    print("=" * 68)
    print("🚀 AutoApply Standalone Evaluation Dashboard")
    print("=" * 68)
    print(f" • Local URL:        http://{host}:{port}")
    print(f" • Primary LLM 1:    Gemini (gemini-3.5-flash-lite) ['Germany' testing]")
    print(f" • Primary LLM 2:    Groq (qwen/qwen3.8-27b) ['Croc']")
    print(f" • Rate Limiting:    Gemini <= 15 RPM | Groq <= 20 RPM")
    print(f" • Features:         Real-Time Terminal Streaming, SSE Web UI,")
    print(f"                     Instant Tabs (All/Selected/Rejected), CSV/JSON Export")
    print("=" * 68)
    print("Opening web browser...\n")

    try:
        webbrowser.open(f"http://{host}:{port}")
    except Exception:
        pass

    # Run Uvicorn server
    uvicorn.run(
        "standalone_dashboard.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )

if __name__ == "__main__":
    main()
