from django.db import models
from django.utils import timezone

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
