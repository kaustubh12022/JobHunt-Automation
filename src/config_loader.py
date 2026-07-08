import yaml
from pathlib import Path

from datetime import datetime

def get_human_date_str() -> str:
    """Return formatted date string (e.g., 2026-07-08) for folders and general usage."""
    return datetime.now().strftime('%Y-%m-%d')

def load_config() -> dict:
    """Load main configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_resume() -> dict:
    """Load master resume from data_folder/plain_text_resume.yaml."""
    resume_path = Path(__file__).parent.parent / "data_folder" / "plain_text_resume.yaml"
    with open(resume_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
