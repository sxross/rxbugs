"""Alembic migration environment.

Connection URL is read from the DATABASE_URL environment variable
(or defaults to the local SQLite file), so migrations always run
against the same database the app is using.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the project root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the URL from environment if present
_DEFAULT_DB_PATH = Path(__file__).parent.parent / "bugtracker.db"
_DEFAULT_URL = f"sqlite:///{_DEFAULT_DB_PATH}"
db_url = os.environ.get("DATABASE_URL", _DEFAULT_URL)
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = None  # We use raw DDL, not MetaData


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
