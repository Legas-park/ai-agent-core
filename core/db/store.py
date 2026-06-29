"""
ConfigStore — DB에 저장된 연동 설정 로드/저장 (Setup API·lifespan에서 사용).

Phase 3 Setup API, Phase 4 lifespan 연동 예정.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.encryption import SecretEncryptor
from core.db.models import LLMProviderConfig, RepositoryConfig, SystemMeta


class ConfigStore:
    """암호화된 설정을 DB에 read/write합니다."""

    def __init__(self, session: AsyncSession, encryptor: SecretEncryptor):
        self._session = session
        self._encryptor = encryptor

    async def get_system_meta(self) -> SystemMeta:
        row = await self._session.get(SystemMeta, 1)
        if row is None:
            row = SystemMeta(id=1, setup_completed=False, setup_version="1")
            self._session.add(row)
            await self._session.commit()
            await self._session.refresh(row)
        return row

    async def get_repository_config(self) -> Optional[RepositoryConfig]:
        return await self._session.get(RepositoryConfig, 1)

    async def list_llm_providers(self, *, enabled_only: bool = True) -> List[LLMProviderConfig]:
        stmt = select(LLMProviderConfig).order_by(LLMProviderConfig.priority)
        if enabled_only:
            stmt = stmt.where(LLMProviderConfig.enabled.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def encrypt_secret(self, plaintext: str) -> str:
        return self._encryptor.encrypt(plaintext)

    def decrypt_secret(self, ciphertext: str) -> str:
        return self._encryptor.decrypt(ciphertext)
