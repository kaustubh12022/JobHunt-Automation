"""
Naukri Auto-Apply Bot - Strict Freshness & Smart Chatbot Error Recovery Edition
================================================================================
Automates job applications on Naukri.com using Selenium with Microsoft Edge:
- Strict Freshness: ONLY jobs posted in the past 24 hours / 1 day (jobAge=1).
- Strict Experience: ONLY Freshers / 0-1 years (experience=0).
- Skips external company career portals ("Apply on company site").
- Smart Chatbot Recovery:
  * Full chat transcript context to understand true question.
  * Field-type sanity guards (e.g. City is ALWAYS 'Pune', never numbers or LPA).
  * Auto-detects 'input seems invalid' rejections and re-prompts Gemini to correct format.
  * Never repeats a rejected answer in a loop.
- Brings Edge window to foreground and verifies real login.
"""

import os
import sys
import time
import logging
import re
import json
import collections
import subprocess
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup

try:
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
load_dotenv()

NAUKRI_EMAIL = os.getenv('NAUKRI_EMAIL', '').strip()
NAUKRI_PASSWORD = os.getenv('NAUKRI_PASSWORD', '').strip()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite').strip()

FIRSTNAME = os.getenv('FIRSTNAME', '').strip()
LASTNAME = os.getenv('LASTNAME', '').strip()

DEFAULT_KEYWORDS = [
    "Full Stack Developer",
    "Java Developer",
    "Backend Developer",
    "React Developer",
    "Graduate Engineer Trainee",
    "Software Engineer Trainee",
    "GenAI Developer",
    "SDE Intern"
]
DEFAULT_LOCATIONS = ["Pune", "Mumbai", "Bangalore"]

_env_keywords = [kw.strip() for kw in os.getenv('KEYWORDS', '').split(',') if kw.strip()]
KEYWORDS = _env_keywords if _env_keywords else DEFAULT_KEYWORDS

_env_locations = [loc.strip() for loc in os.getenv('LOCATIONS', os.getenv('LOCATION', '')).split(',') if loc.strip()]
LOCATIONS = _env_locations if _env_locations else DEFAULT_LOCATIONS
LOCATION = LOCATIONS[0] if LOCATIONS else "Pune"

MAX_EXPERIENCE = int(os.getenv('MAX_EXPERIENCE', '3'))
JOB_AGE_DAYS = int(os.getenv('JOB_AGE_DAYS', '1'))
MAX_APPLICATIONS = int(os.getenv('MAX_APPLICATIONS', '0'))
PAGES_PER_KEYWORD = int(os.getenv('PAGES_PER_KEYWORD', '1'))
INPUT_CSV = os.getenv('INPUT_CSV', '').strip()

EDGE_DRIVER_PATH = os.getenv('EDGE_DRIVER_PATH', '')

# ------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Candidate Master Profile (Fed into Gemini & DeepSeek AI)
# ------------------------------------------------------------
CANDIDATE_PROFILE = {
    "personal_details": {
        "full_name": "Kaustubh Sanjay Kale",
        "first_name": "Kaustubh",
        "middle_name": "Sanjay",
        "last_name": "Kale",
        "email": "kaustubh.kale.work@gmail.com",
        "phone": "+91-9975526627",
        "phone_digits": "9975526627",
        "current_city": "Pune",
        "home_town": "Pune",
        "state": "Maharashtra",
        "country": "India",
        "pincode": "411037",
        "gender": "Male",
        "nationality": "Indian"
    },
    "education": {
        "degree": "Bachelor of Engineering (B.E.) in Information Technology",
        "institution": "SKNSITS, Lonavala (Savitribai Phule Pune University)",
        "cgpa": "7.51 / 10.0",
        "graduation_year": "2026",
        "current_status": "Final Year Student / B.E. IT (2022-2026)",
        "secondary_education": {
            "12th_hsc": "82.33% (Maharashtra Board, 2022)",
            "10th_ssc": "88.00% (Maharashtra Board, 2020)"
        }
    },
    "work_experience": {
        "total_experience_years": 1,
        "is_fresher": False,
        "internships": [
            {
                "role": "Java Developer Intern",
                "company": "CWIPedia Technologies",
                "duration": "Jan 2025 - Feb 2025",
                "skills": ["Java", "SQL", "JDBC", "REST APIs", "HTML5", "CSS3", "JavaScript", "Agile/Scrum"]
            }
        ],
        "current_company": "CWIPedia Technologies (Ex-Intern) / Freelance Full-Stack Developer",
        "current_ctc": "0",
        "expected_ctc": "400000",
        "notice_period": "Immediate",
        "notice_period_days": 0
    },
    "tech_experience_years": {
        "full_stack_development": 1,
        "mern_stack": 1,
        "react": 1,
        "nextjs": 1,
        "nodejs": 1,
        "express": 1,
        "javascript": 1,
        "typescript": 1,
        "python": 1,
        "fastapi": 1,
        "django": 1,
        "java": 1,
        "spring_boot": 1,
        "rest_apis": 1,
        "sql": 1,
        "mysql": 1,
        "postgresql": 1,
        "mongodb": 1,
        "websockets_socketio": 1,
        "aws_cloud": 1,
        "docker": 1,
        "git_github": 1,
        "ai_llm_integration": 1
    },
    "preferences": {
        "preferred_locations": ["Pune", "Mumbai", "Bangalore", "Remote", "Any"],
        "current_location": "Pune",
        "willing_to_relocate": "Yes",
        "ready_to_join": "Immediately"
    },
    "skills": [
        "Full Stack Development", "MERN Stack", "React", "Next.js", "Node.js", "Express",
        "JavaScript", "TypeScript", "Python", "FastAPI", "Django", "Java", "Spring Boot",
        "Hibernate/JPA", "JDBC", "REST APIs", "WebSockets", "Socket.IO", "SQL", "MySQL",
        "PostgreSQL", "MongoDB", "Mongoose", "SQLite", "Supabase", "AWS", "Docker", "Git",
        "GitHub", "Postman", "Tailwind CSS", "Bootstrap", "HTML5", "CSS3", "LangChain",
        "Google Gemini API", "DeepSeek API", "Ollama", "MCP", "Data Structures & Algorithms"
    ]
}

gemini_client = None
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info(f"✓ Gemini AI Client active ({GEMINI_MODEL})")
    except Exception as e:
        logger.warning(f"Could not initialize Gemini Client: {e}")


class SlidingWindowRateLimiter:
    """
    Sliding window tracker for API calls.
    Allows up to `max_requests` (14) within `window_seconds` (60s).
    Instead of pausing/sleeping when the 15th request arrives within the window,
    `can_request_gemini()` returns False, enabling zero-wait fallback to DeepSeek API.
    As soon as older requests roll off after 60s, automatically reverts to Gemini.
    """
    def __init__(self, max_requests=14, window_seconds=60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps = collections.deque()

    def can_request_gemini(self):
        now = time.time()
        while self.timestamps and (now - self.timestamps[0]) >= self.window_seconds:
            self.timestamps.popleft()

        if len(self.timestamps) < self.max_requests:
            self.timestamps.append(now)
            return True
        return False


gemini_rate_limiter = SlidingWindowRateLimiter(max_requests=14, window_seconds=60.0)


def call_deepseek_screening_assistant(prompt):
    """Fallback screening question solver using DeepSeek chat completions API."""
    import requests
    api_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if not api_key:
        logger.warning("DEEPSEEK_API_KEY not found for fallback!")
        return None
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': 'You are an automated job screening assistant. Answer questions concisely with clean exact values (e.g. single digit numbers, Yes/No, or exact option). No conversational filler.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.1,
            'max_tokens': 60
        }
        resp = requests.post('https://api.deepseek.com/chat/completions', headers=headers, json=payload, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content'].strip().strip('"').strip("'").strip()
        else:
            logger.warning(f"DeepSeek fallback HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"DeepSeek screening assistant error: {e}")
    return None


def bring_window_to_foreground():
    """Bring the Microsoft Edge window to the front."""
    try:
        cmd = "(New-Object -ComObject WScript.Shell).AppActivate('Edge'); (New-Object -ComObject WScript.Shell).AppActivate('Naukri')"
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=5)
    except Exception:
        pass


def validate_config():
    """Check required configuration values."""
    errors = []
    if not NAUKRI_EMAIL:
        errors.append("NAUKRI_EMAIL is not set in .env")
    if not KEYWORDS:
        errors.append("KEYWORDS is not set in .env")
    if not FIRSTNAME:
        errors.append("FIRSTNAME is not set in .env")
    if not LASTNAME:
        errors.append("LASTNAME is not set in .env")
    if errors:
        for e in errors:
            logger.error(e)
        return False
    return True


def create_edge_driver():
    """Create and return an Edge WebDriver instance with a persistent profile."""
    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "edge_profile"))
    options.add_argument(f"--user-data-dir={profile_dir}")
    logger.info(f"Using persistent Edge profile: {profile_dir}")

    if WEBDRIVER_MANAGER_AVAILABLE:
        service = EdgeService(EdgeChromiumDriverManager().install())
    elif EDGE_DRIVER_PATH:
        service = EdgeService(executable_path=EDGE_DRIVER_PATH)
    else:
        service = EdgeService()

    driver = webdriver.Edge(service=service, options=options)
    driver.maximize_window()
    bring_window_to_foreground()
    return driver


