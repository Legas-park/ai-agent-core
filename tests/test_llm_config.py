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


def test_llm_accepts_custom_model_id():
    settings = Settings(
        default_llm_provider="openai",
        openai_api_key="sk-test",
        openai_model="gpt-4.1-custom-preview",
        startup_mode="lenient",
    )
    status = check_llm_config(settings)
    assert status.configured is True
    assert status.model == "gpt-4.1-custom-preview"


def test_llm_rejects_empty_model_id():
    settings = Settings(
        default_llm_provider="openai",
        openai_api_key="sk-test",
        openai_model="   ",
        startup_mode="lenient",
    )
    status = check_llm_config(settings)
    assert status.configured is False
    assert "OPENAI_MODEL" in status.missing_fields


def test_llm_strict_blocks_startup():
    settings = Settings(
        default_llm_provider="openai",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        startup_mode="strict",
    )
    with pytest.raises(SystemExit):
        assert_llm_startup(settings)


def test_llm_model_doc_url_populated():
    settings = Settings(default_llm_provider="gemini", gemini_model="gemini-2.0-flash")
    status = check_llm_config(settings)
    assert "google.dev" in status.model_doc_url
