import psycopg2

# Supabase direct connection string
DATABASE_URL = "postgresql://postgres:Kaustubh%401202@db.hysfjbecwcljddszcjui.supabase.co:5432/postgres"

# SQL from the implementation plan
SQL = """
-- Table 1: Pipeline run history
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT NOT NULL DEFAULT 'prod',         -- prod | test | dry_run
    jobs_scraped INT DEFAULT 0,
    jobs_filtered INT DEFAULT 0,
    jobs_scored INT DEFAULT 0,
    jobs_shortlisted INT DEFAULT 0,
    resumes_generated INT DEFAULT 0,
    tokens_used INT DEFAULT 0,                 -- Added for Cost Tracking
    scrape_stats JSONB,                        -- Full stats breakdown
    platforms TEXT[],                           -- ['linkedin', 'indeed']
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Table 2: Individual jobs from each run
CREATE TABLE IF NOT EXISTS tracked_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES pipeline_runs(id),
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    url TEXT,
    source TEXT,                               -- linkedin | indeed
    score INT,
    missing_skills TEXT[],
    extracted_requirements TEXT,
    is_testing_role BOOLEAN DEFAULT FALSE,
    tailored_resume JSONB,                     -- The Delta-merged JSON
    pdf_filename TEXT,                          -- Local PDF path or Supabase URL
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Table 3: Application tracking
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES tracked_jobs(id),
    status TEXT NOT NULL DEFAULT 'generated',
    -- Statuses: generated | applied | shortlisted | interview 
    --           | offer_received | accepted | rejected | custom
    custom_status TEXT,
    notes TEXT,
    applied_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Table 4: Status change history
CREATE TABLE IF NOT EXISTS status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    old_status TEXT,
    new_status TEXT NOT NULL,
    notes TEXT,
    changed_at TIMESTAMPTZ DEFAULT now()
);

-- Table 5: JD Cache for faster re-runs
CREATE TABLE IF NOT EXISTS jd_cache (
    url TEXT PRIMARY KEY,
    score INT,
    missing_skills TEXT[],
    extracted_requirements TEXT,
    is_testing_role BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Ensure tokens_used column exists if table was already created
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS tokens_used INT DEFAULT 0;

-- Ensure we insert bucket manually via SQL if possible (Note: usually done via dashboard/API)
INSERT INTO storage.buckets (id, name, public) 
VALUES ('resumes', 'resumes', true) 
ON CONFLICT (id) DO NOTHING;
"""

def setup_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(SQL)
        conn.commit()
        cur.close()
        conn.close()
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    setup_db()
