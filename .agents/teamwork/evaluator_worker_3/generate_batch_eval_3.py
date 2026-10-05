import json
import re
import sys

def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

raw_jobs = {d['job_index']: d for d in load_jsonl('regex_audit/master_raw_dataset_2026-09-29.jsonl')}
l1_pass = {d['job_index']: d for d in load_jsonl('regex_audit/filter_results/layer1_pandas_pass.jsonl')}
l1_fail = {d['job_index']: d for d in load_jsonl('regex_audit/filter_results/layer1_pandas_fail.jsonl')}
l2_pass = {d['job_index']: d for d in load_jsonl('regex_audit/filter_results/layer2_regex_pass.jsonl')}
l2_fail = {d['job_index']: d for d in load_jsonl('regex_audit/filter_results/layer2_regex_fail.jsonl')}

batch_indices = list(range(758, 1137))
eval_records = []

# Known Discrepancy Sets
FALSE_POSITIVES = {796, 1038}
FALSE_NEGATIVES = {1027}

# True Positives in Batch 3
TRUE_POSITIVES = {821, 830, 833, 910, 911, 1018, 1020, 1021, 1035, 1048, 1051, 1052}

# Domain mapping helper
def infer_domain(title, desc):
    t_low = title.lower()
    d_low = desc.lower()
    combined = t_low + " " + d_low
    if any(k in t_low for k in ['ai', 'agentic', 'machine learning', 'llm', 'genai']):
        return "ai_ml"
    if any(k in t_low for k in ['java', 'spring']):
        if any(k in combined for k in ['react', 'angular', 'full stack', 'fullstack']):
            return "java_fullstack"
        return "java_backend"
    if any(k in t_low for k in ['python']):
        if any(k in combined for k in ['react', 'angular', 'full stack', 'fullstack']):
            return "full_stack_python"
        return "python_backend"
    if any(k in t_low for k in ['.net', 'dotnet', 'c#', 'csharp']):
        if any(k in combined for k in ['react', 'angular', 'full stack', 'fullstack']):
            return "dotnet_fullstack"
        return "dotnet_backend"
    if any(k in t_low for k in ['qa', 'tester', 'testing', 'automation', 'sdet']):
        return "qa_automation"
    if any(k in t_low for k in ['mern', 'react', 'node', 'express']):
        return "mern_stack"
    if any(k in t_low for k in ['full stack', 'fullstack', 'software engineer', 'software developer', 'sde']):
        return "full_stack"
    return None

