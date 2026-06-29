import asyncio
from typing import List, Optional
from loguru import logger
from datetime import datetime

from core.agent.context import AgentContext
from core.agent.base_agent import BaseAgent

class WorkflowOrchestrator:
    """
    [코어 핵심] 주입받은 개별 에이전트 리스트(파이프라인)의 실행 흐름을 제어하는 오케스트레이터입니다.
    코드가 특정 도메인을 알지 못하며, 서비스 플러그인이 선언해 준 에이전트 순서 그대로
    실행 루프를 돌리고 비동기 대기, 타임아웃 예외, 전체 상태 갱신을 집중 제어합니다.
    """
    def __init__(self, pipeline: List[BaseAgent], default_timeout: int = 300):
        """
        오케스트레이터를 초기화합니다.
        
        Args:
            pipeline: 실행할 순서대로 인스턴스화된 BaseAgent 상속 객체 리스트
            default_timeout: 각 에이전트별 강제 타임아웃 제한 시간 (초 단위, 기본 5분)
        """
        self.pipeline = pipeline
        self.default_timeout = default_timeout
        # 비동기 백그라운드 태스크 관리를 위한 임시 셋 객체
        self.background_tasks = set()

    async def run(self, context: AgentContext) -> AgentContext:
        """
        [코어 기동] 준비된 파이프라인의 에이전트 루프를 차례대로 순차 구동합니다.
        
        Args:
            context: 웹훅 정보등 초기 데이터가 탑재된 상태 컨텍스트
        Returns:
            모든 파이프라인을 통과하거나 에러로 중단된 최종 상태 컨텍스트
        """
        logger.info(f"[{context.task_id}] 오케스트레이터가 {len(self.pipeline)}개의 에이전트 체인 실행을 시작합니다.")
        
        try:
            # 주입받은 에이전트 목록을 순서대로 순회하며 동기/비동기 기동
            for agent in self.pipeline:
                # [안전 장치] 다음 에이전트를 기동하기 직전, 취소 플래그가 들어왔다면 실행 정지
                if context.is_cancelled:
                    logger.warning(f"[{context.task_id}] 전체 작업 취소 신호가 수신되어 파이프라인 가동을 조기 중단합니다.")
                    break

                # [안전 장치] 이전 단계의 에이전트 작업 중 심각한 에러가 발생했다면 전체 파이프라인 중단
                if context.error:
                    logger.warning(f"[{context.task_id}] 이전 에이전트 처리 오류({context.error})로 인해 작업을 조기 강제 차단합니다.")
                    break

                logger.debug(f"[{context.task_id}] 현재 실행 대상 에이전트: {agent.name} (최대 대기 제한: {self.default_timeout}초)")
                
                try:
                    # 비동기 타임아웃(asyncio.wait_for)을 걸어 에이전트가 통제 범위를 벗어나 무한 대기하는 현상을 예방
                    context = await asyncio.wait_for(agent.run(context), timeout=self.default_timeout)
                except asyncio.TimeoutError:
                    # 타임아웃 발생 시 실패 처리 후 루프 강제 탈출
                    error_msg = f"{agent.name} 에이전트가 제한 시간 {self.default_timeout}초 이내에 처리를 완료하지 못해 타임아웃 처리되었습니다."
                    logger.error(f"[{context.task_id}] {error_msg}")
                    context.error = error_msg
                    context.add_history(agent.name, "timeout", f"제한 한계: {self.default_timeout}초")
                    break

        except Exception as e:
            # 예기치 못한 시스템 크래시나 치명적 오류 처리
            logger.critical(f"[{context.task_id}] 워크플로우 실행 엔진이 중단되었습니다: {e}")
            context.error = str(e)
            
        # 전체 워크플로우 기동 종료 시각 기록
        context.end_time = datetime.now()
        logger.info(f"[{context.task_id}] 오케스트레이터의 에이전트 체인 실행이 완료되었습니다. 최종 상태: {context.current_stage}")
        
        return context

    def run_background_subagent(self, agent: BaseAgent, context: AgentContext):
        """
        [비동기 백그라운드 관리] 메인 파이프라인의 실시간 실행 속도를 가로막지 않고, 
        뒤쪽에서 비동기적으로 수행될 서브에이전트(예: 회고 및 분석용 RetrospectiveAgent)를 백그라운드 태스크로 띄웁니다.
        
        Args:
            agent: 백그라운드에서 실행할 에이전트 인스턴스
            context: 해당 에이전트가 단독으로 참조하여 사용할 상태 컨텍스트
        """
        async def _task():
            try:
                # 백그라운드로 안전하게 격리 구동
                await asyncio.wait_for(agent.run(context), timeout=self.default_timeout)
            except Exception as e:
                logger.error(f"[{context.task_id}] 백그라운드 서브에이전트 {agent.name} 실행 중 실패: {e}")

        # 백그라운드 코루틴 태스크 셋에 바인딩하여 GC(가비지 컬렉션) 방지
        task = asyncio.create_task(_task())
        self.background_tasks.add(task)
        # 태스크 완료 시 셋에서 자동 제거되도록 콜백 연결
        task.add_done_callback(self.background_tasks.discard)
