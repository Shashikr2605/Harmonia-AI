from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db.base import get_db
from app.db.models import ProcessingJob, Song

router = APIRouter()


class JobStatusResponse(BaseModel):
    status: str
    progress: int
    error_message: Optional[str]


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """
    Returns the current status, progress percentage, and any error message
    for a processing job.  Scoped to the requesting user via the job's parent song.
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Ownership check — ensure the job's song belongs to the requesting user
    song = (
        db.query(Song)
        .filter(Song.id == job.song_id, Song.user_id == uuid.UUID(user_id))
        .first()
    )
    if not song:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return JobStatusResponse(
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
    )
