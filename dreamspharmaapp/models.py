from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, FileExtensionValidator
import random
import string
import uuid

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('SUPERADMIN', 'Super Admin'),
        ('RETAILER', 'Retailer'),
    )
    
    STATUS_CHOICES = (
        ('PENDING_OTP_VERIFICATION', 'Pending OTP Verification'),
        ('REGISTERED', 'Registered'),
        ('KYC_SUBMITTED', 'KYC Submitted'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved (by SuperAdmin)'),
        ('LOGIN_ENABLED', 'Login Enabled'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='RETAILER')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='REGISTERED')
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True, validators=[
        RegexValidator(r'^\d{10,15}$', 'Phone number must be 10-15 digits')
    ])
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True, help_text="Profile picture for user")

    is_kyc_approved = models.BooleanField(default=False)
    first_login_otp_verified = models.BooleanField(default=False, help_text="Tracks if user has completed first login OTP verification")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False) | models.Q(phone_number__isnull=False),
                name='email_or_phone_required'
            )
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
       
        if self.is_superuser and self.role != 'SUPERADMIN':
            self.role = 'SUPERADMIN'
        elif not self.is_superuser and self.role == 'SUPERADMIN':
          
            self.role = 'RETAILER'
        super().save(*args, **kwargs)


class KYC(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='kyc')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
  
    shop_name = models.CharField(max_length=200)
    shop_address = models.TextField()
    shop_email = models.EmailField(blank=True, null=True)
    shop_phone = models.CharField(max_length=15, validators=[
        RegexValidator(r'^\d{10,15}$', 'Phone number must be 10-15 digits')
    ], blank=True, null=True)
    
  
    customer_address = models.TextField()
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text='Aadhaar number or PAN'
    )
    customer_photo = models.FileField(
        upload_to='kyc/customer_photos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Customer profile photo'
    )
    
    gst_number = models.CharField(max_length=20, unique=True)
    drug_license_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
  
    drug_license = models.FileField(
        upload_to='kyc/drug_licenses/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    id_proof = models.FileField(
        upload_to='kyc/id_proofs/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Aadhaar or other valid ID'
    )
    store_photo = models.FileField(
        upload_to='kyc/store_photos/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Front view of store - direct camera picture or document (PDF, JPG, JPEG, PNG)'
    )
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"KYC - {self.user.username} ({self.status})"


class OTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=4)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    OTP_EXPIRY_TIME = 60  # 60 seconds (1 minute)
    
    def is_expired(self):
        """Check if OTP has expired (5 minutes)"""
        from django.utils import timezone
        expiry_time = self.created_at + timezone.timedelta(seconds=self.OTP_EXPIRY_TIME)
        return timezone.now() > expiry_time
    
    def get_expiry_time_remaining(self):
        """Get remaining time in seconds before OTP expires"""
        from django.utils import timezone
        expiry_time = self.created_at + timezone.timedelta(seconds=self.OTP_EXPIRY_TIME)
        remaining = (expiry_time - timezone.now()).total_seconds()
        return max(0, int(remaining))
    
    def generate_otp(self):
        self.otp_code = ''.join(random.choices(string.digits, k=4))
        self.email = self.user.email
        self.is_verified = False
        self.save()
        return self.otp_code
    
    def __str__(self):
        return f"OTP - {self.email}"


# ==================== ERP INTEGRATION MODELS ====================

