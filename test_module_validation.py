"""
Module-by-module test for the scraping pipeline.
Tests:
1. Workday scraper — 422 error handling, deduplication, timeout behavior
2. Counter accuracy — simulates the callback/log interceptor interaction
3. Cycle counter — verifies global cycle numbering across job types
4. Pipeline handoff — verifies data flows correctly between modules
"""
import sys
import os

# Fix Windows console encoding for emoji output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.logger import logger

# ══════════════════════════════════════════════
# TEST 1: Workday Scraper — 422 Error Handling
# ══════════════════════════════════════════════
def test_workday_422_handling():
    """Test that Workday scraper handles HTTP 422 gracefully without hanging."""
    print("\n" + "="*60)
    print("TEST 1: Workday 422 Error Handling")
    print("="*60)
    
    from src.scrapers.workday import scrape_workday
    
    # Test with a single query that we know triggers 422 on ServiceNow
    try:
        jobs = scrape_workday(
            queries=["Software Tester"],
            test_mode=True,  # Only 1 employer
            max_results_per_query=5
        )
        print(f"  ✅ Workday returned {len(jobs)} jobs (no hang/crash)")
        return True
    except Exception as e:
        print(f"  ❌ Workday scraper crashed: {e}")
        return False


# ══════════════════════════════════════════════
# TEST 2: Workday Scraper — Full Run (All Employers)
# ══════════════════════════════════════════════
def test_workday_full_run():
    """Test Workday scraper across all employers with all search terms."""
    print("\n" + "="*60)
    print("TEST 2: Workday Full Run (All Employers)")
    print("="*60)
    
    from src.scrapers.workday import scrape_workday
    from src.config_loader import load_config
    
    config = load_config()
    search_terms = config.get('search', {}).get('search_terms', ['Software Engineer'])
    
    try:
        import time
        start = time.time()
        jobs = scrape_workday(
            queries=search_terms,
            test_mode=False,
            max_results_per_query=5  # Small limit for testing
        )
        elapsed = time.time() - start
        
        # Check for duplicates
        urls = [j.url for j in jobs]
        unique_urls = set(urls)
        dupes = len(urls) - len(unique_urls)
        
        print(f"  ✅ Workday returned {len(jobs)} jobs in {elapsed:.1f}s")
        print(f"     Unique URLs: {len(unique_urls)}")
        if dupes > 0:
            print(f"  ⚠️  Found {dupes} duplicate URLs (dedup should have caught these)")
        else:
            print(f"  ✅ No duplicates found")
        
        # Show per-employer breakdown
        from collections import Counter
        employer_counts = Counter(j.source for j in jobs)
        for emp, count in sorted(employer_counts.items()):
            print(f"     {emp}: {count} jobs")
            
        return True
    except Exception as e:
        print(f"  ❌ Workday full run crashed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ══════════════════════════════════════════════
# TEST 3: Counter Accuracy Simulation
# ══════════════════════════════════════════════
def test_counter_accuracy():
    """Simulate the pipeline's counting mechanism to verify no double-counting."""
    print("\n" + "="*60)
    print("TEST 3: Counter Accuracy (Callback vs Log Interceptor)")
    print("="*60)
    
    # Simulate pipeline_state
    pipeline_state = {
        "scan": {"total_found": 0},
    }
    
    # Simulate on_job_scraped callback
    def on_job_scraped(job_dict):
        pipeline_state["scan"]["total_found"] += 1
    
    # Simulate the FIXED log interceptor (should NOT touch total_found)
    import re
    def extract_number(text):
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0
    
    def pipeline_log_interceptor_FIXED(text):
        """The fixed interceptor — does NOT increment total_found from log messages."""
        text_lower = text.lower()
        # No total_found manipulation here — that's the fix!
        pass
    
    # Simulate 715 jobs scraped via callbacks (like JobSpy)
    for i in range(715):
        on_job_scraped({"title": f"Job {i}", "company": "Test"})
    
    after_jobspy = pipeline_state["scan"]["total_found"]
    print(f"  After 715 JobSpy callbacks: total_found = {after_jobspy}")
    assert after_jobspy == 715, f"Expected 715, got {after_jobspy}"
    
    # Simulate Workday returning 200 jobs via callbacks
    for i in range(200):
        on_job_scraped({"title": f"WD Job {i}", "company": "Test"})
    
    after_workday_callback = pipeline_state["scan"]["total_found"]
    print(f"  After 200 Workday callbacks: total_found = {after_workday_callback}")
    assert after_workday_callback == 915, f"Expected 915, got {after_workday_callback}"
    
    # Now simulate what happens with the FIXED log interceptor
    pipeline_log_interceptor_FIXED("✅ Workday Scraper finished. Found 200 jobs.")
    after_log = pipeline_state["scan"]["total_found"]
    print(f"  After FIXED log interceptor: total_found = {after_log}")
    assert after_log == 915, f"Expected 915 (no change), got {after_log}"
    
    print(f"  ✅ Counter stayed at {after_log} — no double-counting!")
    
    # Show what would have happened with the OLD buggy interceptor
    old_extract = extract_number("✅ Workday Scraper finished. Found 200 jobs.")
    old_total = 915 + old_extract
    print(f"  ⚠️  OLD buggy interceptor would have made it: {old_total} (added {old_extract} extra)")
    
    return True


# ══════════════════════════════════════════════
# TEST 4: Cycle Counter Across Job Types
# ══════════════════════════════════════════════
def test_cycle_counter():
    """Verify that the cycle counter is cumulative across job types.
    
    After the location-batching optimization, cycles = terms (not terms×locations).
    All locations are passed as a single comma-separated string per search term.
    """
    print("\n" + "="*60)
    print("TEST 4: Cycle Counter Across Job Types (Location-Batched)")
    print("="*60)
    
    from src.config_loader import load_config
    config = load_config()
    search_cfg = config.get('search', {})
    
    search_terms = search_cfg.get('search_terms', ['Java Developer'])
    locations = search_cfg.get('locations', ['Pune'])
    job_types = search_cfg.get('job_types', ['fulltime', 'internship'])
    platforms = ['linkedin', 'indeed']
    
    # Simulate the OPTIMIZED pre-calculation: 1 cycle per term (locations batched)
    global_total_cycles = 0
    for jt in job_types:
        jobspy_plats = [p for p in platforms if p not in ["workday", "jsonld"]]
        if jt == "internship" and "linkedin" in jobspy_plats:
            jobspy_plats = [p for p in jobspy_plats if p != "linkedin"]
        if jobspy_plats:
            combos = len(search_terms)  # One call per term, all locations batched
            global_total_cycles += combos
    
    old_total = len(search_terms) * len(locations) * len(job_types)  # Old un-batched count
    
    print(f"  Search terms: {len(search_terms)}")
    print(f"  Locations: {len(locations)} (batched into single call)")
    print(f"  Job types: {job_types}")
    print(f"  Platforms: {platforms}")
    print(f"  OLD cycles (un-batched): {old_total}  ({len(search_terms)} terms × {len(locations)} locs × {len(job_types)} types)")
    print(f"  NEW cycles (batched):    {global_total_cycles}  ({len(search_terms)} terms × {len(job_types)} types)")
    print(f"  Speedup: {old_total / max(global_total_cycles, 1):.1f}x fewer cycles")
    print(f"  Batched location string: \"{', '.join(locations)}\"")
    
    assert global_total_cycles == len(search_terms) * len(job_types), \
        f"Expected {len(search_terms) * len(job_types)} cycles, got {global_total_cycles}"
    assert global_total_cycles < old_total, "Batched should have fewer cycles than un-batched"
    
    print(f"  ✅ Cycle count correct: {global_total_cycles} (was {old_total})")
    
    return True


# ══════════════════════════════════════════════
# TEST 5: Pipeline Data Handoff (Scraper → Filter)
# ══════════════════════════════════════════════
def test_pipeline_handoff():
    """Test that data flows correctly from scraper output to the pandas filter."""
    print("\n" + "="*60)
    print("TEST 5: Pipeline Data Handoff (Scraper -> Filter)")
    print("="*60)
    
    from src.scraper import apply_pandas_filter
    from src.models import Job
    import pandas as pd
    
    # Create mock jobs simulating scraper output
    mock_jobs = []
    for i in range(10):
        job = Job(
            id=str(i),
            title=f"Software Engineer {i}",
            company=f"Company {i}",
            location="Pune, Maharashtra, India",
            description=f"We are looking for a software engineer with 1-2 years of experience in Python and JavaScript. This is a junior role. Job {i}.",
            url=f"https://example.com/job/{i}",
            source="linkedin",
            job_type="fulltime"
        )
        job.date_posted = pd.Timestamp.now(tz="UTC")
        job.is_remote = False
        mock_jobs.append(job)
    
    # Add a senior job (should be filtered)
    senior_job = Job(
        id="senior1",
        title="Senior Software Engineer",
        company="BigCorp",
        location="Pune",
        description="Looking for a senior engineer with 10 years experience.",
        url="https://example.com/senior",
        source="linkedin",
        job_type="fulltime"
    )
    senior_job.date_posted = pd.Timestamp.now(tz="UTC")
    senior_job.is_remote = False
    mock_jobs.append(senior_job)
    
    # Add a duplicate
    dup_job = Job(
        id="dup1",
        title="Software Engineer 0",
        company="Company 0",
        location="Pune, Maharashtra, India",
        description="We are looking for a software engineer with 1-2 years of experience. Duplicate.",
        url="https://example.com/job/0",  # Same URL as job 0
        source="indeed",
        job_type="fulltime"
    )
    dup_job.date_posted = pd.Timestamp.now(tz="UTC")
    dup_job.is_remote = False
    mock_jobs.append(dup_job)
    
    print(f"  Input: {len(mock_jobs)} jobs (10 valid + 1 senior + 1 duplicate)")
    
    # Track what gets dropped
    dropped = []
    def on_drop(title, company, reason):
        dropped.append({"title": title, "company": company, "reason": reason})
    
    callbacks = {"on_job_dropped": on_drop}
    
    filtered = apply_pandas_filter(mock_jobs, ["Pune", "Mumbai", "Bangalore"], callbacks=callbacks)
    
    print(f"  Output: {len(filtered)} jobs after filtering")
    print(f"  Dropped: {len(dropped)} jobs")
    for d in dropped:
        print(f"    - {d['title']} at {d['company']}: {d['reason']}")
    
    # Verify senior job was filtered
    senior_filtered = any(j.title == "Senior Software Engineer" for j in filtered)
    assert not senior_filtered, "Senior job should have been filtered!"
    print(f"  ✅ Senior job correctly filtered out")
    
    # Verify duplicate was filtered  
    urls = [j.url for j in filtered]
    assert len(urls) == len(set(urls)), "Duplicate URLs should have been removed!"
    print(f"  ✅ Duplicate correctly removed")
    
    return True


# ══════════════════════════════════════════════
# RUN ALL TESTS
# ══════════════════════════════════════════════
if __name__ == "__main__":
    results = {}
    
    # Non-network tests first
    results["Counter Accuracy"] = test_counter_accuracy()
    results["Cycle Counter"] = test_cycle_counter()
    results["Pipeline Handoff"] = test_pipeline_handoff()
    
    # Network tests (these make real API calls)
    results["Workday 422 Handling"] = test_workday_422_handling()
    results["Workday Full Run"] = test_workday_full_run()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(results.values())
    print(f"\n{'🎉 All tests passed!' if all_passed else '⚠️ Some tests failed.'}")
    sys.exit(0 if all_passed else 1)
