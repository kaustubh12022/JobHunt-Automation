"""
AutoApply Scorer V2 — Deterministic Standalone Regex Filtering Pipeline.

Architecture Rules:
- 100% deterministic regex filtering pipeline with zero token / zero LLM cost.
- Expanded domain anchors and tech tools covering MERN stack and AI/LLM domains.
- Robust boundary-checked senior title identification with progression masking.
- Context-aware experience requirement filtering with company boilerplate stripping.
- Role-scoped out-of-scope technology checks preserving hybrid and peripheral skills.
- Preserves original src/scorer.py and src/scraper.py interfaces.
"""

import json
import re
from typing import List, Dict, Any, Optional
import pandas as pd


# ── Boilerplate stripping regex patterns ──
BOILERPLATE_PATTERNS = [
    r'(?i)(?:^|\n)\s*(?:about\s+(?:us|the\s+company|our\s+company)).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:company\s+(?:overview|description|profile)).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:benefits|perks|what\s+we\s+offer|compensation|what\s+you.*?get).*?(?=\n\s*(?:[A-Z]|\Z))',
    r'(?i)(?:^|\n)\s*(?:equal\s+opportunity|diversity|eeo|we\s+are\s+an?\s+equal).*?(?=(?:\n\s*(?:technical\s+requirements|requirements|responsibilities|qualifications|skills|job\s+description|[A-Z][A-Za-z0-9\s/]+:))|\Z)',
    r'(?i)(?:^|\n)\s*(?:disclaimer|note\s*:?\s*this).*?(?=(?:\n\s*(?:technical\s+requirements|requirements|responsibilities|qualifications|skills|job\s+description|[A-Z][A-Za-z0-9\s/]+:))|\Z)',
    r'(?i)(?:^|\n)\s*(?:life\s+at|why\s+join\s+us|our\s+culture|covid).*?(?=\n\s*(?:[A-Z]|\Z))',
]

# ── Zero-Token Domain-Anchored Keyword Relevance Filter (V2 Expanded) ──
DOMAIN_ANCHORS = [
    # Core SWE / Java / Python / Backend
    'java', 'python', 'qa', 'selenium', 'automation',
    '.net', 'c#', 'csharp', 'asp.net', 'spring', 'full stack', 'fullstack',
    'full-stack', r'full\-stack',
    'sdet', 'quality assurance', 'postman', 'pytest', 'junit',
    'playwright', 'cypress', 'tester', 'manual testing', 'automation testing',
    'software testing', 'api testing', 'test automation', 'test case', 'test cases',
    'test suite', 'test plan', 'test engineer',
    # Target Domain 6: MERN Stack
    'mern', 'mern stack', 'mean', 'react', 'reactjs', 'react.js',
    'node', 'nodejs', 'node.js', 'express', 'expressjs', 'express.js', 'mongodb',
    # Target Domain 7: AI / ML / LLM / Agentic AI
    'ai', 'ml', 'machine learning', 'llm', 'llms', 'agentic',
    'genai', 'generative ai', 'rag', 'langchain', 'llamaindex', 'deep learning'
]

TECH_TOOLS = [
    'spring', 'sql', 'pytest', 'postman', 'junit', 'rest api', 'api', 'react',
    'javascript', 'typescript', 'html', 'css', 'mysql', 'mongodb', 'docker', 'git', 'jdbc',
    'azure', 'c#', 'java', 'python', 'selenium', 'automation', 'database',
    'oops', 'oop', 'microservices', 'django', 'flask', 'node', 'nodejs', 'node.js',
    'express', 'expressjs', 'express.js', 'fastapi', 'nextjs', 'next.js',
    'redis', 'postgres', 'postgresql', 'graphql',
    'llm', 'rag', 'agentic', 'genai', 'langchain', 'llamaindex',
    'tailwind', 'redux', 'deep learning', 'machine learning', 'ai', 'ml',
    'test', 'qa'
]

CORE_STACK_KEYWORDS = [
    'java', 'python', 'sql', 'selenium', 'postman', 'junit', 'pytest',
    'automation', 'qa', '.net', 'c#', 'asp.net', 'spring', 'jdbc',
    'rest api', 'backend', 'testing', 'test case', 'api testing',
    'html', 'css', 'javascript', 'typescript', 'full stack', 'software engineer',
    'developer', 'agile', 'git', 'mysql', 'mongodb', 'docker', 'react', 'node',
    'express', 'fastapi', 'llm', 'rag', 'ai', 'ml'
]
MIN_KEYWORD_MATCHES = 2

