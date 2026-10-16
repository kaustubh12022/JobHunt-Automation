"""
run_batch_urls.py — CLI entry point to process batch URLs for automated resume tailoring.

Usage:
    python run_batch_urls.py --links-file links.txt
    python run_batch_urls.py --raw-text "Valeo ... https://... Wipro ... https://..."
    python run_batch_urls.py https://link1 https://link2
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import date

# Fix Windows console emoji encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

from src.logger import logger
from src.batch_url_pipeline import run_batch_url_pipeline


def main():
    parser = argparse.ArgumentParser(description="Batch URL Resume Tailoring Pipeline")
    parser.add_argument("urls", nargs="*", help="Direct URLs to process")
    parser.add_argument("--links-file", "-f", help="Path to text file containing URLs or broadcast message")
    parser.add_argument("--raw-text", "-t", help="Raw text containing links and job descriptions")
    parser.add_argument("--min-score", "-s", type=int, default=60, help="Minimum AI match score required for resume generation (default: 60)")
    parser.add_argument("--output-dir", "-o", help="Custom output directory on Desktop")
    args = parser.parse_args()

    input_data = ""
    if args.links_file:
        file_path = Path(args.links_file)
        if not file_path.exists():
            print(f"❌ Error: Links file not found: {args.links_file}")
            sys.exit(1)
        input_data = file_path.read_text(encoding="utf-8", errors="replace")
    elif args.raw_text:
        input_data = args.raw_text
    elif args.urls:
        input_data = " ".join(args.urls)
    else:
        print("📋 Paste links or broadcast message (press Enter twice or Ctrl+Z/Ctrl+D to finish):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        input_data = "\n".join(lines)

    if not input_data.strip():
        print("⚠️ No links or text provided. Exiting.")
        sys.exit(0)

    print("\n" + "═" * 60)
    print("🚀 STARTING BATCH URL RESUME TAILORING PIPELINE")
    print(f"🎯 Threshold: Match Score >= {args.min_score}% required for resume generation")
    print("═" * 60 + "\n")

    results = run_batch_url_pipeline(
        urls_or_text=input_data,
        min_score_threshold=args.min_score,
        output_desktop_dir=args.output_dir
    )

    desktop_dir = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"
    
    # Identify table pdf from results
    table_pdf = results.get('catalog_pdf') or str(desktop_dir / "Job_Applications_Table.pdf")
    zip_path = results.get("zip_path", "")

    # Save comprehensive report to batch_summary_report.json
    import json
    report_data = {
        "timestamp": date.today().isoformat(),
        "total_urls": results['total_urls'],
        "parsed_count": len(results['shortlisted_jobs']) + len(results['low_score_jobs']),
        "shortlisted_count": len(results['shortlisted_jobs']),
        "low_score_count": len(results['low_score_jobs']),
        "failed_count": len(results['failed_links']),
        "shortlisted_jobs": results['shortlisted_jobs'],
        "low_score_jobs": results['low_score_jobs'],
        "failed_links": results['failed_links'],
        "desktop_folder": results['desktop_folder'],
        "zip_path": zip_path,
        "catalog_pdf": results.get('catalog_pdf', ''),
        "summary_pdf": results.get('summary_pdf', ''),
        "summary_md": results.get('summary_md', '')
    }
    report_file = Path(__file__).resolve().parent / "batch_summary_report.json"
    with open(report_file, "w", encoding="utf-8") as rf:
        json.dump(report_data, rf, indent=2)

    print("\n" + "═" * 60)
    print("🎉 BATCH PROCESSING COMPLETE!")
    print(f"   Total Links Analyzed:       {results['total_urls']}")
    print(f"   Successfully Parsed:        {report_data['parsed_count']}")
    print(f"   Resumes Generated (>=60%):  {len(results['shortlisted_jobs'])}")
    print(f"   Low Relevance (<60%):       {len(results['low_score_jobs'])}")
    print(f"   Failed / Unparsed Links:    {len(results['failed_links'])}")
    print(f"   📁 Output Folder:           {results['desktop_folder']}")
    if zip_path:
        print(f"   📦 Deliverable ZIP:         {zip_path}")

    if results['shortlisted_jobs']:
        print("\n✅ SHORTLISTED JOBS & GENERATED RESUMES:")
        for idx, sj in enumerate(results['shortlisted_jobs'], 1):
            print(f"   [{idx}] {sj['company']} — {sj['role']} ({sj['score']}% Match)")
            print(f"       Resume: {sj['filename']}")
            print(f"       Apply:  {sj['apply_link']}")

    if results['low_score_jobs']:
        print("\n🔍 LOW RELEVANCE ROLES (Score < 60% — No Resume Generated):")
        for idx, lj in enumerate(results['low_score_jobs'], 1):
            print(f"   [{idx}] {lj['company']} — {lj['role']} ({lj['score']}% Match)")
            print(f"       Reason: {lj['reason']}")

    if results['failed_links']:
        print("\n⚠️ UNPARSED / FAILED LINKS:")
        for idx, fj in enumerate(results['failed_links'], 1):
            print(f"   [{idx}] {fj.get('company', 'Unknown')} — {fj.get('title', 'Link')}")
            print(f"       URL:    {fj['url']}")
            print(f"       Reason: {fj['error_reason']}")
            print(f"       Action: {fj.get('suggested_action', 'Check URL manually')}")

    print("═" * 60)


if __name__ == "__main__":
    main()
