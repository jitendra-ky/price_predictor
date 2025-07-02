# sudo apt update
# sudo apt install redis-server
# sudo service redis-server start
# redis-cli ping

# start celery worker
# celery -A zproject worker --loglevel=info

# start celery monitoring
# celery -A zproject flower

# quick one-liner to check if everything is working
# sudo services redis-server status

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zproject.settings')

app = Celery('zproject')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
