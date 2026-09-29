from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── alembic Config object ─────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── DATABASE_URL override ─────────────────────────────────────────────────
# We intentionally do NOT hard-code a connection string here.  The DATABASE_URL
# env var must be the Supabase session pooler URL (port 6543), not the direct
# connection.  Fail fast if the var is missing.
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL env var is not set. "
        "Export it before running `alembic upgrade head`."
    )
config.set_main_option("sqlalchemy.url", database_url)

# ── Import all models so autogenerate sees them ───────────────────────────
# The import order matters: base must come before models.
from app.db.base import Base  # noqa: E402
from app.db import models  # noqa: E402, F401 — side-effect: registers all tables

target_metadata = Base.metadata


# ── Migration runners ─────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Useful for generating SQL scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Supabase Postgres supports transactional DDL
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations against a live connection.
    Uses NullPool so each `alembic` invocation opens exactly one connection
    and closes it cleanly — important for pgbouncer compatibility.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
