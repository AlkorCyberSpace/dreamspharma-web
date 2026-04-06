from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from dreamspharmaapp.models import KYC, SalesOrder
from .models import AdminNotification
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

# ==================== USER & KYC NOTIFICATIONS ====================

@receiver(post_save, sender=User)
def notification_new_retailer(sender, instance, created, **kwargs):
    """Trigger notification when a new retailer registers"""
    if created and getattr(instance, 'role', '') == 'RETAILER':
        AdminNotification.objects.create(
            title="New Retailer Registration",
            message=f"A new retailer '{instance.username}' ({instance.email}) has registered and is pending KYC review.",
            notification_type='USER',
            priority='MEDIUM',
            related_id=str(instance.id)
        )

@receiver(post_save, sender=KYC)
def notification_kyc_status(sender, instance, created, **kwargs):
    """Trigger notification when KYC is submitted or re-submitted"""
    if instance.status == 'PENDING':
        # Avoid duplicate unread notifications for the same KYC
        exists = AdminNotification.objects.filter(
            notification_type='USER',
            related_id=f"kyc_{instance.id}",
            is_read=False,
            title="KYC Pending Review"
        ).exists()

        if not exists:
            AdminNotification.objects.create(
                title="KYC Pending Review",
                message=f"Retailer '{instance.user.username}' ({instance.user.email}) has uploaded KYC documents. Shop: {instance.shop_name}. Please review.",
                notification_type='USER',
                priority='HIGH',
                related_id=f"kyc_{instance.id}"
            )

# ==================== ORDER NOTIFICATIONS ====================

@receiver(post_save, sender=SalesOrder)
def notification_high_value_order(sender, instance, created, **kwargs):
    """Trigger notification for orders above ₹50,000"""
    if created and instance.order_total and float(instance.order_total) > 50000:
        AdminNotification.objects.create(
            title="High Value Order Received",
            message=f"Order '{instance.order_id}' placed by {instance.patient_name} with a total of ₹{instance.order_total:,.2f}. Please verify.",
            notification_type='ORDER',
            priority='HIGH',
            related_id=str(instance.order_id)
        )

# ==================== PAYMENT NOTIFICATIONS ====================
# Note: Imported lazily to prevent circular dependencies if apps load out of order

def _setup_payment_signals():
    try:
        from payment.models import Payment, PaymentRefund

        @receiver(post_save, sender=Payment)
        def notification_payment_failure(sender, instance, **kwargs):
            if getattr(instance, 'status', '') == 'FAILED' and getattr(instance, 'payment_method', '') == 'RAZORPAY':
                exists = AdminNotification.objects.filter(
                    notification_type='PAYMENT',
                    related_id=f"payment_{instance.payment_id}",
                    is_read=False
                ).exists()

                if not exists:
                    order_info = f" for order {instance.sales_order.order_id}" if instance.sales_order else ""
                    AdminNotification.objects.create(
                        title="Payment Failed (Razorpay)",
                        message=f"Razorpay payment{order_info} of ₹{instance.amount:,.2f} by {instance.customer_name} has failed. Error: {instance.error_description or 'Unknown'}.",
                        notification_type='PAYMENT',
                        priority='HIGH',
                        related_id=f"payment_{instance.payment_id}"
                    )

        @receiver(post_save, sender=PaymentRefund)
        def notification_refund_request(sender, instance, created, **kwargs):
            if created:
                order_info = f" for order {instance.payment.sales_order.order_id}" if instance.payment and instance.payment.sales_order else ""
                AdminNotification.objects.create(
                    title="Refund Request",
                    message=f"A {instance.refund_type.lower()} refund of ₹{instance.amount:,.2f}{order_info} has been initiated. Reason: {instance.reason}.",
                    notification_type='PAYMENT',
                    priority='HIGH',
                    related_id=f"refund_{instance.refund_id}"
                )
    except ImportError:
        pass

# Call setup when module loads
_setup_payment_signals()