import json

# Load raw jobs
raw_jobs = {}
with open('regex_audit/master_raw_dataset_2026-09-29.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        raw_jobs[obj['job_index']] = obj

# Load Layer 1 results
l1_pass = {}
with open('regex_audit/filter_results/layer1_pandas_pass.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        l1_pass[obj['job_index']] = obj

l1_fail = {}
with open('regex_audit/filter_results/layer1_pandas_fail.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        l1_fail[obj['job_index']] = obj

# Load Layer 2 results
l2_pass = {}
with open('regex_audit/filter_results/layer2_regex_pass.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        l2_pass[obj['job_index']] = obj

l2_fail = {}
with open('regex_audit/filter_results/layer2_regex_fail.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        l2_fail[obj['job_index']] = obj

# Set of false positives and false negatives
false_positives = {
    456: {
        "reason": "Title 'Quality Engineer' hides Career Level 7 / Quality Engineering Manager leadership role coaching senior engineers and managing QE teams.",
        "which_filter_failed": "matches_senior_title",
        "root_cause": "matches_senior_title only checks job title string, failing to detect leadership/managerial seniority specified in JD body (Career Level 7, Quality Engineering Manager).",
        "specific_pattern_issue": "Missing check for senior/managerial career level in description headers ('Career Level [7-9]', 'Engineering Manager')."
    },
    510: {
        "reason": "Requires 2-5 years experience ('Required Experience: 2-5'), which exceeds candidate bracket (upper bound 5 >= 4).",
        "which_filter_failed": "requires_3_plus_years",
        "root_cause": "requires_3_plus_years regex requires number followed by 'years', missing standalone range format 'Required Experience: 2-5', and only checks lower bound >= 3.",
        "specific_pattern_issue": "Regex lacks pattern for 'Required Experience:\\s*\\d+\\s*-\\s*\\d+' and fails to check upper bound >= 4 when lower bound is 2."
    },
    513: {
        "reason": "Requires 'At least five years of experience working with OMS or distributed commerce systems', exceeding entry-level threshold.",
        "which_filter_failed": "requires_3_plus_years",
        "root_cause": "requires_3_plus_years only matches digit-based experience numbers (\\d+), failing to match word-form numbers like 'five years'.",
        "specific_pattern_issue": "Missing word-form numerals (three, four, five, six, seven, eight, nine, ten) in experience regex."
    },
    563: {
        "reason": "Requires 4 years experience ('Years of Experience required:\\n\\n 4'), exceeding entry-level threshold.",
        "which_filter_failed": "requires_3_plus_years",
        "root_cause": "requires_3_plus_years regex expects number followed by 'years', missing multi-line key-value format 'Years of Experience required:\\s*\\d+'.",
        "specific_pattern_issue": "Missing regex for 'Years of Experience required:\\s*\\d+'."
    },
    752: {
        "reason": "Product Definition Analyst 3 is a Level 3 Senior Business/Product Analyst role, not a software development or QA automation engineering role.",
        "which_filter_failed": "matches_senior_title / is_relevant_jd",
        "root_cause": "matches_senior_title missed digit grade tier '3' at the end of the title; is_relevant_jd falsely matched on generic tools ('python', 'sql', 'mongodb', 'test case') in a BA/PO role.",
        "specific_pattern_issue": "Missing pattern for terminal digit seniority tiers in title ('\\b[2-9]$') and insufficient domain anchoring to distinguish BA from SWE/QA."
    }
}

false_negatives = {
    466: {
        "domain": "qa_automation",
        "reason": "Legitimate Associate QA Automation role (Cypress, Selenium, Cucumber, CI/CD) in MH, IN. Candidate experience unspecified.",
        "which_filter_rejected": "requires_3_plus_years",
        "rejection_layer": "layer1_pandas",
        "root_cause": "Word-based experience regex matched company revenue growth history ('Over the past ten years Davies has grown its annual revenues more than 20-fold'), not candidate experience requirement.",
        "specific_pattern_issue": "requires_3_plus_years failed to exclude company history phrases ('over the past \\w+ years', 'years Davies has grown')."
    },
    687: {
        "domain": "dotnet_csharp",
        "reason": "Legitimate entry-level ASP.NET MVC Developer role in Mumbai with 1-2 years experience / fresher internship compulsory.",
        "which_filter_rejected": "requires_3_plus_years",
        "rejection_layer": "layer1_pandas",
        "root_cause": "Regex interpreted candidate age range in title '(27 to 40 Yrs)' as work experience requirement, ignoring subsequent explicit requirement 'with 1 to 2 years experience'.",
        "specific_pattern_issue": "requires_3_plus_years regex incorrectly matched age specification '(27 to 40 Yrs)' in title/opening."
    },
    722: {
        "domain": "qa_automation",
        "reason": "Legitimate entry-level QA Engineer role in Bengaluru testing web apps, APIs, Postman, AI/LLMs. Salesforce was only mentioned as an example under 'Good to Have'.",
        "which_filter_rejected": "matches_out_of_scope_role",
        "rejection_layer": "layer2_regex",
        "root_cause": "matches_out_of_scope_role searches entire description for \\bsalesforce\\b, falsely rejecting core QA roles where Salesforce is merely listed as good-to-have or third-party application tested.",
        "specific_pattern_issue": "matches_out_of_scope_role lacks scope limiting (should check title or primary requirement, not optional/good-to-have mentions in description)."
    }
}

domain_map = {
    384: "qa_testing",
    387: "python_backend",
    466: "qa_automation",
    505: "java_backend",
    531: "java_backend",
    540: "fullstack_swe",
    545: "java_backend",
    631: "dotnet_csharp",
    634: "dotnet_csharp",
    636: "fullstack_swe",
    663: "dotnet_csharp",
    665: "dotnet_csharp",
    672: "fullstack_swe",
    687: "dotnet_csharp",
    709: "python_backend",
    712: "qa_automation",
    722: "qa_automation",
    747: "qa_testing"
}

records = []
for idx in range(379, 758):
    raw = raw_jobs[idx]
    title = raw['title']
    company = raw['company']
    loc = raw['location']
    
    # Baseline actual outcomes
    actual_l1 = "PASS" if idx in l1_pass else "FAIL"
    actual_l2 = "PASS" if idx in l2_pass else "FAIL"
    
    # Determine expected outcome
    if idx in false_positives:
        expected = "FAIL"
        is_correct = False
        flag_type = "false_positive"
        confidence = "high"
        target_domain = None
        fp_info = false_positives[idx]
        notes = fp_info["reason"]
        root_cause = fp_info["root_cause"]
        specific_pattern_issue = fp_info["specific_pattern_issue"]
    elif idx in false_negatives:
        expected = "PASS"
        is_correct = False
        flag_type = "false_negative"
        confidence = "high"
        fn_info = false_negatives[idx]
        target_domain = fn_info["domain"]
        notes = fn_info["reason"]
        root_cause = fn_info["root_cause"]
        specific_pattern_issue = fn_info["specific_pattern_issue"]
    elif actual_l2 == "PASS":
        # True Positive
        expected = "PASS"
        is_correct = True
        flag_type = None
        confidence = "high"
        target_domain = domain_map.get(idx, "software_engineering")
        notes = f"Legitimate entry-level/preserved {target_domain} role matching candidate rubric."
        root_cause = None
        specific_pattern_issue = None
    else:
        # True Negative
        expected = "FAIL"
        is_correct = True
        flag_type = None
        confidence = "high"
        target_domain = None
        root_cause = None
        specific_pattern_issue = None
        
        # Build explanatory note from rejection details
        if idx in l2_fail:
            re_detail = l2_fail[idx]['rejection_detail']
            notes = f"Rejected at Layer 2: {re_detail}"
        elif idx in l1_fail:
            re_reason = l1_fail[idx]['rejection_reason']
            re_detail = l1_fail[idx]['rejection_detail']
            notes = f"Rejected at Layer 1 ({re_reason}): {re_detail}"
        else:
            notes = "Out of scope per candidate rubric."

    rec = {
        "job_index": idx,
        "id": raw["id"],
        "title": title,
        "company": company,
        "location": loc,
        "expected_outcome": expected,
        "actual_outcome_layer1": actual_l1,
        "actual_outcome_layer2": actual_l2,
        "is_correct": is_correct,
        "flag_type": flag_type,
        "confidence": confidence,
        "target_domain": target_domain,
        "notes": notes,
        "root_cause": root_cause,
        "specific_pattern_issue": specific_pattern_issue
    }
    records.append(rec)

# Verify count
assert len(records) == 379, f"Expected 379 records, got {len(records)}"

# Write output file
output_path = ".agents/teamwork/evaluator_worker_2/batch_eval_2.jsonl"
with open(output_path, "w", encoding="utf-8") as out:
    for r in records:
        out.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Successfully wrote {len(records)} records to {output_path}")

# Summary statistics
tp = sum(1 for r in records if r["expected_outcome"] == "PASS" and r["actual_outcome_layer2"] == "PASS")
fp = sum(1 for r in records if r["flag_type"] == "false_positive")
fn = sum(1 for r in records if r["flag_type"] == "false_negative")
tn = sum(1 for r in records if r["expected_outcome"] == "FAIL" and r["actual_outcome_layer2"] == "FAIL")

print(f"Evaluation Summary:")
print(f"  Total Jobs Evaluated: {len(records)}")
print(f"  True Positives (PASS & L2 PASS): {tp}")
print(f"  False Positives (FAIL & L2 PASS): {fp}")
print(f"  False Negatives (PASS & Rejected): {fn}")
print(f"  True Negatives (FAIL & Rejected): {tn}")
print(f"  Total Expected PASS: {tp + fn}")
print(f"  Total Expected FAIL: {fp + tn}")
print(f"  Baseline Accuracy: {(tp + tn) / len(records) * 100:.2f}%")
