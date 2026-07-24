"""
Store Location Manager
Provides utilities for finding nearest stores based on customer location using distance calculation
"""

import math
import logging
from decimal import Decimal
from django.db.models import F, FloatField, Value
from django.db.models.functions import Sqrt, Power
from django.core.cache import cache
from .models import Store

logger = logging.getLogger(__name__)


class StoreLocationManager:
    """Utility class for store location operations"""
    
    EARTH_RADIUS_KM = 6371  # Earth's radius in kilometers
    
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculate distance between two GPS coordinates using Haversine formula
        
        Args:
            lat1, lon1: Customer coordinates (latitude, longitude)
            lat2, lon2: Store coordinates (latitude, longitude)
        
        Returns:
            float: Distance in kilometers
        """
        # Convert degrees to radians
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))
        
        # Differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        distance_km = StoreLocationManager.EARTH_RADIUS_KM * c
        
        return round(distance_km, 2)
    
    @staticmethod
    def find_nearest_store(latitude, longitude):
        """
        Find the nearest active store to given coordinates.
        Results are cached in Django cache for 10 minutes to avoid repeated DB queries.
        
        Args:
            latitude (float): Customer latitude
            longitude (float): Customer longitude
        
        Returns:
            dict or None: Store details with distance, or None if no stores found
        """
        # Round to 3 decimal places (~110m precision) for a stable cache key
        try:
            lat_r = round(float(latitude), 3)
            lon_r = round(float(longitude), 3)
        except (TypeError, ValueError):
            lat_r, lon_r = latitude, longitude

        cache_key = f"nearest_store_{lat_r}_{lon_r}"

        # 1. Check Django cache first
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"[STORE_CACHE] Cache hit for nearest store at ({lat_r}, {lon_r})")
            # cached stores the serialisable result dict (no ORM object)
            # Re-attach a live Store object so callers can access store fields
            try:
                cached['store'] = Store.objects.get(pk=cached['store_id'])
            except Store.DoesNotExist:
                pass
            return cached

        # 2. Cache miss — query DB
        active_stores = list(Store.objects.filter(is_active=True))

        if not active_stores:
            return None

        nearest_store = None
        min_distance = float('inf')

        for store in active_stores:
            distance = StoreLocationManager.haversine_distance(
                latitude, longitude,
                store.latitude, store.longitude
            )

            if distance < min_distance:
                min_distance = distance
                nearest_store = store

        if nearest_store:
            result = {
                'store':      nearest_store,
                'distance':   min_distance,
                'store_id':   nearest_store.id,
                'store_name': nearest_store.name,
                'c2_code':    nearest_store.c2_code,
                'erp_store_id': nearest_store.store_id,
                'address':    nearest_store.address,
                'phone':      nearest_store.phone,
            }
            # Cache a serialisable copy (no ORM object) for 10 minutes
            serialisable = {k: v for k, v in result.items() if k != 'store'}
            cache.set(cache_key, serialisable, timeout=600)
            logger.debug(f"[STORE_CACHE] Cached nearest store ({nearest_store.name}) for ({lat_r}, {lon_r})")
            return result

        return None
    
    @staticmethod
    def find_nearby_stores(latitude, longitude, radius_km=10):
        """
        Find all active stores within specified radius from coordinates
        
        Args:
            latitude (float): Customer latitude
            longitude (float): Customer longitude
            radius_km (int): Search radius in kilometers (default: 10 km)
        
        Returns:
            list: List of stores with distances, sorted by distance
        """
        active_stores = Store.objects.filter(is_active=True)
        nearby = []
        

        for store in active_stores:
            distance = StoreLocationManager.haversine_distance(
                latitude, longitude,
                store.latitude, store.longitude
            )
            
            if distance <= radius_km:
                nearby.append({
                    'store': store,
                    'distance': distance,
                    'store_id': store.id,
                    'store_name': store.name,
                    'c2_code': store.c2_code,
                    'erp_store_id': store.store_id,
                    'city': store.city,
                    'address': store.address,
                    'phone': store.phone,
                })
        
        # Sort by distance (nearest first)
        nearby.sort(key=lambda x: x['distance'])
        return nearby
    
    @staticmethod
    def find_store_by_pincode(pincode):
        """
        Find the nearest active store to a given pincode
        (Useful when you have address/pincode but no GPS coordinates)
        
        Args:
            pincode (str): Customer pincode
        
        Returns:
            dict or None: Nearest store details with distance
        """
        # Find all stores with exact pincode match
        exact_match = Store.objects.filter(pincode=pincode, is_active=True).first()
        if exact_match:
            return {
                'store': exact_match,
                'distance': 0,
                'store_id': exact_match.id,
                'store_name': exact_match.name,
                'c2_code': exact_match.c2_code,
                'erp_store_id': exact_match.store_id,
                'address': exact_match.address,
                'phone': exact_match.phone,
                'match_type': 'exact'
            }
        
        # If no exact match, find nearest store (use store coordinates)
        all_stores = Store.objects.filter(is_active=True)
        if not all_stores.exists():
            return None
        
        # For now, return the first store (in production, use geocoding to convert pincode to lat/lon)
        store = all_stores.first()
        return {
            'store': store,
            'distance': None,
            'store_id': store.id,
            'store_name': store.name,
            'c2_code': store.c2_code,
            'erp_store_id': store.store_id,
            'address': store.address,
            'phone': store.phone,
            'match_type': 'default'
        }
    
    @staticmethod
    def get_all_stores(active_only=True):
        """
        Get all stores
        
        Args:
            active_only (bool): Return only active stores
        
        Returns:
            QuerySet: Store objects
        """
        if active_only:
            return Store.objects.filter(is_active=True).order_by('name')
        return Store.objects.all().order_by('name')
    
    @staticmethod
    def get_store_by_id(store_id):
        """
        Get store details by store ID
        
        Args:
            store_id (int or str): Store ID
        
        Returns:
            Store or None: Store object
        """
        try:
            return Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return None
    
    @staticmethod
    def get_store_erp_config(store_id):
        """
        Get ERP configuration for a specific store
        
        Args:
            store_id (int or str): Store ID
        
        Returns:
            dict or None: ERP configuration with c2_code, store_id, prod_code, security_key
        """
        store = StoreLocationManager.get_store_by_id(store_id)
        if store:
            return store.get_erp_config()
        return None
