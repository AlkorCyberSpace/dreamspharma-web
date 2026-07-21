"""
ERP Redis Cache Service
=======================
Centralises all ERP data caching using Redis via django-redis.

Cache key structure (all prefixed by settings.KEY_PREFIX = 'dreamspharma'):
  erp:master:{store_id}:{input_date_slug}   → full master-data list (1 hr TTL)
  erp:stock:{store_id}:{codes_hash}          → stock map dict     (5 min TTL)

Usage in views:
    from .erp_redis_cache import ERPRedisCache

    # Master data
    items = ERPRedisCache.get_master_data(store_id, input_date_time)
    if items is None:
        items = <call ERP API>
        ERPRedisCache.set_master_data(store_id, input_date_time, items)

    # Stock map
    stock_map = ERPRedisCache.get_stock_map(store_id, item_codes)
    if stock_map is None:
        stock_map = <call ERP stock API>
        ERPRedisCache.set_stock_map(store_id, item_codes, stock_map)

    # Invalidate all ERP cache for a store (e.g. after product update)
    ERPRedisCache.invalidate_store(store_id)
"""

import hashlib
import logging

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# ── TTL constants (configurable via settings or env vars) ─────────────────────
MASTER_TTL = getattr(settings, 'ERP_MASTER_DATA_CACHE_TTL', 3600)  # 1 hour
STOCK_TTL  = getattr(settings, 'ERP_STOCK_CACHE_TTL',       300)   # 5 minutes
TOKEN_TTL  = getattr(settings, 'ERP_TOKEN_CACHE_TTL',       86400) # 24 hours


def _master_key(store_id: str, input_date_time: str) -> str:
    """Redis key for full ERP master-data list for a store + date window."""
    slug = input_date_time.replace(' ', '_').replace(':', '-')
    return f"erp:master:{store_id}:{slug}"


def _stock_key(store_id: str, item_codes: list) -> str:
    """
    Redis key for stock map. Uses a hash of sorted item codes so that any
    combination of item codes gets its own stable cache slot.
    """
    sorted_codes = sorted(str(c) for c in item_codes)
    codes_hash = hashlib.md5(','.join(sorted_codes).encode()).hexdigest()[:12]
    return f"erp:stock:{store_id}:{codes_hash}"


def _store_pattern(store_id: str) -> str:
    """Pattern to match ALL cache keys for a given store (used for invalidation)."""
    return f"erp:*:{store_id}:*"


