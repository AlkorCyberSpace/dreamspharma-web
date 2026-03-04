"""
Scheduled jobs for dreamspharmaapp using APScheduler
Runs sync_itemmaster management command every 15 minutes
"""

import logging
from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)


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
