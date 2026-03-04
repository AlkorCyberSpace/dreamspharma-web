from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate, logout
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
import random
import re
import string
import base64
import requests
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

from .models import CustomUser, KYC, OTP, APIToken, ItemMaster, Stock, GLCustomer, SalesOrder, SalesOrderItem, Invoice, InvoiceDetail, Cart, CartItem, Wishlist, WishlistItem, Brand, ProductInfo, Address
from .serializers import (
    CustomUserSerializer, UserRegistrationSerializer, KYCSerializer, 
    KYCSubmitSerializer, SuperAdminLoginSerializer, RetailerLoginSerializer,
    ForgotPasswordSerializer, OTPVerifySerializer, PasswordResetSerializer,
    ChangePasswordSerializer, GenerateTokenRequestSerializer, GenerateTokenResponseSerializer,
    ItemMasterSerializer, FetchStockRequestSerializer, StockItemSerializer,
    CreateSalesOrderRequestSerializer, CreateSalesOrderResponseSerializer,
    CreateGLCustomerRequestSerializer, CreateGLCustomerResponseSerializer,
    OrderStatusResponseSerializer, InvoiceForStatusSerializer,
    CartSerializer, CartItemSerializer, AddToCartSerializer, UpdateCartItemSerializer,
    WishlistSerializer, WishlistItemSerializer, AddToWishlistSerializer, MoveToCartSerializer,
    BrandSerializer, ProductListSerializer, AddressListSerializer, CreateAddressSerializer,
    SelectAddressSerializer, DetectLocationSerializer, LocationAddressResponseSerializer,
    ConfirmLocationAddressSerializer
)
from .geocoding import reverse_geocode, GeocodingException, validate_coordinates


User = get_user_model()


# ==================== UTILITY FUNCTIONS ====================

