"""
Database connection and schema for MAXergy persistence (SQLAlchemy Core).

- `DATABASE_URL` selects the database: Railway Postgres (`postgres://` / `postgresql://` URLs are
  normalised to the psycopg 3 driver) or, when unset, a local SQLite file `backend/maxergy.db`.
- The schema is created by Alembic migrations (`backend/migrations`), applied at startup by
  `run_migrations()`; tables are never created implicitly.
"""

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, create_engine
from sqlalchemy.engine import Engine

BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_URL = f"sqlite:///{(BACKEND_DIR / 'maxergy.db').as_posix()}"

metadata = MetaData()

assessments = Table(
    "assessments",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)


def database_url() -> str:
    """SQLAlchemy URL from DATABASE_URL (psycopg 3 for Postgres), SQLite file by default."""
    url = os.getenv("DATABASE_URL", "").strip() or DEFAULT_SQLITE_URL
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@lru_cache(maxsize=None)
def _engine_for(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, future=True)


def get_engine() -> Engine:
    return _engine_for(database_url())


def run_migrations() -> None:
    """Bring the database schema to the latest Alembic revision."""
    from alembic import command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
    command.upgrade(cfg, "head")
