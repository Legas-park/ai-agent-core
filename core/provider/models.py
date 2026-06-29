"""
지원 LLM 공급자별 주요 모델 카탈로그.

.env의 GEMINI_MODEL / OPENAI_MODEL은 아래 목록 중 하나를 사용합니다.
"""
from typing import Dict, List, Literal

LLMProviderName = Literal["gemini", "openai"]

# 공급자별 추천·주요 모델 (2025~2026 기준)
LLM_MODEL_CATALOG: Dict[LLMProviderName, List[str]] = {
    "gemini": [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "o1-mini",
        "o3-mini",
    ],
}

LLM_DEFAULT_MODELS: Dict[LLMProviderName, str] = {
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}


def get_models_for_provider(provider: str) -> List[str]:
    """공급자에 등록된 모델명 목록을 반환합니다."""
    return list(LLM_MODEL_CATALOG.get(provider, []))  # type: ignore[arg-type]


def is_supported_model(provider: str, model: str) -> bool:
    """모델명이 카탈로그에 포함되는지 확인합니다."""
    return model in get_models_for_provider(provider)


def api_key_field_for_provider(provider: str) -> str:
    """공급자에 대응하는 env 변수명을 반환합니다."""
    mapping = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    return mapping.get(provider, "LLM_API_KEY")
