# JobHunt-Automation

Built by **Kaustubh**. An idea by **Kaustubh**.

Automates the job application process with just **1 click** — scrapes jobs from LinkedIn, scores them against your profile, tailors your resume using AI, generates a PDF, and emails it directly to recruiters. Everything happens fully automatically!

## What It Does

1. **1-Click Automation:** Just run it and it does everything end-to-end.
2. **Scrapes** job listings from LinkedIn based on your preferences
3. **Scores** each job against your resume to find the best matches
4. **Tailors** your resume for each job using DeepSeek AI
5. **Generates** a professional PDF resume
6. **Emails** your tailored resume to the recruiter automatically

## Setup

```bash
pip install -r requirements.txt
```

Add your API keys in `config.yaml` and `data_folder/secrets.yaml`:
- DeepSeek API key
- Gmail app password

Add your resume details in `data_folder/plain_text_resume.yaml`.

## Run

```bash
python run.py
```

Or simply double-click the `Start_AutoApply.bat` file on your desktop to launch the web dashboard!

## Tech Stack

- Python
- DeepSeek AI (Advanced LLM for resume tailoring)
- Playwright (Robust LinkedIn scraping)
- Flask (Web dashboard)
- WeasyPrint (PDF generation)

## License

This project is for personal use.
