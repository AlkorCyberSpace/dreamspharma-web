from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from dreamspharmaapp.models import KYC
from .serializers import (
    RetailerKYCDetailSerializer, ApproveKYCSerializer, RejectKYCSerializer
)

User = get_user_model()


class SuperAdminGetAllRetailersView(APIView):
    """
    API endpoint for superadmin to get all retailers' KYC plus registration details.
    GET /api/superadmin/retailers/ - Get all retailers' KYC and registration details
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all retailers with their KYC and registration details"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all retailers with KYC submitted
        retailers_kyc = KYC.objects.select_related('user').all().order_by('-submitted_at')
        
        if not retailers_kyc.exists():
            return Response({
                'message': 'No retailers with KYC found',
                'count': 0,
                'results': []
            }, status=status.HTTP_200_OK)
        
        serializer = RetailerKYCDetailSerializer(retailers_kyc, many=True)
        
        return Response({
            'message': 'All retailers KYC and registration details',
            'count': retailers_kyc.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class ApproveKYCView(APIView):
    """
    API endpoint for superadmin to approve KYC.
    POST /api/superadmin/kyc/approve/<user_id>/ - Approve a retailer's KYC
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """Approve KYC for a retailer"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can approve KYC'
            }, status=status.HTTP_403_FORBIDDEN)
        
        data = {'user_id': user_id}
        serializer = ApproveKYCSerializer(data=data)
        
        if serializer.is_valid():
            kyc = serializer.save()
            kyc_serializer = RetailerKYCDetailSerializer(kyc)
            
            return Response({
                'message': 'KYC approved successfully',
                'kyc': kyc_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Failed to approve KYC',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RejectKYCView(APIView):
    """
    API endpoint for superadmin to reject KYC.
    POST /api/superadmin/kyc/reject/<user_id>/ - Reject a retailer's KYC with reason
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """Reject KYC for a retailer"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can reject KYC'
            }, status=status.HTTP_403_FORBIDDEN)
        
        data = {'user_id': user_id, **request.data}
        serializer = RejectKYCSerializer(data=data)
        
        if serializer.is_valid():
            kyc = serializer.save()
            kyc_serializer = RetailerKYCDetailSerializer(kyc)
            
            return Response({
                'message': 'KYC rejected successfully',
                'kyc': kyc_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Failed to reject KYC',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

