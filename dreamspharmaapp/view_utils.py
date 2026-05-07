"""
View Utilities and Decorators
Provides decorators for views to enforce store context and handle location errors
"""
import logging
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .store_context import get_store_context, StoreContextError

logger = logging.getLogger(__name__)


def require_store_context(view_func):
    """
    Decorator: Enforce that request has valid store context
    
    Automatically extracts store context from request location.
    Returns 400 error if location not provided or invalid.
    Makes store context available as first argument to view method.
    
    Usage:
    -----
    @require_store_context
    def get(self, request, store_context):
        erp_config = store_context.get_erp_config()
        return Response({'store_id': store_context.erp_store_id})
    """
    
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        try:
            store_ctx = get_store_context(request, required=True)
            return view_func(self, request, store_ctx, *args, **kwargs)
        
        except StoreContextError as e:
            logger.warning(f"[VIEW] Store context error: {str(e)}")
            return Response({
                'code': '400',
                'type': 'LocationRequired',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"[VIEW] Unexpected error in store context: {str(e)}")
            return Response({
                'code': '500',
                'type': 'StoreContextError',
                'message': 'Failed to determine store context'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return wrapper


def optional_store_context(view_func):
    """
    Decorator: Optional store context (view works with or without it)
    
    Attempts to extract store context but doesn't fail if missing.
    Makes store context available as first argument (may be None).
    
    Usage:
    -----
    @optional_store_context
    def get(self, request, store_context):
        if store_context:
            # Use store-specific logic
            erp_config = store_context.get_erp_config()
        else:
            # Use fallback logic
            pass
    """
    
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        try:
            store_ctx = get_store_context(request, required=False)
            return view_func(self, request, store_ctx, *args, **kwargs)
        
        except StoreContextError as e:
            logger.warning(f"[VIEW] Store context error (optional): {str(e)}")
            return view_func(self, request, None, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"[VIEW] Unexpected error in optional store context: {str(e)}")
            return view_func(self, request, None, *args, **kwargs)
    
    return wrapper


def enforce_store_context_from_middleware(view_func):
    """
    Decorator: Use store context from middleware (already attached to request)
    
    Assumes middleware has already populated request.store_context.
    Useful for endpoints that need store but don't want to make it a hard requirement.
    
    Usage:
    -----
    @enforce_store_context_from_middleware
    def post(self, request):
        if hasattr(request, 'store_context') and request.store_context:
            erp_config = request.store_context.get_erp_config()
    """
    
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        # Check if middleware already set store_context
        store_ctx = getattr(request, 'store_context', None)
        
        if not store_ctx:
            logger.warning("[VIEW] No store context from middleware")
        
        return view_func(self, request, *args, **kwargs)
    
    return wrapper


# Error response helper functions

def error_location_required():
    """Generate standard error response for missing location"""
    return Response({
        'code': '400',
        'type': 'LocationRequired',
        'message': 'Location required. Provide coordinates via X-Store-Location header or latitude/longitude parameters'
    }, status=status.HTTP_400_BAD_REQUEST)


def error_store_not_found():
    """Generate standard error response for store not found"""
    return Response({
        'code': '404',
        'type': 'StoreNotFound',
        'message': 'No active stores found near your location'
    }, status=status.HTTP_404_NOT_FOUND)


def error_invalid_location():
    """Generate standard error response for invalid location data"""
    return Response({
        'code': '400',
        'type': 'InvalidLocation',
        'message': 'Invalid location data format'
    }, status=status.HTTP_400_BAD_REQUEST)
