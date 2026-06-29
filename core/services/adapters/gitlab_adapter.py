"""GitLab REST API → BaseRepositoryService 어댑터."""
from typing import Any, Dict, List

from core.integrations.gitlab_client import GitLabClient
from core.services.base_repository import BaseRepositoryService
from core.services.models import FileDiff, PullRequestRef


class GitLabRepositoryAdapter(BaseRepositoryService):
    """GitLabClient를 BaseRepositoryService 규격으로 감쌉니다."""

    name = "gitlab"

    def __init__(self, client: GitLabClient):
        self._client = client

    async def get_pull_request_changes(self, ref: PullRequestRef) -> List[FileDiff]:
        raw = await self._client.get_mr_changes(ref.project_ref, ref.number)
        return [
            FileDiff(
                path=d.path,
                diff=d.diff,
                new_file=d.new_file,
                renamed_file=d.renamed_file,
                deleted_file=d.deleted_file,
            )
            for d in raw
        ]

    async def post_pull_request_comment(self, ref: PullRequestRef, body: str) -> Dict[str, Any]:
        return await self._client.post_mr_note(ref.project_ref, ref.number, body)
