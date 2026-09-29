"""
tasks/__init__.py — Celery app discovery entrypoint.

`celery -A tasks worker` imports this module and expects to find a Celery
application instance.  We expose it as `app` (Celery's default discovery
attribute) and import all task modules as side-effects so their @celery_app.task
decorators run and the tasks get registered.
"""
from __future__ import annotations

from tasks.celery_app import celery_app

# Expose as 'app' so `celery -A tasks` discovers it without extra config
app = celery_app

# Import task modules to register all tasks with the Celery app
from tasks.separation import separate_audio          # noqa: F401, E402
from tasks.update_job_status import update_job_status  # noqa: F401, E402

__all__ = ["app", "separate_audio", "update_job_status"]
