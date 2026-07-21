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
from dreamspharmaapp.models import ItemMaster, Store
from dreamspharmaapp.erp_token_service import get_erp_token_for_store_config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync ItemMaster cache from ERP every 15-30 minutes for all warehouses'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f'[{datetime.now()}] Starting ItemMaster sync from ERP...'))
        
        try:
            # 🎯 Get all active warehouses/stores from the DB
            active_stores = Store.objects.filter(is_active=True)
            
            configs = []
            if active_stores.exists():
                for store in active_stores:
                    cfg = store.get_erp_config()
                    cfg['base_url'] = settings.ERP_BASE_URL
                    configs.append({
                        'name': store.name,
                        'erp_config': cfg
                    })
            else:
                # Fallback to default single store configuration if no stores are registered
                configs.append({
                    'name': 'Default Settings Store',
                    'erp_config': {
                        'c2_code': settings.ERP_C2_CODE,
                        'store_id': settings.ERP_STORE_ID,
                        'prod_code': settings.ERP_PROD_CODE,
                        'security_key': settings.ERP_SECURITY_KEY if hasattr(settings, 'ERP_SECURITY_KEY') else '',
                        'base_url': settings.ERP_BASE_URL
                    }
                })

            created_count = 0
            updated_count = 0
            error_count = 0
            processed_item_codes = set()
            
            for config in configs:
                store_name = config['name']
                erp_config = config['erp_config']
                self.stdout.write(f"[{datetime.now()}] Syncing master data for warehouse/store: {store_name} ({erp_config['store_id']})...")
                
                try:
                    # Get ERP token for this store/warehouse configuration
                    api_key = get_erp_token_for_store_config(erp_config)
                    if not api_key:
                        self.stdout.write(self.style.ERROR(f'Failed to get ERP token for {store_name}. Skipping.'))
                        logger.error(f'[SYNC_ITEMMASTER] Failed to get ERP token for store {store_name}')
                        continue
                    
                    # Fetch all items from ERP for this store
                    erp_url = f"{settings.ERP_BASE_URL}/ws_c2_services_get_master_data"
                    payload = {
                        'apiKey': api_key,
                        'prodCode': erp_config['prod_code'],
                        'c2Code': erp_config['c2_code'],
                        'storeId': erp_config['store_id'],
                        'inputDateTime': '2021-07-01 10:10:00',
                        'itemcodes': []
                    }
                    
                    self.stdout.write(f'Fetching items from ERP url: {erp_url}')
                    response = requests.get(erp_url, json=payload, timeout=30)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get('code') != '200' or not data.get('data'):
                        self.stdout.write(self.style.ERROR(f'No data returned from ERP for store {store_name}'))
                        continue
                    
                    items_data = data.get('data', [])
                    
                    # ── Pre-warm Redis cache for this store ──────────────────
                    try:
                        from dreamspharmaapp.erp_redis_cache import ERPRedisCache
                        # Pre-warm both default 2021 date and the sync date key
                        ERPRedisCache.set_master_data(erp_config['store_id'], '2021-07-01 10:10:00', items_data)
                        self.stdout.write(self.style.SUCCESS(f"Pre-warmed Redis master cache for store {erp_config['store_id']}"))
                    except Exception as redis_err:
                        self.stdout.write(self.style.WARNING(f"Failed to pre-warm Redis cache: {redis_err}"))

                    # Update each item in cache
                    for item_data in items_data:
                        try:
                            item_code = item_data.get('c_item_code') or item_data.get('itemCode')
                            if not item_code:
                                continue
                            
                            # Check existing item to preserve fields not sent in master data
                            existing_item = ItemMaster.objects.filter(item_code=item_code).first()

                            # Parse expiry date
                            expiry_date_str = item_data.get('expiryDate')
                            if expiry_date_str:
                                try:
                                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                                except:
                                    expiry_date = existing_item.expiry_date if existing_item else datetime(2099, 12, 31).date()
                            else:
                                expiry_date = existing_item.expiry_date if existing_item else datetime(2099, 12, 31).date()
                            
                            # Parse discount rates
                            std_disc = float(item_data.get('stdDiscRate') or item_data.get('std_disc') or 0)
                            max_disc = float(item_data.get('maxDiscPer') or item_data.get('max_disc') or 0)
                            
                            # MRP: preserve if not sent in master data
                            mrp_val = item_data.get('mrpBox') or item_data.get('mrp')
                            if mrp_val is not None:
                                mrp = float(mrp_val)
                            else:
                                mrp = existing_item.mrp if existing_item else 0.0
                                
                            # Batch No: preserve if not sent
                            batch_no = item_data.get('batchNo') or item_data.get('batch_no')
                            if batch_no is None:
                                batch_no = existing_item.batch_no if existing_item else '-'

                            # Update or create ItemMaster with all fields
                            item, created = ItemMaster.objects.update_or_create(
                                item_code=item_code,
                                defaults={
                                    'item_name': item_data.get('itemName', ''),
                                    'item_qty_per_box': item_data.get('itemQtyPerBox', 1),
                                    'batch_no': batch_no,
                                    'std_disc': std_disc,
                                    'max_disc': max_disc,
                                    'mrp': mrp,
                                    'expiry_date': expiry_date,
                                    'brand_code': item_data.get('brandCode') or '-',
                                    'brand_name': item_data.get('brandName') or '-',
                                    'category_code': item_data.get('categoryCode') or '-',
                                    'category_name': item_data.get('categoryName') or '-',
                                    'content_code': item_data.get('contentCode') or '-',
                                    'content_name': item_data.get('contentName') or '-',
                                    'hsn_sac_name': item_data.get('hsnSacName') or '-',
                                    'item_full_name': item_data.get('itemFullName'),
                                    'item_short_name': item_data.get('itemShortName') or '-',
                                    'pack_code': item_data.get('packCode') or '-',
                                    'pack_name': item_data.get('packName') or '-',
                                    'hsn_code': item_data.get('hsnSacCode') or item_data.get('hsnCode') or '-',
                                }
                            )
                            
                            if item_code not in processed_item_codes:
                                processed_item_codes.add(item_code)
                                if created:
                                    created_count += 1
                                else:
                                    updated_count += 1
                                    
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Error syncing item {item_code} for store {store_name}: {str(e)}")
                            continue
                            
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing store {store_name}: {str(e)}"))
                    logger.error(f"Error syncing warehouse/store {store_name}: {str(e)}")
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
