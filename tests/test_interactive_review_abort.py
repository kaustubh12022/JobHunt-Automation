"""
Integration and unit tests for:
1. Interactive review phase (pauses after AI scoring, displays 1-sentence summary and missing skills).
2. Missing skills injection into tailored resume.
3. Pipeline abort handling across review, scraping, and tailoring phases.
4. Input validation and edge cases for review endpoints.
5. Strict 1-page PDF layout verification with updated template spacing.
"""

import copy
import json
import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from src.models import Job
from src.resume_tailor import validate_and_sanitize_tailored
from app import (
    app,
    pipeline_state,
    pipeline_lock,
    stop_event,
    resume_generation_event,
    pending_pipeline_data,
    get_single_sentence_summary,
    run_pipeline,
)


@pytest.fixture(autouse=True)
def clean_pipeline_state():
    """Ensure clean thread events and state before and after each test."""
    with pipeline_lock:
        stop_event.clear()
        resume_generation_event.clear()
        pending_pipeline_data.clear()
        pipeline_state["running"] = False
        pipeline_state["phase"] = "idle"
        pipeline_state["mode"] = "idle"
        pipeline_state["status_text"] = ""
        pipeline_state["shortlisted_jobs"] = []
        pipeline_state["scan"]["live_jobs"] = []
        pipeline_state["scan"]["total_found"] = 0
        pipeline_state["score"]["live_scores"] = []
        pipeline_state["score"]["scored"] = 0
        pipeline_state["score"]["shortlisted"] = 0
        pipeline_state["tailor"]["results"] = []
    yield
    with pipeline_lock:
        stop_event.set()
        resume_generation_event.set()
        pipeline_state["running"] = False
        pipeline_state["phase"] = "idle"
        pipeline_state["mode"] = "idle"
        pipeline_state["status_text"] = ""
        pipeline_state["shortlisted_jobs"] = []


# =====================================================================
# 1. Interactive Review Phase Tests
# =====================================================================

