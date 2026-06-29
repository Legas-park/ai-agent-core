"""
통합 설정 ORM 모델.

- repository_config: 저장소 연동 singleton
- llm_provider_config: LLM primary/fallback chain (N행)
- system_meta: setup_completed 등 전역 플래그
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class RepositoryConfig(Base):
    """저장소 연동 설정 (1행 singleton, id=1)."""

    __tablename__ = "repository_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_project: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    webhook_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")
    configured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=_utcnow
    )


class LLMProviderConfig(Base):
    """LLM 공급자 설정 — priority 0=primary, 1+=fallback."""

    __tablename__ = "llm_provider_config"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")
    api_base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=_utcnow
    )


class SystemMeta(Base):
    """전역 시스템 메타 (1행 singleton, id=1)."""

    __tablename__ = "system_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    setup_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    setup_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=_utcnow
    )
