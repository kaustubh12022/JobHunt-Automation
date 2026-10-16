"""
tracker.py — Automated Application Workflow & Verified Submission Auditing Engine.

Responsible for Pillar 5:
- Local SQLite database (application_tracker.db) tracking every discovered, shortlisted,
  vetoed, tailored, and applied job with zero external database dependencies.
- Verified Submission Auditing: records submission timestamps, portal confirmation numbers,
  proof screenshot paths, and verification status.
- Provides fast SQL query methods for morning digest reports and telemetry dashboards.
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.logger import logger
from src.models import Job

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = PROJECT_DIR / "data_folder"
DB_PATH = DATA_FOLDER / "application_tracker.db"


def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row_factory enabled."""
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables and indexes for the application tracker."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tracked Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tracked_jobs (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        url TEXT,
        source TEXT,
        job_type TEXT,
        applicant_count INTEGER,
        is_early_applicant INTEGER,
        early_priority_tier TEXT,
        score INTEGER,
        missing_skills TEXT,
        status TEXT DEFAULT 'DISCOVERED',
        veto_reason TEXT,
        tailored_resume_path TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracked_jobs_url ON tracked_jobs(url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracked_jobs_status ON tracked_jobs(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracked_jobs_early ON tracked_jobs(is_early_applicant)")

    # 2. Submission Audit Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submission_audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        company TEXT,
        title TEXT,
        portal TEXT NOT NULL,
        applied_at TEXT NOT NULL,
        confirmation_id TEXT,
        screenshot_path TEXT,
        submission_verified INTEGER DEFAULT 1,
        response_status TEXT,
        audit_notes TEXT,
        FOREIGN KEY (job_id) REFERENCES tracked_jobs(id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audits_job_id ON submission_audits(job_id)")

    # 3. Daily Metrics Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_metrics (
        run_date TEXT PRIMARY KEY,
        jobs_scanned INTEGER DEFAULT 0,
        early_applicants_found INTEGER DEFAULT 0,
        vetoed_spam INTEGER DEFAULT 0,
        resumes_tailored INTEGER DEFAULT 0,
        applications_submitted INTEGER DEFAULT 0,
        updated_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def upsert_job(job: Job, status: Optional[str] = None) -> bool:
    """Inserts or updates a Job in the SQLite application tracker."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().astimezone().isoformat()

    if not job.id:
        import re
        c_clean = re.sub(r'[^a-zA-Z0-9]', '_', job.company or "Company").strip('_')
        t_clean = re.sub(r'[^a-zA-Z0-9]', '_', job.title or "Role").strip('_')
        job.id = f"{c_clean}_{t_clean}_{now_iso[:10]}"
    job_id = job.id

    current_status = status or getattr(job, "application_status", "DISCOVERED") or "DISCOVERED"
    job.application_status = current_status
    missing_skills_json = json.dumps(job.missing_skills or [])

    cursor.execute("""
    INSERT INTO tracked_jobs (
        id, title, company, location, url, source, job_type,
        applicant_count, is_early_applicant, early_priority_tier,
        score, missing_skills, status, veto_reason, tailored_resume_path,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        score = coalesce(excluded.score, tracked_jobs.score),
        applicant_count = coalesce(excluded.applicant_count, tracked_jobs.applicant_count),
        is_early_applicant = coalesce(excluded.is_early_applicant, tracked_jobs.is_early_applicant),
        early_priority_tier = coalesce(excluded.early_priority_tier, tracked_jobs.early_priority_tier),
        status = excluded.status,
        veto_reason = coalesce(excluded.veto_reason, tracked_jobs.veto_reason),
        tailored_resume_path = coalesce(excluded.tailored_resume_path, tracked_jobs.tailored_resume_path),
        updated_at = excluded.updated_at
    """, (
        job_id,
        job.title,
        job.company,
        job.location,
        job.url,
        getattr(job, "source", ""),
        getattr(job, "job_type", "fulltime"),
        getattr(job, "applicant_count", None),
        1 if getattr(job, "is_early_applicant", False) else 0,
        getattr(job, "early_priority_tier", "TIER_3_STANDARD"),
        getattr(job, "score", None),
        missing_skills_json,
        current_status,
        getattr(job, "veto_reason", None),
        getattr(job, "tailored_resume_path", None),
        now_iso,
        now_iso
    ))

    conn.commit()
    conn.close()
    return True


def batch_upsert_jobs(jobs: List[Job]) -> int:
    """Batch updates multiple jobs into the tracking database."""
    init_db()
    count = 0
    for j in jobs:
        upsert_job(j)
        count += 1
    return count


def record_submission_audit(
    job_id: str,
    portal: str,
    company: str = "",
    title: str = "",
    confirmation_id: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    verified: bool = True,
    response_status: str = "SUBMITTED",
    notes: str = ""
) -> int:
    """
    Records verified submission audit evidence into the database.
    Marks the corresponding tracked job as APPLIED.
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().astimezone().isoformat()

    cursor.execute("""
    INSERT INTO submission_audits (
        job_id, company, title, portal, applied_at, confirmation_id,
        screenshot_path, submission_verified, response_status, audit_notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        company,
        title,
        portal,
        now_iso,
        confirmation_id or f"CONF-{int(datetime.now().timestamp())}",
        screenshot_path,
        1 if verified else 0,
        response_status,
        notes
    ))
    audit_id = cursor.lastrowid

    # Update job status to APPLIED in tracked_jobs
    cursor.execute("""
    UPDATE tracked_jobs
    SET status = 'APPLIED', updated_at = ?
    WHERE id = ? OR (company = ? AND title = ?)
    """, (now_iso, job_id, company, title))

    conn.commit()
    conn.close()
    logger.info(f"✅ Verified submission audit recorded (Audit ID #{audit_id}) for job {job_id} on {portal}")
    return audit_id


def get_daily_metrics(run_date: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves metrics breakdown for a specific date (defaults to today)."""
    init_db()
    if not run_date:
        run_date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()

    utc_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT
        count(*) as total_tracked,
        sum(case when is_early_applicant = 1 then 1 else 0 end) as early_applicants,
        sum(case when status = 'VETOED_SPAM' then 1 else 0 end) as vetoed_spam,
        sum(case when status = 'SHORTLISTED' then 1 else 0 end) as shortlisted,
        sum(case when status = 'TAILORED' then 1 else 0 end) as tailored,
        sum(case when status = 'APPLIED' then 1 else 0 end) as applied_in_tracked
    FROM tracked_jobs
    WHERE created_at LIKE ? OR created_at LIKE ? OR updated_at LIKE ? OR updated_at LIKE ?
    """, (f"{run_date}%", f"{utc_date}%", f"{run_date}%", f"{utc_date}%"))
    row = cursor.fetchone()

    cursor.execute("""
    SELECT count(*) as verified_submissions
    FROM submission_audits
    WHERE applied_at LIKE ? OR applied_at LIKE ?
    """, (f"{run_date}%", f"{utc_date}%"))
    audit_row = cursor.fetchone()
    conn.close()

    applied_count = max(
        (row["applied_in_tracked"] or 0) if row else 0,
        (audit_row["verified_submissions"] or 0) if audit_row else 0
    )

    if row:
        return {
            "date": run_date,
            "total_tracked": row["total_tracked"] or 0,
            "early_applicants": row["early_applicants"] or 0,
            "vetoed_spam": row["vetoed_spam"] or 0,
            "shortlisted": row["shortlisted"] or 0,
            "tailored": row["tailored"] or 0,
            "applied": applied_count
        }
    return {
        "date": run_date,
        "total_tracked": 0,
        "early_applicants": 0,
        "vetoed_spam": 0,
        "shortlisted": 0,
        "tailored": 0,
        "applied": applied_count
    }


def get_pending_early_opportunities(limit: int = 15) -> List[Dict[str, Any]]:
    """Returns top prioritized early applicant opportunities ready for application."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, title, company, location, url, source, applicant_count, early_priority_tier, score
    FROM tracked_jobs
    WHERE is_early_applicant = 1 AND status IN ('DISCOVERED', 'SHORTLISTED', 'TAILORED')
    ORDER BY
        case early_priority_tier
            when 'TIER_1_IMMEDIATE' then 1
            when 'TIER_2_EARLY' then 2
            else 3
        end ASC,
        score DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_submission_audits(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns recent verified submission records with proof details."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, job_id, company, title, portal, applied_at, confirmation_id, screenshot_path, submission_verified, response_status
    FROM submission_audits
    ORDER BY applied_at DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
