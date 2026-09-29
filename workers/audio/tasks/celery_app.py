from __future__ import annotations

import os

from celery import Celery

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "harmonia_audio_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # Routing — all tasks in this worker go to the 'audio' queue
    task_default_queue="audio",
    task_queues={
        "audio": {"exchange": "audio", "routing_key": "audio"},
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Acknowledge tasks only after they finish (not just when received).
    # This means a worker crash re-queues the task rather than silently
    # dropping it — important for long-running Demucs jobs.
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # don't prefetch more than concurrency allows
    broker_connection_retry_on_startup=True,
)
