from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import (
    KYC, OTP, APIToken, ItemMaster, Stock, GLCustomer, 
    SalesOrder, SalesOrderItem, Invoice, InvoiceDetail,
    Cart, CartItem, Wishlist, WishlistItem, ProductInfo, ProductImage, Address,
    Category, Offer, RetailerNotification, CreditNote, RetailerWallet, WalletTransaction
)
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ==================== USER SERIALIZERS ====================

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'email', 'role', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'status']


class SuperAdminLoginSerializer(serializers.Serializer):
    """Serializer for SuperAdmin login"""
    username = serializers.CharField(required=True, help_text="Username or email")
    password = serializers.CharField(write_only=True, required=True, help_text="Password")
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        # Try to find user by username or email with SUPERADMIN role
        user = None
        try:
            user = User.objects.get(username=username, role='SUPERADMIN')
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username, role='SUPERADMIN')
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid username or email. No Super Admin account found")
        
        # Authenticate the user with the correct username
        authenticated_user = authenticate(username=user.username, password=password)
        if authenticated_user is None:
            raise serializers.ValidationError("Incorrect password")
        
        # Check if user is actually a superadmin
        if authenticated_user.role != 'SUPERADMIN':
            raise serializers.ValidationError("Only superadmin accounts can login here")
        
        data['user'] = authenticated_user
        return data


class RetailerLoginSerializer(serializers.Serializer):
    """Serializer for Retailer login with email and password"""
    email = serializers.EmailField(required=True, help_text="Registered email", error_messages={
        'required': 'Email is required',
        'invalid': 'Enter a valid email address',
        'blank': 'Email cannot be blank'
    })
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        min_length=8,
        help_text="Password",
        error_messages={
            'required': 'Password is required',
            'blank': 'Password cannot be blank',
            'max_length': 'Password too long',
            'min_length': 'Password must be at least 8 characters'
        }
    )
    
    def validate_email(self, value):
        """Validate email exists and belongs to a retailer"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("Email cannot be empty")
        
        # Check if email format is valid
        if '@' not in value or '.' not in value:
            raise serializers.ValidationError("Enter a valid email address")
        
        return value.lower()
    
    def validate_password(self, value):
        """Validate password is not empty and has minimum length"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("Password cannot be empty")
        
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        
        return value
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            raise serializers.ValidationError("Email and password are required")
        
        # Try to find user by email with RETAILER role
        try:
            user = User.objects.get(email=email, role='RETAILER')
        except User.DoesNotExist:
            raise serializers.ValidationError("Email is not registered or not a retailer account")
        
        # Check if user is approved by admin or login enabled
        if user.status not in ['APPROVED', 'LOGIN_ENABLED']:
            raise serializers.ValidationError({
                'error': f"Your account status is {user.get_status_display()}. Only APPROVED or LOGIN ENABLED accounts can login.",
                'user_id': user.id
                
            })
        
        # Check if user has submitted KYC
        if not hasattr(user, 'kyc'):
            raise serializers.ValidationError({
                'error': 'KYC not submitted. Please submit your KYC documents first.',
                'user_id': user.id
                
            })
        
        # Check if KYC is approved by admin
        if user.kyc.status != 'APPROVED':
            raise serializers.ValidationError(
                f"Your KYC status is {user.kyc.get_status_display()}. Only retailers with APPROVED KYC can login."
            )
        
        # Authenticate the user with password
        authenticated_user = authenticate(username=user.username, password=password)
        if authenticated_user is None:
            raise serializers.ValidationError("Password is incorrect. Please try again.")
        
        data['user'] = authenticated_user
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField(required=True, min_length=10, max_length=15)

    class Meta:
        model = User
        fields = ['first_name', 'email', 'phone_number', 'password', 'password2']
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match"})

        email = data.get('email')
        phone_number = data.get('phone_number')

        if not email:
            raise serializers.ValidationError({"email": "Email is required"})
        if not phone_number:
            raise serializers.ValidationError({"phone_number": "Phone number is required"})

        # Check email: Allow re-registration only if existing user has PENDING_OTP_VERIFICATION status
        existing_email_user = User.objects.filter(email=email).first()
        if existing_email_user:
            if existing_email_user.status == 'PENDING_OTP_VERIFICATION':
                # Delete the pending registration to allow re-registration
                existing_email_user.delete()
            else:
                raise serializers.ValidationError({"email": "Email already exists"})
        
        # Check phone number: Allow re-registration only if existing user has PENDING_OTP_VERIFICATION status
        existing_phone_user = User.objects.filter(phone_number=phone_number).first()
        if existing_phone_user:
            if existing_phone_user.status == 'PENDING_OTP_VERIFICATION':
                # Delete the pending registration to allow re-registration
                existing_phone_user.delete()
            else:
                raise serializers.ValidationError({"phone_number": "Phone number already exists"})

        # Optionally, add phone number format validation here
        return data
    
    def create(self, validated_data):
        validated_data.pop('password2')
        phone_number = validated_data.pop('phone_number', None)

        base_username = validated_data.get('first_name', 'user').lower()
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            password=validated_data['password'],
            phone_number=phone_number,
            role='RETAILER'
        )
        # Create OTP record for the user
        OTP.objects.create(user=user)
        return user


class KYCSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = KYC
        fields = [
            'id', 'username', 'shop_name', 'shop_address', 'shop_email', 'shop_phone',
            'customer_name', 'customer_id', 'customer_photo', 'customer_address', 
            'gst_number', 'drug_license_number', 'drug_license', 'id_proof', 'store_photo', 
            'status', 'submitted_at', 'approved_at', 'rejection_reason'
        ]
        read_only_fields = ['id', 'submitted_at', 'approved_at', 'status']


class KYCSubmitSerializer(serializers.ModelSerializer):
    drug_license = serializers.FileField(required=True)
    id_proof = serializers.FileField(required=True)
    store_photo = serializers.FileField(required=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_id = serializers.CharField(required=False, allow_blank=True, help_text='Aadhaar or PAN')
    
    class Meta:
        model = KYC
        fields = [
            'shop_name', 'shop_address', 'shop_email', 'shop_phone', 'customer_name', 
            'customer_id', 'customer_address', 'gst_number', 
            'drug_license_number', 'drug_license', 'id_proof', 'store_photo'
        ]
    
    def validate_customer_id(self, value):
        """
        Validate Aadhaar format: exactly 12 digits, no alphabets or special characters
        """
        if value and value.strip():  # Only validate if provided and not empty
            # Check if it contains only digits
            if not value.isdigit():
                raise serializers.ValidationError(
                    "Aadhaar must contain only numeric digits. Alphabets and special characters are not allowed."
                )
            # Check if length is exactly 12
            if len(value) != 12:
                raise serializers.ValidationError(
                    "Aadhaar must be exactly 12 digits long."
                )
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value, role='RETAILER').exists():
            raise serializers.ValidationError("No retailer found with this email.")
        return value


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    otp_code = serializers.CharField(max_length=4)

    def validate(self, data):
        email = data.get('email')
        otp_code = data.get('otp_code')
        
        # If email is provided (forgot password flow), verify user by email
        if email:
            try:
                user = User.objects.get(email=email, role='RETAILER')
            except User.DoesNotExist:
                raise serializers.ValidationError({"email": "No retailer found with this email."})
            try:
                otp_obj = OTP.objects.filter(user=user, otp_code=otp_code, is_verified=False).latest('created_at')
            except OTP.DoesNotExist:
                raise serializers.ValidationError({"otp_code": "Invalid or expired OTP."})
        else:
            # No email provided (registration flow), find OTP by code only
            try:
                otp_obj = OTP.objects.filter(otp_code=otp_code, is_verified=False).latest('created_at')
                user = otp_obj.user
            except OTP.DoesNotExist:
                raise serializers.ValidationError({"otp_code": "Invalid or expired OTP."})
        
        if otp_obj.is_expired():
            raise serializers.ValidationError({"otp_code": "OTP has expired."})
        data['user'] = user
        data['otp_obj'] = otp_obj
        return data


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=4)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        # Reuse OTP validation
        otp_serializer = OTPVerifySerializer(data={
            'email': data['email'],
            'otp_code': data['otp_code']
        })
        otp_serializer.is_valid(raise_exception=True)
        data['user'] = otp_serializer.validated_data['user']
        data['otp_obj'] = otp_serializer.validated_data['otp_obj']
        return data