# Primary out-of-scope technology stacks
OUT_OF_SCOPE_STACK_PATTERN = re.compile(
    r'\b(?:php|laravel|ruby|rails|ios|swift|swiftui|android|kotlin|flutter|react\s+native|salesforce|apex|sap|abap|drupal|magento|wordpress)\b',
    re.IGNORECASE
)

# Career progression masking patterns (to preserve entry-level roles with growth tracks)
PROGRESSION_PATTERNS = [
    r'\b(?:fast[- ]track|path(?:way)?|journey|road)\s+to\s+(?:tech\s+)?lead\b',
    r'\baspiring\s+(?:tech\s+)?lead\b',
    r'\bpotential\s+to\s+(?:become|grow\s+into)\s+(?:a\s+)?(?:tech\s+)?lead\b',
]

# Senior keywords with boundaries, executive acronyms, and terminal digit tiers
SENIOR_KEYWORDS_PATTERN = (
    r'\b(?:senior|lead|manager|principal|director|head|vp|president|experienced|'
    r'architect|staff|expert|ii|iii|iv|v|vi|vii|viii|level\s*[2-9]|l[2-9]|avp|'
    r'associate\s+vice\s+president|advanced)\b|\bsr[\.,\s]|\bsr$|'
    r'\b(?:analyst|engineer|developer|consultant|specialist|architect|scientist|quality|manager|lead)[-\s]+[2-9]\s*$'
)


def _match_keyword(kw: str, text: str) -> bool:
    """
    Matches a keyword in text, applying word boundary for short abbreviations (<= 2 chars)
    to prevent false substring matches (e.g. 'ai' in 'maintain', 'ml' in 'html').
    Safely normalizes case and guards against non-string inputs.
    """
    if not isinstance(kw, str) or not isinstance(text, str):
        return False
    kw_clean = kw.lower().strip()
    text_clean = text.lower()
    if not kw_clean or not text_clean:
        return False
    if len(kw_clean) <= 2 and kw_clean not in ('.net', 'c#'):
        return bool(re.search(r'\b' + re.escape(kw_clean) + r'\b', text_clean))
    return kw_clean in text_clean


def matches_out_of_scope_role(title: str = "", description: str = "") -> bool:
    """
    Returns True if title or description indicates an out-of-scope technology stack
    (PHP, Ruby, iOS, Android, Flutter, React Native, Salesforce, SAP, WordPress).

    Protections:
    - Allows 'Kotlin' in title when paired with Java or Full Stack backend.
    - Exempts Salesforce in description when mentioned as a tested enterprise app in QA roles.
    - Exempts Flutter / React Native in description when peripheral in Full Stack roles.
    - Exempts keywords mentioned under optional / nice-to-have sections.
    """
    if not isinstance(title, str):
        title = "" if title is None or pd.isna(title) else str(title)
    if not isinstance(description, str):
        description = "" if description is None or pd.isna(description) else str(description)

    title_clean = title.lower() if title else ""

    # Check title: Allow Kotlin when paired with Java or backend/fullstack
    if 'kotlin' in title_clean and ('java' in title_clean or 'backend' in title_clean or 'full stack' in title_clean):
        pass
    elif OUT_OF_SCOPE_STACK_PATTERN.search(title_clean):
        return True

    if description:
        desc_lower = description.lower()
        is_qa_role = bool(re.search(r'\b(?:qa|quality assurance|tester|test automation|testing)\b', title_clean))
        is_fullstack_role = bool(re.search(r'\b(?:full stack|fullstack|software engineer|developer)\b', title_clean))

        oos_keywords = [
            'php', 'laravel', 'ruby', 'rails', 'ios', 'swift', 'swiftui',
            'android', 'salesforce', 'apex', 'sap', 'abap', 'drupal',
            'magento', 'wordpress', 'flutter', 'react native'
        ]

        for oos_kw in oos_keywords:
            if re.search(r'\b' + oos_kw + r'\b', desc_lower):
                # Context 1: Salesforce mentioned as a tested SaaS app in QA roles
                if oos_kw == 'salesforce' and is_qa_role:
                    if re.search(r'(?:testing|tested|products\s+such\s+as|integrations?\s+with).*?salesforce', desc_lower):
                        continue
                # Context 2: Flutter / React Native mentioned as optional mobile framework in fullstack roles
                if oos_kw in ['flutter', 'react native'] and is_fullstack_role:
                    if re.search(r'react.*?flutter|flutter.*?react|node.*?flutter', desc_lower):
                        continue
                # Context 3: Good to have / Optional qualification
                if re.search(r'(?:good\s+to\s+have|nice\s+to\s+have|preferred|plus|optional)[^.\n]*?\b' + oos_kw + r'\b', desc_lower):
                    continue
                return True

    return False