def test_pipeline_pauses_in_review_phase_after_scoring():
    """
    Verifies that when AI scoring completes, the pipeline does NOT automatically
    start tailoring resumes. It must pause, set phase="review", and expose
    the shortlisted jobs with 1-sentence summary and missing skills.
    """
    job1 = Job(
        title="Full Stack Developer",
        company="Acme Corp",
        location="Remote",
        description="We need a Full Stack Developer experienced with React and Node.js. Experience with Docker and AWS is preferred.",
        url="https://example.com/job1",
        id="job-101",
        score=85,
        reasons=["Strong fullstack alignment with React and Python background."],
        missing_skills=["Docker", "AWS", "GraphQL"],
        extracted_requirements="React, Node.js, Docker, AWS",
        is_testing_role=False,
    )
    job2 = Job(
        title="Software Engineer - Backend",
        company="Beta Inc",
        location="New York, NY",
        description="Beta Inc is looking for a backend engineer. Kafka and Redis knowledge required.",
        url="https://example.com/job2",
        id="job-102",
        score=78,
        reasons=["Good backend fundamentals matching Python and PostgreSQL."],
        missing_skills=["Kafka", "Redis"],
        extracted_requirements="Kafka, Redis, Python",
        is_testing_role=False,
    )

    tailoring_invoked = threading.Event()

    def mock_tailor_batch(jobs, **kwargs):
        tailoring_invoked.set()
        return [{"profile_summary": "Tailored"} for _ in jobs]

    with patch("app.run_scraper", return_value=([job1, job2], {"reached_scoring": 2})), \
         patch("app.score_jobs", return_value=[job1, job2]), \
         patch("src.resume_tailor.tailor_resumes_batch", side_effect=mock_tailor_batch), \
         patch("app.save_pipeline_results", return_value=None):

        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(["linkedin"], ["fulltime"], True, False),
            daemon=True
        )
        pipeline_thread.start()

        # Wait up to 3 seconds for the pipeline to hit the review pause
        start_time = time.time()
        while time.time() - start_time < 3.0:
            with pipeline_lock:
                if pipeline_state.get("phase") == "review":
                    break
            time.sleep(0.05)

        with pipeline_lock:
            assert pipeline_state["phase"] == "review", f"Expected phase 'review', got {pipeline_state['phase']}"
            assert pipeline_state["running"] is True
            shortlisted = pipeline_state.get("shortlisted_jobs", [])
            assert len(shortlisted) == 2

            j1_data = next(j for j in shortlisted if j["id"] == "job-101")
            assert j1_data["title"] == "Full Stack Developer"
            assert j1_data["company"] == "Acme Corp"
            assert j1_data["score"] == 85
            assert "Docker" in j1_data["missing_skills"]
            assert "AWS" in j1_data["missing_skills"]
            assert len(j1_data["summary"]) > 10

        # Tailoring MUST NOT have run yet
        assert not tailoring_invoked.is_set(), "Tailoring should NOT have started automatically!"

        # Now simulate user selecting ONLY job1 with Docker skill confirmed
        client = app.test_client()
        resp = client.post("/api/generate-resumes", json={
            "selected_jobs": [
                {"id": "job-101", "selected_skills": ["Docker", "Kubernetes"]}
            ]
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 1

        # Wait for thread to finish
        pipeline_thread.join(timeout=3.0)
        assert not pipeline_thread.is_alive(), "Pipeline thread should terminate after tailoring"
        assert tailoring_invoked.is_set(), "Tailoring should have been invoked after user triggered it"

        with pipeline_lock:
            assert pipeline_state["phase"] == "done"
            assert pipeline_state["running"] is False


def test_user_selected_skills_injection_in_resume():
    """
    Verifies that when a user selects missing skills (or adds custom ones),
    the resume tailor sanitization logic deterministically embeds them
    into tailored['skills'] up to the limit.
    """
    master_resume = {
        "personal_information": {"name": "Kaustubh", "surname": "Kale"},
        "profile_summary": "Full stack engineer with experience in React and Node.js.",
        "skills": ["JavaScript", "Python", "React", "PostgreSQL", "Git", "REST APIs"],
        "experience_details": [
            {
                "position": "Software Developer Intern",
                "company": "Koyal Infotech",
                "employment_period": "Jul 2024 - Dec 2024",
                "location": "Pune, India",
                "key_achievements": ["Built full-stack React and FastAPI dashboards."]
            }
        ],
        "projects": [
            {"name": "SmartApply", "skills": "React, Python", "key_achievements": ["Built resume tailoring engine."]},
            {"name": "CampFlow", "skills": "React, Node.js", "key_achievements": ["Built booking system."]},
            {"name": "Neon Pulse", "skills": "Three.js, WebGL", "key_achievements": ["Built audio visualizer."]}
        ],
        "education": [{"institution": "MIT", "degree": "B.Tech", "period": "2021 - 2025"}]
    }

    job = Job(
        title="Cloud Infrastructure Engineer",
        company="CloudNet",
        location="Remote",
        description="Looking for an engineer with Terraform, Kubernetes, and Docker skills.",
        url="https://example.com/job",
        id="job-cloud",
        score=80,
        missing_skills=["Terraform", "Kubernetes", "Docker"],
        is_testing_role=False,
    )

    # Candidate knows Docker and Kubernetes and also adds custom skill "CI/CD"
    user_skills = ["Docker", "Kubernetes", "CI/CD"]

    tailored_input = copy.deepcopy(master_resume)
    sanitized = validate_and_sanitize_tailored(
        tailored_data=tailored_input,
        master_resume=master_resume,
        role_lens="fullstack",
        job=job,
        selected_skills=user_skills
    )

    skills_result = sanitized.get("skills", [])
    assert "Docker" in skills_result, f"Docker should be injected into skills: {skills_result}"
    assert "Kubernetes" in skills_result, f"Kubernetes should be injected into skills: {skills_result}"
    assert "CI/CD" in skills_result, f"CI/CD should be injected into skills: {skills_result}"
    assert len(skills_result) <= 14, "Skills list must not exceed 14 items"


def test_user_selected_skills_injection_at_full_capacity():
    """
    Verifies that when a master resume already has 14 skills, injecting multiple
    user-confirmed missing skills preserves ALL selected skills rather than
    repeatedly overwriting the last item.
    """
    master_resume = {
        "personal_information": {"name": "Kaustubh", "surname": "Kale"},
        "profile_summary": "Software Engineer",
        "skills": [
            "Java", "Python", "SQL", "C#", "JavaScript", "TypeScript",
            "HTML", "CSS", "Spring Core", "JDBC", "REST APIs", "Git",
            "MySQL", "Maven"
        ],
        "experience_details": [
            {
                "position": "Intern",
                "company": "Koyal Infotech",
                "employment_period": "2024",
                "location": "Pune",
                "key_responsibilities": ["Fullstack work"]
            }
        ],
        "projects": [
            {"name": "SmartApply", "skills": "Python", "key_achievements": ["Tailoring"]},
            {"name": "CampFlow", "skills": "React", "key_achievements": ["Booking"]},
            {"name": "Neon Pulse", "skills": "JS", "key_achievements": ["Logic"]}
        ],
        "education": [{"institution": "MIT", "degree": "B.Tech", "period": "2021-2025"}]
    }

    job = Job(
        title="Senior Cloud Platform Engineer",
        company="GlobalTech",
        location="Remote",
        description="Kubernetes, Docker, and Redis requirements.",
        url="https://example.com/cloud",
        id="job-cap",
        score=82,
        missing_skills=["Kubernetes", "Docker", "Redis"],
    )

    user_skills = ["Docker", "Kubernetes", "Redis"]
    sanitized = validate_and_sanitize_tailored(
        tailored_data=copy.deepcopy(master_resume),
        master_resume=master_resume,
        role_lens="fullstack",
        job=job,
        selected_skills=user_skills
    )

    result = sanitized.get("skills", [])
    assert "Docker" in result, f"Docker must be present: {result}"
    assert "Kubernetes" in result, f"Kubernetes must be present: {result}"
    assert "Redis" in result, f"Redis must be present: {result}"
    assert len(result) <= 14, f"Must stay within 14 skills budget: {len(result)}"


# =====================================================================
# 2. Pipeline Abort Functionality Across Phases
# =====================================================================

def test_abort_pipeline_during_review_phase():
    """
    Verifies that calling /api/stop while the pipeline is in the 'review' phase
    wakes up the blocked thread, cleanly halts, and resets phase to 'idle'.
    """
    job = Job(
        title="Developer",
        company="TechCorp",
        location="Remote",
        description="Dev role",
        url="https://example.com",
        id="job-dev-1",
        score=90,
        missing_skills=["Go"],
    )

    with patch("app.run_scraper", return_value=([job], {"reached_scoring": 1})), \
         patch("app.score_jobs", return_value=[job]):

        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(["linkedin"], ["fulltime"], True, False),
            daemon=True
        )
        pipeline_thread.start()

        # Wait until review phase
        start = time.time()
        while time.time() - start < 3.0:
            with pipeline_lock:
                if pipeline_state.get("phase") == "review":
                    break
            time.sleep(0.05)

        with pipeline_lock:
            assert pipeline_state["phase"] == "review"
            assert len(pipeline_state["shortlisted_jobs"]) == 1

        # Now call abort endpoint
        client = app.test_client()
        stop_resp = client.post("/api/stop")
        assert stop_resp.status_code == 200
        assert stop_resp.get_json()["message"] == "Pipeline aborted."

        pipeline_thread.join(timeout=2.0)
        assert not pipeline_thread.is_alive(), "Pipeline thread must terminate upon abort"

        with pipeline_lock:
            assert pipeline_state["phase"] == "idle"
            assert pipeline_state["running"] is False
            assert pipeline_state["shortlisted_jobs"] == []
            assert "Aborted" in pipeline_state["status_text"]


def test_abort_pipeline_during_scraping_phase():
    """
    Verifies that aborting while the scraper is running immediately halts the pipeline.
    """
    def mock_scraper_with_stop(*args, **kwargs):
        ev = kwargs.get("stop_event")
        while ev and not ev.is_set():
            time.sleep(0.05)
        return [], {"reached_scoring": 0}

    with patch("app.run_scraper", side_effect=mock_scraper_with_stop):
        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(["linkedin"], ["fulltime"], True, False),
            daemon=True
        )
        pipeline_thread.start()

        # Wait for scanning phase
        start = time.time()
        while time.time() - start < 2.0:
            with pipeline_lock:
                if pipeline_state.get("phase") == "scanning":
                    break
            time.sleep(0.05)

        client = app.test_client()
        stop_resp = client.post("/api/stop")
        assert stop_resp.status_code == 200

        pipeline_thread.join(timeout=2.0)
        assert not pipeline_thread.is_alive()

        with pipeline_lock:
            assert pipeline_state["phase"] == "idle"
            assert pipeline_state["running"] is False