class ChangePasswordSerializer(serializers.Serializer):
    oldpassword = serializers.CharField(write_only=True, required=True)
    newpassword = serializers.CharField(write_only=True, required=True)
    confirmpassword = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['newpassword'] != data['confirmpassword']:
            raise serializers.ValidationError(
                {"confirmpassword": "New password and confirm password do not match."}
            )
        if data['oldpassword'] == data['newpassword']:
            raise serializers.ValidationError(
                {"newpassword": "New password cannot be the same as old password."}
            )
        return data


# ==================== ERP INTEGRATION SERIALIZERS ====================

class GenerateTokenRequestSerializer(serializers.Serializer):
    """Serializer for API token generation request"""
    c2Code = serializers.CharField(max_length=20)
    storeId = serializers.CharField(max_length=20)
    prodCode = serializers.CharField(max_length=20, required=False, default="02")
    securityKey = serializers.CharField(max_length=255)


class GenerateTokenResponseSerializer(serializers.Serializer):
    """Serializer for API token generation response"""
    code = serializers.CharField()
    type = serializers.CharField()
    apiKey = serializers.CharField()


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""
    
    class Meta:
        model = ProductImage
        fields = ['image', 'image_order']


class ProductInfoForItemMasterSerializer(serializers.ModelSerializer):
    """Serializer for ProductInfo when included with ItemMaster"""
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductInfo
        fields = ['subheading', 'description', 'type_label', 'images']


class ItemMasterSerializer(serializers.ModelSerializer):
    """Serializer for ItemMaster model with product information"""
    c_item_code = serializers.CharField(source='item_code')
    itemName = serializers.CharField(source='item_name')
    itemQtyPerBox = serializers.IntegerField(source='item_qty_per_box')
    batchNo = serializers.CharField(source='batch_no')
    std_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    expiryDate = serializers.DateField(source='expiry_date')
    # New fields for mobile app
    subheading = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    type_label = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemMaster
        fields = ['c_item_code', 'itemName', 'itemQtyPerBox', 'batchNo', 'std_disc', 'max_disc', 'expiryDate', 'mrp', 'subheading', 'description', 'type_label', 'images']
    
    def get_subheading(self, obj):
        """Get subheading from ProductInfo if exists"""
        try:
            return obj.product_info.subheading or ""
        except:
            return ""
    
    def get_description(self, obj):
        """Get description from ProductInfo if exists"""
        try:
            return obj.product_info.description or ""
        except:
            return ""
    
    def get_type_label(self, obj):
        """Get type_label from ProductInfo if exists"""
        try:
            return obj.product_info.type_label or ""
        except:
            return ""
    
    def get_images(self, obj):
        """Get product images from ProductInfo"""
        try:
            request = self.context.get('request')
            images = obj.product_info.images.all().order_by('image_order')[:3]
            image_urls = []
            for img in images:
                if request:
                    image_url = request.build_absolute_uri(img.image.url)
                else:
                    image_url = img.image.url
                image_urls.append({
                    'image': image_url,
                    'image_order': img.image_order
                })
            return image_urls
        except:
            return []


class ProductListSerializer(serializers.Serializer):
    """Serializer for product listing with all required fields"""
    itemCode = serializers.CharField(source='item.item_code', read_only=True)
    itemName = serializers.CharField(source='item.item_name', read_only=True)
    mrp = serializers.DecimalField(source='item.mrp', max_digits=10, decimal_places=2, read_only=True)
    description = serializers.CharField(source='item.description', read_only=True, allow_null=True, default="")
    images = ProductImageSerializer(many=True, read_only=True)
    batchNo = serializers.CharField(source='batch_no', read_only=True, default="")
    c_item_code = serializers.CharField(source='item.item_code', read_only=True, default="")
    expiryDate = serializers.DateField(source='expiry_date', read_only=True, default=None)
    itemQtyPerBox = serializers.IntegerField(source='item_qty_per_box', read_only=True, default=1)
    max_disc = serializers.FloatField(read_only=True, default=0)
    std_disc = serializers.FloatField(read_only=True, default=0)
    stockBalQty = serializers.IntegerField(source='stock_bal_qty', read_only=True, default=0)
    subheading = serializers.CharField(read_only=True, default="")
    type_label = serializers.CharField(read_only=True, default="")
    brand_id = serializers.IntegerField(read_only=True, default=None)
    brand_name = serializers.CharField(read_only=True, default="")
    brand_logo = serializers.CharField(read_only=True, default="")
    cart_status = serializers.BooleanField(read_only=True, default=False)
    wishlist_status = serializers.BooleanField(read_only=True, default=False)
    discountPercentage = serializers.FloatField(source='discount_percentage', read_only=True, default=0)
    discountedPrice = serializers.FloatField(source='discounted_price', read_only=True, default=0)

    class Meta:
        model = ProductInfo
        fields = [
            'itemCode', 'itemName', 'mrp', 'description', 'images', 'batchNo', 'c_item_code', 'expiryDate',
            'itemQtyPerBox', 'max_disc', 'std_disc', 'stockBalQty', 'subheading', 'type_label', 'brand_id',
            'brand_name', 'brand_logo', 'cart_status', 'wishlist_status', 'discountPercentage', 'discountedPrice'
        ]


class FetchStockRequestSerializer(serializers.Serializer):
    """Serializer for ERP item master request - matches ERP API spec"""
    c2Code = serializers.CharField(max_length=20, required=True, help_text="Company/Branch code")
    storeId = serializers.CharField(max_length=20, required=True, help_text="Store identifier")
    apiKey = serializers.CharField(max_length=255, required=True, help_text="API authentication key")
    prodCode = serializers.CharField(max_length=20, required=False, default="02", help_text="Production code (optional)")
    indexId = serializers.IntegerField(required=False, help_text="Item index ID (optional)")
    inputDateTime = serializers.DateTimeField(required=False, help_text="Reference date/time (optional)")


class StockItemSerializer(serializers.ModelSerializer):
    """Serializer for stock items in response"""
    itemCode = serializers.CharField(source='item.item_code')
    itemName = serializers.CharField(source='item.item_name')
    contCode = serializers.CharField(source='cont_code')
    contName = serializers.CharField(source='cont_name')
    qtyBox = serializers.IntegerField(source='qty_box')
    totalBalLsQty = serializers.IntegerField(source='total_bal_ls_qty')
    packQty = serializers.IntegerField(source='pack_qty')
    looseQty = serializers.IntegerField(source='loose_qty')
    lastModifiedDateTime = serializers.DateTimeField(source='last_modified_datetime')
    
    class Meta:
        model = Stock
        fields = ['itemCode', 'itemName', 'contCode', 'contName', 'qtyBox', 'totalBalLsQty', 'packQty', 'looseQty', 'lastModifiedDateTime']


class SalesOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for sales order items with batch & expiry tracking for medicine recall management
    
    ✅ ALL FIELDS ARE OPTIONAL
    - Send only the fields you have
    - Missing fields will use default values
    - Accepts both camelCase (itemSeq) and snake_case (item_seq) field names for Flutter compatibility
    """
    # ── Camel-case fields (primary API format) ──
    itemSeq = serializers.IntegerField(source='item_seq', required=False, default=1)
    itemcode = serializers.CharField(source='item_code', required=False, allow_blank=True, default='')
    itemName = serializers.CharField(source='item_name', required=False, allow_blank=True, allow_null=True, help_text="Product name for display")
    batchNo = serializers.CharField(source='batch_no', required=False, allow_blank=True, allow_null=True, help_text="Medicine batch number for recall tracking")
    expiryDate = serializers.CharField(source='expiry_date', required=False, allow_blank=True, allow_null=True, help_text="Medicine expiry date (YYYY-MM-DD or empty)")
    totalLooseQty = serializers.IntegerField(source='total_loose_qty', required=False, default=0)
    totalLooseSchQty = serializers.IntegerField(source='total_loose_sch_qty', required=False, default=0)
    serviceQty = serializers.IntegerField(source='service_qty', required=False, default=0)
    saleRate = serializers.DecimalField(max_digits=10, decimal_places=3, source='sale_rate', required=False, default=0.00)
    discPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='disc_per', required=False, default=0.00)
    schDiscPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='sch_disc_per', required=False, default=0.00)
    
    class Meta:
        model = SalesOrderItem
        fields = ['itemSeq', 'itemcode', 'itemName', 'batchNo', 'expiryDate', 'totalLooseQty', 'totalLooseSchQty', 'serviceQty', 'saleRate', 'discPer', 'schDiscPer']
    
    def to_internal_value(self, data):
        """Normalize both camelCase and snake_case field names to the camelCase format expected by the serializer"""
        from datetime import datetime
        
        # Map snake_case to camelCase for internal processing
        snake_to_camel = {
            'item_seq': 'itemSeq',
            'item_code': 'itemcode',
            'item_name': 'itemName',
            'batch_no': 'batchNo',
            'expiry_date': 'expiryDate',
            'total_loose_qty': 'totalLooseQty',
            'total_loose_sch_qty': 'totalLooseSchQty',
            'service_qty': 'serviceQty',
            'sale_rate': 'saleRate',
            'disc_per': 'discPer',
            'sch_disc_per': 'schDiscPer',
        }
        
        # Normalize the incoming data
        normalized = {}
        for key, value in data.items():
            # If it's snake_case, convert to camelCase
            if key in snake_to_camel:
                normalized[snake_to_camel[key]] = value
            else:
                # Keep camelCase as-is
                normalized[key] = value
        
        # Handle empty strings for date fields - convert to None
        if 'expiryDate' in normalized:
            if normalized['expiryDate'] == '' or normalized['expiryDate'] is None:
                normalized['expiryDate'] = None
            elif isinstance(normalized['expiryDate'], str) and normalized['expiryDate']:
                # Try to parse date string if it's a valid date format
                try:
                    parsed_date = datetime.strptime(normalized['expiryDate'], '%Y-%m-%d').strftime('%Y-%m-%d')
                    normalized['expiryDate'] = parsed_date
                except (ValueError, TypeError):
                    # If parsing fails, set to None (will be handled as optional)
                    normalized['expiryDate'] = None
        
        # Call parent to validate normalized data
        return super().to_internal_value(normalized)


class CreateSalesOrderRequestSerializer(serializers.Serializer):
    """Serializer for creating sales order
    
    ✅ ALL FIELDS ARE OPTIONAL
    - Send only the fields you have
    - Missing fields will use default values or be skipped
    - No validation errors for empty/null values
    
    🎯 NOTE: apiKey is auto-generated - tokens generated in background
    """
    
    # ==================== ROUTING & AUTH (ALL OPTIONAL) ====================
    c2Code = serializers.CharField(max_length=20, required=False, allow_blank=True, help_text="Company/branch code")
    storeId = serializers.CharField(max_length=20, required=False, allow_blank=True, help_text="Store identifier")
    prodCode = serializers.CharField(max_length=20, required=False, default="02", help_text="Product code")
    apiKey = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="Deprecated: Auto-generated by backend")
    
    # ==================== AUDIT & TIME (ALL OPTIONAL) ====================
    ordDate = serializers.DateField(required=False, help_text="Order date (YYYY-MM-DD)")
    ordTime = serializers.TimeField(required=False, help_text="Order time (HH:mm:ss)")
    userId = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="User who created order")
    actCode = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="Account code")
    actName = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="Account name")
    
    # ==================== FINANCIALS & TRANSACTION TYPE (ALL OPTIONAL) ====================
    counterSale = serializers.IntegerField(required=False, default=0, help_text="Counter sale indicator (0 or 1)")
    orderTotal = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0.00, help_text="Total bill amount")
    orderDiscPer = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0.00, help_text="Order discount percentage")
    
    # ==================== ITEM ARRAY (OPTIONAL) ====================
    materialInfo = SalesOrderItemSerializer(many=True, required=False, help_text="Line items (optional)")
    
    # ==================== OPTIONAL: CUSTOMER DETAILS (RECOMMENDED) ====================
    mobileNo = serializers.CharField(max_length=15, required=False, allow_blank=True, help_text="Customer mobile (recommended)")
    patientName = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="Patient/customer name (recommended)")
    patientEmail = serializers.EmailField(required=False, allow_blank=True, help_text="Patient email (optional)")
    patientAddress = serializers.CharField(required=False, allow_blank=True, help_text="Patient address (optional)")
    ipNo = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="IP number (optional)")
    
    # ==================== CONDITIONAL: DOCTOR DETAILS (For Schedule H drugs) ====================
    drCode = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="Doctor code (mandatory for Schedule H drugs)")
    drName = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="Doctor name (optional)")
    drAddress = serializers.CharField(required=False, allow_blank=True, help_text="Doctor address (optional)")
    drRegNo = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="Doctor registration number (optional)")
    drOfficeCode = serializers.CharField(max_length=50, required=False, default="-", help_text="Doctor office code (optional)")
    
    # ==================== SYSTEM INFO (ALL OPTIONAL) ====================
    sysName = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="System name (for logging)")
    sysIp = serializers.IPAddressField(required=False, help_text="System IP address (for logging)")
    sysUser = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="System user (for logging)")
    
    # ==================== OPTIONAL: SUPPLEMENTARY ====================
    dmanCode = serializers.CharField(max_length=50, required=False, default="-", help_text="Delivery manager code (optional)")
    refNo = serializers.IntegerField(required=False, help_text="Reference number (optional)")
    remark = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text="Remarks (optional)")
    urgentFlag = serializers.IntegerField(required=False, default=0, help_text="Urgent flag (0 or 1)")
    ordConversionFlag = serializers.IntegerField(required=False, default=0, help_text="Order conversion flag")
    dcConversionFlag = serializers.IntegerField(required=False, default=0, help_text="DC conversion flag")
    ordRefNo = serializers.IntegerField(required=False, default=0, help_text="Order reference number")
    
    # ==================== PAYMENT MODE ====================
    paymentMode = serializers.ChoiceField(choices=['COD', 'RAZORPAY'], required=False, default='COD', help_text="Payment mode: 'COD' (Cash on Delivery) or 'RAZORPAY'")
    
    def validate_materialInfo(self, value):
        """Validate materialInfo if provided"""
        if value and len(value) > 0:
            # Validate each item if provided
            for idx, item in enumerate(value):
                # Check item_code if present
                if not item.get('item_code'):
                    # Allow empty items as materialInfo is now optional
                    pass
        return value
    
    def validate_counterSale(self, value):
        """Validate counterSale is 0 or 1"""
        if value not in [0, 1]:
            raise serializers.ValidationError("counterSale must be 0 or 1")
        return value
    
    def validate_orderTotal(self, value):
        """Validate orderTotal - allow 0 for optional fields"""
        if value < 0:
            raise serializers.ValidationError("orderTotal cannot be negative")
        return value


class DocumentDetailSerializer(serializers.Serializer):
    """Serializer for document details in order response"""
    brCode = serializers.CharField(source='br_code')
    tranYear = serializers.CharField(source='tran_year')
    tranPrefix = serializers.CharField(source='tran_prefix')
    tranSrno = serializers.CharField(source='tran_srno')
    documentPk = serializers.CharField(source='document_pk')
    OrderId = serializers.CharField(source='order_id')
    createdDate = serializers.DateField(source='ord_date')
    billTotal = serializers.CharField(source='bill_total')


class CreateSalesOrderResponseSerializer(serializers.Serializer):
    """Serializer for sales order creation response"""
    code = serializers.CharField()
    type = serializers.CharField()
    message = serializers.CharField()
    documentDetails = DocumentDetailSerializer(many=True)


class CreateGLCustomerRequestSerializer(serializers.Serializer):
    """Serializer for global local customer creation request
    
    🎯 NOTE: apiKey is now optional - tokens auto-generated in background
    """
    c2Code = serializers.CharField(max_length=20)
    StoreID = serializers.CharField(max_length=20)
    apiKey = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="Deprecated: Auto-generated by backend")
    StoreID = serializers.CharField(max_length=20)
    apiKey = serializers.CharField(max_length=255)
    Code = serializers.CharField(max_length=50)
    ipName = serializers.CharField(max_length=255)
    Mail = serializers.EmailField()
    Gender = serializers.CharField(max_length=1)
    Dlno = serializers.CharField(max_length=100, required=False)
    City = serializers.CharField(max_length=255)
    ipState = serializers.CharField(max_length=255)
    Address1 = serializers.CharField()
    Address2 = serializers.CharField(required=False)
    Pincode = serializers.IntegerField()
    Mobile = serializers.CharField(max_length=15)
    Gstno = serializers.CharField(max_length=20, required=False)


class CreateGLCustomerResponseSerializer(serializers.Serializer):
    """Serializer for global local customer creation response"""
    code = serializers.CharField()
    type = serializers.CharField()
    message = serializers.CharField()


class InvoiceDetailForStatusSerializer(serializers.ModelSerializer):
    """Serializer for invoice details in order status"""
    productId = serializers.CharField(source='product_id')
    productName = serializers.CharField(source='product_name')
    hsnCode = serializers.CharField(source='hsn_code')
    qtyPerBox = serializers.CharField(source='qty_per_box')
    expiryDate = serializers.DateField(source='expiry_date')
    saleRate = serializers.DecimalField(max_digits=10, decimal_places=3, source='sale_rate')
    discAmt = serializers.DecimalField(max_digits=10, decimal_places=2, source='disc_amt')
    discPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='disc_per')
    itemTotal = serializers.DecimalField(max_digits=12, decimal_places=2, source='item_total')
    cgstPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='cgst_per')
    cgstAmt = serializers.DecimalField(max_digits=10, decimal_places=2, source='cgst_amt')
    sgstPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='sgst_per')
    sgstAmt = serializers.DecimalField(max_digits=10, decimal_places=2, source='sgst_amt')
    igstPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='igst_per')
    igstAmt = serializers.DecimalField(max_digits=10, decimal_places=2, source='igst_amt')
    cessPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='cess_per')
    cessAmt = serializers.DecimalField(max_digits=10, decimal_places=2, source='cess_amt')
    
    class Meta:
        model = InvoiceDetail
        fields = [
            'productId', 'productName', 'hsnCode', 'qtyPerBox', 'batch', 'qty', 
            'expiryDate', 'mrp', 'saleRate', 'discAmt', 'discPer', 'itemTotal',
            'cgstPer', 'cgstAmt', 'sgstPer', 'sgstAmt', 'igstPer', 'igstAmt', 'cessPer', 'cessAmt'
        ]


class InvoiceForStatusSerializer(serializers.ModelSerializer):
    """Serializer for invoice in order status response"""
    docNo = serializers.CharField(source='doc_no')
    docDate = serializers.DateField(source='doc_date')
    docStatus = serializers.CharField(source='doc_status')
    createdBy = serializers.CharField(source='created_by')
    docDiscount = serializers.CharField(source='doc_discount')
    docTotal = serializers.CharField(source='doc_total')
    detail = InvoiceDetailForStatusSerializer(source='details', many=True)
    
    class Meta:
        model = Invoice
        fields = ['docNo', 'docDate', 'docStatus', 'createdBy', 'docDiscount', 'docTotal', 'detail']


class OrderStatusResponseSerializer(serializers.Serializer):
    """Serializer for order status response"""
    code = serializers.CharField()
    orderId = serializers.CharField()
    custCode = serializers.CharField()
    fromGstNo = serializers.CharField()
    toGstNo = serializers.CharField()
    customerType = serializers.CharField()
    doctorName = serializers.CharField()
    invoices = InvoiceForStatusSerializer(many=True)


# ==================== CART & WISHLIST SERIALIZERS ====================

class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart item with full product details"""
    itemCode = serializers.CharField(source='item.item_code', read_only=True)
    itemName = serializers.CharField(source='item.item_name', read_only=True)
    subheading = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    categoryName = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    mrp = serializers.DecimalField(source='item.mrp', max_digits=10, decimal_places=2, read_only=True)
    discountPercentage = serializers.SerializerMethodField()
    discountedPrice = serializers.SerializerMethodField()
    itemTotalMrp = serializers.SerializerMethodField()
    itemTotalDiscounted = serializers.SerializerMethodField()
    itemSavings = serializers.SerializerMethodField()
    batchNo = serializers.CharField(source='batch_no', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'itemCode', 'itemName', 'subheading', 'description', 
            'categoryName', 'images', 'mrp', 'quantity', 'batchNo',
            'discountPercentage', 'discountedPrice', 'itemTotalMrp', 
            'itemTotalDiscounted', 'itemSavings'
        ]
    
    def get_subheading(self, obj):
        """Get subheading from ProductInfo"""
        try:
            product_info = obj.item.product_info
            return product_info.subheading or None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_description(self, obj):
        """Get description from ProductInfo"""
        try:
            product_info = obj.item.product_info
            return product_info.description or None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_categoryName(self, obj):
        """Get category name from ProductInfo"""
        try:
            product_info = obj.item.product_info
            if product_info.category:
                return product_info.category.name
            return None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_images(self, obj):
        """Get all product images for cart item"""
        try:
            product_info = obj.item.product_info
            images = product_info.images.all().order_by('image_order')
            return ProductImageSerializer(images, many=True, context=self.context).data
        except ProductInfo.DoesNotExist:
            return []
    
    def get_discountPercentage(self, obj):
        return obj.get_discount_percentage()
    
    def get_discountedPrice(self, obj):
        return obj.get_discounted_price()
    
    def get_itemTotalMrp(self, obj):
        return obj.get_item_total_mrp()
    
    def get_itemTotalDiscounted(self, obj):
        return obj.get_item_total_discounted()
    
    def get_itemSavings(self, obj):
        return obj.get_item_savings()


