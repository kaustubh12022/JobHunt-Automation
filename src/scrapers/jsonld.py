import json
import logging
import urllib.request
from bs4 import BeautifulSoup
import yaml
from pathlib import Path
from src.logger import logger
from src.models import Job
import uuid
import re

def strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r'<[^>]+>', '', str(html))
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_jsonld(url: str) -> list[Job]:
    jobs = []
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read()
            
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            if not script.string:
                continue
                
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError:
                continue
                
            # data can be a list or a dict
            if isinstance(data, dict):
                data = [data]
                
            for item in data:
                if item.get('@type') == 'JobPosting':
                    title = item.get('title', '')
                    company_dict = item.get('hiringOrganization', {})
                    company = company_dict.get('name', 'Unknown')
                    
                    description = strip_html(item.get('description', ''))
                    
                    # Extract location
                    location_dict = item.get('jobLocation', {})
                    if isinstance(location_dict, list) and len(location_dict) > 0:
                        location_dict = location_dict[0]
                        
                    address = location_dict.get('address', {})
                    loc_parts = []
                    if isinstance(address, dict):
                        if address.get('addressLocality'): loc_parts.append(address['addressLocality'])
                        if address.get('addressRegion'): loc_parts.append(address['addressRegion'])
                        if address.get('addressCountry'): loc_parts.append(address['addressCountry'])
                    location = ", ".join(loc_parts) if loc_parts else "Unknown"
                    
                    jobs.append(Job(
                        id=str(uuid.uuid4()),
                        title=title,
                        company=company,
                        location=location,
                        description=description,
                        url=url,
                        source="jsonld"
                    ))
                    
    except Exception as e:
        logger.error(f"Error scraping JSON-LD from {url}: {e}")
        
    return jobs


def scrape_jsonld(test_mode: bool = False) -> list[Job]:
    """Main entry point for JSON-LD discovery"""
    yaml_path = Path(__file__).parent / "jsonld_sites.yaml"
    if not yaml_path.exists():
        return []
        
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            sites = data.get("sites", []) if data else []
    except Exception as e:
        logger.error(f"Failed to load JSON-LD sites: {e}")
        return []
        
    if not sites:
        return []
        
    if test_mode:
        logger.info("🧪 TEST MODE (JSON-LD): Scraping 1 site only.")
        sites = sites[:1]
        
    logger.info(f"🌐 Starting JSON-LD Scrape for {len(sites)} sites...")
    all_jobs = []
    
    for url in sites:
        jobs = extract_jsonld(url)
        all_jobs.extend(jobs)
        
    logger.info(f"✅ JSON-LD Scraper finished. Found {len(all_jobs)} jobs.")
    return all_jobs
