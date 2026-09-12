"""
Milestone 2 Challenger 2 Adversarial Stress Test Suite:
1. Deduplication when 10+ different jobs have company None, "", or "Unknown" and unique URLs (all preserved).
2. Deduplication when identical jobs have tracking query parameters (pruning verified).
3. clean_html preserves paragraphs, bullet points (- ), and formatting without collapsing to a single line.
4. Valid apply URLs remain functional (functional query params like 'jk' preserved, paths intact, parseable).
"""
import urllib.parse
import pytest
import pandas as pd
from src.models import Job
from src.scraper import (
    apply_pandas_filter,
    clean_html,
    normalize_url,
    TRACKING_PARAMS,
)


# ==============================================================================
# SECTION 1: Unknown / Missing Company Deduplication (10+ jobs)
# ==============================================================================

def test_deduplication_10_jobs_with_company_none_all_preserved():
    """
    CRITICAL EMPIRICAL TEST:
    10 different jobs with identical title ('Software Engineer'), company=None,
    and 10 unique URLs.
    Per Milestone 2 requirements, ALL 10 must be preserved.
    """
    jobs = [
        Job(
            id=f"job-none-{i}",
            title="Software Engineer",
            company=None,
            location="Pune",
            description="Entry-level Python developer 0-2 years.",
            url=f"https://company-none.org/job/{i}",
        )
        for i in range(10)
    ]

    filtered = apply_pandas_filter(jobs, ["Pune"], hours_old=72)
    assert len(filtered) == 10, (
        f"Expected all 10 jobs with company=None to be preserved, but got {len(filtered)}. "
        f"Dropped {10 - len(filtered)} jobs!"
    )


def test_deduplication_10_jobs_with_company_empty_string_all_preserved():
    """10 different jobs with identical title, company='', and 10 unique URLs: all 10 preserved."""
    jobs = [
        Job(
            id=f"job-empty-{i}",
            title="Software Engineer",
            company="",
            location="Pune",
            description="Entry-level Python developer 0-2 years.",
            url=f"https://company-empty.org/job/{i}",
        )
        for i in range(10)
    ]

    filtered = apply_pandas_filter(jobs, ["Pune"], hours_old=72)
    assert len(filtered) == 10, f"Expected all 10 jobs with company='' to be preserved, got {len(filtered)}"


def test_deduplication_10_jobs_with_company_unknown_all_preserved():
    """10 different jobs with identical title, company='Unknown', and 10 unique URLs: all 10 preserved."""
    jobs = [
        Job(
            id=f"job-unknown-{i}",
            title="Software Engineer",
            company="Unknown",
            location="Pune",
            description="Entry-level Python developer 0-2 years.",
            url=f"https://company-unknown.org/job/{i}",
        )
        for i in range(10)
    ]

    filtered = apply_pandas_filter(jobs, ["Pune"], hours_old=72)
    assert len(filtered) == 10, f"Expected all 10 jobs with company='Unknown' to be preserved, got {len(filtered)}"



def test_deduplication_unknown_companies_with_duplicate_urls():
    """
    Verify that when jobs have unknown company AND the exact same URL,
    URL deduplication correctly prunes the duplicate while preserving unique URLs.
    """
    jobs = [
        Job(
            id="job-u1",
            title="Python Developer",
            company="Unknown",
            location="Pune",
            description="Entry level role 1-2 years.",
            url="https://example.com/job/shared-123",
        ),
        Job(
            id="job-u2",
            title="Python Developer",
            company="Unknown",
            location="Pune",
            description="Entry level role 1-2 years.",
            url="https://example.com/job/shared-123",  # Duplicate URL
        ),
        Job(
            id="job-u3",
            title="Python Developer",
            company="Unknown",
            location="Pune",
            description="Entry level role 1-2 years.",
            url="https://example.com/job/unique-456",  # Unique URL
        ),
    ]

    filtered = apply_pandas_filter(jobs, ["Pune"], hours_old=72)
    assert len(filtered) == 2, f"Expected 2 jobs after pruning duplicate URL, got {len(filtered)}"
    urls = [j.url for j in filtered]
    assert urls.count("https://example.com/job/shared-123") == 1
    assert "https://example.com/job/unique-456" in urls


