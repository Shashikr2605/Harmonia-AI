FROM python:3.12-slim

WORKDIR /app

# ffmpeg is required by Demucs, faster-whisper, and librosa's audio backend
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# CPU-only torch build — this box has no GPU. Keeps the image ~2GB smaller
# than the CUDA build and avoids a broken install on ARM.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Pre-download Demucs model weights into the image layer so the first
# separation job doesn't stall on a multi-hundred-MB checkpoint download.
# htdemucs is the 4-stem HT-Demucs model; used with --two-stems=vocals
# it produces vocals.wav + no_vocals.wav without downloading extra weights.
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

COPY . .

CMD ["celery", "-A", "tasks", "worker", "--loglevel=info", "--concurrency=1", "-Q", "audio"]

