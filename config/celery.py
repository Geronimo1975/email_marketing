"""
Celery configuration for email_marketing project.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('email_marketing')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    'process-scheduled-campaigns': {
        'task': 'apps.campaigns.tasks.process_scheduled_campaigns',
        'schedule': 60.0,  # Run every minute
    },
    'process-automation-workflows': {
        'task': 'apps.automation.tasks.process_workflow_actions',
        'schedule': 30.0,  # Run every 30 seconds
    },
    'update-subscriber-engagement': {
        'task': 'apps.analytics.tasks.update_subscriber_engagement_scores',
        'schedule': 3600.0,  # Run every hour
    },
    'sync-mailgun-suppressions': {
        'task': 'apps.integrations.tasks.sync_mailgun_suppressions',
        'schedule': 3600.0 * 6,  # Run every 6 hours
    },
    'cleanup-old-webhook-logs': {
        'task': 'apps.integrations.tasks.cleanup_old_webhook_logs',
        'schedule': 3600.0 * 24,  # Run daily
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')