class ERPRedisCache:
    """
    Static helper class for all ERP Redis cache operations.
    Uses Django's cache framework (backed by django-redis) so it degrades
    gracefully when Redis is unavailable (IGNORE_EXCEPTIONS = True in settings).
    """

    # ── Master data ───────────────────────────────────────────────────────────

    @staticmethod
    def get_master_data(store_id: str, input_date_time: str):
        """
        Retrieve cached ERP master-data list from Redis.

        Returns:
            list[dict] if cache hit, None if cache miss / Redis unavailable.
        """
        key = _master_key(store_id, input_date_time)
        data = cache.get(key)
        if data is not None:
            logger.info(
                f"[ERP_CACHE] [MASTER] CACHE HIT  store={store_id} "
                f"date={input_date_time} items={len(data)}"
            )
        else:
            logger.info(
                f"[ERP_CACHE] [MASTER] CACHE MISS store={store_id} "
                f"date={input_date_time}"
            )
        return data

    @staticmethod
    def set_master_data(store_id: str, input_date_time: str, items: list) -> bool:
        """
        Store ERP master-data list in Redis with MASTER_TTL.

        Returns:
            True if stored, False on failure.
        """
        if not items:
            return False
        key = _master_key(store_id, input_date_time)
        try:
            cache.set(key, items, timeout=MASTER_TTL)
            logger.info(
                f"[ERP_CACHE] [MASTER] STORED    store={store_id} "
                f"date={input_date_time} items={len(items)} ttl={MASTER_TTL}s"
            )
            return True
        except Exception as e:
            logger.error(f"[ERP_CACHE] [MASTER] SET FAILED: {e}")
            return False

    @staticmethod
    def invalidate_master_data(store_id: str, input_date_time: str) -> None:
        """Delete a specific master-data cache entry."""
        key = _master_key(store_id, input_date_time)
        cache.delete(key)
        logger.info(
            f"[ERP_CACHE] [MASTER] DELETED store={store_id} date={input_date_time}"
        )

    # ── Stock map ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_stock_map(store_id: str, item_codes: list):
        """
        Retrieve cached stock map from Redis.

        Returns:
            dict {item_code: pack_qty} if hit, None on miss / unavailable.
        """
        if not item_codes:
            return {}
        key = _stock_key(store_id, item_codes)
        data = cache.get(key)
        if data is not None:
            logger.info(
                f"[ERP_CACHE] [STOCK]  CACHE HIT  store={store_id} "
                f"codes={len(item_codes)}"
            )
        else:
            logger.info(
                f"[ERP_CACHE] [STOCK]  CACHE MISS store={store_id} "
                f"codes={len(item_codes)}"
            )
        return data

    @staticmethod
    def set_stock_map(store_id: str, item_codes: list, stock_map: dict) -> bool:
        """
        Store stock map in Redis with STOCK_TTL (default 5 min).

        Returns:
            True if stored, False on failure.
        """
        if not item_codes:
            return False
        key = _stock_key(store_id, item_codes)
        try:
            cache.set(key, stock_map, timeout=STOCK_TTL)
            logger.info(
                f"[ERP_CACHE] [STOCK]  STORED    store={store_id} "
                f"codes={len(item_codes)} entries={len(stock_map)} ttl={STOCK_TTL}s"
            )
            return True
        except Exception as e:
            logger.error(f"[ERP_CACHE] [STOCK]  SET FAILED: {e}")
            return False

    # ── Invalidation ──────────────────────────────────────────────────────────

    @staticmethod
    def invalidate_store(store_id: str) -> int:
        """
        Delete ALL ERP cache entries for a store (master data + all stock maps).
        Uses django-redis's `delete_pattern()` which maps to Redis SCAN + DEL.

        Returns:
            Number of keys deleted (0 if Redis unavailable or no keys found).
        """
        try:
            # django-redis exposes delete_pattern() on the raw client
            from django_redis import get_redis_connection
            con = get_redis_connection("default")

            key_prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
            # Full pattern: dreamspharma:1:erp:*:{store_id}:*
            # (django-redis appends :<version>: between prefix and key)
            pattern = f"{key_prefix}:*:erp:*:{store_id}:*"
            keys = list(con.scan_iter(match=pattern, count=100))
            if keys:
                deleted = con.delete(*keys)
            else:
                deleted = 0
            logger.info(
                f"[ERP_CACHE] [INVALIDATE] store={store_id} "
                f"deleted={deleted} keys (pattern={pattern})"
            )
            return deleted
        except Exception as e:
            logger.error(f"[ERP_CACHE] [INVALIDATE] Failed for store={store_id}: {e}")
            return 0

    @staticmethod
    def invalidate_all_erp() -> int:
        """
        Delete ALL ERP cache entries across all stores.
        Use with caution (will cause a cold-cache on next request).
        """
        try:
            from django_redis import get_redis_connection
            con = get_redis_connection("default")

            key_prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
            pattern = f"{key_prefix}:*:erp:*"
            keys = list(con.scan_iter(match=pattern, count=100))
            if keys:
                deleted = con.delete(*keys)
            else:
                deleted = 0
            logger.warning(
                f"[ERP_CACHE] [INVALIDATE_ALL] deleted={deleted} ERP cache keys"
            )
            return deleted
        except Exception as e:
            logger.error(f"[ERP_CACHE] [INVALIDATE_ALL] Failed: {e}")
            return 0

    # ── Diagnostics ───────────────────────────────────────────────────────────

    @staticmethod
    def get_cache_info(store_id: str = None) -> dict:
        """
        Return diagnostic info about current ERP cache entries.
        Used by the admin cache invalidation endpoint.
        """
        info = {
            'backend': str(settings.CACHES['default']['BACKEND']),
            'master_ttl_seconds': MASTER_TTL,
            'stock_ttl_seconds':  STOCK_TTL,
            'token_ttl_seconds':  TOKEN_TTL,
        }
        try:
            from django_redis import get_redis_connection
            con = get_redis_connection("default")

            key_prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
            if store_id:
                pattern = f"{key_prefix}:*:erp:*:{store_id}:*"
            else:
                pattern = f"{key_prefix}:*:erp:*"
            keys = list(con.scan_iter(match=pattern, count=200))
            info['cached_keys_count'] = len(keys)
            info['cached_keys'] = [k.decode() if isinstance(k, bytes) else k for k in keys[:50]]
        except Exception as e:
            info['error'] = str(e)
        return info
