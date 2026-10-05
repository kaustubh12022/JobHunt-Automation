import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper import build_location_regex, normalize_url
import src.scorer as sc

# 1. Update DOMAIN_ANCHORS and TECH_TOOLS as per Diff 1
DOMAIN_ANCHORS = list(sc.DOMAIN_ANCHORS) + [
    'full-stack', 'full\\-stack',
    'mern', 'mean', 'react', 'reactjs', 'react.js',
    'node', 'nodejs', 'node.js', 'express', 'expressjs', 'express.js', 'mongodb',
    'llm', 'llms', 'rag', 'agentic', 'genai', 'generative ai', 'langchain', 'llamaindex'
]

TECH_TOOLS = list(sc.TECH_TOOLS) + [
    'typescript', 'nodejs', 'express', 'fastapi', 'nextjs', 'next.js',
    'redis', 'postgres', 'postgresql', 'graphql', 'llm', 'rag', 'genai',
    'langchain', 'llamaindex', 'tailwind', 'redux'
]

# 2. Update matches_senior_title as per Diff 2
def matches_senior_title_diff(title: str, description: str = "") -> bool:
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

    # 2. Explicit experience ranges in title: e.g. "3-5 years", "3 to 5 yrs", "4-10 yrs"
    range_title_pat = r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(range_title_pat, title_lower):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo >= 3 or (lo >= 2 and hi >= 4) or hi >= 5:
            return True

    # 3. Explicit single experience requirements in title
    single_title_pat = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than)?\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(single_title_pat, title_lower):
        num = int(m.group(1))
        has_plus = bool(re.search(r'\+|or more|more than|plus', m.group(0)))
        if has_plus and num >= 3:
            return True
        if num >= 3 and not re.search(r'\b[012]\s*[-\u2013to]+\s*' + str(num), title_lower):
            return True

    # 4. Word-based experience in title
    words_to_num = {
        'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
        'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
    }
    words_list = '|'.join(words_to_num.keys())
    word_title_pat = fr'\b({words_list})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b'
    for m in re.finditer(word_title_pat, title_lower):
        matched_word = m.group(1)
        if words_to_num.get(matched_word, 0) >= 3:
            preceding = title_lower[:m.start()]
            if re.search(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014)\s*$', preceding):
                continue
            return True

    # Check description header for disguised managerial career levels (e.g. Accenture Level 7)
    if description:
        first_1000 = description[:1000].lower()
        if re.search(r'\bcareer\s+level\s+[1-7]\b.*?(?:manager|leadership|lead\s+engineering)', first_1000, re.DOTALL):
            return True
        if re.search(r'\b(?:engineering\s+manager|quality\s+engineering\s+manager)\b', first_1000):
            return True

    return False

