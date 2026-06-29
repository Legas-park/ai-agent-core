import pytest
import asyncio
from typing import Dict, Any, List

from core.agent.base_agent import BaseAgent
from core.agent.context import AgentContext
from core.workflow.orchestrator import WorkflowOrchestrator
from core.plugin import ServicePlugin

# =====================================================================
# 🧪 테스트용 가상(Mock) 에이전트 및 플러그인 정의
# =====================================================================

class MockPlanningAgent(BaseAgent):
    """테스트용 기획 에이전트: 웹훅 페이로드에서 값을 읽어 diff 정보를 컨텍스트에 씁니다."""
    async def process(self, context: AgentContext) -> AgentContext:
        await self.log_info(context, "가상 변경 파일을 탐색 중...")
        # outputs 저장소에 가상의 diff 데이터를 저장
        context.set_output("mock_diff", "print('hello world')")
        return context

class MockReviewAgent(BaseAgent):
    """테스트용 리뷰 에이전트: 기획 에이전트가 기록해둔 diff를 읽어 검사 후 최종 결과를 씁니다."""
    async def process(self, context: AgentContext) -> AgentContext:
        diff_content = context.get_output("mock_diff")
        await self.log_info(context, f"획득한 파일 내용 검사 중: {diff_content}")
        
        # 검사 분석 결과 코멘트를 적재
        context.set_output("mock_review_comment", "규칙 준수 완료: 특이사항 없음.")
        return context

class MockSlowAgent(BaseAgent):
    """테스트용 느린 에이전트: 타임아웃 검증을 위해 의도적으로 긴 시간 동안 수면에 들어갑니다."""
    async def process(self, context: AgentContext) -> AgentContext:
        await self.log_info(context, "장시간 대기 상태에 진입합니다...")
        await asyncio.sleep(2.0) # 2초 대기
        context.set_output("slow_success", True)
        return context

class MockFailAgent(BaseAgent):
    """테스트용 예외 발생 에이전트: 일부러 에러를 내어 예외 전파와 오케스트레이션 차단을 확인합니다."""
    async def process(self, context: AgentContext) -> AgentContext:
        await self.log_info(context, "의도적인 에러를 발생시킵니다.")
        raise ValueError("심각한 런타임 빌드 에러 감지!")


class MockServicePlugin(ServicePlugin):
    """테스트용 가상 플러그인 명세"""
    @property
    def name(self) -> str:
        return "mock_test_service"

    def can_handle(self, payload: Dict[str, Any]) -> bool:
        # payload에 test_trigger가 참으로 들어오는 경우 매칭
        return payload.get("test_trigger") is True

    def get_pipeline(self, payload: Dict[str, Any]) -> List[BaseAgent]:
        # 기획 -> 리뷰 에이전트 순으로 오케스트레이션 파이프라인 조립
        return [
            MockPlanningAgent(name="MockPlanningAgent"),
            MockReviewAgent(name="MockReviewAgent")
        ]

# =====================================================================
# 🏃‍♂️ Pytest 비동기 격리 테스트 시나리오 수행
# =====================================================================

# pytest가 비동기 코루틴 함수(async def)를 테스트할 수 있게 선언
pytestmark = pytest.mark.asyncio

async def test_successful_pipeline_execution():
    """
    [검증 1] 정상적인 파이프라인 순차 실행 및 에이전트 간 데이터 전달 검증
    - 기획 에이전트가 쓴 데이터("mock_diff")를 리뷰 에이전트가 꺼내어 가공할 수 있는가?
    - 에이전트들의 실행 히스토리가 순서대로 완벽히 누적되는가?
    """
    # 1. Given: 가상의 이벤트와 서비스 플러그인 셋업
    payload = {"test_trigger": True}
    context = AgentContext(task_id="test-task-001", metadata={"payload": payload})
    plugin = MockServicePlugin()
    
    # 2. When: 코어 빌더를 통해 오케스트레이터를 조립하고 실행 시작
    orchestrator = plugin.build_orchestrator(payload)
    final_context = await orchestrator.run(context)

    # 3. Then: 결과 확인
    assert final_context.error is None
    # 기획 에이전트 성과물 확인
    assert final_context.get_output("mock_diff") == "print('hello world')"
    # 리뷰 에이전트 최종 결과물 확인
    assert final_context.get_output("mock_review_comment") == "규칙 준수 완료: 특이사항 없음."
    
    # 에이전트 히스토리가 순서대로 잘 쌓였는지 검증
    stages = [h["agent"] for h in final_context.history if h["action"] == "completed"]
    assert stages == ["MockPlanningAgent", "MockReviewAgent"]


