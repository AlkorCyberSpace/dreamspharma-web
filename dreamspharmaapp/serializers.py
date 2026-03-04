from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import (
    KYC, OTP, APIToken, ItemMaster, Stock, GLCustomer, 
    SalesOrder, SalesOrderItem, Invoice, InvoiceDetail,
    Cart, CartItem, Wishlist, WishlistItem
)
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


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
            raise serializers.ValidationError(
                f"Your account status is {user.get_status_display()}. Only APPROVED or LOGIN ENABLED accounts can login."
            )
        
        # Check if user has submitted KYC
        if not hasattr(user, 'kyc'):
            raise serializers.ValidationError(
                "KYC not submitted. Please submit your KYC documents first."
            )
        
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
        data['is_first_login'] = not authenticated_user.first_login_otp_verified
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


class ItemMasterSerializer(serializers.ModelSerializer):
    """Serializer for ItemMaster model"""
    c_item_code = serializers.CharField(source='item_code')
    itemName = serializers.CharField(source='item_name')
    itemQtyPerBox = serializers.IntegerField(source='item_qty_per_box')
    batchNo = serializers.CharField(source='batch_no')
    std_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_disc = serializers.DecimalField(max_digits=10, decimal_places=2)
    expiryDate = serializers.DateField(source='expiry_date')
    
    class Meta:
        model = ItemMaster
        fields = ['c_item_code', 'itemName', 'itemQtyPerBox', 'batchNo', 'std_disc', 'max_disc', 'expiryDate', 'mrp']


class FetchStockRequestSerializer(serializers.Serializer):
    """Serializer for stock fetch request"""
    c2Code = serializers.CharField(max_length=20)
    storeId = serializers.CharField(max_length=20)
    prodCode = serializers.CharField(max_length=20, required=False, default="02")
    apiKey = serializers.CharField(max_length=255)
    inputDateTime = serializers.DateTimeField(required=False)


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
    """Serializer for sales order items"""
    itemSeq = serializers.IntegerField(source='item_seq')
    itemcode = serializers.CharField(source='item_code')
    totalLooseQty = serializers.IntegerField(source='total_loose_qty')
    totalLooseSchQty = serializers.IntegerField(source='total_loose_sch_qty')
    serviceQty = serializers.IntegerField(source='service_qty')
    saleRate = serializers.DecimalField(max_digits=10, decimal_places=3, source='sale_rate')
    discPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='disc_per')
    schDiscPer = serializers.DecimalField(max_digits=5, decimal_places=2, source='sch_disc_per')
    
    class Meta:
        model = SalesOrderItem
        fields = ['itemSeq', 'itemcode', 'totalLooseQty', 'totalLooseSchQty', 'serviceQty', 'saleRate', 'discPer', 'schDiscPer']


class CreateSalesOrderRequestSerializer(serializers.Serializer):
    """Serializer for creating sales order"""
    c2Code = serializers.CharField(max_length=20)
    storeId = serializers.CharField(max_length=20)
    prodCode = serializers.CharField(max_length=20, required=False, default="02")
    apiKey = serializers.CharField(max_length=255)
    ipNo = serializers.CharField(max_length=100)
    mobileNo = serializers.CharField(max_length=15)
    patientName = serializers.CharField(max_length=255)
    patientAddress = serializers.CharField()
    patientEmail = serializers.EmailField()
    counterSale = serializers.IntegerField()
    ordDate = serializers.DateField()
    ordTime = serializers.TimeField()
    userId = serializers.CharField(max_length=100)
    actCode = serializers.CharField(max_length=50)
    actName = serializers.CharField(max_length=255)
    drCode = serializers.CharField(max_length=50, required=False, allow_blank=True)
    drName = serializers.CharField(max_length=255, required=False, allow_blank=True)
    drAddress = serializers.CharField(required=False, allow_blank=True)
    drRegNo = serializers.CharField(max_length=50, required=False, allow_blank=True)
    drOfficeCode = serializers.CharField(max_length=50, required=False, default="-")
    dmanCode = serializers.CharField(max_length=50, required=False, default="-")
    orderTotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    orderDiscPer = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0.00)
    refNo = serializers.IntegerField(required=False)
    orderId = serializers.IntegerField()
    remark = serializers.CharField(required=False, allow_null=True)
    urgentFlag = serializers.IntegerField(required=False, default=0)
    ordConversionFlag = serializers.IntegerField(required=False, default=0)
    dcConversionFlag = serializers.IntegerField(required=False, default=0)
    ordRefNo = serializers.IntegerField(required=False, default=0)
    sysName = serializers.CharField(max_length=100)
    sysIp = serializers.IPAddressField()
    sysUser = serializers.CharField(max_length=100)
    materialInfo = SalesOrderItemSerializer(many=True)


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
    """Serializer for global local customer creation request"""
    c2Code = serializers.CharField(max_length=20)
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
    """Serializer for cart item"""
    itemCode = serializers.CharField(source='item.item_code', read_only=True)
    itemName = serializers.CharField(source='item.item_name', read_only=True)
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
            'id', 'itemCode', 'itemName', 'mrp', 'quantity', 'batchNo',
            'discountPercentage', 'discountedPrice', 'itemTotalMrp', 
            'itemTotalDiscounted', 'itemSavings'
        ]
    
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


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding item to cart"""
    itemCode = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    batchNo = serializers.CharField(required=False, allow_null=True)


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=1)


class WishlistItemSerializer(serializers.ModelSerializer):
    """Serializer for wishlist item"""
    itemCode = serializers.CharField(source='item.item_code', read_only=True)
    itemName = serializers.CharField(source='item.item_name', read_only=True)
    mrp = serializers.DecimalField(source='item.mrp', max_digits=10, decimal_places=2, read_only=True)
    discountPercentage = serializers.SerializerMethodField()
    discountedPrice = serializers.SerializerMethodField()
    
    class Meta:
        model = WishlistItem
        fields = ['id', 'itemCode', 'itemName', 'mrp', 'discountPercentage', 'discountedPrice', 'created_at']
    
    def get_discountPercentage(self, obj):
        return float(obj.item.std_disc)
    
    def get_discountedPrice(self, obj):
        mrp = float(obj.item.mrp)
        discount = float(obj.item.std_disc)
        return round(mrp * (1 - discount / 100), 2)


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
