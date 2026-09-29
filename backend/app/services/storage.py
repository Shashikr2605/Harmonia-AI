from __future__ import annotations

import logging

import boto3
from botocore.config import Config

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# R2 client singleton
# ---------------------------------------------------------------------------

def _make_client():
    settings = get_settings()
    # Sign presigned URLs against the browser-reachable endpoint (see config.py).
    # For R2 this is the same host; for local MinIO it's http://localhost:9000
    # while the worker container reaches MinIO at http://minio:9000.
    endpoint = settings.s3_presign_endpoint_url or settings.r2_endpoint_url
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        # R2 is not in a real AWS region; "auto" is its placeholder. MinIO needs
        # a concrete region (us-east-1). Path-style addressing works for both and
        # avoids virtual-host DNS (bucket.localhost) which breaks against MinIO.
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


_client = None


def _get_client():
    global _client
    if _client is None:
        _client = _make_client()
    return _client


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_presigned_upload_url(
    key: str,
    content_type: str = "application/octet-stream",
    expires: int = 900,  # 15 minutes
) -> str:
    """
    Returns a presigned PUT URL the browser can use to upload directly to R2.
    The API never proxies the audio file itself — this URL goes to the client
    which PUTs to R2 directly.

    NOTE: R2 requires a CORS policy on the bucket to allow PUT/OPTIONS from
    your frontend origin.  Set this in Cloudflare dashboard → R2 → bucket →
    Settings → CORS.  Without it, browser uploads will fail with an opaque
    CORS error even though this URL is valid.
    """
    settings = get_settings()
    client = _get_client()
    url: str = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.r2_bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )
    logger.debug("Generated presigned upload URL for key=%s (expires=%ds)", key, expires)
    return url


def generate_presigned_download_url(key: str, expires: int = 3600) -> str:
    """
    Returns a presigned GET URL for downloading a stem or original audio.
    Expires in 1 hour by default.  Never return raw r2_object_key to the client.
    """
    settings = get_settings()
    client = _get_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": key},
        ExpiresIn=expires,
    )
    logger.debug("Generated presigned download URL for key=%s (expires=%ds)", key, expires)
    return url
