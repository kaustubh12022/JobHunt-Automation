import json
import sys

path = r'c:\Users\kalek\Desktop\Projects\Job_Hunt\.agents\teamwork\evaluator_worker_3\batch_eval_3.jsonl'
records = []
with open(path, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, start=1):
        try:
            d = json.loads(line)
            records.append(d)
        except Exception as e:
            print(f"Error on line {line_num}: {e}")
            sys.exit(1)

print(f"Total records read: {len(records)}")
assert len(records) == 379, f"Expected 379 records, got {len(records)}"

# Check index continuity
indices = [r['job_index'] for r in records]
assert indices == list(range(758, 1137)), "Indices do not match range(758, 1137)"

# Check required fields
required_fields = [
    'job_index', 'title', 'company', 'expected_outcome',
    'actual_outcome_layer1', 'actual_outcome_layer2',
    'is_correct', 'flag_type', 'confidence', 'notes',
    'root_cause', 'specific_pattern_issue'
]

fp_count = 0
fn_count = 0
correct_count = 0

for r in records:
    for field in required_fields:
        assert field in r, f"Field '{field}' missing in job {r.get('job_index')}"
    
    assert r['expected_outcome'] in ['PASS', 'FAIL'], f"Invalid expected_outcome in job {r['job_index']}"
    assert r['actual_outcome_layer1'] in ['PASS', 'FAIL'], f"Invalid actual_outcome_layer1 in job {r['job_index']}"
    assert r['actual_outcome_layer2'] in ['PASS', 'FAIL'], f"Invalid actual_outcome_layer2 in job {r['job_index']}"
    assert isinstance(r['is_correct'], bool), f"Invalid is_correct type in job {r['job_index']}"
    assert r['confidence'] in ['high', 'medium', 'low'], f"Invalid confidence in job {r['job_index']}"
    
    if r['flag_type'] == 'false_positive':
        fp_count += 1
        assert r['actual_outcome_layer2'] == 'PASS' and r['expected_outcome'] == 'FAIL'
        assert not r['is_correct']
        assert r['root_cause'] is not None and len(r['root_cause']) > 10
        assert r['specific_pattern_issue'] is not None and len(r['specific_pattern_issue']) > 10
    elif r['flag_type'] == 'false_negative':
        fn_count += 1
        assert r['actual_outcome_layer2'] == 'FAIL' and r['expected_outcome'] == 'PASS'
        assert not r['is_correct']
        assert r['root_cause'] is not None and len(r['root_cause']) > 10
        assert r['specific_pattern_issue'] is not None and len(r['specific_pattern_issue']) > 10
    else:
        assert r['flag_type'] is None
        assert r['is_correct']
        correct_count += 1

print("\n--- Validation Summary ---")
print(f"Total Records: {len(records)}")
print(f"Correct Decisions: {correct_count} ({correct_count / len(records) * 100:.2f}%)")
print(f"False Positives: {fp_count}")
print(f"False Negatives: {fn_count}")
print(f"Expected PASS: {sum(1 for r in records if r['expected_outcome'] == 'PASS')}")
print(f"Expected FAIL: {sum(1 for r in records if r['expected_outcome'] == 'FAIL')}")
print("ALL ASSERTIONS PASSED! File batch_eval_3.jsonl is 100% valid and verified.")