class CartSerializer(serializers.ModelSerializer):
    """Serializer for cart"""
    items = CartItemSerializer(many=True, read_only=True)
    bagTotal = serializers.SerializerMethodField()
    bagSavings = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    grandTotal = serializers.SerializerMethodField()
    itemCount = serializers.SerializerMethodField()
    convenienceFee = serializers.DecimalField(source='convenience_fee', max_digits=10, decimal_places=2)
    deliveryFee = serializers.DecimalField(source='delivery_fee', max_digits=10, decimal_places=2)
    platformFee = serializers.DecimalField(source='platform_fee', max_digits=10, decimal_places=2)
    
    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'bagTotal', 'bagSavings', 'subtotal', 'grandTotal',
            'convenienceFee', 'deliveryFee', 'platformFee', 'itemCount'
        ]
    
    def get_bagTotal(self, obj):
        return obj.get_bag_total()
    
    def get_bagSavings(self, obj):
        return obj.get_bag_savings()
    
    def get_subtotal(self, obj):
        return obj.get_subtotal()
    
    def get_grandTotal(self, obj):
        return obj.get_grand_total()
    
    def get_itemCount(self, obj):
        return obj.get_item_count()


class CartItemSmallSerializer(serializers.ModelSerializer):
    """Serializer for cart item - balanced details for add/update/display endpoints"""
    itemCode = serializers.CharField(source='item.item_code', read_only=True)
    itemName = serializers.CharField(source='item.item_name', read_only=True)
    subheading = serializers.SerializerMethodField()
    primaryImage = serializers.SerializerMethodField()
    mrp = serializers.DecimalField(source='item.mrp', max_digits=10, decimal_places=2, read_only=True)
    discountPercentage = serializers.SerializerMethodField()
    discountedPrice = serializers.SerializerMethodField()
    itemTotalMrp = serializers.SerializerMethodField()
    itemTotalDiscounted = serializers.SerializerMethodField()
    itemSavings = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'itemCode', 'itemName', 'subheading', 'primaryImage',
            'mrp', 'quantity', 'discountPercentage', 'discountedPrice', 
            'itemTotalMrp', 'itemTotalDiscounted', 'itemSavings'
        ]
    
    def get_subheading(self, obj):
        """Get subheading from ProductInfo"""
        try:
            product_info = obj.item.product_info
            return product_info.subheading or None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_primaryImage(self, obj):
        """Get first/primary image for cart item"""
        try:
            product_info = obj.item.product_info
            first_image = product_info.images.all().order_by('image_order').first()
            if first_image:
                return ProductImageSerializer(first_image, context=self.context).data.get('imageUrl')
            return None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_discountPercentage(self, obj):
        return obj.get_discount_percentage()
    
    def get_discountedPrice(self, obj):
        return obj.get_discounted_price()
    
    def get_itemTotalMrp(self, obj):
        return obj.get_item_total_mrp()
    
    def get_itemTotalDiscounted(self, obj):
        return obj.get_item_total_discounted()
    
    def get_itemSavings(self, obj):
        return obj.get_item_savings()


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding item to cart"""
    itemCode = serializers.CharField(max_length=50, min_length=1)
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    batchNo = serializers.CharField(required=False, allow_null=True)
    
    def validate_quantity(self, value):
        """Validate quantity is reasonable to prevent spam orders"""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1 unit")
        if value > 100:
            raise serializers.ValidationError("Cannot order more than 100 units at once")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=1)


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""
    imageUrl = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['image_order', 'imageUrl']
    
    def get_imageUrl(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class WishlistItemSerializer(serializers.ModelSerializer):
    """Serializer for wishlist item with full product details"""
    itemCode = serializers.CharField(source='item.item_code', read_only=True)
    itemName = serializers.CharField(source='item.item_name', read_only=True)
    batchNo = serializers.CharField(source='item.batch_no', read_only=True)
    subheading = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    categoryName = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    mrp = serializers.DecimalField(source='item.mrp', max_digits=10, decimal_places=2, read_only=True)
    discountPercentage = serializers.SerializerMethodField()
    discountedPrice = serializers.SerializerMethodField()
    
    class Meta:
        model = WishlistItem
        fields = [
            'id', 'itemCode', 'itemName', 'batchNo', 'subheading', 'description', 
            'categoryName', 'images', 'mrp', 'quantity', 
            'discountPercentage', 'discountedPrice'
        ]
    
    def get_subheading(self, obj):
        """Get subheading from ProductInfo"""
        try:
            product_info = obj.item.product_info
            return product_info.subheading or None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_description(self, obj):
        """Get description from ProductInfo"""
        try:
            product_info = obj.item.product_info
            return product_info.description or None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_categoryName(self, obj):
        """Get category name from ProductInfo"""
        try:
            product_info = obj.item.product_info
            if product_info.category:
                return product_info.category.name
            return None
        except ProductInfo.DoesNotExist:
            return None
    
    def get_images(self, obj):
        """Get all product images for wishlist item"""
        try:
            product_info = obj.item.product_info
            images = product_info.images.all().order_by('image_order')
            return ProductImageSerializer(images, many=True, context=self.context).data
        except ProductInfo.DoesNotExist:
            return []
    
    def get_discountPercentage(self, obj):
        return obj.get_discount_percentage()
    
    def get_discountedPrice(self, obj):
        return obj.get_discounted_price()


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for wishlist"""
    items = WishlistItemSerializer(many=True, read_only=True)
    itemCount = serializers.SerializerMethodField()
    
    class Meta:
        model = Wishlist
        fields = ['id', 'items', 'itemCount']
    
    def get_itemCount(self, obj):
        return obj.get_item_count()


