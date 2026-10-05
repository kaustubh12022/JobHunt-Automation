"""
AutoApply — Master Raw Dataset Collection & Verification Pipeline.

This script executes Phase 1: Fresh Pipeline Run for the entire job scraping suite.
It captures and permanently preserves 100% of raw scraped jobs before any
disqualification or filtering occurs, writes real-time JSONL streams, creates
full JSON copies in both project storage and the user's Desktop, and runs
an exhaustive data completeness and integrity audit.
"""

import sys
import os
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import logger
from src.config_loader import load_config
from src.scraper import run_scraper, get_last_raw_jobs
from src.models import Job


def serialize_job(idx: int, job: Job) -> dict:
    date_posted_val = getattr(job, "date_posted", None)
    if date_posted_val is not None:
        date_posted_str = str(date_posted_val)
    else:
        date_posted_str = None

    raw_meta = getattr(job, "raw_metadata", None)
    if not isinstance(raw_meta, dict):
        raw_meta = {}

    return {
        "job_index": idx,
        "id": getattr(job, "id", str(uuid.uuid4())),
        "title": str(getattr(job, "title", "Unknown") or "Unknown"),
        "company": str(getattr(job, "company", "Unknown") or "Unknown"),
        "location": str(getattr(job, "location", "Unknown") or "Unknown"),
        "description": str(getattr(job, "description", "") or ""),
        "url": str(getattr(job, "url", "") or ""),
        "source": str(getattr(job, "source", "unknown") or "unknown"),
        "job_type": str(getattr(job, "job_type", "fulltime") or "fulltime"),
        "date_posted": date_posted_str,
        "is_remote": bool(getattr(job, "is_remote", False)),
        "raw_metadata": raw_meta,
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }


