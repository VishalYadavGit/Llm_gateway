from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings

settings = get_settings()


def _normalize_database_url(url: str) -> str:
    normalized = url.strip()

    # Dokploy/Heroku-style URLs often use postgres://, which SQLAlchemy does not recognize.
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+asyncpg://", 1)
    elif normalized.startswith("postgresql://") and "+" not in normalized.split("://", 1)[0]:
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

    return normalized


database_url = _normalize_database_url(settings.database_url)

engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