class AddToWishlistSerializer(serializers.Serializer):
    """Serializer for adding item to wishlist"""
    itemCode = serializers.CharField()


class MoveToCartSerializer(serializers.Serializer):
    """Serializer for moving item from wishlist to cart"""
    itemCode = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, default=1)

# ==================== ADDRESS SERIALIZERS ====================

class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address management"""
    
    class Meta:
        model = Address
        fields = [
            'id', 'user', 'name', 'phone', 'pincode', 'city', 'state',
            'locality', 'flat_building', 'landmark', 'address_type',
            'is_default', 'is_active', 'latitude', 'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_phone(self, value):
        """Validate phone number format"""
        if not value.isdigit() or len(value) < 10 or len(value) > 15:
            raise serializers.ValidationError("Phone number must be 10-15 digits")
        return value
    
    def validate_pincode(self, value):
        """Validate pincode format"""
        if not value.isdigit() or len(value) < 4 or len(value) > 10:
            raise serializers.ValidationError("Pincode must be 4-10 digits")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Check for locality or flat_building at minimum
        if not data.get('locality') and not data.get('flat_building'):
            raise serializers.ValidationError("Either locality or flat/building name is required")
        return data


class AddressListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing addresses"""
    full_address = serializers.SerializerMethodField()
    
    class Meta:
        model = Address
        fields = [
            'id', 'name', 'phone', 'pincode', 'city', 'state',
            'address_type', 'is_default', 'is_active', 'full_address',
            'latitude', 'longitude'
        ]
    
    def get_full_address(self, obj):
        return obj.get_full_address()


class CreateAddressSerializer(serializers.ModelSerializer):
    """Serializer for creating address with GPS coordinates from Flutter"""
    
    class Meta:
        model = Address
        fields = [
            'name', 'phone', 'pincode', 'city', 'state',
            'locality', 'flat_building', 'landmark', 'address_type', 'is_default',
            'latitude', 'longitude'
        ]
    
    def validate_phone(self, value):
        """Validate phone number format"""
        if not value.isdigit() or len(value) < 10 or len(value) > 15:
            raise serializers.ValidationError("Phone number must be 10-15 digits")
        return value
    
    def validate_pincode(self, value):
        """Validate pincode format"""
        if not value.isdigit() or len(value) < 4 or len(value) > 10:
            raise serializers.ValidationError("Pincode must be 4-10 digits")
        return value
    
    def validate_latitude(self, value):
        """Validate latitude range"""
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude range"""
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        if not data.get('locality') and not data.get('flat_building'):
            raise serializers.ValidationError("Either locality or flat/building name is required")
        return data

# ==================== PRODUCT INFO UPDATE SERIALIZERS ====================

class UpdateProductInfoRequestSerializer(serializers.Serializer):
    """Serializer for updating product info (subheading, description, type_label, and images)
    Authentication: JWT Token (SUPERADMIN only)
    """
    c_item_code = serializers.CharField(required=True, help_text="Item code")
    subheading = serializers.CharField(required=False, allow_blank=True, help_text="Product subheading/subtitle")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Product description")
    type_label = serializers.CharField(required=False, allow_blank=True, help_text="Product type label (e.g., 'Pain Relief', 'Antibiotic') shown under product name")
    # Image fields - accepts multiple images
    image_1 = serializers.ImageField(required=False, allow_null=True, help_text="Primary product image")
    image_2 = serializers.ImageField(required=False, allow_null=True, help_text="Secondary product image")
    image_3 = serializers.ImageField(required=False, allow_null=True, help_text="Tertiary product image")
    
    def validate_c_item_code(self, value):
        """Validate that item exists"""
        try:
            ItemMaster.objects.get(item_code=value)
        except ItemMaster.DoesNotExist:
            raise serializers.ValidationError(f"Item with code {value} does not exist")
        return value
    
    def validate_image_1(self, value):
        """Validate image file"""
        if value:
            return self._validate_image_file(value)
        return value
    
    def validate_image_2(self, value):
        """Validate image file"""
        if value:
            return self._validate_image_file(value)
        return value
    
    def validate_image_3(self, value):
        """Validate image file"""
        if value:
            return self._validate_image_file(value)
        return value
    
    def _validate_image_file(self, value):
        """Common validation for all image files"""
        if value.size > 5 * 1024 * 1024:  # 5MB limit
            raise serializers.ValidationError("Image file size must not exceed 5MB")
        
        # Check file extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"Only {', '.join(allowed_extensions)} files are allowed")
        
        return value


class UploadProductImageRequestSerializer(serializers.Serializer):
    """Serializer for uploading product images
    Authentication: JWT Token (SUPERADMIN only)
    """
    c_item_code = serializers.CharField(required=True, help_text="Item code")
    image = serializers.ImageField(required=True, help_text="Product image file")
    image_order = serializers.IntegerField(required=False, default=1, min_value=1, max_value=3, help_text="Image order (1-3)")
    
    def validate_c_item_code(self, value):
        """Validate that item exists"""
        try:
            ItemMaster.objects.get(item_code=value)
        except ItemMaster.DoesNotExist:
            raise serializers.ValidationError(f"Item with code {value} does not exist")
        return value
    
    def validate_image(self, value):
        """Validate image file"""
        if value.size > 5 * 1024 * 1024:  # 5MB limit
            raise serializers.ValidationError("Image file size must not exceed 5MB")
        
        # Check file extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"Only {', '.join(allowed_extensions)} files are allowed")
        
        return value


class UpdateProductInfoResponseSerializer(serializers.Serializer):
    """Response serializer for product info update"""
    code = serializers.CharField()
    message = serializers.CharField()
    data = serializers.DictField()


class SelectAddressSerializer(serializers.Serializer):
    """Serializer for selecting address for order"""
    address_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID of the address to use (optional - uses default if not provided)")
    payment_method = serializers.ChoiceField(
        choices=['RAZORPAY', 'COD', 'NETBANKING', 'WALLET', 'UPI'],
        required=False,
        default='RAZORPAY',
        help_text="Payment method: RAZORPAY or COD"
    )
    
    def validate_address_id(self, value):
        """Validate address exists if provided"""
        if value is not None:
            try:
                Address.objects.get(id=value)
            except Address.DoesNotExist:
                raise serializers.ValidationError("Address not found")
        return value


class DetectLocationSerializer(serializers.Serializer):
    """Serializer for GPS-based location detection"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True, help_text="GPS latitude")
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True, help_text="GPS longitude")
    accuracy = serializers.IntegerField(required=False, allow_null=True, help_text="GPS accuracy in meters")
    
    def validate_latitude(self, value):
        """Validate latitude range"""
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude range"""
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class LocationAddressResponseSerializer(serializers.Serializer):
    """Response serializer for detected/geocoded address"""
    full_address = serializers.CharField(help_text="Complete formatted address")
    street = serializers.CharField(allow_blank=True, help_text="Street name and number")
    locality = serializers.CharField(help_text="Locality/Area/Street")
    city = serializers.CharField(help_text="City name")
    state = serializers.CharField(help_text="State/Province")
    pincode = serializers.CharField(allow_blank=True, help_text="Postal code")
    country = serializers.CharField(allow_blank=True, help_text="Country")
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, help_text="Latitude")
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, help_text="Longitude")
    accuracy = serializers.CharField(help_text="Location accuracy level")


class ConfirmLocationAddressSerializer(serializers.ModelSerializer):
    """Serializer for confirming and saving detected address"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    location_accuracy = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Address
        fields = [
            'name', 'phone', 'pincode', 'city', 'state',
            'locality', 'flat_building', 'landmark', 'address_type',
            'is_default', 'latitude', 'longitude', 'location_accuracy'
        ]
    
    def validate_phone(self, value):
        """Validate phone number format"""
        if not value.isdigit() or len(value) < 10 or len(value) > 15:
            raise serializers.ValidationError("Phone number must be 10-15 digits")
        return value
    
    def validate_pincode(self, value):
        """Validate pincode format"""
        if not value.isdigit() or len(value) < 4 or len(value) > 10:
            raise serializers.ValidationError("Pincode must be 4-10 digits")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        if not data.get('locality') and not data.get('flat_building'):
            raise serializers.ValidationError("Either locality or flat/building name is required")
        return data