def matches_senior_title(title: str, description: str = "") -> bool:
    """
    Returns True if job title indicates a senior/lead/managerial role or
    explicitly requires >= 3 years of experience in the title.
    Preserves genuine entry-level, junior, associate, graduate, trainee, and 0-2 / 1-3 year jobs.

    V2 Enhancements:
    - Masks career progression suffixes (e.g. 'Fast-Track to Tech Lead').
    - Recognizes AVP, Associate Vice President, and Advanced Engineer tiers.
    - Matches terminal senior digit tiers (e.g. 'Analyst 3', 'Engineer 2').
    - Checks description header for disguised managerial career levels (Accenture Level 7).
    """
    if not isinstance(title, str):
        title = "" if title is None or pd.isna(title) else str(title)
    if not isinstance(description, str):
        description = "" if description is None or pd.isna(description) else str(description)
    if not title.strip():
        return False
    title_lower = title.lower().strip()

    # 1. Mask career progression phrases to avoid false rejections on entry roles
    masked_title = title_lower
    for prog in PROGRESSION_PATTERNS:
        masked_title = re.sub(prog, 'progression_role', masked_title, flags=re.I)

    # 2. Senior role keywords with boundaries, executive grades, and terminal digit tiers
    if re.search(SENIOR_KEYWORDS_PATTERN, masked_title, flags=re.I):
        return True

    # 3. Explicit experience ranges in title: e.g. "3-5 years", "3 to 5 yrs", "4-10 yrs"
    # Preserves entry-level ranges like "0-2 years", "0-3 yrs", "1-3 years"
    range_title_pat = r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(range_title_pat, masked_title):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo >= 25 or hi >= 25:  # Ignore candidate age brackets in title
            continue
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # 4. Explicit single experience requirements in title: e.g. "5+ years", "5+yrs", "3+ yoe"
    single_title_pat = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(single_title_pat, masked_title):
        num = int(m.group(1))
        has_plus = bool(re.search(r'\+|or more|more than|plus', m.group(0)))
        if has_plus and num >= 3:
            return True
        if num >= 3 and not re.search(r'\b[012]\s*[-\u2013to]+\s*' + str(num), masked_title):
            return True

    # 5. Word-based experience in title (e.g. "three to five years")
    words_to_num = {
        'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
        'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
    }
    words_list = '|'.join(words_to_num.keys())
    word_title_pat = fr'\b({words_list})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b'
    for m in re.finditer(word_title_pat, masked_title):
        matched_word = m.group(1)
        if words_to_num.get(matched_word, 0) >= 3:
            preceding = masked_title[:m.start()]
            if re.search(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014)\s*$', preceding):
                continue
            return True

    # 6. Check description header for disguised managerial career levels
    if description:
        first_1000 = description[:1000].lower()
        if re.search(r'\bcareer\s+level\s+[1-7]\b.*?(?:manager|leadership|lead\s+engineering)', first_1000, re.DOTALL):
            return True
        if re.search(r'\b(?:engineering\s+manager|quality\s+engineering\s+manager)\b', first_1000):
            return True

    return False


