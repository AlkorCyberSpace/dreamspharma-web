"""
Store Context Utility Module
Provides centralized function to extract and manage store context from requests
This implements STEP 1-2 of the retailer workflow: Location detection → Store selection
"""
import json
import logging
from django.conf import settings
from .store_manager import StoreLocationManager
from .erp_service import ERPService
from .models import Store

logger = logging.getLogger(__name__)


class StoreContextError(Exception):
    """Raised when store context cannot be determined"""
    pass


class StoreContext:
    """
    Encapsulates store information and ERP config for a request
    """
    def __init__(self, store, distance_km=None):
        self.store = store
        self.distance_km = distance_km
        self.store_id = store.id  # Database ID
        self.store_name = store.name
        self.erp_store_id = store.store_id  # ERP identifier (e.g., "001")
        self.c2_code = store.c2_code
        self.prod_code = store.prod_code
        self.security_key = store.security_key
        
    def get_erp_config(self):
        """Return ERP config ready for API calls"""
        return {
            'c2_code': self.c2_code,
            'store_id': self.erp_store_id,
            'prod_code': self.prod_code,
            'security_key': self.security_key,
            'base_url': settings.ERP_BASE_URL
        }
    
    def to_dict(self):
        """Convert to dictionary for response/logging"""
        return {
            'store_id': self.store_id,
            'store_name': self.store_name,
            'erp_store_id': self.erp_store_id,
            'c2_code': self.c2_code,
            'distance_km': self.distance_km
        }


def extract_location_from_request(request):
    """
    Extract location (latitude, longitude) from request
    Tries multiple sources in order:
    1. X-Store-Location header (JSON format)
    2. Request body/query params (latitude, longitude)
    
    Args:
        request: Django REST request object
    
    Returns:
        tuple: (latitude, longitude) or (None, None) if not found
    
    Raises:
        StoreContextError: If location data is malformed
    """
    latitude = None
    longitude = None
    
    # ✅ METHOD 1: Try X-Store-Location header
    location_header = request.META.get('HTTP_X_STORE_LOCATION')
    if location_header:
        try:
            location_data = json.loads(location_header)
            latitude = location_data.get('latitude')
            longitude = location_data.get('longitude')
            logger.debug(f"[LOCATION] Extracted from header: lat={latitude}, lon={longitude}")
            return latitude, longitude
        except (json.JSONDecodeError, TypeError) as e:
            raise StoreContextError(f"Invalid X-Store-Location header format: {str(e)}")
    
    # ✅ METHOD 2: Try request body (POST)
    if request.method == 'POST' and hasattr(request, 'data'):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        if latitude and longitude:
            logger.debug(f"[LOCATION] Extracted from body: lat={latitude}, lon={longitude}")
            return latitude, longitude
    
    # ✅ METHOD 3: Try query parameters (GET)
    latitude = request.query_params.get('latitude')
    longitude = request.query_params.get('longitude')
    if latitude and longitude:
        logger.debug(f"[LOCATION] Extracted from query: lat={latitude}, lon={longitude}")
        return latitude, longitude
    
    logger.debug("[LOCATION] No location data found in request")
    return None, None


def get_store_context_from_location(latitude, longitude):
    """
    Find nearest store for given location
    
    Args:
        latitude (float): Customer latitude
        longitude (float): Customer longitude
    
    Returns:
        StoreContext: Store context object with ERP config
    
    Raises:
        StoreContextError: If no active stores found
    """
    if not latitude or not longitude:
        raise StoreContextError("Latitude and longitude are required")
    
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (ValueError, TypeError):
        raise StoreContextError("Invalid latitude/longitude format")
    
    # Validate GPS coordinates
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise StoreContextError("Invalid GPS coordinates")
    
    # Find nearest store
    store_info = StoreLocationManager.find_nearest_store(latitude, longitude)
    
    if not store_info:
        raise StoreContextError("No active stores found in database")
    
    store = store_info['store']
    distance_km = store_info['distance']
    
    logger.info(
        f"[STORE_DETECTION] Found nearest store: {store.name} | "
        f"ERP ID: {store.store_id} | "
        f"Distance: {distance_km}km"
    )
    
    return StoreContext(store, distance_km)


def get_store_context_from_store_id(store_db_id):
    """
    Get store context for a specific store DB ID
    
    Args:
        store_db_id (int): Store database ID
    
    Returns:
        StoreContext: Store context object
    
    Raises:
        StoreContextError: If store not found or inactive
    """
    try:
        store = Store.objects.get(id=store_db_id, is_active=True)
        logger.info(f"[STORE_DETECTION] Got store by ID: {store.name}")
        return StoreContext(store)
    except Store.DoesNotExist:
        raise StoreContextError(f"Store ID {store_db_id} not found or inactive")


def get_store_context(request, required=True):
    """
    PRIMARY FUNCTION: Extract store context from request
    
    This is the main entry point for all views that need store context.
    Implements the workflow STEP 1-2: Extract location → Find nearest store → Return context
    
    Args:
        request: Django REST request object
        required (bool): If True, raises error when location not provided.
                        If False, returns None when location not found.
    
    Returns:
        StoreContext: Store context object with store info and ERP config
        None: If required=False and location not found
    
    Raises:
        StoreContextError: If location is invalid or no stores found (when required=True)
    
    Usage in Views:
    -----
    from .store_context import get_store_context, StoreContextError
    
    class MyView(APIView):
        def get(self, request):
            try:
                # Get store context from request location
                store_ctx = get_store_context(request)
                
                # Use store's ERP config
                erp_config = store_ctx.get_erp_config()
                
                # Make ERP API call
                api_key = get_erp_token_for_store_config(erp_config)
                
                # Pass store_id_val to ERP
                store_id_val = store_ctx.erp_store_id
                
            except StoreContextError as e:
                return Response({
                    'code': '400',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
    """
    
    try:
        # Extract location from request
        latitude, longitude = extract_location_from_request(request)
        
        # If no location and not required, return None
        if (not latitude or not longitude) and not required:
            logger.debug("[STORE_CONTEXT] No location provided (not required)")
            return None
        
        # If no location but required, raise error
        if not latitude or not longitude:
            raise StoreContextError(
                "Location required. Please provide coordinates via:\n"
                "1. Header: X-Store-Location: {\"latitude\": 12.34, \"longitude\": 56.78}\n"
                "2. Body/Query: latitude=12.34&longitude=56.78"
            )
        
        # Find nearest store for location
        store_ctx = get_store_context_from_location(latitude, longitude)
        
        logger.info(f"[STORE_CONTEXT] ✓ Store context ready: {store_ctx.to_dict()}")
        return store_ctx
        
    except StoreContextError:
        raise
    except Exception as e:
        logger.error(f"[STORE_CONTEXT] Unexpected error: {str(e)}")
        raise StoreContextError(f"Failed to determine store context: {str(e)}")


# Helper functions for common patterns
def get_store_erp_config(request, required=True):
    """
    Shortcut: Get just the ERP config from request location
    (skips StoreContext object, useful for simple endpoints)
    """
    store_ctx = get_store_context(request, required=required)
    return store_ctx.get_erp_config() if store_ctx else None


def get_store_erp_ids(request, required=True):
    """
    Shortcut: Get just the store ERP identifiers (store_id and c2_code)
    (useful for ERP API calls)
    """
    store_ctx = get_store_context(request, required=required)
    if store_ctx:
        return {
            'store_id': store_ctx.erp_store_id,
            'c2_code': store_ctx.c2_code
        }
    return None