async def test_pipeline_halts_on_agent_error():
    """
    [검증 2] 파이프라인 중단 검증
    - 중간에 에러가 발생한 에이전트(MockFailAgent)가 있다면 다음 에이전트는 기동되지 않고 차단되는가?
    - 발생한 예외 에러가 컨텍스트에 정상 박제되는가?
    """
    # 1. Given: 실패 에이전트 -> 정상 리뷰 에이전트 순으로 강제 조립
    pipeline = [
        MockFailAgent(name="MockFailAgent"),
        MockReviewAgent(name="MockReviewAgent")
    ]
    context = AgentContext(task_id="test-task-002")
    orchestrator = WorkflowOrchestrator(pipeline=pipeline)

    # 2. When: 가동
    final_context = await orchestrator.run(context)

    # 3. Then: 에러가 기록되었고, 다음 단계 에이전트인 MockReviewAgent는 스킵되었는지 검증
    assert final_context.error is not None
    assert "심각한 런타임 빌드 에러 감지!" in final_context.error
    assert final_context.get_output("mock_review_comment") is None  # 실행되지 않음


async def test_pipeline_respects_cancellation():
    """
    [검증 3] 사용자 긴급 정지(취소) 신호 차단 검증
    - 컨텍스트의 취소 플래그(is_cancelled)가 작동하면 다음 에이전트의 실행이 원천 봉쇄되는가?
    """
    # 1. Given: 기획 에이전트 정상 처리 후, 강제 취소 상태 부여
    pipeline = [
        MockPlanningAgent(name="MockPlanningAgent"),
        MockReviewAgent(name="MockReviewAgent")
    ]
    context = AgentContext(task_id="test-task-003")
    orchestrator = WorkflowOrchestrator(pipeline=pipeline)

    # 기획 에이전트 실행 완료 직후, 강제 취소 플래그가 들어왔다고 가정하기 위해 수동 구동 시뮬레이션
    context = await MockPlanningAgent(name="MockPlanningAgent").run(context)
    context.is_cancelled = True # 긴급 정지 상태 주입

    # 2. When: 두 번째 에이전트인 MockReviewAgent를 돌리려 할 때
    with pytest.raises(Exception) as exc_info:
        await MockReviewAgent(name="MockReviewAgent").run(context)

    # 3. Then: 기동 취소 예외가 발생했는지 검증
    assert "TaskCancelled" in str(exc_info.value)
    # 히스토리에 취소 에러 로그 박제 확인
    assert context.history[-1]["action"] == "error"
    assert "사용자 요청에 의해 강제 취소되었습니다." in context.history[-1]["details"]


async def test_agent_timeout_handling():
    """
    [검증 4] 비동기 타임아웃 차단 검증
    - 제한 시간(예: 0.5초)보다 더 오랫동안 수면에 잠긴 느린 에이전트(MockSlowAgent)가 있을 때,
      오케스트레이터가 타임아웃 오류를 내며 연결을 강제 수거하는가?
    """
    # 1. Given: 제한 시간을 0.5초로 극도로 타이트하게 설정
    pipeline = [MockSlowAgent(name="MockSlowAgent")]
    context = AgentContext(task_id="test-task-004")
    orchestrator = WorkflowOrchestrator(pipeline=pipeline, default_timeout=1) # 1초 제한 부여

    # 2. When: 2초가 걸리는 에이전트를 1초 제한 오케스트레이터로 구동
    final_context = await orchestrator.run(context)

    # 3. Then: 타임아웃 강제 실패 처리가 정상 동작했는지 검증
    assert final_context.error is not None
    # 윈도우 인코딩 환경에서 한글 깨짐 이슈를 피하기 위해 영문 및 숫자 위주로 안전하게 단언합니다.
    assert "MockSlowAgent" in final_context.error
    assert "1" in final_context.error
    assert final_context.get_output("slow_success") is None # 느린 처리가 마저 도는 도중에 강제 회수됨
