from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create a configured async SQLAlchemy engine."""
    return create_async_engine(
        url=settings.database_url,
        echo=settings.sqlalchemy_echo,
        pool_pre_ping=settings.database_pool_pre_ping,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


settings = get_settings()
engine = create_engine(settings)
async_session_factory = create_session_factory(engine)
