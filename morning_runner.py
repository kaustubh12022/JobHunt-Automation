import sys
import os
import time
import socket
import logging
import zipfile
import subprocess
from datetime import datetime
from pathlib import Path

# Fix Windows console emoji encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_DIR = Path(__file__).resolve().parent
DESKTOP_DIR = Path(os.environ.get("USERPROFILE", "C:/Users/kalek")) / "Desktop"
LOG_FILE = PROJECT_DIR / "morning_pipeline.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MorningRunner")

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
    """
    When waking from Sleep/Hibernate, Wi-Fi can take 5-15s to reconnect.
    This checks connectivity before launching the scraper.
    """
    logger.info("📡 Checking internet connectivity after wake-up...")
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            # Check connection to Cloudflare DNS or Google
            sock = socket.create_connection(("1.1.1.1", 53), timeout=3)
            sock.close()
            logger.info("   ✅ Internet connection verified! Wi-Fi is active.")
            return True
        except Exception:
            time.sleep(3)
    logger.warning("   ⚠️ Internet check timed out. Proceeding anyway...")
    return False

def package_zip_archive() -> str:
    """
    Packages the generated resumes and Job_Applications_Table.pdf into deliverable ZIP.
    Delegates to shared package_pipeline_archive.
    """
    from src.archive_packager import package_pipeline_archive
    return package_pipeline_archive(desktop_dir=DESKTOP_DIR)

def main():
    logger.info("==================================================")
    logger.info("🚀 JOBHUNT MORNING PIPELINE AUTO-LAUNCHER (10:00 AM IST)")
    logger.info("==================================================")

    # 1. Acquire Windows power lock to prevent system sleep
    prevent_sleep()

    try:
        # 2. Wait for Wi-Fi to stabilize after wake
        wait_for_internet(timeout_seconds=45)

        # 2.5 Sync profile and credentials from Desktop resume
        try:
            from src.profile_manager import sync_profile_from_desktop
            sync_profile_from_desktop()
        except Exception as e:
            logger.warning(f"Could not auto-sync profile from Desktop: {e}")

        # 3. Run the main pipeline with off-peak enabled immediately
        cmd = [
            sys.executable,
            str(PROJECT_DIR / "run.py"),
            "--no-wait-offpeak"
        ]
        logger.info(f"▶️ Executing: {' '.join(cmd)}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        try:
            # Stream output in real-time
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
            logger.info(f"🏁 Pipeline execution finished with return code: {process.returncode}")

        except Exception as e:
            logger.error(f"❌ Subprocess failed: {e}")

        # 4. Create the ZIP archive on Desktop
        zip_result = package_zip_archive()

        # 5. Generate Morning Executive Digest & Audit Telemetry
        try:
            from src.morning_digest import generate_morning_digest
            digest_report = generate_morning_digest()
            logger.info(f"🌅 Morning Digest generated: {digest_report.get('markdown_path')}")
        except Exception as e:
            logger.warning(f"Could not generate morning digest: {e}")

        logger.info("==================================================")
        logger.info("🎉 MORNING RUN COMPLETE!")
        if zip_result:
            logger.info(f"📁 FINAL DELIVERABLE READY: {zip_result}")
        logger.info(f"📄 Full log saved at: {LOG_FILE}")
        logger.info("==================================================")
    finally:
        restore_sleep()

if __name__ == "__main__":
    main()
