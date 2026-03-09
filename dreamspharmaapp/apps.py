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
        """Start APScheduler when app is ready"""
        global _scheduler_started
        
        # Skip if already started in this process
        if _scheduler_started:
            return
        
        # Skip scheduler initialization if this is not the main Django process
        # This prevents duplicate schedulers in multi-process environments
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.events import EVENT_JOB_EXECUTED
            from django_apscheduler.jobstores import DjangoJobStore
            from django_apscheduler.util import close_old_connections
            from .jobs import sync_itemmaster_job
            
            scheduler = BackgroundScheduler(jobstore=DjangoJobStore())
            scheduler.add_job(
                sync_itemmaster_job,
                trigger=IntervalTrigger(minutes=15),
                id='sync_itemmaster',
                name='Sync ItemMaster Cache',
                replace_existing=True,
                max_instances=1  # Ensure only one instance of this job runs at a time
            )
            scheduler.add_listener(close_old_connections, EVENT_JOB_EXECUTED)
            scheduler.start()
            _scheduler_started = True
            logger.info('[OK] APScheduler started - sync_itemmaster will run every 15 minutes')
        except Exception as e:
            logger.error(f'Failed to start APScheduler: {str(e)}')
