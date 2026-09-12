"""
Milestone 6 Challenger 1 Adversarial Test Suite:
Supabase Offline Resilience, Storage Fallbacks, Error Handling & Route Verification.

Challenges:
1. Supabase offline resilience under network timeouts and connection drops.
2. Handling of invalid keys, missing tables, schema cache mismatches, and 403 RLS policies.
3. Local file preservation: guarantees local PDF files are never corrupted or deleted during DB failures.
4. Route testing: /api/resume/<job_id> under local file vs Supabase URL vs missing file vs legacy IDs.
5. Real candidate data & real-world job fixtures with edge-case telemetry (None tokens, zero values).
6. Live Supabase read verification with zero live DeepSeek API calls.
"""

import os
import gc
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from httpx import ConnectTimeout, ReadTimeout

from src.models import Job


# =====================================================================
# Fixtures & Helpers
# =====================================================================

@pytest.fixture
def dummy_pdf(tmp_path):
    """Creates a realistic dummy PDF file and returns its path."""
    pdf_path = tmp_path / "resume_kaustubh_qa.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Title (Test Resume) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF")
    return str(pdf_path)


@pytest.fixture
def real_fresher_job(jobs_200_dataset):
    """Retrieves a real-world entry-level job from the 200+ dataset fixture."""
    selected_data = None
    for j_data in jobs_200_dataset:
        if j_data.get("is_fresher_relevant") and j_data.get("city") in ["Pune", "Bangalore", "Mumbai"]:
            selected_data = j_data
            break

    if not selected_data:
        selected_data = {
            "title": "Junior QA Automation Engineer",
            "company": "Persistent Systems",
            "city": "Pune",
            "description": "Python, Selenium, SQL automation testing",
            "url": "https://in.linkedin.com/jobs/view/999",
            "platform": "linkedin"
        }

    job = Job(
        id="c0000000-0000-0000-0000-000000000001",
        title=selected_data.get("title", "QA Automation Trainee"),
        company=selected_data.get("company", "Infosys"),
        location=f"{selected_data.get('city', 'Pune')}, India",
        description=selected_data.get("description", "Job Description"),
        url=selected_data.get("url", "https://in.linkedin.com/jobs/view/1"),
        source=selected_data.get("platform", "linkedin"),
        score=85,
        missing_skills=["Docker"],
        extracted_requirements="Python, Selenium, SQL",
        is_testing_role=True,
        tokens_used=450
    )
    job.cost_usd = 0.00045
    job.token_usage = {
        "prompt_tokens": 300,
        "prompt_cache_hit_tokens": 150,
        "prompt_cache_miss_tokens": 150,
        "completion_tokens": 150
    }
    return job


# =====================================================================
# Group 1: Supabase Network Outage & Timeouts
# =====================================================================

def test_save_pipeline_results_network_timeout_on_run_insert(real_fresher_job, dummy_pdf):
    """Stress test: save_pipeline_results must not raise unhandled exception when network times out on pipeline_runs insert."""
    from src import db

    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.side_effect = ConnectTimeout("Connection timed out to Supabase")

    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 1},
        "filter": {"after": 1},
        "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }

    # Must complete cleanly without unhandled exception
    with patch.object(db, 'supabase', mock_client):
        db.save_pipeline_results(pipeline_state, [real_fresher_job], [dummy_pdf])

    # Verify local file is intact
    assert Path(dummy_pdf).exists()
    assert Path(dummy_pdf).stat().st_size > 0


def test_save_pipeline_results_network_timeout_on_job_insert(real_fresher_job, dummy_pdf):
    """Stress test: save_pipeline_results must not crash when tracked_jobs insert times out."""
    from src import db

    mock_client = MagicMock()
    mock_runs = MagicMock()
    mock_runs.insert.return_value.execute.return_value.data = [{"id": "run-timeout-test"}]

    mock_jobs = MagicMock()
    mock_jobs.insert.return_value.execute.side_effect = ReadTimeout("Read timeout on tracked_jobs")

    def table_router(tbl):
        if tbl == "pipeline_runs":
            return mock_runs
        return mock_jobs

    mock_client.table.side_effect = table_router
    mock_client.storage.from_.return_value.upload.return_value = {"Key": "resumes/sample.pdf"}

    pipeline_state = {"mode": "test"}
    with patch.object(db, 'supabase', mock_client):
        db.save_pipeline_results(pipeline_state, [real_fresher_job], [dummy_pdf])

    # Local PDF remains intact
    assert Path(dummy_pdf).exists()


