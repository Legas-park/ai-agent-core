"""
SQLAlchemy async 세션 factory.

마이그레이션은 Alembic(sync)으로, 런타임은 asyncpg로 접속합니다.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

_engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def create_engine_from_url(database_url: str) -> AsyncEngine:
    """DATABASE_URL로 async 엔진을 생성합니다."""
    if not database_url:
        raise ValueError("DATABASE_URL이 비어 있습니다.")
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)


def init_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    """전역 async 세션 factory를 초기화합니다."""
    global _engine, async_session_factory
    _engine = create_engine_from_url(database_url)
    async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return async_session_factory


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """FastAPI Depends용 async 세션 generator."""
    if async_session_factory is None:
        raise RuntimeError("DB 세션이 초기화되지 않았습니다. lifespan에서 init_session_factory를 호출하세요.")
    async with async_session_factory() as session:
        yield session


async def dispose_engine() -> None:
    """앱 종료 시 엔진 연결을 정리합니다."""
    global _engine, async_session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    async_session_factory = None
