# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Синхронный движок
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Асинхронный движок - ИСПРАВЛЕННАЯ ВЕРСИЯ
async_database_uri = settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+psycopg2", "postgresql+asyncpg")
async_engine = create_async_engine(
    async_database_uri, 
    pool_pre_ping=True,
    # Добавьте эти параметры, чтобы предотвратить преждевременное подключение
    future=True,
    pool_recycle=3600,
    connect_args={"server_settings": {"application_name": "FastAPI"}}
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # Важный параметр для асинхронных сессий
)

# Базовый класс
Base = declarative_base()

# Зависимости FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()



async def get_async_db_for_scheduler():
    """
    Получает сессию БД для планировщика задач
    """
    engine = create_async_engine(async_database_uri)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()