def test_deduplication_known_companies_are_properly_deduplicated():
    """
    Positive control: verify that jobs with KNOWN companies (e.g. 'Google', 'Microsoft')
    and identical title are properly deduplicated across different URLs.
    """
    jobs = [
        Job(
            id="job-k1",
            title="Software Engineer",
            company="Google",
            location="Bangalore",
            description="Fresher role 0-2 years.",
            url="https://linkedin.com/jobs/view/111",
        ),
        Job(
            id="job-k2",
            title="Software Engineer",
            company="Google",
            location="Bangalore",
            description="Fresher role 0-2 years.",
            url="https://indeed.com/viewjob?jk=222",  # Different URL, same company & title
        ),
    ]

    filtered = apply_pandas_filter(jobs, ["Bangalore"], hours_old=72)
    assert len(filtered) == 1, (
        f"Expected 1 job for known company duplicate ('Google', 'Software Engineer'), got {len(filtered)}"
    )


def test_deduplication_known_and_unknown_interleaved():
    """
    Stress-test: mix of known duplicate jobs and unknown company jobs.
    Known duplicates should be collapsed to 1 each; unknown company jobs with unique URLs
    should all be retained.
    """
    jobs = [
        # Known company A duplicates (2)
        Job(id="k-a1", title="QA Tester", company="Infosys", location="Pune", description="Fresher 0-1 yrs.", url="http://a1.com"),
        Job(id="k-a2", title="QA Tester", company="Infosys", location="Pune", description="Fresher 0-1 yrs.", url="http://a2.com"),
        # Known company B single (1)
        Job(id="k-b1", title="QA Tester", company="Wipro", location="Pune", description="Fresher 0-1 yrs.", url="http://b1.com"),
        # Unknown companies with same title (4 distinct URLs)
        Job(id="u-1", title="QA Tester", company="Unknown", location="Pune", description="Fresher 0-1 yrs.", url="http://u1.com"),
        Job(id="u-2", title="QA Tester", company=None, location="Pune", description="Fresher 0-1 yrs.", url="http://u2.com"),
        Job(id="u-3", title="QA Tester", company="", location="Pune", description="Fresher 0-1 yrs.", url="http://u3.com"),
        Job(id="u-4", title="QA Tester", company="N/A", location="Pune", description="Fresher 0-1 yrs.", url="http://u4.com"),
    ]

    filtered = apply_pandas_filter(jobs, ["Pune"], hours_old=72)
    # Expected: 1 from Infosys + 1 from Wipro + 4 unknown = 6 total
    assert len(filtered) == 6, f"Expected 6 jobs (1 Infosys, 1 Wipro, 4 Unknowns), got {len(filtered)}"


# ==============================================================================
# SECTION 2: Tracking Query Parameters and URL Normalization Deduplication
# ==============================================================================

def test_normalize_url_strips_all_tracking_parameters():
    """Verify normalize_url thoroughly strips all UTM and tracking parameters."""
    tracking_samples = [
        ("https://linkedin.com/jobs/view/123?utm_source=linkedin&utm_medium=job_post", "https://linkedin.com/jobs/view/123"),
        ("https://linkedin.com/jobs/view/123?refId=abc&trackingId=def", "https://linkedin.com/jobs/view/123"),
        ("https://linkedin.com/jobs/view/123?trk=public_jobs&trkcampaign=email", "https://linkedin.com/jobs/view/123"),
        ("https://example.com/job/456?fbclid=IwAR123&gclid=Cj0KCQj&msclkid=xyz", "https://example.com/job/456"),
        ("https://example.com/job/456?midToken=abc&mc_cid=99&mc_eid=88", "https://example.com/job/456"),
        ("https://example.com/job/456?_ga=GA1.2.3&_gl=1*abc", "https://example.com/job/456"),
        ("https://example.com/job/789/?UTM_SOURCE=ad&REFID=999", "https://example.com/job/789"),
    ]

    for raw, expected in tracking_samples:
        normalized = normalize_url(raw)
        assert normalized == expected, f"Failed for {raw}: expected {expected}, got {normalized}"


