"""
LLM primary + fallback chain 라우터.

첫 공급자 실패 시 다음 공급자로 자동 전환합니다.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from loguru import logger

from core.provider.llm import BaseLLMProvider, LLMError


class LLMRouter(BaseLLMProvider):
    """여러 LLM 공급자를 순서대로 시도하는 라우터."""

    name = "router"

    def __init__(self, chain: Sequence[BaseLLMProvider], chain_names: Sequence[str]):
        if not chain:
            raise ValueError("LLMRouter에는 최소 1개의 공급자가 필요합니다.")
        if len(chain) != len(chain_names):
            raise ValueError("chain과 chain_names 길이가 일치해야 합니다.")
        self.chain = list(chain)
        self.chain_names = list(chain_names)

    async def complete(
        self,
        prompt: str,
        *,
        system=None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        last_error: Optional[LLMError] = None

        for provider_name, provider in zip(self.chain_names, self.chain):
            try:
                result = await provider.complete(
                    prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if provider_name != self.chain_names[0]:
                    logger.info(f"LLM fallback 성공: {provider_name}")
                return result
            except LLMError as exc:
                last_error = exc
                logger.warning(
                    f"LLM fallback: {provider_name} 실패 ({exc}) — "
                    f"{'다음 공급자 시도' if provider_name != self.chain_names[-1] else 'chain 종료'}"
                )

        raise LLMError(
            f"LLM fallback chain 전체 실패 ({' → '.join(self.chain_names)}). "
            f"마지막 오류: {last_error}"
        ) from last_error