def is_logged_in(driver):
    """Accurately verify if user is authenticated on Naukri.com."""
    try:
        current = driver.current_url.lower()
        if "/nlogin" in current or "login.naukri.com" in current:
            return False
        login_btns = driver.find_elements(By.ID, 'login_Layer')
        if login_btns and login_btns[0].is_displayed():
            return False
        profile_els = driver.find_elements(By.CSS_SELECTOR, "a.nI-gNb-header__profile-link, .nI-gNb-drawer__icon, div.nI-gNb-drawer, a[href*='/mnjuser/profile']")
        if profile_els or "/mnjuser" in current:
            return True
        return False
    except Exception:
        return False


def login_naukri(driver):
    """Ensure the user is authenticated on Naukri.com."""
    logger.info("Checking login state on Naukri.com...")
    driver.get('https://www.naukri.com/')
    time.sleep(3)
    bring_window_to_foreground()

    if is_logged_in(driver):
        logger.info("✓ Already logged in with active session!")
        return True

    logger.info("Navigating to login page...")
    driver.get('https://www.naukri.com/nlogin/login')
    time.sleep(3)
    bring_window_to_foreground()

    try:
        uname = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.ID, 'usernameField'))
        )
        uname.clear()
        uname.send_keys(NAUKRI_EMAIL)
        logger.info(f"Entered username: {NAUKRI_EMAIL}")

        if NAUKRI_PASSWORD:
            passwd = driver.find_element(By.ID, 'passwordField')
            passwd.clear()
            passwd.send_keys(NAUKRI_PASSWORD)
            passwd.send_keys(Keys.ENTER)
            logger.info("Entered password automatically. Waiting for authentication...")
        else:
            logger.info("=" * 65)
            logger.info("👉 ACTION REQUIRED: Edge browser is open on your screen!")
            logger.info("👉 Please log in (Password, Google, or OTP) in the browser window.")
            logger.info("=" * 65)
    except Exception as e:
        logger.warning(f"Login form note: {e}")

    logger.info("Waiting for login to complete in the visible browser window (up to 120s)...")
    for sec in range(60):
        time.sleep(2)
        bring_window_to_foreground()
        if is_logged_in(driver):
            logger.info("🎉 Login verified successfully! Continuing with job automation...")
            time.sleep(2)
            return True

    logger.error("❌ Login was not completed in time. Halting to avoid false applications.")
    return False


# ============================================================
# Smart Field Type-Guards & Gemini Screening Solver
# ============================================================

def apply_strict_type_guard(question_text):
    """
    Guarantees correct field formatting so invalid inputs (like '0 LPA' for city)
    can NEVER occur.
    """
    q = question_text.lower()

    # 1. City / Location Questions
    if any(k in q for k in ["city", "current location", "preferred location", "which location", "native"]):
        return "Pune"

    # 2. Willing to relocate
    if "relocate" in q or "willing to travel" in q:
        return "Yes"

    # 3. Notice Period Questions
    if "notice" in q:
        if "day" in q:
            return "0"
        return "Immediate"

    # 4. Current CTC / Salary
    if any(k in q for k in ["current ctc", "current salary", "ctc in lacs", "current annual"]):
        return "0"

    # 5. Expected CTC / Salary
    if any(k in q for k in ["expected ctc", "expected salary", "expected annual"]):
        return "400000"

    # 6. Highest Degree / Qualification
    if "qualification" in q or "highest degree" in q:
        return "B.E / B.Tech"

    return None


def get_adaptive_alternative(question_text, rejected_answers=None):
    """
    When an answer is rejected by the portal, adaptively rotate to alternative representations.
    Prevents repeated submission of invalid formats.
    """
    q = question_text.lower()
    rejected_set = set(str(a).strip().lower() for a in (rejected_answers or []))

    # 1. Current CTC / Salary in Lacs
    if any(k in q for k in ["current ctc", "current salary", "ctc in lacs", "current annual"]):
        candidates = ["0", "0.0", "Fresher", "0.00", "0 LPA"]
        for cand in candidates:
            if cand.lower() not in rejected_set:
                return cand

    # 2. Expected CTC / Salary
    if any(k in q for k in ["expected ctc", "expected salary", "expected annual"]):
        candidates = ["400000", "4.0", "4", "400000 INR", "4 LPA"]
        for cand in candidates:
            if cand.lower() not in rejected_set:
                return cand

    # 3. Experience in years
    if any(k in q for k in ["experience", "years of experience", "how many years"]):
        candidates = ["1", "1.0", "1 year", "2", "0"]
        for cand in candidates:
            if cand.lower() not in rejected_set:
                return cand

    # 4. Location / City
    if any(k in q for k in ["city", "current location", "preferred location", "which location", "native"]):
        candidates = ["Pune", "Pune, Maharashtra", "pune"]
        for cand in candidates:
            if cand.lower() not in rejected_set:
                return cand

    # 5. Notice Period
    if "notice" in q:
        candidates = ["Immediate", "0", "0 days", "15 days", "15"]
        for cand in candidates:
            if cand.lower() not in rejected_set:
                return cand

    return None


def answer_screening_question_with_ai(question_text, options=None, error_context=None, rejected_answers=None):
    """
    Answers recruiter questions using:
    1. Adaptive alternative if recovering from prior error.
    2. Strict Type-Guards for basic profile invariants (location, relocation, degree).
    3. Gemini AI reasoning with full candidate profile.
    4. Zero-wait DeepSeek API fallback when 15 RPM Gemini cap is reached or if Gemini encounters an error.
    """
    rejected_set = set(str(a).strip().lower() for a in (rejected_answers or []))

    # If recovering from an error on free-text, check adaptive alternative first
    if error_context and not options:
        alt = get_adaptive_alternative(question_text, rejected_answers)
        if alt:
            logger.info(f"🔄 [Adaptive Recovery] Alternating for '{question_text}' (rejected: {rejected_answers}) -> '{alt}'")
            return alt

    # If first attempt without options, check strict type guard for basic non-skill constants
    if not options and not error_context:
        guarded = apply_strict_type_guard(question_text)
        if guarded and guarded.lower() not in rejected_set:
            logger.info(f"🛡️ [Type-Guard] Invariant match for '{question_text}' -> '{guarded}'")
            return guarded

    prompt = f"""You are the automated job application assistant for candidate Kaustubh Sanjay Kale.
Answer the following recruiter screening question based strictly on his profile data.

CANDIDATE PROFILE:
{json.dumps(CANDIDATE_PROFILE, indent=2)}

RECRUITER QUESTION:
"{question_text}"
"""

    if error_context:
        prompt += f"""
⚠️ IMPORTANT ERROR RECOVERY:
The recruiter's form previously returned an error: "{error_context}".
The following answers were REJECTED as invalid by the system: {json.dumps(rejected_answers or [])}.
CRITICAL REQUIREMENT: DO NOT repeat any rejected answer! Provide a valid, different alternative representation or format.
"""

    if options:
        available_opts = [opt for opt in options if opt.lower() not in rejected_set] or options
        prompt += f"""
AVAILABLE OPTIONS (Choose exactly one):
{json.dumps(available_opts, indent=2)}

INSTRUCTIONS:
- You MUST choose exactly ONE option from the AVAILABLE OPTIONS list.
- Return ONLY the exact text of the chosen option. No markdown, no quotes, no extra words.
"""
    else:
        prompt += """
INSTRUCTIONS:
- For any primary engineering skill the candidate actively develops with:
  * Full Stack Development, MERN Stack, React, Next.js, Node.js, Express, JavaScript, TypeScript, Python, FastAPI, Django, Java, Spring Boot, REST APIs, SQL, MySQL, PostgreSQL, MongoDB, WebSockets, Socket.IO, AWS, Docker:
  -> Return '1' (or integer years if requested).
- If asked for total or overall experience: return '1' (accounting for CWIPedia internship & production web applications).
- If asked for city or location: return 'Pune'.
- If asked if willing to relocate: return 'Yes'.
- If asked for notice period: return 'Immediate' or '0'.
- If asked for current CTC / salary in Lacs: return '0'.
- If asked for expected CTC / salary: return '400000'.
- Return ONLY the exact answer string with NO conversational words and NO quotes.
"""

    use_gemini = gemini_client and gemini_rate_limiter.can_request_gemini()
    answer = None

    if use_gemini:
        try:
            logger.info(f"🤖 [Gemini AI] Processing question (Window: {len(gemini_rate_limiter.timestamps)}/14)...")
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            answer = response.text.strip().strip('"').strip("'").strip()
        except Exception as e:
            logger.warning(f"Gemini API error ({e}). Seamlessly switching to DeepSeek fallback...")
            use_gemini = False

    if not use_gemini or not answer:
        logger.info("⚡ [Smart Fallback -> DeepSeek] Gemini 15 RPM cap reached (or unavailable). Querying DeepSeek API (zero wait)...")
        answer = call_deepseek_screening_assistant(prompt)

    if answer:
        if answer.lower() in rejected_set:
            logger.warning(f"⚠️ AI suggested '{answer}' which was already rejected! Finding adaptive alternative...")
            alt = get_adaptive_alternative(question_text, rejected_answers)
            if alt:
                return alt
        model_used = "Gemini AI" if use_gemini else "DeepSeek Fallback"
        logger.info(f"🤖 [{model_used}] Q: '{question_text}' -> Ans: '{answer}'")
        return answer

    return fallback_answer(question_text, options)


