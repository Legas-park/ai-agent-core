from typing import Dict, Any, Optional
from loguru import logger

class LLMProviderRegistry:
    """
    [코어 핵심] 다양한 LLM 공급자(Gemini, Ollama, OpenAI 등) 클라이언트 객체를 중앙 집중 관리하는 레지스트리입니다.
    서비스 플러그인 에이전트들은 여기에 직접 API 키를 들고 접근하는 대신, 
    'llm_registry.get_provider("gemini")'를 호출하여 잘 정돈된 공통 클라이언트를 꺼내 씁니다.
    이를 통해 API 클라이언트 초기화 코드와 설정이 서비스 에이전트들에 흩어지는 것을 예방합니다.
    """
    def __init__(self):
        # 등록된 LLM 클라이언트 인스턴스들을 모아두는 고유 레지스트리 저장소
        self.providers: Dict[str, Any] = {}
        # 기본 공급자 식별 키 (설정에서 주입). 미지정 시 첫 등록 공급자를 사용.
        self.default_name: Optional[str] = None

    def set_default(self, name: str):
        """기본 공급자 키를 지정합니다. 설정값(default_llm_provider)을 반영할 때 사용합니다."""
        self.default_name = name

    def register_provider(self, name: str, client_instance: Any):
        """
        초기화 완료된 실제 LLM 클라이언트를 레지스트리에 보관합니다.
        보통 서버 기동 라이프사이클(`lifespan`) 시작 시점에 중앙 연동 설정 후 한번 등록합니다.
        
        Args:
            name: 공급자 고유 식별 키 (예: 'gemini', 'ollama')
            client_instance: 초기화가 완료된 실제 API 연동 클라이언트 SDK 인스턴스
        """
        self.providers[name] = client_instance
        logger.info(f"새로운 공통 LLM 서비스 공급자가 레지스트리에 활성화되었습니다: {name}")

    def get_provider(self, name: str) -> Optional[Any]:
        """
        에이전트가 비즈니스 프롬프트를 보낼 때, 레지스트리에 보관된 클라이언트를 획득합니다.
        
        Args:
            name: 획득할 공급자 식별 이름 (예: 'gemini')
        Returns:
            사전에 기동된 실제 API 클라이언트 객체
        """
        return self.providers.get(name)

    def get_default(self) -> Optional[Any]:
        """
        설정된 기본 공급자를 반환합니다. 우선순위는
        (1) set_default()로 지정한 키 → (2) 등록된 첫 공급자 순입니다.
        하나도 등록되지 않았다면 None을 반환하여 호출 측이 LLM 단계를 건너뛸 수 있게 합니다.
        """
        if self.default_name and self.default_name in self.providers:
            return self.providers[self.default_name]
        if self.providers:
            return next(iter(self.providers.values()))
        return None

# 전역에서 공통으로 클라이언트를 주입받고 추출해 쓸 수 있도록 레지스트리 싱글톤 인스턴스화
llm_registry = LLMProviderRegistry()
