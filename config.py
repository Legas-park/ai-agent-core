from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.provider.models import LLM_DEFAULT_MODELS


class Settings(BaseSettings):
    app_name: str = "AI Agent Core"
    version: str = "1.0.0"
    debug: bool = True

    api_server_host: str = "0.0.0.0"
    api_server_port: int = 8000

    startup_mode: Literal["lenient", "strict"] = "lenient"

    webhook_secret: str = ""

    repository_provider: Literal["gitlab", "github"] = "gitlab"

    gitlab_url: str = ""
    gitlab_token: str = ""
    gitlab_default_project_id: str = ""

    github_base_url: str = "https://api.github.com"
    github_access_token: str = ""
    github_default_repo: str = ""

    default_llm_provider: Literal["gemini", "openai"] = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    gemini_model: str = LLM_DEFAULT_MODELS["gemini"]
    openai_model: str = LLM_DEFAULT_MODELS["openai"]

    plugins_dir: str = "services/plugins"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("startup_mode", mode="before")
    @classmethod
    def normalize_startup_mode(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("repository_provider", mode="before")
    @classmethod
    def normalize_repository_provider(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("default_llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("gemini_model", "openai_model", mode="before")
    @classmethod
    def strip_model_name(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


settings = Settings()