def get_client_ip(request):
    """
    Get client's IP address from request
    Handles X-Forwarded-For header for proxied requests
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ProfileView for GET, POST, PUT
from rest_framework.permissions import IsAuthenticated


class ProfileView(APIView):
    """
    API endpoint for retrieving and updating retailer profile only.
    GET: Retrieve current retailer's profile or by user_id (superadmin only)
    PUT: Update current retailer's profile
    """
    permission_classes = [AllowAny]

    def get(self, request, user_id=None):
        user = request.user
        # If user_id is provided, only superadmin or the user themselves can fetch others' profiles
        if user_id is not None:
            # AnonymousUser has no role/id, so allow access for anyone if user is not authenticated
            if user.is_authenticated:
                if getattr(user, 'role', None) != 'SUPERADMIN' and getattr(user, 'id', None) != user_id:
                    return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            target_user = get_object_or_404(User, id=user_id)
        else:
            # If not authenticated, cannot get own profile
            if not user.is_authenticated:
                return Response({'error': 'Authentication required to access your own profile.'}, status=status.HTTP_401_UNAUTHORIZED)
            target_user = user
        if getattr(target_user, 'role', None) != 'RETAILER':
            return Response({'error': 'Only retailers have profiles at this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Try to get KYC info using queryset to avoid RelatedObjectDoesNotExist issues
        kyc = None
        kyc_exists = False
        try:
            kyc = KYC.objects.get(user=target_user)
            kyc_exists = True
        except KYC.DoesNotExist:
            kyc_exists = False
        except Exception as e:
            print(f"Error fetching KYC: {e}")
            kyc_exists = False
        
        profile = {
            'id': target_user.id,
            'name': target_user.first_name or target_user.username,
            'shop_name': kyc.shop_name if kyc else '',
            'shop_address': kyc.shop_address if kyc else '',
            'customer_name': kyc.customer_name if kyc else '',
            'customer_id': kyc.customer_id if kyc else '',
            'email': target_user.email,
            'customer_email': kyc.shop_email if kyc else '',
            'phone': target_user.phone_number or (kyc.customer_mobile if kyc else ''),
            'store_photo': request.build_absolute_uri(kyc.store_photo.url) if kyc and kyc.store_photo else '',
            'customer_photo': request.build_absolute_uri(kyc.customer_photo.url) if kyc and kyc.customer_photo else '',
            'kyc_exists': kyc_exists,
            'kyc_status': kyc.get_status_display() if kyc else 'Not Submitted'
        }
        return Response(profile, status=status.HTTP_200_OK)

    def post(self, request, user_id=None):
        """
        POST: Upload customer photo to profile
        Expects user_id as URL parameter or uses authenticated user
        """
        # Determine which user to update
        if user_id is not None:
            user = get_object_or_404(User, id=user_id)
        else:
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required to upload customer photo.'}, status=status.HTTP_401_UNAUTHORIZED)
            user = request.user
        
        if getattr(user, 'role', None) != 'RETAILER':
            return Response({'error': 'Only retailers can upload customer photo.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if customer_photo is provided
        if 'customer_photo' not in request.FILES:
            return Response({'error': 'customer_photo file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get KYC record using queryset
        kyc = None
        try:
            kyc = KYC.objects.get(user=user)
        except KYC.DoesNotExist:
            return Response({'error': 'KYC record not found. Please submit KYC first.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Error retrieving KYC: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update customer_photo
        kyc.customer_photo = request.FILES['customer_photo']
        kyc.save()
        
        # Return updated profile
        profile = {
            'id': user.id,
            'name': user.first_name or user.username,
            'shop_name': kyc.shop_name if kyc else '',
            'shop_address': kyc.shop_address if kyc else '',
            'customer_name': kyc.customer_name if kyc else '',
            'customer_id': kyc.customer_id if kyc else '',
            'email': user.email,
            'customer_email': kyc.shop_email if kyc else '',
            'phone': user.phone_number or (kyc.customer_mobile if kyc else ''),
            'store_photo': self.request.build_absolute_uri(kyc.store_photo.url) if kyc and kyc.store_photo else '',
            'customer_photo': self.request.build_absolute_uri(kyc.customer_photo.url) if kyc and kyc.customer_photo else '',
            'kyc_exists': True,
            'kyc_status': kyc.get_status_display()
        }
        return Response(profile, status=status.HTTP_200_OK)

    def put(self, request, user_id=None):
        # Only allow updating specific profile fields
        if user_id is None:
            return Response({'error': 'user_id is required in the URL.'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, id=user_id)
        if getattr(user, 'role', None) != 'RETAILER':
            return Response({'error': 'Only retailers can update their profile.'}, status=status.HTTP_403_FORBIDDEN)

        # Only allow updating name (first_name), and KYC fields: shop_name, shop_email, shop_address, shopphone number, store_photo, customer_photo
        allowed_user_fields = ['first_name']
        allowed_kyc_fields = ['shop_name', 'shop_email', 'shop_address', 'shop_phone', 'store_photo', 'customer_photo']

        # Update user name if provided
        if 'name' in request.data:
            user.first_name = request.data['name']
            user.save()

        # Get or create KYC record
        kyc = None
        try:
            kyc = KYC.objects.get(user=user)
        except KYC.DoesNotExist:
            return Response({'error': 'KYC record not found. Please submit KYC first.'}, status=status.HTTP_404_NOT_FOUND)

        # Update allowed KYC fields
        updated = False
        for field in allowed_kyc_fields:
            if field in request.data:
                value = request.data[field]
                setattr(kyc, field, value)
                updated = True
        if updated:
            kyc.save()

        # Build response with only the allowed fields
        profile = {
            'name': user.first_name,
            'shop_name': kyc.shop_name if kyc else '',
            'shop_email': kyc.shop_email if kyc else '',
            'shop_address': kyc.shop_address if kyc else '',
            'shop_phone': kyc.shop_phone if kyc else '',
            'store_photo': request.build_absolute_uri(kyc.store_photo.url) if kyc and kyc.store_photo else '',
            'customer_photo': request.build_absolute_uri(kyc.customer_photo.url) if kyc and kyc.customer_photo else '',
        }
        return Response(profile, status=status.HTTP_200_OK)


class SuperAdminLoginView(APIView):
    """
    API endpoint for superadmin login.
    POST /api/auth/login/ - Login with username/email and password
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Login a superadmin with username/email and password.
        Returns access and refresh JWT tokens.
        
        Request Body:
        {
            "username": "admin_username or admin@example.com",
            "password": "password123"
        }
        """
        serializer = SuperAdminLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


class RetailerLoginView(APIView):
    """
    API endpoint for retailer login with email and password.
    POST /api/retailer-auth/login/ - Step 1: Login with email + password, OTP sent to email
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 1: Login with email and password. OTP is sent to email for verification.
        
        Request Body:
        {
            "email": "retailer@example.com",
            "password": "password123"
        }
        
        Response:
        {
            "message": "Email and password verified. OTP sent to your email.",
            "email": "retailer@example.com"
        }
        """
        serializer = RetailerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        
        # Delete any existing OTPs for this user
        OTP.objects.filter(user=user).delete()
        
        # Generate and send OTP via email
        otp_obj = OTP.objects.create(user=user)
        otp_code = otp_obj.generate_otp()
        
        try:
            send_mail(
                subject="Your Dream's Pharmacy Login OTP",
                message=f'Your 4-digit OTP for login is: {otp_code}\n\nThis OTP is valid for 1 minute.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending email: {e}")
            return Response({
                'error': 'Failed to send OTP email. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'Email and password verified. OTP sent to your email.',
            'email': user.email
        }, status=status.HTTP_200_OK)


class RetailerVerifyOTPView(APIView):
    """
    API endpoint for retailer OTP verification during login.
    POST /api/retailer-auth/verify-otp/ - Step 2: Verify OTP and get JWT tokens
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 2: Verify OTP to complete login.
        
        Request Body:
        {
            "otp_code": "1234"
        }
        
        Response (Success):
        {
            "message": "OTP verified successfully. You are now logged in.",
            "access": "JWT_TOKEN",
            "refresh": "REFRESH_TOKEN"
        }
        
        Response (Error - Invalid OTP):
        {
            "error": "Invalid OTP. Please try again."
        }
        """
        otp_code = request.data.get('otp_code')
        
        if not otp_code:
            return Response({
                'error': 'OTP code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Find OTP by code (most recent one)
            otp_obj = OTP.objects.filter(otp_code=otp_code).latest('created_at')
            user = otp_obj.user
            
            # Check if OTP is expired
            if otp_obj.is_expired():
                return Response({
                    'error': 'Your OTP has expired. Please login again to request a new OTP.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # OTP verified successfully
            otp_obj.is_verified = True
            otp_obj.save()
            
            # Update user status based on workflow stage
            if user.status == 'PENDING_OTP_VERIFICATION':
                # First-time registration OTP - need to submit KYC
                user.status = 'REGISTERED'
                user.save()
                return Response({
                    'message': 'OTP verified successfully. Please submit your KYC to continue.',
                    'user': {
                        'id': user.id,
                        'email': user.email
                    },
                    'workflow_stage': 'REGISTERED',
                    'next_step': 'Submit KYC at /api/kyc/submit/<user_id>/'
                }, status=status.HTTP_200_OK)
            
            # User is approved - can login
            if user.status == 'APPROVED':
                user.status = 'LOGIN_ENABLED'
                user.save()
            
            # Generate JWT tokens for approved/login enabled users
            refresh = RefreshToken.for_user(user)
            
            # Get token lifetimes from settings for mobile app silent refresh
            access_lifetime = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME')
            refresh_lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')
            
            return Response({
                'message': 'OTP verified successfully. You are now logged in.',
                'user': {
                    'id': user.id,
                    'email': user.email
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'access_expires_in': int(access_lifetime.total_seconds()),  # 600 seconds (10 min)
                    'refresh_expires_in': int(refresh_lifetime.total_seconds()),  # 604800 seconds (7 days)
                    'token_type': 'Bearer'
                }
            }, status=status.HTTP_200_OK)
        
        except OTP.DoesNotExist:
            return Response({
                'error': 'Invalid OTP. Please try again.'
            }, status=status.HTTP_400_BAD_REQUEST)


class RetailerResendOTPView(APIView):
    """
    API endpoint to resend OTP for retailer login.
    POST /api/retailer-auth/resend-otp/ - Resend OTP to email
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Resend OTP for login verification.
        
        Request Body:
        {
            "email": "retailer@example.com"
        }
        
        Response (Success):
        {
            "message": "OTP resent successfully.",
            "email": "retailer@example.com"
        }
        """
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email.lower(), role='RETAILER')
        except User.DoesNotExist:
            return Response({
                'error': 'Email is not registered or not a retailer account'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Delete any existing OTPs for this user
        OTP.objects.filter(user=user).delete()
        
        # Generate and send new OTP
        otp_obj = OTP.objects.create(user=user)
        otp_code = otp_obj.generate_otp()
        
        try:
            send_mail(
                subject="Your Dream's Pharmacy Login OTP (Resent)",
                message=f'Your 4-digit OTP for login is: {otp_code}\n\nThis OTP is valid for 1 minute.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending email: {e}")
            return Response({
                'error': 'Failed to send OTP email. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'OTP resent successfully.',
            'email': user.email
        }, status=status.HTTP_200_OK)


class UserRegistrationView(APIView):
    """
    API endpoint for user registration.
    Only creates RETAILER accounts.
    POST /api/auth/register/ - Register a new retailer
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Register a new retailer. KYC will be submitted in a separate step after OTP verification."""
       
        registration_serializer = UserRegistrationSerializer(data=request.data)
        if not registration_serializer.is_valid():
            return Response(registration_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
       
        user = registration_serializer.save()
        user.status = 'PENDING_OTP_VERIFICATION'
        user.save()
        
      
        otp_obj = OTP.objects.filter(user=user).latest('created_at')
        
        # Generate and send OTP via email
        otp_code = otp_obj.generate_otp()
        
        try:
            send_mail(
                subject="Your Dream's Pharmacy Registration OTP",
                message=f'Your 4-digit OTP for registration verification is: {otp_code}\n\nThis OTP is valid for 30 seconds.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending email: {e}")
        
        return Response({
            'message': 'Registration successful! 4-digit OTP sent to your email.',
            'otp_expires_in': 60,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
            },
        }, status=status.HTTP_201_CREATED)


class OTPRequestView(APIView):
    """
    API endpoint for requesting OTP via email.
    POST /api/otp/request_otp/ - Request OTP for registration or login via email
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Request OTP for registration or login via email."""
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email, role='RETAILER')
            
            # Allow OTP request for PENDING_OTP_VERIFICATION (during registration) and APPROVED (login) users
            allowed_statuses = ['PENDING_OTP_VERIFICATION', 'APPROVED']
            if user.status not in allowed_statuses:
                return Response({
                    'error': f'Your account status: {user.get_status_display()}. Cannot request OTP at this stage.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Generate and send OTP via email
            otp_obj = OTP.objects.create(user=user)
            otp_code = otp_obj.generate_otp()
            
            # Determine OTP purpose based on user status
            if user.status == 'PENDING_OTP_VERIFICATION':
                # Registration OTP
                otp_subject = "Your Dream's Pharmacy Registration OTP"
                otp_message = f'Your 4-digit OTP for registration verification is: {otp_code}\n\nThis OTP is valid for 1 minute.'
            else:  # user.status == 'APPROVED'
                # Login OTP
                otp_subject = "Your Dream's Pharmacy Login OTP"
                otp_message = f'Your 4-digit OTP for login is: {otp_code}\n\nThis OTP is valid for 1 minute.'
            
            try:
                send_mail(
                    subject=otp_subject,
                    message=otp_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error sending email: {e}")
            
            return Response({
                'message': 'OTP sent to your email successfully',
                'email': email,
                'otp_expires_in': 60,
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'error': 'User not found with this email'
            }, status=status.HTTP_404_NOT_FOUND)


class OTPVerifyView(APIView):
    """
    API endpoint for verifying OTP.
    POST /api/otp/verify_otp/ - Verify OTP and update user status based on workflow stage
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Verify OTP and update user status based on workflow stage"""
        otp_code = request.data.get('otp_code')
        
        if not otp_code:
            return Response({
                'error': 'OTP code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Find OTP by code (most recent one)
            otp_obj = OTP.objects.filter(otp_code=otp_code).latest('created_at')
            user = otp_obj.user
            
            # Check if OTP is expired
            if otp_obj.is_expired():
                return Response({
                    'error': 'Your OTP has expired. Please generate a new OTP to continue.',
                    'otp_expires_in': 0
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if otp_obj.otp_code == otp_code:
                otp_obj.is_verified = True
                otp_obj.save()
                
                
                if user.status == 'PENDING_OTP_VERIFICATION':
                    # Change status to REGISTERED after OTP verification
                    user.status = 'REGISTERED'
                    user.save()
                    return Response({
                        'message': 'Your OTP has been verified. Please submit your KYC to continue.',
                        'otp_expires_in': otp_obj.get_expiry_time_remaining(),
                        'user': CustomUserSerializer(user).data,
                    }, status=status.HTTP_200_OK)
                
                
                elif user.status == 'APPROVED':
                    user.status = 'LOGIN_ENABLED'
                    user.save()
                    
                    refresh = RefreshToken.for_user(user)
                    
                    # Get token lifetimes for mobile app silent refresh
                    access_lifetime = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME')
                    refresh_lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')
                    
                    return Response({
                        'message': 'OTP verified successfully. You are now logged in.',
                        'otp_expires_in': otp_obj.get_expiry_time_remaining(),
                        'user': CustomUserSerializer(user).data,
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                        'access_expires_in': int(access_lifetime.total_seconds()),
                        'refresh_expires_in': int(refresh_lifetime.total_seconds()),
                        'token_type': 'Bearer'
                    }, status=status.HTTP_200_OK)
                
                else:
                    return Response({
                        'error': f'Cannot verify OTP. User status is {user.get_status_display()}. Expected PENDING_OTP_VERIFICATION or APPROVED.',
                        'otp_expires_in': otp_obj.get_expiry_time_remaining()
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'error': 'Invalid OTP',
                    'otp_expires_in': otp_obj.get_expiry_time_remaining()
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except OTP.DoesNotExist:
            return Response({
                'error': 'Invalid OTP. Please check and try again'
            }, status=status.HTTP_400_BAD_REQUEST)


class KYCSubmitView(APIView):
    """
    API endpoint for KYC submission with user ID in URL path.
    POST /api/kyc/submit/<user_id>/ - Submit KYC documents for approval
    Example: POST /api/kyc/submit/28/
    """
    permission_classes = [AllowAny] 
    
    def post(self, request, user_id=None):
        """Submit KYC documents. User must have verified OTP first."""
        
        if request.user.is_authenticated:
            user = request.user
        else:
            if not user_id:
                return Response({
                    'error': 'User ID required in URL. Example: /api/kyc/submit/28/'
                }, status=status.HTTP_400_BAD_REQUEST)
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'error': f'User with ID {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        if user.role != 'RETAILER':
            return Response({
                'error': 'Only retailers can submit KYC'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if KYC already submitted FIRST
        if hasattr(user, 'kyc'):
            return Response({
                'error': 'KYC already submitted for this user',
                'kyc_status': user.kyc.status,
                'kyc': KYCSerializer(user.kyc).data
            }, status=status.HTTP_400_BAD_REQUEST)
       
        # Check if user status is REGISTERED (which means OTP has been verified)
        if user.status != 'REGISTERED':
            return Response({
                'error': f'You must verify OTP first before submitting KYC. Current status: {user.get_status_display()}',
                'workflow_stage': user.status,
                'next_step': 'Verify OTP at /api/otp/verify_otp/'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = KYCSubmitSerializer(data=request.data)
        if serializer.is_valid():
            kyc = KYC.objects.create(user=user, **serializer.validated_data)
            
           
            user.status = 'PENDING_APPROVAL'
            user.save()
            
            return Response({
                'message': 'KYC submitted successfully! Awaiting admin approval.',
                'workflow_stage': 'PENDING_APPROVAL',
                'kyc_status': kyc.get_status_display(),
                'kyc': KYCSerializer(kyc).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KYCStatusView(APIView):
    """
    API endpoint to check KYC status.
    GET /api/kyc/status/?user_id=<user_id> - Get KYC status for a user
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            # If no user_id provided, try to get from authenticated user
            if request.user.is_authenticated:
                user = request.user
            else:
                return Response({
                    'error': 'user_id query parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'error': f'User with ID {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if KYC exists
        kyc = None
        kyc_exists = False
        try:
            kyc = KYC.objects.get(user=user)
            kyc_exists = True
        except KYC.DoesNotExist:
            kyc_exists = False
        
        if not kyc_exists:
            return Response({
                'status': 'NOT_SUBMITTED',
                'message': 'KYC not yet submitted'
            }, status=status.HTTP_200_OK)
        
        # Determine message based on status
        if kyc.status == 'REJECTED':
            message = 'Your KYC has been rejected. Please review the rejection reason and resubmit.'
        elif kyc.status == 'APPROVED':
            message = 'Your KYC has been approved. You can now login.'
        else:
            message = 'Your KYC is pending approval.'
        
        return Response({
            'status': kyc.status,
            'message': message
        }, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email, role='RETAILER')
        # Generate and save OTP
        otp_obj = OTP.objects.create(user=user)
        otp_code = otp_obj.generate_otp()
        # Send OTP via email
        try:
            send_mail(
                subject="Dream's Pharmacy Password Reset OTP",
                message=f'Your OTP for password reset is: {otp_code}\n\nThis OTP is valid for 1 minute.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)

class ResetOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "OTP verified. You can now reset your password."}, status=status.HTTP_200_OK)

class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.validated_data['user']
        otp_obj = serializer.validated_data['otp_obj']
        new_password = serializer.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        otp_obj.is_verified = True
        otp_obj.save()
        return Response({"message": "Password reset successful. You can now log in with your new password."}, status=status.HTTP_200_OK)

class ChangePasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, user_id=None):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({"user_id": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            if not user.check_password(serializer.validated_data['oldpassword']):
                return Response(
                    {"oldpassword": "Old password is incorrect."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.validated_data['newpassword'])
            user.save()
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SuperAdminChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'SUPERADMIN':
            return Response({"error": "Only Super Admins can change password here."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['oldpassword']):
                return Response(
                    {"oldpassword": "Old password is incorrect."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if serializer.validated_data['oldpassword'] == serializer.validated_data['newpassword']:
                return Response(
                    {"newpassword": "New password cannot be the same as old password."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.validated_data['newpassword'])
            user.save()
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class HomeView(APIView):
    """
    Home endpoint for authenticated users.
    GET /api/home/ - Get welcome message with user details
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "message": f"Welcome {user.username}!",
            "email": user.email,
            "user_id": user.id,
            "role": user.role,
            "status": user.get_status_display()
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            logout(request)
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(APIView):
    """
    Silent token refresh endpoint for mobile apps.
    POST /api/retailer-auth/token/refresh/ - Refresh access token silently
    
    Industry-standard approach:
    - Access token: 10 minutes (short-lived for security)
    - Refresh token: 7 days (user stays logged in)
    - Token rotation: New refresh token on each refresh (more secure)
    
    Mobile app should:
    1. Store both access and refresh tokens securely
    2. Check access token expiry before API calls (or catch 401)
    3. Call this endpoint ~1 min before access token expires
    4. Update both tokens from response
    
    User experience: Feels like token never expires (silent refresh)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Refresh access token using refresh token.
        
        Request Body:
        {
            "refresh": "REFRESH_TOKEN"
        }
        
        Response (Success):
        {
            "access": "NEW_ACCESS_TOKEN",
            "refresh": "NEW_REFRESH_TOKEN",  // Token rotation enabled
            "access_expires_in": 600,  // 10 minutes in seconds
            "refresh_expires_in": 604800  // 7 days in seconds
        }
        
        Response (Error - Expired/Invalid):
        {
            "error": "Token is invalid or expired",
            "code": "token_not_valid"
        }
        """
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({
                'error': 'Refresh token is required',
                'code': 'missing_token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create refresh token object
            refresh = RefreshToken(refresh_token)
            
            # Get user from token
            user_id = refresh.payload.get('user_id')
            user = User.objects.get(id=user_id)
            
            # Check if user is still active and approved
            if not user.is_active:
                return Response({
                    'error': 'User account is disabled',
                    'code': 'user_inactive'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate new access token
            new_access = str(refresh.access_token)
            
            # Token rotation: Generate new refresh token and blacklist old one
            # This is handled automatically by ROTATE_REFRESH_TOKENS setting
            new_refresh = str(refresh)
            
            # Get token lifetimes from settings
            from django.conf import settings
            access_lifetime = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME')
            refresh_lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')
            
            return Response({
                'access': new_access,
                'refresh': new_refresh,
                'access_expires_in': int(access_lifetime.total_seconds()),
                'refresh_expires_in': int(refresh_lifetime.total_seconds()),
                'token_type': 'Bearer'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = str(e)
            if 'token_not_valid' in error_message.lower() or 'invalid' in error_message.lower():
                return Response({
                    'error': 'Token is invalid or expired. Please login again.',
                    'code': 'token_not_valid'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            return Response({
                'error': 'Token refresh failed. Please login again.',
                'code': 'refresh_failed'
            }, status=status.HTTP_401_UNAUTHORIZED)


# ==================== ERP INTEGRATION VIEWS ====================

class GenerateTokenView(APIView):
    """
    Generate API token for ERP integration
    POST: Generate and return API token
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = GenerateTokenRequestSerializer(data=request.data)
        if serializer.is_valid():
            c2_code = serializer.validated_data['c2Code']
            store_id = serializer.validated_data['storeId']
            prod_code = serializer.validated_data.get('prodCode', '02')
            security_key = serializer.validated_data['securityKey']
            
            try:
                # Get or create API token
                api_token, created = APIToken.objects.get_or_create(
                    c2_code=c2_code,
                    defaults={
                        'store_id': store_id,
                        'prod_code': prod_code,
                        'security_key': security_key,
                        'api_key': base64.b64encode(f"{c2_code}^{timezone.now()}".encode()).decode()
                    }
                )
                
                response_data = {
                    'code': '200',
                    'type': 'generateToken',
                    'apiKey': api_token.api_key
                }
                return Response(response_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    'code': '500',
                    'type': 'generateToken',
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'generateToken',
            'message': 'Invalid parameters'
        }, status=status.HTTP_400_BAD_REQUEST)


class GetItemMasterView(APIView):
    """
    Get item master details
    GET: Fetch item details based on parameters in request body
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        serializer = FetchStockRequestSerializer(data=request.data)
        if serializer.is_valid():
            api_key = serializer.validated_data['apiKey']
            
            try:
                # Validate API key
                api_token = APIToken.objects.get(api_key=api_key, is_active=True)
            except APIToken.DoesNotExist:
                return Response({
                    'code': '401',
                    'type': 'getMasterData',
                    'message': 'Unauthorized - Invalid API key'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get items from database
            items = ItemMaster.objects.all()
            item_serializer = ItemMasterSerializer(items, many=True)
            
            return Response({
                'code': '200',
                'type': 'getMasterData',
                'data': item_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'code': '400',
            'type': 'getMasterData',
            'message': 'Invalid parameters'
        }, status=status.HTTP_400_BAD_REQUEST)


class FetchStockView(APIView):
    """
    Fetch stock details for items
    GET: Get stock information for all items
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        serializer = FetchStockRequestSerializer(data=request.query_params)
        if serializer.is_valid():
            api_key = serializer.validated_data['apiKey']
            store_id = serializer.validated_data.get('storeId')
            
            try:
                # Validate API key
                api_token = APIToken.objects.get(api_key=api_key, is_active=True)
            except APIToken.DoesNotExist:
                return Response({
                    'code': '401',
                    'message': 'Unauthorized - Invalid API key'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get stock data
            if store_id:
                stocks = Stock.objects.filter(store_id=store_id)
            else:
                stocks = Stock.objects.all()
            
            stock_serializer = StockItemSerializer(stocks, many=True)
            
            return Response(stock_serializer.data, status=status.HTTP_200_OK)
        
        return Response({
            'code': '400',
            'message': 'Invalid parameters'
        }, status=status.HTTP_400_BAD_REQUEST)


class CreateSalesOrderView(APIView):
    """
    Create a sales order in the system
    POST: Create sales order with line items
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CreateSalesOrderRequestSerializer(data=request.data)
        if serializer.is_valid():
            api_key = serializer.validated_data['apiKey']
            
            try:
                # Validate API key
                api_token = APIToken.objects.get(api_key=api_key, is_active=True)
            except APIToken.DoesNotExist:
                return Response({
                    'code': '401',
                    'type': 'SaleOrderCreate',
                    'message': 'Unauthorized - Invalid API key'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            try:
                # Create sales order
                sales_order = SalesOrder.objects.create(
                    c2_code=serializer.validated_data['c2Code'],
                    store_id=serializer.validated_data['storeId'],
                    order_id=f"{serializer.validated_data['orderId']}",
                    ip_no=serializer.validated_data['ipNo'],
                    mobile_no=serializer.validated_data['mobileNo'],
                    patient_name=serializer.validated_data['patientName'],
                    patient_address=serializer.validated_data['patientAddress'],
                    patient_email=serializer.validated_data['patientEmail'],
                    counter_sale=bool(serializer.validated_data['counterSale']),
                    ord_date=serializer.validated_data['ordDate'],
                    ord_time=serializer.validated_data['ordTime'],
                    user_id=serializer.validated_data['userId'],
                    cust_code=serializer.validated_data['actCode'],
                    cust_name=serializer.validated_data['actName'],
                    dr_code=serializer.validated_data.get('drCode', ''),
                    dr_name=serializer.validated_data.get('drName', ''),
                    dr_address=serializer.validated_data.get('drAddress', ''),
                    dr_reg_no=serializer.validated_data.get('drRegNo', ''),
                    dr_office_code=serializer.validated_data.get('drOfficeCode', '-'),
                    dman_code=serializer.validated_data.get('dmanCode', '-'),
                    order_total=serializer.validated_data['orderTotal'],
                    order_disc_per=serializer.validated_data.get('orderDiscPer', 0),
                    ref_no=serializer.validated_data.get('refNo'),
                    remark=serializer.validated_data.get('remark'),
                    urgent_flag=bool(serializer.validated_data.get('urgentFlag', 0)),
                    ord_conversion_flag=bool(serializer.validated_data.get('ordConversionFlag', 0)),
                    dc_conversion_flag=bool(serializer.validated_data.get('dcConversionFlag', 0)),
                    ord_ref_no=serializer.validated_data.get('ordRefNo', 0),
                    sys_name=serializer.validated_data['sysName'],
                    sys_ip=serializer.validated_data['sysIp'],
                    sys_user=serializer.validated_data['sysUser'],
                    br_code=serializer.validated_data['storeId'],
                    tran_year=str(timezone.now().year % 100),
                    tran_prefix='6',
                    tran_srno='1',
                    bill_total=serializer.validated_data['orderTotal']
                )
                
                # Create line items with batch and expiry tracking
                material_info = serializer.validated_data['materialInfo']
                for item in material_info:
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        item_seq=item['item_seq'],
                        item_code=item['item_code'],
                        item_name=item.get('item_name', ''),
                        batch_no=item.get('batch_no'),  # ✅ FIX #2: Track batch for recalls
                        expiry_date=item.get('expiry_date'),  # ✅ FIX #2: Track expiry for recalls
                        total_loose_qty=item['total_loose_qty'],
                        total_loose_sch_qty=item.get('total_loose_sch_qty', 0),
                        service_qty=item.get('service_qty', 0),
                        sale_rate=item['sale_rate'],
                        disc_per=item.get('disc_per', 0),
                        sch_disc_per=item.get('sch_disc_per', 0)
                    )
                
                # Generate document number
                sales_order.document_pk = f"{sales_order.br_code}{sales_order.tran_year}{sales_order.tran_prefix}{sales_order.id}"
                sales_order.save()
                
                # ✅ FIX #4: AUDIT LOGGING - Log all order creation details
                logger.info(f"[ORDER_CREATED] ID: {sales_order.order_id} | Patient: {sales_order.patient_name} | Email: {sales_order.patient_email} | Mobile: {sales_order.mobile_no} | Total: {sales_order.order_total} | User: {sales_order.sys_user} | IP: {sales_order.sys_ip}")
                for order_item in sales_order.items.all():
                    logger.info(f"  [ORDER_ITEM] Code: {order_item.item_code} | Name: {order_item.item_name} | Batch: {order_item.batch_no} | Expiry: {order_item.expiry_date} | Qty: {order_item.total_loose_qty} | Rate: {order_item.sale_rate}")
                
                response_data = {
                    'code': '200',
                    'type': 'SaleOrderCreate',
                    'message': f'Document No. : {sales_order.document_pk} successfully processed.',
                    'documentDetails': [{
                        'brCode': sales_order.br_code,
                        'tranYear': sales_order.tran_year,
                        'tranPrefix': sales_order.tran_prefix,
                        'tranSrno': sales_order.tran_srno,
                        'documentPk': sales_order.document_pk,
                        'OrderId': sales_order.order_id,
                        'createdDate': str(sales_order.ord_date),
                        'billTotal': str(sales_order.bill_total)
                    }]
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response({
                    'code': '500',
                    'type': 'SaleOrderCreate',
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'SaleOrderCreate',
            'message': 'Invalid parameters'
        }, status=status.HTTP_400_BAD_REQUEST)


class CreateGLCustomerView(APIView):
    """
    Create Global Local Customer Master
    POST: Create customer record accessible across stores
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CreateGLCustomerRequestSerializer(data=request.data)
        if serializer.is_valid():
            api_key = serializer.validated_data['apiKey']
            code = serializer.validated_data['Code']
            
            try:
                # Validate API key
                api_token = APIToken.objects.get(api_key=api_key, is_active=True)
            except APIToken.DoesNotExist:
                return Response({
                    'code': '401',
                    'type': 'glcustcreation',
                    'message': 'Unauthorized - Invalid API key'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if customer code already exists
            if GLCustomer.objects.filter(code=code).exists():
                return Response({
                    'code': '400',
                    'type': 'glcustcreation',
                    'message': f'LcCode Already Exists:{code}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                customer = GLCustomer.objects.create(
                    c2_code=serializer.validated_data['c2Code'],
                    store_id=serializer.validated_data['StoreID'],
                    code=code,
                    ip_name=serializer.validated_data['ipName'],
                    mail=serializer.validated_data['Mail'],
                    gender=serializer.validated_data['Gender'],
                    dl_no=serializer.validated_data.get('Dlno', ''),
                    city=serializer.validated_data['City'],
                    ip_state=serializer.validated_data['ipState'],
                    address1=serializer.validated_data['Address1'],
                    address2=serializer.validated_data.get('Address2', ''),
                    pincode=serializer.validated_data['Pincode'],
                    mobile=serializer.validated_data['Mobile'],
                    gst_no=serializer.validated_data.get('Gstno', '')
                )
                
                return Response({
                    'code': '200',
                    'type': 'glcustcreation',
                    'message': f"Customer Name : {customer.ip_name} with Customer Code : {customer.code} created sucessfully."
                }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response({
                    'code': '500',
                    'type': 'glcustcreation',
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'glcustcreation',
            'message': 'Invalid parameters'
        }, status=status.HTTP_400_BAD_REQUEST)


class GetOrderStatusView(APIView):
    """
    Get order status with transaction details
    GET: Retrieve sales order status and invoice details
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Parse request parameters
        c2_code = request.query_params.get('c2Code')
        store_id = request.query_params.get('storeId')
        api_key = request.query_params.get('apiKey')
        order_id = request.query_params.get('orderId')
        
        if not all([c2_code, store_id, api_key, order_id]):
            return Response({
                'code': '400',
                'message': 'Missing required parameters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate API key
            api_token = APIToken.objects.get(api_key=api_key, is_active=True)
        except APIToken.DoesNotExist:
            return Response({
                'code': '401',
                'message': 'Unauthorized - Invalid API key'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get sales order
            sales_order = SalesOrder.objects.get(order_id=order_id, c2_code=c2_code)
            
            # Get invoices for this order
            invoices = Invoice.objects.filter(sales_order=sales_order)
            
            response_data = {
                'code': '200',
                'orderId': sales_order.order_id,
                'custCode': sales_order.cust_code,
                'fromGstNo': '07NQQAE5107K2ZW',  # Replace with actual GST from backend
                'toGstNo': '07NQQAE5107K2ZW',    # Replace with actual GST from customer
                'customerType': 'Un - Registered',
                'doctorName': sales_order.dr_name or '-',
                'invoices': []
            }
            
            invoice_serializer = InvoiceForStatusSerializer(invoices, many=True)
            response_data['invoices'] = invoice_serializer.data
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except SalesOrder.DoesNotExist:
            return Response({
                'code': '404',
                'message': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({
                'code': '500',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== CART VIEWS ====================

class CartView(APIView):
    """
    Get or clear user's cart
    GET: Retrieve cart with all items and totals
    DELETE: Clear entire cart
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        
        # Fetch fresh stock status for each item
        api_key = request.query_params.get('apiKey')
        cart_data = serializer.data
        
        for item in cart_data.get('items', []):
            item_code = item.get('item')
            stock_status = get_item_stock_status(item_code, api_key)
            item['availability'] = stock_status['status']
            item['available_qty'] = stock_status['qty']
            item['in_stock'] = stock_status['available']
            item['current_price'] = stock_status['price']
            item['current_discount'] = stock_status['discount']
        
        return Response({
            'success': True,
            'message': 'Cart retrieved successfully',
            'data': cart_data
        }, status=status.HTTP_200_OK)
    
    def delete(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()
            serializer = CartSerializer(cart)
            return Response({
                'success': True,
                'message': 'Cart cleared successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Cart not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AddToCartView(APIView):
    """
    Add item to cart
    POST: Add a new item or update quantity if exists
    Always fetches latest item details from ERP - No cached fallback
    FAILS if ERP is down (no stale data shown to customers)
    Uses atomic transaction to prevent race conditions
    Logs all additions for audit trail
    """
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
        from django.db import transaction
        
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item_code = serializer.validated_data['itemCode']
        quantity = serializer.validated_data.get('quantity', 1)
        batch_no = serializer.validated_data.get('batchNo')
        api_key = request.data.get('apiKey')
        
        # Get user from database
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # ✅ FIX #3: ATOMIC TRANSACTION - Prevents race condition overselling
        try:
            with transaction.atomic():
                # Fetch fresh item details from ERP - REQUIRED, no fallback
                item_data = fetch_item_from_erp(item_code, api_key)
                
                if not item_data:
                    return Response({
                        'success': False,
                        'message': 'ERP service temporarily unavailable. Please try again.'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
                # Update ItemMaster cache with fresh ERP data (essential fields only)
                item = update_itemmaster_cache(item_code, item_data)
                
                if not item:
                    return Response({
                        'success': False,
                        'message': 'Failed to process item. Please try again.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Check stock availability - CRITICAL for pharmacy (includes expiry check)
                stock_status = get_item_stock_status(item_code, api_key)
                if not stock_status['available']:
                    logger.warning(f"User {user_id} tried to add unavailable item {item_code} - Status: {stock_status['status']}")
                    return Response({
                        'success': False,
                        'message': f'{item.item_name} is {stock_status["status"]}',
                        'status': stock_status['status'],
                        'available_qty': stock_status['qty'],
                        'expiry_date': stock_status.get('expiry_date'),
                        'is_expired': stock_status.get('is_expired')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if requested quantity is available
                if quantity > stock_status['qty']:
                    logger.warning(f"User {user_id} requested {quantity} units but only {stock_status['qty']} available for {item_code}")
                    return Response({
                        'success': False,
                        'message': f'Only {stock_status["qty"]} units available',
                        'requested': quantity,
                        'available_qty': stock_status['qty']
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Get or create cart
                cart, _ = Cart.objects.get_or_create(user=user)
                
                # Check if item already in cart
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    item=item,
                    defaults={'quantity': quantity, 'batch_no': batch_no}
                )
                
                if not created:
                    # Update quantity
                    cart_item.quantity += quantity
                    cart_item.batch_no = batch_no or cart_item.batch_no
                    cart_item.save()
                
                # ✅ FIX #4: AUDIT LOGGING - Track all cart additions
                logger.info(f"[CART_ADD] User: {user.id} ({user.username}) | Item: {item_code} | Qty: {quantity} | Batch: {batch_no} | Total Items in Cart: {cart.items.count()}")
                
                cart_serializer = CartSerializer(cart)
                return Response({
                    'success': True,
                    'message': f'{item.item_name} added to cart' if created else f'{item.item_name} quantity updated',
                    'data': cart_serializer.data
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        except Exception as e:
            # Transaction automatically rolled back
            logger.error(f"[CART_ERROR] User: {user_id} | Item: {item_code} | Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': 'An error occurred while adding item to cart. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateCartItemView(APIView):
    """
    Update cart item quantity
    PUT: Update quantity of specific cart item
    DELETE: Remove item from cart
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request, item_id):
        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.quantity = serializer.validated_data['quantity']
            cart_item.save()
            
            cart_serializer = CartSerializer(cart)
            return Response({
                'success': True,
                'message': 'Cart item updated successfully',
                'data': cart_serializer.data
            }, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Cart not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except CartItem.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Cart item not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, item_id):
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            item_name = cart_item.item.item_name
            cart_item.delete()
            
            cart_serializer = CartSerializer(cart)
            return Response({
                'success': True,
                'message': f'{item_name} removed from cart',
                'data': cart_serializer.data
            }, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Cart not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except CartItem.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Cart item not found'
            }, status=status.HTTP_404_NOT_FOUND)



# ==================== WISHLIST VIEWS ====================
from rest_framework.decorators import action
# --- Update Wishlist Item Quantity View ---
class UpdateWishlistItemView(APIView):
    """
    Update wishlist item quantity (increase/decrease)
    PUT: Update quantity of specific wishlist item
    DELETE: Remove item from wishlist (if quantity becomes 0)
    """
    permission_classes = [AllowAny]

    def put(self, request, item_id):
        """
        Increase or decrease wishlist item quantity.
        Request body: { "quantity": <int> }
        """
        from .models import Wishlist, WishlistItem
        quantity = request.data.get('quantity')
        if quantity is None:
            return Response({
                'success': False,
                'message': 'Quantity is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'message': 'Quantity must be an integer'
            }, status=status.HTTP_400_BAD_REQUEST)
        if quantity < 0:
            return Response({
                'success': False,
                'message': 'Quantity cannot be negative'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_item = WishlistItem.objects.get(id=item_id, wishlist=wishlist)
        except Wishlist.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wishlist not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except WishlistItem.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wishlist item not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if quantity == 0:
            item_name = wishlist_item.item.item_name
            wishlist_item.delete()
            from .serializers import WishlistSerializer
            wishlist_serializer = WishlistSerializer(wishlist)
            return Response({
                'success': True,
                'message': f'{item_name} removed from wishlist',
                'data': wishlist_serializer.data
            }, status=status.HTTP_200_OK)
        elif quantity < 1:
            return Response({
                'success': False,
                'message': 'Minimum allowed quantity is 1'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            wishlist_item.quantity = quantity
            wishlist_item.save()
            from .serializers import WishlistSerializer
            wishlist_serializer = WishlistSerializer(wishlist)
            return Response({
                'success': True,
                'message': 'Wishlist item quantity updated',
                'data': wishlist_serializer.data
            }, status=status.HTTP_200_OK)

class WishlistView(APIView):
    """
    Get or clear user's wishlist
    GET: Retrieve wishlist with all items
    DELETE: Clear entire wishlist
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        api_key = request.query_params.get('apiKey')
        user = request.user
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'User with id {user_id} not found',
                    'data': []
                }, status=status.HTTP_404_NOT_FOUND)
        elif not user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required or user_id must be provided',
                'data': []
            }, status=status.HTTP_401_UNAUTHORIZED)
        wishlist, created = Wishlist.objects.get_or_create(user=user)
        
        # Fetch fresh stock status for each item
        wishlist_data = {
            'id': wishlist.id,
            'user': wishlist.user.id,
            'items': []
        }
        
        for item in wishlist.items.all():
            stock_status = get_item_stock_status(item.item.item_code, api_key)
            item_data = {
                'id': item.id,
                'item': item.item.item_code,
                'item_name': item.item.item_name,
                'quantity': item.quantity,
                'availability': stock_status['status'],
                'available_qty': stock_status['qty'],
                'in_stock': stock_status['available'],
                'current_price': stock_status['price'],
                'current_discount': stock_status['discount']
            }
            wishlist_data['items'].append(item_data)
        
        return Response({
            'success': True,
            'message': 'Wishlist retrieved successfully',
            'data': wishlist_data
        }, status=status.HTTP_200_OK)
    
    def delete(self, request):
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist.items.all().delete()
            serializer = WishlistSerializer(wishlist)
            return Response({
                'success': True,
                'message': 'Wishlist cleared successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Wishlist.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wishlist not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AddToWishlistView(APIView):
    """
    Add item to wishlist
    POST: Add a new item to wishlist
    Always fetches latest item details from ERP - No cached fallback
    FAILS if ERP is down (no stale data shown to customers)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from django.db import transaction
        
        serializer = AddToWishlistSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item_code = serializer.validated_data['itemCode']
        api_key = request.data.get('apiKey')
        
        # ✅ FIX #3: ATOMIC TRANSACTION - Prevents race conditions
        try:
            with transaction.atomic():
                # Fetch fresh item details from ERP - REQUIRED, no fallback
                item_data = fetch_item_from_erp(item_code, api_key)
                
                if not item_data:
                    return Response({
                        'success': False,
                        'message': 'ERP service temporarily unavailable. Please try again.'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
                # Check stock availability BEFORE adding to wishlist
                stock_status = get_item_stock_status(item_code, api_key)
                if not stock_status['available']:
                    logger.warning(f"User tried to wishlist unavailable item {item_code} - Status: {stock_status['status']}")
                    return Response({
                        'success': False,
                        'message': f'Item is {stock_status["status"]}',
                        'status': stock_status['status'],
                        'available_qty': stock_status['qty'],
                        'is_expired': stock_status.get('is_expired')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Update ItemMaster cache with fresh ERP data (essential fields only)
                item = update_itemmaster_cache(item_code, item_data)
                
                if not item:
                    return Response({
                        'success': False,
                        'message': 'Failed to process item. Please try again.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Get or create wishlist
                wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
                
                # Check if item already in wishlist
                wishlist_item, created = WishlistItem.objects.get_or_create(
                    wishlist=wishlist,
                    item=item,
                    defaults={'quantity': 1}
                )
                if not created:
                    wishlist_item.quantity += 1
                    wishlist_item.save()
                    logger.info(f"[WISHLIST_UPDATE] User: {request.user.id} | Item: {item_code} | Quantity now: {wishlist_item.quantity}")
                    return Response({
                        'success': False,
                        'message': f'{item.item_name} is already in your wishlist'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # ✅ FIX #4: AUDIT LOGGING
                logger.info(f"[WISHLIST_ADD] User: {request.user.id} ({request.user.username}) | Item: {item_code}")
                
                wishlist_serializer = WishlistSerializer(wishlist)
                return Response({
                    'success': True,
                    'message': f'{item.item_name} added to wishlist',
                    'data': wishlist_serializer.data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"[WISHLIST_ERROR] User: {request.user.id} | Item: {item_code} | Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': 'An error occurred while adding item to wishlist. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveFromWishlistView(APIView):
    """
    Remove item from wishlist
    DELETE: Remove specific item from wishlist
    """
    permission_classes = [AllowAny]
    
    def delete(self, request, item_id):
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_item = WishlistItem.objects.get(id=item_id, wishlist=wishlist)
            item_name = wishlist_item.item.item_name
            wishlist_item.delete()
            
            wishlist_serializer = WishlistSerializer(wishlist)
            return Response({
                'success': True,
                'message': f'{item_name} removed from wishlist',
                'data': wishlist_serializer.data
            }, status=status.HTTP_200_OK)
        except Wishlist.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wishlist not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except WishlistItem.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wishlist item not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MoveToCartView(APIView):
    """
    Move item from wishlist to cart
    POST: Move item to cart and remove from wishlist
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = MoveToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item_code = serializer.validated_data['itemCode']
        # Use wishlist_item.quantity for cart
        
        try:
            item = ItemMaster.objects.get(item_code=item_code)
        except ItemMaster.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Item with code {item_code} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get wishlist and check if item exists
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_item = WishlistItem.objects.get(wishlist=wishlist, item=item)
        except (Wishlist.DoesNotExist, WishlistItem.DoesNotExist):
            return Response({
                'success': False,
                'message': 'Item not found in wishlist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create cart and add item
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            item=item,
            defaults={'quantity': wishlist_item.quantity}
        )
        if not created:
            cart_item.quantity += wishlist_item.quantity
            cart_item.save()
        # Remove from wishlist
        wishlist_item.delete()
        
        cart_serializer = CartSerializer(cart)
        return Response({
            'success': True,
            'message': f'{item.item_name} moved to cart',
            'data': {
                'cart': cart_serializer.data
            }
        }, status=status.HTTP_200_OK)


# ==================== BRAND VIEWS ====================

class BrandsView(APIView):
    """
    Get all medicine brands for sidebar categorization
    GET: Retrieve all active brands
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            brands = Brand.objects.filter(is_active=True)
            serializer = BrandSerializer(brands, many=True)
            
            return Response({
                'success': True,
                'message': 'Brands retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error retrieving brands: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class BrandProductsView(APIView):
    """
    Get products by brand
    GET: Retrieve products filtered by brand
    Query Parameters:
        - brand_id: Brand ID (required)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            brand_id = request.query_params.get('brand_id')
            
            if not brand_id:
                return Response({
                    'success': False,
                    'message': 'brand_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if brand exists
            try:
                brand = Brand.objects.get(id=brand_id, is_active=True)
            except Brand.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Brand not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get products for this brand with product info
            product_infos = ProductInfo.objects.filter(brand=brand).select_related('item')
            
            products = []
            for product_info in product_infos:
                item = product_info.item
                mrp = float(item.mrp)
                discount = float(item.std_disc)
                discounted = mrp * (1 - discount / 100)
                
                product_image_url = None
                if product_info.product_image:
                    product_image_url = request.build_absolute_uri(product_info.product_image.url)
                
                products.append({
                    'itemCode': item.item_code,
                    'itemName': item.item_name,
                    'brandName': brand.name,
                    'productImage': product_image_url,
                    'mrp': float(item.mrp),
                    'discountPercentage': item.std_disc,
                    'discountedPrice': round(discounted, 2),
                    'description': product_info.description
                })
            
            logo_url = None
            if brand.logo:
                logo_url = request.build_absolute_uri(brand.logo.url)
            
            return Response({
                'success': True,
                'message': 'Products retrieved successfully',
                'data': {
                    'brand': {
                        'id': brand.id,
                        'name': brand.name,
                        'logo': logo_url,
                        'description': brand.description
                    },
                    'products': products,
                    'count': len(products)
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error retrieving products: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class AllProductsView(APIView):
    """
    Get all products with optional brand filter
    GET: Retrieve all products with optional brand filter or search
    Query Parameters:
        - brand_id: Filter by brand ID (optional)
        - search: Search by product name (optional)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Start with all product infos
            product_infos = ProductInfo.objects.select_related('item', 'brand')
            
            # Filter by brand if provided
            brand_id = request.query_params.get('brand_id')
            if brand_id:
                product_infos = product_infos.filter(brand_id=brand_id)
            
            # Search by product name if provided
            search = request.query_params.get('search')
            if search:
                product_infos = product_infos.filter(item__item_name__icontains=search)
            
            products = []
            for product_info in product_infos:
                item = product_info.item
                mrp = float(item.mrp)
                discount = float(item.std_disc)
                discounted = mrp * (1 - discount / 100)
                
                product_image_url = None
                if product_info.product_image:
                    product_image_url = request.build_absolute_uri(product_info.product_image.url)
                
                products.append({
                    'itemCode': item.item_code,
                    'itemName': item.item_name,
                    'brandName': product_info.brand.name if product_info.brand else None,
                    'productImage': product_image_url,
                    'mrp': float(item.mrp),
                    'discountPercentage': item.std_disc,
                    'discountedPrice': round(discounted, 2),
                    'description': product_info.description
                })
            
            return Response({
                'success': True,
                'message': 'Products retrieved successfully',
                'data': products,
                'count': len(products)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error retrieving products: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


# ==================== ERP FETCH UTILITIES ====================

def fetch_item_from_erp(item_code, api_key=None):
    """
    Fetch a specific item from ERP endpoint
    Returns item data dict or None if not found
    ALWAYS FRESH - no cache used here
    """
    try:
        # Fetch all items from ERP
        erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
        params = {'apiKey': api_key} if api_key else {}
        
        response = requests.get(erp_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') != '200' or not data.get('data'):
            return None
        
        # Find the specific item
        for item_data in data.get('data', []):
            if item_data.get('c_item_code') == item_code:
                return item_data
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching from ERP: {str(e)}")
        return None


def update_itemmaster_cache(item_code, item_data):
    """
    Update ItemMaster cache with ESSENTIAL FIELDS ONLY
    Called periodically (every 15-30 min) and on-demand
    NEVER cache prices/availability - only structural data
    """
    try:
        if not item_data:
            return None
        
        item, created = ItemMaster.objects.update_or_create(
            item_code=item_code,
            defaults={
                'item_name': item_data.get('itemName', ''),
                'item_qty_per_box': item_data.get('itemQtyPerBox', 1),
                'batch_no': item_data.get('batchNo', ''),
                # ESSENTIAL FIELDS ONLY - updated from ERP
                'std_disc': float(item_data.get('std_disc', 0)),
                'max_disc': float(item_data.get('max_disc', 0)),
                'mrp': float(item_data.get('mrp', 0)),
                'expiry_date': datetime.strptime(item_data.get('expiryDate', '2099-12-31'), '%Y-%m-%d').date(),
            }
        )
        return item
    except Exception as e:
        logger.error(f"Error updating ItemMaster cache: {str(e)}")
        return None


def get_item_stock_status(item_code, api_key=None):
    """
    Fetch stock availability status for item from ERP
    CRITICAL CHECKS:
    - Stock quantity > 0
    - Expiry date not passed
    Always fresh - no caching
    """
    try:
        item_data = fetch_item_from_erp(item_code, api_key)
        if not item_data:
            return {'available': False, 'status': 'Not found in ERP', 'qty': 0, 'is_expired': False, 'expiry_date': None}
        
        stock_qty = item_data.get('stockBalQty', 0)
        
        # ✅ FIX #1: CHECK EXPIRY DATE - CRITICAL FOR PHARMACY
        try:
            expiry_date_str = item_data.get('expiryDate', '2099-12-31')
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            is_expired = expiry_date < timezone.now().date()
        except:
            expiry_date = None
            is_expired = False
        
        # Medicine is available ONLY if stock > 0 AND not expired
        available = stock_qty > 0 and not is_expired
        
        if is_expired:
            status = 'EXPIRED - Cannot Order'
        elif stock_qty == 0:
            status = 'Out of Stock'
        else:
            status = 'In Stock'
        
        return {
            'available': available,
            'status': status,
            'qty': int(stock_qty),
            'price': float(item_data.get('mrp', 0)),
            'discount': float(item_data.get('std_disc', 0)),
            'expiry_date': str(expiry_date) if expiry_date else None,
            'is_expired': is_expired
        }
    except Exception as e:
        logger.error(f"Error getting stock status: {str(e)}")
        return {'available': False, 'status': 'Unable to check availability', 'qty': 0, 'is_expired': False, 'expiry_date': None}


# ================== ADDRESS VIEWS ==================

class ListAddressesView(APIView):
    """List all delivery addresses for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all addresses"""
        try:
            addresses = Address.objects.filter(user=request.user, is_active=True).order_by('-is_default', '-created_at')
            serializer = AddressListSerializer(addresses, many=True)
            logger.info(f"[ADDRESS_LIST] User {request.user.username} retrieved {len(addresses)} addresses")
            return Response({
                'success': True,
                'count': len(addresses),
                'data': serializer.data,
                'message': 'Addresses retrieved successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error listing addresses for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error retrieving addresses: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateAddressView(APIView):
    """Add a new delivery address"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create new address"""
        try:
            serializer = CreateAddressSerializer(data=request.data)
            if serializer.is_valid():
                # Check if user already has this exact address
                existing = Address.objects.filter(
                    user=request.user,
                    phone=serializer.validated_data['phone'],
                    pincode=serializer.validated_data['pincode'],
                    locality=serializer.validated_data.get('locality', '')
                ).first()
                
                if existing:
                    return Response({
                        'success': False,
                        'message': 'This address already exists'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Create new address
                address = serializer.save(user=request.user)
                response_serializer = AddressListSerializer(address)
                logger.info(f"[ADDRESS_CREATE] User {request.user.username} added address: {address.name} ({address.address_type})")
                
                return Response({
                    'success': True,
                    'message': 'Address added successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error creating address for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error creating address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateAddressView(APIView):
    """Update an existing delivery address"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, address_id):
        """Update address"""
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            serializer = CreateAddressSerializer(address, data=request.data, partial=True)
            if serializer.is_valid():
                address = serializer.save()
                response_serializer = AddressListSerializer(address)
                logger.info(f"[ADDRESS_UPDATE] User {request.user.username} updated address ID {address_id}")
                
                return Response({
                    'success': True,
                    'message': 'Address updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error updating address {address_id} for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error updating address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAddressView(APIView):
    """Delete a delivery address (soft delete)"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, address_id):
        """Delete address"""
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            address.is_active = False
            address.save()
            logger.info(f"[ADDRESS_DELETE] User {request.user.username} deleted address ID {address_id}")
            
            return Response({
                'success': True,
                'message': 'Address deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error deleting address {address_id} for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error deleting address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetDefaultAddressView(APIView):
    """Set an address as default"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, address_id):
        """Set address as default"""
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Remove default from other addresses
            Address.objects.filter(user=request.user, is_default=True).exclude(id=address_id).update(is_default=False)
            address.is_default = True
            address.save()
            response_serializer = AddressListSerializer(address)
            logger.info(f"[ADDRESS_DEFAULT] User {request.user.username} set address ID {address_id} as default")
            
            return Response({
                'success': True,
                'message': 'Default address set successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error setting default address {address_id} for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error setting default address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckoutWithAddressView(APIView):
    """Checkout with selected delivery address"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Checkout with address selection"""
        try:
            serializer = SelectAddressSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            address_id = serializer.validated_data['address_id']
            
            # Verify address belongs to user
            try:
                address = Address.objects.get(id=address_id, user=request.user, is_active=True)
            except Address.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Selected address not found or not available'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get user's cart
            try:
                cart = Cart.objects.get(user=request.user)
            except Cart.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Cart is empty'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            cart_items = cart.items.all()
            if not cart_items.exists():
                return Response({
                    'success': False,
                    'message': 'Cart is empty'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Prepare order data
            order_data = {
                'c2_code': address.pincode[:3],
                'store_id': getattr(request.user.kyc, 'user_id', '00001'),
                'order_id': f"ORD-{uuid.uuid4().hex[:8].upper()}",
                'ip_no': getattr(request.user.kyc, 'user_id', ''),
                'mobile_no': address.phone,
                'patient_name': address.name,
                'patient_address': address.get_full_address(),
                'patient_email': request.user.email,
                'user_id': str(request.user.id),
                'cust_code': getattr(request.user.kyc, 'gst_number', ''),
                'cust_name': address.name,
                'ord_date': timezone.now().date(),
                'ord_time': timezone.now().time(),
                'order_total': 0,
                'sys_name': request.META.get('HTTP_USER_AGENT', 'Web'),
                'sys_ip': get_client_ip(request),
                'sys_user': request.user.username,
                'br_code': '001',
                'tran_year': str(timezone.now().year),
                'tran_prefix': 'ORD',
                'tran_srno': '001',
                'bill_total': 0,
            }
            
            with transaction.atomic():
                # Create sales order with address
                sales_order = SalesOrder.objects.create(
                    **order_data,
                    delivery_address=address
                )
                
                # Add cart items to order
                total_amount = 0
                for idx, cart_item in enumerate(cart_items, 1):
                    item_data = fetch_item_from_erp(cart_item.item.item_code)
                    if not item_data:
                        raise ValueError(f"Item {cart_item.item.item_code} not available in ERP")
                    
                    sale_rate = float(item_data.get('mrp', 0)) * (1 - float(item_data.get('std_disc', 0)) / 100)
                    item_total = sale_rate * cart_item.quantity
                    total_amount += item_total
                    
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        item_seq=idx,
                        item_code=cart_item.item.item_code,
                        item_name=cart_item.item.item_name,
                        batch_no=item_data.get('batch_no'),
                        expiry_date=item_data.get('expiryDate'),
                        total_loose_qty=cart_item.quantity,
                        sale_rate=sale_rate,
                        disc_per=item_data.get('std_disc', 0),
                        item_total=item_total
                    )
                
                # Update order totals
                sales_order.order_total = total_amount
                sales_order.bill_total = total_amount
                sales_order.save()
                
                # Clear cart
                cart.items.all().delete()
                
                logger.info(f"[ORDER_CHECKOUT] User {request.user.username} completed checkout with address ID {address_id}")
                logger.info(f"[ORDER_CREATED] Order {sales_order.order_id} created for {address.name} at {address.get_full_address()}")
                
                return Response({
                    'success': True,
                    'message': 'Order placed successfully',
                    'data': {
                        'order_id': sales_order.order_id,
                        'delivery_address': AddressListSerializer(address).data,
                        'total_amount': float(total_amount),
                        'item_count': len(cart_items)
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"[CHECKOUT_ERROR] Error during checkout for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error completing checkout: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================== GPS LOCATION DETECTION VIEWS ==================

class DetectCurrentLocationView(APIView):
    """Detect user's current location and reverse geocode to address"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Detect location from GPS coordinates and reverse geocode to address
        
        Request body:
        {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accuracy": 10  # meters (optional)
        }
        """
        try:
            serializer = DetectLocationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            latitude = serializer.validated_data['latitude']
            longitude = serializer.validated_data['longitude']
            accuracy = serializer.validated_data.get('accuracy')
            
            # Validate coordinates
            validate_coordinates(latitude, longitude)
            
            # Reverse geocode to get address
            address_data = reverse_geocode(latitude, longitude)
            
            response_serializer = LocationAddressResponseSerializer(address_data)
            logger.info(f"[LOCATION_DETECT] User {request.user.username} detected location at ({latitude}, {longitude})")
            
            return Response({
                'success': True,
                'message': 'Location detected successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except GeocodingException as e:
            logger.warning(f"[LOCATION_ERROR] Geocoding failed for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Could not detect address from location: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"[LOCATION_ERROR] Error detecting location for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error detecting location: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmLocationAddressView(APIView):
    """Confirm detected location and save as address"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Confirm detected location and save as address
        
        Request body:
        {
            "name": "John Doe",
            "phone": "9876543210",
            "city": "Bangalore",
            "state": "Karnataka",
            "locality": "Indiranagar",
            "pincode": "560001",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "location_accuracy": 10,
            "address_type": "HOME",
            "is_default": true,
            "flat_building": "Apt 101"  (optional)
            "landmark": "Near mall"  (optional)
        }
        """
        try:
            serializer = ConfirmLocationAddressSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check for duplicate address
            latitude = serializer.validated_data['latitude']
            longitude = serializer.validated_data['longitude']
            
            existing = Address.objects.filter(
                user=request.user,
                phone=serializer.validated_data['phone'],
                pincode=serializer.validated_data['pincode'],
                latitude=latitude,
                longitude=longitude
            ).first()
            
            if existing:
                return Response({
                    'success': False,
                    'message': 'This address already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save address with GPS data
            address = serializer.save(user=request.user, is_gps_verified=True)
            
            response_serializer = AddressListSerializer(address)
            logger.info(f"[ADDRESS_GPS_SAVE] User {request.user.username} saved GPS-detected address: {address.name} ({latitude}, {longitude})")
            
            return Response({
                'success': True,
                'message': 'Address saved successfully from location',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"[LOCATION_ERROR] Error saving location address for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error saving address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NearbyAddressesView(APIView):
    """Find addresses near current location"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Find user's saved addresses near current location
        
        Request body:
        {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "radius_km": 5  # Search radius in kilometers
        }
        """
        try:
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            radius_km = float(request.data.get('radius_km', 5))
            
            # Validate coordinates
            validate_coordinates(latitude, longitude)
            
            if radius_km <= 0 or radius_km > 50:
                return Response({
                    'success': False,
                    'message': 'Radius must be between 0 and 50 km'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get all user's addresses
            addresses = Address.objects.filter(user=request.user, is_active=True)
            
            # Import geocoding utility
            from .geocoding import calculate_distance
            
            nearby_addresses = []
            for addr in addresses:
                if addr.latitude and addr.longitude:
                    distance = calculate_distance(
                        float(latitude), float(longitude),
                        float(addr.latitude), float(addr.longitude)
                    )
                    if distance <= radius_km:
                        nearby_addresses.append({
                            'address': addr,
                            'distance_km': round(distance, 2)
                        })
            
            # Sort by distance
            nearby_addresses.sort(key=lambda x: x['distance_km'])
            
            data = [
                {
                    **AddressListSerializer(item['address']).data,
                    'distance_km': item['distance_km']
                }
                for item in nearby_addresses
            ]
            
            logger.info(f"[LOCATION_NEARBY] User {request.user.username} found {len(nearby_addresses)} nearby addresses")
            
            return Response({
                'success': True,
                'count': len(nearby_addresses),
                'message': f'Found {len(nearby_addresses)} saved addresses nearby',
                'data': data
            }, status=status.HTTP_200_OK)
            
        except ValueError:
            return Response({
                'success': False,
                'message': 'Coordinates and radius must be numeric'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except GeocodingException as e:
            logger.warning(f"[LOCATION_ERROR] Error in nearby search for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Location error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"[LOCATION_ERROR] Error finding nearby addresses for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error searching nearby addresses: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================== ORDER CONFIRMATION PREVIEW VIEW ==================

class OrderConfirmationPreviewView(APIView):
    """Get order confirmation preview with delivery address before payment"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Get order preview with selected address"""
        try:
            serializer = SelectAddressSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            address_id = serializer.validated_data['address_id']
            
            # Verify address belongs to user
            try:
                address = Address.objects.get(id=address_id, user=request.user, is_active=True)
            except Address.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Selected address not found or not available'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get user's cart
            try:
                cart = Cart.objects.get(user=request.user)
            except Cart.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Cart is empty'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            cart_items = cart.items.all()
            if not cart_items.exists():
                return Response({
                    'success': False,
                    'message': 'Cart is empty'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Prepare items for response
            items_data = []
            for item in cart_items:
                item_data = {
                    'id': item.id,
                    'item_code': item.item.item_code,
                    'item_name': item.item.item_name,
                    'mrp': float(item.item.mrp),
                    'quantity': item.quantity,
                    'discount_percentage': float(item.item.std_disc),
                    'discounted_price': item.get_discounted_price(),
                    'item_total': item.get_item_total_discounted(),
                    'savings': item.get_item_savings()
                }
                items_data.append(item_data)
            
            # Calculate totals
            bag_total = cart.get_bag_total()
            bag_savings = cart.get_bag_savings()
            subtotal = cart.get_subtotal()
            convenience_fee = float(cart.convenience_fee)
            delivery_fee = float(cart.delivery_fee)
            platform_fee = float(cart.platform_fee)
            amount_payable = cart.get_grand_total()
            
            logger.info(f"[CHECKOUT_PREVIEW] User {request.user.username} generated order preview with address ID {address_id}")
            
            return Response({
                'success': True,
                'message': 'Order preview generated successfully',
                'data': {
                    'items': items_data,
                    'delivery_address': AddressListSerializer(address).data,
                    'order_summary': {
                        'bag_total': bag_total,
                        'bag_savings': bag_savings,
                        'subtotal': subtotal,
                        'convenience_fee': convenience_fee,
                        'delivery_fee': delivery_fee,
                        'platform_fee': platform_fee,
                        'amount_payable': amount_payable
                    },
                    'item_count': len(cart_items)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"[PREVIEW_ERROR] Error generating order preview for user {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error generating order preview: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