# ── Pre-compiled Third-Party Experience Patterns (Module-Level) ──
THIRD_PARTY_EXPERIENCE_PREFIXES = (
    r'our\s+team\s+(?:has|have|with|of)',
    r'the\s+team\s+(?:has|have|with|of)',
    r'work(?:ing)?\s+(?:with|alongside|beside|among)\s+(?:a\s+team|teams|colleagues|engineers|experts|leaders|seniors|other\s+developers)?',
    r'join(?:ing)?\s+(?:a\s+)?team\s+(?:of|with)?',
    r'(?:we\s+are\s+a|a)\s+team\s+with',
    r'(?:founded|established|started|operating|running)\s+(?:in|since|for|with)',
    r'(?:we\s+have|company\s+has|firm\s+has)\s+(?:over|more\s+than|been)',
    r'(?:our\s+company|our\s+firm|our\s+organisation)\s+(?:has|have)',
    r'colleagues?\s+(?:with|who\s+have)',
    r'mentors?\s+(?:with|who\s+have)',
    r'mentorship\s+from',
    r'learn(?:ing)?\s+from',
    r'(?:combined|collective|total)\s+experience',
    r'(?:history|heritage|industry)\s+(?:of|spanning)',
    r'(?:team|group|pool)\s+of\s+(?:engineers?|developers?|professionals?)\s+with',
    r'(?:senior\s+)?engineers?\s+(?:who\s+have|with\s+over)',
    r'in\s+\d{4}\s+with',
    r'(?:over\s+the\s+past|in\s+the\s+past)',
    r'with\s+(?:over|more\s+than)',
)

_NUM_WORDS_OR_DIGITS = r'(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty)'

THIRD_PARTY_PATTERN = re.compile(
    r'\b(?:' + '|'.join(THIRD_PARTY_EXPERIENCE_PREFIXES) + fr')\s*(?:(?:about|around|over|more than|approximately)\s*)?{_NUM_WORDS_OR_DIGITS}\+?(?:\s*[-–]\s*{_NUM_WORDS_OR_DIGITS})?\+?\s*(?:years?|yrs?)\b',
    re.IGNORECASE
)

THIRD_PARTY_HERITAGE_PATTERN = re.compile(
    r'\b(?:(?:over\s+the\s+past|in\s+the\s+past)\s+\w+\s+years\s+\w+\s+has\s+grown|(?:years\s+)?\w+\s+has\s+grown)\b',
    re.IGNORECASE
)

AGE_PATTERN = re.compile(r'\(\s*(?:[2-9]\d)\s*(?:to|-)\s*(?:[2-9]\d)\s*yrs?\s*\)', re.IGNORECASE)
KV_RANGE_PATTERN = re.compile(r'(?:required|work|total)?\s*experience\s*:\s*(\d+)\s*[-\u2013to]+\s*(\d+)', re.IGNORECASE)
KV_SINGLE_PATTERN = re.compile(r'years\s+of\s+experience\s+required\s*:\s*(\d+)', re.IGNORECASE)

NUM_TOKENS = r'(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'
RANGE_SEP = r'(?:[-\u2013\u2014]|to|till|and)'
RANGE_PATTERN = re.compile(fr'\b({NUM_TOKENS})\s*(?:\([^\)]+\)\s*)?{RANGE_SEP}\s*({NUM_TOKENS})\s*(?:\([^\)]+\)\s*)?(?:\+|or more|plus)?\s*(?:years?|yrs?\.?|yoe)\b', re.IGNORECASE)
PLUS_PATTERN = re.compile(r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than|plus)\s*(?:years?|yrs?\.?|yoe)', re.IGNORECASE)
MIN_PATTERN = re.compile(fr'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?({NUM_TOKENS})\s*(?:years?|yrs?\.?)?', re.IGNORECASE)
SINGLE_EXP_PATTERN = re.compile(r'(?<![-\u2013\d])\b(\d+)\s*(?:years?|yrs?\.?)\s*(?:of\s+)?(?:experience|exp|hands[- ]on|relevant|background|industry|work)?', re.IGNORECASE)
YRS_PATTERN = re.compile(r'(?<![-\u2013\d])\b(\d+)\s+yrs?\b', re.IGNORECASE)

WORDS_TO_NUM = {
    'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
    'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
}
WORDS_LIST = '|'.join(WORDS_TO_NUM.keys())
WORD_PATTERN = re.compile(fr'\b({WORDS_LIST})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b', re.IGNORECASE)

WORDS_TO_NUM_ALL = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12
}


def _tok_to_val(tok: str) -> int:
    tok_clean = tok.lower().strip()
    if tok_clean.isdigit():
        return int(tok_clean)
    return WORDS_TO_NUM_ALL.get(tok_clean, 0)