def test_save_manual_job_network_timeout(real_fresher_job, dummy_pdf):
    """Stress test: save_manual_job gracefully handles network drop during manual tailoring."""
    from src import db

    mock_client = MagicMock()
    mock_client.table.side_effect = ConnectTimeout("Network down during manual save")
    mock_client.storage.from_.side_effect = ConnectTimeout("Storage unreachable")

    with patch.object(db, 'supabase', mock_client):
        db.save_manual_job(real_fresher_job, dummy_pdf)

    # Local PDF must be completely untouched
    assert Path(dummy_pdf).exists()
    assert Path(dummy_pdf).stat().st_size > 0


def test_cleanup_and_delete_network_timeouts():
    """Stress test: cleanup_old_pdfs, delete_pipeline_run, and delete_application handle network drops."""
    from src import db

    mock_client = MagicMock()
    mock_client.table.side_effect = ConnectTimeout("Supabase gateway timeout")
    mock_client.storage.from_.side_effect = ConnectTimeout("Storage gateway timeout")

    with patch.object(db, 'supabase', mock_client):
        # All must fail gracefully without unhandled exceptions
        db.cleanup_old_pdfs()
        paths = db.delete_pipeline_run("run-dead")
        assert paths == []
        app_pdf = db.delete_application("app-dead")
        assert app_pdf is None


# =====================================================================
# Group 2: Schema Mismatches, Missing Tables & PGRST Errors
# =====================================================================

def test_save_pipeline_results_ai_metrics_schema_fallback(real_fresher_job, dummy_pdf):
    """Verify fallback behavior when Supabase throws PGRST204 (column ai_metrics does not exist)."""
    from src import db

    mock_client = MagicMock()
    mock_runs = MagicMock()

    # First insert fails with PGRST204 column error
    pgrst_error = Exception("PGRST204: Could not find the 'ai_metrics' column of 'pipeline_runs' in the schema cache")
    # Second insert succeeds (fallback into scrape_stats)
    success_res = MagicMock()
    success_res.data = [{"id": "run-fallback-123"}]
    mock_runs.insert.return_value.execute.side_effect = [pgrst_error, success_res]

    mock_other = MagicMock()
    mock_other.insert.return_value.execute.return_value.data = [{"id": "item-1"}]

    def table_router(tbl):
        if tbl == "pipeline_runs":
            return mock_runs
        return mock_other

    mock_client.table.side_effect = table_router
    mock_client.storage.from_.return_value.upload.return_value = {"Key": "resumes/sample.pdf"}

    pipeline_state = {"mode": "test", "scrape_stats": {"total_scraped": 5}}

    with patch.object(db, 'supabase', mock_client):
        db.save_pipeline_results(pipeline_state, [real_fresher_job], [dummy_pdf])

    # Check that fallback insert was executed with ai_metrics embedded in scrape_stats
    assert mock_runs.insert.call_count == 2
    fallback_call_args = mock_runs.insert.call_args_list[1][0][0]
    assert "ai_metrics" not in fallback_call_args
    assert "scrape_stats" in fallback_call_args
    assert "ai_metrics" in fallback_call_args["scrape_stats"]


def test_missing_tables_does_not_crash(real_fresher_job, dummy_pdf):
    """Verify that Postgres table missing error (PGRST205) does not crash save operations."""
    from src import db

    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
        "PGRST205: Could not find the table 'public.tracked_jobs' in the schema cache"
    )

    with patch.object(db, 'supabase', mock_client):
        db.save_pipeline_results({"mode": "test"}, [real_fresher_job], [dummy_pdf])
        db.save_manual_job(real_fresher_job, dummy_pdf)


# =====================================================================
# Group 3: Storage Bucket Errors & RLS 403 Fallback
# =====================================================================

