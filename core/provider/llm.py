import abc
import asyncio
import json
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

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

    def __init__(self, api_key: str, model: str, timeout: int = 60):
        if not api_key:
            raise ValueError("GeminiProvider 초기화에 api_key가 필요합니다.")
        if not model or not model.strip():
            raise ValueError("GeminiProvider 초기화에 model id가 필요합니다.")
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


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    OpenAI Chat Completions 호환 REST 클라이언트.

    Ollama, vLLM, LM Studio 등 로컬/자체 호스팅 LLM 서버에 사용합니다.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        *,
        provider_name: str = "openai_compatible",
        timeout: int = 60,
    ):
        if not model or not model.strip():
            raise ValueError("OpenAICompatibleProvider 초기화에 model id가 필요합니다.")
        if not base_url or not base_url.strip():
            raise ValueError("OpenAICompatibleProvider 초기화에 base_url이 필요합니다.")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.name = provider_name
        self.timeout = timeout
        normalized = base_url.strip().rstrip("/")
        if normalized.endswith("/v1"):
            self._endpoint = f"{normalized}/chat/completions"
        else:
            self._endpoint = f"{normalized}/v1/chat/completions"

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

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = requests.post(
            self._endpoint,
            headers=headers,
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=self.timeout,
        )
        label = self.name
        if resp.status_code >= 500 or resp.status_code == 429:
            raise LLMError(f"{label} 일시 오류 {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise LLMError(f"{label} 호출 실패 {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(
                f"{label} 응답 형식이 예상과 다릅니다: {json.dumps(data)[:300]}"
            ) from exc


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Chat Completions 호환 REST 클라이언트."""

    name = "openai"
    _ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str, timeout: int = 60):
        if not api_key:
            raise ValueError("OpenAIProvider 초기화에 api_key가 필요합니다.")
        if not model or not model.strip():
            raise ValueError("OpenAIProvider 초기화에 model id가 필요합니다.")
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


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Messages API REST 클라이언트."""

    name = "anthropic"
    _ENDPOINT = "https://api.anthropic.com/v1/messages"
    _API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, model: str, timeout: int = 60):
        if not api_key:
            raise ValueError("AnthropicProvider 초기화에 api_key가 필요합니다.")
        if not model or not model.strip():
            raise ValueError("AnthropicProvider 초기화에 model id가 필요합니다.")
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
        body: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        resp = requests.post(
            self._ENDPOINT,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self._API_VERSION,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self.timeout,
        )
        if resp.status_code >= 500 or resp.status_code == 429:
            raise LLMError(f"Anthropic 일시 오류 {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise LLMError(f"Anthropic 호출 실패 {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        try:
            for block in data["content"]:
                if block.get("type") == "text" and block.get("text"):
                    return block["text"]
            raise KeyError("text block")
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Anthropic 응답 형식이 예상과 다릅니다: {json.dumps(data)[:300]}"
            ) from exc


def parse_llm_fallback_chain(primary: str, fallback_csv: str) -> List[str]:
    """primary + LLM_FALLBACK_PROVIDERS 순서로 중복 없는 chain 이름 목록을 만듭니다."""
    chain: List[str] = []
    if primary:
        chain.append(primary.strip())
    for part in fallback_csv.split(","):
        name = part.strip()
        if name and name not in chain:
            chain.append(name)
    return chain


def build_all_providers_from_settings(settings) -> Dict[str, BaseLLMProvider]:
    """설정된 모든 LLM 공급자를 조립합니다 (primary/fallback 공통)."""
    providers: Dict[str, BaseLLMProvider] = {}

    if getattr(settings, "gemini_api_key", "").strip() and getattr(settings, "gemini_model", "").strip():
        model = settings.gemini_model.strip()
        providers["gemini"] = GeminiProvider(api_key=settings.gemini_api_key, model=model)
        logger.info(f"Gemini 프로바이더 등록 (model={model})")

    if getattr(settings, "openai_api_key", "").strip() and getattr(settings, "openai_model", "").strip():
        model = settings.openai_model.strip()
        providers["openai"] = OpenAIProvider(api_key=settings.openai_api_key, model=model)
        logger.info(f"OpenAI 프로바이더 등록 (model={model})")

    if getattr(settings, "anthropic_api_key", "").strip() and getattr(settings, "anthropic_model", "").strip():
        model = settings.anthropic_model.strip()
        providers["anthropic"] = AnthropicProvider(
            api_key=settings.anthropic_api_key, model=model
        )
        logger.info(f"Anthropic 프로바이더 등록 (model={model})")

    local_base = getattr(settings, "local_llm_base_url", "").strip()
    local_model = getattr(settings, "local_llm_model", "").strip()
    if local_base and local_model:
        providers["local"] = OpenAICompatibleProvider(
            api_key=getattr(settings, "local_llm_api_key", ""),
            model=local_model,
            base_url=local_base,
            provider_name="local",
        )
        logger.info(f"Local LLM 프로바이더 등록 (model={local_model}, base={local_base})")

    return providers


def build_llm_router_from_settings(settings, providers: Dict[str, BaseLLMProvider]):
    """primary + fallback chain으로 LLMRouter를 만듭니다."""
    from core.provider.router import LLMRouter

    chain_names = parse_llm_fallback_chain(
        settings.default_llm_provider,
        getattr(settings, "llm_fallback_providers", ""),
    )
    chain = []
    resolved_names: List[str] = []
    for name in chain_names:
        provider = providers.get(name)
        if provider is not None:
            chain.append(provider)
            resolved_names.append(name)

    if not chain:
        return None

    if len(chain) == 1:
        return chain[0]

    logger.info(f"LLM fallback chain: {' → '.join(resolved_names)}")
    return LLMRouter(chain, resolved_names)


def build_providers_from_settings(settings) -> Dict[str, BaseLLMProvider]:
    """
    하위 호환: 선택 primary 공급자만 반환 (deprecated — build_all_providers_from_settings 사용).
    """
    all_providers = build_all_providers_from_settings(settings)
    primary = getattr(settings, "default_llm_provider", "gemini")
    if primary in all_providers:
        return {primary: all_providers[primary]}
    return {}