class APIToken(models.Model):
    """Store API tokens for external ERP system authentication"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    c2_code = models.CharField(max_length=20, unique=True, help_text="Unique C2 code for the company/branch")
    store_id = models.CharField(max_length=20, help_text="Store identifier")
    prod_code = models.CharField(max_length=20, default="02", help_text="Production code")
    api_key = models.CharField(max_length=255, unique=True, help_text="Encoded API key")
    security_key = models.CharField(max_length=255, help_text="Security key for validation")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"APIToken - {self.c2_code} ({self.store_id})"
    
    class Meta:
        ordering = ['-created_at']


class ItemMaster(models.Model):
    """Product/Item master data"""
    item_code = models.CharField(max_length=50, unique=True, primary_key=True)
    item_name = models.CharField(max_length=255)
    item_qty_per_box = models.IntegerField(default=1)
    batch_no = models.CharField(max_length=100)
    std_disc = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Standard discount")
    max_disc = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Maximum discount")
    expiry_date = models.DateField()
    mrp = models.DecimalField(max_digits=10, decimal_places=2, help_text="Maximum Retail Price")
    hsn_code = models.CharField(max_length=20, blank=True, null=True, help_text="HSN code for taxation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.item_code} - {self.item_name}"
    
    class Meta:
        ordering = ['item_code']


class Category(models.Model):
    """Product categories/brands with icons (e.g., Cipla, Mankind, Apollo Pharma)"""
    name = models.CharField(max_length=255, unique=True, help_text="Brand/Category name (e.g., Cipla, Mankind, Apollo Pharma)")
    icon = models.ImageField(upload_to='categories/icons/', blank=True, null=True, help_text="Brand logo/icon for UI display")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Categories (Brands)"


class ProductInfo(models.Model):
    """Product information and display"""
    item = models.OneToOneField(ItemMaster, on_delete=models.CASCADE, related_name='product_info', primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', help_text="Brand/Category assigned by superadmin (e.g., Cipla, Mankind)")
    type_label = models.CharField(max_length=100, blank=True, null=True, help_text="Product type label (e.g., 'Pain Relief', 'Antibiotic') shown under product name")
    subheading = models.CharField(max_length=255, blank=True, null=True, help_text="Product subheading/subtitle for mobile app")
    description = models.TextField(blank=True, null=True, help_text="Detailed product description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    
    def __str__(self):
        return f"{self.item.item_name}"
    
    class Meta:
        verbose_name_plural = "Product Info"
        ordering = ['-created_at']


class ProductImage(models.Model):
    """Multiple product images for items"""
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    image_order = models.PositiveIntegerField(default=1, help_text="Order of image display (1-3 for 3 main images)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image {self.image_order} - {self.product_info.item.item_name}"
    
    class Meta:
        ordering = ['image_order']
        unique_together = ('product_info', 'image_order')


class Stock(models.Model):
    """Stock information for items"""
    item = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='stocks')
    store_id = models.CharField(max_length=20)
    total_bal_ls_qty = models.IntegerField(help_text="Total balance quantity in loose units")
    pack_qty = models.IntegerField(help_text="Quantity per pack or total pack quantity")
    loose_qty = models.IntegerField(help_text="Loose quantity available")
    qty_box = models.IntegerField(help_text="Number of boxes available")
    cont_code = models.CharField(max_length=100, default="-", help_text="Content/composition code")
    cont_name = models.CharField(max_length=255, default="-", help_text="Content/composition name")
    last_modified_datetime = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Stock - {self.item.item_code} ({self.store_id})"
    
    class Meta:
        unique_together = ('item', 'store_id')
        ordering = ['-last_modified_datetime']


class GLCustomer(models.Model):
    """Global Local Customer Master"""
    c2_code = models.CharField(max_length=20)
    store_id = models.CharField(max_length=20)
    code = models.CharField(max_length=50, unique=True)
    ip_name = models.CharField(max_length=255)  # Customer name
    mail = models.EmailField()
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')])
    dl_no = models.CharField(max_length=100, blank=True, null=True, help_text="Driver's License number")
    city = models.CharField(max_length=255)
    ip_state = models.CharField(max_length=255)
    address1 = models.TextField(help_text="Primary address")
    address2 = models.TextField(blank=True, null=True, help_text="Secondary address")
    pincode = models.IntegerField()
    mobile = models.CharField(max_length=15, validators=[
        RegexValidator(r'^\d{10,15}$', 'Mobile number must be 10-15 digits')
    ])
    gst_no = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code} - {self.ip_name}"
    
    class Meta:
        unique_together = ('c2_code', 'code')
        ordering = ['-created_at']


class Address(models.Model):
    """Delivery addresses for users"""
    ADDRESS_TYPE_CHOICES = (
        ('HOME', 'Home'),
        ('OFFICE', 'Office'),
        ('OTHER', 'Others'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=200, help_text='Name of recipient')
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\d{10,15}$', 'Phone number must be 10-15 digits')]
    )
    pincode = models.CharField(max_length=10)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    locality = models.CharField(max_length=255, help_text='Locality/Area/Street')
    flat_building = models.CharField(max_length=255, blank=True, null=True, help_text='Flat no/Building Name')
    landmark = models.CharField(max_length=255, blank=True, null=True, help_text='Landmark (optional)')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='HOME')
    is_default = models.BooleanField(default=False, help_text='Set as default delivery address')
    is_active = models.BooleanField(default=True)
    
    # GPS Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text='Latitude from GPS/map')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text='Longitude from GPS/map')
    location_accuracy = models.IntegerField(blank=True, null=True, help_text='GPS accuracy in meters')
    is_gps_verified = models.BooleanField(default=False, help_text='Address confirmed via GPS coordinates')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        unique_together = ('user', 'phone', 'pincode', 'locality')  # Avoid duplicate exact addresses
    
    def __str__(self):
        return f"{self.name} - {self.address_type} ({self.city}, {self.state})"
    
    def get_full_address(self):
        """Return complete formatted address"""
        parts = [self.flat_building, self.locality, self.city, self.state, self.pincode]
        return ', '.join([p for p in parts if p])
    
    def save(self, *args, **kwargs):
        # Only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class SalesOrder(models.Model):
    """Sales Order document"""
    c2_code = models.CharField(max_length=20)
    store_id = models.CharField(max_length=20)
    order_id = models.CharField(max_length=100, unique=True)
    ip_no = models.CharField(max_length=100, help_text="Patient/Customer IP number")
    mobile_no = models.CharField(max_length=15)
    patient_name = models.CharField(max_length=255)
    patient_address = models.TextField()
    delivery_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='sales_orders', blank=True, null=True, help_text="Linked delivery address for this order")
    patient_email = models.EmailField()
    counter_sale = models.BooleanField(default=False)
    ord_date = models.DateField()
    ord_time = models.TimeField()
    user_id = models.CharField(max_length=100)  # User placing order
    cust_code = models.CharField(max_length=50, help_text="Customer/Account code")
    cust_name = models.CharField(max_length=255)
    dr_code = models.CharField(max_length=50, blank=True, null=True)
    dr_name = models.CharField(max_length=255, blank=True, null=True)
    dr_address = models.TextField(blank=True, null=True)
    dr_reg_no = models.CharField(max_length=50, blank=True, null=True)
    dr_office_code = models.CharField(max_length=50, default="-")
    dman_code = models.CharField(max_length=50, default="-")
    order_total = models.DecimalField(max_digits=12, decimal_places=2)
    order_disc_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ref_no = models.IntegerField(blank=True, null=True)
    remark = models.TextField(blank=True, null=True)
    urgent_flag = models.BooleanField(default=False)
    ord_conversion_flag = models.BooleanField(default=False)
    dc_conversion_flag = models.BooleanField(default=False)
    ord_ref_no = models.IntegerField(default=0)
    sys_name = models.CharField(max_length=100)
    sys_ip = models.GenericIPAddressField()
    sys_user = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Document details
    br_code = models.CharField(max_length=20)
    tran_year = models.CharField(max_length=4)
    tran_prefix = models.CharField(max_length=10)
    tran_srno = models.CharField(max_length=50)
    document_pk = models.CharField(max_length=100, unique=True, blank=True, null=True)
    bill_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"Order {self.order_id} - {self.patient_name}"
    
    class Meta:
        ordering = ['-ord_date', '-ord_time']


class SalesOrderItem(models.Model):
    """Line items in a sales order"""
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    item_seq = models.IntegerField()
    item_code = models.CharField(max_length=50)
    item_name = models.CharField(max_length=255, blank=True, null=True)
    batch_no = models.CharField(max_length=100, blank=True, null=True, help_text='Medicine batch number for recall tracking')
    expiry_date = models.DateField(blank=True, null=True, help_text='Medicine expiry date')
    total_loose_qty = models.IntegerField()
    total_loose_sch_qty = models.IntegerField(default=0)
    service_qty = models.IntegerField(default=0)
    sale_rate = models.DecimalField(max_digits=10, decimal_places=3)
    disc_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sch_disc_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    item_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.item_code} - Batch: {self.batch_no} - Qty: {self.total_loose_qty}"
    
    class Meta:
        ordering = ['item_seq']
        unique_together = ('sales_order', 'item_seq')


class Invoice(models.Model):
    """Invoice document linked to sales order"""
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='invoices')
    doc_no = models.CharField(max_length=100, unique=True)
    doc_date = models.DateField()
    doc_status = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100)
    doc_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    doc_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Invoice {self.doc_no}"
    
    class Meta:
        ordering = ['-doc_date']


class InvoiceDetail(models.Model):
    """Line items in invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='details')
    product_id = models.CharField(max_length=50)
    product_name = models.CharField(max_length=255)
    hsn_code = models.CharField(max_length=20)
    qty_per_box = models.CharField(max_length=20)
    batch = models.CharField(max_length=100)
    qty = models.DecimalField(max_digits=10, decimal_places=3)
    expiry_date = models.DateField()
    mrp = models.DecimalField(max_digits=10, decimal_places=3)
    sale_rate = models.DecimalField(max_digits=10, decimal_places=3)
    disc_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    disc_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    item_total = models.DecimalField(max_digits=12, decimal_places=2)
    cgst_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    cgst_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sgst_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sgst_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    igst_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    igst_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cess_per = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    cess_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product_name} (Invoice: {self.invoice.doc_no})"
    
    class Meta:
        ordering = ['id']


