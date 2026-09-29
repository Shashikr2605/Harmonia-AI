from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Worker DB engine
# ---------------------------------------------------------------------------
# The worker connects to the same Supabase Postgres as the backend but runs
# in a separate container with its own connection pool.
#
# pool_pre_ping=True is non-negotiable here: Supabase uses pgbouncer in
# transaction mode which drops idle connections.  Without pool_pre_ping, a
# long separation job completes and then the DB write fails with an opaque
# OperationalError because the connection aged out while Demucs was running.
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var must be set for the audio worker.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # detects stale connections after long Demucs runs
    pool_size=2,         # small pool — worker concurrency is typically 1
    max_overflow=0,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Returns a new SQLAlchemy session.  Caller is responsible for closing it."""
    return SessionLocal()