def test_storage_rls_policy_403_violation_fallback(real_fresher_job, dummy_pdf):
    """
    Stress test: Storage upload fails with 403 RLS violation (the exact real-world condition
    observed with publishable anon keys). Verify pipeline saves local file path as fallback.
    """
    from src import db

    mock_client = MagicMock()
    mock_runs = MagicMock()
    mock_runs.insert.return_value.execute.return_value.data = [{"id": "run-rls-test"}]

    mock_jobs = MagicMock()
    mock_jobs.insert.return_value.execute.return_value.data = [{"id": real_fresher_job.id}]

    mock_apps = MagicMock()
    mock_apps.insert.return_value.execute.return_value.data = [{"id": "app-rls"}]

    def table_router(tbl):
        if tbl == "pipeline_runs": return mock_runs
        if tbl == "tracked_jobs": return mock_jobs
        if tbl == "applications": return mock_apps
        return MagicMock()

    mock_client.table.side_effect = table_router

    # Storage raises 403 RLS violation
    mock_storage_bucket = MagicMock()
    mock_storage_bucket.upload.side_effect = Exception("StorageApiError: 403 new row violates row-level security policy")
    mock_client.storage.from_.return_value = mock_storage_bucket

    pipeline_state = {"mode": "test"}

    with patch.object(db, 'supabase', mock_client):
        db.save_pipeline_results(pipeline_state, [real_fresher_job], [dummy_pdf])

    # Check tracked_jobs insert payload
    job_insert_args = mock_jobs.insert.call_args[0][0]
    # In db.py, stored_pdf_url remains the local path on storage failure
    assert job_insert_args["pdf_filename"] == dummy_pdf
    # Applications table was still updated
    assert mock_apps.insert.called


# =====================================================================
# Group 4: Local File Integrity & Telemetry Precision
# =====================================================================

def test_local_file_integrity_under_all_failures(real_fresher_job, tmp_path):
    """
    Verify that regardless of catastrophic database failures,
    the generated local PDF is never truncated, modified, or deleted.
    """
    from src import db

    pdf_file = tmp_path / "protected_resume.pdf"
    original_bytes = b"%PDF-1.4 Authoritative Candidate Resume Content"
    pdf_file.write_bytes(original_bytes)

    failing_client = MagicMock()
    failing_client.table.side_effect = Exception("Catastrophic DB crash")
    failing_client.storage.from_.side_effect = Exception("Storage outage")

    with patch.object(db, 'supabase', failing_client):
        # Run pipeline save
        db.save_pipeline_results({"mode": "prod"}, [real_fresher_job], [str(pdf_file)])
        # Run manual save
        db.save_manual_job(real_fresher_job, str(pdf_file))

    # Assert byte-for-byte identical content
    assert pdf_file.exists()
    assert pdf_file.read_bytes() == original_bytes


def test_telemetry_calculation_with_omitted_telemetry_succeeds(dummy_pdf):
    """
    Verifies that when token_usage is not populated (default Job instance),
    save_pipeline_results gracefully defaults all ai_metrics fields to 0 without crashing.
    """
    from src import db

    job_omitted = Job(
        id="c0000000-0000-0000-0000-000000000003",
        title="Python Developer",
        company="TCS",
        location="Mumbai",
        description="Python",
        url="http://example.com/3",
        score=75
    )

    mock_client = MagicMock()
    mock_runs = MagicMock()
    mock_runs.insert.return_value.execute.return_value.data = [{"id": "run-telemetry-omitted"}]
    mock_client.table.side_effect = lambda tbl: mock_runs if tbl == "pipeline_runs" else MagicMock()

    with patch.object(db, 'supabase', mock_client):
        db.save_pipeline_results({"mode": "test"}, [job_omitted], [dummy_pdf])

    payload = mock_runs.insert.call_args_list[0][0][0]
    metrics = payload["ai_metrics"]
    assert metrics["total_tokens"] == 0
    assert metrics["total_cost_usd"] == 0.0
    assert metrics["input_tokens"] == 0
    assert metrics["cached_tokens"] == 0
    assert metrics["output_tokens"] == 0
    assert metrics["cache_hit_rate"] == 0.0


def test_telemetry_vulnerability_when_token_usage_is_explicitly_none(dummy_pdf):
    """
    Empirical bug reproduction: When a job has token_usage explicitly set to None,
    getattr(j, "token_usage", {}) evaluates to None (since attribute exists),
    causing src/db.py line 125 to raise AttributeError: 'NoneType' object has no attribute 'get'.
    This test verifies and captures the exact failure mode.
    """
    from src import db

    job_with_none_token_usage = Job(
        id="c0000000-0000-0000-0000-000000000002",
        title="Python Developer",
        company="TCS",
        location="Mumbai",
        description="Python",
        url="http://example.com/2",
        score=75
    )
    job_with_none_token_usage.tokens_used = None
    job_with_none_token_usage.cost_usd = None
    job_with_none_token_usage.token_usage = None

    mock_client = MagicMock()
    mock_runs = MagicMock()
    mock_runs.insert.return_value.execute.return_value.data = [{"id": "run-none-token-test"}]
    mock_client.table.side_effect = lambda tbl: mock_runs if tbl == "pipeline_runs" else MagicMock()
    with patch.object(db, 'supabase', mock_client):
        # Defended against NoneType: must complete without AttributeError
        db.save_pipeline_results({"mode": "test"}, [job_with_none_token_usage], [dummy_pdf])
    assert mock_runs.insert.called


