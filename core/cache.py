"""
In-memory cache for store settings and admin IDs.
Permanent in-memory storage for admin IDs, with settings.ADMIN_TELEGRAM_ID as guaranteed admin.
"""
import logging
from typing import Optional, Dict, Any, Set
from core.config import settings

logger = logging.getLogger(__name__)

# ─── Store Settings Cache ───────────────────────────────────────────────────
_store_settings: Optional[Dict[str, Any]] = None


def get_cached_store_settings() -> Optional[Dict[str, Any]]:
    return _store_settings


def set_cached_store_settings(data: Dict[str, Any]) -> None:
    global _store_settings
    _store_settings = data


def invalidate_store_settings_cache() -> None:
    global _store_settings
    _store_settings = None


# ─── Admin IDs Cache (Permanent in-memory set, never expires) ───────────────
_admin_ids: Set[int] = set()


def get_cached_admin_ids() -> Set[int]:
    """
    Returns all cached admin telegram IDs.
    Guarantees settings.ADMIN_TELEGRAM_ID is always included.
    """
    result = set(_admin_ids)
    if settings.ADMIN_TELEGRAM_ID and settings.ADMIN_TELEGRAM_ID > 0:
        result.add(int(settings.ADMIN_TELEGRAM_ID))
    return result


def set_cached_admin_ids(ids: Set[int]) -> None:
    """
    Updates in-memory admin IDs set.
    """
    global _admin_ids
    _admin_ids = set(ids)
    if settings.ADMIN_TELEGRAM_ID and settings.ADMIN_TELEGRAM_ID > 0:
        _admin_ids.add(int(settings.ADMIN_TELEGRAM_ID))


def is_admin_id(telegram_id: int) -> bool:
    """
    Instant check whether a given telegram_id belongs to an admin.
    """
    if not telegram_id:
        return False
    if settings.ADMIN_TELEGRAM_ID and int(telegram_id) == int(settings.ADMIN_TELEGRAM_ID):
        return True
    return int(telegram_id) in _admin_ids
