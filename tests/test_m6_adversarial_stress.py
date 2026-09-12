"""
Independent Adversarial Stress Testing for Milestone 6
Auditor: teamwork_preview_auditor_m6_1
Target: Milestone 6 (Supabase Integration & UI Audit)
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app import app, pipeline_state, stop_event
from src.models import Job
from src import db

client = app.test_client()

def test_adversarial_db_empty_and_malformed_inputs():
    """Stress-test src/db functions against empty dicts and malformed inputs."""
    # 1. Empty pipeline state and empty job lists
    db.save_pipeline_results({}, [], [])
    
    # 2. Malformed Job object missing standard attributes
    class BareJob:
        pass
    bare_job = BareJob()
    bare_job.id = "bare-1"
    bare_job.title = "Bare Title"
    bare_job.company = "Bare Co"
    bare_job.location = "Pune"
    bare_job.url = "http://bare.test"
    bare_job.score = 75
    
    with patch.object(db, 'supabase', None):
        db.save_pipeline_results({"mode": "test"}, [bare_job], [""])
        db.save_manual_job(bare_job, "")
        assert db.get_job_by_id("nonexistent") is None
        assert db.get_job_pdf_path("nonexistent") is None
        assert db.delete_pipeline_run("") == []
        assert db.delete_pipeline_run(None) == []
        assert db.delete_application("") is None
        assert db.delete_application(None) is None
        assert db.get_cached_jd_score("") is None
        assert db.get_cached_jd_score(None) is None

def test_adversarial_resolve_local_pdf_path_edge_cases():
    """Verify resolve_local_pdf_path handles path traversal, nulls, and weird URLs."""
    assert db.resolve_local_pdf_path("") == ""
    assert db.resolve_local_pdf_path(None) == ""
    
    with patch.object(db, 'get_job_pdf_path') as mock_get_path:
        # Traversal attempt
        mock_get_path.return_value = "../../../../etc/passwd"
        assert db.resolve_local_pdf_path("evil-id") == ""
        
        # Absolute nonexistent file
        mock_get_path.return_value = "C:/nonexistent/path/to/resume.pdf"
        assert db.resolve_local_pdf_path("nonexistent-file") == ""
        
        # URL with nonexistent local match
        mock_get_path.return_value = "https://example.supabase.co/storage/v1/object/public/resumes/ghost.pdf"
        assert db.resolve_local_pdf_path("ghost-url") == ""

def test_adversarial_serve_react_path_traversal():
    """Verify Flask SPA routing rejects directory traversal attempts."""
    resp = client.get('/../../config.yaml')
    # Flask / Werkzeug routing will sanitize or return 404/400
    assert resp.status_code in [404, 400]

def test_adversarial_concurrency_lock_race():
    """Simulate rapid concurrent start requests to verify running lock prevents race condition."""
    stop_event.clear()
    pipeline_state["running"] = False
    pipeline_state["phase"] = "idle"
    
    with patch('threading.Thread'):
        responses = []
        for _ in range(10):
            r = client.post('/api/start', json={"platforms": ["linkedin"]})
            responses.append(r.status_code)
            
        # First request must succeed (200), all subsequent must be blocked (400)
        assert responses[0] == 200
        assert all(code == 400 for code in responses[1:])
        assert pipeline_state["running"] is True

    # Clean up
    client.post('/api/stop')
    assert pipeline_state["running"] is False

def test_adversarial_api_settings_get_and_post_rejection():
    """Verify /api/ai-settings is GET-only and rejects POST with 405."""
    # GET must succeed and return valid settings
    resp_get = client.get('/api/ai-settings')
    assert resp_get.status_code == 200
    data = resp_get.get_json()
    assert "scoring_model" in data
    assert "tailoring_model" in data
    
    # POST is disallowed (settings are configured via start payloads)
    resp_post = client.post('/api/ai-settings', json={"scoring_model": "deepseek-chat"})
    assert resp_post.status_code == 405

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