def test_deduplication_identical_jobs_with_tracking_params_pruned():
    """
    Stress-test: 5 identical job postings pointing to the same underlying URL
    with different tracking query params.
    All duplicates MUST be pruned, leaving exactly 1 job.
    """
    urls_with_tracking = [
        "https://www.linkedin.com/jobs/view/3829104820?utm_source=linkedin&utm_medium=job_post&utm_campaign=hiring",
        "https://www.linkedin.com/jobs/view/3829104820?refId=abc123xyz&trackingId=987fed",
        "https://www.linkedin.com/jobs/view/3829104820/?trk=public_jobs_topcard-title&midToken=999",
        "https://www.linkedin.com/jobs/view/3829104820/?fbclid=IwAR123&gclid=Cj0KCQj",
        "https://www.linkedin.com/jobs/view/3829104820",
    ]

    jobs = [
        Job(
            id=f"track-job-{i}",
            title="Java Developer",
            company="Accenture",
            location="Mumbai, Maharashtra",
            description="Entry level Java developer needed. 0-2 years experience.",
            url=url,
        )
        for i, url in enumerate(urls_with_tracking)
    ]

    filtered = apply_pandas_filter(jobs, ["Mumbai"], hours_old=72)
    # 1. Verify duplicates were pruned
    assert len(filtered) == 1, (
        f"Expected exactly 1 job retained after pruning tracking parameter duplicates, got {len(filtered)}. "
        f"Retained: {[j.url for j in filtered]}"
    )
    # 2. Verify the retained job normalizes to the clean base URL
    assert normalize_url(filtered[0].url) == "https://www.linkedin.com/jobs/view/3829104820"

    # 3. Verify that jobs passed with run_scraper's normalize_url upfront also dedup to 1 clean job
    scraper_jobs = [
        Job(
            id=f"scraper-job-{i}",
            title="Java Developer",
            company="Accenture",
            location="Mumbai, Maharashtra",
            description="Entry level Java developer needed. 0-2 years experience.",
            url=normalize_url(url),
        )
        for i, url in enumerate(urls_with_tracking)
    ]
    filtered_scraper = apply_pandas_filter(scraper_jobs, ["Mumbai"], hours_old=72)
    assert len(filtered_scraper) == 1
    assert filtered_scraper[0].url == "https://www.linkedin.com/jobs/view/3829104820"


def test_normalize_url_trailing_slashes_and_fragments():
    """Verify trailing slashes and fragment identifiers (#) are normalized for deduplication."""
    url1 = "https://careers.company.com/job/101/"
    url2 = "https://careers.company.com/job/101"
    url3 = "https://careers.company.com/job/101#apply-section"

    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)
    norm3 = normalize_url(url3)

    assert norm1 == "https://careers.company.com/job/101"
    assert norm2 == "https://careers.company.com/job/101"
    assert norm3 == "https://careers.company.com/job/101"


def test_normalize_url_host_case_insensitivity():
    """Verify netloc hostname is normalized to lowercase."""
    url_upper = "HTTPS://WWW.LINKEDIN.COM/jobs/view/12345"
    norm = normalize_url(url_upper)
    assert norm == "https://www.linkedin.com/jobs/view/12345"


# ==============================================================================
# SECTION 3: clean_html Preserves Paragraphs and Bullet Points
# ==============================================================================

def test_clean_html_preserves_paragraphs_and_newlines():
    """
    Verify clean_html preserves paragraph boundaries (<p>, <div>, <br>)
    and does NOT collapse descriptions into a single contiguous line.
    """
    html_input = (
        "<h3>About the Role</h3>"
        "<p>We are seeking an enthusiastic Fresher Java Developer to join our team in Pune.</p>"
        "<p>You will work on modern microservices and cloud solutions.</p>"
        "<div>Our culture encourages continuous learning and mentorship.</div>"
    )

    cleaned = clean_html(html_input)

    assert "\n" in cleaned, "clean_html collapsed text into a single line without newlines"
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    assert len(lines) >= 4, f"Expected at least 4 distinct lines, got {len(lines)}: {lines}"
    assert "About the Role" in lines[0]
    assert "Fresher Java Developer" in lines[1]
    assert "microservices" in lines[2]
    assert "continuous learning" in lines[3]


def test_clean_html_preserves_bullet_points_with_hyphen_prefix():
    """
    Verify clean_html transforms <li> tags into markdown bullet points ('- ')
    on distinct lines.
    """
    html_input = (
        "<p>Key Responsibilities:</p>"
        "<ul>"
        "  <li>Develop RESTful APIs using Spring Boot and Java 17.</li>"
        "  <li>Collaborate with QA teams on test automation.</li>"
        "  <li>Write clean, maintainable, and well-documented code.</li>"
        "</ul>"
    )

    cleaned = clean_html(html_input)

    assert "- Develop RESTful APIs using Spring Boot and Java 17." in cleaned
    assert "- Collaborate with QA teams on test automation." in cleaned
    assert "- Write clean, maintainable, and well-documented code." in cleaned

    bullet_lines = [l.strip() for l in cleaned.splitlines() if l.strip().startswith("- ")]
    assert len(bullet_lines) == 3, f"Expected 3 bullet lines, got {len(bullet_lines)}: {bullet_lines}"


