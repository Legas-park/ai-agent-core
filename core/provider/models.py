"""
LLM 공급자 메타데이터.

모델 ID는 공급자 문서에 따라 사용자가 직접 입력합니다 (하드코딩 카탈로그 없음).
"""
from typing import Dict, Literal

LLMProviderName = Literal["gemini", "openai"]

# .env 기본값 제안용 (카탈로그·허용 목록 아님)
LLM_DEFAULT_MODELS: Dict[LLMProviderName, str] = {
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}

# 공급자별 model id 참고 문서
LLM_MODEL_DOC_URLS: Dict[LLMProviderName, str] = {
    "gemini": "https://ai.google.dev/gemini-api/docs/models",
    "openai": "https://platform.openai.com/docs/models",
}


def api_key_field_for_provider(provider: str) -> str:
    """공급자에 대응하는 env 변수명을 반환합니다."""
    mapping = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    return mapping.get(provider, "LLM_API_KEY")


def model_field_for_provider(provider: str) -> str:
    """공급자에 대응하는 model env 변수명을 반환합니다."""
    mapping = {
        "gemini": "GEMINI_MODEL",
        "openai": "OPENAI_MODEL",
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
