import asyncio
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from core.utils.retry import async_retry


class GitHubError(RuntimeError):
    """GitHub API 호출 계층의 공통 예외."""


class GitHubClient:
    """
    GitHub REST API v3/v4를 감싸는 비동기 클라이언트.
    PR diff 조회 및 코멘트 작성을 담당합니다.
    """

    _SKIP_SUFFIXES = (
        ".lock", ".min.js", ".map", ".svg", ".png", ".jpg", ".jpeg",
        ".gif", ".ico", ".pdf", ".woff", ".woff2", ".ttf",
    )
    _SKIP_DIRS = ("node_modules/", "dist/", "build/", "vendor/", ".venv/")

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        if not base_url:
            raise ValueError("GitHubClient 초기화에 base_url이 필요합니다.")
        if not token:
            raise ValueError("GitHubClient 초기화에 access token이 필요합니다.")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self.timeout = timeout

    def _should_review(self, path: str) -> bool:
        if any(path.endswith(suf) for suf in self._SKIP_SUFFIXES):
            return False
        if any(seg in path for seg in self._SKIP_DIRS):
            return False
        return True

    @staticmethod
    def _split_repo(full_name: str) -> tuple[str, str]:
        owner, _, repo = full_name.partition("/")
        if not owner or not repo:
            raise GitHubError(f"잘못된 저장소 형식: {full_name} (owner/repo 필요)")
        return owner, repo

    @async_retry(max_attempts=3, retry_on=(requests.RequestException, GitHubError))
    async def get_pr_files(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_pr_files_sync, repo_full_name, pr_number)

    def _get_pr_files_sync(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        owner, repo = self._split_repo(repo_full_name)
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        resp = self.session.get(url, timeout=self.timeout, params={"per_page": 100})
        if resp.status_code >= 500 or resp.status_code == 429:
            raise GitHubError(f"GitHub 일시 오류 {resp.status_code}")
        if resp.status_code >= 400:
            raise GitHubError(f"PR files 조회 실패 {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    @async_retry(max_attempts=3, retry_on=(requests.RequestException, GitHubError))
    async def post_pr_comment(self, repo_full_name: str, pr_number: int, body: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._post_pr_comment_sync, repo_full_name, pr_number, body)

    def _post_pr_comment_sync(self, repo_full_name: str, pr_number: int, body: str) -> Dict[str, Any]:
        owner, repo = self._split_repo(repo_full_name)
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = self.session.post(url, json={"body": body}, timeout=self.timeout)
        if resp.status_code >= 500 or resp.status_code == 429:
            raise GitHubError(f"GitHub 일시 오류 {resp.status_code}")
        if resp.status_code >= 400:
            raise GitHubError(f"PR comment 작성 실패 {resp.status_code}: {resp.text[:200]}")
        return resp.json()


def build_github_client(settings) -> Optional[GitHubClient]:
    """설정에 GitHub URL/토큰이 있으면 클라이언트를 만들고, 없으면 None을 반환합니다."""
    url = getattr(settings, "github_base_url", "")
    token = getattr(settings, "github_access_token", "")
    if not url or not token:
        logger.warning(
            "GitHub URL/토큰 미설정: repository_provider=github 일 때 저장소 API를 사용할 수 없습니다."
        )
        return None
    return GitHubClient(base_url=url, token=token)
