"""Alembic environment: async migrations as the owner, one transaction per migration.

The owner/superuser DSN comes from the environment variable MESL_ADMIN_DATABASE_URL only
(same variable as Settings.admin_database_url); it is never read from any file and never
written to alembic.ini. Migrations must run as the owner because the schema creates
roles, extensions and GRANTs; the labapp role cannot and must not.

db/schema.sql (or later scripts) is executed by the revisions themselves; this file
knows nothing about payloads. How a revision executes its script is decided in step 1.2.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # no autogenerate: the schema is written by hand in db/schema.sql

ENV_VAR = "MESL_ADMIN_DATABASE_URL"


def _owner_url() -> str:
    """The owner DSN from the environment, normalized for the asyncpg driver."""
    dsn = os.environ.get(ENV_VAR)
    if not dsn:
        raise SystemExit(
            f"{ENV_VAR} is not set: Alembic needs the owner/superuser DSN to run migrations"
        )
    if not dsn.startswith("postgresql+asyncpg://"):
        if dsn.startswith(("postgresql://", "postgres://")):
            dsn = dsn.replace("://", "+asyncpg://", 1)
        else:
            raise SystemExit(
                f"{ENV_VAR} must be a postgresql:// DSN, got: {dsn.split('@', 1)[-1][:40]}"
            )
    return dsn


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        transaction_per_migration=True,  # one transaction per migration, not per series
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = {"sqlalchemy.url": _owner_url()}
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


def run_migrations_offline() -> None:
    context.configure(
        url=_owner_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
