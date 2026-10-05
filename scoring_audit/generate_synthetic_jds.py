"""
Synthetic Benchmark Dataset Generator for AI Scoring Phase Audit.

Generates 300 diverse, realistic synthetic job descriptions across 15 distinct categories
(20 JDs each) with pre-determined ground-truth score ranges, classification flags,
and genuine missing skills evaluated against the candidate profile (Kaustubh Kale).

Output: scoring_audit/synthetic_jds.json
"""

import json
import os
import re
import sys
import argparse
from typing import List, Dict, Any, Tuple


# Candidate skills normalized from data_folder/plain_text_resume.yaml
# Used to verify that expected_missing_skills contains ONLY genuine missing skills.
CANDIDATE_KNOWN_SKILLS = {
    # Core Languages
    "java", "python", "sql", "c#", "csharp", "c#.net", "javascript", "typescript", "html", "css", "html5", "css3",
    # Frameworks & Backend
    "react", "react.js", "next.js", "nextjs", "node.js", "nodejs", "express", "express.js",
    "vite", "mongoose", "spring", "spring core", "jdbc", "rest apis", "rest api", "rest", "json",
    "mvc", "mvc architecture", "pandas", "asyncio", "jinja2", "beautifulsoup", "regex",
    # Testing
    "junit", "postman", "selenium", "pytest", "manual testing", "manual testing fundamentals",
    "test case design", "test cases",
    # Concepts
    "data structures", "algorithms", "dsa", "oop", "dbms", "problem-solving",
    # Tools & Platforms
    "docker", "kubernetes", "mongodb", "git", "github", "vs code", "intellij", "intellij idea",
    "mysql", "maven", "sts", "spring tool suite", "agile", "scrum", "windows task scheduler", "excel",
    # Cloud & Certifications
    "azure", "microsoft azure", "azure fundamentals", "cybersecurity"
}