NON_WORK_CONTEXT = re.compile(r'degree|bachelor|diploma|bond|agreement|contract|commitment|lock-in|warranty|course', re.IGNORECASE)
PRECEDING_ENTRY_PATTERN = re.compile(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014|till|and|or)\s*$', re.IGNORECASE)


def requires_3_plus_years(desc: str = "", text: str = "") -> bool:
    """
    Returns True if the JD requires 3+ years of CANDIDATE experience.
    Safeguards:
    - Strips third-party/company/team experience sentences without swallowing candidate skills.
    - Ignores candidate age specifications (e.g. '(27 to 40 Yrs)').
    - Parses standalone key-value experience formats and multi-line headers.
    - Preserves 0-1, 0-2, 0-3, 1-2, 1-3 year jobs (1-3 years is NEVER dropped).
    - Checks upper bounds only when lower bound indicates non-entry level.
    """
    content = text if text else desc
    if not isinstance(content, str):
        content = "" if content is None or pd.isna(content) else str(content)
    if not content.strip():
        return False
    desc_lower = content.lower().replace('\\', '')

    # Step 1: Strip third-party / company / team experience via pre-compiled regex substitution
    candidate_text = THIRD_PARTY_PATTERN.sub(' ', desc_lower)
    candidate_text = THIRD_PARTY_HERITAGE_PATTERN.sub(' ', candidate_text)

    # Guard against candidate age brackets (e.g. '(27 to 40 Yrs)')
    candidate_text = AGE_PATTERN.sub(' ', candidate_text)

    # Standalone key-value experience range (e.g. 'Required Experience: 2-5')
    kv_range = KV_RANGE_PATTERN.search(candidate_text)
    if kv_range:
        lo, hi = int(kv_range.group(1)), int(kv_range.group(2))
        if lo >= 25 or hi >= 25:
            pass
        elif lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # Multi-line key-value experience header (e.g. 'Years of Experience required:\n\n 4')
    kv_single = KV_SINGLE_PATTERN.search(candidate_text)
    if kv_single and int(kv_single.group(1)) >= 3:
        return True

    # Step 2: Experience range check (X-Y years, digits or words)
    for m in RANGE_PATTERN.finditer(candidate_text):
        lo, hi = _tok_to_val(m.group(1)), _tok_to_val(m.group(2))
        if lo >= 25 or hi >= 25:  # Ignore candidate age specifications
            continue
        # Keep 0-1, 0-2, 0-3, 1-2, 1-3, 2-3
        # Drop if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # Strip ranges before checking single numbers so second number (e.g. 3 in 1-3) is not re-matched
    candidate_noranges = RANGE_PATTERN.sub(' ', candidate_text)

    # Step 3: Single number + '+' or 'or more' (e.g. 3+ years, 5+ yrs)
    for m in PLUS_PATTERN.finditer(candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return True

    # Step 4: 'minimum/at least X years' (with digits and word numerals support)
    for m in MIN_PATTERN.finditer(candidate_noranges):
        num = _tok_to_val(m.group(1))
        if 3 <= num <= 20:
            return True

    # Step 5: Single number with candidate experience context
    for m in SINGLE_EXP_PATTERN.finditer(candidate_noranges):
        num = int(m.group(1))
        # Avoid false positives like degree duration '3 years degree', '3 years bond'
        if NON_WORK_CONTEXT.search(candidate_text[max(0, m.start()-20):min(len(candidate_text), m.end()+20)]):
            continue
        if 3 <= num <= 25:
            return True

    # Step 6: 'X yrs' shorthand
    for m in YRS_PATTERN.finditer(candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return True

    # Step 7: Word-based ('three to five years')
    for m in WORD_PATTERN.finditer(candidate_noranges):
        matched_word = m.group(1)
        if WORDS_TO_NUM.get(matched_word, 0) >= 3:
            preceding = candidate_noranges[:m.start()]
            if PRECEDING_ENTRY_PATTERN.search(preceding):
                continue
            return True

    return False



def is_relevant_jd(description: str, title: str = "") -> bool:
    """
    Zero-token relevance check: ensures the JD contains at least
    1 core domain anchor and at least 1 technology tool/qualifier,
    and does not belong to an out-of-scope technology stack.

    V2 Enhancements:
    - Normalizes markdown escaped hyphens and underscores (e.g. 'full\\-stack' -> 'full-stack').
    - Evaluates both description and title for domain anchors and tools.
    - Applies word boundary protection for short abbreviations (ai, ml).
    """
    if not isinstance(description, str):
        description = "" if description is None or pd.isna(description) else str(description)
    if not isinstance(title, str):
        title = "" if title is None or pd.isna(title) else str(title)
    if not description.strip():
        return False
    desc_clean = description.lower().replace(r'\-', '-').replace(r'\_', '_')
    title_clean = title.lower() if title else ""

    # Reject out-of-scope stacks immediately
    if matches_out_of_scope_role(title, description):
        return False

    has_anchor = (
        any(_match_keyword(kw, desc_clean) for kw in DOMAIN_ANCHORS) or
        any(_match_keyword(kw, title_clean) for kw in DOMAIN_ANCHORS)
    )
    has_tool = (
        any(_match_keyword(kw, desc_clean) for kw in TECH_TOOLS) or
        any(_match_keyword(kw, title_clean) for kw in TECH_TOOLS)
    )
    return has_anchor and has_tool


def strip_boilerplate(description: str) -> str:
    """
    Aggressively strip HR boilerplate from a job description to reduce token cost.
    Targets: About Us, Benefits, EEO statements, company overviews.
    """
    if not isinstance(description, str):
        description = "" if description is None or pd.isna(description) else str(description)
    if not description:
        return ""
    cleaned = description
    for pattern in BOILERPLATE_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
    # Collapse excessive whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else description



class ScoredJobList(list):
    """
    List of filtered/shortlisted jobs that retains all scored jobs
    for full token and cost telemetry accounting.
    """
    def __init__(self, iterable=(), all_scored_jobs=None):
        super().__init__(iterable)
        self.all_scored_jobs = all_scored_jobs if all_scored_jobs is not None else []

    def __getitem__(self, item):
        res = super().__getitem__(item)
        if isinstance(item, slice):
            return ScoredJobList(res, all_scored_jobs=self.all_scored_jobs)
        return res


_LAST_SCORED_JOBS: list = []


def get_last_scored_jobs() -> list:
    """Retrieve the complete list of jobs scored during the most recent run."""
    global _LAST_SCORED_JOBS
    return list(_LAST_SCORED_JOBS)


def apply_pandas_filter(*args, **kwargs):
    """Convenience delegate for apply_pandas_filter to ensure interface contract compliance."""
    from src.scraper import apply_pandas_filter as _apf
    return _apf(*args, **kwargs)


def score_jobs(jobs: list, test_mode=False, callbacks=None, stop_event=None) -> list:
    """
    Synchronously filters jobs through Scorer V2 deterministic regex filters
    (matches_senior_title, matches_out_of_scope_role, requires_3_plus_years, is_relevant_jd).
    """
    import pandas as pd
    try:
        from src.config_loader import load_config
        config = load_config()
        hours_old = config.get('search', {}).get('hours_old', 72)
    except Exception:
        hours_old = 72

    cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=hours_old)

    # 1. Freshness filter
    fresh_jobs = []
    skipped_stale = 0
    for job in jobs:
        date_posted = getattr(job, 'date_posted', None)
        if date_posted is not None:
            try:
                dt = pd.to_datetime(date_posted, errors='coerce', utc=True)
                if pd.notna(dt) and dt < cutoff:
                    skipped_stale += 1
                    continue
            except Exception:
                pass
        fresh_jobs.append(job)

    # 2. Filter irrelevant and senior jobs synchronously using V2 filters
    relevant_jobs = []
    skipped_irrelevant = 0

    for job in fresh_jobs:
        title = getattr(job, 'title', '')
        desc = getattr(job, 'description', '')
        if (
            matches_senior_title(title, desc)
            or matches_out_of_scope_role(title, desc)
            or requires_3_plus_years(desc)
            or not is_relevant_jd(desc, title)
        ):
            skipped_irrelevant += 1
            continue
        relevant_jobs.append(job)

    global _LAST_SCORED_JOBS
    _LAST_SCORED_JOBS = list(relevant_jobs)

    if test_mode:
        return ScoredJobList(relevant_jobs[:3], all_scored_jobs=relevant_jobs)
    return ScoredJobList(relevant_jobs, all_scored_jobs=relevant_jobs)
