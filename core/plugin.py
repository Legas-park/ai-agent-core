from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.workflow.orchestrator import WorkflowOrchestrator
from core.agent.base_agent import BaseAgent

class ServicePlugin(ABC):
    """
    [코어 규격] 새롭게 부착할 모든 서비스 플러그인(Service Plugins)들의 최상위 공통 추상 클래스입니다.
    새로운 기능(코드 리뷰, 문서화 등)을 추가할 개발자는 이 클래스를 상속받아 플러그인 규격을 충족해야 합니다.
    이를 통해 코어는 깃랩용인지 위키용인지에 구애받지 않고 모든 서비스를 제어할 수 있는 다형성을 획득합니다.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """
        [필수 구현] 플러그인의 고유 식별명을 정의합니다.
        
        Returns:
            플러그인의 식별 이름 문자열 (예: 'code_review_service')
        """
        pass
        
    @abstractmethod
    def can_handle(self, payload: Dict[str, Any]) -> bool:
        """
        [필수 구현] 유입된 웹훅 페이로드를 내 플러그인이 처리할 수 있는지 감지하여 참/거짓을 반환합니다.
        코어의 Webhook Gateway는 이 함수를 호출하여 어떤 서비스 플러그인을 기동할지 자동으로 식별합니다.
        
        Args:
            payload: 외부 서버(GitLab 등)로부터 들어온 원본 웹훅 JSON 데이터
        Returns:
            해당 웹훅을 이 플러그인이 소화할 수 있다면 True, 처리 대상이 아니라면 False
        """
        pass

    @abstractmethod
    def get_pipeline(self, payload: Dict[str, Any]) -> List[BaseAgent]:
        """
        [필수 구현] 이 플러그인이 실행될 때 사용할 에이전트들의 실스턴스 순차 체인 목록을 조립하여 반환합니다.
        
        Args:
            payload: 들어온 페이로드 상세 정보 (조립 시 참조 가능)
        Returns:
            순차적으로 실행할 에이전트 인스턴스들의 파이프라인 리스트
        """
        pass

    def build_orchestrator(self, payload: Dict[str, Any]) -> WorkflowOrchestrator:
        """
        [코어 도우미] 이 플러그인이 가지고 있는 고유한 에이전트 파이프라인 체인을 로드하여 
        즉시 구동 가능한 워크플로우 오케스트레이터 객체를 제작 및 반환합니다.
        
        Args:
            payload: 에이전트 체인 조립 시 활용될 웹훅 데이터
        Returns:
            이 플러그인 맞춤형으로 셋업된 코어 오케스트레이터 인스턴스
        """
        pipeline = self.get_pipeline(payload)
        return WorkflowOrchestrator(pipeline=pipeline)
