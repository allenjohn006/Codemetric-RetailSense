from celery import Celery
from config import settings

celery_app = Celery(
    "retailsense",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,  # 24 hours
    worker_max_tasks_per_child=50,  # restart worker after 50 tasks to free memory
    broker_connection_retry_on_startup=True,  # Suppress deprecation warning
)
