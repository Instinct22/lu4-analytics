import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

for path in os.environ.get("PYTHONPATH", "/app").split(":"):
    if path and path not in sys.path:
        sys.path.insert(0, path)

# Fallback for local runs: /opt/project/database/migrations -> /opt/project/backend
_backend = Path(__file__).resolve().parents[2] / "backend"
if _backend.exists() and str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from config import settings
from database import Base
import models.user  # noqa: F401
import models.permissions  # noqa: F401
import models.login_log  # noqa: F401
import models.wiki  # noqa: F401
import models.market  # noqa: F401
import models.analytics  # noqa: F401
import models.character  # noqa: F401
import models.craft  # noqa: F401
import models.npc_loot  # noqa: F401
import models.preferences  # noqa: F401
import models.raid  # noqa: F401
import models.raid_timer_log  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
