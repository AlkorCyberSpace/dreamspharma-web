from django.db import models
from django.contrib.auth import get_user_model
from dreamspharmaapp.models import SalesOrder
import uuid

User = get_user_model()


class Payment(models.Model):
    """Payment transaction model for Razorpay integration"""
    
    PAYMENT_STATUS_CHOICES = (
        ('INITIATED', 'Payment Initiated'),
        ('PENDING', 'Payment Pending'),
        ('SUCCESS', 'Payment Successful'),
        ('FAILED', 'Payment Failed'),
        ('CANCELLED', 'Payment Cancelled'),
        ('REFUNDED', 'Payment Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('RAZORPAY', 'Razorpay'),
        ('NETBANKING', 'Net Banking'),
        ('WALLET', 'Wallet'),
        ('UPI', 'UPI'),
        ('COD', 'Cash on Delivery'),
    )
    
    # Identifiers
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    # Relations
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='payments', blank=True, null=True)
    
    # Payment Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='RAZORPAY')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='INITIATED')
    
    # Transaction Details
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField(blank=True, null=True)
    
    # Response Data
    error_code = models.CharField(max_length=100, blank=True, null=True)
    error_description = models.TextField(blank=True, null=True)
    
    # Security & Tracking
    customer_ip = models.GenericIPAddressField(blank=True, null=True, help_text="Customer IP address at time of payment")
    customer_user_agent = models.CharField(max_length=500, blank=True, null=True, help_text="User browser/device info")
    retry_count = models.IntegerField(default=0, help_text="Number of payment attempts")
    merchant_reference_id = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Merchant reference for settlement")
    
    # Razorpay Specific
    razorpay_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Razorpay processing fee")
    razorpay_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Tax on processing fee")
    
    # Settlement
    settlement_id = models.CharField(max_length=100, blank=True, null=True, help_text="Razorpay settlement ID")
    settlement_date = models.DateTimeField(blank=True, null=True, help_text="Payment settlement date")
    is_settled = models.BooleanField(default=False, help_text="Is payment settled in merchant account")
    
    # COD Specific
    cod_collected = models.BooleanField(default=False, help_text="For COD orders, marks if cash has been collected")
    cod_collected_at = models.DateTimeField(blank=True, null=True, help_text="Timestamp when COD payment was collected")
    cod_collected_by = models.CharField(max_length=255, blank=True, null=True, help_text="Name/ID of person who collected COD")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_completed_at = models.DateTimeField(blank=True, null=True)
    expiry_at = models.DateTimeField(blank=True, null=True, help_text="Razorpay order expiry time (15 mins)")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['razorpay_order_id']),
            models.Index(fields=['razorpay_payment_id']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['merchant_reference_id']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['is_settled', '-settlement_date']),
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['cod_collected', '-cod_collected_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.get_status_display()} - ₹{self.amount}"


class PaymentLog(models.Model):
    """Log for payment API calls and responses"""
    
    OPERATION_CHOICES = (
        ('CREATE_ORDER', 'Create Order'),
        ('VERIFY_PAYMENT', 'Verify Payment'),
        ('FETCH_ORDER', 'Fetch Order'),
        ('REFUND', 'Refund'),
        ('WEBHOOK', 'Webhook'),
    )
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    operation = models.CharField(max_length=50, choices=OPERATION_CHOICES)
    
    # Request Data
    request_data = models.JSONField(default=dict)
    
    # Response Data
    response_data = models.JSONField(default=dict)
    response_status_code = models.IntegerField(blank=True, null=True)
    
    # Status
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Log'
        verbose_name_plural = 'Payment Logs'
    
    def __str__(self):
        payment_id = self.payment.payment_id if self.payment else 'Unknown'
        return f"Log {self.id} - {self.get_operation_display()} - {payment_id}"


class PaymentRefund(models.Model):
    """Refund management for payments"""
    
    REFUND_STATUS_CHOICES = (
        ('INITIATED', 'Refund Initiated'),
        ('PENDING', 'Refund Pending'),
        ('SUCCESS', 'Refund Successful'),
        ('FAILED', 'Refund Failed'),
        ('REJECTED', 'Refund Rejected'),
    )
    
    refund_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    razorpay_refund_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='INITIATED')
    
    # Refund Type
    refund_type = models.CharField(
        max_length=20,
        choices=[('FULL', 'Full Refund'), ('PARTIAL', 'Partial Refund')],
        default='FULL',
        help_text="Full or partial refund"
    )
    
    request_notes = models.TextField(blank=True, null=True)
    response_notes = models.JSONField(default=dict)
    
    error_code = models.CharField(max_length=100, blank=True, null=True)
    error_description = models.TextField(blank=True, null=True)
    
    initiated_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    refund_completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund {self.refund_id} - {self.get_status_display()} - ₹{self.amount}"