# =====================================================================
# Group 5: PDF Path Resolution Helper (src/db.py)
# =====================================================================

def test_resolve_local_pdf_path_existing_local(tmp_path):
    """Verify resolve_local_pdf_path when path in DB is an existing local file."""
    from src import db

    pdf_file = tmp_path / "my_local_resume.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 content")

    with patch.object(db, 'get_job_pdf_path', return_value=str(pdf_file)):
        resolved = db.resolve_local_pdf_path("some-uuid")
        assert resolved == str(pdf_file)


def test_resolve_local_pdf_path_supabase_url_searches_local_directories(tmp_path):
    """Verify resolve_local_pdf_path extracts filename from Supabase URL and finds local copy."""
    from src import db

    filename = "resume_target_123.pdf"
    target_dir = tmp_path / "AutoApply_Output" / "main pipeline" / "session_1"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_pdf = target_dir / filename
    target_pdf.write_bytes(b"%PDF-1.4 target content")

    fake_config = {
        "output": {
            "desktop_path": str(tmp_path),
            "folder_name": "AutoApply_Output"
        }
    }

    url = f"https://hysfjbecwcljddszcjui.supabase.co/storage/v1/object/public/resumes/{filename}"

    with patch.object(db, 'get_job_pdf_path', return_value=url):
        with patch('src.config_loader.load_config', return_value=fake_config):
            resolved = db.resolve_local_pdf_path("uuid-test")
            assert resolved == str(target_pdf)


def test_resolve_local_pdf_path_not_found(tmp_path):
    """Verify resolve_local_pdf_path returns empty string if file does not exist locally."""
    from src import db

    fake_config = {
        "output": {
            "desktop_path": str(tmp_path),
            "folder_name": "NonExistent"
        }
    }

    with patch.object(db, 'get_job_pdf_path', return_value="https://supabase.co/resumes/ghost.pdf"):
        with patch('src.config_loader.load_config', return_value=fake_config):
            assert db.resolve_local_pdf_path("ghost-uuid") == ""

    with patch.object(db, 'get_job_pdf_path', return_value=None):
        assert db.resolve_local_pdf_path("none-uuid") == ""


# =====================================================================
# Group 6: PDF Download Route Adversarial Testing
# =====================================================================

def test_api_get_resume_local_file_exists(flask_client, tmp_path):
    """Route test: /api/resume/<job_id> returns HTTP 200 when PDF exists locally."""
    from src import db

    pdf_file = tmp_path / "valid_resume.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 valid test pdf")

    test_uuid = "11111111-1111-1111-1111-111111111111"

    with patch.object(db, 'get_job_pdf_path', return_value=str(pdf_file)):
        resp = flask_client.get(f'/api/resume/{test_uuid}')
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type") == "application/pdf"
        assert resp.data == b"%PDF-1.4 valid test pdf"
        resp.close()


def test_api_get_resume_supabase_url_with_local_fallback(flask_client, tmp_path):
    """
    Route test: If DB stores a Supabase URL, but file exists locally in output directory,
    Flask serves the local file (200 OK) rather than making a remote network request (bypassing 504).
    """
    from src import db

    filename = "resume_test_supabase_url.pdf"
    fake_output_dir = tmp_path / "AutoApply_Output" / "main pipeline" / "06sep-12-00"
    fake_output_dir.mkdir(parents=True, exist_ok=True)
    local_pdf = fake_output_dir / filename
    local_pdf.write_bytes(b"%PDF-1.4 local cached pdf")

    fake_config = {
        "output": {
            "desktop_path": str(tmp_path),
            "folder_name": "AutoApply_Output"
        }
    }

    test_uuid = "22222222-2222-2222-2222-222222222222"
    remote_url = f"https://hysfjbecwcljddszcjui.supabase.co/storage/v1/object/public/resumes/{filename}"

    with patch.object(db, 'get_job_pdf_path', return_value=remote_url):
        with patch('app.load_config', return_value=fake_config):
            resp = flask_client.get(f'/api/resume/{test_uuid}')
            assert resp.status_code == 200
            assert resp.data == b"%PDF-1.4 local cached pdf"
            resp.close()


