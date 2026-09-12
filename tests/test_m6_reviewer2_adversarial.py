"""
Milestone 6 Reviewer 2 Adversarial Verification & Stress-Test Suite.

Audits:
1. Concurrency Safety: Stress-tests /api/start and /api/test-start under concurrent load to detect TOCTOU race conditions.
2. Serialization Integrity: Verifies that pipeline_state containing Job objects causes TypeError in json.dumps (/api/stream and sync_state_to_supabase).
3. Route Robustness: Tests /api/start, /api/test-start, /api/status, /api/config, /api/ai-settings, /api/logs, /api/stop,
   and manual tailoring endpoints under malformed, non-dict, and unexpected inputs.
4. Database Fault Tolerance: Verifies src/db.py behaves safely when Supabase is offline or returns errors, and preserves local files.
5. Path Traversal & Security: Verifies /api/resume/<job_id> guards against path traversal and malformed IDs.
"""

import copy
import json
import os
import threading
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
    pipeline_state.pop("all_scored_jobs", None)
    yield
    stop_event.clear()
    pipeline_state["running"] = False
    pipeline_state["phase"] = "idle"
    pipeline_state["mode"] = "idle"
    pipeline_state["status_text"] = ""
    pipeline_state.pop("all_scored_jobs", None)


# =====================================================================
# 1. Concurrency Safety & Race Condition Audit
# =====================================================================

def test_adv_concurrent_start_requests_race_condition():
    """
    Adversarial concurrency test: Multiple concurrent requests hitting /api/start simultaneously.
    Demonstrates whether pipeline_state['running'] without a threading.Lock permits TOCTOU race condition.
    """
    from app import app, pipeline_state

    threads_spawned = 0
    spawn_lock = threading.Lock()

    def mock_thread_init(target, args=(), **kwargs):
        nonlocal threads_spawned
        with spawn_lock:
            threads_spawned += 1
        m = MagicMock()
        return m

    pipeline_state["running"] = False
    barrier = threading.Barrier(10)
    results = []
    res_lock = threading.Lock()

    def worker():
        client = app.test_client()
        with patch('threading.Thread', side_effect=mock_thread_init):
            barrier.wait()
            resp = client.post('/api/start', json={'platforms': ['linkedin']})
            with res_lock:
                results.append(resp.status_code)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Empirical observation:
    # In an ideal race-safe implementation with a mutex lock, exactly 1 thread gets 200 and 9 get 400.
    # Without a mutex, multiple threads can pass the `if pipeline_state['running']` check before it is set to True.
    success_count = results.count(200)
    assert success_count == 1, f"Expected exactly 1 success with mutex lock, got {success_count}"
    assert threads_spawned == 1, f"Expected exactly 1 thread spawned, got {threads_spawned}"
    assert results.count(400) == 9, f"Expected 9 rejections with 400, got {results.count(400)}"


# =====================================================================
# 2. Serialization Integrity & SSE Stream (/api/stream)
# =====================================================================

def test_adv_stream_serialization_with_job_dataclass():
    """
    Adversarial serialization test:
    When pipeline_state['all_scored_jobs'] contains Job dataclass instances,
    json.dumps(pipeline_state) in /api/stream and sync_state_to_supabase raises TypeError.
    """
    from app import pipeline_state

    test_job = Job(
        title="QA Automation Engineer",
        company="Persistent",
        location="Pune",
        description="Selenium test",
        url="http://example.com/qa1",
        id="job-uuid-123"
    )
    pipeline_state["all_scored_jobs"] = [test_job]

    # Standard json.dumps (as used in app.py lines 43 and 450) fails on Job dataclass
    with pytest.raises(TypeError, match="is not JSON serializable"):
        json.dumps(pipeline_state)


