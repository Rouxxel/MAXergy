"""Alembic environment: uses the backend's DATABASE_URL (see src/services/persistence/database.py)."""

from alembic import context
from sqlalchemy import create_engine, pool

from src.services.persistence.database import database_url, metadata

target_metadata = metadata


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = context.config.get_main_option("sqlalchemy.url") or database_url()
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
