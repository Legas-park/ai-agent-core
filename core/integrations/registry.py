from typing import Any, Dict, Optional
from loguru import logger


class IntegrationRegistry:
    """
    [코어 통합] 외부 SaaS 클라이언트(GitLab, Jira 등)를 이름으로 중앙 보관하는 레지스트리입니다.
    LLMProviderRegistry와 같은 패턴으로, 에이전트가 토큰을 직접 들고 다니지 않고
    'integration_registry.get("gitlab")' 한 줄로 초기화된 클라이언트를 꺼내 씁니다.
    """

    def __init__(self):
        self._clients: Dict[str, Any] = {}

    def register(self, name: str, client: Any):
        if client is None:
            return
        self._clients[name] = client
        logger.info(f"외부 통합 클라이언트 등록: {name}")

    def get(self, name: str) -> Optional[Any]:
        return self._clients.get(name)


integration_registry = IntegrationRegistry()
