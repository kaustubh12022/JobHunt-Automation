import re
import json

with open('extracted_consultancies.txt', 'r', encoding='utf-8') as f:
    text = f.read()

results = []
pages = text.split("Tracking version - source information preserved from supplied 4-page directory Page")

for page in pages:
    if not page.strip(): continue
    
    # Try to extract the title
    match_title = re.search(r'\n\d+\.\s+(.*?)\nTier', page)
    if not match_title: 
        match_title = re.search(r'\n(\d+\.\s+[^\n]+)', page)
        if match_title:
            title = match_title.group(1).split('.', 1)[1].strip()
        else:
            continue
    else:
        title = match_title.group(1).strip()
        
    # Try to extract email
    match_email = re.search(r'Email\s*(.*?)\nPhone', page, re.DOTALL)
    if not match_email: 
        match_email = re.search(r'Email\s*(.*?)\nLocation', page, re.DOTALL)
        if not match_email:
            continue
    
    email_str = match_email.group(1).strip()
    
    # Extract actual emails
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email_str)
    
    if emails:
        results.append({
            "name": title,
            "emails": list(set(emails))
        })

with open('consultancy_emails.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=4)

print(f"Extracted {len(results)} consultancies with emails")