def test_clean_html_complex_nested_html_and_entities():
    """
    Stress-test clean_html with:
    - Inline tags (<strong>, <em>, <span>, <a>)
    - HTML entities (&amp;, &lt;, &gt;, &quot;, &#39;, &nbsp;)
    - Multiple consecutive <br><br><br>
    - Table elements (<tr>, <td>)
    """
    html_input = (
        "<div><strong>Company:</strong> Tech Corp &amp; Partners</div>"
        "<br><br><br>"
        "<p>Requirements &lt;0-2 Yrs&gt;:</p>"
        "<ul>"
        "  <li>Proficiency in <em>Java</em> &amp; <span>Spring Boot</span></li>"
        "  <li>Basic knowledge of &quot;SQL&quot; &amp; Git</li>"
        "  <li>Must possess a Bachelor&#39;s degree</li>"
        "</ul>"
        "<div>Salary:&nbsp;&nbsp;6-8&nbsp;LPA</div>"
    )

    cleaned = clean_html(html_input)

    # Entities properly unescaped
    assert "Tech Corp & Partners" in cleaned
    assert "&amp;" not in cleaned
    assert "Requirements <0-2 Yrs>:" in cleaned
    assert "&lt;" not in cleaned
    assert "Bachelor's degree" in cleaned
    assert "&#39;" not in cleaned
    assert '"SQL"' in cleaned
    assert "&quot;" not in cleaned

    # Bullets formatted
    assert "- Proficiency in Java & Spring Boot" in cleaned
    assert "- Basic knowledge of \"SQL\" & Git" in cleaned

    # Non-breaking space normalized
    assert "Salary: 6-8 LPA" in cleaned or "6-8 LPA" in cleaned

    # No excessive blank lines (max 2 newlines)
    assert "\n\n\n" not in cleaned


def test_clean_html_edge_cases_and_resilience():
    """Verify clean_html handles empty strings, None, and plain text without crashing."""
    assert clean_html("") == ""
    assert clean_html(None) == ""
    assert clean_html("   ") == ""

    plain_text = "Line 1\n\nLine 2\n- Bullet 1"
    assert clean_html(plain_text) == plain_text


# ==============================================================================
# SECTION 4: Valid Apply URLs Remain Functional
# ==============================================================================

def test_valid_apply_urls_functional_indeed():
    """
    CRITICAL: Verify Indeed apply URLs retain the 'jk' parameter.
    Stripping 'jk' would destroy the job link (Indeed job view requires jk).
    """
    indeed_raw = "https://www.indeed.com/viewjob?jk=c23d049f50e93bfa&from=serp&vjs=3&utm_source=indeed"
    normalized = normalize_url(indeed_raw)

    parsed = urllib.parse.urlparse(normalized)
    query_params = dict(urllib.parse.parse_qsl(parsed.query))

    assert "jk" in query_params, f"'jk' parameter was improperly stripped from Indeed URL: {normalized}"
    assert query_params["jk"] == "c23d049f50e93bfa"
    assert "utm_source" not in query_params, f"utm_source was not stripped: {normalized}"
    assert parsed.netloc == "www.indeed.com"
    assert parsed.path == "/viewjob"


