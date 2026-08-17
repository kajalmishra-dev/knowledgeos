import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create a configured async SQLAlchemy engine."""
    engine = create_async_engine(
        url=settings.database_url,
        echo=settings.sqlalchemy_echo,
        pool_pre_ping=settings.database_pool_pre_ping,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _register_pgvector(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        try:
            from pgvector.psycopg import register_vector

            register_vector(dbapi_connection)
        except Exception:
            logging.getLogger(__name__).warning(
                "Could not register pgvector on this connection; vector inserts may fail.",
                exc_info=True,
            )

    return engine


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
