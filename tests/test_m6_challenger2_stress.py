"""
Milestone 6 Adversarial Challenge Test Suite by Challenger 2.

Focus Areas:
1. Concurrency Stress: Rapid concurrent POST requests to /api/start and /api/test-start
   verifying thread safety and running lock semantics (exactly 1 succeeds with 200, all others 400).
2. Endpoint Stress: Calling Flask routes (/api/status, /api/config, /api/ai-settings, /api/logs, /api/stop)
   with malformed payloads, injection attempts, and across various pipeline phases. Zero unhandled 500s.
3. Frontend Assets Integrity: Verifying frontend/dist/index.html scripts, stylesheets,
   and icons are served with HTTP 200 without broken 404 links.
4. Edge Case Payload Handling on pipeline start endpoints.
"""

import os
import re
import time
import concurrent.futures
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app import app, pipeline_state, stop_event


@pytest.fixture(autouse=True)
def clean_pipeline_state():
    """Ensure pipeline state is reset to idle before and after every test."""
    stop_event.clear()
    pipeline_state["running"] = False
    pipeline_state["phase"] = "idle"
    pipeline_state["mode"] = "idle"
    pipeline_state["status_text"] = ""
    pipeline_state["scan"] = {
        "total_found": 0,
        "current_platform": "",
        "current_city": "",
        "current_term": "",
        "combos_done": 0,
        "combos_total": 0,
        "live_jobs": []
    }
    yield
    stop_event.clear()
    pipeline_state["running"] = False
    pipeline_state["phase"] = "idle"
    pipeline_state["mode"] = "idle"
    pipeline_state["status_text"] = ""


# =====================================================================
# 1. Concurrency Stress Tests
# =====================================================================

def test_concurrency_start_sequential_rejection(flask_client):
    """
    Verify that once /api/start initiates a run, subsequent calls return HTTP 400 with error JSON.
    """
    def mock_run_pipeline(*args, **kwargs):
        time.sleep(0.4)

    with patch("app.run_pipeline", side_effect=mock_run_pipeline):
        resp1 = flask_client.post("/api/start", json={"platforms": ["linkedin"]})
        assert resp1.status_code == 200
        assert "Started successfully" in resp1.get_json().get("message", "")

        # Immediate subsequent calls must be rejected with 400
        resp2 = flask_client.post("/api/start", json={"platforms": ["linkedin"]})
        assert resp2.status_code == 400
        assert "already running" in resp2.get_json().get("error", "").lower()

        resp3 = flask_client.post("/api/test-start", json={"platforms": ["indeed"]})
        assert resp3.status_code == 400
        assert "already running" in resp3.get_json().get("error", "").lower()

        assert pipeline_state["running"] is True
        assert pipeline_state["mode"] == "prod"


def test_concurrency_test_start_lock():
    """
    Stress-test /api/test-start with rapid subsequent requests.
    Once initiated, subsequent calls return HTTP 400 with error JSON.
    """
    def mock_run_pipeline(*args, **kwargs):
        time.sleep(0.4)

    with patch("app.run_pipeline", side_effect=mock_run_pipeline):
        def send_test_start(i):
            time.sleep(i * 0.01)  # 10ms stagger
            with app.test_client() as client:
                return client.post("/api/test-start", json={"platforms": ["indeed"]})

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_test_start, i) for i in range(10)]
            responses = [f.result() for f in futures]

        status_codes = [r.status_code for r in responses]
        assert status_codes.count(200) == 1, f"Expected exactly 1 HTTP 200, got: {status_codes.count(200)}"
        assert status_codes.count(400) == 9, f"Expected exactly 9 HTTP 400, got: {status_codes.count(400)}"

        assert pipeline_state["running"] is True
        assert pipeline_state["mode"] == "test"


