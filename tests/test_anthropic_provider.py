from unittest.mock import MagicMock, patch

import pytest

from config import Settings
from core.provider.llm import AnthropicProvider, build_providers_from_settings
from core.setup.llm import check_llm_config


def test_anthropic_configured_with_api_key_and_model():
    settings = Settings(
        default_llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        anthropic_model="claude-sonnet-4-20250514",
        startup_mode="lenient",
    )
    status = check_llm_config(settings)
    assert status.configured is True
    assert status.provider == "anthropic"
    assert "anthropic.com" in status.model_doc_url


def test_anthropic_not_configured_when_model_missing():
    settings = Settings(
        default_llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        anthropic_model="",
    )
    status = check_llm_config(settings)
    assert status.configured is False
    assert "ANTHROPIC_MODEL" in status.missing_fields


def test_anthropic_provider_init_requires_credentials():
    with pytest.raises(ValueError, match="api_key"):
        AnthropicProvider(api_key="", model="claude-sonnet-4-20250514")
    with pytest.raises(ValueError, match="model id"):
        AnthropicProvider(api_key="sk-ant-test", model="  ")


def test_build_providers_registers_anthropic():
    settings = Settings(
        default_llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        anthropic_model="claude-sonnet-4-20250514",
    )
    providers = build_providers_from_settings(settings)
    assert "anthropic" in providers
    assert providers["anthropic"].model == "claude-sonnet-4-20250514"


@pytest.mark.asyncio
async def test_anthropic_complete_parses_text_block():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"type": "text", "text": "Hello from Claude"}],
    }

    provider = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-4-20250514")

    with patch("core.provider.llm.requests.post", return_value=mock_resp) as mock_post:
        result = await provider.complete("Hi", system="You are helpful")

    assert result == "Hello from Claude"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["model"] == "claude-sonnet-4-20250514"
    assert call_kwargs["json"]["system"] == "You are helpful"
    assert call_kwargs["headers"]["x-api-key"] == "sk-ant-test"
    assert call_kwargs["headers"]["anthropic-version"] == "2023-06-01"
