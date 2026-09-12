"""
Adversarial Stress Test Suite for Milestone 1:
- SafeConsoleSink CP1252 & Unicode fallback
- Windows path and directory creation edge cases
- JobTitle / CompanyName filename sanitization edge cases
"""
import io
import os
import re
import sys
import time
import shutil
import tempfile
import pytest
from pathlib import Path

from src.logger import SafeConsoleSink
from src.models import Job
from src.pdf_generator import generate_pdf


# ==============================================================================
# SECTION 1: SafeConsoleSink Stress Testing Under CP1252 Environment
# ==============================================================================

class StrictCP1252Stream:
    """A TextIO stream that strictly rejects any characters outside CP1252."""
    def __init__(self):
        self.raw = io.BytesIO()
        self.encoding = "cp1252"

    def write(self, s: str):
        # Strict encode to cp1252 - will raise UnicodeEncodeError on any non-cp1252 char
        b = s.encode("cp1252", errors="strict")
        self.raw.write(b)
        return len(s)

    def flush(self):
        pass

    def get_decoded(self) -> str:
        return self.raw.getvalue().decode("cp1252", errors="replace")


def test_safe_console_sink_ascii():
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    sink.write("Hello World 123!@#\n")
    assert "Hello World 123!@#" in stream.get_decoded()


def test_safe_console_sink_cp1252_valid_unicode():
    """CP1252 natively supports characters like €, £, ¥, ©, ®, é, ü, ñ."""
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    sink.write("Currency: €50, £20, ¥100 | Accent: résumé, café, señor\n")
    out = stream.get_decoded()
    assert "€50" in out
    assert "résumé" in out


def test_safe_console_sink_unmappable_arrows():
    """Arrow → (\u2192) must be translated to '->' and not crash."""
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    sink.write("Step 1 → Step 2 → Step 3: Done\n")
    out = stream.get_decoded()
    assert "Step 1 -> Step 2 -> Step 3" in out


def test_safe_console_sink_unmappable_rupee():
    """Rupee symbol ₹ (\u20b9) must be translated to 'Rs. ' and not crash."""
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    sink.write("Salary: ₹50,000 to ₹1,00,000 per month\n")
    out = stream.get_decoded()
    assert "Rs. 50,000" in out
    assert "Rs. 1,00,000" in out


def test_safe_console_sink_emojis_across_pipeline():
    """Pipeline uses emojis (🚀, ✅, ❌, 🛡️, 🎉, ⚠️, 🧠, 📋, 💡, 🧪). They must not crash CP1252."""
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    emojis_msg = "🚀 Pipeline: ✅ Passed, ❌ Failed, 🛡️ Dry Run, 🎉 Done, ⚠️ Warning, 🧠 AI, 🧪 Test\n"
    sink.write(emojis_msg)
    out = stream.get_decoded()
    # Emojis are outside cp1252, so they should be replaced by '?' rather than raising UnicodeEncodeError
    assert "Pipeline:" in out
    assert "Passed" in out
    assert "Failed" in out


def test_safe_console_sink_asian_and_indic_scripts():
    """Verify non-Latin scripts (Hindi, Chinese, Japanese, Arabic) don't crash."""
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    msg = "Hindi: नमस्ते | Chinese: 自动化测试 | Japanese: テスト | Arabic: اختبار\n"
    sink.write(msg)
    out = stream.get_decoded()
    assert "Hindi:" in out
    assert "Chinese:" in out


def test_safe_console_sink_large_mixed_payload():
    """Stress test with 100KB message containing rapid interleaving of emojis, arrows, rupees, ascii."""
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    chunk = "Job ₹100k → Status ✅ | 🚀 " * 50
    large_payload = (chunk + "\n") * 100  # ~250 KB
    sink.write(large_payload)
    out = stream.get_decoded()
    assert len(out) > 50000
    assert "Job Rs. 100k -> Status" in out


def test_safe_console_sink_missing_encoding_attribute():
    """Stream without an encoding attribute should default to utf-8 gracefully."""
    class NoEncodingStream:
        def __init__(self):
            self.buf = []
        def write(self, s):
            self.buf.append(s)
        def flush(self):
            pass

    stream = NoEncodingStream()
    sink = SafeConsoleSink(stream)
    sink.write("Normal message\n")
    assert "".join(stream.buf) == "Normal message\n"


def test_safe_console_sink_with_loguru_integration():
    """Test actual loguru logger with SafeConsoleSink under strict CP1252 stream."""
    from loguru import logger
    stream = StrictCP1252Stream()
    sink = SafeConsoleSink(stream)
    handler_id = logger.add(sink, format="{message}")
    try:
        logger.info("Test arrow: a → b | Rupee: ₹250 | Emoji: 🚀")
        out = stream.get_decoded()
        assert "a -> b" in out
        assert "Rs. 250" in out
    finally:
        logger.remove(handler_id)


# ==============================================================================
# SECTION 2: Windows Path & Directory Creation Stress Testing
# ==============================================================================

