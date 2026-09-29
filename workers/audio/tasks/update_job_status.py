from __future__ import annotations

import logging
import uuid

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="update_job_status", bind=True)
def update_job_status(self, result, *, stage: str) -> None:
    """
    Utility task that sits between steps in a Celery chain to record
    intermediate status transitions without duplicating DB logic in each task.

    ``result`` is the return value of the previous task in the chain.
    ``stage`` is a freeform label used in logging (e.g. 'separation_complete').
    """
    from db import get_session
    from db_models import ProcessingJob

    logger.info("update_job_status: stage=%s result=%s", stage, result)
    # In the current MVP pipeline the chain is just:
    #   separate_audio → update_job_status(stage='separation_complete')
    # Future stages (transcription, analysis) will add more links here.
    # For now this is a no-op beyond logging, since separate_audio marks
    # the job complete itself.
