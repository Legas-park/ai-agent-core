"""
LLM 프로바이더 설정 검증.

선택한 DEFAULT_LLM_PROVIDER에 맞는 API 키·모델 ID가 준비되었는지 확인합니다.
모델 ID는 공급자 문서 기준 사용자 자유 입력입니다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, TYPE_CHECKING

from core.provider.models import (
    api_key_field_for_provider,
    is_valid_model_id,
    model_doc_url_for_provider,
    model_field_for_provider,
)

if TYPE_CHECKING:
    from config import Settings

LLM_SETUP_GUIDE = "docs/setup/llm_provider_guide.md"

LLMProviderName = Literal["gemini", "openai", "anthropic"]
StartupMode = Literal["lenient", "strict"]

_PROVIDER_API_KEY_ATTR = {
    "gemini": "gemini_api_key",
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
}

_PROVIDER_MODEL_ATTR = {
    "gemini": "gemini_model",
    "openai": "openai_model",
    "anthropic": "anthropic_model",
}


@dataclass
class LLMConfigStatus:
    """LLM 프로바이더 설정 점검 결과."""

    provider: LLMProviderName
    model: str
    configured: bool
    missing_fields: List[str] = field(default_factory=list)
    model_doc_url: str = ""
    startup_mode: StartupMode = "lenient"
    setup_guide: str = LLM_SETUP_GUIDE

    def summary_message(self) -> str:
        if self.configured:
            return f"LLM 프로바이더({self.provider}, model={self.model}) 설정이 완료되었습니다."
        missing = ", ".join(self.missing_fields)
        return (
            f"LLM 프로바이더({self.provider}) 설정이 불완전합니다. "
            f"누락: {missing}. 가이드: {self.setup_guide}"
        )


def _api_key_for_provider(settings: Settings, provider: LLMProviderName) -> str:
    attr = _PROVIDER_API_KEY_ATTR[provider]
    return getattr(settings, attr, "").strip()


def _model_for_provider(settings: Settings, provider: LLMProviderName) -> str:
    attr = _PROVIDER_MODEL_ATTR[provider]
    return getattr(settings, attr, "").strip()


def check_llm_config(settings: Settings) -> LLMConfigStatus:
    """현재 Settings 기준으로 LLM 설정 완료 여부를 반환합니다."""
    provider: LLMProviderName = settings.default_llm_provider  # type: ignore[assignment]
    startup_mode: StartupMode = settings.startup_mode  # type: ignore[assignment]
    model = _model_for_provider(settings, provider)
    model_field = model_field_for_provider(provider)
    doc_url = model_doc_url_for_provider(provider)
    missing: List[str] = []

    if not _api_key_for_provider(settings, provider):
        missing.append(api_key_field_for_provider(provider))
    if not model:
        missing.append(model_field)
    elif not is_valid_model_id(model):
        missing.append(f"{model_field}(공급자 문서의 model id를 입력하세요: {doc_url})")

    return LLMConfigStatus(
        provider=provider,
        model=model,
        configured=len(missing) == 0,
        missing_fields=missing,
        model_doc_url=doc_url,
        startup_mode=startup_mode,
        setup_guide=LLM_SETUP_GUIDE,
    )


def assert_llm_startup(settings: Settings) -> LLMConfigStatus:
    """
    startup_mode=strict 이고 LLM 설정이 불완전하면 SystemExit로 기동을 중단합니다.
    lenient 모드에서는 경고만 남기고 기동을 허용합니다.
    """
    from loguru import logger

    status = check_llm_config(settings)

    if status.configured:
        logger.info(status.summary_message())
        return status

    message = status.summary_message()

    if status.startup_mode == "strict":
        logger.error(message)
        raise SystemExit(
            f"STARTUP_MODE=strict: LLM 설정이 완료되지 않아 서버를 시작할 수 없습니다. "
            f"({status.setup_guide})"
        )

    logger.warning(f"{message} (STARTUP_MODE=lenient — LLM 없이 기동합니다.)")
    return status