# ==================== RECOMMENDATION SERIALIZERS ====================

class ProductRecommendationSerializer(serializers.ModelSerializer):
    """
    Serializer for recommended products with ERP enrichment support
    
    Data Sources:
    - Primary: Database (ItemMaster model)
    - Secondary: ERP (when apiKey provided in request) - enriches with live pricing, stock, expiry
    
    Field Priority (for fields from ERP):
    1. If apiKey provided: Use ERP data (mrp, std_disc, max_disc, expiry_date, stockBalQty)
    2. Fallback: Use database values
    """
    batchNo = serializers.CharField(source='batch_no', allow_null=True)
    c_item_code = serializers.CharField(source='item_code')
    expiryDate = serializers.DateField(source='expiry_date', allow_null=True)
    itemName = serializers.CharField(source='item_name')
    itemQtyPerBox = serializers.IntegerField(source='item_qty_per_box', allow_null=True)
    max_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2)
    std_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    stockBalQty = serializers.SerializerMethodField()
    subheading = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    type_label = serializers.SerializerMethodField()
    brand_id = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    brand_logo = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    cart_status = serializers.SerializerMethodField()
    wishlist_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemMaster
        fields = ['batchNo', 'c_item_code', 'expiryDate', 'itemName', 'itemQtyPerBox', 
                  'max_disc', 'mrp', 'std_disc', 'stockBalQty', 'subheading', 'description',
                  'type_label', 'brand_id', 'brand_name', 'brand_logo', 'images', 
                  'cart_status', 'wishlist_status']
    
    def get_stockBalQty(self, obj):
        """
        Get stock quantity with ERP enrichment support
        
        Priority:
        1. ERP stock (if apiKey was provided and data was fetched)
        2. Database Stock model record
        3. Default: 0
        """
        # Check if ERP stock was attached during enrichment
        if hasattr(obj, 'erp_stock') and obj.erp_stock is not None:
            return obj.erp_stock  # ← From ERP via apiKey
        
        # Fallback to database
        try:
            from .models import Stock
            stock = Stock.objects.filter(item=obj).first()
            if stock:
                return stock.total_bal_ls_qty  # ← From DB
            return 0
        except:
            return 0
    
    def get_subheading(self, obj):
        """Get product subheading"""
        try:
            return obj.product_info.subheading or ""
        except:
            return ""
    
    def get_description(self, obj):
        """Get product description"""
        try:
            return obj.product_info.description or ""
        except:
            return ""
    
    def get_type_label(self, obj):
        """Get product type label"""
        try:
            return obj.product_info.type_label or ""
        except:
            return ""
    
    def get_brand_id(self, obj):
        """Get brand/category ID"""
        try:
            return obj.product_info.category.id if obj.product_info.category else None
        except:
            return None
    
    def get_brand_name(self, obj):
        """Get brand/category name"""
        try:
            return obj.product_info.category.name if obj.product_info.category else ""
        except:
            return ""
    
    def get_brand_logo(self, obj):
        """Get brand logo"""
        try:
            request = self.context.get('request')
            if obj.product_info.category and obj.product_info.category.icon:
                if request:
                    return request.build_absolute_uri(obj.product_info.category.icon.url)
                return obj.product_info.category.icon.url
            return ""
        except:
            return ""
    
    def get_images(self, obj):
        """Get ALL product images ordered by image_order"""
        try:
            request = self.context.get('request')
            from .models import ProductImage
            images = ProductImage.objects.filter(product_info=obj.product_info).order_by('image_order')
            result = []
            for img in images:
                if request:
                    image_url = request.build_absolute_uri(img.image.url)
                else:
                    image_url = img.image.url
                result.append({
                    'image': image_url,
                    'image_order': img.image_order
                })
            return result
        except:
            return []
    
    def get_cart_status(self, obj):
        """Check if product is in user's cart"""
        # Priority 1: Use user from context (set by view with userId param)
        user = self.context.get('cart_wishlist_user')
        
        # Priority 2: Fallback to request.user if available
        if not user:
            request = self.context.get('request')
            if request and request.user and request.user.is_authenticated:
                user = request.user
        
        # Check cart if user exists
        if user:
            try:
                from .models import CartItem
                return CartItem.objects.filter(
                    cart__user=user,
                    product_info=obj.product_info
                ).exists()
            except:
                return False
        return False
    
    def get_wishlist_status(self, obj):
        """Check if product is in user's wishlist"""
        # Priority 1: Use user from context (set by view with userId param)
        user = self.context.get('cart_wishlist_user')
        
        # Priority 2: Fallback to request.user if available
        if not user:
            request = self.context.get('request')
            if request and request.user and request.user.is_authenticated:
                user = request.user
        
        # Check wishlist if user exists
        if user:
            try:
                from .models import WishlistItem
                return WishlistItem.objects.filter(
                    wishlist__user=user,
                    product_info=obj.product_info
                ).exists()
            except:
                return False
        return False


class SimilarProductsResponseSerializer(serializers.Serializer):
    """
    Response serializer for similar products recommendation
    
    Data Source: Database + Optional ERP enrichment
    - Products are queried from database (same category)
    - When apiKey provided: Enriched with live ERP data (pricing, stock, expiry)
    
    Usage in view: /api/recommendations/similar/?itemCode=INJ001&apiKey=xyz
    """
    category = serializers.CharField()
    categoryId = serializers.IntegerField()
    count = serializers.IntegerField()
    products = ProductRecommendationSerializer(many=True)


class FrequentlyBoughtTogetherResponseSerializer(serializers.Serializer):
    """
    Response serializer for frequently bought together recommendation
    
    Data Source: Database + Optional ERP enrichment
    - Recommendations from SalesOrder history (products bought together)
    - When apiKey provided: Each product enriched with live ERP data
    
    Usage in view: /api/recommendations/frequently-bought/?itemCode=INJ001&apiKey=xyz
    """
    baseProductCode = serializers.CharField()
    baseProductName = serializers.CharField()
    frequentlyBoughtWith = ProductRecommendationSerializer(many=True)
    totalPurchaseCount = serializers.IntegerField()


class TopSellingResponseSerializer(serializers.Serializer):
    """
    Response serializer for top selling products
    
    Data Source: Database + Optional ERP enrichment
    - Top products by sales volume from SalesOrder records
    - When apiKey provided: Each product enriched with live ERP data (pricing, stock)
    
    Usage in view: /api/recommendations/top-selling/?period=weekly&apiKey=xyz
    """
    period = serializers.CharField()  # 'weekly', 'monthly', 'all-time'
    totalCount = serializers.IntegerField()
    products = ProductRecommendationSerializer(many=True)

# ==================== CATEGORY SERIALIZER ====================

from .models import Category


