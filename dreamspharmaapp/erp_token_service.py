"""
ERP Token Service - Handles automatic token generation and caching PER STORE
Each store gets its own cached token - no manual generation needed
"""

import logging
import base64
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import APIToken

logger = logging.getLogger(__name__)

# Cache key template for ERP tokens (per store)
def get_erp_token_cache_key(store_id):
    """Generate cache key for a specific store's token"""
    return f'erp_api_token_{store_id}'

def get_erp_token_expiry_cache_key(store_id):
    """Generate cache key for a specific store's token expiry"""
    return f'erp_api_token_expiry_{store_id}'

# Legacy keys for fallback compatibility
ERP_TOKEN_CACHE_KEY = 'erp_api_token'
ERP_TOKEN_EXPIRY_CACHE_KEY = 'erp_api_token_expiry'


def generate_erp_token_for_store(store_config):
    """
    Generate ERP token for a specific store by calling the ERP server.
    
    Args:
        store_config (dict): Dictionary with keys:
            - 'c2_code': ERP company code (e.g., '03C000')
            - 'store_id': Store ID (e.g., '001')
            - 'prod_code': Production code (e.g., '02')
            - 'security_key': ERP security key
            - 'base_url': ERP base URL (e.g., 'http://localhost:44000')
    
    Returns:
        dict: {'token': 'xxxxx', 'store_id': '001'} or None
    """
    try:
        erp_url = f"{store_config['base_url']}/ws_c2_services_generate_token"
        
        payload = {
            "c2Code": store_config['c2_code'],
            "storeId": store_config['store_id'],
            "prodCode": store_config['prod_code'],
            "securityKey": store_config['security_key']
        }
        
        logger.info(
            f"[ERP_TOKEN] [STORE {store_config['store_id']}] "
            f"Generating token for store {store_config['store_id']} ({store_config['c2_code']})"
        )
        
        # 🎯 Official Ecogreen API uses GET with JSON body for token generation
        response = requests.get(erp_url, json=payload, timeout=10)

        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '200' and data.get('apiKey'):
                token = data.get('apiKey')
                logger.info(
                    f"[ERP_TOKEN] [STORE {store_config['store_id']}] [OK] Token generated successfully"
                )
                return {
                    'token': token,
                    'store_id': store_config['store_id'],
                    'c2_code': store_config['c2_code']
                }
            else:
                logger.error(
                    f"[ERP_TOKEN] [STORE {store_config['store_id']}] [FAIL] ERP error: {data.get('message')}"
                )
                return None
        else:
            logger.error(
                f"[ERP_TOKEN] [STORE {store_config['store_id']}] [FAIL] HTTP {response.status_code}"
            )
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"[ERP_TOKEN] [STORE {store_config['store_id']}] [FAIL] Timeout")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"[ERP_TOKEN] [STORE {store_config['store_id']}] [FAIL] Connection failed")
        return None
    except Exception as e:
        logger.error(f"[ERP_TOKEN] [STORE {store_config['store_id']}] [FAIL] Error: {str(e)}")
        return None


def generate_erp_token_from_server():
    """
    [LEGACY] Generate ERP token using settings (single-store fallback).
    New code should use generate_erp_token_for_store() with store config.
    
    Returns: token string or None
    """
    store_config = {
        'c2_code': settings.ERP_C2_CODE,
        'store_id': settings.ERP_STORE_ID,
        'prod_code': settings.ERP_PROD_CODE,
        'security_key': settings.ERP_SECURITY_KEY,
        'base_url': settings.ERP_BASE_URL
    }
    
    result = generate_erp_token_for_store(store_config)
    return result['token'] if result else None


def get_cached_erp_token_for_store(store_config):
    """
    Get ERP token from cache for a specific store. Generate if expired/missing.
    
    Args:
        store_config (dict): Store configuration with c2_code, store_id, etc.
    
    Returns:
        str: API token or None
    """
    store_id = store_config['store_id']
    cache_key = get_erp_token_cache_key(store_id)
    expiry_key = get_erp_token_expiry_cache_key(store_id)
    
    # Try to get from cache first
    cached_token = cache.get(cache_key)
    cached_expiry = cache.get(expiry_key)
    
    if cached_token and cached_expiry:
        # Check if token is still valid (with 1 hour buffer)
        try:
            expiry_time = datetime.fromisoformat(cached_expiry)
            if timezone.now() < (expiry_time - timedelta(hours=1)):
                logger.info(
                    f"[ERP_TOKEN] [STORE {store_id}] [OK] Using cached token "
                    f"(valid until {cached_expiry})"
                )
                return cached_token
        except:
            pass
    
    # Token not in cache or expired - generate new one
    logger.info(f"[ERP_TOKEN] [STORE {store_id}] Token expired/missing - generating new...")
    result = generate_erp_token_for_store(store_config)
    
    if result:
        token = result['token']
        # Cache for 24 hours
        cache_timeout = 24 * 60 * 60
        new_expiry = timezone.now() + timedelta(hours=24)
        
        cache.set(cache_key, token, cache_timeout)
        cache.set(expiry_key, new_expiry.isoformat(), cache_timeout)
        
        logger.info(f"[ERP_TOKEN] [STORE {store_id}] [OK] Cached new token for 24 hours")
        return token
    
    logger.warning(f"[ERP_TOKEN] [STORE {store_id}] [FAIL] Failed to generate new token")
    return None