def test_valid_apply_urls_functional_greenhouse_lever_workday():
    """
    Verify applicant tracking system (ATS) URLs maintain full path routing
    to job postings without corruption.
    """
    test_urls = [
        # Greenhouse
        "https://boards.greenhouse.io/databricks/jobs/5234193003?gh_src=linkedin",
        # Lever
        "https://jobs.lever.co/palantir/8f74a0dc-84c1-4bcf-a19b-f1bbd067c29e",
        # Workday
        "https://citi.wd5.myworkdayjobs.com/en-US/2/job/Pune-India/Software-Development-Engineer_24759021-1",
        # LinkedIn
        "https://www.linkedin.com/jobs/view/3829104820",
    ]

    for raw in test_urls:
        norm = normalize_url(raw)
        parsed = urllib.parse.urlparse(norm)

        assert parsed.scheme in ("http", "https"), f"Scheme lost for {raw}: {norm}"
        assert parsed.netloc, f"Netloc lost for {raw}: {norm}"
        assert parsed.path, f"Path lost for {raw}: {norm}"

        # Ensure ID or token is preserved in path
        if "5234193003" in raw:
            assert "5234193003" in parsed.path
        if "8f74a0dc" in raw:
            assert "8f74a0dc-84c1-4bcf-a19b-f1bbd067c29e" in parsed.path
        if "24759021-1" in raw:
            assert "24759021-1" in parsed.path
        if "3829104820" in raw:
            assert "3829104820" in parsed.path


def test_valid_apply_urls_non_tracking_query_params_preserved():
    """
    Verify functional application query parameters (e.g. job_id, req_id, lang)
    are retained, while tracking parameters are stripped.
    """
    url = "https://careers.targetcompany.com/apply?req_id=REQ-9921&job_id=441&lang=en&utm_campaign=autumn&refId=123"
    norm = normalize_url(url)

    parsed = urllib.parse.urlparse(norm)
    params = dict(urllib.parse.parse_qsl(parsed.query))

    assert params.get("req_id") == "REQ-9921"
    assert params.get("job_id") == "441"
    assert params.get("lang") == "en"
    assert "utm_campaign" not in params
    assert "refId" not in params


def test_deduplication_stress_composite_matrix():
    """
    Stress-test a complex matrix of 50 jobs simultaneously:
    - 10 Unknown company jobs with identical title ('DevOps Fresher'), 10 unique URLs -> 10 survive
    - 10 Known company jobs ('Amazon', 'DevOps Fresher') across 10 different URLs -> 1 survives (9 deduped)
    - 10 Identical URL jobs with diverse tracking parameters -> 1 survives (9 deduped)
    - 5 Senior jobs ('Senior DevOps Manager') -> 0 survive (anti-senior)
    - 5 Stale jobs (100h old) -> 0 survive (freshness)
    - 10 Fresher jobs across target cities -> 10 survive
    Total Expected Surviving: 10 + 1 + 1 + 0 + 0 + 10 = 22 jobs.
    """
    now = pd.Timestamp.now(tz="UTC")
    jobs = []

    # 1. 10 Unknown company jobs
    for i in range(10):
        jobs.append(Job(
            id=f"matrix-unknown-{i}",
            title="DevOps Fresher",
            company="Unknown" if i % 2 == 0 else None,
            location="Pune, MH",
            description="Entry level DevOps, Docker, Linux, CI/CD. 0-1 years.",
            url=f"https://unknown-portal.com/job/{i}",
        ))

    # 2. 10 Known company duplicates ('Amazon', 'DevOps Fresher')
    for i in range(10):
        jobs.append(Job(
            id=f"matrix-amazon-{i}",
            title="DevOps Fresher",
            company="Amazon",
            location="Bangalore, KA",
            description="Entry level DevOps, Docker, Linux, CI/CD. 0-1 years.",
            url=f"https://amazon.jobs/en/req-{i}",
        ))

    # 3. 10 Identical URL jobs with different tracking query strings
    for i in range(10):
        jobs.append(Job(
            id=f"matrix-track-{i}",
            title=f"Cloud Associate {i}",
            company=f"CloudCorp {i}",
            location="Mumbai, MH",
            description="Cloud operations trainee. 0-2 years.",
            url=f"https://cloudcorp.com/apply/1234?utm_source=src_{i}&refId=ref_{i}",
        ))

    # 4. 5 Senior jobs
    for i in range(5):
        jobs.append(Job(
            id=f"matrix-senior-{i}",
            title="Senior DevOps Engineering Manager",
            company=f"TechGiant {i}",
            location="Pune",
            description="Lead team of 10. 8+ years experience.",
            url=f"https://techgiant.com/job/senior-{i}",
        ))

    # 5. 5 Stale jobs
    for i in range(5):
        j = Job(
            id=f"matrix-stale-{i}",
            title="DevOps Fresher",
            company=f"StaleCo {i}",
            location="Pune",
            description="DevOps junior 0-1 yrs.",
            url=f"https://staleco.com/job/{i}",
        )
        j.date_posted = (now - pd.Timedelta(hours=120)).strftime('%Y-%m-%d')
        jobs.append(j)

    # 6. 10 Distinct Fresher jobs across locations
    cities = ["Pune", "Mumbai", "Bangalore"]
    for i in range(10):
        jobs.append(Job(
            id=f"matrix-fresher-{i}",
            title=f"Software Engineer Track {i}",
            company=f"UniqueCompany {i}",
            location=f"{cities[i % len(cities)]}, India",
            description="Software engineering graduate program. 0-1 years experience.",
            url=f"https://uniquecompany-{i}.com/career/openings/{i}",
        ))

    assert len(jobs) == 50, f"Setup error: expected 50 jobs, got {len(jobs)}"

    filtered = apply_pandas_filter(jobs, ["Pune", "Mumbai", "Bangalore"], hours_old=72)
    # Expected:
    # 10 (Unknown) + 1 (Amazon deduped) + 1 (Tracking deduped) + 0 (Senior) + 0 (Stale) + 10 (Unique fresher) = 22
    assert len(filtered) == 22, (
        f"Expected exactly 22 surviving jobs from 50 input matrix, got {len(filtered)}. "
        f"Surviving: {[(j.title, j.company, j.url) for j in filtered]}"
    )


