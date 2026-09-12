"""
Milestone 6 Test Suite: Supabase Integration & UI Audit.

Verifies:
1. Frontend lib files (api.js, supabase.js) existence and proper exports.
2. Frontend dist build verification (index.html, compiled assets).
3. Flask root and SPA route serving from frontend/dist.
4. Flask API endpoints (/api/status, /api/config, /api/ai-settings, /api/logs).
5. Pipeline start/stop controls and running lock semantics.
6. Supabase database functions, storage, and defensive offline fallback.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.models import Job


@pytest.fixture(autouse=True)
def reset_app_pipeline_state():
    """Ensures clean pipeline state before and after each test."""
    from app import pipeline_state, stop_event
    stop_event.clear()
    pipeline_state["running"] = False
    pipeline_state["phase"] = "idle"
    pipeline_state["mode"] = "idle"
    pipeline_state["status_text"] = ""
    yield
    stop_event.clear()
    pipeline_state["running"] = False
    pipeline_state["phase"] = "idle"
    pipeline_state["mode"] = "idle"
    pipeline_state["status_text"] = ""


# =====================================================================
# 1. Frontend Library Files Verification
# =====================================================================

def test_frontend_lib_files_exist():
    """Verify frontend/src/lib/api.js and supabase.js exist and export required symbols."""
    workspace_root = Path(__file__).resolve().parent.parent
    lib_dir = workspace_root / "frontend" / "src" / "lib"
    assert lib_dir.exists(), f"Directory {lib_dir} must exist"

    supabase_js = lib_dir / "supabase.js"
    assert supabase_js.exists(), "frontend/src/lib/supabase.js must exist"
    supabase_content = supabase_js.read_text(encoding="utf-8")
    assert "createClient" in supabase_content, "supabase.js must import createClient"
    assert "export const supabase" in supabase_content or "export { supabase" in supabase_content, (
        "supabase.js must export supabase client"
    )
    assert "https://hysfjbecwcljddszcjui.supabase.co" in supabase_content, (
        "supabase.js must contain the project Supabase URL fallback"
    )
    assert "sb_publishable_UwSom1GLyDkoTDha4ykc-w__AO0LPaI" in supabase_content, (
        "supabase.js must contain the project publishable key fallback"
    )

    api_js = lib_dir / "api.js"
    assert api_js.exists(), "frontend/src/lib/api.js must exist"
    api_content = api_js.read_text(encoding="utf-8")
    assert "export async function api" in api_content or "export function api" in api_content or "export { api" in api_content, (
        "api.js must export api fetch helper"
    )
    assert "fetch(" in api_content, "api.js must invoke native fetch"


# =====================================================================
# 2. Frontend Dist Build Verification
# =====================================================================

def test_frontend_dist_built():
    """Verify that frontend/dist/ was successfully generated with index.html and assets."""
    workspace_root = Path(__file__).resolve().parent.parent
    dist_dir = workspace_root / "frontend" / "dist"
    assert dist_dir.exists(), "frontend/dist/ must exist"
    index_html = dist_dir / "index.html"
    assert index_html.exists(), "frontend/dist/index.html must exist"
    assert index_html.stat().st_size > 0, "frontend/dist/index.html must not be empty"

    assets_dir = dist_dir / "assets"
    assert assets_dir.exists(), "frontend/dist/assets/ directory must exist"
    asset_files = list(assets_dir.glob("*"))
    assert len(asset_files) >= 2, "frontend/dist/assets/ must contain bundled JS and CSS files"
    has_js = any(f.suffix == ".js" for f in asset_files)
    has_css = any(f.suffix == ".css" for f in asset_files)
    assert has_js, "frontend/dist/assets/ must contain compiled JavaScript bundle"
    assert has_css, "frontend/dist/assets/ must contain compiled CSS bundle"


# =====================================================================
# 3. Flask Serving Verification
# =====================================================================

def test_flask_serves_frontend(flask_client):
    """Verify Flask serves frontend/dist/index.html on GET / with HTTP 200."""
    resp = flask_client.get('/')
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("Content-Type", "")
    html_text = resp.get_data(as_text=True)
    assert "<html" in html_text.lower()
    assert "root" in html_text.lower() or "vite" in html_text.lower()


def test_flask_serves_spa_routes(flask_client):
    """Verify Flask fallback routes serve index.html for client-side SPA navigation."""
    for spa_path in ['/tracker', '/pipeline', '/jobs']:
        resp = flask_client.get(spa_path)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("Content-Type", "")
        html_text = resp.get_data(as_text=True)
        assert "<html" in html_text.lower()


def test_flask_serves_static_assets(flask_client):
    """Verify Flask serves static files from frontend/dist/."""
    workspace_root = Path(__file__).resolve().parent.parent
    dist_assets = workspace_root / "frontend" / "dist" / "assets"
    css_files = list(dist_assets.glob("*.css"))
    if css_files:
        css_name = css_files[0].name
        resp = flask_client.get(f'/assets/{css_name}')
        assert resp.status_code == 200


# =====================================================================
# 4. Flask API Routes Verification
# =====================================================================

def test_flask_api_routes(flask_client):
    """Verify core API routes (/api/status, /api/config, /api/ai-settings) return 200 and expected schemas."""
    # /api/status
    status_resp = flask_client.get('/api/status')
    assert status_resp.status_code == 200
    status_data = status_resp.get_json()
    assert isinstance(status_data, dict)
    for required_key in ["running", "mode", "phase", "scan", "score", "tailor"]:
        assert required_key in status_data, f"Status response missing key: {required_key}"

    # /api/config
    config_resp = flask_client.get('/api/config')
    assert config_resp.status_code == 200
    config_data = config_resp.get_json()
    assert isinstance(config_data, dict)
    for section in ["ai", "search", "scoring", "output"]:
        assert section in config_data, f"Config response missing section: {section}"

    # /api/ai-settings
    ai_resp = flask_client.get('/api/ai-settings')
    assert ai_resp.status_code == 200
    ai_data = ai_resp.get_json()
    assert isinstance(ai_data, dict)
    assert "scoring_model" in ai_data
    assert "tailoring_model" in ai_data


def test_flask_logs_endpoint(flask_client):
    """Verify /api/logs returns 200 OK and a list of log entries."""
    resp = flask_client.get('/api/logs')
    assert resp.status_code == 200
    logs = resp.get_json()
    assert isinstance(logs, list)


# =====================================================================
# 5. Flask Pipeline Start / Stop & Running Lock
# =====================================================================

def test_flask_start_stop_controls(flask_client):
    """Verify starting and stopping pipeline state machine cleanly."""
    from app import pipeline_state

    with patch('threading.Thread') as mock_thread_cls:
        mock_instance = MagicMock()
        mock_thread_cls.return_value = mock_instance

        # 1. Start prod pipeline
        resp = flask_client.post('/api/start', json={"platforms": ["linkedin"]})
        assert resp.status_code == 200
        assert "Started successfully" in resp.get_json().get("message", "")
        assert pipeline_state["running"] is True
        assert pipeline_state["mode"] == "prod"

        # 2. Prevent duplicate start while running (lock verification)
        duplicate_resp = flask_client.post('/api/start', json={})
        assert duplicate_resp.status_code == 400
        assert "already running" in duplicate_resp.get_json().get("error", "")

        duplicate_test = flask_client.post('/api/test-start', json={})
        assert duplicate_test.status_code == 400
        assert "already running" in duplicate_test.get_json().get("error", "")

        # 3. Stop pipeline
        stop_resp = flask_client.post('/api/stop')
        assert stop_resp.status_code == 200
        assert pipeline_state["running"] is False
        assert pipeline_state["phase"] == "idle"

        # 4. Start test pipeline
        test_start_resp = flask_client.post('/api/test-start', json={"platforms": ["indeed"]})
        assert test_start_resp.status_code == 200
        assert pipeline_state["running"] is True
        assert pipeline_state["mode"] == "test"


# =====================================================================
# 6. Supabase Defensive Handling & Offline Fallback
# =====================================================================

def test_supabase_db_defensive_handling_no_client():
    """Verify all src/db functions execute cleanly without exceptions when supabase is None."""
    from src import db

    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 1},
        "filter": {"after": 1},
        "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }
    job = Job(title="QA Trainee", company="Infosys", location="Pune", description="QA", url="http://example.com/job", id="j1")

    with patch.object(db, 'supabase', None):
        # None of these should raise unhandled exceptions
        db.save_pipeline_results(pipeline_state, [job], [""])
        db.save_manual_job(job, "")
        assert db.get_cached_jd_score("http://example.com/job") is None
        db.save_jd_cache("http://example.com/job", 80, ["Git"], "QA", True)
        db.cleanup_old_pdfs()
        assert db.delete_pipeline_run("nonexistent-run") == []
        assert db.get_job_pdf_path("j1") is None
        assert db.get_job_by_id("j1") is None
        assert db.delete_application("app1") is None


def test_supabase_db_defensive_handling_failing_client():
    """Verify src/db functions gracefully handle database timeouts/exceptions without process crash."""
    from src import db

    failing_client = MagicMock()
    failing_client.table.side_effect = Exception("Supabase connection refused (offline)")
    failing_client.storage.from_.side_effect = Exception("Storage service unavailable")

    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 1},
        "filter": {"after": 1},
        "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }
    job = Job(title="Java Fresher", company="Wipro", location="Bangalore", description="Java", url="http://example.com/j2", id="j2")

    with patch.object(db, 'supabase', failing_client):
        # save_pipeline_results catches DB error gracefully
        db.save_pipeline_results(pipeline_state, [job], [""])

        # save_manual_job catches DB error gracefully
        db.save_manual_job(job, "")

        # get_cached_jd_score returns None on DB error
        cached = db.get_cached_jd_score("http://example.com/j2")
        assert cached is None

        # save_jd_cache does not crash
        db.save_jd_cache("http://example.com/j2", 90, [], "Java", False)

        # cleanup_old_pdfs does not crash
        db.cleanup_old_pdfs()

        # delete_pipeline_run returns empty list on failure
        deleted_paths = db.delete_pipeline_run("run-123")
        assert deleted_paths == []

        # get_job_pdf_path returns None on error
        assert db.get_job_pdf_path("j2") is None

        # get_job_by_id returns None on error
        assert db.get_job_by_id("j2") is None

        # delete_application returns None on error
        assert db.delete_application("app-123") is None


def test_supabase_storage_offline_fallback(mock_supabase, tmp_path):
    """Verify that if Supabase Storage upload fails, pipeline execution finishes with local path fallback."""
    from src import db

    # Create dummy local PDF
    pdf_file = tmp_path / "resume_test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy pdf content")

    mock_supabase.storage.from_().upload.side_effect = Exception("Upload timeout 504")

    pipeline_state = {
        "mode": "test",
        "scan": {"total_found": 1},
        "filter": {"after": 1},
        "score": {"scored": 1, "shortlisted": 1},
        "phase": "saving"
    }
    job = Job(title="QA Engineer", company="Cognizant", location="Pune", description="QA", url="http://example.com/j3", id="j3")

    with patch.object(db, 'supabase', mock_supabase):
        db.save_pipeline_results(pipeline_state, [job], [str(pdf_file)])
        # Verify table inserts still completed
        mock_supabase.table.assert_any_call("pipeline_runs")
        mock_supabase.table.assert_any_call("tracked_jobs")
        mock_supabase.table.assert_any_call("applications")