def get_cached_erp_token():
    """
    [LEGACY] Get ERP token from cache using single-store settings (fallback).
    New code should use get_cached_erp_token_for_store() with store config.
    
    Returns: token string or None
    """
    store_config = {
        'c2_code': settings.ERP_C2_CODE,
        'store_id': settings.ERP_STORE_ID,
        'prod_code': settings.ERP_PROD_CODE,
        'security_key': settings.ERP_SECURITY_KEY,
        'base_url': settings.ERP_BASE_URL
    }
    
    return get_cached_erp_token_for_store(store_config)


def save_token_to_db(store_config, token):
    """
    Save token to database for backup/audit purposes (per store).
    
    Args:
        store_config (dict): Store configuration
        token (str): API token
    """
    try:
        api_token, created = APIToken.objects.get_or_create(
            c2_code=store_config['c2_code'],
            store_id=store_config['store_id'],
            defaults={
                'prod_code': store_config['prod_code'],
                'security_key': store_config['security_key'],
                'api_key': token,
                'is_active': True
            }
        )
        
        if not created:
            # Update existing token
            api_token.api_key = token
            api_token.is_active = True
            api_token.save()
            logger.info(
                f"[ERP_TOKEN] [DB] [STORE {store_config['store_id']}] Updated token record"
            )
        else:
            logger.info(
                f"[ERP_TOKEN] [DB] [STORE {store_config['store_id']}] Created new token record"
            )
            
    except Exception as e:
        logger.error(
            f"[ERP_TOKEN] [DB] [STORE {store_config['store_id']}] Error: {str(e)}"
        )


