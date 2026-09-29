"""
Backend ORM models.

WARNING: These models are duplicated in `workers/audio/db_models.py` because
the worker runs in a separate container and cannot import from the backend.
Any schema changes must be manually synced between both files.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ---------------------------------------------------------------------------
# User (local email/password auth)
# ---------------------------------------------------------------------------

class User(Base):
    """
    Local auth user. When running against Supabase instead, identities live in
    Supabase's auth.users and this table is unused — songs.user_id just stores
    whatever UUID the verified JWT's `sub` claim carries.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Song
# ---------------------------------------------------------------------------

class Song(Base):
    """
    Master record for an uploaded audio file.
    status lifecycle: uploaded → processing → complete | failed
    """
    __tablename__ = "songs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    r2_original_key: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # relationships
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="song", cascade="all, delete-orphan"
    )
    stems: Mapped[list["AudioStem"]] = relationship(
        "AudioStem", back_populates="song", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# ProcessingJob
# ---------------------------------------------------------------------------

class ProcessingJob(Base):
    """
    Tracks a single Celery task run for a song.
    status lifecycle: queued → running → complete | failed
    progress: 0–100 int, updated by the worker.
    """
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(Text, nullable=False, default="stem_separation")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    celery_task_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    song: Mapped["Song"] = relationship("Song", back_populates="processing_jobs")


# ---------------------------------------------------------------------------
# AudioStem
# ---------------------------------------------------------------------------

class AudioStem(Base):
    """
    One separated stem file stored in R2.
    stem_type: vocals | instrumental | drums | bass | other
    """
    __tablename__ = "audio_stems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stem_type: Mapped[str] = mapped_column(Text, nullable=False)
    r2_object_key: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # relationships
    song: Mapped["Song"] = relationship("Song", back_populates="stems")
