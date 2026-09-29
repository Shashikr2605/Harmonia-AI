from __future__ import annotations

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from celery import chain
from sqlalchemy.exc import OperationalError

from services import demucs_service
from services import storage as r2
from tasks.celery_app import celery_app
from tasks.update_job_status import update_job_status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _get_job_and_song(db, song_id: str):
    """
    Returns (job, song) for the given song_id.
    Raises ValueError if not found.
    """
    from db_models import ProcessingJob, Song

    song = db.query(Song).filter(Song.id == uuid.UUID(song_id)).first()
    if not song:
        raise ValueError(f"Song {song_id} not found in database")

    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.song_id == uuid.UUID(song_id))
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )
    if not job:
        raise ValueError(f"No ProcessingJob found for song {song_id}")

    return job, song


def _fail_job(db, job, song, exc: Exception) -> None:
    """Records failure in DB and re-raises so Celery sees it."""
    try:
        job.status = "failed"
        job.error_message = str(exc)[:2000]  # column is Text but guard against huge traces
        job.completed_at = _now()
        song.status = "failed"
        db.commit()
        logger.error(
            "Job %s failed for song %s: %s", job.id, song.id, exc, exc_info=True
        )
    except Exception as db_exc:
        logger.error("Failed to record job failure in DB: %s", db_exc)


# ---------------------------------------------------------------------------
# Primary task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="separate_audio",
    bind=True,
    max_retries=3,
    # Only autoretry on transient network / DB errors.
    # RuntimeError from Demucs (corrupt audio, unsupported format) is
    # intentionally excluded — retry won't help, and it would hide the real
    # error message from the UI.
    autoretry_for=(BotoCoreError, ClientError, OperationalError),
    retry_backoff=True,        # exponential backoff between retries
    retry_backoff_max=60,      # cap at 60s
    retry_jitter=True,         # add jitter to avoid thundering herd
    queue="audio",
)
def separate_audio(self, song_id: str) -> str:
    """
    Main stem-separation pipeline task.

    Pipeline shape (chain):
        separate_audio(song_id)
        → update_job_status(stage='separation_complete')

    Future extension point — add after update_job_status when ready:
        → group(transcribe_vocals.s(), analyze_audio.s())
        → chord callback → generate_embeddings.s()

    Args:
        song_id: UUID string of the song to process.

    Returns:
        song_id (passed through for potential downstream chain/group tasks).
    """
    from db import get_session
    from db_models import AudioStem, ProcessingJob, Song

    tmp_dir: str | None = None
    db = get_session()

    try:
        # ── 1. Mark job running ───────────────────────────────────────────
        job, song = _get_job_and_song(db, song_id)
        job.status = "running"
        job.started_at = _now()
        job.progress = 10
        db.commit()
        logger.info("Job %s started for song %s", job.id, song_id)

        # ── 2. Download original audio from R2 ────────────────────────────
        tmp_dir = tempfile.mkdtemp(prefix="harmonia_")
        ext = Path(song.original_filename).suffix or ".audio"
        local_input = os.path.join(tmp_dir, f"input{ext}")

        r2.download_file(song.r2_original_key, local_input)

        job.progress = 30
        db.commit()

        # ── 3. Run Demucs separation ──────────────────────────────────────
        # Progress checkpoints: 40 after model would normally load (but since
        # weights are baked into the image, this is immediate), 80 after done.
        job.progress = 40
        db.commit()
        logger.info("Running Demucs on %s", local_input)

        output_dir = os.path.join(tmp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # demucs_service.separate raises RuntimeError on Demucs failure.
        # RuntimeError is NOT in autoretry_for, so it fails fast here.
        stem_paths = demucs_service.separate(local_input, output_dir)

        job.progress = 80
        db.commit()
        logger.info("Demucs complete. Stems: %s", stem_paths)

        # ── 4. Upload stems to R2 ─────────────────────────────────────────
        stem_records = []
        for stem_type, local_path in stem_paths.items():
            r2_key = f"stems/{song_id}/{stem_type}.wav"
            r2.upload_file(local_path, r2_key, content_type="audio/wav")
            file_size = os.path.getsize(local_path)
            stem_records.append((stem_type, r2_key, file_size))

        # ── 5. Insert audio_stems rows ────────────────────────────────────
        for stem_type, r2_key, file_size in stem_records:
            stem = AudioStem(
                id=uuid.uuid4(),
                song_id=uuid.UUID(song_id),
                stem_type=stem_type,
                r2_object_key=r2_key,
                format="wav",
                file_size=file_size,
            )
            db.add(stem)

        # ── 6. Mark complete ──────────────────────────────────────────────
        job.status = "complete"
        job.progress = 100
        job.completed_at = _now()
        song.status = "complete"
        db.commit()
        logger.info("Job %s complete for song %s", job.id, song_id)

        return song_id  # pass through for downstream chain tasks

    except (BotoCoreError, ClientError, OperationalError):
        # Transient errors — autoretry_for will re-queue.
        # Don't mark the job as failed yet; let Celery retry first.
        # On final retry exhaustion, Celery will call on_failure which we
        # don't override, but the autoretry mechanism will re-raise and the
        # except-all below will catch it.
        raise

    except Exception as exc:
        # Non-transient failure (Demucs RuntimeError, ValueError, etc.)
        # Record failure immediately and re-raise so Celery tracks it.
        _fail_job(db, *_get_job_and_song(db, song_id), exc)
        raise

    finally:
        # ── 7. Always clean up temp files ─────────────────────────────────
        # This VM has 12GB RAM total.  Orphaned temp audio will fill disk fast.
        if tmp_dir and os.path.exists(tmp_dir):
            import shutil
            try:
                shutil.rmtree(tmp_dir)
                logger.debug("Cleaned up temp dir: %s", tmp_dir)
            except Exception as cleanup_exc:
                logger.warning("Failed to clean up temp dir %s: %s", tmp_dir, cleanup_exc)
        db.close()


# ---------------------------------------------------------------------------
# Wired workflow (called by backend via send_task, not directly)
# ---------------------------------------------------------------------------
# The backend calls:
#   celery_app.send_task('separate_audio', args=[song_id], queue='audio')
#
# If you later want the backend to trigger the full chain:
#   workflow = chain(
#       separate_audio.s(song_id),
#       update_job_status.s(stage='separation_complete'),
#       # STUB: group(transcribe_vocals.s(), analyze_audio.s()) goes here
#   )
#   workflow.delay()
# ---------------------------------------------------------------------------