def test_concurrency_interleaved_start_and_test_start():
    """
    Stress-test interleaved rapid calls across /api/start and /api/test-start.
    Across 20 mixed requests, exactly 1 must start and 19 must receive HTTP 400 with error JSON.
    """
    def mock_run_pipeline(*args, **kwargs):
        time.sleep(0.5)

    with patch("app.run_pipeline", side_effect=mock_run_pipeline):
        def send_mixed(i):
            time.sleep(i * 0.005)  # 5ms stagger
            endpoint = "/api/start" if i % 2 == 0 else "/api/test-start"
            with app.test_client() as client:
                return client.post(endpoint, json={"platforms": ["linkedin", "indeed"]})

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_mixed, i) for i in range(20)]
            responses = [f.result() for f in futures]

        status_codes = [r.status_code for r in responses]
        assert status_codes.count(200) == 1, f"Expected exactly 1 HTTP 200, got: {status_codes.count(200)}"
        assert status_codes.count(400) == 19, f"Expected exactly 19 HTTP 400, got: {status_codes.count(400)}"


def test_concurrency_stop_and_restart(flask_client):
    """
    Verify /api/stop releases the running lock and allows subsequent start requests.
    """
    def mock_run_pipeline(*args, **kwargs):
        time.sleep(0.3)

    with patch("app.run_pipeline", side_effect=mock_run_pipeline):
        # 1. Start prod
        resp1 = flask_client.post("/api/start", json={})
        assert resp1.status_code == 200
        assert pipeline_state["running"] is True

        # 2. Confirmed locked
        resp2 = flask_client.post("/api/start", json={})
        assert resp2.status_code == 400

        # 3. Stop
        stop_resp = flask_client.post("/api/stop")
        assert stop_resp.status_code == 200
        assert pipeline_state["running"] is False
        assert pipeline_state["phase"] == "idle"

        # 4. Start test pipeline now works
        resp3 = flask_client.post("/api/test-start", json={})
        assert resp3.status_code == 200
        assert pipeline_state["running"] is True
        assert pipeline_state["mode"] == "test"


def test_concurrency_rapid_stops():
    """
    Verify rapid concurrent /api/stop calls are idempotent and non-crashing.
    """
    pipeline_state["running"] = True
    pipeline_state["phase"] = "scoring"

    def send_stop(i):
        with app.test_client() as client:
            return client.post("/api/stop")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_stop, i) for i in range(10)]
        responses = [f.result() for f in futures]

    assert all(r.status_code == 200 for r in responses)
    assert pipeline_state["running"] is False
    assert pipeline_state["phase"] == "idle"


# =====================================================================
# 2. Endpoint Stress & Malformed Payload Tests
# =====================================================================

def test_endpoints_get_routes_malformed_queries(flask_client):
    """
    Call GET endpoints (/api/status, /api/config, /api/ai-settings, /api/logs)
    with SQLi, XSS, large queries, and special characters across all pipeline phases.
    Verify 0 unhandled 500 errors.
    """
    phases = ["idle", "scanning", "filtering", "scoring", "tailoring", "saving", "done", "error"]
    routes = ["/api/status", "/api/config", "/api/ai-settings", "/api/logs"]
    test_queries = [
        "",
        "?q=" + "Z" * 2000,
        "?id=1%27%20OR%201=1--",
        "?xss=%3Cscript%3Ealert(1)%3C/script%3E",
        "?unicode=%E2%9C%A8%F0%9F%9A%80",
        "?nested[a][b]=1&flag=true&flag=false",
    ]

    for phase in phases:
        pipeline_state["phase"] = phase
        pipeline_state["running"] = (phase not in ["idle", "done", "error"])
        for route in routes:
            for query in test_queries:
                resp = flask_client.get(route + query)
                assert resp.status_code == 200, (
                    f"GET {route}{query} during phase {phase} returned {resp.status_code}"
                )
                assert resp.is_json, f"GET {route}{query} did not return JSON"


def test_stop_endpoint_malformed_payloads(flask_client):
    """
    Call POST /api/stop with empty body, plain text, invalid JSON, and binary bytes
    across various pipeline states. Verify 0 unhandled 500 errors.
    """
    phases = ["idle", "scanning", "scoring", "saving", "done"]
    payloads = [
        (b"", "text/plain"),
        (b"{broken json", "application/json"),
        (b"[1, 2, 3]", "application/json"),
        (b"\"quoted string\"", "application/json"),
        (b"12345", "application/json"),
        (b'{"arbitrary": "data", "unexpected_field": [1, 2]}', "application/json"),
        (b"\x00\x01\x02\xff\xfe", "application/octet-stream"),
    ]

    for phase in phases:
        pipeline_state["phase"] = phase
        pipeline_state["running"] = True
        for body, ctype in payloads:
            resp = flask_client.post("/api/stop", data=body, content_type=ctype)
            assert resp.status_code == 200, (
                f"POST /api/stop with {ctype} returned {resp.status_code} (phase={phase})"
            )
            assert resp.is_json
            assert resp.get_json().get("message") == "Pipeline aborted."
            assert pipeline_state["running"] is False


