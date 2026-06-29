import pytest

from core.agent.context import AgentContext
from core.provider.registry import llm_registry
from core.services.registry import service_registry
from core.services.models import FileDiff, PullRequestRef
from services.plugins.code_review import CodeReviewPlugin

pytestmark = pytest.mark.asyncio


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.last_prompt = None
        self.last_system = None

    async def complete_json(self, prompt, *, system=None, temperature=0.1):
        self.last_prompt = prompt
        self.last_system = system
        return self.result


class FakeRepository:
    def __init__(self, diffs):
        self.diffs = diffs
        self.posted = []

    async def get_pull_request_changes(self, ref: PullRequestRef):
        return self.diffs

    async def post_pull_request_comment(self, ref: PullRequestRef, body: str):
        self.posted.append({"ref": ref, "body": body})
        return {"id": 9999}


SAMPLE_PAYLOAD = {
    "object_kind": "merge_request",
    "project": {"id": 105, "path_with_namespace": "team/backend"},
    "object_attributes": {"iid": 12, "title": "feat: 사용자 API", "source_branch": "feature/user-api"},
}


@pytest.fixture(autouse=True)
def clean_registries():
    saved_providers = dict(llm_registry.providers)
    saved_default = llm_registry.default_name
    saved_services = dict(service_registry._services)
    yield
    llm_registry.providers = saved_providers
    llm_registry.default_name = saved_default
    service_registry._services = saved_services


async def test_full_pipeline_posts_review_comment():
    fake_llm = FakeProvider(
        {
            "summary": "전반적으로 양호하나 입력 검증이 부족합니다.",
            "issues": [
                {
                    "file": "app/user.py",
                    "severity": "major",
                    "category": "security",
                    "comment": "사용자 입력 SQL 직결 위험",
                }
            ],
        }
    )
    fake_repo = FakeRepository(
        [
            FileDiff(
                path="app/user.py",
                diff='+ query = f"select ... {uid}"',
                deleted_file=False,
            )
        ]
    )
    llm_registry.providers = {"gemini": fake_llm}
    llm_registry.default_name = "gemini"
    service_registry._services = {"repository": fake_repo}

    plugin = CodeReviewPlugin()
    context = AgentContext(task_id="t-001", metadata={"payload": SAMPLE_PAYLOAD})
    final = await plugin.build_orchestrator(SAMPLE_PAYLOAD).run(context)

    assert final.error is None
    assert "app/user.py" in fake_llm.last_prompt
    assert len(final.get_output("review_result")["issues"]) == 1
    assert len(fake_repo.posted) == 1
    assert "AI 코드 리뷰" in fake_repo.posted[0]["body"]


async def test_deleted_files_are_filtered_out():
    fake_llm = FakeProvider({"summary": "변경 없음", "issues": []})
    fake_repo = FakeRepository([FileDiff(path="old.py", diff="", deleted_file=True)])
    llm_registry.providers = {"gemini": fake_llm}
    llm_registry.default_name = "gemini"
    service_registry._services = {"repository": fake_repo}

    plugin = CodeReviewPlugin()
    context = AgentContext(task_id="t-002", metadata={"payload": SAMPLE_PAYLOAD})
    final = await plugin.build_orchestrator(SAMPLE_PAYLOAD).run(context)

    assert final.get_output("review_files") == []
    assert fake_llm.last_prompt is None


async def test_dryrun_without_integrations():
    llm_registry.providers = {}
    llm_registry.default_name = None
    service_registry._services = {}

    plugin = CodeReviewPlugin()
    context = AgentContext(task_id="t-003", metadata={"payload": SAMPLE_PAYLOAD})
    final = await plugin.build_orchestrator(SAMPLE_PAYLOAD).run(context)

    assert final.error is None
    assert final.get_output("review_files") == []
    assert final.get_output("posted_note_id") is None


def test_plugin_can_handle_gitlab_and_github():
    plugin = CodeReviewPlugin()
    assert plugin.can_handle({"object_kind": "merge_request"}) is True
    assert plugin.can_handle({"action": "opened", "pull_request": {}}) is True
    assert plugin.can_handle({"object_kind": "push"}) is False
    assert plugin.can_handle({"action": "closed", "pull_request": {}}) is False
