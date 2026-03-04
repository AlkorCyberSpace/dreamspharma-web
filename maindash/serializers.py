from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from dreamspharmaapp.models import KYC

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
        
        return kyc

