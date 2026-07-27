from django.apps import AppConfig
import logging
import os
import sys
import threading

logger = logging.getLogger(__name__)

# Global flag to ensure scheduler only starts once per process
_scheduler_started = False


def _prewarm_search_cache():
    """
    Run in a background thread at startup.
    Fetches all ERP items + builds search_index + master_dict in Redis
    so the very first user search is instant (< 50ms) instead of 42s.
    """
    import time
    import sys
    
    # Sleep in small increments to allow fast exit checking
    for _ in range(30):
        if sys.is_finalizing():
            return
        time.sleep(0.1)
        
    try:
        if sys.is_finalizing():
            return
        logger.info('[PREWARM] Starting ERP search cache pre-warm...')
        
        from django.core.management import call_command
        import io
        
        # Safe stdout/stderr to prevent lock acquisition errors on finalized streams
        class SafeOut(io.StringIO):
            def write(self, s):
                if not sys.is_finalizing():
                    try:
                        sys.stdout.write(s)
                    except Exception:
                        pass
            def flush(self):
                if not sys.is_finalizing():
                    try:
                        sys.stdout.flush()
                    except Exception:
                        pass
            def isatty(self):
                return False

        class SafeErr(io.StringIO):
            def write(self, s):
                if not sys.is_finalizing():
                    try:
                        sys.stderr.write(s)
                    except Exception:
                        pass
            def flush(self):
                if not sys.is_finalizing():
                    try:
                        sys.stderr.flush()
                    except Exception:
                        pass
            def isatty(self):
                return False
                
        safe_stdout = SafeOut()
        safe_stderr = SafeErr()
        
        if sys.is_finalizing():
            return
            
        call_command('sync_itemmaster', stdout=safe_stdout, stderr=safe_stderr)
        
        if sys.is_finalizing():
            return
        logger.info('[PREWARM] ERP search cache pre-warm complete.')
    except Exception as e:
        if not sys.is_finalizing():
            logger.error(f'[PREWARM] Pre-warm failed: {e}')


class DreamspharmaappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dreamspharmaapp'
    
    def ready(self):
        """Start APScheduler and initialize ERP token when app is ready"""
        global _scheduler_started
        
        # Monkey-patch APScheduler executor to suppress harmless shutdown RuntimeError
        try:
            from apscheduler.executors.base import BaseExecutor
            def safe_submit_job(self, job, run_times):
                import sys
                try:
                    self._do_submit_job(job, run_times)
                except Exception as e:
                    if 'after shutdown' in str(e) or sys.is_finalizing():
                        return
                    self._logger.exception('Error submitting job "%s" to executor "%s"', job, self._alias)
            BaseExecutor.submit_job = safe_submit_job
        except Exception:
            pass
        
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

        # ==================== PRE-WARM SEARCH CACHE ====================
        # Run immediately in background so first user search is instant.
        try:
            t = threading.Thread(target=_prewarm_search_cache, daemon=True)
            t.start()
            logger.info('[PREWARM] Background cache pre-warm thread started.')
        except Exception as e:
            logger.error(f'[PREWARM] Failed to start pre-warm thread: {e}')
            
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.events import EVENT_JOB_EXECUTED
            from django_apscheduler.jobstores import DjangoJobStore
            from django_apscheduler.util import close_old_connections
            from .jobs import sync_itemmaster_job, refresh_erp_token_job, retry_unsynced_orders_job
            
            scheduler = BackgroundScheduler(jobstore=DjangoJobStore())
            
            # Job 1: Sync ItemMaster Cache every 10 minutes
            # Keep PostgreSQL database catalog synchronized with ERP in near real-time
            scheduler.add_job(
                sync_itemmaster_job,
                trigger=IntervalTrigger(minutes=10),
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
            logger.info(f'  [OK] sync_itemmaster: every 10 minutes (keeps cache hot)')
            logger.info(f'  [OK] refresh_erp_token: every {token_refresh_hours} hours')
            logger.info(f'  [OK] retry_unsynced_orders: every 5 minutes')
            
            # Register atexit handler to shut down scheduler cleanly with wait=False
            import atexit
            def _shutdown_scheduler():
                try:
                    if scheduler.running:
                        scheduler.shutdown(wait=False)
                except Exception:
                    pass
            atexit.register(_shutdown_scheduler)
        except Exception as e:
            logger.error(f'Failed to start APScheduler: {str(e)}')

