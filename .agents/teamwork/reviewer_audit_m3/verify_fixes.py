import json
import re
from typing import Dict, List, Any

# Load Master Raw Dataset
raw_jobs: List[Dict[str, Any]] = [
    json.loads(line) for line in open('regex_audit/master_raw_dataset_2026-09-29.jsonl', encoding='utf-8')
]

# Load Ground Truth
gt_data: List[Dict[str, Any]] = [
    json.loads(line) for line in open('regex_audit/evaluation/ground_truth.jsonl', encoding='utf-8')
]

# Load FP & FN
fp_data = [json.loads(line) for line in open('regex_audit/evaluation/false_positives.jsonl', encoding='utf-8')]
fn_data = [json.loads(line) for line in open('regex_audit/evaluation/false_negatives.jsonl', encoding='utf-8')]

# Proposed DOMAIN_ANCHORS and TECH_TOOLS from audit_report.md Section 4.1
DOMAIN_ANCHORS = [
    'java', 'python', 'qa', 'selenium', 'automation',
    '.net', 'c#', 'csharp', 'asp.net', 'spring', 'full stack', 'fullstack',
    'full-stack', 'full\\-stack',
    'sdet', 'quality assurance', 'postman', 'pytest', 'junit',
    'playwright', 'cypress', 'tester', 'manual testing', 'automation testing',
    'software testing', 'api testing', 'test automation', 'test case', 'test cases',
    'test suite', 'test plan', 'test engineer',
    # Target Domain 6: MERN Stack
    'mern', 'mean', 'react', 'reactjs', 'react.js',
    'node', 'nodejs', 'node.js', 'express', 'expressjs', 'express.js', 'mongodb',
    # Target Domain 7: AI / ML / LLM / Agentic AI
    'llm', 'llms', 'rag', 'agentic', 'genai', 'generative ai', 'langchain', 'llamaindex'
]

TECH_TOOLS = [
    'spring', 'sql', 'pytest', 'postman', 'junit', 'rest api', 'api', 'react',
    'javascript', 'typescript', 'html', 'css', 'mysql', 'mongodb', 'docker', 'git', 'jdbc',
    'azure', 'c#', 'java', 'python', 'selenium', 'automation', 'database',
    'oops', 'oop', 'microservices', 'django', 'flask', 'node', 'nodejs', 'express',
    'fastapi', 'nextjs', 'next.js', 'redis', 'postgres', 'postgresql', 'graphql',
    'llm', 'rag', 'genai', 'langchain', 'llamaindex', 'tailwind', 'redux', 'test', 'qa'
]

OUT_OF_SCOPE_STACK_PATTERN = re.compile(
    r'\b(?:php|laravel|ruby|rails|ios|swift|swiftui|android|kotlin|flutter|react\s+native|salesforce|apex|sap|abap|drupal|magento|wordpress)\b',
    re.IGNORECASE
)

# Proposed matches_senior_title from Section 4.2
def matches_senior_title_v2(title: str, description: str = "") -> bool:
    if not title or not isinstance(title, str):
        return False
    title_lower = title.lower()

    # Mask career progression phrases to avoid false rejections on entry-level roles
    progression_patterns = [
        r'\b(?:fast[- ]track|path(?:way)?|aspiring|journey|road)\s+to\s+(?:tech\s+)?lead\b',
        r'\bpotential\s+to\s+(?:become|grow\s+into)\s+(?:a\s+)?(?:tech\s+)?lead\b',
    ]
    masked_title = title_lower
    for prog in progression_patterns:
        masked_title = re.sub(prog, 'progression_role', masked_title)

    # Include AVP, Associate Vice President, Advanced, and terminal digit tiers [2-9]$
    senior_keywords_pattern = (
        r'\b(?:senior|lead|manager|principal|director|head|vp|president|experienced|'
        r'architect|staff|expert|ii|iii|iv|v|vi|vii|viii|level\s*[2-9]|l[2-9]|avp|'
        r'associate\s+vice\s+president|advanced)\b|\bsr[\.,\s]|\bsr$|\b[2-9]$'
    )
    if re.search(senior_keywords_pattern, masked_title):
        return True

    # Check description header for disguised managerial career levels (e.g. Accenture Level 7)
    if description:
        first_1000 = description[:1000].lower()
        if re.search(r'\bcareer\s+level\s+[1-7]\b.*?(?:manager|leadership|lead\s+engineering)', first_1000, re.DOTALL):
            return True
        if re.search(r'\b(?:engineering\s+manager|quality\s+engineering\s+manager)\b', first_1000):
            return True

    return False

