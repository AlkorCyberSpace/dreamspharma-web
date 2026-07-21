from django.apps import AppConfig
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Global flag to ensure scheduler only starts once per process
_scheduler_started = False


class DreamspharmaappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dreamspharmaapp'
    
    def ready(self):
        """Start APScheduler and initialize ERP token when app is ready"""
        global _scheduler_started
        
        # Skip if already started in this process
        if _scheduler_started:
            return
        
        # Skip scheduler initialization if this is not the main Django process
        # This prevents duplicate schedulers in multi-process environments
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        # ==================== INITIALIZE ERP TOKEN ====================
        try:
            logger.info('[ERP_TOKEN] Initializing ERP token on app startup...')
            from .erp_token_service import initialize_erp_token
            initialize_erp_token()
        except Exception as e:
            logger.error(f'[ERP_TOKEN] Error initializing token: {str(e)}')
            
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.events import EVENT_JOB_EXECUTED
            from django_apscheduler.jobstores import DjangoJobStore
            from django_apscheduler.util import close_old_connections
            from .jobs import sync_itemmaster_job, refresh_erp_token_job, retry_unsynced_orders_job
            
            scheduler = BackgroundScheduler(jobstore=DjangoJobStore())
            
            # Job 1: Sync ItemMaster Cache every 15 minutes
            scheduler.add_job(
                sync_itemmaster_job,
                trigger=IntervalTrigger(minutes=15),
                id='sync_itemmaster',
                name='Sync ItemMaster Cache',
                replace_existing=True,
                max_instances=1  # Ensure only one instance of this job runs at a time
            )
            
            # Job 2: Refresh ERP token every 23 hours (before 24-hour expiry)
            from django.conf import settings
            token_refresh_hours = getattr(settings, 'ERP_TOKEN_REFRESH_HOURS', 23)
            scheduler.add_job(
                refresh_erp_token_job,
                trigger=IntervalTrigger(hours=token_refresh_hours),
                id='refresh_erp_token',
                name='Refresh ERP Token',
                replace_existing=True,
                max_instances=1
            )
            
            # Job 3: Retry Unsynced ERP Orders every 5 minutes (Outbox pattern)
            scheduler.add_job(
                retry_unsynced_orders_job,
                trigger=IntervalTrigger(minutes=5),
                id='retry_unsynced_orders',
                name='Retry Unsynced ERP Orders',
                replace_existing=True,
                max_instances=1
            )
            
            scheduler.add_listener(close_old_connections, EVENT_JOB_EXECUTED)
            scheduler.start()
            _scheduler_started = True
            logger.info('[OK] APScheduler started - Jobs scheduled:')
            logger.info(f'  [OK] sync_itemmaster: every 15 minutes')
            logger.info(f'  [OK] refresh_erp_token: every {token_refresh_hours} hours')
            logger.info(f'  [OK] retry_unsynced_orders: every 5 minutes')
        except Exception as e:
            logger.error(f'Failed to start APScheduler: {str(e)}')
