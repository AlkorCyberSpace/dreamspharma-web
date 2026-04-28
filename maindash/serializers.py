from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from dreamspharmaapp.models import KYC, SalesOrder, Category
from .emails import send_kyc_approval_email, send_kyc_rejection_email
from .models import AuditLog

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user details in KYC context"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'email', 'phone_number', 'role', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'status']


class RetailerKYCDetailSerializer(serializers.ModelSerializer):
    """Serializer for displaying KYC details with user information"""
    user = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = KYC
        fields = [
            'id', 'user', 'status', 'shop_name', 'shop_address', 'shop_email', 
            'shop_phone', 'customer_address', 'gst_number', 'drug_license_number',
            'drug_license', 'id_proof', 'store_photo', 'submitted_at', 
            'approved_at', 'rejection_reason'
        ]
        read_only_fields = [
            'id', 'submitted_at', 'approved_at', 'status', 'rejection_reason', 'user'
        ]


class ApproveKYCSerializer(serializers.Serializer):
    """Serializer for approving KYC of a retailer"""
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        """Validate that user exists and is a retailer"""
        try:
            user = User.objects.get(id=value)
            if user.role != 'RETAILER':
                raise serializers.ValidationError("User must be a retailer")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
    
    def save(self):
        """Approve the KYC for the user"""
        user_id = self.validated_data['user_id']
        user = User.objects.get(id=user_id)
        
        # Get or create KYC
        kyc, _ = KYC.objects.get_or_create(user=user)
        
        # Update KYC status
        kyc.status = 'APPROVED'
        kyc.approved_at = timezone.now()
        kyc.save()
        
        # Update user status
        user.is_kyc_approved = True
        user.status = 'APPROVED'
        user.save()
        
        # Send approval email
        try:
            send_kyc_approval_email(user, kyc)
        except Exception as e:
            print(f"Failed to send approval email: {e}")
        
        return kyc


