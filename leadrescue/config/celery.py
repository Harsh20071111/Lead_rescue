"""
Celery configuration for LeadRescue.

Initializes the Celery application and auto-discovers tasks
from all installed Django apps.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("leadrescue")

# Load config from Django settings, using the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in all installed apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Verify Celery is working. Run: celery -A config call config.celery.debug_task"""
    print(f"Request: {self.request!r}")
