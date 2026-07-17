import os
import pytest
from cryptography.fernet import Fernet
import json

# Setup mock environment variable for tests before importing the module
os.environ['VAULT_KEY'] = Fernet.generate_key().decode('utf-8')

from src.credentials_vault import get_credential, save_credential, list_platforms, delete_credential, VaultKeyError, _save_vault, _load_vault

def test_save_and_get_credential(tmp_path, monkeypatch):
    test_file = tmp_path / "credentials.enc"
    
    # We must patch the vault file location to not mess with real credentials
    import src.credentials_vault
    monkeypatch.setattr(src.credentials_vault, 'VAULT_FILE', str(test_file))
    
    save_credential("linkedin", {"email": "test@example.com", "password": "password123"})
    
    cred = get_credential("linkedin")
    assert cred is not None
    assert cred["email"] == "test@example.com"
    assert cred["password"] == "password123"

def test_list_and_delete_credential(tmp_path, monkeypatch):
    test_file = tmp_path / "credentials.enc"
    
    import src.credentials_vault
    monkeypatch.setattr(src.credentials_vault, 'VAULT_FILE', str(test_file))
    
    save_credential("indeed", {"email": "test2@example.com"})
    save_credential("workday", {"email": "test3@example.com"})
    
    platforms = list_platforms()
    assert "indeed" in platforms
    assert "workday" in platforms
    
    delete_credential("indeed")
    
    platforms = list_platforms()
    assert "indeed" not in platforms
    assert "workday" in platforms
    assert get_credential("indeed") is None

def test_vault_key_error():
    # Remove VAULT_KEY temporarily
    original_key = os.environ.get('VAULT_KEY')
    del os.environ['VAULT_KEY']
    
    from src.credentials_vault import _get_fernet
    with pytest.raises(VaultKeyError):
        _get_fernet()
        
    # Restore key
    os.environ['VAULT_KEY'] = original_key
