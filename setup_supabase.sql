-- Table 1: Pipeline run history
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT NOT NULL DEFAULT 'prod',         -- prod | test | dry_run
    jobs_scraped INT DEFAULT 0,
    jobs_filtered INT DEFAULT 0,
    jobs_scored INT DEFAULT 0,
    jobs_shortlisted INT DEFAULT 0,
    resumes_generated INT DEFAULT 0,
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
    description TEXT,
    url TEXT,
    source TEXT,                               -- linkedin | indeed
    score INT,
    missing_skills TEXT[],
    extracted_requirements TEXT,
    is_testing_role BOOLEAN DEFAULT FALSE,
    tailored_resume JSONB,                     -- The Delta-merged JSON
    pdf_filename TEXT,                          -- Local PDF path
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

-- IMPORTANT: Disable Row Level Security (RLS) to allow the python backend to insert data without authentication
ALTER TABLE pipeline_runs DISABLE ROW LEVEL SECURITY;
ALTER TABLE tracked_jobs DISABLE ROW LEVEL SECURITY;
ALTER TABLE applications DISABLE ROW LEVEL SECURITY;
ALTER TABLE status_history DISABLE ROW LEVEL SECURITY;
