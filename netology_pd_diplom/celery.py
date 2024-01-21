import os

from celery import Celery

# from celery.result import AsyncResult

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netology_pd_diplom.settings")

app = Celery("netology_pd_diplom")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# def get_result(task_id: str) -> AsyncResult:
#     return AsyncResult(task_id, app=app)
