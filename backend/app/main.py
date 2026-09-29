from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth_endpoint, config_endpoint, jobs, songs
from app.config import get_settings
from app.db.base import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Warm up the DB engine on startup so the first request doesn't pay
    # the connection-establishment cost (also surfaces bad DATABASE_URL early)
    get_engine()
    yield
    # Nothing to clean up — SQLAlchemy engine disposes on process exit


def create_app() -> FastAPI:
    settings = get_settings()

    # Structured logging — LOG_LEVEL env var controls verbosity
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Harmonia AI API (log_level=%s)", settings.log_level)

    app = FastAPI(
        title="Harmonia AI",
        description="Backend API for AI-powered audio stem separation",
        version="0.1.0",
        lifespan=lifespan,
        # Disable the default /docs redirect on /redoc so /health stays clean
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    # ALLOWED_ORIGINS is comma-separated, e.g.:
    #   "https://harmonia-ai.vercel.app,http://localhost:3000"
    # This must include the EXACT Vercel production URL — a trailing slash or
    # wrong subdomain will cause silent CORS failures on the frontend.
    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health check (no auth, for Caddy / uptime monitors) ──────────────────
    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    # ── API v1 routers ────────────────────────────────────────────────────────
    app.include_router(auth_endpoint.router, prefix="/api/v1", tags=["auth"])
    app.include_router(songs.router, prefix="/api/v1", tags=["songs"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(config_endpoint.router, prefix="/api/v1", tags=["config"])

    return app


# This is the entrypoint referenced in backend/Dockerfile:
#   CMD ["uvicorn", "app.main:app", ...]
app = create_app()
