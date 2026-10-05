import json
import sys
import yaml
from pathlib import Path

sys.path.insert(0, ".")
from scoring_audit.generate_synthetic_jds import generate_all_synthetic_jds, validate_dataset

# 1. Compare saved JSON with generator output
with open('scoring_audit/synthetic_jds.json', 'r', encoding='utf-8') as f:
    saved = json.load(f)

generated = generate_all_synthetic_jds()
assert len(saved) == len(generated) == 300
diffs = 0
for i in range(300):
    if saved[i] != generated[i]:
        diffs += 1
        print(f"Diff at index {i}: id={saved[i]['id']} vs {generated[i]['id']}")
print(f"Total diffs between saved JSON and generator: {diffs}")

# 2. Check resume skills vs all expected_missing_skills
with open('data_folder/plain_text_resume.yaml', 'r', encoding='utf-8') as f:
    resume = yaml.safe_load(f)

resume_text = yaml.dump(resume).lower()

all_missing_skills = set()
for jd in saved:
    for s in jd['ground_truth']['expected_missing_skills']:
        all_missing_skills.add(s)

print(f"\nUnique expected missing skills across all 300 JDs ({len(all_missing_skills)}):")
print(sorted(all_missing_skills))

# Check each skill against candidate resume
potential_conflicts = []
for skill in sorted(all_missing_skills):
    skill_lower = skill.lower()
    # Check if exact word or phrase exists in resume
    if skill_lower in resume_text:
        potential_conflicts.append(skill)

print(f"\nPotential skill conflicts in resume text: {potential_conflicts}")

# Check resume explicit skills list
explicit_skills = [s.lower() for s in resume.get('skills', [])]
print(f"\nExplicit resume skills list ({len(explicit_skills)}):")
for s in explicit_skills:
    print(f"  - {s}")