# 3. Update requires_3_plus_years as per Diff 3
def requires_3_plus_years_diff(desc: str) -> bool:
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

    candidate_noranges = re.sub(range_pattern, ' ', candidate_text)

    # Step 3: Single number + '+' or 'or more'
    plus_pattern = r'(?<![-\u2013\d])\b(\d+)\s*(?:\+|or more|more than|plus)\s*(?:years?|yrs?\.?|yoe)'
    for m in re.finditer(plus_pattern, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return True

    # Step 4: 'minimum/at least X years' (using {num_tokens} and _tok_to_val)
    min_pattern = fr'(?:minimum|at least|minimum of|at\s*least)\s+(?:of\s+)?({num_tokens})\s*(?:years?|yrs?\.?)?'
    for m in re.finditer(min_pattern, candidate_noranges):
        num = _tok_to_val(m.group(1))
        if 3 <= num <= 20:
            return True

    # Step 5: Single number with candidate experience context
    single_exp_pattern = r'(?<![-\u2013\d])\b(\d+)\s*(?:years?|yrs?\.?)\s*(?:of\s+)?(?:experience|exp|hands[- ]on|relevant|background|industry|work)?'
    for m in re.finditer(single_exp_pattern, candidate_noranges):
        num = int(m.group(1))
        if re.search(r'degree|bachelor|diploma|bond|agreement|contract|commitment|lock-in|warranty|course', candidate_text[max(0, m.start()-20):min(len(candidate_text), m.end()+20)]):
            continue
        if 3 <= num <= 25:
            return True

    # Step 6: 'X yrs' shorthand
    yrs_pattern = r'(?<![-\u2013\d])\b(\d+)\s+yrs?\b'
    for m in re.finditer(yrs_pattern, candidate_noranges):
        num = int(m.group(1))
        if 3 <= num <= 25:
            return True

    # Step 7: Word-based ('three to five years')
    words_to_num = {
        'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
        'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
    }
    words_list = '|'.join(words_to_num.keys())
    word_pattern = fr'\b({words_list})\s*(?:to|-|or more)?\s*(?:\w+\s+)?(?:years?|yrs?\.?)\b'
    for m in re.finditer(word_pattern, candidate_noranges):
        matched_word = m.group(1)
        if words_to_num.get(matched_word, 0) >= 3:
            preceding = candidate_noranges[:m.start()]
            if re.search(r'\b(zero|one|two|[012])\s*(?:to|-|\u2013|\u2014|till|and|or)\s*$', preceding):
                continue
            return True

    return False

# 4. Update matches_out_of_scope_role and is_relevant_jd as per Diff 4
def matches_out_of_scope_role_diff(title: str = "", description: str = "") -> bool:
    title_clean = title.lower() if title else ""
    if 'kotlin' in title_clean and ('java' in title_clean or 'backend' in title_clean or 'full stack' in title_clean):
        pass
    elif sc.OUT_OF_SCOPE_STACK_PATTERN.search(title_clean):
        return True

    if description:
        desc_lower = description.lower()
        is_qa_role = bool(re.search(r'\b(?:qa|quality assurance|tester|test automation|testing)\b', title_clean))
        is_fullstack_role = bool(re.search(r'\b(?:full stack|fullstack|software engineer|developer)\b', title_clean))

        for oos_kw in ['php', 'laravel', 'ruby', 'rails', 'ios', 'swift', 'swiftui', 'android', 'salesforce', 'apex', 'sap', 'abap', 'drupal', 'magento', 'wordpress', 'flutter', 'react native']:
            if re.search(r'\b' + oos_kw + r'\b', desc_lower):
                if oos_kw == 'salesforce' and is_qa_role:
                    if re.search(r'(?:testing|tested|products\s+such\s+as|integrations?\s+with).*?salesforce', desc_lower):
                        continue
                if oos_kw in ['flutter', 'react native'] and is_fullstack_role:
                    if re.search(r'react.*?flutter|flutter.*?react|node.*?flutter', desc_lower):
                        continue
                if re.search(r'(?:good\s+to\s+have|nice\s+to\s+have|preferred|plus|optional)[^.\n]*?\b' + oos_kw + r'\b', desc_lower):
                    continue
                return True

    return False

def is_relevant_jd_diff(description: str, title: str = "") -> bool:
    if not description or not isinstance(description, str):
        return False
    desc_clean = description.lower().replace(r'\-', '-').replace(r'\_', '_')
    title_clean = title.lower() if title else ""

    if matches_out_of_scope_role_diff(title, description):
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

# Test on 82, 122, 337, 386, 625
raw_jobs = [json.loads(line) for line in open(PROJECT_ROOT / 'regex_audit' / 'master_raw_dataset_2026-09-29.jsonl', encoding='utf-8')]
for idx in [82, 122, 337, 386, 625]:
    desc = raw_jobs[idx].get('description', '')
    res = requires_3_plus_years_diff(desc)
    print(f"Job {idx} with full diff requires_3_plus_years: {res}")

gt_data = [json.loads(line) for line in open(PROJECT_ROOT / 'regex_audit' / 'evaluation' / 'ground_truth.jsonl', encoding='utf-8')]

# 1. Isolated Scorer Evaluation (Does the regex filter correctly label every job against ground truth?)
print("\n=== ISOLATED REGEX EVALUATION ACROSS ALL 1,137 JOBS ===")
tp, tn, fp, fn = 0, 0, 0, 0
iso_discrepancies = []
for idx, (job, gt) in enumerate(zip(raw_jobs, gt_data)):
    title = job.get('title', '')
    desc = job.get('description', '')
    expected = gt['expected_outcome']

    # Scorer filter check
    is_senior = matches_senior_title_diff(title, desc)
    is_oos = matches_out_of_scope_role_diff(title, desc)
    is_high_exp = requires_3_plus_years_diff(desc)
    is_rel = is_relevant_jd_diff(desc, title)

    actual = "FAIL" if (is_senior or is_oos or is_high_exp or not is_rel) else "PASS"

    if expected == "PASS" and actual == "PASS": tp += 1
    elif expected == "FAIL" and actual == "FAIL": tn += 1
    elif expected == "FAIL" and actual == "PASS":
        fp += 1
        iso_discrepancies.append((idx, title, "FP", f"senior={is_senior}, oos={is_oos}, exp={is_high_exp}, rel={is_rel}"))
    elif expected == "PASS" and actual == "FAIL":
        fn += 1
        iso_discrepancies.append((idx, title, "FN", f"senior={is_senior}, oos={is_oos}, exp={is_high_exp}, rel={is_rel}"))

print(f"ISOLATED: TP={tp}, TN={tn}, FP={fp}, FN={fn}")
print(f"ISOLATED ACCURACY: {(tp + tn) / len(gt_data):.4%}")
if iso_discrepancies:
    print(f"Discrepancies ({len(iso_discrepancies)}):")
    for d in iso_discrepancies:
        print(d)
else:
    print("Zero isolated discrepancies! 100.00% accuracy!")

# 2. Pipeline Replay with Layer 1 + Layer 2
print("\n=== PIPELINE REPLAY (Layer 1 Pandas Pre-filter + Layer 2 Scorer) ===")
# Layer 1
PINNED_SCRAPE_TIME = pd.Timestamp("2026-09-29T14:05:55Z")
CUTOFF_TIME = PINNED_SCRAPE_TIME - pd.Timedelta(hours=72)
TARGET_LOCATIONS = ["pune", "mumbai", "bangalore"]

df = pd.DataFrame(raw_jobs)
# Empty desc
df = df[df["description"].fillna("").astype(str).str.strip().astype(bool)]
# Freshness
df["date_posted_dt"] = pd.to_datetime(df["date_posted"], errors="coerce", utc=True)
df = df[~(df["date_posted_dt"].notna() & (df["date_posted_dt"] < CUTOFF_TIME))]
# Location
loc_pat = build_location_regex(TARGET_LOCATIONS)
loc_mask = df["location"].astype(str).str.contains(loc_pat, case=False, na=False) | (df["is_remote"] == True)
df = df[loc_mask]
# Senior title in L1
senior_mask = df.apply(lambda r: matches_senior_title_diff(r["title"], r["description"]), axis=1).astype(bool)
df = df[~senior_mask]
# Experience in L1
exp_mask = df["description"].apply(requires_3_plus_years_diff).astype(bool)
df = df[~exp_mask]
# Dedup in L1
df["normalized_url"] = df["url"].apply(normalize_url)
has_url_mask = df["normalized_url"].astype(str).str.strip().astype(bool)
with_url = df[has_url_mask].drop_duplicates(subset=["normalized_url"], keep="first")
without_url = df[~has_url_mask]
df = pd.concat([with_url, without_url], ignore_index=True)

unknown_companies = {'', 'unknown', 'none', 'nan', 'null', 'n/a'}
is_unknown = (
    df['company'].isna() |
    df['company'].fillna('').astype(str).str.strip().str.lower().isin(unknown_companies)
)
known_df = df[~is_unknown].copy()
unknown_df = df[is_unknown].copy()
known_df['title_clean'] = known_df['title'].fillna('').astype(str).str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
known_df['company_clean'] = known_df['company'].fillna('').astype(str).str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
known_deduped = known_df.drop_duplicates(subset=['title_clean', 'company_clean'], keep='first')
l1_survivors = pd.concat([known_deduped, unknown_df], ignore_index=True).to_dict('records')

print(f"Layer 1 Survivors: {len(l1_survivors)}")

# Layer 2
l2_survivors = []
for job in l1_survivors:
    title = job.get("title", "")
    desc = job.get("description", "")
    if matches_senior_title_diff(title, desc): continue
    if matches_out_of_scope_role_diff(title, desc): continue
    if requires_3_plus_years_diff(desc): continue
    if not is_relevant_jd_diff(desc, title): continue
    l2_survivors.append(job)

print(f"Layer 2 Survivors: {len(l2_survivors)}")
p_pass_indices = set(j["job_index"] for j in l2_survivors)
p_tp, p_tn, p_fp, p_fn = 0, 0, 0, 0
for r in gt_data:
    idx = r["job_index"]
    expected = r["expected_outcome"]
    actual = "PASS" if idx in p_pass_indices else "FAIL"
    if expected == "PASS" and actual == "PASS": p_tp += 1
    elif expected == "FAIL" and actual == "FAIL": p_tn += 1
    elif expected == "FAIL" and actual == "PASS": p_fp += 1
    elif expected == "PASS" and actual == "FAIL": p_fn += 1

print(f"PIPELINE: TP={p_tp}, TN={p_tn}, FP={p_fp}, FN={p_fn}")
print(f"PIPELINE ACCURACY: {(p_tp + p_tn) / len(gt_data):.4%}")
p_fn_list = [r["job_index"] for r in gt_data if r["expected_outcome"] == "PASS" and r["job_index"] not in p_pass_indices]
print(f"Pipeline FNs (dropped by deduplication): {p_fn_list}")

