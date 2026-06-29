"""GitHub REST API → BaseRepositoryService 어댑터."""
from typing import Any, Dict, List

from core.integrations.github_client import GitHubClient
from core.services.base_repository import BaseRepositoryService
from core.services.models import FileDiff, PullRequestRef


_SKIP_SUFFIXES = (
    ".lock", ".min.js", ".map", ".svg", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".pdf", ".woff", ".woff2", ".ttf",
)
_SKIP_DIRS = ("node_modules/", "dist/", "build/", "vendor/", ".venv/")


def _should_review(path: str) -> bool:
    if any(path.endswith(suf) for suf in _SKIP_SUFFIXES):
        return False
    if any(seg in path for seg in _SKIP_DIRS):
        return False
    return True


class GitHubRepositoryAdapter(BaseRepositoryService):
    """GitHubClient를 BaseRepositoryService 규격으로 감쌉니다."""

    name = "github"

    def __init__(self, client: GitHubClient):
        self._client = client

    async def get_pull_request_changes(self, ref: PullRequestRef) -> List[FileDiff]:
        files = await self._client.get_pr_files(ref.project_ref, ref.number)
        diffs: List[FileDiff] = []
        for item in files:
            path = item.get("filename") or ""
            if not path:
                continue
            status = item.get("status", "")
            deleted = status == "removed"
            if deleted:
                diffs.append(
                    FileDiff(path=path, diff="", deleted_file=True)
                )
                continue
            if not _should_review(path):
                continue
            diffs.append(
                FileDiff(
                    path=path,
                    diff=item.get("patch") or "",
                    new_file=status == "added",
                    renamed_file=status == "renamed",
                    deleted_file=False,
                )
            )
        return diffs

    async def post_pull_request_comment(self, ref: PullRequestRef, body: str) -> Dict[str, Any]:
        return await self._client.post_pr_comment(ref.project_ref, ref.number, body)
