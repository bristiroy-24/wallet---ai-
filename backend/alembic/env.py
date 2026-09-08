"""
alembic/env.py
───────────────
Alembic migration environment.

Configured for async SQLAlchemy using asyncpg.
Reads DATABASE_URL from app settings (pydantic-settings / .env).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Load app config for DATABASE_URL
from app.core.config import settings

# Import Base
from app.db.base import Base

# EXPLICITLY import all model files here:
from app.models.user import User  # noqa: F401
from app.models.account import Account  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.ai_insight import AIInsight  # noqa: F401 (or whatever your AI insight model filename/class is)

target_metadata = Base.metadata



# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url from settings (replaces the blank in alembic.ini)
config.set_main_option("sqlalchemy.url", 
settings.DATABASE_URL.replace("%" , "%%"))

# Python logging setup from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode (generates SQL without connecting) ───────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects to DB and applies migrations) ───────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
