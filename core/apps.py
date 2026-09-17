import threading
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .scheduler import start_scheduler
        # threading.Thread(target=start_scheduler, daemon=True).start()
        start_scheduler()