def test_abort_pipeline_during_scoring_phase():
    """
    Verifies that aborting while AI scoring is running immediately halts the pipeline
    and cleanly resets state to 'idle' without overwriting phase to 'done'.
    """
    job = Job(
        title="Software Engineer",
        company="TechCorp",
        location="Remote",
        description="Full stack python",
        url="https://example.com/job",
        id="job-score-abort",
    )

    def mock_score_with_stop(jobs, **kwargs):
        ev = kwargs.get("stop_event")
        while ev and not ev.is_set():
            time.sleep(0.05)
        return []

    with patch("app.run_scraper", return_value=([job], {"reached_scoring": 1})), \
         patch("app.score_jobs", side_effect=mock_score_with_stop):

        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(["linkedin"], ["fulltime"], True, False),
            daemon=True
        )
        pipeline_thread.start()

        # Wait for scoring phase
        start = time.time()
        while time.time() - start < 2.0:
            with pipeline_lock:
                if pipeline_state.get("phase") == "scoring":
                    break
            time.sleep(0.05)

        client = app.test_client()
        stop_resp = client.post("/api/stop")
        assert stop_resp.status_code == 200

        pipeline_thread.join(timeout=2.0)
        assert not pipeline_thread.is_alive()

        with pipeline_lock:
            assert pipeline_state["phase"] == "idle"
            assert pipeline_state["running"] is False
            assert "Aborted" in pipeline_state["status_text"]


