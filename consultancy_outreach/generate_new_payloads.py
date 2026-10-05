import json

new_consultancies = [
    {"name": "Cybotrix Technologies", "emails": ["contact@cybotrix.com"]},
    {"name": "CP HR Services", "emails": ["info@cphrservices.in"]},
    {"name": "HoRizon HR World", "emails": ["career@horizonhrconsultancy.in"]},
    {"name": "Vinush Recruitment Agency", "emails": ["info@vinush.com"]},
    {"name": "TalentPro India", "emails": ["sales@talentproindia.com"]},
    {"name": "Alliance Recruitment Agency", "emails": ["sales@alliancerecruitmentagency.com"]},
    {"name": "Source One Management Services", "emails": ["hr@msourceone.com"]},
    {"name": "Alp Consulting", "emails": ["hr@alpconsulting.in"]}
]

payloads = []
for item in new_consultancies:
    name = item['name']
    for email in item['emails']:
        short_name = name.split(' / ')[0].split(' (')[0].strip()
        
        subject = "Inquiry for IT Fresher Openings - Kaustubh"
        
        htmlBody = f"""
        <p>Hi {short_name} Team,</p>
        <p>My name is Kaustubh, and I am a <strong>2026 B.E. IT Graduate</strong> and a <strong>Fresher</strong>. I am reaching out to check if you have any current <strong>IT Opportunities</strong> or openings for freshers at your consultancy.</p>
        <p>I have attached my updated <strong>Resume</strong> for your reference. If you have any suitable opportunities, please share the process and details with me.</p>
        <p>Additionally, if there are any registration, consultancy, or service charges associated with your placement services, kindly let me know.</p>
        <p>Best regards,<br>Kaustubh</p>
        """
        
        payload = {
            "to": [email],
            "subject": subject,
            "body": "Please view this email in an HTML viewer.",
            "htmlBody": htmlBody,
            "attachments": [r"C:\Users\kalek\Desktop\Resume_Dev_Updated.pdf"],
            "mimeType": "text/html"
        }
        payloads.append(payload)

with open(r'C:\Users\kalek\Desktop\new_email_payloads.json', 'w', encoding='utf-8') as f:
    json.dump(payloads, f, indent=4)
print(f"Generated {len(payloads)} payloads.")