# Category product serializer with ERP enrichment support
class CategoryProductWithERPSerializer(serializers.Serializer):
    """
    Serializer for products in a category with optional ERP enrichment
    
    Data Sources:
    - Primary: ItemMaster + ProductInfo (database)
    - Secondary: ERP (when apiKey provided in request context)
    
    Supports live data enrichment via context['api_key']
    """
    itemCode = serializers.CharField(source='item_code')
    itemName = serializers.CharField(source='item_name')
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    batchNo = serializers.CharField(source='batch_no', allow_null=True)
    c_item_code = serializers.CharField(source='item_code')
    expiryDate = serializers.DateField(source='expiry_date', allow_null=True)
    itemQtyPerBox = serializers.IntegerField(source='item_qty_per_box', allow_null=True)
    max_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    std_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    stockBalQty = serializers.SerializerMethodField()
    subheading = serializers.SerializerMethodField()
    type_label = serializers.SerializerMethodField()
    brand_id = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    brand_logo = serializers.SerializerMethodField()
    cart_status = serializers.SerializerMethodField()
    wishlist_status = serializers.SerializerMethodField()
    discountPercentage = serializers.FloatField(default=0.0)
    discountedPrice = serializers.FloatField(default=0.0)
    
    def get_stockBalQty(self, obj):
        """Get stock with priority: ERP enriched > Database > 0"""
        # Priority 1: ERP enriched data (attached by view)
        if hasattr(obj, 'erp_stock') and obj.erp_stock is not None:
            return int(obj.erp_stock)
        
        # Priority 2: Database Stock model
        try:
            stock = Stock.objects.filter(item=obj).first()
            if stock and stock.total_bal_ls_qty:
                return stock.total_bal_ls_qty
        except:
            pass
        
        # Fallback: 0
        return 0
    
    def get_description(self, obj):
        """Get description from ProductInfo"""
        try:
            return obj.product_info.description or ""
        except:
            return ""
    
    def get_subheading(self, obj):
        """Get subheading from ProductInfo"""
        try:
            return obj.product_info.subheading or ""
        except:
            return ""
    
    def get_type_label(self, obj):
        """Get type_label from ProductInfo"""
        try:
            return obj.product_info.type_label or ""
        except:
            return ""
    
    def get_images(self, obj):
        """Get ALL product images"""
        try:
            request = self.context.get('request')
            images = obj.product_info.images.all().order_by('image_order')
            result = []
            for img in images:
                if request:
                    image_url = request.build_absolute_uri(img.image.url)
                else:
                    image_url = img.image.url
                result.append({
                    'image': image_url,
                    'image_order': img.image_order
                })
            return result
        except:
            return []
    
    def get_brand_id(self, obj):
        """Get category/brand ID"""
        try:
            return obj.product_info.category.id if obj.product_info.category else None
        except:
            return None
    
    def get_brand_name(self, obj):
        """Get category/brand name"""
        try:
            return obj.product_info.category.name if obj.product_info.category else ""
        except:
            return ""
    
    def get_brand_logo(self, obj):
        """Get category/brand icon"""
        try:
            request = self.context.get('request')
            if obj.product_info.category and obj.product_info.category.icon:
                if request:
                    return request.build_absolute_uri(obj.product_info.category.icon.url)
                return obj.product_info.category.icon.url
            return ""
        except:
            return ""
    
    def get_cart_status(self, obj):
        """Check if product is in user's cart"""
        # Priority 1: Use user from context (set by view with userId param)
        user = self.context.get('cart_wishlist_user')
        
        # Priority 2: Fallback to request.user if available
        if not user:
            request = self.context.get('request')
            if request and request.user and request.user.is_authenticated:
                user = request.user
        
        # Check cart if user exists
        if user:
            try:
                return CartItem.objects.filter(
                    cart__user=user,
                    product_info=obj.product_info
                ).exists()
            except:
                return False
        return False
    
    def get_wishlist_status(self, obj):
        """Check if product is in user's wishlist"""
        # Priority 1: Use user from context (set by view with userId param)
        user = self.context.get('cart_wishlist_user')
        
        # Priority 2: Fallback to request.user if available
        if not user:
            request = self.context.get('request')
            if request and request.user and request.user.is_authenticated:
                user = request.user
        
        # Check wishlist if user exists
        if user:
            try:
                return WishlistItem.objects.filter(
                    wishlist__user=user,
                    product_info=obj.product_info
                ).exists()
            except:
                return False
        return False


# Nested serializer for products under each category
class CategoryWithProductsSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'is_active', 'products']
    
    def get_products(self, obj):
        """Get category products as ItemMaster objects with ERP enrichment support"""
        # Get all ProductInfo for this category
        product_infos = obj.products.all()
        
        # Get related ItemMaster objects for each ProductInfo
        items = []
        erp_stock_map = self.context.get('erp_stock_map', {})
        
        for prod_info in product_infos:
            try:
                # Get the ItemMaster via the product_info's item field
                if hasattr(prod_info, 'item') and prod_info.item:
                    # Attach ProductInfo to ItemMaster for serializer access
                    prod_info.item.product_info = prod_info
                    
                    # Attach ERP stock if available
                    if erp_stock_map:
                        prod_info.item.erp_stock = erp_stock_map.get(prod_info.item.item_code)
                    
                    items.append(prod_info.item)
            except:
                pass
        
        # Serialize with context (includes request and api_key for ERP enrichment)
        serializer = CategoryProductWithERPSerializer(
            items, 
            many=True, 
            context=self.context
        )
        return serializer.data

# ==================== OFFER SERIALIZERS ====================

