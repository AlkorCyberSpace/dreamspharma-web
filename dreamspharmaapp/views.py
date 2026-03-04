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
import random
import re
import string
import base64

from .models import CustomUser, KYC, OTP, APIToken, ItemMaster, Stock, GLCustomer, SalesOrder, SalesOrderItem, Invoice, InvoiceDetail, Cart, CartItem, Wishlist, WishlistItem
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
    WishlistSerializer, WishlistItemSerializer, AddToWishlistSerializer, MoveToCartSerializer
)


User = get_user_model()


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
        # Allow public update by user_id
        if user_id is None:
            return Response({'error': 'user_id is required in the URL.'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, id=user_id)
        if getattr(user, 'role', None) != 'RETAILER':
            return Response({'error': 'Only retailers can update their profile.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = CustomUserSerializer(user, data=request.data, partial=True)
        kyc_fields = ['shop_name', 'shop_address', 'customer_name', 'customer_id', 'customer_photo', 'store_photo', 'customer_mobile']
        kyc_data = {field: request.data.get(field) for field in kyc_fields if field in request.data}
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
        
        # Update user fields
        if serializer.is_valid():
            serializer.save()
            # Update KYC fields if present
            if kyc and kyc_data:
                for field, value in kyc_data.items():
                    if value is not None:
                        setattr(kyc, field, value)
                kyc.save()
            # Build the same profile response as in GET
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
                'kyc_exists': kyc_exists,
                'kyc_status': kyc.get_status_display() if kyc else 'Not Submitted'
            }
            return Response(profile, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    POST /api/retailer-auth/login/ - Step 1: Login with email + password
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 1: Login with email and password.
        
        First Login: System sends 4-digit OTP to email
        Subsequent Login: System returns JWT tokens directly
        
        Request Body:
        {
            "email": "retailer@example.com",
            "password": "password123"
        }
        
        Response (First Login):
        {
            "message": "Email and password verified. 4-digit OTP sent to your email.",
            "is_first_login": true,
            "otp_expires_in": 60,
            "email": "retailer@example.com"
        }
        
        Response (Subsequent Login):
        {
            "message": "Login successful!",
            "is_first_login": false,
            "access": "JWT_TOKEN",
            "refresh": "REFRESH_TOKEN"
        }
        """
        serializer = RetailerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        is_first_login = serializer.validated_data.get('is_first_login', False)
        
        # FIRST LOGIN: Generate and send OTP
        if is_first_login:
            # Generate and send OTP via email
            otp_obj = OTP.objects.create(user=user)
            otp_code = otp_obj.generate_otp()
            
            try:
                send_mail(
                    subject="Your Dream's Pharmacy First Login OTP",
                    message=f'Your 4-digit OTP for first login verification is: {otp_code}\n\nThis OTP is valid for 1 minute.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error sending email: {e}")
            
            return Response({
                'message': 'Email and password verified. 4-digit OTP sent to your email.',
                'email': user.email
            }, status=status.HTTP_200_OK)
        
        # SUBSEQUENT LOGINS: Direct login without OTP
        else:
            # Update user status to LOGIN_ENABLED
            user.status = 'LOGIN_ENABLED'
            user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful!',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'is_first_login': False
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_200_OK)


class RetailerVerifyOTPView(APIView):
    """
    API endpoint for retailer OTP verification during first login.
    POST /api/retailer-auth/verify-otp/ - Step 2: Verify OTP (first login only)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 2: Verify OTP for first login only.
        
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
            
            # Mark first login as completed
            user.first_login_otp_verified = True
            user.status = 'LOGIN_ENABLED'
            user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'OTP verified successfully. You are now logged in.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': CustomUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        except OTP.DoesNotExist:
            return Response({
                'error': 'Invalid OTP. Please try again.'
            }, status=status.HTTP_400_BAD_REQUEST)


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
                    
                    return Response({
                        'message': 'OTP verified successfully. You are now logged in.',
                        'otp_expires_in': otp_obj.get_expiry_time_remaining(),
                        'user': CustomUserSerializer(user).data,
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
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
    GET: Fetch item details based on parameters
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        serializer = FetchStockRequestSerializer(data=request.query_params)
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
                
                # Create line items
                material_info = serializer.validated_data['materialInfo']
                for item in material_info:
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        item_seq=item['item_seq'],
                        item_code=item['item_code'],
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
        return Response({
            'success': True,
            'message': 'Cart retrieved successfully',
            'data': serializer.data
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
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
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
        
        try:
            item = ItemMaster.objects.get(item_code=item_code)
        except ItemMaster.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Item with code {item_code} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            item=item,
            defaults={'quantity': quantity, 'batch_no': batch_no}
        )
        
        if not created:
            # Update quantity
            cart_item.quantity += quantity
            cart_item.save()
        
        cart_serializer = CartSerializer(cart)
        return Response({
            'success': True,
            'message': f'{item.item_name} added to cart' if created else f'{item.item_name} quantity updated',
            'data': cart_serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


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

class WishlistView(APIView):
    """
    Get or clear user's wishlist
    GET: Retrieve wishlist with all items
    DELETE: Clear entire wishlist
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        serializer = WishlistSerializer(wishlist)
        return Response({
            'success': True,
            'message': 'Wishlist retrieved successfully',
            'data': serializer.data
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
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AddToWishlistSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item_code = serializer.validated_data['itemCode']
        
        try:
            item = ItemMaster.objects.get(item_code=item_code)
        except ItemMaster.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Item with code {item_code} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create wishlist
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        
        # Check if item already in wishlist
        wishlist_item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            item=item
        )
        
        if not created:
            return Response({
                'success': False,
                'message': f'{item.item_name} is already in your wishlist'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        wishlist_serializer = WishlistSerializer(wishlist)
        return Response({
            'success': True,
            'message': f'{item.item_name} added to wishlist',
            'data': wishlist_serializer.data
        }, status=status.HTTP_201_CREATED)


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
        quantity = serializer.validated_data.get('quantity', 1)
        
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
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
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
