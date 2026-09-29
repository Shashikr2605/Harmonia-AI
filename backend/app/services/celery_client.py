from __future__ import annotations

import logging

from celery import Celery

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery client (no task bodies — this is the backend's send-only client)
# ---------------------------------------------------------------------------
# The actual task implementations live in workers/audio/tasks/separation.py.
# We only call celery_app.send_task() here — we do not import or define any
# task functions.  This avoids coupling the backend to the worker's dependencies
# (torch, demucs, etc.) which would bloat the API image.
# ---------------------------------------------------------------------------

def _make_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "harmonia_backend_client",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        broker_connection_retry_on_startup=True,
    )
    return app


_celery_app: Celery | None = None


def get_celery_app() -> Celery:
    global _celery_app
    if _celery_app is None:
        _celery_app = _make_celery_app()
    return _celery_app


def dispatch_separation_task(song_id: str) -> str:
    """
    Dispatches the 'separate_audio' task to the audio queue.
    Returns the Celery task ID to store as processing_jobs.celery_task_id.

    The worker registers the task named 'separate_audio' on the 'audio' queue
    (celery -Q audio).  That queue name must match the -Q flag in docker-compose.yml.
    """
    celery_app = get_celery_app()
    result = celery_app.send_task(
        "separate_audio",
        args=[song_id],
        queue="audio",
    )
    logger.info("Dispatched separate_audio task task_id=%s for song_id=%s", result.id, song_id)
    return result.id