class RejectKYCSerializer(serializers.Serializer):
    """Serializer for rejecting KYC of a retailer"""
    user_id = serializers.IntegerField()
    rejection_reason = serializers.CharField(required=True, max_length=500)
    
    def validate_user_id(self, value):
        """Validate that user exists and is a retailer"""
        try:
            user = User.objects.get(id=value)
            if user.role != 'RETAILER':
                raise serializers.ValidationError("User must be a retailer")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
    
    def validate_rejection_reason(self, value):
        """Validate rejection reason is not empty"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("Rejection reason cannot be empty")
        return value
    
    def save(self):
        """Reject the KYC for the user"""
        user_id = self.validated_data['user_id']
        rejection_reason = self.validated_data['rejection_reason']
        user = User.objects.get(id=user_id)
        
        # Get or create KYC
        kyc, _ = KYC.objects.get_or_create(user=user)
        
        # Update KYC status
        kyc.status = 'REJECTED'
        kyc.rejection_reason = rejection_reason
        kyc.save()
        
        # Update user status back to KYC_SUBMITTED so they can resubmit
        user.status = 'KYC_SUBMITTED'
        user.is_kyc_approved = False
        user.save()
        
        # Send rejection email
        try:
            send_kyc_rejection_email(user, kyc, rejection_reason)
        except Exception as e:
            print(f"Failed to send rejection email: {e}")
        
        return kyc


class DashboardStatisticsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics with week-over-week comparisons"""

    # ── KPI Cards ────────────────────────────────────────────────────────────────
    total_retailers = serializers.IntegerField(read_only=True)
    retailers_change_percentage = serializers.FloatField(read_only=True)
    retailers_change_text = serializers.CharField(read_only=True)

    pending_kyc = serializers.IntegerField(read_only=True)
    pending_kyc_change = serializers.IntegerField(read_only=True)
    pending_kyc_change_text = serializers.CharField(read_only=True)

    total_orders = serializers.IntegerField(read_only=True)
    orders_change_percentage = serializers.FloatField(read_only=True)
    orders_change_text = serializers.CharField(read_only=True)

    orders_in_dispatch = serializers.IntegerField(read_only=True)
    dispatch_change_percentage = serializers.FloatField(read_only=True)
    dispatch_change_text = serializers.CharField(read_only=True)

    top_selling_product = serializers.CharField(read_only=True)
    top_selling_change_percentage = serializers.FloatField(read_only=True)

    # ── Graph / Chart Data ───────────────────────────────────────────────────────
    daily_order_volume = serializers.ListField(child=serializers.DictField(), read_only=True)
    orders_by_status = serializers.ListField(child=serializers.DictField(), read_only=True)

    # ── NEW: Income & Expense breakdown ──────────────────────────────────────────
    # Each item in the list is a dict:
    #   { "category": str, "amount": float, "percentage": float }
    income_by_category = serializers.ListField(
        child=serializers.DictField(),
        read_only=True,
        default=list,
        help_text=(
            "Income aggregated by product category. "
            "Each entry: {category, amount, percentage}."
        ),
    )
    expense_by_category = serializers.ListField(
        child=serializers.DictField(),
        read_only=True,
        default=list,
        help_text=(
            "Approved credit-note expenses aggregated by product category (or reason). "
            "Each entry: {category, amount, percentage}."
        ),
    )


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    
    def validate_old_password(self, value):
        """Validate that old password is not empty"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("Old password cannot be empty")
        return value
    
    def validate_new_password(self, value):
        """Validate new password strength"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("New password cannot be empty")
        if len(value) < 6:
            raise serializers.ValidationError("New password must be at least 6 characters long")
        return value
    
    def validate(self, data):
        """Validate that new password is different from old password"""
        if data.get('old_password') == data.get('new_password'):
            raise serializers.ValidationError("New password must be different from old password")
        return data
    
    def save(self, user):
        """Change the password for the user"""
        old_password = self.validated_data['old_password']
        new_password = self.validated_data['new_password']
        
        # Verify old password
        if not user.check_password(old_password):
            raise serializers.ValidationError("Old password is incorrect")
        
        # Set new password
        user.set_password(new_password)
        user.save()
        return user


class SuperAdminProfileSerializer(serializers.ModelSerializer):
    """Serializer for super admin profile information"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_image', 'phone_number']
        read_only_fields = ['id']


class SuperAdminProfileImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading super admin profile image"""
    profile_image = serializers.ImageField(required=True)
    
    class Meta:
        model = User
        fields = ['profile_image']
    
    def validate_profile_image(self, value):
        """Validate profile image"""
        if not value:
            raise serializers.ValidationError("Image cannot be empty")
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size must not exceed 5MB")
        return value


class AddCategorySerializer(serializers.ModelSerializer):
    """Serializer for adding new brand/category"""
    class Meta:
        model = Category
        fields = ['name', 'icon', 'is_active']
        extra_kwargs = {
            'name': {'required': True},
            'icon': {'required': False},
            'is_active': {'required': False, 'default': True}
        }
    
    def validate_name(self, value):
        """Validate that category name is unique"""
        if Category.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Category with this name already exists")
        return value
    
    def validate_icon(self, value):
        """Validate icon file"""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Icon size must not exceed 5MB")
            
            # Check file extension
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            ext = value.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise serializers.ValidationError(f"Only {', '.join(allowed_extensions)} files are allowed")
        
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog entries"""

    class Meta:
        model = AuditLog
        fields = [
            'log_id',
            'action',
            'performed_by',
            'target_entity',
            'details',
            'category',
            'created_at',
        ]
        read_only_fields = fields
from rest_framework import serializers
from .models import AdminNotification

class AdminNotificationSerializer(serializers.ModelSerializer):
    """Serializer for admin notifications"""
    class Meta:
        model = AdminNotification
        fields = ['id', 'title', 'message', 'notification_type', 'priority', 'related_id', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'priority', 'related_id', 'created_at']        
