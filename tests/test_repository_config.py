"""저장소 프로바이더 설정 검증 테스트."""
import pytest

from config import Settings
from core.setup.repository import assert_repository_startup, check_repository_config


def test_gitlab_not_configured_when_token_missing():
    settings = Settings(
        repository_provider="gitlab",
        gitlab_url="https://gitlab.com",
        gitlab_token="",
        startup_mode="lenient",
    )
    status = check_repository_config(settings)
    assert status.configured is False
    assert "GITLAB_TOKEN" in status.missing_fields


def test_gitlab_configured_when_url_and_token_present():
    settings = Settings(
        repository_provider="gitlab",
        gitlab_url="https://gitlab.com",
        gitlab_token="glpat-test",
        startup_mode="lenient",
    )
    status = check_repository_config(settings)
    assert status.configured is True
    assert status.missing_fields == []


def test_github_not_configured_when_token_missing():
    settings = Settings(
        repository_provider="github",
        github_base_url="https://api.github.com",
        github_access_token="",
        startup_mode="lenient",
    )
    status = check_repository_config(settings)
    assert status.configured is False
    assert "GITHUB_ACCESS_TOKEN" in status.missing_fields


def test_github_configured_when_credentials_present():
    settings = Settings(
        repository_provider="github",
        github_base_url="https://api.github.com",
        github_access_token="ghp_test",
        startup_mode="lenient",
    )
    status = check_repository_config(settings)
    assert status.configured is True


def test_lenient_allows_startup_when_not_configured():
    settings = Settings(
        repository_provider="gitlab",
        gitlab_url="",
        gitlab_token="",
        startup_mode="lenient",
    )
    status = assert_repository_startup(settings)
    assert status.configured is False


def test_strict_blocks_startup_when_not_configured():
    settings = Settings(
        repository_provider="gitlab",
        gitlab_url="https://gitlab.com",
        gitlab_token="",
        startup_mode="strict",
    )
    with pytest.raises(SystemExit):
        assert_repository_startup(settings)
