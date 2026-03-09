from django.contrib import admin
from django.utils.html import format_html
from .models import CustomUser, KYC, OTP


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'phone_number', 'role_badge', 'is_kyc_approved', 'created_at']
    list_filter = ['role', 'is_kyc_approved', 'created_at']
    search_fields = ['username', 'email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'email', 'phone_number', 'first_name', 'password')
        }),
        ('Role & Status', {
            'fields': ('role', 'is_kyc_approved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def role_badge(self, obj):
        colors = {
            'SUPERADMIN': '#ff6b6b',
            'RETAILER': '#4ecdc4',
        }
        color = colors.get(obj.role, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'


@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'customer_name', 'shop_name', 'status_badge', 'submitted_at', 'approved_at']
    list_filter = ['status', 'submitted_at', 'approved_at']
    search_fields = ['user__username', 'user__email', 'customer_name', 'customer_id', 'shop_name', 'shop_email', 'shop_phone', 'gst_number', 'drug_license_number']
    readonly_fields = ['submitted_at', 'approved_at', 'user', 'drug_license_preview', 'id_proof_preview', 'store_photo_preview']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_id', 'customer_address')
        }),
        ('Shop Details', {
            'fields': ('shop_name', 'shop_address', 'shop_email', 'shop_phone')
        }),
        ('Business Documents', {
            'fields': ('gst_number', 'drug_license_number', 'drug_license', 'drug_license_preview', 'id_proof', 'id_proof_preview', 'store_photo', 'store_photo_preview')
        }),
        ('Status', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_kyc', 'reject_kyc']
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'User'
    
    def customer_name(self, obj):
        return obj.customer_name if obj.customer_name else '-'
    customer_name.short_description = 'Customer Name'
    
    def drug_license_preview(self, obj):
        if obj.drug_license:
            return format_html(
                '<a href="{}" target="_blank">View Drug License</a>',
                obj.drug_license.url
            )
        return 'No file'
    drug_license_preview.short_description = 'Drug License Preview'
    
    def id_proof_preview(self, obj):
        if obj.id_proof:
            return format_html(
                '<a href="{}" target="_blank">View ID Proof</a>',
                obj.id_proof.url
            )
        return 'No file'
    id_proof_preview.short_description = 'ID Proof Preview'
    
    def store_photo_preview(self, obj):
        if obj.store_photo:
            return format_html(
                '<img src="{}" width="200" height="auto" />',
                obj.store_photo.url
            )
        return 'No image'
    store_photo_preview.short_description = 'Store Photo Preview'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#f39c12',
            'APPROVED': '#27ae60',
            'REJECTED': '#e74c3c',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def approve_kyc(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for kyc in queryset.filter(status='PENDING'):
            kyc.status = 'APPROVED'
            kyc.approved_at = timezone.now()
            kyc.user.is_kyc_approved = True
            kyc.user.save()
            kyc.save()
            updated += 1
        self.message_user(request, f'{updated} KYC(s) approved successfully.')
    approve_kyc.short_description = 'Approve selected KYCs'
    
    def reject_kyc(self, request, queryset):
        for kyc in queryset.filter(status='PENDING'):
            kyc.status = 'REJECTED'
            kyc.save()
        self.message_user(request, f'{queryset.count()} KYC(s) rejected.')
    reject_kyc.short_description = 'Reject selected KYCs'


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'email', 'otp_code', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'email']
    readonly_fields = ['created_at', 'user', 'otp_code', 'email']
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'User'


# ==================== PRODUCT INFO ADMIN ====================

from .models import ProductInfo, ProductImage


class ProductImageInline(admin.TabularInline):
    """Inline admin for ProductImage"""
    model = ProductImage
    extra = 1
    fields = ['image', 'image_order']
    ordering = ['image_order']


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ['item_code', 'item_name', 'subheading_preview', 'image_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['item__item_code', 'item__item_name', 'subheading', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProductImageInline]
    fieldsets = (
        ('Product', {
            'fields': ('item',)
        }),
        ('Details', {
            'fields': ('subheading', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def item_code(self, obj):
        return obj.item.item_code
    item_code.short_description = "Item Code"
    
    def item_name(self, obj):
        return obj.item.item_name
    item_name.short_description = "Item Name"
    
    def subheading_preview(self, obj):
        return obj.subheading if obj.subheading else "No subheading"
    subheading_preview.short_description = "Subheading"
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = "Images Count"

