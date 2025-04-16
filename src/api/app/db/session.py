"""
Database session and connection handling.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Convert standard PostgreSQL URL to async version
if settings.DATABASE_URL.startswith("postgresql://"):
    async_database_url = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
else:
    async_database_url = settings.DATABASE_URL

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    async_database_url,
    echo=settings.API_DEBUG,
    future=True,
    pool_pre_ping=True,
)

# Create async session factory
async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.exception(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """
    Create all tables defined in models.

    This function is called during application startup.
    """
    try:
        # Import all models here to ensure they are registered with Base
        from app.models import document, job, extraction  # noqa

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise 