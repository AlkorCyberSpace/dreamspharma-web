"""
Scheduled jobs for dreamspharmaapp using APScheduler
Runs sync_itemmaster management command every 15 minutes
"""

import logging
from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)


from django.db import close_old_connections

def sync_itemmaster_job():
    """
    Synchronize ItemMaster cache with ERP data
    Runs every 15 minutes
    """
    try:
        logger.info(f'[{timezone.now()}] Starting sync_itemmaster job...')
        call_command('sync_itemmaster')
        logger.info(f'[{timezone.now()}] sync_itemmaster job completed successfully')
    except Exception as e:
        logger.error(f'[{timezone.now()}] Error in sync_itemmaster job: {str(e)}')
    finally:
        close_old_connections()


def refresh_erp_token_job():
    """
    🔄 Refresh ERP token periodically to prevent expiry
    Runs every 23 hours (configurable in settings.ERP_TOKEN_REFRESH_HOURS)
    
    This ensures the cached token is always fresh and available
    for background services and API calls
    """
    try:
        logger.info(f'[{timezone.now()}] [REFRESH] Starting refresh_erp_token job...')
        from .erp_token_service import refresh_erp_token
        success = refresh_erp_token()
        if success:
            logger.info(f'[{timezone.now()}] [SUCCESS] Token refresh job completed successfully')
        else:
            logger.error(f'[{timezone.now()}] [FAILED] Token refresh job failed')
    except Exception as e:
        logger.error(f'[{timezone.now()}] [FAILED] Error in refresh_erp_token_job: {str(e)}')
    finally:
        close_old_connections()


def retry_unsynced_orders_job():
    """
    📦 Outbox pattern job: Re-attempts pushing unsynced SalesOrders to ERP
    Runs every 5 minutes
    """
    try:
        logger.info(f'[{timezone.now()}] [OUTBOX_JOB] Starting retry_unsynced_orders job...')
        from .services import retry_unsynced_erp_orders
        count = retry_unsynced_erp_orders()
        logger.info(f'[{timezone.now()}] [OUTBOX_JOB] retry_unsynced_orders job completed (synced {count} orders)')
    except Exception as e:
        logger.error(f'[{timezone.now()}] [OUTBOX_JOB] Error in retry_unsynced_orders job: {str(e)}')
    finally:
        close_old_connections()
