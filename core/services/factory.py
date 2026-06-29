"""repository_provider 설정에 따라 GitLab/GitHub 어댑터를 조립합니다."""
from typing import Optional

from loguru import logger

from core.integrations.github_client import build_github_client
from core.integrations.gitlab_client import build_gitlab_client
from core.services.adapters.github_adapter import GitHubRepositoryAdapter
from core.services.adapters.gitlab_adapter import GitLabRepositoryAdapter
from core.services.base_repository import BaseRepositoryService


def build_repository_service(settings) -> Optional[BaseRepositoryService]:
    """
    REPOSITORY_PROVIDER에 맞는 저장소 어댑터를 반환합니다.
    URL/토큰이 없으면 None(드라이런)을 반환합니다.
    """
    provider = getattr(settings, "repository_provider", "gitlab")

    if provider == "github":
        client = build_github_client(settings)
        if client is None:
            return None
        logger.info("GitHub 저장소 어댑터 구성 완료")
        return GitHubRepositoryAdapter(client)

    client = build_gitlab_client(settings)
    if client is None:
        return None
    logger.info("GitLab 저장소 어댑터 구성 완료")
    return GitLabRepositoryAdapter(client)