def refresh_erp_token_for_store(store_config):
    """
    Refresh/regenerate ERP token for a specific store.
    Useful for scheduled background tasks.
    
    Args:
        store_config (dict): Store configuration
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"[ERP_TOKEN] [REFRESH] Starting token refresh for store {store_config['store_id']}...")
    
    result = generate_erp_token_for_store(store_config)
    
    if result:
        token = result['token']
        store_id = store_config['store_id']
        
        # Update cache
        cache_timeout = 24 * 60 * 60
        new_expiry = timezone.now() + timedelta(hours=24)
        
        cache.set(get_erp_token_cache_key(store_id), token, cache_timeout)
        cache.set(get_erp_token_expiry_cache_key(store_id), new_expiry.isoformat(), cache_timeout)
        
        # Save to DB
        save_token_to_db(store_config, token)
        
        logger.info(
            f"[ERP_TOKEN] [REFRESH] [OK] Token refresh successful for store {store_id}"
        )
        return True
    else:
        logger.error(
            f"[ERP_TOKEN] [REFRESH] [FAIL] Token refresh failed for store {store_config['store_id']}"
        )
        return False


def refresh_erp_token():
    """
    [LEGACY] Refresh token using single-store settings (fallback).
    New code should use refresh_erp_token_for_store() with store config.
    
    Returns: True if successful, False otherwise
    """
    store_config = {
        'c2_code': settings.ERP_C2_CODE,
        'store_id': settings.ERP_STORE_ID,
        'prod_code': settings.ERP_PROD_CODE,
        'security_key': settings.ERP_SECURITY_KEY,
        'base_url': settings.ERP_BASE_URL
    }
    
    return refresh_erp_token_for_store(store_config)


def get_erp_token_for_store_config(store_config):
    """
    [MAIN FUNCTION] Get token for a specific store's config.
    This is what views should call for multi-store support.
    
    ✅ STEP 2 IMPLEMENTATION:
    - Generates token PER STORE (separate API call for each store)
    - Caches tokens in backend (per-store cache keys)
    
    ✅ STEP 3 IMPLEMENTATION:
    - Always includes storeId in the store_config
    - Returns token ready to use in ERP requests
    
    Args:
        store_config (dict): Must include:
            - 'c2_code': ERP company code
            - 'store_id': Store ID (e.g., '001', '002')
            - 'prod_code': Production code
            - 'security_key': Security key
            - 'base_url': ERP base URL
    
    Returns:
        str: API token for the store (never None - uses fallback)
    
    Usage in Views:
        from .erp_service import ERPService
        from .erp_token_service import get_erp_token_for_store_config
        
        # Step 1: Get store config based on location
        store_info = ERPService.get_nearest_store_config(latitude, longitude)
        store_config = store_info['erp_config']  # ← Contains store_id!
        
        # Step 2 & 3: Get token for that store + always pass storeId
        api_token = get_erp_token_for_store_config(store_config)
        
        # Step 3: Make ERP request with storeId + apiKey
        erp_params = {
            "c2Code": store_config['c2_code'],
            "storeId": store_config['store_id'],  # ← Store ID passed!
            "prodCode": store_config['prod_code'],
            "securityKey": store_config['security_key'],
            "apiKey": api_token  # ← Generated for this store!
        }
    """
    # Try cache first
    token = get_cached_erp_token_for_store(store_config)
    if token:
        return token
    
    # Fallback: Check database for last known good token
    try:
        api_token_obj = APIToken.objects.filter(
            c2_code=store_config['c2_code'],
            store_id=store_config['store_id'],
            is_active=True
        ).latest('created_at')
        
        if api_token_obj:
            logger.warning(
                f"[ERP_TOKEN] [STORE {store_config['store_id']}] "
                f"Using fallback token from database"
            )
            return api_token_obj.api_key
    except APIToken.DoesNotExist:
        pass
    
    logger.critical(
        f"[ERP_TOKEN] [STORE {store_config['store_id']}] "
        f"[CRITICAL] No valid token available!"
    )
    return None


def get_erp_token_for_request():
    """
    [LEGACY] Get token using single-store settings (fallback).
    New code should use get_erp_token_for_store_config() with store config.
    
    Returns: token string (never None - uses fallback logic)
    """
    store_config = {
        'c2_code': settings.ERP_C2_CODE,
        'store_id': settings.ERP_STORE_ID,
        'prod_code': settings.ERP_PROD_CODE,
        'security_key': settings.ERP_SECURITY_KEY,
        'base_url': settings.ERP_BASE_URL
    }
    
    return get_erp_token_for_store_config(store_config)


# ==================== INITIALIZATION ====================

def initialize_erp_token():
    """
    [INIT] Initialize ERP tokens on app startup.
    Generates initial tokens for all active stores in the database.
    
    Call this in apps.py ready() method:
        class DreamspharmaappConfig(AppConfig):
            def ready(self):
                from .erp_token_service import initialize_erp_token
                initialize_erp_token()
    """
    from django.apps import apps
    
    # Only initialize if Django apps are fully loaded
    if not apps.ready:
        logger.warning(f"[ERP_TOKEN] [INIT] Django apps not ready, deferring initialization...")
        return
    
    logger.info(f"[ERP_TOKEN] [INIT] Initializing multi-store ERP token service...")
    
    try:
        from .models import Store
        
        # Initialize tokens for all active stores
        stores = Store.objects.filter(is_active=True)
        
        if not stores.exists():
            logger.warning(
                f"[ERP_TOKEN] [INIT] No active stores in database. "
                f"Using settings fallback for token generation."
            )
            # Initialize fallback single-store token
            token = get_cached_erp_token()
            if token:
                logger.info(f"[ERP_TOKEN] [INIT] [OK] Fallback token initialized")
            else:
                logger.error(f"[ERP_TOKEN] [INIT] [FAIL] Failed to initialize fallback token")
            return
        
        # Generate tokens for each store
        success_count = 0
        fail_count = 0
        
        for store in stores:
            store_config = {
                'c2_code': store.c2_code,
                'store_id': store.store_id,
                'prod_code': store.prod_code,
                'security_key': store.security_key,
                'base_url': settings.ERP_BASE_URL
            }
            
            token = get_cached_erp_token_for_store(store_config)
            if token:
                success_count += 1
                logger.info(f"[ERP_TOKEN] [INIT] [OK] Store {store.store_id} token ready")
            else:
                fail_count += 1
                logger.error(f"[ERP_TOKEN] [INIT] [FAIL] Failed to initialize token for store {store.store_id}")
        
        logger.info(
            f"[ERP_TOKEN] [INIT] Initialization complete: "
            f"{success_count} stores OK, {fail_count} stores FAIL"
        )
        
    except Exception as e:
        logger.error(f"[ERP_TOKEN] [INIT] Error during initialization: {str(e)}")