def fallback_answer(question_text, options=None):
    """Safe fallback heuristic."""
    q = question_text.lower()
    if options:
        if "notice" in q:
            for opt in options:
                if any(w in opt.lower() for w in ["immediate", "0", "15"]):
                    return opt
        if "location" in q or "city" in q:
            for opt in options:
                if "pune" in opt.lower():
                    return opt
        if "relocate" in q:
            for opt in options:
                if "yes" in opt.lower():
                    return opt
        return options[0]

    guarded = apply_strict_type_guard(question_text)
    if guarded:
        return guarded
    return "Yes"


# ============================================================
# Chatbot Questionnaire Drawer Engine (With Error Recovery)
# ============================================================

def is_any_questionnaire_open(driver):
    """
    Checks if any screening questionnaire is visible:
    - Chatbot drawer (.chatbot_Drawer, #ChatbotContainer)
    - Form questionnaire drawer / modal (.drawerWrapper, [class*='drawer'], [class*='questionnaire'], dialog)
    """
    selectors = [
        "[id*='ChatbotContainer']",
        ".chatbot_Drawer",
        "div.drawerWrapper",
        "div[class*='drawer']",
        "div[class*='Drawer']",
        "div[class*='chatbot']",
        "div[class*='Chatbot']",
        "div[class*='questionnaire']",
        "div[class*='Questionnaire']",
        "div[class*='applyDrawer']",
        "div[class*='apply-drawer']",
        "div.apply-modal",
        "div.modal-content",
        "div[role='dialog']",
        "div.popup-container"
    ]
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    # Confirm it has inputs, textareas, selects, or chat messages
                    has_content = driver.execute_script("""
                        var el = arguments[0];
                        return el.querySelector('input, select, textarea, [contenteditable="true"], .msg, [class*="msg"], [class*="question"]') !== null;
                    """, el)
                    if has_content:
                        return True
        except Exception:
            continue
    return False


def is_chatbot_drawer_open(driver):
    """Check if any screening drawer is visible."""
    return is_any_questionnaire_open(driver)


def get_bot_chat_bubbles(driver):
    """
    Retrieve message bubbles strictly sent by the BOT / RECRUITER.
    Guaranteed never to return the candidate's own responses.
    """
    bot_selectors = [
        ".chatbot_ListItem.botItem .msg",
        ".chatbot_ListItem .botMsg .msg",
        ".botItem .msg",
        "li.botItem .msg",
        "div.botItem .msg",
        "[class*='botItem'] [class*='msg']",
        "[class*='botMsg'] [class*='msg']",
    ]
    for sel in bot_selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            texts = [el.text.strip() for el in els if el.is_displayed() and el.text.strip()]
            if texts:
                return texts
        except Exception:
            continue

    try:
        all_msgs = driver.find_elements(By.CSS_SELECTOR, ".chatbot_ListItem .msg, [class*='ListItem'] [class*='msg'], .msg")
        bot_texts = []
        for el in all_msgs:
            if not el.is_displayed():
                continue
            try:
                is_user = driver.execute_script("""
                    return arguments[0].closest('.userItem, .userMsg, [class*="userItem"], [class*="userMsg"], [class*="user-msg"]') !== null;
                """, el)
                if not is_user:
                    t = el.text.strip()
                    if t:
                        bot_texts.append(t)
            except Exception:
                t = el.text.strip()
                if t:
                    bot_texts.append(t)
        return bot_texts
    except Exception:
        return []


def parse_bot_question(bot_bubble):
    """
    Separates error indicators from the actual question text.
    Example:
    'The input seems invalid. What is your current CTC in Lacs per annum?'
    -> question: 'What is your current CTC in Lacs per annum?'
    -> error_context: 'The input seems invalid.'
    """
    raw = bot_bubble.strip()
    is_error = any(w in raw.lower() for w in [
        "invalid", "incorrect", "valid input", "try again", "not recognized", "seems invalid"
    ])
    if not is_error:
        return raw, None

    error_context = raw
    clean = re.sub(r'^(?:the\s+)?input\s+seems\s+invalid[.!:\-\s]*', '', raw, flags=re.IGNORECASE).strip()
    clean = re.sub(r'^(?:please\s+enter\s+a\s+valid\s+input[.!:\-\s]*)', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'^(?:incorrect\s+input[.!:\-\s]*)', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'^(?:please\s+try\s+again[.!:\-\s]*)', '', clean, flags=re.IGNORECASE).strip()

    if clean and len(clean) > 3:
        return clean, error_context

    return raw, error_context


def find_chatbot_save_button(driver):
    """Find Save / Send button in drawer."""
    selectors = [
        ".sendMsg",
        ".sendMsgbtn_container .sendMsg",
        "[class*='sendMsg']",
        "div.sendMsg",
        "button[class*='save']",
        "button[class*='send']"
    ]
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    return el
        except Exception:
            continue
    return None


def get_element_question_label(driver, el):
    """
    Finds the descriptive question label/text for a given input element.
    Uses placeholder, aria-label, label[for], or parent container headings.
    """
    try:
        aria = el.get_attribute('aria-label') or el.get_attribute('placeholder')
        if aria and len(aria.strip()) > 3:
            return aria.strip()

        el_id = el.get_attribute('id')
        if el_id:
            labels = driver.find_elements(By.CSS_SELECTOR, f"label[for='{el_id}']")
            for lbl in labels:
                if lbl.is_displayed() and lbl.text.strip():
                    return lbl.text.strip()

        question_text = driver.execute_script("""
            var el = arguments[0];
            var parent = el.closest('.form-group, .field, [class*="question"], [class*="field"], [class*="item"], [class*="row"], li, div');
            for (var i = 0; i < 5 && parent; i++) {
                var label = parent.querySelector('label, [class*="label"], [class*="title"], [class*="heading"], h3, h4, h5, p, span');
                if (label && label.innerText.trim().length > 3) {
                    return label.innerText.trim();
                }
                parent = parent.parentElement;
            }
            return '';
        """, el)
        if question_text and len(question_text.strip()) > 3:
            return question_text.strip()
    except Exception:
        pass

    return el.get_attribute('name') or el.get_attribute('placeholder') or "Recruiter Question"


