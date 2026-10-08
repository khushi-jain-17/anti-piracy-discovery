import os
import logging
from celery import Celery
from config import settings

logger = logging.getLogger("celery_app")

# Initialize Celery Application
app = Celery(
    "dazn_anti_piracy",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.verification"]
)

# Celery Configuration for Production Robustness
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,      # Avoid head-of-line blocking for heavy browser tasks
    task_acks_late=True,                # Re-queue task if worker crashes or gets killed
    task_reject_on_worker_lost=True,
    result_expires=settings.REDIS_CACHE_TTL_SEC,
    broker_connection_retry_on_startup=True,
)

if __name__ == "__main__":
    app.start()
