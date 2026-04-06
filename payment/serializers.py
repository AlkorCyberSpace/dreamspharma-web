from rest_framework import serializers
from .models import Payment, PaymentLog, PaymentRefund


class PaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLog
        fields = [
            'id', 'payment', 'operation', 'request_data',
            'response_data', 'response_status_code', 'success',
            'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaymentRefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRefund
        fields = [
            'id', 'refund_id', 'payment', 'amount', 'reason',
            'status', 'refund_type', 'razorpay_refund_id', 'error_code',
            'error_description', 'initiated_by', 'created_at',
            'updated_at', 'refund_completed_at'
        ]
        read_only_fields = [
            'id', 'refund_id', 'razorpay_refund_id',
            'created_at', 'updated_at'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    logs = PaymentLogSerializer(many=True, read_only=True)
    refunds = PaymentRefundSerializer(many=True, read_only=True)
    order_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'razorpay_order_id', 'razorpay_payment_id',
            'user', 'order_id', 'amount', 'currency', 'payment_method',
            'status', 'customer_name', 'customer_email', 'customer_phone',
            'customer_address', 'customer_ip', 'customer_user_agent',
            'retry_count', 'merchant_reference_id', 'error_code', 'error_description',
            'razorpay_fee', 'razorpay_tax', 'settlement_id', 'settlement_date', 'is_settled',
            'cod_collected', 'cod_collected_at', 'cod_collected_by',
            'created_at', 'updated_at', 'payment_completed_at', 'expiry_at',
            'logs', 'refunds'
        ]
        read_only_fields = [
            'id', 'payment_id', 'razorpay_order_id', 'razorpay_payment_id',
            'razorpay_signature', 'status', 'created_at', 'updated_at',
            'payment_completed_at', 'logs', 'refunds', 'merchant_reference_id'
        ]
    
    def get_order_id(self, obj):
        if obj.sales_order:
            return obj.sales_order.order_id
        return None