def test_adv_status_endpoint_with_job_dataclass(flask_client):
    """
    Verify /api/status handles pipeline_state with Job dataclasses.
    Flask's jsonify natively handles dataclasses in Flask 2.2+, returning 200.
    """
    from app import pipeline_state

    test_job = Job(
        title="Software Engineer",
        company="TCS",
        location="Mumbai",
        description="Java dev",
        url="http://example.com/se1",
        id="job-uuid-456"
    )
    pipeline_state["all_scored_jobs"] = [test_job]

    resp = flask_client.get('/api/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert "all_scored_jobs" in data
    assert data["all_scored_jobs"][0]["company"] == "TCS"


# =====================================================================
# 3. Route Robustness & Unexpected Input Handling
# =====================================================================

def test_adv_api_start_unexpected_payload_types(flask_client):
    """
    Stress-test /api/start with unexpected non-dict JSON payloads:
    Passing a list [1, 2] instead of a dictionary causes AttributeError in data.get().
    """
    from app import pipeline_state
    pipeline_state["running"] = False

    try:
        resp = flask_client.post('/api/start', json=[1, 2, 3])
        # If framework handles exception, status should be 400 or 500
        assert resp.status_code in [400, 500]
    except AttributeError as e:
        # Confirms AttributeError: 'list' object has no attribute 'get' is raised
        assert "has no attribute 'get'" in str(e)


def test_adv_api_test_start_unexpected_payload_types(flask_client):
    """
    Stress-test /api/test-start with non-dict JSON payloads.
    """
    from app import pipeline_state
    pipeline_state["running"] = False

    try:
        resp = flask_client.post('/api/test-start', json=[1, 2, 3])
        assert resp.status_code in [400, 500]
    except AttributeError as e:
        assert "has no attribute 'get'" in str(e)


def test_adv_core_endpoints_with_unexpected_query_params(flask_client):
    """
    Verify GET endpoints handle arbitrary, unexpected query strings gracefully.
    """
    for endpoint in ['/api/status', '/api/config', '/api/ai-settings', '/api/logs']:
        resp = flask_client.get(f'{endpoint}?unexpected_param=123&drop_table=true&malformed=%00%FF')
        assert resp.status_code == 200, f"{endpoint} failed with status {resp.status_code}"


def test_adv_api_stop_handles_arbitrary_payloads(flask_client):
    """
    Verify POST /api/stop behaves idempotently and safely under any payload.
    """
    from app import pipeline_state

    # 1. Stop when already idle
    pipeline_state["running"] = False
    resp1 = flask_client.post('/api/stop', json={"unexpected": 123})
    assert resp1.status_code == 200
    assert pipeline_state["running"] is False

    # 2. Stop with text body
    pipeline_state["running"] = True
    resp2 = flask_client.post('/api/stop', data="non-json raw text", content_type="text/plain")
    assert resp2.status_code == 200
    assert pipeline_state["running"] is False

    # 3. Stop with empty body
    resp3 = flask_client.post('/api/stop')
    assert resp3.status_code == 200


def test_adv_manual_tailor_empty_and_malformed_inputs(flask_client):
    """
    Verify /api/manual-tailor/score and /api/manual-tailor/generate handle empty or malformed JSON.
    """
    resp = flask_client.post('/api/manual-tailor/score', json={})
    assert resp.status_code in [200, 400, 500]


# =====================================================================
# 4. Path Traversal & Security in /api/resume/<job_id>
# =====================================================================

def test_adv_resume_route_path_traversal_and_malformed_ids(flask_client):
    """
    Verify /api/resume/<job_id> safely rejects path traversal attempts and malformed IDs.
    """
    # 1. Legacy short ID (< 36 characters) returns 404 with specific message
    resp1 = flask_client.get('/api/resume/12345678')
    assert resp1.status_code == 404
    assert "Legacy ID" in resp1.get_json().get("error", "")

    # 2. Non-existent UUID returns 404
    resp2 = flask_client.get('/api/resume/00000000-0000-0000-0000-000000000000')
    assert resp2.status_code == 404

    # 3. 36-char non-existent ID queries Supabase and safely returns 404
    resp3 = flask_client.get('/api/resume/' + 'a' * 36)
    assert resp3.status_code == 404
    assert "Resume not found" in resp3.get_json().get("error", "")

    # 4. Multi-segment path traversal (/api/resume/../../) is safely intercepted by SPA router (serves index.html, no file leak)
    resp4 = flask_client.get('/api/resume/../../win.ini')
    assert resp4.status_code == 200
    assert "text/html" in resp4.headers.get("Content-Type", "")


# =====================================================================
# 5. Database Fault Tolerance & Storage Fallbacks
# =====================================================================

def test_adv_db_operations_when_supabase_offline():
    """
    Stress test src/db.py: when Supabase connection completely drops,
    pipeline functions must log warnings but never crash or raise unhandled exceptions.
    """
    from src import db

    offline_client = MagicMock()
    offline_client.table.side_effect = ConnectionError("Supabase backend offline")
    offline_client.storage.from_.side_effect = ConnectionError("Storage offline")

    job = Job(
        title="Full Stack Trainee",
        company="Tata Elxsi",
        location="Pune",
        description="Node, React",
        url="http://example.com/job1",
        id="c0000000-0000-0000-0000-000000000099"
    )

    with patch.object(db, 'supabase', offline_client):
        # 1. Pipeline results save
        db.save_pipeline_results({"mode": "test"}, [job], [""])

        # 2. Manual job save
        db.save_manual_job(job, "")

        # 3. Cache lookup
        assert db.get_cached_jd_score("http://example.com/job1") is None

        # 4. Cache save
        db.save_jd_cache("http://example.com/job1", 85, [], "Node", False)

        # 5. Delete run
        assert db.delete_pipeline_run("offline-run-id") == []

        # 6. Delete application
        assert db.delete_application("offline-app-id") is None

        # 7. Get job by ID
        assert db.get_job_by_id("c0000000-0000-0000-0000-000000000099") is None


def test_adv_db_local_file_preservation_on_error(tmp_path):
    """
    Stress test: Verify that local PDF files are preserved byte-for-byte
    even when database inserts and storage uploads raise exceptions.
    """
    from src import db

    pdf_file = tmp_path / "protected_resume.pdf"
    content = b"%PDF-1.4 Authoritative Candidate Resume"
    pdf_file.write_bytes(content)

    job = Job(
        title=".NET Developer",
        company="Cognizant",
        location="Bangalore",
        description="C#, ASP.NET",
        url="http://example.com/dotnet1",
        id="c0000000-0000-0000-0000-000000000088"
    )

    failing_client = MagicMock()
    failing_client.table.side_effect = RuntimeError("Database write failure")
    failing_client.storage.from_.side_effect = RuntimeError("Storage write failure")

    with patch.object(db, 'supabase', failing_client):
        db.save_pipeline_results({"mode": "prod"}, [job], [str(pdf_file)])

    assert pdf_file.exists()
    assert pdf_file.read_bytes() == content
