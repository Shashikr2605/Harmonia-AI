from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
# We use htdemucs (4-stem HT-Demucs) with --two-stems=vocals to produce
# exactly two outputs: vocals.wav and no_vocals.wav.
# The model weights are pre-baked into the Docker image (see Dockerfile) so
# the first job doesn't stall on a multi-hundred-MB download.
# ---------------------------------------------------------------------------
_MODEL = "htdemucs"


def separate(input_path: str, output_dir: str) -> dict[str, str]:
    """
    Runs Demucs 2-stem separation on *input_path*.

    Returns a dict mapping stem name to absolute output file path:
        {"vocals": "/tmp/xyz/htdemucs/track/vocals.wav",
         "instrumental": "/tmp/xyz/htdemucs/track/no_vocals.wav"}

    This function is intentionally a thin subprocess wrapper so it can be
    swapped for a GPU-backed implementation or a different model without
    touching the Celery task layer.

    Raises:
        RuntimeError: if Demucs exits non-zero OR expected output files are
                      missing.  This error is deliberately NOT in the
                      autoretry_for list — corrupt / unsupported audio should
                      fail fast and record the real error, not be retried.
    """
    input_path_obj = Path(input_path)
    output_dir_obj = Path(output_dir)

    logger.info(
        "Starting Demucs separation: model=%s input=%s output_dir=%s",
        _MODEL, input_path, output_dir,
    )

    cmd = [
        "python", "-m", "demucs",
        "--two-stems", "vocals",   # produces vocals.wav + no_vocals.wav
        "-n", _MODEL,
        "-o", str(output_dir_obj),
        str(input_path_obj),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Log the full stderr for debugging — don't swallow it
        logger.error("Demucs stderr:\n%s", result.stderr)
        raise RuntimeError(
            f"Demucs exited with code {result.returncode}. "
            f"stderr: {result.stderr[-2000:]}"  # last 2k chars to avoid log explosion
        )

    # Demucs output structure:
    #   {output_dir}/{model_name}/{track_stem}/vocals.wav
    #   {output_dir}/{model_name}/{track_stem}/no_vocals.wav
    track_name = input_path_obj.stem
    demucs_out = output_dir_obj / _MODEL / track_name

    vocals_path = demucs_out / "vocals.wav"
    no_vocals_path = demucs_out / "no_vocals.wav"

    if not vocals_path.exists():
        raise RuntimeError(f"Expected vocals.wav not found at {vocals_path}")
    if not no_vocals_path.exists():
        raise RuntimeError(f"Expected no_vocals.wav not found at {no_vocals_path}")

    logger.info(
        "Demucs separation complete: vocals=%s instrumental=%s",
        vocals_path, no_vocals_path,
    )

    return {
        "vocals": str(vocals_path),
        "instrumental": str(no_vocals_path),  # map no_vocals → instrumental for the DB
    }
