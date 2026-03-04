from django.contrib import admin
from .models import Payment, PaymentLog, PaymentRefund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model"""
    list_display = [
        'payment_id',
        'customer_name',
        'amount',
        'status',
        'payment_method',
        'created_at',
        'payment_completed_at'
    ]
    list_filter = ['status', 'payment_method', 'currency', 'created_at']
    search_fields = ['payment_id', 'razorpay_order_id', 'customer_email', 'customer_phone']
    readonly_fields = [
        'payment_id',
        'razorpay_order_id',
        'razorpay_payment_id',
        'razorpay_signature',
        'created_at',
        'updated_at',
        'payment_completed_at'
    ]
    fieldsets = (
        ('Payment Identifiers', {
            'fields': ('payment_id', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature')
        }),
        ('Relations', {
            'fields': ('user', 'sales_order')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'payment_method', 'status')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_address')
        }),
        ('Error Details', {
            'fields': ('error_code', 'error_description'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'payment_completed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    """Admin interface for PaymentLog model"""
    list_display = ['id', 'payment', 'operation', 'success', 'created_at']
    list_filter = ['operation', 'success', 'created_at']
    search_fields = ['payment__payment_id']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Log Details', {
            'fields': ('payment', 'operation', 'created_at')
        }),
        ('Request Data', {
            'fields': ('request_data',)
        }),
        ('Response Data', {
            'fields': ('response_data', 'response_status_code')
        }),
        ('Status', {
            'fields': ('success', 'error_message')
        })
    )


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    """Admin interface for PaymentRefund model"""
    list_display = [
        'refund_id',
        'payment',
        'amount',
        'status',
        'created_at',
        'refund_completed_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['refund_id', 'razorpay_refund_id', 'payment__payment_id']
    readonly_fields = [
        'refund_id',
        'razorpay_refund_id',
        'created_at',
        'updated_at'
    ]
    fieldsets = (
        ('Refund Identifiers', {
            'fields': ('refund_id', 'razorpay_refund_id', 'payment')
        }),
        ('Refund Details', {
            'fields': ('amount', 'reason', 'status', 'initiated_by')
        }),
        ('Response Data', {
            'fields': ('response_notes',),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': ('error_code', 'error_description'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'refund_completed_at'),
            'classes': ('collapse',)
        })
    )
