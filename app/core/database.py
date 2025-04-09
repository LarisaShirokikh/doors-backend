from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Синхронный движок (обычный)
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

# Асинхронный движок (asyncpg)
async_database_uri = settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+psycopg2", "postgresql+asyncpg")
async_engine = create_async_engine(async_database_uri, pool_pre_ping=True)

# Сессии
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False
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
        yield session