"""
In-memory cache for store settings, admin IDs, and catalog (products & categories).
Permanent in-memory storage for admin IDs, with settings.ADMIN_TELEGRAM_ID as guaranteed admin.
"""
import logging
from typing import Optional, Dict, Any, Set, List
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


# ─── Catalog Cache (Products & Categories) ───────────────────────────────────
_categories_cache: Optional[List[Dict[str, Any]]] = None
_products_cache: Optional[List[Dict[str, Any]]] = None


def get_cached_categories() -> Optional[List[Dict[str, Any]]]:
    return _categories_cache


def set_cached_categories(categories: List[Dict[str, Any]]) -> None:
    global _categories_cache
    _categories_cache = categories


def get_cached_products() -> Optional[List[Dict[str, Any]]]:
    return _products_cache


def set_cached_products(products: List[Dict[str, Any]]) -> None:
    global _products_cache
    _products_cache = products


def invalidate_catalog_cache() -> None:
    """Call whenever admin creates, updates, or deletes product or category."""
    global _categories_cache, _products_cache
    _categories_cache = None
    _products_cache = None
    logger.debug("Catalog cache invalidated.")