# 15 Category Definitions with Ground Truth Specifications
CATEGORY_SPECS = [
    {
        "category": "Java_Spring_Backend",
        "min_score": 80,
        "max_score": 95,
        "is_testing": False,
        "acceptable_pass": True,
        "target_domain": "Java / Spring / Backend",
        "roles": [
            ("Junior Java Developer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Kafka"]),
            ("Associate Java Software Engineer", "LTIMindtree", "Pune, Maharashtra", "0-2 years", []),
            ("Entry Level Java Backend Developer", "Cognizant", "Mumbai, Maharashtra", "0-1 years", ["Microservices", "Kafka"]),
            ("Graduate Engineer Trainee - Java", "Infosys", "Pune, Maharashtra", "Fresher / 2025-2026 Batch", []),
            ("Junior Backend Developer (Java)", "Swiggy Labs", "Bangalore, Karnataka", "0-1 years", ["Redis"]),
            ("Java Developer - Fresher / 0-1 yr", "Barclays Global Service Centre", "Pune, Maharashtra", "0-1 years", ["AWS"]),
            ("Software Development Engineer I (Java)", "Razorpay", "Bangalore, Karnataka", "0-2 years", ["RabbitMQ", "Kafka"]),
            ("Java Backend Associate", "Capgemini", "Mumbai, Maharashtra", "0-1 years", []),
            ("Junior Software Engineer - Java", "TCS Digital", "Pune, Maharashtra", "Fresher", []),
            ("Backend Java Developer Trainee", "Persistent Technologies", "Pune, Maharashtra", "0-1 years", []),
            ("Junior Java / Spring Boot Engineer", "Zeta Suite", "Bangalore, Karnataka", "0-2 years", ["Redis"]),
            ("Associate Developer - Java Ecosystem", "Wipro", "Hyderabad, Telangana", "0-1 years", []),
            ("Junior Backend Engineer (Java)", "Groww", "Bangalore, Karnataka", "0-2 years", ["Kafka", "Redis"]),
            ("Software Engineer (Java Track)", "Mindtree", "Pune, Maharashtra", "0-1 years", []),
            ("Java Developer - 0 to 2 Years", "Persistent Systems", "Nagpur / Pune", "0-2 years", ["AWS"]),
            ("Backend Engineer - Java (Fresher)", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", []),
            ("Junior Application Developer (Java)", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", ["GraphQL"]),
            ("SDE Trainee (Java / Spring)", "PhonePe", "Bangalore, Karnataka", "Fresher", ["Microservices", "Kafka"]),
            ("Junior Java Backend Specialist", "Deutsche Bank GCC", "Pune, Maharashtra", "0-1 years", []),
            ("Associate Backend Software Engineer", "Cimpress", "Mumbai, Maharashtra", "0-2 years", ["Redis"]),
        ],
        "tech_focus": "Core Java, Spring Boot, Spring Core, RESTful APIs, MySQL, JDBC, Hibernate, Maven, OOP",
    },
    {
        "category": "QA_Automation_Testing",
        "min_score": 80,
        "max_score": 95,
        "is_testing": True,
        "acceptable_pass": True,
        "target_domain": "QA / Automation Testing",
        "roles": [
            ("Junior QA Automation Engineer", "BrowserStack", "Mumbai, Maharashtra", "0-2 years", ["Cypress"]),
            ("Associate SDET - Automation", "Postman Labs", "Bangalore, Karnataka", "0-1 years", []),
            ("Test Automation Engineer (Fresher)", "Persistent Systems", "Pune, Maharashtra", "Fresher", []),
            ("Junior SDET (Python & Selenium)", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["Playwright"]),
            ("QA Automation Trainee", "LTIMindtree", "Pune, Maharashtra", "0-1 years", ["JMeter"]),
            ("Associate Quality Assurance Engineer", "Razorpay", "Bangalore, Karnataka", "0-2 years", ["Jenkins", "Cypress"]),
            ("Automation Test Engineer (0-1 yr)", "Cognizant", "Chennai, Tamil Nadu", "0-1 years", []),
            ("Junior SDET - Web & API", "Zeta Suite", "Bangalore, Karnataka", "0-1 years", ["Playwright"]),
            ("QA Automation Analyst", "Capgemini", "Pune, Maharashtra", "0-2 years", []),
            ("Entry Level QA Engineer (Automation)", "TCS", "Mumbai, Maharashtra", "Fresher / 0-1 yr", []),
            ("Junior Automation Tester (Python)", "Wipro", "Hyderabad, Telangana", "0-1 years", []),
            ("Software Development Engineer in Test (SDET I)", "Pine Labs", "Bangalore, Karnataka", "0-2 years", ["Appium"]),
            ("Junior QA Engineer - Automation", "Mindtree", "Pune, Maharashtra", "0-1 years", []),
            ("QA Automation Associate", "Barclays GSC", "Pune, Maharashtra", "0-2 years", ["Cucumber", "BDD"]),
            ("Junior SDET (API & UI Automation)", "InMobi", "Bangalore, Karnataka", "0-1 years", ["Playwright"]),
            ("Test Automation Engineer - Fresher", "Persistent Systems", "Pune, Maharashtra", "0-1 years", []),
            ("Associate QA Automation Specialist", "Freshworks", "Chennai, Tamil Nadu", "0-2 years", ["Cypress"]),
            ("Junior SDET (Automation & Quality)", "CleverTap", "Mumbai, Maharashtra", "0-1 years", ["JMeter"]),
            ("Automation QA Engineer (0-2 yrs)", "Tech Mahindra", "Pune, Maharashtra", "0-2 years", []),
            ("Junior SDET Trainee", "PhonePe", "Bangalore, Karnataka", "Fresher", ["RestAssured", "Kafka"]),
        ],
        "tech_focus": "Selenium WebDriver, JUnit, pytest, Postman API Testing, Test Case Design, Java / Python automation, Bug Lifecycle",
    },
    {
        "category": "MERN_Stack",
        "min_score": 75,
        "max_score": 90,
        "is_testing": False,
        "acceptable_pass": True,
        "target_domain": "MERN Stack Development",
        "roles": [
            ("Junior MERN Stack Developer", "CleverTap", "Mumbai, Maharashtra", "0-2 years", ["Redux"]),
            ("Associate Full Stack Engineer (MERN)", "Zeta Suite", "Bangalore, Karnataka", "0-1 years", []),
            ("MERN Stack Developer (Fresher / 0-1 yr)", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Tailwind CSS"]),
            ("Junior Full Stack Developer (React & Node)", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["AWS"]),
            ("Entry Level MERN Developer", "GeekyAnts", "Bangalore, Karnataka", "Fresher", []),
            ("Associate Web Developer (MERN Stack)", "Mindtree", "Pune, Maharashtra", "0-1 years", []),
            ("Junior MERN Developer", "Razorpay", "Bangalore, Karnataka", "0-2 years", ["Redis", "GraphQL"]),
            ("Full Stack Javascript Developer - Fresher", "TCS Digital", "Mumbai, Maharashtra", "Fresher", []),
            ("Junior MERN Stack Engineer", "InMobi", "Bangalore, Karnataka", "0-1 years", ["WebSockets"]),
            ("MERN Stack Trainee", "LTIMindtree", "Pune, Maharashtra", "0-1 years", []),
            ("Junior Full Stack Javascript Engineer", "Capgemini", "Pune, Maharashtra", "0-2 years", []),
            ("React & Node.js Developer (0-2 yrs)", "Cognizant", "Hyderabad, Telangana", "0-2 years", ["Redux Toolkit"]),
            ("Junior MERN Stack Developer", "Wipro", "Bangalore, Karnataka", "0-1 years", []),
            ("Associate Software Engineer - MERN", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", []),
            ("Junior Web Developer (MERN)", "Persistent Systems", "Pune, Maharashtra", "0-1 years", []),
            ("MERN Developer (0-1 yr)", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", ["AWS"]),
            ("Full Stack Associate (MERN)", "Infosys", "Pune, Maharashtra", "Fresher / 0-1 yr", []),
            ("Junior MERN Developer", "Groww", "Bangalore, Karnataka", "0-2 years", ["GraphQL"]),
            ("MERN Stack Software Engineer", "Barclays", "Pune, Maharashtra", "0-1 years", []),
            ("Junior Full Stack Engineer (MERN)", "Cimpress", "Mumbai, Maharashtra", "0-2 years", ["Tailwind CSS"]),
        ],
        "tech_focus": "React.js, Node.js, Express.js, MongoDB, Mongoose, RESTful APIs, JavaScript (ES6+), HTML5/CSS3, Git",
    },
    {
        "category": "AI_ML_LLM",
        "min_score": 75,
        "max_score": 88,
        "is_testing": False,
        "acceptable_pass": True,
        "target_domain": "AI / ML / LLM / Agentic AI",
        "roles": [
            ("Junior Generative AI Developer", "Swiggy Labs", "Bangalore, Karnataka", "0-2 years", ["LangChain", "Vector DB"]),
            ("Associate AI / ML Engineer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["PyTorch"]),
            ("Junior Prompt Engineer & AI Developer", "Razorpay", "Bangalore, Karnataka", "0-2 years", ["LlamaIndex"]),
            ("AI Application Developer Trainee", "InMobi", "Bangalore, Karnataka", "0-1 years", ["RAG"]),
            ("Entry Level LLM Solutions Engineer", "Zeta Suite", "Bangalore, Karnataka", "Fresher", ["ChromaDB"]),
            ("Junior AI Engineer (Python & GenAI)", "CleverTap", "Mumbai, Maharashtra", "0-1 years", ["Hugging Face"]),
            ("Associate Machine Learning / AI Developer", "TCS Research", "Pune, Maharashtra", "0-2 years", ["PyTorch", "TensorFlow"]),
            ("Junior Agentic AI Developer", "Mindtree", "Pune, Maharashtra", "0-1 years", ["LangChain"]),
            ("AI / Data Science Trainee", "LTIMindtree", "Bangalore, Karnataka", "Fresher / 0-1 yr", ["Scikit-Learn"]),
            ("Junior LLM Integration Engineer", "Postman Labs", "Bangalore, Karnataka", "0-1 years", []),
            ("Generative AI Associate", "Capgemini", "Mumbai, Maharashtra", "0-2 years", ["Vector DB"]),
            ("Junior AI Developer", "Cognizant", "Chennai, Tamil Nadu", "0-1 years", ["LangChain"]),
            ("Associate AI / NLP Developer", "Wipro", "Hyderabad, Telangana", "0-1 years", ["Spacy", "NLTK"]),
            ("Junior AI Automation Engineer", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", []),
            ("GenAI Software Engineer (Fresher)", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", ["LlamaIndex"]),
            ("Junior AI Systems Developer", "Infosys", "Pune, Maharashtra", "Fresher", ["PyTorch"]),
            ("Associate AI Engineer", "Groww", "Bangalore, Karnataka", "0-2 years", ["Pinecone"]),
            ("Junior LLM Applications Developer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["RAG Architecture"]),
            ("AI / ML Associate Trainee", "Barclays", "Pune, Maharashtra", "0-1 years", []),
            ("Junior Generative AI Engineer", "Cimpress", "Mumbai, Maharashtra", "0-2 years", ["LangChain"]),
        ],
        "tech_focus": "Python, LLM APIs (OpenAI/Gemini/DeepSeek), Prompt Engineering, Pandas, Asyncio, REST APIs, JSON processing",
    },
    {
        "category": "Python_Backend",
        "min_score": 75,
        "max_score": 90,
        "is_testing": False,
        "acceptable_pass": True,
        "target_domain": "Python / Django / Flask / FastAPI Backend",
        "roles": [
            ("Junior Python Backend Developer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Celery"]),
            ("Associate Python Software Engineer", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["Redis"]),
            ("Python Developer (Fresher / 0-1 yr)", "Razorpay", "Bangalore, Karnataka", "0-1 years", []),
            ("Junior Backend Engineer (Python)", "LTIMindtree", "Pune, Maharashtra", "0-2 years", ["SQLAlchemy"]),
            ("Entry Level Python Developer", "Mindtree", "Bangalore, Karnataka", "Fresher", []),
            ("Python Backend Trainee", "Cognizant", "Mumbai, Maharashtra", "0-1 years", []),
            ("Junior Python / REST API Engineer", "Capgemini", "Pune, Maharashtra", "0-1 years", []),
            ("Associate Software Engineer - Python", "TCS", "Pune, Maharashtra", "0-2 years", []),
            ("Junior Backend Developer (Python)", "Wipro", "Hyderabad, Telangana", "0-1 years", ["Celery"]),
            ("Python Developer - 0 to 2 Years", "Zeta Suite", "Bangalore, Karnataka", "0-2 years", ["Redis"]),
            ("Junior Software Engineer (Python Track)", "InMobi", "Bangalore, Karnataka", "0-1 years", ["AWS"]),
            ("Backend Python Developer (Fresher)", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", []),
            ("Junior Python Web Developer", "CleverTap", "Mumbai, Maharashtra", "0-2 years", ["GraphQL"]),
            ("Associate Backend Developer (Python)", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", []),
            ("Junior Python Engineer", "Groww", "Bangalore, Karnataka", "0-2 years", ["RabbitMQ"]),
            ("Python Developer Trainee", "Infosys", "Pune, Maharashtra", "Fresher", []),
            ("Junior Backend Engineer - Python", "Postman", "Bangalore, Karnataka", "0-1 years", []),
            ("Associate Python Engineer", "Barclays", "Pune, Maharashtra", "0-2 years", []),
            ("Junior Python Backend Specialist", "Cimpress", "Mumbai, Maharashtra", "0-1 years", ["Redis"]),
            ("Python SDE-1", "Persistent Systems", "Pune, Maharashtra", "0-2 years", ["Celery"]),
        ],
        "tech_focus": "Python, Django, Flask, FastAPI, REST APIs, PostgreSQL, MySQL, Asyncio, OOP, Data Structures",
    },
    {
        "category": "DotNet_CSharp",
        "min_score": 60,
        "max_score": 75,
        "is_testing": False,
        "acceptable_pass": True,
        "target_domain": ".NET / C# / ASP.NET",
        "roles": [
            ("Junior .NET Developer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Entity Framework Core", "SQL Server"]),
            ("Associate C# Software Engineer", "Cognizant", "Mumbai, Maharashtra", "0-2 years", ["ASP.NET MVC", "LINQ"]),
            ("Entry Level .NET Developer", "LTIMindtree", "Pune, Maharashtra", "0-1 years", ["Entity Framework", "SQL Server"]),
            ("Graduate Engineer Trainee - .NET", "Infosys", "Pune, Maharashtra", "Fresher", ["ASP.NET Core"]),
            ("Junior C# Backend Developer", "Mindtree", "Bangalore, Karnataka", "0-2 years", ["LINQ", "Azure DevOps"]),
            (".NET Developer Trainee", "Capgemini", "Mumbai, Maharashtra", "0-1 years", ["ASP.NET Core", "Entity Framework"]),
            ("Junior Software Engineer - C# / .NET", "TCS", "Pune, Maharashtra", "0-2 years", ["WCF", "LINQ"]),
            ("Associate .NET Engineer", "Wipro", "Hyderabad, Telangana", "0-1 years", ["Entity Framework Core", "SQL Server"]),
            ("Junior C# Application Developer", "Barclays", "Pune, Maharashtra", "0-2 years", ["LINQ", "Entity Framework"]),
            ("Entry Level .NET Core Developer", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", ["ASP.NET Core", "SQL Server"]),
            ("Junior .NET Backend Engineer", "Persistent Systems", "Nagpur / Pune", "0-2 years", ["Azure DevOps", "LINQ"]),
            ("Associate C# Developer", "Cimpress", "Mumbai, Maharashtra", "0-1 years", ["Entity Framework", "LINQ"]),
            ("Junior .NET Web Developer", "Cognizant", "Chennai, Tamil Nadu", "0-2 years", ["ASP.NET MVC", "SQL Server"]),
            (".NET Trainee Engineer", "Infosys", "Bangalore, Karnataka", "Fresher", ["Entity Framework"]),
            ("Junior C# / Azure Software Developer", "LTIMindtree", "Bangalore, Karnataka", "0-1 years", ["Azure Functions", "LINQ"]),
            ("Associate .NET Developer", "Capgemini", "Pune, Maharashtra", "0-2 years", ["Entity Framework Core"]),
            ("Junior Software Engineer (.NET)", "Wipro", "Pune, Maharashtra", "0-1 years", ["ASP.NET Core", "LINQ"]),
            (".NET Developer (0-2 Years)", "Mindtree", "Pune, Maharashtra", "0-2 years", ["LINQ", "SQL Server"]),
            ("Junior C# Developer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Entity Framework", "LINQ"]),
            ("Associate .NET Solutions Engineer", "TCS Digital", "Mumbai, Maharashtra", "0-2 years", ["Microservices", "LINQ"]),
        ],
        "tech_focus": "C#, .NET Core, ASP.NET Web API, Microsoft Azure, OOP principles, SQL Server, Relational Databases",
    },
    {
        "category": "FullStack_SWE",
        "min_score": 70,
        "max_score": 85,
        "is_testing": False,
        "acceptable_pass": True,
        "target_domain": "Full Stack / Software Engineering (general)",
        "roles": [
            ("Associate Software Engineer - Full Stack", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["AWS"]),
            ("Junior Full Stack Developer", "Razorpay", "Bangalore, Karnataka", "0-1 years", ["CI/CD"]),
            ("Graduate Software Engineer", "Persistent Systems", "Pune, Maharashtra", "Fresher", []),
            ("Software Development Engineer I (Generalist)", "Zeta Suite", "Bangalore, Karnataka", "0-2 years", ["GraphQL"]),
            ("Junior Full Stack Engineer", "InMobi", "Bangalore, Karnataka", "0-1 years", ["Webpack"]),
            ("SWE Trainee (Full Stack)", "CleverTap", "Mumbai, Maharashtra", "0-1 years", []),
            ("Junior Web Application Developer", "Mindtree", "Pune, Maharashtra", "0-2 years", ["AWS"]),
            ("Associate Software Development Engineer", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", []),
            ("Junior Full Stack SWE", "LTIMindtree", "Pune, Maharashtra", "0-2 years", ["Tailwind CSS"]),
            ("Entry Level Software Engineer", "Infosys", "Pune, Maharashtra", "Fresher", []),
            ("Junior Software Engineer", "Cognizant", "Mumbai, Maharashtra", "0-1 years", []),
            ("Associate Full Stack Developer", "Capgemini", "Pune, Maharashtra", "0-2 years", []),
            ("Junior Software Developer (Full Stack)", "TCS", "Pune, Maharashtra", "0-1 years", []),
            ("Software Engineer - Early Career", "Wipro", "Bangalore, Karnataka", "0-2 years", ["AWS"]),
            ("Junior Full Stack Programmer", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", []),
            ("Associate Software Engineer", "Barclays", "Pune, Maharashtra", "0-2 years", []),
            ("Junior Full Stack Developer", "Groww", "Bangalore, Karnataka", "0-1 years", ["GraphQL"]),
            ("Early Career SWE", "Postman", "Bangalore, Karnataka", "0-2 years", []),
            ("Junior Software Engineer (Web)", "Cimpress", "Mumbai, Maharashtra", "0-1 years", []),
            ("Associate SWE - Full Stack", "Persistent Systems", "Pune, Maharashtra", "0-2 years", ["CI/CD"]),
        ],
        "tech_focus": "JavaScript, TypeScript, React, HTML/CSS, Python or Java backend, SQL, REST APIs, Git, Algorithms",
    },
    {
        "category": "Manual_QA_Testing",
        "min_score": 65,
        "max_score": 80,
        "is_testing": True,
        "acceptable_pass": True,
        "target_domain": "Manual QA / Software Testing",
        "roles": [
            ("Junior QA Tester (Manual)", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["JIRA"]),
            ("Associate Quality Analyst", "Cognizant", "Mumbai, Maharashtra", "0-2 years", ["JIRA", "TestRail"]),
            ("Software Test Trainee (Manual QA)", "LTIMindtree", "Pune, Maharashtra", "Fresher", ["JIRA"]),
            ("Manual QA Engineer (Web & Mobile)", "Capgemini", "Pune, Maharashtra", "0-2 years", ["JIRA", "Zephyr"]),
            ("Junior Test Specialist", "TCS", "Pune, Maharashtra", "0-1 years", ["JIRA"]),
            ("Quality Assurance Associate (Fresher)", "Infosys", "Pune, Maharashtra", "Fresher / 0-1 yr", ["JIRA"]),
            ("Junior Manual Tester", "Wipro", "Hyderabad, Telangana", "0-1 years", ["JIRA", "Bugzilla"]),
            ("Associate Software Tester", "Mindtree", "Bangalore, Karnataka", "0-2 years", ["JIRA"]),
            ("Junior Quality Analyst", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", ["JIRA", "TestRail"]),
            ("QA Trainee - Manual Testing", "Persistent Systems", "Nagpur / Pune", "Fresher", ["JIRA"]),
            ("Junior Software Test Engineer", "Barclays", "Pune, Maharashtra", "0-2 years", ["JIRA", "ALM"]),
            ("Manual QA Analyst (Fresher)", "Cimpress", "Mumbai, Maharashtra", "0-1 years", ["JIRA"]),
            ("Junior Test Engineer (QA)", "Swiggy", "Bangalore, Karnataka", "0-1 years", ["JIRA", "Charles Proxy"]),
            ("QA Associate - Manual Testing", "Razorpay", "Bangalore, Karnataka", "0-2 years", ["JIRA"]),
            ("Junior QA Analyst (0-1 yr)", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", ["JIRA"]),
            ("Manual Test Engineer", "InMobi", "Bangalore, Karnataka", "0-2 years", ["JIRA", "TestRail"]),
            ("Associate QA Tester", "CleverTap", "Mumbai, Maharashtra", "0-1 years", ["JIRA"]),
            ("Software QA Trainee", "Groww", "Bangalore, Karnataka", "Fresher", ["JIRA"]),
            ("Junior Quality Engineer (Manual)", "Postman", "Bangalore, Karnataka", "0-1 years", ["JIRA"]),
            ("Entry Level QA Analyst", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["JIRA"]),
        ],
        "tech_focus": "STLC, Manual Testing, Test Case Writing, Black-box Testing, Regression Testing, Defect Lifecycle, Postman API basics, SQL",
    },
    {
        "category": "Senior_Java_Lead",
        "min_score": 0,
        "max_score": 25,
        "is_testing": False,
        "acceptable_pass": False,
        "target_domain": "Senior / Lead Java Role (Trap: 5-10+ yrs)",
        "roles": [
            ("Lead Java Architect (8+ Years)", "Persistent Systems", "Pune, Maharashtra", "8+ years", ["Distributed Systems Design", "Kafka", "8+ years experience"]),
            ("Senior Java Technical Lead", "Cognizant", "Mumbai, Maharashtra", "7-10 years", ["Team Leadership", "Microservices Architecture", "7+ years experience"]),
            ("Principal Java Engineer", "Swiggy", "Bangalore, Karnataka", "8+ years", ["System Architecture", "Kafka", "8+ years experience"]),
            ("Senior Java Software Engineer (5+ yrs)", "Razorpay", "Bangalore, Karnataka", "5-7 years", ["Microservices", "Kafka", "5+ years experience"]),
            ("Staff Software Engineer - Java", "Zeta Suite", "Bangalore, Karnataka", "10+ years", ["System Design", "Distributed Systems", "10+ years experience"]),
            ("Java Tech Lead", "LTIMindtree", "Pune, Maharashtra", "6-9 years", ["Cloud Architecture", "Team Mentorship", "6+ years experience"]),
            ("Senior Principal Java Architect", "Barclays", "Pune, Maharashtra", "10+ years", ["Enterprise Architecture", "Kafka", "10+ years experience"]),
            ("Java Engineering Lead", "Infosys", "Pune, Maharashtra", "8+ years", ["Sprint Management", "Technical Leadership", "8+ years experience"]),
            ("Senior Java Backend Developer (5-8 yrs)", "Mindtree", "Pune, Maharashtra", "5-8 years", ["Kafka", "Microservices", "5+ years experience"]),
            ("Lead Software Engineer (Java)", "TCS", "Mumbai, Maharashtra", "7+ years", ["Architecture Reviews", "7+ years experience"]),
            ("Principal Java Backend Developer", "InMobi", "Bangalore, Karnataka", "8+ years", ["Low Latency Systems", "Kafka", "8+ years experience"]),
            ("Senior Backend Engineer - Java (6+ yrs)", "CleverTap", "Mumbai, Maharashtra", "6+ years", ["High Throughput Architecture", "Kafka", "6+ years experience"]),
            ("Lead Java Developer", "Capgemini", "Pune, Maharashtra", "8+ years", ["Spring Cloud", "Team Leadership", "8+ years experience"]),
            ("Senior Java Architect (10+ yrs)", "Wipro", "Hyderabad, Telangana", "10+ years", ["SaaS Architecture", "10+ years experience"]),
            ("Java Tech Lead (6-10 yrs)", "Tech Mahindra", "Pune, Maharashtra", "6-10 years", ["Client Management", "6+ years experience"]),
            ("Senior Staff Engineer - Java", "Pine Labs", "Noida, Uttar Pradesh", "9+ years", ["Distributed Transactions", "Kafka", "9+ years experience"]),
            ("Senior Java Engineer (7+ yrs)", "Groww", "Bangalore, Karnataka", "7+ years", ["High Availability Systems", "7+ years experience"]),
            ("Principal Engineer - Java Platform", "Postman", "Bangalore, Karnataka", "8+ years", ["Platform Engineering", "8+ years experience"]),
            ("Java Technical Manager", "Persistent Systems", "Pune, Maharashtra", "8-12 years", ["People Management", "8+ years experience"]),
            ("Senior Lead Java Specialist", "Cimpress", "Mumbai, Maharashtra", "7+ years", ["Event-Driven Architecture", "Kafka", "7+ years experience"]),
        ],
        "tech_focus": "Enterprise Java, Spring Boot microservices, high-throughput distributed systems, Kafka, Redis, system architecture, team leadership",
    },
    {
        "category": "Senior_QA_Lead",
        "min_score": 0,
        "max_score": 25,
        "is_testing": True,
        "acceptable_pass": False,
        "target_domain": "Senior / Lead QA Role (Trap: 5-10+ yrs)",
        "roles": [
            ("QA Automation Architect (8+ yrs)", "Persistent Systems", "Pune, Maharashtra", "8+ years", ["Test Architecture", "Enterprise Framework Design", "8+ years experience"]),
            ("Senior SDET Lead (6-10 yrs)", "Swiggy", "Bangalore, Karnataka", "6-10 years", ["Performance Testing", "JMeter", "6+ years experience"]),
            ("Principal Quality Engineer", "Razorpay", "Bangalore, Karnataka", "8+ years", ["Test Strategy", "Team Leadership", "8+ years experience"]),
            ("QA Lead / Test Manager", "Cognizant", "Mumbai, Maharashtra", "7+ years", ["QA Management", "Client Interfacing", "7+ years experience"]),
            ("Senior Test Architect (8+ yrs)", "LTIMindtree", "Pune, Maharashtra", "8+ years", ["Test Architecture", "Gatling", "8+ years experience"]),
            ("Lead SDET", "Zeta Suite", "Bangalore, Karnataka", "5-8 years", ["Chaos Engineering", "5+ years experience"]),
            ("Quality Assurance Lead (7+ yrs)", "Barclays", "Pune, Maharashtra", "7+ years", ["Regulatory Testing", "7+ years experience"]),
            ("Senior Manager - Quality Engineering", "Infosys", "Pune, Maharashtra", "10+ years", ["QA Budgeting", "Delivery Management", "10+ years experience"]),
            ("Lead Automation Engineer (6+ yrs)", "Mindtree", "Bangalore, Karnataka", "6+ years", ["Selenium Grid Architecture", "JMeter", "6+ years experience"]),
            ("Principal SDET", "InMobi", "Bangalore, Karnataka", "8+ years", ["Appium", "JMeter", "8+ years experience"]),
            ("Senior QA Lead", "CleverTap", "Mumbai, Maharashtra", "7+ years", ["Big Data Testing", "Team Mentorship", "7+ years experience"]),
            ("Test Automation Manager", "Capgemini", "Pune, Maharashtra", "8+ years", ["QA Governance", "8+ years experience"]),
            ("Lead SDET (Python & Performance)", "Pine Labs", "Noida, Uttar Pradesh", "6+ years", ["Locust", "JMeter", "6+ years experience"]),
            ("Principal Quality Assurance Lead", "Wipro", "Hyderabad, Telangana", "8+ years", ["COE Leadership", "8+ years experience"]),
            ("Senior SDET Manager", "Tech Mahindra", "Pune, Maharashtra", "7-10 years", ["Resource Allocation", "7+ years experience"]),
            ("Staff Quality Engineer", "Groww", "Bangalore, Karnataka", "8+ years", ["Security Testing", "8+ years experience"]),
            ("Lead Test Automation Architect", "Postman", "Bangalore, Karnataka", "7+ years", ["Chaos Testing", "7+ years experience"]),
            ("Senior QA Lead (6+ yrs)", "Cimpress", "Mumbai, Maharashtra", "6+ years", ["Team Mentoring", "6+ years experience"]),
            ("Head of Quality Assurance", "Persistent Systems", "Pune, Maharashtra", "10+ years", ["QA Org Leadership", "10+ years experience"]),
            ("Senior SDET Lead (5-8 yrs)", "TCS", "Mumbai, Maharashtra", "5-8 years", ["Performance Testing", "5+ years experience"]),
        ],
        "tech_focus": "QA strategy, Test Automation Architecture, JMeter performance testing, Team management, CI/CD pipeline governance, Executive reporting",
    },
    {
        "category": "Mobile_Dev_OutOfScope",
        "min_score": 0,
        "max_score": 20,
        "is_testing": False,
        "acceptable_pass": False,
        "target_domain": "Mobile Development (Out of Scope)",
        "roles": [
            ("Junior iOS Developer", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["Swift", "SwiftUI", "iOS SDK", "Xcode"]),
            ("Associate Android Engineer", "Razorpay", "Bangalore, Karnataka", "0-2 years", ["Kotlin", "Android SDK", "Jetpack Compose"]),
            ("Flutter App Developer (0-2 yrs)", "Zeta Suite", "Bangalore, Karnataka", "0-2 years", ["Flutter", "Dart"]),
            ("React Native Mobile Developer", "CleverTap", "Mumbai, Maharashtra", "0-2 years", ["React Native"]),
            ("Entry Level iOS Developer", "Persistent Systems", "Pune, Maharashtra", "Fresher", ["Swift", "CocoaTouch", "Xcode"]),
            ("Junior Android Developer", "InMobi", "Bangalore, Karnataka", "0-1 years", ["Android SDK", "Kotlin", "Android Studio"]),
            ("Flutter Mobile Engineer Trainee", "Mindtree", "Pune, Maharashtra", "Fresher", ["Flutter", "Dart"]),
            ("iOS Application Developer (0-1 yr)", "LTIMindtree", "Pune, Maharashtra", "0-1 years", ["Swift", "Objective-C", "iOS SDK"]),
            ("Android Software Engineer (Fresher)", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", ["Kotlin", "Android SDK", "Room DB"]),
            ("Mobile App Developer (Flutter/Dart)", "Infosys", "Pune, Maharashtra", "Fresher / 0-1 yr", ["Flutter", "Dart"]),
            ("Junior Swift / iOS Developer", "Cognizant", "Chennai, Tamil Nadu", "0-2 years", ["Swift", "UIKit", "SwiftUI"]),
            ("React Native Mobile Specialist", "Capgemini", "Pune, Maharashtra", "0-2 years", ["React Native"]),
            ("Android App Developer Trainee", "TCS", "Pune, Maharashtra", "Fresher", ["Android SDK", "Kotlin"]),
            ("Mobile Software Engineer (iOS)", "Wipro", "Hyderabad, Telangana", "0-2 years", ["Swift", "Xcode", "iOS SDK"]),
            ("Junior Flutter Developer", "Groww", "Bangalore, Karnataka", "0-1 years", ["Flutter", "Dart"]),
            ("Associate Android Developer", "Tech Mahindra", "Pune, Maharashtra", "0-2 years", ["Android SDK", "Kotlin"]),
            ("iOS Developer - Early Career", "Postman", "Bangalore, Karnataka", "0-2 years", ["Swift", "Xcode"]),
            ("React Native Mobile Engineer", "Cimpress", "Mumbai, Maharashtra", "0-1 years", ["React Native"]),
            ("Junior Kotlin Android Developer", "Barclays", "Pune, Maharashtra", "0-2 years", ["Kotlin", "Android SDK"]),
            ("Flutter & Cross-Platform Mobile Engineer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Flutter", "Dart"]),
        ],
        "tech_focus": "Swift, SwiftUI, iOS SDK, Kotlin, Jetpack Compose, Android SDK, Flutter, Dart, React Native, Mobile App Lifecycle",
    },
    {
        "category": "Legacy_OutOfScope",
        "min_score": 0,
        "max_score": 20,
        "is_testing": False,
        "acceptable_pass": False,
        "target_domain": "Legacy / Specialized Stacks (Out of Scope)",
        "roles": [
            ("Junior PHP Developer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["PHP", "Laravel"]),
            ("Ruby on Rails Developer (0-2 yrs)", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["Ruby", "Ruby on Rails"]),
            ("Salesforce Developer Trainee", "Cognizant", "Mumbai, Maharashtra", "Fresher", ["Salesforce", "Apex", "Visualforce"]),
            ("SAP ABAP Consultant (Fresher)", "LTIMindtree", "Pune, Maharashtra", "Fresher", ["SAP", "ABAP"]),
            ("Junior WordPress / PHP Developer", "Capgemini", "Pune, Maharashtra", "0-2 years", ["PHP", "WordPress"]),
            ("Associate Salesforce CRM Developer", "TCS", "Pune, Maharashtra", "0-2 years", ["Salesforce", "Apex", "LWC"]),
            ("Junior Ruby on Rails Engineer", "CleverTap", "Mumbai, Maharashtra", "0-1 years", ["Ruby", "Ruby on Rails", "RSpec"]),
            ("PHP / Symfony Developer Trainee", "Infosys", "Pune, Maharashtra", "Fresher", ["PHP", "Symfony"]),
            ("SAP HANA & ABAP Associate", "Wipro", "Hyderabad, Telangana", "0-2 years", ["SAP", "ABAP", "HANA"]),
            ("Drupal / PHP Web Developer", "Mindtree", "Bangalore, Karnataka", "0-2 years", ["Drupal", "PHP"]),
            ("Entry Level Salesforce Engineer", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", ["Salesforce", "Apex"]),
            ("Junior Laravel Developer", "Persistent Systems", "Nagpur / Pune", "0-1 years", ["PHP", "Laravel"]),
            ("Ruby on Rails Software Engineer", "InMobi", "Bangalore, Karnataka", "0-2 years", ["Ruby", "Ruby on Rails", "Sidekiq"]),
            ("SAP Fiori & ABAP Developer", "Barclays", "Pune, Maharashtra", "0-2 years", ["SAP", "ABAP", "SAP Fiori"]),
            ("Junior PHP / CodeIgniter Developer", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", ["PHP", "CodeIgniter"]),
            ("Salesforce Associate Consultant", "Zeta Suite", "Bangalore, Karnataka", "0-2 years", ["Salesforce", "Apex"]),
            ("Ruby Developer - Early Career", "Postman", "Bangalore, Karnataka", "0-1 years", ["Ruby", "Rails"]),
            ("SAP Technical Trainee", "Cimpress", "Mumbai, Maharashtra", "Fresher", ["SAP", "ABAP"]),
            ("PHP Web Application Developer", "Groww", "Bangalore, Karnataka", "0-2 years", ["PHP", "Laravel"]),
            ("Associate Salesforce Developer", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Salesforce", "Apex"]),
        ],
        "tech_focus": "PHP, Laravel, Symfony, Ruby on Rails, Salesforce CRM, Apex, Visualforce, SAP ABAP, SAP HANA, Drupal, WordPress",
    },
    {
        "category": "DevOps_Cloud_Infra",
        "min_score": 30,
        "max_score": 55,
        "is_testing": False,
        "acceptable_pass": False,
        "target_domain": "DevOps / Cloud Infrastructure (Edge: Partial Match)",
        "roles": [
            ("Junior DevOps Engineer", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["AWS", "Terraform", "Jenkins"]),
            ("Cloud Infrastructure Associate", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["Terraform", "AWS", "Linux SysAdmin"]),
            ("Site Reliability Engineer (SRE) Trainee", "Razorpay", "Bangalore, Karnataka", "Fresher", ["Prometheus", "Grafana", "Linux SysAdmin"]),
            ("Junior Cloud Operations Engineer", "Cognizant", "Mumbai, Maharashtra", "0-2 years", ["AWS", "Ansible", "Jenkins"]),
            ("DevOps Trainee", "LTIMindtree", "Pune, Maharashtra", "Fresher / 0-1 yr", ["Jenkins", "Terraform", "Bash"]),
            ("Associate DevOps Engineer", "Zeta Suite", "Bangalore, Karnataka", "0-2 years", ["Helm", "Terraform", "AWS"]),
            ("Systems & Cloud Infrastructure Associate", "Capgemini", "Pune, Maharashtra", "0-1 years", ["AWS", "Ansible", "Linux SysAdmin"]),
            ("SRE - Early Career", "InMobi", "Bangalore, Karnataka", "0-2 years", ["Datadog", "Prometheus", "Linux SysAdmin"]),
            ("Junior Cloud & DevOps Specialist", "TCS", "Pune, Maharashtra", "0-2 years", ["AWS", "Terraform", "CI/CD"]),
            ("DevOps Engineer (0-2 yrs)", "Mindtree", "Bangalore, Karnataka", "0-2 years", ["Jenkins", "AWS"]),
            ("Associate Infrastructure Engineer", "Infosys", "Pune, Maharashtra", "Fresher", ["Ansible", "AWS", "Linux SysAdmin"]),
            ("Junior Site Reliability Engineer", "CleverTap", "Mumbai, Maharashtra", "0-1 years", ["AWS", "Prometheus", "Alertmanager"]),
            ("Cloud Support & DevOps Associate", "Wipro", "Hyderabad, Telangana", "0-2 years", ["Terraform", "Jenkins", "AWS"]),
            ("Junior Infrastructure Automation Engineer", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", ["Ansible", "Terraform", "AWS"]),
            ("DevOps Associate Trainee", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", ["Jenkins", "Terraform"]),
            ("SRE Associate", "Groww", "Bangalore, Karnataka", "0-2 years", ["Prometheus", "Grafana", "AWS"]),
            ("Junior Cloud DevOps Engineer", "Barclays", "Pune, Maharashtra", "0-2 years", ["Terraform", "Jenkins", "AWS"]),
            ("Cloud Systems Engineer - Early Career", "Postman", "Bangalore, Karnataka", "0-1 years", ["AWS", "Terraform", "Datadog"]),
            ("Junior Site Reliability Specialist", "Cimpress", "Mumbai, Maharashtra", "0-2 years", ["Linux SysAdmin", "Prometheus", "Bash"]),
            ("Associate Cloud & SRE Engineer", "Persistent Systems", "Pune, Maharashtra", "0-2 years", ["AWS", "Terraform", "Ansible"]),
        ],
        "tech_focus": "AWS cloud infrastructure, Terraform, Ansible, Jenkins CI/CD, Kubernetes cluster administration, Prometheus, Linux sysadmin",
    },
    {
        "category": "Sparse_Job_Description",
        "min_score": 40,
        "max_score": 60,
        "is_testing": False,
        "acceptable_pass": False,
        "target_domain": "Sparse / Minimal Description (Edge Case)",
        "roles": [
            ("Software Engineer", "Tech Mahindra", "Pune, Maharashtra", "0-1 years", []),
            ("Developer Trainee", "Cognizant", "Mumbai, Maharashtra", "Fresher", []),
            ("IT Trainee", "LTIMindtree", "Pune, Maharashtra", "Fresher / 2025-2026 Batch", []),
            ("Software Associate", "Persistent Systems", "Pune, Maharashtra", "0-1 years", []),
            ("Programmer Analyst Trainee", "Wipro", "Hyderabad, Telangana", "Fresher", []),
            ("Junior Web Developer", "Infotech Solutions", "Bangalore, Karnataka", "0-1 years", []),
            ("Software Developer", "Global Services", "Remote, India", "0-2 years", []),
            ("Associate Software Engineer", "Apex Systems", "Pune, Maharashtra", "Fresher", []),
            ("Entry Level Developer", "Sigma Technologies", "Mumbai, Maharashtra", "0-1 years", []),
            ("Junior Developer", "Alpha Soft", "Bangalore, Karnataka", "0-1 years", []),
            ("Graduate Trainee", "Delta Corp", "Chennai, Tamil Nadu", "Fresher", []),
            ("Software Engineer - Fresher", "Zenith Info", "Pune, Maharashtra", "Fresher", []),
            ("Junior Programmer", "Omega Tech", "Noida, Uttar Pradesh", "0-1 years", []),
            ("Software Trainee", "Prime Solutions", "Hyderabad, Telangana", "Fresher", []),
            ("Developer - Entry Level", "Radiant Systems", "Pune, Maharashtra", "0-1 years", []),
            ("IT Engineer Trainee", "Summit Tech", "Gurgaon, Haryana", "Fresher", []),
            ("Associate Programmer", "Vector Labs", "Bangalore, Karnataka", "0-1 years", []),
            ("Junior Software Associate", "Vista Services", "Mumbai, Maharashtra", "Fresher", []),
            ("Software Developer Trainee", "Nexus Tech", "Pune, Maharashtra", "0-1 years", []),
            ("Entry Level Engineer", "Horizon IT", "Pune, Maharashtra", "Fresher", []),
        ],
        "tech_focus": "Minimal 1-2 sentence description testing AI handling of sparse text",
    },
    {
        "category": "Non_Technical_Role",
        "min_score": 0,
        "max_score": 10,
        "is_testing": False,
        "acceptable_pass": False,
        "target_domain": "Non-Technical / Business / Operations",
        "roles": [
            ("Business Development Executive (BDE)", "Swiggy", "Bangalore, Karnataka", "0-2 years", ["B2B Sales", "Lead Generation", "Cold Calling"]),
            ("Technical Recruiter", "Persistent Systems", "Pune, Maharashtra", "0-1 years", ["IT Recruitment", "Talent Sourcing", "Interview Scheduling"]),
            ("Digital Marketing Executive", "CleverTap", "Mumbai, Maharashtra", "0-2 years", ["SEO", "SEM", "Google Ads", "Social Media Marketing"]),
            ("HR Operations Associate", "LTIMindtree", "Pune, Maharashtra", "Fresher / 0-1 yr", ["Employee Onboarding", "HR Operations", "Payroll"]),
            ("Financial Analyst Trainee", "Barclays", "Pune, Maharashtra", "0-1 years", ["Financial Modeling", "Accounting", "Financial Analysis"]),
            ("Inside Sales Representative", "Razorpay", "Bangalore, Karnataka", "0-2 years", ["Outbound Sales", "CRM Management", "Cold Calling"]),
            ("Customer Success Specialist", "Freshworks", "Chennai, Tamil Nadu", "0-1 years", ["Customer Success", "Account Management"]),
            ("Content Writer & Copywriter", "InMobi", "Bangalore, Karnataka", "0-2 years", ["Copywriting", "Creative Writing", "Editorial Proofreading"]),
            ("Brand & Public Relations Associate", "Pine Labs", "Noida, Uttar Pradesh", "0-1 years", ["Public Relations", "Press Releases", "Event Coordination"]),
            ("Corporate Legal Assistant", "Mindtree", "Bangalore, Karnataka", "0-2 years", ["Contract Review", "Legal Compliance", "NDA Preparation"]),
            ("Talent Acquisition Specialist", "Cognizant", "Mumbai, Maharashtra", "0-2 years", ["Campus Hiring", "Talent Acquisition"]),
            ("Sales Operations Coordinator", "Zeta Suite", "Bangalore, Karnataka", "0-1 years", ["Sales Operations", "Sales Tracking"]),
            ("Social Media Manager", "Groww", "Bangalore, Karnataka", "0-2 years", ["Community Management", "Influencer Outreach"]),
            ("Office Administrator & Facilities Executive", "Capgemini", "Pune, Maharashtra", "0-2 years", ["Office Administration", "Vendor Management"]),
            ("Accountant & Financial Trainee", "TCS", "Pune, Maharashtra", "0-1 years", ["GST Filing", "Taxation", "Tally ERP"]),
            ("Product Marketing Associate", "Postman", "Bangalore, Karnataka", "0-2 years", ["Product Marketing", "GTM Strategy", "Sales Enablement"]),
            ("Procurement Specialist", "Wipro", "Hyderabad, Telangana", "0-1 years", ["Procurement", "Vendor Negotiation", "Purchase Orders"]),
            ("Operations Executive", "Tech Mahindra", "Pune, Maharashtra", "0-2 years", ["Operations Management", "SLA Monitoring"]),
            ("Graphic Designer & Visual Artist", "Cimpress", "Mumbai, Maharashtra", "0-2 years", ["Adobe Photoshop", "Adobe Illustrator", "Graphic Design"]),
            ("Corporate Trainer - Soft Skills", "Infosys", "Pune, Maharashtra", "0-2 years", ["Soft Skills Training", "Behavioral Coaching"]),
        ],
        "tech_focus": "Sales, Marketing, HR, Finance, Procurement, Administration, Graphic Design, Soft Skills",
    }
]


def _build_sparse_description(title: str, company: str, location: str, exp: str, idx: int) -> str:
    """Generates realistic minimal 1-2 sentence descriptions for Category 14."""
    templates = [
        f"We are hiring fresh engineering graduates with strong computer science basics and problem-solving skills for {title} positions at {company} in {location}. Immediate joiners with good academic record preferred.",
        f"Looking for energetic junior developers with foundational knowledge in Java, Python, or Web Technologies to join our engineering team at {company}, {location}. Freshers with 2025/2026 graduation batch are eligible.",
        f"{company} is conducting campus/off-campus hiring for {title} roles ({exp}) based out of our {location} facility. Candidates must possess good analytical reasoning and communication skills.",
        f"Seeking enthusiastic entry-level candidates for {title} role at {company}. Must have an understanding of core computer science subjects, algorithms, and database management.",
        f"Urgent requirement for {title} ({exp}) at {company}, {location}. Walk-in interviews scheduled this weekend for passionate candidates who want to start their software development career.",
        f"Hiring freshers with B.E./B.Tech/MCA in IT or Computer Science for {title} position at {company}. Strong aptitude and willingness to learn modern tech stacks required.",
        f"{company} invites applications from junior software professionals for {title} in {location}. Basic coding knowledge in any standard language and SQL is desirable.",
        f"Immediate opening for {title} ({exp}) at {company}. Selected candidates will undergo technical training on enterprise software solutions in {location}.",
        f"We are seeking motivated entry-level {title} candidates in {location} to assist our engineering teams in designing, testing, and maintaining software applications.",
        f"{company} is hiring for {title} ({exp}). If you are passionate about coding, algorithms, and clean software architecture, submit your resume for review."
    ]
    return templates[idx % len(templates)]


def _build_rich_description(
    category: str,
    title: str,
    company: str,
    location: str,
    exp: str,
    missing_skills: List[str],
    idx: int
) -> str:
    """Generates rich, realistic, multi-paragraph job descriptions tailored to category and role."""
    
    # 1. Company Intro / Culture
    company_intros = [
        f"{company} is a leading digital transformation and technology solutions provider, empowering global enterprises across banking, healthcare, retail, and logistics through cutting-edge software engineering.",
        f"At {company}, we build mission-critical digital products and high-concurrency systems that serve millions of active users daily, fostering an engineering culture founded on innovation, ownership, and technical excellence.",
        f"Join the engineering organization at {company}, where our multidisciplinary teams develop scalable cloud-native architectures, resilient distributed systems, and customer-centric software solutions in {location}.",
        f"{company} is recognized globally for engineering excellence and digital innovation. We are expanding our core technical team in {location} to accelerate the delivery of next-generation enterprise platforms."
    ]
    intro = company_intros[idx % len(company_intros)]

    # 2. Category-Specific Body
    if category == "Java_Spring_Backend":
        desc = f"""About the Role:
{intro}
We are seeking a talented and motivated {title} to join our backend engineering team in {location}. In this role, you will design, develop, and maintain robust backend microservices, RESTful APIs, and database components that power our core product capabilities.

Key Responsibilities:
- Design, implement, and maintain high-performance backend APIs and microservices using Core Java and the Spring Framework (Spring Boot, Spring Core).
- Write modular, testable, and clean code adhering to SOLID design principles and standard design patterns.
- Implement database interactions using JDBC, Hibernate/JPA, and write optimized SQL queries, indexes, and stored procedures on relational databases (MySQL / PostgreSQL).
- Build and consume secure RESTful web services with comprehensive JSON payload validation and HTTP status handling.
- Collaborate closely with frontend engineers, QA specialists, and product managers in an Agile/Scrum environment.
- Troubleshoot, debug, and optimize application performance and latency across production services.

Qualifications & Technical Requirements:
- Education: Bachelor's degree (B.E. / B.Tech) in Computer Science, Information Technology, or related discipline.
- Experience: {exp}. Freshers with strong project credentials and internship experience are warmly encouraged to apply.
- Strong proficiency in Core Java (Collections, Multithreading, OOP concepts, Exception Handling).
- Hands-on experience with Spring Core or Spring Boot and REST API development.
- Solid understanding of Relational Database Management Systems (RDBMS) and SQL (MySQL, PostgreSQL).
- Familiarity with version control using Git/GitHub and build automation tools like Maven.
- Strong problem-solving abilities, Data Structures & Algorithms (DSA) foundation, and communication skills."""

    elif category == "QA_Automation_Testing":
        desc = f"""About the Role:
{intro}
We are looking for a dedicated {title} to ensure the highest quality standards for our enterprise web applications and API ecosystems in {location}. You will be responsible for creating, executing, and automating test suites across the software testing lifecycle.

Key Responsibilities:
- Develop, maintain, and execute automated regression test suites using Selenium WebDriver and modern testing frameworks (JUnit / TestNG / pytest).
- Design comprehensive test plans, detailed test cases, test data sets, and defect reports covering functional, regression, and sanity testing.
- Conduct robust API testing using Postman to validate status codes, response payloads, headers, and authentication tokens.
- Identify, document, track, and verify software bugs using bug tracking workflows, collaborating with developers to achieve swift resolution.
- Participate in sprint planning, user story grooming, and quality gate reviews within an Agile delivery team.
- Assist in optimizing test automation coverage and accelerating CI/CD deployment pipelines.

Qualifications & Technical Requirements:
- Education: B.E. / B.Tech / MCA in Information Technology, Computer Science, or equivalent.
- Experience Level: {exp}.
- Strong hands-on knowledge of Selenium WebDriver with Java or Python.
- Proven experience in API testing using Postman (automated assertions and environment variables).
- Solid grasp of Software Testing Life Cycle (STLC) and Software Development Life Cycle (SDLC).
- Experience in writing test scripts with JUnit or pytest.
- Basic understanding of SQL queries for test data validation in relational databases.
- Good understanding of version control with Git and Agile/Scrum methodologies."""

    elif category == "MERN_Stack":
        desc = f"""About the Role:
{intro}
We are hiring a passionate {title} to build dynamic, responsive, and full-stack web applications in {location}. You will work across both client-side interfaces and server-side architectures using the modern JavaScript ecosystem.

Key Responsibilities:
- Develop interactive, responsive, and cross-browser compatible frontend interfaces using React.js, HTML5, and CSS3.
- Build scalable server-side applications, microservices, and RESTful APIs using Node.js and Express.js.
- Model, query, and manage NoSQL databases using MongoDB and Mongoose ODM.
- Implement secure authentication and authorization mechanisms (JWT, session management, OAuth).
- Integrate frontend client applications with backend REST endpoints, handling asynchronous data flows and state.
- Write clean, modular, and maintainable JavaScript (ES6+) and TypeScript code.
- Optimize web applications for maximum speed, responsiveness, and SEO performance.

Qualifications & Technical Requirements:
- Education: B.E. / B.Tech in IT/CS or relevant degree.
- Experience: {exp}.
- Proficiency in React.js (Hooks, Component Lifecycle, Virtual DOM).
- Strong hands-on capability in Node.js and Express.js backend development.
- Familiarity with MongoDB database schemas, CRUD operations, and Mongoose indexing.
- Solid understanding of JavaScript fundamentals (Promises, Event Loop, Closures, Async/Await).
- Experience using Git/GitHub for source control and collaboration."""

    elif category == "AI_ML_LLM":
        desc = f"""About the Role:
{intro}
We are actively seeking an enthusiastic {title} to join our cutting-edge AI Innovation Lab in {location}. You will work on integrating Large Language Models (LLMs), engineering intelligent prompts, and developing automated AI-driven workflows that transform business operations.

Key Responsibilities:
- Build and deploy AI-driven software pipelines leveraging state-of-the-art LLMs (Gemini, OpenAI, DeepSeek, Claude) via REST APIs.
- Formulate, test, and optimize advanced prompt engineering strategies (Few-Shot, Chain-of-Thought, structured JSON outputs).
- Process, parse, and analyze structured and unstructured datasets using Python and Pandas.
- Implement intelligent automation features, text summarization, data extraction, and semantic search agents.
- Integrate LLM inference endpoints into backend web services using Python frameworks (FastAPI / Flask).
- Monitor token utilization, API latency, and model hallucination rates, optimizing inference cost and throughput.

Qualifications & Technical Requirements:
- Education: B.E. / B.Tech / M.Tech in Computer Science, Data Science, Artificial Intelligence, or related fields.
- Experience: {exp}.
- Strong Python programming skills, with hands-on experience in Pandas, Regex, and Asyncio.
- Demonstrated experience integrating LLM APIs and building structured JSON responses.
- Understanding of prompt engineering techniques and generative AI principles.
- Familiarity with RESTful API communication and JSON data schemas.
- Strong analytical mindset, curiosity for modern AI advancements, and solid DSA fundamentals."""

    elif category == "Python_Backend":
        desc = f"""About the Role:
{intro}
We are looking for a sharp {title} to engineer scalable backend services and high-throughput data processing workflows in {location}. You will design REST APIs and data models that support critical enterprise operations.

Key Responsibilities:
- Develop clean, asynchronous, and robust backend services using Python and web frameworks (Django / Flask / FastAPI).
- Design and implement RESTful APIs with comprehensive documentation, serialization, and error handling.
- Build efficient database schemas and execute optimized queries using PostgreSQL, MySQL, or SQLite.
- Implement background workers, scheduled automated tasks, and data ingestion routines.
- Write unit and integration tests using pytest to maintain high test coverage and system stability.
- Collaborate with frontend developers and DevOps engineers to deploy and monitor services.

Qualifications & Technical Requirements:
- Education: Bachelor's in Computer Science, IT, or related degree.
- Experience: {exp}.
- Strong proficiency in Python 3.x, OOP concepts, and asynchronous programming.
- Hands-on experience developing REST APIs with Django, Flask, or FastAPI.
- Solid understanding of relational database management, SQL queries, and normalization.
- Familiarity with Git, automated testing with pytest, and containerization basics."""

    elif category == "DotNet_CSharp":
        desc = f"""About the Role:
{intro}
We are expanding our Microsoft Technology Practice in {location} and are hiring a junior {title}. In this role, you will contribute to the engineering of enterprise web applications and cloud solutions built on the .NET ecosystem.

Key Responsibilities:
- Develop backend APIs and web services using C# and modern .NET Core / ASP.NET frameworks.
- Implement business logic and data access layers adhering to Object-Oriented Programming (OOP) and MVC architecture.
- Write and optimize SQL queries, stored procedures, and tables on Microsoft SQL Server or Azure SQL databases.
- Integrate cloud components and microservices hosted on Microsoft Azure.
- Perform code debugging, unit testing, and participate in peer code reviews within Agile teams.
- Maintain and enhance existing enterprise .NET modules.

Qualifications & Technical Requirements:
- Education: B.E. / B.Tech in Computer Engineering, IT, or equivalent.
- Experience: {exp}.
- Foundational understanding of C# programming, OOP concepts, collections, and exception handling.
- Basic familiarity with .NET Core / ASP.NET Web API development.
- Knowledge of relational databases and SQL Server syntax.
- Microsoft Azure Fundamentals certification or cloud concepts awareness is highly advantageous.
- Good analytical and verbal communication skills."""

    elif category == "FullStack_SWE":
        desc = f"""About the Role:
{intro}
We are looking for a versatile {title} to contribute across our full software delivery lifecycle in {location}. You will solve technical problems across both user interfaces and backend services, developing seamless digital applications.

Key Responsibilities:
- Develop responsive, accessible web interfaces utilizing HTML5, CSS3, JavaScript (ES6+), and modern UI frameworks like React.js.
- Implement server-side logic, API endpoints, and data processing routines using Python or Java backend services.
- Design, manage, and query relational databases (MySQL / PostgreSQL) for optimal data storage and retrieval.
- Collaborate with product designers to translate UI/UX wireframes into functional, interactive web pages.
- Participate in Agile ceremonies, write unit tests, and maintain Git code repositories.
- Troubleshoot cross-browser compatibility issues and optimize frontend/backend performance.

Qualifications & Technical Requirements:
- Education: B.E. / B.Tech in CS/IT or equivalent degree.
- Experience: {exp}.
- Proficiency in core web technologies: HTML5, CSS3, JavaScript (DOM manipulation, async programming).
- Hands-on experience with React.js frontend development.
- Backend foundation in either Python (Django/Flask) or Java (Spring/JDBC).
- Solid SQL querying capabilities and relational database design understanding.
- Strong problem-solving acumen, curiosity to master new technologies, and team spirit."""

    elif category == "Manual_QA_Testing":
        desc = f"""About the Role:
{intro}
We are seeking a detail-oriented {title} to join our Quality Assurance group in {location}. You will play a crucial role in validating software applications, identifying functional bugs, and ensuring flawless user experiences before releases.

Key Responsibilities:
- Analyze functional requirement specifications, user stories, and acceptance criteria to design detailed test cases and test scenarios.
- Execute manual test cycles including Smoke, Sanity, Functional, Negative, Integration, and Regression testing across web applications.
- Log, report, and track bugs with clear steps to reproduce, screenshots, and system logs in defect tracking tools.
- Conduct basic API testing using Postman to verify backend data contracts, response codes, and JSON schemas.
- Execute SQL queries to validate database state, backend data integrity, and records persistence.
- Collaborate with software developers, business analysts, and QA leads to verify bug fixes and sign off on release builds.

Qualifications & Technical Requirements:
- Education: B.E., B.Tech, BCA, MCA, or B.Sc in Computer Science / IT.
- Experience: {exp}.
- Strong understanding of Software Testing Life Cycle (STLC), test levels, and testing types (Black-box, White-box).
- Hands-on skill in authoring comprehensive test cases, test matrices, and bug reports.
- Basic knowledge of Postman for API verification.
- Basic SQL knowledge (SELECT, INSERT, UPDATE, JOINs).
- Excellent attention to detail, analytical mindset, and clear written documentation skills."""

    elif category == "Senior_Java_Lead":
        desc = f"""About the Role:
{intro}
We are seeking an accomplished, battle-tested {title} with {exp} of hands-on expertise to lead the technical architecture and delivery of our flagship distributed systems in {location}.

Key Responsibilities:
- Architect, design, and lead the implementation of high-throughput, low-latency distributed microservices in Java 17/21.
- Establish architectural standards, design patterns, and engineering governance across multiple development teams.
- Lead system design reviews, capacity planning, and disaster recovery strategies for high-scale enterprise platforms.
- Mentor senior and junior software engineers, drive technical excellence, and lead technical hiring.
- Drive adoption of event-driven architectures utilizing Apache Kafka, distributed caching with Redis, and Kubernetes orchestration.
- Interface with executive stakeholders, product directors, and client leadership on strategic technology roadmaps.

Qualifications & Technical Requirements:
- Education: Bachelor's or Master's in Computer Science or related field.
- Mandatory Experience: {exp} of professional software engineering experience (strictly 5-10+ years required).
- Deep mastery of Java, Spring Boot, Spring Cloud, and distributed microservices architecture.
- Extensive experience designing fault-tolerant distributed systems handling millions of events/transactions.
- Proven track record mentoring engineering teams and leading complex cross-functional initiatives.
- Deep expertise in Kafka, Redis, PostgreSQL, Kubernetes, and enterprise cloud design."""

    elif category == "Senior_QA_Lead":
        desc = f"""About the Role:
{intro}
We are hiring a visionary {title} with {exp} of proven quality leadership to head our Quality Engineering and Test Automation organization in {location}.

Key Responsibilities:
- Define and execute the end-to-end quality assurance strategy, test governance, and automation vision for enterprise ecosystems.
- Architect scalable, maintainable test automation frameworks from the ground up across web, mobile, and API layers.
- Oversee enterprise performance, load, stress, and chaos engineering testing using JMeter, Gatling, and Locust.
- Manage and mentor a team of 10+ SDETs and QA engineers, conducting technical reviews and setting performance benchmarks.
- Integrate quality gates into enterprise CI/CD pipelines, automating regression cycles and continuous deployment monitoring.
- Communicate quality metrics, risk assessments, and test coverage analytics to senior executive leadership.

Qualifications & Technical Requirements:
- Education: Bachelor's/Master's in Engineering or Computer Science.
- Mandatory Experience: {exp} in Quality Engineering and Test Automation leadership (strictly 5+ years required).
- Expert-level mastery of test automation architecture (Selenium, Appium, Playwright, REST Assured).
- Proven experience leading performance and security testing at scale.
- Strong organizational management, client handling, and strategic planning skills."""

    elif category == "Mobile_Dev_OutOfScope":
        desc = f"""About the Role:
{intro}
We are seeking an innovative {title} to build engaging mobile applications in {location}. You will design, build, and publish high-performance mobile apps for millions of smartphone users worldwide.

Key Responsibilities:
- Develop native and cross-platform mobile user interfaces and features according to platform design specifications.
- Integrate native device hardware APIs (Camera, GPS, Bluetooth, Push Notifications, Biometrics).
- Connect mobile client applications to backend RESTful and GraphQL endpoints, handling offline storage and caching.
- Optimize mobile application performance, startup times, memory consumption, and battery footprint.
- Manage mobile build configurations, code signing, and deployments to the Apple App Store and Google Play Console.
- Write unit tests and UI tests for mobile user journeys.

Qualifications & Technical Requirements:
- Education: B.E. / B.Tech in Computer Science, IT, or related degree.
- Experience: {exp}.
- Primary expertise in mobile app development platforms (iOS Swift/SwiftUI, Android Kotlin/Jetpack Compose, or Flutter/Dart).
- Experience utilizing mobile development IDEs (Xcode or Android Studio).
- Understanding of mobile app architecture patterns (MVVM, Clean Architecture, Bloc).
- Familiarity with publishing apps to Google Play Store or Apple App Store."""

    elif category == "Legacy_OutOfScope":
        desc = f"""About the Role:
{intro}
We are looking for a skilled {title} to develop, customize, and maintain business systems and web applications in {location}. You will work on specialized platform technologies powering enterprise business workflows.

Key Responsibilities:
- Develop custom application modules, business logic, and workflows using specialized backend languages and enterprise packages.
- Design database models, write custom queries, and integrate with external third-party software systems.
- Customize enterprise packages, plugins, themes, and customer relationship management (CRM) workflows.
- Troubleshoot legacy codebases, perform code refactoring, and implement new client feature requests.
- Provide production support, patch deployments, and data migration assistance for enterprise customers.

Qualifications & Technical Requirements:
- Education: Bachelor's degree in IT, Computer Science, or related field.
- Experience: {exp}.
- Core proficiency in specialized technology stacks (PHP, Laravel, Ruby on Rails, Salesforce CRM Apex/Visualforce, or SAP ABAP).
- Strong understanding of relational database design, SQL queries, and data modeling.
- Experience in customized enterprise workflows and third-party integrations."""

    elif category == "DevOps_Cloud_Infra":
        desc = f"""About the Role:
{intro}
We are seeking a motivated {title} to support our cloud infrastructure, build automation pipelines, and maintain site reliability in {location}.

Key Responsibilities:
- Provision, configure, and manage cloud infrastructure on Amazon Web Services (AWS) using Infrastructure as Code (Terraform).
- Configure and manage enterprise CI/CD automation pipelines using Jenkins, GitLab CI, or GitHub Actions.
- Manage Docker container deployments and Kubernetes (EKS/GKE) cluster operations, namespaces, and ingress controllers.
- Configure system telemetry, metrics collection, and alerting using Prometheus, Grafana, and ELK stack.
- Manage Linux server administration, user access policies, network security, and shell scripting.
- Participate in on-call rotations to investigate production incidents and perform root-cause analysis (RCA).

Qualifications & Technical Requirements:
- Education: B.E. / B.Tech in Computer Science, IT, or Electronics.
- Experience: {exp}.
- Hands-on experience with AWS cloud services (EC2, S3, VPC, IAM, RDS, Route53).
- Proficiency with Infrastructure as Code using Terraform or Ansible.
- Strong Linux system administration foundation and Bash shell scripting skills.
- Understanding of Docker containerization and Kubernetes cluster concepts.
- Familiarity with CI/CD build tools like Jenkins and monitoring stacks."""

    elif category == "Non_Technical_Role":
        desc = f"""About the Role:
{intro}
We are looking for a proactive and results-driven {title} to join our business operations and commercial organization in {location}.

Key Responsibilities:
- Execute daily operational, commercial, or administrative initiatives supporting company growth and client satisfaction.
- Engage with internal and external stakeholders through effective verbal and written communication.
- Manage and maintain accurate records, databases, reports, and documentation using enterprise CRM, ERP, or spreadsheet tools.
- Coordinate cross-functional schedules, meetings, operational reviews, and deliverables.
- Analyze business metrics, identify operational bottlenecks, and implement continuous process improvements.

Qualifications & Technical Requirements:
- Education: Bachelor's degree in Business Administration, Commerce, Arts, Human Resources, or related field.
- Experience: {exp}.
- Excellent interpersonal, verbal, and written communication skills.
- Strong organizational, multitasking, and problem-solving abilities.
- Proficiency with Microsoft Office Suite (Excel, Word, PowerPoint) or Google Workspace.
- Ability to thrive in a dynamic, collaborative corporate environment."""

    else:
        desc = f"{intro}\nRole: {title}\nLocation: {location}\nExperience: {exp}\nJoin our engineering team."

    # 3. Add Optional / Secondary Missing Skills section realistically
    if missing_skills:
        skills_str = ", ".join(missing_skills)
        desc += f"\n\nPreferred / Good to Have Skills:\n- Prior exposure or familiarity with {skills_str} is considered an added advantage."

    # 4. Benefits & Offer
    desc += f"""\n\nWhat We Offer:
- Competitive compensation package and performance bonuses.
- Comprehensive health insurance coverage for you and your family.
- Hybrid and flexible working arrangements supporting work-life harmony.
- Generous learning & development allowances and professional certification support."""

    return desc


def generate_all_synthetic_jds() -> List[Dict[str, Any]]:
    """Generates exactly 300 synthetic JDs across 15 categories (20 each)."""
    jds = []
    job_counter = 1

    for spec in CATEGORY_SPECS:
        category = spec["category"]
        min_score = spec["min_score"]
        max_score = spec["max_score"]
        is_testing = spec["is_testing"]
        acceptable_pass = spec["acceptable_pass"]
        roles = spec["roles"]

        # Ensure exactly 20 roles per category
        assert len(roles) == 20, f"Category {category} has {len(roles)} roles, expected 20!"

        for i, (title, company, location, exp, missing_skills) in enumerate(roles):
            job_id = f"SYNTH_{job_counter:03d}"
            job_counter += 1

            if category == "Sparse_Job_Description":
                description = _build_sparse_description(title, company, location, exp, i)
            else:
                description = _build_rich_description(category, title, company, location, exp, missing_skills, i)

            jd_obj = {
                "id": job_id,
                "category": category,
                "title": title,
                "company": company,
                "location": location,
                "experience_required": exp,
                "description": description,
                "ground_truth": {
                    "expected_min_score": min_score,
                    "expected_max_score": max_score,
                    "is_testing_role": is_testing,
                    "expected_missing_skills": missing_skills,
                    "acceptable_pass": acceptable_pass
                }
            }
            jds.append(jd_obj)

    return jds


def validate_dataset(jds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates synthetic JDs against all schema, quantitative, and qualitative constraints:
    - Exactly 300 total records
    - Exactly 15 categories, 20 records each
    - Unique IDs formatted SYNTH_001 to SYNTH_300
    - All required fields present and non-empty
    - Valid ground truth score ranges [0, 100] with min <= max
    - Boolean flags valid
    - Expected missing skills genuinely missing from candidate resume
    """
    errors = []
    warnings = []

    # 1. Total Count
    if len(jds) != 300:
        errors.append(f"Total JDs count is {len(jds)}, expected exactly 300.")

    # 2. Category Distribution
    category_counts = {}
    for jd in jds:
        cat = jd.get("category")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    if len(category_counts) != 15:
        errors.append(f"Found {len(category_counts)} categories, expected exactly 15.")

    for cat, count in category_counts.items():
        if count != 20:
            errors.append(f"Category '{cat}' has {count} JDs, expected exactly 20.")

    # 3. ID Uniqueness and Schema Checks
    seen_ids = set()
    required_top_keys = ["id", "category", "title", "company", "location", "experience_required", "description", "ground_truth"]
    required_gt_keys = ["expected_min_score", "expected_max_score", "is_testing_role", "expected_missing_skills", "acceptable_pass"]

    for idx, jd in enumerate(jds):
        # Key presence
        for k in required_top_keys:
            if k not in jd:
                errors.append(f"JD #{idx} missing top-level key '{k}'.")
            elif not jd[k] and not isinstance(jd[k], (bool, int, list, dict)):
                errors.append(f"JD #{idx} has empty value for '{k}'.")

        # ID format
        jid = jd.get("id", "")
        if not re.match(r"^SYNTH_\d{3}$", jid):
            errors.append(f"JD #{idx} invalid id format '{jid}'. Expected SYNTH_xxx.")
        if jid in seen_ids:
            errors.append(f"Duplicate JD ID detected: '{jid}'.")
        seen_ids.add(jid)

        # Ground truth checks
        gt = jd.get("ground_truth", {})
        if not isinstance(gt, dict):
            errors.append(f"JD {jid} ground_truth is not a dict.")
            continue

        for gk in required_gt_keys:
            if gk not in gt:
                errors.append(f"JD {jid} ground_truth missing '{gk}'.")

        min_s = gt.get("expected_min_score")
        max_s = gt.get("expected_max_score")
        if not isinstance(min_s, int) or not isinstance(max_s, int):
            errors.append(f"JD {jid} score bounds not integers ({min_s}, {max_s}).")
        else:
            if not (0 <= min_s <= max_s <= 100):
                errors.append(f"JD {jid} invalid score range [{min_s}, {max_s}].")

        is_test = gt.get("is_testing_role")
        if not isinstance(is_test, bool):
            errors.append(f"JD {jid} is_testing_role is not a bool ({is_test}).")

        acc_pass = gt.get("acceptable_pass")
        if not isinstance(acc_pass, bool):
            errors.append(f"JD {jid} acceptable_pass is not a bool ({acc_pass}).")

        missing_skills = gt.get("expected_missing_skills", [])
        if not isinstance(missing_skills, list):
            errors.append(f"JD {jid} expected_missing_skills is not a list.")
        else:
            # Check candidate resume false-positives
            for s in missing_skills:
                norm_s = s.strip().lower()
                if norm_s in CANDIDATE_KNOWN_SKILLS:
                    errors.append(f"JD {jid} lists '{s}' as missing, but candidate HAS this skill in resume!")

    return {
        "valid": len(errors) == 0,
        "total_jds": len(jds),
        "total_categories": len(category_counts),
        "category_counts": category_counts,
        "errors": errors,
        "warnings": warnings
    }


# Pytest Test Cases
def test_synthetic_jds_total_count():
    jds = generate_all_synthetic_jds()
    assert len(jds) == 300, f"Expected 300 JDs, got {len(jds)}"


def test_synthetic_jds_category_distribution():
    jds = generate_all_synthetic_jds()
    category_counts = {}
    for jd in jds:
        cat = jd["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    assert len(category_counts) == 15, f"Expected 15 categories, got {len(category_counts)}"
    for cat, count in category_counts.items():
        assert count == 20, f"Category {cat} has {count} items, expected 20"


def test_synthetic_jds_schema_and_types():
    jds = generate_all_synthetic_jds()
    res = validate_dataset(jds)
    assert res["valid"], f"Validation failed with errors: {res['errors'][:5]}"


def test_synthetic_jds_no_false_missing_skills():
    jds = generate_all_synthetic_jds()
    for jd in jds:
        missing = jd["ground_truth"]["expected_missing_skills"]
        for s in missing:
            norm = s.strip().lower()
            assert norm not in CANDIDATE_KNOWN_SKILLS, f"Skill '{s}' in {jd['id']} is actually known by candidate!"


def main():
    parser = argparse.ArgumentParser(description="Generate and validate synthetic benchmark JDs.")
    parser.add_argument("--output", default="scoring_audit/synthetic_jds.json", help="Path to output JSON file")
    parser.add_argument("--verify", action="store_true", help="Only verify existing output file without regenerating")
    args = parser.parse_args()

    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path)

    if args.verify:
        if not os.path.exists(output_path):
            print(f"[ERROR] Target file does not exist: {output_path}")
            sys.exit(1)
        print(f"Loading and verifying {output_path}...")
        with open(output_path, "r", encoding="utf-8") as f:
            jds = json.load(f)
    else:
        print("Generating 300 synthetic job descriptions across 15 categories...")
        os.makedirs(output_dir, exist_ok=True)
        jds = generate_all_synthetic_jds()
        print(f"Writing dataset to {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(jds, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(jds)} records.")

    print("\nRunning comprehensive dataset validation...")
    validation_results = validate_dataset(jds)

    print("-" * 75)
    print(f"{'Category':<32} | {'Count':<6} | {'Expected Score':<16} | {'Testing?':<8}")
    print("-" * 75)
    for spec in CATEGORY_SPECS:
        cat = spec["category"]
        count = validation_results["category_counts"].get(cat, 0)
        score_rng = f"{spec['min_score']}-{spec['max_score']}"
        testing = str(spec["is_testing"])
        print(f"{cat:<32} | {count:<6} | {score_rng:<16} | {testing:<8}")
    print("-" * 75)

    if validation_results["valid"]:
        print("\n[SUCCESS] ALL VALIDATION CHECKS PASSED PERFECTLY!")
        print(f"Total JDs: {validation_results['total_jds']}")
        print(f"Total Categories: {validation_results['total_categories']}")
        print(f"Output File: {output_path}")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] Validation encountered {len(validation_results['errors'])} errors:")
        for err in validation_results["errors"][:20]:
            print(f" - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
