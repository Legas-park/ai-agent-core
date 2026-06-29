import abc
import asyncio
import json
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from core.provider.models import LLM_DEFAULT_MODELS
from core.utils.retry import async_retry


class LLMError(RuntimeError):
    """LLM 호출 계층에서 발생한 오류를 감싸는 공통 예외."""


class BaseLLMProvider(abc.ABC):
    """
    [코어 규격] 모든 LLM 공급자 클라이언트가 구현해야 하는 공통 인터페이스입니다.
    서비스 에이전트는 구체 구현(Gemini/OpenAI)을 몰라도 `complete()` 하나로 추론을 호출합니다.

    동기 HTTP 호출(requests)은 `asyncio.to_thread`로 감싸 이벤트 루프를 막지 않도록 하고,
    일시 장애에는 지수 백오프 재시도를 적용합니다.
    """

    name: str = "base"

    @abc.abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        """프롬프트를 받아 모델의 텍스트 응답을 반환합니다."""
        raise NotImplementedError

    async def complete_json(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Any:
        """
        모델 응답을 JSON으로 파싱해 반환합니다. 모델이 코드펜스(```json ...```)로 감싸는
        흔한 케이스를 방어적으로 벗겨낸 뒤 파싱합니다. 실패 시 LLMError를 던집니다.
        """
        raw = await self.complete(prompt, system=system, temperature=temperature)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> Any:
        text = raw.strip()
        if text.startswith("```"):
            # ```json 또는 ``` 로 시작하는 펜스 제거
            text = text.split("```", 2)
            text = text[1] if len(text) > 1 else raw
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
            text = text.strip().rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # 본문 어딘가에 박혀 있는 첫 JSON 블록만 잘라 재시도
            start = text.find("{")
            start_arr = text.find("[")
            if start_arr != -1 and (start == -1 or start_arr < start):
                start = start_arr
            end = max(text.rfind("}"), text.rfind("]"))
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise LLMError(f"모델 응답을 JSON으로 파싱하지 못했습니다: {exc}") from exc


class GeminiProvider(BaseLLMProvider):
    """Google Gemini (Generative Language API) REST 클라이언트."""

    name = "gemini"
    _ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, model: str = LLM_DEFAULT_MODELS["gemini"], timeout: int = 60):
        if not api_key:
            raise ValueError("GeminiProvider 초기화에 api_key가 필요합니다.")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @async_retry(max_attempts=3, retry_on=(requests.RequestException, LLMError))
    async def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        return await asyncio.to_thread(
            self._complete_sync, prompt, system, temperature, max_tokens
        )

    def _complete_sync(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int
    ) -> str:
        url = self._ENDPOINT.format(model=self.model)
        body: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        resp = requests.post(
            url,
            params={"key": self.api_key},
            json=body,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code >= 500 or resp.status_code == 429:
            raise LLMError(f"Gemini 일시 오류 {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise LLMError(f"Gemini 호출 실패 {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Gemini 응답 형식이 예상과 다릅니다: {json.dumps(data)[:300]}") from exc


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Chat Completions 호환 REST 클라이언트."""

    name = "openai"
    _ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = LLM_DEFAULT_MODELS["openai"], timeout: int = 60):
        if not api_key:
            raise ValueError("OpenAIProvider 초기화에 api_key가 필요합니다.")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @async_retry(max_attempts=3, retry_on=(requests.RequestException, LLMError))
    async def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        return await asyncio.to_thread(
            self._complete_sync, prompt, system, temperature, max_tokens
        )

    def _complete_sync(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int
    ) -> str:
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(
            self._ENDPOINT,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=self.timeout,
        )
        if resp.status_code >= 500 or resp.status_code == 429:
            raise LLMError(f"OpenAI 일시 오류 {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise LLMError(f"OpenAI 호출 실패 {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"OpenAI 응답 형식이 예상과 다릅니다: {json.dumps(data)[:300]}") from exc


def build_providers_from_settings(settings) -> Dict[str, BaseLLMProvider]:
    """
    설정값을 읽어 선택된 LLM 프로바이더(default_llm_provider)의 API 키가 있을 때
    해당 클라이언트를 조립합니다. 키가 없으면 빈 dict를 반환합니다.
    """
    providers: Dict[str, BaseLLMProvider] = {}
    default_provider = getattr(settings, "default_llm_provider", "gemini")

    if default_provider == "gemini" and getattr(settings, "gemini_api_key", ""):
        model = getattr(settings, "gemini_model", LLM_DEFAULT_MODELS["gemini"])
        providers["gemini"] = GeminiProvider(api_key=settings.gemini_api_key, model=model)
        logger.info(f"Gemini 프로바이더 구성 완료 (model={model})")
    elif default_provider == "openai" and getattr(settings, "openai_api_key", ""):
        model = getattr(settings, "openai_model", LLM_DEFAULT_MODELS["openai"])
        providers["openai"] = OpenAIProvider(api_key=settings.openai_api_key, model=model)
        logger.info(f"OpenAI 프로바이더 구성 완료 (model={model})")

    if not providers:
        logger.warning(
            f"선택 LLM({default_provider}) API 키 미설정 — 에이전트 LLM 단계는 드라이런됩니다. "
            f"가이드: docs/setup/llm_provider_guide.md"
        )
    return providers
