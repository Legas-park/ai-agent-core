"""저장소 연동 공통 데이터 모델."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FileDiff:
    """PR/MR 변경 파일 1건의 정규화된 표현."""

    path: str
    diff: str
    new_file: bool = False
    renamed_file: bool = False
    deleted_file: bool = False


@dataclass
class PullRequestRef:
    """
    GitLab MR / GitHub PR 공통 좌표.
    project_ref: GitLab project id/path 또는 GitHub owner/repo
    number: MR iid 또는 PR number
    """

    project_ref: str
    number: int
    title: str = ""
    source_branch: str = ""


@dataclass
class PullRequestEvent:
    """웹훅 페이로드를 정규화한 PR/MR 이벤트."""

    provider: str  # gitlab | github
    ref: PullRequestRef
    raw_payload: dict

    @property
    def project_ref(self) -> str:
        return self.ref.project_ref

    @property
    def number(self) -> int:
        return self.ref.number
