# maindash/apps.py
from django.apps import AppConfig

class MaindashConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'maindash'

    def ready(self):
        import maindash.signals  # Connect signals on startup
