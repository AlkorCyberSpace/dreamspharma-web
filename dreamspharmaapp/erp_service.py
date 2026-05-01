"""
ERP Service — Gets store-specific ERP config from database
Replaces hardcoded settings.ERP_C2_CODE, settings.ERP_STORE_ID etc.
"""
import math
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _calculate_distance_km(lat1, lon1, lat2, lon2):
    """Haversine formula — distance in km"""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [
        float(lat1), float(lon1),
        float(lat2), float(lon2)
    ])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return round(R * 2 * math.asin(math.sqrt(a)), 2)


class ERPService:
    """
    Central service to get ERP config for any store.
    All views should use this instead of settings.ERP_STORE_ID etc.
    """

    @staticmethod
    def get_nearest_store_config(latitude, longitude):
        """
        Find nearest store by GPS and return its ERP config.
        Used by: CreateSalesOrderView, GetItemMasterView, FetchStockView

        Returns:
        {
            'store_db_id': 1,
            'store_name': 'Dream Pharma Main',
            'distance_km': 1.2,
            'erp_config': {
                'c2_code': '03C000',
                'store_id': '001',
                'prod_code': '02',
                'security_key': 'TUVVek1EQXhNalE9',
                'base_url': 'http://localhost:44000'
            }
        }
        """
        from .models import Store

        stores = Store.objects.filter(is_active=True)

        if not stores.exists():
            # Fallback to settings if no stores in DB
            logger.warning("[ERP_SERVICE] No stores in database — using settings fallback")
            return ERPService._get_fallback_config()

        nearest = None
        nearest_distance = float('inf')

        for store in stores:
            distance = _calculate_distance_km(
                latitude, longitude,
                store.latitude, store.longitude
            )
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = store

        if not nearest:
            return ERPService._get_fallback_config()

        logger.info(
            f"[ERP_SERVICE] Nearest store: {nearest.store_name} | "
            f"Distance: {nearest_distance}km | "
            f"Store ID: {nearest.store_id}"
        )

        return {
            'store_db_id': nearest.id,
            'store_name': nearest.store_name,
            'distance_km': nearest_distance,
            'erp_config': {
                'c2_code': nearest.c2_code,
                'store_id': nearest.store_id,
                'prod_code': nearest.prod_code,
                'security_key': nearest.security_key,
                'base_url': settings.ERP_BASE_URL
            }
        }

    @staticmethod
    def get_config_by_store_id(store_id):
        """
        Get ERP config for a specific store_id string (e.g. '001').
        Used when store_id is already known (e.g. from saved order).
        """
        from .models import Store

        try:
            store = Store.objects.get(store_id=store_id, is_active=True)
            return {
                'store_db_id': store.id,
                'store_name': store.store_name,
                'erp_config': {
                    'c2_code': store.c2_code,
                    'store_id': store.store_id,
                    'prod_code': store.prod_code,
                    'security_key': store.security_key,
                    'base_url': settings.ERP_BASE_URL
                }
            }
        except Store.DoesNotExist:
            logger.warning(f"[ERP_SERVICE] Store {store_id} not found — using fallback")
            return ERPService._get_fallback_config()

    @staticmethod
    def _get_fallback_config():
        """
        Fallback to settings.py values.
        Used when no stores in DB or GPS not provided.
        """
        return {
            'store_db_id': None,
            'store_name': 'Default Store',
            'distance_km': 0,
            'erp_config': {
                'c2_code': getattr(settings, 'ERP_C2_CODE', '03C000'),
                'store_id': getattr(settings, 'ERP_STORE_ID', '001'),
                'prod_code': getattr(settings, 'ERP_PROD_CODE', '02'),
                'security_key': getattr(settings, 'ERP_SECURITY_KEY', 'TUVVek1EQXhNalE9'),
                'base_url': settings.ERP_BASE_URL
            }
        }
