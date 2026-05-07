"""
Celery configuration for DreamsPharma
Handles async tasks like ERP API calls, invoice generation, notifications
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dreamspharma.settings')

app = Celery('dreamspharma')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Task routing for order processing
app.conf.task_routes = {
    'dreamspharmaapp.tasks.process_order': {'queue': 'orders', 'priority': 10},
    'dreamspharmaapp.tasks.sync_erp': {'queue': 'erp', 'priority': 5},
    'dreamspharmaapp.tasks.send_notification': {'queue': 'notifications', 'priority': 3},
    'maindash.tasks.generate_invoice': {'queue': 'invoices', 'priority': 7},
}

# Beat schedule (periodic tasks)
app.conf.beat_schedule = {
    # Refresh ERP tokens every 22 hours (before 24-hour expiry)
    'refresh-erp-tokens': {
        'task': 'dreamspharmaapp.tasks.refresh_erp_tokens',
        'schedule': crontab(hour='*/22'),  # Every 22 hours
        'options': {'priority': 10}
    },
    # Sync inventory every 5 minutes
    'sync-inventory': {
        'task': 'dreamspharmaapp.tasks.sync_inventory_from_erp',
        'schedule': 300.0,  # Every 5 minutes (in seconds)
        'options': {'priority': 8}
    },
    # Clean up old cart items (>7 days)
    'cleanup-old-carts': {
        'task': 'dreamspharmaapp.tasks.cleanup_expired_carts',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
        'options': {'priority': 1}
    },
}

# Task execution settings
app.conf.task_acks_late = True  # Acknowledge task only after execution
app.conf.task_reject_on_worker_lost = True  # Reject tasks if worker dies
app.conf.worker_prefetch_multiplier = 4  # Don't load too many tasks at once
app.conf.worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks (prevent memory leaks)

@app.task(bind=True)
def debug_task(self):
    """Test task - verify Celery is working"""
    print(f'Request: {self.request!r}')
