"""GitLab / GitHub 웹훅 페이로드를 공통 PullRequestEvent로 정규화."""
from typing import Any, Dict, Optional

from core.services.models import PullRequestEvent, PullRequestRef

_GITHUB_PR_ACTIONS = frozenset(
    {"opened", "synchronize", "reopened", "ready_for_review", "edited"}
)


def normalize_pull_request_event(payload: Dict[str, Any]) -> Optional[PullRequestEvent]:
    """
    GitLab MR 또는 GitHub PR 웹훅을 PullRequestEvent로 변환합니다.
    PR/MR 이벤트가 아니면 None을 반환합니다.
    """
    if payload.get("object_kind") == "merge_request":
        return _from_gitlab(payload)
    if "pull_request" in payload:
        return _from_github(payload)
    return None


def _from_gitlab(payload: Dict[str, Any]) -> Optional[PullRequestEvent]:
    project = payload.get("project") or {}
    attrs = payload.get("object_attributes") or {}
    project_ref = project.get("id") or project.get("path_with_namespace")
    number = attrs.get("iid")
    if project_ref is None or number is None:
        return None
    ref = PullRequestRef(
        project_ref=str(project_ref),
        number=int(number),
        title=attrs.get("title", "") or "",
        source_branch=attrs.get("source_branch", "") or "",
    )
    return PullRequestEvent(provider="gitlab", ref=ref, raw_payload=payload)


def _from_github(payload: Dict[str, Any]) -> Optional[PullRequestEvent]:
    action = payload.get("action")
    if action and action not in _GITHUB_PR_ACTIONS:
        return None

    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}
    full_name = repo.get("full_name")
    number = pr.get("number")
    if not full_name or number is None:
        return None

    ref = PullRequestRef(
        project_ref=full_name,
        number=int(number),
        title=pr.get("title", "") or "",
        source_branch=(pr.get("head") or {}).get("ref", "") or "",
    )
    return PullRequestEvent(provider="github", ref=ref, raw_payload=payload)