for idx in batch_indices:
    r = raw_jobs[idx]
    title = r['title']
    company = r['company']
    location = r['location']
    job_id = r['id']
    desc = r['description']
    
    # Layer outcomes
    actual_l1 = "PASS" if idx in l1_pass else "FAIL"
    actual_l2 = "PASS" if idx in l2_pass else "FAIL"
    
    # Expected outcome determination
    if idx in TRUE_POSITIVES or idx in FALSE_NEGATIVES:
        expected_outcome = "PASS"
    else:
        expected_outcome = "FAIL"
        
    is_correct = (expected_outcome == actual_l2)
    
    if idx in FALSE_POSITIVES:
        flag_type = "false_positive"
    elif idx in FALSE_NEGATIVES:
        flag_type = "false_negative"
    else:
        flag_type = None
        
    confidence = "high"
    target_domain = infer_domain(title, desc)
    root_cause = None
    specific_pattern_issue = None
    
    # Detailed notes, root cause, pattern issues
    if idx == 796:
        # Software Engineer, AVP | NatWest Group
        target_domain = "java_backend"
        notes = "Senior management executive role at Associate Vice President level ('We're offering this role at associate vice president level'). Title contains 'AVP'."
        root_cause = "matches_senior_title in src/scorer.py failed to recognize executive/senior grade acronym 'AVP' (Associate Vice President) in job title."
        specific_pattern_issue = "matches_senior_title lacks regex boundary match for r'\\bavp\\b' and 'associate vice president'"
    elif idx == 1038:
        # Fullstack Python Engineer | Azuga, Inc.
        target_domain = "full_stack_python"
        notes = "Strictly requires 'At least 3 years of experience working with React.' Exceeds entry-level 0-2 / 1-3 years experience ceiling."
        root_cause = "requires_3_plus_years incorrectly stripped qualification sentence '* At least 3 years of experience working with React' because third_party_prefixes over-eagerly matched '(?:work|working)\\s+(?:with|alongside|beside|among)', treating candidate skill experience as company/colleague description."
        specific_pattern_issue = "requires_3_plus_years third_party_prefixes pattern r'(?:work|working)\\s+(?:with|alongside|beside|among)' falsely stripped candidate qualification sentence containing 'working with <tech>'"
    elif idx == 1027:
        # Software Engineer – Full Stack (.NET/React) | DYMATRIX
        target_domain = "dotnet_fullstack"
        notes = "Valid entry-level Full Stack role (.NET/React/TypeScript/AI coding) in Bengaluru with no candidate experience requirement. Falsely rejected by Layer 1 experience filter due to company history sentence ('With over 20 years of experience, DYMATRIX is...')."
        root_cause = "requires_3_plus_years in Layer 1 failed to identify 'With over 20 years of experience, DYMATRIX is...' as company background text, mistakenly attributing 20 years to candidate experience."
        specific_pattern_issue = "requires_3_plus_years third_party_prefixes lacks pattern for company background clause r'\\bwith\\s+(?:over|more\\s+than)\\s+\\d+\\s+years\\s+of\\s+experience\\b'"
    elif idx in TRUE_POSITIVES:
        if idx == 821:
            notes = "Valid entry-level Software Engineer role at Cisco (Bachelors + 2 yrs or Masters + 0 yrs, 1-2 yrs SDLC, Python/Go) in Bengaluru."
        elif idx == 830:
            notes = "Valid Full Stack Engineer role at Optum India (Java, Python, React/Angular, 2+ yrs experience preserved per 1-3 yr rule) in Bengaluru."
        elif idx == 833:
            notes = "Valid Intermediate Software Engineer role at Q2 (Python, SQL, 2+ yrs experience preserved) in Bengaluru."
        elif idx == 910:
            notes = "Valid AI / Python Full-Stack Engineer role at Tavant (Python, FastAPI, LangChain, LLM APIs, RAG, React) in Bengaluru."
        elif idx == 911:
            notes = "Valid Python Developer role at NTT DATA (Python, REST APIs, microservices, remote eligible) in Bangalore Urban."
        elif idx == 1018:
            notes = "Valid .NET Full Stack Developer role at Infosys (C#, ASP.NET Core, React/Angular, 2-3 yrs experience preserved) in Bengaluru."
        elif idx == 1020:
            notes = "Valid Entry-Level Full Stack Developer role at Ucanly (web development, JavaScript, third-party integrations) in Bengaluru."
        elif idx == 1021:
            notes = "Valid Java Full Stack Engineer role at ITC Infotech (Java, React, AWS, self-starter entry/mid profile) in Bengaluru/Pune (Hybrid)."
        elif idx == 1035:
            notes = "Valid AI Forward Deployed Engineer role at Cursor (Python, TypeScript, AI workflows) in Bengaluru/Mumbai."
        elif idx == 1048:
            notes = "Valid Full Stack Developer role at QualityAI (Python, FastAPI, React, Angular, AWS) in Bengaluru."
        elif idx == 1051:
            notes = "Valid Java Full Stack Developer role at C5i (Java, Spring Boot, Microservices, Angular, MongoDB) in Bengaluru."
        elif idx == 1052:
            notes = "Valid .NET Full Stack Developer role at CGI (.NET, C#, HTML/CSS/JavaScript, React/Angular) in Bengaluru."
    elif idx in l2_fail:
        # Job 1075
        fail_rec = l2_fail[idx]
        notes = f"Correctly rejected by Layer 2 ({fail_rec['rejection_reason']}): {fail_rec['rejection_detail']}."
    else:
        # Layer 1 fail records
        fail_rec = l1_fail[idx]
        reason = fail_rec['rejection_reason']
        detail = fail_rec['rejection_detail']
        if reason == 'duplicate_url':
            notes = f"Correctly dropped in Layer 1: duplicate listing of earlier raw record ({detail})."
            target_domain = None
        elif reason == 'stale':
            notes = f"Correctly dropped in Layer 1: job posting is stale (>72h old, posted {r.get('date_posted')})."
            target_domain = None
        elif reason == 'location_mismatch':
            notes = f"Correctly dropped in Layer 1: location '{location}' does not match target metros (Pune, Mumbai, Bangalore) or remote."
            target_domain = None
        elif reason == 'senior_title':
            notes = f"Correctly dropped in Layer 1: senior title ({title}) violates entry-level rubric."
        elif reason == 'experience_3_plus':
            notes = f"Correctly dropped in Layer 1: candidate experience requirement strictly exceeds entry-level ceiling ({detail})."

    record = {
        "job_index": idx,
        "id": job_id,
        "title": title,
        "company": company,
        "location": location,
        "expected_outcome": expected_outcome,
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
    eval_records.append(record)

out_path = r'c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_3\batch_eval_3.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for rec in eval_records:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

print(f"Successfully wrote {len(eval_records)} records to {out_path}!")
