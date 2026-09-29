from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db.base import get_db
from app.db.models import AudioStem, ProcessingJob, Song
from app.services import celery_client, storage

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateSongRequest(BaseModel):
    title: str
    original_filename: str


class CreateSongResponse(BaseModel):
    song_id: str
    r2_original_key: str


class UploadUrlResponse(BaseModel):
    url: str


class ProcessResponse(BaseModel):
    job_id: str


class StemResponse(BaseModel):
    id: str
    stem_type: str
    format: str
    file_size: int
    download_url: str


class SongListItem(BaseModel):
    id: str
    title: str
    original_filename: str
    status: str
    created_at: str
    duration_seconds: Optional[float]


# ---------------------------------------------------------------------------
# POST /api/v1/songs
# ---------------------------------------------------------------------------


@router.post("/songs", response_model=CreateSongResponse, status_code=status.HTTP_201_CREATED)
def create_song(
    body: CreateSongRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
) -> CreateSongResponse:
    """
    Creates a song record (status='uploaded').
    r2_original_key is the R2 object path to which the browser will PUT.
    The actual upload happens via the presigned URL returned by /upload-url.
    user_id is always taken from the JWT — never trust the request body for it.
    """
    song_id = uuid.uuid4()
    r2_key = f"uploads/{song_id}/{body.original_filename}"

    song = Song(
        id=song_id,
        user_id=uuid.UUID(user_id),
        title=body.title,
        original_filename=body.original_filename,
        r2_original_key=r2_key,
        status="uploaded",
    )
    db.add(song)
    db.commit()

    return CreateSongResponse(song_id=str(song_id), r2_original_key=r2_key)


# ---------------------------------------------------------------------------
# POST /api/v1/songs/{song_id}/upload-url
# ---------------------------------------------------------------------------


@router.post("/songs/{song_id}/upload-url", response_model=UploadUrlResponse)
def get_upload_url(
    song_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    content_type: str = Query(default="audio/mpeg"),
    db: Session = Depends(get_db),
) -> UploadUrlResponse:
    """
    Returns a presigned PUT URL for direct browser upload to R2.
    Pass ?content_type=audio/wav (or relevant MIME) so the signed URL and the
    PUT request use the same Content-Type — R2 enforces this.
    """
    song = _get_user_song(db, song_id, user_id)
    url = storage.generate_presigned_upload_url(
        song.r2_original_key,
        content_type=content_type,
    )
    return UploadUrlResponse(url=url)


# ---------------------------------------------------------------------------
# POST /api/v1/songs/{song_id}/process
# ---------------------------------------------------------------------------


@router.post("/songs/{song_id}/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED)
def process_song(
    song_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
) -> ProcessResponse:
    """
    Creates a processing_jobs row, dispatches the Celery task, marks
    songs.status='processing'.
    """
    song = _get_user_song(db, song_id, user_id)

    # Create the job record first so we have a job_id to return
    job = ProcessingJob(
        id=uuid.uuid4(),
        song_id=song.id,
        job_type="stem_separation",
        status="queued",
        progress=0,
    )
    db.add(job)
    db.flush()  # flush to get the id before dispatching

    # Dispatch Celery task
    celery_task_id = celery_client.dispatch_separation_task(str(song.id))

    # Update records
    job.celery_task_id = celery_task_id
    song.status = "processing"
    db.commit()

    return ProcessResponse(job_id=str(job.id))


# ---------------------------------------------------------------------------
# GET /api/v1/songs  (Library — scoped to JWT user)
# ---------------------------------------------------------------------------


@router.get("/songs", response_model=list[SongListItem])
def list_songs(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[SongListItem]:
    """
    Returns paginated list of the authenticated user's songs, newest first.
    """
    offset = (page - 1) * page_size
    songs = (
        db.query(Song)
        .filter(Song.user_id == uuid.UUID(user_id))
        .order_by(Song.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return [
        SongListItem(
            id=str(s.id),
            title=s.title,
            original_filename=s.original_filename,
            status=s.status,
            created_at=s.created_at.isoformat(),
            duration_seconds=s.duration_seconds,
        )
        for s in songs
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/songs/{song_id}/stems
# ---------------------------------------------------------------------------


@router.get("/songs/{song_id}/stems", response_model=list[StemResponse])
def get_stems(
    song_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
) -> list[StemResponse]:
    """
    Returns audio stems for the song with presigned download URLs.
    Raw r2_object_key is never returned to the client.
    """
    _get_user_song(db, song_id, user_id)  # ownership check

    stems = (
        db.query(AudioStem)
        .filter(AudioStem.song_id == uuid.UUID(song_id))
        .order_by(AudioStem.created_at.asc())
        .all()
    )
    return [
        StemResponse(
            id=str(stem.id),
            stem_type=stem.stem_type,
            format=stem.format,
            file_size=stem.file_size,
            download_url=storage.generate_presigned_download_url(stem.r2_object_key),
        )
        for stem in stems
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_song(db: Session, song_id: str, user_id: str) -> Song:
    """Fetches a song, enforcing that it belongs to the requesting user."""
    try:
        song_uuid = uuid.UUID(song_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")

    song = (
        db.query(Song)
        .filter(Song.id == song_uuid, Song.user_id == user_uuid)
        .first()
    )
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    return song