def test_abort_pipeline_during_tailoring_phase():
    """
    Verifies that aborting during tailoring phase immediately halts the pipeline.
    """
    job = Job(
        title="Engineer",
        company="Startup",
        location="Remote",
        description="Full stack dev",
        url="https://example.com",
        id="job-tailor-abort",
        score=92,
    )

    def mock_tailor_batch_with_stop(jobs, **kwargs):
        ev = kwargs.get("stop_event")
        while ev and not ev.is_set():
            time.sleep(0.05)
        return []

    with patch("app.run_scraper", return_value=([job], {"reached_scoring": 1})), \
         patch("app.score_jobs", return_value=[job]), \
         patch("src.resume_tailor.tailor_resumes_batch", side_effect=mock_tailor_batch_with_stop):

        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(["linkedin"], ["fulltime"], True, False),
            daemon=True
        )
        pipeline_thread.start()

        # Wait for review phase
        start = time.time()
        while time.time() - start < 3.0:
            with pipeline_lock:
                if pipeline_state.get("phase") == "review":
                    break
            time.sleep(0.05)

        client = app.test_client()
        # Resume to tailoring
        client.post("/api/generate-resumes", json={"selected_jobs": [{"id": "job-tailor-abort"}]})

        # Wait for tailoring phase
        start = time.time()
        while time.time() - start < 2.0:
            with pipeline_lock:
                if pipeline_state.get("phase") == "tailoring":
                    break
            time.sleep(0.05)

        # Abort during tailoring
        stop_resp = client.post("/api/stop")
        assert stop_resp.status_code == 200

        pipeline_thread.join(timeout=2.0)
        assert not pipeline_thread.is_alive()

        with pipeline_lock:
            assert pipeline_state["phase"] == "idle"
            assert pipeline_state["running"] is False


# =====================================================================
# 3. Edge Cases and Input Validation
# =====================================================================

