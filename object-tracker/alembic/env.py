from logging.config import fileConfig

print("DEBUG: env.py is running")

from sqlalchemy import engine_from_config, pool  # noqa: E402

from alembic import context  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import os  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db.models import Base  # noqa: E402

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    from config.settings import get_cached_settings

    settings = get_cached_settings()
    url = settings.database_url
    # Ensure it's synchronous driver for alembic (e.g., asyncpg -> psycopg2 or just fall back if supported)  # noqa: E501

    # Actually asyncpg is supported if we use run_migrations_online with a specific approach,
    # but the simplest is just let it run. Wait, alembic requires sync driver for simple env.py.
    # Let's replace 'postgresql+asyncpg' with 'postgresql' for the migration URL.
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")

    config.set_main_option("sqlalchemy.url", url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    from config.settings import get_cached_settings

    settings = get_cached_settings()
    url = settings.database_url
    print(f"DEBUG: settings.database_url = {url}")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"DEBUG: after replace url = {url}")

    alembic_config = config.get_section(config.config_ini_section, {})
    alembic_config["sqlalchemy.url"] = url
    print(f"DEBUG: alembic_config['sqlalchemy.url'] = {alembic_config['sqlalchemy.url']}")

    connectable = engine_from_config(
        alembic_config,
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
