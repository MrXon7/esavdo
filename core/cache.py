"""
In-memory cache for store settings and admin IDs.
Avoids repeated DB round-trips for data that rarely changes.
"""
import asyncio
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ─── Store Settings Cache ───────────────────────────────────────────────────
_store_settings: Optional[Dict[str, Any]] = None
_store_settings_ttl: float = 0.0
STORE_SETTINGS_CACHE_SECONDS = 300  # 5 minutes


def get_cached_store_settings() -> Optional[Dict[str, Any]]:
    if _store_settings and time.monotonic() < _store_settings_ttl:
        return _store_settings
    return None


def set_cached_store_settings(data: Dict[str, Any]) -> None:
    global _store_settings, _store_settings_ttl
    _store_settings = data
    _store_settings_ttl = time.monotonic() + STORE_SETTINGS_CACHE_SECONDS


def invalidate_store_settings_cache() -> None:
    """Call this after admin updates store settings."""
    global _store_settings
    _store_settings = None
    logger.debug("Store settings cache invalidated")


# ─── Admin IDs Cache ─────────────────────────────────────────────────────────
_admin_ids: Optional[set] = None
_admin_ids_ttl: float = 0.0
ADMIN_IDS_CACHE_SECONDS = 120  # 2 minutes


def get_cached_admin_ids() -> Optional[set]:
    if _admin_ids is not None and time.monotonic() < _admin_ids_ttl:
        return _admin_ids
    return None


def set_cached_admin_ids(ids: set) -> None:
    global _admin_ids, _admin_ids_ttl
    _admin_ids = ids
    _admin_ids_ttl = time.monotonic() + ADMIN_IDS_CACHE_SECONDS


def invalidate_admin_ids_cache() -> None:
    global _admin_ids
    _admin_ids = None
