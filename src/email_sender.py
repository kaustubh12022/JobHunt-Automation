"""
AutoApply Email Sender — SMTP 587 + STARTTLS.

Architecture Rules:
- MUST use SMTP port 587 with starttls() BEFORE login()
- Fault-tolerant: on failure, preserve ZIP on Desktop
- Sends HTML email with stats table and shortlisted jobs
"""
import os
import shutil
import smtplib
import socket
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from src.logger import logger
from src.config_loader import load_config
from src.models import Job


def deliver_daily_resumes(output_folder: str, date_str: str, stats: dict = None, shortlisted: list[Job] = None):
    """
    Zips the daily output folder and emails it using Gmail SMTP.
    
    SMTP Sequence (mandatory):
    1. SMTP('smtp.gmail.com', 587)
    2. server.starttls()  ← cryptographic layer BEFORE login
    3. server.login(email, app_password)
    """
    config = load_config()
    email_cfg = config.get('email', {})

    if not email_cfg.get('enabled', False):
        logger.info("📧 Email delivery is disabled in config. Skipping delivery.")
        return

    sender_email = email_cfg.get('sender')
    recipient_email = email_cfg.get('recipient')
    app_password = email_cfg.get('app_password')

    if not sender_email or not recipient_email or not app_password or app_password == "YOUR_16_CHAR_APP_PASSWORD":
        logger.warning("⚠️ Email is enabled but credentials are not configured properly. Skipping.")
        return

    # ── Create ZIP on Desktop ──
    desktop_path = Path(config['output']['desktop_path'])
    zip_base_path = desktop_path / f"AutoApply_Daily_{date_str.replace(' ', '_')}"

    logger.info("📦 Zipping daily output to Desktop...")
    try:
        zip_path = shutil.make_archive(str(zip_base_path), 'zip', output_folder)
        logger.info(f"✅ ZIP file created: {zip_path}")
    except Exception as e:
        logger.error(f"❌ Failed to create ZIP file: {e}")
        return

    # ── Compose HTML email ──
    logger.info("📧 Drafting email...")

    msg = MIMEMultipart()
    msg['Subject'] = f'🚀 AutoApply: Your Daily Resumes are Ready! ({date_str})'
    msg['From'] = sender_email
    msg['To'] = recipient_email

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto;">
        <h2>🚀 AutoApply Pipeline Complete</h2>
        <p>Your daily job automation has finished. The Excel tracker and tailored PDFs are in the attached ZIP.</p>
        
        <h3>📊 Scraping & Filtering Stats</h3>
        <ul>
          <li><b>Initially Found (Raw):</b> {stats.get('found_initial', 0) if stats else 0} jobs</li>
          <li><b>Filtered by Pandas (Stale/Senior/Exp/Loc):</b> {stats.get('pandas_dropped', 0) if stats else 0} jobs removed</li>
          <li><b>Removed Duplicate Overlap:</b> {stats.get('dedup_dropped', 0) if stats else 0} jobs removed</li>
          <li><b>Reached AI Scoring Stage:</b> {stats.get('reached_scoring', 0) if stats else 0} jobs</li>
        </ul>
        
        <h3>🤖 AI Processing Stats</h3>
        <ul>
          <li><b>Successfully Scored:</b> {stats.get('scored', 0) if stats else 0} jobs</li>
          <li><b>Resumes Tailored & Generated:</b> {stats.get('tailored', 0) if stats else 0} jobs</li>
        </ul>
        <br>
    """

    if shortlisted:
        html += """
        <h3>🏆 Final Jobs (Resumes Generated)</h3>
        <table border="1" cellpadding="8" style="border-collapse: collapse; text-align: left; width: 100%;">
          <tr style="background-color: #f2f2f2;">
            <th>Job Title</th>
            <th>Company Name</th>
            <th>Fit Score</th>
          </tr>
        """
        for job in shortlisted:
            color = 'green' if (job.score or 0) >= 80 else 'orange'
            html += f"""
          <tr>
            <td>{job.title}</td>
            <td>{job.company}</td>
            <td style="font-weight: bold; color: {color}; text-align: center;">{job.score}%</td>
          </tr>
            """
        html += "</table><br>"

    html += "<p>Keep crushing it! 🔥</p></body></html>"
    msg.attach(MIMEText(html, 'html'))

    # ── Attach ZIP ──
    try:
        with open(zip_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(zip_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_path)}"'
        msg.attach(part)
    except Exception as e:
        logger.error(f"❌ Failed to attach ZIP file: {e}")
        return

    # ── Send via SMTP 587 + STARTTLS ──
    logger.info("📡 Sending via Gmail (SMTP 587 + STARTTLS)...")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()  # Mandatory: cryptographic layer BEFORE login
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        logger.info("✅ Email sent successfully!")

    except (socket.gaierror, OSError) as e:
        logger.error(f"❌ NETWORK ERROR: No internet connection. {e}")
        logger.error(f"⚠️ Your ZIP file is safely saved on your Desktop: {zip_path}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ EMAIL ERROR: Invalid App Password or Email Address. {e}")
        logger.error(f"⚠️ Your ZIP file is safely saved on your Desktop: {zip_path}")
    except Exception as e:
        logger.error(f"❌ EMAIL ERROR: {e}")
        logger.error(f"⚠️ Your ZIP file is safely saved on your Desktop: {zip_path}")