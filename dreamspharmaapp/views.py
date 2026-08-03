# Related Products API (category-based)

from rest_framework.decorators import api_view, permission_classes
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
from decimal import Decimal
import logging
import uuid
import json

logger = logging.getLogger(__name__)

from .models import CustomUser, KYC, OTP, APIToken, ItemMaster, Stock, GLCustomer, SalesOrder, SalesOrderItem, Invoice, InvoiceDetail, Cart, CartItem, Wishlist, WishlistItem, ProductInfo, ProductImage, Address, Category, ProductView, SearchHistory, CreditNote, RetailerWallet, WalletTransaction, FCMDevice, ProductStore, Store
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
    FrequentlyBoughtTogetherResponseSerializer, TopSellingResponseSerializer, CategoryWithProductsSerializer,
    CreditNoteCreateSerializer, CreditNoteListSerializer, CreditNoteDetailSerializer, RetailerWalletSerializer
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
    API endpoint for retrieving and updating retailer profile.
    GET: Retrieve current retailer's profile
    PUT: Update current retailer's profile
    POST: Upload customer photo to profile
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'RETAILER':
            return Response({'error': 'Only retailers have profiles at this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Try to get KYC info using queryset to avoid RelatedObjectDoesNotExist issues
        kyc = None
        kyc_exists = False
        try:
            kyc = KYC.objects.get(user=user)
            kyc_exists = True
        except KYC.DoesNotExist:
            kyc_exists = False
        except Exception as e:
            print(f"Error fetching KYC: {e}")
            kyc_exists = False
        
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
            'store_photo': request.build_absolute_uri(kyc.store_photo.url) if kyc and kyc.store_photo else '',
            'customer_photo': request.build_absolute_uri(kyc.customer_photo.url) if kyc and kyc.customer_photo else '',
            'kyc_exists': kyc_exists,
            'kyc_status': kyc.get_status_display() if kyc else 'Not Submitted'
        }
        return Response(profile, status=status.HTTP_200_OK)

    def post(self, request):
        """
        POST: Upload customer photo to profile
        Requires JWT authentication
        """
        user = request.user
        if user.role != 'RETAILER':
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

    def put(self, request):
        # Only allow updating specific profile fields
        user = request.user
        if user.role != 'RETAILER':
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

        # ── Audit log ──
        try:
            from maindash.views import log_audit
            client_ip = get_client_ip(request)
            log_audit(
                action='Admin Login',
                performed_by_user=user,
                target_entity='System',
                details=f'Successful login from IP {client_ip}',
                category='System',
            )
        except Exception:
            pass

        return Response({
            'message': 'Login successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


class RetailerLoginView(APIView):
    """
    API endpoint for retailer login with email and password.
    POST /api/retailer-auth/login/ - Email + Password login
    
    FIRST LOGIN:  OTP is sent to email for verification
    RETURNING:    Tokens generated immediately (no OTP needed)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Login with email and password.
        OTP is sent on every login for additional security.
        
        Request Body:
        {
            "email": "retailer@example.com",
            "password": "password123"
        }
        
        Response:
        {
            "message": "Email and password verified. OTP sent to your email.",
            "email": "retailer@example.com",
            "otp_required": true,
            "otp_expires_in": 60,
            "user": {
                "id": 1,
                "username": "retailer@example.com",
                "email": "retailer@example.com",
                "phone_number": "+1234567890"
            }
        }
        """
        serializer = RetailerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        
        # ─── SEND OTP ON EVERY LOGIN ───────────────────────────
        # Delete any existing OTP records for this user
        OTP.objects.filter(user=user).delete()
        
        # Create new OTP
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
            'email': user.email,
            'otp_required': True,
            'otp_expires_in': 60,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
            },
        }, status=status.HTTP_200_OK)


