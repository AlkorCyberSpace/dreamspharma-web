from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class DreamspharmaappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dreamspharmaapp'
    
    def ready(self):
        """Start APScheduler when app is ready"""
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from apscheduler.events import EVENT_JOB_EXECUTED
        from django_apscheduler.jobstores import DjangoJobStore
        from django_apscheduler.util import close_old_connections
        from .jobs import sync_itemmaster_job
        import django
        
        # Only start the scheduler once (check if already running)
        if not hasattr(django, '_scheduler_running'):
            try:
                scheduler = BackgroundScheduler(jobstore=DjangoJobStore())
                scheduler.add_job(
                    sync_itemmaster_job,
                    trigger=IntervalTrigger(minutes=15),
                    id='sync_itemmaster',
                    name='Sync ItemMaster Cache',
                    replace_existing=True
                )
                scheduler.add_listener(close_old_connections, EVENT_JOB_EXECUTED)
                scheduler.start()
                django._scheduler_running = True
                logger.info('[OK] APScheduler started - sync_itemmaster will run every 15 minutes')
            except Exception as e:
                logger.error(f'Failed to start APScheduler: {str(e)}')
