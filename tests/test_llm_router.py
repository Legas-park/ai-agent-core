from unittest.mock import MagicMock, patch

import pytest

from config import Settings
from core.provider.llm import (
    LLMError,
    OpenAICompatibleProvider,
    build_all_providers_from_settings,
    build_llm_router_from_settings,
    parse_llm_fallback_chain,
)
from core.provider.router import LLMRouter
from core.setup.llm import check_llm_config


class FakeProvider:
    name = "fake"

    def __init__(self, label: str, result: str = "ok", fail: bool = False):
        self.label = label
        self.result = result
        self.fail = fail
        self.name = label

    async def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=2048):
        if self.fail:
            raise LLMError(f"{self.label} failed")
        return self.result


def test_parse_llm_fallback_chain_deduplicates():
    chain = parse_llm_fallback_chain("local", "gemini,local,openai")
    assert chain == ["local", "gemini", "openai"]


def test_local_llm_configured_without_api_key():
    settings = Settings(
        default_llm_provider="local",
        local_llm_base_url="http://localhost:11434/v1",
        local_llm_model="qwen3.5",
    )
    status = check_llm_config(settings)
    assert status.configured is True


def test_local_llm_requires_base_url():
    settings = Settings(
        default_llm_provider="local",
        local_llm_model="qwen3.5",
    )
    status = check_llm_config(settings)
    assert status.configured is False
    assert "LOCAL_LLM_BASE_URL" in status.missing_fields


def test_build_all_providers_includes_local():
    settings = Settings(
        local_llm_base_url="http://localhost:11434/v1",
        local_llm_model="qwen3.5",
    )
    providers = build_all_providers_from_settings(settings)
    assert "local" in providers
    assert providers["local"].model == "qwen3.5"


@pytest.mark.asyncio
async def test_llm_router_falls_back_on_failure():
    primary = FakeProvider("local", fail=True)
    fallback = FakeProvider("gemini", result="from gemini")
    router = LLMRouter([primary, fallback], ["local", "gemini"])

    result = await router.complete("hello")
    assert result == "from gemini"


@pytest.mark.asyncio
async def test_llm_router_raises_when_all_fail():
    router = LLMRouter(
        [FakeProvider("a", fail=True), FakeProvider("b", fail=True)],
        ["a", "b"],
    )
    with pytest.raises(LLMError, match="chain 전체 실패"):
        await router.complete("hello")


def test_build_llm_router_from_settings_resolves_chain():
    settings = Settings(
        default_llm_provider="local",
        llm_fallback_providers="gemini",
        local_llm_base_url="http://localhost:11434/v1",
        local_llm_model="qwen3.5",
        gemini_api_key="key",
        gemini_model="gemini-2.0-flash",
    )
    all_providers = build_all_providers_from_settings(settings)
    router = build_llm_router_from_settings(settings, all_providers)
    assert isinstance(router, LLMRouter)
    assert router.chain_names == ["local", "gemini"]


@pytest.mark.asyncio
async def test_openai_compatible_local_endpoint():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "local response"}}],
    }
    provider = OpenAICompatibleProvider(
        api_key="",
        model="qwen3.5",
        base_url="http://localhost:11434/v1",
        provider_name="local",
    )

    with patch("core.provider.llm.requests.post", return_value=mock_resp) as mock_post:
        result = await provider.complete("test")

    assert result == "local response"
    assert mock_post.call_args.kwargs["json"]["model"] == "qwen3.5"
    assert "Authorization" not in mock_post.call_args.kwargs["headers"]
