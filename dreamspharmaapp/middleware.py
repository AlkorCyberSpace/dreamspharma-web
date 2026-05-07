"""
Store Context Middleware
Automatically detects store from location header and attaches to request
Makes store context available to all views via request.store_context
"""
import logging
from .store_context import get_store_context, StoreContextError

logger = logging.getLogger(__name__)


class StoreContextMiddleware:
    """
    Middleware to automatically extract and attach store context to requests.
    
    Features:
    - Extracts location from X-Store-Location header or request body/query
    - Detects nearest store using Haversine distance calculation
    - Attaches StoreContext object to request for use in views
    - Logs store detection for debugging
    
    Setup in settings.py:
    ----
    MIDDLEWARE = [
        # ... other middleware ...
        'dreamspharmaapp.middleware.StoreContextMiddleware',
    ]
    
    Usage in Views:
    ----
    def get(self, request):
        if hasattr(request, 'store_context') and request.store_context:
            erp_config = request.store_context.get_erp_config()
            store_name = request.store_context.store_name
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Try to extract store context (not required - some endpoints may not need it)
        try:
            store_ctx = get_store_context(request, required=False)
            request.store_context = store_ctx
            
            if store_ctx:
                logger.debug(
                    f"[MIDDLEWARE] Store context attached: {store_ctx.store_name} "
                    f"(ERP ID: {store_ctx.erp_store_id})"
                )
        except StoreContextError as e:
            logger.warning(f"[MIDDLEWARE] Could not determine store context: {str(e)}")
            request.store_context = None
        except Exception as e:
            logger.error(f"[MIDDLEWARE] Unexpected error: {str(e)}")
            request.store_context = None
        
        response = self.get_response(request)
        return response