def test_api_get_resume_supabase_url_without_local_file(flask_client, tmp_path):
    """
    Route test: If DB stores a Supabase URL and the file is NOT on local disk,
    Flask returns HTTP 302 redirecting to the remote Supabase URL.
    """
    from src import db

    fake_config = {
        "output": {
            "desktop_path": str(tmp_path),
            "folder_name": "NonExistent"
        }
    }

    test_uuid = "33333333-3333-3333-3333-333333333333"
    remote_url = "https://hysfjbecwcljddszcjui.supabase.co/storage/v1/object/public/resumes/remote_only.pdf"

    with patch.object(db, 'get_job_pdf_path', return_value=remote_url):
        with patch('app.load_config', return_value=fake_config):
            resp = flask_client.get(f'/api/resume/{test_uuid}')
            assert resp.status_code == 302
            assert resp.headers.get("Location") == remote_url
            resp.close()


def test_api_get_resume_in_memory_pipeline_fallback(flask_client, tmp_path):
    """
    Route test: If PDF path is not yet committed to Supabase, but pipeline is currently running,
    /api/resume/<job_id> falls back to reading pipeline_state["tailor"]["results"].
    """
    from app import pipeline_state
    from src import db

    pdf_file = tmp_path / "in_memory_resume.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 in-memory generated pdf")

    test_uuid = "55555555-5555-5555-5555-555555555555"
    pipeline_state["tailor"]["results"] = [
        {"id": test_uuid, "pdf_path": str(pdf_file)}
    ]

    with patch.object(db, 'get_job_pdf_path', return_value=None):
        resp = flask_client.get(f'/api/resume/{test_uuid}')
        assert resp.status_code == 200
        assert resp.data == b"%PDF-1.4 in-memory generated pdf"
        resp.close()


def test_api_get_resume_legacy_short_id(flask_client):
    """
    Route test: Passing an old 8-char legacy ID returns 404 with friendly message
    instead of triggering a Postgres 22P02 invalid UUID error.
    """
    resp = flask_client.get('/api/resume/12345678')
    assert resp.status_code == 404
    assert "Legacy ID format no longer supported" in resp.get_json()["error"]
    resp.close()


def test_api_get_resume_deleted_or_missing(flask_client):
    """Route test: Local path points to deleted file -> returns 404."""
    from src import db

    test_uuid = "44444444-4444-4444-4444-444444444444"
    with patch.object(db, 'get_job_pdf_path', return_value="C:/nonexistent/path/deleted.pdf"):
        resp = flask_client.get(f'/api/resume/{test_uuid}')
        assert resp.status_code == 404
        assert "not found or local file deleted" in resp.get_json()["error"]
        resp.close()


def test_api_manual_resume_route(flask_client):
    """Route test: /api/resume/manual/<filename> serves local file or 404."""
    manual_dir = Path.cwd() / "output" / "manual"
    manual_dir.mkdir(parents=True, exist_ok=True)
    test_pdf = manual_dir / "test_challenger_manual.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 manual resume test")

    resp = flask_client.get('/api/resume/manual/test_challenger_manual.pdf')
    assert resp.status_code == 200
    assert resp.data == b"%PDF-1.4 manual resume test"
    resp.close()

    missing_resp = flask_client.get('/api/resume/manual/nonexistent_manual.pdf')
    assert missing_resp.status_code == 404
    missing_resp.close()

    del resp
    del missing_resp
    gc.collect()
    try:
        if test_pdf.exists():
            test_pdf.unlink()
    except PermissionError:
        pass


# =====================================================================
# Group 7: Live Supabase Read Verification (Zero DeepSeek calls)
# =====================================================================

def test_live_supabase_connectivity_and_read():
    """
    Empirically verifies connectivity to the live Supabase instance with project credentials.
    Performs read-only query; consumes 0 DeepSeek API calls.
    """
    from src.db import supabase
    if supabase is None:
        pytest.skip("Supabase client is not configured in current environment")

    # Read-only query to tracked_jobs
    res = supabase.table("tracked_jobs").select("id").limit(1).execute()
    assert hasattr(res, "data"), "Live Supabase response must have data attribute"
    assert isinstance(res.data, list), "Response data must be a list"
