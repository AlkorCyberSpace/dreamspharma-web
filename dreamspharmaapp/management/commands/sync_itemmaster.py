"""
Django management command to sync ItemMaster cache from ERP
Run every 15-30 minutes using cron or Celery Beat

Usage:
  python manage.py sync_itemmaster
  
Or add to crontab:
  */15 * * * * cd /path/to/app && python manage.py sync_itemmaster
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import logging
from datetime import datetime
from dreamspharmaapp.models import ItemMaster
from dreamspharmaapp.erp_token_service import get_cached_erp_token

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync ItemMaster cache from ERP every 15-30 minutes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f'[{datetime.now()}] Starting ItemMaster sync from ERP...'))
        
        try:
            # 🎯 Get ERP token for authentication
            api_key = get_cached_erp_token()
            if not api_key:
                self.stdout.write(self.style.ERROR('Failed to get ERP token. Aborting sync.'))
                logger.error('[SYNC_ITEMMASTER] Failed to get ERP token')
                return
            
            # Fetch all items from ERP with authentication
            erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
            params = {
                'apiKey': api_key,
                'prodCode': settings.ERP_PROD_CODE,
                'c2Code': settings.ERP_C2_CODE,
                'storeId': settings.ERP_STORE_ID
            }
            
            self.stdout.write(f'[SYNC_ITEMMASTER] Fetching items from ERP: {erp_url}')
            response = requests.get(erp_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != '200' or not data.get('data'):
                self.stdout.write(self.style.ERROR('Failed to fetch data from ERP'))
                logger.error('ERP returned no data during sync')
                return
            
            items_data = data.get('data', [])
            created_count = 0
            updated_count = 0
            error_count = 0
            
            # Update each item in cache
            for item_data in items_data:
                try:
                    item_code = item_data.get('c_item_code')
                    if not item_code:
                        continue
                    
                    # Parse expiry date
                    expiry_date_str = item_data.get('expiryDate', '2099-12-31')
                    try:
                        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                    except:
                        expiry_date = datetime(2099, 12, 31).date()
                    
                    # Update or create ItemMaster with essential fields only
                    item, created = ItemMaster.objects.update_or_create(
                        item_code=item_code,
                        defaults={
                            'item_name': item_data.get('itemName', ''),
                            'item_qty_per_box': item_data.get('itemQtyPerBox', 1),
                            'batch_no': item_data.get('batchNo', ''),
                            'std_disc': float(item_data.get('std_disc', 0)),
                            'max_disc': float(item_data.get('max_disc', 0)),
                            'mrp': float(item_data.get('mrp', 0)),
                            'expiry_date': expiry_date,
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error syncing item {item_code}: {str(e)}")
                    continue
            
            # Log results
            result_msg = f'Created: {created_count}, Updated: {updated_count}, Errors: {error_count}'
            self.stdout.write(self.style.SUCCESS(f'ItemMaster sync completed! {result_msg}'))
            logger.info(f'ItemMaster sync result: {result_msg}')
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'ERP connection failed: {str(e)}'))
            logger.error(f'ERP connection error during sync: {str(e)}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Sync failed: {str(e)}'))
            logger.error(f'ItemMaster sync error: {str(e)}')
