"""
Store Views & API Endpoints
Handles store location-based operations and customer store selection
"""

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Store
from .serializers import (
    StoreSerializer, StoreListSerializer, LocationInputSerializer,
    NearestStoreResponseSerializer, NearbyStoresResponseSerializer
)
from .store_manager import StoreLocationManager

# ── Helper: validate user_id without requiring a Bearer token ─────────────────
def _get_user_by_id(user_id):
    """
    Returns the User object for the given user_id, or None if not found.
    Used by endpoints that authenticate via user_id instead of Bearer token.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None






class AdminStoreViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD operations for Stores/Warehouses
    """
    queryset = Store.objects.all().order_by('-is_primary', 'name')
    serializer_class = StoreSerializer
    # Replace IsSuperAdmin with IsAuthenticated and manual check if IsSuperAdmin doesn't exist
    permission_classes = [IsAuthenticated]
    
    def check_permissions(self, request):
        super().check_permissions(request)
        if not request.user.role == 'SUPERADMIN':
            self.permission_denied(request, message="Only SuperAdmins can manage warehouses/stores.")

class StoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Store management
    
    Endpoints:
    - GET /api/stores/ - List all active stores
    - GET /api/stores/{id}/ - Get store details
    """
    queryset = Store.objects.filter(is_active=True)
    serializer_class = StoreSerializer
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StoreListSerializer
        return StoreSerializer
    
    def list(self, request, *args, **kwargs):
        """List all active stores — user_id in URL path for auth (no Bearer token)"""
        user_id = self.kwargs.get('user_id')
        user = _get_user_by_id(user_id)
        if not user:
            return Response(
                {'success': False, 'message': 'Invalid user_id'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        stores = self.get_queryset().order_by('-is_primary', 'name')
        serializer = self.get_serializer(stores, many=True)
        return Response({
            'success': True,
            'count': stores.count(),
            'stores': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Get store details — user_id in URL path for auth (no Bearer token)"""
        user_id = self.kwargs.get('user_id')
        user = _get_user_by_id(user_id)
        if not user:
            return Response(
                {'success': False, 'message': 'Invalid user_id'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        store = self.get_object()
        serializer = self.get_serializer(store)
        return Response({
            'success': True,
            'store': serializer.data
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def find_nearest_store(request):
    user_id = request.user.id
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    """
    Find the nearest store to customer location.
    Authenticated via user_id in URL path (no Bearer token required).

    URL: /api/stores/find-nearest/{user_id}/

    Request body:
    { "latitude": 12.9352, "longitude": 77.6245 }
    or
    { "pincode": "560001" }
    """
    # ── user_id-based auth ──────────────────────────────────────────────────
    user = _get_user_by_id(user_id)
    if not user:
        return Response(
            {'success': False, 'message': 'Invalid user_id'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    # ─────────────────────────────────────────────────────────────────────────
    serializer = LocationInputSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    latitude = validated_data.get('latitude')
    longitude = validated_data.get('longitude')
    pincode = validated_data.get('pincode')
    
    # Find nearest store
    if latitude is not None and longitude is not None:
        # Use GPS coordinates
        store_data = StoreLocationManager.find_nearest_store(latitude, longitude)
    else:
        # Use pincode
        store_data = StoreLocationManager.find_store_by_pincode(pincode)
    
    if not store_data:
        return Response({
            'success': False,
            'message': 'No active stores found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Format response
    response_data = {
        'success': True,
        'store': {
            'store_id': store_data['store_id'],
            'store_name': store_data['store_name'],
            'address': store_data['address'],
            'city': store_data['store'].city,
            'state': store_data['store'].state,
            'pincode': store_data['store'].pincode,
            'phone': store_data['phone'],
            'distance': store_data.get('distance'),
            'c2_code': store_data['c2_code'],
            'erp_store_id': store_data['erp_store_id'],
            'prod_code': store_data['store'].prod_code,
        }
    }
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([AllowAny])
def find_nearby_stores(request):
    user_id = request.user.id
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    """
    Find all stores near customer location within radius.
    Authenticated via user_id in URL path (no Bearer token required).

    URL: /api/stores/find-nearby/{user_id}/

    Request body:
    { "latitude": 12.9352, "longitude": 77.6245, "radius": 10 }
    """
    # ── user_id-based auth ──────────────────────────────────────────────────
    user = _get_user_by_id(user_id)
    if not user:
        return Response(
            {'success': False, 'message': 'Invalid user_id'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    # ─────────────────────────────────────────────────────────────────────────
    serializer = LocationInputSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    latitude = validated_data.get('latitude')
    longitude = validated_data.get('longitude')
    radius = validated_data.get('radius', 10)
    
    if latitude is None or longitude is None:
        return Response({
            'success': False,
            'message': 'Latitude and longitude are required for nearby stores search'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Find nearby stores
    nearby_stores = StoreLocationManager.find_nearby_stores(latitude, longitude, radius)
    
    if not nearby_stores:
        return Response({
            'success': True,
            'message': f'No stores found within {radius} km',
            'count': 0,
            'stores': []
        })
    
    # Format response
    stores_data = [
        {
            'store_id': store['store_id'],
            'store_name': store['store_name'],
            'address': store['address'],
            'city': store['city'],
            'pincode': store['store'].pincode,
            'phone': store['phone'],
            'distance': store['distance'],
            'c2_code': store['c2_code'],
            'erp_store_id': store['erp_store_id'],
        }
        for store in nearby_stores
    ]
    
    return Response({
        'success': True,
        'count': len(stores_data),
        'radius_km': radius,
        'stores': stores_data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_store_details(request, store_id, user_id):
    """
    Get detailed information about a specific store.
    Authenticated via user_id in the URL path (no Bearer token required).

    URL: /api/stores/{store_id}/details/{user_id}/

    Response:
    {
        "success": true,
        "store": {
            "id": 1,
            "name": "DreamsPharma - Bangalore",
            "address": "...",
            "city": "Bangalore",
            "c2_code": "03C000",
            "phone": "...",
            "manager_name": "...",
            ...
        }
    }
    """
    # ── user_id-based auth (no Bearer token needed) ───────────────────────────
    user = _get_user_by_id(user_id)
    if not user:
        return Response(
            {'success': False, 'message': 'Invalid user_id'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    # ─────────────────────────────────────────────────────────────────────────

    store = get_object_or_404(Store, id=store_id, is_active=True)
    serializer = StoreSerializer(store)

    return Response({
        'success': True,
        'store': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_store_erp_config(request, store_id, user_id):
    """
    Get ERP configuration for a specific store.
    Authenticated via user_id in the URL path (no Bearer token required).

    URL: /api/stores/{store_id}/erp-config/{user_id}/

    Response:
    {
        "success": true,
        "erp_config": {
            "c2_code": "03C000",
            "store_id": "001",
            "prod_code": "02",
            "security_key": "..."
        }
    }
    """
    # ── user_id-based auth (no Bearer token needed) ───────────────────────────
    user = _get_user_by_id(user_id)
    if not user:
        return Response(
            {'success': False, 'message': 'Invalid user_id'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    # ─────────────────────────────────────────────────────────────────────────

    store = get_object_or_404(Store, id=store_id, is_active=True)

    return Response({
        'success': True,
        'erp_config': store.get_erp_config(),
        'store_name': store.name
    })
