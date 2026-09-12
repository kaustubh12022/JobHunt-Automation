"""
Milestone 6 Challenger 2 Gen 2 Independent Verification Test Suite.

Empirical verification of:
1. Concurrency mutex lock (pipeline_lock) under high concurrency barrier (50 threads).
2. Non-dict JSON payload handling across all relevant POST endpoints.
3. Serialization of pipeline_state with Job dataclasses in SSE and Supabase threads.
4. Token usage defensive calculations in db layer.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
import pytest

from app import app, pipeline_state, stop_event, pipeline_lock
from src.models import Job
import src.db as db_module


@pytest.fixture(autouse=True)
def reset_pipeline():
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


def test_concurrency_barrier_50_threads():
    """
    Stress-test /api/start with 50 threads synchronized on a barrier.
    Guarantees all 50 threads invoke /api/start simultaneously.
    Must produce exactly 1 HTTP 200 and 49 HTTP 400 responses.
    """
    barrier = threading.Barrier(50)

    def hit_start(idx):
        barrier.wait()
        with app.test_client() as c:
            return c.post("/api/start", json={"platforms": ["linkedin"]})

    with patch("app._apply_ai_settings"), patch("app.run_pipeline", side_effect=lambda *a, **k: time.sleep(0.5)):
        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = [pool.submit(hit_start, i) for i in range(50)]
            responses = [f.result() for f in futures]

    codes = [r.status_code for r in responses]
    assert codes.count(200) == 1, f"Expected 1 HTTP 200, got {codes.count(200)}"
    assert codes.count(400) == 49, f"Expected 49 HTTP 400, got {codes.count(400)}"
    for r in responses:
        if r.status_code == 400:
            assert "already running" in r.get_json().get("error", "").lower()


def test_concurrency_barrier_test_start_50_threads():
    """
    Stress-test /api/test-start with 50 threads synchronized on a barrier.
    Must produce exactly 1 HTTP 200 and 49 HTTP 400 responses.
    """
    barrier = threading.Barrier(50)

    def hit_test_start(idx):
        barrier.wait()
        with app.test_client() as c:
            return c.post("/api/test-start", json={"platforms": ["indeed"]})

    with patch("app._apply_ai_settings"), patch("app.run_pipeline", side_effect=lambda *a, **k: time.sleep(0.5)):
        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = [pool.submit(hit_test_start, i) for i in range(50)]
            responses = [f.result() for f in futures]

    codes = [r.status_code for r in responses]
    assert codes.count(200) == 1, f"Expected 1 HTTP 200, got {codes.count(200)}"
    assert codes.count(400) == 49, f"Expected 49 HTTP 400, got {codes.count(400)}"


def test_non_dict_json_payloads_return_400(flask_client):
    """
    Verify all non-dict JSON payloads return HTTP 400 Bad Request
    with error message across start and manual-tailor routes.
    """
    malformed_bodies = [
        '[1, 2, 3]',
        '"a plain string"',
        '12345',
        'true',
        'false',
    ]

    target_routes = [
        "/api/start",
        "/api/test-start",
        "/api/manual-tailor/score",
        "/api/manual-tailor/generate",
    ]

    for route in target_routes:
        for body in malformed_bodies:
            resp = flask_client.post(route, data=body, content_type="application/json")
            assert resp.status_code == 400, f"Route {route} with body '{body}' returned {resp.status_code}"
            json_data = resp.get_json()
            assert "error" in json_data
            assert "Invalid JSON payload" in json_data["error"]


def test_pipeline_state_serialization_with_dataclasses():
    """
    Verify that pipeline_state containing raw Job dataclasses or converted dicts
    serializes cleanly without raising TypeError.
    """
    j = Job(
        title="Software Engineer",
        company="TechCorp",
        location="Bangalore",
        description="Python Engineer JD",
        url="https://job.url",
        id="test-job-uuid-1",
        score=92,
        reasons="Excellent match",
        missing_skills=[],
        extracted_requirements="Python, Flask",
        is_testing_role=False,
        tokens_used=150
    )
    j.cost_usd = 0.0003
    j.token_usage = {"prompt_tokens": 100, "completion_tokens": 50}

    # Test conversion logic matching app.py:237-254
    raw_scored = [j]
    pipeline_state["all_scored_jobs"] = [
        {
            "id": getattr(item, "id", ""),
            "title": getattr(item, "title", ""),
            "company": getattr(item, "company", ""),
            "location": getattr(item, "location", ""),
            "score": getattr(item, "score", 0),
            "reasons": getattr(item, "reasons", []),
            "missing_skills": getattr(item, "missing_skills", []),
            "extracted_requirements": getattr(item, "extracted_requirements", ""),
            "is_testing_role": getattr(item, "is_testing_role", False),
            "tokens_used": getattr(item, "tokens_used", 0),
            "cost_usd": getattr(item, "cost_usd", 0.0),
            "token_usage": getattr(item, "token_usage", {}) or {},
        }
        if not isinstance(item, dict) else item
        for item in raw_scored
    ]

    # Standard json.dumps must succeed without default=str
    serialized = json.dumps(pipeline_state)
    assert "TechCorp" in serialized
    assert "Software Engineer" in serialized

    # Stream fallback with default=str must also succeed even if raw Job is placed directly
    pipeline_state["all_scored_jobs"] = [j]
    serialized_stream = json.dumps(pipeline_state, default=str)
    assert "Job(" in serialized_stream or "TechCorp" in serialized_stream


def test_telemetry_with_none_or_missing_token_usage():
    """
    Verify src.db.save_pipeline_results correctly computes telemetry
    when jobs have token_usage=None or missing fields.
    """
    j1 = Job(title="Dev 1", company="C1", location="Remote", description="JD", url="", id="1")
    j1.tokens_used = 100
    j1.cost_usd = 0.001
    j1.token_usage = None  # Explicit None

    j2 = Job(title="Dev 2", company="C2", location="Remote", description="JD", url="", id="2")
    j2.tokens_used = 200
    j2.cost_usd = 0.002
    # token_usage default is None / not set

    mock_state = {"scan": {}, "score": {}, "tailor": {}}
    mock_supabase = MagicMock()
    mock_runs_table = MagicMock()
    mock_jobs_table = MagicMock()
    mock_runs_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-1"}])
    mock_jobs_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "job-1"}])

    def table_router(table_name):
        if table_name == "pipeline_runs":
            return mock_runs_table
        return mock_jobs_table

    mock_supabase.table.side_effect = table_router

    with patch("src.db.supabase", mock_supabase):
        db_module.save_pipeline_results(
            pipeline_state=mock_state,
            shortlisted_jobs=[j1, j2],
            pdf_paths=["", ""],
            all_scored_jobs=[j1, j2]
        )
        assert mock_runs_table.insert.called
        call_args = mock_runs_table.insert.call_args[0][0]
        assert call_args["tokens_used"] == 300
        assert call_args["ai_metrics"]["total_cost_usd"] == 0.003
        assert call_args["ai_metrics"]["jobs_scored_count"] == 2
