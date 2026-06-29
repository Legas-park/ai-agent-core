"""저장소(GitLab/GitHub) 연동 추상 인터페이스."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from core.services.models import FileDiff, PullRequestRef


class BaseRepositoryService(ABC):
    """
    GitLab MR / GitHub PR을 동일한 메서드로 다루는 추상 저장소 서비스.
    서비스 플러그인은 구체 구현(GitLab/GitHub)을 알 필요가 없습니다.
    """

    name: str = "repository"

    @abstractmethod
    async def get_pull_request_changes(self, ref: PullRequestRef) -> List[FileDiff]:
        """PR/MR의 변경 파일·diff 목록을 반환합니다."""

    @abstractmethod
    async def post_pull_request_comment(self, ref: PullRequestRef, body: str) -> Dict[str, Any]:
        """PR/MR에 리뷰 코멘트를 작성합니다."""