def test_api_generate_resumes_validation():
    """
    Tests input validation and error states for /api/generate-resumes.
    """
    client = app.test_client()

    # 1. Calling when phase != review
    with pipeline_lock:
        pipeline_state["phase"] = "idle"
    resp = client.post("/api/generate-resumes", json={"selected_jobs": []})
    assert resp.status_code == 400
    assert "Pipeline is not in review phase" in resp.get_json()["error"]

    # 2. Calling with invalid JSON format (raw string or list instead of dict)
    with pipeline_lock:
        pipeline_state["phase"] = "review"
    resp = client.post("/api/generate-resumes", data="not json", content_type="application/json")
    assert resp.status_code == 400

    resp = client.post("/api/generate-resumes", json=["not", "a", "dict"])
    assert resp.status_code == 400

    # 3. Calling with selected_jobs not being a list
    resp = client.post("/api/generate-resumes", json={"selected_jobs": "not a list"})
    assert resp.status_code == 400
    assert "selected_jobs must be a list" in resp.get_json()["error"]


def test_user_selects_zero_jobs_completes_gracefully():
    """
    If user submits selected_jobs: [] (selects 0 jobs), pipeline should finish
    cleanly without tailoring unselected jobs.
    """
    job = Job(
        title="Dev",
        company="Corp",
        location="Remote",
        description="Dev",
        url="https://example.com",
        id="job-zero",
        score=85,
    )

    tailor_called = False
    def mock_tailor(jobs, **kwargs):
        nonlocal tailor_called
        tailor_called = True
        return []

    with patch("app.run_scraper", return_value=([job], {"reached_scoring": 1})), \
         patch("app.score_jobs", return_value=[job]), \
         patch("src.resume_tailor.tailor_resumes_batch", side_effect=mock_tailor):

        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(["linkedin"], ["fulltime"], True, False),
            daemon=True
        )
        pipeline_thread.start()

        # Wait for review phase
        start = time.time()
        while time.time() - start < 3.0:
            with pipeline_lock:
                if pipeline_state.get("phase") == "review":
                    break
            time.sleep(0.05)

        client = app.test_client()
        # Submit empty list
        resp = client.post("/api/generate-resumes", json={"selected_jobs": []})
        assert resp.status_code == 200

        pipeline_thread.join(timeout=2.0)
        assert not pipeline_thread.is_alive()
        assert not tailor_called, "Tailor should NOT be called if 0 jobs were selected"

        with pipeline_lock:
            assert pipeline_state["phase"] == "done"
            assert pipeline_state["running"] is False
            assert "No jobs selected" in pipeline_state["status_text"]


# =====================================================================
# 4. Single Sentence Summary Derivation
# =====================================================================

def test_single_sentence_summary_derivation():
    """
    Verifies that get_single_sentence_summary produces a concise, readable
    single sentence across diverse job representations.
    """
    # Case 0: Job with direct explicit job_summary
    j0 = Job(
        title="Java Developer",
        company="Amazon",
        location="Seattle, WA",
        description="Full text",
        url="https://example.com/j0",
        job_summary="Java Developer role focused on building high-throughput microservices.",
    )
    s0 = get_single_sentence_summary(j0)
    assert s0 == "Java Developer role focused on building high-throughput microservices."

    # Case 1: Job with reasons list
    j1 = Job(
        title="Frontend Engineer",
        company="Stripe",
        location="San Francisco, CA",
        description="Full job description",
        url="https://example.com/j1",
        reasons=["High frontend alignment with strong TypeScript and React experience."],
    )
    s1 = get_single_sentence_summary(j1)
    assert s1 == "High frontend alignment with strong TypeScript and React experience."

    # Case 2: Job with extracted requirements
    j2 = Job(
        title="DevOps Engineer",
        company="GitLab",
        location="Remote",
        description="Long text without reasons.",
        url="https://example.com/j2",
        extracted_requirements="Kubernetes, Terraform, CI/CD pipelines",
    )
    s2 = get_single_sentence_summary(j2)
    assert "DevOps Engineer role at GitLab requiring Kubernetes, Terraform, CI/CD pipelines." in s2

    # Case 3: Job with only description
    j3 = Job(
        title="Data Analyst",
        company="Meta",
        location="Menlo Park, CA",
        description="We are seeking an experienced Data Analyst to join our team. You will analyze large datasets using SQL and Python. Qualifications include 3+ years experience.",
        url="https://example.com/j3",
    )
    s3 = get_single_sentence_summary(j3)
    assert "We are seeking an experienced Data Analyst to join our team" in s3

    # Case 4: Minimal fallback
    j4 = Job(
        title="QA Specialist",
        company="Shopify",
        location="Toronto, Canada",
        description="",
        url="https://example.com/j4",
    )
    s4 = get_single_sentence_summary(j4)
    assert s4 == "QA Specialist position at Shopify."


