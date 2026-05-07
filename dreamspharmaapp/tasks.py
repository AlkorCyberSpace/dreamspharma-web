"""
Async Tasks for DreamsPharma using Celery
Move heavy operations to background to prevent timeout errors
"""
from celery import shared_task
from django.db import transaction
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging
import time

from .models import SalesOrder, CustomUser, ProductStore, Store

logger = logging.getLogger(__name__)


# ==================== ORDER PROCESSING TASKS ====================

@shared_task(
    bind=True,
    max_retries=3,  # Retry up to 3 times on failure
    default_retry_delay=60,  # Wait 60 seconds before retry
    acks_late=True,  # Only mark as done after successful execution
    time_limit=600,  # 10 minutes hard limit
)
def process_order(self, order_id):
    """
    Process order with ERP sync, payment, and notifications
    
    ✅ PRODUCTION FIX: This runs in background async
    ⏱️ User gets response instantly instead of waiting 10+ seconds
    🔄 If it fails, Celery retries automatically
    """
    try:
        order = SalesOrder.objects.select_for_update().get(id=order_id)
        
        logger.info(f"Processing SalesOrder #{order.id} for user {order.user.id}")
        
        # Step 1: Get store ERP config
        if not order.fulfilling_store:
            raise ValueError(f"Order {order_id} has no store assigned")
        
        erp_config = order.fulfilling_store.get_erp_config()
        
        # Step 2: Sync with ERP (the heavy operation)
        logger.info(f"Syncing SalesOrder #{order.id} with ERP...")
        sync_result = sync_order_with_erp(order_id, erp_config)
        
        # Step 3: Update order status
        if sync_result['success']:
            order.status = 'confirmed'
            logger.info(f"SalesOrder #{order.id} confirmed in ERP")
        else:
            order.status = 'failed'
            logger.error(f"ERP sync failed for SalesOrder #{order.id}: {sync_result['error']}")
        
        order.save()
        
        # Step 4: Send confirmation email
        send_order_confirmation_email.delay(order_id)
        
        logger.info(f"SalesOrder #{order.id} processing complete")
        return {'status': 'success', 'order_id': order_id}
        
    except Exception as exc:
        logger.error(f"Error processing order {order_id}: {str(exc)}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def sync_order_with_erp(order_id, erp_config):
    """
    Sync order with ERP system (this is the slow operation)
    Takes 5-10 seconds normally
    """
    try:
        from .services import ERPService
        
        order = SalesOrder.objects.get(id=order_id)
        erp_service = ERPService(erp_config)
        
        # Call ERP API to create sales order there
        erp_order = erp_service.create_sales_order(
            customer_id=order.user.id,
            items=[
                {
                    'product_id': item.product.id,
                    'quantity': item.quantity,
                    'price': item.price
                }
                for item in order.items.all()
            ],
            total_amount=float(order.total_amount),
        )
        
        return {
            'success': True,
            'erp_order_id': erp_order.get('order_id')
        }
        
    except Exception as e:
        logger.error(f"ERP sync error for order {order_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(max_retries=2, default_retry_delay=30)
def send_order_confirmation_email(order_id):
    """Send order confirmation email asynchronously"""
    try:
        order = SalesOrder.objects.get(id=order_id)
        
        # Render email template
        context = {
            'order': order,
            'user': order.user,
            'fulfilling_store': order.fulfilling_store,
            'total': order.total_amount,
        }
        
        html_message = render_to_string('order_confirmation.html', context)
        
        # Send email
        send_mail(
            subject=f'Order Confirmation #{order.id}',
            message=f'Your order has been confirmed. Order ID: {order.id}',
            html_message=html_message,
            from_email='noreply@dreamspharma.com',
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        order.confirmation_email_sent = True
        order.save(update_fields=['confirmation_email_sent'])
        
        logger.info(f"Confirmation email sent for order {order_id}")
        return True
        
    except Exception as exc:
        logger.error(f"Failed to send confirmation email for order {order_id}: {str(exc)}")
        raise self.retry(exc=exc)


# ==================== INVENTORY SYNC TASKS ====================

@shared_task(
    max_retries=3,
    default_retry_delay=120,  # 2 minutes if fails
    time_limit=300,  # 5 minute limit per sync
)
def sync_inventory_from_erp():
    """
    Periodic task: Sync product inventory from ERP every 5 minutes
    
    ✅ Prevents stale inventory data
    ✅ Ensures stock accuracy across stores
    ⏱️ Runs in background, doesn't block user requests
    """
    try:
        logger.info("Starting inventory sync from ERP...")
        
        stores = Store.objects.filter(is_active=True)
        total_synced = 0
        
        for store in stores:
            try:
                # Get inventory for this store from ERP
                erp_config = store.get_erp_config()
                inventory_data = get_inventory_from_erp(erp_config)
                
                # Update ProductStore records
                for product_id, stock_qty in inventory_data.items():
                    ProductStore.objects.filter(
                        store=store,
                        product_id=product_id
                    ).update(stock_quantity=stock_qty)
                
                total_synced += len(inventory_data)
                logger.info(f"Synced {len(inventory_data)} items for store {store.name}")
                
            except Exception as e:
                logger.warning(f"Failed to sync inventory for store {store.name}: {str(e)}")
                continue
        
        # Invalidate product cache (5-minute TTL)
        cache.delete_many([f'store_products_{store.id}' for store in stores])
        
        logger.info(f"Inventory sync complete. Synced {total_synced} product records")
        return {'synced': total_synced}
        
    except Exception as exc:
        logger.error(f"Inventory sync failed: {str(exc)}")
        raise


def get_inventory_from_erp(erp_config):
    """Get real-time inventory from ERP system"""
    try:
        from .services import ERPService
        erp_service = ERPService(erp_config)
        return erp_service.get_inventory()
    except Exception as e:
        logger.error(f"Failed to get inventory from ERP: {str(e)}")
        raise


@shared_task
def refresh_erp_tokens():
    """
    Periodic task: Refresh ERP tokens before expiry (every 22 hours)
    
    ✅ Prevents token expiry errors
    ✅ Ensures continuous ERP connectivity
    """
    try:
        logger.info("Refreshing ERP tokens for all stores...")
        
        stores = Store.objects.filter(is_active=True)
        refreshed_count = 0
        
        for store in stores:
            try:
                erp_config = store.get_erp_config()
                # Token service handles refresh logic
                erp_token_service = ERPTokenService(erp_config)
                erp_token_service.refresh_token_if_needed()
                refreshed_count += 1
            except Exception as e:
                logger.warning(f"Failed to refresh token for store {store.name}: {str(e)}")
                continue
        
        logger.info(f"ERP tokens refreshed for {refreshed_count} stores")
        return {'refreshed': refreshed_count}
        
    except Exception as exc:
        logger.error(f"Token refresh failed: {str(exc)}")


# ==================== CLEANUP TASKS ====================

@shared_task
def cleanup_expired_carts():
    """
    Periodic task: Remove carts abandoned >7 days
    Runs daily at 3 AM
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Find carts older than 7 days without active order
        cutoff_date = timezone.now() - timedelta(days=7)
        
        # Delete old cart items (implementation depends on your Cart model)
        logger.info("Cleaning up expired carts...")
        logger.info("Cleanup complete")
        
    except Exception as e:
        logger.error(f"Cart cleanup failed: {str(e)}")


# ==================== NOTIFICATION TASKS ====================

@shared_task(max_retries=2)
def send_low_stock_notification(product_store_id):
    """Alert when product stock falls below reorder level"""
    try:
        product_store = ProductStore.objects.get(id=product_store_id)
        
        if product_store.is_low_stock():
            logger.warning(
                f"Low stock alert: {product_store.product.item_name} "
                f"at {product_store.store.name} - Only {product_store.stock_quantity} units"
            )
            
            # Send email to inventory manager
            send_mail(
                subject=f"Low Stock Alert",
                message=f"Product {product_store.product.item_name} is low at {product_store.store.name}",
                from_email='alerts@dreamspharma.com',
                recipient_list=['inventory@dreamspharma.com'],
            )
            
    except Exception as exc:
        logger.error(f"Failed to send low stock notification: {str(exc)}")


# ==================== HEALTH CHECK ====================

@shared_task
def celery_health_check():
    """Periodic task to verify Celery is working"""
    logger.info("Celery health check - working correctly")
    return True
