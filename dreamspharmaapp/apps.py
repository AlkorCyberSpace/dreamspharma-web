from django.apps import AppConfig
import logging
import os
import sys

logger = logging.getLogger(__name__)


class DreamspharmaappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dreamspharmaapp'

    def ready(self):
        """Initialize ERP token only — scheduler handled by cron"""

        # Skip in management commands and reloader processes
        if os.environ.get('RUN_MAIN') == 'true':
            return

        # Skip in test/migration/shell processes
        argv = sys.argv
        if len(argv) > 1 and argv[1] in ('migrate', 'makemigrations', 'test', 'shell', 'collectstatic', 'sync_itemmaster'):
            return

        # Initialize ERP token on startup (fast, just checks cache)
        try:
            logger.info('[ERP_TOKEN] Initializing ERP token on startup...')
            from .erp_token_service import initialize_erp_token
            initialize_erp_token()
            logger.info('[ERP_TOKEN] Token initialization done')
        except Exception as e:
            logger.error(f'[ERP_TOKEN] Token init error: {str(e)}')

        # NOTE: sync_itemmaster and other jobs are handled by cron
        # NOT by APScheduler inside Gunicorn — this prevents duplicate
        # jobs and RAM kills from multiple workers
        logger.info('[SCHEDULER] Jobs managed by cron — APScheduler disabled in Gunicorn')