# =====================================================================
# 5. Strict 1-Page Layout Verification (Playwright)
# =====================================================================

def test_resume_template_strictly_one_page():
    """
    Renders realistic full-content resume into PDF using Playwright and PyPDF2
    to verify that spacing reductions guarantee a strict 1-page document.
    """
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright
    import pypdf
    import io

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("resume_template.html")

    # Maximal realistic candidate resume data
    full_resume = {
        "personal_information": {
            "name": "Kaustubh",
            "surname": "Kale",
            "email": "kaustubh@example.com",
            "phone": "9876543210",
            "phone_prefix": "+91",
            "city": "Pune",
            "country": "India",
            "linkedin": "https://linkedin.com/in/kaustubh-kale",
            "github": "https://github.com/kaustubh12022",
        },
        "profile_summary": "Results-driven Software Engineer with extensive full-stack experience building high-scale distributed applications, RESTful microservices, and AI-powered workflow automation. Proficient in React, Node.js, Python, and cloud architectures, consistently optimizing system reliability, latency, and ATS-compliant delivery pipelines.",
        "skills": [
            "React", "TypeScript", "Node.js", "Python", "FastAPI",
            "PostgreSQL", "MongoDB", "Docker", "Kubernetes", "Redis",
            "GraphQL", "CI/CD", "AWS", "Git"
        ],
        "experience_details": [
            {
                "position": "Software Developer Intern",
                "company": "Koyal Infotech",
                "employment_period": "Jul 2024 - Dec 2024",
                "location": "Pune, India",
                "key_achievements": [
                    "Engineered modular micro-frontends and full-stack React dashboards reducing dashboard load latency by 35%.",
                    "Architected robust FastAPI microservices processing 10,000+ daily requests with automated unit testing."
                ]
            }
        ],
        "projects": [
            {
                "name": "SmartApply — AI Tailoring Engine",
                "skills": "React, Python, FastAPI, Playwright",
                "key_achievements": [
                    "Engineered end-to-end automated pipeline tailoring resumes against job descriptions with 94% ATS match rate.",
                    "Designed headless Playwright rendering module generating deterministic, pixel-perfect single-page PDFs.",
                    "Implemented real-time telemetry dashboard monitoring token usage, API latency, and LLM reasoning steps."
                ]
            },
            {
                "name": "CampFlow — Camping Reservation Platform",
                "skills": "React, Node.js, Express, MongoDB",
                "key_achievements": [
                    "Architected scalable campsite discovery and booking engine with interactive Mapbox spatial search.",
                    "Integrated Stripe webhook checkout pipeline with transactional concurrency control."
                ]
            },
            {
                "name": "Neon Pulse — Interactive WebGL Visualizer",
                "skills": "Three.js, WebGL, Web Audio API",
                "key_achievements": [
                    "Constructed real-time 3D frequency spectrum analyzer rendering 60 FPS animations across modern browsers.",
                    "Optimized GLSL shader math and particle buffer allocations to eliminate frame drops."
                ]
            }
        ],
        "education": [
            {
                "institution": "MIT World Peace University",
                "degree": "B.Tech in Computer Science and Engineering",
                "period": "2021 - 2025"
            }
        ],
        "certifications": [
            "AWS Certified Cloud Practitioner",
            "PostgreSQL Professional Developer"
        ]
    }

    html_content = template.render(resume=full_resume)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0in", "bottom": "0in", "left": "0in", "right": "0in"}
        )
        browser.close()

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    assert page_count == 1, f"Resume MUST strictly fit onto 1 page! Got {page_count} pages."
