import hashlib
import hmac
import json
import urllib.parse
from typing import Any, Dict, Optional
from core.config import settings


def validate_telegram_init_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Validates Telegram WebApp initData using HMAC-SHA256.
    Returns parsed data dictionary including 'user' object if valid, else None.
    """
    if not init_data:
        return None

    # Development / local test bypass when DEBUG is True
    if settings.DEBUG and init_data in ("mock_admin", "mock_user"):
        return {
            "user": {
                "id": 111222333 if init_data == "mock_admin" else 444555666,
                "first_name": "Test Admin" if init_data == "mock_admin" else "Test User",
                "username": "test_admin" if init_data == "mock_admin" else "test_user",
            },
            "auth_date": 9999999999,
        }

    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return None

        # Build data check string: keys sorted in alphabetical order, joined by \n
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

        # Secret key: HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

        # Calculated HMAC: HMAC-SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        # Parse user JSON if present
        if "user" in parsed_data:
            parsed_data["user"] = json.loads(parsed_data["user"])

        return parsed_data
    except Exception:
        return None