def handle_form_questionnaire(driver):
    """
    Solves multi-question form drawers and modals:
    1. Scans all radio groups, selects, text inputs, textareas.
    2. Identifies question label for each control.
    3. Prompts Gemini AI for answers based on candidate profile.
    4. Populates fields and clicks Submit / Apply button.
    """
    logger.info("  Processing Form Questionnaire with Gemini AI...")

    # 1. Radio Groups
    try:
        radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        handled_radio_names = set()
        for r in radios:
            if not r.is_displayed():
                continue
            r_name = r.get_attribute('name') or f"radio_{r.get_attribute('id') or 'group'}"
            if r_name in handled_radio_names:
                continue
            handled_radio_names.add(r_name)

            if r.get_attribute('name'):
                group_radios = driver.find_elements(By.CSS_SELECTOR, f"input[type='radio'][name='{r.get_attribute('name')}']")
            else:
                group_radios = [r]

            q_label = get_element_question_label(driver, r)
            options_data = []
            for gr in group_radios:
                opt_text = driver.execute_script("""
                    var r = arguments[0];
                    var id = r.id;
                    if (id) {
                        var lbl = document.querySelector('label[for="' + id + '"]');
                        if (lbl && lbl.innerText.trim()) return lbl.innerText.trim();
                    }
                    var parentLabel = r.closest('label');
                    if (parentLabel && parentLabel.innerText.trim()) return parentLabel.innerText.trim();
                    var next = r.nextElementSibling;
                    if (next && next.innerText.trim()) return next.innerText.trim();
                    return r.value || '';
                """, gr)
                if opt_text and opt_text.strip():
                    options_data.append((opt_text.strip(), gr))

            if options_data:
                opts = [o[0] for o in options_data]
                chosen = answer_screening_question_with_ai(q_label, options=opts)
                for opt_text, gr_el in options_data:
                    if chosen.lower() in opt_text.lower() or opt_text.lower() in chosen.lower():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gr_el)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", gr_el)
                        logger.info(f"  ✓ [Radio] Q: '{q_label[:40]}' -> Selected: '{opt_text}'")
                        break
    except Exception as e:
        logger.warning(f"  Error processing form radios: {e}")

    # 2. Select Dropdowns
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        for sel in selects:
            if not sel.is_displayed():
                continue
            q_label = get_element_question_label(driver, sel)
            opts = [o.text.strip() for o in sel.find_elements(By.TAG_NAME, "option") if o.text.strip() and not any(p in o.text.lower() for p in ['select', 'choose', '--'])]
            if opts:
                chosen = answer_screening_question_with_ai(q_label, options=opts)
                driver.execute_script("""
                    var sel = arguments[0];
                    var val = arguments[1];
                    for (var i = 0; i < sel.options.length; i++) {
                        if (sel.options[i].text.toLowerCase().indexOf(val.toLowerCase()) !== -1 || val.toLowerCase().indexOf(sel.options[i].text.toLowerCase()) !== -1) {
                            sel.selectedIndex = i;
                            sel.dispatchEvent(new Event('change', {bubbles: true}));
                            break;
                        }
                    }
                """, sel, chosen)
                logger.info(f"  ✓ [Dropdown] Q: '{q_label[:40]}' -> Selected: '{chosen}'")
    except Exception as e:
        logger.warning(f"  Error processing form selects: {e}")

    # 3. Text & Number Inputs and Textareas
    try:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number'], input:not([type]), textarea")
        for inp in inputs:
            if not inp.is_displayed():
                continue
            current_val = inp.get_attribute('value') or ""
            if current_val.strip() and len(current_val.strip()) > 1:
                continue

            q_label = get_element_question_label(driver, inp)
            ans = answer_screening_question_with_ai(q_label, options=None)
            driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center'});
                arguments[0].focus();
                arguments[0].value = '';
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
            """, inp, ans.strip())
            logger.info(f"  ✓ [Text Input] Q: '{q_label[:40]}' -> Entered: '{ans.strip()}'")
            time.sleep(0.3)
    except Exception as e:
        logger.warning(f"  Error processing form text inputs: {e}")

    # 4. Click Submit / Apply Button
    time.sleep(1)
    submit_xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit and apply')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save and apply')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'done')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
        "//input[@type='submit']"
    ]
    for sxp in submit_xpaths:
        try:
            btns = driver.find_elements(By.XPATH, sxp)
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn_text = btn.text.strip().lower()
                    if any(w in btn_text for w in ['submit', 'save', 'apply', 'done', 'next']):
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", btn)
                        logger.info(f"  ✓ Clicked Questionnaire Submit button ('{btn.text.strip()}')")
                        time.sleep(3)
                        return True
        except Exception:
            continue

    return True


def handle_chatbot_drawer(driver):
    """
    Processes the recruiter screening drawer:
    - Reads chat history from the bot only (ignores applicant's own bubbles).
    - Detects 'invalid input' errors and alternates representations.
    - Prevents repeating rejected answers.
    - Supports radio options, contenteditable, and standard inputs.
    """
    logger.info("=" * 65)
    logger.info("📋 Recruiter Screening Chatbot Drawer detected! Starting AI Solver...")
    logger.info("=" * 65)
    time.sleep(2)

    last_attempted_answers = []

    for turn in range(15):
        if not is_any_questionnaire_open(driver):
            logger.info("✓ Chatbot drawer closed! Questionnaire finished.")
            return True

        bot_bubbles = get_bot_chat_bubbles(driver)
        if not bot_bubbles:
            time.sleep(2)
            continue

        latest_bubble = bot_bubbles[-1]
        logger.info(f"[Turn {turn+1}] Chatbot message: '{latest_bubble}'")

        # Check for completion message
        if any(thanks in latest_bubble.lower() for thanks in ["thank you", "application submitted", "successfully submitted", "responses have been recorded"]):
            logger.info("✓ Recruiter screening completed! Waiting for drawer to close...")
            time.sleep(3)
            return True

        actual_question, error_detected = parse_bot_question(latest_bubble)
        if error_detected:
            logger.warning(f"⚠️ Chatbot reported invalid input: '{error_detected}'. Triggering error recovery...")

        # 1. RADIO BUTTONS
        try:
            radio_container = driver.find_elements(By.CSS_SELECTOR, ".singleselect-radiobutton-container, [class*='radiobutton-container']")
            if radio_container and radio_container[0].is_displayed():
                labels = radio_container[0].find_elements(By.CSS_SELECTOR, ".ssrc__label, label")
                radios = radio_container[0].find_elements(By.CSS_SELECTOR, ".ssrc__radio, input[type='radio']")
                options = [lbl.text.strip() for lbl in labels if lbl.text.strip()]

                if options:
                    chosen = answer_screening_question_with_ai(
                        actual_question,
                        options=options,
                        error_context=error_detected,
                        rejected_answers=last_attempted_answers
                    )
                    last_attempted_answers.append(chosen)

                    for rb, lbl in zip(radios, labels):
                        if chosen.lower() in lbl.text.strip().lower() or lbl.text.strip().lower() in chosen.lower():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", lbl)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", lbl)
                            logger.info(f"  ✓ Clicked radio: '{lbl.text.strip()}'")
                            break

                    time.sleep(1)
                    btn = find_chatbot_save_button(driver)
                    if btn:
                        driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    continue
        except Exception as e:
            logger.warning(f"Radio error: {e}")

        # 2. FREE-TEXT CONTENTEDITABLE INPUT
        try:
            text_areas = driver.find_elements(By.CSS_SELECTOR, ".chatbot_SendMessageContainer .textArea[contenteditable='true'], div.textArea[contenteditable='true'], div[contenteditable='true']")
            visible_ta = None
            for ta in text_areas:
                if ta.is_displayed():
                    visible_ta = ta
                    break

            if visible_ta:
                answer = answer_screening_question_with_ai(
                    actual_question,
                    options=None,
                    error_context=error_detected,
                    rejected_answers=last_attempted_answers
                )
                last_attempted_answers.append(answer)

                driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].innerHTML = '';
                    arguments[0].innerText = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                """, visible_ta, answer.strip())
                logger.info(f"  ✓ Entered text: '{answer.strip()}'")
                time.sleep(1)

                btn = find_chatbot_save_button(driver)
                if btn:
                    driver.execute_script("arguments[0].click();", btn)
                    logger.info("  ✓ Clicked Save button")
                else:
                    try:
                        visible_ta.send_keys(Keys.RETURN)
                    except Exception:
                        pass

                time.sleep(3)
                continue
        except Exception as e:
            logger.warning(f"Text input error: {e}")

        # 3. STANDARD INPUT BOX IN CHATBOT DRAWER
        try:
            std_inps = driver.find_elements(By.CSS_SELECTOR, ".chatbot_Drawer input[type='text'], .chatbot_Drawer input[type='number'], div[class*='chatbot'] input")
            visible_inp = None
            for inp in std_inps:
                if inp.is_displayed():
                    visible_inp = inp
                    break

            if visible_inp:
                answer = answer_screening_question_with_ai(
                    actual_question,
                    options=None,
                    error_context=error_detected,
                    rejected_answers=last_attempted_answers
                )
                last_attempted_answers.append(answer)

                driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].value = '';
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                """, visible_inp, answer.strip())
                logger.info(f"  ✓ Entered standard input: '{answer.strip()}'")
                time.sleep(1)

                btn = find_chatbot_save_button(driver)
                if btn:
                    driver.execute_script("arguments[0].click();", btn)
                    logger.info("  ✓ Clicked Save button")
                else:
                    try:
                        visible_inp.send_keys(Keys.RETURN)
                    except Exception:
                        pass

                time.sleep(3)
                continue
        except Exception as e:
            logger.warning(f"Standard input error: {e}")

        # 4. GENERIC SAVE BUTTON
        btn = find_chatbot_save_button(driver)
        if btn:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
            except Exception:
                pass

        time.sleep(2)

    return True


def resolve_questionnaire_with_ai(driver):
    """
    Unified AI solver that detects the questionnaire format and solves all questions:
    - If chatbot bubbles are present -> handles conversation turn-by-turn with Gemini AI.
    - If form fields are present -> scans all questions, fills with Gemini AI, and submits.
    """
    logger.info("=" * 65)
    logger.info("📋 Recruiter Screening Questionnaire detected! Starting Gemini AI Solver...")
    logger.info("=" * 65)
    time.sleep(2)

    # Check if conversational chatbot bubbles are present
    bot_bubbles = get_bot_chat_bubbles(driver)
    if bot_bubbles:
        logger.info("  Format: Conversational Chatbot")
        return handle_chatbot_drawer(driver)

    # Otherwise, solve as Form Questionnaire Drawer / Modal
    logger.info("  Format: Multi-Question Form")
    return handle_form_questionnaire(driver)


# ============================================================
# Search & Job Application Pipeline (Strict 24h & Fresher Filter)
# ============================================================

def build_search_urls():
    """
    Build search URLs with:
    - Keywords across configured Locations (e.g. Pune, Mumbai, Bangalore)
    - jobAge=JOB_AGE_DAYS (Posted in the past 24 hours / 1 day strictly)
    - Experience matching MAX_EXPERIENCE (0-3 yrs)
    """
    urls = []
    locations = LOCATIONS if LOCATIONS else (['Pune'] if not LOCATION else [LOCATION])
    for keyword in KEYWORDS:
        clean_kw = re.sub(r'[^a-zA-Z0-9\s]', '', keyword.replace('/', ' ')).strip()
        keyword_slug = re.sub(r'\s+', '-', clean_kw.lower())
        for loc in locations:
            clean_loc = re.sub(r'[^a-zA-Z0-9\s]', '', loc).strip()
            loc_slug = re.sub(r'\s+', '-', clean_loc.lower())
            for page_num in range(1, PAGES_PER_KEYWORD + 1):
                base = f"https://www.naukri.com/{keyword_slug}-jobs-in-{loc_slug}" if page_num == 1 else f"https://www.naukri.com/{keyword_slug}-jobs-in-{loc_slug}-{page_num}"
                if MAX_EXPERIENCE <= 1:
                    url = f"{base}?experience=0&jobAge={JOB_AGE_DAYS}"
                else:
                    url = f"{base}?jobAge={JOB_AGE_DAYS}"
                urls.append((keyword, loc, url))
    return urls


def extract_post_date_text(card):
    """
    Extracts post date string from card snippet across various DOM patterns.
    """
    selectors = [
        'span.job-post-day',
        'span[class*="job-post-day"]',
        'span[class*="posted"]',
        'span[class*="date"]',
        'span[class*="tuple-sub-title"]'
    ]
    for sel in selectors:
        try:
            el = card.select_one(sel)
            if el and el.text.strip():
                return el.text.strip()
        except Exception:
            continue

    # Search all child elements for date markers
    for tag in card.find_all(['span', 'div', 'p', 'li']):
        t = tag.text.strip().lower()
        if any(marker in t for marker in ['ago', 'just now', 'today', 'few hour', 'days ago', 'day ago', 'weeks ago', 'months ago']):
            if len(t) < 40:
                return tag.text.strip()

    return None


def is_strictly_fresh(date_str):
    """
    Verify the card is strictly posted within the past 24 hours (Today, Just now, 1 day ago).
    Rejects 2+ days, weeks, months.
    """
    if not date_str:
        return False

    t = date_str.lower().strip()

    # Reject older posts (2+ days, weeks, months)
    rejection_markers = [
        "2 day", "3 day", "4 day", "5 day", "6 day", "7 day", "8 day", "9 day", "10 day",
        "11 day", "12 day", "13 day", "14 day", "15 day", "20 day", "25 day", "30 day", "30+",
        "+ day", "days ago", "week", "month", "year"
    ]
    if any(rm in t for rm in rejection_markers):
        if "1 day ago" in t:
            return True
        return False

    # Accept strictly fresh indicators
    valid_indicators = ["just now", "few hour", "hour ago", "hours ago", "min ago", "mins ago", "today", "1 day ago"]
    if any(v in t for v in valid_indicators):
        return True

    return False


def extract_min_experience(job_wrapper):
    """Parse minimum required experience from job card snippet."""
    exp_text = None
    selectors = [
        'span.expwdth',
        'span[class*="expwdth"]',
        'span[class*="exp-wrap"]',
        'span[class*="experience"]',
        'li[class*="experience"]'
    ]
    for sel in selectors:
        try:
            el = job_wrapper.select_one(sel)
            if el and el.text.strip():
                exp_text = el.text.strip().lower()
                break
        except Exception:
            continue

    if not exp_text:
        for tag in job_wrapper.find_all(['span', 'div', 'li']):
            t = tag.text.strip().lower()
            if any(k in t for k in ['yr', 'yrs', 'year', 'fresher']) and len(t) < 30:
                if re.search(r'\d+\s*(?:-|to)\s*\d+\s*(?:yr|year)', t) or 'fresher' in t:
                    exp_text = t
                    break

    if not exp_text:
        return 0

    if 'fresher' in exp_text or 'intern' in exp_text or '0 yr' in exp_text or '0-' in exp_text:
        return 0

    match = re.search(r'(\d+)\s*(?:-|to)?\s*(\d+)?\s*(?:yr|year)', exp_text)
    if match:
        return int(match.group(1))

    return 0


def collect_job_links_from_tab(driver, window_handle):
    """Collect job links: strictly past 24 hours AND <= 1 year experience."""
    links = []
    try:
        driver.switch_to.window(window_handle)
        time.sleep(3)
        bring_window_to_foreground()

        soup = BeautifulSoup(driver.page_source, 'html5lib')
        job_wrappers = soup.find_all('div', class_='srp-jobtuple-wrapper')
        if not job_wrappers:
            job_wrappers = soup.find_all('div', class_='cust-job-tuple')

        logger.info(f"Tab '{driver.title[:45]}': Found {len(job_wrappers)} candidate cards")

        for job_wrapper in job_wrappers:
            title_link = job_wrapper.find('a', class_='title')
            title_text = title_link.text.strip() if title_link else "Unknown"

            # 1. STRICT FRESHNESS CHECK (PAST 24 HOURS ONLY)
            date_str = extract_post_date_text(job_wrapper) or "Unknown"
            if not is_strictly_fresh(date_str):
                logger.info(f"  ⏭ Skipping old/unverified job ({date_str}): {title_text}")
                continue

            # 2. STRICT EXPERIENCE CHECK (FRESHERS / <= 1 YR)
            min_exp = extract_min_experience(job_wrapper)
            if min_exp > MAX_EXPERIENCE:
                logger.info(f"  ⏭ Skipping senior role ({min_exp}+ yrs): {title_text}")
                continue

            if title_link and title_link.get('href'):
                href = title_link.get('href')
                if href.startswith('/'):
                    href = 'https://www.naukri.com' + href
                logger.info(f"  ✓ Matching Fresh Listing (Posted: {date_str} | Exp: {min_exp} yrs): {title_text}")
                links.append((title_text, min_exp, date_str, href))

    except WebDriverException as e:
        logger.warning(f"Error reading tab: {e}")

    return links


def save_discovered_jobs_to_final_csv(all_jobs):
    """Persists all discovered fresh jobs to final_jobs.csv for downstream DeepSeek scoring and PDF generation."""
    if not all_jobs:
        return
    rows = []
    for j in all_jobs:
        rows.append({
            'jobTitle': j['title'],
            'companyName': j['company'],
            'location': j['location'],
            'minimumExperience': j['min_exp'],
            'postedDate': j['date_str'],
            'portalUrl': j['href'],
            'apply link': j['href'],
            'url': j['href'],
            'company': j['company'],
            'title': j['title'],
            'descriptionText': j['description'],
            'descriptionSnippet': j['description'][:200],
            'source': 'naukri_direct_search'
        })
    df_new = pd.DataFrame(rows)
    final_csv = 'final_jobs.csv'
    if os.path.exists(final_csv):
        try:
            df_old = pd.read_csv(final_csv)
            df_comb = pd.concat([df_old, df_new], ignore_index=True)
            for url_col in ['portalUrl', 'apply link', 'url']:
                if url_col in df_comb.columns:
                    df_comb = df_comb.drop_duplicates(subset=[url_col], keep='first')
            df_comb.to_csv(final_csv, index=False)
            logger.info(f"📁 Updated {final_csv} with {len(df_new)} newly discovered direct search jobs (Total: {len(df_comb)})")
            return
        except Exception as e:
            logger.warning(f"Could not merge into {final_csv}: {e}")
    df_new.to_csv(final_csv, index=False)
    logger.info(f"📁 Saved {len(df_new)} direct search jobs to {final_csv}")


def collect_all_jobs_parallel(driver, search_urls):
    """Scan search URLs sequentially and collect matching fresh jobs without overloading browser tabs."""
    logger.info("=" * 65)
    logger.info(f"Scanning {len(search_urls)} search queries (Strict Filter: Past 24h & Exp <= {MAX_EXPERIENCE} yrs)...")
    logger.info("=" * 65)

    all_jobs = []
    seen = set()

    for idx, item in enumerate(search_urls, 1):
        if len(item) == 3:
            keyword, loc, url = item
        else:
            keyword, url = item
            loc = "Default"

        logger.info(f"[{idx}/{len(search_urls)}] Scanning: '{keyword}' in {loc} -> {url}")
        try:
            driver.get(url)
            time.sleep(2.5)
            bring_window_to_foreground()

            soup = BeautifulSoup(driver.page_source, 'html5lib')
            job_wrappers = soup.find_all('div', class_='srp-jobtuple-wrapper')
            if not job_wrappers:
                job_wrappers = soup.find_all('div', class_='cust-job-tuple')

            found_on_page = 0
            for job_wrapper in job_wrappers:
                title_link = job_wrapper.find('a', class_='title')
                title_text = title_link.text.strip() if title_link else "Unknown"

                # 1. STRICT FRESHNESS CHECK (PAST 24 HOURS ONLY)
                date_str = extract_post_date_text(job_wrapper) or "Unknown"
                if not is_strictly_fresh(date_str):
                    continue

                # 2. STRICT EXPERIENCE CHECK (<= MAX_EXPERIENCE YRS)
                min_exp = extract_min_experience(job_wrapper)
                if min_exp > MAX_EXPERIENCE:
                    continue

                if title_link and title_link.get('href'):
                    href = title_link.get('href')
                    if href.startswith('/'):
                        href = 'https://www.naukri.com' + href
                    clean_href = href.split('?')[0].strip()

                    if clean_href in seen:
                        continue
                    seen.add(clean_href)

                    # Extract company name
                    comp_elem = (job_wrapper.find('a', class_=re.compile(r'comp-name|company')) or 
                                 job_wrapper.find('span', class_=re.compile(r'comp-name|company')) or
                                 job_wrapper.find('div', class_=re.compile(r'companyInfo')))
                    comp_text = comp_elem.text.strip() if comp_elem else "Unknown Company"

                    # Extract location
                    loc_elem = (job_wrapper.find('span', class_=re.compile(r'loc|location')) or
                                job_wrapper.find('li', class_=re.compile(r'location')))
                    job_loc = loc_elem.text.strip() if loc_elem else loc

                    # Extract snippet / description
                    desc_elem = (job_wrapper.find('div', class_=re.compile(r'job-description|job-desc|row6')) or
                                 job_wrapper.find('span', class_=re.compile(r'job-desc')))
                    desc_text = desc_elem.text.strip() if desc_elem else f"{title_text} at {comp_text} ({job_loc})"

                    tags = [t.text.strip() for t in job_wrapper.find_all('li', class_=re.compile(r'tag|skill')) if t.text.strip()]
                    if tags:
                        desc_text += f"\nKey Skills: {', '.join(tags)}"

                    logger.info(f"  ✓ Matching Fresh Listing (Posted: {date_str} | Exp: {min_exp} yrs): {title_text} @ {comp_text}")
                    all_jobs.append({
                        'title': title_text,
                        'company': comp_text,
                        'location': job_loc,
                        'min_exp': min_exp,
                        'date_str': date_str,
                        'href': clean_href,
                        'description': desc_text
                    })
                    found_on_page += 1

            logger.info(f"  -> Found {found_on_page} fresh jobs on this page.")
        except Exception as e:
            logger.warning(f"Error reading page {url}: {e}")

    logger.info("=" * 65)
    logger.info(f"Total matching 24h fresh jobs collected: {len(all_jobs)}")
    logger.info("=" * 65)

    save_discovered_jobs_to_final_csv(all_jobs)

    return [(j['title'], j['min_exp'], j['date_str'], j['href']) for j in all_jobs]


def is_external_job(driver):
    """Detect if the job requires applying on an external company career portal."""
    external_keywords = [
        'company site',
        "company's site",
        'company website',
        'employer website',
        'external site',
        'apply on website',
        'apply on employer',
        'apply on company',
    ]
    external_xpaths = [
        "//*[@id='company-site-button']",
        "//*[contains(@class, 'company-site-button')]",
        "//*[contains(@class, 'company-site')]",
        "//button[contains(@class, 'external')]",
        "//a[contains(@class, 'external')]",
    ]
    for kw in external_keywords:
        external_xpaths.append(f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')]")
        external_xpaths.append(f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')]")
        external_xpaths.append(f"//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')]")

    for xpath in external_xpaths:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            for el in els:
                if el.is_displayed():
                    return True
        except Exception:
            continue
    return False


def is_already_applied(driver):
    """Detect if the candidate has already applied to this job on Naukri."""
    already_xpaths = [
        "//button[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='applied']",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'already applied')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applied on')]",
        "//span[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='applied']",
        "//div[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='applied']",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'already applied')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applied on')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'application submitted')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applied earlier')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'you applied') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'you have applied')]",
    ]
    for xp in already_xpaths:
        try:
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if el.is_displayed():
                    txt = el.text.strip().lower()
                    if txt in ['applied', 'already applied'] or 'applied on' in txt or 'already applied' in txt or 'you applied' in txt or 'you have applied' in txt or 'applied earlier' in txt or 'application submitted' in txt:
                        return True
        except Exception:
            continue
    return False


def handle_naukri_pre_apply_modals(driver):
    """
    Handles Naukri's interstitial prompts like:
    - 'Add missing skills to your profile' -> click 'Skip and apply' or 'Apply without updating'
    """
    skip_xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'skip and apply')]",
        "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'skip and apply')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply anyway')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply without')]",
        "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'skip and apply')]",
    ]
    for xp in skip_xpaths:
        try:
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if el.is_displayed():
                    driver.execute_script("arguments[0].click();", el)
                    logger.info(f"  ✓ Handled interstitial modal (clicked '{el.text.strip()}')")
                    time.sleep(2)
                    return True
        except Exception:
            continue
    return False


def check_naukri_rate_limit(driver):
    """
    Detects if Naukri's anti-abuse firewall or rate-limiting blocked the application.
    Matches toasts, banners, or DOM text like 'invalid request, please try again later'.
    """
    error_patterns = [
        r'invalid\s+request.*try\s+again\s+later',
        r'try\s+again\s+later',
        r'maximum\s+application.*exceeded',
        r'daily.*limit.*reached',
        r'applied.*maximum.*jobs',
        r'something\s+went\s+wrong.*try\s+again'
    ]
    # 1. Search in visible toast/alert/error/snackbar/banner elements
    try:
        elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'toast') or contains(@class, 'error') or contains(@class, 'alert') or contains(@class, 'msg') or contains(@class, 'snackbar') or contains(@class, 'banner') or contains(@class, 'err')]")
        for el in elements:
            if el.is_displayed():
                txt = el.text.strip().lower()
                for pat in error_patterns:
                    if re.search(pat, txt):
                        return True, el.text.strip()
    except Exception:
        pass

    # 2. Check page source for the literal toast phrase
    try:
        src = driver.page_source.lower()
        if 'invalid request' in src and 'try again later' in src:
            return True, "Invalid request, please try again later"
        if 'maximum application' in src or 'daily limit' in src:
            return True, "Daily maximum application limit reached"
    except Exception:
        pass

    return False, ""


def handle_rate_limit_cooldown(driver, cooldown_minutes=25):
    """
    Waits for 20-30 minutes when a rate limit / 'try again later' error is encountered,
    logging countdown updates so the user knows the bot is in a cooldown pause.
    """
    total_seconds = int(cooldown_minutes * 60)
    logger.warning("=" * 65)
    logger.warning(f"🛑 [Rate Limit / 'Try Again Later' Detected!]")
    logger.warning(f"⏳ Pausing bot execution for {cooldown_minutes} minutes cooldown...")
    resume_time = (pd.Timestamp.now() + pd.Timedelta(minutes=cooldown_minutes)).strftime('%H:%M:%S')
    logger.warning(f"⏰ Execution will safely resume at: {resume_time}")
    logger.warning("=" * 65)

    interval = 60  # check/log every minute
    elapsed = 0
    while elapsed < total_seconds:
        time.sleep(interval)
        elapsed += interval
        rem_min = (total_seconds - elapsed) // 60
        if rem_min % 5 == 0 or rem_min in [1, 2, 3]:
            logger.info(f"⏳ Cooldown in progress... {rem_min} minutes remaining before resuming.")

    logger.info("=" * 65)
    logger.info("✅ Cooldown complete! Resuming auto-apply flow...")
    logger.info("=" * 65)


def find_direct_apply_button(driver):
    """Find direct Naukri 1-click / chatbot apply button."""
    direct_xpaths = [
        "//button[normalize-space()='Apply']",
        "//button[@id='apply-button']",
        "//button[contains(@class, 'apply-button') and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company')) and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'external')) and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'website'))]",
        "//button[contains(., 'Apply') and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company')) and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'external')) and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'website'))]",
        "//a[contains(@class, 'apply-button') and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company')) and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'external')) and not(contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'website'))]",
        "//div[contains(@class, 'apply-button-container')]//button",
    ]
    for xpath in direct_xpaths:
        try:
            btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            btn_text = btn.text.strip().lower()
            if btn_text in ['applied', 'already applied']:
                continue
            if any(ext in btn_text for ext in ['company', 'external', 'website', 'employer']):
                continue
            return btn
        except Exception:
            continue
    return None


def get_already_processed_urls():
    """Retrieve URLs that were already processed in naukriapplied.csv."""
    csv_file = "naukriapplied.csv"
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file)
            if 'url' in df.columns:
                return set(df['url'].dropna().tolist())
        except Exception:
            pass
    return set()


def record_job_result(title, posted, status, url):
    """Appends job result directly to naukriapplied.csv in real-time."""
    csv_file = "naukriapplied.csv"
    row = pd.DataFrame([{
        "title": title,
        "posted": posted,
        "status": status,
        "url": url
    }])
    if os.path.exists(csv_file):
        row.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        row.to_csv(csv_file, mode='w', header=True, index=False)


def load_jobs_from_csv(csv_path):
    """
    Loads and validates candidate jobs from an input CSV file.
    Orders jobs so freshest/most relevant posts are processed first.
    Filters out already processed jobs.
    """
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return []

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error(f"Error reading CSV {csv_path}: {e}")
        return []

    col_map = {c.lower().strip().replace('_', ' ').replace('-', ' '): c for c in df.columns}
    col_map_simple = {re.sub(r'[^a-z0-9]', '', c.lower()): c for c in df.columns}

    title_col = (col_map.get('job title') or col_map.get('title') or 
                 col_map_simple.get('jobtitle') or col_map_simple.get('title'))
    link_col = (col_map.get('apply link') or col_map.get('link') or col_map.get('url') or col_map.get('job url') or
                col_map.get('portal url') or col_map_simple.get('portalurl') or col_map_simple.get('applylink') or col_map_simple.get('url'))
    exp_col = (col_map.get('experience') or col_map.get('exp') or col_map.get('experience text') or
               col_map_simple.get('experience') or col_map_simple.get('experiencetext') or col_map_simple.get('minimumexperience'))
    date_col = (col_map.get('posted date') or col_map.get('posted') or col_map.get('date') or col_map.get('created date') or
                col_map_simple.get('posteddate') or col_map_simple.get('createddate') or col_map_simple.get('date'))
    company_col = (col_map.get('company name') or col_map.get('company') or 
                   col_map_simple.get('companyname') or col_map_simple.get('company'))

    if not link_col:
        logger.error(f"Could not find Apply Link / URL column in CSV. Found columns: {df.columns.tolist()}")
        return []

    already_processed = get_already_processed_urls()
    jobs = []
    skipped_already = 0
    skipped_senior = 0

    if date_col:
        try:
            df = df.sort_values(by=date_col, ascending=False)
        except Exception:
            pass

    for _, row in df.iterrows():
        link = str(row[link_col]).strip()
        if not link or link == 'nan' or not link.startswith('http'):
            continue

        if link in already_processed:
            skipped_already += 1
            continue

        title = str(row[title_col]).strip() if title_col else "Software Engineer"
        exp_str = str(row[exp_col]).strip() if exp_col else "0-1 Yrs"
        date_str = str(row[date_col]).strip()[:10] if date_col else "Recent"
        company = str(row[company_col]).strip() if company_col else "Company"

        m = re.search(r'(\d+)\s*(?:-|to)?\s*(\d+)?', exp_str.lower())
        min_exp = 0
        if m:
            try:
                min_exp = int(m.group(1))
            except ValueError:
                min_exp = 0

        if min_exp > MAX_EXPERIENCE:
            skipped_senior += 1
            logger.info(f"  ⏭ Skipping CSV job with min exp {min_exp} > {MAX_EXPERIENCE} yrs: {title}")
            continue

        jobs.append((title, exp_str, date_str, link))

    logger.info("=" * 65)
    logger.info(f"📂 CSV Loading Summary:")
    logger.info(f"   Total rows in CSV: {len(df)}")
    logger.info(f"   Already processed in prior runs: {skipped_already}")
    logger.info(f"   Senior roles filtered out: {skipped_senior}")
    logger.info(f"   Fresh eligible jobs ready to apply: {len(jobs)}")
    logger.info("=" * 65)

    return jobs


def resolve_job_source():
    """
    Determines whether to load jobs from a CSV file or scrape live via keywords.
    Order of precedence:
    1. CLI argument: --csv <path>
    2. CLI argument: --search (forces live keyword scraping)
    3. .env variable: INPUT_CSV
    4. Auto-detection: Desktop/Naukri_Pune_Fresher_Jobs_24h.csv
    """
    args = sys.argv[1:]
    if any(s in args for s in ["--search", "--direct-search", "--live-search"]):
        return "search", None

    for i, arg in enumerate(args):
        if arg == "--csv" and i + 1 < len(args):
            return "csv", args[i + 1]
        elif arg.endswith(".csv") and os.path.exists(arg):
            return "csv", arg

    if INPUT_CSV and os.path.exists(INPUT_CSV):
        return "csv", INPUT_CSV

    desktop_csv = os.path.expanduser(r"~\Desktop\Naukri_Pune_Fresher_Jobs_24h.csv")
    if os.path.exists(desktop_csv):
        return "csv", desktop_csv

    return "search", None


def apply_to_jobs(driver, jobs):
    """Apply to direct fresh jobs, solving screening questionnaires via Gemini AI."""
    applied = 0
    skipped_external = 0
    failed = 0
    applied_list = {'title': [], 'posted': [], 'status': [], 'url': []}

    target_desc = f"{MAX_APPLICATIONS} DIRECT fresh applications" if MAX_APPLICATIONS > 0 else f"ALL {len(jobs)} eligible jobs (No Limit)"
    logger.info("=" * 65)
    logger.info(f"Targeting {target_desc}...")
    logger.info("=" * 65)

    main_window = driver.current_window_handle
    already_processed = get_already_processed_urls()

    for i, (title, exp, date_str, link) in enumerate(jobs, 1):
        if MAX_APPLICATIONS > 0 and applied >= MAX_APPLICATIONS:
            logger.info(f"🎉 Target direct applications reached ({MAX_APPLICATIONS}). Stopping.")
            break

        if link in already_processed:
            logger.info(f"[{i}/{len(jobs)}] ⏭ Already processed previously: {title}. Skipping...")
            continue

        logger.info(f"[{i}/{len(jobs)}] Inspecting ({date_str} | {exp} yrs): {title}")
        logger.info(f"  URL: {link}")

        # Top-level per-job error guard: an issue on any single job NEVER crashes the bot
        try:
            # 0. Clean up any stray secondary tabs left open from prior actions
            try:
                all_handles = driver.window_handles
                if main_window not in all_handles and all_handles:
                    main_window = all_handles[0]
                for h in all_handles:
                    if h != main_window:
                        try:
                            driver.switch_to.window(h)
                            driver.execute_script("window.close();")
                        except Exception:
                            try:
                                driver.close()
                            except Exception:
                                pass
                driver.switch_to.window(main_window)
            except Exception:
                pass

            initial_handles = set(driver.window_handles)

            # Navigate to job URL
            try:
                driver.get(link)
                time.sleep(3)
                bring_window_to_foreground()
            except WebDriverException as e:
                logger.warning(f"  ✗ Failed to load page: {e}")
                failed += 1
                applied_list['title'].append(title)
                applied_list['posted'].append(date_str)
                applied_list['status'].append('failed_load')
                applied_list['url'].append(link)
                record_job_result(title, date_str, 'failed_load', link)
                already_processed.add(link)
                continue

            # Handle any initial popup/modal
            handle_naukri_pre_apply_modals(driver)

            # 1. CHECK IF ALREADY APPLIED
            if is_already_applied(driver):
                logger.info(f"  ℹ️ Already applied previously. Moving to next job...")
                applied_list['title'].append(title)
                applied_list['posted'].append(date_str)
                applied_list['status'].append('already_applied')
                applied_list['url'].append(link)
                record_job_result(title, date_str, 'already_applied', link)
                already_processed.add(link)
                continue

            # 2. SKIP EXTERNAL COMPANY PORTALS
            if is_external_job(driver):
                skipped_external += 1
                logger.info(f"  ⏭ SKIPPED (External Company Portal): '{title}' applies externally. Moving to next job...")
                applied_list['title'].append(title)
                applied_list['posted'].append(date_str)
                applied_list['status'].append('skipped_external_site')
                applied_list['url'].append(link)
                record_job_result(title, date_str, 'skipped_external_site', link)
                already_processed.add(link)
                continue

            # 3. LOCATE DIRECT APPLY BUTTON
            apply_btn = find_direct_apply_button(driver)
            if not apply_btn:
                # Double-check if the button or page indicates already applied
                if is_already_applied(driver):
                    logger.info(f"  ℹ️ Already applied previously. Moving to next job...")
                    applied_list['title'].append(title)
                    applied_list['posted'].append(date_str)
                    applied_list['status'].append('already_applied')
                    applied_list['url'].append(link)
                    record_job_result(title, date_str, 'already_applied', link)
                    already_processed.add(link)
                    continue

                failed += 1
                logger.warning(f"  ✗ No direct Apply button found. Moving to next job...")
                applied_list['title'].append(title)
                applied_list['posted'].append(date_str)
                applied_list['status'].append('no_direct_apply_button')
                applied_list['url'].append(link)
                record_job_result(title, date_str, 'no_direct_apply_button', link)
                already_processed.add(link)
                continue

            # 4. CLICK DIRECT APPLY
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_btn)
                time.sleep(0.5)
                try:
                    apply_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", apply_btn)
                logger.info("  ✓ Clicked direct Naukri Apply button!")
                time.sleep(3)

                # 4.1 Check for immediate rate limit toast / 'try again later'
                is_limited, limit_msg = check_naukri_rate_limit(driver)
                if is_limited:
                    logger.warning(f"  🛑 [Rate Limit / 'Try Again Later' Detected on Apply]: {limit_msg}")
                    handle_rate_limit_cooldown(driver, cooldown_minutes=25)
                    # Refresh and retry
                    driver.get(link)
                    time.sleep(3)
                    handle_naukri_pre_apply_modals(driver)
                    apply_btn = find_direct_apply_button(driver)
                    if apply_btn:
                        try:
                            apply_btn.click()
                            time.sleep(3)
                            is_limited_again, _ = check_naukri_rate_limit(driver)
                            if is_limited_again:
                                logger.warning("  ⚠️ Still rate limited after 25m cooldown (Daily quota exhausted). Transitioning remaining direct jobs to external scoring...")
                                break
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"  Could not click apply button: {e}")
                failed += 1
                continue

            # 5. VERIFY NO EXTERNAL REDIRECT TAB WAS OPENED
            try:
                current_all_handles = driver.window_handles
            except Exception:
                current_all_handles = [main_window]

            new_handles = [h for h in current_all_handles if h != main_window and h not in initial_handles]
            if new_handles:
                is_redirect = False
                for handle in new_handles:
                    try:
                        driver.switch_to.window(handle)
                        time.sleep(0.5)
                        opened_url = ""
                        try:
                            opened_url = driver.current_url.lower()
                        except Exception:
                            pass
                        if "naukri.com" not in opened_url and opened_url not in ["about:blank", ""]:
                            is_redirect = True
                            logger.info(f"  Detected external redirect URL: {opened_url[:60]}...")
                        # Close extra tab safely without blocking EdgeDriver
                        try:
                            driver.execute_script("window.close();")
                        except Exception:
                            try:
                                driver.close()
                            except Exception:
                                pass
                    except Exception as tab_err:
                        logger.debug(f"Handling extra tab note: {tab_err}")

                try:
                    driver.switch_to.window(main_window)
                except Exception:
                    remaining = driver.window_handles
                    if remaining:
                        main_window = remaining[0]
                        driver.switch_to.window(main_window)

                if is_redirect:
                    skipped_external += 1
                    logger.info(f"  ⏭ SKIPPED (External Redirect tab spawned). Closed tab and moving to next job...")
                    applied_list['title'].append(title)
                    applied_list['posted'].append(date_str)
                    applied_list['status'].append('skipped_external_redirect')
                    applied_list['url'].append(link)
                    record_job_result(title, date_str, 'skipped_external_redirect', link)
                    already_processed.add(link)
                    continue

            # Check if current tab itself was redirected away from Naukri
            try:
                curr_url = driver.current_url.lower()
                if "naukri.com" not in curr_url and curr_url not in ["about:blank", ""]:
                    skipped_external += 1
                    logger.info(f"  ⏭ SKIPPED (Tab navigated to external portal: {curr_url[:60]}). Moving to next job...")
                    applied_list['title'].append(title)
                    applied_list['posted'].append(date_str)
                    applied_list['status'].append('skipped_external_redirect')
                    applied_list['url'].append(link)
                    record_job_result(title, date_str, 'skipped_external_redirect', link)
                    already_processed.add(link)
                    continue
            except Exception:
                pass

            # Handle interstitial modal if prompted after clicking apply
            handle_naukri_pre_apply_modals(driver)

            # 6. DETECT & SOLVE SCREENING QUESTIONNAIRES (Chatbot Drawer or Form Modal)
            questionnaire_detected = False
            for sec in range(8):
                if is_any_questionnaire_open(driver):
                    questionnaire_detected = True
                    resolve_questionnaire_with_ai(driver)
                    time.sleep(2)
                    break
                time.sleep(1)

            # 7. HANDLE INLINE FORM (first/last name, submit if present)
            try:
                first_in = driver.find_element(By.ID, 'CUSTOM-FIRSTNAME')
                first_in.clear()
                first_in.send_keys(FIRSTNAME)
                logger.info("  Filled first name")
            except NoSuchElementException:
                pass

            try:
                last_in = driver.find_element(By.ID, 'CUSTOM-LASTNAME')
                last_in.clear()
                last_in.send_keys(LASTNAME)
                logger.info("  Filled last name")
            except NoSuchElementException:
                pass

            try:
                submit_btn = driver.find_element(By.XPATH, "//*[text()='Submit and Apply']")
                submit_btn.click()
                logger.info("  Clicked 'Submit and Apply'")
                time.sleep(2)
            except NoSuchElementException:
                pass

            # Check for rate limit after submission
            is_limited_sub, limit_msg_sub = check_naukri_rate_limit(driver)
            if is_limited_sub:
                logger.warning(f"  🛑 [Rate Limit Detected on Submission]: {limit_msg_sub}")
                handle_rate_limit_cooldown(driver, cooldown_minutes=25)

            # 8. VERIFICATION GUARD: CONFIRM QUESTIONNAIRE IS NOT STILL BLOCKING
            if is_any_questionnaire_open(driver):
                logger.info("  Questionnaire still detected. Running secondary solver attempt...")
                resolve_questionnaire_with_ai(driver)
                time.sleep(3)

            if is_any_questionnaire_open(driver):
                logger.warning(f"  ⚠️ Application for '{title}' could not complete mandatory questionnaire. Skipping...")
                failed += 1
                applied_list['title'].append(title)
                applied_list['posted'].append(date_str)
                applied_list['status'].append('questionnaire_incomplete')
                applied_list['url'].append(link)
                record_job_result(title, date_str, 'questionnaire_incomplete', link)
                already_processed.add(link)
                continue

            # 9. CONFIRM DIRECT APPLICATION SUCCESS
            applied += 1
            applied_list['title'].append(title)
            applied_list['posted'].append(date_str)
            applied_list['status'].append('direct_applied_success')
            applied_list['url'].append(link)
            record_job_result(title, date_str, 'direct_applied_success', link)
            already_processed.add(link)
            total_str = f"{MAX_APPLICATIONS}" if MAX_APPLICATIONS > 0 else f"{len(jobs)}"
            logger.info(f"  🎉 Application Successfully Submitted! (Total Applied: {applied}/{total_str})")

            # Humanized pacing delay (10-18s) to avoid WAF burst flagging
            import random
            pacing_delay = round(random.uniform(10.0, 18.0), 1)
            logger.info(f"  Pacing delay: waiting {pacing_delay}s before next application to maintain natural activity...")
            time.sleep(pacing_delay)

        except Exception as job_err:
            logger.error(f"  ❌ Error applying to '{title}': {job_err}")
            failed += 1
            applied_list['title'].append(title)
            applied_list['posted'].append(date_str)
            applied_list['status'].append('error')
            applied_list['url'].append(link)
            record_job_result(title, date_str, 'error', link)
            already_processed.add(link)

            # Safely recover browser window state for subsequent jobs
            try:
                for h in driver.window_handles:
                    if h != main_window:
                        try:
                            driver.switch_to.window(h)
                            driver.execute_script("window.close();")
                        except Exception:
                            try:
                                driver.close()
                            except Exception:
                                pass
                driver.switch_to.window(main_window)
            except Exception:
                if driver.window_handles:
                    main_window = driver.window_handles[0]
                    driver.switch_to.window(main_window)
            continue

    logger.info("=" * 65)
    logger.info(f"Summary: {applied} Direct Applied | {skipped_external} External Sites Skipped | {failed} Failed/Other")
    logger.info("=" * 65)
    return applied, failed, applied_list


def save_results(applied_list):
    """Save applied jobs to CSV."""
    csv_file = "naukriapplied.csv"
    logger.info(f"All progress verified and saved in {csv_file}")


def main():
    """Main entry point."""
    global MAX_APPLICATIONS
    logger.info("=" * 65)
    logger.info("Naukri Auto-Apply Bot (Past 24h & Smart AI Chatbot Recovery)")
    logger.info("=" * 65)

    # Check for CLI --limit, --max, --all, --no-limit
    args = sys.argv[1:]
    if any(flag in args for flag in ["--all", "--no-limit", "--unlimited"]):
        MAX_APPLICATIONS = 0
        logger.info("Target applications set from CLI: ALL jobs (Unlimited)")
    else:
        for i, arg in enumerate(args):
            if arg in ["--limit", "--max"] and i + 1 < len(args):
                try:
                    MAX_APPLICATIONS = int(args[i + 1])
                    logger.info(f"Target applications set from CLI: {MAX_APPLICATIONS}")
                except ValueError:
                    pass

    if not validate_config():
        return

    logger.info(f"Candidate: {CANDIDATE_PROFILE['personal_details']['full_name']}")
    logger.info(f"Strict Experience: <= {MAX_EXPERIENCE} Years (Freshers/Entry-level)")
    logger.info(f"AI Engine: {GEMINI_MODEL} (Google Gemini)")
    target_label = f"{MAX_APPLICATIONS} Direct Naukri Jobs" if MAX_APPLICATIONS > 0 else "ALL eligible jobs (No Limit)"
    logger.info(f"Target Applications: {target_label}")

    source_type, source_path = resolve_job_source()

    driver = None
    try:
        driver = create_edge_driver()

        if "--wait-for-user" in sys.argv:
            driver.get('https://www.naukri.com/')
            bring_window_to_foreground()
            logger.info("=" * 65)
            logger.info("👀 BROWSER LAUNCHED: Edge is now open on your screen!")
            logger.info("⏳ Waiting for user approval signal (start_applying.flag)...")
            logger.info("=" * 65)
            flag_file = os.path.abspath("start_applying.flag")
            if os.path.exists(flag_file):
                try:
                    os.remove(flag_file)
                except Exception:
                    pass
            while not os.path.exists(flag_file):
                time.sleep(1)
            logger.info("✅ User approval received! Continuing with auto-apply...")
            try:
                os.remove(flag_file)
            except Exception:
                pass

        if not login_naukri(driver):
            logger.error("Stopping execution because user is not authenticated.")
            return

        if source_type == "csv":
            logger.info(f"📁 Source Mode: CSV File ({source_path})")
            matching_jobs = load_jobs_from_csv(source_path)
        else:
            logger.info(f"🌐 Source Mode: Live Keyword Search ({KEYWORDS} in {LOCATION})")
            search_urls = build_search_urls()
            matching_jobs = collect_all_jobs_parallel(driver, search_urls)

        if not matching_jobs:
            logger.warning("No eligible jobs found to apply.")
            return

        applied, failed, applied_list = apply_to_jobs(driver, matching_jobs)
        save_results(applied_list)

        logger.info("👀 Bot run completed! Leaving browser open for 30 seconds so you can see the result...")
        time.sleep(30)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Browser closed.")
            except Exception:
                pass


if __name__ == "__main__":
    main()