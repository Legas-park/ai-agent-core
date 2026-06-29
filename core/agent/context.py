from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class AgentStatus(str, Enum):
    """에이전트 워크플로우의 실행 상태를 구분하는 공통 열거형(Enum)입니다."""
    IDLE = "idle"          # 대기 중
    RUNNING = "running"    # 실행 중
    COMPLETED = "completed"# 성공 완료
    FAILED = "failed"      # 에러로 인한 실패
    SKIPPED = "skipped"    # 건너뜀
    CANCELLED = "cancelled"# 강제 취소됨

class AgentContext(BaseModel):
    """
    [코어 핵심] 모든 에이전트들이 공통으로 데이터를 읽고 쓰는 '제네릭 상태 머신 컨텍스트'입니다.
    기존의 GitLab 정보나 특정 도메인 변수(mr_iid 등)를 직접 갖고 있지 않고, 
    서비스 플러그인이 자유롭게 사용할 수 있는 동적 딕셔너리 구조를 제공하여 강결합을 방지합니다.
    """
    # 고유 작업 아이디 (로그 추적용)
    task_id: str
    
    # [핵심] 서비스 플러그인이 수신한 웹훅 원본이나 설정 데이터를 보관하는 메타데이터 공간
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # [핵심] 각 에이전트들이 자신의 가공 완료 결과물을 담아 다음 에이전트에 물려주는 데이터 공간
    # 예: {"git_diff": "...", "review_results": [...]}
    outputs: Dict[str, Any] = Field(default_factory=dict)

    # 현재 실행 중인 에이전트명 (예: 'PlanningAgent')
    current_stage: str = "init"
    
    # 에이전트들의 실시간 진행 및 히스토리 이력로그를 타임스탬프와 함께 자동 기록하는 리스트
    history: List[Dict[str, Any]] = Field(default_factory=list, description="에이전트 실행 및 추적용 로그 기록")

    # 전체 워크플로우 시간 측정용 시작/종료 시각
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # 실행 중 발생한 예외 에러 메시지 보관함
    error: Optional[str] = None
    
    # 사용자의 실행 취소 요청 신호 플래그 (True 시 즉각 기동 정지)
    is_cancelled: bool = False

    def add_history(self, agent_name: str, action: str, details: Any = None):
        """
        에이전트가 어떤 상태로 진입했는지 진행 상황 히스토리를 타임스탬프와 함께 자동으로 밀어 넣습니다.
        
        Args:
            agent_name: 기록을 작성하는 에이전트 식별명
            action: 상태값 ('started' | 'completed' | 'info' | 'error')
            details: 로그 상세 요약본
        """
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "action": action,
            "details": str(details) if details else ""
        })

    def get_output(self, key: str, default: Any = None) -> Any:
        """
        이전 에이전트가 outputs에 채워둔 결과물을 안전하게 조회합니다.
        
        Args:
            key: 조회할 결과물의 키값 (예: 'git_diff')
            default: 해당 키가 없을 경우 반환할 기본값
        """
        return self.outputs.get(key, default)

    def set_output(self, key: str, value: Any):
        """
        내가 완료한 성과물을 outputs 공간에 등록하여 다음 순서의 에이전트가 쓸 수 있게 전송합니다.
        
        Args:
            key: 등록할 데이터의 고유 이름
            value: 가공한 데이터 내용물
        """
        self.outputs[key] = value
