from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, logout
from django.shortcuts import get_object_or_404
from django.utils import timezone
from dreamspharmaapp.models import KYC, SalesOrder
from .serializers import (
    RetailerKYCDetailSerializer, ApproveKYCSerializer, RejectKYCSerializer, DashboardStatisticsSerializer, ChangePasswordSerializer, SuperAdminProfileSerializer, SuperAdminProfileImageSerializer
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


class DashboardStatisticsView(APIView):
    """
    API endpoint for superadmin to get dashboard statistics.
    GET /api/superadmin/dashboard/statistics/ - Get dashboard statistics
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get dashboard statistics for superadmin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Calculate statistics
        total_retailers = User.objects.filter(role='RETAILER').count()
        pending_kyc = KYC.objects.filter(status='PENDING').count()
        total_orders = SalesOrder.objects.count()
        
        # Prepare data
        stats_data = {
            'total_retailers': total_retailers,
            'pending_kyc': pending_kyc,
            'total_orders': total_orders,
        }
        
        serializer = DashboardStatisticsSerializer(stats_data)
        
        return Response({
            'message': 'Dashboard statistics fetched successfully',
            'statistics': serializer.data
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    API endpoint for super admin to change password.
    POST /api/superadmin/change-password/ - Change password for logged-in super admin
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Change password for super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
                return Response({
                    'message': 'Password changed successfully'
                }, status=status.HTTP_200_OK)
            except serializers.ValidationError as e:
                return Response({
                    'error': str(e.detail[0])
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'error': 'Password change failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class GetSuperAdminProfileView(APIView):
    """
    API endpoint for super admin to get profile information.
    GET /api/superadmin/profile/ - Get super admin profile info (username, email, phone, image)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get profile information for super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SuperAdminProfileSerializer(request.user)
        
        return Response({
            'message': 'Profile information fetched successfully',
            'profile': serializer.data
        }, status=status.HTTP_200_OK)


class UploadSuperAdminProfileImageView(APIView):
    """
    API endpoint for super admin to upload profile image.
    POST /api/superadmin/profile/image/ - Upload profile image
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Upload profile image for super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SuperAdminProfileImageSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile image uploaded successfully',
                'profile_image': serializer.data['profile_image']
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Image upload failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DeleteSuperAdminProfileImageView(APIView):
    """
    API endpoint for super admin to delete profile image.
    DELETE /api/superadmin/profile/image/ - Delete profile image
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """Delete profile image for super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user has a profile image
        if not request.user.profile_image:
            return Response({
                'error': 'No profile image found to delete'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Delete the image file
        if request.user.profile_image.storage.exists(request.user.profile_image.name):
            request.user.profile_image.storage.delete(request.user.profile_image.name)
        
        # Clear the profile_image field
        request.user.profile_image = None
        request.user.save()
        
        return Response({
            'message': 'Profile image deleted successfully'
        }, status=status.HTTP_200_OK)


class SuperAdminLogoutView(APIView):
    """
    API endpoint for super admin to logout.
    POST /api/superadmin/logout/ - Logout super admin
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Logout super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        logout(request)
        
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_205_RESET_CONTENT)
