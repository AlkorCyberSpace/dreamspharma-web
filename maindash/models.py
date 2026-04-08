from django.db import models
from django.conf import settings
from django.utils import timezone


class AuditLog(models.Model):
    """
    Audit trail for all critical admin actions in the system.
    Tracks: who did what, when, on which object, and categorizes it.
    """

    CATEGORY_CHOICES = (
        ('KYC', 'KYC'),
        ('ERP', 'ERP'),
        ('Refund', 'Refund'),
        ('System', 'System'),
        ('Order', 'Order'),
        ('Category', 'Category'),
        ('Offer', 'Offer'),
        ('Product', 'Product'),
    )

    # Auto-generated log ID like "AUD-001"
    log_id = models.CharField(max_length=20, unique=True, editable=False)

    # Action taken e.g. "KYC Approved", "Order Synced"
    action = models.CharField(max_length=255)

    # Who performed the action ("Admin User", "System", "Finance Admin")
    performed_by = models.CharField(max_length=255, default='System')

    # The user who performed the action (linked, nullable for system actions)
    performed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )

    # The target entity e.g. "MedPlus Pharmacy (RET001)", "REF-001", "ORD-2026-003"
    target_entity = models.CharField(max_length=500)

    # Details of the action e.g. "All documents verified and approved"
    details = models.TextField()

    # Category: KYC, ERP, Refund, System, Order, Category, Offer, Product
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='System')

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def save(self, *args, **kwargs):
        """Auto-generate LOG ID like AUD-001 on first save."""
        if not self.log_id:
            # Get last inserted log to determine next ID number
            last = AuditLog.objects.order_by('-id').first()
            if last and last.log_id:
                try:
                    last_num = int(last.log_id.split('-')[1])
                    next_num = last_num + 1
                except (IndexError, ValueError):
                    next_num = 1
            else:
                next_num = 1
            self.log_id = f"AUD-{str(next_num).zfill(3)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.log_id} | {self.action} | {self.performed_by} | {self.category}"

class AdminNotification(models.Model):
    TYPE_CHOICES = (
        ('USER', 'User/KYC'),
        ('ORDER', 'Order'),
        ('INVENTORY', 'Inventory/Stock'),
        ('PAYMENT', 'Payment'),
        ('PROMO', 'Promotion/Banner'),
        ('SYSTEM', 'System/Sync'),
    )

    PRIORITY_CHOICES = (
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    priority = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default='MEDIUM')
    related_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID of the related object (e.g., SalesOrder order_id, User ID)")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'admin_notifications'
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'

    def __str__(self):
        return f"[{self.priority}] {self.title} - Read: {self.is_read}"