def test_clean_html_extreme_large_description_100kb():
    """
    Verify clean_html executes swiftly on 100 KB of complex HTML without
    catastrophic regex backtracking, and preserves multiline structure.
    """
    import time
    paragraphs = []
    for i in range(500):
        paragraphs.append(
            f"<h3>Section {i}</h3>"
            f"<p>This is paragraph {i} detailing role responsibilities and requirements.</p>"
            f"<ul>"
            f"  <li>Requirement {i}.A: Knowledge of Java and Spring Boot</li>"
            f"  <li>Requirement {i}.B: Knowledge of SQL and databases</li>"
            f"</ul>"
        )
    huge_html = "<div>" + "\n".join(paragraphs) + "</div>"
    assert len(huge_html) > 80_000, f"HTML size was {len(huge_html)} bytes, expected > 80KB"

    start = time.time()
    cleaned = clean_html(huge_html)
    elapsed = time.time() - start

    assert elapsed < 1.0, f"clean_html took {elapsed:.2f}s on 100KB HTML, expected < 1.0s"
    assert "\n" in cleaned
    assert "- Requirement 0.A: Knowledge of Java and Spring Boot" in cleaned
    assert "- Requirement 499.B: Knowledge of SQL and databases" in cleaned
    lines = [l for l in cleaned.splitlines() if l.strip()]
    assert len(lines) >= 1500, f"Expected at least 1500 lines, got {len(lines)}"


def test_clean_html_windows_crlf_and_whitespace_preservation():
    """Verify clean_html handles Windows CRLF (\\r\\n) and varied whitespace properly."""
    html_crlf = (
        "<p>Line One</p>\r\n"
        "<p>Line Two</p>\r\n"
        "<ul>\r\n"
        "\t<li>Item A</li>\r\n"
        "\t<li>Item B</li>\r\n"
        "</ul>"
    )
    cleaned = clean_html(html_crlf)
    assert "Line One" in cleaned
    assert "Line Two" in cleaned
    assert "- Item A" in cleaned
    assert "- Item B" in cleaned
    # Check no leftover raw carriage returns
    assert "\r" not in cleaned


def test_valid_apply_urls_ports_and_deep_paths():
    """Verify non-standard ports and deeply nested paths are preserved intact."""
    deep_urls = [
        "http://internal-careers.local:8080/jobs/view/99001",
        "https://citi.wd5.myworkdayjobs.com/en-US/Citi_Careers/job/Pune/Lead-Software-Engineer_24759021-1/apply",
        "https://example.com/apply/v2/path/to/job?job_id=QA%2BDev&city=Pune&utm_campaign=ignore",
    ]

    for raw in deep_urls:
        norm = normalize_url(raw)
        parsed = urllib.parse.urlparse(norm)

        if "8080" in raw:
            assert parsed.port == 8080
            assert parsed.netloc == "internal-careers.local:8080"
        if "Citi_Careers" in raw:
            assert parsed.path.endswith("/apply")
        if "QA%2BDev" in raw:
            assert "job_id=QA%2BDev" in parsed.query or "job_id=QA+Dev" in parsed.query
            assert "utm_campaign" not in parsed.query

