import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from loguru import logger

from core.utils.retry import async_retry


class GitLabError(RuntimeError):
    """GitLab API 호출 계층의 공통 예외."""


@dataclass
class FileDiff:
    """MR 변경 파일 1건의 정규화된 표현."""

    path: str
    diff: str
    new_file: bool
    renamed_file: bool
    deleted_file: bool


class GitLabClient:
    """
    [코어 통합] GitLab REST API v4를 감싸는 얇은 비동기 클라이언트입니다.
    동기 requests 호출을 asyncio.to_thread로 감싸 이벤트 루프를 막지 않으며,
    일시 장애에는 지수 백오프 재시도를 적용합니다.

    필요한 권한: api 스코프의 Personal/Project Access Token.
    """

    # 코드 리뷰 의미가 없는 잠금/바이너리/벤더 파일은 사전 필터링한다.
    _SKIP_SUFFIXES = (
        ".lock", ".min.js", ".map", ".svg", ".png", ".jpg", ".jpeg",
        ".gif", ".ico", ".pdf", ".woff", ".woff2", ".ttf",
    )
    _SKIP_DIRS = ("node_modules/", "dist/", "build/", "vendor/", ".venv/")

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        if not base_url:
            raise ValueError("GitLabClient 초기화에 base_url이 필요합니다.")
        if not token:
            raise ValueError("GitLabClient 초기화에 access token이 필요합니다.")
        self.base_url = base_url.rstrip("/")
        self.api = f"{self.base_url}/api/v4"
        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": token})
        self.timeout = timeout

    @staticmethod
    def _encode_project(project_id: Any) -> str:
        # 숫자 ID는 그대로, 'group/repo' 경로는 URL 인코딩하여 사용
        if isinstance(project_id, int) or (isinstance(project_id, str) and project_id.isdigit()):
            return str(project_id)
        return quote(str(project_id), safe="")

    def _should_review(self, path: str) -> bool:
        if any(path.endswith(suf) for suf in self._SKIP_SUFFIXES):
            return False
        if any(seg in path for seg in self._SKIP_DIRS):
            return False
        return True

    @async_retry(max_attempts=3, retry_on=(requests.RequestException, GitLabError))
    async def get_mr_changes(self, project_id: Any, mr_iid: int) -> List[FileDiff]:
        """MR의 변경 파일/디프 목록을 가져와 리뷰 대상만 정규화하여 반환합니다."""
        return await asyncio.to_thread(self._get_mr_changes_sync, project_id, mr_iid)

    def _get_mr_changes_sync(self, project_id: Any, mr_iid: int) -> List[FileDiff]:
        pid = self._encode_project(project_id)
        url = f"{self.api}/projects/{pid}/merge_requests/{mr_iid}/changes"
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code >= 500 or resp.status_code == 429:
            raise GitLabError(f"GitLab 일시 오류 {resp.status_code}")
        if resp.status_code >= 400:
            raise GitLabError(f"MR changes 조회 실패 {resp.status_code}: {resp.text[:200]}")

        changes = resp.json().get("changes", [])
        diffs: List[FileDiff] = []
        for ch in changes:
            path = ch.get("new_path") or ch.get("old_path") or ""
            if not path or not self._should_review(path):
                continue
            diffs.append(
                FileDiff(
                    path=path,
                    diff=ch.get("diff", ""),
                    new_file=ch.get("new_file", False),
                    renamed_file=ch.get("renamed_file", False),
                    deleted_file=ch.get("deleted_file", False),
                )
            )
        logger.debug(f"MR !{mr_iid}: 전체 {len(changes)}건 중 리뷰 대상 {len(diffs)}건")
        return diffs

    @async_retry(max_attempts=3, retry_on=(requests.RequestException, GitLabError))
    async def post_mr_note(self, project_id: Any, mr_iid: int, body: str) -> Dict[str, Any]:
        """MR에 일반 코멘트(note)를 작성합니다."""
        return await asyncio.to_thread(self._post_mr_note_sync, project_id, mr_iid, body)

    def _post_mr_note_sync(self, project_id: Any, mr_iid: int, body: str) -> Dict[str, Any]:
        pid = self._encode_project(project_id)
        url = f"{self.api}/projects/{pid}/merge_requests/{mr_iid}/notes"
        resp = self.session.post(url, json={"body": body}, timeout=self.timeout)
        if resp.status_code >= 500 or resp.status_code == 429:
            raise GitLabError(f"GitLab 일시 오류 {resp.status_code}")
        if resp.status_code >= 400:
            raise GitLabError(f"MR note 작성 실패 {resp.status_code}: {resp.text[:200]}")
        return resp.json()


def build_gitlab_client(settings) -> Optional[GitLabClient]:
    """설정에 GitLab URL/토큰이 있으면 클라이언트를 만들고, 없으면 None을 반환합니다."""
    url = getattr(settings, "gitlab_url", "")
    token = getattr(settings, "gitlab_token", "")
    if not url or not token:
        logger.warning("GitLab URL/토큰 미설정: code_review 플러그인은 드라이런(코멘트 미작성)으로 동작합니다.")
        return None
    return GitLabClient(base_url=url, token=token)