class OfferSerializer(serializers.ModelSerializer):
    """Serializer for Offer model - ListCreate operations"""
    is_valid_now = serializers.SerializerMethodField()
    placement_display = serializers.CharField(source='get_placement_display', read_only=True)
    status_display = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Offer
        fields = [
            'offer_id', 'title', 'description', 'discount_percentage', 'valid_from', 'valid_to',
            'placement', 'placement_display', 'category', 'category_name',
            'status', 'status_display', 'banner_image', 'is_valid_now',
            'products_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_valid_now(self, obj):
        return obj.is_valid_now
    
    def get_status_display(self, obj):
        return "Active" if obj.status else "Inactive"
    
    def get_products_count(self, obj):
        return obj.products.count()


class OfferCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating offers"""
    products = serializers.PrimaryKeyRelatedField(
        queryset=ItemMaster.objects.all(),
        many=True,
        required=False
    )
    
    class Meta:
        model = Offer
        fields = [
            'offer_id', 'title', 'description', 'discount_percentage', 'valid_from', 'valid_to',
            'placement', 'category', 'products', 'status', 'banner_image'
        ]
    
    def to_internal_value(self, data):
        """Handle form-data format - extract single values from lists"""
        # Convert data to regular dict and extract single values from lists
        data_copy = {}
        for key, value in data.items():
            # If it's a list with single item, extract it (except products)
            if key != 'products' and isinstance(value, (list, tuple)):
                data_copy[key] = value[0] if value else None
            else:
                data_copy[key] = value
        
        # Now handle products field
        if 'products' in data_copy:
            products = data_copy.get('products')
            products_list = []
            
            # Case 1: Already a list (from form-data with multiple fields)
            if isinstance(products, (list, tuple)):
                for item in products:
                    item_str = str(item).strip()
                    # Handle if item itself is a stringified list
                    if item_str.startswith('[') and item_str.endswith(']'):
                        import ast
                        try:
                            parsed = ast.literal_eval(item_str)
                            products_list.extend([str(p).strip() for p in parsed])
                        except:
                            products_list.append(item_str.strip('[]').strip())
                    else:
                        products_list.append(item_str)
            
            # Case 2: String format
            elif isinstance(products, str):
                item_str = products.strip().strip('"').strip("'")
                
                # Stringified list: ['I00003', 'I00017']
                if item_str.startswith('[') and item_str.endswith(']'):
                    import ast
                    try:
                        parsed = ast.literal_eval(item_str)
                        products_list = [str(p).strip().strip('"').strip("'") for p in parsed]
                    except:
                        # Manual extraction
                        inner = item_str.strip('[]').strip()
                        products_list = [p.strip().strip('"').strip("'") for p in inner.split(',')]
                # Comma-separated
                elif ',' in item_str:
                    products_list = [p.strip() for p in item_str.split(',')]
                # Single product
                else:
                    products_list = [item_str] if item_str else []
            
            # Set cleaned products
            if products_list:
                data_copy['products'] = products_list
        
        return super().to_internal_value(data_copy)
    
    def validate(self, data):
        """Validate dates"""
        if data.get('valid_from') and data.get('valid_to'):
            if data['valid_from'] > data['valid_to']:
                raise serializers.ValidationError(
                    {'valid_to': 'End date must be after start date'}
                )
        return data


class OfferProductSerializer(serializers.Serializer):
    """Serializer for products within an offer with discounted pricing"""
    product_id = serializers.CharField(source='item_code')
    product_name = serializers.CharField(source='item_name')
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    batch_no = serializers.CharField()
    expiry_date = serializers.DateField()
    category = serializers.SerializerMethodField()
    type_label = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    
    def get_discount_percentage(self, obj):
        """Get discount percentage from the offer context"""
        request = self.context.get('request')
        offer_discount = self.context.get('discount_percentage', 0)
        return float(offer_discount)
    
    def get_discounted_price(self, obj):
        """Calculate discounted price based on offer discount"""
        offer_discount = self.context.get('discount_percentage', 0)
        discount_amount = float(obj.mrp) * (float(offer_discount) / 100)
        discounted_price = float(obj.mrp) - discount_amount
        return round(discounted_price, 2)
    
    def get_category(self, obj):
        """Get category name if product has one"""
        try:
            if hasattr(obj, 'product_info') and obj.product_info.category:
                return obj.product_info.category.name
            return None
        except:
            return None
    
    def get_type_label(self, obj):
        """Get type label from ProductInfo if exists"""
        try:
            if hasattr(obj, 'product_info'):
                return obj.product_info.type_label or ""
            return ""
        except:
            return ""
    
    def get_images(self, obj):
        """Get product images"""
        try:
            request = self.context.get('request')
            if hasattr(obj, 'product_info'):
                images = obj.product_info.images.all().order_by('image_order')[:3]
                image_urls = []
                for img in images:
                    if request:
                        image_url = request.build_absolute_uri(img.image.url)
                    else:
                        image_url = img.image.url
                    image_urls.append({
                        'image': image_url,
                        'image_order': img.image_order
                    })
                return image_urls
            return []
        except:
            return []


class OfferListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing offers with products and discounted details"""
    is_valid_now = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    placement_display = serializers.CharField(source='get_placement_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    products = serializers.SerializerMethodField()
    
    class Meta:
        model = Offer
        fields = [
            'offer_id', 'title', 'description', 'discount_percentage', 'valid_from', 'valid_to', 'placement',
            'placement_display', 'category_name', 'status', 'status_display',
            'is_valid_now', 'banner_image', 'products'
        ]
    
    def get_is_valid_now(self, obj):
        return obj.is_valid_now
    
    def get_status_display(self, obj):
        return "Active" if obj.status else "Inactive"
    
    def get_products(self, obj):
        """Get products for this offer with discounted pricing"""
        request = self.context.get('request')
        products = obj.products.all()
        
        # If no specific products are selected, get all products from the category
        if not products.exists() and obj.category:
            products = ItemMaster.objects.filter(product_info__category=obj.category)
        
        # Limit to first 10 products for performance
        products = products[:10]
        
        context = {
            'request': request,
            'discount_percentage': obj.discount_percentage
        }
        
        serializer = OfferProductSerializer(products, many=True, context=context)
        return serializer.data


# ==================== RETAILER NOTIFICATIONS ====================

class RetailerNotificationSerializer(serializers.ModelSerializer):
    """Serializer for retailer notifications - full details"""
    offer_title = serializers.CharField(source='offer.title', read_only=True, allow_null=True)
    offer_discount = serializers.DecimalField(source='offer.discount_percentage', max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    offer_image = serializers.CharField(source='offer.offer_image', read_only=True, allow_null=True)
    
    class Meta:
        model = RetailerNotification
        fields = [
            'notification_id', 'title', 'message', 'is_read', 'icon_url', 
            'offer', 'offer_title', 'offer_discount', 'offer_image',
            'created_at', 'read_at'
        ]
        read_only_fields = ['notification_id', 'created_at', 'read_at']


class RetailerNotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing notifications"""
    offer_title = serializers.CharField(source='offer.title', read_only=True, allow_null=True)
    offer_discount = serializers.DecimalField(source='offer.discount_percentage', max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    
    class Meta:
        model = RetailerNotification
        fields = [
            'notification_id', 'title', 'message', 'is_read', 'icon_url',
            'offer_title', 'offer_discount', 'created_at'
        ]


class RetailerNotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications (admin use)"""
    
    class Meta:
        model = RetailerNotification
        fields = ['title', 'message', 'offer', 'icon_url']
    
    def create(self, validated_data):
        return RetailerNotification.objects.create(**validated_data)


# ==================== CREDIT NOTE SERIALIZERS ====================

class CreditNoteCreateSerializer(serializers.ModelSerializer):
    """Retailer creates a credit note request"""
    
    class Meta:
        model = CreditNote
        fields = [
            'reference_invoice', 'order_id', 'product_name',
            'item_code', 'quantity', 'quantity_to_return',
            'amount', 'sale_rate',
            'reason', 'additional_notes', 'upload_image',
            'retailer_confirmed'
        ]
    
    def validate_quantity_to_return(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity to return must be greater than 0"
            )
        return value
    
    def validate(self, data):
        if data.get('quantity_to_return', 0) > data.get('quantity', 0):
            raise serializers.ValidationError(
                "Return quantity cannot exceed original quantity"
            )
        return data
    
    def create(self, validated_data):
        # If you're recalculating here, use sale_rate from validated_data
        sale_rate = validated_data.get('sale_rate', 0)
        qty_to_return = validated_data.get('quantity_to_return', 0)
        
        # Only calculate amount if sale_rate is provided (frontend can also send amount directly)
        if sale_rate and qty_to_return:
            validated_data['amount'] = sale_rate * qty_to_return
        
        return super().create(validated_data)


class CreditNoteListSerializer(serializers.ModelSerializer):
    """For listing credit notes - retailer and admin"""
    retailer_name = serializers.CharField(
        source='retailer.first_name', 
        read_only=True
    )
    shop_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    reason_display = serializers.CharField(
        source='get_reason_display', 
        read_only=True
    )
    
    class Meta:
        model = CreditNote
        fields = [
            'id', 'credit_note_id', 'retailer_name', 'shop_name',
            'reference_invoice', 'order_id', 'product_name',
            'quantity', 'quantity_to_return', 'sale_rate', 'amount',
            'reason', 'reason_display', 'status', 'status_display',
            'additional_notes', 'upload_image',
            'admin_remarks', 'reviewed_at', 'created_at'
        ]
    
    def get_shop_name(self, obj):
        try:
            return obj.retailer.kyc.shop_name
        except:
            return ''


class CreditNoteDetailSerializer(serializers.ModelSerializer):
    """Full detail for admin modal view"""
    retailer_name = serializers.CharField(
        source='retailer.first_name', 
        read_only=True
    )
    shop_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.username', 
        read_only=True,
        allow_null=True
    )
    upload_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CreditNote
        fields = [
            'id', 'credit_note_id', 'retailer_name', 'shop_name',
            'reference_invoice', 'order_id', 'product_name',
            'item_code', 'quantity', 'quantity_to_return', 'sale_rate', 'amount',
            'reason', 'additional_notes', 'upload_image_url',
            'status', 'admin_remarks', 'reviewed_by_name',
            'reviewed_at', 'retailer_confirmed', 'created_at'
        ]
    
    def get_shop_name(self, obj):
        try:
            return obj.retailer.kyc.shop_name
        except:
            return ''
    
    def get_upload_image_url(self, obj):
        request = self.context.get('request')
        if obj.upload_image and request:
            return request.build_absolute_uri(obj.upload_image.url)
        return None


# ==================== WALLET SERIALIZERS ====================

class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for wallet transactions"""
    source_display = serializers.CharField(
        source='get_source_display',
        read_only=True
    )
    type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    credit_note_id = serializers.CharField(
        source='credit_note.credit_note_id',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'type_display', 'source', 'source_display',
            'amount', 'description', 'closing_balance', 'credit_note_id', 'created_at'
        ]


class RetailerWalletSerializer(serializers.ModelSerializer):
    """Serializer for retailer wallet with transaction history"""
    transactions = WalletTransactionSerializer(many=True, read_only=True)
    retailer_name = serializers.CharField(
        source='retailer.first_name',
        read_only=True
    )
    
    class Meta:
        model = RetailerWallet
        fields = [
            'id', 'retailer_name', 'balance', 'transactions', 'updated_at'
        ]

