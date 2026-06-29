import pytest

from config import Settings
from core.setup.llm import assert_llm_startup, check_llm_config


def test_llm_not_configured_when_api_key_missing():
    settings = Settings(
        default_llm_provider="gemini",
        gemini_api_key="",
        gemini_model="gemini-2.0-flash",
        startup_mode="lenient",
    )
    status = check_llm_config(settings)
    assert status.configured is False
    assert "GEMINI_API_KEY" in status.missing_fields


def test_llm_configured_with_valid_gemini():
    settings = Settings(
        default_llm_provider="gemini",
        gemini_api_key="test-key",
        gemini_model="gemini-2.0-flash",
        startup_mode="lenient",
    )
    status = check_llm_config(settings)
    assert status.configured is True


def test_llm_invalid_model_name():
    settings = Settings(
        default_llm_provider="openai",
        openai_api_key="sk-test",
        openai_model="gpt-unknown-model",
        startup_mode="lenient",
    )
    status = check_llm_config(settings)
    assert status.configured is False
    assert any("OPENAI_MODEL" in field for field in status.missing_fields)


def test_llm_strict_blocks_startup():
    settings = Settings(
        default_llm_provider="openai",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        startup_mode="strict",
    )
    with pytest.raises(SystemExit):
        assert_llm_startup(settings)


def test_llm_supported_models_list_populated():
    settings = Settings(default_llm_provider="gemini", gemini_model="gemini-2.0-flash")
    status = check_llm_config(settings)
    assert "gemini-2.0-flash" in status.supported_models
