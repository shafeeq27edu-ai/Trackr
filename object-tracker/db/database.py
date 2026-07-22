from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from config.settings import get_cached_settings

settings = get_cached_settings()
SQLALCHEMY_DATABASE_URL = settings.database_url

from sqlalchemy.pool import NullPool  # noqa: E402

# Async Engine for PostgreSQL
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, poolclass=NullPool)

# Async session factory
SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

Base = declarative_base()


async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