def test_endpoint_method_mismatch_never_500(flask_client):
    """
    Verify HTTP method mismatches on routes return 405 Method Not Allowed or SPA fallback, never 500.
    """
    # GET-only routes should strictly reject POST, PUT, DELETE with 405
    get_only = ["/api/status", "/api/config", "/api/ai-settings", "/api/logs"]
    for route in get_only:
        resp_post = flask_client.post(route, json={})
        assert resp_post.status_code == 405, f"Expected 405 on POST {route}, got {resp_post.status_code}"
        resp_put = flask_client.put(route, json={})
        assert resp_put.status_code == 405, f"Expected 405 on PUT {route}, got {resp_put.status_code}"
        resp_del = flask_client.delete(route)
        assert resp_del.status_code == 405, f"Expected 405 on DELETE {route}, got {resp_del.status_code}"

    # POST-only routes: verify none return unhandled 500
    post_only = ["/api/start", "/api/test-start", "/api/stop"]
    for route in post_only:
        resp_get = flask_client.get(route)
        assert resp_get.status_code in [200, 405], f"Unexpected code on GET {route}: {resp_get.status_code}"
        resp_put = flask_client.put(route, json={})
        assert resp_put.status_code in [200, 405], f"Unexpected code on PUT {route}: {resp_put.status_code}"


def test_api_resume_endpoint_defensive(flask_client):
    """
    Verify /api/resume/<job_id> defends against short/invalid job IDs without 500 errors.
    """
    # Short legacy/malformed ID (<36 chars) returns 404
    resp_short = flask_client.get("/api/resume/abc-123")
    assert resp_short.status_code == 404
    assert "Legacy ID format" in resp_short.get_json().get("error", "")

    # Nonexistent UUID (36 chars) returns 404
    with patch("src.db.get_job_pdf_path", return_value=None):
        resp_uuid = flask_client.get("/api/resume/12345678-1234-5678-1234-567812345678")
        assert resp_uuid.status_code == 404


def test_api_runs_and_applications_delete_resilience(flask_client):
    """
    Verify DELETE /api/runs/<run_id> and DELETE /api/applications/<app_id>
    handle missing/malformed IDs without unhandled 500 errors.
    """
    with patch("src.db.delete_pipeline_run", return_value=[]):
        resp_run = flask_client.delete("/api/runs/nonexistent-run-id")
        assert resp_run.status_code == 200
        assert "Run deleted" in resp_run.get_json().get("message", "")

    with patch("src.db.delete_application", return_value=None):
        resp_app = flask_client.delete("/api/applications/nonexistent-app-id")
        assert resp_app.status_code == 200
        assert "Application deleted" in resp_app.get_json().get("message", "")


# =====================================================================
# 3. Frontend Assets Integrity Verification
# =====================================================================

def test_frontend_index_html_assets_referenced_and_served(flask_client):
    """
    Extract all script, stylesheet, and icon asset URLs from frontend/dist/index.html
    and verify that Flask serves each one with HTTP 200 OK and valid non-empty body.
    """
    workspace_root = Path(__file__).resolve().parent.parent
    index_html_path = workspace_root / "frontend" / "dist" / "index.html"
    assert index_html_path.exists(), "frontend/dist/index.html must exist"

    html_content = index_html_path.read_text(encoding="utf-8")
    assert len(html_content) > 0, "index.html must not be empty"

    # Extract script src
    script_matches = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html_content)
    assert len(script_matches) > 0, "index.html must contain at least one <script src=...>"

    # Extract link href (css, icons, manifest)
    link_matches = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', html_content)
    assert len(link_matches) > 0, "index.html must contain <link> elements"

    all_assets = set(script_matches + link_matches)

    for asset_path in all_assets:
        resp = flask_client.get(asset_path)
        assert resp.status_code == 200, (
            f"Asset {asset_path} referenced in index.html returned HTTP {resp.status_code}"
        )
        data = resp.get_data()
        assert len(data) > 0, f"Asset {asset_path} returned empty response body"

        # Check content types
        content_type = resp.headers.get("Content-Type", "")
        if asset_path.endswith(".js"):
            assert "javascript" in content_type or "text/" in content_type
        elif asset_path.endswith(".css"):
            assert "css" in content_type
        elif asset_path.endswith(".svg"):
            assert "svg" in content_type or "image/" in content_type
        elif asset_path.endswith(".json"):
            assert "json" in content_type


