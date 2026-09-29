from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class ConfigResponse(BaseModel):
    max_upload_size_mb: int


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """
    Public endpoint — no auth required.
    Returns client-side configuration hints so the frontend can validate
    file size before attempting an upload (avoiding a wasted presigned URL
    round-trip on an oversized file).
    The API never enforces this itself by streaming the file — uploads go
    directly to R2 via presigned PUT URLs.
    """
    settings = get_settings()
    return ConfigResponse(max_upload_size_mb=settings.max_upload_size_mb)