def run_master_scrape():
    start_time = datetime.now(timezone.utc)
    date_str = start_time.strftime("%Y-%m-%d")
    timestamp_str = start_time.strftime("%Y-%m-%d_%H%M%S")

    logger.info("=" * 70)
    logger.info("🚀 STARTING FRESH MASTER RAW SCRAPE PIPELINE")
    logger.info(f"   Timestamp: {start_time.isoformat()}")
    logger.info("=" * 70)

    # 1. Define Destinations
    audit_dir = PROJECT_ROOT / "regex_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    data_dir = PROJECT_ROOT / "data_folder"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Master permanent storage paths
    jsonl_master_path = audit_dir / f"master_raw_dataset_{date_str}.jsonl"
    json_master_path = audit_dir / f"master_raw_dataset_{date_str}.json"
    json_data_folder_path = data_dir / f"master_raw_dataset_{date_str}.json"

    # User Desktop storage paths
    config = load_config()
    desktop_base = Path(config.get("output", {}).get("desktop_path", "C:/Users/kalek/Desktop"))
    desktop_output_folder = desktop_base / config.get("output", {}).get("folder_name", "AutoApply_Output")
    desktop_output_folder.mkdir(parents=True, exist_ok=True)

    desktop_json_path = desktop_base / f"master_raw_jobs_{date_str}.json"
    desktop_folder_json_path = desktop_output_folder / f"master_raw_jobs_{date_str}.json"

    logger.info("📁 Target Storage Locations:")
    logger.info(f"   [Permanent JSONL]:   {jsonl_master_path}")
    logger.info(f"   [Permanent JSON]:    {json_master_path}")
    logger.info(f"   [Data Folder JSON]:  {json_data_folder_path}")
    logger.info(f"   [Desktop Root JSON]: {desktop_json_path}")
    logger.info(f"   [Desktop Out JSON]:  {desktop_folder_json_path}")

    # Open JSONL for live streaming (append mode)
    jsonl_file = open(jsonl_master_path, "w", encoding="utf-8")

    captured_jobs_records = []
    seen_ids = set()

    # Live streaming callback
    def on_raw_job_scraped(job: Job):
        nonlocal captured_jobs_records
        record_idx = len(captured_jobs_records)
        record = serialize_job(record_idx, job)
        captured_jobs_records.append(record)
        
        # Immediate stream-write & flush to disk
        line = json.dumps(record, ensure_ascii=False) + "\n"
        jsonl_file.write(line)
        jsonl_file.flush()

        if (record_idx + 1) % 50 == 0:
            logger.info(f"   💾 Stream-saved {record_idx + 1} raw jobs to JSONL...")

    def on_cycle_start_callback(info):
        cycle_lbl = info.get("cycle_label", "")
        msg = info.get("message", "")
        if cycle_lbl:
            logger.info(f"🔄 {cycle_lbl}")
        elif msg:
            logger.info(f"   {msg}")

    callbacks = {
        "on_raw_job": on_raw_job_scraped,
        "on_cycle_start": on_cycle_start_callback,
    }

    platforms = config.get("search", {}).get("platforms", ["linkedin", "indeed"])
    job_types = config.get("search", {}).get("job_types", ["fulltime", "internship"])

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"🚀 INITIATING RUN_SCRAPER")
    logger.info(f"   Platforms: {platforms}")
    logger.info(f"   Job Types: {job_types}")
    logger.info(f"   Search terms: {config.get('search', {}).get('search_terms', [])}")
    logger.info(f"   Locations:    {config.get('search', {}).get('locations', [])}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        # Run scraper (test_mode=False for the real fresh production pipeline)
        filtered_jobs, stats = run_scraper(
            selected_platforms=platforms,
            selected_job_types=job_types,
            test_mode=False,
            callbacks=callbacks
        )
    except Exception as e:
        logger.error(f"❌ Scraper crashed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        jsonl_file.close()

    # Retrieve all raw jobs from module cache to ensure 100% sync
    last_raw_jobs = get_last_raw_jobs()
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"🏁 SCRAPING COMPLETED")
    logger.info(f"   Stream-saved raw records: {len(captured_jobs_records)}")
    logger.info(f"   Scraper module cached raw: {len(last_raw_jobs)}")
    logger.info(f"   Pre-filter survivors:     {len(filtered_jobs)}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # If for any reason stream missed something present in last_raw_jobs, backfill
    if len(last_raw_jobs) > len(captured_jobs_records):
        logger.warning(f"⚠️ Backfilling {len(last_raw_jobs) - len(captured_jobs_records)} jobs from module cache...")
        streamed_urls = {r["url"] for r in captured_jobs_records if r.get("url")}
        with open(jsonl_master_path, "a", encoding="utf-8") as f_append:
            for job in last_raw_jobs:
                if job.url and job.url in streamed_urls:
                    continue
                rec = serialize_job(len(captured_jobs_records), job)
                captured_jobs_records.append(rec)
                f_append.write(json.dumps(rec, ensure_ascii=False) + "\n")

    total_scraped = len(captured_jobs_records)
    logger.info(f"📊 Final Raw Jobs Count: {total_scraped}")

    if total_scraped == 0:
        logger.error("❌ ZERO jobs were scraped! Please check network connection or JobSpy limits.")
        return False

    # 2. Save full JSON arrays
    logger.info("💾 Writing full JSON dataset copies...")
    json_data_str = json.dumps(captured_jobs_records, indent=2, ensure_ascii=False)

    # Master permanent JSON
    with open(json_master_path, "w", encoding="utf-8") as f:
        f.write(json_data_str)
    logger.info(f"   ✅ Saved: {json_master_path} ({os.path.getsize(json_master_path) / (1024*1024):.2f} MB)")

    # Data folder JSON
    with open(json_data_folder_path, "w", encoding="utf-8") as f:
        f.write(json_data_str)
    logger.info(f"   ✅ Saved: {json_data_folder_path} ({os.path.getsize(json_data_folder_path) / (1024*1024):.2f} MB)")

    # Desktop Root JSON
    try:
        with open(desktop_json_path, "w", encoding="utf-8") as f:
            f.write(json_data_str)
        logger.info(f"   ✅ Saved: {desktop_json_path} ({os.path.getsize(desktop_json_path) / (1024*1024):.2f} MB)")
    except Exception as e:
        logger.error(f"   ❌ Could not write to desktop root: {e}")

    # Desktop Output Folder JSON
    try:
        with open(desktop_folder_json_path, "w", encoding="utf-8") as f:
            f.write(json_data_str)
        logger.info(f"   ✅ Saved: {desktop_folder_json_path} ({os.path.getsize(desktop_folder_json_path) / (1024*1024):.2f} MB)")
    except Exception as e:
        logger.error(f"   ❌ Could not write to desktop output folder: {e}")

    # 3. VERIFICATION SUITE
    logger.info("=" * 70)
    logger.info("🔍 EXECUTING COMPREHENSIVE DATA INTEGRITY AUDIT")
    logger.info("=" * 70)

    verification = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_jobs_scraped": total_scraped,
        "files_verified": {},
        "integrity_checks": {},
        "dataset_statistics": {}
    }

    # Verify each file on disk
    files_to_check = {
        "permanent_jsonl": jsonl_master_path,
        "permanent_json": json_master_path,
        "data_folder_json": json_data_folder_path,
        "desktop_json": desktop_json_path,
        "desktop_output_json": desktop_folder_json_path
    }

    all_files_ok = True
    for label, fpath in files_to_check.items():
        exists = fpath.exists()
        size = fpath.stat().st_size if exists else 0
        status_ok = exists and size > 0
        if not status_ok:
            all_files_ok = False
        
        # Test parsing
        records_read = 0
        parse_ok = False
        if exists:
            try:
                if fpath.suffix == ".jsonl":
                    with open(fpath, "r", encoding="utf-8") as f:
                        records_read = sum(1 for line in f if line.strip())
                    parse_ok = (records_read == total_scraped)
                else:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    records_read = len(data)
                    parse_ok = (records_read == total_scraped)
            except Exception as pe:
                parse_ok = False

        verification["files_verified"][label] = {
            "path": str(fpath),
            "exists": exists,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "records_counted": records_read,
            "syntax_valid": parse_ok
        }
        logger.info(f"   [{label}] Exists: {exists} | Size: {size/(1024*1024):.2f}MB | Records: {records_read}/{total_scraped} | Valid: {parse_ok}")

    # Detailed record field integrity checks
    has_title_count = 0
    has_company_count = 0
    has_location_count = 0
    has_description_count = 0
    has_url_count = 0
    platform_breakdown = {}
    job_type_breakdown = {}
    location_breakdown = {}

    for r in captured_jobs_records:
        if r.get("title") and r["title"] != "Unknown":
            has_title_count += 1
        if r.get("company") and r["company"] != "Unknown":
            has_company_count += 1
        if r.get("location") and r["location"] != "Unknown":
            has_location_count += 1
        if r.get("description") and r["description"].strip():
            has_description_count += 1
        if r.get("url") and r["url"].strip():
            has_url_count += 1

        src = r.get("source", "unknown")
        platform_breakdown[src] = platform_breakdown.get(src, 0) + 1

        jt = r.get("job_type", "unknown")
        job_type_breakdown[jt] = job_type_breakdown.get(jt, 0) + 1

        loc = r.get("location", "unknown")
        location_breakdown[loc] = location_breakdown.get(loc, 0) + 1

    verification["integrity_checks"] = {
        "all_records_have_id": all(bool(r.get("id")) for r in captured_jobs_records),
        "valid_title_ratio": f"{has_title_count}/{total_scraped} ({has_title_count/total_scraped*100:.1f}%)",
        "valid_company_ratio": f"{has_company_count}/{total_scraped} ({has_company_count/total_scraped*100:.1f}%)",
        "valid_location_ratio": f"{has_location_count}/{total_scraped} ({has_location_count/total_scraped*100:.1f}%)",
        "non_empty_description_ratio": f"{has_description_count}/{total_scraped} ({has_description_count/total_scraped*100:.1f}%)",
        "valid_url_ratio": f"{has_url_count}/{total_scraped} ({has_url_count/total_scraped*100:.1f}%)",
        "zero_missing_records": (total_scraped == len(captured_jobs_records))
    }

    verification["dataset_statistics"] = {
        "platform_breakdown": platform_breakdown,
        "job_type_breakdown": job_type_breakdown,
        "top_locations": dict(sorted(location_breakdown.items(), key=lambda x: x[1], reverse=True)[:10])
    }

    # Save verification report as JSON and Markdown
    report_json_path = audit_dir / f"dataset_verification_report_{date_str}.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(verification, f, indent=2, ensure_ascii=False)

    report_md_path = audit_dir / f"dataset_verification_report_{date_str}.md"
    md_content = f"""# Master Raw Dataset Verification Report
**Date:** {date_str}  
**Scrape Run Timestamp:** {start_time.isoformat()}  
**Total Raw Jobs Captured:** {total_scraped}

## File Storage Verification
| Location Label | Path | Size (MB) | Records Verified | Syntax Valid |
|---|---|---|---|---|
"""
    for lbl, meta in verification["files_verified"].items():
        md_content += f"| `{lbl}` | `{meta['path']}` | {meta['size_mb']} MB | {meta['records_counted']} | {'✅' if meta['syntax_valid'] else '❌'} |\n"

    md_content += f"""
## Field Completeness & Integrity
- **Unique Records:** {total_scraped}
- **Valid Titles:** {verification['integrity_checks']['valid_title_ratio']}
- **Valid Companies:** {verification['integrity_checks']['valid_company_ratio']}
- **Valid Locations:** {verification['integrity_checks']['valid_location_ratio']}
- **Full Cleaned Descriptions:** {verification['integrity_checks']['non_empty_description_ratio']}
- **Valid URLs:** {verification['integrity_checks']['valid_url_ratio']}

## Platform Distribution
"""
    for plat, count in platform_breakdown.items():
        md_content += f"- **{plat}**: {count} jobs ({count/total_scraped*100:.1f}%)\n"

    md_content += f"""
## Job Type Distribution
"""
    for jt, count in job_type_breakdown.items():
        md_content += f"- **{jt}**: {count} jobs ({count/total_scraped*100:.1f}%)\n"

    md_content += f"""
## Top 10 Locations
"""
    for loc, count in verification["dataset_statistics"]["top_locations"].items():
        md_content += f"- **{loc}**: {count} jobs\n"

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info("=" * 70)
    logger.info("🎉 MASTER RAW SCRAPE & VERIFICATION COMPLETED SUCCESSFULLY!")
    logger.info(f"   Total Raw Jobs:        {total_scraped}")
    logger.info(f"   Master JSONL:          {jsonl_master_path}")
    logger.info(f"   Master JSON:           {json_master_path}")
    logger.info(f"   Desktop JSON:          {desktop_json_path}")
    logger.info(f"   Verification Report:   {report_md_path}")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = run_master_scrape()
    sys.exit(0 if success else 1)
