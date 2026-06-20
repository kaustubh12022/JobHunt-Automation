import yaml
from pathlib import Path

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