# =====================================================================
# 4. Start Payload Robustness & Edge Cases
# =====================================================================

def test_start_pipeline_valid_and_empty_payloads(flask_client):
    """
    Verify /api/start and /api/test-start handle empty and standard payloads cleanly.
    """
    with patch("threading.Thread") as mock_thread_cls:
        mock_instance = MagicMock()
        mock_thread_cls.return_value = mock_instance

        # 1. Empty body
        resp = flask_client.post("/api/start", data="", content_type="application/json")
        assert resp.status_code == 200

        # Reset
        pipeline_state["running"] = False

        # 2. Empty JSON object
        resp2 = flask_client.post("/api/start", json={})
        assert resp2.status_code == 200

        # Reset
        pipeline_state["running"] = False

        # 3. Custom platforms and job types
        payload = {
            "platforms": ["linkedin"],
            "job_types": ["fulltime"],
            "dry_run": True,
            "scoring_model": "deepseek-chat",
            "scoring_thinking": False,
            "tailoring_model": "deepseek-reasoner",
            "tailoring_thinking": True
        }
        resp3 = flask_client.post("/api/start", json=payload)
        assert resp3.status_code == 200


def test_start_pipeline_non_dict_json_unhandled_attribute_error(flask_client):
    """
    [REMEDIATED]
    Verifies that posting non-dict JSON (e.g. [1, 2, 3]) returns HTTP 400 Bad Request
    with error JSON instead of raising an unhandled AttributeError or 500 error.
    """
    resp = flask_client.post("/api/start", data="[1, 2, 3]", content_type="application/json")
    assert resp.status_code == 400
    assert "Invalid JSON payload" in resp.get_json().get("error", "")


def test_test_start_pipeline_non_dict_json_unhandled_attribute_error(flask_client):
    """
    [REMEDIATED]
    Verifies that /api/test-start returns HTTP 400 Bad Request on non-dict JSON
    without raising an unhandled AttributeError or 500 error.
    """
    resp = flask_client.post("/api/test-start", data="[1, 2, 3]", content_type="application/json")
    assert resp.status_code == 400
    assert "Invalid JSON payload" in resp.get_json().get("error", "")


def test_concurrency_toctou_race_window_without_mutex():
    """
    [REMEDIATED]
    Verifies that pipeline_lock eliminates the TOCTOU race condition in /api/start.
    Even with simulated logging/IO delay during settings application, exactly 1 run
    starts (HTTP 200) and all 4 concurrent requests are rejected with HTTP 400.
    """
    def slow_apply(data):
        time.sleep(0.05)  # Simulate small logging/IO delay

    with patch("app._apply_ai_settings", side_effect=slow_apply):
        with patch("app.run_pipeline", side_effect=lambda *a, **k: time.sleep(0.5)):
            pipeline_state["running"] = False
            stop_event.clear()

            def send_start(i):
                with app.test_client() as c:
                    return c.post("/api/start", json={"platforms": ["linkedin"]})

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                futures = [ex.submit(send_start, i) for i in range(5)]
                responses = [f.result() for f in futures]

            codes = [r.status_code for r in responses]
            # With pipeline_lock mutex, exactly 1 request succeeds (200) and all others fail (400)
            assert codes.count(200) == 1, f"Expected exactly 1 HTTP 200, got: {codes}"
            assert codes.count(400) == 4, f"Expected exactly 4 HTTP 400, got: {codes}"