# ==================== CART & WISHLIST MODELS ====================

class Cart(models.Model):
    """Shopping cart for a user"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fee configurations (can be adjusted via admin)
    convenience_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=29.00)
    
    def get_bag_total(self):
        """Calculate total MRP of all items"""
        total = sum(item.get_item_total_mrp() for item in self.items.all())
        return round(total, 2)
    
    def get_bag_savings(self):
        """Calculate total savings from discounts"""
        savings = sum(item.get_item_savings() for item in self.items.all())
        return round(savings, 2)
    
    def get_subtotal(self):
        """Calculate subtotal after discounts"""
        subtotal = sum(item.get_item_total_discounted() for item in self.items.all())
        return round(subtotal, 2)
    
    def get_grand_total(self):
        """Calculate grand total including fees"""
        subtotal = self.get_subtotal()
        total = subtotal + float(self.convenience_fee) + float(self.delivery_fee) + float(self.platform_fee)
        return round(total, 2)
    
    def get_item_count(self):
        """Get total number of items in cart"""
        return self.items.count()
    
    def __str__(self):
        return f"Cart - {self.user.username}"


class CartItem(models.Model):
    """Individual item in a cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    batch_no = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_item_total_mrp(self):
        """Calculate total MRP for this item"""
        return float(self.item.mrp) * self.quantity
    
    def get_discount_percentage(self):
        """Get discount percentage for this item"""
        return float(self.item.std_disc)
    
    def get_discounted_price(self):
        """Calculate price per unit after discount"""
        mrp = float(self.item.mrp)
        discount = float(self.item.std_disc)
        discounted_price = mrp * (1 - discount / 100)
        return round(discounted_price, 2)
    
    def get_item_total_discounted(self):
        """Calculate total price after discount"""
        return round(self.get_discounted_price() * self.quantity, 2)
    
    def get_item_savings(self):
        """Calculate savings for this item"""
        return round(self.get_item_total_mrp() - self.get_item_total_discounted(), 2)
    
    class Meta:
        unique_together = ('cart', 'item')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.item.item_name} x {self.quantity}"


class Wishlist(models.Model):
    """Wishlist for a user"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_item_count(self):
        """Get total number of items in wishlist"""
        return self.items.count()
    
    def __str__(self):
        return f"Wishlist - {self.user.username}"


class WishlistItem(models.Model):
    """Individual item in a wishlist"""
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='wishlist_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('wishlist', 'item')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.item.item_name} x {self.quantity} (Wishlist: {self.wishlist.user.username})"
