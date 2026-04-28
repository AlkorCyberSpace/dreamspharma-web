import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import requests
from datetime import datetime, timedelta
import time

def initialize_firebase():
    """Initialize Firebase Admin SDK on first use"""
    if not firebase_admin._apps:
        try:
            cred_path = os.path.join(settings.BASE_DIR, 'firebase_credentials.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin SDK initialized successfully.")
            else:
                print(f"Warning: Firebase credentials file not found at {cred_path}")
        except Exception as e:
            print(f"Failed to initialize Firebase: {e}")

# Initialize right away when imported
initialize_firebase()

logger = logging.getLogger(__name__)

def send_push_notification(user, title, body, data=None):
    """
    Send push notification to all active devices of a user
    """
    try:
        if not firebase_admin._apps:
            logger = logging.getLogger(__name__)
            logger.warning("Firebase is not initialized. Cannot send notification.")
            return {"error": "Firebase not initialized"}
            
        if data is None:
            data = {}
        
        # Needs to be string dict for Firebase data payload
        data_payload = {str(k): str(v) for k, v in data.items()}
        
        # Refresh user to get latest related objects
        from .models import CustomUser
        user = CustomUser.objects.get(pk=user.pk)
        
        devices = user.fcm_devices.filter(is_active=True)
        if not devices.exists():
            return {"success": 0, "failure": 0}
        
        tokens = [device.registration_id for device in devices if device.registration_id]
        
        if not tokens:
            return {"success": 0, "failure": 0}
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data_payload,
            tokens=tokens,
        )
        
        response = messaging.send_each_for_multicast(message)
        
        # Handle failed tokens (e.g. unregister them)
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    failed_tokens.append(tokens[idx])
            
            # Deactivate failed tokens so we don't try again
            if failed_tokens:
                user.fcm_devices.filter(registration_id__in=failed_tokens).update(is_active=False)
                
        return {
            "success": response.success_count,
            "failure": response.failure_count
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error sending push notification: {e}")
        return {"error": str(e)}


# ==================== INVOICE SYNC FROM ERP ====================

def sync_invoice_from_erp(order_id, c2_code, store_id, max_retries=10):
    """
    Fetch invoice details from ERP server after sales order creation
    
    Workflow:
    1. Sales order created -> This function called in background thread
    2. Wait for ERP to process order and generate invoices (typically 2-5 seconds)
    3. Poll ERP's get_orderstatus endpoint to retrieve invoices
    4. Store invoices and line items in local database
    
    Args:
        order_id: Order ID created in sales order
        c2_code: Customer C2 code
        store_id: Store identifier
        max_retries: Maximum retry attempts (default 10, ~60+ seconds total with exponential backoff)
    """
    try:
        from .models import SalesOrder, Invoice, InvoiceDetail
        from .erp_token_service import get_cached_erp_token
        
        # Get token for API authentication
        api_key = get_cached_erp_token()
        if not api_key:
            logger.error(f"[INVOICE_SYNC] Failed to get ERP token for order {order_id}")
            return False
        
        erp_base_url = settings.ERP_BASE_URL
        
        # Poll ERP for invoices (with retry logic for eventual consistency)
        retry_count = 0
        invoices_data = None
        
        while retry_count < max_retries:
            try:
                # Build request
                url = f"{erp_base_url}/ws_c2_services_get_orderstatus"
                payload = {
                    "c2Code": c2_code,
                    "storeId": store_id,
                    "prodCode": settings.ERP_PROD_CODE,
                    "apiKey": api_key,
                    "orderId": order_id
                }
                
                logger.info(f"[INVOICE_SYNC] Attempting to fetch invoices | Order: {order_id} | Attempt: {retry_count + 1}/{max_retries}")
                logger.debug(f"[INVOICE_SYNC] Request details | URL: {url} | Payload: {payload}")
                
                response = requests.get(url, params=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"[INVOICE_SYNC] ERP Response: {data}")
                    
                    if data.get('code') == '200':
                        invoices_data = data.get('invoices', [])
                        
                        if invoices_data:
                            logger.info(f"[INVOICE_SYNC] [SUCCESS] Found {len(invoices_data)} invoice(s) for order {order_id}")
                            break
                        else:
                            logger.info(f"[INVOICE_SYNC] No invoices found yet | Order: {order_id} | Will retry...")
                    else:
                        logger.warning(f"[INVOICE_SYNC] ERP returned non-200 code: {data.get('code')} | Message: {data.get('message')}")
                        # Don't break - retry on non-200 code as ERP might still be processing
                else:
                    logger.warning(f"[INVOICE_SYNC] HTTP {response.status_code} | Response: {response.text[:200]}")
            
            except requests.exceptions.Timeout:
                logger.warning(f"[INVOICE_SYNC] Connection timeout | Attempt {retry_count + 1}/{max_retries}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"[INVOICE_SYNC] Connection error | Attempt {retry_count + 1}/{max_retries}")
            except Exception as e:
                logger.error(f"[INVOICE_SYNC] Unexpected error: {str(e)} | Attempt {retry_count + 1}/{max_retries}")
            
            retry_count += 1
            if retry_count < max_retries and not invoices_data:
                # Wait before retry (exponential backoff: 2s, 4s, 8s, 15s, 15s, ...)
                wait_time = min(2 ** (retry_count + 1), 15)  # Cap at 15 seconds
                logger.info(f"[INVOICE_SYNC] Retrying in {wait_time}s... (Attempt {retry_count}/{max_retries})")
                time.sleep(wait_time)
        
        # Store invoices if found
        if not invoices_data:
            logger.warning(f"[INVOICE_SYNC] No invoices found after {max_retries} attempts for order {order_id}. Will attempt manual sync later.")
            return False
        
        # Get the sales order
        try:
            sales_order = SalesOrder.objects.get(order_id=order_id)
        except SalesOrder.DoesNotExist:
            logger.error(f"[INVOICE_SYNC] Sales order not found: {order_id}")
            return False
        
        # Store each invoice and its line items
        stored_count = 0
        for invoice_data in invoices_data:
            try:
                doc_no = invoice_data.get('docNo')
                
                # Check if invoice already exists
                if Invoice.objects.filter(doc_no=doc_no).exists():
                    logger.info(f"[INVOICE_SYNC] Invoice already stored: {doc_no}")
                    stored_count += 1
                    continue
                
                # Create invoice
                invoice = Invoice.objects.create(
                    sales_order=sales_order,
                    doc_no=doc_no,
                    doc_date=parse_date(invoice_data.get('docDate')),
                    doc_status=invoice_data.get('docStatus', 'Invoice Created'),
                    created_by=invoice_data.get('createdBy', 'SYSTEM'),
                    doc_discount=invoice_data.get('docDiscount', 0),
                    doc_total=invoice_data.get('docTotal', 0)
                )
                
                # Store invoice line items
                details = invoice_data.get('detail', [])
                for line_item in details:
                    try:
                        InvoiceDetail.objects.create(
                            invoice=invoice,
                            product_id=line_item.get('productId', ''),
                            product_name=line_item.get('productName', ''),
                            hsn_code=line_item.get('hsnCode', ''),
                            qty_per_box=line_item.get('qtyPerBox', '1'),
                            batch=line_item.get('batch', ''),
                            qty=line_item.get('qty', 0),
                            expiry_date=parse_date(line_item.get('expiryDate')),
                            mrp=line_item.get('mrp', 0),
                            sale_rate=line_item.get('saleRate', 0),
                            disc_amt=line_item.get('discAmt', 0),
                            disc_per=line_item.get('discPer', 0),
                            item_total=line_item.get('itemTotal', 0),
                            cgst_per=line_item.get('cgstPer', 0),
                            cgst_amt=line_item.get('cgstAmt', 0),
                            sgst_per=line_item.get('sgstPer', 0),
                            sgst_amt=line_item.get('sgstAmt', 0),
                            igst_per=line_item.get('igstPer', 0),
                            igst_amt=line_item.get('igstAmt', 0),
                            cess_per=line_item.get('cessPer', 0),
                            cess_amt=line_item.get('cessAmt', 0)
                        )
                    except Exception as e:
                        logger.error(f"[INVOICE_SYNC] Failed to store line item: {str(e)}")
                
                logger.info(f"[INVOICE_SYNC] ✓ Invoice stored | DocNo: {doc_no} | Items: {len(details)}")
                stored_count += 1
                
            except Exception as e:
                logger.error(f"[INVOICE_SYNC] Failed to store invoice: {str(e)}")
        
        if stored_count > 0:
            logger.info(f"[INVOICE_SYNC] ✓ COMPLETE | Stored {stored_count} invoice(s) for order {order_id}")
            return True
        else:
            logger.warning(f"[INVOICE_SYNC] Failed to store any invoices for order {order_id}")
            return False
    
    except Exception as e:
        logger.error(f"[INVOICE_SYNC] ✗ FAILED | Order: {order_id} | Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def parse_date(date_str):
    """Parse date string in YYYY-MM-DD format"""
    from datetime import datetime
    if not date_str:
        return None
    try:
        if isinstance(date_str, str):
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        return date_str
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse date: {date_str}")
        return None


def fetch_order_status_from_erp(order_id, c2_code, store_id):
    """
    Fetch complete order status and invoice details from ERP
    
    Args:
        order_id: Order ID to fetch
        c2_code: Customer C2 code
        store_id: Store identifier
    
    Returns:
        dict with order and invoice details, or None on error
    """
    try:
        from .erp_token_service import get_cached_erp_token
        
        api_key = get_cached_erp_token()
        if not api_key:
            logger.error(f"[ORDER_STATUS] Failed to get ERP token for order {order_id}")
            return None
        
        erp_base_url = settings.ERP_BASE_URL
        
        # Call get_orderstatus endpoint
        url = f"{erp_base_url}/ws_c2_services_get_orderstatus"
        payload = {
            "c2Code": c2_code,
            "storeId": store_id,
            "prodCode": settings.ERP_PROD_CODE,
            "apiKey": api_key,
            "orderId": order_id
        }
        
        logger.info(f"[ORDER_STATUS] Fetching order status from ERP | Order: {order_id}")
        
        response = requests.get(url, params=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '200':
                logger.info(f"[ORDER_STATUS] ✓ Successfully fetched order {order_id}")
                return data
            else:
                logger.warning(f"[ORDER_STATUS] ERP error: {data.get('message')}")
                return None
        else:
            logger.error(f"[ORDER_STATUS] HTTP {response.status_code}: {response.text[:200]}")
            return None
    
    except Exception as e:
        logger.error(f"[ORDER_STATUS] Error fetching order status: {str(e)}")
        return None
