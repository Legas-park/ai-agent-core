from abc import ABC, abstractmethod
from typing import Any
from loguru import logger

from core.agent.context import AgentContext

class BaseAgent(ABC):
    """
    [코어 핵심] AI Agent Core 프레임워크의 모든 에이전트가 상속받아야 하는 추상 클래스(Base Class)입니다.
    이 클래스는 템플릿 메서드 패턴을 적용하여, 개별 에이전트가 예외 처리, 비상 정지(취소),
    시작/완료 로그 기록 등의 반복적인 코드 없이 핵심 'process' 로직에만 집중할 수 있게 통제합니다.
    """
    def __init__(self, name: str):
        """
        에이전트 인스턴스를 초기화합니다.
        
        Args:
            name: 에이전트의 식별 이름 (예: 'PlanningAgent', 'CodeReviewAgent')
        """
        self.name = name

    @abstractmethod
    async def process(self, context: AgentContext) -> AgentContext:
        """
        [개발자 필수 구현] 개별 서비스 에이전트가 실제로 수행할 구체적인 비즈니스 로직을 구현하는 영역입니다.
        모든 서비스 에이전트는 이 메서드를 오버라이딩하여 자신만의 작업(Git diff 긁기, LLM 분석 등)을 실행합니다.
        
        Args:
            context: 이전 단계 에이전트들이 흘려준 데이터 및 공통 설정 정보를 포함한 상태 객체
        Returns:
            자신의 처리 결과(outputs)를 추가 혹은 가공한 새로운 상태 객체
        """
        pass

    async def log_start(self, context: AgentContext):
        """에이전트가 작동을 시작했음을 로그에 기록하고, 컨텍스트 히스토리에 적재합니다."""
        logger.info(f"[{context.task_id}] [{self.name}] 에이전트가 작업을 시작합니다...")
        context.add_history(self.name, "started")
        context.current_stage = self.name # 현재 진행 단계를 내 이름으로 갱신

    async def log_complete(self, context: AgentContext, summary: str = ""):
        """에이전트가 성공적으로 완료되었음을 기록하고 히스토리에 적재합니다."""
        logger.info(f"[{context.task_id}] [{self.name}] 에이전트 작업 완료. {summary}")
        context.add_history(self.name, "completed", summary)

    async def log_info(self, context: AgentContext, details: str):
        """에이전트 작동 중간에 실시간 진행 정보를 로깅 및 히스토리에 기록합니다."""
        logger.info(f"[{context.task_id}] [{self.name}] {details}")
        context.add_history(self.name, "info", details)

    def log_error(self, context: AgentContext, message: str):
        """작업 실패 또는 예외 상황 시 에러 세부 사항을 기록합니다."""
        logger.error(f"[{context.task_id}] [{self.name}] 에러 발생: {message}")
        context.add_history(self.name, "error", message)

    async def run(self, context: AgentContext) -> AgentContext:
        """
        [코어 실행 엔진] 에이전트의 실제 안전 실행을 총괄하는 외부 호출용 래퍼(Wrapper) 함수입니다.
        실행 전 취소 체크, 공통 시작/완료 로깅, 크래시 방지를 위한 try-except 구문을 일괄 처리합니다.
        """
        # [안전 장치] 실행 전 사용자가 취소 요청(is_cancelled)을 보냈는지 확인하여 즉각 차단
        if context.is_cancelled:
            logger.warning(f"[{context.task_id}] [{self.name}] 작업 시작 전 취소 신호가 감지되어 기동을 중단합니다.")
            self.log_error(context, "사용자 요청에 의해 강제 취소되었습니다.")
            raise Exception("TaskCancelled")

        # 공통 시작 단계 처리 및 시작 기록 적재
        await self.log_start(context)
        try:
            # 상속받은 서비스 에이전트의 실제 'process' 비즈니스 로직 구동
            new_context = await self.process(context)
            
            # 최종 완료 기록 시, 히스토리의 마지막 메시지를 요약본으로 추출
            summary = ""
            if new_context.history and new_context.history[-1]['agent'] == self.name:
                last_entry = new_context.history[-1]
                if last_entry.get('details'):
                    summary = last_entry['details']
                    
            await self.log_complete(new_context, summary=summary)
            return new_context
        except Exception as e:
            # 예외 발생 시 에러 히스토리 자동 기록 및 상위 워크플로우로 예외 버블링
            if "TaskCancelled" in str(e):
                self.log_error(context, "사용자 요청에 의해 강제 취소되었습니다.")
            else:
                self.log_error(context, str(e))
            raise e
