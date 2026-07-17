import pytest
import asyncio
from unittest.mock import patch, MagicMock

from src.gmail_otp import extract_otp_from_body, extract_body

def test_extract_otp_from_body():
    assert extract_otp_from_body("Your verification code is 123456.") == "123456"
    assert extract_otp_from_body("OTP: 9876") == "9876"
    assert extract_otp_from_body("Please use 555555 to verify.") == "555555"
    assert extract_otp_from_body("No code here") is None

def test_extract_body():
    import base64
    
    encoded = base64.urlsafe_b64encode(b"Hello OTP: 123456").decode('utf-8')
    message = {
        'payload': {
            'mimeType': 'text/plain',
            'body': {
                'data': encoded
            }
        }
    }
    body = extract_body(message)
    assert "123456" in body

@pytest.mark.asyncio
async def test_fetch_otp_timeout():
    with patch('src.gmail_otp.get_gmail_service') as mock_service:
        mock_service.return_value.users.return_value.messages.return_value.list.return_value.execute.return_value = {}
        
        # We test with a short timeout to not hang the test
        otp = await fetch_otp("test@example.com", "verify", timeout=1)
        assert otp is None

# Import fetch_otp here to avoid circular dependencies if it happens
from src.gmail_otp import fetch_otp
