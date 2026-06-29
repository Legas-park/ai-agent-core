"""
저장소 프로바이더(GitLab / GitHub) 설정 상태 검증.

API 연동(어댑터)은 코어 3에서 구현하며, 본 모듈은
.env 기반 설정 완료 여부와 기동 시 strict/lenient 정책만 담당합니다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from config import Settings

REPOSITORY_SETUP_GUIDE = "docs/setup/repository_provider_guide.md"

ProviderName = Literal["gitlab", "github"]
StartupMode = Literal["lenient", "strict"]


@dataclass
class RepositoryConfigStatus:
    """저장소 프로바이더 설정 점검 결과."""

    provider: ProviderName
    configured: bool
    missing_fields: List[str] = field(default_factory=list)
    startup_mode: StartupMode = "lenient"
    setup_guide: str = REPOSITORY_SETUP_GUIDE

    def summary_message(self) -> str:
        if self.configured:
            return f"저장소 프로바이더({self.provider}) 설정이 완료되었습니다."
        missing = ", ".join(self.missing_fields)
        return (
            f"저장소 프로바이더({self.provider}) 설정이 불완전합니다. "
            f"누락: {missing}. 가이드: {self.setup_guide}"
        )


def _gitlab_missing(settings: Settings) -> List[str]:
    missing: List[str] = []
    if not settings.gitlab_url.strip():
        missing.append("GITLAB_URL")
    if not settings.gitlab_token.strip():
        missing.append("GITLAB_TOKEN")
    return missing


def _github_missing(settings: Settings) -> List[str]:
    missing: List[str] = []
    if not settings.github_base_url.strip():
        missing.append("GITHUB_BASE_URL")
    if not settings.github_access_token.strip():
        missing.append("GITHUB_ACCESS_TOKEN")
    return missing


def check_repository_config(settings: Settings) -> RepositoryConfigStatus:
    """현재 Settings 기준으로 저장소 연동 설정 완료 여부를 반환합니다."""
    provider: ProviderName = settings.repository_provider  # type: ignore[assignment]
    startup_mode: StartupMode = settings.startup_mode  # type: ignore[assignment]

    if provider == "gitlab":
        missing = _gitlab_missing(settings)
    else:
        missing = _github_missing(settings)

    return RepositoryConfigStatus(
        provider=provider,
        configured=len(missing) == 0,
        missing_fields=missing,
        startup_mode=startup_mode,
        setup_guide=REPOSITORY_SETUP_GUIDE,
    )


def assert_repository_startup(settings: Settings) -> RepositoryConfigStatus:
    """
    startup_mode=strict 이고 설정이 불완전하면 SystemExit로 기동을 중단합니다.
    lenient 모드에서는 경고만 남기고 기동을 허용합니다.
    """
    from loguru import logger

    status = check_repository_config(settings)

    if status.configured:
        logger.info(status.summary_message())
        return status

    message = status.summary_message()

    if status.startup_mode == "strict":
        logger.error(message)
        raise SystemExit(
            f"STARTUP_MODE=strict: 저장소 설정이 완료되지 않아 서버를 시작할 수 없습니다. "
            f"({status.setup_guide})"
        )

    logger.warning(f"{message} (STARTUP_MODE=lenient — 코어 개발 모드로 기동합니다.)")
    return status
