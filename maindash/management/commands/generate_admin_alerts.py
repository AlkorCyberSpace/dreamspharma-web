import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from dreamspharmaapp.models import ItemMaster, Stock, Offer
from maindash.models import AdminNotification
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate administrative alerts for low stock, expiring products, and expiring banners/offers'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting admin alert generation...'))
        
        self.check_low_stock()
        self.check_product_expiry()
        self.check_banner_offer_expiry()
        
        self.stdout.write(self.style.SUCCESS('Admin alert generation completed.'))

    def check_low_stock(self):
        """Check for items with 0 stock in Stock model"""
        # Focus on items with no stock recorded or stock = 0
        out_of_stock_items = Stock.objects.filter(total_bal_ls_qty__lte=0).select_related('item')
        
        for stock_entry in out_of_stock_items:
            # Avoid duplicate unread notifications
            exists = AdminNotification.objects.filter(
                notification_type='INVENTORY',
                related_id=f"stock_out_{stock_entry.item.item_code}",
                is_read=False
            ).exists()
            
            if not exists:
                AdminNotification.objects.create(
                    title="Out of Stock Alert",
                    message=f"Item '{stock_entry.item.item_name}' (Code: {stock_entry.item.item_code}) is out of stock in store {stock_entry.store_id}.",
                    notification_type='INVENTORY',
                    priority='HIGH',
                    related_id=f"stock_out_{stock_entry.item.item_code}"
                )
                self.stdout.write(f"Generated out of stock alert for {stock_entry.item.item_code}")

    def check_product_expiry(self):
        """Check for products expiring within the next 30 days"""
        expiry_threshold = timezone.now().date() + timezone.timedelta(days=30)
        expiring_products = ItemMaster.objects.filter(expiry_date__lte=expiry_threshold, expiry_date__gte=timezone.now().date())
        
        for item in expiring_products:
            exists = AdminNotification.objects.filter(
                notification_type='INVENTORY',
                related_id=f"expiry_{item.item_code}",
                is_read=False
            ).exists()
            
            if not exists:
                AdminNotification.objects.create(
                    title="Product Expiry Alert",
                    message=f"Item '{item.item_name}' (Batch: {item.batch_no}) is expiring on {item.expiry_date}.",
                    notification_type='INVENTORY',
                    priority='CRITICAL',
                    related_id=f"expiry_{item.item_code}"
                )
                self.stdout.write(f"Generated expiry alert for {item.item_code}")

    def check_banner_offer_expiry(self):
        """Check for banners/offers expiring within the next 24 hours"""
        expiry_threshold = timezone.now().date() + timezone.timedelta(days=1)
        expiring_offers = Offer.objects.filter(valid_to__lte=expiry_threshold, status=True)
        
        for offer in expiring_offers:
            exists = AdminNotification.objects.filter(
                notification_type='PROMO',
                related_id=f"offer_expiry_{offer.offer_id}",
                is_read=False
            ).exists()
            
            if not exists:
                AdminNotification.objects.create(
                    title="Banner/Offer Expiry Alert",
                    message=f"The banner/offer '{offer.title}' is set to expire on {offer.valid_to}.",
                    notification_type='PROMO',
                    priority='MEDIUM',
                    related_id=f"offer_expiry_{offer.offer_id}"
                )
                self.stdout.write(f"Generated offer expiry alert for {offer.offer_id}")
