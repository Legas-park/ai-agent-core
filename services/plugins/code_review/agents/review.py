from typing import Any, Dict, List

from core.agent.base_agent import BaseAgent
from core.agent.context import AgentContext
from core.provider.registry import llm_registry
from core.provider.llm import LLMError
from core.services.registry import service_registry
from core.services.models import PullRequestRef
from core.services.payload_normalizer import normalize_pull_request_event
from services.plugins.code_review.prompts import (
    SYSTEM_PROMPT,
    build_review_prompt,
    render_review_comment,
)

_MAX_DIFF_CHARS_PER_FILE = 6000
_MAX_TOTAL_DIFF_CHARS = 24000


def _resolve_pr_event(context: AgentContext, payload: Dict[str, Any]):
    """metadata.pr_event 또는 payload에서 PR/MR 좌표를 해석합니다."""
    cached = context.metadata.get("pr_event")
    if cached:
        return PullRequestRef(
            project_ref=str(cached["project_ref"]),
            number=int(cached["number"]),
            title=cached.get("title", "") or "",
            source_branch=cached.get("source_branch", "") or "",
        )
    event = normalize_pull_request_event(payload)
    if event is None:
        return None
    return event.ref


class PlanningAgent(BaseAgent):
    """
    [1단계] 웹훅에서 PR/MR 좌표를 추출하고,
    service_registry.repository로 변경 diff를 수집합니다.
    """

    async def process(self, context: AgentContext) -> AgentContext:
        payload: Dict[str, Any] = context.metadata.get("payload", {})
        ref = _resolve_pr_event(context, payload)

        if ref is None:
            await self.log_info(context, "PR/MR 좌표를 페이로드에서 찾지 못해 리뷰를 건너뜁니다.")
            context.set_output("review_files", [])
            return context

        context.set_output("project_id", ref.project_ref)
        context.set_output("mr_iid", ref.number)
        context.set_output("mr_title", ref.title)
        context.set_output("mr_source_branch", ref.source_branch)

        repository = service_registry.get("repository")
        if repository is None:
            await self.log_info(context, "저장소 어댑터 미구성(드라이런): diff 수집을 건너뜁니다.")
            context.set_output("review_files", [])
            return context

        diffs = await repository.get_pull_request_changes(ref)
        files: List[Dict[str, str]] = []
        for d in diffs:
            if d.deleted_file:
                continue
            snippet = d.diff[:_MAX_DIFF_CHARS_PER_FILE]
            files.append({"path": d.path, "diff": snippet})

        context.set_output("review_files", files)
        await self.log_info(context, f"리뷰 대상 파일 {len(files)}건 수집 완료 (PR #{ref.number})")
        return context


class CodeReviewAgent(BaseAgent):
    """[2단계] LLM 분석 후 repository에 리뷰 코멘트를 게시합니다."""

    async def process(self, context: AgentContext) -> AgentContext:
        files: List[Dict[str, str]] = context.get_output("review_files", [])
        if not files:
            await self.log_info(context, "리뷰할 diff가 없어 분석을 종료합니다.")
            context.set_output("review_result", {"summary": "리뷰 대상 변경이 없습니다.", "issues": []})
            return context

        provider = llm_registry.get_default()
        if provider is None:
            await self.log_info(context, "LLM 프로바이더 미구성: 분석을 건너뜁니다(드라이런).")
            context.set_output("review_result", {"summary": "LLM 미구성으로 분석을 건너뛰었습니다.", "issues": []})
            return context

        diff_block = self._assemble_diff_block(files)
        prompt = build_review_prompt(
            title=context.get_output("mr_title", ""),
            source_branch=context.get_output("mr_source_branch", ""),
            diff_block=diff_block,
        )

        try:
            result = await provider.complete_json(prompt, system=SYSTEM_PROMPT)
        except LLMError as exc:
            self.log_error(context, f"LLM 리뷰 분석 실패: {exc}")
            context.set_output("review_result", {"summary": f"분석 실패: {exc}", "issues": []})
            return context

        summary = result.get("summary", "") if isinstance(result, dict) else ""
        issues = result.get("issues", []) if isinstance(result, dict) else []
        context.set_output("review_result", {"summary": summary, "issues": issues})
        await self.log_info(context, f"LLM 분석 완료: 이슈 {len(issues)}건")

        await self._publish(context, summary, issues)
        return context

    @staticmethod
    def _assemble_diff_block(files: List[Dict[str, str]]) -> str:
        chunks: List[str] = []
        total = 0
        for f in files:
            header = f"\n----- FILE: {f['path']} -----\n"
            body = f["diff"]
            if total + len(header) + len(body) > _MAX_TOTAL_DIFF_CHARS:
                chunks.append("\n----- (이하 분량 초과로 생략) -----\n")
                break
            chunks.append(header + body)
            total += len(header) + len(body)
        return "".join(chunks)

    async def _publish(self, context: AgentContext, summary: str, issues: list):
        repository = service_registry.get("repository")
        project_id = context.get_output("project_id")
        pr_number = context.get_output("mr_iid")
        if repository is None or project_id is None or pr_number is None:
            await self.log_info(context, "저장소 미구성: 코멘트 게시를 건너뜁니다.")
            return

        ref = PullRequestRef(
            project_ref=str(project_id),
            number=int(pr_number),
            title=context.get_output("mr_title", "") or "",
            source_branch=context.get_output("mr_source_branch", "") or "",
        )
        body = render_review_comment(summary, issues)
        note = await repository.post_pull_request_comment(ref, body)
        context.set_output("posted_note_id", note.get("id"))
        await self.log_info(context, f"PR #{pr_number}에 리뷰 코멘트 게시 완료 (id: {note.get('id')})")