# Proposed requires_3_plus_years from Section 4.3
def requires_3_plus_years_v2(desc: str) -> bool:
    if not isinstance(desc, str):
        return False
    desc_lower = desc.lower().replace('\\', '')

    third_party_prefixes = (
        r'(?:our|the)\s+team\s+(?:has|have|with|of)',
        r'(?:work|working)\s+(?:with|alongside|beside|among)\s+(?:a\s+team|teams|colleagues|engineers|experts|leaders|seniors|other\s+developers)',
        r'(?:join|joining)\s+(?:a\s+)?team\s+(?:of|with)',
        r'(?:founded|established|started|operating|running)\s+(?:in|since|for|with)',
        r'(?:we\s+have|company\s+has|firm\s+has)\s+(?:over|more\s+than|been)',
        r'(?:our\s+company|our\s+firm|our\s+organisation)\s+(?:has|have)',
        r'colleagues?\s+(?:with|who\s+have)',
        r'mentors?\s+(?:with|who\s+have)',
        r'mentorship\s+from',
        r'(?:learn|learning)\s+from',
        r'(?:combined|collective|total)\s+experience',
        r'(?:history|heritage|industry)\s+(?:of|spanning)',
        r'(?:team|group|pool)\s+of\s+(?:engineers?|developers?|professionals?)\s+with',
        r'(?:senior\s+)?engineers?\s+(?:who\s+have|with\s+over)',
        r'in\s+\d{4}\s+with\s+\d+\s+years',
        r'(?:over\s+the\s+past|in\s+the\s+past)\s+\w+\s+years',
        r'with\s+(?:over|more\s+than)\s+\d+\s+years\s+(?:of\s+)?experience',
        r'(?:years\s+)?\w+\s+has\s+grown',
    )
    sentences = re.split(r'(?<=[.!?\n])\s*', desc_lower)
    candidate_sentences = [
        sent for sent in sentences
        if not any(re.search(pat, sent) for pat in third_party_prefixes)
    ]
    candidate_text = ' '.join(candidate_sentences)

    words_to_num_all = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12
    }
    def _tok_to_val(tok: str) -> int:
        tok_clean = tok.lower().strip()
        if tok_clean.isdigit():
            return int(tok_clean)
        return words_to_num_all.get(tok_clean, 0)

    # Guard against candidate age brackets (e.g. '(27 to 40 Yrs)')
    age_pattern = r'\(\s*(?:[2-9]\d)\s*(?:to|-)\s*(?:[2-9]\d)\s*yrs?\s*\)'
    candidate_text = re.sub(age_pattern, ' ', candidate_text, flags=re.I)

    # Standalone key-value experience range (e.g. 'Required Experience: 2-5')
    kv_range = re.search(r'(?:required|work|total)?\s*experience\s*:\s*(\d+)\s*[-\u2013to]+\s*(\d+)', candidate_text)
    if kv_range:
        lo, hi = int(kv_range.group(1)), int(kv_range.group(2))
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # Multi-line key-value experience header (e.g. 'Years of Experience required:\n\n 4')
    kv_single = re.search(r'years\s+of\s+experience\s+required\s*:\s*(\d+)', candidate_text)
    if kv_single and int(kv_single.group(1)) >= 3:
        return True

    num_tokens = r'(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'
    range_sep = r'(?:[-\u2013\u2014]|to|till|and)'
    range_pattern = fr'\b({num_tokens})\s*(?:\([^\)]+\)\s*)?{range_sep}\s*({num_tokens})\s*(?:\([^\)]+\)\s*)?(?:\+|or more|plus)?\s*(?:years?|yrs?\.?|yoe)\b'
    for m in re.finditer(range_pattern, candidate_text):
        lo, hi = _tok_to_val(m.group(1)), _tok_to_val(m.group(2))
        if lo >= 25 or hi >= 25:  # Ignore age specifications
            continue
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # Candidate experience single number check
    candidate_noranges = re.sub(range_pattern, ' ', candidate_text)
    min_pattern = fr'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?({num_tokens})\s*(?:years?|yrs?\.?)?'
    for m in re.finditer(min_pattern, candidate_noranges):
        num = _tok_to_val(m.group(1))
        if 3 <= num <= 20:
            return True

    plus_pattern = r'\b([3-9]|\d{2,})\s*(?:\+|(?:or\s+more)|(?:plus))\s*(?:years?|yrs?\.?|yoe)\b'
    for m in re.finditer(plus_pattern, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 20:
            return True

    exp_pattern = r'(?:experience|exp\.?)\s*(?:of|required|is)?\s*[:\-\s]\s*([3-9]|\d{2,})\s*(?:years?|yrs?\.?|yoe)\b'
    for m in re.finditer(exp_pattern, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 20:
            return True

    return False

# Proposed matches_out_of_scope_role from Section 4.4
def matches_out_of_scope_role_v2(title: str = "", description: str = "") -> bool:
    title_clean = title.lower() if title else ""
    # Allow Kotlin when paired with Java or Full Stack backend
    if 'kotlin' in title_clean and ('java' in title_clean or 'backend' in title_clean or 'full stack' in title_clean):
        pass
    elif OUT_OF_SCOPE_STACK_PATTERN.search(title_clean):
        return True

    if description:
        desc_lower = description.lower()
        is_qa_role = bool(re.search(r'\b(?:qa|quality assurance|tester|test automation|testing)\b', title_clean))
        is_fullstack_role = bool(re.search(r'\b(?:full stack|fullstack|software engineer|developer)\b', title_clean))

        for oos_kw in ['php', 'laravel', 'ruby', 'rails', 'ios', 'swift', 'swiftui', 'android', 'salesforce', 'apex', 'sap', 'abap', 'drupal', 'magento', 'wordpress', 'flutter', 'react native']:
            if re.search(r'\b' + oos_kw + r'\b', desc_lower):
                # Context 1: Salesforce mentioned as a tested SaaS app in QA roles
                if oos_kw == 'salesforce' and is_qa_role:
                    if re.search(r'(?:testing|tested|products\s+such\s+as|integrations?\s+with).*?salesforce', desc_lower):
                        continue
                # Context 2: Flutter mentioned as one optional mobile framework in fullstack roles
                if oos_kw in ['flutter', 'react native'] and is_fullstack_role:
                    if re.search(r'react.*?flutter|flutter.*?react|node.*?flutter', desc_lower):
                        continue
                # Context 3: Good to have / Optional qualification
                if re.search(r'(?:good\s+to\s+have|nice\s+to\s+have|preferred|plus|optional)[^.\n]*?\b' + oos_kw + r'\b', desc_lower):
                    continue
                return True

    return False

# Proposed is_relevant_jd from Section 4.4
def is_relevant_jd_v2(description: str, title: str = "") -> bool:
    if not description or not isinstance(description, str):
        return False
    desc_clean = description.lower().replace(r'\-', '-').replace(r'\_', '_')
    title_clean = title.lower() if title else ""

    if matches_out_of_scope_role_v2(title, description):
        return False

    has_anchor = (
        any(kw in desc_clean for kw in DOMAIN_ANCHORS) or
        any(kw in title_clean for kw in DOMAIN_ANCHORS)
    )
    has_tool = (
        any(kw in desc_clean for kw in TECH_TOOLS) or
        any(kw in title_clean for kw in TECH_TOOLS)
    )
    return has_anchor and has_tool

def evaluate_job(job: Dict[str, Any]) -> str:
    title = job.get('title', '')
    desc = job.get('description', '')
    
    if matches_senior_title_v2(title, desc):
        return "FAIL_SENIOR_TITLE"
    if matches_out_of_scope_role_v2(title, desc):
        return "FAIL_OUT_OF_SCOPE"
    if requires_3_plus_years_v2(desc):
        return "FAIL_EXPERIENCE"
    if not is_relevant_jd_v2(desc, title):
        return "FAIL_IRRELEVANT"
    return "PASS"

# Test FP jobs
print("=== TESTING FALSE POSITIVES (Expected: all should FAIL) ===")
fp_indices = [fp['job_index'] for fp in fp_data]
for idx in fp_indices:
    job = raw_jobs[idx]
    decision = evaluate_job(job)
    print(f"FP Job {idx} ({job.get('title')}): result = {decision}")

# Test FN jobs
print("\n=== TESTING FALSE NEGATIVES (Expected: all should PASS) ===")
fn_indices = [fn['job_index'] for fn in fn_data]
for idx in fn_indices:
    job = raw_jobs[idx]
    decision = evaluate_job(job)
    print(f"FN Job {idx} ({job.get('title')}): result = {decision}")

# Test All 1137 jobs against Ground Truth
print("\n=== TESTING ALL 1,137 JOBS AGAINST GROUND TRUTH ===")
tp, tn, fp, fn = 0, 0, 0, 0
discrepancies = []

for idx, (job, gt) in enumerate(zip(raw_jobs, gt_data)):
    expected = gt.get('expected_outcome')
    pred_reason = evaluate_job(job)
    predicted = "PASS" if pred_reason == "PASS" else "FAIL"

    if expected == "PASS" and predicted == "PASS":
        tp += 1
    elif expected == "FAIL" and predicted == "FAIL":
        tn += 1
    elif expected == "FAIL" and predicted == "PASS":
        fp += 1
        discrepancies.append((idx, job.get('title'), "NEW_FP", pred_reason))
    elif expected == "PASS" and predicted == "FAIL":
        fn += 1
        discrepancies.append((idx, job.get('title'), "NEW_FN", pred_reason))

print(f"Total: {len(raw_jobs)}, TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")
print(f"Accuracy: {(tp + tn) / len(raw_jobs):.4%}")
if discrepancies:
    print(f"Discrepancies ({len(discrepancies)}):")
    for d in discrepancies:
        print(d)
else:
    print("ALL 1,137 JOBS MATCH GROUND TRUTH PERFECTLY (100.00%)!")
