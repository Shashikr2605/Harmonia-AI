from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    # Use Supabase session pooler (port 6543), not direct connection (port 5432).
    database_url: str

    # ── Supabase / Auth ───────────────────────────────────────────────────────
    # JWT_SECRET is the "JWT Secret" shown in Supabase → Project Settings → API.
    # Supabase uses HS256 by default.  Newer projects may switch to asymmetric
    # signing (ES256 via JWKS) — if auth.py raises "invalid algorithm", check
    # your project's JWT algorithm setting and swap decode logic accordingly.
    jwt_secret: str
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Local email/password auth (app/api/v1/auth_endpoint.py) mints HS256 tokens
    # signed with jwt_secret; app/auth.py verifies them. When pointed at Supabase
    # instead, jwt_secret is Supabase's JWT Secret and these tokens interoperate.
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ── Object storage (S3-compatible: Cloudflare R2 or local MinIO) ──────────
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str
    r2_endpoint_url: str
    r2_public_url: str = ""

    # Endpoint used ONLY when signing presigned URLs handed to the browser.
    # It must be reachable from the user's browser, which is not the same host
    # the API container uses to reach storage:
    #   • Local MinIO: API container reaches minio at http://minio:9000, but the
    #     browser must PUT/GET to http://localhost:9000 → set this to that.
    #   • Cloudflare R2: browser and server share one public host → leave blank
    #     and R2_ENDPOINT_URL is used for both.
    # If blank, falls back to r2_endpoint_url (correct for R2).
    s3_presign_endpoint_url: str = ""
    # MinIO validates the SigV4 region; R2 uses the "auto" placeholder. For local
    # MinIO set S3_REGION=us-east-1; leave "auto" for R2.
    s3_region: str = "auto"

    # ── Celery ────────────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # ── App-level ─────────────────────────────────────────────────────────────
    # ALLOWED_ORIGINS: comma-separated list, e.g.
    # "https://harmonia.vercel.app,http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    max_upload_size_mb: int = 100

    # ── LLM (completely optional — app runs fine without it) ──────────────────
    anthropic_api_key: Optional[str] = None

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def strip_origins(cls, v: str) -> str:
        return v.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