def test_windows_directory_creation_timestamp_formats(tmp_path):
    """Test various timestamp formats in directory creation."""
    formats = [
        "06sep-14-22",                  # standard Worker M1 format
        "2026-09-06_14-22-30",          # ISO-like with underscores and hyphens
        "06-Sep-2026",                  # Standard date
        "run_20260906_142200",          # Underscore delimited
        "test/06sep-14-22",             # Subdirectory nested
        "main pipeline/06sep-14-22",    # Directory with spaces
        "batch_#1_(test)_[v2.0]",       # Special valid symbols #, (), [], {}
    ]
    for fmt in formats:
        target = tmp_path / fmt
        target.mkdir(parents=True, exist_ok=True)
        assert target.is_dir(), f"Failed to create directory with format: {fmt}"
        # Verify file creation inside
        test_file = target / "test.txt"
        test_file.write_text("ok", encoding="utf-8")
        assert test_file.read_text(encoding="utf-8") == "ok"


def test_windows_directory_creation_unicode_characters(tmp_path):
    """Test directory creation with Unicode / International characters on Windows NTFS."""
    unicode_dirs = [
        "test_тест_russian",
        "test_测试_chinese",
        "test_テスト_japanese",
        "test_बेंगलुरु_hindi",
        "test_café_accented",
    ]
    for udir in unicode_dirs:
        target = tmp_path / udir
        target.mkdir(parents=True, exist_ok=True)
        assert target.is_dir(), f"Failed to create unicode directory: {udir}"
        test_file = target / "data.json"
        test_file.write_text('{"status": "ok"}', encoding="utf-8")
        assert test_file.exists()


def test_windows_directory_creation_path_length_stress(tmp_path):
    """Stress test deep nested paths on Windows."""
    deep_path = tmp_path
    for i in range(10):
        deep_path = deep_path / f"nested_level_{i}"
    deep_path.mkdir(parents=True, exist_ok=True)
    assert deep_path.is_dir()
    test_file = deep_path / "deep_file.txt"
    test_file.write_text("deep", encoding="utf-8")
    assert test_file.read_text(encoding="utf-8") == "deep"


def test_windows_invalid_colon_character_behavior(tmp_path):
    """Verify that colons ':' in directory paths fail on Windows (confirming Worker M1's bugfix)."""
    invalid_path_with_colon = tmp_path / "06sep-14:22"
    with pytest.raises(OSError):
        invalid_path_with_colon.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# SECTION 3: Filename Sanitization Adversarial Stress Testing
# ==============================================================================

def sanitize_filename(title: str, company: str) -> str:
    """Extract of filename sanitization used in src/pdf_generator.py."""
    safe_title = "".join([c if c.isalnum() else "_" for c in title]).strip("_")
    safe_company = "".join([c if c.isalnum() else "_" for c in company]).strip("_")
    safe_title = re.sub(r'_+', '_', safe_title)
    safe_company = re.sub(r'_+', '_', safe_company)
    return f"{safe_title}_{safe_company}.pdf"


def test_sanitize_filename_all_forbidden_chars():
    """All 9 Windows forbidden characters in title and company."""
    title = 'QA: <Lead> "Architect" *Pune* / SDET \\ Test | Level? 1'
    company = 'Google: Global / Cloud \\ UK *Ltd* <LLC> "Pvt" | Corp?'
    fname = sanitize_filename(title, company)
    forbidden = [':', '*', '?', '"', '<', '>', '|', '/', '\\']
    for ch in forbidden:
        assert ch not in fname
    assert fname.endswith(".pdf")


def test_sanitize_filename_all_punctuation():
    """When title and company are 100% punctuation / special characters."""
    title = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    company = "~~~```***+++///\\\\\\:::"
    fname = sanitize_filename(title, company)
    # Both become empty string, result is '_.pdf'
    assert fname == "_.pdf"
    for ch in [':', '*', '?', '"', '<', '>', '|', '/', '\\']:
        assert ch not in fname


def test_sanitize_filename_unicode_alphanumeric():
    """Unicode alphanumeric characters (café, 日本語, etc.) in titles."""
    title = "Développeur QA 日本語"
    company = "Société Générale"
    fname = sanitize_filename(title, company)
    assert fname.endswith(".pdf")
    # c.isalnum() includes unicode letters
    assert "Développeur" in fname or "Société" in fname


def test_sanitize_filename_emojis():
    """Emojis in job title and company name."""
    title = "🚀 Senior QA Automation Engineer 🤖"
    company = "🏢 Tech Innovations 🔥"
    fname = sanitize_filename(title, company)
    assert fname.endswith(".pdf")
    for ch in [':', '*', '?', '"', '<', '>', '|', '/', '\\']:
        assert ch not in fname
    # Emojis are not isalnum(), so they become underscores and are stripped
    assert "Senior_QA_Automation_Engineer" in fname
    assert "Tech_Innovations" in fname


def test_sanitize_filename_long_strings():
    """Very long job titles (e.g. 200+ chars from poorly scraped postings)."""
    long_title = "Senior Principal Lead Senior Lead QA Quality Assurance Automation Engineer " * 4
    long_company = "International Business Machines Global Delivery Services Private Limited"
    fname = sanitize_filename(long_title, long_company)
    assert fname.endswith(".pdf")
    assert len(fname) > 100
