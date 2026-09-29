from __future__ import annotations

import logging
import os

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# R2 client for the audio worker
# ---------------------------------------------------------------------------
# This is intentionally a copy of the backend's storage.py rather than a
# shared module — the worker runs in a completely separate container and Python
# environment.  Keeping them independent avoids a shared-code coupling that
# would complicate deployment and Docker layering.
# ---------------------------------------------------------------------------

_R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "")
_R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
_R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
_R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
# "auto" for R2; MinIO needs a concrete region (us-east-1) to match the SigV4 scope.
_S3_REGION = os.environ.get("S3_REGION", "auto")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=_R2_ENDPOINT_URL,
            aws_access_key_id=_R2_ACCESS_KEY_ID,
            aws_secret_access_key=_R2_SECRET_ACCESS_KEY,
            region_name=_S3_REGION,
            # Path-style addressing works for both R2 and MinIO and avoids
            # virtual-host DNS (bucket.minio) which does not resolve in-cluster.
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    return _client


def download_file(r2_key: str, local_path: str) -> None:
    """Downloads *r2_key* from R2 to *local_path*."""
    logger.info("Downloading r2://%s → %s", r2_key, local_path)
    _get_client().download_file(_R2_BUCKET_NAME, r2_key, local_path)
    logger.info("Download complete: %s", local_path)


def upload_file(local_path: str, r2_key: str, content_type: str = "audio/wav") -> None:
    """Uploads *local_path* to R2 at *r2_key*."""
    logger.info("Uploading %s → r2://%s", local_path, r2_key)
    _get_client().upload_file(
        local_path,
        _R2_BUCKET_NAME,
        r2_key,
        ExtraArgs={"ContentType": content_type},
    )
    logger.info("Upload complete: r2://%s", r2_key)