class RetailerVerifyOTPView(APIView):
    """
    API endpoint for retailer OTP verification during FIRST LOGIN only.
    POST /api/retailer-auth/verify-otp/ - Verify OTP and get JWT tokens (first login only)
    
    After first login is verified, all subsequent logins skip OTP and go directly to tokens.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Verify OTP to complete first login and get tokens.
        
        Request Body:
        {
            "otp_code": "1234"
        }
        
        Response (Success - First Login Complete):
        {
            "message": "OTP verified successfully. You are now logged in.",
            "user": { "id": 1, "email": "user@example.com" },
            "tokens": {
                "access": "...",
                "refresh": "...",
                "access_expires_in": 900,
                "refresh_expires_in": 31536000,
                "token_type": "Bearer"
            }
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
            
            # Mark first login as complete (skip OTP on future logins)
            if not user.first_login_otp_verified:
                user.first_login_otp_verified = True
                user.save()
            
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
                    'access_expires_in': int(access_lifetime.total_seconds()),  # 900 seconds (15 min)
                    'refresh_expires_in': int(refresh_lifetime.total_seconds()),  # 31536000 seconds (365 days)
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
    """
    Change password for authenticated users (retailers)
    POST /api/auth/change-password/
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'RETAILER':
            return Response({"error": "Only retailers can change password at this endpoint."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
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
            print(f"DEBUG LOGOUT: request.data = {request.data}")
            # Explicitly fail if refresh token key name is supplied in the request body
            if "refresh" in request.data or ("tokens" in request.data and isinstance(request.data["tokens"], dict) and "refresh" in request.data["tokens"]):
                return Response({
                    "error": "Refresh token is not allowed for logout. Please use access token.",
                    "code": "refresh_token_not_allowed"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 1. Extract token safely from request body (handling nesting like "tokens" or "data")
            def extract_token(d):
                if not isinstance(d, dict):
                    return None
                token = d.get("access") or d.get("token")
                if token:
                    return token
                if "tokens" in d and isinstance(d["tokens"], dict):
                    token = d["tokens"].get("access") or d["tokens"].get("token")
                    if token:
                        return token
                if "data" in d and isinstance(d["data"], dict):
                    return extract_token(d["data"])
                return None

            token_str = extract_token(request.data)
                
            if not token_str:
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token_str = auth_header.split(" ")[1]
                    
            if not token_str:
                return Response({
                    "error": "Token is required",
                    "code": "missing_token"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # 2. Validate token type claim using simplejwt
            from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, TokenError
            
            # Check if it is a valid AccessToken
            try:
                AccessToken(token_str)
            except TokenError as e:
                # If AccessToken fails, check if it's a RefreshToken
                try:
                    RefreshToken(token_str)
                    return Response({
                        "error": "Refresh token is not allowed for logout. Please use access token.",
                        "code": "refresh_token_not_allowed"
                    }, status=status.HTTP_400_BAD_REQUEST)
                except TokenError:
                    pass
                
                return Response({
                    "error": "Invalid or expired access token",
                    "code": "invalid_token",
                    "details": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Blacklist outstanding refresh tokens for this user so they must re-login
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            user = request.user
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for out_token in outstanding_tokens:
                BlacklistedToken.objects.get_or_create(token=out_token)
                
            logout(request)
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": "Logout failed",
                "code": "logout_failed",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(APIView):
    """
    Silent token refresh endpoint for mobile apps.
    POST /api/retailer-auth/token/refresh/ - Refresh access token silently
    
    Industry-standard approach:
    - Access token: 15 minutes (short-lived for security)
    - Refresh token: 365 days (user stays logged in year-long)
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
            "refresh": "NEW_REFRESH_TOKEN",  // Token rotation enabled (30 days)
            "access_expires_in": 900,  // 15 minutes in seconds
            "refresh_expires_in": 2592000  // 30 days in seconds
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
            user = CustomUser.objects.get(id=user_id)
            
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
    [DEPRECATED] Use auto-generated token instead!
    
    This endpoint is NO LONGER NEEDED
    Tokens are now automatically generated and cached in the background
    
    All ERP endpoints now use auto-generated tokens transparently
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        return Response({
            'code': '200',
            'type': 'generateToken',
            'message': '[DEPRECATED] Token generation is now automatic. No manual call needed.',
            'note': 'All ERP endpoints auto-generate tokens in background.',
            'apiKey': 'AUTO_GENERATED_BY_BACKEND'
        }, status=status.HTTP_200_OK)


class GetItemMasterView(APIView):
    """
    Get item master details with product information including images, subheading, and description
    GET: Fetch item details DIRECTLY from ERP test server (real-time data)
    Enhanced with product images, subheading, and description from Django database
    
    URL Pattern:
    - /api/erp/ws_c2_services_get_master_data/      (JWT authenticated - includes wishlist/cart status)
    - /api/erp/ws_c2_services_get_master_data?latitude=&longitude=   (store by location)
    - /api/erp/ws_c2_services_get_master_data?storeId=<id>          (store by ID)
    
    🎯 Authentication: Bearer token (JWT access token)
    User is automatically extracted from the access token's JWT payload
    Token is silently refreshed by frontend using the refresh endpoint
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            from .erp_service import ERPService
            from .erp_token_service import get_erp_token_for_store_config

            # ── Pagination params ──────────────────────────────────────────
            try:
                page = max(1, int(request.query_params.get('page', 1)))
            except (ValueError, TypeError):
                page = 1

            try:
                page_size = min(2000, max(1, int(request.query_params.get('page_size', 10))))
            except (ValueError, TypeError):
                page_size = 10

            # ── Store config ───────────────────────────────────────────────
            latitude  = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            store_id  = request.query_params.get('storeId')
            input_date_time = request.query_params.get('inputDateTime', '2021-07-01 10:10:00')

            # ── Search & Filter params ──────────────────────────────────────
            search = request.query_params.get('search')
            brand_name = request.query_params.get('brand')
            no_pagination = request.query_params.get('no_pagination', 'false').lower() == 'true'

            if latitude and longitude:
                store_info = ERPService.get_nearest_store_config(latitude, longitude)
            elif store_id:
                store_info = ERPService.get_config_by_store_id(store_id)
            else:
                store_info = ERPService._get_fallback_config()

            erp_config = store_info['erp_config']

            # ── ERP token ──────────────────────────────────────────────────
            api_key = get_erp_token_for_store_config(erp_config)
            if not api_key:
                return Response({
                    'code': '503',
                    'type': 'getMasterData',
                    'message': 'ERP service temporarily unavailable — token generation failed',
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            try:
                from .erp_redis_cache import ERPRedisCache

                # ── force_refresh query param lets admins bypass cache ─────
                force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
                erp_store_id  = erp_config['store_id']

                # ── 1. ERP Master Data — Redis cache-first ─────────────────
                all_items = None
                if not force_refresh:
                    all_items = ERPRedisCache.get_master_data(erp_store_id, input_date_time)

                if all_items is None:
                    # Cache miss → call ERP
                    erp_server_url = f"{erp_config['base_url']}/ws_c2_services_get_master_data"
                    erp_payload = {
                        'apiKey':        api_key,
                        'prodCode':      erp_config['prod_code'],
                        'c2Code':        erp_config['c2_code'],
                        'storeId':       erp_store_id,
                        'inputDateTime': input_date_time,
                        'itemcodes':     []
                    }
                    erp_response = requests.get(erp_server_url, json=erp_payload, timeout=30)

                    if erp_response.status_code != 200:
                        return Response({
                            'code': '500',
                            'type': 'getMasterData',
                            'message': f'ERP Server error: {erp_response.text}',
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    all_items = erp_response.json().get('data', []) or []
                    # Store in Redis for next requests
                    ERPRedisCache.set_master_data(erp_store_id, input_date_time, all_items)

                # ── 2. Get Global Stock Map (Redis cache-first) ─────────────
                global_stock_map = ERPRedisCache.get_global_stock_map(erp_store_id)
                if not global_stock_map:
                    global_stock_map = {}
                    try:
                        stock_server_url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
                        stock_payload = {
                            'apiKey':        api_key,
                            'prodCode':      erp_config['prod_code'],
                            'c2Code':        erp_config['c2_code'],
                            'storeId':       erp_store_id,
                            'inputDateTime': input_date_time,
                            'itemCodes':     []  # fetch all stock
                        }
                        headers = {
                            'User-Agent': 'PostmanRuntime/7.43.0',
                            'Accept': '*/*',
                            'Accept-Encoding': 'gzip, deflate',
                            'Connection': 'keep-alive'
                        }
                        stock_response = requests.post(stock_server_url, json=stock_payload, headers=headers, timeout=30, stream=True)
                        stock_items = []
                        if stock_response.status_code == 200:
                            raw_chunks = []
                            for chunk in stock_response.iter_content(chunk_size=65536):
                                if chunk:
                                    raw_chunks.append(chunk)
                            raw_bytes = b''.join(raw_chunks)
                            raw_text = raw_bytes.decode('utf-8', errors='replace').strip()
                            if raw_text.startswith('\ufeff'):
                                raw_text = raw_text[1:]
                            import re
                            raw_text = re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
                            try:
                                stock_data = json.loads(raw_text)
                                if isinstance(stock_data, dict):
                                    stock_items = stock_data.get('stockDetails', []) or stock_data.get('data', [])
                                elif isinstance(stock_data, list):
                                    stock_items = stock_data
                            except Exception as parse_err:
                                logger.error(f"Error parsing stock response: {parse_err}")

                        for s in stock_items:
                            s_code = s.get('c_item_code') or s.get('itemCode')
                            if s_code:
                                s_code = str(s_code).strip()
                                s_code_val = s.get('itemCode') or s.get('c_item_code')
                                s.pop('c_item_code', None)
                                if s_code_val:
                                    s['itemCode'] = str(s_code_val).strip()

                                if s_code not in global_stock_map:
                                    global_stock_map[s_code] = dict(s)
                                    global_stock_map[s_code]['batchDetails'] = list(s.get('batchDetails', []) or [])
                                else:
                                    global_stock_map[s_code]['batchDetails'].extend(s.get('batchDetails', []) or [])
                                    for key in ('qtyBox', 'contCode', 'contName'):
                                        if key not in global_stock_map[s_code] or global_stock_map[s_code][key] is None:
                                            global_stock_map[s_code][key] = s.get(key)

                        # Write to global stock cache (60s TTL) so search and views can reuse
                        if global_stock_map:
                            ERPRedisCache.set_global_stock_map(erp_store_id, global_stock_map)

                    except Exception as e:
                        logger.error(f"Error fetching global stock data from ERP: {e}")

                # ── 3. Populate stockBalQty & batchDetails on all items ──────
                for item in all_items:
                    item_code = str(item.get('c_item_code') or item.get('itemCode') or '').strip()
                    stock_entry = global_stock_map.get(item_code) if global_stock_map else None
                    if isinstance(stock_entry, dict):
                        batch_list = stock_entry.get('batchDetails', [])
                        if batch_list:
                            total_pack_qty = sum(int(float(b.get('packQty') or 0)) for b in batch_list)
                            item['stockBalQty'] = total_pack_qty
                        else:
                            item['stockBalQty'] = int(float(stock_entry.get('totalBalLsQty') or stock_entry.get('packQty') or 0))
                        item['batchDetails'] = batch_list
                    else:
                        item['stockBalQty'] = 0
                        item['batchDetails'] = []

                # ── 4. Stable sort: in-stock first, out-of-stock last ─────────
                all_items.sort(
                    key=lambda item: 0 if float(item.get('stockBalQty', 0) or 0) > 0 else 1
                )

                # ── 5. Paginate in-memory ──────────────────────────────────
                total_items = len(all_items)
                low_stock_count = sum(1 for item in all_items if float(item.get('stockBalQty', 0) or 0) < 5)

                if no_pagination:
                    paged_items = all_items
                    total_pages = 1
                else:
                    total_pages = max(1, (total_items + page_size - 1) // page_size)
                    page        = min(page, total_pages)
                    start       = (page - 1) * page_size
                    paged_items = all_items[start: start + page_size]

                # ── 6. Setup variables for subsequent enrichment ────────────
                page_item_codes = [
                    itm.get('c_item_code') or itm.get('itemCode')
                    for itm in paged_items
                ]
                page_item_codes = [c for c in page_item_codes if c]
                stock_map = global_stock_map

                # ── 4. Bulk pre-fetch DB records (admin-only fields) ──────────
                # ItemMaster is NOT queried here — ERP is the source for catalog fields.
                # We only fetch ProductInfo (images, description, brand assignment)
                # and Cart/Wishlist status flags.
                product_info_map = {}
                images_by_product_map = {}
                user_cart_item_codes = set()
                user_wishlist_item_codes = set()

                if page_item_codes:
                    # Query 1: ProductInfo + assigned brand (admin-managed fields)
                    product_infos = ProductInfo.objects.filter(
                        item__item_code__in=page_item_codes
                    ).select_related('category')
                    for info in product_infos:
                        product_info_map[info.item.item_code] = info

                    # Query 2: Product images in bulk
                    product_images = ProductImage.objects.filter(
                        product_info__in=product_infos
                    ).order_by('image_order')
                    for img in product_images:
                        prod_info_id = img.product_info_id
                        if prod_info_id not in images_by_product_map:
                            images_by_product_map[prod_info_id] = []
                        images_by_product_map[prod_info_id].append(img)

                    # Query 3 & 4: Cart and wishlist status flags
                    user = request.user if request.user.is_authenticated else None
                    if user:
                        try:
                            user_cart = Cart.objects.get(user=user)
                            user_cart_item_codes = set(
                                CartItem.objects.filter(
                                    cart=user_cart, item__item_code__in=page_item_codes
                                ).values_list('item__item_code', flat=True)
                            )
                        except Cart.DoesNotExist:
                            pass

                        try:
                            user_wishlist = Wishlist.objects.get(user=user)
                            user_wishlist_item_codes = set(
                                WishlistItem.objects.filter(
                                    wishlist=user_wishlist, item__item_code__in=page_item_codes
                                ).values_list('item__item_code', flat=True)
                            )
                        except Wishlist.DoesNotExist:
                            pass

                # ── 5. Enrich paged items ─────────────────────────────────
                for idx, item in enumerate(paged_items):
                    item_code = item.get('c_item_code') or item.get('itemCode')

                    # Reconstruct dict to normalise c_item_code and itemCode keys
                    new_item = {
                        'c_item_code': item_code,
                        'itemCode': item_code
                    }
                    for k, v in item.items():
                        if k not in ('c_item_code', 'itemCode'):
                            new_item[k] = v

                    # Merge stock balance and details from Redis-cached stock map
                    stock_entry = stock_map.get(str(item_code).strip()) if stock_map else None
                    if isinstance(stock_entry, dict):
                        # Merge stock_entry fields directly into new_item, avoiding overwrite of c_item_code/itemCode
                        for k, v in stock_entry.items():
                            if k not in ('c_item_code', 'itemCode'):
                                new_item[k] = v
                        
                        # Calculate stockBalQty
                        batch_list = stock_entry.get('batchDetails', [])
                        if batch_list:
                            total_pack_qty = sum(int(float(b.get('packQty') or 0)) for b in batch_list)
                            new_item['stockBalQty'] = total_pack_qty
                        else:
                            new_item['stockBalQty'] = int(float(stock_entry.get('totalBalLsQty') or stock_entry.get('packQty') or 0))
                    elif isinstance(stock_entry, (int, float)):
                        new_item['stockBalQty'] = stock_entry
                        new_item['batchDetails'] = []
                    else:
                        new_item['stockBalQty'] = 0
                        new_item['batchDetails'] = []

                    paged_items[idx] = new_item
                    item = new_item

                    # ── SOURCE 1: ERP (ws_c2_services_get_master_data) ─────
                    # These fields come DIRECTLY from the ERP response.
                    # No DB involved — ERP is the single source of truth.
                    item['contentCode']  = item.get('contentCode')  or '-'
                    item['contentName']  = item.get('contentName')  or '-'
                    item['packCode']     = item.get('packCode')      or '-'
                    item['packName']     = item.get('packName')      or '-'
                    item['hsnSacCode']   = item.get('hsnSacCode')    or '-'
                    item['hsnSacName']   = item.get('hsnSacName')    or '-'
                    item['brandCode']    = item.get('brandCode')     or '-'
                    item['brandName']    = item.get('brandName')     or '-'
                    item['categoryCode'] = item.get('categoryCode')  or '-'
                    item['categoryName'] = item.get('categoryName')  or '-'
                    item['itemFullName'] = item.get('itemFullName')  or item.get('itemName') or '-'
                    item['itemShortName']= item.get('itemShortName') or '-'
                    item['itemAddedDate']   = item.get('itemAddedDate')   or '-'
                    item['itemUpdatedDate'] = item.get('itemUpdatedDate') or '-'

                    # ── SOURCE 2: DB (ProductInfo) ──────────────────────────
                    # Only admin-managed fields: images, description,
                    # subheading, and the brand assignment made in dashboard.
                    product_info = product_info_map.get(item_code)
                    if product_info:
                        item['subheading']  = product_info.subheading  or ''
                        item['description'] = product_info.description or ''
                        item['type_label']  = product_info.type_label  or ''
                        item['brand_id']    = product_info.category.id   if product_info.category else None
                        item['brand_name']  = product_info.category.name if product_info.category else ''
                        item['brand_logo']  = (
                            request.build_absolute_uri(product_info.category.icon.url)
                            if product_info.category and product_info.category.icon else ''
                        )
                        images = images_by_product_map.get(product_info.pk, [])
                        item['images'] = [
                            {
                                'image':       request.build_absolute_uri(img.image.url),
                                'image_order': img.image_order,
                            }
                            for img in images
                        ]
                    else:
                        item['subheading'] = ''
                        item['description'] = ''
                        item['type_label']  = ''
                        item['brand_id']    = None
                        item['brand_name']  = ''
                        item['brand_logo']  = ''
                        item['images']      = []

                    # Check statuses using pre-fetched sets
                    item['cart_status']     = item_code in user_cart_item_codes
                    item['wishlist_status'] = item_code in user_wishlist_item_codes

                    # Reconstruct to return exactly the fields requested by the user
                    formatted_item = {
                        'c_item_code':     item_code,
                        'itemCode':        item_code,
                        'itemName':        item.get('itemName') or '',
                        'itemFullName':    item.get('itemFullName') or item.get('itemName') or '',
                        'maxDiscPer':      item.get('maxDiscPer', 0),
                        'stdDiscRate':     item.get('stdDiscRate', 0),
                        'itemQtyPerBox':   int(item.get('itemQtyPerBox') or item.get('qtyBox') or 1),
                        'stockBalQty':     item.get('stockBalQty', 0),
                        'batchDetails':    item.get('batchDetails', []),
                        'subheading':      item.get('subheading', ''),
                        'description':     item.get('description', ''),
                        'type_label':      item.get('type_label', ''),
                        'brand_id':        item.get('brand_id'),
                        'brand_name':      item.get('brand_name', ''),
                        'brand_logo':      item.get('brand_logo', ''),
                        'images':          item.get('images', []),
                        'cart_status':     item.get('cart_status', False),
                        'wishlist_status': item.get('wishlist_status', False),
                    }
                    paged_items[idx] = formatted_item

                if no_pagination:
                    return Response({
                        'code':    '200',
                        'type':    'getMasterData',
                        'data':    paged_items,
                        'message': f'All {len(paged_items)} items fetched without pagination',
                        'cache_source': 'redis' if not force_refresh else 'erp_fresh',
                        'c2Code':     erp_config['c2_code'],
                        'storeId':    erp_config['store_id'],
                        'prodCode':   erp_config['prod_code'],
                        'storeName':  store_info.get('store_name'),
                        'distanceKm': store_info.get('distance_km'),
                    }, status=status.HTTP_200_OK)

                return Response({
                    'code':    '200',
                    'type':    'getMasterData',
                    'data':    paged_items,
                    'message': f'Page {page} of {total_pages} ({total_items} total items)',
                    'pagination': {
                        'current_page': page,
                        'page_size':    page_size,
                        'total_items':  total_items,
                        'total_pages':  total_pages,
                        'has_next':     page < total_pages,
                        'has_previous': page > 1,
                    },

                    'cache_source': 'redis' if not force_refresh else 'erp_fresh',
                    'c2Code':     erp_config['c2_code'],
                    'storeId':    erp_config['store_id'],
                    'prodCode':   erp_config['prod_code'],
                    'storeName':  store_info.get('store_name'),
                    'distanceKm': store_info.get('distance_km'),
                }, status=status.HTTP_200_OK)

            except requests.exceptions.ConnectionError:
                return Response({
                    'code': '503',
                    'type': 'getMasterData',
                    'message': 'ERP Server is not reachable.',
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except requests.exceptions.Timeout:
                logger.error("Timeout fetching from ERP")
                return Response({
                    'code': '504',
                    'type': 'getMasterData',
                    'message': 'ERP Server request timed out.',
                }, status=status.HTTP_504_GATEWAY_TIMEOUT)
            except Exception as e:
                logger.error(f"Error fetching from ERP: {e}")
                return Response({
                    'code': '500',
                    'type': 'getMasterData',
                    'message': f'Error: {e}',
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in GetItemMasterView: {e}")
            return Response({
                'code': '500',
                'type': 'getMasterData',
                'message': f'Error: {e}',
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


# ==================== ERP REDIS CACHE MANAGEMENT ====================

class ERPCacheInvalidateView(APIView):
    """
    Invalidate ERP Redis cache for a specific store or all stores.
    POST: Flush cached master data and stock maps.

    Query params:
        store_id (optional): Invalidate only this store's cache
        (if not provided, invalidates ALL ERP cache)

    SuperAdmin only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', None) != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'erpCacheInvalidate',
                'message': 'Forbidden - Only SUPERADMIN can manage ERP cache',
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            from .erp_redis_cache import ERPRedisCache

            store_id = request.data.get('store_id') or request.query_params.get('store_id')

            if store_id:
                deleted = ERPRedisCache.invalidate_store(store_id)
                return Response({
                    'code': '200',
                    'type': 'erpCacheInvalidate',
                    'message': f'ERP cache invalidated for store {store_id}',
                    'deleted_keys': deleted,
                }, status=status.HTTP_200_OK)
            else:
                deleted = ERPRedisCache.invalidate_all_erp()
                return Response({
                    'code': '200',
                    'type': 'erpCacheInvalidate',
                    'message': 'All ERP cache invalidated',
                    'deleted_keys': deleted,
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error invalidating ERP cache: {e}")
            return Response({
                'code': '500',
                'type': 'erpCacheInvalidate',
                'message': f'Error: {e}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ERPCacheInfoView(APIView):
    """
    View diagnostic info about ERP Redis cache.
    GET: Returns cache backend, TTLs, and list of cached keys.

    Query params:
        store_id (optional): Filter info for a specific store

    SuperAdmin only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'erpCacheInfo',
                'message': 'Forbidden - Only SUPERADMIN can view ERP cache info',
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            from .erp_redis_cache import ERPRedisCache

            store_id = request.query_params.get('store_id')
            info = ERPRedisCache.get_cache_info(store_id)

            return Response({
                'code': '200',
                'type': 'erpCacheInfo',
                'data': info,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting ERP cache info: {e}")
            return Response({
                'code': '500',
                'type': 'erpCacheInfo',
                'message': f'Error: {e}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            # 🎯 Get store-specific ERP config based on location
            from .erp_service import ERPService
            from .erp_token_service import get_erp_token_for_store_config
            from .models import ItemMaster, Stock
            
            # Get customer location or store ID
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            store_id = request.query_params.get('storeId')
            input_date_time = request.query_params.get('inputDateTime', '2021-07-01 10:10:00')
            
            # Optional itemCodes query parameter (comma-separated list)
            item_codes_param = request.query_params.get('itemCodes')
            item_codes = []
            if item_codes_param:
                item_codes = [c.strip() for c in item_codes_param.split(',') if c.strip()]
            
            # Select store based on location or store_id
            if latitude and longitude:
                store_info = ERPService.get_nearest_store_config(latitude, longitude)
            elif store_id:
                store_info = ERPService.get_config_by_store_id(store_id)
            else:
                store_info = ERPService._get_fallback_config()
            
            erp_config = store_info['erp_config']
            logger.info(f"[FETCH_STOCK] Using store: {store_info.get('store_name')} | Store ID: {erp_config['store_id']}")
            
            # ✅ STEP 2 & 3: Generate token PER STORE with storeId
            api_key = get_erp_token_for_store_config(erp_config)
            if not api_key:
                return Response({
                    'code': '503',
                    'type': 'fetchStock',
                    'message': 'ERP service temporarily unavailable - token generation failed'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            logger.info(f"[FETCH_STOCK] [OK] Token generated for store {erp_config['store_id']}")
            
            try:
                # FETCH DIRECTLY FROM ERP SERVER (real-time stock data)
                erp_server_url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
                
                logger.info(f"[FETCH_STOCK] Fetching from ERP: {erp_server_url}")
                
                # Build ERP request payload (matches Postman body)
                erp_payload = {
                    'apiKey': api_key,
                    'storeId': erp_config['store_id'],
                    'c2Code': erp_config['c2_code'],
                    'prodCode': erp_config['prod_code'],
                    'inputDateTime': input_date_time,
                    'itemCodes': item_codes
                }
                
                # Mimic Postman headers to force gzip compression and bypass ERP 80KB limit
                headers = {
                    'User-Agent': 'PostmanRuntime/7.43.0',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
                
                import sys, urllib3, json as json_lib
                logger.info(f"[FETCH_STOCK] [VERSION_CHECK] Python: {sys.version} | Requests: {requests.__version__} | Urllib3: {urllib3.__version__}")
                logger.info(f"[FETCH_STOCK] Sending GET request to ERP server")
                
                # Use stream=True + iter_content to fully assemble chunked TCP response
                # This bypasses urllib3 chunked-read truncation inside Django threads
                erp_response = requests.get(erp_server_url, json=erp_payload, headers=headers, timeout=30, stream=True)
                
                if erp_response.status_code != 200:
                    logger.error(f"ERP Server error: {erp_response.status_code}")
                    return Response({
                        'code': '500',
                        'type': 'fetchStock',
                        'message': f'ERP Server error: HTTP {erp_response.status_code}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Read all chunks and assemble into a single bytes object
                raw_chunks = []
                for chunk in erp_response.iter_content(chunk_size=65536):
                    if chunk:
                        raw_chunks.append(chunk)
                raw_bytes = b''.join(raw_chunks)
                logger.info(f"[FETCH_STOCK] Received {len(raw_bytes)} bytes from ERP")
                
                # ERP sends invalid JSON: bare decimals like "mrp":.861 instead of "mrp":0.861
                # Fix by adding leading zero before any bare decimal number in JSON values
                import re
                raw_text = raw_bytes.decode('utf-8', errors='replace')
                raw_text = re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
                
                try:
                    erp_data = json_lib.loads(raw_text)
                except (ValueError, UnicodeDecodeError) as json_err:
                    snippet = raw_text[:1000]
                    logger.error(f"[FETCH_STOCK] Failed to parse JSON from ERP: {str(json_err)}. Snippet: {snippet}")
                    return Response({
                        'code': '502',
                        'type': 'fetchStock',
                        'message': f'Invalid JSON response from ERP: {str(json_err)}',
                        'response_snippet': snippet
                    }, status=status.HTTP_502_BAD_GATEWAY)
                
                # Handle both dict and list responses
                if isinstance(erp_data, dict):
                    stock_items = erp_data.get('stockDetails', []) or erp_data.get('data', [])
                elif isinstance(erp_data, list):
                    stock_items = erp_data
                else:
                    stock_items = []
                
                # Normalize keys
                for item in stock_items:
                    item_code_val = item.get('itemCode') or item.get('c_item_code')
                    # Remove internal c_item_code key — itemCode is the standard field
                    item.pop('c_item_code', None)
                    if item_code_val:
                        item['itemCode'] = item_code_val
                
                logger.info(f"[FETCH_STOCK] Fetched {len(stock_items)} stock items from ERP server")
                
                return Response({
                    'stockDetails': stock_items
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        # ── Debug incoming request ──
        logger.info(f"[ORDER_DEBUG] Request data: {request.data}")
        
        serializer = CreateSalesOrderRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"[ORDER_VALIDATION] Errors: {serializer.errors}")
            return Response({
                'code': '400',
                'type': 'SaleOrderCreate',
                'message': 'Invalid parameters',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"[ORDER_DEBUG] Validated data: {serializer.validated_data}")

        payment_mode = serializer.validated_data.get('paymentMode', 'COD')
        if payment_mode not in ['COD', 'RAZORPAY']:
            return Response({
                'code': '400',
                'type': 'SaleOrderCreate',
                'message': f'Invalid payment mode: {payment_mode}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 🎯 Get store-specific ERP config based on location or storeId
        from .erp_service import ERPService
        from .erp_token_service import get_erp_token_for_store_config
        
        # Get customer location or store ID from request
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        store_id = request.data.get('storeId')
        
        # Select store based on location or store_id
        if latitude and longitude:
            store_info = ERPService.get_nearest_store_config(latitude, longitude)
        elif store_id:
            store_info = ERPService.get_config_by_store_id(store_id)
        else:
            store_info = ERPService._get_fallback_config()
        
        erp_config = store_info['erp_config']
        logger.info(f"[CREATE_ORDER] Using store: {store_info.get('store_name')} | Store ID: {erp_config['store_id']}")
        
        # ✅ STEP 2 & 3: Generate token PER STORE with storeId
        api_key = get_erp_token_for_store_config(erp_config)
        if not api_key:
            return Response({
                'code': '503',
                'type': 'SaleOrderCreate',
                'message': 'ERP service temporarily unavailable'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            with transaction.atomic():

                # ── Safe value extraction helpers ──
                def safe_str(val, default=''):
                    if val is None:
                        return default
                    s = str(val).strip()
                    return s if s else default

                def safe_float(val, default=0.0):
                    try:
                        return float(val) if val is not None else default
                    except (ValueError, TypeError):
                        return default

                def safe_int(val, default=0):
                    try:
                        return int(val) if val is not None else default
                    except (ValueError, TypeError):
                        return default

                def safe_bool(val, default=False):
                    try:
                        return bool(int(str(val))) if val is not None else default
                    except (ValueError, TypeError):
                        return default

                def safe_email(val):
                    # EmailField cannot store '' — must be None
                    if not val:
                        return None
                    s = str(val).strip()
                    return s if s and '@' in s else None

                def safe_ip(val):
                    # GenericIPAddressField cannot store '' — must be None
                    if not val:
                        return None
                    s = str(val).strip()
                    return s if s else None

                order_total = safe_float(serializer.validated_data.get('orderTotal'))

                # ── ERP config (from store database) ──
                store_id_val = safe_str(erp_config['store_id'])
                store_id = store_id_val.zfill(3)
                c2_code = safe_str(erp_config['c2_code'])
                prod_code = safe_str(erp_config['prod_code'])

                # ── Generate order ID ──
                date_str = timezone.now().strftime('%Y%m%d')
                time_str = timezone.now().strftime('%H%M%S')
                unique_suffix = str(uuid.uuid4())[:8].upper()
                order_id = f"{store_id}{date_str}{time_str}{unique_suffix}"
                logger.info(f"[ORDER_ID] Generated: {order_id}")

                # ── Capture IP from request ──
                client_ip = safe_ip(get_client_ip(request))
                
                # Always use JWT token's user ID — IsAuthenticated guarantees request.user is valid
                user_id_raw = str(request.user.id)

                # ── Build order_kwargs with all safe values ──
                order_kwargs = dict(
                    c2_code=c2_code,
                    store_id=store_id_val,
                    order_id=order_id,
                    ip_no=safe_str(serializer.validated_data.get('ipNo')),
                    mobile_no=safe_str(serializer.validated_data.get('mobileNo')),
                    patient_name=safe_str(serializer.validated_data.get('patientName')),
                    patient_address=safe_str(serializer.validated_data.get('patientAddress')),
                    patient_email=safe_email(serializer.validated_data.get('patientEmail')),
                    counter_sale=safe_bool(serializer.validated_data.get('counterSale', 0)),
                    ord_date=serializer.validated_data.get('ordDate') or timezone.now().date(),
                    ord_time=serializer.validated_data.get('ordTime') or timezone.now().time(),
                    user_id=user_id_raw,
                    cust_code=safe_str(serializer.validated_data.get('actCode')),
                    cust_name=safe_str(serializer.validated_data.get('actName')),
                    dr_code=safe_str(serializer.validated_data.get('drCode')),
                    dr_name=safe_str(serializer.validated_data.get('drName')),
                    dr_address=safe_str(serializer.validated_data.get('drAddress')),
                    dr_reg_no=safe_str(serializer.validated_data.get('drRegNo')),
                    dr_office_code=safe_str(serializer.validated_data.get('drOfficeCode'), '-'),
                    dman_code=safe_str(serializer.validated_data.get('dmanCode'), '-'),
                    order_total=order_total,
                    order_disc_per=safe_float(serializer.validated_data.get('orderDiscPer')),
                    ref_no=serializer.validated_data.get('refNo') or None,
                    remark=serializer.validated_data.get('remark') or None,
                    urgent_flag=safe_bool(serializer.validated_data.get('urgentFlag', 0)),
                    ord_conversion_flag=safe_bool(serializer.validated_data.get('ordConversionFlag', 0)),
                    dc_conversion_flag=safe_bool(serializer.validated_data.get('dcConversionFlag', 0)),
                    ord_ref_no=safe_int(serializer.validated_data.get('ordRefNo')),
                    sys_name=safe_str(serializer.validated_data.get('sysName')),
                    sys_ip=client_ip,        # safe None if empty
                    sys_user=safe_str(serializer.validated_data.get('sysUser')),
                    br_code=store_id_val,
                    tran_year=str(timezone.now().year % 100),
                    tran_prefix='6',
                    tran_srno='1',
                    bill_total=order_total,
                    fulfilling_store_id=store_info.get('store_db_id'),  # ✅ Assign fulfilling store for backend order tracking
                )

                logger.info(f"[ORDER_DEBUG] order_kwargs built successfully")

                # ── Create SalesOrder with retry ──
                from django.db import IntegrityError
                sales_order = None
                for attempt in range(2):
                    try:
                        sales_order = SalesOrder.objects.create(**order_kwargs)
                        logger.info(f"[ORDER_DEBUG] SalesOrder created: id={sales_order.id}")
                        break
                    except IntegrityError as ie:
                        logger.error(f"[ORDER_INTEGRITY] Attempt {attempt+1}: {str(ie)}")
                        if attempt == 0:
                            time_str_retry = timezone.now().strftime('%H%M%S%f')[:8]
                            unique_suffix_retry = str(uuid.uuid4())[:8].upper()
                            order_id = f"{store_id}{date_str}{time_str_retry}{unique_suffix_retry}"
                            order_kwargs['order_id'] = order_id
                        else:
                            raise

                if not sales_order:
                    return Response({
                        'code': '500',
                        'type': 'SaleOrderCreate',
                        'message': 'Failed to create order after retries.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # ── Create line items ──
                material_info = serializer.validated_data.get('materialInfo') or []
                logger.info(f"[ORDER_DEBUG] Processing {len(material_info)} line items")

                # ── Validate item_code values before creating items ──
                invalid_items = []
                for idx, item in enumerate(material_info):
                    item_code = safe_str(item.get('item_code'))
                    if not item_code:
                        invalid_items.append(idx)
                
                if invalid_items:
                    logger.error(
                        f"[ORDER_VALIDATION] Items with missing item_code at indices: {invalid_items}. "
                        f"Cannot proceed without valid item codes."
                    )
                    # Delete the order since items are invalid
                    sales_order.delete()
                    return Response({
                        'code': '400',
                        'type': 'SaleOrderCreate',
                        'message': f'Invalid items: missing item_code at positions {[i+1 for i in invalid_items]}. '
                                   f'All items must have valid item codes.',
                        'invalid_item_indices': invalid_items
                    }, status=status.HTTP_400_BAD_REQUEST)

                # ── Track used item_seq to prevent duplicates ──
                used_item_seqs = set()

                # ✅ PRODUCTION-GRADE CHECKOUT: Validate stock with SELECT_FOR_UPDATE locking
                # Prevents race conditions when multiple users order the same item simultaneously
                # ✅ Validate each item exists in ItemMaster
                # (Stock management handled by ERP, not local database)
                for item_data in material_info:
                    item_code = safe_str(item_data.get('item_code'))
                    
                    # Validate item exists in ItemMaster
                    try:
                        ItemMaster.objects.get(item_code=item_code)
                        logger.info(f"[CHECKOUT] Item {item_code} validated in ItemMaster")
                    except ItemMaster.DoesNotExist:
                        sales_order.delete()
                        error_msg = f"Item {item_code} not found in system. Please verify item code."
                        logger.error(f"[CHECKOUT] Item validation failed: {error_msg}")
                        return Response({
                            'code': '400',
                            'type': 'SaleOrderCreate',
                            'message': error_msg
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                logger.info(f"[CHECKOUT] All items validated successfully - order can proceed")

                for idx, item in enumerate(material_info):
                    item_seq = safe_int(item.get('item_seq'), idx + 1)
                    
                    # ── Ensure item_seq is unique ──
                    if item_seq in used_item_seqs:
                        logger.warning(
                            f"[ORDER_ITEMS] Duplicate item_seq {item_seq} at index {idx}, "
                            f"reassigning to next available"
                        )
                        # Find next available item_seq
                        next_seq = max(used_item_seqs) + 1 if used_item_seqs else 1
                        while next_seq in used_item_seqs:
                            next_seq += 1
                        item_seq = next_seq
                    
                    used_item_seqs.add(item_seq)
                    
                    qty = safe_int(item.get('total_loose_qty'))
                    sale_rate = safe_float(item.get('sale_rate'))
                    disc_per = safe_float(item.get('disc_per'))
                    sch_disc_per = safe_float(item.get('sch_disc_per'))
                    item_total = round(sale_rate * (1 - disc_per / 100) * qty, 2)

                    logger.info(
                        f"[ORDER_DEBUG] Item {idx+1}: "
                        f"code={item.get('item_code')} "
                        f"qty={qty} rate={sale_rate} total={item_total}"
                    )

                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        item_seq=item_seq,
                        item_code=safe_str(item.get('item_code')),
                        item_name=safe_str(item.get('item_name')),
                        batch_no=item.get('batch_no') or None,
                        expiry_date=item.get('expiry_date') or None,
                        total_loose_qty=qty,
                        total_loose_sch_qty=safe_int(item.get('total_loose_sch_qty')),
                        service_qty=safe_int(item.get('service_qty')),
                        sale_rate=sale_rate,
                        disc_per=disc_per,
                        sch_disc_per=sch_disc_per,
                        item_total=item_total,
                    )

                # ── Recalculate total if 0 ──
                provided_total = safe_float(serializer.validated_data.get('orderTotal'))
                if provided_total == 0 and material_info:
                    actual_total = round(sum(
                        safe_float(i.get('sale_rate'))
                        * (1 - safe_float(i.get('disc_per')) / 100)
                        * safe_int(i.get('total_loose_qty'))
                        for i in material_info
                    ), 2)
                    sales_order.order_total = actual_total
                    sales_order.bill_total = actual_total
                    logger.info(f"[ORDER_DEBUG] Auto-calculated total: {actual_total}")

                # ── document_pk ──
                sales_order.document_pk = (
                    f"{sales_order.tran_year}"
                    f"{sales_order.br_code}"
                    f"{sales_order.tran_prefix}"
                    f"{sales_order.id}"
                )
                sales_order.save()
                logger.info(f"[ORDER_DEBUG] document_pk: {sales_order.document_pk}")

                # ── WALLET HANDLING - ONLY STORE INTENT, APPLY AFTER PAYMENT SUCCEEDS ──
                # ✅ FIX: Don't deduct wallet here - only track that user wants to use wallet
                # Wallet will be applied ONLY AFTER payment succeeds (in VerifyPaymentView/WebhookView)
                wallet_requested = serializer.validated_data.get('use_wallet', False)
                wallet_intent_user_id = serializer.validated_data.get('user_id') if wallet_requested else None
                
                # Store wallet intent in order for later reference
                sales_order.wallet_requested = wallet_requested
                sales_order.wallet_intent_user_id = wallet_intent_user_id
                sales_order.save()
                
                logger.info(
                    f"[WALLET_INTENT] Order: {sales_order.order_id} | "
                    f"Wallet Requested: {wallet_requested} | "
                    f"Will be applied AFTER payment succeeds"
                )
                wallet_deducted = Decimal('0')  # Nothing deducted yet

                # ── SYNC ORDER TO ERP SERVER ──
                # Build ERP payload with all items
                erp_material_info = []
                for order_item in SalesOrderItem.objects.filter(sales_order=sales_order).order_by('item_seq'):
                    erp_material_info.append({
                        "itemSeq": order_item.item_seq,
                        "itemcode": order_item.item_code,  # ERP field: lowercase 'c'
                        "totalLooseQty": order_item.total_loose_qty,
                        "totalLooseSchQty": order_item.total_loose_sch_qty,
                        "serviceQty": order_item.service_qty,
                        "saleRate": str(order_item.sale_rate),  # ERP expects string
                        "discPer": str(order_item.disc_per),    # ERP expects string
                        "schDiscPer": str(order_item.sch_disc_per),
                    })

                erp_payload = {
                    "c2Code": c2_code,
                    "storeId": store_id_val,
                    "prodCode": prod_code,
                    "apiKey": api_key,  # Already generated at start of post()
                    "ipNo": sales_order.ip_no,
                    "mobileNo": sales_order.mobile_no,
                    "patientName": sales_order.patient_name,
                    "patientAddress": sales_order.patient_address,
                    "patientEmail": sales_order.patient_email or '',
                    "counterSale": "1" if sales_order.counter_sale else "0",
                    "ordDate": str(sales_order.ord_date),
                    "ordTime": str(sales_order.ord_time),
                    "userId": sales_order.user_id,
                    "actCode": sales_order.cust_code or 'GC01',
                    "actName": sales_order.cust_name or sales_order.patient_name or 'General Customer',
                    "drCode": sales_order.dr_code or 'GD01',
                    "drName": sales_order.dr_name or '',
                    "drAddress": sales_order.dr_address or '',
                    "drRegNo": sales_order.dr_reg_no or '',
                    "drOfficeCode": sales_order.dr_office_code or '-',
                    "dmanCode": sales_order.dman_code or '-',
                    "orderTotal": str(sales_order.order_total),
                    "orderDiscPer": str(sales_order.order_disc_per),
                    "refNo": sales_order.ref_no or 0,
                    "orderId": sales_order.order_id,  # ERP spec: orderId in request body
                    "remark": sales_order.remark or '',
                    "urgentFlag": 1 if sales_order.urgent_flag else 0,
                    "ordConversionFlag": 1 if sales_order.ord_conversion_flag else 0,
                    "dcConversionFlag": 1 if sales_order.dc_conversion_flag else 0,
                    "ordRefNo": sales_order.ord_ref_no or 0,
                    "sysName": sales_order.sys_name or '',
                    "sysIp": sales_order.sys_ip or '',  # actual request IP
                    "sysUser": sales_order.sys_user or '',
                    "materialInfo": erp_material_info,
                }

                # Send to ERP
                erp_sync_success = False
                sync_err_msg = None
                try:
                    erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_create_sale_order"
                    logger.info(f"[ERP_SYNC] Syncing order {sales_order.order_id} to ERP: {erp_url}")
                    
                    erp_response = requests.post(erp_url, json=erp_payload, timeout=15)
                    
                    # Accept both 200 OK and 201 Created as success
                    if erp_response.status_code in [200, 201]:
                        import json as _json
                        import re as _re
                        raw_text = erp_response.text
                        raw_text = _re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
                        erp_data = _json.loads(raw_text)
                        erp_message = erp_data.get('message', '') or ''
                        if erp_data.get('code') == '200' or 'Order Number Already Exists' in erp_message:
                            logger.info(
                                f"[ERP_SYNC] [SUCCESS] Order {sales_order.order_id} accepted by ERP (or already exists) | "
                                f"ERP message: {erp_message}"
                            )
                            erp_sync_success = True
                        else:
                            sync_err_msg = f"ERP rejected order: {erp_message}"
                            logger.error(f"[ERP_SYNC] {sync_err_msg}")
                    else:
                        sync_err_msg = f"HTTP {erp_response.status_code} from ERP: {erp_response.text[:300]}"
                        logger.error(f"[ERP_SYNC] {sync_err_msg}")
                except requests.exceptions.Timeout:
                    sync_err_msg = f"Timeout syncing order to ERP"
                    logger.error(f"[ERP_SYNC] {sync_err_msg}")
                except requests.exceptions.ConnectionError:
                    sync_err_msg = f"Cannot reach ERP server (offline)"
                    logger.error(f"[ERP_SYNC] {sync_err_msg}")
                except Exception as e:
                    sync_err_msg = f"Unexpected error: {str(e)}"
                    logger.error(f"[ERP_SYNC] {sync_err_msg}", exc_info=True)

                # ── Save ERP sync status to sales_order (Outbox pattern) ──
                sales_order.is_erp_synced = erp_sync_success
                sales_order.erp_sync_payload = erp_payload
                sales_order.erp_sync_error = sync_err_msg if not erp_sync_success else None
                sales_order.last_erp_sync_attempt = timezone.now()
                sales_order.save(update_fields=['is_erp_synced', 'erp_sync_payload', 'erp_sync_error', 'last_erp_sync_attempt'])

                if not erp_sync_success:
                    logger.warning(
                        f"[ERP_SYNC] Order {order_id} saved locally but ERP sync failed — "
                        f"outbox retry worker will re-attempt order push in background"
                    )

                # NOTE: Cart will be cleared AFTER payment succeeds via webhook or VerifyPaymentView
                # Do NOT clear cart here - user might cancel payment and need to retry

                # ── Background invoice sync ──
                # Only spawn if ERP sync succeeded, or spawn anyway to retry
                import threading
                from .services import sync_invoice_from_erp
                thread = threading.Thread(
                    target=sync_invoice_from_erp,
                    args=(sales_order.order_id, sales_order.c2_code, sales_order.store_id),
                    daemon=True
                )
                thread.start()

                return Response({
                    'code': '200',
                    'type': 'SaleOrderCreate',
                    'message': f'Document No. : {sales_order.document_pk} successfully processed.',
                    'paymentMode': payment_mode,
                    'walletApplied': str(wallet_deducted),
                    'amountToPay': str(sales_order.bill_total),
                    'paymentDetails': {
                        'mode': payment_mode,
                        'amount': str(sales_order.bill_total),
                        'walletDeducted': str(wallet_deducted),
                        'currency': 'INR'
                    },
                    'config': {
                        'c2Code': erp_config['c2_code'],
                        'storeId': erp_config['store_id'],
                        'prodCode': erp_config['prod_code'],
                        'storeName': store_info.get('store_name', 'Default Store'),
                    },
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
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"[ORDER_ERROR] {str(e)}\n{tb}")
            return Response({
                'code': '500',
                'type': 'SaleOrderCreate',
                'message': str(e),
                'traceback': tb   # remove before production
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    
    Flow:
    1. Check local database for invoices
    2. If not found, sync from ERP (invoices are generated server-side after sales order creation)
    3. Return invoice details to client
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Parse request parameters
        order_id = request.query_params.get('orderId')
        
        if not order_id:
            return Response({
                'code': '400',
                'message': 'Missing required parameter: orderId'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 1. Get sales order by order_id first to resolve store and c2_code dynamically
            sales_order = SalesOrder.objects.get(order_id=order_id)
            
            # 2. Determine store_id (from query parameter, order, or settings fallback)
            store_id = request.query_params.get('storeId') or sales_order.store_id or settings.ERP_STORE_ID
            
            # 3. Fetch store ERP configuration dynamically
            from .erp_service import ERPService
            store_info = ERPService.get_config_by_store_id(store_id) if store_id else None
            if not store_info:
                store_info = ERPService._get_fallback_config()
                
            erp_config = store_info['erp_config']
            
            # Determine c2_code (from query parameter, order, or store config fallback)
            c2_code = request.query_params.get('c2Code') or sales_order.c2_code or erp_config.get('c2_code') or settings.ERP_C2_CODE
            
            # 4. Generate/Fetch token dynamically for this store config
            from .erp_token_service import get_erp_token_for_store_config
            api_key = get_erp_token_for_store_config(erp_config)
            
            if not api_key:
                return Response({
                    'code': '503',
                    'message': 'ERP service temporarily unavailable (token missing)'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Get invoices for this order
            invoices = Invoice.objects.filter(sales_order=sales_order)
            
            # If no invoices found, try syncing from ERP
            if not invoices.exists():
                logger.info(f"[ORDER_STATUS] No invoices found locally for order {order_id}. Syncing from ERP...")
                
                from .services import sync_invoice_from_erp
                # Sync synchronously to ensure invoices are available for this response
                sync_success = sync_invoice_from_erp(
                    order_id=order_id,
                    c2_code=c2_code,
                    store_id=store_id,
                    max_retries=3
                )
                
                if sync_success:
                    # Retrieve invoices again after sync
                    invoices = Invoice.objects.filter(sales_order=sales_order)
                    logger.info(f"[ORDER_STATUS] [OK] Successfully synced {invoices.count()} invoice(s)")
                else:
                    logger.warning(f"[ORDER_STATUS] Failed to sync invoices from ERP for order {order_id}")
            
            # Build response
            response_data = {
                'code': '200',
                'orderId': sales_order.order_id,
                'custCode': sales_order.cust_code,
                'fromGstNo': '07NQQAE5107K2ZW',  # Replace with actual GST from backend settings
                'toGstNo': '07NQQAE5107K2ZW',    # Replace with actual GST from customer data
                'customerType': 'Un - Registered',
                'doctorName': sales_order.dr_name or '-',
                'invoices': []
            }
            
            # Serialize invoices with all details
            invoice_serializer = InvoiceForStatusSerializer(invoices, many=True)
            response_data['invoices'] = invoice_serializer.data
            
            # Log successful retrieval
            logger.info(f"[ORDER_STATUS] [OK] Retrieved order status | Order: {order_id} | Invoices: {invoices.count()}")
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except SalesOrder.DoesNotExist:
            logger.warning(f"[ORDER_STATUS] Order not found: {order_id}")
            return Response({
                'code': '404',
                'message': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"[ORDER_STATUS] Error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
        user = request.user
        
        cart, created = Cart.objects.get_or_create(user=user)
        
        # 1. Update stock and price in DB for all items first
        for cart_item in cart.items.all():
            get_item_stock_status(cart_item.item.item_code)
            
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
            item['current_price'] = str(round(stock_status.get('price', float(item.get('mrpBox', 0))), 2))
            item['current_discount'] = round(stock_status.get('discount', 0), 2)
        
        return Response({
            'success': True,
            'message': 'Cart retrieved successfully',
            'data': cart_data
        }, status=status.HTTP_200_OK)
    
    def delete(self, request):
        user = request.user
        
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
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
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
        store_id = serializer.validated_data.get('storeId')
        # [UPDATED] Token now auto-generated - no need for apiKey from request
        
        # Get user from authenticated request
        user = request.user
            
        if not store_id and user.preferred_store:
            store_id = user.preferred_store.store_id
        
        # ─── STEP 1: All ERP calls OUTSIDE transaction (slow HTTP, don't hold DB lock) ───
        # Fetch fresh item details from ERP
        item_data = fetch_item_from_erp(item_code, store_id=store_id)

        item = None
        if item_data:
            item = update_itemmaster_cache(item_code, item_data)
        else:
            item = ItemMaster.objects.filter(item_code=item_code).first()

        # If still not found, auto-create from stock response
        if not item:
            try:
                from .erp_token_service import get_erp_token_for_store_config
                from .erp_service import ERPService
                store_info = ERPService.get_config_by_store_id(store_id) if store_id else ERPService._get_fallback_config()
                if store_info:
                    erp_config = store_info['erp_config']
                    api_key = get_erp_token_for_store_config(erp_config)
                    if api_key:
                        erp_url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
                        erp_payload = {
                            'apiKey':        api_key,
                            'prodCode':      erp_config['prod_code'],
                            'c2Code':        erp_config['c2_code'],
                            'storeId':       erp_config['store_id'],
                            'inputDateTime': '2021-07-01 10:10:00',
                            'itemCodes':     [item_code]
                        }
                        response = requests.post(erp_url, json=erp_payload, timeout=60)
                        if response.status_code == 200:
                            try:
                                raw_text = response.text
                                raw_text = re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
                                stock_data = json.loads(raw_text)
                            except Exception:
                                stock_data = {}
                            stock_items = []
                            if isinstance(stock_data, dict):
                                stock_items = stock_data.get('stockDetails', []) or stock_data.get('data', [])
                            elif isinstance(stock_data, list):
                                stock_items = stock_data
                            for s_item in stock_items:
                                item_code_val = s_item.get('c_item_code') or s_item.get('itemCode')
                                if str(item_code_val) == str(item_code):
                                    batch_list = s_item.get('batchDetails', [])
                                    first_batch = batch_list[0] if batch_list else {}
                                    batch_no = first_batch.get('batchNo', '')
                                    expiry_date_str = first_batch.get('expiryDate', '')
                                    mrp_val = first_batch.get('mrpBox') or first_batch.get('mrp', 0.0)
                                    try:
                                        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else datetime(2099, 12, 31).date()
                                    except Exception:
                                        expiry_date = datetime(2099, 12, 31).date()
                                    item, _ = ItemMaster.objects.get_or_create(
                                        item_code=item_code,
                                        defaults={
                                            'item_name': s_item.get('itemName') or 'Unknown Product',
                                            'item_qty_per_box': int(s_item.get('qtyBox', 1)),
                                            'batch_no': batch_no,
                                            'std_disc': 0.0,
                                            'max_disc': 0.0,
                                            'mrp': float(mrp_val),
                                            'expiry_date': expiry_date,
                                        }
                                    )
                                    ProductInfo.objects.get_or_create(
                                        item=item,
                                        defaults={
                                            'type_label': s_item.get('contName') or 'Medicine',
                                            'description': 'Real-time stock product'
                                        }
                                    )
                                    break
            except Exception as e:
                logger.error(f"Error auto-creating ItemMaster from stock response: {str(e)}")

        if not item:
            return Response({
                'success': False,
                'message': 'Product not found in system or ERP master.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check stock availability BEFORE entering transaction (ERP call outside lock)
        stock_status = get_item_stock_status(item_code, store_id=store_id)
        if not stock_status['available']:
            logger.warning(f"User {user.id} tried to add unavailable item {item_code} - Status: {stock_status['status']}")
            return Response({
                'success': False,
                'message': f'{item.item_name} is {stock_status["status"]}',
                'status': stock_status['status'],
                'available_qty': stock_status['qty'],
                'expiry_date': stock_status.get('expiry_date'),
                'is_expired': stock_status.get('is_expired')
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check against TOTAL quantity (already in cart + newly requested)
        existing_cart_qty = 0
        try:
            existing_cart = Cart.objects.filter(user=user).first()
            if existing_cart:
                existing_item = CartItem.objects.filter(cart=existing_cart, item__item_code=item_code).first()
                if existing_item:
                    existing_cart_qty = existing_item.quantity
        except Exception:
            existing_cart_qty = 0

        total_requested_qty = existing_cart_qty + quantity
        if total_requested_qty > stock_status['qty']:
            remaining = max(0, stock_status['qty'] - existing_cart_qty)
            logger.warning(
                f"User {user.id} requested {quantity} units (already has {existing_cart_qty} in cart, "
                f"total={total_requested_qty}) but only {stock_status['qty']} available for {item_code}"
            )
            return Response({
                'success': False,
                'message': (
                    f'Cannot add {quantity} units. You already have {existing_cart_qty} in cart. '
                    f'Only {remaining} more unit(s) can be added (max {stock_status["qty"]} total).'
                ) if existing_cart_qty > 0 else f'Only {stock_status["qty"]} units available',
                'requested': quantity,
                'existing_in_cart': existing_cart_qty,
                'total_requested': total_requested_qty,
                'available_qty': stock_status['qty'],
                'can_add': remaining
            }, status=status.HTTP_400_BAD_REQUEST)

        # Reload item from database to get the fresh MRP and details updated by get_item_stock_status
        item = ItemMaster.objects.get(item_code=item_code)

        # Get active store_id for stock locking
        from .erp_service import ERPService
        store_info = ERPService.get_config_by_store_id(store_id) if store_id else ERPService._get_fallback_config()
        active_store_id = store_info['erp_config']['store_id'] if store_info else (store_id or '001')

        # ─── STEP 2: Atomic transaction ONLY for DB writes (fast, minimal lock time) ───
        try:
            with transaction.atomic():
                # Lock only during DB write — no ERP calls inside here
                try:
                    stock_record = Stock.objects.select_for_update().filter(
                        item__item_code=item_code,
                        store_id=active_store_id
                    ).first()
                except Exception:
                    stock_record = None

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
                
                item_serializer = CartItemSmallSerializer(cart_item)
                item_data = item_serializer.data
                
                # Add stock status to response
                stock_status = get_item_stock_status(item_code)
                item_data['availability'] = stock_status.get('status', 'Unknown')
                item_data['available_qty'] = stock_status.get('qty', 0)
                item_data['in_stock'] = stock_status.get('available', False)
                item_data['current_price'] = str(round(stock_status.get('price', float(item_data.get('mrpBox', 0))), 2))
                item_data['current_discount'] = round(stock_status.get('discount', 0), 2)
                
                # ── Show wallet balance (preview only - no deduction) ──
                wallet_balance = Decimal('0.00')
                try:
                    wallet = RetailerWallet.objects.get(retailer=user)
                    wallet_balance = wallet.balance
                except RetailerWallet.DoesNotExist:
                    wallet, _ = RetailerWallet.objects.get_or_create(retailer=user)
                    wallet_balance = wallet.balance
                
                return Response({
                    'success': True,
                    'message': f'{item.item_name} added to cart' if created else f'{item.item_name} quantity updated',
                    'data': item_data,
                    'wallet': {
                        'balance': str(round(wallet_balance, 2)),
                        'can_apply': wallet_balance > 0
                    }
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        except Exception as e:
            # Transaction automatically rolled back
            logger.error(f"[CART_ERROR] User: {request.user.id} | Item: {item_code} | Error: {str(e)}", exc_info=True)
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
        # Get user from authenticated request
        user = request.user
        
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

            new_quantity = serializer.validated_data['quantity']
            item_code = cart_item.item.item_code

            # Validate against live packQty from ERP before saving
            stock_status = get_item_stock_status(item_code)
            if not stock_status['available']:
                return Response({
                    'success': False,
                    'message': f'{cart_item.item.item_name} is {stock_status["status"]}',
                    'status': stock_status['status'],
                    'available_qty': stock_status['qty'],
                    'is_expired': stock_status.get('is_expired')
                }, status=status.HTTP_400_BAD_REQUEST)

            if new_quantity > stock_status['qty']:
                logger.warning(
                    f"[CART_UPDATE] User {user.id} tried to set qty={new_quantity} "
                    f"but only {stock_status['qty']} available for {item_code}"
                )
                return Response({
                    'success': False,
                    'message': f'Only {stock_status["qty"]} units available. Cannot set quantity to {new_quantity}.',
                    'requested': new_quantity,
                    'available_qty': stock_status['qty']
                }, status=status.HTTP_400_BAD_REQUEST)

            cart_item.quantity = new_quantity
            cart_item.save()

            # Refresh cart_item from DB to get the updated ItemMaster fields
            cart_item.refresh_from_db()

            item_serializer = CartItemSmallSerializer(cart_item)
            item_data = item_serializer.data

            item_data['availability'] = stock_status.get('status', 'Unknown')
            item_data['available_qty'] = stock_status.get('qty', 0)
            item_data['in_stock'] = stock_status.get('available', False)
            item_data['current_price'] = str(round(stock_status.get('price', float(item_data.get('mrpBox', 0))), 2))
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
        # Get user from authenticated request
        user = request.user
        
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
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        """
        Increase or decrease wishlist item quantity.
        Request body: { "quantity": <int> }
        """
        from .models import Wishlist, WishlistItem
        
        # Get user from authenticated request
        user = request.user
        
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
            
            # Enrich items before serialization
            store_id = request.query_params.get('storeId')
            if not store_id and user.preferred_store:
                store_id = user.preferred_store.store_id
            wishlist_items = list(wishlist.items.all())
            enrich_wishlist_items(wishlist_items, store_id=store_id)
            wishlist._prefetched_objects_cache = {'items': wishlist_items}

            from .serializers import WishlistSerializer
            wishlist_serializer = WishlistSerializer(wishlist, context={'request': request})
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
            logger.info(f"[WISHLIST_UPDATE] User: {request.user.id} ({request.user.username}) | WishlistItem: {item_id} | Quantity: {quantity}")
            
            # Enrich items before serialization
            store_id = request.query_params.get('storeId')
            if not store_id and user.preferred_store:
                store_id = user.preferred_store.store_id
            wishlist_items = list(wishlist.items.all())
            enrich_wishlist_items(wishlist_items, store_id=store_id)
            wishlist._prefetched_objects_cache = {'items': wishlist_items}

            from .serializers import WishlistSerializer
            wishlist_serializer = WishlistSerializer(wishlist, context={'request': request})
            return Response({
                'success': True,
                'message': 'Wishlist item quantity updated',
                'data': wishlist_serializer.data
            }, status=status.HTTP_200_OK)

def enrich_wishlist_items(wishlist_items, store_id=None):
    """
    Helper function to enrich a list of wishlist items with real-time stock and batch details from ERP.
    """
    if not wishlist_items:
        return
        
    item_codes = [wi.item.item_code for wi in wishlist_items if wi.item and wi.item.item_code]
    if not item_codes:
        return

    # Fetch real-time stock and batch details in bulk
    erp_item_map, stock_map = fetch_items_with_stock_and_batches(item_codes, store_id=store_id)

    for wishlist_item in wishlist_items:
        item = wishlist_item.item
        if not item:
            continue
            
        # 1. Enrich from ERP Item Master real-time data
        if erp_item_map and item.item_code in erp_item_map:
            erp_data = erp_item_map[item.item_code]
            if erp_data.get('mrp') is not None:
                try: item.mrp = float(erp_data['mrp'])
                except: pass
            if erp_data.get('std_disc') is not None:
                try: item.std_disc = float(erp_data['std_disc'])
                except: pass
            if erp_data.get('batchNo'):
                item.batch_no = erp_data['batchNo']
            if erp_data.get('expiryDate'):
                item.expiry_date = erp_data['expiryDate']
            item.erp_stock = erp_data.get('stockBalQty', 0)
        else:
            # Fallback to database Stock model
            try:
                from .models import Stock
                stock = Stock.objects.filter(item=item).first()
                if stock and stock.total_bal_ls_qty:
                    item.erp_stock = stock.total_bal_ls_qty
                else:
                    item.erp_stock = 0
            except:
                item.erp_stock = 0

        # 2. Enrich from live stock/batchDetails
        stock_entry = stock_map.get(str(item.item_code))
        item.erp_batch_details = stock_entry.get('batchDetails', []) if stock_entry else []


class WishlistView(APIView):
    """
    Get or clear user's wishlist
    GET: Retrieve wishlist with all items
    DELETE: Clear entire wishlist
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        store_id = request.query_params.get('storeId')
        user = request.user
        
        wishlist, created = Wishlist.objects.get_or_create(user=user)
        
        # ✅ ENRICH items with REAL-TIME stock and batchDetails from EcoGreen
        wishlist_items = wishlist.items.all()
        enrich_wishlist_items(wishlist_items, store_id=store_id)
        
        # Use WishlistItemSerializer instead of manual serialization
        from .serializers import WishlistItemSerializer
        items_serializer = WishlistItemSerializer(wishlist_items, many=True, context={'request': request})
        
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
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from django.db import transaction
        
        # Get user from authenticated request
        user = request.user
        
        serializer = AddToWishlistSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item_code = serializer.validated_data['itemCode']
        store_id = serializer.validated_data.get('storeId')
        
        if not store_id and user.preferred_store:
            store_id = user.preferred_store.store_id
            
        # [UPDATED] Token now auto-generated - no need for apiKey from request
        
        # ✅ FIX #3: ATOMIC TRANSACTION - Prevents race conditions
        try:
            with transaction.atomic():
                # Fetch fresh item details from ERP - REQUIRED, no fallback
                item_data = fetch_item_from_erp(item_code, store_id=store_id)
                
                if not item_data:
                    return Response({
                        'success': False,
                        'message': 'ERP service temporarily unavailable. Please try again.'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
                # Update ItemMaster cache with fresh ERP data (essential fields only)
                # NOTE: Out-of-stock items CAN be wishlisted - stock check happens at cart stage
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
                
                # Enrich wishlist item with real-time stock/batches from EcoGreen
                enrich_wishlist_items([wishlist_item], store_id=store_id)

                if not created:
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
            logger.error(f"[WISHLIST_ERROR] User: {user.id} | Item: {item_code} | Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': 'An error occurred while adding item to wishlist. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveFromWishlistView(APIView):
    """
    Remove item from wishlist
    DELETE: Remove specific item from wishlist
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, item_id):
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_item = WishlistItem.objects.get(id=item_id, wishlist=wishlist)
            item_name = wishlist_item.item.item_name
            wishlist_item.delete()
            
            # Enrich items before serialization
            store_id = request.query_params.get('storeId')
            if not store_id and request.user.preferred_store:
                store_id = request.user.preferred_store.store_id
            wishlist_items = list(wishlist.items.all())
            enrich_wishlist_items(wishlist_items, store_id=store_id)
            wishlist._prefetched_objects_cache = {'items': wishlist_items}

            wishlist_serializer = WishlistSerializer(wishlist, context={'request': request})
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
    permission_classes = [IsAuthenticated]
    
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
        
        # Check stock availability before moving to cart
        quantity = serializer.validated_data.get('quantity', wishlist_item.quantity)
        stock_status = get_item_stock_status(item_code)
        
        if not stock_status['available']:
            logger.warning(f"User {request.user.id} tried to move unavailable item {item_code} from wishlist to cart - Status: {stock_status['status']}")
            return Response({
                'success': False,
                'message': f'Cannot add to cart. Item is {stock_status["status"]}',
                'status': stock_status['status'],
                'available_qty': stock_status['qty'],
                'is_expired': stock_status.get('is_expired')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if requested quantity is available
        if quantity > stock_status['qty']:
            logger.warning(f"User {request.user.id} requested {quantity} units but only {stock_status['qty']} available for {item_code}")
            return Response({
                'success': False,
                'message': f'Only {stock_status["qty"]} units available',
                'requested': quantity,
                'available_qty': stock_status['qty']
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Reload item from database to get the fresh MRP and details updated by get_item_stock_status
        item = ItemMaster.objects.get(item_code=item_code)
        
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
        
        # Update stock and price in DB for all items first
        for c_item in cart.items.all():
            get_item_stock_status(c_item.item.item_code)
            
        cart_serializer = CartSerializer(cart)
        cart_data = cart_serializer.data
        
        # Fetch fresh stock status for each item
        for item in cart_data.get('items', []):
            item_code = item.get('itemCode')
            stock_status = get_item_stock_status(item_code)
            item['availability'] = stock_status.get('status', 'Unknown')
            item['available_qty'] = stock_status.get('qty', 0)
            item['in_stock'] = stock_status.get('available', False)
            item['current_price'] = str(round(stock_status.get('price', float(item.get('mrpBox', 0))), 2))
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
            limit = int(request.query_params.get('limit', 1000))
            
            # [UPDATED] Always use auto-generated token - try ERP first
            # [UPDATED] Always use auto-generated token - try Redis index lookup first (sub-50ms)
            from .erp_redis_cache import ERPRedisCache
            from .erp_service import ERPService
            
            store_info = ERPService._get_fallback_config()
            erp_config = store_info['erp_config']
            erp_store_id = erp_config['store_id']
            input_date_time = '2021-07-01 10:10:00'
            
            search_index = ERPRedisCache.get_search_index(erp_store_id, input_date_time)
            master_dict = ERPRedisCache.get_master_dict(erp_store_id, input_date_time)
            
            erp_items = []
            if search_index and master_dict:
                if search:
                    search_lower = search.lower()
                    matching_codes = []
                    # priority 1: starts with
                    for entry in search_index:
                        if entry['n'].startswith(search_lower):
                            matching_codes.append(entry['c'])
                            if len(matching_codes) >= limit:
                                break
                    # priority 2: contains
                    if len(matching_codes) < limit:
                        seen = set(matching_codes)
                        for entry in search_index:
                            if len(matching_codes) >= limit:
                                break
                            if entry['c'] not in seen and search_lower in entry['n']:
                                matching_codes.append(entry['c'])
                                seen.add(entry['c'])
                    erp_items = [master_dict[c] for c in matching_codes if c in master_dict]
                else:
                    # No search: just take first 'limit' items
                    erp_items = [master_dict[entry['c']] for entry in search_index[:limit] if entry['c'] in master_dict]
            else:
                # Fallback to fetch_all_items_from_erp
                erp_items = fetch_all_items_from_erp()
                if search and erp_items:
                    search_lower = search.lower()
                    erp_items = [
                        item for item in erp_items
                        if search_lower in item.get('itemName', '').lower()
                    ]
                erp_items = erp_items[:limit]
                
                # Format response
                products = []
                for item in erp_items:
                    mrp = float(item.get('mrp', 0))
                    discount = float(item.get('std_disc', 0))
                    discounted = mrp * (1 - discount / 100) if mrp > 0 else 0
                    
                    # Check cart and wishlist status
                    cart_status = False
                    wishlist_status = False
                    if request.user.is_authenticated:
                        try:
                            from .models import CartItem, WishlistItem
                            c_item_code = item.get('c_item_code') or item.get('itemCode')
                            if c_item_code:
                                cart_status = CartItem.objects.filter(
                                    cart__user=request.user,
                                    item__item_code=c_item_code
                                ).exists()
                                wishlist_status = WishlistItem.objects.filter(
                                    wishlist__user=request.user,
                                    item__item_code=c_item_code
                                ).exists()
                        except:
                            pass

                    products.append({
                        'c_item_code': item.get('c_item_code') or item.get('itemCode'),
                        'itemName': item.get('itemName'),
                        'itemQtyPerBox': item.get('itemQtyPerBox'),
                        'batchNo': item.get('batchNo'),
                        'mrp': mrp,
                        'std_disc': discount,
                        'max_disc': float(item.get('max_disc', 0)),
                        'discountedPrice': round(discounted, 2),
                        'stockBalQty': item.get('stockBalQty', 0),
                        'expiryDate': item.get('expiryDate'),
                        'cart_status': cart_status,
                        'wishlist_status': wishlist_status,
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
                
                # Check cart and wishlist status
                cart_status = False
                wishlist_status = False
                if request.user.is_authenticated:
                    try:
                        from .models import CartItem, WishlistItem
                        cart_status = CartItem.objects.filter(
                            cart__user=request.user,
                            item=item
                        ).exists()
                        wishlist_status = WishlistItem.objects.filter(
                            wishlist__user=request.user,
                            item=item
                        ).exists()
                    except:
                        pass

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
                    'cart_status': cart_status,
                    'wishlist_status': wishlist_status,
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
        - page: Current page (default: 1)
        - page_size: Results per page (default: 20)
        - apiKey: Optional ERP API key for live data enrichment
    
    Data Sources:
        - Without apiKey: Database only (stockBalQty from Stock table)
        - With apiKey: ERP live data (pricing, stock, expiry)
    
    Example: /api/search/88/?q=paracetamol&page_size=10&apiKey=YOUR_KEY
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Get search query from params — empty query returns all products
            query = (request.query_params.get('q') or request.query_params.get('search') or '').strip()
            category_id = request.query_params.get('category')

            # ── Pagination params ──────────────────────────────────────────
            try:
                page = max(1, int(request.query_params.get('page', 1)))
            except (ValueError, TypeError):
                page = 1

            try:
                page_size = int(request.query_params.get('page_size') or 10)
                page_size = min(2000, max(1, page_size))
            except (ValueError, TypeError):
                page_size = 10

            no_pagination = request.query_params.get('no_pagination', 'false').lower() == 'true'
            search_capacity = 2000

            # Always fetch live stock for matched search results (targeted call, fast)
            # No minimum length — empty query = show all (up to capacity)

            
            # ── Get ERP items from Redis cache (FAST) ────────────────────
            # Uses the SAME Redis cache as GetItemMasterView (1-hour TTL).
            # ERP is only called on cold cache — search is instant on cache hit.
            from .erp_redis_cache import ERPRedisCache
            from .erp_service import ERPService
            from .erp_token_service import get_erp_token_for_store_config

            # ── Store config ───────────────────────────────────────────────
            store_id = request.query_params.get('storeId')
            if store_id:
                store_info = ERPService.get_config_by_store_id(store_id)
            else:
                store_info = ERPService._get_fallback_config()

            erp_config  = store_info['erp_config']
            erp_store_id = erp_config['store_id']
            input_date_time = '2021-07-01 10:10:00'

            # ── Get ERP items from Redis cache (FAST) ────────────────────
            # Uses the Redis search index built by background scheduler
            search_index = ERPRedisCache.get_search_index(erp_store_id, input_date_time)
            master_dict  = ERPRedisCache.get_master_dict(erp_store_id, input_date_time)

            matching_erp_items = []
            products = []

            if search_index and master_dict:
                # ── Warm Cache Path: Fast scan on Redis index (sub-50ms) ───
                logger.info(f'[SEARCH] Index HIT — scanning {len(search_index)} compact entries')
                query_lower = query.lower()
                matching_codes = []
                if not query_lower:
                    matching_codes = [entry['c'] for entry in search_index[:search_capacity]]
                else:
                    import re
                    query_words = [w.strip() for w in re.split(r'[\s\-\'\,\.\/\`]+', query_lower) if w.strip() and len(w.strip()) > 1]
                    
                    if not query_words:
                        matching_codes = [entry['c'] for entry in search_index[:search_capacity]]
                    else:
                        scored_entries = []
                        first_word = query_words[0]
                        for entry in search_index:
                            n = entry.get('n', '')
                            b = entry.get('b', '')
                            co = entry.get('co', '')
                            s = entry.get('s', '')
                            ca = entry.get('ca', '')
                            
                            match_count = 0
                            for word in query_words:
                                if word in n or word in b or word in co or word in s or word in ca:
                                    match_count += 1
                            
                            if match_count > 0:
                                first_word_matched = (first_word in n or first_word in b or first_word in co)
                                startswith_boost = n.startswith(query_lower) or b.startswith(query_lower)
                                scored_entries.append({
                                    'code': entry['c'],
                                    'matches': match_count,
                                    'first_matched': first_word_matched,
                                    'startswith_boost': startswith_boost,
                                    'name_len': len(n)
                                })
                        
                        scored_entries.sort(key=lambda x: (-x['matches'], -x['first_matched'], -x['startswith_boost'], x['name_len']))
                        matching_codes = [x['code'] for x in scored_entries[:search_capacity]]

                # O(1) lookup of full item data for matched codes
                matching_erp_items = [master_dict[c] for c in matching_codes if c in master_dict]

            # Fallback to local database search if cache is missing OR returns zero matches
            if not matching_erp_items:
                # ── Cold Cache Miss / Fallback Path: Search local ItemMaster database directly (instant!) ──
                logger.info(f'[SEARCH] Cache miss or zero results — querying local ItemMaster DB for query: "{query}"')
                from django.db.models import Q
                
                query_lower = query.lower()
                db_matches = []
                if not query_lower:
                    db_matches = list(ItemMaster.objects.all()[:search_capacity])
                else:
                    import re
                    query_words = [w.strip() for w in re.split(r'[\s\-\'\,\.\/\`]+', query_lower) if w.strip() and len(w.strip()) > 1]
                    if not query_words:
                        db_matches = list(ItemMaster.objects.all()[:search_capacity])
                    else:
                        first_word = query_words[0]
                        token_q = (
                            Q(item_name__icontains=first_word) |
                            Q(brand_name__icontains=first_word) |
                            Q(content_name__icontains=first_word)
                        )
                        
                        candidates = ItemMaster.objects.filter(token_q)[:search_capacity]
                        scored_candidates = []
                        for itm in candidates:
                            match_count = 0
                            itm_name_lower = (itm.item_name or '').lower()
                            brand_lower = (itm.brand_name or '').lower()
                            content_lower = (itm.content_name or '').lower()
                            category_lower = (itm.category_name or '').lower()
                            
                            for word in query_words:
                                if word in itm_name_lower or word in brand_lower or word in content_lower or word in category_lower:
                                    match_count += 1
                                    
                            if match_count > 0:
                                first_word_matched = first_word in itm_name_lower or first_word in brand_lower
                                startswith_boost = itm_name_lower.startswith(query_lower) or brand_lower.startswith(query_lower)
                                scored_candidates.append({
                                    'itm': itm,
                                    'matches': match_count,
                                    'first_matched': first_word_matched,
                                    'startswith_boost': startswith_boost,
                                    'name_len': len(itm_name_lower)
                                })
                        
                        scored_candidates.sort(key=lambda x: (-x['matches'], -x['first_matched'], -x['startswith_boost'], x['name_len']))
                        db_matches = [x['itm'] for x in scored_candidates]

                # Format local ItemMaster objects to the dictionary structure expected by views
                for itm in db_matches:
                    matching_erp_items.append({
                        'c_item_code':     itm.item_code,
                        'itemCode':        itm.item_code,
                        'itemName':        itm.item_name,
                        'itemShortName':   itm.item_short_name or '-',
                        'itemFullName':    itm.item_full_name or itm.item_name,
                        'brandCode':       itm.brand_code or '-',
                        'brandName':       itm.brand_name or '-',
                        'categoryCode':    itm.category_code or '-',
                        'categoryName':    itm.category_name or '-',
                        'maxDiscPer':      float(itm.max_disc or 0.0),
                        'stdDiscRate':     float(itm.std_disc or 0.0),
                        'contentCode':     itm.content_code or '-',
                        'contentName':     itm.content_name or '-',
                        'packCode':        itm.pack_code or '-',
                        'packName':        itm.pack_name or '-',
                        'itemQtyPerBox':   itm.item_qty_per_box or 1,
                        'itemAddedDate':   '-',
                        'itemUpdatedDate': '-',
                        'hsnSacCode':      itm.hsn_code or '-',
                        'hsnSacName':      itm.hsn_sac_name or '-',
                    })
                
                # If product not in Redis and not in local DB, fetch fresh from live ERP API
                if not matching_erp_items:
                    logger.info(f'[SEARCH] DB miss — invoking live ERP API fallback for query: "{query}"')
                    try:
                        from .erp_token_service import get_erp_token_for_store_config
                        from .erp_service import ERPService
                        
                        api_key = get_erp_token_for_store_config(erp_config)
                        if api_key:
                            erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
                            erp_payload = {
                                'apiKey':        api_key,
                                'prodCode':      erp_config['prod_code'],
                                'c2Code':        erp_config['c2_code'],
                                'storeId':       erp_store_id,
                                'inputDateTime': '2021-07-01 10:10:00',
                                'itemcodes':     []
                            }
                            
                            response = requests.get(erp_url, json=erp_payload, timeout=15)
                            if response.status_code == 200:
                                res_data = response.json()
                                if res_data.get('code') == '200' and res_data.get('data'):
                                    fresh_items = res_data.get('data', [])
                                    # Run token-based matching on fresh ERP items
                                    import re
                                    query_words = [w.strip() for w in re.split(r'[\s\-\'\,\.\/\`]+', query_lower) if w.strip() and len(w.strip()) > 1]
                                    if query_words:
                                        scored_fresh = []
                                        for itm in fresh_items:
                                            itm_name_lower = (itm.get('itemName') or '').lower()
                                            brand_lower = (itm.get('brandName') or '').lower()
                                            content_lower = (itm.get('contentName') or '').lower()
                                            category_lower = (itm.get('categoryName') or '').lower()
                                            
                                            match_count = 0
                                            for word in query_words:
                                                if word in itm_name_lower or word in brand_lower or word in content_lower or word in category_lower:
                                                    match_count += 1
                                            
                                            if match_count > 0:
                                                first_word = query_words[0]
                                                first_word_matched = first_word in itm_name_lower or first_word in brand_lower
                                                startswith_boost = itm_name_lower.startswith(query_lower) or brand_lower.startswith(query_lower)
                                                scored_fresh.append({
                                                    'itm': itm,
                                                    'matches': match_count,
                                                    'first_matched': first_word_matched,
                                                    'startswith_boost': startswith_boost,
                                                    'name_len': len(itm_name_lower)
                                                })
                                        
                                        scored_fresh.sort(key=lambda x: (-x['matches'], -x['first_matched'], -x['startswith_boost'], x['name_len']))
                                        matched_fresh = [x['itm'] for x in scored_fresh[:search_capacity]]
                                        
                                        # Convert and save on-the-fly to PostgreSQL ItemMaster
                                        for fitm in matched_fresh:
                                            f_code = fitm.get('c_item_code') or fitm.get('itemCode')
                                            if f_code:
                                                std_disc = float(fitm.get('stdDiscRate') or fitm.get('std_disc') or 0)
                                                max_disc = float(fitm.get('maxDiscPer') or fitm.get('max_disc') or 0)
                                                mrp = float(fitm.get('mrpBox') or fitm.get('mrp') or 0)
                                                
                                                db_item, _ = ItemMaster.objects.update_or_create(
                                                    item_code=f_code,
                                                    defaults={
                                                        'item_name': fitm.get('itemName', ''),
                                                        'item_qty_per_box': fitm.get('itemQtyPerBox', 1),
                                                        'batch_no': fitm.get('batchNo') or '-',
                                                        'std_disc': std_disc,
                                                        'max_disc': max_disc,
                                                        'mrp': mrp,
                                                        'brand_code': fitm.get('brandCode') or '-',
                                                        'brand_name': fitm.get('brandName') or '-',
                                                        'category_code': fitm.get('categoryCode') or '-',
                                                        'category_name': fitm.get('categoryName') or '-',
                                                        'content_code': fitm.get('contentCode') or '-',
                                                        'content_name': fitm.get('contentName') or '-',
                                                        'hsn_sac_name': fitm.get('hsnSacName') or '-',
                                                        'item_full_name': fitm.get('itemFullName'),
                                                        'item_short_name': fitm.get('itemShortName') or '-',
                                                        'pack_code': fitm.get('packCode') or '-',
                                                        'pack_name': fitm.get('packName') or '-',
                                                        'hsn_code': fitm.get('hsnSacCode') or fitm.get('hsnCode') or '-',
                                                    }
                                                )
                                                
                                                matching_erp_items.append({
                                                    'c_item_code':     f_code,
                                                    'itemCode':        f_code,
                                                    'itemName':        fitm.get('itemName', ''),
                                                    'itemShortName':   fitm.get('itemShortName') or '-',
                                                    'itemFullName':    fitm.get('itemFullName') or fitm.get('itemName') or '',
                                                    'maxDiscPer':      max_disc,
                                                    'stdDiscRate':     std_disc,
                                                    'itemQtyPerBox':   fitm.get('itemQtyPerBox') or 1,
                                                })
                    except Exception as fallback_err:
                        logger.error(f'[SEARCH] Live ERP API fallback error: {fallback_err}')

            # ── Pagination logic ──
            total_items = len(matching_erp_items)
            import math
            if no_pagination:
                paged_matching_erp_items = matching_erp_items
                total_pages = 1
            else:
                total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paged_matching_erp_items = matching_erp_items[start_idx:end_idx]

            # ── Stock fetch — identical strategy to GetItemMasterView ─────────────
            # Pass only the current-page item codes → ERP returns just those items (fast).
            # 1. Try global stock cache (warmed by GetItemMasterView, 60s TTL) for instant lookup.
            # 2. On cache miss, make targeted ERP call for only the page's item codes.
            search_stock_map = {}
            page_item_codes = [
                str(item.get('c_item_code') or item.get('itemCode')).strip()
                for item in paged_matching_erp_items
                if item.get('c_item_code') or item.get('itemCode')
            ]
            page_item_codes = [c for c in page_item_codes if c]

            if page_item_codes:
                # Step 1: try global stock cache (warmed by GetItemMasterView)
                global_stock = ERPRedisCache.get_global_stock_map(erp_store_id)
                if global_stock:
                    for code in page_item_codes:
                        entry = global_stock.get(code)
                        if entry:
                            search_stock_map[code] = entry
                    logger.info(f'[SEARCH] Stock from global cache: {len(search_stock_map)}/{len(page_item_codes)} items')

                if not search_stock_map:
                    # Step 2: targeted ERP stock call — only for this page's items
                    try:
                        api_key_for_stock = get_erp_token_for_store_config(erp_config)
                        if api_key_for_stock:
                            stock_server_url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
                            stock_payload = {
                                'apiKey':        api_key_for_stock,
                                'prodCode':      erp_config['prod_code'],
                                'c2Code':        erp_config['c2_code'],
                                'storeId':       erp_store_id,
                                'inputDateTime': input_date_time,
                                'itemCodes':     page_item_codes,   # ← targeted, NOT []
                            }
                            stock_headers = {
                                'User-Agent': 'PostmanRuntime/7.43.0',
                                'Accept': '*/*',
                                'Accept-Encoding': 'gzip, deflate',
                                'Connection': 'keep-alive',
                            }
                            stock_resp = requests.post(
                                stock_server_url, json=stock_payload,
                                headers=stock_headers, timeout=30, stream=True
                            )
                            if stock_resp.status_code == 200:
                                raw_chunks = []
                                for chunk in stock_resp.iter_content(chunk_size=65536):
                                    if chunk:
                                        raw_chunks.append(chunk)
                                raw_bytes = b''.join(raw_chunks)
                                raw_text = raw_bytes.decode('utf-8', errors='replace').strip()
                                if raw_text.startswith('\ufeff'):
                                    raw_text = raw_text[1:]
                                import re as _re
                                raw_text = _re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
                                try:
                                    stock_data = json.loads(raw_text)
                                    stock_items_list = (
                                        stock_data.get('stockDetails', []) or stock_data.get('data', [])
                                        if isinstance(stock_data, dict) else stock_data
                                    )
                                    for s in stock_items_list:
                                        s_code = str(s.get('c_item_code') or s.get('itemCode') or '').strip()
                                        if s_code:
                                            s_code_val = s.get('itemCode') or s.get('c_item_code')
                                            s.pop('c_item_code', None)
                                            if s_code_val:
                                                s['itemCode'] = str(s_code_val).strip()
                                            if s_code not in search_stock_map:
                                                search_stock_map[s_code] = dict(s)
                                                search_stock_map[s_code]['batchDetails'] = list(s.get('batchDetails', []) or [])
                                            else:
                                                search_stock_map[s_code]['batchDetails'].extend(s.get('batchDetails', []) or [])
                                                for key in ('qtyBox', 'contCode', 'contName'):
                                                    if key not in search_stock_map[s_code] or search_stock_map[s_code][key] is None:
                                                        search_stock_map[s_code][key] = s.get(key)
                                    # Cache result globally for other callers (60s TTL)
                                    if search_stock_map:
                                        existing_stock = ERPRedisCache.get_global_stock_map(erp_store_id) or {}
                                        existing_stock.update(search_stock_map)
                                        ERPRedisCache.set_global_stock_map(erp_store_id, existing_stock)
                                        logger.info(f'[SEARCH] Targeted stock fetched & merged: {len(search_stock_map)} items')
                                except Exception as parse_err:
                                    logger.error(f'[SEARCH] Stock parse error: {parse_err}')
                    except Exception as stock_err:
                        logger.error(f'[SEARCH] Stock fetch error: {stock_err}')

            # ── Bulk pre-fetch ProductInfo + images (same as GetItemMasterView) ─────
            product_info_map = {}
            images_by_product_map = {}
            user_cart_item_codes = set()
            user_wishlist_item_codes = set()

            if page_item_codes:
                # Query 1: ProductInfo + brand/category (select_related avoids N+1)
                product_infos = ProductInfo.objects.filter(
                    item__item_code__in=page_item_codes
                ).select_related('item', 'category')
                for info in product_infos:
                    product_info_map[info.item.item_code] = info

                # Query 2: Product images in bulk (keyed by product_info.id like GetItemMasterView)
                from .models import ProductImage
                product_images = ProductImage.objects.filter(
                    product_info__in=product_infos
                ).order_by('image_order')
                for img in product_images:
                    prod_info_id = img.product_info_id
                    if prod_info_id not in images_by_product_map:
                        images_by_product_map[prod_info_id] = []
                    images_by_product_map[prod_info_id].append(img)

                # Query 3 & 4: Cart and wishlist flags
                auth_user = request.user if request.user.is_authenticated else None
                if auth_user:
                    try:
                        user_cart = Cart.objects.get(user=auth_user)
                        user_cart_item_codes = set(
                            CartItem.objects.filter(
                                cart=user_cart, item__item_code__in=page_item_codes
                            ).values_list('item__item_code', flat=True)
                        )
                    except Cart.DoesNotExist:
                        pass
                    try:
                        user_wishlist = Wishlist.objects.get(user=auth_user)
                        user_wishlist_item_codes = set(
                            WishlistItem.objects.filter(
                                wishlist=user_wishlist, item__item_code__in=page_item_codes
                            ).values_list('item__item_code', flat=True)
                        )
                    except Wishlist.DoesNotExist:
                        pass

            # ── Enrich paged items — identical to GetItemMasterView ───────────────
            for idx, erp_item in enumerate(paged_matching_erp_items):
                item_code = str(erp_item.get('c_item_code') or erp_item.get('itemCode') or '').strip()

                # Merge stock data
                stock_entry = search_stock_map.get(item_code)
                if isinstance(stock_entry, dict):
                    for k, v in stock_entry.items():
                        if k not in ('c_item_code', 'itemCode'):
                            erp_item[k] = v
                    batch_list = stock_entry.get('batchDetails', [])
                    if batch_list:
                        erp_item['stockBalQty'] = sum(int(float(b.get('packQty') or 0)) for b in batch_list)
                    else:
                        erp_item['stockBalQty'] = int(float(stock_entry.get('totalBalLsQty') or stock_entry.get('packQty') or 0))
                elif isinstance(stock_entry, (int, float)):
                    erp_item['stockBalQty'] = stock_entry
                    erp_item['batchDetails'] = []
                else:
                    erp_item['stockBalQty'] = 0
                    erp_item['batchDetails'] = []

                paged_matching_erp_items[idx] = erp_item

                # ERP catalog fields (normalise)
                erp_item['contentCode']  = erp_item.get('contentCode')  or '-'
                erp_item['contentName']  = erp_item.get('contentName')  or '-'
                erp_item['packCode']     = erp_item.get('packCode')     or '-'
                erp_item['packName']     = erp_item.get('packName')     or '-'
                erp_item['hsnSacCode']   = erp_item.get('hsnSacCode')   or '-'
                erp_item['hsnSacName']   = erp_item.get('hsnSacName')   or '-'
                erp_item['brandCode']    = erp_item.get('brandCode')    or '-'
                erp_item['brandName']    = erp_item.get('brandName')    or '-'
                erp_item['categoryCode'] = erp_item.get('categoryCode') or '-'
                erp_item['categoryName'] = erp_item.get('categoryName') or '-'
                erp_item['itemFullName'] = erp_item.get('itemFullName') or erp_item.get('itemName') or '-'
                erp_item['itemShortName']= erp_item.get('itemShortName') or '-'
                erp_item['itemAddedDate']   = erp_item.get('itemAddedDate')   or '-'
                erp_item['itemUpdatedDate'] = erp_item.get('itemUpdatedDate') or '-'

                # DB enrichment (ProductInfo + images)
                product_info = product_info_map.get(item_code)
                if product_info:
                    subheading  = product_info.subheading  or ''
                    description = product_info.description or ''
                    type_label  = product_info.type_label  or ''
                    brand_id    = product_info.category.id   if product_info.category else None
                    brand_name  = product_info.category.name if product_info.category else ''
                    brand_logo  = (
                        request.build_absolute_uri(product_info.category.icon.url)
                        if product_info.category and product_info.category.icon else ''
                    )
                    images = images_by_product_map.get(product_info.pk, [])
                    images_list = [
                        {'image': request.build_absolute_uri(img.image.url), 'image_order': img.image_order}
                        for img in images
                    ]
                else:
                    subheading = description = type_label = brand_logo = ''
                    brand_id = None
                    brand_name = erp_item.get('brandName') or ''
                    images_list = []

                formatted_item = {
                    'c_item_code':     item_code,
                    'itemCode':        item_code,
                    'itemName':        erp_item.get('itemName') or '',
                    'maxDiscPer':      erp_item.get('maxDiscPer', 0),
                    'stdDiscRate':     erp_item.get('stdDiscRate', 0),
                    'itemQtyPerBox':   int(erp_item.get('itemQtyPerBox') or erp_item.get('qtyBox') or 1),
                    'stockBalQty':     erp_item.get('stockBalQty', 0),
                    'batchDetails':    erp_item.get('batchDetails', []),
                    'subheading':      subheading,
                    'description':     description,
                    'type_label':      type_label,
                    'brand_id':        brand_id,
                    'brand_name':      brand_name,
                    'brand_logo':      brand_logo,
                    'images':          images_list,
                    'cart_status':     item_code in user_cart_item_codes,
                    'wishlist_status': item_code in user_wishlist_item_codes,
                }
                products.append(formatted_item)
            
            # Track product views for matched items that exist in our database
            try:
                user = request.user if request.user.is_authenticated else None
                if user and product_info_map:
                    from .models import ProductView
                    for product_info in product_info_map.values():
                        ProductView.objects.update_or_create(
                            user=user,
                            item=product_info.item,
                            defaults={'viewed_at': timezone.now()}
                        )
            except Exception as e:
                logger.warning(f"[PRODUCT_VIEW_ERROR] Failed to track product views: {str(e)}")

            if not products:
                return Response({
                    'success': True,
                    'message': 'No products found',
                    'query': query,
                    'count': 0,
                    'data': [],
                    'pagination': {
                        'current_page': page,
                        'page_size':    page_size,
                        'total_items':  total_items,
                        'total_pages':  total_pages,
                        'has_next':     page < total_pages,
                        'has_previous': page > 1,
                    }
                }, status=status.HTTP_200_OK)
            
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
            
            return Response({
                'success': True,
                'message': f'Found {total_items} products',
                'query': query,
                'count': len(products),
                'data': products,
                'source': 'erp' if search_index else 'database',
                'pagination': {
                    'current_page': page,
                    'page_size':    page_size,
                    'total_items':  total_items,
                    'total_pages':  total_pages,
                    'has_next':     page < total_pages,
                    'has_previous': page > 1,
                }
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
            
            # Collect all matching item codes first
            item_codes = []
            search_products_map = {}
            for search in popular_searches:
                query = search.query
                product_infos = list(ProductInfo.objects.select_related('item', 'category').filter(
                    Q(item__item_name__icontains=query) |
                    Q(description__icontains=query) |
                    Q(type_label__icontains=query) |
                    Q(category__name__icontains=query)
                ).distinct()[:20])
                search_products_map[query] = product_infos
                for prod_info in product_infos:
                    if prod_info.item and prod_info.item.item_code:
                        item_codes.append(prod_info.item.item_code)

            # [UPDATED] Fetch ERP data and live stock for these matching item codes in bulk
            erp_map, stock_map = fetch_items_with_stock_and_batches(item_codes)
            if erp_map:
                logger.info(f"[POPULAR_SEARCH] Fetched {len(erp_map)} items from ERP with live stock")
            
            # Serialize popular searches with products
            searches = []
            for search in popular_searches:
                query = search.query
                product_infos = search_products_map.get(query, [])
                
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
                        
                        # Fetch live stock quantity from stock_map
                        stock_entry = stock_map.get(item.item_code, {})
                        batch_list = stock_entry.get('batchDetails', [])
                        total_pack_qty = sum(int(float(b.get('packQty') or 0)) for b in batch_list)
                        item.erp_stock = total_pack_qty
                    
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
                                item=item
                            ).exists()
                            wishlist_status = WishlistItem.objects.filter(
                                wishlist__user=request.user,
                                item=item
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

def fetch_item_from_erp(item_code, store_id=None):
    """
    Fetch a specific item from ERP endpoint
    Returns item data dict or None if not found
    [UPDATED] Checks Redis master cache first before hitting ERP
    """
    try:
        # Check Redis master_dict cache first — avoids ERP call
        from .erp_redis_cache import ERPRedisCache
        _store_id = store_id or '501'
        master_dict = ERPRedisCache.get_master_dict(_store_id, '2021-07-01 10:10:00')
        if master_dict and str(item_code) in master_dict:
            item_data = master_dict[str(item_code)]
            item_data['c_item_code'] = item_code
            item_data['itemCode'] = item_code
            logger.info(f"[FETCH_ITEM] Redis cache HIT for {item_code}")
            return item_data
    except Exception as cache_err:
        logger.warning(f"[FETCH_ITEM] Redis cache check failed for {item_code}: {cache_err}")

    try:
        from .erp_token_service import get_erp_token_for_store_config
        from .erp_service import ERPService
        
        if store_id:
            store_info = ERPService.get_config_by_store_id(store_id)
        else:
            store_info = ERPService._get_fallback_config()
            
        if not store_info:
            store_info = ERPService._get_fallback_config()
            
        erp_config = store_info['erp_config']
        api_key = get_erp_token_for_store_config(erp_config)
            
        if not api_key:
            logger.error("Could not get auto-generated token")
            return None
        
        # Fetch all items from ERP
        erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
        
        # 🎯 Official Ecogreen API uses GET with JSON body for master data
        erp_payload = {
            'apiKey':        api_key,
            'prodCode':      erp_config['prod_code'],
            'c2Code':        erp_config['c2_code'],
            'storeId':       erp_config['store_id'],
            'inputDateTime': '2021-07-01 10:10:00',
            'itemcodes':     [item_code]
        }
        
        response = requests.get(erp_url, json=erp_payload, timeout=10)
        response.raise_for_status()
        
        raw_text = response.text
        raw_text = re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
        data = json.loads(raw_text)
        if data.get('code') != '200' or not data.get('data'):
            return None
        
        # Find the specific item
        for item_data in data.get('data', []):
            item_code_val = item_data.get('c_item_code') or item_data.get('itemCode')
            if item_code_val == item_code:
                # Normalize keys for compatibility
                item_data['c_item_code'] = item_code_val
                item_data['itemCode'] = item_code_val
                return item_data
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching from ERP: {str(e)}")
        return None

def fetch_all_items_from_erp(store_id=None):
    """
    Helper function: Fetch all items from ERP in one call
    Used by recommendation views to enrich data with live pricing/stock
    
    Returns: List of item dicts from ERP, or empty list if error
    Usage: Used in SimilarProductsView, FrequentlyBoughtTogetherView, TopSellingProductsView, WishlistView
    [UPDATED] Now uses auto-generated token automatically and supports store_id
    """
    try:
        from .erp_token_service import get_erp_token_for_store_config
        from .erp_service import ERPService
        
        if store_id:
            store_info = ERPService.get_config_by_store_id(store_id)
        else:
            store_info = ERPService._get_fallback_config()
            
        if not store_info:
            store_info = ERPService._get_fallback_config()
            
        erp_config = store_info['erp_config']
        api_key = get_erp_token_for_store_config(erp_config)
            
        from .erp_redis_cache import ERPRedisCache
        
        # ── 1. Check Redis cache first (sub-50ms) ──────────────────────────────────
        cached_items = ERPRedisCache.get_master_data(erp_config['store_id'], '2021-07-01 10:10:00')
        if cached_items:
            logger.info(f"[ERP_FETCH_ALL] Cache HIT — loaded {len(cached_items)} items from Redis for store {erp_config['store_id']}")
            return cached_items

        erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
        logger.info(f"[ERP_FETCH_ALL] Cache MISS — fetching all items from ERP: {erp_url}")
        
        # 🎯 Official Ecogreen API uses GET with JSON body for master data
        erp_payload = {
            'apiKey':        api_key,
            'prodCode':      erp_config['prod_code'],
            'c2Code':        erp_config['c2_code'],
            'storeId':       erp_config['store_id'],
            'inputDateTime': '2021-07-01 10:10:00',
            'itemcodes':     []
        }
        
        response = requests.get(erp_url, json=erp_payload, timeout=15)
        response.raise_for_status()
        
        raw_text = response.text
        raw_text = re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
        data = json.loads(raw_text)
        if data.get('code') != '200':
            logger.error(f"[ERP_ERROR] ERP returned non-200 code: {data.get('code')}")
            return []
        
        items = data.get('data', [])
        
        # Normalize keys for compatibility (c_item_code and itemCode)
        for item in items:
            item_code_val = item.get('c_item_code') or item.get('itemCode')
            if item_code_val:
                item['c_item_code'] = item_code_val
                item['itemCode'] = item_code_val
                
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


def fetch_items_by_codes_from_erp(item_codes, store_id=None):
    """
    Optimized helper: Get ERP master data details for a specific list of item codes.
    Avoids loading and de-serializing all 165k items from Redis.
    """
    if not item_codes:
        return []
        
    # Clean/normalize codes list
    item_codes = list(set(str(code).strip() for code in item_codes if code))
    if not item_codes:
        return []

    try:
        from .erp_redis_cache import ERPRedisCache
        from .erp_service import ERPService
        
        if store_id:
            store_info = ERPService.get_config_by_store_id(store_id)
        else:
            store_info = ERPService._get_fallback_config()
            
        if not store_info:
            store_info = ERPService._get_fallback_config()
            
        erp_config = store_info['erp_config']
        erp_store_id = erp_config['store_id']
        input_date_time = '2021-07-01 10:10:00'
        
        # 1. Try master_dict cache in Redis
        master_dict = ERPRedisCache.get_master_dict(erp_store_id, input_date_time)
        if master_dict:
            logger.info(f"[ERP_FETCH_CODES] Cache HIT for {len(item_codes)} codes")
            results = []
            for code in item_codes:
                itm = master_dict.get(code)
                if itm:
                    # Normalize keys
                    itm_code = itm.get('c_item_code') or itm.get('itemCode')
                    itm['c_item_code'] = itm_code
                    itm['itemCode'] = itm_code
                    results.append(itm)
            return results
            
        # 2. Cache miss: Fall back to local ItemMaster database lookup (instant)
        logger.info(f"[ERP_FETCH_CODES] Cache MISS — loading {len(item_codes)} codes from local database")
        db_items = ItemMaster.objects.filter(item_code__in=item_codes)
        results = []
        for itm in db_items:
            results.append({
                'c_item_code':     itm.item_code,
                'itemCode':        itm.item_code,
                'itemName':        itm.item_name,
                'itemShortName':   itm.item_short_name or '-',
                'itemFullName':    itm.item_full_name or itm.item_name,
                'brandCode':       itm.brand_code or '-',
                'brandName':       itm.brand_name or '-',
                'categoryCode':    itm.category_code or '-',
                'categoryName':    itm.category_name or '-',
                'maxDiscPer':      itm.max_disc or 0,
                'stdDiscRate':     itm.std_disc or 0,
                'contentCode':     itm.content_code or '-',
                'contentName':     itm.content_name or '-',
                'packCode':        itm.pack_code or '-',
                'packName':        itm.pack_name or '-',
                'itemQtyPerBox':   itm.item_qty_per_box or 1,
                'hsnSacCode':      itm.hsn_code or '-',
                'hsnSacName':      itm.hsn_sac_name or '-',
            })
        return results
        
    except Exception as e:
        logger.error(f"[ERP_FETCH_CODES] Error loading codes: {str(e)}")
        return []


def fetch_items_with_stock_and_batches(item_codes, store_id=None):
    """
    Optimized helper: Get both ERP master data and live stock/batchDetails for a list of item codes in bulk.
    Returns: (erp_item_map, stock_map)
    """
    if not item_codes:
        return {}, {}
        
    item_codes = list(set(str(code).strip() for code in item_codes if code))
    if not item_codes:
        return {}, {}

    # 1. Fetch Item Master details
    erp_items = fetch_items_by_codes_from_erp(item_codes, store_id=store_id)
    erp_item_map = {item.get('c_item_code'): item for item in erp_items} if erp_items else {}

    # 2. Fetch live stock and batch details
    stock_map = {}
    try:
        from .erp_service import ERPService
        from .erp_token_service import get_erp_token_for_store_config
        if store_id:
            store_info = ERPService.get_config_by_store_id(store_id)
        else:
            store_info = ERPService._get_fallback_config()

        if store_info:
            erp_config = store_info['erp_config']
            api_key = get_erp_token_for_store_config(erp_config)
            if api_key:
                stock_url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
                stock_payload = {
                    'apiKey':        api_key,
                    'prodCode':      erp_config['prod_code'],
                    'c2Code':        erp_config['c2_code'],
                    'storeId':       erp_config['store_id'],
                    'inputDateTime': '2021-07-01 10:10:00',
                    'itemCodes':     item_codes,
                }
                headers = {
                    'User-Agent': 'PostmanRuntime/7.43.0',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                stock_resp = requests.post(stock_url, json=stock_payload, headers=headers, timeout=30, stream=True)
                if stock_resp.status_code == 200:
                    raw_chunks = []
                    for chunk in stock_resp.iter_content(chunk_size=65536):
                        if chunk:
                            raw_chunks.append(chunk)
                    raw_bytes = b''.join(raw_chunks)
                    raw_text = raw_bytes.decode('utf-8', errors='replace').strip()
                    if raw_text.startswith('\ufeff'):
                        raw_text = raw_text[1:]
                    # Fix malformed decimals like .000 -> 0.000 (ERP bug)
                    import re as _re
                    raw_text = _re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
                    try:
                        stock_data = json.loads(raw_text)
                    except:
                        stock_data = {}
                    stock_items_list = []
                    if isinstance(stock_data, dict):
                        stock_items_list = stock_data.get('stockDetails', []) or stock_data.get('data', [])
                    elif isinstance(stock_data, list):
                        stock_items_list = stock_data
                    item_codes_set = set(str(c) for c in item_codes)
                    for s in stock_items_list:
                        s_code = str(s.get('c_item_code') or s.get('itemCode') or '').strip()
                        if s_code not in item_codes_set:
                            continue
                        batch_details = s.get('batchDetails', [])
                        if s_code not in stock_map:
                            stock_map[s_code] = {'batchDetails': list(batch_details or [])}
                        else:
                            stock_map[s_code]['batchDetails'].extend(batch_details or [])
    except Exception as e:
        logger.warning(f"[ERP_STOCK_HELPER] Failed to fetch live stock/batches: {e}")

    return erp_item_map, stock_map


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
        
        existing = ItemMaster.objects.filter(item_code=item_code).first()
        
        # Parse discount keys from ERP response
        std_disc = float(item_data.get('stdDiscRate') or item_data.get('std_disc') or 0)
        max_disc = float(item_data.get('maxDiscPer') or item_data.get('max_disc') or 0)
        
        # Parse expiry date
        expiry_date_str = item_data.get('expiryDate')
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            except:
                expiry_date = existing.expiry_date if existing else datetime(2099, 12, 31).date()
        else:
            expiry_date = existing.expiry_date if existing else datetime(2099, 12, 31).date()
            
        # MRP: preserve if not sent
        mrp_val = item_data.get('mrpBox') or item_data.get('mrp')
        if mrp_val is not None:
            mrp = float(mrp_val)
        else:
            mrp = existing.mrp if existing else 0.0
            
        # Batch No: preserve if not sent
        batch_no = item_data.get('batchNo') or item_data.get('batch_no')
        if batch_no is None:
            batch_no = existing.batch_no if existing else '-'
            
        item, created = ItemMaster.objects.update_or_create(
            item_code=item_code,
            defaults={
                'item_name': item_data.get('itemName', ''),
                'item_qty_per_box': item_data.get('itemQtyPerBox', 1),
                'batch_no': batch_no,
                'std_disc': std_disc,
                'max_disc': max_disc,
                'mrp': mrp,
                'expiry_date': expiry_date,
            }
        )
        return item
    except Exception as e:
        logger.error(f"Error updating ItemMaster cache: {str(e)}")
        return None


def fetch_stock_from_erp(item_code, store_id=None):
    """
    Fetch stock balance for a specific item directly from the ERP stock API (ws_c2_services_fetch_stock)
    Returns: Integer stock quantity (packQty) or 0 if not found/error
    NOTE: ERP returns ALL items regardless of itemCodes filter — we search locally after fetch.
    Fallback: uses local Stock DB (pack_qty) if ERP JSON is malformed/unreadable.
    """
    try:
        # Check Redis global stock cache first — avoids ERP call
        from .erp_redis_cache import ERPRedisCache
        from .erp_service import ERPService
        _store_id = store_id or '501'
        global_stock = ERPRedisCache.get_global_stock_map(_store_id)
        if global_stock and str(item_code) in global_stock:
            cached_item = global_stock[str(item_code)]
            batch_list = cached_item.get('batchDetails', [])
            from django.utils import timezone
            from datetime import datetime
            today = timezone.now().date()
            total_qty = 0
            for b in batch_list:
                pack_qty = float(b.get('packQty') or 0)
                expiry_str = b.get('expiryDate', '')
                try:
                    if expiry_str:
                        exp = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                        if exp >= today:
                            total_qty += pack_qty
                    else:
                        total_qty += pack_qty
                except Exception:
                    total_qty += pack_qty
            logger.info(f"[STOCK_DEBUG] Redis cache HIT for {item_code} — qty={total_qty}")
            return int(total_qty)
    except Exception as cache_err:
        logger.warning(f"[STOCK_DEBUG] Redis cache check failed for {item_code}: {cache_err}")

    try:
        from .erp_token_service import get_erp_token_for_store_config
        from .erp_service import ERPService
        from django.utils import timezone
        from datetime import datetime
        from .models import ItemMaster, ProductInfo, Stock
        
        if store_id:
            store_info = ERPService.get_config_by_store_id(store_id)
        else:
            store_info = ERPService._get_fallback_config()
            
        if not store_info:
            store_info = ERPService._get_fallback_config()
            
        erp_config = store_info['erp_config']
        api_key = get_erp_token_for_store_config(erp_config)
            
        if not api_key:
            logger.error("Could not get auto-generated token for stock fetch")
            return 0
        
        erp_url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
        
        erp_payload = {
            'apiKey':        api_key,
            'prodCode':      erp_config['prod_code'],
            'c2Code':        erp_config['c2_code'],
            'storeId':       erp_config['store_id'],
            'inputDateTime': '2021-07-01 10:10:00',
            'itemCodes':     [item_code]
        }
        
        response = requests.post(erp_url, json=erp_payload, timeout=60)
        response.raise_for_status()
        
        # ✅ Byte-level decode — handles BOM, bad chars, encoding issues that cause JSONDecodeError
        raw_bytes = response.content
        logger.info(f"[STOCK_DEBUG] ERP response size for {item_code}: {len(raw_bytes)} bytes")
        try:
            raw_text = raw_bytes.decode('utf-8', errors='replace').strip()
            # Remove BOM if present
            if raw_text.startswith('\ufeff'):
                raw_text = raw_text[1:]
            import json as _json
            import re as _re
            raw_text = _re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', raw_text)
            data = _json.loads(raw_text)
        except Exception as json_err:
            logger.error(f"[STOCK_DEBUG] ERP JSON malformed for {item_code} ({len(raw_bytes)} bytes): {json_err}")
            # ✅ Fallback: use local Stock DB pack_qty (synced from ERP via sync_itemmaster)
            try:
                stock_obj = Stock.objects.filter(item__item_code=item_code).first()
                if stock_obj:
                    logger.info(f"[STOCK_DEBUG] ERP parse failed → DB fallback pack_qty={stock_obj.pack_qty} for {item_code}")
                    return stock_obj.pack_qty or 0
            except Exception as db_err:
                logger.error(f"[STOCK_DEBUG] DB fallback also failed for {item_code}: {db_err}")
            return 0

        stock_items = []
        if isinstance(data, dict):
            stock_items = data.get('stockDetails', []) or data.get('data', [])
        elif isinstance(data, list):
            stock_items = data

        logger.info(f"[STOCK_DEBUG] total stock_items in ERP response: {len(stock_items)}")
            
        for stock_item in stock_items:
            item_code_val = stock_item.get('c_item_code') or stock_item.get('itemCode')
            # ✅ Type-safe comparison: ERP may return int or str for item code
            if str(item_code_val) == str(item_code):
                try:
                    batch_list = stock_item.get('batchDetails', [])
                    logger.info(f"[STOCK_DEBUG] MATCHED {item_code} — batchDetails: {batch_list}")
                    
                    qty_box = int(stock_item.get('qtyBox') or 1)
                    today = timezone.now().date()
                    
                    active_batches = []
                    expired_batches = []
                    zero_qty_batches = []
                    
                    for b in batch_list:
                        batch_no = b.get('batchNo', '')
                        expiry_date_str = b.get('expiryDate', '')
                        pack_qty = float(b.get('packQty') or 0)
                        mrp_box = float(b.get('mrpBox') or b.get('mrp') or 0)
                        
                        # Check expiry
                        is_expired = False
                        try:
                            if expiry_date_str:
                                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                                if expiry_date < today:
                                    is_expired = True
                            else:
                                expiry_date = datetime(2099, 12, 31).date()
                        except Exception:
                            expiry_date = datetime(2099, 12, 31).date()
                            is_expired = False
                            
                        batch_info = {
                            'batch_no': batch_no,
                            'expiry_date': expiry_date,
                            'pack_qty': pack_qty,
                            'mrp_box': mrp_box,
                            'is_expired': is_expired,
                            'raw': b
                        }
                        
                        if is_expired:
                            expired_batches.append(batch_info)
                        elif pack_qty <= 0:
                            zero_qty_batches.append(batch_info)
                        else:
                            active_batches.append(batch_info)
                            
                    # FEFO Logic for Selecting Batch
                    selected_batch = None
                    if active_batches:
                        active_batches.sort(key=lambda x: x['expiry_date'])
                        selected_batch = active_batches[0]
                    elif zero_qty_batches:
                        zero_qty_batches.sort(key=lambda x: x['expiry_date'])
                        selected_batch = zero_qty_batches[0]
                    elif expired_batches:
                        expired_batches.sort(key=lambda x: x['expiry_date'], reverse=True)
                        selected_batch = expired_batches[0]
                        
                    mrp_box = 0.0
                    expiry_date = datetime(2099, 12, 31).date()
                    batch_no = '-'
                    
                    if selected_batch:
                        mrp_box = selected_batch['mrp_box']
                        expiry_date = selected_batch['expiry_date']
                        batch_no = selected_batch['batch_no']
                    
                    # Update local database cache
                    item, _ = ItemMaster.objects.update_or_create(
                        item_code=item_code,
                        defaults={
                            'item_name': stock_item.get('itemName') or 'Unknown Product',
                            'item_qty_per_box': qty_box,
                            'batch_no': batch_no,
                            'mrp': mrp_box, # Use mrpBox from the ERP as the price!
                            'expiry_date': expiry_date,
                        }
                    )
                    
                    # Ensure ProductInfo
                    ProductInfo.objects.update_or_create(
                        item=item,
                        defaults={
                            'type_label': stock_item.get('contName') or 'Medicine',
                        }
                    )
                    
                    # Sum across all active/non-expired batches
                    total_pack_qty = sum(int(b['pack_qty']) for b in active_batches)
                    total_bal_ls_qty = sum(int(b['raw'].get('totalBalLsQty') or 0) for b in active_batches)
                    total_loose_qty = sum(int(b['raw'].get('looseQty') or 0) for b in active_batches)
                    
                    # Update Stock table
                    Stock.objects.update_or_create(
                        item=item,
                        store_id=store_id or erp_config['store_id'],
                        defaults={
                            'total_bal_ls_qty': total_bal_ls_qty,
                            'pack_qty': total_pack_qty,
                            'loose_qty': total_loose_qty,
                            'qty_box': qty_box,
                            'cont_code': stock_item.get('contCode') or stock_item.get('cont_code') or '-',
                            'cont_name': stock_item.get('contName') or stock_item.get('cont_name') or '-',
                        }
                    )
                    
                    logger.info(f"[STOCK_DEBUG] Updated item {item_code}: stock={total_pack_qty}, mrp_box={mrp_box}, batch={batch_no}, expiry={expiry_date}")
                    return total_pack_qty
                except Exception as inner_e:
                    logger.error(f"[STOCK_DEBUG] Error processing stockDetails for {item_code}: {inner_e}", exc_info=True)
                    return 0
        logger.warning(f"[STOCK_DEBUG] item_code='{item_code}' NOT FOUND in ERP stock response ({len(stock_items)} items)")
        return 0
    except Exception as e:
        logger.error(f"[STOCK_DEBUG] Exception in fetch_stock_from_erp for {item_code}: {str(e)}", exc_info=True)
        return 0



def get_item_stock_status(item_code, store_id=None):
    """
    Fetch stock availability status for item from ERP
    CRITICAL CHECKS:
    - Stock quantity > 0
    - Expiry date not passed
    Always fresh - no caching
    [UPDATED] Now uses auto-generated token automatically and supports store_id
    """
    try:
        from django.utils import timezone
        from .models import ItemMaster
        
        # 1. Fetch stock and update the local DB
        stock_qty = fetch_stock_from_erp(item_code, store_id=store_id)
        
        # 2. Get the updated ItemMaster from the database
        item = ItemMaster.objects.filter(item_code=item_code).first()
        
        # If still not found, fallback to fetching master data (or auto-create)
        if not item:
            item_data = fetch_item_from_erp(item_code, store_id=store_id)
            if item_data:
                item = update_itemmaster_cache(item_code, item_data)
        
        if not item:
            return {
                'available': False,
                'status': 'Product not found',
                'qty': 0,
                'price': 0.0,
                'discount': 0.0,
                'expiry_date': None,
                'is_expired': False
            }
            
        today = timezone.now().date()
        is_expired = item.expiry_date < today if item.expiry_date else False
        available = stock_qty > 0 and not is_expired
        
        if is_expired:
            status = 'EXPIRED - Cannot Order'
        elif stock_qty == 0:
            status = 'Out of Stock'
        else:
            status = 'In Stock'
            
        # Get price from Redis stock cache — DB mrp is often 0
        redis_price = 0.0
        try:
            from .erp_redis_cache import ERPRedisCache
            _store_id = store_id or '501'
            global_stock = ERPRedisCache.get_global_stock_map(_store_id)
            if global_stock and str(item_code) in global_stock:
                batches = global_stock[str(item_code)].get('batchDetails', [])
                for b in batches:
                    bp = float(b.get('mrpBox') or b.get('mrp') or 0)
                    if bp > 0:
                        redis_price = bp
                        break
        except Exception:
            pass
        final_price = redis_price if redis_price > 0 else float(item.mrp)

        return {
            'available': available,
            'status': status,
            'qty': int(stock_qty),
            'price': final_price,
            'discount': float(item.std_disc),
            'expiry_date': str(item.expiry_date) if item.expiry_date else None,
            'is_expired': is_expired
        }
    except Exception as e:
        logger.error(f"Error getting stock status: {str(e)}", exc_info=True)
        return {'available': False, 'status': 'Unable to check availability', 'qty': 0, 'is_expired': False, 'expiry_date': None}


# ================== ADDRESS VIEWS ==================

class ListAddressesView(APIView):
    """List all delivery addresses for user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all addresses"""
        try:
            user = request.user
            addresses = Address.objects.filter(user=user, is_active=True).order_by('-is_default', '-created_at')
            serializer = AddressListSerializer(addresses, many=True)
            logger.info(f"[ADDRESS_LIST] User {request.user.id} retrieved {len(addresses)} addresses")
            return Response({
                'success': True,
                'count': len(addresses),
                'data': serializer.data,
                'message': 'Addresses retrieved successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error listing addresses for user {request.user.id}: {str(e)}")
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
            # Check if Content-Type is incorrect and try to parse it anyway
            content_type = request.META.get('CONTENT_TYPE', '')
            request_data = request.data
            
            if 'text/plain' in content_type:
                # Try to parse the body as JSON if Content-Type is text/plain
                try:
                    request_data = json.loads(request.body.decode('utf-8'))
                    logger.info(f"[ADDRESS_CREATE] Parsed text/plain request body as JSON for user {request.user.id}")
                except (json.JSONDecodeError, UnicodeDecodeError) as parse_err:
                    logger.error(f"[ADDRESS_ERROR] Could not parse text/plain request body for user {request.user.id}: {str(parse_err)}")
                    return Response({
                        'success': False,
                        'message': 'Invalid Content-Type. Please set Content-Type to application/json and ensure body is valid JSON'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            user = request.user
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
                logger.info(f"[ADDRESS_CREATE] User {request.user.id} added address: {address.name} ({address.address_type}) - {gps_info}")
                
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
            logger.error(f"[ADDRESS_ERROR] Error creating address for user {request.user.id}: {str(e)}")
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
            user = request.user
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
                logger.info(f"[ADDRESS_UPDATE] User {request.user.id} updated address ID {address_id} - {gps_info}")
                
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
            logger.error(f"[ADDRESS_ERROR] Error updating address {address_id} for user {request.user.id}: {str(e)}")
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
            user = request.user
            address = get_object_or_404(Address, id=address_id, user=user)
        except:
            return Response({
                'success': False,
                'message': 'Address not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            address.is_active = False
            address.save()
            logger.info(f"[ADDRESS_DELETE] User {request.user.id} deleted address ID {address_id}")
            
            return Response({
                'success': True,
                'message': 'Address deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error deleting address {address_id} for user {request.user.id}: {str(e)}")
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
            user = request.user
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
            logger.info(f"[ADDRESS_DEFAULT] User {request.user.id} set address ID {address_id} as default")
            
            return Response({
                'success': True,
                'message': 'Default address set successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ADDRESS_ERROR] Error setting default address {address_id} for user {request.user.id}: {str(e)}")
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
            
            address_id = serializer.validated_data.get('address_id')
            
            # Get address - either specified or use default/last used
            if address_id:
                # Use specified address
                try:
                    address = Address.objects.get(id=address_id, user=request.user, is_active=True)
                except Address.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': 'Selected address not found or not available'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                # Auto-select: Try default address first, then most recently created
                address = Address.objects.filter(
                    user=request.user, 
                    is_active=True, 
                    is_default=True
                ).first()
                
                if not address:
                    # No default address, use the most recently created
                    address = Address.objects.filter(
                        user=request.user, 
                        is_active=True
                    ).order_by('-created_at').first()
                
                if not address:
                    return Response({
                        'success': False,
                        'message': 'No active delivery address found. Please add an address first.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
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
            
            # Prepare order data (order_id will be auto-generated in SalesOrder.save())
            order_data = {
                'c2_code': address.pincode[:3],
                'store_id': getattr(request.user.kyc, 'user_id', '00001'),
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
                # Create sales order with address and fulfilling store
                # Get user's preferred store or find nearest store for fulfillment
                from .store_manager import StoreLocationManager
                fulfilling_store = request.user.preferred_store
                if not fulfilling_store:
                    # Fallback: find nearest store if not set on user
                    store_info = StoreLocationManager.find_nearest_store(28.7041, 77.1025)
                    fulfilling_store = store_info['store'] if store_info else Store.objects.filter(is_active=True, is_primary=True).first()
                
                # Create sales order with address and fulfilling store
                sales_order = SalesOrder.objects.create(
                    **order_data,
                    delivery_address=address,
                    fulfilling_store=fulfilling_store,
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
                
                # NOTE: Cart will be cleared AFTER payment succeeds
                # (Not immediately - so user can retry if payment fails)
                
                # Get payment method from request
                payment_method = serializer.validated_data.get('payment_method', 'RAZORPAY')
                
                logger.info(f"[ORDER_CHECKOUT] User {request.user.username} completed checkout with address ID {address_id} - Payment Method: {payment_method}")
                logger.info(f"[ORDER_CREATED] Order {sales_order.order_id} created for {address.name} at {address.get_full_address()}")

                # ── Audit log ──
                try:
                    from maindash.views import log_audit
                    log_audit(
                        action='Order Synced',
                        performed_by_user=request.user,
                        target_entity=sales_order.order_id,
                        details=f'Order placed for {address.name} — Total: ₹{total_amount:.2f} via {payment_method}',
                        category='Order',
                    )
                except Exception:
                    pass
                
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
            request_data = _parse_request_data(request)
            serializer = DetectLocationSerializer(data=request_data)
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
            
            # ── Persist detected location to user profile automatically ──
            user = get_object_or_404(User, id=user_id)
            try:
                user.last_latitude = float(latitude)
                user.last_longitude = float(longitude)
                user.last_location_update = timezone.now()
                pincode = address_data.get('pincode')
                if pincode:
                    user.location_pincode = pincode
                
                # Update user's preferred store to nearest store automatically
                from .store_manager import StoreLocationManager
                store_data = StoreLocationManager.find_nearest_store(float(latitude), float(longitude))
                if store_data and store_data.get('store_id'):
                    from .models import Store as _Store
                    try:
                        user.preferred_store = _Store.objects.get(pk=store_data['store_id'])
                    except _Store.DoesNotExist:
                        pass
                user.save(update_fields=[
                    'last_latitude', 'last_longitude', 'last_location_update',
                    'location_pincode', 'preferred_store'
                ])
                logger.info(f"[LOCATION_DETECT] Auto-saved coordinates to user {user_id} profile: ({latitude}, {longitude})")
            except Exception as persist_err:
                logger.warning(f"[LOCATION_DETECT] Could not auto-save location to profile for user {user_id}: {persist_err}")

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
            request_data = _parse_request_data(request)
            serializer = ConfirmLocationAddressSerializer(data=request_data)
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
            
            # Get user from authenticated request
            user = request.user
            
            # Verify address belongs to user
            try:
                address = Address.objects.get(id=address_id, user=user, is_active=True)
            except Address.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Selected address not found or not available'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get user's cart
            try:
                cart = Cart.objects.get(user=user)
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
            
            # For pre-order wallet preview, apply wallet in this orderflow
            wallet, _ = RetailerWallet.objects.get_or_create(retailer=user)
            wallet_balance = float(wallet.balance)
            
            # Cart total approach: calculate wallet applicable based on grand total
            wallet_applicable = min(wallet_balance, amount_payable)
            amount_after_wallet = max(0, amount_payable - wallet_applicable)
            
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
                    'wallet_info': {
                        'wallet_balance': wallet_balance,
                        'wallet_applicable': wallet_applicable,
                        'amount_after_wallet': amount_after_wallet
                    },
                    'item_count': len(cart_items)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"[PREVIEW_ERROR] Error generating order preview for user {user_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error generating order preview: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== RECOMMENDATION VIEWS ====================

class FrequentlyBoughtTogetherView(APIView):
    """
    Get products frequently bought together with a specific item (with ERP enrichment)
    GET: Fetch products often purchased with the provided item based on order history
    Requires JWT authentication
    
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
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            item_code = request.query_params.get('itemCode')
            limit = int(request.query_params.get('limit', 5))
            days = int(request.query_params.get('days', 90))
            # [UPDATED] Token now auto-generated - no need for apiKey from request
            use_erp = True  # Always use ERP with auto-generated token
            
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
            erp_map, stock_map = fetch_items_with_stock_and_batches(frequently_bought_item_codes)
            
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
                
                # Attach live batchDetails
                stock_entry = stock_map.get(str(product.item_code))
                product.erp_batch_details = stock_entry.get('batchDetails', []) if stock_entry else []
                
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
            erp_map, stock_map = fetch_items_with_stock_and_batches(top_item_codes)
            
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
                
                # Attach live batchDetails
                stock_entry = stock_map.get(str(product.item_code))
                product.erp_batch_details = stock_entry.get('batchDetails', []) if stock_entry else []
                
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
    Requires JWT authentication
    
    Query Parameters:
        - limit: Max number of recommendations (default: 15)
        - apiKey: Optional API key to fetch fresh data from ERP
    
    Example: /api/recommendations/for-you/?limit=15&apiKey=xyz
    
    Algorithm:
    1. Get user's purchase history (categories they bought from)
    2. Get user's search history (keywords they searched)
    3. Find similar products in those categories
    4. Rank by category frequency + popularity + stock
    5. Fetch fresh ERP data
    6. Return personalized recommendations
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_id = request.user.id
        try:
            limit = int(request.query_params.get('limit', 15))
            # [UPDATED] Token now auto-generated - no need for apiKey from request
            use_erp = True  # Always use ERP with auto-generated token
            
            user_id = str(request.user.id)
            
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
            
            # Convert to list so we can append/fill default products if needed
            rec_products_list = list(recommended_products)
            
            # Ensure we return at least 10 products by default
            target_count = max(10, limit)
            if len(rec_products_list) < target_count:
                fill_needed = target_count - len(rec_products_list)
                existing_item_codes = [p.item.item_code for p in rec_products_list if p.item]
                
                # Fetch default ProductInfo records that are not already in existing_item_codes
                default_infos = ProductInfo.objects.exclude(
                    item__item_code__in=existing_item_codes
                ).select_related('item', 'category')[:fill_needed]
                
                rec_products_list.extend(list(default_infos))
                
                # If we still need more, fallback to any ItemMaster records
                if len(rec_products_list) < target_count:
                    still_needed = target_count - len(rec_products_list)
                    current_item_codes = [p.item.item_code for p in rec_products_list if p.item]
                    fallback_items = ItemMaster.objects.exclude(
                        item_code__in=current_item_codes
                    )[:still_needed]
                    
                    for item in fallback_items:
                        p_info, _ = ProductInfo.objects.get_or_create(item=item)
                        rec_products_list.append(p_info)
            
            if not rec_products_list:
                logger.warning(f"[PERSONALIZED] No products available at all for user {user_id}")
                return Response({
                    'success': True,
                    'message': 'No recommendations available',
                    'count': 0,
                    'recommendationType': fallback_source,
                    'reason': 'No products available',
                    'userId': user_id,
                    'data': [],
                    'purchaseCategories': len(purchased_products),
                    'searchKeywords': search_keywords,
                    'lastFetched': timezone.now().isoformat()
                }, status=status.HTTP_200_OK)
            
            # ✅ Step 4: Fetch fresh data from ERP and enrich with auto-generated token
            rec_item_codes = [p_info.item.item_code for p_info in rec_products_list if p_info.item and p_info.item.item_code]
            erp_map, stock_map = fetch_items_with_stock_and_batches(rec_item_codes)
            
            products_data = []
            for product_info in rec_products_list:
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
                
                # Attach live batchDetails
                stock_entry = stock_map.get(str(item.item_code))
                item.erp_batch_details = stock_entry.get('batchDetails', []) if stock_entry else []
                
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
            
            # ✅ Step 3: Find products matching popular searches
            from django.db.models import Q
            
            popular_product_codes = set()
            if popular_searches.exists():
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
            
            # Convert to list so we can append default products if needed
            products_list = list(popular_items)
            
            # Ensure we return at least 10 products by default
            target_count = max(10, limit)
            if len(products_list) < target_count:
                fill_needed = target_count - len(products_list)
                existing_codes = [p.item_code for p in products_list]
                
                # Fetch default products (prioritize those with product_info so they are richer)
                default_products = ItemMaster.objects.filter(
                    product_info__isnull=False
                ).exclude(
                    item_code__in=existing_codes
                )[:fill_needed]
                
                default_products_list = list(default_products)
                
                # If we still need more, fallback to any ItemMaster records
                if len(products_list) + len(default_products_list) < target_count:
                    still_needed = target_count - (len(products_list) + len(default_products_list))
                    all_existing_codes = existing_codes + [p.item_code for p in default_products_list]
                    fallback_products = ItemMaster.objects.exclude(
                        item_code__in=all_existing_codes
                    )[:still_needed]
                    default_products_list.extend(list(fallback_products))
                
                products_list.extend(default_products_list)
            
            # ✅ Step 4: Fetch fresh data from ERP with auto-generated token
            popular_item_codes = [itm.item_code for itm in products_list]
            erp_map, stock_map = fetch_items_with_stock_and_batches(popular_item_codes)
            
            products_data = []
            search_count_map = {search.query: search.search_count for search in popular_searches}
            
            for item in products_list:
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
                
                # Attach live batchDetails
                stock_entry = stock_map.get(str(item.item_code))
                item.erp_batch_details = stock_entry.get('batchDetails', []) if stock_entry else []
                
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
    Requires JWT authentication
    
    Query Parameters:
        - limit: Max number of products (default: 10)
    
    Example: /api/recommendations/recently-viewed/?limit=10
    
    Data Flow:
    1. Get ProductView records for user
    2. Order by most recently viewed
    3. Limit to requested count
    4. Fetch live ERP data for each
    5. Return with fresh pricing/stock info
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_id = request.user.id
        try:
            limit = int(request.query_params.get('limit', 10))
            
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
                        'userName': request.user.username,
                        'recentlyViewed': [],
                        'totalCount': 0,
                        'source': 'database'
                    }
                }, status=status.HTTP_200_OK)
            
            # Extract items
            viewed_items = [pv.item for pv in recently_viewed]
            
            # ✅ Step 2: Fetch fresh data from ERP with auto-generated token
            viewed_item_codes = [itm.item_code for itm in viewed_items if itm and itm.item_code]
            erp_map, stock_map = fetch_items_with_stock_and_batches(viewed_item_codes)
            
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
                
                # Attach live batchDetails
                stock_entry = stock_map.get(str(product.item_code))
                product.erp_batch_details = stock_entry.get('batchDetails', []) if stock_entry else []
                
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
                    'userName': request.user.username,
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
    Requires JWT authentication
    
    Query Parameters:
        - limit: Max number of items per category (default: 10)
        - viewed_limit: Specific limit for recently viewed (overrides limit)
        - cart_limit: Specific limit for cart items (overrides limit)
        - wishlist_limit: Specific limit for wishlist items (overrides limit)
    
    Example: /api/recommendations/user-activity/?limit=5
    Response includes all three: recentlyViewed, recentlyCart, recentlyWishlist
    
    Data Flow:
    1. Get recently viewed products
    2. Get cart items
    3. Get wishlist items
    4. Fetch live ERP data for all
    5. Return consolidated response with all activities
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_id = request.user.id
        try:
            # Get limits from query params
            limit = int(request.query_params.get('limit', 10))
            viewed_limit = int(request.query_params.get('viewed_limit', limit))
            cart_limit = int(request.query_params.get('cart_limit', limit))
            wishlist_limit = int(request.query_params.get('wishlist_limit', limit))
            
            # ✅ Collect relevant item codes before fetching
            viewed_codes = list(ProductView.objects.filter(user_id=user_id).values_list('item__item_code', flat=True)[:viewed_limit])
            cart_codes = []
            try:
                cart_codes = list(CartItem.objects.filter(cart__user_id=user_id).values_list('item__item_code', flat=True)[:cart_limit])
            except:
                pass
            wishlist_codes = []
            try:
                wishlist_codes = list(WishlistItem.objects.filter(wishlist__user_id=user_id).values_list('item__item_code', flat=True)[:wishlist_limit])
            except:
                pass
                
            combined_codes = list(set(viewed_codes + cart_codes + wishlist_codes))
            
            # ✅ Fetch ERP data once (reuse for all)
            erp_items = fetch_items_by_codes_from_erp(combined_codes)
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
                    'userName': request.user.username,
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
    permission_classes = [IsAuthenticated]
    
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
        # Fetch ERP master data to enrich with stock quantities
        try:
            from .models import ProductInfo
            active_product_codes = list(ProductInfo.objects.filter(
                category__is_active=True
            ).values_list('item__item_code', flat=True).distinct())
            
            items = fetch_items_by_codes_from_erp(active_product_codes)
            if items:
                # Create mapping of item_code -> stockBalQty from ERP
                stock_map = {}
                for item in items:
                    if item.get('c_item_code'):
                        stock_map[item['c_item_code']] = item.get('stockBalQty', 0)
                
                context['erp_stock_map'] = stock_map
                logger.info(f"[CATEGORIES] [SUCCESS] Successfully enriched with {len(stock_map)} ERP items")
            else:
                logger.error("[CATEGORIES] ERP Server returned no items or failed")
                context['erp_stock_map'] = {}
        except Exception as e:
            logger.error(f"[CATEGORIES] [FAILED] Failed to fetch ERP data: {str(e)}")
            context['erp_stock_map'] = {}
        
        return context
    


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def related_products(request, product_id):
    """
    Get related products by category (excluding the current product), enriched with ERP data if available.
    Requires JWT authentication.
    """
    from .views import fetch_items_by_codes_from_erp, parse_date
    try:
        try:
            product = ProductInfo.objects.get(pk=product_id)
        except ProductInfo.DoesNotExist:
            try:
                item = ItemMaster.objects.get(item_code=product_id)
                product, _ = ProductInfo.objects.get_or_create(item=item)
            except ItemMaster.DoesNotExist:
                return Response({"error": "Product not found"}, status=404)

        if product.category:
            related_queryset = ProductInfo.objects.filter(
                category=product.category
            ).exclude(pk=product.pk)[:10]
            related_list = list(related_queryset)
        else:
            related_list = []

        # Ensure we always return at least 10 related products as fallback
        if len(related_list) < 10:
            fill_needed = 10 - len(related_list)
            exclude_pks = [product.pk] + [p.pk for p in related_list]
            fill_products = ProductInfo.objects.exclude(
                pk__in=exclude_pks
            )[:fill_needed]
            related_list.extend(list(fill_products))
            
            # If still need more, fallback to wrap any other ItemMaster records
            if len(related_list) < 10:
                still_needed = 10 - len(related_list)
                current_item_codes = [p.item.item_code for p in related_list if p.item] + [product.item.item_code]
                fallback_items = ItemMaster.objects.exclude(
                    item_code__in=current_item_codes
                )[:still_needed]
                for f_item in fallback_items:
                    p_info, _ = ProductInfo.objects.get_or_create(item=f_item)
                    related_list.append(p_info)
                    
        related = related_list

        # ERP enrichment logic: only lookup the related item codes
        related_codes = [p_info.item.item_code for p_info in related if p_info.item and p_info.item.item_code]
        erp_items = fetch_items_by_codes_from_erp(related_codes)
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
                        item=item
                    ).exists()
                    wishlist_status = WishlistItem.objects.filter(
                        wishlist__user=request.user,
                        item=item
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
    
class RetailerOrdersView(APIView):
    """
    Get all orders for the authenticated retailer
    GET /api/orders/
    Query params: ?status=active|completed|all (default: all)
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # ── Use authenticated user ──
        user = request.user

        filter_status = request.query_params.get('status', 'all').lower()
        if filter_status not in ['active', 'completed', 'all']:
            return Response({
                'success': False,
                'message': 'Invalid status filter. Use: active, completed, or all'
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── Fetch orders for this user ──
        # user_id stored as string in SalesOrder (see CreateSalesOrderView)
        orders = SalesOrder.objects.filter(
            user_id=str(user.id)
        ).prefetch_related('items', 'payments').order_by('-created_at')

        if not orders.exists():
            result_data = {'active': [], 'completed': []} if filter_status == 'all' else []
            return Response({
                'success': True,
                'message': 'No orders found',
                'data': result_data
            }, status=status.HTTP_200_OK)

        active_orders = []
        completed_orders = []

        for order in orders:

            # ── Check if order should be hidden ──
            # Hide pending online payment orders (Razorpay) - show only pending COD orders
            payment = order.payments.first() if order.payments.exists() else None
            # We don't continue anymore, we show them as Cancelled if they are Razorpay PENDING
            
            # ── Determine order status (matching superadmin logic) ──
            # Based on payment outcome and ERP conversion flags
            is_cod = payment and payment.payment_method == 'COD'

            if payment and payment.status in ['FAILED', 'CANCELLED']:
                # Online payment explicitly failed or cancelled
                order_status = 'Cancelled'
                is_completed = True
            elif payment and payment.status in ['PENDING', 'INITIATED'] and payment.payment_method not in ('COD',):
                # Online payment was initiated but never completed
                order_status = 'Cancelled'
                is_completed = True
            elif is_cod:
                # COD order status logic:
                if order.dc_conversion_flag:
                    order_status = 'Delivered'
                    is_completed = True
                elif order.ord_conversion_flag:
                    order_status = 'Confirmed'
                    is_completed = True
                elif order.invoices.exists():
                    # Order has invoice - show as Dispatched
                    order_status = 'Dispatched'
                    # COD order is NOT completed until admin confirms it
                    is_completed = False
                else:
                    order_status = 'Pending'
                    is_completed = False
            else:
                # Online payment or standard flow
                if order.dc_conversion_flag:
                    # Order delivered
                    order_status = 'Delivered'
                    is_completed = True
                elif order.invoices.exists():
                    # Order has invoice - show as Dispatched
                    order_status = 'Dispatched'
                    is_completed = True
                elif order.ord_conversion_flag:
                    # Order confirmed
                    order_status = 'Confirmed'
                    is_completed = True
                elif payment and payment.status == 'SUCCESS' and payment.payment_method not in ('COD',):
                    # Online payment received = auto-Confirmed
                    order_status = 'Confirmed'
                    is_completed = True
                else:
                    # COD or pending order
                    order_status = 'Pending'
                    is_completed = False

            # ── Build timeline ──
            timeline = []
            timeline.append({
                'label': 'Created',
                'date': timezone.localtime(order.created_at).strftime('%Y-%m-%d %I:%M %p') if order.created_at else '',
                'status': 'completed'
            })
            if order.ord_conversion_flag:
                timeline.append({
                    'label': 'Confirmed',
                    'date': timezone.localtime(order.updated_at).strftime('%Y-%m-%d %I:%M %p') if order.updated_at else '',
                    'status': 'completed'
                })
            if order.dc_conversion_flag:
                timeline.append({
                    'label': 'Delivered',
                    'date': timezone.localtime(order.updated_at).strftime('%Y-%m-%d %I:%M %p') if order.updated_at else '',
                    'status': 'completed'
                })

            # ── Build items list ──
            items_data = []
            for order_item in order.items.all():
                # Skip items with empty product codes
                if not order_item.item_code or str(order_item.item_code).strip() == "":
                    logger.debug(f"[RETAILER_ORDERS] Skipping order item {order_item.id} with empty code")
                    continue

                image_url = None
                subheading = ""
                type_label = ""
                description = ""

                # FIX: item_code is a plain CharField in SalesOrderItem
                # Must look up ItemMaster first, then ProductInfo
                try:
                    item_master = ItemMaster.objects.get(
                        item_code=order_item.item_code
                    )
                    try:
                        product_info = ProductInfo.objects.get(item=item_master)
                        subheading = product_info.subheading or ""
                        type_label = product_info.type_label or ""
                        description = product_info.description or ""

                        first_image = product_info.images.order_by(
                            'image_order'
                        ).first()
                        if first_image and first_image.image:
                            image_url = request.build_absolute_uri(
                                first_image.image.url
                            )
                    except ProductInfo.DoesNotExist:
                        # Item exists in ERP but no product info added yet
                        logger.info(
                            f"[RETAILER_ORDERS] No ProductInfo for: "
                            f"{order_item.item_code}"
                        )
                except ItemMaster.DoesNotExist:
                    # Item not yet synced to local DB from ERP
                    logger.warning(
                        f"[RETAILER_ORDERS] ItemMaster not found for code: {order_item.item_code} "
                        f"(Order: {order.order_id})"
                    )
                except Exception as e:
                    logger.error(
                        f"[RETAILER_ORDERS] Error fetching product info "
                        f"for {order_item.item_code}: {str(e)}"
                    )

                # FIX: item_total fallback guards against None/zero sale_rate
                if order_item.item_total:
                    line_total = str(order_item.item_total)
                else:
                    rate = float(order_item.sale_rate or 0)
                    qty = int(order_item.total_loose_qty or 0)
                    disc = float(order_item.disc_per or 0)
                    line_total = str(round(rate * (1 - disc / 100) * qty, 2))

                items_data.append({
                    'item_id': order_item.id,
                    'item_code': order_item.item_code,
                    'name': order_item.item_name or order_item.item_code,
                    'subheading': subheading,
                    'type_label': type_label,
                    'description': description,
                    'image': image_url,
                    'qty': order_item.total_loose_qty,
                    'batch_no': order_item.batch_no or '',
                    'expiry_date': str(order_item.expiry_date) if order_item.expiry_date else None,
                    # ERP spec fields
                    'sale_rate': str(order_item.sale_rate or 0),
                    'disc_per': str(order_item.disc_per or 0),
                    'total': line_total,
                })

            order_data = {
                'order_id': order.order_id,
                'document_pk': order.document_pk,
                'date': order.ord_date.strftime('%Y-%m-%d') if order.ord_date else '',
                'time': str(order.ord_time) if order.ord_time else '',
                'patient_name': order.patient_name or '',
                'mobile_no': order.mobile_no or '',
                'total': str(order.order_total or 0),
                'bill_total': str(order.bill_total or 0),
                'status': order_status,
                # ERP spec flags
                'ord_conversion_flag': order.ord_conversion_flag,
                'dc_conversion_flag': order.dc_conversion_flag,
                'is_completed': is_completed,
                'item_count': len(items_data),
                'items': items_data,
                'timeline': timeline,
            }

            if is_completed:
                completed_orders.append(order_data)
            else:
                active_orders.append(order_data)

        # ── Filter response ──
        if filter_status == 'active':
            result_data = active_orders
            message = f'Found {len(active_orders)} active order(s)'
        elif filter_status == 'completed':
            result_data = completed_orders
            message = f'Found {len(completed_orders)} completed order(s)'
        else:
            result_data = {
                'active': active_orders,
                'completed': completed_orders,
                'total_active': len(active_orders),
                'total_completed': len(completed_orders),
            }
            message = (
                f'Found {len(active_orders)} active and '
                f'{len(completed_orders)} completed order(s)'
            )

        logger.info(
            f"[RETAILER_ORDERS] User {user.id} | "
            f"Active: {len(active_orders)} | "
            f"Completed: {len(completed_orders)}"
        )

        return Response({
            'success': True,
            'message': message,
            'data': result_data
        }, status=status.HTTP_200_OK)

# ==================== ORDER MANAGEMENT VIEWS ====================

class SuperAdminOrdersView(APIView):
    """
    API endpoint for superadmin to get all orders with items and payment info.
    GET /api/superadmin/orders/ - Get all orders with their line items
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all orders with items and payment details"""
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)

        # Query params for filtering
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search', '').strip()

        orders = SalesOrder.objects.prefetch_related(
            'items', 'payments'
        ).order_by('-created_at')

        # Filter by conversion status (maps to frontend status labels)
        if status_filter:
            status_map = {
                'Confirmed': {'ord_conversion_flag': True, 'dc_conversion_flag': False},
                'Dispatched': {'dc_conversion_flag': True},
                'Pending': {'ord_conversion_flag': False, 'dc_conversion_flag': False},
            }
            if status_filter in status_map:
                orders = orders.filter(**status_map[status_filter])

        # Search by order_id, patient_name, cust_name, or retailer shop_name (via KYC)
        if search:
            from django.db.models import Q
            # First get matching order_ids from direct order fields
            direct_matches = orders.filter(
                Q(order_id__icontains=search) |
                Q(patient_name__icontains=search) |
                Q(cust_name__icontains=search)
            )
            
            # Also search by retailer shop_name via KYC
            kyc_matches = KYC.objects.filter(shop_name__icontains=search).values_list('user_id', flat=True)
            shop_name_orders = SalesOrder.objects.filter(user_id__in=[str(uid) for uid in kyc_matches])
            
            # Combine both querysets
            order_ids = set(direct_matches.values_list('id', flat=True)) | set(shop_name_orders.values_list('id', flat=True))
            orders = SalesOrder.objects.filter(id__in=order_ids).prefetch_related('items', 'payments').order_by('-created_at')

        results = []
        for order in orders:
            # Determine order status
            payment = order.payments.first()
            payment_method = payment.get_payment_method_display() if payment else 'COD'
            payment_status = payment.status if payment else 'PENDING'

            # Check for cancelled or failed payments
            is_razorpay_success = payment and payment.payment_method == 'RAZORPAY' and payment.status == 'SUCCESS'
            
            if payment and payment.payment_method == 'RAZORPAY':
                if payment.status == 'SUCCESS':
                    order_status = 'Confirmed'
                else:
                    # FAILED, CANCELLED, PENDING, INITIATED -> Cancelled
                    order_status = 'Cancelled'
            elif order.dc_conversion_flag:
                order_status = 'Dispatched'
            elif order.ord_conversion_flag:
                order_status = 'Confirmed'
            else:
                order_status = 'Pending'
                
            # Only COD orders in Pending state need admin confirmation
            needs_admin_confirmation = (order_status == 'Pending' and payment and payment.payment_method == 'COD')

            # Build items list for modal
            items_data = []
            for item in order.items.all():
                items_data.append({
                    'name': item.item_name or item.item_code,
                    'item_code': item.item_code,
                    'qty': item.total_loose_qty,
                    'mrp': float(item.sale_rate),
                    'total': float(item.item_total) if item.item_total else float(item.sale_rate) * item.total_loose_qty,
                    'batch_no': item.batch_no,
                })

            # Build timeline
            timeline = []
            timeline.append({
                'label': 'Created',
                'date': timezone.localtime(order.created_at).strftime('%Y-%m-%d %I:%M %p') if order.created_at else '',
                'status': 'completed'
            })
            if order.ord_conversion_flag:
                timeline.append({
                    'label': 'Confirmed',
                    'date': timezone.localtime(order.updated_at).strftime('%Y-%m-%d %I:%M %p') if order.updated_at else '',
                    'status': 'completed'
                })
            if order.dc_conversion_flag:
                timeline.append({
                    'label': 'Dispatched',
                    'date': timezone.localtime(order.updated_at).strftime('%Y-%m-%d %I:%M %p') if order.updated_at else '',
                    'status': 'completed'
                })
                
            # Get retailer shop name from KYC via user_id
            retailer_shop_name = ''
            retailer_id = order.store_id if order.store_id else 'RET001'

            # Try to find the retailer user and get shop_name from KYC
            if order.user_id:
                try:
                    if order.user_id.isdigit():
                        retailer_user = get_user_model().objects.select_related('kyc').get(id=int(order.user_id))
                        # Get shop name from KYC
                        if hasattr(retailer_user, 'kyc') and retailer_user.kyc and retailer_user.kyc.shop_name:
                            retailer_shop_name = retailer_user.kyc.shop_name
                            if retailer_user.kyc.user_id:
                                retailer_id = retailer_user.kyc.user_id
                        # Fallback: use retailer username if no KYC shop_name
                        elif not retailer_shop_name:
                            retailer_shop_name = retailer_user.username
                except (ValueError, get_user_model().DoesNotExist):
                    pass

            # Final fallback: check if we can find KYC with c2_code
            if not retailer_shop_name and order.c2_code:
                try:
                    kyc = KYC.objects.filter(user__c2_code=order.c2_code).first()
                    if kyc and kyc.shop_name:
                        retailer_shop_name = kyc.shop_name
                        retailer_id = kyc.user.c2_code or retailer_id
                except Exception:
                    pass

            # Last resort fallback
            if not retailer_shop_name:
                retailer_shop_name = order.cust_name or order.patient_name or 'Unknown Retailer'

            results.append({
                'id': order.order_id,
                'retailer_id': retailer_id,
                'retailer': retailer_shop_name,
                'date': order.ord_date.strftime('%Y - %m - %d') if order.ord_date else '', # Figma format
                'items': order.items.count(),
                'total': str(order.order_total),
                'payment': payment_method,
                'payment_status': payment_status,
                'status': order_status,
                'erpRef': order.document_pk or f"{order.tran_prefix} - {order.tran_srno}" if order.tran_prefix else '',
                'detailedTimeline': timeline,
                'detailedItems': items_data,
                'needs_admin_confirmation': needs_admin_confirmation,
                'requires_admin_action': needs_admin_confirmation,
            })

        # ── Post-loop filter for payment-derived statuses ──────────────────
        # DB-level flags can't capture Razorpay Cancelled/Confirmed or 'completed'.
        # 'completed' is a virtual alias: Dispatched + Cancelled (terminal states).
        COMPLETED_STATUSES = ('Dispatched', 'Cancelled')
        if status_filter:
            if status_filter == 'completed':
                results = [r for r in results if r['status'] in COMPLETED_STATUSES]
            elif status_filter in ('Cancelled', 'Confirmed'):
                # These are payment-derived — filter after status is resolved per-order
                results = [r for r in results if r['status'] == status_filter]

        return Response({
            'message': f'Found {len(results)} order(s)',
            'count': len(results),
            'results': results
        }, status=status.HTTP_200_OK)


class SuperAdminUpdateOrderStatusView(APIView):
    """
    API endpoint for superadmin to update order status.
    POST /api/superadmin/orders/update-status/
    
    Payload:
    {
        "order_id": "TEST-COD-34BE5317",
        "status": "confirmed" | "dispatched"
    }
    
    Status Flow: Pending → Confirmed → Dispatched
    - confirmed:  sets ord_conversion_flag = True
    - dispatched: sets ord_conversion_flag = True (auto), creates/updates invoice if needed
    
    For COD orders, also handles payment collection on dispatch.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)

        order_id = request.data.get('order_id')
        new_status = request.data.get('status', '').lower().strip()

        if not order_id:
            return Response({
                'success': False,
                'error': 'order_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = ['confirmed', 'dispatched']
        if new_status not in valid_statuses:
            return Response({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = SalesOrder.objects.get(order_id=order_id)
        except SalesOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check current status to prevent invalid transitions
        from payment.models import Payment
        payment = order.payments.first()
        
        # Determine current order status (match logic in SuperAdminOrdersView)
        if payment and payment.payment_method == 'RAZORPAY':
            if payment.status == 'SUCCESS':
                current_status = 'confirmed'
            else:
                current_status = 'cancelled'
        elif order.dc_conversion_flag:
            current_status = 'dispatched'
        elif order.ord_conversion_flag:
            current_status = 'confirmed'
        elif payment and payment.status in ['FAILED', 'CANCELLED']:
            current_status = 'cancelled'
        else:
            current_status = 'pending'

        if current_status == 'cancelled':
            return Response({
                'success': False,
                'error': 'Cannot update status for a cancelled or failed order'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate status transition
        status_order = {'pending': 0, 'confirmed': 1, 'dispatched': 2}
        if status_order.get(new_status, 0) <= status_order.get(current_status, 0):
            return Response({
                'success': False,
                'error': f'Cannot change status from "{current_status}" to "{new_status}". Order is already at or past this stage.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Prevent manual confirmation of non-COD orders
        if new_status == 'confirmed' and payment and payment.payment_method != 'COD':
            return Response({
                'success': False,
                'error': 'Only COD orders require manual confirmation. Online payments are confirmed automatically.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Apply status update
        action_msg = ''
        log_details = ''

        if new_status == 'confirmed':
            order.ord_conversion_flag = True
            order.save()
            action_msg = 'Order Confirmed'
            log_details = f'Order "{order_id}" marked as Confirmed'

        elif new_status == 'dispatched':
            order.ord_conversion_flag = True  # Ensure confirmed
            order.dc_conversion_flag = True   # Mark as dispatched
            order.save()
            action_msg = 'Order Dispatched'
            log_details = f'Order "{order_id}" marked as Dispatched'

            # For COD orders, auto-mark payment as collected
            if payment and payment.payment_method == 'COD' and not payment.cod_collected:
                payment.cod_collected = True
                payment.cod_collected_at = timezone.now()
                payment.cod_collected_by = request.user.username
                payment.status = 'SUCCESS'
                payment.save()
                log_details += ' and COD payment collected'

        # Send push notification to the retailer
        if order.user_id and order.user_id.isdigit():
            try:
                retailer_user = get_user_model().objects.get(id=int(order.user_id))
                from .services import send_push_notification
                status_labels = {
                    'confirmed': 'Confirmed ✅',
                    'dispatched': 'Dispatched 🚚',
                }
                send_push_notification(
                    user=retailer_user,
                    title=f"Order {status_labels.get(new_status, new_status)}",
                    body=f"Your order {order_id} has been {new_status}.",
                    data={
                        "type": "order_status_update",
                        "order_id": order_id,
                        "status": new_status
                    }
                )
            except Exception as e:
                logger.warning(f"[ORDER_STATUS] Push notification failed: {e}")

        # Audit log
        try:
            from maindash.views import log_audit
            log_audit(
                action=action_msg,
                performed_by_user=request.user,
                target_entity=order_id,
                details=log_details,
                category='Order',
            )
        except Exception as e:
            logger.warning(f"[ORDER_STATUS] Audit log failed: {e}")

        # Determine updated status label for response
        if order.ord_conversion_flag:
            updated_status = 'Confirmed'
        else:
            updated_status = 'Pending'

        return Response({
            'success': True,
            'message': log_details + ' successfully',
            'order_id': order_id,
            'new_status': updated_status,
        }, status=status.HTTP_200_OK)


# ==================== CREDIT NOTE VIEWS ====================

class RetailerCreditNoteCreateView(APIView):
    """
    Retailer raises a credit note request
    POST /api/credit-notes/create/
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        if user.role != 'RETAILER':
            return Response({
                'success': False,
                'message': 'Only retailers can create credit notes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CreditNoteCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate amount: use sale_rate if provided, else auto-calculate from invoice
        amount = 0.00
        sale_rate = serializer.validated_data.get('sale_rate', 0)
        qty_to_return = serializer.validated_data.get('quantity_to_return', 0)
        invoice_ref = serializer.validated_data.get('reference_invoice')
        
        # Priority 1: If sale_rate is provided by frontend, use it
        if sale_rate and qty_to_return:
            amount = float(sale_rate) * qty_to_return
        # Priority 2: Try to auto-calculate from invoice if available
        elif invoice_ref:
            try:
                invoice = Invoice.objects.filter(
                    sales_order__user_id=str(user.id)
                ).filter(
                    details__product_name__icontains=serializer.validated_data.get('product_name', '')
                ).first()
                
                if invoice:
                    detail = invoice.details.filter(
                        product_name__icontains=serializer.validated_data.get('product_name', '')
                    ).first()
                    if detail:
                        amount = float(detail.sale_rate) * qty_to_return
            except Exception as e:
                logger.warning(f"[CREDIT_NOTE] Could not auto-calc amount: {str(e)}")
        
        credit_note = serializer.save(
            retailer=user,
            amount=amount
        )
        
        logger.info(
            f"[CREDIT_NOTE_CREATED] ID: {credit_note.credit_note_id} | "
            f"Retailer: {user.username} | Product: {credit_note.product_name} | "
            f"Reason: {credit_note.reason}"
        )
        
        # Send push notification to retailer
        try:
            from .services import send_push_notification
            send_push_notification(
                user=user,
                title="Credit Note Submitted ✅",
                body=f"Your credit note {credit_note.credit_note_id} has been submitted and is pending review.",
                data={"type": "credit_note", "credit_note_id": credit_note.credit_note_id}
            )
        except Exception as e:
            logger.warning(f"[CREDIT_NOTE] Push notification failed: {str(e)}")
        
        return Response({
            'success': True,
            'message': f'Credit note {credit_note.credit_note_id} submitted successfully',
            'data': CreditNoteListSerializer(credit_note).data
        }, status=status.HTTP_201_CREATED)


class RetailerCreditNoteListView(APIView):
    """
    Retailer views their own credit note history
    GET /api/credit-notes/
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role != 'RETAILER':
            return Response({
                'success': False,
                'message': 'Only retailers can view credit notes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Optional status filter
        status_filter = request.query_params.get('status')
        
        credit_notes = CreditNote.objects.filter(retailer=user)
        
        if status_filter:
            credit_notes = credit_notes.filter(status=status_filter.upper())
        
        serializer = CreditNoteListSerializer(
            credit_notes, 
            many=True,
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'count': credit_notes.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class AdminCreditNoteListView(APIView):
    """
    SuperAdmin views all credit note requests
    GET /api/admin/credit-notes/
    Query params: status, search, date_from, date_to
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'success': False,
                'message': 'Only SuperAdmin can access this'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from django.db.models import Q
        
        credit_notes = CreditNote.objects.select_related(
            'retailer', 'retailer__kyc'
        ).all()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            credit_notes = credit_notes.filter(status=status_filter.upper())
        
        # Search by retailer name, shop name, credit note id
        search = request.query_params.get('search', '').strip()
        if search:
            credit_notes = credit_notes.filter(
                Q(credit_note_id__icontains=search) |
                Q(retailer__first_name__icontains=search) |
                Q(retailer__kyc__shop_name__icontains=search) |
                Q(reference_invoice__icontains=search) |
                Q(product_name__icontains=search)
            )
        
        # Date range filter
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            credit_notes = credit_notes.filter(created_at__date__gte=date_from)
        if date_to:
            credit_notes = credit_notes.filter(created_at__date__lte=date_to)
        
        serializer = CreditNoteListSerializer(
            credit_notes,
            many=True,
            context={'request': request}
        )
        
        # Summary counts
        all_notes = CreditNote.objects.all()
        
        return Response({
            'success': True,
            'count': credit_notes.count(),
            'summary': {
                'total': all_notes.count(),
                'pending': all_notes.filter(status='PENDING').count(),
                'approved': all_notes.filter(status='APPROVED').count(),
                'rejected': all_notes.filter(status='REJECTED').count(),
                'delivered': all_notes.filter(status='DELIVERED').count(),
            },
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class AdminCreditNoteDetailView(APIView):
    """
    SuperAdmin views credit note detail (modal)
    GET /api/admin/credit-notes/<credit_note_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, credit_note_id):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'success': False,
                'message': 'Only SuperAdmin can access this'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            credit_note = CreditNote.objects.get(credit_note_id=credit_note_id)
        except CreditNote.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Credit note not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreditNoteDetailSerializer(
            credit_note,
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class AdminCreditNoteApproveView(APIView):
    """
    SuperAdmin approves a credit note
    POST /api/admin/credit-notes/<credit_note_id>/approve/

    Body:
    {
        "admin_remarks": "Approved after verification",  (optional)
        "amount": 2500.00  (optional - override amount)
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, credit_note_id):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'success': False,
                'message': 'Only SuperAdmin can approve credit notes'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            credit_note = CreditNote.objects.get(credit_note_id=credit_note_id)
        except CreditNote.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Credit note not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if credit_note.status != 'PENDING':
            return Response({
                'success': False,
                'message': f'Cannot approve. Credit note is already {credit_note.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update
        admin_remarks = request.data.get('admin_remarks', '')
        amount = request.data.get('amount')

        credit_note.status = 'APPROVED'
        credit_note.admin_remarks = admin_remarks
        credit_note.reviewed_by = request.user
        credit_note.reviewed_at = timezone.now()
        if amount:
            credit_note.amount = amount
        credit_note.save()

        logger.info(
            f"[CREDIT_NOTE_APPROVED] ID: {credit_note_id} | "
            f"Admin: {request.user.username} | "
            f"Amount: {credit_note.amount}"
        )

        # Credit wallet after approval
        from .wallet_service import credit_wallet

        wallet_result = credit_wallet(
            retailer=credit_note.retailer,
            amount=credit_note.amount,
            source='CREDIT_NOTE',
            credit_note=credit_note,
            description=f'Credit note {credit_note_id} approved - {credit_note.get_reason_display()}'
        )

        if wallet_result['success']:
            logger.info(
                f"[CREDIT_NOTE_WALLET] ✅ Wallet credited | "
                f"Retailer: {credit_note.retailer.username} | "
                f"Amount: ₹{credit_note.amount} | "
                f"New Balance: ₹{wallet_result['new_balance']}"
            )
        else:
            logger.error(
                f"[CREDIT_NOTE_WALLET] ❌ Wallet credit failed | "
                f"Error: {wallet_result['error']}"
            )

        # Push notification to retailer
        try:
            from .services import send_push_notification
            send_push_notification(
                user=credit_note.retailer,
                title="Credit Note Approved ✅",
                body=f"₹{credit_note.amount} has been added to your wallet. New balance: ₹{wallet_result.get('new_balance', 0)}",
                data={
                    "type": "credit_note_approved",
                    "credit_note_id": credit_note_id,
                    "amount": str(credit_note.amount),
                    "wallet_balance": str(wallet_result.get('new_balance', 0))
                }
            )
        except Exception as e:
            logger.warning(f"[CREDIT_NOTE] Push failed: {str(e)}")

        # Send approval email to retailer
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            retailer_email = credit_note.retailer.email
            
            if retailer_email:
                shop_name = ""
                try:
                    shop_name = credit_note.retailer.kyc.shop_name
                except:
                    shop_name = credit_note.retailer.first_name
                
                email_subject = f"Credit Note Approved ✅ - {credit_note_id}"
                
                email_body = f"""
Hello {credit_note.retailer.first_name},

Good news! Your credit note request has been approved.

Credit Note Details:
─────────────────────────────────────────
Credit Note ID:     {credit_note_id}
Shop Name:          {shop_name}
Product Name:       {credit_note.product_name}
Quantity Returned:  {credit_note.quantity_to_return}
Approved Amount:    ₹{credit_note.amount}
Status:             APPROVED ✅
Approval Date:      {timezone.now().strftime('%d-%m-%Y %H:%M:%S')}

What Happens Next?
─────────────────────────────────────────
✅ ₹{credit_note.amount} has been added to your wallet
✅ New Wallet Balance: ₹{wallet_result.get('new_balance', 0)}
✅ This amount will be deducted from your next order

Your credit will be automatically applied to your next purchase.
No additional action is required.

Admin Remarks:
─────────────────────────────────────────
{admin_remarks if admin_remarks else 'Approved by admin'}

If you have any questions, please don't hesitate to contact us.

Best regards,
Dream Pharma Support Team
"""
                
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[retailer_email],
                    fail_silently=False,
                )
                
                logger.info(
                    f"[CREDIT_NOTE_EMAIL] Approval email sent to {retailer_email} | "
                    f"Credit Note: {credit_note_id} | "
                    f"Amount: ₹{credit_note.amount}"
                )
        except Exception as e:
            logger.warning(f"[CREDIT_NOTE_EMAIL] Failed to send approval email: {str(e)}")

        # Audit log
        try:
            from maindash.views import log_audit
            log_audit(
                action='Credit Note Approved',
                performed_by_user=request.user,
                target_entity=credit_note_id,
                details=f'Approved for {credit_note.retailer.username} | Amount: ₹{credit_note.amount}',
                category='Credit Note',
            )
        except Exception:
            pass

        return Response({
            'success': True,
            'message': f'Credit note {credit_note_id} approved successfully',
            'data': CreditNoteDetailSerializer(
                credit_note,
                context={'request': request}
            ).data
        }, status=status.HTTP_200_OK)


class AdminCreditNoteRejectView(APIView):
    """
    SuperAdmin rejects a credit note
    POST /api/admin/credit-notes/<credit_note_id>/reject/

    Body:
    {
        "admin_remarks": "Reason for rejection"  (required)
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, credit_note_id):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'success': False,
                'message': 'Only SuperAdmin can reject credit notes'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            credit_note = CreditNote.objects.get(credit_note_id=credit_note_id)
        except CreditNote.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Credit note not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if credit_note.status != 'PENDING':
            return Response({
                'success': False,
                'message': f'Cannot reject. Credit note is already {credit_note.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Reject reason is required
        admin_remarks = request.data.get('admin_remarks', '').strip()
        if not admin_remarks:
            return Response({
                'success': False,
                'message': 'admin_remarks (rejection reason) is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update
        credit_note.status = 'REJECTED'
        credit_note.admin_remarks = admin_remarks
        credit_note.reviewed_by = request.user
        credit_note.reviewed_at = timezone.now()
        credit_note.save()

        logger.info(
            f"[CREDIT_NOTE_REJECTED] ID: {credit_note_id} | "
            f"Admin: {request.user.username} | "
            f"Reason: {admin_remarks}"
        )

        # Push notification to retailer
        try:
            from .services import send_push_notification
            send_push_notification(
                user=credit_note.retailer,
                title="Credit Note Rejected ❌",
                body=f"Your credit note {credit_note_id} was rejected. Reason: {admin_remarks}",
                data={
                    "type": "credit_note_rejected",
                    "credit_note_id": credit_note_id,
                    "reason": admin_remarks
                }
            )
        except Exception as e:
            logger.warning(f"[CREDIT_NOTE] Push notification failed: {str(e)}")

        # Send rejection email to retailer
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            retailer_email = credit_note.retailer.email
            
            if retailer_email:
                shop_name = ""
                try:
                    shop_name = credit_note.retailer.kyc.shop_name
                except:
                    shop_name = credit_note.retailer.first_name
                
                email_subject = f"Credit Note Rejected - {credit_note_id}"
                
                email_body = f"""
Hello {credit_note.retailer.first_name},

We regret to inform you that your credit note request has been rejected.

Credit Note Details:
─────────────────────────────────────────
Credit Note ID:     {credit_note_id}
Shop Name:          {shop_name}
Product Name:       {credit_note.product_name}
Quantity Returned:  {credit_note.quantity_to_return}
Requested Amount:   ₹{credit_note.amount}
Status:             REJECTED
Rejection Date:     {timezone.now().strftime('%d-%m-%Y %H:%M:%S')}

Reason for Rejection:
─────────────────────────────────────────
{admin_remarks}

What's Next?
─────────────────────────────────────────
If you believe this decision is incorrect or would like to appeal, 
please contact our support team or reply to this email.

If you have any questions, please don't hesitate to contact us.

Best regards,
Dream Pharma Support Team
"""
                
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[retailer_email],
                    fail_silently=False,
                )
                
                logger.info(
                    f"[CREDIT_NOTE_EMAIL] Rejection email sent to {retailer_email} | "
                    f"Credit Note: {credit_note_id}"
                )
        except Exception as e:
            logger.warning(f"[CREDIT_NOTE_EMAIL] Failed to send rejection email: {str(e)}")

        # Audit log
        try:
            from maindash.views import log_audit
            log_audit(
                action='Credit Note Rejected',
                performed_by_user=request.user,
                target_entity=credit_note_id,
                details=f'Rejected for {credit_note.retailer.username} | Reason: {admin_remarks}',
                category='Credit Note',
            )
        except Exception:
            pass

        return Response({
            'success': True,
            'message': f'Credit note {credit_note_id} rejected',
            'data': CreditNoteDetailSerializer(
                credit_note,
                context={'request': request}
            ).data
        }, status=status.HTTP_200_OK)


class RetailerWalletView(APIView):
    """
    GET /api/wallet/
    Returns wallet balance and transaction history
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'RETAILER':
            return Response({
                'success': False,
                'message': 'Only retailers can access wallet'
            }, status=status.HTTP_403_FORBIDDEN)

        from .models import RetailerWallet, WalletTransaction

        wallet, _ = RetailerWallet.objects.get_or_create(retailer=user)
        
        # Get transaction history
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:20]

        transactions_data = []
        for txn in transactions:
            transactions_data.append({
                'id': txn.id,
                'type': txn.transaction_type,
                'source': txn.source,
                'amount': str(txn.amount),
                'description': txn.description,
                'closing_balance': str(txn.closing_balance),
                'credit_note_id': txn.credit_note.credit_note_id if txn.credit_note else None,
                'created_at': txn.created_at.isoformat()
            })

        return Response({
            'success': True,
            'data': {
                'balance': str(wallet.balance),
                'transactions': transactions_data
            }
        }, status=status.HTTP_200_OK)


class ApplyWalletToOrderView(APIView):
    """
    POST /api/wallet/apply/
    Checkout preview - Show breakdown of wallet application (NO ACTUAL DEDUCTION)
    
    Actual wallet deduction happens only when order is placed with use_wallet=true
    in CreateSalesOrderView
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'RETAILER':
            return Response({
                'success': False,
                'message': 'Only retailers can access wallet'
            }, status=status.HTTP_403_FORBIDDEN)

        order_total = request.data.get('order_total', 0)
        use_wallet = request.data.get('use_wallet', False)

        if not order_total or order_total <= 0:
            return Response({
                'success': False,
                'message': 'order_total is required and must be > 0'
            }, status=status.HTTP_400_BAD_REQUEST)

        from .models import RetailerWallet
        wallet, _ = RetailerWallet.objects.get_or_create(retailer=user)

        order_total = float(order_total)
        wallet_balance = float(wallet.balance)

        if not use_wallet or wallet_balance <= 0:
            return Response({
                'success': True,
                'data': {
                    'order_total': order_total,
                    'wallet_balance': wallet_balance,
                    'wallet_applied': 0,
                    'amount_to_pay': order_total,
                    'wallet_used': False,
                    'note': 'Preview only - wallet will not be applied'
                }
            }, status=status.HTTP_200_OK)

        # Calculate preview (no actual deduction)
        wallet_applied = min(wallet_balance, order_total)
        amount_to_pay = max(0, order_total - wallet_applied)

        logger.info(
            f"[WALLET_PREVIEW] User: {user.username} | "
            f"Order Total: ₹{order_total} | "
            f"Wallet Applied (preview): ₹{wallet_applied} | "
            f"Amount to Pay: ₹{amount_to_pay}"
        )

        return Response({
            'success': True,
            'data': {
                'order_total': order_total,
                'wallet_balance': wallet_balance,
                'wallet_applied': wallet_applied,
                'amount_to_pay': amount_to_pay,
                'wallet_used': True,
                'note': 'Preview only. Wallet will be deducted when order is placed with use_wallet=true.'
            }
        }, status=status.HTTP_200_OK)


class GetProductsByOrderView(APIView):
    """
    GET /api/credit-notes/order-products/?order_id=RET001
    When retailer types Order ID in credit note form,
    this returns products from that order for the dropdown
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'RETAILER':
            return Response({
                'success': False,
                'message': 'Only retailers can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        order_id = request.query_params.get('order_id', '').strip()

        if not order_id:
            return Response({
                'success': False,
                'message': 'order_id query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Order must belong to this retailer
        try:
            sales_order = SalesOrder.objects.get(
                order_id=order_id,
                user_id=str(user.id)
            )
        except SalesOrder.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Order {order_id} not found for this retailer'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get reference invoice
        reference_invoice = ''
        try:
            invoice = Invoice.objects.filter(sales_order=sales_order).first()
            if invoice:
                reference_invoice = invoice.doc_no
        except Exception:
            pass

        # Build product dropdown list
        order_items = SalesOrderItem.objects.filter(sales_order=sales_order)
        
        if not order_items.exists():
            return Response({
                'success': False,
                'message': 'No products found in this order'
            }, status=status.HTTP_404_NOT_FOUND)

        products = []
        for item in order_items:
            image_url = None
            try:
                product_info = ProductInfo.objects.get(item__item_code=item.item_code)
                first_image = product_info.images.first()
                if first_image:
                    image_url = request.build_absolute_uri(first_image.image.url)
            except ProductInfo.DoesNotExist:
                pass

            products.append({
                'item_code': item.item_code,
                'item_name': item.item_name or item.item_code,
                'quantity': item.total_loose_qty,        # ← auto-fill quantity field
                'sale_rate': str(item.sale_rate),
                'batch_no': item.batch_no or '',
                'expiry_date': str(item.expiry_date) if item.expiry_date else '',
                'image': image_url,
                'max_refund_amount': str(
                    round(float(item.sale_rate) * item.total_loose_qty, 2)
                ),
            })

        return Response({
            'success': True,
            'data': {
                'order_id': order_id,
                'order_date': str(sales_order.ord_date),
                'reference_invoice': reference_invoice,  # ← auto-fill invoice field
                'order_total': str(sales_order.order_total),
                'products': products                     # ← populate dropdown
            }
        }, status=status.HTTP_200_OK)
    

# ================================================================================
# PRODUCTION CHECKOUT VIEW - SELECT_FOR_UPDATE METHOD (Flipkart/Amazon Approach)
# ================================================================================


# ================================================================================
# STARTUP LOCATION APIs
# Completely standalone — do NOT touch any existing view, serializer, or workflow.
# These replicate the Swiggy/Zomato "detect location at app startup" pattern.
#
#  POST /api/location/detect/   — Public. Accepts lat/lng → returns address + nearest store.
#  GET  /api/location/me/       — Auth.   Returns last saved location for logged-in user.
#  POST /api/location/save/     — Auth.   Saves new lat/lng and re-runs nearest-store logic.
# ================================================================================

from .serializers import StartupLocationInputSerializer, StartupLocationResponseSerializer
from .store_manager import StoreLocationManager
from .geocoding import reverse_geocode as _reverse_geocode, GeocodingException

def _parse_request_data(request):
    """Robust parser helper to parse JSON data even if Content-Type is text/plain"""
    content_type = request.META.get('CONTENT_TYPE', '')
    request_data = request.data
    if 'text/plain' in content_type or not request_data:
        try:
            body_bytes = request.body
            if body_bytes:
                request_data = json.loads(body_bytes.decode('utf-8'))
        except Exception:
            pass
    return request_data or {}

def _build_location_payload(lat, lon, accuracy=None):
    try:
        addr = _reverse_geocode(lat, lon)
    except GeocodingException:
        addr = {
            'full_address': '', 'locality': '', 'city': '',
            'state': '', 'pincode': '', 'country': '', 'accuracy': 'UNKNOWN',
        }

    # Nearest store (unchanged — still used for primary store fields)
    store_data = StoreLocationManager.find_nearest_store(lat, lon)

    store_id = store_name = store_address = store_city = None
    store_pincode = store_phone = distance_km = None
    erp_c2_code = erp_store_id = erp_prod_code = None

    if store_data:
        store_obj     = store_data['store']
        store_id      = store_data['store_id']
        store_name    = store_data['store_name']
        store_address = store_data['address']
        store_city    = store_obj.city
        store_pincode = store_obj.pincode
        store_phone   = store_data['phone']
        distance_km   = store_data['distance']
        erp_c2_code   = store_obj.c2_code
        erp_store_id  = store_obj.store_id
        erp_prod_code = store_obj.prod_code

    return {
        # address
        'full_address': addr.get('full_address', ''),
        'locality':     addr.get('locality', ''),
        'city':         addr.get('city', ''),
        'state':        addr.get('state', ''),
        'pincode':      addr.get('pincode', ''),
        'country':      addr.get('country', ''),
        'latitude':     float(lat),
        'longitude':    float(lon),
        # nearest store (primary)
        'store_id':      store_id,
        'store_name':    store_name,
        'store_address': store_address,
        'store_city':    store_city,
        'store_pincode': store_pincode,
        'store_phone':   store_phone,
        'distance_km':   distance_km,
        'erp_c2_code':   erp_c2_code,
        'erp_store_id':  erp_store_id,
        'erp_prod_code': erp_prod_code,
    }

class StartupDetectLocationView(APIView):
    """
    POST /api/location/detect/           — no user_id (anonymous browsing)
    POST /api/location/detect/<user_id>/ — with user_id (saves to user profile)

    Public endpoint — no auth header required.
    The Flutter/mobile app calls this ONCE at startup after receiving GPS coordinates.

    Request body:
    {
        "latitude":  12.9716,
        "longitude": 77.5946,
        "accuracy":  15.0        ← optional (metres)
    }

    Response (200):
    {
        "success": true,
        "message": "Location detected successfully",
        "data": {
            "full_address": "...",
            "locality":     "Indiranagar",
            "city":         "Bangalore",
            "state":        "Karnataka",
            "pincode":      "560038",
            "country":      "India",
            "latitude":     12.9716,
            "longitude":    77.5946,
            "store_id":      1,
            "store_name":    "DreamsPharma - Bangalore",
            "store_address": "...",
            "store_city":    "Bangalore",
            "store_pincode": "560001",
            "store_phone":   "9876543210",
            "distance_km":   2.4,
            "erp_c2_code":   "03C000",
            "erp_store_id":  "001",
            "erp_prod_code": "02"
        }
    }
    """
    permission_classes = [AllowAny]

    def post(self, request, user_id=None):
        request_data = _parse_request_data(request)
        serializer = StartupLocationInputSerializer(data=request_data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid location data',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        lat      = serializer.validated_data['latitude']
        lon      = serializer.validated_data['longitude']
        accuracy = serializer.validated_data.get('accuracy')

        payload = _build_location_payload(lat, lon, accuracy)

        # ── Persist location if user_id is provided in the URL ──
        if user_id is not None:
            user = get_object_or_404(User, id=user_id)
            try:
                user.last_latitude        = lat
                user.last_longitude       = lon
                user.last_location_update = timezone.now()
                if payload['pincode']:
                    user.location_pincode = payload['pincode']
                if payload['store_id']:
                    from .models import Store as _Store
                    try:
                        user.preferred_store = _Store.objects.get(pk=payload['store_id'])
                    except _Store.DoesNotExist:
                        pass
                user.save(update_fields=[
                    'last_latitude', 'last_longitude', 'last_location_update',
                    'location_pincode', 'preferred_store',
                ])
                logger.info(
                    f"[STARTUP_LOCATION] User {user_id} location saved: "
                    f"({lat}, {lon}) → store {payload['store_id']}"
                )
            except Exception as persist_err:
                logger.warning(f"[STARTUP_LOCATION] Could not persist location for user {user_id}: {persist_err}")

        logger.info(
            f"[STARTUP_LOCATION] Detected: ({lat}, {lon}) "
            f"-> store={payload['store_name']} dist={payload['distance_km']}km"
        )

        return Response({
            'success': True,
            'message': 'Location detected successfully',
            'data': payload,
        }, status=status.HTTP_200_OK)


class GetMyLocationView(APIView):
    """
    GET /api/location/me/

    Returns the last saved location (posted via SaveMyLocationView).
    This retrieves the GPS coordinates and address data that was saved.
    Requires JWT authentication.

    Response (200):
    {
        "success": true,
        "data": {
            "full_address": "...",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "city": "Bangalore",
            "store_name": "DreamsPharma - Bangalore",
            ...
        }
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ── single DB query — fetches user + preferred_store in one JOIN ──
        user = request.user.__class__.objects.select_related('preferred_store').get(
            pk=request.user.pk
        )

        if not user.last_latitude or not user.last_longitude:
            return Response({
                'success': True,
                'message': 'No location saved yet. Please call POST /api/location/save/ to save a location.',
                'data': None,
            }, status=status.HTTP_200_OK)

        lat = user.last_latitude
        lon = user.last_longitude

        if user.preferred_store:
            # ── Fast path: build payload from persisted store + cached geocode ──
            # reverse_geocode is cached — sub-millisecond after first call.
            # preferred_store is already loaded via select_related — zero extra DB hit.
            ps = user.preferred_store
            try:
                addr = _reverse_geocode(lat, lon)
            except GeocodingException:
                addr = {
                    'full_address': '', 'locality': '', 'city': '',
                    'state': '', 'pincode': user.location_pincode or '',
                    'country': '', 'accuracy': 'UNKNOWN',
                }

            payload = {
                'full_address': addr.get('full_address', ''),
                'locality':     addr.get('locality', ''),
                'city':         addr.get('city', ''),
                'state':        addr.get('state', ''),
                'pincode':      addr.get('pincode', '') or user.location_pincode or '',
                'country':      addr.get('country', ''),
                'latitude':     float(lat),
                'longitude':    float(lon),
                'store_id':      ps.id,
                'store_name':    ps.name,
                'store_address': ps.address,
                'store_city':    ps.city,
                'store_pincode': ps.pincode,
                'store_phone':   ps.phone,
                'distance_km':   None,
                'erp_c2_code':   ps.c2_code,
                'erp_store_id':  ps.store_id,
                'erp_prod_code': ps.prod_code,
            }
        else:
            # ── Slow path: full nearest-store lookup (both geocode + store are cached) ──
            payload = _build_location_payload(lat, lon)
            if not payload['pincode'] and user.location_pincode:
                payload['pincode'] = user.location_pincode

        logger.info(f"[GET_MY_LOCATION] User {user.id} fetched last saved location.")

        return Response({
            'success': True,
            'data': payload,
        }, status=status.HTTP_200_OK)


class SaveMyLocationView(APIView):
    """
    POST /api/location/save/

    Called when the user explicitly taps "Change Location".
    Accepts new GPS coordinates, re-runs nearest-store logic,
    and updates the user's saved location + preferred_store.
    Requires JWT authentication.

    Request body:
    {
        "latitude":  13.0827,
        "longitude": 80.2707,
        "accuracy":  10.0    ← optional
    }

    Response (200):
    {
        "success":  true,
        "message":  "Location updated successfully",
        "data": { ... same shape as /detect/ ... }
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        request_data = _parse_request_data(request)
        serializer = StartupLocationInputSerializer(data=request_data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid location data',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        lat      = serializer.validated_data['latitude']
        lon      = serializer.validated_data['longitude']
        accuracy = serializer.validated_data.get('accuracy')

        payload = _build_location_payload(lat, lon, accuracy)

        # Persist to user profile
        user.last_latitude        = lat
        user.last_longitude       = lon
        user.last_location_update = timezone.now()
        if payload['pincode']:
            user.location_pincode = payload['pincode']
        if payload['store_id']:
            from .models import Store as _Store
            try:
                user.preferred_store = _Store.objects.get(pk=payload['store_id'])
            except _Store.DoesNotExist:
                pass
        user.save(update_fields=[
            'last_latitude', 'last_longitude', 'last_location_update',
            'location_pincode', 'preferred_store',
        ])

        logger.info(
            f"[SAVE_MY_LOCATION] User {user.id} updated location: "
            f"({lat}, {lon}) -> store {payload['store_id']}"
        )

        return Response({
            'success': True,
            'message': 'Location updated successfully',
            'data': payload,
        }, status=status.HTTP_200_OK)


