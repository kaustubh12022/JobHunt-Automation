"""
Script to generate tests/fixtures/jobs_200_dataset.json with 220+ realistic Indian tech jobs
and comprehensive ground-truth labels for recall, precision, and role-lens testing.
"""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

def generate_dataset():
    now = datetime.now(timezone.utc)
    fresh_date = (now - timedelta(hours=12)).strftime('%Y-%m-%d')
    two_days_old = (now - timedelta(hours=48)).strftime('%Y-%m-%d')
    stale_date = (now - timedelta(hours=96)).strftime('%Y-%m-%d')

    jobs = []

    # 1. Fresher QA Automation Roles (Target: ~40 jobs)
    qa_titles = [
        "QA Automation Engineer - Fresher", "Junior QA Automation Engineer", "Automation Tester (Fresher)",
        "SDET - 0-1 Years", "Associate QA Engineer (Selenium/Python)", "QA Tester - Trainee",
        "Junior Test Automation Engineer", "Software Test Engineer (0-2 Yrs)", "Automation Testing Intern",
        "QA Analyst - Entry Level", "Trainee Automation Engineer", "Junior SDET - Java/Selenium",
        "API Testing Fresher (Postman/Rest)", "Test Engineer - Freshers Welcome", "Associate Test Engineer"
    ]
    qa_companies = [
        "Infosys", "Wipro", "TCS", "Cognizant", "Persistent Systems", "Capgemini", "Zensar Technologies",
        "Cybage Software", "Globant", "Veritas Technologies", "Synechron", "BMC Software", "Mindtree"
    ]
    locations = [
        "Pune, Maharashtra, India", "Pune", "Pune, MH, IN",
        "Bengaluru, Karnataka, India", "Bangalore", "Bangalore, KA, IN",
        "Mumbai, Maharashtra, India", "Mumbai", "Navi Mumbai, MH",
        "Remote, India", "Hybrid - Pune"
    ]

    for i in range(40):
        title = qa_titles[i % len(qa_titles)]
        company = qa_companies[i % len(qa_companies)]
        loc = locations[i % len(locations)]
        job_id = f"qa-fresher-{i+1:03d}"
        desc = (
            f"About the Role: We are seeking a passionate {title} to join our QA team at {company} in {loc}.\n"
            f"Responsibilities:\n"
            f"- Write and maintain automated test scripts using Selenium and Python or Java.\n"
            f"- Perform API testing using Postman and REST client tools.\n"
            f"- Design detailed test cases, execute test suites, and log defects in JIRA.\n"
            f"- Work with Agile development teams to ensure high code quality.\n"
            f"Requirements:\n"
            f"- B.E./B.Tech in Computer Science, IT, or related technical field.\n"
            f"- 0-2 years of experience or strong internship background in automation testing.\n"
            f"- Hands-on knowledge of Python or Java, Selenium WebDriver, Postman, and SQL.\n"
            f"- Familiarity with Git version control and test methodologies.\n"
            f"Note: Freshers with project experience in automated testing are strongly encouraged to apply."
        )
        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "description": desc,
            "url": f"https://www.linkedin.com/jobs/view/{2000000000 + i}",
            "source": "linkedin" if i % 2 == 0 else "indeed",
            "job_type": "fulltime" if i % 4 != 0 else "internship",
            "date_posted": fresh_date if i % 5 != 0 else two_days_old,
            "is_remote": "Remote" in loc,
            "is_relevant": True,
            "is_senior": False,
            "target_role": "qa",
            "min_experience_years": 0,
            "max_experience_years": 2,
            "expected_ai_relevance": True
        })

    # 2. Fresher Java Developer Roles (Target: ~40 jobs)
    java_titles = [
        "Java Developer - Fresher", "Junior Java Developer", "Java Backend Developer (0-2 Years)",
        "Associate Software Engineer - Java", "Graduate Trainee - Java", "Junior Backend Engineer (Java/Spring)",
        "Java Software Engineer - Entry Level", "Java/SQL Developer Fresher", "Trainee Java Programmer",
        "Junior Software Developer (Java/JDBC)", "Java Developer Intern", "Entry Level Java Engineer"
    ]
    java_companies = [
        "Accenture", "LTIMindtree", "Tech Mahindra", "Tata Elxsi", "HCLTech", "Mphasis",
        "KPIT Technologies", "Hexaware", "Virtusa", "Birlasoft", "Persistent Systems"
    ]
    for i in range(40):
        title = java_titles[i % len(java_titles)]
        company = java_companies[i % len(java_companies)]
        loc = locations[(i + 2) % len(locations)]
        job_id = f"java-fresher-{i+1:03d}"
        desc = (
            f"{company} is hiring a {title} for our development team in {loc}.\n"
            f"Key Responsibilities:\n"
            f"- Design and implement modular backend components using Java, Spring Boot, and JDBC.\n"
            f"- Develop RESTful APIs and microservices for core business applications.\n"
            f"- Write SQL queries and database schemas for MySQL and PostgreSQL.\n"
            f"- Collaborate in Agile sprints and optimize data structures and algorithms.\n"
            f"Qualifications:\n"
            f"- Bachelor's degree in Information Technology or Computer Science.\n"
            f"- 0-2 years of experience in Java programming.\n"
            f"- Proficiency in Core Java, OOP concepts, Collections, and basic Spring Framework.\n"
            f"- Understanding of relational databases (SQL, DBMS) and REST APIs."
        )
        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "description": desc,
            "url": f"https://www.linkedin.com/jobs/view/{2100000000 + i}",
            "source": "linkedin" if i % 2 == 0 else "indeed",
            "job_type": "fulltime" if i % 3 != 0 else "internship",
            "date_posted": fresh_date if i % 4 != 0 else two_days_old,
            "is_remote": "Remote" in loc,
            "is_relevant": True,
            "is_senior": False,
            "target_role": "java",
            "min_experience_years": 0,
            "max_experience_years": 2,
            "expected_ai_relevance": True
        })

    # 3. Fresher .NET Developer Roles (Target: ~30 jobs)
    dotnet_titles = [
        ".NET Developer - Fresher", "Junior .NET Developer", "C# Software Engineer Trainee",
        "Associate .NET Developer", "Junior Backend Developer - C#/ASP.NET", "Entry Level .NET Engineer",
        "Trainee .NET Programmer", ".NET Core Developer (0-2 Yrs)", "Junior C# Developer"
    ]
    dotnet_companies = [
        "CitiusTech", "Datamatics", "Tata Consultancy Services", "Wipro", "Hexaware", "ITC Infotech",
        "LTI", "Syntel", "Mastek", "Zycus", "Neilsoft"
    ]
    for i in range(30):
        title = dotnet_titles[i % len(dotnet_titles)]
        company = dotnet_companies[i % len(dotnet_companies)]
        loc = locations[(i + 4) % len(locations)]
        job_id = f"dotnet-fresher-{i+1:03d}"
        desc = (
            f"Exciting opportunity at {company} for a {title} based in {loc}.\n"
            f"Job Overview:\n"
            f"- Develop backend services and APIs using C# and ASP.NET Core.\n"
            f"- Work with MS SQL Server for database operations and query tuning.\n"
            f"- Interface with Microsoft Azure cloud components.\n"
            f"- Write unit tests and maintain software quality.\n"
            f"Candidate Profile:\n"
            f"- Freshers or candidates with 0-2 years of relevant experience.\n"
            f"- Solid fundamentals in C#, OOP, and .NET Framework / .NET Core.\n"
            f"- Understanding of RESTful services, SQL, and database concepts.\n"
            f"- Certifications in Azure Fundamentals is a plus."
        )
        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "description": desc,
            "url": f"https://www.linkedin.com/jobs/view/{2200000000 + i}",
            "source": "indeed" if i % 2 == 0 else "linkedin",
            "job_type": "fulltime",
            "date_posted": fresh_date,
            "is_remote": "Remote" in loc,
            "is_relevant": True,
            "is_senior": False,
            "target_role": "dotnet",
            "min_experience_years": 0,
            "max_experience_years": 2,
            "expected_ai_relevance": True
        })

    # 4. Fresher Full Stack / Software Engineer Roles (Target: ~35 jobs)
    fs_titles = [
        "Full Stack Developer Fresher", "Junior Full Stack Developer", "Software Engineer - Fresher",
        "Associate Software Engineer", "Graduate Software Engineer Trainee", "Junior Python/React Developer",
        "Web Developer Intern", "Junior Software Engineer", "Full Stack Engineer (0-2 Years)",
        "Software Developer - Entry Level"
    ]
    fs_companies = [
        "Zoho", "Freshworks", "Postman", "Razorpay", "Jio Platforms", "Swiggy", "PhonePe",
        "BrowserStack", "Dream11", "InMobi", "Info Edge"
    ]
    for i in range(35):
        title = fs_titles[i % len(fs_titles)]
        company = fs_companies[i % len(fs_companies)]
        loc = locations[(i + 6) % len(locations)]
        job_id = f"fs-fresher-{i+1:03d}"
        desc = (
            f"Join {company} as a {title} in {loc}.\n"
            f"What you will do:\n"
            f"- Build scalable full stack web applications using Python, JavaScript, HTML, CSS, and modern frameworks.\n"
            f"- Develop backend REST APIs and connect with PostgreSQL or MongoDB databases.\n"
            f"- Write clean, maintainable, and modular code adhering to engineering best practices.\n"
            f"- Participate in daily standups, code reviews, and sprint planning.\n"
            f"Requirements:\n"
            f"- B.Tech/B.E./MCA in IT or Computer Science (2024/2025/2026 batch).\n"
            f"- 0-2 years experience with Python, JavaScript, and Web technologies.\n"
            f"- Strong problem-solving, DSA, and analytical abilities."
        )
        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "description": desc,
            "url": f"https://www.linkedin.com/jobs/view/{2300000000 + i}",
            "source": "linkedin" if i % 2 == 0 else "indeed",
            "job_type": "fulltime" if i % 3 != 0 else "internship",
            "date_posted": fresh_date,
            "is_remote": "Remote" in loc,
            "is_relevant": True,
            "is_senior": False,
            "target_role": "fullstack",
            "min_experience_years": 0,
            "max_experience_years": 2,
            "expected_ai_relevance": True
        })

    # 5. Negative: Senior / Lead / Staff / Manager Tech Roles (Target: ~40 jobs)
    senior_titles = [
        "Senior QA Automation Engineer", "Lead SDET", "QA Manager", "Principal Test Architect",
        "Senior Java Developer", "Java Technical Lead", "Principal Architect - Java",
        "Senior .NET Architect", "Lead Software Engineer - C#", "Staff Software Engineer",
        "Engineering Manager", "Director of Software Engineering", "VP of Technology",
        "Head of Quality Assurance", "Senior Full Stack Architect", "Lead Backend Engineer"
    ]
    senior_companies = [
        "Amazon India", "Microsoft India", "Oracle", "Cisco Systems", "SAP Labs", "Salesforce India",
        "IBM India", "Dell Technologies", "Intel India", "Adobe India", "Siemens"
    ]
    for i in range(40):
        title = senior_titles[i % len(senior_titles)]
        company = senior_companies[i % len(senior_companies)]
        loc = locations[(i + 1) % len(locations)]
        job_id = f"senior-tech-{i+1:03d}"
        exp_req = 5 + (i % 8) # 5 to 12 years
        desc = (
            f"Position: {title}\n"
            f"Company: {company} - Location: {loc}\n"
            f"Role Summary: We are looking for an experienced professional with {exp_req}+ years of experience to lead our engineering teams.\n"
            f"Responsibilities:\n"
            f"- Architect high-scale distributed systems and lead technical roadmaps.\n"
            f"- Mentor junior engineers, manage sprint deliverables, and define architectural standards.\n"
            f"- Oversee CI/CD, cloud infrastructure, and enterprise architecture.\n"
            f"Requirements:\n"
            f"- Minimum {exp_req} years of professional software development experience.\n"
            f"- Proven leadership, architectural design, and people management skills."
        )
        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "description": desc,
            "url": f"https://www.linkedin.com/jobs/view/{2400000000 + i}",
            "source": "linkedin",
            "job_type": "fulltime",
            "date_posted": fresh_date,
            "is_remote": False,
            "is_relevant": False,
            "is_senior": True,
            "target_role": "out_of_scope",
            "min_experience_years": exp_req,
            "max_experience_years": exp_req + 3,
            "expected_ai_relevance": False
        })

    # 6. Negative: Junior/Neutral Titles demanding High Experience (Target: ~25 jobs)
    sneaky_titles = [
        "Software Engineer", "Developer", "Backend Developer", "Automation Tester",
        "Java Programmer", "Full Stack Engineer", "Application Developer"
    ]
    for i in range(25):
        title = sneaky_titles[i % len(sneaky_titles)]
        company = senior_companies[i % len(senior_companies)]
        loc = locations[(i + 3) % len(locations)]
        job_id = f"sneaky-senior-{i+1:03d}"
        lo_exp = 3 + (i % 4) # 3, 4, 5, 6
        hi_exp = lo_exp + 2  # 5, 6, 7, 8
        desc = (
            f"Job Opening: {title} at {company} in {loc}.\n"
            f"Requirements:\n"
            f"- Candidate MUST have {lo_exp}-{hi_exp} years of dedicated commercial experience.\n"
            f"- At least {lo_exp} years working with enterprise Java or .NET stacks.\n"
            f"- Proven track record delivering complex production modules."
        )
        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "description": desc,
            "url": f"https://www.linkedin.com/jobs/view/{2500000000 + i}",
            "source": "indeed",
            "job_type": "fulltime",
            "date_posted": fresh_date,
            "is_remote": False,
            "is_relevant": False,
            "is_senior": True,
            "target_role": "out_of_scope",
            "min_experience_years": lo_exp,
            "max_experience_years": hi_exp,
            "expected_ai_relevance": False
        })

    # 7. Negative: Completely Out-of-Scope / Non-Tech Roles (Target: ~20 jobs)
    non_tech_titles = [
        "Senior Accountant", "HR Generalist", "Sales Executive", "Digital Marketing Specialist",
        "Business Development Manager", "Customer Support Associate", "Content Writer",
        "Financial Analyst", "Operations Executive", "Recruitment Consultant"
    ]
    non_tech_companies = [
        "Bajaj Finserv", "HDFC Bank", "Deloitte India", "KPMG", "ICICI Securities",
        "Reliance Retail", "PwC India", "Titan Company"
    ]
    for i in range(20):
        title = non_tech_titles[i % len(non_tech_titles)]
        company = non_tech_companies[i % len(non_tech_companies)]
        loc = locations[i % len(locations)]
        job_id = f"non-tech-{i+1:03d}"
        desc = (
            f"Role: {title} at {company} ({loc}).\n"
            f"Responsible for managing accounts, reconciliations, taxation, client audits, and financial ledgers.\n"
            f"Qualifications: B.Com / MBA in Finance or HR. Strong knowledge of Tally, Excel, and accounting principles."
        )
        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "description": desc,
            "url": f"https://www.linkedin.com/jobs/view/{2600000000 + i}",
            "source": "indeed",
            "job_type": "fulltime",
            "date_posted": fresh_date,
            "is_remote": False,
            "is_relevant": False,
            "is_senior": "Senior" in title or "Manager" in title,
            "target_role": "out_of_scope",
            "min_experience_years": 1,
            "max_experience_years": 3,
            "expected_ai_relevance": False
        })

    # 8. Boundary & Edge Cases: 1-3 yr fresher ranges, team exp statements, special chars (Target: ~15 jobs)
    edge_cases = [
        {
            "title": "Junior Automation Tester (1-3 Years)",
            "company": "Cognizant",
            "location": "Pune, Maharashtra, India",
            "desc": "Cognizant is hiring a Junior Automation Tester. Candidate must have 1-3 years of experience in Selenium, Python, and API testing. Freshers with 1 year internship eligible.",
            "is_relevant": True, "is_senior": False, "target_role": "qa"
        },
        {
            "title": "Software Engineer - Fresher (0-3 Yrs)",
            "company": "Infosys",
            "location": "Bengaluru, Karnataka, India",
            "desc": "Looking for entry level engineers. Experience: 0-3 years in Java or Python. Join our dynamic team.",
            "is_relevant": True, "is_senior": False, "target_role": "fullstack"
        },
        {
            "title": "Junior Java Developer",
            "company": "FinTech Innovations",
            "location": "Pune, India",
            "desc": "Our team has over 15 years of combined experience in payments architecture. We are hiring a fresher Java Developer (0-1 yr exp) with core Java and SQL knowledge.",
            "is_relevant": True, "is_senior": False, "target_role": "java"
        },
        {
            "title": "QA Test Engineer (Selenium & Postman)",
            "company": "L&T Infotech",
            "location": "Mumbai, Maharashtra",
            "desc": "Founded in 1996 with 28 years of industry excellence. We require an associate QA engineer with 0 to 2 years experience in automated testing.",
            "is_relevant": True, "is_senior": False, "target_role": "qa"
        },
        {
            "title": ".NET Developer (C# / SQL)",
            "company": "KPIT Technologies",
            "location": "Pune, Maharashtra",
            "desc": "Work alongside senior engineers who have 10+ years in automotive embedded systems. Candidate requirement: 0-2 yrs in C# and ASP.NET Core.",
            "is_relevant": True, "is_senior": False, "target_role": "dotnet"
        },
        {
            "title": "Stale QA Automation Tester",
            "company": "Old Corp",
            "location": "Pune",
            "desc": "Automation testing role with Python and Selenium, 0-2 years exp.",
            "is_relevant": False, "is_senior": False, "target_role": "qa", "date_posted": stale_date
        },
        {
            "title": "Non-Target Location QA Tester",
            "company": "Delhi Tech",
            "location": "New Delhi, Delhi, India",
            "desc": "Junior QA tester with Selenium and Java, 0-2 years exp.",
            "is_relevant": False, "is_senior": False, "target_role": "qa"
        },
        {
            "title": "Senior Staff Architect (15+ Years)",
            "company": "MegaCorp",
            "location": "Bengaluru",
            "desc": "15+ years of experience leading massive distributed cloud deployments.",
            "is_relevant": False, "is_senior": True, "target_role": "out_of_scope"
        },
        {
            "title": "Java Developer (three to five years experience)",
            "company": "Global Systems",
            "location": "Pune",
            "desc": "Requires three to five years of commercial Java backend experience.",
            "is_relevant": False, "is_senior": True, "target_role": "out_of_scope"
        },
        {
            "title": "Software Tester - 0 Years Experience Welcome",
            "company": "StartUp Labs",
            "location": "Remote, India",
            "desc": "0 years experience required. Fresh graduates in Computer Science with Selenium or Python knowledge.",
            "is_relevant": True, "is_senior": False, "target_role": "qa"
        }
    ]

    for i, ec in enumerate(edge_cases):
        job_id = f"edge-case-{i+1:03d}"
        jobs.append({
            "id": job_id,
            "title": ec["title"],
            "company": ec["company"],
            "location": ec["location"],
            "description": ec["desc"],
            "url": f"https://www.linkedin.com/jobs/view/{2700000000 + i}",
            "source": "linkedin",
            "job_type": "fulltime",
            "date_posted": ec.get("date_posted", fresh_date),
            "is_remote": "Remote" in ec["location"],
            "is_relevant": ec["is_relevant"],
            "is_senior": ec["is_senior"],
            "target_role": ec["target_role"],
            "min_experience_years": 0,
            "max_experience_years": 3 if ec["is_relevant"] else 5,
            "expected_ai_relevance": ec["is_relevant"]
        })

    out_file = os.path.join(os.path.dirname(__file__), "jobs_200_dataset.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)

    print(f"Successfully generated {len(jobs)} jobs in {out_file}")
    
    # Summary of counts
    relevant_count = sum(1 for j in jobs if j["is_relevant"])
    senior_count = sum(1 for j in jobs if j["is_senior"])
    out_of_scope = sum(1 for j in jobs if j["target_role"] == "out_of_scope")
    print(f"Breakdown: Total={len(jobs)}, Relevant Freshers={relevant_count}, Senior/Lead={senior_count}, OutOfScope={out_of_scope}")

if __name__ == "__main__":
    generate_dataset()
