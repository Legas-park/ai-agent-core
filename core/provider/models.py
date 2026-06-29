"""
LLM 공급자 메타데이터.

모델 ID·API 키는 사용자가 .env 또는 Setup API로 직접 입력합니다.
코어는 특정 모델명을 하드코딩하지 않습니다.
"""
from typing import Dict, Literal

LLMProviderName = Literal["gemini", "openai", "anthropic"]

# 공급자별 model id 참고 문서 (목록·추천 모델 아님)
LLM_MODEL_DOC_URLS: Dict[LLMProviderName, str] = {
    "gemini": "https://ai.google.dev/gemini-api/docs/models",
    "openai": "https://platform.openai.com/docs/models",
    "anthropic": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
}


def api_key_field_for_provider(provider: str) -> str:
    """공급자에 대응하는 env 변수명을 반환합니다."""
    mapping = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    return mapping.get(provider, "LLM_API_KEY")


def model_field_for_provider(provider: str) -> str:
    """공급자에 대응하는 model env 변수명을 반환합니다."""
    mapping = {
        "gemini": "GEMINI_MODEL",
        "openai": "OPENAI_MODEL",
        "anthropic": "ANTHROPIC_MODEL",
    }
    return mapping.get(provider, "LLM_MODEL")


def model_doc_url_for_provider(provider: str) -> str:
    """공급자 model id 문서 URL을 반환합니다."""
    return LLM_MODEL_DOC_URLS.get(provider, "")  # type: ignore[arg-type]


def is_valid_model_id(model: str) -> bool:
    """model id가 비어 있지 않고 기본 형식을 만족하는지 확인합니다."""
    if not model or not model.strip():
        return False
    normalized = model.strip()
    if len(normalized) > 128:
        return False
    if any(char in normalized for char in ("\n", "\r", "\t")):
        return False
    return True
