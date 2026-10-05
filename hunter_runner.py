import sys
import os
import time
import socket
import logging
import zipfile
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Fix Windows console emoji encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_DIR = Path(__file__).resolve().parent
DESKTOP_DIR = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"
LOG_FILE = PROJECT_DIR / "hunter_pipeline.log"
PROGRESS_FILE = PROJECT_DIR / "pipeline_progress.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HunterRunner")

def prevent_sleep():
    """Prevent Windows from sleeping or idling during pipeline execution."""
    if sys.platform == "win32":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_AWAYMODE_REQUIRED = 0x00000040
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
            logger.info("🛡️ Power execution lock acquired (Windows sleep/standby prevented during run).")
        except Exception as e:
            logger.warning(f"Could not set thread execution state: {e}")

def restore_sleep():
    """Restore normal sleep behavior after pipeline completes."""
    if sys.platform == "win32":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            logger.info("🛡️ Power execution lock released.")
        except Exception as e:
            logger.warning(f"Could not restore thread execution state: {e}")

def wait_for_internet(timeout_seconds: int = 60) -> bool:
    """Verifies internet connectivity before launching pipeline."""
    logger.info("📡 Checking internet connectivity...")
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            sock = socket.create_connection(("1.1.1.1", 53), timeout=3)
            sock.close()
            logger.info("   ✅ Internet connection verified!")
            return True
        except Exception:
            time.sleep(2)
    logger.warning("   ⚠️ Internet check timed out. Proceeding anyway...")
    return False

def package_deliverable_archive() -> str:
    """
    Packages the generated resumes and 3-column Job_Applications_Table into deliverable ZIP.
    ZIP Name: '<Date>.zip' (e.g. '4 October.zip') on Desktop.
    Archive contents:
      - Job_Applications_Table.pdf (root)
      - Job_Applications_Table.csv (root)
      - resume/ (subfolder with tailored resumes)
    """
    from src.archive_packager import package_pipeline_archive
    return package_pipeline_archive(desktop_dir=DESKTOP_DIR)

def main():
    parser = argparse.ArgumentParser(description="Hunter Autonomous Job Pipeline Runner")
    parser.add_argument("--hours-old", type=int, default=48, help="Scrape freshness cutoff in hours (24, 36, 48, 72)")
    parser.add_argument("--platforms", type=str, default="naukri,instahyre,internshala,unstop,hirist,workday,linkedin,indeed", help="Comma-separated platforms")
    parser.add_argument("--test-mode", action="store_true", help="Run fast test mode")
    parser.add_argument("--wait-offpeak", action="store_true", help="Wait for offpeak DeepSeek window (default: execute immediately)")
    parser.add_argument("--raw-text", "-t", help="Raw broadcast text or URLs to process in batch tailor mode")
    parser.add_argument("--links-file", "-f", help="File path containing links to process in batch tailor mode")
    args = parser.parse_args()

    is_batch_mode = bool(args.raw_text or args.links_file)

    logger.info("==================================================")
    logger.info("🎯 HUNTER AUTONOMOUS JOB PIPELINE LAUNCHER")
    if is_batch_mode:
        logger.info("   Mode:              BATCH URL / BROADCAST TAILORING")
        logger.info(f"   Input Source:      {'Raw Text' if args.raw_text else args.links_file}")
    else:
        logger.info("   Mode:              AUTONOMOUS PORTAL SWEEP")
        logger.info(f"   Freshness Cutoff:  {args.hours_old} hours")
        logger.info(f"   Target Platforms:  {args.platforms}")
    logger.info(f"   Execution Mode:    {'TEST' if args.test_mode else 'PRODUCTION'}")
    logger.info("==================================================")

    # 1. Acquire sleep lock
    prevent_sleep()

    try:
        # 2. Check connection
        wait_for_internet(timeout_seconds=30)

        # 3. Assemble command
        if is_batch_mode:
            cmd = [
                sys.executable,
                str(PROJECT_DIR / "run_batch_urls.py")
            ]
            if args.raw_text:
                cmd.extend(["--raw-text", args.raw_text])
            elif args.links_file:
                cmd.extend(["--links-file", args.links_file])
        else:
            cmd = [
                sys.executable,
                str(PROJECT_DIR / "run.py"),
                "--hours-old", str(args.hours_old),
                "--platforms", args.platforms
            ]
            if not args.wait_offpeak:
                cmd.append("--no-wait-offpeak")
            if args.test_mode:
                cmd.append("--test-mode")

        logger.info(f"▶️ Executing: {' '.join(cmd)}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 4. Stream subprocess output live
        max_retries = 2
        success = False

        for attempt in range(1, max_retries + 1):
            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1
                )

                for line in process.stdout:
                    print(line, end="")
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(line)

                process.wait()
                if process.returncode == 0:
                    logger.info("🏁 Pipeline execution finished cleanly with code 0.")
                    success = True
                    break
                else:
                    logger.warning(f"⚠️ Process returned non-zero exit code: {process.returncode}")
                    if attempt < max_retries:
                        logger.info(f"🔄 Retrying pipeline execution (Attempt {attempt+1}/{max_retries})...")
                        time.sleep(5)
            except Exception as e:
                logger.error(f"❌ Subprocess execution error: {e}")
                if attempt < max_retries:
                    logger.info("🔄 Auto-recovering and retrying...")
                    time.sleep(5)

        # 5. Package final deliverable ZIP on Desktop
        zip_path = package_deliverable_archive()

        logger.info("==================================================")
        logger.info("🎉 HUNTER PIPELINE RUN COMPLETE!")
        if zip_path:
            logger.info(f"📁 FINAL DELIVERABLE ARCHIVE ON DESKTOP: {zip_path}")
        logger.info(f"📄 Detailed log: {LOG_FILE}")
        logger.info("==================================================")

    finally:
        restore_sleep()

if __name__ == "__main__":
    main()
