from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
import os
import sys

# Подключаем путь к проекту
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import Base
from app.models import *  # все модели

# Настройки Alembic
config = context.config

# 🛠️ Удаляем +asyncpg
sync_url = settings.SQLALCHEMY_DATABASE_URI.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_url)

# Конфиг логирования
fileConfig(config.config_file_name)

# Подключаем метадату
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()