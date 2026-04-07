# Related Products API (category-based)

from rest_framework.decorators import api_view
from .serializers import ProductListSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
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
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import FCMDevice

logger = logging.getLogger(__name__)

from .models import CustomUser, KYC, OTP, APIToken, ItemMaster, Stock, GLCustomer, SalesOrder, SalesOrderItem, Invoice, InvoiceDetail, Cart, CartItem, Wishlist, WishlistItem, ProductInfo, ProductImage, Address, Category, ProductView, SearchHistory
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
    CartItemSmallSerializer,
    WishlistSerializer, WishlistItemSerializer, AddToWishlistSerializer, MoveToCartSerializer,
    ProductListSerializer, AddressListSerializer, CreateAddressSerializer,
    SelectAddressSerializer, DetectLocationSerializer, LocationAddressResponseSerializer,
    ConfirmLocationAddressSerializer, UpdateProductInfoRequestSerializer, UploadProductImageRequestSerializer,
    ProductRecommendationSerializer, SimilarProductsResponseSerializer, 
    FrequentlyBoughtTogetherResponseSerializer, TopSellingResponseSerializer, CategoryWithProductsSerializer
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
            # Handle both top-level and nested refresh tokens
            refresh_token = request.data.get("refresh")
            if not refresh_token and "tokens" in request.data:
                refresh_token = request.data["tokens"].get("refresh")
                
            if not refresh_token:
                return Response({
                    "error": "Refresh token is required",
                    "code": "missing_token"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            token = RefreshToken(refresh_token)
            token.blacklist()
            logout(request)
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": "Invalid or expired token",
                "code": "invalid_token",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


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
    ⚠️ DEPRECATED - Use auto-generated token instead!
    
    This endpoint is NO LONGER NEEDED
    Tokens are now automatically generated and cached in the background
    
    All ERP endpoints now use auto-generated tokens transparently
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        return Response({
            'code': '200',
            'type': 'generateToken',
            'message': '⚠️ DEPRECATED: Token generation is now automatic. No manual call needed.',
            'note': 'All ERP endpoints auto-generate tokens in background.',
            'apiKey': 'AUTO_GENERATED_BY_BACKEND'
        }, status=status.HTTP_200_OK)


class GetItemMasterView(APIView):
    """
    Get item master details with product information including images, subheading, and description
    GET: Fetch item details DIRECTLY from ERP test server (real-time data)
    Enhanced with product images, subheading, and description from Django database
    
    URL Patterns:
    - /api/erp/ws_c2_services_get_master_data/                (no user - no wishlist/cart status)
    - /api/erp/ws_c2_services_get_master_data/<user_id>/      (with user - includes wishlist/cart status)
    - /api/erp/ws_c2_services_get_master_data?userId=<id>     (query param - includes wishlist/cart status)
    
    🎯 NEW: Token is now automatically generated in background!
    Frontend doesn't need to provide apiKey - backend handles it automatically
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id=None):
        try:
            # 🎯 Use auto-generated token ONLY - NO apiKey from request accepted
            from .erp_token_service import get_erp_token_for_request
            
            api_key = get_erp_token_for_request()
            if not api_key:
                return Response({
                    'code': '503',
                    'type': 'getMasterData',
                    'message': 'ERP service temporarily unavailable - token generation failed'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            logger.info(f"[GET_ITEM_MASTER] Using auto-generated token")
            
            try:
                # FETCH DIRECTLY FROM ERP SERVER (configurable in settings.py)
                erp_base_url = settings.ERP_BASE_URL
                erp_server_url = f"{erp_base_url}/ws_c2_services_get_master_data"
                
                logger.info(f"[GET_ITEM_MASTER] Fetching from ERP: {erp_server_url}")
                
                erp_response = requests.get(erp_server_url, params={'apiKey': api_key}, timeout=10)
                
                if erp_response.status_code != 200:
                    logger.error(f"ERP Server error: {erp_response.status_code} - {erp_response.text}")
                    return Response({
                        'code': '500',
                        'type': 'getMasterData',
                        'message': f'ERP Server error: {erp_response.text}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                erp_data = erp_response.json()
                items = erp_data.get('data', [])
                
                # Get user from URL param first, then query params, then authenticated user
                user = None
                actual_user_id = user_id
                
                if not actual_user_id:
                    # Try query parameter
                    actual_user_id = request.query_params.get('userId')
                
                if actual_user_id:
                    try:
                        user = CustomUser.objects.get(id=actual_user_id)
                    except CustomUser.DoesNotExist:
                        logger.warning(f"[GET_ITEM_MASTER] User {actual_user_id} not found")
                        pass
                
                # Get cart/wishlist info for user
                user_cart = None
                user_wishlist = None
                
                if user:
                    try:
                        user_cart = Cart.objects.get(user=user)
                    except Cart.DoesNotExist:
                        pass
                    
                    try:
                        user_wishlist = Wishlist.objects.get(user=user)
                    except Wishlist.DoesNotExist:
                        pass
                
                # Enhance each item with product info from Django database
                for item in items:
                    item_code = item.get('c_item_code')
                    
                    # Try to get ProductInfo (images, subheading, description) from database
                    try:
                        item_master = ItemMaster.objects.get(item_code=item_code)
                        product_info = ProductInfo.objects.get(item=item_master)
                        
                        # Add enriched data
                        item['subheading'] = product_info.subheading
                        item['description'] = product_info.description
                        item['type_label'] = product_info.type_label
                        item['brand_id'] = product_info.category.id if product_info.category else None
                        item['brand_name'] = product_info.category.name if product_info.category else ''
                        item['brand_logo'] = request.build_absolute_uri(product_info.category.icon.url) if product_info.category and product_info.category.icon else ''
                        
                        # Add images
                        images = ProductImage.objects.filter(product_info=product_info).order_by('image_order')
                        item['images'] = [
                            {
                                'image': request.build_absolute_uri(img.image.url),
                                'image_order': img.image_order
                            }
                            for img in images
                        ]
                    except (ItemMaster.DoesNotExist, ProductInfo.DoesNotExist):
                        # Item exists in ERP but not in our product info database
                        # That's okay - SUPERADMIN can add product info later
                        item['subheading'] = ''
                        item['description'] = ''
                        item['type_label'] = ''
                        item['brand_id'] = None
                        item['brand_name'] = ''
                        item['brand_logo'] = ''
                        item['images'] = []
                    
                    # Add cart and wishlist status
                    item['cart_status'] = False
                    item['wishlist_status'] = False
                    
                    if user and item_code:
                        try:
                            item_master = ItemMaster.objects.get(item_code=item_code)
                            
                            # Check if item is in cart
                            if user_cart:
                                item['cart_status'] = CartItem.objects.filter(
                                    cart=user_cart,
                                    item=item_master
                                ).exists()
                            
                            # Check if item is in wishlist
                            if user_wishlist:
                                item['wishlist_status'] = WishlistItem.objects.filter(
                                    wishlist=user_wishlist,
                                    item=item_master
                                ).exists()
                        except ItemMaster.DoesNotExist:
                            pass
                
                logger.info(f"[GET_ITEM_MASTER] Fetched {len(items)} items from ERP server with product enhancements")
                
                return Response({
                    'code': '200',
                    'type': 'getMasterData',
                    'data': items,
                    'message': f'Fetched {len(items)} items from ERP server'
                }, status=status.HTTP_200_OK)
            
            except requests.exceptions.ConnectionError:
                return Response({
                    'code': '503',
                    'type': 'getMasterData',
                    'message': 'ERP Server is not reachable. Make sure erp_test_server.py is running on port 44000'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception as e:
                logger.error(f"Error fetching from ERP server: {str(e)}")
                return Response({
                    'code': '500',
                    'type': 'getMasterData',
                    'message': f'Error: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error in GetItemMasterView: {str(e)}")
            return Response({
                'code': '500',
                'type': 'getMasterData',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateProductInfoView(APIView):
    """
    Update product information (subheading, description, and images)
    POST/PUT: Update product info and upload images for an item
    SUPERADMIN ONLY - Add product details through mobile app
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user is SUPERADMIN
        if getattr(request.user, 'role', None) != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'updateProductInfo',
                'message': 'Forbidden - Only SUPERADMIN can update product information'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UpdateProductInfoRequestSerializer(data=request.data)
        if serializer.is_valid():
            item_code = serializer.validated_data['c_item_code']
            subheading = serializer.validated_data.get('subheading', '')
            description = serializer.validated_data.get('description', '')
            type_label = serializer.validated_data.get('type_label', '')
            
            # Get images if provided
            images = {
                1: serializer.validated_data.get('image_1'),
                2: serializer.validated_data.get('image_2'),
                3: serializer.validated_data.get('image_3'),
            }
            
            try:
                # Get the item
                item = ItemMaster.objects.get(item_code=item_code)
                
                # Get or create ProductInfo
                product_info, created = ProductInfo.objects.get_or_create(
                    item=item
                )
                
                # Update ProductInfo fields
                product_info.subheading = subheading
                product_info.description = description
                product_info.type_label = type_label
                product_info.save()
                
                # Audit log
                logger.info(f"[PRODUCT_INFO_UPDATED] Item: {item_code} | Subheading: {subheading} | Description: {description} | Type Label: {type_label} | Updated by: {request.user.username}")
                
                # Handle image uploads
                uploaded_images = []
                for image_order in [1, 2, 3]:
                    image_file = images.get(image_order)
                    if image_file:
                        try:
                            # Check if image with same order already exists
                            existing_image = ProductImage.objects.filter(
                                product_info=product_info,
                                image_order=image_order
                            ).first()
                            
                            if existing_image:
                                # Update existing image
                                existing_image.image = image_file
                                existing_image.save()
                                image_url = request.build_absolute_uri(existing_image.image.url)
                                uploaded_images.append({
                                    'image_order': image_order,
                                    'status': 'updated',
                                    'image': image_url
                                })
                                logger.info(f"[PRODUCT_IMAGE_UPDATED] Item: {item_code} | Order: {image_order} | Updated by: {request.user.username}")
                            else:
                                # Create new image
                                product_image = ProductImage.objects.create(
                                    product_info=product_info,
                                    image=image_file,
                                    image_order=image_order
                                )
                                image_url = request.build_absolute_uri(product_image.image.url)
                                uploaded_images.append({
                                    'image_order': image_order,
                                    'status': 'uploaded',
                                    'image': image_url
                                })
                                logger.info(f"[PRODUCT_IMAGE_CREATED] Item: {item_code} | Order: {image_order} | Created by: {request.user.username}")
                        except Exception as img_error:
                            logger.error(f"Error uploading image {image_order}: {str(img_error)}")
                            uploaded_images.append({
                                'image_order': image_order,
                                'status': 'error',
                                'error': str(img_error)
                            })
                
                return Response({
                    'code': '200',
                    'type': 'updateProductInfo',
                    'message': 'Product info updated successfully',
                    'data': {
                        'c_item_code': item_code,
                        'subheading': product_info.subheading,
                        'description': product_info.description,
                        'type_label': product_info.type_label,
                        'brand_id': product_info.category.id if product_info.category else None,
                        'brand_name': product_info.category.name if product_info.category else '',
                        'brand_logo': request.build_absolute_uri(product_info.category.icon.url) if product_info.category and product_info.category.icon else '',
                        'images': uploaded_images
                    }
                }, status=status.HTTP_200_OK)
            
            except ItemMaster.DoesNotExist:
                return Response({
                    'code': '404',
                    'type': 'updateProductInfo',
                    'message': f'Item with code {item_code} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Error updating product info: {str(e)}")
                return Response({
                    'code': '500',
                    'type': 'updateProductInfo',
                    'message': f'Error updating product info: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'updateProductInfo',
            'message': 'Invalid parameters',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        """PUT method - same as POST for updating product information"""
        return self.post(request)





class UploadProductImageView(APIView):
    """
    Upload product images
    POST/PUT: Upload image for a product
    SUPERADMIN ONLY - Add product images through mobile app
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user is SUPERADMIN
        if getattr(request.user, 'role', None) != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'uploadProductImage',
                'message': 'Forbidden - Only SUPERADMIN can upload product images'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UploadProductImageRequestSerializer(data=request.data)
        if serializer.is_valid():
            item_code = serializer.validated_data['c_item_code']
            image = serializer.validated_data['image']
            image_order = serializer.validated_data.get('image_order', 1)
            
            try:
                # Get the item
                item = ItemMaster.objects.get(item_code=item_code)
                
                # Get or create ProductInfo
                product_info, _ = ProductInfo.objects.get_or_create(item=item)
                
                # Check if image with same order already exists
                existing_image = ProductImage.objects.filter(
                    product_info=product_info,
                    image_order=image_order
                ).first()
                
                if existing_image:
                    # Update existing image
                    existing_image.image = image
                    existing_image.save()
                    action = 'updated'
                    logger.info(f"[PRODUCT_IMAGE_UPDATED] Item: {item_code} | Order: {image_order} | Updated by: {request.user.username}")
                else:
                    # Create new image
                    ProductImage.objects.create(
                        product_info=product_info,
                        image=image,
                        image_order=image_order
                    )
                    action = 'uploaded'
                    logger.info(f"[PRODUCT_IMAGE_CREATED] Item: {item_code} | Order: {image_order} | Created by: {request.user.username}")
                
                return Response({
                    'code': '200',
                    'type': 'uploadProductImage',
                    'message': f'Product image {action} successfully',
                    'data': {
                        'c_item_code': item_code,
                        'image_order': image_order,
                        'status': action
                    }
                }, status=status.HTTP_200_OK)
            
            except ItemMaster.DoesNotExist:
                return Response({
                    'code': '404',
                    'type': 'uploadProductImage',
                    'message': f'Item with code {item_code} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Error uploading product image: {str(e)}")
                return Response({
                    'code': '500',
                    'type': 'uploadProductImage',
                    'message': f'Error uploading product image: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'uploadProductImage',
            'message': 'Invalid parameters',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        """PUT method - same as POST for uploading product images"""
        return self.post(request)


class FetchStockView(APIView):
    """
    Fetch real-time stock details from ERP server
    GET: Get stock information directly from ERP (real-time data)
    
    🎯 NEW: Token is now automatically generated in background!
    Frontend doesn't need to provide apiKey - backend handles it automatically
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # 🎯 Use auto-generated token ONLY - NO apiKey from request accepted
            from .erp_token_service import get_erp_token_for_request
            
            api_key = get_erp_token_for_request()
            if not api_key:
                return Response({
                    'code': '503',
                    'type': 'fetchStock',
                    'message': 'ERP service temporarily unavailable - token generation failed'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            logger.info(f"[FETCH_STOCK] Using auto-generated token")
            
            store_id = request.query_params.get('storeId')
            
            try:
                # FETCH DIRECTLY FROM ERP SERVER (real-time stock data)
                erp_base_url = settings.ERP_BASE_URL
                erp_server_url = f"{erp_base_url}/ws_c2_services_fetch_stock"
                
                logger.info(f"[FETCH_STOCK] Fetching from ERP: {erp_server_url}")
                
                # Build ERP request parameters
                erp_params = {'apiKey': api_key}
                if store_id:
                    erp_params['storeId'] = store_id
                
                erp_response = requests.get(erp_server_url, params=erp_params, timeout=10)
                
                if erp_response.status_code != 200:
                    logger.error(f"ERP Server error: {erp_response.status_code} - {erp_response.text}")
                    return Response({
                        'code': '500',
                        'type': 'fetchStock',
                        'message': f'ERP Server error: {erp_response.text}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                erp_data = erp_response.json()
                # Handle both dict with 'data' key and direct list responses from ERP
                if isinstance(erp_data, dict):
                    stock_items = erp_data.get('data', [])
                elif isinstance(erp_data, list):
                    stock_items = erp_data
                else:
                    stock_items = []
                
                logger.info(f"[FETCH_STOCK] Fetched {len(stock_items)} stock items from ERP server")
                
                return Response({
                    'code': '200',
                    'type': 'fetchStock',
                    'data': stock_items,
                    'message': f'Fetched {len(stock_items)} stock items from ERP server'
                }, status=status.HTTP_200_OK)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"[FETCH_STOCK] Error connecting to ERP: {str(e)}")
                return Response({
                    'code': '500',
                    'type': 'fetchStock',
                    'message': f'Error connecting to ERP server: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"[FETCH_STOCK] Error in get request: {str(e)}")
            return Response({
                'code': '500',
                'type': 'fetchStock',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateSalesOrderView(APIView):
    """
    Create a sales order in the system
    POST: Create sales order with line items
    
    🎯 Token auto-generated in background - NO apiKey needed in request!
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CreateSalesOrderRequestSerializer(data=request.data)
        if serializer.is_valid():
            # 🎯 Use auto-generated token from background service
            from .erp_token_service import get_erp_token_for_request
            api_key = get_erp_token_for_request()
            if not api_key:
                return Response({
                    'code': '503',
                    'type': 'SaleOrderCreate',
                    'message': 'ERP service temporarily unavailable'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            try:
                # ✅ FIX #5: ATOMIC TRANSACTION - Prevents race conditions and ensures data consistency
                with transaction.atomic():
                    # ✅ AUTO-GENERATE UNIQUE ORDER ID (Always - Backend Responsibility)
                    # Format: {storeId}{YYYYMMDD}{HHMMSS}{UUID}
                    # Example: 001202604051430AB12CD34
                    store_id = serializer.validated_data['storeId'].zfill(3)  # Pad to 3 digits
                    date_str = timezone.now().strftime('%Y%m%d')
                    time_str = timezone.now().strftime('%H%M%S')
                    unique_suffix = str(uuid.uuid4())[:8].upper()
                    order_id = f"{store_id}{date_str}{time_str}{unique_suffix}"
                    logger.info(f"[ORDER_ID] Auto-generated orderId: {order_id} | StoreId: {store_id}")
                    
                    # Create sales order with duplicate ID check
                    from django.db import IntegrityError
                    try:
                        sales_order = SalesOrder.objects.create(
                            c2_code=serializer.validated_data['c2Code'],
                            store_id=serializer.validated_data['storeId'],
                            order_id=order_id,
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
                    except IntegrityError as e:
                        # ✅ FIX #5: Handle duplicate order ID (race condition - extremely rare)
                        logger.error(f"[ORDER_DUPLICATE] Rare race condition - Duplicate orderId {order_id} | Error: {str(e)}")
                        # Retry with new timestamp
                        time_str_retry = timezone.now().strftime('%H%M%S%f')[:6]  # Include microseconds
                        unique_suffix_retry = str(uuid.uuid4())[:8].upper()
                        order_id_retry = f"{store_id}{date_str}{time_str_retry}{unique_suffix_retry}"
                        logger.info(f"[ORDER_RETRY] Retrying with new orderId: {order_id_retry}")
                        
                        try:
                            sales_order = SalesOrder.objects.create(
                                c2_code=serializer.validated_data['c2Code'],
                                store_id=serializer.validated_data['storeId'],
                                order_id=order_id_retry,
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
                            order_id = order_id_retry  # Update for logging
                        except IntegrityError as e2:
                            logger.error(f"[ORDER_CREATION_FAILED] Failed even after retry | Error: {str(e2)}")
                            return Response({
                                'code': '500',
                                'type': 'SaleOrderCreate',
                                'message': 'Failed to create order after multiple retries. Please contact support.'
                            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
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
    
    🎯 Token auto-generated in background - NO apiKey needed in request!
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CreateGLCustomerRequestSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data['Code']
            
            # 🎯 Use auto-generated token from background service
            from .erp_token_service import get_erp_token_for_request
            api_key = get_erp_token_for_request()
            if not api_key:
                return Response({
                    'code': '503',
                    'type': 'glcustcreation',
                    'message': 'ERP service temporarily unavailable'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
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
    
    🎯 Token auto-generated in background - NO apiKey needed in request!
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Parse request parameters
        c2_code = request.query_params.get('c2Code')
        store_id = request.query_params.get('storeId')
        order_id = request.query_params.get('orderId')
        
        if not all([c2_code, store_id, order_id]):
            return Response({
                'code': '400',
                'message': 'Missing required parameters (c2Code, storeId, orderId)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 🎯 Use auto-generated token from background service
        from .erp_token_service import get_erp_token_for_request
        api_key = get_erp_token_for_request()
        if not api_key:
            return Response({
                'code': '503',
                'message': 'ERP service temporarily unavailable'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
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
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        cart, created = Cart.objects.get_or_create(user=user)
        serializer = CartSerializer(cart)
        
        # Fetch fresh stock status for each item
        # [UPDATED] Token now auto-generated - no need for apiKey from request
        cart_data = serializer.data
        
        for item in cart_data.get('items', []):
            item_code = item.get('itemCode')
            stock_status = get_item_stock_status(item_code)
            item['availability'] = stock_status.get('status', 'Unknown')
            item['available_qty'] = stock_status.get('qty', 0)
            item['in_stock'] = stock_status.get('available', False)
            item['current_price'] = str(round(stock_status.get('price', float(item.get('mrp', 0))), 2))
            item['current_discount'] = round(stock_status.get('discount', 0), 2)
        
        return Response({
            'success': True,
            'message': 'Cart retrieved successfully',
            'data': cart_data
        }, status=status.HTTP_200_OK)
    
    def delete(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            cart = Cart.objects.get(user=user)
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
        # [UPDATED] Token now auto-generated - no need for apiKey from request
        
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
                # ✅ FIX #5: LOCK Stock record to prevent concurrent writes
                # select_for_update() locks the row at DB level during the transaction
                try:
                    stock_record = Stock.objects.select_for_update().get(item__item_code=item_code)
                except Stock.DoesNotExist:
                    stock_record = None
                
                # Fetch fresh item details from ERP - REQUIRED, no fallback
                item_data = fetch_item_from_erp(item_code)
                
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
                stock_status = get_item_stock_status(item_code)
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
                
                # Get or create cart (also locked within transaction)
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
                
                item_serializer = CartItemSmallSerializer(cart_item)
                item_data = item_serializer.data
                
                # Add stock status to response
                stock_status = get_item_stock_status(item_code)
                item_data['availability'] = stock_status.get('status', 'Unknown')
                item_data['available_qty'] = stock_status.get('qty', 0)
                item_data['in_stock'] = stock_status.get('available', False)
                item_data['current_price'] = str(round(stock_status.get('price', float(item_data.get('mrp', 0))), 2))
                item_data['current_discount'] = round(stock_status.get('discount', 0), 2)
                
                return Response({
                    'success': True,
                    'message': f'{item.item_name} added to cart' if created else f'{item.item_name} quantity updated',
                    'data': item_data
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
    Query params: user_id (required)
    """
    permission_classes = [AllowAny]
    
    def put(self, request, item_id):
        # Get user_id from query params
        user_id = request.query_params.get('userId')
        if not user_id:
            return Response({
                'success': False,
                'message': 'userId query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = Cart.objects.get(user=user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.quantity = serializer.validated_data['quantity']
            cart_item.save()
            
            item_serializer = CartItemSmallSerializer(cart_item)
            item_data = item_serializer.data
            
            # Add stock status to response
            item_code = cart_item.item.item_code
            stock_status = get_item_stock_status(item_code)
            item_data['availability'] = stock_status.get('status', 'Unknown')
            item_data['available_qty'] = stock_status.get('qty', 0)
            item_data['in_stock'] = stock_status.get('available', False)
            item_data['current_price'] = str(round(stock_status.get('price', float(item_data.get('mrp', 0))), 2))
            item_data['current_discount'] = round(stock_status.get('discount', 0), 2)
            
            return Response({
                'success': True,
                'message': 'Cart item updated successfully',
                'data': item_data
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
        # Get user_id from query params
        user_id = request.query_params.get('userId')
        if not user_id:
            return Response({
                'success': False,
                'message': 'userId query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            cart = Cart.objects.get(user=user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            item_name = cart_item.item.item_name
            item_id_val = cart_item.id
            cart_item.delete()
            
            return Response({
                'success': True,
                'message': f'{item_name} removed from cart',
                'data': {
                    'id': item_id_val,
                    'itemName': item_name
                }
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
        Query param: user_id (required)
        """
        from .models import Wishlist, WishlistItem
        
        # Get user_id from query params
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({
                'success': False,
                'message': 'user_id query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user from database
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
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
            wishlist = Wishlist.objects.get(user=user)
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
            logger.info(f"[WISHLIST_UPDATE] User: {user.id} ({user.username}) | WishlistItem: {item_id} | Quantity: {quantity}")
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
    
    def get(self, request, user_id=None):
        # Get user_id from URL path or query params
        if not user_id:
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
        
        # Use WishlistItemSerializer instead of manual serialization
        from .serializers import WishlistItemSerializer
        items_serializer = WishlistItemSerializer(wishlist.items.all(), many=True, context={'request': request})
        
        wishlist_data = {
            'id': wishlist.id,
            'user': wishlist.user.id,
            'items': items_serializer.data
        }
        
        # If wishlist is empty, return success with empty message
        message = 'Wishlist retrieved successfully' if wishlist_data['items'] else 'Wishlist is empty'
        
        return Response({
            'success': True,
            'message': message,
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
    
    def post(self, request, user_id):
        from django.db import transaction
        
        # ✅ FIX: Get user from database instead of request.user
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddToWishlistSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item_code = serializer.validated_data['itemCode']
        # [UPDATED] Token now auto-generated - no need for apiKey from request
        
        # ✅ FIX #3: ATOMIC TRANSACTION - Prevents race conditions
        try:
            with transaction.atomic():
                # Fetch fresh item details from ERP - REQUIRED, no fallback
                item_data = fetch_item_from_erp(item_code)
                
                if not item_data:
                    return Response({
                        'success': False,
                        'message': 'ERP service temporarily unavailable. Please try again.'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
                # Check stock availability BEFORE adding to wishlist
                stock_status = get_item_stock_status(item_code)
                if not stock_status['available']:
                    logger.warning(f"User {user_id} tried to wishlist unavailable item {item_code} - Status: {stock_status['status']}")
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
                
                # Get or create wishlist for the user
                wishlist, _ = Wishlist.objects.get_or_create(user=user)
                
                # Check if item already in wishlist
                wishlist_item, created = WishlistItem.objects.get_or_create(
                    wishlist=wishlist,
                    item=item,
                    defaults={'quantity': 1}
                )
                if not created:
                    wishlist_item.quantity += 1
                    wishlist_item.save()
                    logger.info(f"[WISHLIST_UPDATE] User: {user.id} ({user.username}) | Item: {item_code} | Quantity now: {wishlist_item.quantity}")
                    # Serialize just the updated item with ProductInfo data
                    item_serializer = WishlistItemSerializer(wishlist_item, context={'request': request})
                    return Response({
                        'success': True,
                        'message': f'{item.item_name} quantity increased to {wishlist_item.quantity}',
                        'data': item_serializer.data
                    }, status=status.HTTP_200_OK)
                
                # ✅ FIX #4: AUDIT LOGGING
                logger.info(f"[WISHLIST_ADD] User: {user.id} ({user.username}) | Item: {item_code}")
                
                # Serialize just the added item with ProductInfo data
                item_serializer = WishlistItemSerializer(wishlist_item, context={'request': request})
                return Response({
                    'success': True,
                    'message': f'{item.item_name} added to wishlist',
                    'data': item_serializer.data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"[WISHLIST_ERROR] User: {user_id} | Item: {item_code} | Error: {str(e)}", exc_info=True)
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
        cart_data = cart_serializer.data
        
        # Fetch fresh stock status for each item
        for item in cart_data.get('items', []):
            item_code = item.get('itemCode')
            stock_status = get_item_stock_status(item_code)
            item['availability'] = stock_status.get('status', 'Unknown')
            item['available_qty'] = stock_status.get('qty', 0)
            item['in_stock'] = stock_status.get('available', False)
            item['current_price'] = str(round(stock_status.get('price', float(item.get('mrp', 0))), 2))
            item['current_discount'] = round(stock_status.get('discount', 0), 2)
        
        return Response({
            'success': True,
            'message': f'{item.item_name} moved to cart',
            'data': {
                'cart': cart_data
            }
        }, status=status.HTTP_200_OK)


# ==================== PRODUCTS VIEW ====================

class AllProductsView(APIView):
    """
    Get all products with optional search and ERP enrichment
    GET: Retrieve all products with optional search
    
    Query Parameters:
        - search: Search by product name (optional)
        - limit: Max results to return (default: 50)
        - apiKey: Optional ERP API key for live data enrichment
    
    Data Sources:
        - Without apiKey: Database only (local cache)
        - With apiKey: ERP live data (pricing, stock, expiry, batches)
    
    Example: /api/products/?search=paracetamol&limit=20&apiKey=YOUR_KEY
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            search = request.query_params.get('search')
            limit = int(request.query_params.get('limit', 50))
            
            # [UPDATED] Always use auto-generated token - try ERP first
            logger.info(f"[PRODUCTS] Fetching from ERP with auto-generated token")
            erp_items = fetch_all_items_from_erp()
            
            if erp_items:
                # Filter by search if provided
                if search:
                    search_lower = search.lower()
                    erp_items = [
                        item for item in erp_items
                        if search_lower in item.get('itemName', '').lower()
                    ]
                
                # Limit results
                erp_items = erp_items[:limit]
                
                # Format response
                products = []
                for item in erp_items:
                    mrp = float(item.get('mrp', 0))
                    discount = float(item.get('std_disc', 0))
                    discounted = mrp * (1 - discount / 100) if mrp > 0 else 0
                    
                    products.append({
                        'c_item_code': item.get('c_item_code'),
                        'itemName': item.get('itemName'),
                        'itemQtyPerBox': item.get('itemQtyPerBox'),
                        'batchNo': item.get('batchNo'),
                        'mrp': mrp,
                        'std_disc': discount,
                        'max_disc': float(item.get('max_disc', 0)),
                        'discountedPrice': round(discounted, 2),
                        'stockBalQty': item.get('stockBalQty', 0),
                        'expiryDate': item.get('expiryDate'),
                        'source': 'erp'
                    })
                
                logger.info(f"[PRODUCTS] Retrieved {len(products)} products from ERP | Source: ERP")
                
                return Response({
                    'success': True,
                    'message': f'Found {len(products)} products from ERP',
                    'data': products,
                    'count': len(products),
                    'source': 'erp',
                    'lastFetched': timezone.now().isoformat()
                }, status=status.HTTP_200_OK)
            
            # [FALLBACK] Fetch from database if ERP not available
            logger.info(f"[PRODUCTS] ERP unavailable, falling back to database")
            product_infos = ProductInfo.objects.select_related('item', 'category')
            
            # Search by product name if provided
            if search:
                product_infos = product_infos.filter(item__item_name__icontains=search)
            
            # Limit results
            product_infos = product_infos[:limit]
            
            products = []
            for product_info in product_infos:
                item = product_info.item
                mrp = float(item.mrp)
                discount = float(item.std_disc)
                discounted = mrp * (1 - discount / 100)
                
                # Get first product image
                product_images = ProductImage.objects.filter(product_info=product_info).first()
                product_image_url = None
                if product_images:
                    product_image_url = request.build_absolute_uri(product_images.image.url)
                
                # Get stock quantity
                stock_qty = 0
                try:
                    stock = Stock.objects.filter(item=item).first()
                    if stock:
                        stock_qty = stock.total_bal_ls_qty
                except:
                    stock_qty = 0
                
                products.append({
                    'c_item_code': item.item_code,
                    'itemName': item.item_name,
                    'itemQtyPerBox': item.item_qty_per_box,
                    'batchNo': item.batch_no,
                    'mrp': float(item.mrp),
                    'std_disc': float(item.std_disc),
                    'max_disc': float(item.max_disc),
                    'discountedPrice': round(discounted, 2),
                    'stockBalQty': stock_qty,
                    'expiryDate': str(item.expiry_date) if item.expiry_date else None,
                    'description': product_info.description or '',
                    'type_label': product_info.type_label or '',
                    'category': product_info.category.name if product_info.category else None,
                    'productImage': product_image_url,
                    'source': 'database'
                })
            
            logger.info(f"[PRODUCTS] Retrieved {len(products)} products from database | Source: Database")
            
            return Response({
                'success': True,
                'message': f'Found {len(products)} products',
                'data': products,
                'count': len(products),
                'source': 'database',
                'hint': 'Use ?apiKey=YOUR_KEY to fetch live ERP data'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[PRODUCTS_ERROR] Error retrieving products: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error retrieving products: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SearchProductsView(APIView):
    """
    Search products by name, category, and keywords
    GET: Search for products matching the query
    
    URL Parameters:
        - user_id: The ID of the user performing the search
    
    Query Parameters:
        - q or search: Search keyword (required)
        - category: Filter by category ID (optional)
        - limit: Max results to return (default: 20)
        - apiKey: Optional ERP API key for live data enrichment
    
    Data Sources:
        - Without apiKey: Database only (stockBalQty from Stock table)
        - With apiKey: ERP live data (pricing, stock, expiry)
    
    Example: /api/search/88/?q=paracetamol&limit=10&apiKey=YOUR_KEY
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            # Get search query from params
            query = request.query_params.get('q') or request.query_params.get('search')
            category_id = request.query_params.get('category')
            limit = int(request.query_params.get('limit', 20))
            
            if not query:
                return Response({
                    'success': False,
                    'message': 'Search query parameter "q" or "search" is required',
                    'example': '/api/search/?q=paracetamol'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Clean and validate query
            query = query.strip()
            if len(query) < 2:
                return Response({
                    'success': False,
                    'message': 'Search query must be at least 2 characters'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # [UPDATED] Fetch ERP data with auto-generated token
            erp_map = {}
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            if erp_map:
                logger.info(f"[SEARCH] Fetched {len(erp_map)} items from ERP with auto-token")
            
            # Start with product infos
            from django.db.models import Q
            product_infos = ProductInfo.objects.select_related('item', 'category').filter(
                Q(item__item_name__icontains=query) |  # Search in product name
                Q(description__icontains=query) |      # Search in description
                Q(type_label__icontains=query) |       # Search in type (Tablet, Injection, etc)
                Q(category__name__icontains=query)     # Search in category/brand name
            ).distinct()
            
            # Filter by category if provided
            if category_id:
                try:
                    category_id = int(category_id)
                    product_infos = product_infos.filter(category_id=category_id)
                except ValueError:
                    pass
            
            # Limit results
            product_infos = product_infos[:limit]
            
            if not product_infos.exists():
                logger.info(f"[SEARCH] No products found for query: '{query}'")
                return Response({
                    'success': True,
                    'message': 'No products found',
                    'query': query,
                    'count': 0,
                    'data': []
                }, status=status.HTTP_200_OK)
            
            # Serialize products
            products = []
            for product_info in product_infos:
                item = product_info.item
                
                # Check for ERP enrichment
                erp_data = erp_map.get(item.item_code)
                if erp_data:
                    # Enrich with ERP data
                    item.item_code = erp_data.get('c_item_code', item.item_code)
                    item.item_name = erp_data.get('itemName', item.item_name)
                    item.batch_no = erp_data.get('batchNo', item.batch_no)
                    item.item_qty_per_box = erp_data.get('itemQtyPerBox', item.item_qty_per_box)
                    item.mrp = float(erp_data.get('mrp', item.mrp))
                    item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                    item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                    item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    item.erp_stock = erp_data.get('stockBalQty', 0)
                
                mrp = float(item.mrp)
                discount = float(item.std_disc)
                discounted_price = mrp * (1 - discount / 100)
                
                # Get all product images (ordered by image_order)
                product_images = ProductImage.objects.filter(product_info=product_info).order_by('image_order')
                images_list = [
                    {
                        'image': request.build_absolute_uri(img.image.url),
                        'image_order': img.image_order
                    }
                    for img in product_images
                ]
                
                # Get stock quantity (ERP first, then database)
                stock_qty = 0
                if hasattr(item, 'erp_stock') and item.erp_stock is not None:
                    stock_qty = item.erp_stock  # ← From ERP
                else:
                    try:
                        from .models import Stock
                        stock = Stock.objects.filter(item=item).first()
                        if stock:
                            stock_qty = stock.total_bal_ls_qty  # ← From DB
                    except:
                        stock_qty = 0
                
                # Check if item is in user's cart
                cart_status = False
                wishlist_status = False
                if request.user.is_authenticated:
                    try:
                        from .models import CartItem, WishlistItem
                        cart_status = CartItem.objects.filter(
                            cart__user=request.user,
                            product_info=product_info
                        ).exists()
                        wishlist_status = WishlistItem.objects.filter(
                            wishlist__user=request.user,
                            product_info=product_info
                        ).exists()
                    except:
                        pass
                
                # Get brand logo
                brand_logo = ''
                if product_info.category and product_info.category.icon:
                    brand_logo = request.build_absolute_uri(product_info.category.icon.url)
                
                products.append({
                    'batchNo': item.batch_no or '',
                    'c_item_code': item.item_code,
                    'expiryDate': str(item.expiry_date) if item.expiry_date else None,
                    'itemName': item.item_name,
                    'itemQtyPerBox': item.item_qty_per_box,
                    'max_disc': float(item.max_disc),
                    'mrp': float(item.mrp),
                    'std_disc': float(item.std_disc),
                    'stockBalQty': stock_qty,
                    'subheading': product_info.subheading or '',
                    'description': product_info.description or '',
                    'type_label': product_info.type_label or '',
                    'brand_id': product_info.category.id if product_info.category else None,
                    'brand_name': product_info.category.name if product_info.category else '',
                    'brand_logo': brand_logo,
                    'images': images_list,
                    'cart_status': cart_status,
                    'wishlist_status': wishlist_status
                })
            
            logger.info(f"[SEARCH] Found {len(products)} products for query: '{query}' | Source: ERP (auto-token)")
            
            # Log search for popular search tracking
            try:
                from .models import SearchHistory
                user = request.user if request.user.is_authenticated else None
                search_history, created = SearchHistory.objects.get_or_create(
                    query=query,
                    defaults={'user': user}
                )
                if not created:
                    search_history.search_count += 1
                    search_history.updated_at = timezone.now()
                    search_history.save()
                logger.info(f"[SEARCH_LOG] Query logged: '{query}' | Count: {search_history.search_count}")
            except Exception as e:
                logger.warning(f"[SEARCH_LOG_ERROR] Failed to log search: {str(e)}")
            
            # ✅ Track product views for recently viewed feature
            try:
                if user_id:  # Only track if user_id provided
                    for product_info in product_infos:
                        ProductView.objects.update_or_create(
                            user_id=user_id,
                            item=product_info.item,
                            defaults={'viewed_at': timezone.now()}
                        )
                    logger.info(f"[PRODUCT_VIEW] Tracked {len(product_infos)} product views for user {user_id}")
            except Exception as e:
                logger.warning(f"[PRODUCT_VIEW_ERROR] Failed to track product views: {str(e)}")
            
            return Response({
                'success': True,
                'message': f'Found {len(products)} products',
                'query': query,
                'count': len(products),
                'data': products,
                'source': 'erp'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[SEARCH_ERROR] Error searching products: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error searching products: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PopularSearchView(APIView):
    """
    Get popular/frequently searched keywords with products
    GET: Retrieve top searched keywords with detailed product information
    
    Query Parameters:
        - limit: Max results to return (default: 10)
        - apiKey: Optional ERP API key for live data enrichment
    
    Data Sources:
        - Without apiKey: Database only (stockBalQty from Stock table)
        - With apiKey: ERP live data (pricing, stock, expiry)
    
    Example: /api/search/popular/?limit=10&apiKey=YOUR_KEY
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
            
            # Import SearchHistory model
            from .models import SearchHistory
            from django.db.models import Q
            
            # Get top searched queries
            popular_searches = SearchHistory.objects.all().order_by('-search_count')[:limit]
            
            if not popular_searches.exists():
                logger.info("[POPULAR_SEARCH] No search history available")
                return Response({
                    'success': True,
                    'message': 'No popular searches available',
                    'count': 0,
                    'data': []
                }, status=status.HTTP_200_OK)
            
            # [UPDATED] Fetch ERP data with auto-generated token
            erp_map = {}
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            if erp_map:
                logger.info(f"[POPULAR_SEARCH] Fetched {len(erp_map)} items from ERP with auto-token")
            
            # Serialize popular searches with products
            searches = []
            for search in popular_searches:
                query = search.query
                
                # Get products matching this popular search query
                product_infos = ProductInfo.objects.select_related('item', 'category').filter(
                    Q(item__item_name__icontains=query) |
                    Q(description__icontains=query) |
                    Q(type_label__icontains=query) |
                    Q(category__name__icontains=query)
                ).distinct()[:20]  # Limit to 20 products per search
                
                # Serialize products
                products = []
                for product_info in product_infos:
                    item = product_info.item
                    
                    # Check for ERP enrichment
                    erp_data = erp_map.get(item.item_code)
                    if erp_data:
                        # Enrich with ERP data (complete product info)
                        item.item_code = erp_data.get('c_item_code', item.item_code)
                        item.item_name = erp_data.get('itemName', item.item_name)
                        item.batch_no = erp_data.get('batchNo', item.batch_no)
                        item.item_qty_per_box = erp_data.get('itemQtyPerBox', item.item_qty_per_box)
                        item.mrp = float(erp_data.get('mrp', item.mrp))
                        item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                        item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                        item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                        item.erp_stock = erp_data.get('stockBalQty', 0)
                    
                    mrp = float(item.mrp)
                    discount = float(item.std_disc)
                    discounted_price = mrp * (1 - discount / 100)
                    
                    # Get all product images
                    product_images = ProductImage.objects.filter(product_info=product_info).order_by('image_order')
                    images_list = [
                        {
                            'image': request.build_absolute_uri(img.image.url),
                            'image_order': img.image_order
                        }
                        for img in product_images
                    ]
                    
                    # Get stock quantity (ERP first, then database)
                    stock_qty = 0
                    if hasattr(item, 'erp_stock') and item.erp_stock is not None:
                        stock_qty = item.erp_stock  # ← From ERP
                    else:
                        try:
                            from .models import Stock
                            stock = Stock.objects.filter(item=item).first()
                            if stock:
                                stock_qty = stock.total_bal_ls_qty  # ← From DB
                        except:
                            stock_qty = 0
                    
                    # Check cart and wishlist status
                    cart_status = False
                    wishlist_status = False
                    if request.user.is_authenticated:
                        try:
                            from .models import CartItem, WishlistItem
                            cart_status = CartItem.objects.filter(
                                cart__user=request.user,
                                product_info=product_info
                            ).exists()
                            wishlist_status = WishlistItem.objects.filter(
                                wishlist__user=request.user,
                                product_info=product_info
                            ).exists()
                        except:
                            pass
                    
                    # Get brand logo
                    brand_logo = ''
                    if product_info.category and product_info.category.icon:
                        brand_logo = request.build_absolute_uri(product_info.category.icon.url)
                    
                    products.append({
                        'batchNo': item.batch_no or '',
                        'c_item_code': item.item_code,
                        'expiryDate': str(item.expiry_date) if item.expiry_date else None,
                        'itemName': item.item_name,
                        'itemQtyPerBox': item.item_qty_per_box,
                        'max_disc': float(item.max_disc),
                        'mrp': float(item.mrp),
                        'std_disc': float(item.std_disc),
                        'stockBalQty': stock_qty,
                        'subheading': product_info.subheading or '',
                        'description': product_info.description or '',
                        'type_label': product_info.type_label or '',
                        'brand_id': product_info.category.id if product_info.category else None,
                        'brand_name': product_info.category.name if product_info.category else '',
                        'brand_logo': brand_logo,
                        'images': images_list,
                        'cart_status': cart_status,
                        'wishlist_status': wishlist_status
                    })
                
                searches.append({
                    'query': query,
                    'searchCount': search.search_count,
                    'lastSearched': search.updated_at.isoformat(),
                    'products': products
                })
            
            logger.info(f"[POPULAR_SEARCH] Retrieved {len(searches)} popular searches with products | Source: ERP (auto-token)")
            
            return Response({
                'success': True,
                'message': f'Found {len(searches)} popular searches',
                'count': len(searches),
                'data': searches,
                'source': 'erp'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[POPULAR_SEARCH_ERROR] Error fetching popular searches: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching popular searches: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogSearchView(APIView):
    """
    Log a search query for popular search tracking
    POST: Save search query to database (increments count if already exists)
    
    Request Body:
        {
            "query": "paracetamol"
        }
    
    Example: POST /api/log-search/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            query = request.data.get('query', '').strip()
            user = request.user if request.user.is_authenticated else None
            
            if not query:
                return Response({
                    'success': False,
                    'message': 'Query parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(query) < 2:
                return Response({
                    'success': False,
                    'message': 'Search query must be at least 2 characters'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Import SearchHistory model
            from .models import SearchHistory
            
            # Get or create search history entry
            search_history, created = SearchHistory.objects.get_or_create(
                query=query,
                defaults={'user': user, 'search_count': 1}
            )
            
            # ✅ FIX #5: Use atomic F() expression to prevent lost updates on concurrent searches
            if not created:
                from django.db.models import F
                SearchHistory.objects.filter(query=query).update(
                    search_count=F('search_count') + 1,
                    updated_at=timezone.now()
                )
                # Refresh to get updated count for logging
                search_history.refresh_from_db()
            
            logger.info(f"[LOG_SEARCH] Query: '{query}' | User: {user.username if user else 'Anonymous'} | Count: {search_history.search_count}")
            
            return Response({
                'success': True,
                'message': 'Search logged successfully',
                'query': query,
                'searchCount': search_history.search_count
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[LOG_SEARCH_ERROR] Error logging search: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error logging search: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== ERP FETCH UTILITIES ====================

def fetch_item_from_erp(item_code):
    """
    Fetch a specific item from ERP endpoint
    Returns item data dict or None if not found
    ALWAYS FRESH - no cache used here
    [UPDATED] Now uses auto-generated token automatically
    """
    try:
        from .erp_token_service import get_erp_token_for_request
        api_key = get_erp_token_for_request()
        if not api_key:
            logger.error("Could not get auto-generated token")
            return None
        
        # Fetch all items from ERP
        erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
        params = {'apiKey': api_key}
        
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


def fetch_all_items_from_erp():
    """
    Helper function: Fetch all items from ERP in one call
    Used by recommendation views to enrich data with live pricing/stock
    
    Returns: List of item dicts from ERP, or empty list if error
    Usage: Used in SimilarProductsView, FrequentlyBoughtTogetherView, TopSellingProductsView
    [UPDATED] Now uses auto-generated token automatically
    """
    try:
        from .erp_token_service import get_erp_token_for_request
        api_key = get_erp_token_for_request()
        if not api_key:
            logger.error("[ERP_ERROR] Could not get auto-generated token")
            return []
        
        erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
        params = {'apiKey': api_key}
        
        logger.info(f"[ERP_FETCH_ALL] Fetching all items from ERP: {erp_url}")
        
        response = requests.get(erp_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') != '200':
            logger.error(f"[ERP_ERROR] ERP returned non-200 code: {data.get('code')}")
            return []
        
        items = data.get('data', [])
        logger.info(f"[ERP_FETCH_ALL] Successfully fetched {len(items)} items from ERP")
        return items
        
    except requests.exceptions.Timeout:
        logger.error("[ERP_ERROR] ERP request timed out (15 seconds)")
        return []
    except requests.exceptions.ConnectionError:
        logger.error("[ERP_ERROR] Failed to connect to ERP server")
        return []
    except Exception as e:
        logger.error(f"[ERP_ERROR] Error fetching all items from ERP: {str(e)}")
        return []


def parse_date(date_string):
    """
    Helper: Parse date string from ERP (format: YYYY-MM-DD)
    Returns: date object or None
    """
    try:
        if not date_string:
            return None
        from datetime import datetime
        return datetime.strptime(str(date_string), '%Y-%m-%d').date()
    except:
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


def get_item_stock_status(item_code):
    """
    Fetch stock availability status for item from ERP
    CRITICAL CHECKS:
    - Stock quantity > 0
    - Expiry date not passed
    Always fresh - no caching
    [UPDATED] Now uses auto-generated token automatically
    """
    try:
        item_data = fetch_item_from_erp(item_code)
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
    """List all delivery addresses for user"""
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        """Get all addresses"""
        try:
            user = get_object_or_404(User, id=user_id)
            addresses = Address.objects.filter(user=user, is_active=True).order_by('-is_default', '-created_at')
            serializer = AddressListSerializer(addresses, many=True)
            logger.info(f"[ADDRESS_LIST] User {user_id} retrieved {len(addresses)} addresses")
            return Response({
                'success': True,
                'count': len(addresses),
                'data': serializer.data,
                'message': 'Addresses retrieved successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error listing addresses for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error retrieving addresses: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateAddressView(APIView):
    """Add a new delivery address"""
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
        """Create new address"""
        try:
            # Check if Content-Type is incorrect and try to parse it anyway
            content_type = request.META.get('CONTENT_TYPE', '')
            request_data = request.data
            
            if 'text/plain' in content_type:
                # Try to parse the body as JSON if Content-Type is text/plain
                try:
                    request_data = json.loads(request.body.decode('utf-8'))
                    logger.info(f"[ADDRESS_CREATE] Parsed text/plain request body as JSON for user {user_id}")
                except (json.JSONDecodeError, UnicodeDecodeError) as parse_err:
                    logger.error(f"[ADDRESS_ERROR] Could not parse text/plain request body for user {user_id}: {str(parse_err)}")
                    return Response({
                        'success': False,
                        'message': 'Invalid Content-Type. Please set Content-Type to application/json and ensure body is valid JSON'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            user = get_object_or_404(User, id=user_id)
            serializer = CreateAddressSerializer(data=request_data)
            if serializer.is_valid():
                # Check if user already has this exact address
                existing = Address.objects.filter(
                    user=user,
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
                address = serializer.save(user=user)
                response_serializer = AddressListSerializer(address)
                gps_info = f"GPS: ({address.latitude}, {address.longitude})" if address.latitude and address.longitude else "No GPS"
                logger.info(f"[ADDRESS_CREATE] User {user_id} added address: {address.name} ({address.address_type}) - {gps_info}")
                
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
            logger.error(f"[ADDRESS_ERROR] Error creating address for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error creating address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateAddressView(APIView):
    """Update an existing delivery address"""
    permission_classes = [AllowAny]
    
    def put(self, request, user_id, address_id):
        """Update address"""
        try:
            user = get_object_or_404(User, id=user_id)
            address = get_object_or_404(Address, id=address_id, user=user)
        except:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            serializer = CreateAddressSerializer(address, data=request.data, partial=True)
            if serializer.is_valid():
                address = serializer.save()
                response_serializer = AddressListSerializer(address)
                gps_info = f"GPS: ({address.latitude}, {address.longitude})" if address.latitude and address.longitude else "No GPS"
                logger.info(f"[ADDRESS_UPDATE] User {user_id} updated address ID {address_id} - {gps_info}")
                
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
            logger.error(f"[ADDRESS_ERROR] Error updating address {address_id} for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error updating address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAddressView(APIView):
    """Delete a delivery address (soft delete)"""
    permission_classes = [AllowAny]
    
    def delete(self, request, user_id, address_id):
        """Delete address"""
        try:
            user = get_object_or_404(User, id=user_id)
            address = get_object_or_404(Address, id=address_id, user=user)
        except:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            address.is_active = False
            address.save()
            logger.info(f"[ADDRESS_DELETE] User {user_id} deleted address ID {address_id}")
            
            return Response({
                'success': True,
                'message': 'Address deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error deleting address {address_id} for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error deleting address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetDefaultAddressView(APIView):
    """Set an address as default"""
    permission_classes = [AllowAny]
    
    def post(self, request, user_id, address_id):
        """Set address as default"""
        try:
            user = get_object_or_404(User, id=user_id)
            address = get_object_or_404(Address, id=address_id, user=user)
        except:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # ✅ FIX #4: Use atomic transaction to prevent multiple default addresses
            with transaction.atomic():
                # Remove default from other addresses
                Address.objects.filter(user=user, is_default=True).exclude(id=address_id).update(is_default=False)
                address.is_default = True
                address.save()
            response_serializer = AddressListSerializer(address)
            logger.info(f"[ADDRESS_DEFAULT] User {user_id} set address ID {address_id} as default")
            
            return Response({
                'success': True,
                'message': 'Default address set successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error setting default address {address_id} for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error setting default address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckoutWithAddressView(APIView):
    """Checkout with selected delivery address"""
    permission_classes = [AllowAny]
    
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
                
                # Get payment method from request
                payment_method = serializer.validated_data.get('payment_method', 'RAZORPAY')
                
                logger.info(f"[ORDER_CHECKOUT] User {request.user.username} completed checkout with address ID {address_id} - Payment Method: {payment_method}")
                logger.info(f"[ORDER_CREATED] Order {sales_order.order_id} created for {address.name} at {address.get_full_address()}")
                
                # Prepare payment instructions based on payment method
                payment_instructions = {
                    'RAZORPAY': {
                        'endpoint': '/api/payment/initiate/',
                        'method': 'POST',
                        'description': 'Call initiate endpoint to get Razorpay order details',
                        'next_step': 'Open Razorpay checkout modal with payment details'
                    },
                    'COD': {
                        'endpoint': '/api/payment/cod/initiate/',
                        'method': 'POST',
                        'description': 'Call COD initiate endpoint to confirm COD payment',
                        'next_step': 'Payment will be collected at delivery'
                    }
                }
                
                return Response({
                    'success': True,
                    'message': 'Order placed successfully',
                    'data': {
                        'order_id': sales_order.order_id,
                        'delivery_address': AddressListSerializer(address).data,
                        'total_amount': float(total_amount),
                        'item_count': len(cart_items),
                        'payment_method': payment_method,
                        'payment_instructions': payment_instructions.get(payment_method, payment_instructions['RAZORPAY'])
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
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
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
            logger.info(f"[LOCATION_DETECT] User {user_id} detected location at ({latitude}, {longitude})")
            
            return Response({
                'success': True,
                'message': 'Location detected successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except GeocodingException as e:
            logger.warning(f"[LOCATION_ERROR] Geocoding failed for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Could not detect address from location: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"[LOCATION_ERROR] Error detecting location for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error detecting location: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmLocationAddressView(APIView):
    """Confirm detected location and save as address"""
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
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
            user = get_object_or_404(User, id=user_id)
            
            existing = Address.objects.filter(
                user=user,
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
            address = serializer.save(user=user, is_gps_verified=True)
            
            response_serializer = AddressListSerializer(address)
            logger.info(f"[ADDRESS_GPS_SAVE] User {user_id} saved GPS-detected address: {address.name} ({latitude}, {longitude})")
            
            return Response({
                'success': True,
                'message': 'Address saved successfully from location',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"[LOCATION_ERROR] Error saving location address for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error saving address: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NearbyAddressesView(APIView):
    """Find addresses near current location"""
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
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
            user = get_object_or_404(User, id=user_id)
            
            # Validate coordinates
            validate_coordinates(latitude, longitude)
            
            if radius_km <= 0 or radius_km > 50:
                return Response({
                    'success': False,
                    'message': 'Radius must be between 0 and 50 km'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get all user's addresses
            addresses = Address.objects.filter(user=user, is_active=True)
            
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
            
            logger.info(f"[LOCATION_NEARBY] User {user_id} found {len(nearby_addresses)} nearby addresses")
            
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
            logger.warning(f"[LOCATION_ERROR] Error in nearby search for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Location error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"[LOCATION_ERROR] Error finding nearby addresses for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error searching nearby addresses: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================== ORDER CONFIRMATION PREVIEW VIEW ==================

class OrderConfirmationPreviewView(APIView):
    """Get order confirmation preview with delivery address before payment"""
    permission_classes = [AllowAny]
    
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


# ==================== RECOMMENDATION VIEWS ====================

class FrequentlyBoughtTogetherView(APIView):
    """
    Get products frequently bought together with a specific item (with ERP enrichment)
    GET: Fetch products often purchased with the provided item based on order history
    
    Query Parameters:
        - itemCode: Item code to get frequently bought together items (required)
        - limit: Max number of recommendations (default: 5)
        - days: Look back period in days (default: 90)
        - apiKey: Optional API key to fetch fresh data from ERP
    
    Example: /api/recommendations/frequently-bought/?itemCode=INJ001&limit=5&days=90&apiKey=xyz
    
    Data Flow:
    1. Query database: Find co-purchased items from order history
    2. Rank by co-purchase frequency
    3. Fetch from ERP: Get live pricing, stock, expiry for each
    4. Return results with fresh ERP data
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            item_code = request.query_params.get('itemCode')
            limit = int(request.query_params.get('limit', 5))
            days = int(request.query_params.get('days', 90))
            # [UPDATED] Token now auto-generated - no need for apiKey from request
            use_erp = True  # Always use ERP with auto-generated token
            
            # Check if user exists
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            if not item_code:
                return Response({
                    'success': False,
                    'message': 'itemCode query parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Step 1: Get the base item
            try:
                base_item = ItemMaster.objects.get(item_code=item_code)
                base_product_info = ProductInfo.objects.get(item=base_item)
            except ItemMaster.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Item with code {item_code} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            except ProductInfo.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Product information not available for {item_code}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # ✅ Step 2: Query database for co-purchased items (filtered by this user)
            from django.utils import timezone
            from datetime import timedelta
            from django.db.models import Count
            
            start_date = timezone.now() - timedelta(days=days)
            
            orders_with_item = SalesOrder.objects.filter(
                user_id=user_id,
                items__item_code=item_code,
                created_at__gte=start_date
            ).distinct()
            
            if not orders_with_item.exists():
                logger.info(f"[FREQUENTLY_BOUGHT] No order history for item {item_code}")
                return Response({
                    'success': True,
                    'data': {
                        'baseProductCode': item_code,
                        'baseProductName': base_item.item_name,
                        'frequentlyBoughtWith': [],
                        'totalPurchaseCount': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # Get all items in these orders (except the base item)
            frequently_bought_counts = SalesOrderItem.objects.filter(
                sales_order__in=orders_with_item
            ).exclude(
                item_code=item_code
            ).values('item_code').annotate(
                co_purchase_count=Count('id')
            ).order_by('-co_purchase_count')[:limit]
            
            # Get the actual items
            frequently_bought_item_codes = [item['item_code'] for item in frequently_bought_counts]
            frequently_bought_items = ItemMaster.objects.filter(
                item_code__in=frequently_bought_item_codes
            )
            
            # Sort by co-purchase count
            item_count_map = {item['item_code']: item['co_purchase_count'] for item in frequently_bought_counts}
            frequently_bought_items = sorted(
                frequently_bought_items,
                key=lambda x: item_count_map.get(x.item_code, 0),
                reverse=True
            )
            
            # ✅ Step 3: Fetch fresh data from ERP with auto-generated token
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            products_data = []
            for product in frequently_bought_items:
                # Enrich with ERP data if available
                erp_data = erp_map.get(product.item_code)
                if erp_data:
                    # Enrich with ERP data (complete product info)
                    product.item_code = erp_data.get('c_item_code', product.item_code)
                    product.item_name = erp_data.get('itemName', product.item_name)
                    product.batch_no = erp_data.get('batchNo', product.batch_no)
                    product.item_qty_per_box = erp_data.get('itemQtyPerBox', product.item_qty_per_box)
                    product.mrp = float(erp_data.get('mrp', product.mrp))
                    product.std_disc = float(erp_data.get('std_disc', product.std_disc))
                    product.max_disc = float(erp_data.get('max_disc', product.max_disc))
                    product.expiry_date = parse_date(erp_data.get('expiryDate', product.expiry_date))
                    product.erp_stock = erp_data.get('stockBalQty', 0)
                
                products_data.append(product)
            
            # ✅ Step 4: Serialize results
            serializer = ProductRecommendationSerializer(
                products_data,
                many=True,
                context={'request': request}
            )
            
            logger.info(f"[FREQUENTLY_BOUGHT] Found {len(products_data)} frequently bought items with {item_code} | Orders: {orders_with_item.count()} | Source: ERP (auto-token)")
            
            return Response({
                'success': True,
                'data': {
                    'baseProductCode': item_code,
                    'baseProductName': base_item.item_name,
                    'frequentlyBoughtWith': serializer.data,
                    'totalPurchaseCount': orders_with_item.count(),
                    'source': 'erp',
                    'lookbackDays': days,
                    'lastFetched': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[RECOMMENDATION_ERROR] Error fetching frequently bought together: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching recommendations: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TopSellingProductsView(APIView):
    """
    Get top selling products across all categories (with ERP enrichment)
    GET: Fetch best-selling products based on sales volume
    
    Query Parameters:
        - period: Time period ('weekly', 'monthly', 'all-time') (default: 'monthly')
        - limit: Max number of top products (default: 10)
        - category: Filter by category ID (optional)
        - apiKey: Optional API key to fetch fresh data from ERP
    
    Example: /api/recommendations/top-selling/?period=monthly&limit=10&apiKey=xyz
    
    Data Flow:
    1. Query database: Aggregate sales volume by item_code
    2. Rank by total quantity sold in period
    3. Fetch from ERP: Get live pricing, stock, expiry for each
    4. Return top sellers with fresh ERP data
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            period = request.query_params.get('period', 'monthly').lower()
            limit = int(request.query_params.get('limit', 10))
            category_id = request.query_params.get('category')
            # [UPDATED] Token now auto-generated - no need for apiKey from request
            use_erp = True  # Always use ERP with auto-generated token
            
            if period not in ['weekly', 'monthly', 'all-time']:
                return Response({
                    'success': False,
                    'message': "period must be one of: 'weekly', 'monthly', 'all-time'"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Step 1: Calculate date range based on period
            from django.utils import timezone
            from datetime import timedelta
            from django.db.models import Sum
            
            now = timezone.now()
            if period == 'weekly':
                start_date = now - timedelta(days=7)
            elif period == 'monthly':
                start_date = now - timedelta(days=30)
            else:  # all-time
                start_date = now - timedelta(days=365*10)  # 10 years
            
            # ✅ Step 2: Query database for sales aggregation
            sales_items = SalesOrderItem.objects.filter(
                sales_order__created_at__gte=start_date
            ).values('item_code').annotate(
                total_qty=Sum('total_loose_qty')
            ).order_by('-total_qty')[:limit]
            
            if not sales_items.exists():
                logger.info(f"[TOP_SELLING] No sales data for period {period}")
                return Response({
                    'success': True,
                    'data': {
                        'period': period,
                        'totalCount': 0,
                        'products': [],
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # Get the actual items
            top_item_codes = [item['item_code'] for item in sales_items]
            
            if category_id:
                top_items = ItemMaster.objects.filter(item_code__in=top_item_codes)
                top_items = top_items.filter(product_info__category_id=category_id)
            else:
                top_items = ItemMaster.objects.filter(item_code__in=top_item_codes)
            
            # Sort by sales quantity
            item_qty_map = {item['item_code']: item['total_qty'] for item in sales_items}
            top_items = sorted(
                top_items,
                key=lambda x: item_qty_map.get(x.item_code, 0),
                reverse=True
            )[:limit]
            
            # ✅ Step 3: Fetch fresh data from ERP with auto-generated token
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            products_data = []
            for product in top_items:
                # Add sales volume from database
                product.sales_volume_qty = item_qty_map.get(product.item_code, 0)
                
                # Enrich with ERP data if available
                erp_data = erp_map.get(product.item_code)
                if erp_data:
                    # Enrich with ERP data (complete product info)
                    product.item_code = erp_data.get('c_item_code', product.item_code)
                    product.item_name = erp_data.get('itemName', product.item_name)
                    product.batch_no = erp_data.get('batchNo', product.batch_no)
                    product.item_qty_per_box = erp_data.get('itemQtyPerBox', product.item_qty_per_box)
                    product.mrp = float(erp_data.get('mrp', product.mrp))
                    product.std_disc = float(erp_data.get('std_disc', product.std_disc))
                    product.max_disc = float(erp_data.get('max_disc', product.max_disc))
                    product.expiry_date = parse_date(erp_data.get('expiryDate', product.expiry_date))
                    product.erp_stock = erp_data.get('stockBalQty', 0)
                
                products_data.append(product)
            
            # ✅ Step 4: Serialize results
            serializer = ProductRecommendationSerializer(
                products_data,
                many=True,
                context={'request': request}
            )
            
            logger.info(f"[TOP_SELLING] Retrieved {len(products_data)} top selling products for period {period} | Source: ERP (auto-token)")
            
            return Response({
                'success': True,
                'data': {
                    'period': period,
                    'periodDays': 7 if period == 'weekly' else 30 if period == 'monthly' else 3650,
                    'totalCount': len(products_data),
                    'products': serializer.data,
                    'message': f'Top selling products for {period}',
                    'source': 'erp',
                    'lastFetched': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[RECOMMENDATION_ERROR] Error fetching top selling products: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching top selling products: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonalizedRecommendationsView(APIView):
    """
    Get personalized recommendations based on user's purchase & search history
    GET: Fetch products recommended based on user's buying pattern
    
    URL Parameters:
        - user_id: User ID (required)
    
    Query Parameters:
        - limit: Max number of recommendations (default: 15)
        - apiKey: Optional API key to fetch fresh data from ERP
    
    Example: /api/recommendations/for-you/88/?limit=15&apiKey=xyz
    
    Algorithm:
    1. Get user's purchase history (categories they bought from)
    2. Get user's search history (keywords they searched)
    3. Find similar products in those categories
    4. Rank by category frequency + popularity + stock
    5. Fetch fresh ERP data
    6. Return personalized recommendations
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            limit = int(request.query_params.get('limit', 15))
            # [UPDATED] Token now auto-generated - no need for apiKey from request
            use_erp = True  # Always use ERP with auto-generated token
            
            # Validate user exists
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'User with ID {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # ✅ Step 1: Get user's purchase history (categories & items already bought)
            user_purchases = SalesOrderItem.objects.filter(
                sales_order__user_id=user_id
            ).values_list('item_code', flat=True).distinct()
            
            purchased_products = ProductInfo.objects.filter(
                item__item_code__in=user_purchases
            ).values_list('category_id', flat=True).distinct()
            
            # ✅ Step 2: Get search history (popular searches - global if not tracked per-user)
            from .models import SearchHistory
            # Try to get user-specific searches first, fallback to popular searches globally
            user_searches = SearchHistory.objects.filter(
                user_id=user_id
            ).order_by('-search_count')[:5].values_list('query', flat=True)
            
            # If no user-specific searches found, use popular global searches (since searches may not track user_id)
            if not user_searches:
                user_searches = SearchHistory.objects.filter(
                    query__isnull=False
                ).order_by('-search_count')[:5].values_list('query', flat=True)
                logger.info(f"[PERSONALIZED] No user-specific searches for user {user_id}, using popular global searches")
            
            search_keywords = list(user_searches) if user_searches else []
            logger.info(f"[PERSONALIZED] User {user_id} | Purchases: {len(purchased_products)} categories | Searches: {len(search_keywords)} keywords")
            
            # ✅ Step 3: Find products in user's favorite categories (similar to what they bought)
            from django.db.models import Q, Count
            
            recommended_products = ProductInfo.objects.none()
            fallback_source = 'personalized'
            fallback_reason = 'Based on your purchases and searches'
            
            # If user has purchase/search history, use personalized recommendations
            if purchased_products.exists() or search_keywords:
                
                # Start with category-based recommendations (if user has purchase history)
                if purchased_products.exists():
                    recommended_products = ProductInfo.objects.filter(
                        category_id__in=purchased_products
                    ).exclude(
                        item__item_code__in=user_purchases  # Exclude already purchased items
                    ).select_related('item', 'category')
                    logger.info(f"[PERSONALIZED] Found {recommended_products.count()} products by category")
                
                # Search by keywords from search history
                if search_keywords:
                    keyword_query = Q()
                    for keyword in search_keywords:
                        keyword_query |= (
                            Q(item__item_name__icontains=keyword) |
                            Q(description__icontains=keyword) |
                            Q(category__name__icontains=keyword)
                        )
                    keyword_products = ProductInfo.objects.filter(keyword_query).exclude(
                        item__item_code__in=user_purchases
                    ).select_related('item', 'category')
                    logger.info(f"[PERSONALIZED] Found {keyword_products.count()} products by keywords: {search_keywords}")
                    
                    # Combine results
                    if recommended_products.exists():
                        recommended_products = recommended_products | keyword_products
                    else:
                        recommended_products = keyword_products
                
                recommended_products = recommended_products.distinct()[:limit * 2]  # Get extra for ranking
            
            # ✅ FALLBACK: If no personalized recommendations, show top-selling products
            if not recommended_products.exists():
                logger.info(f"[PERSONALIZED] No personalized recommendations for user {user_id}, falling back to top-selling products")
                
                from django.db.models import Sum
                from datetime import timedelta
                start_date = timezone.now() - timedelta(days=30)  # Last 30 days
                
                # Get top-selling items for the month
                top_sales = SalesOrderItem.objects.filter(
                    sales_order__created_at__gte=start_date
                ).values('item_code').annotate(
                    total_qty=Sum('total_loose_qty')
                ).order_by('-total_qty')[:limit]
                
                top_item_codes = [item['item_code'] for item in top_sales]
                
                if top_item_codes:
                    top_items = ItemMaster.objects.filter(item_code__in=top_item_codes)
                    recommended_products = ProductInfo.objects.filter(item__in=top_items).select_related('item', 'category')
                    fallback_source = 'top-selling'
                    fallback_reason = 'Based on popular products (no purchase history yet)'
                else:
                    # If still no products, show most recent products
                    recommended_products = ProductInfo.objects.all().select_related('item', 'category')[:limit]
                    fallback_source = 'recent'
                    fallback_reason = 'New to our catalog'
            else:
                fallback_source = 'personalized'
                fallback_reason = 'Based on your purchases and searches'
            
            if not recommended_products.exists():
                logger.warning(f"[PERSONALIZED] No products available at all for user {user_id}")
                return Response({
                    'success': True,
                    'data': {
                        'userId': user_id,
                        'recommendations': [],
                        'reason': 'No products available',
                        'count': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # ✅ Step 4: Fetch fresh data from ERP and enrich with auto-generated token
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            products_data = []
            for product_info in recommended_products:
                item = product_info.item
                
                # Enrich with ERP data if available
                erp_data = erp_map.get(item.item_code)
                if erp_data:
                    item.item_code = erp_data.get('c_item_code', item.item_code)
                    item.item_name = erp_data.get('itemName', item.item_name)
                    item.mrp = float(erp_data.get('mrp', item.mrp))
                    item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                    item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                    item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    item.erp_stock = erp_data.get('stockBalQty', 0)
                
                products_data.append(item)
            
            # ✅ Step 5: Serialize and rank by stock availability
            serializer = ProductRecommendationSerializer(
                products_data[:limit],
                many=True,
                context={'request': request}
            )
            
            logger.info(f"[PERSONALIZED] Generated {len(serializer.data)} recommendations for user {user_id} | Source: {fallback_source}")
            
            return Response({
                'success': True,
                'message': f'Found {len(serializer.data)} recommendations for you',
                'count': len(serializer.data),
                'recommendationType': fallback_source,
                'reason': fallback_reason,
                'userId': user_id,
                'data': serializer.data,
                'purchaseCategories': len(purchased_products),
                'searchKeywords': search_keywords,
                'lastFetched': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[PERSONALIZED_ERROR] Error fetching personalized recommendations: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching recommendations: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PopularProductsView(APIView):
    """
    Get popular products based on search frequency and purchases
    GET: Fetch trending/popular products
    
    Query Parameters:
        - limit: Max number of products (default: 10)
        - period: 'weekly', 'monthly', 'all-time' (default: 'monthly')
        - apiKey: Optional API key to fetch fresh data from ERP
    
    Example: /api/recommendations/popular/?limit=10&period=monthly&apiKey=xyz
    
    Algorithm:
    1. Get most searched keywords
    2. Aggregate search count + purchase count
    3. Rank by popularity score
    4. Fetch fresh ERP data
    5. Return trending products
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
            period = request.query_params.get('period', 'monthly').lower()
            # [UPDATED] Token now auto-generated - no need for apiKey from request
            
            if period not in ['weekly', 'monthly', 'all-time']:
                return Response({
                    'success': False,
                    'message': "period must be one of: 'weekly', 'monthly', 'all-time'"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Step 1: Calculate date range
            from django.utils import timezone
            from datetime import timedelta
            from django.db.models import Count, Sum, F
            
            now = timezone.now()
            if period == 'weekly':
                start_date = now - timedelta(days=7)
            elif period == 'monthly':
                start_date = now - timedelta(days=30)
            else:  # all-time
                start_date = now - timedelta(days=365*10)  # 10 years
            
            # ✅ Step 2: Get popular search terms
            from .models import SearchHistory
            popular_searches = SearchHistory.objects.filter(
                updated_at__gte=start_date
            ).order_by('-search_count')[:limit]
            
            if not popular_searches.exists():
                logger.info(f"[POPULAR] No search history for period {period}")
                return Response({
                    'success': True,
                    'data': {
                        'period': period,
                        'totalCount': 0,
                        'products': [],
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # ✅ Step 3: Find products matching popular searches
            from django.db.models import Q
            
            popular_product_codes = set()
            for search in popular_searches:
                products = ProductInfo.objects.filter(
                    Q(item__item_name__icontains=search.query) |
                    Q(description__icontains=search.query) |
                    Q(category__name__icontains=search.query)
                ).values_list('item__item_code', flat=True)
                popular_product_codes.update(products)
            
            popular_items = ItemMaster.objects.filter(
                item_code__in=popular_product_codes
            )[:limit]
            
            if not popular_items.exists():
                return Response({
                    'success': True,
                    'data': {
                        'period': period,
                        'totalCount': 0,
                        'products': [],
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # ✅ Step 4: Fetch fresh data from ERP with auto-generated token
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            products_data = []
            search_count_map = {search.query: search.search_count for search in popular_searches}
            
            for item in popular_items:
                # Enrich with ERP data if available
                erp_data = erp_map.get(item.item_code)
                if erp_data:
                    item.item_code = erp_data.get('c_item_code', item.item_code)
                    item.item_name = erp_data.get('itemName', item.item_name)
                    item.mrp = float(erp_data.get('mrp', item.mrp))
                    item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                    item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                    item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    item.erp_stock = erp_data.get('stockBalQty', 0)
                
                products_data.append(item)
            
            # ✅ Step 5: Serialize results
            serializer = ProductRecommendationSerializer(
                products_data,
                many=True,
                context={'request': request}
            )
            
            logger.info(f"[POPULAR] Found {len(serializer.data)} popular products for period {period}")
            
            return Response({
                'success': True,
                'data': {
                    'period': period,
                    'totalCount': len(serializer.data),
                    'products': serializer.data,
                    'source': 'erp',
                    'lastFetched': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[POPULAR_ERROR] Error fetching popular products: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching popular products: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RecentlyViewedView(APIView):
    """
    Get recently viewed products for a user
    GET: Fetch products recently viewed by this user in order (most recent first)
    
    Path Parameters:
        - user_id: User to get recently viewed products for (required)
    
    Query Parameters:
        - limit: Max number of products (default: 10)
    
    Example: /api/recommendations/recently-viewed/5/?limit=10
    
    Data Flow:
    1. Get ProductView records for user
    2. Order by most recently viewed
    3. Limit to requested count
    4. Fetch live ERP data for each
    5. Return with fresh pricing/stock info
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            limit = int(request.query_params.get('limit', 10))
            
            # Check if user exists
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # ✅ Step 1: Get recently viewed products for this user
            from django.db.models import Max
            
            # ✅ Auto-cleanup: Keep only last 10 views, delete older ones
            max_views = 10  # Configurable retention limit
            all_views = ProductView.objects.filter(
                user_id=user_id
            ).order_by('-viewed_at')
            
            total_views = all_views.count()
            if total_views > max_views:
                # Get the 11th record onward and delete
                views_to_delete = all_views[max_views:]
                deleted_count = views_to_delete.count()
                for view in views_to_delete:
                    view.delete()
                logger.info(f"[RECENTLY_VIEWED_CLEANUP] Deleted {deleted_count} old views for user {user_id} (kept {max_views})")
            
            # Now fetch for display
            recently_viewed = ProductView.objects.filter(
                user_id=user_id
            ).select_related('item').order_by('-viewed_at')[:limit]
            
            if not recently_viewed.exists():
                logger.info(f"[RECENTLY_VIEWED] No viewing history for user {user_id}")
                return Response({
                    'success': True,
                    'data': {
                        'userId': user_id,
                        'userName': user.username,
                        'recentlyViewed': [],
                        'totalCount': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # Extract items
            viewed_items = [pv.item for pv in recently_viewed]
            
            # ✅ Step 2: Fetch fresh data from ERP with auto-generated token
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            products_data = []
            for product in viewed_items:
                # Enrich with ERP data if available
                erp_data = erp_map.get(product.item_code)
                if erp_data:
                    product.item_code = erp_data.get('c_item_code', product.item_code)
                    product.item_name = erp_data.get('itemName', product.item_name)
                    product.batch_no = erp_data.get('batchNo', product.batch_no)
                    product.item_qty_per_box = erp_data.get('itemQtyPerBox', product.item_qty_per_box)
                    product.mrp = float(erp_data.get('mrp', product.mrp))
                    product.std_disc = float(erp_data.get('std_disc', product.std_disc))
                    product.max_disc = float(erp_data.get('max_disc', product.max_disc))
                    product.expiry_date = parse_date(erp_data.get('expiryDate', product.expiry_date))
                    product.erp_stock = erp_data.get('stockBalQty', 0)
                
                products_data.append(product)
            
            # ✅ Step 3: Serialize results
            serializer = ProductRecommendationSerializer(
                products_data,
                many=True,
                context={'request': request}
            )
            
            logger.info(f"[RECENTLY_VIEWED] Found {len(products_data)} recently viewed items for user {user_id} | Source: ERP (auto-token)")
            
            return Response({
                'success': True,
                'data': {
                    'userId': user_id,
                    'userName': user.username,
                    'recentlyViewed': serializer.data,
                    'totalCount': len(serializer.data),
                    'source': 'erp',
                    'lastFetched': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[RECENTLY_VIEWED_ERROR] Error fetching recently viewed products: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching recently viewed products: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserRecentActivityView(APIView):
    """
    Get all recent user activity in one API call
    GET: Fetch user's recently viewed products, cart items, and wishlist items
    
    Path Parameters:
        - user_id: User to get activity for (required)
    
    Query Parameters:
        - limit: Max number of items per category (default: 10)
        - viewed_limit: Specific limit for recently viewed (overrides limit)
        - cart_limit: Specific limit for cart items (overrides limit)
        - wishlist_limit: Specific limit for wishlist items (overrides limit)
    
    Example: /api/recommendations/user-activity/88/?limit=5
    Response includes all three: recentlyViewed, recentlyCart, recentlyWishlist
    
    Data Flow:
    1. Get recently viewed products
    2. Get cart items
    3. Get wishlist items
    4. Fetch live ERP data for all
    5. Return consolidated response with all activities
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            # Get limits from query params
            limit = int(request.query_params.get('limit', 10))
            viewed_limit = int(request.query_params.get('viewed_limit', limit))
            cart_limit = int(request.query_params.get('cart_limit', limit))
            wishlist_limit = int(request.query_params.get('wishlist_limit', limit))
            
            # Check if user exists
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # ✅ Fetch ERP data once (reuse for all)
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            # ✅ Step 1: Get recently viewed products
            recently_viewed_data = []
            try:
                # Auto-cleanup
                all_views = ProductView.objects.filter(user_id=user_id).order_by('-viewed_at')
                total_views = all_views.count()
                if total_views > 10:
                    views_to_delete = all_views[10:]
                    for view in views_to_delete:
                        view.delete()
                
                # Fetch for display
                recently_viewed = ProductView.objects.filter(
                    user_id=user_id
                ).select_related('item').order_by('-viewed_at')[:viewed_limit]
                
                for pv in recently_viewed:
                    item = pv.item
                    erp_data = erp_map.get(item.item_code)
                    if erp_data:
                        item.mrp = float(erp_data.get('mrp', item.mrp))
                        item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                        item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                        item.erp_stock = erp_data.get('stockBalQty', 0)
                        item.batch_no = erp_data.get('batchNo', item.batch_no)
                        item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    
                    # Get product info for additional details
                    try:
                        product_info = ProductInfo.objects.get(item=item)
                        # Get images
                        images = ProductImage.objects.filter(product_info=product_info).order_by('image_order')
                        images_list = [{'image': request.build_absolute_uri(img.image.url), 'image_order': img.image_order} for img in images]
                        
                        # Check cart/wishlist status
                        cart_status = CartItem.objects.filter(item=item, cart__user_id=user_id).exists() if user_id else False
                        wishlist_status = WishlistItem.objects.filter(item=item, wishlist__user_id=user_id).exists() if user_id else False
                    except ProductInfo.DoesNotExist:
                        product_info = None
                        images_list = []
                        cart_status = False
                        wishlist_status = False
                    
                    recently_viewed_data.append({
                        'itemCode': item.item_code,
                        'itemName': item.item_name,
                        'batchNo': item.batch_no or '',
                        'expiryDate': str(item.expiry_date) if item.expiry_date else None,
                        'itemQtyPerBox': item.item_qty_per_box,
                        'mrp': float(item.mrp),
                        'std_disc': float(item.std_disc),
                        'max_disc': float(item.max_disc),
                        'stock': getattr(item, 'erp_stock', 0),
                        'subheading': product_info.subheading if product_info else '',
                        'description': product_info.description if product_info else '',
                        'type_label': product_info.type_label if product_info else '',
                        'brand_id': product_info.category.id if product_info and product_info.category else None,
                        'brand_name': product_info.category.name if product_info and product_info.category else '',
                        'brand_logo': request.build_absolute_uri(product_info.category.icon.url) if product_info and product_info.category and product_info.category.icon else '',
                        'images': images_list,
                        'cart_status': cart_status,
                        'wishlist_status': wishlist_status,
                        'viewedAt': pv.viewed_at.isoformat()
                    })
            except Exception as e:
                logger.warning(f"[USER_ACTIVITY] Failed to fetch recently viewed: {str(e)}")
            
            # ✅ Step 2: Get recently added to cart
            recently_cart_data = []
            try:
                cart = Cart.objects.get(user_id=user_id)
                cart_items = CartItem.objects.filter(
                    cart=cart
                ).select_related('item').order_by('-created_at')[:cart_limit]
                
                for ci in cart_items:
                    item = ci.item
                    erp_data = erp_map.get(item.item_code)
                    if erp_data:
                        item.mrp = float(erp_data.get('mrp', item.mrp))
                        item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                        item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                        item.erp_stock = erp_data.get('stockBalQty', 0)
                        item.batch_no = erp_data.get('batchNo', item.batch_no)
                        item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    
                    # Get product info for additional details
                    try:
                        product_info = ProductInfo.objects.get(item=item)
                        # Get images
                        images = ProductImage.objects.filter(product_info=product_info).order_by('image_order')
                        images_list = [{'image': request.build_absolute_uri(img.image.url), 'image_order': img.image_order} for img in images]
                        
                        # Check wishlist status
                        wishlist_status = WishlistItem.objects.filter(item=item, wishlist__user_id=user_id).exists()
                    except ProductInfo.DoesNotExist:
                        product_info = None
                        images_list = []
                        wishlist_status = False
                    
                    recently_cart_data.append({
                        'cartItemId': ci.id,
                        'itemCode': item.item_code,
                        'itemName': item.item_name,
                        'batchNo': item.batch_no or '',
                        'expiryDate': str(item.expiry_date) if item.expiry_date else None,
                        'itemQtyPerBox': item.item_qty_per_box,
                        'mrp': float(item.mrp),
                        'std_disc': float(item.std_disc),
                        'max_disc': float(item.max_disc),
                        'stock': getattr(item, 'erp_stock', 0),
                        'subheading': product_info.subheading if product_info else '',
                        'description': product_info.description if product_info else '',
                        'type_label': product_info.type_label if product_info else '',
                        'brand_id': product_info.category.id if product_info and product_info.category else None,
                        'brand_name': product_info.category.name if product_info and product_info.category else '',
                        'brand_logo': request.build_absolute_uri(product_info.category.icon.url) if product_info and product_info.category and product_info.category.icon else '',
                        'images': images_list,
                        'quantity': ci.quantity,
                        'wishlist_status': wishlist_status,
                        'addedAt': ci.created_at.isoformat()
                    })
            except Cart.DoesNotExist:
                pass
            except Exception as e:
                logger.warning(f"[USER_ACTIVITY] Failed to fetch cart items: {str(e)}")
            
            # ✅ Step 3: Get recently added to wishlist
            recently_wishlist_data = []
            try:
                wishlist = Wishlist.objects.get(user_id=user_id)
                wishlist_items = WishlistItem.objects.filter(
                    wishlist=wishlist
                ).select_related('item').order_by('-created_at')[:wishlist_limit]
                
                for wi in wishlist_items:
                    item = wi.item
                    erp_data = erp_map.get(item.item_code)
                    if erp_data:
                        item.mrp = float(erp_data.get('mrp', item.mrp))
                        item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                        item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                        item.erp_stock = erp_data.get('stockBalQty', 0)
                        item.batch_no = erp_data.get('batchNo', item.batch_no)
                        item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    
                    # Get product info for additional details
                    try:
                        product_info = ProductInfo.objects.get(item=item)
                        # Get images
                        images = ProductImage.objects.filter(product_info=product_info).order_by('image_order')
                        images_list = [{'image': request.build_absolute_uri(img.image.url), 'image_order': img.image_order} for img in images]
                        
                        # Check cart status
                        cart_status = CartItem.objects.filter(item=item, cart__user_id=user_id).exists()
                    except ProductInfo.DoesNotExist:
                        product_info = None
                        images_list = []
                        cart_status = False
                    
                    recently_wishlist_data.append({
                        'wishlistItemId': wi.id,
                        'itemCode': item.item_code,
                        'itemName': item.item_name,
                        'batchNo': item.batch_no or '',
                        'expiryDate': str(item.expiry_date) if item.expiry_date else None,
                        'itemQtyPerBox': item.item_qty_per_box,
                        'mrp': float(item.mrp),
                        'std_disc': float(item.std_disc),
                        'max_disc': float(item.max_disc),
                        'stock': getattr(item, 'erp_stock', 0),
                        'subheading': product_info.subheading if product_info else '',
                        'description': product_info.description if product_info else '',
                        'type_label': product_info.type_label if product_info else '',
                        'brand_id': product_info.category.id if product_info and product_info.category else None,
                        'brand_name': product_info.category.name if product_info and product_info.category else '',
                        'brand_logo': request.build_absolute_uri(product_info.category.icon.url) if product_info and product_info.category and product_info.category.icon else '',
                        'images': images_list,
                        'cart_status': cart_status,
                        'addedAt': wi.created_at.isoformat()
                    })
            except Wishlist.DoesNotExist:
                pass
            except Exception as e:
                logger.warning(f"[USER_ACTIVITY] Failed to fetch wishlist items: {str(e)}")
            
            logger.info(f"[USER_ACTIVITY] Fetched activity for user {user_id} | Views: {len(recently_viewed_data)}, Cart: {len(recently_cart_data)}, Wishlist: {len(recently_wishlist_data)}")
            
            return Response({
                'success': True,
                'data': {
                    'userId': user_id,
                    'userName': user.username,
                    'recentlyViewed': {
                        'items': recently_viewed_data,
                        'count': len(recently_viewed_data)
                    },
                    'recentlyCart': {
                        'items': recently_cart_data,
                        'count': len(recently_cart_data),
                        'totalQuantity': sum(item['quantity'] for item in recently_cart_data)
                    },
                    'recentlyWishlist': {
                        'items': recently_wishlist_data,
                        'count': len(recently_wishlist_data)
                    },
                    'summary': {
                        'totalViewedProducts': len(recently_viewed_data),
                        'totalCartItems': len(recently_cart_data),
                        'totalWishlistItems': len(recently_wishlist_data)
                    },
                    'source': 'erp',
                    'lastFetched': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[USER_ACTIVITY_ERROR] Error fetching user activity: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching user activity: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RecentlyAddedToCartView(APIView):
    """
    Get recently added to cart products for a user
    GET: Fetch products recently added to user's cart (most recent first)
    
    Path Parameters:
        - user_id: User to get recently added to cart products for (required)
    
    Query Parameters:
        - limit: Max number of products (default: 10)
    
    Example: /api/recommendations/recently-cart/5/?limit=10
    
    Data Flow:
    1. Get cart items for user
    2. Order by most recently added
    3. Limit to requested count
    4. Fetch live ERP data for each
    5. Return with fresh pricing/stock info
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            limit = int(request.query_params.get('limit', 10))
            
            # Check if user exists
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # ✅ Step 1: Get cart items for this user
            try:
                cart = Cart.objects.get(user_id=user_id)
            except Cart.DoesNotExist:
                return Response({
                    'success': True,
                    'data': {
                        'userId': user_id,
                        'userName': user.username,
                        'recentlyAddedToCart': [],
                        'totalCount': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            cart_items = CartItem.objects.filter(
                cart=cart
            ).select_related('product_info', 'product_info__item').order_by('-created_at')[:limit]
            
            if not cart_items.exists():
                return Response({
                    'success': True,
                    'data': {
                        'userId': user_id,
                        'userName': user.username,
                        'recentlyAddedToCart': [],
                        'totalCount': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # ✅ Step 2: Fetch fresh data from ERP with auto-generated token
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            products_data = []
            for cart_item in cart_items:
                product = cart_item.product_info
                item = product.item
                
                # Enrich with ERP data if available
                erp_data = erp_map.get(item.item_code)
                if erp_data:
                    item.item_code = erp_data.get('c_item_code', item.item_code)
                    item.item_name = erp_data.get('itemName', item.item_name)
                    item.batch_no = erp_data.get('batchNo', item.batch_no)
                    item.item_qty_per_box = erp_data.get('itemQtyPerBox', item.item_qty_per_box)
                    item.mrp = float(erp_data.get('mrp', item.mrp))
                    item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                    item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                    item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    item.erp_stock = erp_data.get('stockBalQty', 0)
                
                products_data.append({
                    'cartItemId': cart_item.id,
                    'product': item,
                    'quantity': cart_item.quantity,
                    'addedAt': cart_item.created_at.isoformat()
                })
            
            # ✅ Step 3: Serialize results
            serialized_products = []
            for item_data in products_data:
                item = item_data['product']
                serialized_products.append({
                    'cartItemId': item_data['cartItemId'],
                    'itemCode': item.item_code,
                    'itemName': item.item_name,
                    'mrp': float(item.mrp),
                    'discount': float(item.std_disc),
                    'stock': getattr(item, 'erp_stock', 0),
                    'quantity': item_data['quantity'],
                    'addedAt': item_data['addedAt']
                })
            
            logger.info(f"[RECENTLY_CART] Found {len(serialized_products)} recently added to cart items for user {user_id}")
            
            return Response({
                'success': True,
                'data': {
                    'userId': user_id,
                    'userName': user.username,
                    'recentlyAddedToCart': serialized_products,
                    'totalCount': len(serialized_products),
                    'source': 'erp',
                    'lastFetched': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[RECENTLY_CART_ERROR] Error fetching recently added to cart: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching recently added to cart: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecentlyAddedToWishlistView(APIView):
    """
    Get recently added to wishlist products for a user
    GET: Fetch products recently added to user's wishlist (most recent first)
    
    Path Parameters:
        - user_id: User to get recently added to wishlist products for (required)
    
    Query Parameters:
        - limit: Max number of products (default: 10)
    
    Example: /api/recommendations/recently-wishlist/5/?limit=10
    
    Data Flow:
    1. Get wishlist items for user
    2. Order by most recently added
    3. Limit to requested count
    4. Fetch live ERP data for each
    5. Return with fresh pricing/stock info
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            limit = int(request.query_params.get('limit', 10))
            
            # Check if user exists
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # ✅ Step 1: Get wishlist items for this user
            try:
                wishlist = Wishlist.objects.get(user_id=user_id)
            except Wishlist.DoesNotExist:
                return Response({
                    'success': True,
                    'data': {
                        'userId': user_id,
                        'userName': user.username,
                        'recentlyAddedToWishlist': [],
                        'totalCount': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            wishlist_items = WishlistItem.objects.filter(
                wishlist=wishlist
            ).select_related('product_info', 'product_info__item').order_by('-created_at')[:limit]
            
            if not wishlist_items.exists():
                return Response({
                    'success': True,
                    'data': {
                        'userId': user_id,
                        'userName': user.username,
                        'recentlyAddedToWishlist': [],
                        'totalCount': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # ✅ Step 2: Fetch fresh data from ERP with auto-generated token
            erp_items = fetch_all_items_from_erp()
            erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}
            
            products_data = []
            for wishlist_item in wishlist_items:
                product = wishlist_item.product_info
                item = product.item
                
                # Enrich with ERP data if available
                erp_data = erp_map.get(item.item_code)
                if erp_data:
                    item.item_code = erp_data.get('c_item_code', item.item_code)
                    item.item_name = erp_data.get('itemName', item.item_name)
                    item.batch_no = erp_data.get('batchNo', item.batch_no)
                    item.item_qty_per_box = erp_data.get('itemQtyPerBox', item.item_qty_per_box)
                    item.mrp = float(erp_data.get('mrp', item.mrp))
                    item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                    item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                    item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                    item.erp_stock = erp_data.get('stockBalQty', 0)
                
                products_data.append({
                    'wishlistItemId': wishlist_item.id,
                    'product': item,
                    'addedAt': wishlist_item.created_at.isoformat()
                })
            
            # ✅ Step 3: Serialize results
            serialized_products = []
            for item_data in products_data:
                item = item_data['product']
                serialized_products.append({
                    'wishlistItemId': item_data['wishlistItemId'],
                    'itemCode': item.item_code,
                    'itemName': item.item_name,
                    'mrp': float(item.mrp),
                    'discount': float(item.std_disc),
                    'stock': getattr(item, 'erp_stock', 0),
                    'addedAt': item_data['addedAt']
                })
            
            logger.info(f"[RECENTLY_WISHLIST] Found {len(serialized_products)} recently added to wishlist items for user {user_id}")
            
            return Response({
                'success': True,
                'data': {
                    'userId': user_id,
                    'userName': user.username,
                    'recentlyAddedToWishlist': serialized_products,
                    'totalCount': len(serialized_products),
                    'source': 'erp',
                    'lastFetched': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"[RECENTLY_WISHLIST_ERROR] Error fetching recently added to wishlist: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error fetching recently added to wishlist: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CategoryListView(ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategoryWithProductsSerializer
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        """Validate user_id from URL path before processing request"""
        user_id = self.kwargs.get('user_id')
        
        # If user_id is provided in URL path, validate it exists
        if user_id:
            try:
                from .models import CustomUser
                CustomUser.objects.get(id=user_id)
                logger.info(f"[CATEGORIES] User ID {user_id} validated successfully")
            except CustomUser.DoesNotExist:
                logger.error(f"[CATEGORIES] User ID {user_id} not found")
                return Response(
                    {
                        'code': '404',
                        'type': 'categories',
                        'message': f'User with ID {user_id} not found'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Continue with normal GET processing
        return super().get(request, *args, **kwargs)
    
    def get_serializer_context(self):
        """Add ERP enrichment context with auto-generated or provided apiKey + User ID support"""
        context = super().get_serializer_context()
        
        # ============ USER ID / AUTHENTICATION HANDLING ============
        # Priority 1: Check if userId in URL path parameters
        user_id = self.kwargs.get('user_id')
        
        # Priority 2: Check if userId provided via query params
        if not user_id:
            user_id = self.request.query_params.get('userId')
        
        user = None
        
        if user_id:
            # Try to fetch user by provided user_id
            try:
                from .models import CustomUser
                user = CustomUser.objects.get(id=user_id)
                logger.info(f"[CATEGORIES] Using provided userId: {user_id}")
            except CustomUser.DoesNotExist:
                logger.warning(f"[CATEGORIES] User with ID {user_id} not found (query param fallback)")
                user = None
        elif self.request.user and self.request.user.is_authenticated:
            # Priority 3: Use authenticated user
            user = self.request.user
            logger.info(f"[CATEGORIES] Using authenticated user: {user.id}")
        
        # Attach user to context for cart_status and wishlist_status checks
        context['cart_wishlist_user'] = user
        
        # ============ ERP TOKEN & STOCK ENRICHMENT ============
        # Priority 1: Check if apiKey provided via query params (manual override)
        api_key = self.request.query_params.get('apiKey')
        
        # Priority 2: Auto-generate token if not provided
        if not api_key:
            try:
                from .erp_token_service import get_erp_token_for_request
                api_key = get_erp_token_for_request()
                logger.info(f"[CATEGORIES] Using auto-generated ERP token")
            except Exception as e:
                logger.warning(f"[CATEGORIES] Failed to generate ERP token: {str(e)}")
                api_key = None
        else:
            logger.info(f"[CATEGORIES] Using provided apiKey from query params")
        
        # Fetch ERP master data to enrich with stock quantities
        if api_key:
            try:
                erp_base_url = settings.ERP_BASE_URL
                erp_server_url = f"{erp_base_url}/ws_c2_services_get_master_data"
                
                logger.info(f"[CATEGORIES] Fetching ERP data from: {erp_server_url}")
                
                erp_response = requests.get(erp_server_url, params={'apiKey': api_key}, timeout=15)
                
                if erp_response.status_code == 200:
                    erp_data = erp_response.json()
                    items = erp_data.get('data', [])
                    
                    # Create mapping of item_code -> stockBalQty from ERP
                    stock_map = {}
                    for item in items:
                        if item.get('c_item_code'):
                            stock_map[item['c_item_code']] = item.get('stockBalQty', 0)
                    
                    context['erp_stock_map'] = stock_map
                    logger.info(f"[CATEGORIES] [SUCCESS] Successfully enriched with {len(stock_map)} ERP items")
                else:
                    logger.error(f"[CATEGORIES] ERP Server error: {erp_response.status_code}")
                    context['erp_stock_map'] = {}
            except Exception as e:
                logger.error(f"[CATEGORIES] [FAILED] Failed to fetch ERP data: {str(e)}")
                context['erp_stock_map'] = {}
        else:
            logger.warning(f"[CATEGORIES] No API key available - using database stock only")
            context['erp_stock_map'] = {}
        
        return context
    


@api_view(['GET'])
def related_products(request, product_id, user_id):
    """
    Get related products by category (excluding the current product), enriched with ERP data if available
    """
    from .views import fetch_all_items_from_erp, parse_date
    try:
        product = ProductInfo.objects.get(pk=product_id)
        related = ProductInfo.objects.filter(
            category=product.category
        ).exclude(pk=product.pk)[:10]

        # ERP enrichment logic (same as search view)
        erp_items = fetch_all_items_from_erp()
        erp_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}

        products = []
        for product_info in related:
            item = product_info.item
            # Enrich with ERP data if available
            erp_data = erp_map.get(item.item_code)
            if erp_data:
                item.item_code = erp_data.get('c_item_code', item.item_code)
                item.item_name = erp_data.get('itemName', item.item_name)
                item.batch_no = erp_data.get('batchNo', item.batch_no)
                item.item_qty_per_box = erp_data.get('itemQtyPerBox', item.item_qty_per_box)
                item.mrp = float(erp_data.get('mrp', item.mrp))
                item.std_disc = float(erp_data.get('std_disc', item.std_disc))
                item.max_disc = float(erp_data.get('max_disc', item.max_disc))
                item.expiry_date = parse_date(erp_data.get('expiryDate', item.expiry_date))
                item.erp_stock = erp_data.get('stockBalQty', 0)

            mrp = float(item.mrp)
            discount = float(item.std_disc)
            discounted_price = mrp * (1 - discount / 100)

            # Get all product images (ordered by image_order)
            product_images = ProductImage.objects.filter(product_info=product_info).order_by('image_order')
            images_list = [
                {
                    'image': request.build_absolute_uri(img.image.url),
                    'image_order': img.image_order
                }
                for img in product_images
            ]

            # Get stock quantity (ERP first, then database)
            stock_qty = 0
            if hasattr(item, 'erp_stock') and item.erp_stock is not None:
                stock_qty = item.erp_stock  # From ERP
            else:
                try:
                    stock = Stock.objects.filter(item=item).first()
                    if stock:
                        stock_qty = stock.total_bal_ls_qty
                except:
                    stock_qty = 0

            # Check if item is in user's cart/wishlist
            cart_status = False
            wishlist_status = False
            if request.user.is_authenticated:
                try:
                    from .models import CartItem, WishlistItem
                    cart_status = CartItem.objects.filter(
                        cart__user=request.user,
                        product_info=product_info
                    ).exists()
                    wishlist_status = WishlistItem.objects.filter(
                        wishlist__user=request.user,
                        product_info=product_info
                    ).exists()
                except:
                    pass

            # Get brand logo
            brand_logo = ''
            if product_info.category and product_info.category.icon:
                brand_logo = request.build_absolute_uri(product_info.category.icon.url)

            products.append({
                'batchNo': item.batch_no or '',
                'c_item_code': item.item_code,
                'expiryDate': str(item.expiry_date) if item.expiry_date else None,
                'itemName': item.item_name,
                'itemQtyPerBox': item.item_qty_per_box,
                'max_disc': float(item.max_disc),
                'mrp': float(item.mrp),
                'std_disc': float(item.std_disc),
                'stockBalQty': stock_qty,
                'subheading': product_info.subheading or '',
                'description': product_info.description or '',
                'type_label': product_info.type_label or '',
                'brand_id': product_info.category.id if product_info.category else None,
                'brand_name': product_info.category.name if product_info.category else '',
                'brand_logo': brand_logo,
                'images': images_list,
                'cart_status': cart_status,
                'wishlist_status': wishlist_status,
                'discountPercentage': discount,
                'discountedPrice': discounted_price
            })

        return Response({
            'success': True,
            'message': f'Found {len(products)} related products',
            'count': len(products),
            'data': products,
            'source': 'erp' if erp_items else 'database'
        }, status=200)
    except ProductInfo.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)



# ==================== PUSH NOTIFICATIONS ====================
from .models import FCMDevice

class RegisterDeviceTokenView(APIView):
    """
    Register FCM device token for push notifications
    POST /api/notifications/register/
    """
    permission_classes = [AllowAny]
    
    def post(self, request, user_id=None):
        token = request.data.get('token')
        device_type = request.data.get('device_type', 'unknown')
        user_id = user_id or request.data.get('user_id')
        
        if not token:
            return Response({'error': 'Device token is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not user_id and not request.user.is_authenticated:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user
            
        # check if token is already registered to another user and remove it
        FCMDevice.objects.filter(registration_id=token).exclude(user=user).delete()
        
        device, created = FCMDevice.objects.update_or_create(
            user=user,
            registration_id=token,
            defaults={
                'device_type': device_type,
                'is_active': True
            }
        )
        
        # Send Welcome Notification if this is their very first registered device
        if created and user.fcm_devices.count() == 1:
            try:
                from .services import send_push_notification
                send_push_notification(
                    user=user,
                    title="Welcome to Dreams Pharma! \U0001f389",
                    body="Thank you for joining us. You will receive important updates here.",
                    data={"type": "welcome"}
                )
            except Exception as e:
                logger.error(f"Failed to send welcome notification: {e}", exc_info=True)
        
        msg = "Token registered successfully" if created else "Token updated successfully"
        return Response({'message': msg}, status=status.HTTP_200_OK)
